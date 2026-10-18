#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define ADMIN_PAGE g_rsql_meta_page0
#define DATABASE_INFO (*(RsqlDatabaseInfo*)g_rsql_meta_page1)
#define TABLE_INFO (*(RsqlSchemaTableInfo*)g_rsql_meta_page1)
#define COLUMN_INFO (*(RsqlSchemaColumnInfo*)g_rsql_meta_page1)
#define INDEX_INFO (*(RsqlSchemaIndexInfo*)g_rsql_meta_page1)
#define TYPE_INFO (*(RsqlSchemaTypeInfo*)g_rsql_meta_page1)
#define MEMBER_INFO (*(RsqlSchemaMemberInfo*)g_rsql_meta_page1)
#define BITMAP_FIRST_PAGE 2u

static rsql_u16 g_inspect_skip;

static rsql_u8 valid_page(char a, char b, char c, char d) {
    return ADMIN_PAGE[0] == (rsql_u8)a &&
        ADMIN_PAGE[1] == (rsql_u8)b &&
        ADMIN_PAGE[2] == (rsql_u8)c &&
        ADMIN_PAGE[3] == (rsql_u8)d &&
        ADMIN_PAGE[4] == RSQL_STORAGE_VERSION &&
        ADMIN_PAGE[RSQL_PAGE_CHECKSUM_OFFSET] == rsql_page_checksum(ADMIN_PAGE);
}

static rsql_u8 read_page(rsql_u16 page, char a, char b, char c, char d) {
    rsql_u8 rc;
    if (page == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
    rc = rsql_reu_read(rsql_reu_page_address(page), ADMIN_PAGE,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_page(a, b, c, d) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 read_root(void) {
    return read_page(rsql_page_catalog_root(), 'R', 'C', 'A', 'T');
}

static rsql_u8 folded(rsql_u8 value) {
    return value >= 'a' && value <= 'z'
        ? (rsql_u8)(value - ('a' - 'A')) : value;
}

static rsql_u8 equal_name(const char* wanted, const rsql_u8* stored,
                          rsql_u8 length) {
    rsql_u8 index;
    for (index = 0u; index < length; ++index) {
        if (!wanted[index] ||
            folded((rsql_u8)wanted[index]) != folded(stored[index])) return 0u;
    }
    return wanted[length] == 0;
}

static void put_count(RsqlI32* destination, unsigned long value) {
    rsql_put_u32(destination->bytes, value);
}

static rsql_u8 emit_record(RsqlExecRequest* request, const void* source,
                           rsql_u16 size) {
    rsql_u16 returned;
    rsql_u16 offset = 0u;
    rsql_u16 index;
    rsql_u8* destination;
    returned = request->output.inspect.returned;
    for (index = 0u; index < returned; ++index) {
        if (offset > (rsql_u16)(request->output.inspect.capacity - size)) {
            return 0u;
        }
        offset += size;
    }
    if (size > (rsql_u16)(request->output.inspect.capacity - offset)) {
        return 0u;
    }
    destination = (rsql_u8*)request->output.inspect.records + offset;
    memcpy(destination, source, size);
    request->output.inspect.returned = returned + 1u;
    return 1u;
}

static rsql_u8 find_table(const char* name, rsql_u16* page_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u8 flags;
    rsql_u8 length;
    rsql_u8 rc = read_root();
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_TABLE]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_TABLE_NEXT]);
        flags = ADMIN_PAGE[RSQL_TABLE_FLAGS];
        length = ADMIN_PAGE[RSQL_TABLE_NAME_LENGTH];
        if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(flags & (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING)) &&
            equal_name(name, &ADMIN_PAGE[RSQL_TABLE_NAME], length)) {
            *page_out = page;
            return RSQL_OK;
        }
        page = next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 count_chain(rsql_u16 page, char c,
                           rsql_u16 next_offset, rsql_u16* count_out) {
    rsql_u16 count = 0u;
    rsql_u16 next;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        /* Row pages predate per-page checksums; leaves and members have one. */
        if (c == 'R') {
            rc = rsql_reu_read(rsql_reu_page_address(page), ADMIN_PAGE,
                               RSQL_REU_PAGE_SIZE);
            if (rc == RSQL_OK &&
                (ADMIN_PAGE[0] != 'R' || ADMIN_PAGE[1] != 'R' ||
                 ADMIN_PAGE[2] != 'O' || ADMIN_PAGE[3] != 'W' ||
                 ADMIN_PAGE[4] != RSQL_STORAGE_VERSION ||
                 ADMIN_PAGE[RSQL_ROW_CAPACITY] == 0u ||
                 ADMIN_PAGE[RSQL_ROW_CAPACITY] > 32u)) {
                rc = RSQL_ERR_CORRUPT_STORAGE;
            }
        } else if (c == 'I') {
            rc = read_page(page, 'R', 'I', 'L', 'F');
        } else {
            rc = read_page(page, 'R', 'E', 'M', 'B');
        }
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[next_offset]);
        ++count;
        if (count > (rsql_u16)rsql_page_limit()) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        page = next;
    }
    *count_out = count;
    return RSQL_OK;
}

static rsql_u8 show_database(RsqlExecRequest* request) {
    rsql_u16 first = rsql_page_first_usable();
    rsql_u16 limit = (rsql_u16)rsql_page_limit();
    rsql_u16 byte_index = first >> 3u;
    rsql_u16 byte_limit = (rsql_u16)((limit + 7u) >> 3u);
    rsql_u16 page;
    rsql_u16 used = 0u;
    rsql_u16 chunk;
    rsql_u16 index;
    rsql_u8 bit;
    rsql_u8 rc;
    rsql_u16 table_count = 0u;
    rsql_u16 index_count = 0u;
    rsql_u16 type_count = 0u;
    rsql_u16 descriptor;
    rsql_u16 next;

    if (request->output.inspect.capacity < sizeof(DATABASE_INFO)) return RSQL_ERR_INVALID_ARGUMENT;
    while (byte_index < byte_limit) {
        chunk = byte_limit - byte_index;
        if (chunk > RSQL_REU_PAGE_SIZE) chunk = RSQL_REU_PAGE_SIZE;
        rc = rsql_reu_read(rsql_reu_page_address(BITMAP_FIRST_PAGE) +
                           byte_index, ADMIN_PAGE, chunk);
        if (rc != RSQL_OK) return rc;
        for (index = 0u; index < chunk; ++index) {
            for (bit = 0u; bit < 8u; ++bit) {
                page = (rsql_u16)(((byte_index + index) << 3u) + bit);
                if (page >= first && page < limit &&
                    (ADMIN_PAGE[index] & (rsql_u8)(1u << bit))) ++used;
            }
        }
        byte_index += chunk;
    }

    rc = read_root();
    if (rc != RSQL_OK) return rc;
    descriptor = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_TABLE]);
    while (descriptor != RSQL_PAGE_NONE) {
        rc = read_page(descriptor, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_TABLE_NEXT]);
        if (!(ADMIN_PAGE[RSQL_TABLE_FLAGS] &
              (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING))) {
            ++table_count;
        }
        descriptor = next;
    }
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    descriptor = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_INDEX]);
    while (descriptor != RSQL_PAGE_NONE) {
        rc = read_page(descriptor, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_INDEX_NEXT]);
        if (!(ADMIN_PAGE[RSQL_INDEX_FLAGS] & RSQL_INDEX_FLAG_DROPPING)) {
            ++index_count;
        }
        descriptor = next;
    }
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    descriptor = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_ENUM]);
    while (descriptor != RSQL_PAGE_NONE) {
        rc = read_page(descriptor, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_NEXT]);
        if (!(ADMIN_PAGE[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING)) {
            ++type_count;
        }
        descriptor = next;
    }

    put_count(&DATABASE_INFO.reu_pages, rsql_reu_page_count());
    put_count(&DATABASE_INFO.database_capacity_pages, limit - first);
    put_count(&DATABASE_INFO.database_used_pages, used);
    put_count(&DATABASE_INFO.database_free_pages, limit - first - used);
    DATABASE_INFO.table_count = table_count;
    DATABASE_INFO.index_count = index_count;
    DATABASE_INFO.type_count = type_count;
    if (g_inspect_skip != 0u) return RSQL_OK;
    return emit_record(request, &DATABASE_INFO, sizeof(DATABASE_INFO))
        ? RSQL_OK : RSQL_ERR_INVALID_ARGUMENT;
}

static rsql_u8 show_tables(RsqlExecRequest* request) {
    rsql_u16 row_pages;
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 head;
    rsql_u16 visible = 0u;
    rsql_u8 flags;
    rsql_u8 rc = read_root();
    if (request->output.inspect.capacity < sizeof(TABLE_INFO)) return RSQL_ERR_INVALID_ARGUMENT;
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_TABLE]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_TABLE_NEXT]);
        flags = ADMIN_PAGE[RSQL_TABLE_FLAGS];
        if (!(flags & (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING))) {
            if (g_inspect_skip != 0u) {
                --g_inspect_skip;
                ++visible;
                page = next;
                continue;
            }
            memset(&TABLE_INFO, 0, sizeof(TABLE_INFO));
            TABLE_INFO.table_page = page;
            TABLE_INFO.flags = flags;
            TABLE_INFO.column_count = ADMIN_PAGE[RSQL_TABLE_COLUMN_COUNT];
            TABLE_INFO.row_width = rsql_get_u16(&ADMIN_PAGE[RSQL_TABLE_ROW_WIDTH]);
            memcpy(TABLE_INFO.row_count.bytes, &ADMIN_PAGE[RSQL_TABLE_ROW_COUNT], 4u);
            TABLE_INFO.name_length = ADMIN_PAGE[RSQL_TABLE_NAME_LENGTH];
            if (TABLE_INFO.name_length > RSQL_TABLE_NAME_MAX) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            memcpy(TABLE_INFO.name, &ADMIN_PAGE[RSQL_TABLE_NAME], TABLE_INFO.name_length);
            TABLE_INFO.name[TABLE_INFO.name_length] = 0;
            head = rsql_get_u16(&ADMIN_PAGE[RSQL_TABLE_ROW_HEAD]);
            rc = count_chain(head, 'R', RSQL_ROW_NEXT, &row_pages);
            if (rc != RSQL_OK) return rc;
            put_count(&TABLE_INFO.row_pages, row_pages);
            if (!emit_record(request, &TABLE_INFO, sizeof(TABLE_INFO))) break;
            ++visible;
        }
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 show_columns(RsqlExecRequest* request) {
    rsql_u16 table;
    rsql_u8 count;
    rsql_u8 column;
    rsql_u8 rc;
    if (request->output.inspect.capacity < sizeof(COLUMN_INFO)) return RSQL_ERR_INVALID_ARGUMENT;
    rc = find_table(g_rsql_statement.table_name, &table);
    if (rc != RSQL_OK) return rc;
    rc = read_page(table, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    count = ADMIN_PAGE[RSQL_TABLE_COLUMN_COUNT];
    if (g_inspect_skip >= count) return RSQL_OK;
    column = (rsql_u8)g_inspect_skip;
    while (column < count) {
        switch (column) {
            case 0u: memmove(ADMIN_PAGE, &ADMIN_PAGE[44u], 24u); break;
            case 1u: memmove(ADMIN_PAGE, &ADMIN_PAGE[68u], 24u); break;
            case 2u: memmove(ADMIN_PAGE, &ADMIN_PAGE[92u], 24u); break;
            case 3u: memmove(ADMIN_PAGE, &ADMIN_PAGE[116u], 24u); break;
            case 4u: memmove(ADMIN_PAGE, &ADMIN_PAGE[140u], 24u); break;
            case 5u: memmove(ADMIN_PAGE, &ADMIN_PAGE[164u], 24u); break;
            case 6u: memmove(ADMIN_PAGE, &ADMIN_PAGE[188u], 24u); break;
            case 7u: memmove(ADMIN_PAGE, &ADMIN_PAGE[212u], 24u); break;
        }
        memset(&COLUMN_INFO, 0, sizeof(COLUMN_INFO));
        COLUMN_INFO.type.tag = ADMIN_PAGE[RSQL_COLUMN_TYPE];
        COLUMN_INFO.type.flags = ADMIN_PAGE[RSQL_COLUMN_FLAGS];
        COLUMN_INFO.type.parameter = COLUMN_INFO.type.tag == RSQL_TYPE_CHAR
            ? rsql_get_u16(&ADMIN_PAGE[RSQL_COLUMN_WIDTH]) : 0u;
        COLUMN_INFO.type.auxiliary = rsql_get_u16(
            &ADMIN_PAGE[RSQL_COLUMN_AUXILIARY]);
        COLUMN_INFO.offset = rsql_get_u16(&ADMIN_PAGE[RSQL_COLUMN_OFFSET]);
        COLUMN_INFO.name_length = ADMIN_PAGE[RSQL_COLUMN_NAME_LENGTH];
        if (COLUMN_INFO.name_length > RSQL_COLUMN_NAME_MAX) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        memcpy(COLUMN_INFO.name, &ADMIN_PAGE[RSQL_COLUMN_NAME], COLUMN_INFO.name_length);
        COLUMN_INFO.name[COLUMN_INFO.name_length] = 0;
        if (!emit_record(request, &COLUMN_INFO, sizeof(COLUMN_INFO))) break;
        ++column;
    }
    return RSQL_OK;
}

static rsql_u8 show_indexes(RsqlExecRequest* request) {
    RsqlSchemaIndexInfo info;
    rsql_u16 leaf_pages;
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 head;
    rsql_u16 visible = 0u;
    rsql_u8 rc = read_root();
    if (request->output.inspect.capacity < sizeof(info)) return RSQL_ERR_INVALID_ARGUMENT;
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_INDEX]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_INDEX_NEXT]);
        if (!(ADMIN_PAGE[RSQL_INDEX_FLAGS] & RSQL_INDEX_FLAG_DROPPING)) {
            if (g_inspect_skip != 0u) {
                --g_inspect_skip;
                ++visible;
                page = next;
                continue;
            }
            memset(&info, 0, sizeof(info));
            info.index_page = page;
            info.table_page = rsql_get_u16(&ADMIN_PAGE[RSQL_INDEX_TABLE]);
            memcpy(info.entry_count.bytes,
                   &ADMIN_PAGE[RSQL_INDEX_ENTRY_COUNT], 4u);
            info.key_width = ADMIN_PAGE[RSQL_INDEX_KEY_WIDTH];
            info.column_count = ADMIN_PAGE[RSQL_INDEX_COLUMN_COUNT];
            if (info.column_count > RSQL_TABLE_COLUMNS_MAX) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            memcpy(info.columns, &ADMIN_PAGE[RSQL_INDEX_COLUMNS],
                   info.column_count);
            info.name_length = ADMIN_PAGE[RSQL_INDEX_NAME_LENGTH];
            if (info.name_length > RSQL_TABLE_NAME_MAX) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            memcpy(info.name, &ADMIN_PAGE[RSQL_INDEX_NAME], info.name_length);
            info.name[info.name_length] = 0;
            head = rsql_get_u16(&ADMIN_PAGE[RSQL_INDEX_LEAF_HEAD]);
            rc = count_chain(head, 'I', RSQL_INDEX_LEAF_NEXT, &leaf_pages);
            if (rc != RSQL_OK) return rc;
            put_count(&info.leaf_pages, leaf_pages);
            if (!emit_record(request, &info, sizeof(info))) break;
            ++visible;
        }
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 find_type(const char* name, rsql_u16* page_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u8 length;
    rsql_u8 rc = read_root();
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_ENUM]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_NEXT]);
        length = ADMIN_PAGE[RSQL_ENUM_NAME_LENGTH];
        if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(ADMIN_PAGE[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING) &&
            equal_name(name, &ADMIN_PAGE[RSQL_ENUM_NAME], length)) {
            *page_out = page;
            return RSQL_OK;
        }
        page = next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 show_types(RsqlExecRequest* request) {
    RsqlSchemaTypeInfo info;
    rsql_u16 member_pages;
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 head;
    rsql_u16 visible = 0u;
    rsql_u8 rc = read_root();
    if (request->output.inspect.capacity < sizeof(info)) return RSQL_ERR_INVALID_ARGUMENT;
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ROOT_FIRST_ENUM]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_NEXT]);
        if (!(ADMIN_PAGE[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING)) {
            if (g_inspect_skip != 0u) {
                --g_inspect_skip;
                ++visible;
                page = next;
                continue;
            }
            memset(&info, 0, sizeof(info));
            info.type_page = page;
            info.type_id = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_ID]);
            info.member_count = rsql_get_u16(
                &ADMIN_PAGE[RSQL_ENUM_MEMBER_COUNT]);
            info.width = ADMIN_PAGE[RSQL_ENUM_WIDTH];
            info.name_length = ADMIN_PAGE[RSQL_ENUM_NAME_LENGTH];
            if (info.name_length > RSQL_TABLE_NAME_MAX) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            memcpy(info.name, &ADMIN_PAGE[RSQL_ENUM_NAME], info.name_length);
            info.name[info.name_length] = 0;
            head = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_FIRST_MEMBERS]);
            rc = count_chain(head, 'E', RSQL_ENUM_MEMBER_PAGE_NEXT,
                             &member_pages);
            if (rc != RSQL_OK) return rc;
            put_count(&info.member_pages, member_pages);
            if (!emit_record(request, &info, sizeof(info))) break;
            ++visible;
        }
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 show_members(RsqlExecRequest* request) {
    RsqlSchemaMemberInfo info;
    rsql_u16 type_page;
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 base;
    rsql_u16 visible = 0u;
    rsql_u8 count;
    rsql_u8 slot;
    rsql_u8 rc;
    if (request->output.inspect.capacity < sizeof(info)) return RSQL_ERR_INVALID_ARGUMENT;
    rc = find_type(g_rsql_statement.table_name, &type_page);
    if (rc != RSQL_OK) return rc;
    rc = read_page(type_page, 'R', 'E', 'N', 'T');
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_FIRST_MEMBERS]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_page(page, 'R', 'E', 'M', 'B');
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&ADMIN_PAGE[RSQL_ENUM_MEMBER_PAGE_NEXT]);
        count = ADMIN_PAGE[RSQL_ENUM_MEMBER_PAGE_COUNT];
        for (slot = 0u; slot < count; ++slot, ++visible) {
            if (g_inspect_skip != 0u) {
                --g_inspect_skip;
                continue;
            }
            base = (rsql_u16)(RSQL_ENUM_MEMBER_PAGE_ENTRIES +
                (rsql_u16)slot * RSQL_ENUM_MEMBER_ENTRY_BYTES);
            memset(&info, 0, sizeof(info));
            info.value = rsql_get_u16(
                &ADMIN_PAGE[base + RSQL_ENUM_MEMBER_VALUE]);
            info.name_length = ADMIN_PAGE[
                base + RSQL_ENUM_MEMBER_NAME_LENGTH];
            if (info.name_length > RSQL_COLUMN_NAME_MAX) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            memcpy(info.name, &ADMIN_PAGE[base + RSQL_ENUM_MEMBER_NAME],
                   info.name_length);
            info.name[info.name_length] = 0;
            if (!emit_record(request, &info, sizeof(info))) {
                return RSQL_OK;
            }
        }
        page = next;
    }
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_inspect_phase(RsqlExecRequest* request) {
    if (!request || !request->output.inspect.records) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    g_inspect_skip = request->output.inspect.start;
    switch (g_rsql_statement.kind) {
        case RSQL_STMT_SHOW_DATABASE: return show_database(request);
        case RSQL_STMT_SHOW_TABLES: return show_tables(request);
        case RSQL_STMT_SHOW_COLUMNS: return show_columns(request);
        case RSQL_STMT_SHOW_INDEXES: return show_indexes(request);
        case RSQL_STMT_SHOW_TYPES: return show_types(request);
        case RSQL_STMT_SHOW_MEMBERS: return show_members(request);
    }
    return RSQL_ERR_UNSUPPORTED_SQL;
}

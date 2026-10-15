#include <string.h>

#include "rsql_errors.h"
#include "rsql_index.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define INDEX_DESCRIPTOR g_rsql_meta_page1
#define INDEX_PAGE       g_rsql_meta_page0

/* Simple scalars deliberately avoid retaining deep-build continuation state
 * in cc65 parameter/local slots or inside dynamically addressed structures. */
static rsql_u16 g_build_descriptor_page = RSQL_PAGE_NONE;
static rsql_u16 g_build_table_page = RSQL_PAGE_NONE;
static rsql_u16 g_build_old_head = RSQL_PAGE_NONE;
static rsql_u16 g_build_row_page = RSQL_PAGE_NONE;
static rsql_u16 g_build_next_page = RSQL_PAGE_NONE;

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ((rsql_u8)'a' - (rsql_u8)'A'));
    }
    return value;
}

static rsql_u8 bit_mask(rsql_u8 bit) {
    switch (bit & 7u) {
        case 0u: return 0x01u;
        case 1u: return 0x02u;
        case 2u: return 0x04u;
        case 3u: return 0x08u;
        case 4u: return 0x10u;
        case 5u: return 0x20u;
        case 6u: return 0x40u;
        case 7u: return 0x80u;
    }
    return 0u;
}

static rsql_u8 name_equal(const char* wanted, const rsql_u8* stored,
                          rsql_u8 stored_length) {
    rsql_u8 index;
    for (index = 0u; index < stored_length; ++index) {
        if (wanted[index] == 0u ||
            folded((rsql_u8)wanted[index]) != folded(stored[index])) return 0u;
    }
    return wanted[stored_length] == 0u;
}

static rsql_u8 valid_magic(const rsql_u8* page, char c, char d) {
    return page[0] == 'R' && page[1] == 'I' &&
           page[2] == (rsql_u8)c && page[3] == (rsql_u8)d &&
           page[4] == RSQL_STORAGE_VERSION &&
           page[RSQL_PAGE_CHECKSUM_OFFSET] == rsql_page_checksum(page);
}

static rsql_u8 read_root(void) {
    rsql_u8 rc = rsql_reu_read(
        rsql_reu_page_address(rsql_page_catalog_root()), INDEX_DESCRIPTOR,
        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (INDEX_DESCRIPTOR[0] != 'R' || INDEX_DESCRIPTOR[1] != 'C' ||
        INDEX_DESCRIPTOR[2] != 'A' || INDEX_DESCRIPTOR[3] != 'T' ||
        INDEX_DESCRIPTOR[4] != RSQL_STORAGE_VERSION ||
        INDEX_DESCRIPTOR[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(INDEX_DESCRIPTOR)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 read_descriptor(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), INDEX_DESCRIPTOR,
                               RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_magic(INDEX_DESCRIPTOR, 'D', 'X')
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 write_descriptor(rsql_u16 page) {
    INDEX_DESCRIPTOR[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(INDEX_DESCRIPTOR);
    return rsql_reu_write(rsql_reu_page_address(page), INDEX_DESCRIPTOR,
                          RSQL_REU_PAGE_SIZE);
}

static rsql_u8 read_leaf(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), INDEX_PAGE,
                               RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_magic(INDEX_PAGE, 'L', 'F')
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 write_leaf(rsql_u16 page, rsql_u8* bytes) {
    bytes[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(bytes);
    return rsql_reu_write(rsql_reu_page_address(page), bytes,
                          RSQL_REU_PAGE_SIZE);
}

static rsql_u16 type_width(const RsqlTypeSpec* type) {
    switch (type->tag) {
        case RSQL_TYPE_BOOLEAN:
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8: return 1u;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_FIXED8_8:
        case RSQL_TYPE_ENUM16: return 2u;
        case RSQL_TYPE_I32: return 4u;
        case RSQL_TYPE_FLOAT5: return 5u;
        case RSQL_TYPE_I64: return 8u;
        case RSQL_TYPE_CHAR: return type->parameter;
    }
    return 0u;
}

static rsql_u8 find_index(const char* name, rsql_u16* page_out) {
    rsql_u16 page;
    rsql_u8 length;
    rsql_u8 rc = read_root();
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_ROOT_FIRST_INDEX]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_descriptor(page);
        if (rc != RSQL_OK) return rc;
        length = INDEX_DESCRIPTOR[RSQL_INDEX_NAME_LENGTH];
        if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(INDEX_DESCRIPTOR[RSQL_INDEX_FLAGS] &
                RSQL_INDEX_FLAG_DROPPING) &&
            name_equal(name, &INDEX_DESCRIPTOR[RSQL_INDEX_NAME], length)) {
            *page_out = page;
            return RSQL_OK;
        }
        page = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static void initialize_leaf(rsql_u8* page, rsql_u8 key_width,
                            rsql_u16 previous, rsql_u16 next) {
    rsql_u8 entry_width = (rsql_u8)(key_width + 3u);
    memset(page, 0, RSQL_REU_PAGE_SIZE);
    page[0] = 'R'; page[1] = 'I'; page[2] = 'L'; page[3] = 'F';
    page[4] = RSQL_STORAGE_VERSION;
    page[RSQL_INDEX_LEAF_CAPACITY] =
        (rsql_u8)((RSQL_PAGE_CHECKSUM_OFFSET - RSQL_INDEX_LEAF_DATA) /
                  entry_width);
    rsql_put_u16(&page[RSQL_INDEX_LEAF_NEXT], next);
    rsql_put_u16(&page[RSQL_INDEX_LEAF_PREVIOUS], previous);
    page[RSQL_INDEX_LEAF_KEY_WIDTH] = key_width;
}

static rsql_i8 compare_entry(const rsql_u8* entry, const rsql_u8* key,
                             rsql_u8 key_width, const RsqlRowId* row_id) {
    rsql_i8 comparison = (rsql_i8)memcmp(entry, key, key_width);
    rsql_u16 page;
    if (comparison != 0) return comparison;
    page = rsql_get_u16(&entry[key_width]);
    if (page < row_id->page) return -1;
    if (page > row_id->page) return 1;
    if (entry[key_width + 2u] < row_id->slot) return -1;
    if (entry[key_width + 2u] > row_id->slot) return 1;
    return 0;
}

static rsql_u8 split_leaf(rsql_u16 descriptor_page, rsql_u16 leaf_page) {
    rsql_u16 next;
    rsql_u16 new_page;
    rsql_u8 entry_width;
    rsql_u8 count;
    rsql_u8 lower;
    rsql_u8 upper;
    rsql_u8 rc;
    rc = read_leaf(leaf_page);
    if (rc != RSQL_OK) return rc;
    count = INDEX_PAGE[RSQL_INDEX_LEAF_COUNT];
    lower = (rsql_u8)(count >> 1u);
    upper = (rsql_u8)(count - lower);
    entry_width = (rsql_u8)(INDEX_PAGE[RSQL_INDEX_LEAF_KEY_WIDTH] + 3u);
    next = rsql_get_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_NEXT]);
    rc = rsql_page_allocate(&new_page);
    if (rc != RSQL_OK) return rc;
    initialize_leaf(INDEX_DESCRIPTOR, INDEX_PAGE[RSQL_INDEX_LEAF_KEY_WIDTH],
                    leaf_page, next);
    memcpy(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_DATA],
           &INDEX_PAGE[RSQL_INDEX_LEAF_DATA + (rsql_u16)lower * entry_width],
           (rsql_u16)upper * entry_width);
    INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_COUNT] = upper;
    INDEX_PAGE[RSQL_INDEX_LEAF_COUNT] = lower;
    rsql_put_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_NEXT], new_page);
    rc = write_leaf(leaf_page, INDEX_PAGE);
    if (rc == RSQL_OK) rc = write_leaf(new_page, INDEX_DESCRIPTOR);
    if (rc != RSQL_OK) return rc;
    if (next != RSQL_PAGE_NONE) {
        rc = read_leaf(next);
        if (rc != RSQL_OK) return rc;
        rsql_put_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_PREVIOUS], new_page);
        return write_leaf(next, INDEX_PAGE);
    }
    rc = read_descriptor(descriptor_page);
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_TAIL], new_page);
    return write_descriptor(descriptor_page);
}

static rsql_u8 insert_entry(rsql_u16 descriptor_page, const rsql_u8* key,
                            const RsqlRowId* row_id) {
    rsql_u16 leaf;
    rsql_u16 next;
    rsql_u16 base;
    rsql_u8 entry_width;
    rsql_u8 key_width;
    rsql_u8 count;
    rsql_u8 slot;
    rsql_u8 rc;
retry:
    rc = read_descriptor(descriptor_page);
    if (rc != RSQL_OK) return rc;
    key_width = INDEX_DESCRIPTOR[RSQL_INDEX_KEY_WIDTH];
    entry_width = (rsql_u8)(key_width + 3u);
    leaf = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD]);
    if (leaf == RSQL_PAGE_NONE) {
        rc = rsql_page_allocate(&leaf);
        if (rc != RSQL_OK) return rc;
        initialize_leaf(INDEX_PAGE, key_width, RSQL_PAGE_NONE, RSQL_PAGE_NONE);
        rc = write_leaf(leaf, INDEX_PAGE);
        if (rc != RSQL_OK) return rc;
        rc = read_descriptor(descriptor_page);
        if (rc != RSQL_OK) return rc;
        rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD], leaf);
        rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_TAIL], leaf);
        rc = write_descriptor(descriptor_page);
        if (rc != RSQL_OK) return rc;
    }
    while (leaf != RSQL_PAGE_NONE) {
        rc = read_leaf(leaf);
        if (rc != RSQL_OK) return rc;
        if (INDEX_PAGE[RSQL_INDEX_LEAF_KEY_WIDTH] != key_width) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        count = INDEX_PAGE[RSQL_INDEX_LEAF_COUNT];
        for (slot = 0u; slot < count; ++slot) {
            base = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                              (rsql_u16)slot * entry_width);
            if (compare_entry(&INDEX_PAGE[base], key, key_width, row_id) >= 0) {
                break;
            }
        }
        next = rsql_get_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_NEXT]);
        if (slot == count && next != RSQL_PAGE_NONE) {
            leaf = next;
            continue;
        }
        if (count >= INDEX_PAGE[RSQL_INDEX_LEAF_CAPACITY]) {
            rc = split_leaf(descriptor_page, leaf);
            if (rc != RSQL_OK) return rc;
            goto retry;
        }
        base = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                          (rsql_u16)slot * entry_width);
        memmove(&INDEX_PAGE[base + entry_width], &INDEX_PAGE[base],
                (rsql_u16)(count - slot) * entry_width);
        memcpy(&INDEX_PAGE[base], key, key_width);
        rsql_put_u16(&INDEX_PAGE[base + key_width], row_id->page);
        INDEX_PAGE[base + key_width + 2u] = row_id->slot;
        INDEX_PAGE[RSQL_INDEX_LEAF_COUNT] = (rsql_u8)(count + 1u);
        rc = write_leaf(leaf, INDEX_PAGE);
        if (rc != RSQL_OK) return rc;
        rc = read_descriptor(descriptor_page);
        if (rc != RSQL_OK) return rc;
        rsql_increment_u32(&INDEX_DESCRIPTOR[RSQL_INDEX_ENTRY_COUNT]);
        return write_descriptor(descriptor_page);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 build_key(const rsql_u8* row, const rsql_u8* columns,
                         const rsql_u16* offsets, const rsql_u16* widths,
                         rsql_u8 column_count, rsql_u8* key_out,
                         rsql_u8 expected_width) {
    rsql_u16 width;
    rsql_u8 source;
    rsql_u8 offset = 0u;
    rsql_u8 index;
    for (index = 0u; index < column_count; ++index) {
        source = columns[index];
        width = widths[index];
        if (width == 0u || (rsql_u16)offset + width + 1u > expected_width) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        if (row[0] & (rsql_u8)(1u << source)) {
            key_out[offset++] = 0u;
            memset(&key_out[offset], 0, width);
        } else {
            key_out[offset++] = 1u;
            memcpy(&key_out[offset], &row[offsets[index]], width);
        }
        offset = (rsql_u8)(offset + width);
    }
    return offset == expected_width ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 free_leaf_chain(rsql_u16 page) {
    rsql_u16 next;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = read_leaf(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_NEXT]);
        rc = rsql_page_free(page);
        if (rc != RSQL_OK) return rc;
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 build_index(rsql_u16 descriptor_page) {
    RsqlTypeSpec type;
    rsql_u16 base;
    rsql_u16 offset;
    rsql_u16 offsets[RSQL_TABLE_COLUMNS_MAX];
    rsql_u16 widths[RSQL_TABLE_COLUMNS_MAX];
    RsqlRowId row_id;
    rsql_u8 columns[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 column_count;
    rsql_u8 key_width;
    rsql_u8 capacity;
    rsql_u8 index;
    rsql_u8 slot;
    rsql_u8 rc;
    rc = read_descriptor(descriptor_page);
    if (rc != RSQL_OK) return rc;
    g_build_descriptor_page = descriptor_page;
    g_build_table_page = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_TABLE]);
    g_build_old_head =
        rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD]);
    key_width = INDEX_DESCRIPTOR[RSQL_INDEX_KEY_WIDTH];
    column_count = INDEX_DESCRIPTOR[RSQL_INDEX_COLUMN_COUNT];
    if (column_count == 0u || column_count > RSQL_TABLE_COLUMNS_MAX ||
        key_width == 0u || key_width > RSQL_INDEX_KEY_MAX) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    memcpy(columns, &INDEX_DESCRIPTOR[RSQL_INDEX_COLUMNS], column_count);
    /* Consume the table reference while the descriptor page is still live.
     * No C-local or resident copy has to survive another helper call. */
    rc = rsql_reu_read(rsql_reu_page_address(
                           g_build_table_page),
                       INDEX_PAGE, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (INDEX_PAGE[0] != 'R' || INDEX_PAGE[1] != 'T' ||
        INDEX_PAGE[2] != 'B' || INDEX_PAGE[3] != 'L' ||
        INDEX_PAGE[4] != RSQL_STORAGE_VERSION ||
        INDEX_PAGE[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(INDEX_PAGE)) return RSQL_ERR_CORRUPT_STORAGE;
    g_rsql_execution.row_width =
        rsql_get_u16(&INDEX_PAGE[RSQL_TABLE_ROW_WIDTH]);
    g_rsql_execution.column_count = INDEX_PAGE[RSQL_TABLE_COLUMN_COUNT];
    g_build_row_page =
        rsql_get_u16(&INDEX_PAGE[RSQL_TABLE_ROW_HEAD]);
    for (index = 0u; index < column_count; ++index) {
        if (columns[index] >= g_rsql_execution.column_count) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        base = (rsql_u16)(RSQL_TABLE_COLUMNS +
            (rsql_u16)columns[index] * RSQL_COLUMN_BYTES);
        memset(&type, 0, sizeof(type));
        type.tag = INDEX_PAGE[base + RSQL_COLUMN_TYPE];
        if (type.tag == RSQL_TYPE_CHAR) {
            type.parameter = rsql_get_u16(&INDEX_PAGE[base + RSQL_COLUMN_WIDTH]);
        }
        widths[index] = type_width(&type);
        offsets[index] = rsql_get_u16(&INDEX_PAGE[base + RSQL_COLUMN_OFFSET]);
        if (widths[index] == 0u) return RSQL_ERR_CORRUPT_STORAGE;
    }
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD], RSQL_PAGE_NONE);
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_TAIL], RSQL_PAGE_NONE);
    memset(&INDEX_DESCRIPTOR[RSQL_INDEX_ENTRY_COUNT], 0, 4u);
    rc = write_descriptor(g_build_descriptor_page);
    if (rc != RSQL_OK) return rc;
    while (g_build_row_page != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(g_build_row_page), INDEX_PAGE,
                           RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) return rc;
        if (INDEX_PAGE[0] != 'R' || INDEX_PAGE[1] != 'R' ||
            INDEX_PAGE[2] != 'O' || INDEX_PAGE[3] != 'W' ||
            INDEX_PAGE[4] != RSQL_STORAGE_VERSION ||
            rsql_get_u16(&INDEX_PAGE[RSQL_ROW_WIDTH]) !=
                g_rsql_execution.row_width) return RSQL_ERR_CORRUPT_STORAGE;
        capacity = INDEX_PAGE[RSQL_ROW_CAPACITY];
        g_build_next_page = rsql_get_u16(&INDEX_PAGE[RSQL_ROW_NEXT]);
        for (slot = 0u; slot < capacity; ++slot) {
            rc = rsql_reu_read(rsql_reu_page_address(g_build_row_page),
                               INDEX_PAGE,
                               RSQL_REU_PAGE_SIZE);
            if (rc != RSQL_OK) return rc;
            if (!(INDEX_PAGE[RSQL_ROW_BITMAP + (slot >> 3u)] &
                  bit_mask(slot))) continue;
            offset = (rsql_u16)(RSQL_ROW_DATA +
                                (rsql_u16)slot * g_rsql_execution.row_width);
            memcpy(g_rsql_execution.row, &INDEX_PAGE[offset],
                   g_rsql_execution.row_width);
            rc = build_key(g_rsql_execution.row, columns, offsets, widths,
                           column_count,
                           g_rsql_cursor.scan_row, key_width);
            if (rc != RSQL_OK) return rc;
            row_id.page = g_build_row_page;
            row_id.slot = slot;
            rc = insert_entry(g_build_descriptor_page,
                              g_rsql_cursor.scan_row, &row_id);
            if (rc != RSQL_OK) return rc;
        }
        g_build_row_page = g_build_next_page;
    }
    return free_leaf_chain(g_build_old_head);
}

rsql_u8 rsql_index_create_phase(void) {
    rsql_u16 first_index;
    rsql_u16 descriptor_page;
    rsql_u16 key_width = 0u;
    rsql_u16 width;
    rsql_u16 duplicate_page;
    rsql_u8 name_length;
    rsql_u8 source;
    rsql_u8 index;
    rsql_u8 rc;
    name_length = (rsql_u8)strlen(g_rsql_statement.index_name);
    if (name_length == 0u || name_length > RSQL_TABLE_NAME_MAX ||
        g_rsql_statement.column_count == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    g_build_table_page = g_rsql_execution.table_page;
    rc = find_index(g_rsql_statement.index_name, &duplicate_page);
    if (rc == RSQL_OK) return RSQL_ERR_ALREADY_EXISTS;
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    for (index = 0u; index < g_rsql_statement.column_count; ++index) {
        source = g_rsql_statement.values[index].integer.bytes[0];
        if (source >= g_rsql_execution.column_count) return RSQL_ERR_NOT_FOUND;
        width = type_width(&g_rsql_execution.columns[source].type);
        if (width == 0u) return RSQL_ERR_UNSUPPORTED_SQL;
        key_width = (rsql_u16)(key_width + width + 1u);
        if (key_width > RSQL_INDEX_KEY_MAX) return RSQL_ERR_SCHEMA_LIMIT;
    }
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    first_index = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_ROOT_FIRST_INDEX]);
    rc = rsql_page_allocate(&descriptor_page);
    if (rc != RSQL_OK) return rc;
    memset(INDEX_DESCRIPTOR, 0, RSQL_REU_PAGE_SIZE);
    INDEX_DESCRIPTOR[0] = 'R'; INDEX_DESCRIPTOR[1] = 'I';
    INDEX_DESCRIPTOR[2] = 'D'; INDEX_DESCRIPTOR[3] = 'X';
    INDEX_DESCRIPTOR[4] = RSQL_STORAGE_VERSION;
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_NEXT], first_index);
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_TABLE],
                 g_build_table_page);
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD], RSQL_PAGE_NONE);
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_TAIL], RSQL_PAGE_NONE);
    INDEX_DESCRIPTOR[RSQL_INDEX_KEY_WIDTH] = (rsql_u8)key_width;
    INDEX_DESCRIPTOR[RSQL_INDEX_COLUMN_COUNT] =
        g_rsql_statement.column_count;
    INDEX_DESCRIPTOR[RSQL_INDEX_NAME_LENGTH] = name_length;
    memcpy(&INDEX_DESCRIPTOR[RSQL_INDEX_NAME], g_rsql_statement.index_name,
           name_length);
    for (index = 0u; index < g_rsql_statement.column_count; ++index) {
        INDEX_DESCRIPTOR[RSQL_INDEX_COLUMNS + index] =
            g_rsql_statement.values[index].integer.bytes[0];
    }
    rc = write_descriptor(descriptor_page);
    if (rc != RSQL_OK) return rc;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&INDEX_DESCRIPTOR[RSQL_ROOT_FIRST_INDEX], descriptor_page);
    INDEX_DESCRIPTOR[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(INDEX_DESCRIPTOR);
    rc = rsql_reu_write(
        rsql_reu_page_address(rsql_page_catalog_root()), INDEX_DESCRIPTOR,
        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return build_index(descriptor_page);
}

rsql_u8 __fastcall__ rsql_index_rebuild_table(rsql_u16 table_page) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u8 rc = read_root();
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_ROOT_FIRST_INDEX]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_descriptor(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_NEXT]);
        if (!(INDEX_DESCRIPTOR[RSQL_INDEX_FLAGS] &
                RSQL_INDEX_FLAG_DROPPING) &&
            rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_TABLE]) == table_page) {
            rc = build_index(page);
            if (rc != RSQL_OK) return rc;
        }
        page = next;
    }
    return RSQL_OK;
}

rsql_u8 rsql_index_scan_open(void) {
    rsql_u16 page;
    rsql_u8 rc;
    if (!g_rsql_cursor.using_index) return RSQL_OK;
    rc = find_index(g_rsql_statement.index_name, &page);
    if (rc != RSQL_OK) return rc;
    if (rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_TABLE]) !=
        g_rsql_cursor.table_page) return RSQL_ERR_TYPE_MISMATCH;
    g_rsql_cursor.index_page = page;
    g_rsql_cursor.index_leaf_head =
        rsql_get_u16(&INDEX_DESCRIPTOR[RSQL_INDEX_LEAF_HEAD]);
    g_rsql_cursor.index_leaf_page = g_rsql_cursor.index_leaf_head;
    g_rsql_cursor.index_leaf_slot = 0u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_index_scan_next(RsqlRowId* row_id_out) {
    rsql_u16 base;
    rsql_u16 next;
    rsql_u8 key_width;
    rsql_u8 count;
    rsql_u8 rc;
    if (!row_id_out || !g_rsql_cursor.using_index) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    while (g_rsql_cursor.index_leaf_page != RSQL_PAGE_NONE) {
        rc = read_leaf(g_rsql_cursor.index_leaf_page);
        if (rc != RSQL_OK) return rc;
        count = INDEX_PAGE[RSQL_INDEX_LEAF_COUNT];
        key_width = INDEX_PAGE[RSQL_INDEX_LEAF_KEY_WIDTH];
        if (g_rsql_cursor.index_leaf_slot < count) {
            base = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                (rsql_u16)g_rsql_cursor.index_leaf_slot *
                (rsql_u16)(key_width + 3u));
            row_id_out->page = rsql_get_u16(&INDEX_PAGE[base + key_width]);
            row_id_out->slot = INDEX_PAGE[base + key_width + 2u];
            ++g_rsql_cursor.index_leaf_slot;
            return RSQL_OK;
        }
        next = rsql_get_u16(&INDEX_PAGE[RSQL_INDEX_LEAF_NEXT]);
        g_rsql_cursor.index_leaf_page = next;
        g_rsql_cursor.index_leaf_slot = 0u;
    }
    return RSQL_ERR_NOT_FOUND;
}

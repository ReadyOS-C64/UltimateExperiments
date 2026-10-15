#include <string.h>

#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define g_catalog_page g_rsql_meta_page1

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ((rsql_u8)'a' - (rsql_u8)'A'));
    }
    return value;
}

static rsql_u8 bounded_length(const char* text, rsql_u8 maximum,
                              rsql_u8* length_out) {
    rsql_u8 length = 0u;
    if (!text || !length_out) return RSQL_ERR_INVALID_ARGUMENT;
    while (text[length] != 0) {
        if (length == maximum) return RSQL_ERR_SCHEMA_LIMIT;
        ++length;
    }
    if (length == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    *length_out = length;
    return RSQL_OK;
}

static rsql_u8 name_equal(const char* wanted, const rsql_u8* stored,
                          rsql_u8 stored_length) {
    rsql_u8 i;
    if (!wanted) return 0u;
    for (i = 0u; i < stored_length; ++i) {
        if (wanted[i] == 0 || folded((rsql_u8)wanted[i]) != folded(stored[i])) {
            return 0u;
        }
    }
    return wanted[stored_length] == 0;
}

static rsql_u8 page_magic(const rsql_u8* page, char a, char b, char c, char d) {
    return page[0] == (rsql_u8)a && page[1] == (rsql_u8)b &&
           page[2] == (rsql_u8)c && page[3] == (rsql_u8)d &&
           page[4] == RSQL_STORAGE_VERSION &&
           page[RSQL_PAGE_CHECKSUM_OFFSET] == rsql_page_checksum(page);
}

static void set_magic(rsql_u8* page, char a, char b, char c, char d) {
    page[0] = (rsql_u8)a;
    page[1] = (rsql_u8)b;
    page[2] = (rsql_u8)c;
    page[3] = (rsql_u8)d;
    page[4] = RSQL_STORAGE_VERSION;
}

static rsql_u8 read_root(void) {
    rsql_u16 root = rsql_page_catalog_root();
    rsql_u8 rc;
    if (root == RSQL_PAGE_NONE) return RSQL_ERR_CORRUPT_STORAGE;
    rc = rsql_reu_read(rsql_reu_page_address(root), g_catalog_page,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return page_magic(g_catalog_page, 'R', 'C', 'A', 'T')
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 read_table_page(rsql_u16 page) {
    rsql_u8 rc;
    if (page == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
    rc = rsql_reu_read(rsql_reu_page_address(page), g_catalog_page,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return page_magic(g_catalog_page, 'R', 'T', 'B', 'L')
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

rsql_u8 rsql_catalog_format(void) {
    rsql_u16 page;
    rsql_u8 rc;
    if (rsql_page_catalog_root() != RSQL_PAGE_NONE) {
        return RSQL_ERR_ALREADY_EXISTS;
    }
    rc = rsql_page_allocate(&page);
    if (rc != RSQL_OK) return rc;
    memset(g_catalog_page, 0, sizeof(g_catalog_page));
    set_magic(g_catalog_page, 'R', 'C', 'A', 'T');
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_TABLE], RSQL_PAGE_NONE);
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_BLOB_DIRECTORY], RSQL_PAGE_NONE);
    rsql_put_u32(&g_catalog_page[RSQL_ROOT_NEXT_BLOB_HANDLE], 1ul);
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_ENUM], RSQL_PAGE_NONE);
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_NEXT_ENUM_ID], 1u);
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_INDEX], RSQL_PAGE_NONE);
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    rc = rsql_reu_write(rsql_reu_page_address(page), g_catalog_page,
                        sizeof(g_catalog_page));
    if (rc == RSQL_OK) rc = rsql_page_set_catalog_root(page);
    if (rc != RSQL_OK) rsql_page_free(page);
    return rc;
}

rsql_u8 rsql_catalog_open(void) {
    return read_root();
}

rsql_u8 rsql_catalog_blob_directory(rsql_u16* page_out) {
    rsql_u8 rc;
    if (!page_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    *page_out = rsql_get_u16(&g_catalog_page[RSQL_ROOT_FIRST_BLOB_DIRECTORY]);
    return RSQL_OK;
}

rsql_u8 rsql_catalog_set_blob_directory(rsql_u16 page) {
    rsql_u8 rc;
    if (page == RSQL_PAGE_NONE) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_BLOB_DIRECTORY], page);
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    return rsql_reu_write(rsql_reu_page_address(rsql_page_catalog_root()),
                          g_catalog_page, sizeof(g_catalog_page));
}

rsql_u8 rsql_catalog_reserve_blob_handle(unsigned long* handle_out) {
    unsigned long handle;
    rsql_u8 rc;
    if (!handle_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    handle = rsql_get_u32(&g_catalog_page[RSQL_ROOT_NEXT_BLOB_HANDLE]);
    if (handle == 0ul || handle == 0xFFFFFFFFul) return RSQL_ERR_SCHEMA_LIMIT;
    rsql_put_u32(&g_catalog_page[RSQL_ROOT_NEXT_BLOB_HANDLE], handle + 1ul);
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    rc = rsql_reu_write(rsql_reu_page_address(rsql_page_catalog_root()),
                        g_catalog_page, sizeof(g_catalog_page));
    if (rc == RSQL_OK) *handle_out = handle;
    return rc;
}

rsql_u8 rsql_catalog_enum_state(rsql_u16* first_page_out,
                                rsql_u16* next_id_out) {
    rsql_u8 rc;
    if (!first_page_out || !next_id_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    *first_page_out = rsql_get_u16(&g_catalog_page[RSQL_ROOT_FIRST_ENUM]);
    *next_id_out = rsql_get_u16(&g_catalog_page[RSQL_ROOT_NEXT_ENUM_ID]);
    return RSQL_OK;
}

rsql_u8 rsql_catalog_link_enum(rsql_u16 enum_page, rsql_u16 next_id) {
    rsql_u8 rc;
    if (enum_page == RSQL_PAGE_NONE || next_id == 0u) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_ENUM], enum_page);
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_NEXT_ENUM_ID], next_id);
    ++g_catalog_page[7u];
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    return rsql_reu_write(rsql_reu_page_address(rsql_page_catalog_root()),
                          g_catalog_page, sizeof(g_catalog_page));
}

rsql_u8 rsql_table_info(rsql_u16 table_page, RsqlTableInfo* info_out) {
    rsql_u8 rc;
    rsql_u8 length;
    if (!info_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_table_page(table_page);
    if (rc != RSQL_OK) return rc;
    length = g_catalog_page[RSQL_TABLE_NAME_LENGTH];
    if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
    info_out->table_page = table_page;
    info_out->row_width = rsql_get_u16(&g_catalog_page[RSQL_TABLE_ROW_WIDTH]);
    info_out->column_count = g_catalog_page[RSQL_TABLE_COLUMN_COUNT];
    info_out->name_length = length;
    memcpy(info_out->name, &g_catalog_page[RSQL_TABLE_NAME], length);
    info_out->name[length] = 0;
    return RSQL_OK;
}

rsql_u8 rsql_table_find(const char* name, RsqlTableInfo* info_out) {
    rsql_u16 page;
    rsql_u8 rc;
    if (!name || !info_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_root();
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_catalog_page[RSQL_ROOT_FIRST_TABLE]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_table_page(page);
        if (rc != RSQL_OK) return rc;
        if (!(g_catalog_page[RSQL_TABLE_FLAGS] &
              (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING)) &&
            name_equal(name, &g_catalog_page[RSQL_TABLE_NAME],
                       g_catalog_page[RSQL_TABLE_NAME_LENGTH])) {
            return rsql_table_info(page, info_out);
        }
        page = rsql_get_u16(&g_catalog_page[RSQL_TABLE_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_column_info(rsql_u16 table_page, rsql_u8 column,
                         RsqlColumnInfo* info_out) {
    rsql_u16 base;
    rsql_u8 length;
    rsql_u8 rc;
    if (!info_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = read_table_page(table_page);
    if (rc != RSQL_OK) return rc;
    if (column >= g_catalog_page[RSQL_TABLE_COLUMN_COUNT]) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    base = (rsql_u16)(RSQL_TABLE_COLUMNS +
                      (rsql_u16)column * RSQL_COLUMN_BYTES);
    info_out->type.tag = g_catalog_page[base + RSQL_COLUMN_TYPE];
    info_out->type.flags = g_catalog_page[base + RSQL_COLUMN_FLAGS];
    info_out->type.parameter = info_out->type.tag == RSQL_TYPE_CHAR
        ? rsql_get_u16(&g_catalog_page[base + RSQL_COLUMN_WIDTH]) : 0u;
    info_out->type.auxiliary = rsql_get_u16(
        &g_catalog_page[base + RSQL_COLUMN_AUXILIARY]);
    info_out->offset = rsql_get_u16(&g_catalog_page[base + RSQL_COLUMN_OFFSET]);
    length = g_catalog_page[base + RSQL_COLUMN_NAME_LENGTH];
    if (length > RSQL_COLUMN_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
    info_out->name_length = length;
    memcpy(info_out->name, &g_catalog_page[base + RSQL_COLUMN_NAME], length);
    info_out->name[length] = 0;
    return RSQL_OK;
}

rsql_u8 rsql_table_create(RsqlCreateTableRequest* request) {
    RsqlTableInfo existing;
    rsql_u16 first_table;
    rsql_u16 table_page;
    rsql_u16 row_width;
    rsql_u16 column_width;
    rsql_u16 base;
    rsql_u8 table_name_length;
    rsql_u8 column_name_length;
    rsql_u8 column;
    rsql_u8 rc;

    if (!request || !request->name || !request->columns ||
        request->column_count == 0u ||
        request->column_count > RSQL_TABLE_COLUMNS_MAX) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = bounded_length(request->name, RSQL_TABLE_NAME_MAX, &table_name_length);
    if (rc != RSQL_OK) return rc;
    rc = rsql_table_find(request->name, &existing);
    if (rc == RSQL_OK) return RSQL_ERR_ALREADY_EXISTS;
    if (rc != RSQL_ERR_NOT_FOUND) return rc;

    row_width = (rsql_u16)((request->column_count + 7u) >> 3u);
    for (column = 0u; column < request->column_count; ++column) {
        rc = bounded_length(request->columns[column].name,
                            RSQL_COLUMN_NAME_MAX, &column_name_length);
        if (rc != RSQL_OK) return rc;
        rc = rsql_type_width(&request->columns[column].type, &column_width);
        if (rc != RSQL_OK) return rc;
        row_width = (rsql_u16)(row_width + column_width);
        if (row_width > (RSQL_REU_PAGE_SIZE - RSQL_ROW_DATA)) {
            return RSQL_ERR_ROW_TOO_WIDE;
        }
    }

    rc = read_root();
    if (rc != RSQL_OK) return rc;
    first_table = rsql_get_u16(&g_catalog_page[RSQL_ROOT_FIRST_TABLE]);
    rc = rsql_page_allocate(&table_page);
    if (rc != RSQL_OK) return rc;

    memset(g_catalog_page, 0, sizeof(g_catalog_page));
    set_magic(g_catalog_page, 'R', 'T', 'B', 'L');
    rsql_put_u16(&g_catalog_page[RSQL_TABLE_NEXT], first_table);
    rsql_put_u16(&g_catalog_page[RSQL_TABLE_ROW_HEAD], RSQL_PAGE_NONE);
    rsql_put_u16(&g_catalog_page[RSQL_TABLE_ROW_TAIL], RSQL_PAGE_NONE);
    rsql_put_u16(&g_catalog_page[RSQL_TABLE_ROW_WIDTH], row_width);
    g_catalog_page[RSQL_TABLE_FLAGS] = request->flags;
    g_catalog_page[RSQL_TABLE_COLUMN_COUNT] = request->column_count;
    g_catalog_page[RSQL_TABLE_NAME_LENGTH] = table_name_length;
    memcpy(&g_catalog_page[RSQL_TABLE_NAME], request->name, table_name_length);

    row_width = (rsql_u16)((request->column_count + 7u) >> 3u);
    for (column = 0u; column < request->column_count; ++column) {
        const RsqlColumnDefinition* definition = &request->columns[column];
        bounded_length(definition->name, RSQL_COLUMN_NAME_MAX,
                       &column_name_length);
        rsql_type_width(&definition->type, &column_width);
        base = (rsql_u16)(RSQL_TABLE_COLUMNS +
                          (rsql_u16)column * RSQL_COLUMN_BYTES);
        g_catalog_page[base + RSQL_COLUMN_TYPE] = definition->type.tag;
        g_catalog_page[base + RSQL_COLUMN_FLAGS] = definition->type.flags;
        rsql_put_u16(&g_catalog_page[base + RSQL_COLUMN_WIDTH], column_width);
        rsql_put_u16(&g_catalog_page[base + RSQL_COLUMN_OFFSET], row_width);
        rsql_put_u16(&g_catalog_page[base + RSQL_COLUMN_AUXILIARY],
                     definition->type.auxiliary);
        g_catalog_page[base + RSQL_COLUMN_NAME_LENGTH] = column_name_length;
        memcpy(&g_catalog_page[base + RSQL_COLUMN_NAME], definition->name,
               column_name_length);
        row_width = (rsql_u16)(row_width + column_width);
    }
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    rc = rsql_reu_write(rsql_reu_page_address(table_page), g_catalog_page,
                        sizeof(g_catalog_page));
    if (rc != RSQL_OK) {
        rsql_page_free(table_page);
        return rc;
    }

    rc = read_root();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&g_catalog_page[RSQL_ROOT_FIRST_TABLE], table_page);
    ++g_catalog_page[RSQL_ROOT_TABLE_COUNT];
    g_catalog_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_catalog_page);
    rc = rsql_reu_write(rsql_reu_page_address(rsql_page_catalog_root()),
                        g_catalog_page, sizeof(g_catalog_page));
    if (rc == RSQL_OK) request->table_page = table_page;
    return rc;
}

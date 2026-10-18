#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_journal.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_row.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_RC (*(volatile unsigned char*)0xCFF4)
#define TEST_ACTUAL (*(volatile unsigned char*)0xCFF5)
#define TEST_EXPECTED (*(volatile unsigned char*)0xCFF6)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_CREATE_SOURCE[] =
    "CREATE TABLE VSRC(BODY TEXT NULL,RAW BLOB)";
static const char SQL_CREATE_RESULT[] =
    "CREATE TEMP TABLE VCOPY AS "
    "SELECT BODY,RAW,SUBSTR(BODY,240,17),BODY||'END' FROM VSRC";
static const char SQL_SELECT_RESULT[] = "SELECT*FROM VCOPY";
static const char SQL_CREATE_ROLL_SOURCE[] =
    "CREATE TABLE RSRC(ID I16,BODY TEXT)";
static const char SQL_INSERT_ROLL1[] =
    "INSERT INTO RSRC VALUES(1,'A')";
static const char SQL_INSERT_ROLL2[] =
    "INSERT INTO RSRC VALUES(2,'B')";
static const char SQL_CREATE_ROLL[] =
    "CREATE TABLE RFAIL AS SELECT ID,BODY,BODY||'!' FROM RSRC";
static const char SQL_COUNT_ROLL_SOURCE[] = "SELECT COUNT(*) FROM RSRC";
static const char SQL_CREATE_BIG_TEMP[] =
    "CREATE TABLE BIGTEMP(ID I16,BODY TEXT)";
static const char SQL_CREATE_BIG_INDEX[] =
    "CREATE INDEX BIGIDX ON BIGTEMP (ID)";
static const char SQL_MATCH_BIG[] =
    "UPDATE BIGTEMP SET ID=7 WHERE BODY LIKE'%'";
static const char SQL_CREATE_BIG_COPY[] =
    "CREATE TABLE BIGCOPY AS SELECT BODY FROM BIGTEMP";
static const char SQL_DROP_BIG_TEMP[] = "DROP TABLE BIGTEMP";
static const char SQL_DROP_BIG_COPY[] = "DROP TABLE BIGCOPY";
static const char SQL_CREATE_WIDE[] =
    "CREATE TABLE WIDE(BODY CHAR(119))";
static const char SQL_CREATE_WIDE_COPY[] =
    "CREATE TABLE WIDECOPY AS SELECT BODY FROM WIDE";
static const char SQL_COUNT_WIDE_COPY[] =
    "SELECT COUNT(*)FROM WIDECOPY";
static const char SQL_DROP_WIDE[] = "DROP TABLE WIDE";
static const char SQL_DROP_WIDE_COPY[] = "DROP TABLE WIDECOPY";
static const char SQL_DROP_INCOMPLETE[] = "DROP TABLE";
static const char SQL_CREATE_STALE[] =
    "CREATE TABLE STALE(ID I16,BODY TEXT)";
static const char SQL_INSERT_STALE[] =
    "INSERT INTO STALE VALUES(1,'S')";
static const char SQL_CREATE_TEMP_ROLL[] =
    "CREATE TEMP TABLE TROLL(ID I16)";
static const char SQL_DROP_TEMP_ROLL[] = "DROP TABLE TROLL";

#define BIG_BLOB_LENGTH 4096u
#define BIG_BLOB_PAGES 17u
#define BIG_COPY_PAGES 18u
#define WIDE_ROWS 34u
#define WIDE_PAGES 17u

static unsigned int g_blob_pages[BIG_BLOB_PAGES];
static unsigned int g_copy_pages[BIG_COPY_PAGES];

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static void stage_fail(unsigned char stage, unsigned char rc,
                       unsigned char actual, unsigned char expected) {
    TEST_STAGE = stage;
    TEST_RC = rc;
    TEST_ACTUAL = actual;
    TEST_EXPECTED = expected;
    fail(rc ? rc : stage);
}

static void exec_affected(const char* sql, unsigned char affected,
                          unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK || request.output.affected_rows.bytes[0] != affected) {
        stage_fail(stage, rc, request.output.affected_rows.bytes[0], affected);
    }
}

static void exec_expected(const char* sql, unsigned char expected,
                          unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != expected) stage_fail(stage, rc, rc, expected);
}

static void expect_count(const char* sql, unsigned char expected,
                         unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    RsqlQueryCloseRequest close;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    column.cursor = open.cursor;
    column.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || !next.has_row || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_I64 ||
        column.value.bytes[0] != expected) {
        stage_fail(stage, rc, column.value.bytes[0], expected);
    }
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) stage_fail(stage, rc, 0u, 0u);
}

static unsigned int first_free_page(void) {
    unsigned long page;
    unsigned char allocated;
    unsigned char rc;
    for (page = rsql_page_first_usable(); page < rsql_page_limit(); ++page) {
        rc = rsql_page_is_allocated((unsigned int)page, &allocated);
        if (rc != RSQL_OK) stage_fail(0x40u, rc, 0u, 0u);
        if (!allocated) return (unsigned int)page;
    }
    return RSQL_PAGE_NONE;
}

static void expect_named_table_missing(const char* name, unsigned char stage) {
    RsqlTableInfo table;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(name, &table);
    if (rc != RSQL_ERR_NOT_FOUND) {
        stage_fail(stage, rc, rc, RSQL_ERR_NOT_FOUND);
    }
}

static void expect_table_missing(unsigned char stage) {
    expect_named_table_missing("RFAIL", stage);
}

static void expect_page_free(unsigned int page, unsigned char stage) {
    unsigned char allocated = 1u;
    unsigned char rc = rsql_page_is_allocated(page, &allocated);
    if (rc != RSQL_OK || allocated) stage_fail(stage, rc, allocated, 0u);
}

static void expect_page_used(unsigned int page, unsigned char stage) {
    unsigned char allocated = 0u;
    unsigned char rc = rsql_page_is_allocated(page, &allocated);
    if (rc != RSQL_OK || !allocated) stage_fail(stage, rc, allocated, 1u);
}

static void capture_owned_index(unsigned int table_page,
                                unsigned int* descriptor_out,
                                unsigned int* leaf_out) {
    unsigned int descriptor;
    unsigned char rc = rsql_reu_read(
        rsql_reu_page_address(rsql_page_catalog_root()), g_rsql_meta_page0,
        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) stage_fail(0x72u, rc, 0u, 0u);
    descriptor = rsql_get_u16(&g_rsql_meta_page0[RSQL_ROOT_FIRST_INDEX]);
    while (descriptor != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(descriptor),
                           g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) stage_fail(0x73u, rc, 0u, 0u);
        if (rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_TABLE]) == table_page) {
            *descriptor_out = descriptor;
            *leaf_out = rsql_get_u16(
                &g_rsql_meta_page0[RSQL_INDEX_LEAF_HEAD]);
            return;
        }
        descriptor = rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_NEXT]);
    }
    stage_fail(0x74u, RSQL_ERR_NOT_FOUND, 0u, 0u);
}

static void create_big_temp(RsqlBlobHandle* handle,
                            unsigned int* table_page_out,
                            unsigned int* row_page_out,
                            unsigned int* index_page_out,
                            unsigned int* index_leaf_out,
                            unsigned int* blob_pages) {
    RsqlBlobInfo info;
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char row[7];
    unsigned int page;
    unsigned char index;
    unsigned char rc;
    exec_affected(SQL_CREATE_BIG_TEMP, 0u, 0x70u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) {
        rc = rsql_blob_create(RSQL_BLOB_KIND_TEXT, 0, BIG_BLOB_LENGTH, handle);
    }
    if (rc == RSQL_OK) rc = rsql_blob_info(handle, &info);
    if (rc == RSQL_OK) rc = rsql_table_find("BIGTEMP", &table);
    memset(row, 0, sizeof(row));
    row[1] = 7u;
    memcpy(&row[3], handle->bytes, 4u);
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) {
        rc = rsql_row_insert(table.table_page, row, sizeof(row), &row_id);
    }
    if (rc != RSQL_OK) stage_fail(0x71u, rc, 0u, 0u);
    *table_page_out = table.table_page;
    *row_page_out = row_id.page;
    page = info.first_page;
    for (index = 0u; index < BIG_BLOB_PAGES; ++index) {
        if (page == RSQL_PAGE_NONE) stage_fail(0x75u, 0u, index,
                                               BIG_BLOB_PAGES);
        blob_pages[index] = page;
        rc = rsql_reu_read(rsql_reu_page_address(page), g_rsql_meta_page0,
                           RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) stage_fail(0x76u, rc, index, 0u);
        page = rsql_get_u16(&g_rsql_meta_page0[6u]);
    }
    if (page != RSQL_PAGE_NONE) stage_fail(0x77u, 0u, 1u, 0u);
    exec_affected(SQL_MATCH_BIG, 1u, 0x77u);
    exec_affected(SQL_CREATE_BIG_INDEX, 0u, 0x78u);
    capture_owned_index(table.table_page, index_page_out, index_leaf_out);
    if (*index_leaf_out == RSQL_PAGE_NONE) stage_fail(0x79u, 0u, 0u, 1u);
}

static void capture_big_copy(RsqlBlobHandle* handle,
                             unsigned int* table_page_out,
                             unsigned int* row_page_out,
                             unsigned int* pages) {
    RsqlBlobInfo info;
    RsqlColumnInfo column;
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char row[5];
    unsigned int page;
    unsigned char index;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("BIGCOPY", &table);
    if (rc == RSQL_OK) rc = rsql_column_info(table.table_page, 0u, &column);
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_row_first(table.table_page, &row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
    }
    if (rc == RSQL_OK) memcpy(handle->bytes, &row[column.offset], 4u);
    if (rc == RSQL_OK) rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_info(handle, &info);
    if (rc != RSQL_OK || info.length != BIG_BLOB_LENGTH) {
        stage_fail(0xA0u, rc, (unsigned char)info.length, 0u);
    }
    *table_page_out = table.table_page;
    *row_page_out = row_id.page;
    page = info.first_page;
    for (index = 0u; index < BIG_COPY_PAGES; ++index) {
        if (page == RSQL_PAGE_NONE) stage_fail(0xA1u, 0u, index,
                                               BIG_COPY_PAGES);
        pages[index] = page;
        rc = rsql_reu_read(rsql_reu_page_address(page), g_rsql_meta_page0,
                           RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) stage_fail(0xA2u, rc, index, 0u);
        page = rsql_get_u16(&g_rsql_meta_page0[6u]);
    }
    if (page != RSQL_PAGE_NONE) stage_fail(0xA3u, 0u, 1u, 0u);
}

static void create_wide_rows(void) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char index;
    unsigned char rc;
    exec_affected(SQL_CREATE_WIDE, 0u, 0xC0u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("WIDE", &table);
    memset(g_rsql_meta_page0, 'W', 120u);
    g_rsql_meta_page0[0] = 0u;
    for (index = 0u; rc == RSQL_OK && index < WIDE_ROWS; ++index) {
        g_rsql_meta_page0[1] = (unsigned char)('A' + index % 26u);
        rc = rsql_journal_begin();
        if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
        if (rc == RSQL_OK) {
            rc = rsql_row_insert(table.table_page, g_rsql_meta_page0, 120u,
                                 &row_id);
        }
        rc = rsql_finish_mutation(rc);
    }
    if (rc != RSQL_OK) stage_fail(0xC1u, rc, index, WIDE_ROWS);
}

static void capture_row_pages(const char* name, unsigned int* table_out,
                              unsigned int* pages, unsigned char expected,
                              unsigned char stage) {
    RsqlTableInfo table;
    unsigned int page;
    unsigned char count = 0u;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(name, &table);
    if (rc == RSQL_OK) {
        rc = rsql_reu_read(rsql_reu_page_address(table.table_page),
                           g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    }
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (rc == RSQL_OK && page != RSQL_PAGE_NONE && count < expected) {
        pages[count++] = page;
        rc = rsql_reu_read(rsql_reu_page_address(page), g_rsql_meta_page0,
                           RSQL_REU_PAGE_SIZE);
        page = rsql_get_u16(&g_rsql_meta_page0[RSQL_ROW_NEXT]);
    }
    if (rc != RSQL_OK || count != expected || page != RSQL_PAGE_NONE) {
        stage_fail(stage, rc, count, expected);
    }
    *table_out = table.table_page;
}

static void mark_stale_building(unsigned int table_page) {
    unsigned char rc = rsql_reu_read(rsql_reu_page_address(table_page),
                                      g_rsql_meta_page0,
                                      RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) stage_fail(0x8Au, rc, 0u, 0u);
    g_rsql_meta_page0[RSQL_TABLE_FLAGS] |= RSQL_TABLE_FLAG_BUILDING;
    g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(g_rsql_meta_page0);
    rc = rsql_reu_write(rsql_reu_page_address(table_page),
                        g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) stage_fail(0x8Bu, rc, 0u, 0u);
}

static unsigned char text_byte(unsigned int offset) {
    return (unsigned char)('A' + (offset % 26u));
}

static unsigned char raw_byte(unsigned int offset) {
    return (unsigned char)(((offset * 7u) ^ 0xA6u) & 0xFFu);
}

static void fill_source(unsigned char raw, unsigned int length) {
    unsigned int index;
    for (index = 0u; index < length; ++index) {
        g_rsql_meta_page0[index] = raw ? raw_byte(index) : text_byte(index);
    }
}

static void create_source_rows(RsqlBlobHandle* source) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char row[9];
    unsigned char rc;
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) {
        fill_source(0u, 256u);
        rc = rsql_blob_create(RSQL_BLOB_KIND_TEXT, g_rsql_meta_page0, 256u,
                              &source[0]);
    }
    if (rc == RSQL_OK) {
        fill_source(1u, 250u);
        rc = rsql_blob_create(RSQL_BLOB_KIND_BINARY, g_rsql_meta_page0, 250u,
                              &source[1]);
    }
    if (rc == RSQL_OK) {
        rc = rsql_blob_create(RSQL_BLOB_KIND_BINARY, "", 0u, &source[2]);
    }
    if (rc == RSQL_OK) rc = rsql_table_find("VSRC", &table);
    memset(row, 0, sizeof(row));
    memcpy(&row[1], source[0].bytes, 4u);
    memcpy(&row[5], source[1].bytes, 4u);
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) {
        rc = rsql_row_insert(table.table_page, row, sizeof(row), &row_id);
    }
    memset(row, 0, sizeof(row));
    row[0] = 1u;
    memcpy(&row[5], source[2].bytes, 4u);
    if (rc == RSQL_OK) {
        rc = rsql_row_insert(table.table_page, row, sizeof(row), &row_id);
    }
    if (rc != RSQL_OK) stage_fail(0x12u, rc, 0u, 0u);
}

static void capture_result_handles(RsqlBlobHandle* handles) {
    RsqlTableInfo table;
    RsqlColumnInfo column;
    RsqlRowId row_id;
    unsigned int offsets[4];
    unsigned char row[17];
    unsigned char index;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("VCOPY", &table);
    for (index = 0u; rc == RSQL_OK && index < 4u; ++index) {
        rc = rsql_column_info(table.table_page, index, &column);
        offsets[index] = column.offset;
    }
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_row_first(table.table_page, &row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
    }
    for (index = 0u; rc == RSQL_OK && index < 4u; ++index) {
        memcpy(handles[index].bytes, &row[offsets[index]], 4u);
    }
    if (rc == RSQL_OK) rc = rsql_row_next(table.table_page, &row_id, &row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
    }
    if (rc == RSQL_OK && row[0] != 0x0Du) {
        stage_fail(0x16u, 0u, row[0], 0x0Du);
    }
    if (rc == RSQL_OK) {
        memcpy(handles[5].bytes, &row[offsets[1]], 4u);
    }
    if (rc != RSQL_OK) stage_fail(0x15u, rc, 0u, 0u);
}

static void expect_handle_info(const RsqlBlobHandle* handle,
                               unsigned char kind, unsigned int length,
                               unsigned char stage) {
    RsqlBlobInfo info;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_info(handle, &info);
    if (rc != RSQL_OK || info.kind != kind || info.length != length) {
        stage_fail(stage, rc, info.kind, kind);
    }
}

static void expect_pattern(const RsqlBlobHandle* handle, unsigned char raw,
                           unsigned int start, unsigned int length,
                           unsigned char suffix, unsigned char stage) {
    unsigned char bytes[32];
    unsigned int offset = 0u;
    unsigned int index;
    unsigned int take;
    unsigned int read;
    unsigned char expected;
    unsigned char rc;
    while (offset < length) {
        take = (unsigned int)(length - offset);
        if (take > sizeof(bytes)) take = sizeof(bytes);
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) {
            rc = rsql_blob_read(handle, offset, bytes, take, &read);
        }
        if (rc != RSQL_OK || read != take) {
            stage_fail(stage, rc, (unsigned char)read, (unsigned char)take);
        }
        for (index = 0u; index < take; ++index) {
            if (start + offset + index < 256u) {
                expected = raw ? raw_byte(start + offset + index)
                               : text_byte(start + offset + index);
            } else {
                expected = ((const unsigned char*)"END")[
                    start + offset + index - 256u];
            }
            if (bytes[index] != expected) {
                stage_fail(stage, 0u, bytes[index], expected);
            }
        }
        offset = (unsigned int)(offset + take);
    }
    (void)suffix;
}

static void verify_query_result(void) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    unsigned char index;
    unsigned char rc;
    open.sql = SQL_SELECT_RESULT;
    open.sql_length = strlen(SQL_SELECT_RESULT);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) stage_fail(0x24u, rc, 0u, 1u);
    column.cursor = open.cursor;
    for (index = 0u; index < 4u; ++index) {
        column.column = index;
        rc = rsql_cursor_column(&column);
        if (rc != RSQL_OK || column.value.is_null) {
            stage_fail((unsigned char)(0x25u + index), rc,
                       column.value.is_null, 0u);
        }
    }
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) stage_fail(0x29u, rc, 0u, 1u);
    for (index = 0u; index < 4u; ++index) {
        column.column = index;
        rc = rsql_cursor_column(&column);
        if (rc != RSQL_OK || column.value.is_null != (index == 1u ? 0u : 1u) ||
            (index == 1u && column.value.length != 0u)) {
            stage_fail((unsigned char)(0x2Au + index), rc,
                       column.value.is_null, index == 1u ? 0u : 1u);
        }
    }
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) stage_fail(0x2Eu, rc, next.has_row, 0u);
    {
        RsqlQueryCloseRequest close;
        close.cursor = open.cursor;
        rc = rsql_query_close(&close);
    }
    if (rc != RSQL_OK) stage_fail(0x2Fu, rc, 0u, 0u);
}

int main(void) {
    RsqlInitRequest init;
    RsqlBlobHandle source[3];
    RsqlBlobHandle result[8];
    unsigned int reclaimed;
    unsigned int expected_free;
    unsigned int build_free;
    unsigned int big_table;
    unsigned int big_row;
    unsigned int big_index;
    unsigned int big_leaf;
    unsigned int big_copy_table;
    unsigned int big_copy_row;
    unsigned int wide_table;
    unsigned int wide_copy_table;
    unsigned int stale_table;
    unsigned int stale_row;
    unsigned int temp_roll_table;
    RsqlBlobHandle big_handle;
    RsqlBlobHandle big_copy_handle;
    RsqlTableInfo lifecycle_table;
    RsqlRowId lifecycle_row;
    unsigned char fail_index;
    unsigned char index;
    unsigned char rc;
    BORDER_COLOR = 0u;
    memset(&init, 0, sizeof(init));
    memset(result, 0, sizeof(result));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) stage_fail(0x10u, rc, 0u, 0u);
    if (rsql_reu_size_kib() != (unsigned int)(512u << REU_SIZE_SELECTOR)) {
        stage_fail(0x11u, 0u, (unsigned char)rsql_reu_size_kib(),
                   (unsigned char)(512u << REU_SIZE_SELECTOR));
    }
    exec_affected(SQL_CREATE_SOURCE, 0u, 0x12u);
    create_source_rows(source);
    exec_affected(SQL_CREATE_RESULT, 2u, 0x13u);
    capture_result_handles(result);
    if (memcmp(source[0].bytes, result[0].bytes, 4u) == 0 ||
        memcmp(source[1].bytes, result[1].bytes, 4u) == 0 ||
        memcmp(source[2].bytes, result[5].bytes, 4u) == 0) {
        stage_fail(0x17u, 0u, 1u, 0u);
    }
    expect_handle_info(&result[0], RSQL_BLOB_KIND_TEXT, 256u, 0x18u);
    expect_handle_info(&result[1], RSQL_BLOB_KIND_BINARY, 250u, 0x19u);
    expect_handle_info(&result[2], RSQL_BLOB_KIND_TEXT, 17u, 0x1Au);
    expect_handle_info(&result[3], RSQL_BLOB_KIND_TEXT, 259u, 0x1Bu);
    expect_handle_info(&result[5], RSQL_BLOB_KIND_BINARY, 0u, 0x1Cu);
    expect_pattern(&result[0], 0u, 0u, 256u, 0u, 0x1Du);
    expect_pattern(&result[1], 1u, 0u, 250u, 0u, 0x1Eu);
    expect_pattern(&result[2], 0u, 239u, 17u, 0u, 0x1Fu);
    expect_pattern(&result[3], 0u, 0u, 259u, 1u, 0x20u);
    verify_query_result();

    rc = rsql_overlay_load(0u);
    for (index = 0u; rc == RSQL_OK && index < 3u; ++index) {
        rc = rsql_blob_delete(&source[index]);
    }
    if (rc == RSQL_OK) rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK || reclaimed != 4u) {
        stage_fail(0x30u, rc, (unsigned char)reclaimed, 4u);
    }
    expect_pattern(&result[0], 0u, 0u, 256u, 0u, 0x31u);
    expect_pattern(&result[1], 1u, 0u, 250u, 0u, 0x32u);
    expect_pattern(&result[2], 0u, 239u, 17u, 0u, 0x33u);
    expect_pattern(&result[3], 0u, 0u, 259u, 1u, 0x34u);

    exec_affected(SQL_CREATE_ROLL_SOURCE, 0u, 0x40u);
    exec_affected(SQL_INSERT_ROLL1, 1u, 0x41u);
    exec_affected(SQL_INSERT_ROLL2, 1u, 0x42u);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 2u; ++fail_index) {
        rsql_journal_test_fail_transaction(
            (unsigned char)(fail_index + 1u), 0u);
        exec_expected(SQL_CREATE_ROLL, RSQL_ERR_IO, 0x50u);
        expect_table_missing(0x51u);
        expect_count(SQL_COUNT_ROLL_SOURCE, 2u, 0x52u);
        if (first_free_page() != expected_free) {
            stage_fail(0x53u, 0u, (unsigned char)first_free_page(),
                       (unsigned char)expected_free);
        }
    }
    exec_affected(SQL_CREATE_ROLL, 2u, 0x60u);
    expect_count(SQL_COUNT_ROLL_SOURCE, 2u, 0x61u);

    /* A single persistent value owns seventeen payload pages, deliberately
     * more than the before-image journal can hold. Explicit DROP must reclaim
     * it through bounded mutations rather than fail with JOURNAL_FULL. */
    expected_free = first_free_page();
    create_big_temp(&big_handle, &big_table, &big_row, &big_index, &big_leaf,
                    g_blob_pages);
    build_free = first_free_page();
    for (fail_index = 0u; fail_index < 6u; ++fail_index) {
        if (fail_index == 0u) {
            rsql_journal_test_fail_transaction(2u, 0u);
        } else if (fail_index == 5u) {
            rsql_journal_test_fail_transaction(21u, 0u);
        } else {
            rsql_journal_test_fail_transaction(10u,
                (unsigned char)(fail_index - 1u));
        }
        exec_expected(SQL_CREATE_BIG_COPY, RSQL_ERR_IO, 0xACu);
        expect_named_table_missing("BIGCOPY", 0xADu);
        if (first_free_page() != build_free) {
            stage_fail(0xAFu, 0u, (unsigned char)first_free_page(),
                       (unsigned char)build_free);
        }
    }
    exec_affected(SQL_CREATE_BIG_COPY, 1u, 0xA4u);
    capture_big_copy(&big_copy_handle, &big_copy_table, &big_copy_row,
                     g_copy_pages);
    exec_affected(SQL_DROP_BIG_TEMP, 0u, 0x7Au);
    expect_named_table_missing("BIGTEMP", 0x7Bu);
    exec_expected(SQL_DROP_BIG_TEMP, RSQL_ERR_NOT_FOUND, 0x7Bu);
    exec_expected(SQL_DROP_INCOMPLETE, RSQL_ERR_SYNTAX, 0x7Bu);
    expect_page_free(big_table, 0x7Du);
    expect_page_free(big_row, 0x7Eu);
    expect_page_free(big_index, 0x7Fu);
    expect_page_free(big_leaf, 0x80u);
    for (index = 0u; index < BIG_BLOB_PAGES; ++index) {
        expect_page_free(g_blob_pages[index], 0x81u);
    }
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) {
        RsqlBlobInfo deleted_info;
        rc = rsql_blob_info(&big_handle, &deleted_info);
    }
    if (rc != RSQL_ERR_NOT_FOUND) {
        stage_fail(0x82u, rc, rc, RSQL_ERR_NOT_FOUND);
    }
    expect_handle_info(&big_copy_handle, RSQL_BLOB_KIND_TEXT,
                       BIG_BLOB_LENGTH, 0xA6u);
    exec_affected(SQL_DROP_BIG_COPY, 0u, 0xA7u);
    expect_page_free(big_copy_table, 0xA8u);
    expect_page_free(big_copy_row, 0xA9u);
    for (index = 0u; index < BIG_COPY_PAGES; ++index) {
        expect_page_free(g_copy_pages[index], 0xAAu);
    }
    if (first_free_page() != expected_free) {
        stage_fail(0xABu, 0u, (unsigned char)first_free_page(),
                   (unsigned char)expected_free);
    }

    /* With two 120-byte rows per RROW page, thirty-four rows force seventeen
     * destination pages. The former monolithic CTAS transaction could not
     * journal this result even though each staged row mutation is bounded. */
    expected_free = first_free_page();
    create_wide_rows();
    capture_row_pages("WIDE", &wide_table, g_blob_pages, WIDE_PAGES, 0xC2u);
    exec_affected(SQL_CREATE_WIDE_COPY, WIDE_ROWS, 0xC3u);
    expect_count(SQL_COUNT_WIDE_COPY, WIDE_ROWS, 0xC4u);
    capture_row_pages("WIDECOPY", &wide_copy_table, g_copy_pages,
                      WIDE_PAGES, 0xC5u);
    exec_affected(SQL_DROP_WIDE, 0u, 0xC6u);
    exec_affected(SQL_DROP_WIDE_COPY, 0u, 0xC7u);
    expect_page_free(wide_table, 0xC8u);
    expect_page_free(wide_copy_table, 0xC9u);
    for (index = 0u; index < WIDE_PAGES; ++index) {
        expect_page_free(g_blob_pages[index], 0xCAu);
        expect_page_free(g_copy_pages[index], 0xCBu);
    }
    if (first_free_page() != expected_free) {
        stage_fail(0xCCu, 0u, (unsigned char)first_free_page(),
                   (unsigned char)expected_free);
    }
    expect_count(SQL_COUNT_ROLL_SOURCE, 2u, 0x83u);
    rc = rsql_shutdown();
    if (rc != RSQL_OK) stage_fail(0x7Cu, rc, 0u, 0u);
    expect_named_table_missing("VCOPY", 0x84u);
    rc = rsql_init(&init);
    if (rc != RSQL_OK) stage_fail(0x85u, rc, 0u, 0u);
    expect_count(SQL_COUNT_ROLL_SOURCE, 2u, 0x85u);

    /* Simulate power loss after a persistent CTAS descriptor and row commit
     * but before publication. BUILDING alone must hide and reclaim it. */
    exec_affected(SQL_CREATE_STALE, 0u, 0x86u);
    exec_affected(SQL_INSERT_STALE, 1u, 0x87u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("STALE", &lifecycle_table);
    stale_table = lifecycle_table.table_page;
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) {
        rc = rsql_row_first(stale_table, &lifecycle_row);
    }
    stale_row = lifecycle_row.page;
    if (rc != RSQL_OK) stage_fail(0x88u, rc, 0u, 0u);
    mark_stale_building(stale_table);
    expect_named_table_missing("STALE", 0x89u);
    rc = rsql_init(&init);
    if (rc != RSQL_OK) stage_fail(0x8Cu, rc, 0u, 0u);
    expect_named_table_missing("STALE", 0x8Du);
    expect_page_free(stale_table, 0x8Eu);
    expect_page_free(stale_row, 0x8Fu);

    /* The explicit DROP visibility marker remains statement-atomic. An
     * injected first write failure leaves the table visible and allocated. */
    exec_affected(SQL_CREATE_TEMP_ROLL, 0u, 0x90u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("TROLL", &lifecycle_table);
    if (rc != RSQL_OK) stage_fail(0x91u, rc, 0u, 0u);
    temp_roll_table = lifecycle_table.table_page;
    rsql_journal_test_fail_after(0u);
    exec_expected(SQL_DROP_TEMP_ROLL, RSQL_ERR_IO, 0x92u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("TROLL", &lifecycle_table);
    if (rc != RSQL_OK) stage_fail(0x93u, rc, 0u, 0u);
    expect_page_used(temp_roll_table, 0x94u);
    exec_affected(SQL_DROP_TEMP_ROLL, 0u, 0x95u);
    expect_named_table_missing("TROLL", 0x96u);
    expect_page_free(temp_roll_table, 0x97u);
    expect_count(SQL_COUNT_ROLL_SOURCE, 2u, 0x98u);

    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

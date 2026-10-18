#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_enum.h"
#include "rsql_errors.h"
#include "rsql_journal.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_row.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_CREATE[] =
    "CREATE TABLE VUP (ID I16, BODY TEXT NULL, RAW BLOB NULL, NAME CHAR(4))";
static const char SQL_INSERT1[] =
    "INSERT INTO VUP VALUES (1, 'ONE', X'0102', 'A')";
static const char SQL_INSERT2[] =
    "INSERT INTO VUP VALUES (2, 'TWO', X'0304', 'B')";
static const char SQL_INSERT3[] =
    "INSERT INTO VUP VALUES (3, NULL, NULL, 'C')";
static const char SQL_UPDATE_ONE[] =
    "UPDATE VUP SET BODY='REPLACED', RAW=X'AA00', NAME='Z' WHERE ID=1";
static const char SQL_UPDATE_BOTH[] =
    "UPDATE VUP SET BODY='BOTH', RAW=X'FF' WHERE ID<=2";
static const char SQL_UPDATE_NULL[] =
    "UPDATE VUP SET BODY=NULL, RAW=NULL WHERE ID=2";
static const char SQL_UPDATE_FROM_NULL[] =
    "UPDATE VUP SET BODY='BORN', RAW=X'' WHERE ID=3";
static const char SQL_UPDATE_NONE[] =
    "UPDATE VUP SET BODY='NEVER', RAW=X'99' WHERE ID>99";
static const char SQL_BAD_TEXT[] =
    "UPDATE VUP SET BODY=X'41' WHERE ID=1";
static const char SQL_BAD_BLOB[] =
    "UPDATE VUP SET RAW='NO' WHERE ID=1";
static const char SQL_COUNT_NULL[] =
    "SELECT COUNT(*) FROM VUP WHERE BODY IS NULL AND RAW IS NULL";
static const char SQL_COUNT_Z[] =
    "SELECT COUNT(*) FROM VUP WHERE NAME='Z'";
static const char SQL_SHAPE_CREATE[] = "CREATE TABLE SL (V CHAR(4))";
static const char SQL_SHAPE_INSERT1[] = "INSERT INTO SL VALUES ('A')";
static const char SQL_SHAPE_INSERT2[] = "INSERT INTO SL VALUES ('CCC')";
static const char SQL_SHAPE_INSERT3[] = "INSERT INTO SL VALUES ('BB')";
static const char SQL_LENGTH_ORDER[] =
    "SELECT LENGTH(V) FROM SL ORDER BY 1 DESC";
static const char SQL_LENGTH_DISTINCT[] =
    "SELECT DISTINCT LENGTH(V) FROM SL ORDER BY 1";

static const char SQL_ROLL_CREATE[] =
    "CREATE TABLE VROLL (ID I16, BODY TEXT, RAW BLOB, NAME CHAR(4))";
static const char SQL_ROLL_INSERT1[] =
    "INSERT INTO VROLL VALUES (1, 'OLD1', X'0102', 'OLD')";
static const char SQL_ROLL_INSERT2[] =
    "INSERT INTO VROLL VALUES (2, 'OLD2', X'0304', 'OLD')";
static const char SQL_ROLL_UPDATE[] =
    "UPDATE VROLL SET BODY='NEW', RAW=X'AA55', NAME='NEW' "
    "WHERE BODY LIKE 'OLD%'";
static const char SQL_ROLL_COUNT_OLD[] =
    "SELECT COUNT(*) FROM VROLL WHERE NAME='OLD'";
static const char SQL_ROLL_COUNT_NEW[] =
    "SELECT COUNT(*) FROM VROLL WHERE NAME='NEW'";

static const char SQL_DROP_TYPE_CREATE[] =
    "CREATE TYPE DTYPE AS ENUM8(OFF,ON)";
static const char SQL_DROP_TABLE_CREATE[] =
    "CREATE TABLE DROW (ID I16,STATE DTYPE)";
static const char SQL_DROP_TABLE_INSERT[] =
    "INSERT INTO DROW VALUES (1,DTYPE.ON)";
static const char SQL_DROP_INDEX_CREATE[] =
    "CREATE INDEX DIDX ON DROW (ID)";
static const char SQL_DROP_INDEX[] = "DROP INDEX DIDX";
static const char SQL_DROP_TYPE[] = "DROP TYPE DTYPE";
static const char SQL_DROP_INDEX_INCOMPLETE[] = "DROP INDEX";
static const char SQL_DROP_TYPE_INCOMPLETE[] = "DROP TYPE";
static const char SQL_DROP_TABLE[] = "DROP TABLE DROW";
static const char SQL_DROP_INDEX_QUERY[] =
    "SELECT COUNT(*) FROM DROW USING INDEX DIDX";
static const char SQL_STALE_TYPE_CREATE[] =
    "CREATE TYPE STYPE AS ENUM8(A,B,C,D,E,F,G,H,I,J,K,L,M,N)";
static const char SQL_STALE_TABLE_CREATE[] =
    "CREATE TABLE STAB (ID I16)";
static const char SQL_STALE_TABLE_INSERT[] =
    "INSERT INTO STAB VALUES (1)";
static const char SQL_STALE_INDEX_CREATE[] =
    "CREATE INDEX SIDX ON STAB (ID)";
static const char SQL_STALE_INDEX_QUERY[] =
    "SELECT COUNT(*) FROM STAB USING INDEX SIDX";
static const char SQL_STALE_TABLE_COUNT[] =
    "SELECT COUNT(*) FROM STAB";
static const char SQL_STALE_TABLE_DROP[] = "DROP TABLE STAB";

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static unsigned char exec_rc(const char* sql, RsqlI64* affected) {
    RsqlExecRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (affected) *affected = request.output.affected_rows;
    return rc;
}

static void exec_expect(const char* sql, unsigned char expected,
                        unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != expected) fail(rc ? rc : stage);
}

static void expect_affected(const char* sql, unsigned char expected,
                            unsigned char stage) {
    RsqlExecRequest request;
    unsigned char index;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK || request.output.affected_rows.bytes[0] != expected) {
        fail(rc ? rc : stage);
    }
    for (index = 1u; index < sizeof(request.output.affected_rows.bytes); ++index) {
        if (request.output.affected_rows.bytes[index] != 0u) fail(stage);
    }
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
        column.value.bytes[0] != expected) fail(rc ? rc : stage);
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc);
}

static void expect_lengths(const char* sql, const unsigned char* expected,
                           unsigned char count, unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    RsqlQueryCloseRequest close;
    unsigned char index;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    column.cursor = open.cursor;
    column.column = 0u;
    for (index = 0u; rc == RSQL_OK && index < count; ++index) {
        rc = rsql_cursor_next(&next);
        if (rc == RSQL_OK && next.has_row) rc = rsql_cursor_column(&column);
        if (rc != RSQL_OK || !next.has_row || column.value.is_null ||
            column.value.type.tag != RSQL_TYPE_I16 ||
            column.value.length != 2u ||
            column.value.bytes[0] != expected[index] ||
            column.value.bytes[1] != 0u) fail(rc ? rc : stage);
    }
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : stage);
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc);
}

static void test_length_shaping(void) {
    static const unsigned char DESCENDING[] = {3u, 2u, 1u};
    static const unsigned char ASCENDING[] = {1u, 2u, 3u};
    exec_expect(SQL_SHAPE_CREATE, RSQL_OK, 0x70u);
    exec_expect(SQL_SHAPE_INSERT1, RSQL_OK, 0x71u);
    exec_expect(SQL_SHAPE_INSERT2, RSQL_OK, 0x72u);
    exec_expect(SQL_SHAPE_INSERT3, RSQL_OK, 0x73u);
    expect_lengths(SQL_LENGTH_ORDER, DESCENDING, 3u, 0x74u);
    expect_lengths(SQL_LENGTH_DISTINCT, ASCENDING, 3u, 0x75u);
}

static unsigned int first_free_page(void) {
    unsigned long page;
    unsigned char allocated;
    unsigned char rc;
    for (page = rsql_page_first_usable(); page < rsql_page_limit(); ++page) {
        rc = rsql_page_is_allocated((unsigned int)page, &allocated);
        if (rc != RSQL_OK) fail(rc);
        if (!allocated) return (unsigned int)page;
    }
    return RSQL_PAGE_NONE;
}

static unsigned char capture_rows(const char* table_name,
                                  RsqlBlobHandle* handles,
                                  unsigned char* nulls,
                                  unsigned char maximum,
                                  unsigned char stage) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char row[15];
    unsigned char count = 0u;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(table_name, &table);
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_row_first(table.table_page, &row_id);
    while (rc == RSQL_OK && count < maximum) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
        if (rc != RSQL_OK) break;
        nulls[count] = row[0];
        memcpy(handles[count * 2u].bytes, &row[3], 4u);
        memcpy(handles[count * 2u + 1u].bytes, &row[7], 4u);
        ++count;
        rc = rsql_row_next(table.table_page, &row_id, &row_id);
    }
    if (rc != RSQL_ERR_NOT_FOUND && !(rc == RSQL_OK && count == maximum)) {
        fail(rc ? rc : stage);
    }
    return count;
}

static unsigned char same_handle(const RsqlBlobHandle* left,
                                 const RsqlBlobHandle* right) {
    return memcmp(left->bytes, right->bytes, 4u) == 0 ? 1u : 0u;
}

static void expect_handle_state(const RsqlBlobHandle* handles,
                                unsigned char count, unsigned char expected,
                                unsigned char stage) {
    RsqlBlobInfo info;
    unsigned char index;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail(rc);
    for (index = 0u; index < count; ++index) {
        rc = rsql_blob_info(&handles[index], &info);
        if (rc != expected) fail(rc ? rc : stage);
    }
}

static void expect_payload(const RsqlBlobHandle* handle, unsigned char kind,
                           const unsigned char* expected,
                           unsigned char length, unsigned char stage) {
    RsqlBlobInfo info;
    unsigned char bytes[16];
    unsigned int read;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_info(handle, &info);
    if (rc != RSQL_OK || info.kind != kind || info.length != length) {
        fail(rc ? rc : stage);
    }
    rc = rsql_blob_read(handle, 0ul, bytes, sizeof(bytes), &read);
    if (rc != RSQL_OK || read != length || memcmp(bytes, expected, length)) {
        fail(rc ? rc : stage);
    }
}

static void expect_query_open(const char* sql, unsigned char expected,
                              unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != expected) fail(rc ? rc : stage);
    if (rc == RSQL_OK) {
        RsqlQueryCloseRequest close;
        close.cursor = open.cursor;
        rc = rsql_query_close(&close);
        if (rc != RSQL_OK) fail(rc);
    }
}

static void expect_enum_state(const char* name, unsigned char expected,
                              unsigned char stage) {
    RsqlEnumInfo info;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_enum_find(name, &info);
    if (rc != expected) fail(rc ? rc : stage);
}

static void expect_page_free(unsigned int page, unsigned char stage) {
    unsigned char allocated = 1u;
    unsigned char rc = rsql_page_is_allocated(page, &allocated);
    if (rc != RSQL_OK || allocated) fail(rc ? rc : stage);
}

static void mark_descriptor(unsigned int page, unsigned char offset,
                            unsigned char flag, unsigned char stage) {
    unsigned char rc = rsql_reu_read(rsql_reu_page_address(page),
                                      g_rsql_meta_page0,
                                      RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc);
    g_rsql_meta_page0[offset] |= flag;
    g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(g_rsql_meta_page0);
    rc = rsql_reu_write(rsql_reu_page_address(page), g_rsql_meta_page0,
                        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static void capture_stale_pages(unsigned int* index_page,
                                unsigned int* index_leaf,
                                unsigned int* enum_page,
                                unsigned int* member1,
                                unsigned int* member2) {
    unsigned char rc = rsql_reu_read(
        rsql_reu_page_address(rsql_page_catalog_root()), g_rsql_meta_page0,
        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc);
    *index_page = rsql_get_u16(&g_rsql_meta_page0[RSQL_ROOT_FIRST_INDEX]);
    *enum_page = rsql_get_u16(&g_rsql_meta_page0[RSQL_ROOT_FIRST_ENUM]);
    rc = rsql_reu_read(rsql_reu_page_address(*index_page),
                       g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc);
    *index_leaf = rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_LEAF_HEAD]);
    rc = rsql_reu_read(rsql_reu_page_address(*enum_page),
                       g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc);
    *member1 = rsql_get_u16(&g_rsql_meta_page0[10u]);
    rc = rsql_reu_read(rsql_reu_page_address(*member1),
                       g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(rc);
    *member2 = rsql_get_u16(&g_rsql_meta_page0[6u]);
    if (*index_page == RSQL_PAGE_NONE || *index_leaf == RSQL_PAGE_NONE ||
        *enum_page == RSQL_PAGE_NONE || *member1 == RSQL_PAGE_NONE ||
        *member2 == RSQL_PAGE_NONE) fail(0xE0u);
}

static void test_schema_drop(RsqlInitRequest* init) {
    unsigned int baseline;
    unsigned int index_page;
    unsigned int index_leaf;
    unsigned int enum_page;
    unsigned int member1;
    unsigned int member2;
    unsigned char rc;

    TEST_STAGE = 0xE0u;
    baseline = first_free_page();
    exec_expect(SQL_DROP_TYPE_CREATE, RSQL_OK, 0xE0u);
    exec_expect(SQL_DROP_TABLE_CREATE, RSQL_OK, 0xE1u);
    exec_expect(SQL_DROP_TABLE_INSERT, RSQL_OK, 0xE2u);
    exec_expect(SQL_DROP_INDEX_CREATE, RSQL_OK, 0xE3u);
    expect_count(SQL_DROP_INDEX_QUERY, 1u, 0xE4u);
    exec_expect(SQL_DROP_TYPE, RSQL_ERR_DEPENDENT_OBJECT, 0xE5u);

    rsql_journal_test_fail_after(0u);
    exec_expect(SQL_DROP_INDEX, RSQL_ERR_IO, 0xE6u);
    expect_count(SQL_DROP_INDEX_QUERY, 1u, 0xE7u);
    expect_affected(SQL_DROP_INDEX, 0u, 0xE8u);
    expect_query_open(SQL_DROP_INDEX_QUERY, RSQL_ERR_NOT_FOUND, 0xE9u);
    exec_expect(SQL_DROP_INDEX, RSQL_ERR_NOT_FOUND, 0xEAu);
    expect_affected(SQL_DROP_TABLE, 0u, 0xEBu);

    rsql_journal_test_fail_after(0u);
    exec_expect(SQL_DROP_TYPE, RSQL_ERR_IO, 0xECu);
    expect_enum_state("DTYPE", RSQL_OK, 0xEDu);
    expect_affected(SQL_DROP_TYPE, 0u, 0xEEu);
    expect_enum_state("DTYPE", RSQL_ERR_NOT_FOUND, 0xEFu);
    exec_expect(SQL_DROP_TYPE, RSQL_ERR_NOT_FOUND, 0xEFu);
    exec_expect(SQL_DROP_INDEX_INCOMPLETE, RSQL_ERR_SYNTAX, 0xEFu);
    exec_expect(SQL_DROP_TYPE_INCOMPLETE, RSQL_ERR_SYNTAX, 0xEFu);
    if (first_free_page() != baseline) fail(0xF0u);

    baseline = first_free_page();
    exec_expect(SQL_STALE_TYPE_CREATE, RSQL_OK, 0xF1u);
    exec_expect(SQL_STALE_TABLE_CREATE, RSQL_OK, 0xF2u);
    exec_expect(SQL_STALE_TABLE_INSERT, RSQL_OK, 0xF3u);
    exec_expect(SQL_STALE_INDEX_CREATE, RSQL_OK, 0xF4u);
    capture_stale_pages(&index_page, &index_leaf, &enum_page,
                        &member1, &member2);
    mark_descriptor(index_page, RSQL_INDEX_FLAGS,
                    RSQL_INDEX_FLAG_DROPPING, 0xF5u);
    mark_descriptor(enum_page, RSQL_ENUM_FLAGS,
                    RSQL_ENUM_FLAG_DROPPING, 0xF6u);
    rc = rsql_init(init);
    if (rc != RSQL_OK) fail(rc);
    expect_page_free(index_page, 0xF7u);
    expect_page_free(index_leaf, 0xF8u);
    expect_page_free(enum_page, 0xF9u);
    expect_page_free(member1, 0xFAu);
    expect_page_free(member2, 0xFBu);
    expect_query_open(SQL_STALE_INDEX_QUERY, RSQL_ERR_NOT_FOUND, 0xFCu);
    expect_enum_state("STYPE", RSQL_ERR_NOT_FOUND, 0xFDu);
    expect_count(SQL_STALE_TABLE_COUNT, 1u, 0xFEu);
    expect_affected(SQL_STALE_TABLE_DROP, 0u, 0xFFu);
    if (first_free_page() != baseline) fail(0xFEu);
}

int main(void) {
    static const unsigned char REPLACED[] = "REPLACED";
    static const unsigned char BOTH[] = "BOTH";
    static const unsigned char BORN[] = "BORN";
    static const unsigned char RAW_AA00[] = {0xAAu, 0x00u};
    static const unsigned char RAW_FF[] = {0xFFu};
    RsqlInitRequest init;
    RsqlBlobHandle old_handles[4];
    RsqlBlobHandle after_one[6];
    RsqlBlobHandle after_both[6];
    RsqlBlobHandle after_null[6];
    RsqlBlobHandle roll_old[4];
    RsqlBlobHandle roll_now[4];
    unsigned char nulls[3];
    RsqlI64 affected;
    unsigned int expected_free;
    unsigned int reclaimed;
    unsigned char fail_index;
    unsigned char success_index = 0xFFu;
    unsigned char rc;

    BORDER_COLOR = 0u;
    memset(&init, 0, sizeof(init));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail(rc);
    if (rsql_reu_size_kib() != (unsigned int)(512u << REU_SIZE_SELECTOR)) {
        fail(0x80u);
    }

    TEST_STAGE = 0x81u;
    exec_expect(SQL_CREATE, RSQL_OK, 0x81u);
    exec_expect(SQL_INSERT1, RSQL_OK, 0x82u);
    exec_expect(SQL_INSERT2, RSQL_OK, 0x83u);
    exec_expect(SQL_INSERT3, RSQL_OK, 0x84u);
    test_length_shaping();
    if (capture_rows("VUP", after_one, nulls, 3u, 0x85u) != 3u) fail(0x85u);
    memcpy(old_handles, after_one, sizeof(old_handles));

    expect_affected(SQL_UPDATE_ONE, 1u, 0x86u);
    capture_rows("VUP", after_one, nulls, 3u, 0x87u);
    expect_handle_state(old_handles, 2u, RSQL_ERR_NOT_FOUND, 0x88u);
    expect_handle_state(&old_handles[2], 2u, RSQL_OK, 0x89u);
    if (same_handle(&after_one[0], &old_handles[0]) ||
        same_handle(&after_one[1], &old_handles[1])) fail(0x8Au);
    expect_payload(&after_one[0], RSQL_BLOB_KIND_TEXT, REPLACED, 8u, 0x8Bu);
    expect_payload(&after_one[1], RSQL_BLOB_KIND_BINARY, RAW_AA00, 2u, 0x8Cu);
    expect_count(SQL_COUNT_Z, 1u, 0x8Du);

    expect_affected(SQL_UPDATE_BOTH, 2u, 0x90u);
    capture_rows("VUP", after_both, nulls, 3u, 0x91u);
    expect_handle_state(after_one, 4u, RSQL_ERR_NOT_FOUND, 0x92u);
    expect_handle_state(after_both, 4u, RSQL_OK, 0x93u);
    if (same_handle(&after_both[0], &after_both[2]) ||
        same_handle(&after_both[1], &after_both[3])) fail(0x94u);
    expect_payload(&after_both[0], RSQL_BLOB_KIND_TEXT, BOTH, 4u, 0x95u);
    expect_payload(&after_both[2], RSQL_BLOB_KIND_TEXT, BOTH, 4u, 0x96u);
    expect_payload(&after_both[1], RSQL_BLOB_KIND_BINARY, RAW_FF, 1u, 0x97u);

    expect_affected(SQL_UPDATE_NULL, 1u, 0x98u);
    capture_rows("VUP", after_null, nulls, 3u, 0x99u);
    if ((nulls[1] & 0x06u) != 0x06u) fail(0x9Au);
    expect_handle_state(&after_both[2], 2u, RSQL_ERR_NOT_FOUND, 0x9Bu);
    expect_count(SQL_COUNT_NULL, 2u, 0x9Cu);

    expect_affected(SQL_UPDATE_FROM_NULL, 1u, 0x9Du);
    capture_rows("VUP", after_null, nulls, 3u, 0x9Eu);
    if (nulls[2] & 0x06u) fail(0x9Fu);
    expect_payload(&after_null[4], RSQL_BLOB_KIND_TEXT, BORN, 4u, 0xA0u);
    expect_payload(&after_null[5], RSQL_BLOB_KIND_BINARY, BORN, 0u, 0xA1u);
    expect_count(SQL_COUNT_NULL, 1u, 0xA2u);
    exec_expect(SQL_BAD_TEXT, RSQL_ERR_TYPE_MISMATCH, 0xA3u);
    exec_expect(SQL_BAD_BLOB, RSQL_ERR_TYPE_MISMATCH, 0xA4u);
    expected_free = first_free_page();
    expect_affected(SQL_UPDATE_NONE, 0u, 0xA5u);
    if (first_free_page() != expected_free) fail(0xA6u);
    TEST_STAGE = 0xB0u;
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK) fail(rc);
    exec_expect(SQL_ROLL_CREATE, RSQL_OK, 0xB0u);
    exec_expect(SQL_ROLL_INSERT1, RSQL_OK, 0xB1u);
    exec_expect(SQL_ROLL_INSERT2, RSQL_OK, 0xB2u);
    if (capture_rows("VROLL", roll_old, nulls, 2u, 0xB3u) != 2u) fail(0xB3u);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 64u; ++fail_index) {
        TEST_STAGE = (unsigned char)(0xC0u + fail_index);
        rsql_journal_test_fail_after(fail_index);
        rc = exec_rc(SQL_ROLL_UPDATE, &affected);
        if (rc == RSQL_OK) {
            success_index = fail_index;
            break;
        }
        if (rc != RSQL_ERR_IO) fail(rc);
        expect_count(SQL_ROLL_COUNT_OLD, 2u, 0xC1u);
        expect_count(SQL_ROLL_COUNT_NEW, 0u, 0xC2u);
        capture_rows("VROLL", roll_now, nulls, 2u, 0xC3u);
        if (memcmp(roll_now, roll_old, sizeof(roll_old))) fail(0xC4u);
        expect_handle_state(roll_old, 4u, RSQL_OK, 0xC5u);
        if (first_free_page() != expected_free) fail(0xC6u);
    }
    if (success_index == 0xFFu || success_index == 0u ||
        affected.bytes[0] != 2u ||
        rsql_journal_test_write_count() != success_index) fail(0xD0u);
    expect_count(SQL_ROLL_COUNT_OLD, 0u, 0xD1u);
    expect_count(SQL_ROLL_COUNT_NEW, 2u, 0xD2u);
    capture_rows("VROLL", roll_now, nulls, 2u, 0xD3u);
    expect_handle_state(roll_old, 4u, RSQL_ERR_NOT_FOUND, 0xD4u);
    expect_handle_state(roll_now, 4u, RSQL_OK, 0xD5u);
    if (same_handle(&roll_now[0], &roll_now[2]) ||
        same_handle(&roll_now[1], &roll_now[3])) fail(0xD6u);
    rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK || reclaimed != 4u) fail(rc ? rc : 0xD7u);

    test_schema_drop(&init);

    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

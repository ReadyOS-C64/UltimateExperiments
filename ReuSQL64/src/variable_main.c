#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_enum.h"
#include "rsql_journal.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_row.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_RC (*(volatile unsigned char*)0xCFF4)
#define TEST_ACTUAL (*(volatile unsigned char*)0xCFF5)
#define TEST_EXPECTED (*(volatile unsigned char*)0xCFF6)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_CREATE_FILTERED[] =
    "CREATE TABLE VDEL(BODY TEXT NULL,RAW BLOB,TAG CHAR(4)NULL)";
static const char SQL_INSERT_FILTERED1[] =
    "INSERT INTO VDEL VALUES ('ALPHA',X'001122','Z')";
static const char SQL_INSERT_FILTERED2[] =
    "INSERT INTO VDEL VALUES (NULL,X'',NULL)";
static const char SQL_DELETE_FILTERED_NULL[] =
    "DELETE FROM VDEL WHERE BODY IS NULL";
static const char SQL_DELETE_FILTERED_ALL[] = "DELETE FROM VDEL";
static const char SQL_COUNT_FILTERED[] = "SELECT COUNT(*) FROM VDEL";
static const char SQL_VARIABLE_BOOL[] =
    "SELECT*FROM VDEL WHERE BODY LIKE 'A%' AND RAW=X'001122'";
static const char SQL_TEXT_CONCAT[] =
    "SELECT BODY||'X',CONCAT('<',BODY),BODY||BODY,BODY||TAG,TAG||BODY FROM VDEL";

static const char SQL_CREATE_MEASURE[] =
    "CREATE TABLE VMEASURE (BODY TEXT, RAW BLOB)";
static const char SQL_INSERT_MEASURE1[] =
    "INSERT INTO VMEASURE VALUES ('ONE', X'0102')";
static const char SQL_INSERT_MEASURE2[] =
    "INSERT INTO VMEASURE VALUES ('TWO', X'0304')";
static const char SQL_DELETE_MEASURE[] = "DELETE FROM VMEASURE";

static const char SQL_CREATE_FAIL[] =
    "CREATE TABLE VFAIL (BODY TEXT, RAW BLOB)";
static const char SQL_INSERT_FAIL1[] =
    "INSERT INTO VFAIL VALUES ('ONE', X'0102')";
static const char SQL_INSERT_FAIL2[] =
    "INSERT INTO VFAIL VALUES ('TWO', X'0304')";
static const char SQL_DELETE_FAIL[] = "DELETE FROM VFAIL";
static const char SQL_COUNT_FAIL[] = "SELECT COUNT(*) FROM VFAIL";

static const char SQL_CREATE_UPDATE[] =
    "CREATE TABLE UDATA (ID I16, NAME CHAR(6), SCORE I32 NULL)";
static const char SQL_INSERT_UPDATE1[] =
    "INSERT INTO UDATA VALUES (1, 'A', 10)";
static const char SQL_INSERT_UPDATE2[] =
    "INSERT INTO UDATA VALUES (2, 'B', NULL)";
static const char SQL_INSERT_UPDATE3[] =
    "INSERT INTO UDATA VALUES (3, 'C', 30)";
static const char SQL_UPDATE_ONE[] =
    "UPDATE UDATA SET NAME = 'Z', SCORE = 99 WHERE ID >= 2 AND ID < 3";
static const char SQL_UPDATE_MULTI[] =
    "UPDATE UDATA SET SCORE = NULL, NAME = 'N' WHERE ID >= 2";
static const char SQL_UPDATE_NONE[] =
    "UPDATE UDATA SET SCORE = 7 WHERE ID > 99";
static const char SQL_UPDATE_RANGE[] =
    "UPDATE UDATA SET ID = 40000 WHERE ID = 1";
static const char SQL_UPDATE_DUPLICATE[] =
    "UPDATE UDATA SET NAME = 'A', NAME = 'B' WHERE ID = 1";
static const char SQL_UPDATE_VARIABLE[] =
    "UPDATE VDEL SET BODY = 'X'";
static const char SQL_UPDATE_BAD[] = "UPDATE UDATA NAME = 'X'";
static const char SQL_COUNT_UPDATE_ONE[] =
    "SELECT COUNT(*) FROM UDATA WHERE NAME = 'Z' AND SCORE = 99";
static const char SQL_COUNT_UPDATE_NULL[] =
    "SELECT COUNT(*) FROM UDATA WHERE SCORE IS NULL";
static const char SQL_COUNT_UPDATE_NAME[] =
    "SELECT COUNT(*) FROM UDATA WHERE NAME = 'N'";
static const char SQL_CREATE_TEMP_RESULT[] =
    "CREATE TEMP TABLE UR AS SELECT ID,NAME,SCORE FROM UDATA "
    "WHERE ID>=2 ORDER BY ID DESC";
static const char SQL_COUNT_TEMP_RESULT[] =
    "SELECT COUNT(*) FROM UR WHERE C1>=2 AND C2 LIKE '%'";
static const char SQL_COUNT_TEMP_NULL[] =
    "SELECT COUNT(*) FROM UR WHERE C3 IS NULL";
static const char SQL_CREATE_AGG_RESULT[] =
    "CREATE TABLE UA AS SELECT COUNT(*),SUM(SCORE) FROM UDATA";
static const char SQL_COUNT_AGG_RESULT[] =
    "SELECT COUNT(*) FROM UA WHERE C1=3 AND C2=40";

static const char SQL_CREATE_UPDATE_MEASURE[] =
    "CREATE TABLE UMEASURE (ID I16, SCORE I32)";
static const char SQL_INSERT_UPDATE_MEASURE1[] =
    "INSERT INTO UMEASURE VALUES (1, 1)";
static const char SQL_INSERT_UPDATE_MEASURE2[] =
    "INSERT INTO UMEASURE VALUES (2, 2)";
static const char SQL_UPDATE_MEASURE[] = "UPDATE UMEASURE SET SCORE = 9";
static const char SQL_CREATE_UPDATE_ROLL[] =
    "CREATE TABLE UROLL (ID I16, SCORE I32)";
static const char SQL_INSERT_UPDATE_ROLL1[] =
    "INSERT INTO UROLL VALUES (1, 1)";
static const char SQL_INSERT_UPDATE_ROLL2[] =
    "INSERT INTO UROLL VALUES (2, 2)";
static const char SQL_UPDATE_ROLL[] = "UPDATE UROLL SET SCORE = 9";
static const char SQL_COUNT_UPDATE_ROLL_OLD[] =
    "SELECT COUNT(*) FROM UROLL WHERE SCORE < 9";
static const char SQL_COUNT_UPDATE_ROLL_NEW[] =
    "SELECT COUNT(*) FROM UROLL WHERE SCORE = 9";

static const char SQL_CREATE_ENUM8[] =
    "CREATE TYPE MOOD AS ENUM8 (SAD = 1, OK = 2, HAPPY = 7)";
static const char SQL_CREATE_ENUM16[] =
    "CREATE TYPE BIGCODE AS ENUM16 (LOW = 1, HIGH = 300)";
static const char SQL_CREATE_ENUM_DUP_VALUE[] =
    "CREATE TYPE BADENUM AS ENUM8 (A = 1, B = 1)";
static const char SQL_CREATE_ENUM_RANGE[] =
    "CREATE TYPE BADRANGE AS ENUM8 (A = 300)";
static const char SQL_CREATE_ENUM_BAD[] =
    "CREATE TYPE BADTYPE AS ENUM32 (A)";
static const char SQL_CREATE_ENUM_MEASURE[] =
    "CREATE TYPE EMEASURE AS ENUM8 (A, B, C)";
static const char SQL_CREATE_ENUM_FAIL[] =
    "CREATE TYPE EFAIL AS ENUM8 (A, B, C)";
static const char SQL_CREATE_ENUM_TABLE[] =
    "CREATE TABLE EDATA (ID I16, STATE MOOD, CODE BIGCODE NULL)";
static const char SQL_CREATE_UNKNOWN_ENUM_TABLE[] =
    "CREATE TABLE EBAD (STATE NOSUCH)";
static const char SQL_INSERT_ENUM1[] =
    "INSERT INTO EDATA VALUES (1, MOOD.HAPPY, BIGCODE.HIGH)";
static const char SQL_INSERT_ENUM2[] =
    "INSERT INTO EDATA VALUES (2, MOOD.SAD, NULL)";
static const char SQL_COUNT_ENUM_HAPPY[] =
    "SELECT COUNT(*) FROM EDATA WHERE STATE = MOOD.HAPPY";
static const char SQL_COUNT_ENUM_OK[] =
    "SELECT COUNT(*) FROM EDATA WHERE STATE = MOOD.OK";
static const char SQL_COUNT_ENUM_HIGH[] =
    "SELECT COUNT(*) FROM EDATA WHERE CODE = BIGCODE.HIGH";
static const char SQL_UPDATE_ENUM[] =
    "UPDATE EDATA SET STATE = MOOD.OK, CODE = BIGCODE.LOW "
    "WHERE STATE = MOOD.HAPPY";
static const char SQL_INSERT_ENUM_MISSING[] =
    "INSERT INTO EDATA VALUES (3, MOOD.MISSING, NULL)";
static const char SQL_INSERT_ENUM_WRONG[] =
    "INSERT INTO EDATA VALUES (3, BIGCODE.LOW, NULL)";
static const char SQL_INSERT_ENUM_NONENUM[] =
    "INSERT INTO EDATA VALUES (MOOD.OK, MOOD.OK, NULL)";
static const char SQL_INSERT_ENUM8_RANGE[] =
    "INSERT INTO EDATA VALUES (3, 256, NULL)";
static const char SQL_INSERT_ENUM16_RANGE[] =
    "INSERT INTO EDATA VALUES (3, MOOD.OK, 65536)";
static const char SQL_SELECT_ENUM_WRONG[] =
    "SELECT COUNT(*) FROM EDATA WHERE STATE = BIGCODE.LOW";
static const char SQL_UPDATE_ENUM_MISSING[] =
    "UPDATE EDATA SET STATE = MOOD.MISSING WHERE ID = 1";
static const char SQL_SELECT_ENUM_ROW[] =
    "SELECT STATE, CODE FROM EDATA WHERE ID = 1";

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static void exec_expect(const char* sql, unsigned char expected,
                        unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != expected) {
        TEST_RC = rc;
        TEST_EXPECTED = expected;
        fail(rc ? rc : stage);
    }
}

static void expect_affected(const char* sql, unsigned char expected,
                            unsigned char stage) {
    RsqlExecRequest request;
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK || request.output.affected_rows.bytes[0] != expected) {
        TEST_RC = rc;
        TEST_ACTUAL = request.output.affected_rows.bytes[0];
        TEST_EXPECTED = expected;
        fail(rc ? rc : stage);
    }
    for (index = 1u; index < 8u; ++index) {
        if (request.output.affected_rows.bytes[index] != 0u) fail(stage);
    }
}

static void close_cursor(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static void expect_concat_column(RsqlCursorHandle cursor,
                                 unsigned char column,
                                 const char* expected,
                                 unsigned char boundary,
                                 unsigned char stage) {
    RsqlCursorColumnRequest info;
    RsqlValueReadRequest read;
    unsigned char bytes[16];
    unsigned char length = strlen(expected);
    unsigned char offset;
    unsigned char slice;
    unsigned char rc;
    info.cursor = cursor;
    info.column = column;
    rc = rsql_cursor_column(&info);
    if (rc != RSQL_OK || info.value.is_null ||
        info.value.type.tag != RSQL_TYPE_TEXT ||
        info.value.length != length) {
        TEST_STAGE = rc ? rc : (unsigned char)info.value.length;
        fail(stage);
    }
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length) {
        TEST_STAGE = rc ? rc : (unsigned char)read.bytes_read;
        fail((unsigned char)(stage + 0x10u));
    }
    if (memcmp(bytes, expected, length) != 0) {
        TEST_STAGE = bytes[0];
        fail((unsigned char)(stage + 0x20u));
    }
    offset = boundary ? (unsigned char)(boundary - 1u) : 0u;
    slice = (unsigned char)(length - offset);
    if (slice > 3u) slice = 3u;
    read.offset = offset;
    read.capacity = 3u;
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != slice ||
        memcmp(bytes, expected + offset, slice) != 0) {
        TEST_STAGE = rc ? rc : (unsigned char)read.bytes_read;
        fail((unsigned char)(stage + 0x30u));
    }
}

static void test_text_concat(void) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest info;
    unsigned char index;
    unsigned char rc;
    open.sql = SQL_TEXT_CONCAT;
    open.sql_length = strlen(SQL_TEXT_CONCAT);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : 0x7Au);
    expect_concat_column(open.cursor, 0u, "ALPHAX", 5u, 0x7Bu);
    expect_concat_column(open.cursor, 1u, "<ALPHA", 1u, 0x7Cu);
    expect_concat_column(open.cursor, 2u, "ALPHAALPHA", 5u, 0x73u);
    expect_concat_column(open.cursor, 3u, "ALPHAZ", 5u, 0x74u);
    expect_concat_column(open.cursor, 4u, "ZALPHA", 1u, 0x75u);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : 0x7Du);
    info.cursor = open.cursor;
    for (index = 0u; index < 5u; ++index) {
        info.column = index;
        rc = rsql_cursor_column(&info);
        if (rc != RSQL_OK || !info.value.is_null) {
            fail(rc ? rc : (unsigned char)(0x7Eu + index));
        }
    }
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : 0x71u);
    close_cursor(open.cursor, 0x72u);
}

static void expect_count(const char* sql, unsigned char expected,
                         unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    unsigned char rc;
    TEST_STAGE = stage;
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
        column.value.bytes[0] != expected || column.value.bytes[1] != 0u) {
        fail(rc ? rc : stage);
    }
    close_cursor(open.cursor, stage);
}

static void open_expect(const char* sql, unsigned char expected,
                        unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != expected) fail(rc ? rc : stage);
    if (rc == RSQL_OK) close_cursor(open.cursor, stage);
}

static void expect_single_scan(const char* sql, unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    unsigned char rc;
    TEST_STAGE = stage;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : stage);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : stage);
    close_cursor(open.cursor, stage);
}

static void expect_enum_row(unsigned char expected_state,
                            unsigned int expected_code,
                            unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    unsigned char rc;
    open.sql = SQL_SELECT_ENUM_ROW;
    open.sql_length = strlen(SQL_SELECT_ENUM_ROW);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    column.cursor = open.cursor;
    column.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || !next.has_row || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_ENUM8 ||
        column.value.bytes[0] != expected_state) fail(rc ? rc : stage);
    column.column = 1u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_ENUM16 ||
        column.value.bytes[0] != (unsigned char)expected_code ||
        column.value.bytes[1] != (unsigned char)(expected_code >> 8u)) {
        fail(rc ? rc : stage);
    }
    close_cursor(open.cursor, stage);
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

static void capture_two_rows(const char* table_name,
                             RsqlBlobHandle* handles,
                             unsigned char stage) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    unsigned char row[13];
    unsigned char rc;
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(table_name, &table);
    if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_row_first(table.table_page, &row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
    }
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    memcpy(handles[0].bytes, &row[1], 4u);
    memcpy(handles[1].bytes, &row[5], 4u);
    rc = rsql_row_next(table.table_page, &row_id, &row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &row_id, row, sizeof(row));
    }
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    memcpy(handles[2].bytes, &row[1], 4u);
    memcpy(handles[3].bytes, &row[5], 4u);
}

static void expect_handles(RsqlBlobHandle* handles, unsigned char count,
                           unsigned char expected, unsigned char stage) {
    RsqlBlobInfo info;
    unsigned char index;
    unsigned char rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail(rc);
    for (index = 0u; index < count; ++index) {
        rc = rsql_blob_info(&handles[index], &info);
        if (rc != expected) fail(rc ? rc : stage);
    }
}

int main(void) {
    RsqlInitRequest init;
    RsqlBlobHandle filtered[4];
    RsqlBlobHandle failed[4];
    RsqlEnumInfo enum_info;
    RsqlTableInfo enum_table;
    RsqlColumnInfo enum_column;
    unsigned int expected_free;
    unsigned int reclaimed;
    unsigned int enum_value;
    unsigned int mood_id;
    unsigned int bigcode_id;
    unsigned char delete_writes;
    unsigned char update_writes;
    unsigned char enum_writes;
    unsigned char fail_index;
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
    exec_expect(SQL_CREATE_FILTERED, RSQL_OK, 0x81u);
    exec_expect(SQL_INSERT_FILTERED1, RSQL_OK, 0x82u);
    exec_expect(SQL_INSERT_FILTERED2, RSQL_OK, 0x83u);
    expect_single_scan(SQL_VARIABLE_BOOL, 0x60u);
    test_text_concat();
    capture_two_rows("VDEL", filtered, 0x84u);
    expect_affected(SQL_DELETE_FILTERED_NULL, 1u, 0x85u);
    expect_count(SQL_COUNT_FILTERED, 1u, 0x86u);
    expect_handles(&filtered[3], 1u, RSQL_ERR_NOT_FOUND, 0x87u);
    expect_handles(filtered, 2u, RSQL_OK, 0x88u);
    expect_affected(SQL_DELETE_FILTERED_ALL, 1u, 0x89u);
    expect_count(SQL_COUNT_FILTERED, 0u, 0x8Au);
    expect_handles(filtered, 2u, RSQL_ERR_NOT_FOUND, 0x8Bu);
    rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK || reclaimed != 2u) fail(rc ? rc : 0x8Cu);

    TEST_STAGE = 0x90u;
    exec_expect(SQL_CREATE_MEASURE, RSQL_OK, 0x90u);
    exec_expect(SQL_INSERT_MEASURE1, RSQL_OK, 0x91u);
    exec_expect(SQL_INSERT_MEASURE2, RSQL_OK, 0x92u);
    expect_affected(SQL_DELETE_MEASURE, 2u, 0x93u);
    delete_writes = rsql_journal_test_write_count();
    if (delete_writes == 0u || delete_writes == 0xFFu) fail(0x94u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK || reclaimed != 4u) fail(rc ? rc : 0x95u);

    TEST_STAGE = 0xA0u;
    exec_expect(SQL_CREATE_FAIL, RSQL_OK, 0xA0u);
    exec_expect(SQL_INSERT_FAIL1, RSQL_OK, 0xA1u);
    exec_expect(SQL_INSERT_FAIL2, RSQL_OK, 0xA2u);
    capture_two_rows("VFAIL", failed, 0xA3u);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < delete_writes; ++fail_index) {
        TEST_STAGE = (unsigned char)(0xB0u + fail_index);
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_DELETE_FAIL, RSQL_ERR_IO, 0xB0u);
        expect_count(SQL_COUNT_FAIL, 2u, 0xB1u);
        expect_handles(failed, 4u, RSQL_OK, 0xB2u);
        if (first_free_page() != expected_free) fail(0xB3u);
    }
    TEST_STAGE = 0xC0u;
    expect_affected(SQL_DELETE_FAIL, 2u, 0xC0u);
    expect_count(SQL_COUNT_FAIL, 0u, 0xC1u);
    expect_handles(failed, 4u, RSQL_ERR_NOT_FOUND, 0xC2u);
    rc = rsql_blob_compact(&reclaimed);
    if (rc != RSQL_OK || reclaimed != 4u) fail(rc ? rc : 0xC3u);

    TEST_STAGE = 0xD0u;
    exec_expect(SQL_CREATE_UPDATE, RSQL_OK, 0xD0u);
    exec_expect(SQL_INSERT_UPDATE1, RSQL_OK, 0xD1u);
    exec_expect(SQL_INSERT_UPDATE2, RSQL_OK, 0xD2u);
    exec_expect(SQL_INSERT_UPDATE3, RSQL_OK, 0xD3u);
    expect_affected(SQL_CREATE_TEMP_RESULT, 2u, 0x10u);
    expect_count(SQL_COUNT_TEMP_RESULT, 2u, 0x11u);
    expect_count(SQL_COUNT_TEMP_NULL, 1u, 0x12u);
    expect_affected(SQL_CREATE_AGG_RESULT, 1u, 0x13u);
    expect_count(SQL_COUNT_AGG_RESULT, 1u, 0x14u);
    expect_affected(SQL_UPDATE_ONE, 1u, 0xD4u);
    expect_count(SQL_COUNT_UPDATE_ONE, 1u, 0xD5u);
    expect_affected(SQL_UPDATE_MULTI, 2u, 0xD6u);
    expect_count(SQL_COUNT_UPDATE_NULL, 2u, 0xD7u);
    expect_count(SQL_COUNT_UPDATE_NAME, 2u, 0xD8u);
    expect_affected(SQL_UPDATE_NONE, 0u, 0xD9u);
    exec_expect(SQL_UPDATE_RANGE, RSQL_ERR_TYPE_MISMATCH, 0xDAu);
    exec_expect(SQL_UPDATE_DUPLICATE, RSQL_ERR_UNSUPPORTED_SQL, 0xDBu);
    expect_affected(SQL_UPDATE_VARIABLE, 0u, 0xDCu);
    exec_expect(SQL_UPDATE_BAD, RSQL_ERR_SYNTAX, 0xDDu);

    TEST_STAGE = 0xE0u;
    exec_expect(SQL_CREATE_UPDATE_MEASURE, RSQL_OK, 0xE0u);
    exec_expect(SQL_INSERT_UPDATE_MEASURE1, RSQL_OK, 0xE1u);
    exec_expect(SQL_INSERT_UPDATE_MEASURE2, RSQL_OK, 0xE2u);
    expect_affected(SQL_UPDATE_MEASURE, 2u, 0xE3u);
    update_writes = rsql_journal_test_write_count();
    if (update_writes == 0u || update_writes == 0xFFu) fail(0xE4u);

    exec_expect(SQL_CREATE_UPDATE_ROLL, RSQL_OK, 0xE5u);
    exec_expect(SQL_INSERT_UPDATE_ROLL1, RSQL_OK, 0xE6u);
    exec_expect(SQL_INSERT_UPDATE_ROLL2, RSQL_OK, 0xE7u);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < update_writes; ++fail_index) {
        TEST_STAGE = (unsigned char)(0xE8u + fail_index);
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_UPDATE_ROLL, RSQL_ERR_IO, 0xE8u);
        expect_count(SQL_COUNT_UPDATE_ROLL_OLD, 2u, 0xE9u);
        expect_count(SQL_COUNT_UPDATE_ROLL_NEW, 0u, 0xEAu);
        if (first_free_page() != expected_free) fail(0xEBu);
    }
    expect_affected(SQL_UPDATE_ROLL, 2u, 0xECu);
    expect_count(SQL_COUNT_UPDATE_ROLL_OLD, 0u, 0xEDu);
    expect_count(SQL_COUNT_UPDATE_ROLL_NEW, 2u, 0xEEu);

    TEST_STAGE = 0x20u;
    exec_expect(SQL_CREATE_ENUM8, RSQL_OK, 0x20u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_enum_find("MOOD", &enum_info);
    if (rc != RSQL_OK || enum_info.width != 1u ||
        enum_info.member_count != 3u) fail(rc ? rc : 0x21u);
    rc = rsql_enum_member_value(enum_info.enum_id, "HAPPY", &enum_value);
    if (rc != RSQL_OK || enum_value != 7u) fail(rc ? rc : 0x22u);
    mood_id = enum_info.enum_id;
    exec_expect(SQL_CREATE_ENUM16, RSQL_OK, 0x23u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_enum_find("BIGCODE", &enum_info);
    if (rc != RSQL_OK || enum_info.width != 2u ||
        enum_info.member_count != 2u) fail(rc ? rc : 0x24u);
    rc = rsql_enum_member_value(enum_info.enum_id, "HIGH", &enum_value);
    if (rc != RSQL_OK || enum_value != 300u) fail(rc ? rc : 0x25u);
    bigcode_id = enum_info.enum_id;
    exec_expect(SQL_CREATE_ENUM8, RSQL_ERR_ALREADY_EXISTS, 0x26u);
    exec_expect(SQL_CREATE_ENUM_DUP_VALUE, RSQL_ERR_ALREADY_EXISTS, 0x27u);
    exec_expect(SQL_CREATE_ENUM_RANGE, RSQL_ERR_TYPE_MISMATCH, 0x28u);
    exec_expect(SQL_CREATE_ENUM_BAD, RSQL_ERR_SYNTAX, 0x29u);

    exec_expect(SQL_CREATE_ENUM_MEASURE, RSQL_OK, 0x2Au);
    enum_writes = rsql_journal_test_write_count();
    if (enum_writes == 0u || enum_writes == 0xFFu) fail(0x2Bu);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < enum_writes; ++fail_index) {
        TEST_STAGE = (unsigned char)(0x30u + fail_index);
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_CREATE_ENUM_FAIL, RSQL_ERR_IO, 0x30u);
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) rc = rsql_enum_find("EFAIL", &enum_info);
        if (rc != RSQL_ERR_NOT_FOUND) fail(rc ? rc : 0x31u);
        if (first_free_page() != expected_free) fail(0x32u);
    }
    exec_expect(SQL_CREATE_ENUM_FAIL, RSQL_OK, 0x33u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_enum_find("EFAIL", &enum_info);
    if (rc != RSQL_OK || enum_info.member_count != 3u) {
        fail(rc ? rc : 0x34u);
    }

    TEST_STAGE = 0x40u;
    exec_expect(SQL_CREATE_ENUM_TABLE, RSQL_OK, 0x40u);
    TEST_STAGE = 0x41u;
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("EDATA", &enum_table);
    if (rc == RSQL_OK) {
        rc = rsql_column_info(enum_table.table_page, 1u, &enum_column);
    }
    if (rc != RSQL_OK || enum_column.type.tag != RSQL_TYPE_ENUM8 ||
        enum_column.type.auxiliary != mood_id) {
        TEST_RC = rc;
        TEST_ACTUAL = enum_column.type.tag;
        TEST_EXPECTED = RSQL_TYPE_ENUM8;
        fail(rc ? rc : 0x41u);
    }
    TEST_STAGE = 0x42u;
    rc = rsql_column_info(enum_table.table_page, 2u, &enum_column);
    if (rc != RSQL_OK || enum_column.type.tag != RSQL_TYPE_ENUM16 ||
        enum_column.type.auxiliary != bigcode_id ||
        !(enum_column.type.flags & RSQL_TYPE_FLAG_NULLABLE)) {
        TEST_RC = rc;
        TEST_ACTUAL = enum_column.type.tag;
        TEST_EXPECTED = RSQL_TYPE_ENUM16;
        fail(rc ? rc : 0x42u);
    }
    exec_expect(SQL_CREATE_UNKNOWN_ENUM_TABLE, RSQL_ERR_NOT_FOUND, 0x43u);
    exec_expect(SQL_INSERT_ENUM1, RSQL_OK, 0x44u);
    exec_expect(SQL_INSERT_ENUM2, RSQL_OK, 0x45u);
    expect_count(SQL_COUNT_ENUM_HAPPY, 1u, 0x46u);
    expect_count(SQL_COUNT_ENUM_HIGH, 1u, 0x47u);
    expect_enum_row(7u, 300u, 0x48u);
    expect_affected(SQL_UPDATE_ENUM, 1u, 0x49u);
    expect_count(SQL_COUNT_ENUM_HAPPY, 0u, 0x4Au);
    expect_count(SQL_COUNT_ENUM_OK, 1u, 0x4Bu);
    expect_count(SQL_COUNT_ENUM_HIGH, 0u, 0x4Cu);
    expect_enum_row(2u, 1u, 0x4Du);
    exec_expect(SQL_INSERT_ENUM_MISSING, RSQL_ERR_NOT_FOUND, 0x4Eu);
    exec_expect(SQL_INSERT_ENUM_WRONG, RSQL_ERR_TYPE_MISMATCH, 0x4Fu);
    exec_expect(SQL_INSERT_ENUM_NONENUM, RSQL_ERR_TYPE_MISMATCH, 0x50u);
    exec_expect(SQL_INSERT_ENUM8_RANGE, RSQL_ERR_TYPE_MISMATCH, 0x51u);
    exec_expect(SQL_INSERT_ENUM16_RANGE, RSQL_ERR_TYPE_MISMATCH, 0x52u);
    open_expect(SQL_SELECT_ENUM_WRONG, RSQL_ERR_TYPE_MISMATCH, 0x53u);
    exec_expect(SQL_UPDATE_ENUM_MISSING, RSQL_ERR_NOT_FOUND, 0x54u);
    expect_enum_row(2u, 1u, 0x55u);

    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

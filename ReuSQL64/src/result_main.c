#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"
#include "rsql_query.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_DIAG0 (*(volatile unsigned char*)0xCFF3)
#define TEST_DIAG1 (*(volatile unsigned char*)0xCFF4)
#define TEST_DIAG2 (*(volatile unsigned char*)0xCFF5)
#define TEST_DIAG3 (*(volatile unsigned char*)0xCFF6)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_ENUM[] =
    "CREATE TYPE RANKING AS ENUM16 (LOW=1,HIGH=60000)";
static const char SQL_TABLE[] =
    "CREATE TABLE SRT (ID I16,CODE I8,NAME CHAR(8),ACTIVE BOOLEAN,"
    "SCORE I32 NULL,KIND RANKING,VALUE FLOAT NULL)";
static const char* const INSERTS[] = {
    "INSERT INTO SRT VALUES (4,-1,'beta',TRUE,NULL,RANKING.HIGH,1.5)",
    "INSERT INTO SRT VALUES (1,127,'Alpha',FALSE,30,RANKING.LOW,-0.75)",
    "INSERT INTO SRT VALUES (3,-128,'alpha',TRUE,20,RANKING.HIGH,2.25)",
    "INSERT INTO SRT VALUES (2,0,'Gamma',FALSE,20,RANKING.LOW,1.5)",
    "INSERT INTO SRT VALUES (5,10,'Beta',TRUE,20,RANKING.HIGH,NULL)"
};

static const char SQL_ASC[] =
    "SELECT ID FROM SRT ORDER BY ID";
static const char SQL_DESC[] =
    "SELECT ID FROM SRT ORDER BY ID DESC";
static const char SQL_NULL_ASC[] =
    "SELECT ID FROM SRT ORDER BY SCORE ASC, ID DESC";
static const char SQL_NULL_DESC[] =
    "SELECT ID FROM SRT ORDER BY SCORE DESC,ID";
static const char SQL_CHAR[] =
    "SELECT ID FROM SRT ORDER BY NAME ASC,ID";
static const char SQL_SIGNED_I8[] =
    "SELECT ID FROM SRT ORDER BY CODE";
static const char SQL_FLOAT[] =
    "SELECT ID FROM SRT ORDER BY VALUE ASC,ID DESC";
static const char SQL_FILTER_LIMIT[] =
    "SELECT ID FROM SRT WHERE ACTIVE=TRUE AND NAME NOT LIKE 'G%' "
    "ORDER BY ID DESC LIMIT 2 OFFSET 1";
static const char SQL_LIMIT_OFFSET[] =
    "SELECT ID FROM SRT ORDER BY ID LIMIT 2 OFFSET 1";
static const char SQL_OFFSET_LIMIT[] =
    "SELECT ID FROM SRT ORDER BY ID OFFSET 2 LIMIT 2";
static const char SQL_LIMIT_ZERO[] =
    "SELECT ID FROM SRT ORDER BY ID LIMIT 0";
static const char SQL_OFFSET_ONLY[] =
    "SELECT ID FROM SRT OFFSET 3";
static const char SQL_QUALIFIED[] =
    "SELECT S.ID FROM SRT AS S ORDER BY s.ID DESC LIMIT 1";
static const char SQL_DISTINCT_NAME[] =
    "SELECT DISTINCT NAME FROM SRT ORDER BY NAME";
static const char SQL_DISTINCT_BOOL[] =
    "SELECT DISTINCT ACTIVE FROM SRT ORDER BY ACTIVE DESC";
static const char SQL_DISTINCT_ENUM[] =
    "SELECT DISTINCT KIND FROM SRT ORDER BY KIND DESC";
static const char SQL_DISTINCT_SHAPED[] =
    "SELECT DISTINCT SCORE FROM SRT WHERE SCORE IS NOT NULL "
    "ORDER BY SCORE DESC LIMIT 1 OFFSET 1";
static const char SQL_DUP_ORDER[] =
    "SELECT ID FROM SRT ORDER BY ID, ID";
static const char SQL_BAD_ORDER[] =
    "SELECT ID FROM SRT ORDER BY MISSING";
static const char SQL_TEXT_TABLE[] =
    "CREATE TABLE T (BODY TEXT NULL,RAW BLOB NULL)";
static const char SQL_TEXT_INSERT[] =
    "INSERT INTO T VALUES ('payload',X'02FF')";
static const char SQL_TEXT_INSERT_NULL[] =
    "INSERT INTO T VALUES (NULL,NULL)";
static const char SQL_TEXT_INSERT_DUPLICATE[] =
    "INSERT INTO T VALUES ('PAYLOAD',X'02FF')";
static const char SQL_TEXT_DISTINCT[] =
    "SELECT DISTINCT BODY,RAW FROM T WHERE BODY LIKE'p%' AND RAW=X'02FF' "
    "ORDER BY RAW,BODY LIMIT 1";
static const char SQL_TEXT_SCALARS[] =
    "SELECT LENGTH(BODY),SUBSTR(BODY,2,3),BODY||'!',BODY||BODY,'<'||BODY "
    "FROM T";
static const char SQL_SCALARS[] =
    "SELECT LENGTH(NAME),SUBSTR(NAME,2,3),SUBSTRING(NAME,5),NAME||'!',"
    "CONCAT('<',NAME),NAME||NAME,'A'||'B','solo' "
    "FROM SRT WHERE ID=1 LIMIT 1";
static const char SQL_SCALAR_NULL_TABLE[] =
    "CREATE TABLE N (NAME CHAR(8) NULL)";
static const char SQL_SCALAR_NULL_INSERT[] =
    "INSERT INTO N VALUES (NULL)";
static const char SQL_SCALAR_NULL[] =
    "SELECT LENGTH(NAME),SUBSTR(NAME,1,2),NAME||'X' FROM N";
static const char SQL_SCALAR_BAD_TYPE[] =
    "SELECT LENGTH(ID) FROM SRT";
static const char SQL_SCALAR_BAD_START[] =
    "SELECT SUBSTR(NAME,0,2) FROM SRT";
static const char SQL_SCALAR_BAD_CONCAT[] =
    "SELECT NAME||ID FROM SRT";
static const char SQL_SCALAR_DISTINCT[] =
    "SELECT DISTINCT LENGTH(BODY),SUBSTR(BODY,2,3),BODY||'!',BODY||BODY,"
    "'<'||BODY FROM T WHERE BODY LIKE'p%'ORDER BY 1,2";

static const signed int IDS_ASC[] = {1, 2, 3, 4, 5};
static const signed int IDS_DESC[] = {5, 4, 3, 2, 1};
static const signed int IDS_NULL_ASC[] = {4, 5, 3, 2, 1};
static const signed int IDS_NULL_DESC[] = {1, 2, 3, 5, 4};
static const signed int IDS_CHAR[] = {1, 3, 4, 5, 2};
static const signed int IDS_I8[] = {3, 4, 2, 5, 1};
static const signed int IDS_FLOAT[] = {5, 1, 4, 2, 3};
static const signed int IDS_FILTER_LIMIT[] = {4, 3};
static const signed int IDS_LIMIT_OFFSET[] = {2, 3};
static const signed int IDS_OFFSET_LIMIT[] = {3, 4};
static const signed int IDS_OFFSET_ONLY[] = {2, 5};
static const signed int IDS_QUALIFIED[] = {5};
static RsqlQueryOpenRequest g_open_request;
static RsqlCursorNextRequest g_next_request;

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static void exec_ok(const char* sql, unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_DIAG0 = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static unsigned char open_rc(const char* sql, RsqlQueryOpenRequest* request) {
    request->sql = sql;
    request->sql_length = strlen(sql);
    return rsql_query_open(request);
}

static RsqlCursorHandle open_query(const char* sql, unsigned char columns,
                                   unsigned char stage) {
    unsigned char rc;
    TEST_DIAG0 = stage;
    rc = open_rc(sql, &g_open_request);
    if (rc != RSQL_OK || g_rsql_cursor.result_column_count != columns) {
        TEST_DIAG1 = rc;
        TEST_DIAG2 = g_rsql_cursor.result_column_count;
        TEST_DIAG3 = columns;
        fail(rc ? rc : stage);
    }
    return 1u;
}

static void close_query(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest request;
    unsigned char rc;
    TEST_DIAG0 = stage;
    (void)cursor;
    request.cursor = 1u;
    rc = rsql_query_close(&request);
    if (rc != RSQL_OK) {
        TEST_DIAG1 = rc;
        TEST_DIAG2 = request.cursor;
        TEST_DIAG3 = cursor;
        fail(rc ? rc : stage);
    }
}

static unsigned char next_row(RsqlCursorHandle cursor, unsigned char stage) {
    unsigned char rc;
    TEST_DIAG0 = stage;
    (void)cursor;
    g_next_request.cursor = 1u;
    rc = rsql_cursor_next(&g_next_request);
    if (rc != RSQL_OK) {
        TEST_DIAG1 = rc;
        TEST_DIAG2 = g_next_request.cursor;
        TEST_DIAG3 = g_rsql_cursor.active;
        fail(rc);
    }
    return g_next_request.has_row;
}

static void column_value(RsqlCursorHandle cursor, unsigned char column,
                         unsigned char stage, RsqlValueInfo* value) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    (void)cursor;
    request.cursor = 1u;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    memcpy(value, &request.value, sizeof(*value));
}

static void expect_i16(RsqlCursorHandle cursor, signed int expected,
                       unsigned char stage) {
    RsqlValueInfo value;
    column_value(cursor, 0u, stage, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_I16 ||
        value.length != 2u || value.bytes[0] != (unsigned char)expected ||
        value.bytes[1] != (unsigned char)((unsigned int)expected >> 8u)) {
        TEST_DIAG1 = value.type.tag;
        TEST_DIAG2 = value.length;
        TEST_DIAG3 = value.bytes[0];
        fail(stage);
    }
}

static void expect_ids(const char* sql, const signed int* expected,
                       unsigned char count, unsigned char stage) {
    RsqlCursorHandle cursor = open_query(sql, 1u, stage);
    unsigned char index;
    TEST_DIAG0 = stage;
    for (index = 0u; index < count; ++index) {
        TEST_DIAG1 = index;
        if (!next_row(cursor, stage)) {
            TEST_DIAG2 = count;
            TEST_DIAG3 = index;
            fail(0xE0u);
        }
        expect_i16(cursor, expected[index], stage);
    }
    if (next_row(cursor, stage)) fail(stage);
    close_query(cursor, stage);
}

static void expect_char8(RsqlCursorHandle cursor, const char* expected,
                         unsigned char stage) {
    RsqlValueReadRequest request;
    unsigned char text[8];
    unsigned char rc;
    request.cursor = cursor;
    request.column = 0u;
    request.offset = 0u;
    request.destination = text;
    request.capacity = sizeof(text);
    rc = rsql_value_read(&request);
    if (rc != RSQL_OK || request.bytes_read != sizeof(text) ||
        memcmp(text, expected, sizeof(text)) != 0) fail(rc ? rc : stage);
}

static void expect_scalar_char(RsqlCursorHandle cursor, unsigned char column,
                               const char* expected, unsigned int declared,
                               unsigned char stage) {
    RsqlValueInfo value;
    RsqlValueReadRequest request;
    unsigned char text[20];
    unsigned int length = strlen(expected);
    unsigned char prefix = length > sizeof(value.bytes)
        ? sizeof(value.bytes) : (unsigned char)length;
    unsigned char rc;
    column_value(cursor, column, stage, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_CHAR ||
        value.type.parameter != declared || value.length != length ||
        memcmp(value.bytes, expected, prefix) != 0) {
        TEST_DIAG1 = value.type.tag;
        TEST_DIAG2 = (unsigned char)value.length;
        TEST_DIAG3 = (unsigned char)declared;
        fail(stage);
    }
    request.cursor = cursor;
    request.column = column;
    request.offset = 0u;
    request.destination = text;
    request.capacity = sizeof(text);
    rc = rsql_value_read(&request);
    if (rc != RSQL_OK || request.bytes_read != length ||
        memcmp(text, expected, length) != 0) fail(rc ? rc : stage);
}

static void test_string_scalars(void) {
    RsqlCursorHandle cursor;
    RsqlValueInfo value;
    RsqlValueReadRequest read;
    unsigned char slice[4];
    unsigned char rc;
    unsigned char column;
    cursor = open_query(SQL_SCALARS, 8u, 0x60u);
    if (!next_row(cursor, 0x61u)) fail(0x61u);
    column_value(cursor, 0u, 0x62u, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_I16 ||
        value.length != 2u || value.bytes[0] != 5u || value.bytes[1] != 0u) {
        fail(0x62u);
    }
    expect_scalar_char(cursor, 1u, "lph", 3u, 0x63u);
    expect_scalar_char(cursor, 2u, "a", 4u, 0x64u);
    expect_scalar_char(cursor, 3u, "Alpha!", 9u, 0x65u);
    expect_scalar_char(cursor, 4u, "<Alpha", 9u, 0x66u);
    expect_scalar_char(cursor, 5u, "AlphaAlpha", 16u, 0x67u);
    expect_scalar_char(cursor, 6u, "AB", 2u, 0x68u);
    expect_scalar_char(cursor, 7u, "solo", 4u, 0x69u);
    read.cursor = cursor;
    read.column = 5u;
    read.offset = 4u;
    read.destination = slice;
    read.capacity = sizeof(slice);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != sizeof(slice) ||
        memcmp(slice, "aAlp", sizeof(slice)) != 0) fail(rc ? rc : 0x6Au);
    if (next_row(cursor, 0x6Bu)) fail(0x6Bu);
    close_query(cursor, 0x6Cu);

    exec_ok(SQL_SCALAR_NULL_TABLE, 0x6Du);
    exec_ok(SQL_SCALAR_NULL_INSERT, 0x6Eu);
    cursor = open_query(SQL_SCALAR_NULL, 3u, 0x6Fu);
    if (!next_row(cursor, 0x70u)) fail(0x70u);
    for (column = 0u; column < 3u; ++column) {
        column_value(cursor, column, (unsigned char)(0x71u + column), &value);
        if (!value.is_null || (column != 0u && value.length != 0u)) {
            fail((unsigned char)(0x71u + column));
        }
    }
    close_query(cursor, 0x74u);
}

static void expect_scalar_text(RsqlCursorHandle cursor, unsigned char column,
                               const char* expected, unsigned char stage) {
    RsqlValueInfo value;
    RsqlValueReadRequest read;
    unsigned char bytes[16];
    unsigned int length = strlen(expected);
    unsigned char rc;
    column_value(cursor, column, stage, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_TEXT ||
        value.length != length) fail(stage);
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length ||
        memcmp(bytes, expected, length) != 0) fail(rc ? rc : stage);
}

static void test_text_scalars(void) {
    RsqlCursorHandle cursor;
    RsqlValueInfo value;
    unsigned char column;
    exec_ok(SQL_TEXT_TABLE, 0x75u);
    exec_ok(SQL_TEXT_INSERT, 0x76u);
    exec_ok(SQL_TEXT_INSERT_NULL, 0x77u);
    cursor = open_query(SQL_TEXT_SCALARS, 5u, 0x78u);
    if (!next_row(cursor, 0x79u)) fail(0x79u);
    column_value(cursor, 0u, 0x7Au, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_I32 ||
        value.length != 4u || value.bytes[0] != 7u ||
        value.bytes[1] != 0u || value.bytes[2] != 0u ||
        value.bytes[3] != 0u) fail(0x7Au);
    expect_scalar_text(cursor, 1u, "ayl", 0x7Bu);
    expect_scalar_text(cursor, 2u, "payload!", 0x7Cu);
    expect_scalar_text(cursor, 3u, "payloadpayload", 0x7Du);
    expect_scalar_text(cursor, 4u, "<payload", 0x7Eu);
    if (!next_row(cursor, 0x7Fu)) fail(0x7Fu);
    for (column = 0u; column < 5u; ++column) {
        column_value(cursor, column, (unsigned char)(0x50u + column), &value);
        if (!value.is_null || (column != 0u && value.length != 0u)) {
            fail((unsigned char)(0x50u + column));
        }
    }
    if (next_row(cursor, 0x55u)) fail(0x55u);
    close_query(cursor, 0x56u);

}

static void test_text_shaping(void) {
    RsqlCursorHandle cursor;
    exec_ok(SQL_TEXT_INSERT_DUPLICATE, 0xD4u);
    cursor = open_query(SQL_TEXT_DISTINCT, 2u, 0xDEu);
    if (!next_row(cursor, 0xDFu)) fail(0xDFu);
    expect_scalar_text(cursor, 0u, "payload", 0xE2u);
    if (next_row(cursor, 0xE3u)) fail(0xE3u);
    close_query(cursor, 0xE4u);

    cursor = open_query(SQL_SCALAR_DISTINCT, 5u, 0xE5u);
    if (!next_row(cursor, 0xE6u)) fail(0xE6u);
    expect_scalar_text(cursor, 1u, "ayl", 0xE7u);
    if (next_row(cursor, 0xE8u)) fail(0xE8u);
    close_query(cursor, 0xE9u);
}

static void test_distinct(void) {
    RsqlCursorHandle cursor;
    RsqlValueInfo value;
    cursor = open_query(SQL_DISTINCT_NAME, 1u, 0xB0u);
    if (!next_row(cursor, 0xB1u)) fail(0xB1u);
    expect_char8(cursor, "Alpha   ", 0xB2u);
    if (!next_row(cursor, 0xB3u)) fail(0xB3u);
    expect_char8(cursor, "beta    ", 0xB4u);
    if (!next_row(cursor, 0xB5u)) fail(0xB5u);
    expect_char8(cursor, "Gamma   ", 0xB6u);
    if (next_row(cursor, 0xB7u)) fail(0xB7u);
    close_query(cursor, 0xB8u);

    cursor = open_query(SQL_DISTINCT_BOOL, 1u, 0xB9u);
    if (!next_row(cursor, 0xBAu)) fail(0xBAu);
    column_value(cursor, 0u, 0xBBu, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_BOOLEAN ||
        value.bytes[0] != 1u) fail(0xBBu);
    if (!next_row(cursor, 0xBCu)) fail(0xBCu);
    column_value(cursor, 0u, 0xBDu, &value);
    if (value.is_null || value.bytes[0] != 0u) fail(0xBDu);
    if (next_row(cursor, 0xBEu)) fail(0xBEu);
    close_query(cursor, 0xBFu);

    cursor = open_query(SQL_DISTINCT_ENUM, 1u, 0xC0u);
    if (!next_row(cursor, 0xC1u)) fail(0xC1u);
    column_value(cursor, 0u, 0xC2u, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_ENUM16 ||
        value.bytes[0] != 0x60u || value.bytes[1] != 0xEAu) fail(0xC2u);
    if (!next_row(cursor, 0xC3u)) fail(0xC3u);
    column_value(cursor, 0u, 0xC4u, &value);
    if (value.bytes[0] != 1u || value.bytes[1] != 0u) fail(0xC4u);
    if (next_row(cursor, 0xC5u)) fail(0xC5u);
    close_query(cursor, 0xC6u);

    cursor = open_query(SQL_DISTINCT_SHAPED, 1u, 0xC7u);
    if (!next_row(cursor, 0xC8u)) fail(0xC8u);
    column_value(cursor, 0u, 0xC9u, &value);
    if (value.is_null || value.type.tag != RSQL_TYPE_I32 ||
        value.bytes[0] != 20u || value.bytes[1] != 0u ||
        value.bytes[2] != 0u || value.bytes[3] != 0u) fail(0xC9u);
    if (next_row(cursor, 0xCAu)) fail(0xCAu);
    close_query(cursor, 0xCBu);
}

static void test_rejections(void) {
    RsqlQueryOpenRequest request;
    unsigned char rc;
    rc = open_rc(SQL_DUP_ORDER, &request);
    if (rc != RSQL_ERR_UNSUPPORTED_SQL) fail(rc ? rc : 0xD0u);
    rc = open_rc(SQL_BAD_ORDER, &request);
    if (rc != RSQL_ERR_NOT_FOUND) fail(rc ? rc : 0xD1u);
    rc = open_rc(SQL_SCALAR_BAD_TYPE, &request);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xD6u);
    rc = open_rc(SQL_SCALAR_BAD_START, &request);
    if (rc != RSQL_ERR_SYNTAX) fail(rc ? rc : 0xD7u);
    rc = open_rc(SQL_SCALAR_BAD_CONCAT, &request);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xD8u);
}

int main(void) {
    RsqlInitRequest init;
    unsigned char index;
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
    exec_ok(SQL_ENUM, 0x81u);
    exec_ok(SQL_TABLE, 0x82u);
    for (index = 0u; index < sizeof(INSERTS) / sizeof(INSERTS[0]); ++index) {
        exec_ok(INSERTS[index], (unsigned char)(0x83u + index));
    }
    expect_ids(SQL_ASC, IDS_ASC, 5u, 0x90u);
    expect_ids(SQL_DESC, IDS_DESC, 5u, 0x91u);
    expect_ids(SQL_NULL_ASC, IDS_NULL_ASC, 5u, 0x92u);
    expect_ids(SQL_NULL_DESC, IDS_NULL_DESC, 5u, 0x93u);
    expect_ids(SQL_CHAR, IDS_CHAR, 5u, 0x94u);
    expect_ids(SQL_SIGNED_I8, IDS_I8, 5u, 0x95u);
    expect_ids(SQL_FLOAT, IDS_FLOAT, 5u, 0x96u);
    expect_ids(SQL_FILTER_LIMIT, IDS_FILTER_LIMIT, 2u, 0x97u);
    expect_ids(SQL_LIMIT_OFFSET, IDS_LIMIT_OFFSET, 2u, 0x98u);
    expect_ids(SQL_OFFSET_LIMIT, IDS_OFFSET_LIMIT, 2u, 0x99u);
    expect_ids(SQL_LIMIT_ZERO, IDS_ASC, 0u, 0x9Au);
    expect_ids(SQL_OFFSET_ONLY, IDS_OFFSET_ONLY, 2u, 0x9Bu);
    expect_ids(SQL_QUALIFIED, IDS_QUALIFIED, 1u, 0x9Cu);
    test_distinct();
    test_string_scalars();
    test_text_scalars();
    test_text_shaping();
    test_rejections();
    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail(rc);
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

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

static const char SQL_CREATE[] =
    "CREATE TABLE A(R CHAR(4),M I16 NULL,T TEXT NULL)";
static const char SQL_CREATE_EMPTY[] =
    "CREATE TABLE E(AMOUNT I16 NULL)";
static const char SQL_INSERT1[] = "INSERT INTO A VALUES('N',10,'N')";
static const char SQL_INSERT2[] = "INSERT INTO A VALUES('N',20,'NO')";
static const char SQL_INSERT3[] = "INSERT INTO A VALUES('S',-5,'S')";
static const char SQL_INSERT4[] = "INSERT INTO A VALUES('S',NULL,'S')";
static const char SQL_INSERT5[] = "INSERT INTO A VALUES('E',NULL,NULL)";
static const char SQL_INSERT6[] = "INSERT INTO A VALUES('N',10,'N')";
static const char SQL_AGGREGATES[] =
    "SELECT DISTINCT COUNT(*),COUNT(M),SUM(M),AVG(M),"
    "MIN(M),MAX(M)FROM A ORDER BY 3 DESC";
static const char SQL_VARIABLE_AGGREGATES[] =
    "SELECT COUNT(*),SUM(M)FROM A WHERE T LIKE'N%'";
static const char SQL_VARIABLE_GROUPED[] =
    "SELECT R,COUNT(*),SUM(M)FROM A WHERE T LIKE'%' GROUP BY R";
static const char SQL_GROUPED[] =
    "SELECT DISTINCT R,COUNT(*),COUNT(M),SUM(M),AVG(M),"
    "MIN(M),MAX(M)FROM A GROUP BY R ORDER BY 4 DESC";
static const char SQL_GROUPED_WHERE[] =
    "SELECT R,SUM(M)FROM A "
    "WHERE M IS NOT NULL GROUP BY R ORDER BY R DESC";
static const char SQL_COMPOUND_GROUP[] =
    "SELECT R,M,COUNT(*)FROM A GROUP BY R,M";
static const char SQL_GROUPED_LIMIT[] =
    "SELECT R,COUNT(*)FROM A GROUP BY R "
    "ORDER BY 2 DESC LIMIT 1 OFFSET 1";
static const char SQL_AGGREGATE_LIMIT_ZERO[] =
    "SELECT COUNT(*)FROM A LIMIT 0";
static const char SQL_SCALAR_ORDER[] =
    "SELECT SUBSTR(R,1,1)FROM A ORDER BY 1";
static const char SQL_SCALAR_DISTINCT[] =
    "SELECT DISTINCT R||'!'FROM A ORDER BY 1 DESC";
static const char SQL_BAD_ORDER_ORDINAL[] =
    "SELECT R FROM A ORDER BY 0";
static const char SQL_BAD_AGGREGATE[] =
    "SELECT R,SUM(M)FROM A";
static const char SQL_GROUP_DISTINCT[] =
    "SELECT DISTINCT R FROM A GROUP BY R,M";
static const char SQL_HAVING[] =
    "SELECT R,COUNT(*)FROM A GROUP BY R HAVING COUNT(*)>1";
static const char SQL_EMPTY_AGGREGATES[] =
    "SELECT COUNT(*),COUNT(AMOUNT),SUM(AMOUNT),AVG(AMOUNT),"
    "MIN(AMOUNT),MAX(AMOUNT)FROM E";
static const char SQL_CREATE_FLOAT[] =
    "CREATE TABLE F(REGION CHAR(2),VALUE FLOAT NULL)";
static const char SQL_FLOAT_INSERT1[] =
    "INSERT INTO F VALUES('A',1.5)";
static const char SQL_FLOAT_INSERT2[] =
    "INSERT INTO F VALUES('A',2.25)";
static const char SQL_FLOAT_INSERT3[] =
    "INSERT INTO F VALUES('B',-0.75)";
static const char SQL_FLOAT_INSERT4[] =
    "INSERT INTO F VALUES('B',NULL)";
static const char SQL_FLOAT_INSERT5[] =
    "INSERT INTO F VALUES('A',2)";
static const char SQL_FLOAT_AGGREGATES[] =
    "SELECT COUNT(*),COUNT(VALUE),SUM(VALUE),AVG(VALUE),"
    "MIN(VALUE),MAX(VALUE)FROM F";
static const char SQL_FLOAT_ALL[] = "SELECT VALUE FROM F";
static const char SQL_FLOAT_GROUPED[] =
    "SELECT REGION,COUNT(VALUE),SUM(VALUE),MIN(VALUE),MAX(VALUE)"
    "FROM F GROUP BY REGION ORDER BY 3 DESC";
static const char SQL_FLOAT_FILTER[] =
    "SELECT VALUE FROM F WHERE VALUE>=1.5 AND VALUE<2.25";
static const char SQL_FLOAT_UPDATE[] =
    "UPDATE F SET VALUE=3.5 WHERE VALUE=-0.75";
static const char SQL_FLOAT_UPDATED[] =
    "SELECT VALUE FROM F WHERE VALUE=3.5";
static const char SQL_FLOAT_TO_INTEGER[] =
    "UPDATE A SET M=1.5 WHERE R='N'";

static const unsigned char F_NEG_075[5] = { 0x80u, 0xC0u, 0u, 0u, 0u };
static const unsigned char F_125[5] = { 0x81u, 0x20u, 0u, 0u, 0u };
static const unsigned char F_15[5] = { 0x81u, 0x40u, 0u, 0u, 0u };
static const unsigned char F_2[5] = { 0x82u, 0u, 0u, 0u, 0u };
static const unsigned char F_225[5] = { 0x82u, 0x10u, 0u, 0u, 0u };
static const unsigned char F_35[5] = { 0x82u, 0x60u, 0u, 0u, 0u };
static const unsigned char F_5[5] = { 0x83u, 0x20u, 0u, 0u, 0u };
static const unsigned char F_575[5] = { 0x83u, 0x38u, 0u, 0u, 0u };
static const unsigned char SCALAR_ORDER_EXPECTED[] = {
    'E', 'N', 'N', 'N', 'S', 'S'
};
static const unsigned char SCALAR_DISTINCT_EXPECTED[][2] = {
    {'S', '!'}, {'N', '!'}, {'E', '!'}
};

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

static RsqlCursorHandle open_query(const char* sql, unsigned char columns,
                                   unsigned char stage) {
    RsqlQueryOpenRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_query_open(&request);
    if (rc != RSQL_OK || request.column_count != columns) {
        fail(rc ? rc : stage);
    }
    return request.cursor;
}

static void close_query(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest request;
    unsigned char rc;
    request.cursor = cursor;
    rc = rsql_query_close(&request);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static void expect_next(RsqlCursorHandle cursor, unsigned char has_row,
                        unsigned char stage) {
    RsqlCursorNextRequest request;
    unsigned char rc;
    request.cursor = cursor;
    rc = rsql_cursor_next(&request);
    if (rc != RSQL_OK || request.has_row != has_row) {
        TEST_DIAG0 = rc;
        TEST_DIAG1 = request.has_row;
        TEST_DIAG2 = has_row;
        TEST_DIAG3 = g_rsql_cursor.mode;
        fail(rc ? rc : stage);
    }
}

static void expect_i64(RsqlCursorHandle cursor, unsigned char column,
                       signed int expected, unsigned char is_null,
                       unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char fill;
    unsigned char index;
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u || request.value.is_null != is_null) {
        TEST_DIAG0 = g_rsql_cursor.aggregate_nulls;
        TEST_DIAG1 = g_rsql_cursor.aggregate_counts[column].bytes[0];
        TEST_DIAG2 = request.value.is_null;
        TEST_DIAG3 = g_rsql_cursor.projection_aggregate[column];
        fail(rc ? rc : stage);
    }
    if (is_null) return;
    fill = expected < 0 ? 0xFFu : 0u;
    if (request.value.bytes[0] != (unsigned char)expected ||
        request.value.bytes[1] !=
            (unsigned char)((unsigned int)expected >> 8u)) fail(stage);
    for (index = 2u; index < 8u; ++index) {
        if (request.value.bytes[index] != fill) fail(stage);
    }
}

static void expect_char4(RsqlCursorHandle cursor, unsigned char column,
                         const char* expected, unsigned char stage) {
    RsqlValueReadRequest request;
    unsigned char text[4];
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    request.offset = 0u;
    request.destination = text;
    request.capacity = sizeof(text);
    rc = rsql_value_read(&request);
    if (rc != RSQL_OK || request.bytes_read != sizeof(text) ||
        memcmp(text, expected, sizeof(text)) != 0) fail(rc ? rc : stage);
}

static void expect_float(RsqlCursorHandle cursor, unsigned char column,
                         const unsigned char* expected,
                         unsigned char is_null, unsigned char stage) {
    RsqlCursorColumnRequest request;
    RsqlValueReadRequest read;
    unsigned char bytes[5];
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.type.tag != RSQL_TYPE_FLOAT5 ||
        request.value.length != 5u || request.value.is_null != is_null) {
        TEST_DIAG0 = request.value.type.tag;
        TEST_DIAG1 = (unsigned char)request.value.length;
        TEST_DIAG2 = request.value.is_null;
        TEST_DIAG3 = rc;
        fail(rc ? rc : stage);
    }
    if (is_null) return;
    if (memcmp(request.value.bytes, expected, 5u) != 0) {
        TEST_DIAG0 = request.value.bytes[0];
        TEST_DIAG1 = request.value.bytes[1];
        TEST_DIAG2 = request.value.bytes[2];
        TEST_DIAG3 = request.value.bytes[3];
        fail(stage);
    }
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 5u ||
        memcmp(bytes, expected, 5u) != 0) fail(rc ? rc : stage);
}

static void expect_scalar(RsqlCursorHandle cursor, const unsigned char* expected,
                          unsigned char length, unsigned char declared,
                          unsigned char stage) {
    RsqlCursorColumnRequest column;
    RsqlValueReadRequest read;
    unsigned char bytes[4];
    unsigned char rc;
    column.cursor = cursor;
    column.column = 0u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_CHAR ||
        column.value.type.parameter != declared ||
        column.value.length != length) fail(rc ? rc : stage);
    read.cursor = cursor;
    read.column = 0u;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length ||
        memcmp(bytes, expected, length) != 0) fail(rc ? rc : stage);
}

static void test_scalar_shaping(void) {
    RsqlCursorHandle cursor;
    unsigned char index;
    cursor = open_query(SQL_SCALAR_ORDER, 1u, 0x10u);
    for (index = 0u; index < sizeof(SCALAR_ORDER_EXPECTED); ++index) {
        expect_next(cursor, 1u, 0x11u);
        expect_scalar(cursor, &SCALAR_ORDER_EXPECTED[index], 1u, 1u, 0x12u);
    }
    expect_next(cursor, 0u, 0x13u);
    close_query(cursor, 0x14u);

    cursor = open_query(SQL_SCALAR_DISTINCT, 1u, 0x15u);
    for (index = 0u; index < 3u; ++index) {
        expect_next(cursor, 1u, 0x16u);
        expect_scalar(cursor, SCALAR_DISTINCT_EXPECTED[index], 2u, 5u, 0x17u);
    }
    expect_next(cursor, 0u, 0x18u);
    close_query(cursor, 0x19u);
}

static void test_ungrouped(void) {
    RsqlCursorHandle cursor = open_query(SQL_AGGREGATES, 6u, 0xA8u);
    expect_next(cursor, 1u, 0xA9u);
    expect_i64(cursor, 0u, 6, 0u, 0xAAu);
    expect_i64(cursor, 1u, 4, 0u, 0xABu);
    expect_i64(cursor, 2u, 35, 0u, 0xACu);
    expect_i64(cursor, 3u, 8, 0u, 0xADu);
    expect_i64(cursor, 4u, -5, 0u, 0xE7u);
    expect_i64(cursor, 5u, 20, 0u, 0xE8u);
    expect_next(cursor, 0u, 0xAEu);
    close_query(cursor, 0xAFu);

    TEST_DIAG0 = 0x89u;
    cursor = open_query(SQL_VARIABLE_AGGREGATES, 2u, 0x8Au);
    expect_next(cursor, 1u, 0x8Bu);
    expect_i64(cursor, 0u, 3, 0u, 0x8Cu);
    expect_i64(cursor, 1u, 40, 0u, 0x8Du);
    expect_next(cursor, 0u, 0x8Eu);
    close_query(cursor, 0x8Fu);

    TEST_DIAG0 = 0x90u;
    cursor = open_query(SQL_VARIABLE_GROUPED, 3u, 0x90u);
    expect_next(cursor, 1u, 0x91u);
    expect_char4(cursor, 0u, "N   ", 0x92u);
    expect_i64(cursor, 1u, 3, 0u, 0x93u);
    expect_i64(cursor, 2u, 40, 0u, 0x94u);
    expect_next(cursor, 1u, 0x97u);
    expect_char4(cursor, 0u, "S   ", 0x98u);
    expect_i64(cursor, 1u, 2, 0u, 0x99u);
    expect_i64(cursor, 2u, -5, 0u, 0x9Au);
    expect_next(cursor, 0u, 0x95u);
    close_query(cursor, 0x96u);
}

static void test_grouped(void) {
    RsqlCursorHandle cursor = open_query(SQL_GROUPED, 7u, 0xB0u);
    expect_next(cursor, 1u, 0xB1u);
    expect_char4(cursor, 0u, "N   ", 0xB2u);
    expect_i64(cursor, 1u, 3, 0u, 0xB3u);
    expect_i64(cursor, 2u, 3, 0u, 0xB4u);
    expect_i64(cursor, 3u, 40, 0u, 0xB5u);
    expect_i64(cursor, 4u, 13, 0u, 0xB6u);
    expect_i64(cursor, 5u, 10, 0u, 0xE9u);
    expect_i64(cursor, 6u, 20, 0u, 0xEAu);
    expect_next(cursor, 1u, 0xB7u);
    expect_char4(cursor, 0u, "S   ", 0xB8u);
    expect_i64(cursor, 1u, 2, 0u, 0xB9u);
    expect_i64(cursor, 2u, 1, 0u, 0xBAu);
    expect_i64(cursor, 3u, -5, 0u, 0xBBu);
    expect_i64(cursor, 4u, -5, 0u, 0xBCu);
    expect_i64(cursor, 5u, -5, 0u, 0xEBu);
    expect_i64(cursor, 6u, -5, 0u, 0xECu);
    expect_next(cursor, 1u, 0xBDu);
    expect_char4(cursor, 0u, "E   ", 0xBEu);
    expect_i64(cursor, 1u, 1, 0u, 0xBFu);
    expect_i64(cursor, 2u, 0, 0u, 0xC0u);
    expect_i64(cursor, 3u, 0, 1u, 0xC1u);
    expect_i64(cursor, 4u, 0, 1u, 0xC2u);
    expect_i64(cursor, 5u, 0, 1u, 0xEDu);
    expect_i64(cursor, 6u, 0, 1u, 0xEEu);
    expect_next(cursor, 0u, 0xC3u);
    close_query(cursor, 0xC4u);
}

static void test_group_where_and_compound(void) {
    RsqlCursorHandle cursor = open_query(SQL_GROUPED_WHERE, 2u, 0xC5u);
    expect_next(cursor, 1u, 0xC6u);
    expect_char4(cursor, 0u, "S   ", 0xC7u);
    expect_i64(cursor, 1u, -5, 0u, 0xC8u);
    expect_next(cursor, 1u, 0xC9u);
    expect_char4(cursor, 0u, "N   ", 0xCAu);
    expect_i64(cursor, 1u, 40, 0u, 0xCBu);
    expect_next(cursor, 0u, 0xCCu);
    close_query(cursor, 0xCDu);

    cursor = open_query(SQL_COMPOUND_GROUP, 3u, 0xCEu);
    expect_next(cursor, 1u, 0xCFu);
    expect_char4(cursor, 0u, "N   ", 0xD0u);
    expect_i64(cursor, 2u, 2, 0u, 0xD1u);
    expect_next(cursor, 1u, 0xD2u);
    expect_i64(cursor, 2u, 1, 0u, 0xD3u);
    close_query(cursor, 0xD4u);

    cursor = open_query(SQL_GROUP_DISTINCT, 1u, 0xDAu);
    expect_next(cursor, 1u, 0xDBu);
    expect_char4(cursor, 0u, "N   ", 0xDCu);
    expect_next(cursor, 1u, 0xDDu);
    expect_char4(cursor, 0u, "S   ", 0xDEu);
    expect_next(cursor, 1u, 0xDFu);
    expect_char4(cursor, 0u, "E   ", 0xE0u);
    expect_next(cursor, 0u, 0xE1u);
    close_query(cursor, 0xE2u);
}

static void test_aggregate_limits(void) {
    RsqlCursorHandle cursor = open_query(SQL_GROUPED_LIMIT, 2u, 0x31u);
    expect_next(cursor, 1u, 0x32u);
    expect_char4(cursor, 0u, "S   ", 0x33u);
    expect_i64(cursor, 1u, 2, 0u, 0x34u);
    expect_next(cursor, 0u, 0x35u);
    close_query(cursor, 0x36u);

    cursor = open_query(SQL_AGGREGATE_LIMIT_ZERO, 1u, 0x37u);
    expect_next(cursor, 0u, 0x38u);
    close_query(cursor, 0x39u);
}

static void test_rejections(void) {
    RsqlQueryOpenRequest request;
    unsigned char rc;
    request.sql = SQL_BAD_AGGREGATE;
    request.sql_length = strlen(SQL_BAD_AGGREGATE);
    rc = rsql_query_open(&request);
    if (rc != RSQL_ERR_UNSUPPORTED_SQL) fail(rc ? rc : 0xD5u);
    request.sql = SQL_HAVING;
    request.sql_length = strlen(SQL_HAVING);
    rc = rsql_query_open(&request);
    if (rc != RSQL_ERR_SYNTAX) fail(rc ? rc : 0xD6u);
    request.sql = SQL_BAD_ORDER_ORDINAL;
    request.sql_length = strlen(SQL_BAD_ORDER_ORDINAL);
    rc = rsql_query_open(&request);
    if (rc != RSQL_ERR_SYNTAX) fail(rc ? rc : 0xD7u);
}

static void test_empty(void) {
    RsqlCursorHandle cursor = open_query(SQL_EMPTY_AGGREGATES, 6u, 0xF0u);
    expect_next(cursor, 1u, 0xF1u);
    expect_i64(cursor, 0u, 0, 0u, 0xF2u);
    expect_i64(cursor, 1u, 0, 0u, 0xF3u);
    expect_i64(cursor, 2u, 0, 1u, 0xF4u);
    expect_i64(cursor, 3u, 0, 1u, 0xF5u);
    expect_i64(cursor, 4u, 0, 1u, 0xF6u);
    expect_i64(cursor, 5u, 0, 1u, 0xF7u);
    expect_next(cursor, 0u, 0xF8u);
    close_query(cursor, 0xF9u);
}

static void test_float(void) {
    RsqlCursorHandle cursor;
    RsqlExecRequest execution;
    unsigned char rc;
    exec_ok(SQL_CREATE_FLOAT, 0x40u);
    exec_ok(SQL_FLOAT_INSERT1, 0x41u);
    exec_ok(SQL_FLOAT_INSERT2, 0x42u);
    exec_ok(SQL_FLOAT_INSERT3, 0x43u);
    exec_ok(SQL_FLOAT_INSERT4, 0x44u);
    exec_ok(SQL_FLOAT_INSERT5, 0x45u);

    cursor = open_query(SQL_FLOAT_ALL, 1u, 0x69u);
    expect_next(cursor, 1u, 0x6Au);
    expect_float(cursor, 0u, F_15, 0u, 0x6Bu);
    expect_next(cursor, 1u, 0x6Cu);
    expect_float(cursor, 0u, F_225, 0u, 0x6Du);
    expect_next(cursor, 1u, 0x6Eu);
    expect_float(cursor, 0u, F_NEG_075, 0u, 0x6Fu);
    expect_next(cursor, 1u, 0x70u);
    expect_float(cursor, 0u, F_15, 1u, 0x71u);
    expect_next(cursor, 1u, 0x72u);
    expect_float(cursor, 0u, F_2, 0u, 0x73u);
    close_query(cursor, 0x74u);

    cursor = open_query(SQL_FLOAT_AGGREGATES, 6u, 0x46u);
    expect_next(cursor, 1u, 0x47u);
    expect_i64(cursor, 0u, 5, 0u, 0x48u);
    expect_i64(cursor, 1u, 4, 0u, 0x49u);
    expect_float(cursor, 2u, F_5, 0u, 0x4Au);
    expect_float(cursor, 3u, F_125, 0u, 0x4Bu);
    expect_float(cursor, 4u, F_NEG_075, 0u, 0x4Cu);
    expect_float(cursor, 5u, F_225, 0u, 0x4Du);
    expect_next(cursor, 0u, 0x4Eu);
    close_query(cursor, 0x4Fu);

    cursor = open_query(SQL_FLOAT_GROUPED, 5u, 0x50u);
    expect_next(cursor, 1u, 0x51u);
    expect_i64(cursor, 1u, 3, 0u, 0x52u);
    expect_float(cursor, 2u, F_575, 0u, 0x53u);
    expect_float(cursor, 3u, F_15, 0u, 0x54u);
    expect_float(cursor, 4u, F_225, 0u, 0x55u);
    expect_next(cursor, 1u, 0x56u);
    expect_i64(cursor, 1u, 1, 0u, 0x57u);
    expect_float(cursor, 2u, F_NEG_075, 0u, 0x58u);
    expect_float(cursor, 3u, F_NEG_075, 0u, 0x59u);
    expect_float(cursor, 4u, F_NEG_075, 0u, 0x5Au);
    close_query(cursor, 0x5Bu);

    cursor = open_query(SQL_FLOAT_FILTER, 1u, 0x5Cu);
    expect_next(cursor, 1u, 0x5Du);
    expect_float(cursor, 0u, F_15, 0u, 0x5Eu);
    expect_next(cursor, 1u, 0x5Fu);
    expect_float(cursor, 0u, F_2, 0u, 0x60u);
    expect_next(cursor, 0u, 0x61u);
    close_query(cursor, 0x62u);

    exec_ok(SQL_FLOAT_UPDATE, 0x63u);
    cursor = open_query(SQL_FLOAT_UPDATED, 1u, 0x64u);
    expect_next(cursor, 1u, 0x65u);
    expect_float(cursor, 0u, F_35, 0u, 0x66u);
    close_query(cursor, 0x67u);

    execution.sql = SQL_FLOAT_TO_INTEGER;
    execution.sql_length = strlen(SQL_FLOAT_TO_INTEGER);
    rc = rsql_exec(&execution);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0x68u);
}

int main(void) {
    RsqlInitRequest init;
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
        fail(0xA0u);
    }
    exec_ok(SQL_CREATE, 0xA1u);
    exec_ok(SQL_CREATE_EMPTY, 0xFAu);
    exec_ok(SQL_INSERT1, 0xA2u);
    exec_ok(SQL_INSERT2, 0xA3u);
    exec_ok(SQL_INSERT3, 0xA4u);
    exec_ok(SQL_INSERT4, 0xA5u);
    exec_ok(SQL_INSERT5, 0xA6u);
    exec_ok(SQL_INSERT6, 0xA7u);
    test_ungrouped();
    test_grouped();
    test_group_where_and_compound();
    test_aggregate_limits();
    test_scalar_shaping();
    test_rejections();
    test_empty();
    test_float();
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

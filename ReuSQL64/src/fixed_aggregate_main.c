#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_DETAIL (*(volatile unsigned char*)0xCFF4)
#define TEST_DIAG0 (*(volatile unsigned char*)0xCFF5)
#define TEST_DIAG1 (*(volatile unsigned char*)0xCFF6)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char* const SETUP[] = {
    "CREATE TABLE F(R I8,V FIXED8_8 NULL)",
    "CREATE TABLE K(R I8)",
    "INSERT INTO F VALUES(1,1)",
    "INSERT INTO F VALUES(1,2)",
    "INSERT INTO F VALUES(2,-2)",
    "INSERT INTO F VALUES(2,NULL)",
    "INSERT INTO F VALUES(3,127)",
    "INSERT INTO F VALUES(3,127)",
    "INSERT INTO F VALUES(3,127)",
    "INSERT INTO K VALUES(1)",
    "INSERT INTO K VALUES(2)",
    "CREATE TABLE G(T TEXT NULL,B BLOB NULL,V I8)",
    "INSERT INTO G VALUES('a',X'0102',1)",
    "INSERT INTO G VALUES('A',X'0102',2)",
    "INSERT INTO G VALUES('b',X'01FF',3)",
    "INSERT INTO G VALUES(NULL,NULL,4)",
    "INSERT INTO G VALUES(NULL,NULL,5)",
    "CREATE INDEX I ON G (V)",
    "CREATE TABLE H(T TEXT,B BLOB)",
    "INSERT INTO H VALUES('a',X'0102')",
    "INSERT INTO H VALUES('A',X'0200')",
    "INSERT INTO H VALUES('b',X'01FF')",
    "CREATE TABLE Q(R I8)",
    "INSERT INTO Q VALUES(1)",
    "INSERT INTO Q VALUES(2)",
    "INSERT INTO Q VALUES(3)",
    "INSERT INTO Q VALUES(4)",
    "INSERT INTO Q VALUES(5)"
};

static const char SQL_ORDINARY[] =
    "SELECT COUNT(*),COUNT(V),SUM(V),AVG(V),MIN(V),MAX(V)"
    "FROM F WHERE R<3";
static const char SQL_GROUPED[] =
    "SELECT DISTINCT R,COUNT(V),SUM(V),AVG(V),MIN(V),MAX(V)"
    "FROM F WHERE R<3 GROUP BY R ORDER BY 3 DESC";
static const char SQL_JOINED[] =
    "SELECT COUNT(*),SUM(Y.V),AVG(Y.V),MIN(Y.V),MAX(Y.V)"
    "FROM K AS X JOIN F AS Y ON X.R=Y.R";
static const char SQL_CORRELATED[] =
    "SELECT SUM(O.V),AVG(O.V)FROM F AS O WHERE O.R<3 AND EXISTS"
    "(SELECT 1 FROM K AS X WHERE X.R=O.R)";
static const char SQL_EMPTY[] =
    "SELECT SUM(V),AVG(V),MIN(V),MAX(V)FROM F WHERE R=9";
static const char SQL_OVERFLOW[] = "SELECT SUM(V)FROM F WHERE R=3";
static const char SQL_CTAS[] =
    "CREATE TEMP TABLE Z AS SELECT SUM(V),AVG(V),MIN(V),MAX(V)"
    "FROM F WHERE R<3";
static const char SQL_CTAS_READ[] = "SELECT*FROM Z";
static const char SQL_VARIABLE_GROUP[] =
    "SELECT T,B,COUNT(*),SUM(V)FROM G USING INDEX I GROUP BY T,B";
static const char SQL_VARIABLE_WHERE_GROUP[] =
    "SELECT T,COUNT(*),SUM(V)FROM G WHERE T LIKE'a%'GROUP BY T";
static const char SQL_VARIABLE_GROUP_ORDER[] =
    "SELECT T,COUNT(*),SUM(V)FROM G USING INDEX I GROUP BY T ORDER BY T DESC";
static const char SQL_VARIABLE_BLOB_ORDER[] =
    "SELECT B,COUNT(*)FROM G GROUP BY B ORDER BY B";
static const char SQL_VARIABLE_GROUP_DISTINCT[] =
    "SELECT DISTINCT T FROM H GROUP BY T,B";
static const char SQL_JOIN_VARIABLE_OUTER[] =
    "SELECT X.T,COUNT(*),SUM(X.V)FROM G AS X CROSS JOIN K AS Y "
    "GROUP BY X.T ORDER BY 1 DESC";
static const char SQL_JOIN_VARIABLE_INNER[] =
    "SELECT Y.T,COUNT(*)FROM G AS X CROSS JOIN H AS Y "
    "GROUP BY Y.T ORDER BY 1";
static const char SQL_CORRELATED_VARIABLE_GROUP[] =
    "SELECT O.T,COUNT(*),SUM(O.V)FROM G AS O WHERE EXISTS"
    "(SELECT 1 FROM Q AS X WHERE X.R=O.V)GROUP BY O.T ORDER BY 1";
static const unsigned char BLOB_A[] = { 0x01u, 0x02u };
static const unsigned char BLOB_B[] = { 0x01u, 0xFFu };

static void fail(unsigned char stage, unsigned char detail) {
    TEST_STAGE = stage;
    TEST_DETAIL = detail;
    BORDER_COLOR = 2u;
    TEST_SENTINEL = detail ? detail : stage;
    for (;;) {}
}

static void exec_ok(const char* sql, unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) fail(stage, rc);
}

static RsqlCursorHandle open_query(const char* sql, unsigned char columns,
                                   unsigned char stage) {
    RsqlQueryOpenRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_query_open(&request);
    if (rc != RSQL_OK || request.column_count != columns) {
        fail(stage, rc ? rc : request.column_count);
    }
    return request.cursor;
}

static void expect_next(RsqlCursorHandle cursor, unsigned char expected,
                        unsigned char stage) {
    RsqlCursorNextRequest request;
    unsigned char rc;
    request.cursor = cursor;
    rc = rsql_cursor_next(&request);
    if (rc != RSQL_OK || request.has_row != expected) {
        fail(stage, rc ? rc : request.has_row);
    }
}

static void close_query(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest request;
    unsigned char rc;
    request.cursor = cursor;
    rc = rsql_query_close(&request);
    if (rc != RSQL_OK) fail(stage, rc);
}

static void expect_i64(RsqlCursorHandle cursor, unsigned char column,
                       unsigned char expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char index;
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u || request.value.bytes[0] != expected) {
        fail(stage, rc ? rc : request.value.type.tag);
    }
    for (index = 1u; index < 8u; ++index) {
        if (request.value.bytes[index] != 0u) fail(stage, index);
    }
}

static void expect_i8(RsqlCursorHandle cursor, unsigned char column,
                      unsigned char expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I8 ||
        request.value.length != 1u || request.value.bytes[0] != expected) {
        fail(stage, rc ? rc : request.value.bytes[0]);
    }
}

static void expect_variable(RsqlCursorHandle cursor, unsigned char column,
                            unsigned char type, const unsigned char* expected,
                            unsigned int length, unsigned char is_null,
                            unsigned char stage) {
    RsqlCursorColumnRequest request;
    RsqlValueReadRequest read;
    unsigned char bytes[8];
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.type.tag != type ||
        request.value.is_null != is_null ||
        request.value.length != (is_null ? 0u : length)) {
        TEST_DIAG0 = request.value.is_null;
        TEST_DIAG1 = (unsigned char)request.value.length;
        fail(stage, rc ? rc : request.value.type.tag);
    }
    if (is_null) return;
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length ||
        memcmp(bytes, expected, length) != 0) {
        fail(stage, rc ? rc : (unsigned char)read.bytes_read);
    }
}

static void expect_fixed(RsqlCursorHandle cursor, unsigned char column,
                         signed int raw, unsigned char is_null,
                         unsigned char stage) {
    RsqlCursorColumnRequest request;
    RsqlValueReadRequest read;
    unsigned char bytes[2];
    unsigned char low = (unsigned char)raw;
    unsigned char high = (unsigned char)((unsigned int)raw >> 8u);
    unsigned char rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.type.tag != RSQL_TYPE_FIXED8_8 ||
        request.value.length != 2u || request.value.is_null != is_null) {
        fail(stage, rc ? rc : request.value.type.tag);
    }
    if (is_null) return;
    if (request.value.bytes[0] != low || request.value.bytes[1] != high) {
        TEST_DIAG0 = request.value.bytes[0];
        TEST_DIAG1 = request.value.bytes[1];
        fail(stage, 0xFEu);
    }
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 2u ||
        bytes[0] != low || bytes[1] != high) fail(stage, rc ? rc : 0xFDu);
}

static void test_row(const char* sql, unsigned char columns,
                     unsigned char stage) {
    RsqlCursorHandle cursor = open_query(sql, columns, stage);
    expect_next(cursor, 1u, (unsigned char)(stage + 1u));
    if (columns == 6u) {
        expect_i64(cursor, 0u, 4u, (unsigned char)(stage + 2u));
        expect_i64(cursor, 1u, 3u, (unsigned char)(stage + 3u));
        expect_fixed(cursor, 2u, 0x0100, 0u, (unsigned char)(stage + 4u));
        expect_fixed(cursor, 3u, 0x0055, 0u, (unsigned char)(stage + 5u));
        expect_fixed(cursor, 4u, -0x0200, 0u, (unsigned char)(stage + 6u));
        expect_fixed(cursor, 5u, 0x0200, 0u, (unsigned char)(stage + 7u));
    } else {
        expect_i64(cursor, 0u, 4u, (unsigned char)(stage + 2u));
        expect_fixed(cursor, 1u, 0x0100, 0u, (unsigned char)(stage + 3u));
        expect_fixed(cursor, 2u, 0x0055, 0u, (unsigned char)(stage + 4u));
        expect_fixed(cursor, 3u, -0x0200, 0u, (unsigned char)(stage + 5u));
        expect_fixed(cursor, 4u, 0x0200, 0u, (unsigned char)(stage + 6u));
    }
    expect_next(cursor, 0u, (unsigned char)(stage + 8u));
    close_query(cursor, (unsigned char)(stage + 9u));
}

static void test_grouped(void) {
    RsqlCursorHandle cursor = open_query(SQL_GROUPED, 6u, 0x40u);
    expect_next(cursor, 1u, 0x41u);
    expect_i8(cursor, 0u, 1u, 0x42u);
    expect_i64(cursor, 1u, 2u, 0x43u);
    expect_fixed(cursor, 2u, 0x0300, 0u, 0x44u);
    expect_fixed(cursor, 3u, 0x0180, 0u, 0x45u);
    expect_fixed(cursor, 4u, 0x0100, 0u, 0x46u);
    expect_fixed(cursor, 5u, 0x0200, 0u, 0x47u);
    expect_next(cursor, 1u, 0x48u);
    expect_i8(cursor, 0u, 2u, 0x49u);
    expect_i64(cursor, 1u, 1u, 0x4Au);
    expect_fixed(cursor, 2u, -0x0200, 0u, 0x4Bu);
    expect_fixed(cursor, 3u, -0x0200, 0u, 0x4Cu);
    expect_fixed(cursor, 4u, -0x0200, 0u, 0x4Du);
    expect_fixed(cursor, 5u, -0x0200, 0u, 0x4Eu);
    expect_next(cursor, 0u, 0x4Fu);
    close_query(cursor, 0x50u);
}

static void test_correlated(void) {
    RsqlCursorHandle cursor = open_query(SQL_CORRELATED, 2u, 0x60u);
    expect_next(cursor, 1u, 0x61u);
    expect_fixed(cursor, 0u, 0x0100, 0u, 0x62u);
    expect_fixed(cursor, 1u, 0x0055, 0u, 0x63u);
    expect_next(cursor, 0u, 0x64u);
    close_query(cursor, 0x65u);
}

static void test_empty(void) {
    RsqlCursorHandle cursor = open_query(SQL_EMPTY, 4u, 0x70u);
    unsigned char column;
    expect_next(cursor, 1u, 0x71u);
    for (column = 0u; column < 4u; ++column) {
        expect_fixed(cursor, column, 0, 1u,
                     (unsigned char)(0x72u + column));
    }
    close_query(cursor, 0x76u);
}

static void test_overflow(void) {
    RsqlCursorHandle cursor = open_query(SQL_OVERFLOW, 1u, 0x80u);
    RsqlCursorColumnRequest column;
    RsqlValueReadRequest read;
    unsigned char bytes[2];
    unsigned char rc;
    expect_next(cursor, 1u, 0x81u);
    column.cursor = cursor;
    column.column = 0u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_ERR_NUMERIC_OVERFLOW) fail(0x82u, rc);
    read.cursor = cursor;
    read.column = 0u;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_ERR_NUMERIC_OVERFLOW) fail(0x83u, rc);
    close_query(cursor, 0x84u);
}

static void test_ctas(void) {
    RsqlCursorHandle cursor;
    exec_ok(SQL_CTAS, 0x90u);
    cursor = open_query(SQL_CTAS_READ, 4u, 0x91u);
    expect_next(cursor, 1u, 0x92u);
    expect_fixed(cursor, 0u, 0x0100, 0u, 0x93u);
    expect_fixed(cursor, 1u, 0x0055, 0u, 0x94u);
    expect_fixed(cursor, 2u, -0x0200, 0u, 0x95u);
    expect_fixed(cursor, 3u, 0x0200, 0u, 0x96u);
    close_query(cursor, 0x97u);
}

static void test_variable_groups(void) {
    RsqlCursorHandle cursor = open_query(SQL_VARIABLE_GROUP, 4u, 0xA0u);
    expect_next(cursor, 1u, 0xA1u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT, 0, 0u, 1u, 0xA2u);
    expect_variable(cursor, 1u, RSQL_TYPE_BLOB, 0, 0u, 1u, 0xA3u);
    expect_i64(cursor, 2u, 2u, 0xA4u);
    expect_i64(cursor, 3u, 9u, 0xA5u);
    expect_next(cursor, 1u, 0xA6u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0xA7u);
    expect_variable(cursor, 1u, RSQL_TYPE_BLOB, BLOB_B, 2u, 0u, 0xA8u);
    expect_i64(cursor, 2u, 1u, 0xA9u);
    expect_i64(cursor, 3u, 3u, 0xAAu);
    expect_next(cursor, 1u, 0xABu);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"A", 1u, 0u, 0xACu);
    expect_variable(cursor, 1u, RSQL_TYPE_BLOB, BLOB_A, 2u, 0u, 0xADu);
    expect_i64(cursor, 2u, 2u, 0xAEu);
    expect_i64(cursor, 3u, 3u, 0xAFu);
    expect_next(cursor, 0u, 0xB0u);
    close_query(cursor, 0xB1u);

    cursor = open_query(SQL_VARIABLE_WHERE_GROUP, 3u, 0xB2u);
    expect_next(cursor, 1u, 0xB3u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"a", 1u, 0u, 0xB4u);
    expect_i64(cursor, 1u, 2u, 0xB5u);
    expect_i64(cursor, 2u, 3u, 0xB6u);
    expect_next(cursor, 0u, 0xB7u);
    close_query(cursor, 0xB8u);

    cursor = open_query(SQL_VARIABLE_GROUP_ORDER, 3u, 0xC0u);
    expect_next(cursor, 1u, 0xC1u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0xC2u);
    expect_i64(cursor, 1u, 1u, 0xC3u);
    expect_i64(cursor, 2u, 3u, 0xC4u);
    expect_next(cursor, 1u, 0xC5u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"A", 1u, 0u, 0xC6u);
    expect_i64(cursor, 1u, 2u, 0xC7u);
    expect_i64(cursor, 2u, 3u, 0xC8u);
    expect_next(cursor, 1u, 0xC9u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT, 0, 0u, 1u, 0xCAu);
    expect_i64(cursor, 1u, 2u, 0xCBu);
    expect_i64(cursor, 2u, 9u, 0xCCu);
    expect_next(cursor, 0u, 0xCDu);
    close_query(cursor, 0xCEu);

    cursor = open_query(SQL_VARIABLE_BLOB_ORDER, 2u, 0xD0u);
    expect_next(cursor, 1u, 0xD1u);
    expect_variable(cursor, 0u, RSQL_TYPE_BLOB, 0, 0u, 1u, 0xD2u);
    expect_i64(cursor, 1u, 2u, 0xD3u);
    expect_next(cursor, 1u, 0xD4u);
    expect_variable(cursor, 0u, RSQL_TYPE_BLOB, BLOB_A, 2u, 0u, 0xD5u);
    expect_i64(cursor, 1u, 2u, 0xD6u);
    expect_next(cursor, 1u, 0xD7u);
    expect_variable(cursor, 0u, RSQL_TYPE_BLOB, BLOB_B, 2u, 0u, 0xD8u);
    expect_i64(cursor, 1u, 1u, 0xD9u);
    expect_next(cursor, 0u, 0xDAu);
    close_query(cursor, 0xDBu);

    cursor = open_query(SQL_VARIABLE_GROUP_DISTINCT, 1u, 0xE0u);
    expect_next(cursor, 1u, 0xE1u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"a", 1u, 0u, 0xE2u);
    expect_next(cursor, 1u, 0xE3u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0xE4u);
    expect_next(cursor, 0u, 0xE5u);
    close_query(cursor, 0xE6u);
}

static void test_composed_variable_groups(void) {
    RsqlCursorHandle cursor = open_query(SQL_JOIN_VARIABLE_OUTER, 3u, 0xF0u);
    expect_next(cursor, 1u, 0xF1u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0xF2u);
    expect_i64(cursor, 1u, 2u, 0xF3u);
    expect_i64(cursor, 2u, 6u, 0xF4u);
    expect_next(cursor, 1u, 0xF5u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"a", 1u, 0u, 0xF6u);
    expect_i64(cursor, 1u, 4u, 0xF7u);
    expect_i64(cursor, 2u, 6u, 0xF8u);
    expect_next(cursor, 1u, 0xF9u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT, 0, 0u, 1u, 0xFAu);
    expect_i64(cursor, 1u, 4u, 0xFBu);
    expect_i64(cursor, 2u, 18u, 0xFCu);
    expect_next(cursor, 0u, 0xFDu);
    close_query(cursor, 0xFEu);

    cursor = open_query(SQL_JOIN_VARIABLE_INNER, 2u, 0x60u);
    expect_next(cursor, 1u, 0x61u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"a", 1u, 0u, 0x62u);
    expect_i64(cursor, 1u, 10u, 0x63u);
    expect_next(cursor, 1u, 0x64u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0x65u);
    expect_i64(cursor, 1u, 5u, 0x66u);
    expect_next(cursor, 0u, 0x67u);
    close_query(cursor, 0x68u);

    cursor = open_query(SQL_CORRELATED_VARIABLE_GROUP, 3u, 0x69u);
    expect_next(cursor, 1u, 0x6Au);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT, 0, 0u, 1u, 0x6Bu);
    expect_i64(cursor, 1u, 2u, 0x6Cu);
    expect_i64(cursor, 2u, 9u, 0x6Du);
    expect_next(cursor, 1u, 0x6Eu);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"a", 1u, 0u, 0x6Fu);
    expect_i64(cursor, 1u, 2u, 0x70u);
    expect_i64(cursor, 2u, 3u, 0x71u);
    expect_next(cursor, 1u, 0x72u);
    expect_variable(cursor, 0u, RSQL_TYPE_TEXT,
                    (const unsigned char*)"b", 1u, 0u, 0x73u);
    expect_i64(cursor, 1u, 1u, 0x74u);
    expect_i64(cursor, 2u, 3u, 0x75u);
    expect_next(cursor, 0u, 0x76u);
    close_query(cursor, 0x77u);
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
    if (rc != RSQL_OK) fail(0x10u, rc);
    if (rsql_reu_size_kib() != (unsigned int)(512u << REU_SIZE_SELECTOR)) {
        fail(0x11u, 0u);
    }
    for (index = 0u; index < sizeof(SETUP) / sizeof(SETUP[0]); ++index) {
        exec_ok(SETUP[index], (unsigned char)(0x12u + index));
    }
    test_row(SQL_ORDINARY, 6u, 0x20u);
    test_grouped();
    test_row(SQL_JOINED, 5u, 0x30u);
    test_correlated();
    test_empty();
    test_overflow();
    test_ctas();
    test_variable_groups();
    test_composed_variable_groups();
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_DETAIL (*(volatile unsigned char*)0xCFF4)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char* const SETUP[] = {
    "CREATE TABLE A(ID I16)",
    "CREATE TABLE B(ID I16,AID I16,V I16 NULL)",
    "CREATE TABLE C(ID I16,BID I16,V I16 NULL)",
    "INSERT INTO A VALUES(1)",
    "INSERT INTO A VALUES(2)",
    "INSERT INTO A VALUES(3)",
    "INSERT INTO B VALUES(10,1,10)",
    "INSERT INTO B VALUES(20,2,NULL)",
    "INSERT INTO B VALUES(30,1,30)",
    "INSERT INTO C VALUES(100,10,10)",
    "INSERT INTO C VALUES(200,20,NULL)",
    "INSERT INTO C VALUES(300,30,30)",
    "INSERT INTO C VALUES(400,30,31)",
    "CREATE TABLE D(K CHAR(3))",
    "CREATE TABLE E(ID I16,AID I16,K CHAR(3))",
    "CREATE TABLE F(ID I16,BID I16,K CHAR(3))",
    "INSERT INTO D VALUES('BY')",
    "INSERT INTO D VALUES('BY')",
    "INSERT INTO D VALUES('Z')",
    "INSERT INTO E VALUES(10,1,'AX')",
    "INSERT INTO E VALUES(20,2,'LM')",
    "INSERT INTO E VALUES(30,1,'AX')",
    "INSERT INTO F VALUES(100,10,'BY')",
    "INSERT INTO F VALUES(200,20,'A')",
    "INSERT INTO F VALUES(300,30,'BY')",
    "INSERT INTO F VALUES(400,999,'Z')"
};

static const char SQL_IN[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.V IN(SELECT C.V FROM C WHERE C.BID=B.ID))";
static const char SQL_NOT_IN_NULL[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.V NOT IN(SELECT C.V FROM C WHERE C.BID=20))";
static const char SQL_NOT_IN_EMPTY[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.V NOT IN(SELECT C.V FROM C WHERE C.ID=999))";
static const char SQL_SCALAR[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.V=(SELECT C.V FROM C WHERE C.BID=B.ID AND C.ID<400))";
static const char SQL_SCALAR_MANY[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.ID=30 AND B.V=(SELECT C.V FROM C WHERE C.BID=B.ID))";
static const char SQL_NESTED_EXISTS[] =
    "SELECT A.ID FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND EXISTS(SELECT 1 FROM C WHERE C.BID=B.ID))";
static const char SQL_AGG_IN[] =
    "SELECT COUNT(*),SUM(A.ID) FROM A WHERE EXISTS(SELECT 1 FROM B "
    "WHERE B.AID=A.ID AND B.V IN(SELECT C.V FROM C WHERE C.BID=B.ID))";
static const char SQL_AGG_SCALAR[] =
    "SELECT COUNT(*) FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.V=(SELECT C.V FROM C WHERE C.BID=B.ID AND C.ID<400))";
static const char SQL_GROUP_EXISTS[] =
    "SELECT A.ID,COUNT(*) FROM A WHERE EXISTS(SELECT 1 FROM B WHERE "
    "B.AID=A.ID AND EXISTS(SELECT 1 FROM C WHERE C.BID=B.ID)) "
    "GROUP BY A.ID ORDER BY A.ID";
static const char SQL_AGG_SCALAR_MANY[] =
    "SELECT COUNT(*) FROM A WHERE EXISTS(SELECT 1 FROM B WHERE B.AID=A.ID "
    "AND B.ID=30 AND B.V=(SELECT C.V FROM C WHERE C.BID=B.ID))";
static const char SQL_GROUP_SCALAR[] =
    "SELECT LENGTH(K),SUBSTR(K,1,1),K||'!',COUNT(*)FROM D GROUP BY K";
static const char SQL_JOIN_GROUP_SCALAR[] =
    "SELECT DISTINCT LENGTH(X.K)FROM D AS X CROSS JOIN E AS Y "
    "WHERE X.K='BY' GROUP BY X.K,Y.K";
static const char SQL_WIDE_GROUP_SCALAR[] =
    "SELECT LENGTH(A0.K),A0.K||Z.K,COUNT(*)FROM D AS A0 "
    "JOIN E AS Y ON Y.K='AX' JOIN F AS Z ON Z.BID=Y.ID "
    "GROUP BY A0.K,Z.K";
static const char SQL_LITERAL_AGG_SCALAR[] =
    "SELECT 'G',COUNT(*)FROM D";
static const char SQL_BAD_AGG_SCALAR[] =
    "SELECT LENGTH(K),COUNT(*)FROM D";
static const char SQL_CREATE_GROUP_SCALAR[] =
    "CREATE TEMP TABLE GS AS SELECT LENGTH(K),K||K,COUNT(*)FROM D GROUP BY K";
static const char SQL_READ_GROUP_SCALAR[] =
    "SELECT*FROM GS ORDER BY C1 DESC";
static const char SQL_ORDER_GROUP_SCALAR[] =
    "SELECT K||'!',COUNT(*)FROM D GROUP BY K ORDER BY 1 DESC";
static const char SQL_DISTINCT_GROUP_SCALAR[] =
    "SELECT DISTINCT 'G' FROM D AS X WHERE EXISTS(SELECT 1 FROM F AS Y "
    "WHERE Y.K=X.K)GROUP BY X.K";
static const char SQL_ORDER_CORRELATED_GROUP_SCALAR[] =
    "SELECT X.K||'!',COUNT(*)FROM D AS X WHERE EXISTS(SELECT 1 FROM F AS Y "
    "WHERE Y.K=X.K)GROUP BY X.K ORDER BY 1 DESC";
static const char SQL_ORDER_JOIN_GROUP_SCALAR[] =
    "SELECT X.K||Y.K,COUNT(*)FROM D AS X CROSS JOIN E AS Y "
    "WHERE X.K='BY' GROUP BY X.K,Y.K ORDER BY 1 DESC";
static const char SQL_ORDER_WIDE_GROUP_SCALAR[] =
    "SELECT LENGTH(A0.K),A0.K||Z.K,COUNT(*)FROM D AS A0 "
    "JOIN E AS Y ON Y.K='AX' JOIN F AS Z ON Z.BID=Y.ID "
    "GROUP BY A0.K,Z.K ORDER BY 2 DESC";

static void fail(unsigned char stage, unsigned char detail) {
    TEST_STAGE = stage;
    TEST_DETAIL = detail;
    TEST_SENTINEL = detail ? detail : stage;
    BORDER_COLOR = 2u;
    for (;;) {}
}

static void exec_ok(const char* sql, unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) fail(stage, rc);
}

static RsqlCursorHandle open_ok(const char* sql, unsigned char columns,
                                unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc;
    TEST_STAGE = stage;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != columns) {
        fail(stage, rc ? rc : open.column_count);
    }
    return open.cursor;
}

static void next_ok(RsqlCursorHandle cursor, unsigned char expected,
                    unsigned char stage) {
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    unsigned char rc;
    TEST_STAGE = stage;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row != expected) {
        if (rc == RSQL_OK && next.has_row && !expected) {
            column.cursor = cursor;
            column.column = 0u;
            if (rsql_cursor_column(&column) == RSQL_OK &&
                !column.value.is_null && column.value.length != 0u) {
                fail(stage, column.value.bytes[0]);
            }
        }
        fail(stage, rc ? rc : 0xFFu);
    }
}

static void expect_i16(RsqlCursorHandle cursor, unsigned char column,
                       unsigned int expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I16 ||
        request.value.length != 2u ||
        request.value.bytes[0] != (unsigned char)expected ||
        request.value.bytes[1] != (unsigned char)(expected >> 8u)) {
        fail(stage, rc ? rc : request.value.bytes[0]);
    }
}

static void expect_i64(RsqlCursorHandle cursor, unsigned char column,
                       unsigned char expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u || request.value.bytes[0] != expected) {
        fail(stage, rc ? rc : request.value.bytes[0]);
    }
    for (index = 1u; index < 8u; ++index) {
        if (request.value.bytes[index] != 0u) fail(stage, index);
    }
}

static void expect_bytes(RsqlCursorHandle cursor, unsigned char column,
                         const char* expected, unsigned char length,
                         unsigned char stage) {
    RsqlValueReadRequest request;
    unsigned char bytes[8];
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    request.cursor = cursor;
    request.column = column;
    request.offset = 0u;
    request.destination = bytes;
    request.capacity = sizeof(bytes);
    rc = rsql_value_read(&request);
    if (rc != RSQL_OK) fail(stage, rc);
    if (request.bytes_read != length) fail(stage, request.bytes_read);
    for (index = 0u; index < length; ++index) {
        if (bytes[index] != (unsigned char)expected[index]) {
            fail(stage, bytes[index]);
        }
    }
}

static void close_ok(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    TEST_STAGE = stage;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(stage, rc);
}

static void expect_single_id(const char* sql, unsigned int expected,
                             unsigned char stage) {
    RsqlCursorHandle cursor = open_ok(sql, 1u, stage);
    next_ok(cursor, 1u, (unsigned char)(stage + 1u));
    expect_i16(cursor, 0u, expected, (unsigned char)(stage + 2u));
    next_ok(cursor, 0u, (unsigned char)(stage + 3u));
    close_ok(cursor, (unsigned char)(stage + 4u));
}

static void expect_no_rows(const char* sql, unsigned char stage) {
    RsqlCursorHandle cursor = open_ok(sql, 1u, stage);
    next_ok(cursor, 0u, (unsigned char)(stage + 1u));
    close_ok(cursor, (unsigned char)(stage + 2u));
}

static void expect_scalar_many(const char* sql, unsigned char columns,
                               unsigned char stage) {
    RsqlCursorHandle cursor = open_ok(sql, columns, stage);
    RsqlCursorNextRequest next;
    unsigned char rc;
    TEST_STAGE = (unsigned char)(stage + 1u);
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_ERR_SUBQUERY_ROWS) fail((unsigned char)(stage + 1u), rc);
    close_ok(cursor, (unsigned char)(stage + 2u));
}

int main(void) {
    RsqlInitRequest init;
    RsqlCursorHandle cursor;
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
        exec_ok(SETUP[index], (unsigned char)(0x20u + index));
    }

    expect_single_id(SQL_IN, 1u, 0x40u);
    expect_no_rows(SQL_NOT_IN_NULL, 0x45u);

    cursor = open_ok(SQL_NOT_IN_EMPTY, 1u, 0x48u);
    next_ok(cursor, 1u, 0x49u);
    expect_i16(cursor, 0u, 1u, 0x4Au);
    next_ok(cursor, 1u, 0x4Bu);
    expect_i16(cursor, 0u, 2u, 0x4Cu);
    next_ok(cursor, 0u, 0x4Du);
    close_ok(cursor, 0x4Eu);

    expect_single_id(SQL_SCALAR, 1u, 0x50u);
    expect_scalar_many(SQL_SCALAR_MANY, 1u, 0x55u);

    cursor = open_ok(SQL_NESTED_EXISTS, 1u, 0x58u);
    next_ok(cursor, 1u, 0x59u);
    expect_i16(cursor, 0u, 1u, 0x5Au);
    next_ok(cursor, 1u, 0x5Bu);
    expect_i16(cursor, 0u, 2u, 0x5Cu);
    next_ok(cursor, 0u, 0x5Du);
    close_ok(cursor, 0x5Eu);

    cursor = open_ok(SQL_AGG_IN, 2u, 0x60u);
    next_ok(cursor, 1u, 0x61u);
    expect_i64(cursor, 0u, 1u, 0x62u);
    expect_i64(cursor, 1u, 1u, 0x63u);
    next_ok(cursor, 0u, 0x64u);
    close_ok(cursor, 0x65u);

    cursor = open_ok(SQL_AGG_SCALAR, 1u, 0x66u);
    next_ok(cursor, 1u, 0x67u);
    expect_i64(cursor, 0u, 1u, 0x68u);
    next_ok(cursor, 0u, 0x69u);
    close_ok(cursor, 0x6Au);

    cursor = open_ok(SQL_GROUP_EXISTS, 2u, 0x6Bu);
    next_ok(cursor, 1u, 0x6Cu);
    expect_i16(cursor, 0u, 1u, 0x6Du);
    expect_i64(cursor, 1u, 1u, 0x6Eu);
    next_ok(cursor, 1u, 0x6Fu);
    expect_i16(cursor, 0u, 2u, 0x70u);
    expect_i64(cursor, 1u, 1u, 0x71u);
    next_ok(cursor, 0u, 0x72u);
    close_ok(cursor, 0x73u);

    expect_scalar_many(SQL_AGG_SCALAR_MANY, 1u, 0x74u);

    cursor = open_ok(SQL_GROUP_SCALAR, 4u, 0x79u);
    next_ok(cursor, 1u, 0x7Au);
    expect_i16(cursor, 0u, 2u, 0x7Bu);
    expect_bytes(cursor, 1u, "B", 1u, 0x7Cu);
    expect_bytes(cursor, 2u, "BY!", 3u, 0x7Du);
    expect_i64(cursor, 3u, 2u, 0x7Eu);
    next_ok(cursor, 1u, 0x80u);
    expect_i16(cursor, 0u, 1u, 0x81u);
    expect_bytes(cursor, 2u, "Z!", 2u, 0x82u);
    expect_i64(cursor, 3u, 1u, 0x83u);
    next_ok(cursor, 0u, 0x84u);
    close_ok(cursor, 0x85u);

    cursor = open_ok(SQL_LITERAL_AGG_SCALAR, 2u, 0x86u);
    next_ok(cursor, 1u, 0x87u);
    expect_bytes(cursor, 0u, "G", 1u, 0x88u);
    expect_i64(cursor, 1u, 3u, 0x89u);
    next_ok(cursor, 0u, 0x8Au);
    close_ok(cursor, 0x8Bu);

    cursor = open_ok(SQL_JOIN_GROUP_SCALAR, 1u, 0x8Cu);
    next_ok(cursor, 1u, 0x8Du);
    expect_i16(cursor, 0u, 2u, 0x8Eu);
    next_ok(cursor, 0u, 0x8Fu);
    close_ok(cursor, 0x90u);

    cursor = open_ok(SQL_WIDE_GROUP_SCALAR, 3u, 0x96u);
    next_ok(cursor, 1u, 0x97u);
    expect_i16(cursor, 0u, 2u, 0x98u);
    expect_bytes(cursor, 1u, "BYBY", 4u, 0x99u);
    expect_i64(cursor, 2u, 4u, 0x9Au);
    next_ok(cursor, 1u, 0x9Bu);
    expect_bytes(cursor, 1u, "ZBY", 3u, 0x9Cu);
    expect_i64(cursor, 2u, 2u, 0x9Du);
    next_ok(cursor, 0u, 0x9Eu);
    close_ok(cursor, 0x9Fu);

    exec_ok(SQL_CREATE_GROUP_SCALAR, 0xA0u);
    cursor = open_ok(SQL_READ_GROUP_SCALAR, 3u, 0xA1u);
    next_ok(cursor, 1u, 0xA2u);
    expect_i16(cursor, 0u, 2u, 0xA3u);
    expect_bytes(cursor, 1u, "BYBY  ", 6u, 0xA4u);
    expect_i64(cursor, 2u, 2u, 0xA6u);
    next_ok(cursor, 1u, 0xA7u);
    expect_i16(cursor, 0u, 1u, 0xA8u);
    expect_bytes(cursor, 1u, "ZZ    ", 6u, 0xA9u);
    expect_i64(cursor, 2u, 1u, 0xAAu);
    next_ok(cursor, 0u, 0xABu);
    close_ok(cursor, 0xACu);

    cursor = open_ok(SQL_ORDER_GROUP_SCALAR, 2u, 0xADu);
    next_ok(cursor, 1u, 0xAEu);
    expect_bytes(cursor, 0u, "Z!", 2u, 0xAFu);
    expect_i64(cursor, 1u, 1u, 0xB0u);
    next_ok(cursor, 1u, 0xB1u);
    expect_bytes(cursor, 0u, "BY!", 3u, 0xB2u);
    expect_i64(cursor, 1u, 2u, 0xB3u);
    next_ok(cursor, 0u, 0xB4u);
    close_ok(cursor, 0xB5u);

    cursor = open_ok(SQL_DISTINCT_GROUP_SCALAR, 1u, 0xB6u);
    next_ok(cursor, 1u, 0xB7u);
    expect_bytes(cursor, 0u, "G", 1u, 0xB8u);
    next_ok(cursor, 0u, 0xB9u);
    close_ok(cursor, 0xBAu);

    cursor = open_ok(SQL_ORDER_WIDE_GROUP_SCALAR, 3u, 0xC5u);
    next_ok(cursor, 1u, 0xC6u);
    expect_bytes(cursor, 1u, "ZBY", 3u, 0xC7u);
    expect_i64(cursor, 2u, 2u, 0xC8u);
    next_ok(cursor, 1u, 0xC9u);
    expect_bytes(cursor, 1u, "BYBY", 4u, 0xCAu);
    expect_i64(cursor, 2u, 4u, 0xCBu);
    next_ok(cursor, 0u, 0xCCu);
    close_ok(cursor, 0xCDu);

    cursor = open_ok(SQL_ORDER_JOIN_GROUP_SCALAR, 2u, 0xCEu);
    next_ok(cursor, 1u, 0xCFu);
    expect_bytes(cursor, 0u, "BYLM", 4u, 0xD0u);
    expect_i64(cursor, 1u, 2u, 0xD1u);
    next_ok(cursor, 1u, 0xD2u);
    expect_bytes(cursor, 0u, "BYAX", 4u, 0xD3u);
    expect_i64(cursor, 1u, 4u, 0xD4u);
    next_ok(cursor, 0u, 0xD5u);
    close_ok(cursor, 0xD6u);

    cursor = open_ok(SQL_ORDER_CORRELATED_GROUP_SCALAR, 2u, 0xD7u);
    next_ok(cursor, 1u, 0xD8u);
    expect_bytes(cursor, 0u, "Z!", 2u, 0xD9u);
    expect_i64(cursor, 1u, 1u, 0xDAu);
    next_ok(cursor, 1u, 0xDBu);
    expect_bytes(cursor, 0u, "BY!", 3u, 0xDCu);
    expect_i64(cursor, 1u, 2u, 0xDDu);
    next_ok(cursor, 0u, 0xDEu);
    close_ok(cursor, 0xE0u);

    {
        RsqlQueryOpenRequest open;
        open.sql = SQL_BAD_AGG_SCALAR;
        open.sql_length = strlen(SQL_BAD_AGG_SCALAR);
        rc = rsql_query_open(&open);
        if (rc != RSQL_ERR_UNSUPPORTED_SQL) fail(0xE1u, rc);
    }

    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail(0xE2u, rc);
    TEST_STAGE = 0xEFu;
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

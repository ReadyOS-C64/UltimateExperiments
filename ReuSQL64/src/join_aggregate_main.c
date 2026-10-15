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
    "CREATE TABLE CUST(ID I16,NAME CHAR(8))",
    "CREATE TABLE ORDR(ID I16,CID I32 NULL,TOTAL I16,SMALL I8,"
        "W32 I32,W64 I64,FVAL FLOAT NULL)",
    "CREATE TABLE E(ID I16)",
    "INSERT INTO CUST VALUES(1,'ADA')",
    "INSERT INTO CUST VALUES(2,'BOB')",
    "INSERT INTO CUST VALUES(3,'CY')",
    "INSERT INTO ORDR VALUES(10,1,50,-100,100000,4294967296,1.5)",
    "INSERT INTO ORDR VALUES(11,1,75,100,-30000,-2,2.25)",
    "INSERT INTO ORDR VALUES(12,2,-5,7,-70000,6,-0.75)",
    "INSERT INTO ORDR VALUES(13,NULL,20,1,20,20,NULL)",
    "INSERT INTO ORDR VALUES(14,99,30,2,30,30,3.5)"
};

static const char SQL_INNER[] =
    "SELECT COUNT(*),COUNT(O.TOTAL),SUM(O.TOTAL),AVG(O.TOTAL),"
    "MIN(O.TOTAL),MAX(O.TOTAL),SUM(C.ID) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_WHERE[] =
    "SELECT COUNT(*),SUM(O.TOTAL),AVG(O.TOTAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "WHERE O.TOTAL>=0";
static const char SQL_LEFT[] =
    "SELECT COUNT(*),COUNT(O.ID),SUM(O.TOTAL) "
    "FROM CUST AS C LEFT JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_CROSS[] =
    "SELECT COUNT(*),SUM(O.TOTAL) "
    "FROM CUST AS C CROSS JOIN ORDR AS O";
static const char SQL_EMPTY[] =
    "SELECT COUNT(*),SUM(E.ID) "
    "FROM CUST AS C CROSS JOIN E AS E";
static const char SQL_I8[] =
    "SELECT SUM(O.SMALL),AVG(O.SMALL),MIN(O.SMALL),MAX(O.SMALL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_I32[] =
    "SELECT SUM(O.W32),AVG(O.W32),MIN(O.W32),MAX(O.W32) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_I64[] =
    "SELECT SUM(O.W64),AVG(O.W64),MIN(O.W64),MAX(O.W64) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_FLOAT[] =
    "SELECT COUNT(*),COUNT(O.FVAL),SUM(O.FVAL),AVG(O.FVAL),"
    "MIN(O.FVAL),MAX(O.FVAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_GROUP_INNER[] =
    "SELECT C.ID,COUNT(*),SUM(O.TOTAL),MIN(O.TOTAL),MAX(O.TOTAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID GROUP BY C.ID";
static const char SQL_GROUP_LEFT[] =
    "SELECT C.ID,COUNT(*),COUNT(O.ID),SUM(O.TOTAL) "
    "FROM CUST AS C LEFT JOIN ORDR AS O ON C.ID=O.CID GROUP BY C.ID";
static const char SQL_GROUP_CROSS_NULL[] =
    "SELECT O.CID,COUNT(*) FROM CUST AS C CROSS JOIN ORDR AS O "
    "GROUP BY O.CID";
static const char SQL_GROUP_COMPOUND_PAGE[] =
    "SELECT C.ID,O.CID,COUNT(*) FROM CUST AS C CROSS JOIN ORDR AS O "
    "GROUP BY C.ID,O.CID LIMIT 1 OFFSET 5";
static const char SQL_GROUP_WHERE[] =
    "SELECT C.ID,COUNT(*),SUM(O.TOTAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "WHERE O.TOTAL>=0 GROUP BY C.ID";
static const char SQL_GROUP_ORDER_AGG[] =
    "SELECT C.ID,COUNT(*),SUM(O.TOTAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "GROUP BY C.ID ORDER BY 3 DESC";
static const char SQL_GROUP_ORDER_INNER[] =
    "SELECT O.CID,COUNT(*) FROM CUST AS C CROSS JOIN ORDR AS O "
    "GROUP BY O.CID ORDER BY O.CID DESC";
static const char SQL_GROUP_ORDER_FLOAT[] =
    "SELECT C.ID,SUM(O.FVAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "GROUP BY C.ID ORDER BY 2";
static const char SQL_GROUP_DISTINCT_KEY[] =
    "SELECT DISTINCT C.ID FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "GROUP BY C.ID,O.TOTAL ORDER BY C.ID DESC";
static const char SQL_GROUP_DISTINCT_AGG[] =
    "SELECT DISTINCT COUNT(*) FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "GROUP BY C.ID ORDER BY 1 DESC";
static const char SQL_GROUP_ORDER_PAGE[] =
    "SELECT C.ID,O.TOTAL,COUNT(*) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "GROUP BY C.ID,O.TOTAL ORDER BY C.ID DESC,O.TOTAL "
    "LIMIT 1 OFFSET 1";
static const char SQL_UNGROUPED_ORDER[] =
    "SELECT COUNT(*),SUM(O.TOTAL) "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID ORDER BY 2 DESC";
static const char SQL_EMPTY_ORDER[] =
    "SELECT COUNT(*),SUM(E.ID) "
    "FROM CUST AS C CROSS JOIN E AS E ORDER BY 1";
static const char SQL_JOIN_EXISTS[] =
    "SELECT COUNT(*),SUM(O.TOTAL) FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "WHERE EXISTS(SELECT 1 FROM ORDR AS X WHERE X.ID=O.ID AND X.CID=C.ID)";
static const char SQL_JOIN_IN[] =
    "SELECT C.ID,COUNT(*),SUM(O.TOTAL) FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "WHERE O.ID IN(SELECT X.ID FROM ORDR AS X WHERE X.TOTAL>=O.TOTAL) "
    "GROUP BY C.ID ORDER BY 3 DESC LIMIT 1";
static const char SQL_JOIN_SCALAR[] =
    "SELECT DISTINCT C.ID,COUNT(*) FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "WHERE O.CID=(SELECT X.CID FROM ORDR AS X WHERE X.ID=O.ID) "
    "GROUP BY C.ID ORDER BY C.ID DESC LIMIT 1";

static const unsigned char I64_NEG_70000[8] =
    {0x90u,0xEEu,0xFEu,0xFFu,0xFFu,0xFFu,0xFFu,0xFFu};
static const unsigned char I64_100000[8] =
    {0xA0u,0x86u,0x01u,0x00u,0x00u,0x00u,0x00u,0x00u};
static const unsigned char I64_4294967300[8] =
    {0x04u,0x00u,0x00u,0x00u,0x01u,0x00u,0x00u,0x00u};
static const unsigned char I64_1431655766[8] =
    {0x56u,0x55u,0x55u,0x55u,0x00u,0x00u,0x00u,0x00u};
static const unsigned char I64_NEG_2[8] =
    {0xFEu,0xFFu,0xFFu,0xFFu,0xFFu,0xFFu,0xFFu,0xFFu};
static const unsigned char I64_4294967296[8] =
    {0x00u,0x00u,0x00u,0x00u,0x01u,0x00u,0x00u,0x00u};
static const unsigned char F_NEG_075[5] = {0x80u,0xC0u,0u,0u,0u};
static const unsigned char F_1[5] = {0x81u,0u,0u,0u,0u};
static const unsigned char F_225[5] = {0x82u,0x10u,0u,0u,0u};
static const unsigned char F_3[5] = {0x82u,0x40u,0u,0u,0u};

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static void exec_ok(const char* sql, unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static void expect_i64(RsqlCursorHandle cursor, unsigned char index,
                       unsigned int expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char fill = (expected & 0x8000u) ? 0xFFu : 0u;
    unsigned char byte;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u ||
        request.value.bytes[0] != (unsigned char)expected ||
        request.value.bytes[1] != (unsigned char)(expected >> 8u)) {
        TEST_DETAIL = index;
        fail(rc ? rc : stage);
    }
    for (byte = 2u; byte < 8u; ++byte) {
        if (request.value.bytes[byte] != fill) fail(stage);
    }
}

static void expect_null_i64(RsqlCursorHandle cursor, unsigned char index,
                            unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || !request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64) fail(rc ? rc : stage);
}

static void expect_i64_bytes(RsqlCursorHandle cursor, unsigned char index,
                             const unsigned char* expected,
                             unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u ||
        memcmp(request.value.bytes, expected, 8u) != 0) {
        TEST_DETAIL = index;
        fail(rc ? rc : stage);
    }
}

static void expect_float(RsqlCursorHandle cursor, unsigned char index,
                         const unsigned char* expected,
                         unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_FLOAT5 ||
        request.value.length != 5u ||
        memcmp(request.value.bytes, expected, 5u) != 0) {
        TEST_DETAIL = index;
        fail(rc ? rc : stage);
    }
}

static void expect_fixed(RsqlCursorHandle cursor, unsigned char index,
                         unsigned char tag, unsigned char width,
                         signed long expected, unsigned char is_null,
                         unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned long value = (unsigned long)expected;
    unsigned char byte;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null != is_null ||
        request.value.type.tag != tag || request.value.length != width) {
        TEST_DETAIL = index;
        fail(rc ? rc : stage);
    }
    if (is_null) return;
    for (byte = 0u; byte < width; ++byte) {
        if (request.value.bytes[byte] != (unsigned char)value) fail(stage);
        value >>= 8u;
    }
}

static void next_row(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlCursorNextRequest next;
    unsigned char rc;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : stage);
}

static RsqlCursorHandle open_first(const char* sql, unsigned char columns,
                                   unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    unsigned char rc;
    TEST_STAGE = stage;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != columns) {
        TEST_DETAIL = rc != RSQL_OK ? rc : open.column_count;
        fail(rc ? rc : stage);
    }
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) {
        TEST_DETAIL = rc != RSQL_OK ? rc : next.has_row;
        fail(rc ? rc : stage);
    }
    return open.cursor;
}

static void close_one_row(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlCursorNextRequest next;
    RsqlQueryCloseRequest close;
    unsigned char rc;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : stage);
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc);
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
    if (rc != RSQL_OK) fail(rc);
    if (rsql_reu_size_kib() != (unsigned int)(512u << REU_SIZE_SELECTOR)) {
        fail(0x80u);
    }
    for (index = 0u; index < sizeof(SETUP) / sizeof(SETUP[0]); ++index) {
        exec_ok(SETUP[index], (unsigned char)(0x81u + index));
    }

    cursor = open_first(SQL_INNER, 7u, 0x20u);
    expect_i64(cursor, 0u, 3u, 0x21u);
    expect_i64(cursor, 1u, 3u, 0x22u);
    expect_i64(cursor, 2u, 120u, 0x23u);
    expect_i64(cursor, 3u, 40u, 0x24u);
    expect_i64(cursor, 4u, 0xFFFBu, 0x25u);
    expect_i64(cursor, 5u, 75u, 0x26u);
    expect_i64(cursor, 6u, 4u, 0x27u);
    close_one_row(cursor, 0x28u);

    cursor = open_first(SQL_WHERE, 3u, 0x30u);
    expect_i64(cursor, 0u, 2u, 0x31u);
    expect_i64(cursor, 1u, 125u, 0x32u);
    expect_i64(cursor, 2u, 62u, 0x33u);
    close_one_row(cursor, 0x34u);

    cursor = open_first(SQL_LEFT, 3u, 0x40u);
    expect_i64(cursor, 0u, 4u, 0x41u);
    expect_i64(cursor, 1u, 3u, 0x42u);
    expect_i64(cursor, 2u, 120u, 0x43u);
    close_one_row(cursor, 0x44u);

    cursor = open_first(SQL_CROSS, 2u, 0x50u);
    expect_i64(cursor, 0u, 15u, 0x51u);
    expect_i64(cursor, 1u, 510u, 0x52u);
    close_one_row(cursor, 0x53u);

    cursor = open_first(SQL_EMPTY, 2u, 0x60u);
    expect_i64(cursor, 0u, 0u, 0x61u);
    expect_null_i64(cursor, 1u, 0x62u);
    close_one_row(cursor, 0x63u);

    cursor = open_first(SQL_I8, 4u, 0x70u);
    expect_i64(cursor, 0u, 7u, 0x71u);
    expect_i64(cursor, 1u, 2u, 0x72u);
    expect_i64(cursor, 2u, 0xFF9Cu, 0x73u);
    expect_i64(cursor, 3u, 100u, 0x74u);
    close_one_row(cursor, 0x75u);

    cursor = open_first(SQL_I32, 4u, 0x76u);
    expect_i64(cursor, 0u, 0u, 0x77u);
    expect_i64(cursor, 1u, 0u, 0x78u);
    expect_i64_bytes(cursor, 2u, I64_NEG_70000, 0x79u);
    expect_i64_bytes(cursor, 3u, I64_100000, 0x7Au);
    close_one_row(cursor, 0x7Bu);

    cursor = open_first(SQL_I64, 4u, 0x90u);
    expect_i64_bytes(cursor, 0u, I64_4294967300, 0x91u);
    expect_i64_bytes(cursor, 1u, I64_1431655766, 0x92u);
    expect_i64_bytes(cursor, 2u, I64_NEG_2, 0x93u);
    expect_i64_bytes(cursor, 3u, I64_4294967296, 0x94u);
    close_one_row(cursor, 0x95u);

    cursor = open_first(SQL_FLOAT, 6u, 0x96u);
    expect_i64(cursor, 0u, 3u, 0x97u);
    expect_i64(cursor, 1u, 3u, 0x98u);
    expect_float(cursor, 2u, F_3, 0x99u);
    expect_float(cursor, 3u, F_1, 0x9Au);
    expect_float(cursor, 4u, F_NEG_075, 0x9Bu);
    expect_float(cursor, 5u, F_225, 0x9Cu);
    close_one_row(cursor, 0x9Du);

    cursor = open_first(SQL_GROUP_INNER, 5u, 0xA0u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0xA1u);
    expect_i64(cursor, 1u, 2u, 0xA2u);
    expect_i64(cursor, 2u, 125u, 0xA3u);
    expect_i64(cursor, 3u, 50u, 0xA4u);
    expect_i64(cursor, 4u, 75u, 0xA5u);
    next_row(cursor, 0xA6u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0xA7u);
    expect_i64(cursor, 1u, 1u, 0xA8u);
    expect_i64(cursor, 2u, 0xFFFBu, 0xA9u);
    expect_i64(cursor, 3u, 0xFFFBu, 0xAAu);
    expect_i64(cursor, 4u, 0xFFFBu, 0xABu);
    close_one_row(cursor, 0xACu);

    cursor = open_first(SQL_GROUP_LEFT, 4u, 0xB0u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0xB1u);
    expect_i64(cursor, 1u, 2u, 0xB2u);
    expect_i64(cursor, 2u, 2u, 0xB3u);
    expect_i64(cursor, 3u, 125u, 0xB4u);
    next_row(cursor, 0xB5u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0xB6u);
    expect_i64(cursor, 1u, 1u, 0xB7u);
    expect_i64(cursor, 2u, 1u, 0xB8u);
    expect_i64(cursor, 3u, 0xFFFBu, 0xB9u);
    next_row(cursor, 0xBAu);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 3, 0u, 0xBBu);
    expect_i64(cursor, 1u, 1u, 0xBCu);
    expect_i64(cursor, 2u, 0u, 0xBDu);
    expect_null_i64(cursor, 3u, 0xBEu);
    close_one_row(cursor, 0xBFu);

    cursor = open_first(SQL_GROUP_CROSS_NULL, 2u, 0xC0u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 1, 0u, 0xC1u);
    expect_i64(cursor, 1u, 6u, 0xC2u);
    next_row(cursor, 0xC3u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 2, 0u, 0xC4u);
    expect_i64(cursor, 1u, 3u, 0xC5u);
    next_row(cursor, 0xC6u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 0, 1u, 0xC7u);
    expect_i64(cursor, 1u, 3u, 0xC8u);
    next_row(cursor, 0xC9u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 99, 0u, 0xCAu);
    expect_i64(cursor, 1u, 3u, 0xCBu);
    close_one_row(cursor, 0xCCu);

    cursor = open_first(SQL_GROUP_COMPOUND_PAGE, 3u, 0xD0u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0xD1u);
    expect_fixed(cursor, 1u, RSQL_TYPE_I32, 4u, 2, 0u, 0xD2u);
    expect_i64(cursor, 2u, 1u, 0xD3u);
    close_one_row(cursor, 0xD4u);

    cursor = open_first(SQL_GROUP_WHERE, 3u, 0xE0u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0xE1u);
    expect_i64(cursor, 1u, 2u, 0xE2u);
    expect_i64(cursor, 2u, 125u, 0xE3u);
    close_one_row(cursor, 0xE4u);

    cursor = open_first(SQL_GROUP_ORDER_AGG, 3u, 0x10u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0x11u);
    expect_i64(cursor, 1u, 2u, 0x12u);
    expect_i64(cursor, 2u, 125u, 0x13u);
    next_row(cursor, 0x14u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0x15u);
    expect_i64(cursor, 1u, 1u, 0x16u);
    expect_i64(cursor, 2u, 0xFFFBu, 0x17u);
    close_one_row(cursor, 0x18u);

    cursor = open_first(SQL_GROUP_ORDER_INNER, 2u, 0x19u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 99, 0u, 0x1Au);
    expect_i64(cursor, 1u, 3u, 0x1Bu);
    next_row(cursor, 0x1Cu);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 2, 0u, 0x1Du);
    next_row(cursor, 0x1Eu);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 1, 0u, 0x1Fu);
    expect_i64(cursor, 1u, 6u, 0x20u);
    next_row(cursor, 0x21u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I32, 4u, 0, 1u, 0x22u);
    close_one_row(cursor, 0x23u);

    cursor = open_first(SQL_GROUP_ORDER_FLOAT, 2u, 0x24u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0x25u);
    expect_float(cursor, 1u, F_NEG_075, 0x26u);
    next_row(cursor, 0x27u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0x28u);
    close_one_row(cursor, 0x29u);

    cursor = open_first(SQL_GROUP_DISTINCT_KEY, 1u, 0x2Au);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0x2Bu);
    next_row(cursor, 0x2Cu);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0x2Du);
    close_one_row(cursor, 0x2Eu);

    cursor = open_first(SQL_GROUP_DISTINCT_AGG, 1u, 0x31u);
    expect_i64(cursor, 0u, 2u, 0x32u);
    next_row(cursor, 0x33u);
    expect_i64(cursor, 0u, 1u, 0x34u);
    close_one_row(cursor, 0x35u);

    cursor = open_first(SQL_GROUP_ORDER_PAGE, 3u, 0x36u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0x37u);
    expect_fixed(cursor, 1u, RSQL_TYPE_I16, 2u, 50, 0u, 0x38u);
    expect_i64(cursor, 2u, 1u, 0x39u);
    close_one_row(cursor, 0x3Au);

    cursor = open_first(SQL_UNGROUPED_ORDER, 2u, 0x3Bu);
    expect_i64(cursor, 0u, 3u, 0x3Cu);
    expect_i64(cursor, 1u, 120u, 0x3Du);
    close_one_row(cursor, 0x3Eu);

    cursor = open_first(SQL_EMPTY_ORDER, 2u, 0x3Fu);
    expect_i64(cursor, 0u, 0u, 0x40u);
    expect_null_i64(cursor, 1u, 0x41u);
    close_one_row(cursor, 0x42u);

    cursor = open_first(SQL_JOIN_EXISTS, 2u, 0x43u);
    expect_i64(cursor, 0u, 3u, 0x44u);
    expect_i64(cursor, 1u, 120u, 0x45u);
    close_one_row(cursor, 0x45u);

    cursor = open_first(SQL_JOIN_IN, 3u, 0x46u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 1, 0u, 0x47u);
    expect_i64(cursor, 1u, 2u, 0x48u);
    expect_i64(cursor, 2u, 125u, 0x49u);
    close_one_row(cursor, 0x48u);

    cursor = open_first(SQL_JOIN_SCALAR, 2u, 0x49u);
    expect_fixed(cursor, 0u, RSQL_TYPE_I16, 2u, 2, 0u, 0x4Au);
    expect_i64(cursor, 1u, 1u, 0x4Bu);
    close_one_row(cursor, 0x4Bu);

    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail(rc);
    TEST_STAGE = 0x7Fu;
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

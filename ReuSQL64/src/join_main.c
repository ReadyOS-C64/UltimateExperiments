#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_DETAIL (*(volatile unsigned char*)0xCFF4)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_CUSTOMERS[] =
    "CREATE TABLE CUST(ID I16,NAME CHAR(8),STATE STATE,"
    "LIMITV FIXED8_8)";
static const char SQL_ORDERS[] =
    "CREATE TABLE ORDR(ID I16,CID I32 NULL,TOTAL I16,"
    "LABEL CHAR(8),NOTE TEXT NULL,STATUS STATE,AMOUNT FIXED8_8)";
static const char SQL_STATE[] =
    "CREATE TYPE STATE AS ENUM8(ACTIVE=1,INACTIVE=2)";
static const char SQL_EMPTY[] = "CREATE TABLE EMPTYJ(ID I16)";
static const char* const INSERTS[] = {
    "INSERT INTO CUST VALUES(1,'ADA',STATE.ACTIVE,2)",
    "INSERT INTO CUST VALUES(2,'BOB',STATE.INACTIVE,-1)",
    "INSERT INTO CUST VALUES(3,'CY',STATE.ACTIVE,3)",
    "INSERT INTO ORDR VALUES(10,1,50,'ADA','FIRST',STATE.ACTIVE,2)",
    "INSERT INTO ORDR VALUES(11,1,75,'BAG',NULL,STATE.INACTIVE,3)",
    "INSERT INTO ORDR VALUES(12,2,-5,'BAD','RETURN',STATE.INACTIVE,-1)",
    "INSERT INTO ORDR VALUES(13,NULL,20,'ORPHAN','NONE',STATE.ACTIVE,3)",
    "INSERT INTO ORDR VALUES(14,99,30,'MISS','X',STATE.ACTIVE,2)"
};
static const char SQL_INNER[] =
    "SELECT DISTINCT C.NAME,O.NOTE,O.ID FROM CUST AS C JOIN ORDR AS O "
    "ON C.ID=O.CID WHERE O.NOTE<'S'";
static const char SQL_LEFT[] =
    "SELECT C.ID,O.ID FROM CUST AS C LEFT JOIN ORDR AS O "
    "ON C.ID=O.CID";
static const char SQL_LEFT_NULL[] =
    "SELECT C.ID FROM CUST AS C LEFT JOIN ORDR AS O "
    "ON C.ID=O.CID WHERE O.ID IS NULL";
static const char SQL_LEFT_ON[] =
    "SELECT C.ID,O.ID FROM CUST AS C LEFT JOIN ORDR AS O "
    "ON C.ID=O.CID AND(O.NOTE LIKE'F%'OR O.NOTE IS NULL)";
static const char SQL_CROSS[] =
    "SELECT CUST.ID FROM ORDR CROSS JOIN CUST "
    "WHERE ORDR.NOTE LIKE'R%' AND CUST.ID>=2 LIMIT 1 OFFSET 1";
static const char SQL_CROSS_REF[] =
    "SELECT C.ID,O.ID FROM CUST AS C CROSS JOIN ORDR AS O "
    "WHERE C.ID=O.CID";
static const char SQL_STRING_REF[] =
    "SELECT C.ID,O.ID FROM CUST AS C JOIN ORDR AS O "
    "ON C.NAME=O.LABEL";
static const char SQL_ENUM_REF[] =
    "SELECT C.ID,O.ID FROM CUST AS C JOIN ORDR AS O "
    "ON C.STATE=O.STATUS AND C.ID=O.CID "
    "WHERE C.STATE=STATE.ACTIVE";
static const char SQL_FIXED_REF[] =
    "SELECT DISTINCT LENGTH(O.NOTE) FROM CUST AS C JOIN ORDR AS O "
    "ON C.LIMITV=O.AMOUNT WHERE O.AMOUNT>=2";
static const char SQL_JOIN_LIMIT[] =
    "SELECT O.ID FROM CUST AS C JOIN ORDR AS O "
    "ON C.ID=O.CID LIMIT 1 OFFSET 1";
static const char SQL_JOIN_ORDER[] =
    "SELECT O.ID,SUBSTR(O.NOTE,1,2) FROM CUST AS C JOIN ORDR AS O "
    "ON C.ID=O.CID WHERE O.NOTE>'E'ORDER BY 2,O.ID DESC";
static const char SQL_JOIN_ORDER_LIMIT[] =
    "SELECT O.ID FROM CUST AS C JOIN ORDR AS O "
    "ON C.ID=O.CID ORDER BY O.TOTAL ASC,O.ID DESC "
    "LIMIT 2 OFFSET 1";
static const char SQL_LEFT_ORDER[] =
    "SELECT C.ID FROM CUST AS C LEFT JOIN ORDR AS O "
    "ON C.ID=O.CID ORDER BY O.ID DESC";
static const char SQL_JOIN_SCALARS[] =
    "SELECT LENGTH(C.NAME),SUBSTR(O.LABEL,2,2),C.NAME||O.LABEL "
    "FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID "
    "ORDER BY 3";
static const char SQL_LEFT_SCALAR_NULL[] =
    "SELECT O.LABEL||'X' FROM CUST AS C LEFT JOIN ORDR AS O "
    "ON C.ID=O.CID WHERE C.ID=3";
static const char SQL_EMPTY_LEFT[] =
    "SELECT C.ID,E.ID FROM CUST AS C LEFT JOIN EMPTYJ AS E ON C.ID=E.ID";
static const char SQL_EMPTY_CROSS[] =
    "SELECT C.ID FROM CUST AS C CROSS JOIN EMPTYJ AS E";
static const char SQL_AMBIGUOUS[] =
    "SELECT ID FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID";
static const char SQL_BAD_TYPES[] =
    "SELECT C.ID FROM CUST AS C JOIN ORDR AS O ON C.NAME=O.ID";
static const char SQL_SAME_UNALIASED[] =
    "SELECT CUST.ID FROM CUST JOIN CUST ON CUST.ID=CUST.ID";
static const char SQL_EXISTS[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID)";
static const char SQL_NOT_EXISTS[] =
    "SELECT C.ID FROM CUST AS C WHERE NOT EXISTS"
    "(SELECT * FROM ORDR AS O WHERE O.CID=C.ID)";
static const char SQL_EXISTS_BOOLEAN[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT O.ID FROM ORDR AS O WHERE O.CID=C.ID AND "
    "(O.TOTAL>60 OR O.TOTAL<0) AND NOT (O.ID=14))";
static const char SQL_IN_CORRELATED[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID IN "
    "(SELECT O.CID FROM ORDR AS O "
    "WHERE O.CID=C.ID AND O.TOTAL>=0)";
static const char SQL_IN_NULL[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID IN "
    "(SELECT O.CID FROM ORDR AS O WHERE O.ID=13)";
static const char SQL_NOT_IN_NULL[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID NOT IN "
    "(SELECT O.CID FROM ORDR AS O)";
static const char SQL_SCALAR[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID="
    "(SELECT O.CID FROM ORDR AS O WHERE O.ID=10)";
static const char SQL_SCALAR_CORRELATED[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID="
    "(SELECT O.CID FROM ORDR AS O "
    "WHERE O.CID=C.ID AND O.ID=12)";
static const char SQL_SCALAR_MANY[] =
    "SELECT C.ID FROM CUST AS C WHERE C.ID="
    "(SELECT O.CID FROM ORDR AS O WHERE O.CID=C.ID)";
static const char SQL_OUTER_BOOLEAN[] =
    "SELECT C.ID FROM CUST AS C WHERE C.NAME LIKE 'A%' OR EXISTS "
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID AND O.ID=12)";
static const char SQL_CHAR_IN[] =
    "SELECT C.ID FROM CUST AS C WHERE C.NAME IN "
    "(SELECT O.LABEL FROM ORDR AS O WHERE O.ID=10)";
static const char SQL_ENUM_EXISTS[] =
    "SELECT C.ID FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS X WHERE X.ID=O.ID "
    "AND X.STATUS=STATE.ACTIVE)";
static const char SQL_ENUM_IN[] =
    "SELECT C.ID FROM CUST AS C WHERE C.STATE IN "
    "(SELECT O.STATUS FROM ORDR AS O WHERE O.CID=C.ID "
    "AND O.STATUS=STATE.ACTIVE)";
static const char SQL_OUTER_ENUM[] =
    "SELECT C.ID FROM CUST AS C WHERE C.STATE=STATE.INACTIVE AND EXISTS "
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID)";
static const char SQL_EMPTY_EXISTS[] =
    "SELECT DISTINCT LENGTH(O.NOTE) FROM ORDR AS O WHERE NOT EXISTS"
    "(SELECT 1 FROM EMPTYJ AS E WHERE E.ID=O.ID)";
static const char SQL_SELF_EXISTS[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM CUST AS X WHERE X.ID=C.ID)";
static const char SQL_SUBQUERY_LIMIT[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID) LIMIT 1 OFFSET 1";
static const char SQL_SUBQUERY_ORDER[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID) ORDER BY 1 DESC";
static const char SQL_SUBQUERY_ORDER_LIMIT[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID) "
    "ORDER BY C.ID DESC LIMIT 1 OFFSET 1";
static const char SQL_SUBQUERY_SCALARS[] =
    "SELECT DISTINCT LENGTH('ABC'),SUBSTR('WXYZ',2,2),C.NAME||'X' "
    "FROM CUST AS C WHERE EXISTS"
    "(SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID AND O.ID>=10 "
    "AND O.TOTAL>-10) ORDER BY 3";
static const char SQL_SUBQUERY_BAD_TYPES[] =
    "SELECT C.ID FROM CUST AS C WHERE C.NAME IN "
    "(SELECT O.ID FROM ORDR AS O)";
static const char SQL_SUBQUERY_SAME_ALIAS[] =
    "SELECT C.ID FROM CUST AS C WHERE EXISTS "
    "(SELECT 1 FROM CUST AS C WHERE C.ID=C.ID)";
static const char SQL_NESTED_TAIL[] =
    " AND EXISTS(SELECT*FROM CUST AS X WHERE X.ID=O.CID AND X.ID=C.ID"
    " AND X.STATE=STATE.ACTIVE))";
static char g_nested_sql[172];

static void fail(unsigned char code) {
    TEST_DETAIL = code;
    TEST_SENTINEL = code;
    BORDER_COLOR = 2u;
    for (;;) {}
}

static void exec_ok(const char* sql, unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) {
        fail(rc ? rc : stage);
    }
}

static unsigned char open_rc(const char* sql, RsqlQueryOpenRequest* open) {
    open->sql = sql;
    open->sql_length = strlen(sql);
    return rsql_query_open(open);
}

static void close_cursor(RsqlCursorHandle cursor) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc);
}

static unsigned char next_row(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlCursorNextRequest next;
    unsigned char rc;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    return next.has_row;
}

static void column(RsqlCursorHandle cursor, unsigned char index,
                   RsqlValueInfo* value, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    request.cursor = cursor;
    request.column = index;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    *value = request.value;
}

static void expect_i16(RsqlCursorHandle cursor, unsigned char index,
                       unsigned int expected, unsigned char stage) {
    RsqlValueInfo value;
    column(cursor, index, &value, stage);
    if (value.is_null || value.type.tag != RSQL_TYPE_I16 ||
        value.bytes[0] != (unsigned char)expected ||
        value.bytes[1] != (unsigned char)(expected >> 8u)) {
        TEST_DETAIL = value.bytes[0];
        fail(stage);
    }
}


static void expect_null(RsqlCursorHandle cursor, unsigned char index,
                        unsigned char type, unsigned char stage) {
    RsqlValueInfo value;
    column(cursor, index, &value, stage);
    if (!value.is_null || value.type.tag != type) fail(stage);
}

static void expect_char(RsqlCursorHandle cursor, unsigned char index,
                        const char* expected, unsigned char stage) {
    RsqlValueInfo value;
    RsqlValueReadRequest read;
    unsigned char bytes[16];
    unsigned char length = (unsigned char)strlen(expected);
    unsigned char rc;
    column(cursor, index, &value, stage);
    if (value.is_null || value.type.tag != RSQL_TYPE_CHAR ||
        value.length != length) fail(stage);
    read.cursor = cursor;
    read.column = index;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length ||
        memcmp(bytes, expected, length) != 0) fail(rc ? rc : stage);
}

static void test_scalar_producers(void) {
    RsqlQueryOpenRequest open;
    RsqlValueInfo value;
    unsigned char rc = open_rc(SQL_JOIN_SCALARS, &open);
    if (rc != RSQL_OK || open.column_count != 3u) fail(rc ? rc : 0x40u);
    if (!next_row(open.cursor, 0x41u)) fail(0x41u);
    column(open.cursor, 0u, &value, 0x42u);
    if (value.is_null || value.type.tag != RSQL_TYPE_I16 ||
        value.bytes[0] != 3u || value.bytes[1] != 0u) fail(0x42u);
    expect_char(open.cursor, 1u, "DA", 0x43u);
    expect_char(open.cursor, 2u, "ADAADA", 0x44u);
    if (!next_row(open.cursor, 0x45u) ||
        !next_row(open.cursor, 0x45u) ||
        next_row(open.cursor, 0x45u)) fail(0x45u);
    close_cursor(open.cursor);

    rc = open_rc(SQL_LEFT_SCALAR_NULL, &open);
    if (rc != RSQL_OK || !next_row(open.cursor, 0x46u)) {
        fail(rc ? rc : 0x46u);
    }
    expect_null(open.cursor, 0u, RSQL_TYPE_CHAR, 0x47u);
    close_cursor(open.cursor);

    rc = open_rc(SQL_SUBQUERY_SCALARS, &open);
    if (rc != RSQL_OK || open.column_count != 3u ||
        !next_row(open.cursor, 0x48u)) fail(rc ? rc : 0x48u);
    column(open.cursor, 0u, &value, 0x49u);
    if (value.is_null || value.bytes[0] != 3u) fail(0x49u);
    expect_char(open.cursor, 1u, "XY", 0x4Au);
    expect_char(open.cursor, 2u, "ADAX", 0x4Bu);
    if (!next_row(open.cursor, 0x4Cu) ||
        next_row(open.cursor, 0x4Cu)) fail(0x4Cu);
    close_cursor(open.cursor);
}

static unsigned char count_rows(const char* sql, unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char count = 0u;
    unsigned char rc;
    rc = open_rc(sql, &open);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
    while (next_row(open.cursor, stage)) ++count;
    close_cursor(open.cursor);
    return count;
}

static void expect_ids(const char* sql, const unsigned char* expected,
                       unsigned char count, unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    rc = open_rc(sql, &open);
    if (rc != RSQL_OK || open.column_count == 0u) fail(rc ? rc : stage);
    for (index = 0u; index < count; ++index) {
        unsigned char row_stage = (unsigned char)(stage + index + 1u);
        TEST_STAGE = row_stage;
        if (!next_row(open.cursor, row_stage)) {
            TEST_DETAIL = 0xFEu;
            fail(row_stage);
        }
        expect_i16(open.cursor, 0u, expected[index], row_stage);
    }
    TEST_STAGE = (unsigned char)(stage + count + 1u);
    if (next_row(open.cursor, (unsigned char)(stage + count + 1u))) {
        fail((unsigned char)(stage + count + 1u));
    }
    close_cursor(open.cursor);
}

static void test_subqueries(void) {
    static const unsigned char IDS12[] = { 1u, 2u };
    static const unsigned char IDS21[] = { 2u, 1u };
    static const unsigned char ID3[] = { 3u };
    static const unsigned char ID1[] = { 1u };
    static const unsigned char ID2[] = { 2u };
    static const unsigned char IDS123[] = { 1u, 2u, 3u };
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    unsigned char rc;
    expect_ids(SQL_EXISTS, IDS12, 2u, 0xC1u);
    expect_ids(SQL_NOT_EXISTS, ID3, 1u, 0xC2u);
    expect_ids(SQL_EXISTS_BOOLEAN, IDS12, 2u, 0xC3u);
    expect_ids(SQL_IN_CORRELATED, ID1, 1u, 0xC4u);
    if (count_rows(SQL_IN_NULL, 0xC5u) != 0u) fail(0xC5u);
    if (count_rows(SQL_NOT_IN_NULL, 0xC6u) != 0u) fail(0xC6u);
    expect_ids(SQL_SCALAR, ID1, 1u, 0xC7u);
    expect_ids(SQL_SCALAR_CORRELATED, ID2, 1u, 0xC8u);
    expect_ids(SQL_OUTER_BOOLEAN, IDS12, 2u, 0xC9u);
    expect_ids(SQL_CHAR_IN, ID1, 1u, 0xCAu);
    expect_ids(SQL_ENUM_EXISTS, ID1, 1u, 0xD1u);
    expect_ids(SQL_ENUM_IN, ID1, 1u, 0xD2u);
    expect_ids(SQL_OUTER_ENUM, ID2, 1u, 0xD3u);
    if (count_rows(SQL_EMPTY_EXISTS, 0xCBu) != 5u) fail(0xCBu);
    expect_ids(SQL_SELF_EXISTS, IDS123, 3u, 0xCCu);
    expect_ids(SQL_SUBQUERY_LIMIT, ID2, 1u, 0x30u);
    expect_ids(SQL_SUBQUERY_ORDER, IDS21, 2u, 0x31u);
    expect_ids(SQL_SUBQUERY_ORDER_LIMIT, ID1, 1u, 0x32u);
    strcpy(g_nested_sql, SQL_EXISTS);
    strcpy(&g_nested_sql[strlen(g_nested_sql) - 1u], SQL_NESTED_TAIL);
    expect_ids(g_nested_sql, ID1, 1u, 0x33u);
    rc = open_rc(SQL_SCALAR_MANY, &open);
    if (rc != RSQL_OK) fail(rc);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_ERR_SUBQUERY_ROWS) fail(rc ? rc : 0xCDu);
    close_cursor(open.cursor);
    rc = open_rc(SQL_SUBQUERY_BAD_TYPES, &open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xCEu);
    rc = open_rc(SQL_SUBQUERY_SAME_ALIAS, &open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xCFu);
}

static void test_inner(void) {
    RsqlQueryOpenRequest open;
    RsqlValueReadRequest read;
    RsqlValueInfo value;
    unsigned char text[8];
    unsigned char rc = open_rc(SQL_INNER, &open);
    if (rc != RSQL_OK || open.column_count != 3u) fail(rc ? rc : 0x90u);
    rc = next_row(open.cursor, 0x91u);
    if (!rc) fail(0x91u);
    column(open.cursor, 0u, &value, 0x92u);
    if (value.is_null || value.type.tag != RSQL_TYPE_CHAR ||
        value.bytes[0] != 'A' || value.bytes[1] != 'D' ||
        value.bytes[2] != 'A') fail(0x92u);
    column(open.cursor, 1u, &value, 0x94u);
    if (value.is_null || value.type.tag != RSQL_TYPE_TEXT ||
        value.length != 5u) fail(0x94u);
    read.cursor = open.cursor;
    read.column = 1u;
    read.offset = 0u;
    read.destination = text;
    read.capacity = sizeof(text);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 5u ||
        memcmp(text, "FIRST", 5u)) fail(rc ? rc : 0x95u);
    expect_i16(open.cursor, 2u, 10u, 0x93u);
    if (!next_row(open.cursor, 0x96u)) fail(0x96u);
    expect_i16(open.cursor, 2u, 12u, 0x97u);
    if (next_row(open.cursor, 0x99u)) fail(0x99u);
    close_cursor(open.cursor);
}

static void test_left(void) {
    static const unsigned char OUTER[] = {1u, 1u, 2u, 3u};
    static const unsigned char INNER[] = {10u, 11u, 12u, 0u};
    RsqlQueryOpenRequest open;
    unsigned char index;
    unsigned char rc = open_rc(SQL_LEFT, &open);
    if (rc != RSQL_OK) fail(rc);
    for (index = 0u; index < 4u; ++index) {
        if (!next_row(open.cursor, 0xA0u)) fail(0xA0u);
        expect_i16(open.cursor, 0u, OUTER[index], 0xA1u);
        if (index == 3u) {
            expect_null(open.cursor, 1u, RSQL_TYPE_I16, 0xA2u);
        } else expect_i16(open.cursor, 1u, INNER[index], 0xA3u);
    }
    if (next_row(open.cursor, 0xA4u)) fail(0xA4u);
    close_cursor(open.cursor);
}


int main(void) {
    RsqlInitRequest init;
    RsqlQueryOpenRequest open;
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
    TEST_STAGE = 0x81u;
    exec_ok(SQL_STATE, 0x81u);
    exec_ok(SQL_CUSTOMERS, 0x82u);
    exec_ok(SQL_ORDERS, 0x83u);
    exec_ok(SQL_EMPTY, 0x84u);
    for (index = 0u; index < sizeof(INSERTS) / sizeof(INSERTS[0]); ++index) {
        exec_ok(INSERTS[index], (unsigned char)(0x84u + index));
    }
    test_inner();
    test_left();
    if (count_rows(SQL_LEFT_NULL, 0xB0u) != 1u) fail(0xB0u);
    if (count_rows(SQL_LEFT_ON, 0xB1u) != 4u) fail(0xB1u);
    if (count_rows(SQL_CROSS, 0xB2u) != 1u) fail(0xB2u);
    if (count_rows(SQL_CROSS_REF, 0xB3u) != 3u) fail(0xB3u);
    if (count_rows(SQL_STRING_REF, 0xB4u) != 1u) fail(0xB4u);
    if (count_rows(SQL_ENUM_REF, 0xBAu) != 1u) fail(0xBAu);
    if (count_rows(SQL_FIXED_REF, 0xBBu) != 4u) fail(0xBBu);
    {
        static const unsigned char ID11[] = { 11u };
        static const unsigned char ORDERED[] = { 10u, 12u };
        static const unsigned char ORDERED_PAGE[] = { 10u, 11u };
        static const unsigned char LEFT_ORDERED[] = { 2u, 1u, 1u, 3u };
        expect_ids(SQL_JOIN_LIMIT, ID11, 1u, 0x31u);
        expect_ids(SQL_JOIN_ORDER, ORDERED, 2u, 0x32u);
        expect_ids(SQL_JOIN_ORDER_LIMIT, ORDERED_PAGE, 2u, 0x34u);
        expect_ids(SQL_LEFT_ORDER, LEFT_ORDERED, 4u, 0x33u);
    }
    if (count_rows(SQL_EMPTY_LEFT, 0xB5u) != 3u) fail(0xB5u);
    if (count_rows(SQL_EMPTY_CROSS, 0xB6u) != 0u) fail(0xB6u);
    test_scalar_producers();
    rc = open_rc(SQL_AMBIGUOUS, &open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xB7u);
    rc = open_rc(SQL_BAD_TYPES, &open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xB8u);
    rc = open_rc(SQL_SAME_UNALIASED, &open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xB9u);
    TEST_STAGE = 0xC1u;
    test_subqueries();
    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail(rc);
    TEST_STAGE = 0xD0u;
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

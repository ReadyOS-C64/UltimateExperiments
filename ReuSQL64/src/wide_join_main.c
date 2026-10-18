#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define TEST_STAGE (*(volatile unsigned char*)0xCFF3)
#define TEST_DETAIL (*(volatile unsigned char*)0xCFF4)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

/* This client is deliberately compiled without optimization because cc65
 * 2.19 crashes while optimizing it.  Keep the request that crosses an
 * overlay load out of the deep software-stack frame. */
static RsqlCursorColumnRequest g_column_request;

static const char* const SETUP[] = {
    "CREATE TYPE WS AS ENUM8(OFF=0,ON=1)",
    "CREATE TABLE A(ID I16,K CHAR(3),STATE WS)",
    "CREATE TABLE B(ID I16,AID I16,K CHAR(3),STATE WS)",
    "CREATE TABLE C(ID I16,BID I16,AID I16,K CHAR(3),STATE WS,V FIXED8_8,F FLOAT,T TEXT)",
    "INSERT INTO A VALUES(1,'AX',WS.ON)",
    "INSERT INTO A VALUES(2,'BY',WS.OFF)",
    "INSERT INTO A VALUES(3,'NO',WS.ON)",
    "INSERT INTO B VALUES(10,1,'AX',WS.ON)",
    "INSERT INTO B VALUES(11,1,'NO',WS.OFF)",
    "INSERT INTO B VALUES(20,2,'BY',WS.OFF)",
    "INSERT INTO C VALUES(100,10,1,'AX',WS.ON,1,1.5,'ALPHA')",
    "INSERT INTO C VALUES(101,11,1,'ZZ',WS.OFF,5,5,'FILTERED')",
    "INSERT INTO C VALUES(200,20,2,'BY',WS.OFF,2,2.5,'BETA-LONG')"
};

static const char SQL_INNER[] =
    "SELECT A.ID,B.ID,C.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K "
    "WHERE C.STATE=A.STATE AND(C.STATE=WS.ON OR A.ID=2)";
static const char SQL_CROSS[] =
    "SELECT A.ID,B.ID,C.ID FROM A CROSS JOIN B CROSS JOIN C "
    "WHERE A.ID=B.AID AND B.ID=C.BID LIMIT 2 OFFSET 1";
static const char SQL_TEXT[] =
    "SELECT A.ID,B.ID,C.T FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K "
    "WHERE C.STATE=A.STATE";
static const char SQL_AGGREGATE[] =
    "SELECT COUNT(*),SUM(C.ID),AVG(B.ID),MIN(A.ID),MAX(C.ID) "
    "FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K "
    "WHERE C.STATE=A.STATE";
static const char SQL_GROUPED[] =
    "SELECT C.STATE,COUNT(*),SUM(C.ID),AVG(B.ID),MIN(A.ID),MAX(C.ID) "
    "FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K "
    "WHERE C.STATE=A.STATE GROUP BY C.STATE";
static const char SQL_GROUP_ORDER[] =
    "SELECT C.STATE,COUNT(*),SUM(C.ID) FROM A "
    "JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "AND C.AID=A.ID AND C.K=B.K WHERE C.STATE=A.STATE "
    "GROUP BY C.STATE ORDER BY C.STATE";
static const char SQL_GROUP_AGG_PAGE[] =
    "SELECT C.STATE,COUNT(*),SUM(C.ID) FROM A "
    "JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "AND C.AID=A.ID AND C.K=B.K WHERE C.STATE=A.STATE "
    "GROUP BY C.STATE ORDER BY 3 DESC LIMIT 1 OFFSET 1";
static const char SQL_GROUP_DISTINCT[] =
    "SELECT DISTINCT COUNT(*) FROM A "
    "JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "AND C.AID=A.ID AND C.K=B.K WHERE C.STATE=A.STATE "
    "GROUP BY C.STATE ORDER BY 1";
static const char SQL_UNGROUPED_SHAPED[] =
    "SELECT DISTINCT COUNT(*) FROM A "
    "JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "ORDER BY 1 DESC LIMIT 1";
static const char SQL_UNGROUPED_OFFSET[] =
    "SELECT COUNT(*) FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID ORDER BY 1 OFFSET 1";
static const char SQL_NUMERIC[] =
    "SELECT SUM(C.V),AVG(C.V),MIN(C.V),MAX(C.V),SUM(C.F),AVG(C.F) "
    "FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K "
    "WHERE C.STATE=A.STATE";
static const char SQL_CTAS[] =
    "CREATE TABLE WOUT AS SELECT A.ID,B.ID,C.ID FROM A "
    "JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "AND C.AID=A.ID AND C.K=B.K WHERE C.STATE=A.STATE "
    "AND(C.STATE=WS.ON OR A.ID=2)";
static const char SQL_CTAS_READ[] =
    "SELECT*FROM WOUT ORDER BY C1,C2,C3";
static const char SQL_AMBIGUOUS[] =
    "SELECT ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID";
static const char SQL_DUP_ALIAS[] =
    "SELECT A.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C AS B ON B.BID=B.ID";
static const char SQL_LEFT[] =
    "SELECT A.ID,B.ID,C.ID FROM A LEFT JOIN B ON B.AID=A.ID "
    "LEFT JOIN C ON C.BID=B.ID AND C.K=B.K ORDER BY A.ID,B.ID,C.ID";
static const char SQL_ORDER[] =
    "SELECT A.ID,B.ID,C.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID ORDER BY C.ID DESC,B.ID";
static const char SQL_DISTINCT[] =
    "SELECT DISTINCT A.ID,A.ID,A.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID ORDER BY A.ID DESC";
static const char SQL_DISTINCT_PAGE[] =
    "SELECT DISTINCT A.ID,A.ID,A.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID ORDER BY 1 DESC LIMIT 1 OFFSET 1";
static const char SQL_BAD_GROUP[] =
    "SELECT A.ID,COUNT(*) FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID GROUP BY C.STATE";
static const char SQL_BAD_SUM[] =
    "SELECT SUM(C.K) FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID";
static void fail(unsigned char code) {
    TEST_DETAIL = code;
    TEST_SENTINEL = code;
    BORDER_COLOR = 2u;
    for (;;) {}
}

static void fail_value(unsigned char code, unsigned char detail) {
    TEST_DETAIL = detail;
    TEST_SENTINEL = code;
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
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static unsigned char open_sql(const char* sql, RsqlQueryOpenRequest* open) {
    open->sql = sql;
    open->sql_length = strlen(sql);
    return rsql_query_open(open);
}

static void close_sql(RsqlCursorHandle cursor) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc);
}

static void expect_rows(const char* sql, const unsigned char* values,
                        unsigned char row_count, unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    unsigned char row;
    unsigned char item;
    unsigned char rc = open_sql(sql, &open);
    if (rc != RSQL_OK || open.column_count != 3u) fail(rc ? rc : 0x80u);
    next.cursor = open.cursor;
    g_column_request.cursor = open.cursor;
    for (row = 0u; row < row_count; ++row) {
        TEST_STAGE = (unsigned char)(stage + row);
        rc = rsql_cursor_next(&next);
        if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : 0x81u);
        for (item = 0u; item < 3u; ++item) {
            g_column_request.cursor = open.cursor;
            g_column_request.column = item;
            rc = rsql_cursor_column(&g_column_request);
            if (rc != RSQL_OK || g_column_request.value.is_null ||
                g_column_request.value.type.tag != RSQL_TYPE_I16 ||
                g_column_request.value.bytes[0] !=
                    values[(rsql_u8)(row * 3u + item)] ||
                g_column_request.value.bytes[1] != 0u) {
                fail_value(rc ? rc : (unsigned char)(0x90u + item),
                           g_column_request.value.bytes[0]);
            }
        }
    }
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : 0x85u);
    close_sql(open.cursor);
}

static void expect_i64_column(RsqlCursorHandle cursor, unsigned char item,
                              signed int expected, unsigned char stage) {
    unsigned char fill = expected < 0 ? 0xFFu : 0u;
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    g_column_request.cursor = cursor;
    g_column_request.column = item;
    rc = rsql_cursor_column(&g_column_request);
    if (rc != RSQL_OK || g_column_request.value.is_null ||
        g_column_request.value.type.tag != RSQL_TYPE_I64 ||
        g_column_request.value.length != 8u ||
        g_column_request.value.bytes[0] != (unsigned char)expected ||
        g_column_request.value.bytes[1] !=
            (unsigned char)((unsigned int)expected >> 8u)) {
        fail(rc ? rc : stage);
    }
    for (index = 2u; index < 8u; ++index) {
        if (g_column_request.value.bytes[index] != fill) fail(stage);
    }
}

static RsqlCursorHandle expect_open(const char* sql, unsigned char columns,
                                    unsigned char stage);
static void expect_next(RsqlCursorHandle cursor, unsigned char has_row,
                        unsigned char stage);

static void expect_text_projection(void) {
    static const char* const expected[] = { "ALPHA", "BETA-LONG" };
    RsqlCursorHandle cursor = expect_open(SQL_TEXT, 3u, 0x9Du);
    RsqlValueReadRequest read;
    unsigned char buffer[12];
    unsigned char row;
    unsigned char rc;
    for (row = 0u; row < 2u; ++row) {
        expect_next(cursor, 1u, (unsigned char)(0x9Eu + row));
        g_column_request.cursor = cursor;
        g_column_request.column = 2u;
        rc = rsql_cursor_column(&g_column_request);
        if (rc != RSQL_OK || g_column_request.value.is_null ||
            g_column_request.value.type.tag != RSQL_TYPE_TEXT ||
            g_column_request.value.length != strlen(expected[row])) {
            fail(rc ? rc : 0xA0u);
        }
        memset(buffer, 0, sizeof(buffer));
        read.cursor = cursor;
        read.column = 2u;
        read.offset = 0u;
        read.destination = buffer;
        read.capacity = sizeof(buffer);
        rc = rsql_value_read(&read);
        if (rc != RSQL_OK || read.bytes_read != strlen(expected[row]) ||
            memcmp(buffer, expected[row], read.bytes_read) != 0) {
            fail(rc ? rc : 0xA1u);
        }
    }
    expect_next(cursor, 0u, 0xA2u);
    close_sql(cursor);
}

static void expect_left_rows(void) {
    static const unsigned char values[] = {
        1u, 10u, 100u,
        1u, 11u, 0xFFu,
        2u, 20u, 200u,
        3u, 0xFFu, 0xFFu
    };
    RsqlCursorHandle cursor = expect_open(SQL_LEFT, 3u, 0xA3u);
    unsigned char row;
    unsigned char item;
    unsigned char expected;
    unsigned char rc;
    for (row = 0u; row < 4u; ++row) {
        expect_next(cursor, 1u, (unsigned char)(0xA4u + row));
        for (item = 0u; item < 3u; ++item) {
            expected = values[(unsigned char)(row * 3u + item)];
            g_column_request.cursor = cursor;
            g_column_request.column = item;
            rc = rsql_cursor_column(&g_column_request);
            if (rc != RSQL_OK ||
                g_column_request.value.type.tag != RSQL_TYPE_I16 ||
                g_column_request.value.is_null != (expected == 0xFFu) ||
                (expected != 0xFFu &&
                 g_column_request.value.bytes[0] != expected)) {
                fail(rc ? rc : 0xA8u);
            }
        }
    }
    expect_next(cursor, 0u, 0xA9u);
    close_sql(cursor);
}


static void expect_enum_column(RsqlCursorHandle cursor, unsigned char item,
                               unsigned char expected, unsigned char stage) {
    unsigned char rc;
    TEST_STAGE = stage;
    g_column_request.cursor = cursor;
    g_column_request.column = item;
    rc = rsql_cursor_column(&g_column_request);
    if (rc != RSQL_OK || g_column_request.value.is_null ||
        g_column_request.value.type.tag != RSQL_TYPE_ENUM8 ||
        g_column_request.value.length != 1u ||
        g_column_request.value.bytes[0] != expected) {
        fail(rc ? rc : stage);
    }
}

static void expect_fixed_column(RsqlCursorHandle cursor, unsigned char item,
                                signed int raw, unsigned char stage) {
    unsigned char rc;
    TEST_STAGE = stage;
    g_column_request.cursor = cursor;
    g_column_request.column = item;
    rc = rsql_cursor_column(&g_column_request);
    if (rc != RSQL_OK || g_column_request.value.is_null ||
        g_column_request.value.type.tag != RSQL_TYPE_FIXED8_8 ||
        g_column_request.value.length != 2u ||
        g_column_request.value.bytes[0] != (unsigned char)raw ||
        g_column_request.value.bytes[1] !=
            (unsigned char)((unsigned int)raw >> 8u)) {
        fail(rc ? rc : stage);
    }
}

static void expect_float_column(RsqlCursorHandle cursor, unsigned char item,
                                const unsigned char* expected,
                                unsigned char stage) {
    unsigned char rc;
    TEST_STAGE = stage;
    g_column_request.cursor = cursor;
    g_column_request.column = item;
    rc = rsql_cursor_column(&g_column_request);
    if (rc != RSQL_OK || g_column_request.value.is_null ||
        g_column_request.value.type.tag != RSQL_TYPE_FLOAT5 ||
        g_column_request.value.length != 5u ||
        memcmp(g_column_request.value.bytes, expected, 5u) != 0) {
        fail(rc ? rc : stage);
    }
}

static RsqlCursorHandle expect_open(const char* sql, unsigned char columns,
                                    unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc;
    TEST_STAGE = stage;
    rc = open_sql(sql, &open);
    if (rc != RSQL_OK || open.column_count != columns) {
        fail(rc ? rc : stage);
    }
    return open.cursor;
}

static void expect_next(RsqlCursorHandle cursor, unsigned char has_row,
                        unsigned char stage) {
    RsqlCursorNextRequest next;
    unsigned char rc;
    TEST_STAGE = stage;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row != has_row) fail(rc ? rc : stage);
}

static void expect_aggregates(void) {
    static const signed int expected[] = { 2, 300, 15, 1, 200 };
    RsqlCursorHandle cursor = expect_open(SQL_AGGREGATE, 5u, 0x56u);
    unsigned char item;
    expect_next(cursor, 1u, 0x57u);
    for (item = 0u; item < 5u; ++item) {
        expect_i64_column(cursor, item, expected[item], 0x58u);
    }
    expect_next(cursor, 0u, 0x59u);
    close_sql(cursor);
}

static void expect_grouped(void) {
    static const unsigned char states[] = { 1u, 0u };
    static const signed int expected[2][5] = {
        { 1, 100, 10, 1, 100 },
        { 1, 200, 20, 2, 200 }
    };
    RsqlCursorHandle cursor = expect_open(SQL_GROUPED, 6u, 0x5Au);
    unsigned char row;
    unsigned char item;
    for (row = 0u; row < 2u; ++row) {
        expect_next(cursor, 1u, (unsigned char)(0x5Bu + row));
        expect_enum_column(cursor, 0u, states[row], 0x5Du);
        for (item = 0u; item < 5u; ++item) {
            expect_i64_column(cursor, (unsigned char)(item + 1u),
                              expected[row][item], 0x5Eu);
        }
    }
    expect_next(cursor, 0u, 0x5Fu);
    close_sql(cursor);
}

static void expect_numeric(void) {
    static const unsigned char FLOAT_FOUR[5] = { 0x83u, 0u, 0u, 0u, 0u };
    static const unsigned char FLOAT_TWO[5] = { 0x82u, 0u, 0u, 0u, 0u };
    RsqlCursorHandle cursor = expect_open(SQL_NUMERIC, 6u, 0x6Bu);
    expect_next(cursor, 1u, 0x6Cu);
    expect_fixed_column(cursor, 0u, 0x0300, 0x6Du);
    expect_fixed_column(cursor, 1u, 0x0180, 0x6Eu);
    expect_fixed_column(cursor, 2u, 0x0100, 0x6Fu);
    expect_fixed_column(cursor, 3u, 0x0200, 0x70u);
    expect_float_column(cursor, 4u, FLOAT_FOUR, 0x71u);
    expect_float_column(cursor, 5u, FLOAT_TWO, 0x72u);
    expect_next(cursor, 0u, 0x73u);
    close_sql(cursor);
}

static void expect_shaped_groups(void) {
    static const unsigned char states[] = { 0u, 1u };
    static const signed int sums[] = { 200, 100 };
    RsqlCursorHandle cursor = expect_open(SQL_GROUP_ORDER, 3u, 0x86u);
    unsigned char row;
    for (row = 0u; row < 2u; ++row) {
        expect_next(cursor, 1u, (unsigned char)(0x87u + row));
        expect_enum_column(cursor, 0u, states[row], 0x89u);
        expect_i64_column(cursor, 1u, 1, 0x8Au);
        expect_i64_column(cursor, 2u, sums[row], 0x8Bu);
    }
    expect_next(cursor, 0u, 0x8Cu);
    close_sql(cursor);

    cursor = expect_open(SQL_GROUP_AGG_PAGE, 3u, 0x8Du);
    expect_next(cursor, 1u, 0x8Eu);
    expect_enum_column(cursor, 0u, 1u, 0x8Fu);
    expect_i64_column(cursor, 1u, 1, 0x90u);
    expect_i64_column(cursor, 2u, 100, 0x91u);
    expect_next(cursor, 0u, 0x92u);
    close_sql(cursor);

    cursor = expect_open(SQL_GROUP_DISTINCT, 1u, 0x93u);
    expect_next(cursor, 1u, 0x94u);
    expect_i64_column(cursor, 0u, 1, 0x95u);
    expect_next(cursor, 0u, 0x96u);
    close_sql(cursor);

    cursor = expect_open(SQL_UNGROUPED_SHAPED, 1u, 0x97u);
    expect_next(cursor, 1u, 0x98u);
    expect_i64_column(cursor, 0u, 3, 0x99u);
    expect_next(cursor, 0u, 0x9Au);
    close_sql(cursor);

    cursor = expect_open(SQL_UNGROUPED_OFFSET, 1u, 0x9Bu);
    expect_next(cursor, 0u, 0x9Cu);
    close_sql(cursor);
}

static void expect_open_error(const char* sql, unsigned char expected,
                              unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc = open_sql(sql, &open);
    if (rc != expected) fail(rc ? rc : stage);
}

int main(void) {
    static const unsigned char INNER_ROWS[] = {
        1u, 10u, 100u,
        2u, 20u, 200u
    };
    static const unsigned char CROSS_ROWS[] = {
        1u, 11u, 101u,
        2u, 20u, 200u
    };
    static const unsigned char ORDER_ROWS[] = {
        2u, 20u, 200u,
        1u, 11u, 101u,
        1u, 10u, 100u
    };
    static const unsigned char DISTINCT_ROWS[] = {
        2u, 2u, 2u,
        1u, 1u, 1u
    };
    static const unsigned char DISTINCT_PAGE_ROW[] = { 1u, 1u, 1u };
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
        fail(0x10u);
    }
    for (index = 0u; index < sizeof(SETUP) / sizeof(SETUP[0]); ++index) {
        exec_ok(SETUP[index], (unsigned char)(0x20u + index));
    }
    expect_rows(SQL_INNER, INNER_ROWS, 2u, 0x40u);
    expect_rows(SQL_CROSS, CROSS_ROWS, 2u, 0x50u);
    expect_text_projection();
    expect_left_rows();
    expect_rows(SQL_ORDER, ORDER_ROWS, 3u, 0x76u);
    expect_rows(SQL_DISTINCT, DISTINCT_ROWS, 2u, 0x7Cu);
    expect_rows(SQL_DISTINCT_PAGE, DISTINCT_PAGE_ROW, 1u, 0x7Eu);
    expect_aggregates();
    expect_grouped();
    expect_numeric();
    expect_shaped_groups();
    expect_open_error(SQL_AMBIGUOUS, RSQL_ERR_TYPE_MISMATCH, 0x60u);
    expect_open_error(SQL_DUP_ALIAS, RSQL_ERR_TYPE_MISMATCH, 0x61u);
    exec_ok(SQL_CTAS, 0x64u);
    expect_rows(SQL_CTAS_READ, INNER_ROWS, 2u, 0x65u);
    expect_open_error(SQL_BAD_GROUP, RSQL_ERR_UNSUPPORTED_SQL, 0x74u);
    expect_open_error(SQL_BAD_SUM, RSQL_ERR_TYPE_MISMATCH, 0x75u);
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

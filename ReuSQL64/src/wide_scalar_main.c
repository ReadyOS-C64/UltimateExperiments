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
    "CREATE TABLE A(ID I16,K CHAR(3),T TEXT)",
    "CREATE TABLE B(ID I16,AID I16,K CHAR(3),RAW BLOB)",
    "CREATE TABLE C(ID I16,BID I16,K CHAR(3),T TEXT,RAW BLOB)",
    "INSERT INTO A VALUES(1,'BY','OUTER-ONE')",
    "INSERT INTO A VALUES(2,'Z','OTHER')",
    "INSERT INTO B VALUES(10,1,'AX',X'10')",
    "INSERT INTO B VALUES(20,2,'LM',X'20')",
    "INSERT INTO B VALUES(30,1,'AX',X'01')",
    "INSERT INTO C VALUES(100,10,'BY','ALPHA',X'0102')",
    "INSERT INTO C VALUES(200,20,'A','BETA',X'01FF')",
    "INSERT INTO C VALUES(300,30,'BY','alpha',X'0102')",
    "CREATE INDEX IA ON A(ID)",
    "CREATE INDEX IB ON B(AID,ID)",
    "CREATE INDEX IC ON C(BID,ID)"
};

static const char SQL_SCALAR[] =
    "SELECT LENGTH(C.K),SUBSTR(C.K,2,1),A.K||C.K,CONCAT('Q',B.K) "
    "FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID WHERE C.ID=100";

static const char SQL_ORDER[] =
    "SELECT LENGTH(C.K),C.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1 DESC,C.ID";

static const char SQL_DISTINCT[] =
    "SELECT DISTINCT A.K||C.K FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1";

static const char SQL_SHAPED_PAGE[] =
    "SELECT DISTINCT SUBSTR(C.K,2,1) FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1 DESC LIMIT 1 OFFSET 1";

static const char SQL_TEXT_ORDER[] =
    "SELECT C.T,C.ID FROM A JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID "
    "WHERE C.ID<400 ORDER BY C.T DESC,C.ID";

static const char SQL_TEXT_DISTINCT[] =
    "SELECT DISTINCT C.T FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1";

static const char SQL_BLOB_DISTINCT[] =
    "SELECT DISTINCT C.RAW FROM A USING INDEX IA JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1 DESC";

static const char SQL_VARIABLE_WHERE[] =
    "SELECT C.ID FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID "
    "WHERE A.T LIKE 'OUT%' AND B.RAW>=X'10' AND C.T LIKE 'AL%'";

static const char SQL_TEXT_SCALAR[] =
    "SELECT LENGTH(C.T),SUBSTR(C.T,2,3),A.T||C.K,CONCAT(B.K,C.T) "
    "FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID WHERE C.ID=100";

static const char SQL_TEXT_LENGTH_ORDER[] =
    "SELECT LENGTH(C.T),C.ID FROM A USING INDEX IA "
    "JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1,C.ID";

static const char SQL_TEXT_SUBSTR_ORDER[] =
    "SELECT SUBSTR(C.T,2,3),C.ID FROM A JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1 DESC,C.ID";

static const char SQL_TEXT_CONCAT_DISTINCT[] =
    "SELECT DISTINCT A.T||C.T FROM A JOIN B ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID WHERE C.ID<400 ORDER BY 1";

static const char SQL_INDEX_ALL[] =
    "SELECT A.ID,B.ID,C.ID FROM A USING INDEX ia "
    "JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID";

static const char SQL_INDEX_SINGLE[] =
    "SELECT ID FROM A USING INDEX IA";

static const char SQL_INDEX_GROUP[] =
    "SELECT A.ID,COUNT(*),SUM(C.ID) FROM A USING INDEX IA "
    "JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID GROUP BY A.ID ORDER BY 3 DESC";

static const char SQL_INDEX_MISSING[] =
    "SELECT A.ID FROM A USING INDEX NOPE JOIN B ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID";

static const char SQL_INDEX_WRONG_TABLE[] =
    "SELECT A.ID FROM A JOIN B USING INDEX IC ON B.AID=A.ID "
    "JOIN C ON C.BID=B.ID";

static const char SQL_JOIN_INDEXED_SHAPED[] =
    "SELECT A.T||'!',B.ID FROM A USING INDEX IA "
    "JOIN B USING INDEX IB ON B.AID=A.ID "
    "WHERE A.T LIKE 'OUT%' ORDER BY 2 DESC";

static const char SQL_JOIN_INDEX_MISSING[] =
    "SELECT A.ID FROM A USING INDEX NOPE JOIN B ON B.AID=A.ID";

static const char SQL_JOIN_INDEX_WRONG_TABLE[] =
    "SELECT A.ID FROM A JOIN B USING INDEX IC ON B.AID=A.ID";

static const char SQL_CTAS_VARIABLE[] =
    "CREATE TABLE WTEXT AS SELECT A.ID,C.T,A.T||C.T,LENGTH(C.T) "
    "FROM A USING INDEX IA JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID WHERE C.ID<400 ORDER BY C.ID";

static const char SQL_CTAS_VARIABLE_READ[] = "SELECT*FROM WTEXT";

static const char SQL_CTAS_AGGREGATE[] =
    "CREATE TABLE WAGG AS SELECT A.ID,COUNT(*),SUM(C.ID) "
    "FROM A USING INDEX IA JOIN B USING INDEX IB ON B.AID=A.ID "
    "JOIN C USING INDEX IC ON C.BID=B.ID GROUP BY A.ID ORDER BY A.ID";

static const char SQL_CTAS_AGGREGATE_READ[] =
    "SELECT*FROM WAGG ORDER BY C1";

static void fail(unsigned char code) {
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

static void expect_bytes(RsqlCursorHandle cursor, unsigned char column,
                         const void* expected, unsigned char length,
                         unsigned char stage) {
    RsqlValueReadRequest read;
    unsigned char bytes[16];
    unsigned char rc;
    TEST_STAGE = stage;
    memset(bytes, 0, sizeof(bytes));
    read.cursor = cursor;
    read.column = column;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != length ||
        memcmp(bytes, expected, length) != 0) fail(rc ? rc : stage);
}

static void close_ok(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    TEST_STAGE = stage;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static RsqlCursorHandle open_ok(const char* sql, unsigned char columns,
                                unsigned char stage) {
    RsqlQueryOpenRequest open;
    unsigned char rc;
    TEST_STAGE = stage;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != columns) fail(rc ? rc : stage);
    return open.cursor;
}

static unsigned int expect_i16(RsqlCursorHandle cursor, unsigned char column,
                               unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char rc;
    TEST_STAGE = stage;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I16 || request.value.length != 2u) {
        fail(rc ? rc : stage);
    }
    return (unsigned int)request.value.bytes[0] |
        ((unsigned int)request.value.bytes[1] << 8u);
}

static void expect_i64(RsqlCursorHandle cursor, unsigned char column,
                       unsigned int expected, unsigned char stage) {
    RsqlCursorColumnRequest request;
    unsigned char index;
    unsigned char rc;
    TEST_STAGE = stage;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.type.tag != RSQL_TYPE_I64 ||
        request.value.length != 8u ||
        request.value.bytes[0] != (unsigned char)expected ||
        request.value.bytes[1] != (unsigned char)(expected >> 8u)) {
        fail(rc ? rc : stage);
    }
    for (index = 2u; index < 8u; ++index) {
        if (request.value.bytes[index] != 0u) fail(stage);
    }
}

static void next_ok(RsqlCursorHandle cursor, unsigned char expected,
                    unsigned char stage) {
    RsqlCursorNextRequest next;
    unsigned char rc;
    TEST_STAGE = stage;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row != expected) fail(rc ? rc : stage);
}

static void test_scalar_shaping(void) {
    static const unsigned int IDS[] = { 100u, 300u, 200u };
    static const char* const DISTINCT_VALUES[] = { "BYBY", "ZA" };
    static const unsigned char DISTINCT_LENGTHS[] = { 4u, 2u };
    RsqlCursorHandle cursor;
    unsigned int actual;
    unsigned char index;

    cursor = open_ok(SQL_ORDER, 2u, 0x40u);
    for (index = 0u; index < 3u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0x41u + index));
        actual = expect_i16(cursor, 1u, (unsigned char)(0x44u + index));
        if (actual != IDS[index]) fail((unsigned char)actual);
    }
    next_ok(cursor, 0u, 0x47u);
    close_ok(cursor, 0x48u);

    cursor = open_ok(SQL_DISTINCT, 1u, 0x49u);
    for (index = 0u; index < 2u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0x4Au + index));
        expect_bytes(cursor, 0u, DISTINCT_VALUES[index],
                     DISTINCT_LENGTHS[index], (unsigned char)(0x4Cu + index));
    }
    next_ok(cursor, 0u, 0x4Eu);
    close_ok(cursor, 0x4Fu);

    cursor = open_ok(SQL_SHAPED_PAGE, 1u, 0x50u);
    next_ok(cursor, 1u, 0x51u);
    expect_bytes(cursor, 0u, "", 0u, 0x52u);
    next_ok(cursor, 0u, 0x53u);
    close_ok(cursor, 0x54u);

}

static void test_variable_shaping(void) {
    static const unsigned int IDS[] = { 200u, 100u, 300u };
    static const char* const TEXT_ORDER[] = { "BETA", "ALPHA", "alpha" };
    static const unsigned char TEXT_LENGTHS[] = { 4u, 5u, 5u };
    static const unsigned char BLOB_HIGH[] = { 0x01u, 0xFFu };
    static const unsigned char BLOB_LOW[] = { 0x01u, 0x02u };
    RsqlCursorHandle cursor;
    unsigned char index;

    cursor = open_ok(SQL_TEXT_ORDER, 2u, 0x60u);
    for (index = 0u; index < 3u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0x61u + index));
        expect_bytes(cursor, 0u, TEXT_ORDER[index], TEXT_LENGTHS[index],
                     (unsigned char)(0x64u + index));
        if (expect_i16(cursor, 1u, (unsigned char)(0x67u + index)) !=
            IDS[index]) fail((unsigned char)(0x6Au + index));
    }
    next_ok(cursor, 0u, 0x6Du);
    close_ok(cursor, 0x6Eu);

    cursor = open_ok(SQL_TEXT_DISTINCT, 1u, 0x70u);
    next_ok(cursor, 1u, 0x71u);
    expect_bytes(cursor, 0u, "ALPHA", 5u, 0x72u);
    next_ok(cursor, 1u, 0x73u);
    expect_bytes(cursor, 0u, "BETA", 4u, 0x74u);
    next_ok(cursor, 0u, 0x75u);
    close_ok(cursor, 0x76u);

    cursor = open_ok(SQL_BLOB_DISTINCT, 1u, 0x77u);
    next_ok(cursor, 1u, 0x78u);
    expect_bytes(cursor, 0u, BLOB_HIGH, 2u, 0x79u);
    next_ok(cursor, 1u, 0x7Au);
    expect_bytes(cursor, 0u, BLOB_LOW, 2u, 0x7Bu);
    next_ok(cursor, 0u, 0x7Cu);
    close_ok(cursor, 0x7Du);

    cursor = open_ok(SQL_VARIABLE_WHERE, 1u, 0x7Eu);
    next_ok(cursor, 1u, 0x7Fu);
    if (expect_i16(cursor, 0u, 0x80u) != 100u) fail(0x81u);
    next_ok(cursor, 0u, 0x82u);
    close_ok(cursor, 0x83u);
}

static void test_text_scalar_projection(void) {
    static const unsigned char FIVE[] = { 5u, 0u, 0u, 0u };
    RsqlCursorHandle cursor;
    cursor = open_ok(SQL_TEXT_SCALAR, 4u, 0x84u);
    next_ok(cursor, 1u, 0x85u);
    expect_bytes(cursor, 0u, FIVE, 4u, 0x86u);
    expect_bytes(cursor, 1u, "LPH", 3u, 0x87u);
    expect_bytes(cursor, 2u, "OUTER-ONEBY", 11u, 0x88u);
    expect_bytes(cursor, 3u, "AXALPHA", 7u, 0x89u);
    next_ok(cursor, 0u, 0x8Au);
    close_ok(cursor, 0x8Bu);
}

static void test_text_scalar_shaping(void) {
    static const unsigned int LENGTH_IDS[] = { 200u, 100u, 300u };
    static const unsigned int SUBSTR_IDS[] = { 100u, 300u, 200u };
    static const char* const DISTINCT_VALUES[] = {
        "OTHERBETA", "OUTER-ONEALPHA"
    };
    static const unsigned char DISTINCT_LENGTHS[] = { 9u, 14u };
    RsqlCursorHandle cursor;
    unsigned char index;

    cursor = open_ok(SQL_TEXT_LENGTH_ORDER, 2u, 0x8Cu);
    for (index = 0u; index < 3u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0x8Du + index));
        if (expect_i16(cursor, 1u, (unsigned char)(0x90u + index)) !=
            LENGTH_IDS[index]) fail((unsigned char)(0x93u + index));
    }
    next_ok(cursor, 0u, 0x96u);
    close_ok(cursor, 0x97u);

    cursor = open_ok(SQL_TEXT_SUBSTR_ORDER, 2u, 0x98u);
    for (index = 0u; index < 3u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0x99u + index));
        if (expect_i16(cursor, 1u, (unsigned char)(0x9Cu + index)) !=
            SUBSTR_IDS[index]) fail((unsigned char)(0x9Fu + index));
    }
    next_ok(cursor, 0u, 0xA2u);
    close_ok(cursor, 0xA3u);

    cursor = open_ok(SQL_TEXT_CONCAT_DISTINCT, 1u, 0xA6u);
    for (index = 0u; index < 2u; ++index) {
        next_ok(cursor, 1u, (unsigned char)(0xA7u + index));
        expect_bytes(cursor, 0u, DISTINCT_VALUES[index],
                     DISTINCT_LENGTHS[index], (unsigned char)(0xA9u + index));
    }
    next_ok(cursor, 0u, 0xABu);
    close_ok(cursor, 0xACu);
}

static void test_index_access_paths(void) {
    static const unsigned int ROWS[3][3] = {
        { 2u, 20u, 200u },
        { 1u, 30u, 300u },
        { 1u, 10u, 100u }
    };
    static const unsigned int GROUP_IDS[] = { 1u, 2u };
    static const unsigned int GROUP_COUNTS[] = { 2u, 1u };
    static const unsigned int GROUP_SUMS[] = { 400u, 200u };
    RsqlQueryOpenRequest open;
    RsqlCursorHandle cursor;
    unsigned char column;
    unsigned char row;
    unsigned char rc;

    cursor = open_ok(SQL_INDEX_SINGLE, 1u, 0xADu);
    next_ok(cursor, 1u, 0xAEu);
    row = (unsigned char)expect_i16(cursor, 0u, 0xAFu);
    if (row != 2u) {
        TEST_DETAIL = row;
        fail(0xAFu);
    }
    close_ok(cursor, 0xB0u);

    cursor = open_ok(SQL_INDEX_ALL, 3u, 0xB0u);
    for (row = 0u; row < 3u; ++row) {
        next_ok(cursor, 1u, (unsigned char)(0xB1u + row));
        for (column = 0u; column < 3u; ++column) {
            unsigned int actual = expect_i16(cursor, column,
                (unsigned char)(0xB4u + column));
            if (actual != ROWS[row][column]) {
                TEST_DETAIL = (unsigned char)actual;
                fail((unsigned char)(0xB7u + row));
            }
        }
    }
    next_ok(cursor, 0u, 0xBAu);
    close_ok(cursor, 0xBBu);

    cursor = open_ok(SQL_INDEX_GROUP, 3u, 0xBCu);
    for (row = 0u; row < 2u; ++row) {
        next_ok(cursor, 1u, (unsigned char)(0xBDu + row));
        if (expect_i16(cursor, 0u, 0xBFu) != GROUP_IDS[row]) fail(0xC0u);
        expect_i64(cursor, 1u, GROUP_COUNTS[row], 0xC1u);
        expect_i64(cursor, 2u, GROUP_SUMS[row], 0xC2u);
    }
    next_ok(cursor, 0u, 0xC3u);
    close_ok(cursor, 0xC4u);

    TEST_STAGE = 0xC5u;
    open.sql = SQL_INDEX_MISSING;
    open.sql_length = strlen(SQL_INDEX_MISSING);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_NOT_FOUND) fail(rc ? rc : 0xC5u);
    TEST_STAGE = 0xC6u;
    open.sql = SQL_INDEX_WRONG_TABLE;
    open.sql_length = strlen(SQL_INDEX_WRONG_TABLE);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xC6u);
}

static void test_two_source_indexes(void) {
    static const unsigned int IDS[] = { 30u, 10u };
    RsqlQueryOpenRequest open;
    RsqlCursorHandle cursor;
    unsigned char row;
    unsigned char rc;

    cursor = open_ok(SQL_JOIN_INDEXED_SHAPED, 2u, 0xDDu);
    for (row = 0u; row < 2u; ++row) {
        next_ok(cursor, 1u, (unsigned char)(0xDEu + row));
        expect_bytes(cursor, 0u, "OUTER-ONE!", 10u, 0xE0u);
        if (expect_i16(cursor, 1u, 0xE1u) != IDS[row]) fail(0xE2u);
    }
    next_ok(cursor, 0u, 0xE3u);
    close_ok(cursor, 0xE4u);

    TEST_STAGE = 0xE5u;
    open.sql = SQL_JOIN_INDEX_MISSING;
    open.sql_length = strlen(SQL_JOIN_INDEX_MISSING);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_NOT_FOUND) fail(rc ? rc : 0xE5u);
    TEST_STAGE = 0xE6u;
    open.sql = SQL_JOIN_INDEX_WRONG_TABLE;
    open.sql_length = strlen(SQL_JOIN_INDEX_WRONG_TABLE);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xE6u);
}

static void test_wide_ctas(void) {
    static const unsigned int IDS[] = { 1u, 2u, 1u };
    static const char* const TEXTS[] = { "ALPHA", "BETA", "alpha" };
    static const unsigned char TEXT_LENGTHS[] = { 5u, 4u, 5u };
    static const char* const CONCAT[] = {
        "OUTER-ONEALPHA", "OTHERBETA", "OUTER-ONEalpha"
    };
    static const unsigned char CONCAT_LENGTHS[] = { 14u, 9u, 14u };
    static const unsigned char LENGTHS[][4] = {
        { 5u, 0u, 0u, 0u }, { 4u, 0u, 0u, 0u },
        { 5u, 0u, 0u, 0u }
    };
    static const unsigned int GROUP_IDS[] = { 1u, 2u };
    static const unsigned int GROUP_COUNTS[] = { 2u, 1u };
    static const unsigned int GROUP_SUMS[] = { 400u, 200u };
    RsqlCursorHandle cursor;
    unsigned char row;
    exec_ok(SQL_CTAS_VARIABLE, 0xC7u);
    cursor = open_ok(SQL_CTAS_VARIABLE_READ, 4u, 0xC8u);
    for (row = 0u; row < 3u; ++row) {
        next_ok(cursor, 1u, (unsigned char)(0xC9u + row));
        {
            unsigned int actual = expect_i16(cursor, 0u, 0xCCu);
            if (actual != IDS[row]) {
                TEST_DETAIL = (unsigned char)(actual +
                    (unsigned char)(IDS[row] << 4u));
                fail(0xCDu);
            }
        }
        expect_bytes(cursor, 1u, TEXTS[row], TEXT_LENGTHS[row], 0xCEu);
        expect_bytes(cursor, 2u, CONCAT[row], CONCAT_LENGTHS[row], 0xCFu);
        expect_bytes(cursor, 3u, LENGTHS[row], 4u, 0xD0u);
    }
    next_ok(cursor, 0u, 0xD1u);
    close_ok(cursor, 0xD2u);

    exec_ok(SQL_CTAS_AGGREGATE, 0xD3u);
    cursor = open_ok(SQL_CTAS_AGGREGATE_READ, 3u, 0xD4u);
    for (row = 0u; row < 2u; ++row) {
        next_ok(cursor, 1u, (unsigned char)(0xD5u + row));
        if (expect_i16(cursor, 0u, 0xD7u) != GROUP_IDS[row]) fail(0xD8u);
        expect_i64(cursor, 1u, GROUP_COUNTS[row], 0xD9u);
        expect_i64(cursor, 2u, GROUP_SUMS[row], 0xDAu);
    }
    next_ok(cursor, 0u, 0xDBu);
    close_ok(cursor, 0xDCu);
}

int main(void) {
    RsqlInitRequest init;
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
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
    TEST_STAGE = 0x30u;
    open.sql = SQL_SCALAR;
    open.sql_length = strlen(SQL_SCALAR);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 4u) fail(rc ? rc : 0x30u);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(rc ? rc : 0x31u);
    column.cursor = open.cursor;
    column.column = 0u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_I16 ||
        column.value.length != 2u || column.value.bytes[0] != 2u) {
        fail(rc ? rc : 0x32u);
    }
    expect_bytes(open.cursor, 1u, "Y", 1u, 0x33u);
    expect_bytes(open.cursor, 2u, "BYBY", 4u, 0x34u);
    expect_bytes(open.cursor, 3u, "QAX", 3u, 0x35u);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : 0x36u);
    close_ok(open.cursor, 0x37u);
    test_scalar_shaping();
    test_variable_shaping();
    test_text_scalar_projection();
    test_text_scalar_shaping();
    test_index_access_paths();
    test_wide_ctas();
    test_two_source_indexes();
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

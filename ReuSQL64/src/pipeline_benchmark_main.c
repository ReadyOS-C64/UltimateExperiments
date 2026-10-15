#include <string.h>

#include "rsql.h"
#include "rsql_catalog.h"
#include "rsql_overlay.h"
#include "rsql_row.h"
#include "storage_layout.h"

#define TEST_SENTINEL (*(volatile rsql_u8*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile rsql_u8*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile rsql_u8*)0xCFF2)
#define TEST_STAGE (*(volatile rsql_u8*)0xCFF3)
#define TIMER_LO (*(volatile rsql_u8*)0xCFF4)
#define TIMER_MID (*(volatile rsql_u8*)0xCFF5)
#define TIMER_HI (*(volatile rsql_u8*)0xCFF6)
#define BENCHMARK_CONTROL (*(volatile rsql_u8*)0xCFFF)
#define BORDER_COLOR (*(volatile rsql_u8*)0xD020)

#define JIFFY_HI (*(volatile rsql_u8*)0x00A0)
#define JIFFY_MID (*(volatile rsql_u8*)0x00A1)
#define JIFFY_LO (*(volatile rsql_u8*)0x00A2)

#define ORDER_COUNT 128u
#define PIPELINE_STEPS 7u
#define fixture_buffer ((rsql_u8*)0x0400)
#define timing_ledger ((volatile rsql_u8*)0x0400)

static const char SQL_CUSTOMERS[] =
    "CREATE TABLE CUSTOMERS(CUSTOMER_ID I16,REGION I8,ACTIVE BOOLEAN,"
    "NAME CHAR(80))";
static const char SQL_PRODUCTS[] =
    "CREATE TABLE PRODUCTS(PRODUCT_ID I8,CATEGORY_ID I8,ACTIVE BOOLEAN,"
    "NAME CHAR(16))";
static const char SQL_ORDERS[] =
    "CREATE TABLE SALES_ORDERS(ORDER_ID I16,CUSTOMER_ID I16,PRODUCT_ID I8,"
    "ORDER_TOTAL I32,ITEM_COUNT I16,DETAILS CHAR(80))";
static const char SQL_CUSTOMER_1[] =
    "INSERT INTO CUSTOMERS VALUES(1,1,TRUE,'C-0001')";
static const char SQL_CUSTOMER_2[] =
    "INSERT INTO CUSTOMERS VALUES(2,2,TRUE,'C-0002')";
static const char SQL_PRODUCT_0[] =
    "INSERT INTO PRODUCTS VALUES(0,0,TRUE,'P-0000')";
static const char SQL_PRODUCT_1[] =
    "INSERT INTO PRODUCTS VALUES(1,1,TRUE,'P-0001')";
static const char SQL_CUSTOMER_INDEX[] =
    "CREATE INDEX CUSTOMER_ID_REGION ON CUSTOMERS(CUSTOMER_ID,REGION)";
static const char SQL_PRODUCT_INDEX[] =
    "CREATE INDEX PRODUCT_ID_CATEGORY ON PRODUCTS(PRODUCT_ID,CATEGORY_ID)";

/* CTAS currently assigns C1..Cn to projected columns. The comments preserve
 * their business meanings at each deliberately narrow pipeline boundary. */
static const char SQL_FILTER_ORDERS[] =
    "CREATE TEMP TABLE FILTERED_ORDERS AS "
    "SELECT ORDER_ID,CUSTOMER_ID,PRODUCT_ID,ORDER_TOTAL,ITEM_COUNT "
    "FROM SALES_ORDERS WHERE ORDER_TOTAL>=1000 AND ITEM_COUNT>=2 "
    "AND DETAILS LIKE 'A%'";
static const char SQL_FILTERED_INDEX[] =
    "CREATE INDEX FILTERED_BUYER_PRODUCT ON FILTERED_ORDERS(C2,C3)";
/* CUSTOMER_SALES: C1 order, C2 product, C3 total, C4 items, C5 region. */
static const char SQL_JOIN_CUSTOMERS[] =
    "CREATE TEMP TABLE CUSTOMER_SALES AS "
    "SELECT O.C1,O.C3,O.C4,O.C5,C.REGION "
    "FROM FILTERED_ORDERS AS O USING INDEX FILTERED_BUYER_PRODUCT "
    "JOIN CUSTOMERS AS C USING INDEX CUSTOMER_ID_REGION "
    "ON C.CUSTOMER_ID=O.C2 WHERE C.ACTIVE=TRUE";
static const char SQL_CUSTOMER_SALES_INDEX[] =
    "CREATE INDEX CUSTOMER_PRODUCT_REGION ON CUSTOMER_SALES(C2,C5)";
/* READY_SALES: C1 total, C2 items, C3 region, C4 category. */
static const char SQL_JOIN_PRODUCTS[] =
    "CREATE TEMP TABLE READY_SALES AS "
    "SELECT S.C3,S.C4,S.C5,P.CATEGORY_ID "
    "FROM CUSTOMER_SALES AS S USING INDEX CUSTOMER_PRODUCT_REGION "
    "JOIN PRODUCTS AS P USING INDEX PRODUCT_ID_CATEGORY "
    "ON P.PRODUCT_ID=S.C2 WHERE P.ACTIVE=TRUE";
static const char SQL_READY_INDEX[] =
    "CREATE INDEX READY_REGION_CATEGORY ON READY_SALES(C3,C4)";
static const char SQL_SUMMARY[] =
    "SELECT C3,C4,COUNT(*),SUM(C1),AVG(C2),MIN(C1),MAX(C1) "
    "FROM READY_SALES USING INDEX READY_REGION_CATEGORY GROUP BY C3,C4 "
    "ORDER BY C3,C4";

static rsql_u8 total_start[3];
static rsql_u8 clock_start[3];
static rsql_u8 clock_end[3];

static void fail(rsql_u8 stage, rsql_u8 detail) {
    TEST_STAGE = stage;
    TIMER_LO = detail;
    TEST_SENTINEL = detail ? detail : 0xFFu;
    BORDER_COLOR = 2u;
    for (;;) {}
}

static void read_clock(rsql_u8* result) {
    __asm__("sei");
    result[0] = JIFFY_LO;
    result[1] = JIFFY_MID;
    result[2] = JIFFY_HI;
    __asm__("cli");
}

static void subtract_clock(const rsql_u8* start, const rsql_u8* end,
                           volatile rsql_u8* destination) {
    rsql_u8 borrow;
    destination[0] = (rsql_u8)(end[0] - start[0]);
    borrow = end[0] < start[0];
    destination[1] = (rsql_u8)(end[1] - start[1] - borrow);
    borrow = (rsql_u8)(end[1] - borrow) < start[1];
    destination[2] = (rsql_u8)(end[2] - start[2] - borrow);
}

static void exec_ok(const char* sql, rsql_u8 stage) {
    RsqlExecRequest request;
    rsql_u8 rc;
    TEST_STAGE = stage;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK) fail(stage, rc);
}

static void timed_exec(const char* sql, rsql_u8 expected_rows,
                       rsql_u8 check_rows, rsql_u8 step, rsql_u8 stage) {
    RsqlExecRequest request;
    rsql_u8 rc;
    TEST_STAGE = stage;
    read_clock(clock_start);
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    read_clock(clock_end);
    subtract_clock(clock_start, clock_end, &timing_ledger[step * 3u]);
    if (rc != RSQL_OK) fail(stage, rc);
    if (check_rows &&
        (request.output.affected_rows.bytes[0] != expected_rows ||
         request.output.affected_rows.bytes[1] != 0u)) {
        fail(stage, request.output.affected_rows.bytes[0]);
    }
}

static void fill_order(rsql_u8* row, rsql_u16 order_id) {
    rsql_u16 sequence = (rsql_u16)(order_id - 1u);
    memset(row, 0, 92u);
    rsql_put_u16(&row[1], order_id);
    rsql_put_u16(&row[3], (rsql_u16)(sequence % 2u + 1u));
    row[5] = (rsql_u8)(sequence % 2u);
    rsql_put_u32(&row[6], 500ul + (unsigned long)(sequence % 20u) * 100ul);
    rsql_put_u16(&row[10], (rsql_u16)(sequence % 5u + 1u));
    memset(&row[12], ' ', 80u);
    row[12] = sequence % 7u < 3u ? 'A' : 'B';
    row[13] = '-';
}

static void insert_orders(void) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    rsql_u16 order_id;
    rsql_u8 rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("SALES_ORDERS", &table);
    if (rc != RSQL_OK || table.row_width != 92u) {
        fail(0x28u, rc ? rc : (rsql_u8)table.row_width);
    }
    rc = rsql_overlay_load(1u);
    if (rc != RSQL_OK) fail(0x29u, rc);
    for (order_id = 1u; order_id <= ORDER_COUNT; ++order_id) {
        fill_order(fixture_buffer, order_id);
        rc = rsql_row_insert(table.table_page, fixture_buffer, 92u, &row_id);
        if (rc != RSQL_OK) fail(0x2Au, rc);
    }
}

static void next_row(RsqlCursorHandle cursor, rsql_u8 expected,
                     rsql_u8 stage) {
    RsqlCursorNextRequest request;
    rsql_u8 rc;
    request.cursor = cursor;
    rc = rsql_cursor_next(&request);
    if (rc != RSQL_OK || request.has_row != expected) {
        fail(stage, rc ? rc : request.has_row);
    }
}

static void expect_integer(RsqlCursorHandle cursor, rsql_u8 column,
                           unsigned long expected, rsql_u8 length,
                           rsql_u8 stage) {
    RsqlCursorColumnRequest request;
    rsql_u8 byte;
    rsql_u8 rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.length != length) fail(stage, rc ? rc : request.value.length);
    for (byte = 0u; byte < length; ++byte) {
        rsql_u8 wanted = byte < 4u
            ? (rsql_u8)(expected >> (byte * 8u)) : 0u;
        if (request.value.bytes[byte] != wanted) fail(stage, byte);
    }
}

static void run_summary(rsql_u8 ledger_step, rsql_u8 stage) {
    static const rsql_u8 regions[] = {1u, 2u};
    static const rsql_u8 categories[] = {0u, 1u};
    static const unsigned long counts[] = {16ul, 17ul};
    static const unsigned long sums[] = {28000ul, 30000ul};
    static const unsigned long minimums[] = {1100ul, 1200ul};
    static const unsigned long maximums[] = {2300ul, 2400ul};
    RsqlQueryOpenRequest open;
    RsqlQueryCloseRequest close;
    rsql_u8 row;
    rsql_u8 rc;
    TEST_STAGE = stage;
    read_clock(clock_start);
    open.sql = SQL_SUMMARY;
    open.sql_length = strlen(SQL_SUMMARY);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 7u) {
        fail(stage, rc ? rc : open.column_count);
    }
    for (row = 0u; row < 2u; ++row) {
        next_row(open.cursor, 1u, (rsql_u8)(stage + 1u));
        expect_integer(open.cursor, 0u, regions[row], 1u, stage);
        expect_integer(open.cursor, 1u, categories[row], 1u, stage);
        expect_integer(open.cursor, 2u, counts[row], 8u, stage);
        expect_integer(open.cursor, 3u, sums[row], 8u, stage);
        expect_integer(open.cursor, 4u, 3ul, 8u, stage);
        expect_integer(open.cursor, 5u, minimums[row], 8u, stage);
        expect_integer(open.cursor, 6u, maximums[row], 8u, stage);
    }
    next_row(open.cursor, 0u, (rsql_u8)(stage + 2u));
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    read_clock(clock_end);
    if (rc != RSQL_OK) fail(stage, rc);
    if (ledger_step < PIPELINE_STEPS) {
        subtract_clock(clock_start, clock_end,
                       &timing_ledger[ledger_step * 3u]);
    }
}

int main(void) {
    RsqlInitRequest init;
    rsql_u8 rc;
    BORDER_COLOR = 0u;
    BENCHMARK_CONTROL = 0u;
    memset(&init, 0, sizeof(init));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail(0x10u, rc);
    if (rsql_reu_size_kib() != (rsql_u16)(512u << REU_SIZE_SELECTOR)) {
        fail(0x11u, (rsql_u8)rsql_reu_size_kib());
    }

    exec_ok(SQL_CUSTOMERS, 0x20u);
    exec_ok(SQL_PRODUCTS, 0x21u);
    exec_ok(SQL_ORDERS, 0x22u);
    exec_ok(SQL_CUSTOMER_1, 0x23u);
    exec_ok(SQL_CUSTOMER_2, 0x24u);
    exec_ok(SQL_PRODUCT_0, 0x25u);
    exec_ok(SQL_PRODUCT_1, 0x26u);
    insert_orders();
    exec_ok(SQL_CUSTOMER_INDEX, 0x2Bu);
    exec_ok(SQL_PRODUCT_INDEX, 0x2Cu);
    memset((void*)timing_ledger, 0, PIPELINE_STEPS * 3u);

    TEST_STAGE = 0xB1u;
    read_clock(total_start);
    timed_exec(SQL_FILTER_ORDERS, 33u, 1u, 0u, 0x40u);
    timed_exec(SQL_FILTERED_INDEX, 0u, 0u, 1u, 0x44u);
    timed_exec(SQL_JOIN_CUSTOMERS, 33u, 1u, 2u, 0x48u);
    timed_exec(SQL_CUSTOMER_SALES_INDEX, 0u, 0u, 3u, 0x4Cu);
    timed_exec(SQL_JOIN_PRODUCTS, 33u, 1u, 4u, 0x50u);
    timed_exec(SQL_READY_INDEX, 0u, 0u, 5u, 0x54u);
    run_summary(6u, 0x58u);
    read_clock(clock_end);
    subtract_clock(total_start, clock_end, &TIMER_LO);
    TEST_STAGE = 0xB2u;
    while (BENCHMARK_CONTROL < 1u) {}

    TEST_STAGE = 0xC1u;
    read_clock(total_start);
    run_summary(PIPELINE_STEPS, 0x60u);
    read_clock(clock_end);
    subtract_clock(total_start, clock_end, &TIMER_LO);
    TEST_STAGE = 0xC2u;
    while (BENCHMARK_CONTROL < 2u) {}

    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

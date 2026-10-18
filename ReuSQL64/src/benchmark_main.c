#include <string.h>

#include "rsql.h"
#include "rsql_catalog.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_reu.h"
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
#define ARCHIVE_COUNT 1920u
#define CUSTOMER_COUNT 2u
#define PRODUCT_COUNT 2u
#define RULE_COUNT 2u
#define FIXTURE_PERIOD 2u

static const char SQL_CUSTOMERS[] =
    "CREATE TABLE CUSTOMERS(CUSTOMER_ID I16,REGION I8,ACTIVE BOOLEAN,"
    "NAME CHAR(80))";
static const char SQL_PRODUCTS[] =
    "CREATE TABLE PRODUCTS(PRODUCT_ID I8,CATEGORY_ID I8,ACTIVE BOOLEAN,"
    "NAME CHAR(16))";
static const char SQL_ORDERS[] =
    "CREATE TABLE SALES_ORDERS(ORDER_ID I16,CUSTOMER_ID I16,PRODUCT_ID I8,"
    "ORDER_TOTAL I32,ITEM_COUNT I16,DETAILS CHAR(80))";
static const char SQL_RULES[] =
    "CREATE TABLE DISCOUNT_RULES(CUSTOMER_ID I16,MIN_TOTAL I32)";
static const char SQL_ARCHIVE[] =
    "CREATE TABLE ORDER_ARCHIVE(ARCHIVE_ID I16,DETAILS CHAR(80))";
static const char SQL_CUSTOMER_INDEX[] =
    "CREATE INDEX CUSTOMER_ID_REGION ON CUSTOMERS(CUSTOMER_ID,REGION)";
static const char SQL_PRODUCT_INDEX[] =
    "CREATE INDEX PRODUCT_ID_CATEGORY ON PRODUCTS(PRODUCT_ID,CATEGORY_ID)";
static const char ORDER_INDEX_NAME[] = "ORDER_BUYER_PROD";

/* This is intentionally readable benchmark SQL. The first query exercises a
 * three-table join, three explicit source indexes, fixed CHAR(80) matching,
 * numeric/boolean filters, grouping, five aggregate forms, and ordering. */
static const char SQL_SALES_SUMMARY[] =
    "SELECT C.REGION,P.CATEGORY_ID,COUNT(*),SUM(O.ORDER_TOTAL),"
    "AVG(O.ITEM_COUNT),MIN(O.ORDER_TOTAL),MAX(O.ORDER_TOTAL) "
    "FROM SALES_ORDERS AS O USING INDEX ORDER_BUYER_PROD "
    "JOIN CUSTOMERS AS C USING INDEX CUSTOMER_ID_REGION "
    "ON C.CUSTOMER_ID=O.CUSTOMER_ID "
    "JOIN PRODUCTS AS P USING INDEX PRODUCT_ID_CATEGORY "
    "ON P.PRODUCT_ID=O.PRODUCT_ID "
    "WHERE O.ORDER_TOTAL>=1000 AND O.ITEM_COUNT>=2 "
    "AND O.DETAILS LIKE 'A%' AND C.ACTIVE=TRUE AND P.ACTIVE=TRUE "
    "GROUP BY C.REGION,P.CATEGORY_ID";

/* The second measured query isolates correlated EXISTS behavior. The indexed
 * joins already live in the summary query above; keeping this outer query to
 * one table avoids implying that a correlated predicate is another join. */
static const char SQL_ELIGIBLE_SALES[] =
    "SELECT O.ORDER_ID,O.CUSTOMER_ID,O.ORDER_TOTAL "
    "FROM SALES_ORDERS AS O "
    "WHERE O.ORDER_TOTAL>=900 AND EXISTS("
    "SELECT 1 FROM DISCOUNT_RULES AS R "
    "WHERE R.CUSTOMER_ID=O.CUSTOMER_ID "
    "AND O.ORDER_TOTAL>=R.MIN_TOTAL) LIMIT 1";

/* The headless benchmark does not use the C64 screen. Its page-sized setup
 * scratch lives there rather than consuming the engine's WORK/stack boundary
 * or colliding with the deliberately broad client in $0801-$30FF. */
#define page_buffer ((rsql_u8*)0x0400)
static rsql_u16 order_table_page;
static rsql_u16 order_row_head;
/* Query execution loads multiple overlays. Keep the timer snapshots in fixed
 * application BSS rather than in a caller's temporary software-stack frame. */
static rsql_u8 timer_start[3];
static rsql_u8 timer_end[3];

static void fail(rsql_u8 stage, rsql_u8 detail) {
    TEST_STAGE = stage;
    TIMER_LO = detail;
    TEST_SENTINEL = detail ? detail : 0xFFu;
    BORDER_COLOR = 2u;
    for (;;) {}
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

static void pad_name(rsql_u8* destination, rsql_u8 width, char prefix,
                     rsql_u16 number) {
    memset(destination, ' ', width);
    destination[0] = (rsql_u8)prefix;
    destination[1] = '-';
    destination[2] = (rsql_u8)('0' + (number / 1000u) % 10u);
    destination[3] = (rsql_u8)('0' + (number / 100u) % 10u);
    destination[4] = (rsql_u8)('0' + (number / 10u) % 10u);
    destination[5] = (rsql_u8)('0' + number % 10u);
}

static void insert_dimension_rows(const char* table_name, rsql_u8 kind,
                                  rsql_u8 count, rsql_u8 width,
                                  rsql_u8 stage) {
    RsqlTableInfo table;
    RsqlRowId row_id;
    rsql_u8 item;
    rsql_u8 rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(table_name, &table);
    if (rc != RSQL_OK || table.row_width != width) fail(stage, rc ? rc : width);
    rc = rsql_overlay_load(1u);
    if (rc != RSQL_OK) fail(stage, rc);
    for (item = 0u; item < count; ++item) {
        memset(page_buffer, 0, width);
        if (kind == 0u) {
            rsql_put_u16(&page_buffer[1], (rsql_u16)(item + 1u));
            page_buffer[3] = (rsql_u8)((item + 1u) & 3u);
            page_buffer[4] = (rsql_u8)(((item + 1u) % 3u) != 0u);
            pad_name(&page_buffer[5], 80u, 'C', (rsql_u16)(item + 1u));
        } else if (kind == 1u) {
            page_buffer[1] = item;
            page_buffer[2] = (rsql_u8)(item & 1u);
            page_buffer[3] = (rsql_u8)(item != 2u);
            pad_name(&page_buffer[4], 16u, 'P', item);
        } else {
            rsql_u16 customer_id = (rsql_u16)(item + 1u);
            rsql_put_u16(&page_buffer[1], customer_id);
            rsql_put_u32(&page_buffer[3],
                1200ul + (unsigned long)(customer_id % 3u) * 100ul);
        }
        rc = rsql_row_insert(table.table_page, page_buffer, width, &row_id);
        if (rc != RSQL_OK) fail(stage, rc);
    }
}

static void fill_order(rsql_u8* row, rsql_u16 order_id) {
    rsql_u16 sequence = (rsql_u16)(order_id - 1u);
    memset(row, 0, 92u);
    rsql_put_u16(&row[1], order_id);
    rsql_put_u16(&row[3], (rsql_u16)(sequence % CUSTOMER_COUNT + 1u));
    row[5] = (rsql_u8)(sequence % PRODUCT_COUNT);
    rsql_put_u32(&row[6], 500ul + (unsigned long)(sequence % 20u) * 100ul);
    rsql_put_u16(&row[10], (rsql_u16)(sequence % 5u + 1u));
    pad_name(&row[12], 80u, sequence % 7u < 3u ? 'A' : 'B', order_id);
}

/* Test-only fast fixture loader. It writes exactly the same persistent row
 * format as rsql_row_insert, but appends known-full pages in O(n) time so the
 * suite measures database queries rather than thousands of setup scans. */
static void bulk_load_wide_table(const char* name, rsql_u16 width,
                                 rsql_u16 rows, rsql_u8 archive) {
    RsqlTableInfo table;
    rsql_u16 first = RSQL_PAGE_NONE;
    rsql_u16 previous = RSQL_PAGE_NONE;
    rsql_u16 current;
    rsql_u16 next;
    rsql_u16 page_number;
    rsql_u16 item_id = 1u;
    rsql_u8 rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find(name, &table);
    if (rc != RSQL_OK || table.row_width != width) fail(0x24u, rc ? rc : 92u);
    if (!archive) order_table_page = table.table_page;

    rc = rsql_page_allocate(&current);
    if (rc != RSQL_OK) fail(0x25u, rc);
    first = current;
    if (!archive) order_row_head = first;
    for (page_number = 0u; page_number < rows / 2u; ++page_number) {
        if (page_number + 1u < rows / 2u) {
            rc = rsql_page_allocate(&next);
            if (rc != RSQL_OK) fail(0x26u, rc);
        } else next = RSQL_PAGE_NONE;
        memset(page_buffer, 0, RSQL_REU_PAGE_SIZE);
        page_buffer[0] = 'R'; page_buffer[1] = 'R';
        page_buffer[2] = 'O'; page_buffer[3] = 'W';
        page_buffer[4] = RSQL_STORAGE_VERSION;
        page_buffer[RSQL_ROW_CAPACITY] = 2u;
        rsql_put_u16(&page_buffer[RSQL_ROW_WIDTH], width);
        rsql_put_u16(&page_buffer[RSQL_ROW_NEXT], next);
        rsql_put_u16(&page_buffer[RSQL_ROW_PREVIOUS], previous);
        page_buffer[RSQL_ROW_BITMAP] = 0x03u;
        if (!archive) {
            fill_order(&page_buffer[RSQL_ROW_DATA], item_id++);
            fill_order(&page_buffer[RSQL_ROW_DATA + 92u], item_id++);
        } else {
            rsql_put_u16(&page_buffer[RSQL_ROW_DATA + 1u], item_id);
            pad_name(&page_buffer[RSQL_ROW_DATA + 3u], 80u, 'H', item_id++);
            rsql_put_u16(&page_buffer[RSQL_ROW_DATA + 84u], item_id);
            pad_name(&page_buffer[RSQL_ROW_DATA + 86u], 80u, 'H', item_id++);
        }
        rc = rsql_reu_write(rsql_reu_page_address(current), page_buffer,
                            RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) fail(0x27u, rc);
        previous = current;
        current = next;
    }

    rc = rsql_reu_read(rsql_reu_page_address(table.table_page), page_buffer,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x28u, rc);
    rsql_put_u16(&page_buffer[RSQL_TABLE_ROW_HEAD], first);
    rsql_put_u16(&page_buffer[RSQL_TABLE_ROW_TAIL], previous);
    rsql_put_u32(&page_buffer[RSQL_TABLE_ROW_COUNT], rows);
    page_buffer[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(page_buffer);
    rc = rsql_reu_write(rsql_reu_page_address(table.table_page), page_buffer,
                        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x29u, rc);
}

static void initialize_order_index_leaf(rsql_u16 previous) {
    memset(page_buffer, 0, RSQL_REU_PAGE_SIZE);
    page_buffer[0] = 'R'; page_buffer[1] = 'I';
    page_buffer[2] = 'L'; page_buffer[3] = 'F';
    page_buffer[4] = RSQL_STORAGE_VERSION;
    page_buffer[RSQL_INDEX_LEAF_CAPACITY] = 30u;
    rsql_put_u16(&page_buffer[RSQL_INDEX_LEAF_NEXT], RSQL_PAGE_NONE);
    rsql_put_u16(&page_buffer[RSQL_INDEX_LEAF_PREVIOUS], previous);
    page_buffer[RSQL_INDEX_LEAF_KEY_WIDTH] = 5u;
}

/* The normal CREATE INDEX path is already covered by focused tests. This
 * benchmark constructs its sorted 128-entry fact index in linear
 * setup time so all measured join keys are indexed without timing index
 * construction or consuming the bounded mutation journal. */
static void bulk_create_order_index(void) {
    rsql_u16 descriptor;
    rsql_u16 head;
    rsql_u16 tail;
    rsql_u16 current;
    rsql_u16 next;
    rsql_u16 previous = RSQL_PAGE_NONE;
    rsql_u16 customer;
    rsql_u16 sequence;
    rsql_u16 residue;
    rsql_u16 root_page;
    rsql_u8 product;
    rsql_u8 count = 0u;
    rsql_u8 found;
    rsql_u8 rc = rsql_page_allocate(&descriptor);
    if (rc == RSQL_OK) rc = rsql_page_allocate(&current);
    if (rc != RSQL_OK) fail(0x35u, rc);
    head = current;
    initialize_order_index_leaf(RSQL_PAGE_NONE);
    for (customer = 1u; customer <= CUSTOMER_COUNT; ++customer) {
        for (product = 0u; product < PRODUCT_COUNT; ++product) {
            found = 0u;
            residue = 0u;
            while (residue < FIXTURE_PERIOD) {
                if (residue % CUSTOMER_COUNT + 1u == customer &&
                    residue % PRODUCT_COUNT == product) {
                    found = 1u;
                    break;
                }
                ++residue;
            }
            if (!found) continue;
            for (sequence = residue; sequence < ORDER_COUNT;
                 sequence += FIXTURE_PERIOD) {
                rsql_u16 offset;
                if (count == 30u) {
                    rc = rsql_page_allocate(&next);
                    if (rc != RSQL_OK) fail(0x36u, rc);
                    rsql_put_u16(&page_buffer[RSQL_INDEX_LEAF_NEXT], next);
                    page_buffer[RSQL_PAGE_CHECKSUM_OFFSET] =
                        rsql_page_checksum(page_buffer);
                    rc = rsql_reu_write(rsql_reu_page_address(current),
                        page_buffer, RSQL_REU_PAGE_SIZE);
                    if (rc != RSQL_OK) fail(0x37u, rc);
                    previous = current;
                    current = next;
                    initialize_order_index_leaf(previous);
                    count = 0u;
                }
                offset = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                                    (rsql_u16)count * 8u);
                page_buffer[offset] = 1u;
                rsql_put_u16(&page_buffer[offset + 1u], customer);
                page_buffer[offset + 3u] = 1u;
                page_buffer[offset + 4u] = product;
                rsql_put_u16(&page_buffer[offset + 5u],
                    (rsql_u16)(order_row_head + sequence / 2u));
                page_buffer[offset + 7u] = (rsql_u8)(sequence & 1u);
                ++count;
                page_buffer[RSQL_INDEX_LEAF_COUNT] = count;
            }
        }
    }
    tail = current;
    page_buffer[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(page_buffer);
    rc = rsql_reu_write(rsql_reu_page_address(current), page_buffer,
                        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x38u, rc);

    root_page = rsql_page_catalog_root();
    rc = rsql_reu_read(rsql_reu_page_address(root_page), page_buffer,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x39u, rc);
    next = rsql_get_u16(&page_buffer[RSQL_ROOT_FIRST_INDEX]);
    memset(page_buffer, 0, RSQL_REU_PAGE_SIZE);
    page_buffer[0] = 'R'; page_buffer[1] = 'I';
    page_buffer[2] = 'D'; page_buffer[3] = 'X';
    page_buffer[4] = RSQL_STORAGE_VERSION;
    rsql_put_u16(&page_buffer[RSQL_INDEX_NEXT], next);
    rsql_put_u16(&page_buffer[RSQL_INDEX_TABLE], order_table_page);
    rsql_put_u16(&page_buffer[RSQL_INDEX_LEAF_HEAD], head);
    rsql_put_u16(&page_buffer[RSQL_INDEX_LEAF_TAIL], tail);
    rsql_put_u32(&page_buffer[RSQL_INDEX_ENTRY_COUNT], ORDER_COUNT);
    page_buffer[RSQL_INDEX_KEY_WIDTH] = 5u;
    page_buffer[RSQL_INDEX_COLUMN_COUNT] = 2u;
    page_buffer[RSQL_INDEX_NAME_LENGTH] =
        (rsql_u8)(sizeof(ORDER_INDEX_NAME) - 1u);
    memcpy(&page_buffer[RSQL_INDEX_NAME], ORDER_INDEX_NAME,
           sizeof(ORDER_INDEX_NAME) - 1u);
    page_buffer[RSQL_INDEX_COLUMNS] = 1u;
    page_buffer[RSQL_INDEX_COLUMNS + 1u] = 2u;
    page_buffer[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(page_buffer);
    rc = rsql_reu_write(rsql_reu_page_address(descriptor), page_buffer,
                        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x3Au, rc);

    rc = rsql_reu_read(rsql_reu_page_address(root_page), page_buffer,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x3Bu, rc);
    rsql_put_u16(&page_buffer[RSQL_ROOT_FIRST_INDEX], descriptor);
    page_buffer[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(page_buffer);
    rc = rsql_reu_write(rsql_reu_page_address(root_page), page_buffer,
                        RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail(0x3Cu, rc);
}

static void read_jiffy(rsql_u8* result) {
    __asm__("sei");
    result[0] = JIFFY_LO;
    result[1] = JIFFY_MID;
    result[2] = JIFFY_HI;
    __asm__("cli");
}

static void store_elapsed(void) {
    rsql_u8 borrow;
    TIMER_LO = (rsql_u8)(timer_end[0] - timer_start[0]);
    borrow = timer_end[0] < timer_start[0];
    TIMER_MID = (rsql_u8)(timer_end[1] - timer_start[1] - borrow);
    borrow = (rsql_u8)(timer_end[1] - borrow) < timer_start[1];
    TIMER_HI = (rsql_u8)(timer_end[2] - timer_start[2] - borrow);
}

static void expect_i8(RsqlCursorHandle cursor, rsql_u8 column,
                      rsql_u8 expected, rsql_u8 stage) {
    RsqlCursorColumnRequest request;
    rsql_u8 rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null ||
        request.value.bytes[0] != expected) fail(stage, rc ? rc : expected);
}

static void expect_i64(RsqlCursorHandle cursor, rsql_u8 column,
                       unsigned long expected, rsql_u8 stage) {
    RsqlCursorColumnRequest request;
    rsql_u8 byte;
    rsql_u8 rc;
    request.cursor = cursor;
    request.column = column;
    rc = rsql_cursor_column(&request);
    if (rc != RSQL_OK || request.value.is_null || request.value.length != 8u) {
        fail(stage, rc ? rc : request.value.length);
    }
    for (byte = 0u; byte < 8u; ++byte) {
        rsql_u8 wanted = byte < 4u
            ? (rsql_u8)(expected >> (byte * 8u)) : 0u;
        if (request.value.bytes[byte] != wanted) fail(stage, byte);
    }
}

static void expect_fixed_integer(RsqlCursorHandle cursor, rsql_u8 column,
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
        if (request.value.bytes[byte] !=
            (rsql_u8)(expected >> (byte * 8u))) fail(stage, byte);
    }
}

static RsqlCursorHandle measured_open(const char* sql, rsql_u8 columns,
                                      rsql_u8 marker) {
    RsqlQueryOpenRequest open;
    rsql_u8 rc;
    TEST_STAGE = marker;
    read_jiffy(timer_start);
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != columns) {
        fail(marker, rc ? rc : open.column_count);
    }
    return open.cursor;
}

static void measured_finish(RsqlCursorHandle cursor, rsql_u8 marker) {
    RsqlQueryCloseRequest close;
    rsql_u8 rc;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    read_jiffy(timer_end);
    if (rc != RSQL_OK) fail(marker, rc);
    store_elapsed();
    TEST_STAGE = marker;
}

static void next_row(RsqlCursorHandle cursor, rsql_u8 expected,
                     rsql_u8 stage) {
    RsqlCursorNextRequest next;
    rsql_u8 rc;
    next.cursor = cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row != expected) {
        fail(stage, rc ? rc : next.has_row);
    }
}

static void run_sales_summary(void) {
    static const rsql_u8 regions[] = {1u, 2u};
    static const rsql_u8 categories[] = {0u, 1u};
    static const unsigned long counts[] = {16ul, 17ul};
    static const unsigned long sums[] = {28000ul, 30000ul};
    static const unsigned long averages[] = {3ul, 3ul};
    static const unsigned long minimums[] = {1100ul, 1200ul};
    static const unsigned long maximums[] = {2300ul, 2400ul};
    rsql_u8 row;
    RsqlCursorHandle cursor = measured_open(
        SQL_SALES_SUMMARY, 7u, 0xB1u);
    for (row = 0u; row < 2u; ++row) {
        next_row(cursor, 1u, 0xB3u);
        expect_i8(cursor, 0u, regions[row], 0xB4u);
        expect_i8(cursor, 1u, categories[row], 0xB5u);
        expect_i64(cursor, 2u, counts[row], 0xB6u);
        expect_i64(cursor, 3u, sums[row], 0xB7u);
        expect_i64(cursor, 4u, averages[row], 0xB8u);
        expect_i64(cursor, 5u, minimums[row], 0xB9u);
        expect_i64(cursor, 6u, maximums[row], 0xBAu);
    }
    next_row(cursor, 0u, 0xBBu);
    measured_finish(cursor, 0xB2u);
    while (BENCHMARK_CONTROL < 1u) {}
}

static void run_eligible_sales(void) {
    RsqlCursorHandle cursor = measured_open(
        SQL_ELIGIBLE_SALES, 3u, 0xC1u);
    next_row(cursor, 1u, 0xC3u);
    expect_fixed_integer(cursor, 0u, 9ul, 2u, 0xC4u);
    expect_i8(cursor, 1u, 1u, 0xC5u);
    expect_fixed_integer(cursor, 2u, 1300ul, 4u, 0xC6u);
    next_row(cursor, 0u, 0xC8u);
    measured_finish(cursor, 0xC2u);
    while (BENCHMARK_CONTROL < 2u) {}
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
    exec_ok(SQL_RULES, 0x23u);
    exec_ok(SQL_ARCHIVE, 0x24u);
    insert_dimension_rows("CUSTOMERS", 0u, CUSTOMER_COUNT, 85u, 0x2Au);
    insert_dimension_rows("PRODUCTS", 1u, PRODUCT_COUNT, 20u, 0x2Bu);
    insert_dimension_rows("DISCOUNT_RULES", 2u, RULE_COUNT, 7u, 0x2Cu);
    bulk_load_wide_table("SALES_ORDERS", 92u, ORDER_COUNT, 0u);
    bulk_load_wide_table("ORDER_ARCHIVE", 83u, ARCHIVE_COUNT, 1u);
    exec_ok(SQL_CUSTOMER_INDEX, 0x30u);
    exec_ok(SQL_PRODUCT_INDEX, 0x31u);
    bulk_create_order_index();

    run_sales_summary();
    run_eligible_sales();
    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

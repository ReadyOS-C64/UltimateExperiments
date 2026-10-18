#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_journal.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_row.h"

#define TEST_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)

static const char SQL_CREATE_TYPES[] =
    "create table sqltypes (flag boolean not null, tiny i8, small i16 null, "
    "wide i32, huge i64, money fixed8_8, value float, label char(9));";
static const char SQL_CREATE_VARIABLES[] =
    "CREATE TABLE SQLVAR (BODY TEXT NULL, RAW BLOB)";
static const char SQL_INSERT_VARIABLES[] =
    "INSERT INTO SQLVAR VALUES ('C64 ''TEXT''', X'00FF104142')";
static const char SQL_INSERT_VARIABLES_NULL[] =
    "INSERT INTO SQLVAR VALUES (NULL, X'')";
static const char SQL_INSERT_VARIABLES_BAD_TEXT[] =
    "INSERT INTO SQLVAR VALUES (X'41', X'00')";
static const char SQL_INSERT_VARIABLES_BAD_BLOB[] =
    "INSERT INTO SQLVAR VALUES ('OK', 'NOT BINARY')";
static const char SQL_INSERT_VARIABLES_BAD_HEX[] =
    "INSERT INTO SQLVAR VALUES ('OK', X'0')";
static const char SQL_COUNT_VARIABLES[] = "SELECT COUNT(*) FROM SQLVAR";
static const char SQL_COUNT_VARIABLE_BODY[] = "SELECT COUNT(BODY) FROM SQLVAR";
static const char SQL_SELECT_VARIABLES[] = "SELECT BODY, RAW FROM SQLVAR";
static const char SQL_CREATE_VAR_SAMPLE[] =
    "CREATE TABLE VARSAMPLE (BODY TEXT, RAW BLOB)";
static const char SQL_INSERT_VAR_SAMPLE[] =
    "INSERT INTO VARSAMPLE VALUES ('SAMPLE', X'0102')";
static const char SQL_CREATE_VAR_FAIL[] =
    "CREATE TABLE VARFAIL (BODY TEXT, RAW BLOB)";
static const char SQL_INSERT_VAR_FAIL[] =
    "INSERT INTO VARFAIL VALUES ('SAMPLE', X'0102')";
static const char SQL_COUNT_VAR_FAIL[] = "SELECT COUNT(*) FROM VARFAIL";
static const char SQL_CREATE_DML[] =
    "CREATE TABLE SQLDML (ID I16, NAME CHAR(8), ACTIVE BOOLEAN, SCORE I32 NULL)";
static const char SQL_INSERT_DML1[] =
    "INSERT INTO SQLDML VALUES (42, 'ADA', TRUE, NULL)";
static const char SQL_INSERT_DML2[] =
    "insert into sqldml values (-7, 'O''NEIL', false, 123456);";
static const char SQL_INSERT_RANGE[] =
    "INSERT INTO SQLDML VALUES (40000, 'X', TRUE, NULL)";
static const char SQL_SELECT_COUNT[] = "SELECT COUNT(*) FROM SQLDML";
static const char SQL_SELECT_PROJECT[] =
    "select name, score, id from sqldml;";
static const char SQL_SELECT_COUNT_NONNULL[] =
    "SELECT COUNT(*) FROM SQLDML WHERE SCORE IS NOT NULL";
static const char SQL_SELECT_NEGATIVE[] =
    "SELECT ID FROM SQLDML WHERE ID < 0";
static const char SQL_SUBQUERY_AGG_EXISTS[] =
    "SELECT COUNT(*) FROM SQLDML AS D WHERE EXISTS "
    "(SELECT 1 FROM SQLDML AS X WHERE X.ID=D.ID)";
static const char SQL_SUBQUERY_AGG_GROUP[] =
    "SELECT DISTINCT COUNT(*),SUM(D.ID) FROM SQLDML AS D WHERE D.ID IN "
    "(SELECT X.ID FROM SQLDML AS X WHERE X.ID=D.ID) "
    "GROUP BY D.ACTIVE ORDER BY 2 LIMIT 1 OFFSET 1";
static const char SQL_SUBQUERY_AGG_SCALAR_MANY[] =
    "SELECT COUNT(*) FROM SQLDML AS D WHERE D.ID="
    "(SELECT X.ID FROM SQLDML AS X)";
static const char SQL_BOOL_PRECEDENCE[] =
    "SELECT COUNT(*) FROM SQLDML WHERE ID < 0 OR ACTIVE = TRUE "
    "AND SCORE IS NULL";
static const char SQL_BOOL_PARENTHESES[] =
    "SELECT COUNT(*) FROM SQLDML WHERE (ID < 0 OR ACTIVE = TRUE) "
    "AND SCORE IS NULL";
static const char SQL_BOOL_UNKNOWN[] =
    "SELECT COUNT(*) FROM SQLDML WHERE NOT (SCORE = NULL) OR ID < 0";
static const char SQL_LIKE_WILDCARDS[] =
    "SELECT COUNT(*) FROM SQLDML WHERE NAME LIKE 'a_a%' OR NAME LIKE '%NEIL'";
static const char SQL_NOT_LIKE[] =
    "SELECT COUNT(*) FROM SQLDML WHERE NAME NOT LIKE '%NEIL'";
static const char SQL_ALL_COMPARISONS[] =
    "SELECT COUNT(*) FROM SQLDML WHERE ID >= -7 AND ID <= 42 AND ID != 0 "
    "AND ID <> 99 AND ID > -8 AND ID = 42";
static const char SQL_BAD_BOOLEAN[] =
    "SELECT ID FROM SQLDML WHERE (ID < 0";
static const char SQL_BAD_LIKE_TYPE[] =
    "SELECT ID FROM SQLDML WHERE ID LIKE '4%'";
static const char SQL_CREATE_JFAIL[] =
    "CREATE TABLE JFAIL (ID I16)";
static const char SQL_INSERT_JFAIL1[] =
    "INSERT INTO JFAIL VALUES (1)";
static const char SQL_INSERT_JFAIL2[] =
    "INSERT INTO JFAIL VALUES (2)";
static const char SQL_COUNT_JFAIL[] =
    "SELECT COUNT(*) FROM JFAIL";
static const char SQL_DELETE_JFAIL1[] =
    "DELETE FROM JFAIL WHERE ID = 1";
static const char SQL_DELETE_JFAIL_NONE[] =
    "DELETE FROM JFAIL WHERE ID > 100";
static const char SQL_DELETE_JFAIL2[] =
    "DELETE FROM JFAIL WHERE ID = 2 OR ID = 99";
static const char SQL_DELETE_JFAIL_ALL[] =
    "DELETE FROM JFAIL";
static const char SQL_DELETE_BAD[] = "DELETE JFAIL WHERE ID = 1";
static const char SQL_BAD_CHAR[] = "CREATE TABLE BROKEN (ID CHAR())";
static const char SQL_RESULT_VIA_EXEC[] = "SELECT * FROM SQLTYPES";

static void fail(unsigned char code) {
    BORDER_COLOR = 2u;
    TEST_SENTINEL = code;
    for (;;) {}
}

static void exec_expect(const char* sql, unsigned char expected,
                        unsigned char stage) {
    RsqlExecRequest request;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != expected) fail(rc ? rc : stage);
    if (rc == RSQL_OK && request.output.affected_rows.bytes[1] != 0u) fail(stage);
}

static void close_cursor(RsqlCursorHandle cursor, unsigned char stage) {
    RsqlQueryCloseRequest close;
    unsigned char rc;
    close.cursor = cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(rc ? rc : stage);
}

static void expect_count(const char* sql, unsigned char expected,
                         unsigned char stage) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest result;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 1u) fail(rc ? rc : stage);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || !next.has_row || result.value.is_null ||
        result.value.type.tag != RSQL_TYPE_I64 ||
        result.value.bytes[0] != expected || result.value.bytes[1] != 0u) {
        fail(rc ? rc : stage);
    }
    close_cursor(open.cursor, stage);
}

static void expect_subquery_groups(void) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest value;
    unsigned char rc;
    open.sql = SQL_SUBQUERY_AGG_GROUP;
    open.sql_length = strlen(SQL_SUBQUERY_AGG_GROUP);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 2u) fail(rc ? rc : 0x38u);
    next.cursor = open.cursor;
    value.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    value.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&value);
    if (rc != RSQL_OK || !next.has_row || value.value.is_null ||
        value.value.type.tag != RSQL_TYPE_I64 || value.value.bytes[0] != 1u) {
        fail(rc ? rc : 0x39u);
    }
    value.column = 1u;
    rc = rsql_cursor_column(&value);
    if (rc != RSQL_OK || value.value.bytes[0] != 42u ||
        value.value.bytes[1] != 0u || value.value.bytes[7] != 0u) {
        fail(rc ? rc : 0x3Au);
    }
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : 0x3Bu);
    close_cursor(open.cursor, 0x3Bu);
}

static unsigned int first_free_page(void) {
    unsigned long page;
    unsigned char allocated;
    unsigned char rc;
    for (page = rsql_page_first_usable(); page < rsql_page_limit(); ++page) {
        rc = rsql_page_is_allocated((unsigned int)page, &allocated);
        if (rc != RSQL_OK) fail(rc);
        if (!allocated) return (unsigned int)page;
    }
    return RSQL_PAGE_NONE;
}

static void expect_affected(const char* sql, unsigned char expected,
                            unsigned char stage) {
    RsqlExecRequest request;
    unsigned char index;
    unsigned char rc;
    request.sql = sql;
    request.sql_length = strlen(sql);
    rc = rsql_exec(&request);
    if (rc != RSQL_OK || request.output.affected_rows.bytes[0] != expected) {
        fail(rc ? rc : stage);
    }
    for (index = 1u; index < 8u; ++index) {
        if (request.output.affected_rows.bytes[index] != 0u) fail(stage);
    }
}

int main(void) {
    RsqlInitRequest init;
    RsqlTableInfo table;
    RsqlColumnInfo column;
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest result;
    RsqlValueReadRequest read;
    RsqlBlobHandle body_handle;
    RsqlBlobHandle raw_handle;
    RsqlBlobInfo blob_info;
    RsqlRowId variable_row_id;
    const RsqlErrorInfo* error;
    unsigned char text[8];
    unsigned char variable_row[9];
    unsigned char variable_value[16];
    unsigned int variable_bytes;
    unsigned char rc;
    unsigned char fail_index;
    unsigned char variable_write_count;
    unsigned int expected_free;

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

    exec_expect(SQL_CREATE_TYPES, RSQL_OK, 0xA1u);
    rc = rsql_table_find("sqltypes", &table);
    if (rc != RSQL_OK || table.column_count != 8u || table.row_width != 33u) {
        fail(rc ? rc : 0xA2u);
    }
    rc = rsql_column_info(table.table_page, 2u, &column);
    if (rc != RSQL_OK || column.type.tag != RSQL_TYPE_I16 ||
        !(column.type.flags & RSQL_TYPE_FLAG_NULLABLE)) fail(rc ? rc : 0xA3u);
    exec_expect(SQL_CREATE_TYPES, RSQL_ERR_ALREADY_EXISTS, 0xA4u);
    exec_expect(SQL_CREATE_VARIABLES, RSQL_OK, 0xA5u);
    exec_expect(SQL_INSERT_VARIABLES_BAD_TEXT, RSQL_ERR_TYPE_MISMATCH, 0x70u);
    exec_expect(SQL_INSERT_VARIABLES_BAD_BLOB, RSQL_ERR_TYPE_MISMATCH, 0x71u);
    exec_expect(SQL_INSERT_VARIABLES_BAD_HEX, RSQL_ERR_SYNTAX, 0x72u);
    exec_expect(SQL_INSERT_VARIABLES, RSQL_OK, 0x73u);
    expect_count(SQL_COUNT_VARIABLES, 1u, 0x74u);

    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_table_find("SQLVAR", &table);
    if (rc != RSQL_OK || table.row_width != sizeof(variable_row)) {
        fail(rc ? rc : 0x75u);
    }
    rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_row_first(table.table_page, &variable_row_id);
    if (rc == RSQL_OK) {
        rc = rsql_row_read(table.table_page, &variable_row_id, variable_row,
                           sizeof(variable_row));
    }
    if (rc != RSQL_OK || variable_row[0] != 0u) fail(rc ? rc : 0x76u);
    memcpy(body_handle.bytes, &variable_row[1], sizeof(body_handle.bytes));
    memcpy(raw_handle.bytes, &variable_row[5], sizeof(raw_handle.bytes));
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_info(&body_handle, &blob_info);
    if (rc != RSQL_OK || blob_info.kind != RSQL_BLOB_KIND_TEXT ||
        blob_info.length != 10ul) fail(rc ? rc : 0x77u);
    memset(variable_value, 0, sizeof(variable_value));
    rc = rsql_blob_read(&body_handle, 0ul, variable_value,
                        sizeof(variable_value), &variable_bytes);
    if (rc != RSQL_OK || variable_bytes != 10u ||
        memcmp(variable_value, "C64 'TEXT'", 10u) != 0) {
        fail(rc ? rc : 0x78u);
    }
    rc = rsql_blob_info(&raw_handle, &blob_info);
    if (rc != RSQL_OK || blob_info.kind != RSQL_BLOB_KIND_BINARY ||
        blob_info.length != 5ul) fail(rc ? rc : 0x79u);
    memset(variable_value, 0, sizeof(variable_value));
    rc = rsql_blob_read(&raw_handle, 0ul, variable_value,
                        sizeof(variable_value), &variable_bytes);
    if (rc != RSQL_OK || variable_bytes != 5u || variable_value[0] != 0x00u ||
        variable_value[1] != 0xFFu || variable_value[2] != 0x10u ||
        variable_value[3] != 0x41u || variable_value[4] != 0x42u) {
        fail(rc ? rc : 0x7Au);
    }
    exec_expect(SQL_INSERT_VARIABLES_NULL, RSQL_OK, 0x7Bu);
    expect_count(SQL_COUNT_VARIABLES, 2u, 0x7Cu);
    expect_count(SQL_COUNT_VARIABLE_BODY, 1u, 0x7Du);

    open.sql = SQL_SELECT_VARIABLES;
    open.sql_length = strlen(SQL_SELECT_VARIABLES);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 2u) fail(rc ? rc : 0x50u);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || !next.has_row || result.value.is_null ||
        result.value.type.tag != RSQL_TYPE_TEXT || result.value.length != 10u) {
        fail(rc ? rc : 0x51u);
    }
    memset(variable_value, 0, sizeof(variable_value));
    read.cursor = open.cursor;
    read.column = 0u;
    read.offset = 0u;
    read.destination = variable_value;
    read.capacity = sizeof(variable_value);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 10u ||
        memcmp(variable_value, "C64 'TEXT'", 10u) != 0) {
        fail(rc ? rc : 0x52u);
    }
    result.column = 1u;
    rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || result.value.is_null ||
        result.value.type.tag != RSQL_TYPE_BLOB || result.value.length != 5u) {
        fail(rc ? rc : 0x53u);
    }
    memset(variable_value, 0, sizeof(variable_value));
    read.column = 1u;
    read.offset = 1u;
    read.capacity = 3u;
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 3u ||
        variable_value[0] != 0xFFu || variable_value[1] != 0x10u ||
        variable_value[2] != 0x41u) fail(rc ? rc : 0x54u);
    rc = rsql_cursor_next(&next);
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || !next.has_row || !result.value.is_null ||
        result.value.length != 0u) fail(rc ? rc : 0x55u);
    result.column = 1u;
    rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || result.value.is_null || result.value.length != 0u) {
        fail(rc ? rc : 0x56u);
    }
    read.column = 1u;
    read.offset = 0u;
    read.capacity = sizeof(variable_value);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 0u) fail(rc ? rc : 0x57u);
    close_cursor(open.cursor, 0x58u);

    exec_expect(SQL_CREATE_VAR_SAMPLE, RSQL_OK, 0x60u);
    exec_expect(SQL_INSERT_VAR_SAMPLE, RSQL_OK, 0x61u);
    variable_write_count = rsql_journal_test_write_count();
    if (variable_write_count == 0u || variable_write_count == 0xFFu) {
        fail(0x62u);
    }
    exec_expect(SQL_CREATE_VAR_FAIL, RSQL_OK, 0x63u);
    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < variable_write_count; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_INSERT_VAR_FAIL, RSQL_ERR_IO, 0x64u);
        expect_count(SQL_COUNT_VAR_FAIL, 0u, 0x65u);
        if (first_free_page() != expected_free) fail(0x66u);
    }
    exec_expect(SQL_INSERT_VAR_FAIL, RSQL_OK, 0x67u);
    expect_count(SQL_COUNT_VAR_FAIL, 1u, 0x68u);
    exec_expect(SQL_CREATE_DML, RSQL_OK, 0xA6u);
    exec_expect(SQL_INSERT_DML1, RSQL_OK, 0xA7u);
    exec_expect(SQL_INSERT_DML2, RSQL_OK, 0xA8u);
    exec_expect(SQL_INSERT_RANGE, RSQL_ERR_TYPE_MISMATCH, 0xA9u);
    expect_count(SQL_SUBQUERY_AGG_EXISTS, 2u, 0x36u);
    expect_subquery_groups();
    open.sql = SQL_SUBQUERY_AGG_SCALAR_MANY;
    open.sql_length = strlen(SQL_SUBQUERY_AGG_SCALAR_MANY);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK) fail(rc);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_ERR_SUBQUERY_ROWS) fail(rc ? rc : 0x37u);
    close_cursor(open.cursor, 0x37u);

    open.sql = SQL_SELECT_COUNT;
    open.sql_length = strlen(SQL_SELECT_COUNT);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 1u) fail(rc ? rc : 0xAAu);
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || !next.has_row ||
        result.value.type.tag != RSQL_TYPE_I64 ||
        result.value.bytes[0] != 2u) fail(rc ? rc : 0xABu);
    close_cursor(open.cursor, 0xACu);

    open.sql = SQL_SELECT_COUNT_NONNULL;
    open.sql_length = strlen(SQL_SELECT_COUNT_NONNULL);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || result.value.bytes[0] != 1u) fail(rc ? rc : 0xADu);
    close_cursor(open.cursor, 0xAEu);

    open.sql = SQL_SELECT_NEGATIVE;
    open.sql_length = strlen(SQL_SELECT_NEGATIVE);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || result.value.bytes[0] != 0xF9u ||
        result.value.bytes[1] != 0xFFu) fail(rc ? rc : 0xAFu);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(rc ? rc : 0xB0u);
    close_cursor(open.cursor, 0xB1u);

    open.sql = SQL_SELECT_PROJECT;
    open.sql_length = strlen(SQL_SELECT_PROJECT);
    rc = rsql_query_open(&open);
    next.cursor = open.cursor;
    if (rc == RSQL_OK) rc = rsql_cursor_next(&next);
    result.cursor = open.cursor;
    result.column = 1u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || !result.value.is_null) fail(rc ? rc : 0xB2u);
    memset(text, 0, sizeof(text));
    read.cursor = open.cursor;
    read.column = 0u;
    read.offset = 0u;
    read.destination = text;
    read.capacity = sizeof(text);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != 8u ||
        memcmp(text, "ADA     ", 8u) != 0) fail(rc ? rc : 0xB3u);
    rc = rsql_cursor_next(&next);
    result.column = 1u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&result);
    if (rc != RSQL_OK || result.value.is_null ||
        result.value.bytes[0] != 0x40u || result.value.bytes[1] != 0xE2u ||
        result.value.bytes[2] != 0x01u) fail(rc ? rc : 0xB4u);
    close_cursor(open.cursor, 0xB5u);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_ERR_CURSOR_STATE) fail(rc ? rc : 0xB6u);

    exec_expect(SQL_BAD_CHAR, RSQL_ERR_SYNTAX, 0xB7u);
    error = rsql_last_error();
    if (error->code != RSQL_ERR_SYNTAX || error->byte_offset == 0u) fail(0xB8u);
    exec_expect(SQL_RESULT_VIA_EXEC, RSQL_ERR_UNSUPPORTED_SQL, 0xB9u);

    expect_count(SQL_BOOL_PRECEDENCE, 2u, 0xC0u);
    expect_count(SQL_BOOL_PARENTHESES, 1u, 0xC1u);
    expect_count(SQL_BOOL_UNKNOWN, 1u, 0xC2u);
    expect_count(SQL_LIKE_WILDCARDS, 2u, 0xC3u);
    expect_count(SQL_NOT_LIKE, 1u, 0xC4u);
    expect_count(SQL_ALL_COMPARISONS, 1u, 0xC5u);

    open.sql = SQL_BAD_BOOLEAN;
    open.sql_length = strlen(SQL_BAD_BOOLEAN);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_SYNTAX) fail(rc ? rc : 0xC6u);
    open.sql = SQL_BAD_LIKE_TYPE;
    open.sql_length = strlen(SQL_BAD_LIKE_TYPE);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail(rc ? rc : 0xC7u);


    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 3u; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_CREATE_JFAIL, RSQL_ERR_IO, 0xD0u);
        rc = rsql_table_find("JFAIL", &table);
        if (rc != RSQL_ERR_NOT_FOUND) fail(rc ? rc : 0xD1u);
        if (first_free_page() != expected_free) fail(0xDCu);
    }
    exec_expect(SQL_CREATE_JFAIL, RSQL_OK, 0xD2u);
    expect_count(SQL_COUNT_JFAIL, 0u, 0xD3u);

    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 3u; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_INSERT_JFAIL1, RSQL_ERR_IO, 0xD4u);
        expect_count(SQL_COUNT_JFAIL, 0u, 0xD5u);
        if (first_free_page() != expected_free) fail(0xDDu);
    }
    exec_expect(SQL_INSERT_JFAIL1, RSQL_OK, 0xD6u);
    expect_count(SQL_COUNT_JFAIL, 1u, 0xD7u);

    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 2u; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_INSERT_JFAIL2, RSQL_ERR_IO, 0xD8u);
        expect_count(SQL_COUNT_JFAIL, 1u, 0xD9u);
        if (first_free_page() != expected_free) fail(0xDEu);
    }
    exec_expect(SQL_INSERT_JFAIL2, RSQL_OK, 0xDAu);
    expect_count(SQL_COUNT_JFAIL, 2u, 0xDBu);

    expected_free = first_free_page();
    for (fail_index = 0u; fail_index < 2u; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_DELETE_JFAIL1, RSQL_ERR_IO, 0xDFu);
        expect_count(SQL_COUNT_JFAIL, 2u, 0xE0u);
        if (first_free_page() != expected_free) fail(0xE1u);
    }
    expect_affected(SQL_DELETE_JFAIL1, 1u, 0xE2u);
    expect_count(SQL_COUNT_JFAIL, 1u, 0xE3u);
    expect_affected(SQL_DELETE_JFAIL_NONE, 0u, 0xE4u);
    expect_count(SQL_COUNT_JFAIL, 1u, 0xE5u);
    expect_affected(SQL_DELETE_JFAIL2, 1u, 0xE6u);
    expect_count(SQL_COUNT_JFAIL, 0u, 0xE7u);

    exec_expect(SQL_INSERT_JFAIL1, RSQL_OK, 0xE8u);
    exec_expect(SQL_INSERT_JFAIL2, RSQL_OK, 0xE9u);
    for (fail_index = 0u; fail_index < 4u; ++fail_index) {
        rsql_journal_test_fail_after(fail_index);
        exec_expect(SQL_DELETE_JFAIL_ALL, RSQL_ERR_IO, 0xEAu);
        expect_count(SQL_COUNT_JFAIL, 2u, 0xEBu);
    }
    expect_affected(SQL_DELETE_JFAIL_ALL, 2u, 0xECu);
    expect_count(SQL_COUNT_JFAIL, 0u, 0xEDu);
    open.sql = SQL_DELETE_BAD;
    open.sql_length = strlen(SQL_DELETE_BAD);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_SYNTAX) fail(rc ? rc : 0xEEu);


    TEST_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

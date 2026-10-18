#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_enum.h"
#include "rsql_journal.h"
#include "rsql_overlay.h"
#include "rsql_page.h"
#include "rsql_query_phase.h"
#include "rsql_row.h"
#include "storage_layout.h"

#define FOUNDATION_SENTINEL (*(volatile unsigned char*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile unsigned char*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile unsigned char*)0xCFF2)
#define FAILURE_STAGE_0 (*(volatile unsigned char*)0xCFF3)
#define FAILURE_STAGE_1 (*(volatile unsigned char*)0xCFF4)
#define FAILURE_DETAIL_0 (*(volatile unsigned char*)0xCFF5)
#define FAILURE_DETAIL_1 (*(volatile unsigned char*)0xCFF6)
#define BORDER_COLOR (*(volatile unsigned char*)0xD020)
#define COLOR_BLACK 0u
#define COLOR_RED 2u
#define COLOR_GREEN 5u
#define CPU_PORT (*(volatile unsigned char*)0x0001)

static unsigned char row_data[22];
static unsigned char row_readback[22];
static union {
    unsigned char page_data[RSQL_REU_PAGE_SIZE];
    unsigned char blob_readback[RSQL_REU_PAGE_SIZE];
} shared_read_buffer;
#define page_data shared_read_buffer.page_data
#define blob_readback shared_read_buffer.blob_readback
static union {
    unsigned char page_readback[RSQL_REU_PAGE_SIZE];
    unsigned char blob_data[600];
} shared_work_buffer;
#define page_readback shared_work_buffer.page_readback
#define blob_data shared_work_buffer.blob_data
static RsqlExecRequest index_exec_request;
static unsigned char index_expected_rc;
static unsigned char index_expected_affected;

static const RsqlColumnDefinition PEOPLE_COLUMNS[] = {
    { "ACTIVE",  { RSQL_TYPE_BOOLEAN, 0u, 0u, 0u } },
    { "AGE",     { RSQL_TYPE_I16, RSQL_TYPE_FLAG_NULLABLE, 0u, 0u } },
    { "BALANCE", { RSQL_TYPE_FIXED8_8, 0u, 0u, 0u } },
    { "NAME",    { RSQL_TYPE_CHAR, 0u, 12u, 0u } },
    { "NOTE",    { RSQL_TYPE_TEXT, RSQL_TYPE_FLAG_NULLABLE, 0u, 0u } }
};

static const RsqlTypeSpec TYPE_SPECS[] = {
    { RSQL_TYPE_BOOLEAN, 0u, 0u, 0u },
    { RSQL_TYPE_I8, 0u, 0u, 0u },
    { RSQL_TYPE_I16, 0u, 0u, 0u },
    { RSQL_TYPE_I32, 0u, 0u, 0u },
    { RSQL_TYPE_I64, 0u, 0u, 0u },
    { RSQL_TYPE_FIXED8_8, 0u, 0u, 0u },
    { RSQL_TYPE_FLOAT5, 0u, 0u, 0u },
    { RSQL_TYPE_CHAR, 0u, 12u, 0u },
    { RSQL_TYPE_TEXT, 0u, 0u, 0u },
    { RSQL_TYPE_BLOB, 0u, 0u, 0u },
    { RSQL_TYPE_ENUM8, 0u, 0u, 7u },
    { RSQL_TYPE_ENUM16, 0u, 0u, 8u }
};

static const unsigned char TYPE_WIDTHS[] = {
    1u, 1u, 2u, 4u, 8u, 2u, 5u, 12u, 4u, 4u, 1u, 2u
};

static const char SQL_INDEX_TABLE[] =
    "CREATE TABLE IDXT (ID I16, NAME CHAR(64), NOTE TEXT NULL)";
static const char SQL_INDEX_INSERT1[] =
    "INSERT INTO IDXT VALUES (42, 'ADA', NULL)";
static const char SQL_INDEX_INSERT2[] =
    "INSERT INTO IDXT VALUES (-7, 'O''NEIL', 'TEXT')";
static const char SQL_INDEX_CREATE[] =
    "CREATE INDEX IDX_NAME_ID ON IDXT (NAME, ID)";
static const char SQL_INDEX_CREATE_SINGLE[] =
    "CREATE INDEX IDX_ID ON IDXT (ID)";
static const char SQL_INDEX_BAD_VARIABLE[] =
    "CREATE INDEX IDX_NOTE ON IDXT (NOTE)";
static const char SQL_INDEX_NEGATIVE[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'O''NEIL'";
static const char SQL_INDEX_UPDATE[] =
    "UPDATE IDXT SET NAME = 'GRACE' WHERE ID = 42";
static const char SQL_INDEX_UPDATED[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'GRACE'";
static const char SQL_INDEX_UPDATE_BACK[] =
    "UPDATE IDXT SET NAME = 'ADA' WHERE ID = 42";
static const char SQL_INDEX_ADA[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'ADA'";
static const char SQL_INDEX_BY_ID[] =
    "SELECT ID FROM IDXT USING INDEX IDX_ID WHERE ID = 42";
static const char SQL_INDEX_LIMIT[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID LIMIT 1 OFFSET 1";
static const char SQL_INDEX_SCALAR[] =
    "SELECT LENGTH(NAME) FROM IDXT USING INDEX IDX_NAME_ID "
    "WHERE NAME='ADA'";
static const char SQL_INDEX_ORDER[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID "
    "ORDER BY ID DESC LIMIT 1";
static const char SQL_INDEX_DISTINCT_SCALAR[] =
    "SELECT DISTINCT LENGTH(NAME) FROM IDXT USING INDEX IDX_NAME_ID "
    "ORDER BY 1 DESC LIMIT 1";
static const char SQL_INDEX_AGGREGATE[] =
    "SELECT SUM(ID) FROM IDXT USING INDEX IDX_NAME_ID";
static const char SQL_INDEX_GROUPED[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID "
    "GROUP BY ID ORDER BY ID LIMIT 1";
static const char SQL_INDEX_INSERT3[] =
    "INSERT INTO IDXT VALUES (5, 'BOB', NULL)";
static const char SQL_INDEX_INSERTED[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'BOB'";
static const char SQL_INDEX_INSERT4[] =
    "INSERT INTO IDXT VALUES (6, 'ZED', NULL)";
static const char SQL_INDEX_SPLIT[] =
    "SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'ZED'";
static const char SQL_INDEX_DELETE[] = "DELETE FROM IDXT WHERE ID = -7";
static const char SQL_INDEX_MISSING[] =
    "SELECT ID FROM IDXT USING INDEX NO_SUCH_INDEX";
static const char SQL_INDEX_WRONG_TABLE[] =
    "SELECT NAME FROM PEOPLE USING INDEX IDX_NAME_ID";
static const char SQL_VPM_CREATE[] =
    "CREATE TABLE V(I I16,T TEXT NULL,B BLOB NULL,N CHAR(2))";
static const char SQL_VPM_INSERT1[] =
    "INSERT INTO V VALUES(1,'A',X'00','A')";
static const char SQL_VPM_INSERT2[] =
    "INSERT INTO V VALUES(2,'B',X'FF','B')";
static const char SQL_VPM_INSERT3[] =
    "INSERT INTO V VALUES(3,NULL,NULL,'C')";
static const char SQL_VPM_UPDATE_TEXT[] =
    "UPDATE V SET N='U' WHERE T LIKE 'A%' OR B>=X'FF'";
static const char SQL_VPM_DELETE[] =
    "DELETE FROM V WHERE T='A' AND B=X'00'";
static const char SQL_VPM_COUNT[] = "SELECT COUNT(*) FROM V";

#ifdef RSQL_QUERY_TEST
static const char SQL_CREATE_TYPES[] =
    "create table sqltypes (flag boolean not null, tiny i8, small i16 null, "
    "wide i32, huge i64, money fixed8_8, value float, label char(9));";
static const char SQL_CREATE_VARIABLES[] =
    "CREATE TABLE SQLVAR (BODY TEXT NULL, RAW BLOB)";
static const char SQL_CREATE_DML[] =
    "CREATE TABLE SQLDML (ID I16, NAME CHAR(8), ACTIVE BOOLEAN, SCORE I32 NULL)";
static const char SQL_INSERT_DML1[] =
    "INSERT INTO SQLDML VALUES (42, 'ADA', TRUE, NULL)";
static const char SQL_INSERT_DML2[] =
    "insert into sqldml values (-7, 'O''NEIL', false, 123456);";
static const char SQL_INSERT_RANGE[] =
    "INSERT INTO SQLDML VALUES (40000, 'X', TRUE, NULL)";
static const char SQL_SELECT_COUNT[] =
    "SELECT COUNT(*) FROM SQLDML";
static const char SQL_SELECT_PROJECT[] =
    "select name, score, id from sqldml;";
static const char SQL_SELECT_COUNT_NONNULL[] =
    "SELECT COUNT(*) FROM SQLDML WHERE SCORE IS NOT NULL";
static const char SQL_SELECT_NEGATIVE[] =
    "SELECT ID FROM SQLDML WHERE ID < 0";
static const char SQL_BAD_CHAR[] =
    "CREATE TABLE BROKEN (ID CHAR())";
static const char SQL_UNSUPPORTED[] = "SELECT * FROM SQLTYPES";
#endif

static const RsqlEnumMemberDefinition COLOR_MEMBERS[] = {
    { "BLACK", 0u }, { "WHITE", 1u }, { "RED", 2u }, { "CYAN", 3u },
    { "PURPLE", 4u }, { "GREEN", 5u }, { "BLUE", 6u }, { "YELLOW", 7u },
    { "ORANGE", 8u }, { "BROWN", 9u }, { "PINK", 10u }, { "DARKGREY", 11u },
    { "GREY", 12u }, { "LIGHTGREEN", 13u }
};

static void fail_screen(const char* stage, unsigned char rc) {
    FAILURE_STAGE_0 = (unsigned char)stage[0];
    FAILURE_STAGE_1 = (unsigned char)stage[3];
    BORDER_COLOR = COLOR_RED;
    FOUNDATION_SENTINEL = rc;
    for (;;) {}
}

static void index_exec_expect(const char* sql, unsigned char expected,
                              unsigned char affected) {
    unsigned char rc;
    index_expected_rc = expected;
    index_expected_affected = affected;
    index_exec_request.sql = sql;
    index_exec_request.sql_length = strlen(sql);
    rc = rsql_exec(&index_exec_request);
    if ((rsql_u8)(rc ^ index_expected_rc) != 0u) {
        FAILURE_STAGE_0 = rc;
        FAILURE_STAGE_1 = index_expected_rc;
        FAILURE_DETAIL_0 = index_exec_request.output.affected_rows.bytes[0];
        FAILURE_DETAIL_1 = (unsigned char)rsql_last_error()->message[0];
        BORDER_COLOR = COLOR_RED;
        FOUNDATION_SENTINEL = 0x92u;
        for (;;) {}
    }
    if (rc == RSQL_OK &&
        (rsql_u8)(index_exec_request.output.affected_rows.bytes[0] ^
                  index_expected_affected) != 0u) {
        FAILURE_DETAIL_1 = index_exec_request.output.affected_rows.bytes[0];
        fail_screen("IDXEXEC", 0x91u);
    }
}

static void index_expect_i16(const char* sql, unsigned int expected,
                             unsigned char has_row) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlCursorColumnRequest column;
    RsqlQueryCloseRequest close;
    unsigned char index;
    unsigned char fill;
    unsigned char rc;
    open.sql = sql;
    open.sql_length = strlen(sql);
    FAILURE_DETAIL_1 = has_row;
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 1u) {
        fail_screen("IDXOPEN", rc ? rc : 0x93u);
    }
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row != has_row) {
        fail_screen("IDXNEXT", rc ? rc : 0x94u);
    }
    if (has_row) {
        column.cursor = open.cursor;
        column.column = 0u;
        rc = rsql_cursor_column(&column);
        if (rc != RSQL_OK ||
            (column.value.type.tag != RSQL_TYPE_I16 &&
             column.value.type.tag != RSQL_TYPE_I64) ||
            column.value.bytes[0] != (unsigned char)expected ||
            column.value.bytes[1] != (unsigned char)(expected >> 8u)) {
            fail_screen("IDXVALUE", rc ? rc : 0x92u);
        }
        if (column.value.type.tag == RSQL_TYPE_I64) {
            fill = (expected & 0x8000u) ? 0xFFu : 0u;
            for (index = 2u; index < 8u; ++index) {
                if (column.value.bytes[index] != fill) {
                    fail_screen("IDXVALUE", 0x92u);
                }
            }
        }
        rc = rsql_cursor_next(&next);
        if (rc != RSQL_OK || next.has_row) {
            fail_screen("IDXEND", rc ? rc : 0x95u);
        }
    }
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail_screen("IDXCLOSE", rc ? rc : 0x96u);
}

int main(void) {
    RsqlInitRequest init;
    unsigned long address;
    unsigned int i;
    unsigned int page;
    unsigned int type_width;
    unsigned char allocated;
    unsigned char rc;
    unsigned char index_fail;
    unsigned char index_update_writes;
    unsigned char old_cpu_port;
    RsqlCreateTableRequest create_table;
    RsqlTableInfo table_info;
    RsqlColumnInfo column_info;
    RsqlRowId row_id;
    RsqlBlobHandle blob_handle;
    RsqlBlobInfo blob_info;
    unsigned int blob_bytes_read;
    unsigned int blob_chunk;
    unsigned int reclaimed_pages;
    RsqlCreateEnumRequest create_enum;
    RsqlEnumInfo enum_info;
    RsqlQueryOpenRequest index_open;
    unsigned int enum_value;
    char enum_name[RSQL_ENUM_MEMBER_NAME_MAX + 1u];
#ifdef RSQL_QUERY_TEST
    RsqlExecRequest exec_request;
    const RsqlErrorInfo* error_info;
    RsqlQueryOpenRequest query_open;
    RsqlCursorNextRequest cursor_next;
    RsqlCursorColumnRequest cursor_column;
    RsqlValueReadRequest value_read;
    RsqlQueryCloseRequest query_close;
#endif

    BORDER_COLOR = COLOR_BLACK;
    memset(&init, 0, sizeof(init));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;

    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail_screen("INIT", rc);
    if (rsql_reu_size_kib() != (unsigned int)(512u << REU_SIZE_SELECTOR)) {
        fail_screen("PROBE", 0xE0u);
    }
    for (i = 0u; i < sizeof(TYPE_WIDTHS); ++i) {
        rc = rsql_type_width(&TYPE_SPECS[i], &type_width);
        if (rc != RSQL_OK || type_width != TYPE_WIDTHS[i]) {
            fail_screen("TYPE", rc ? rc : 0xE9u);
        }
    }
    if (!rsql_type_is_variable(&TYPE_SPECS[8]) ||
        !rsql_type_is_variable(&TYPE_SPECS[9]) ||
        rsql_type_is_variable(&TYPE_SPECS[7])) {
        fail_screen("VARTYPE", 0xEAu);
    }
    rc = rsql_page_allocate(&page);
    if (rc != RSQL_OK || page <= rsql_page_catalog_root() ||
        page < rsql_page_first_usable()) {
        fail_screen("ALLOC", rc ? rc : 0xE1u);
    }
    for (i = 0u; i < RSQL_REU_PAGE_SIZE; ++i) {
        page_data[i] = (unsigned char)(i ^ 0x5Au);
    }
    address = rsql_reu_page_address(page);
    rc = rsql_reu_write(address, page_data, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) fail_screen("WRITE", rc);
    memset(page_readback, 0, sizeof(page_readback));
    rc = rsql_reu_read(address, page_readback, sizeof(page_readback));
    if (rc != RSQL_OK ||
        memcmp(page_data, page_readback, sizeof(page_data)) != 0) {
        fail_screen("READ", rc ? rc : 0xE2u);
    }
    rc = rsql_page_is_allocated(page, &allocated);
    if (rc != RSQL_OK || !allocated) fail_screen("BITSET", rc ? rc : 0xE3u);
    rc = rsql_page_free(page);
    if (rc != RSQL_OK) fail_screen("FREE", rc);
    rc = rsql_page_is_allocated(page, &allocated);
    if (rc != RSQL_OK || allocated) fail_screen("BITCLR", rc ? rc : 0xE4u);

    create_table.name = "PEOPLE";
    create_table.column_count = 5u;
    create_table.columns = PEOPLE_COLUMNS;
    create_table.flags = 0u;
    create_table.table_page = RSQL_PAGE_NONE;
    rc = rsql_table_create(&create_table);
    if (rc != RSQL_OK) fail_screen("CREATE", rc);
    rc = rsql_table_find("people", &table_info);
    if (rc != RSQL_OK || table_info.table_page != create_table.table_page ||
        table_info.row_width != sizeof(row_data) ||
        table_info.column_count != 5u) {
        fail_screen("CATALOG", rc ? rc : 0xE6u);
    }
    rc = rsql_column_info(table_info.table_page, 3u, &column_info);
    if (rc != RSQL_OK || column_info.type.tag != RSQL_TYPE_CHAR ||
        column_info.type.parameter != 12u || column_info.offset != 6u ||
        strcmp(column_info.name, "NAME") != 0) {
        fail_screen("COLUMN", rc ? rc : 0xE7u);
    }
    rc = rsql_table_create(&create_table);
    if (rc != RSQL_ERR_ALREADY_EXISTS) fail_screen("DUP", rc);

    create_enum.name = "COLOR";
    create_enum.width = 1u;
    create_enum.member_count = (unsigned char)(sizeof(COLOR_MEMBERS) /
                                                sizeof(COLOR_MEMBERS[0]));
    create_enum.members = COLOR_MEMBERS;
    create_enum.enum_id = 0u;
    rc = rsql_enum_create(&create_enum);
    if (rc != RSQL_OK) fail_screen("ENUMCREATE", rc);
    rc = rsql_enum_find("color", &enum_info);
    if (rc != RSQL_OK || enum_info.enum_id != create_enum.enum_id ||
        enum_info.width != 1u || enum_info.member_count != 14u) {
        fail_screen("ENUMFIND", rc ? rc : 0xF1u);
    }
    rc = rsql_enum_member_value(enum_info.enum_id, "lightgreen", &enum_value);
    if (rc != RSQL_OK || enum_value != 13u) {
        fail_screen("ENUMVALUE", rc ? rc : 0xF2u);
    }
    rc = rsql_enum_member_name(enum_info.enum_id, 2u, enum_name,
                               sizeof(enum_name));
    if (rc != RSQL_OK || strcmp(enum_name, "RED") != 0) {
        fail_screen("ENUMNAME", rc ? rc : 0xF3u);
    }
    rc = rsql_enum_create(&create_enum);
    if (rc != RSQL_ERR_ALREADY_EXISTS) fail_screen("ENUMDUP", rc);

    rc = rsql_overlay_load(1u);
    if (rc != RSQL_OK) fail_screen("OVLROW", rc);
    memset(row_data, 0, sizeof(row_data));
    row_data[1] = 1u;
    row_data[2] = 42u;
    row_data[3] = 0u;
    row_data[4] = 0x80u;
    row_data[5] = 12u;
    memset(&row_data[6], ' ', 12u);
    memcpy(&row_data[6], "ADA", 3u);
    rc = rsql_row_insert(table_info.table_page, row_data, sizeof(row_data),
                         &row_id);
    if (rc != RSQL_OK) fail_screen("INSERT", rc);
    memset(row_readback, 0, sizeof(row_readback));
    rc = rsql_row_read(table_info.table_page, &row_id, row_readback,
                       sizeof(row_readback));
    if (rc != RSQL_OK || memcmp(row_data, row_readback, sizeof(row_data)) != 0) {
        fail_screen("ROWREAD", rc ? rc : 0xE8u);
    }
    rc = rsql_row_delete(table_info.table_page, &row_id);
    if (rc != RSQL_OK) fail_screen("DELETE", rc);
    rc = rsql_row_read(table_info.table_page, &row_id, row_readback,
                       sizeof(row_readback));
    if (rc != RSQL_ERR_NOT_FOUND) fail_screen("DELETED", rc);
    rc = rsql_row_insert(table_info.table_page, row_data, sizeof(row_data),
                         &row_id);
    if (rc != RSQL_OK || row_id.slot != 0u) fail_screen("REUSE", rc);
    rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail_screen("OVLMETA", rc);
    rc = rsql_catalog_open();
    if (rc != RSQL_OK) fail_screen("REOPEN", rc);
    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail_screen("SHUTDOWN", rc);
    init.format_if_missing = 0u;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail_screen("REINIT", rc);
    rc = rsql_table_find("PEOPLE", &table_info);
    if (rc != RSQL_OK) fail_screen("REFIND", rc);
    rc = rsql_overlay_load(1u);
    if (rc != RSQL_OK) fail_screen("OVLROW2", rc);
    rc = rsql_row_read(table_info.table_page, &row_id, row_readback,
                       sizeof(row_readback));
    if (rc != RSQL_OK || memcmp(row_data, row_readback, sizeof(row_data)) != 0) {
        fail_screen("REREAD", rc ? rc : 0xEBu);
    }
    rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail_screen("OVLMETA2", rc);
    for (i = 0u; i < sizeof(blob_data); ++i) {
        blob_data[i] = (unsigned char)((i * 7u) ^ 0xA6u);
    }
    rc = rsql_blob_create(RSQL_BLOB_KIND_TEXT, blob_data, sizeof(blob_data),
                          &blob_handle);
    if (rc != RSQL_OK) fail_screen("BLOBCREATE", rc);
    rc = rsql_blob_info(&blob_handle, &blob_info);
    if (rc != RSQL_OK || blob_info.length != sizeof(blob_data) ||
        blob_info.kind != RSQL_BLOB_KIND_TEXT) {
        fail_screen("BLOBINFO", rc ? rc : 0xECu);
    }
    for (i = 0u; i < sizeof(blob_data); i += blob_chunk) {
        blob_chunk = (unsigned int)(sizeof(blob_data) - i);
        if (blob_chunk > sizeof(blob_readback)) {
            blob_chunk = sizeof(blob_readback);
        }
        memset(blob_readback, 0, sizeof(blob_readback));
        rc = rsql_blob_read(&blob_handle, (unsigned long)i, blob_readback,
                            blob_chunk, &blob_bytes_read);
        if (rc != RSQL_OK || blob_bytes_read != blob_chunk ||
            memcmp(&blob_data[i], blob_readback, blob_chunk) != 0) {
            fail_screen("BLOBREAD", rc ? rc : 0xEDu);
        }
    }
    memset(blob_readback, 0, 100u);
    rc = rsql_blob_read(&blob_handle, 240ul, blob_readback, 100u,
                        &blob_bytes_read);
    if (rc != RSQL_OK || blob_bytes_read != 100u ||
        memcmp(&blob_data[240], blob_readback, 100u) != 0) {
        fail_screen("BLOBSLICE", rc ? rc : 0xEEu);
    }
    rc = rsql_blob_delete(&blob_handle);
    if (rc != RSQL_OK) fail_screen("BLOBDELETE", rc);
    rc = rsql_blob_info(&blob_handle, &blob_info);
    if (rc != RSQL_ERR_NOT_FOUND) fail_screen("BLOBTOMB", rc);
    rc = rsql_blob_compact(&reclaimed_pages);
    if (rc != RSQL_OK || reclaimed_pages != 3u) {
        fail_screen("COMPACT", rc ? rc : 0xEFu);
    }
    rc = rsql_blob_compact(&reclaimed_pages);
    if (rc != RSQL_OK || reclaimed_pages != 0u) {
        fail_screen("COMPACT2", rc ? rc : 0xF0u);
    }
    rc = rsql_reu_write_byte(0ul, 0u);
    if (rc != RSQL_OK) fail_screen("DAMAGE", rc);
    rc = rsql_shutdown();
    if (rc == RSQL_OK) rc = rsql_init(&init);
    if (rc != RSQL_OK) fail_screen("SUPERB", rc);
    rc = rsql_reu_write_byte(0ul, (unsigned char)'R');
    if (rc != RSQL_OK) fail_screen("RESTORE", rc);

    rc = rsql_overlay_load(2u);
    if (rc != RSQL_OK || rsql_query_parse_phase_id() != 0x52u) {
        fail_screen("OVLPARSE", rc ? rc : 0xF4u);
    }
    rc = rsql_overlay_load(3u);
    if (rc != RSQL_OK || rsql_query_exec_phase_id() != 0x58u) {
        fail_screen("OVLEXEC", rc ? rc : 0xF5u);
    }
    FAILURE_DETAIL_0 = 1u;
    index_exec_expect(SQL_INDEX_TABLE, RSQL_OK, 0u);
    FAILURE_DETAIL_0 = 2u;
    index_exec_expect(SQL_INDEX_INSERT1, RSQL_OK, 1u);
    FAILURE_DETAIL_0 = 3u;
    index_exec_expect(SQL_INDEX_INSERT2, RSQL_OK, 1u);
    FAILURE_DETAIL_0 = 4u;
    index_exec_expect(SQL_INDEX_CREATE, RSQL_OK, 0u);
    rc = rsql_reu_read(rsql_reu_page_address(rsql_page_catalog_root()),
                       page_data, sizeof(page_data));
    if (rc != RSQL_OK) fail_screen("IDXROOT", rc);
    page = rsql_get_u16(&page_data[RSQL_ROOT_FIRST_INDEX]);
    rc = rsql_reu_read(rsql_reu_page_address(page), page_data,
                       sizeof(page_data));
    if (rc != RSQL_OK) fail_screen("IDXDESC", rc);
    rc = rsql_reu_read(rsql_reu_page_address(
                           rsql_get_u16(&page_data[RSQL_INDEX_TABLE])),
                       page_readback, sizeof(page_readback));
    if (rc != RSQL_OK) fail_screen("IDXSOURCE", rc);
    if (page_readback[RSQL_TABLE_ROW_COUNT] != 2u ||
        rsql_get_u16(&page_readback[RSQL_TABLE_ROW_HEAD]) == RSQL_PAGE_NONE) {
        fail_screen("IDXSOURCE", 0x98u);
    }
    if (page_data[RSQL_INDEX_ENTRY_COUNT] != 2u ||
        rsql_get_u16(&page_data[RSQL_INDEX_LEAF_HEAD]) == RSQL_PAGE_NONE) {
        fail_screen("IDXBUILD", 0x97u);
    }
    FAILURE_DETAIL_0 = 5u;
    index_exec_expect(SQL_INDEX_CREATE, RSQL_ERR_ALREADY_EXISTS, 0u);
    FAILURE_DETAIL_0 = 6u;
    index_exec_expect(SQL_INDEX_BAD_VARIABLE, RSQL_ERR_UNSUPPORTED_SQL, 0u);
    FAILURE_DETAIL_0 = 7u;
    index_exec_expect(SQL_INDEX_CREATE_SINGLE, RSQL_OK, 0u);
    FAILURE_DETAIL_0 = 0x81u;
    index_expect_i16(SQL_INDEX_NEGATIVE, 0xFFF9u, 1u);
    FAILURE_DETAIL_0 = 0x82u;
    index_expect_i16(SQL_INDEX_BY_ID, 42u, 1u);
    FAILURE_DETAIL_0 = 0x83u;
    index_expect_i16(SQL_INDEX_LIMIT, 0xFFF9u, 1u);
    FAILURE_DETAIL_0 = 0x84u;
    index_expect_i16(SQL_INDEX_SCALAR, 3u, 1u);
    FAILURE_DETAIL_0 = 0x85u;
    index_expect_i16(SQL_INDEX_AGGREGATE, 35u, 1u);
    FAILURE_DETAIL_0 = 0x86u;
    index_expect_i16(SQL_INDEX_GROUPED, 0xFFF9u, 1u);
    index_open.sql = SQL_INDEX_MISSING;
    index_open.sql_length = strlen(SQL_INDEX_MISSING);
    rc = rsql_query_open(&index_open);
    if (rc != RSQL_ERR_NOT_FOUND) fail_screen("IDXMISS", rc);
    index_open.sql = SQL_INDEX_WRONG_TABLE;
    index_open.sql_length = strlen(SQL_INDEX_WRONG_TABLE);
    rc = rsql_query_open(&index_open);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail_screen("IDXTABLE", rc);
    FAILURE_DETAIL_0 = 8u;
    index_exec_expect(SQL_INDEX_UPDATE, RSQL_OK, 1u);
    index_expect_i16(SQL_INDEX_UPDATED, 42u, 1u);
    index_update_writes = rsql_journal_test_write_count();
    if (index_update_writes == 0u || index_update_writes == 0xFFu) {
        fail_screen("IDXWRITES", 0x99u);
    }
    for (index_fail = 0u; index_fail < index_update_writes; ++index_fail) {
        rsql_journal_test_fail_after(index_fail);
        FAILURE_DETAIL_0 = 9u;
        index_exec_expect(SQL_INDEX_UPDATE_BACK, RSQL_ERR_IO, 0u);
        index_expect_i16(SQL_INDEX_UPDATED, 42u, 1u);
        index_expect_i16(SQL_INDEX_ADA, 0u, 0u);
    }
    FAILURE_DETAIL_0 = 10u;
    index_exec_expect(SQL_INDEX_UPDATE_BACK, RSQL_OK, 1u);
    index_expect_i16(SQL_INDEX_ADA, 42u, 1u);
    FAILURE_DETAIL_0 = 11u;
    index_exec_expect(SQL_INDEX_UPDATE, RSQL_OK, 1u);
    FAILURE_DETAIL_0 = 12u;
    index_exec_expect(SQL_INDEX_INSERT3, RSQL_OK, 1u);
    index_expect_i16(SQL_INDEX_INSERTED, 5u, 1u);
    FAILURE_DETAIL_0 = 13u;
    index_exec_expect(SQL_INDEX_INSERT4, RSQL_OK, 1u);
    index_expect_i16(SQL_INDEX_SPLIT, 6u, 1u);
    index_expect_i16(SQL_INDEX_ORDER, 42u, 1u);
    index_expect_i16(SQL_INDEX_DISTINCT_SCALAR, 6u, 1u);
    rc = rsql_shutdown();
    if (rc == RSQL_OK) rc = rsql_init(&init);
    if (rc != RSQL_OK) fail_screen("IDXREINIT", rc);
    index_expect_i16(SQL_INDEX_UPDATED, 42u, 1u);
    FAILURE_DETAIL_0 = 14u;
    index_exec_expect(SQL_INDEX_DELETE, RSQL_OK, 1u);
    index_expect_i16(SQL_INDEX_NEGATIVE, 0u, 0u);
    index_exec_expect(SQL_VPM_CREATE, RSQL_OK, 0u);
    index_exec_expect(SQL_VPM_INSERT1, RSQL_OK, 1u);
    index_exec_expect(SQL_VPM_INSERT2, RSQL_OK, 1u);
    index_exec_expect(SQL_VPM_INSERT3, RSQL_OK, 1u);
    index_exec_expect(SQL_VPM_UPDATE_TEXT, RSQL_OK, 2u);
    index_exec_expect(SQL_VPM_DELETE, RSQL_OK, 1u);
    index_expect_i16(SQL_VPM_COUNT, 2u, 1u);
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_blob_compact(&reclaimed_pages);
    if (rc != RSQL_OK || reclaimed_pages != 3u) {
        fail_screen("VPMCOMPACT", rc ? rc : 0x9Au);
    }

#ifdef RSQL_QUERY_TEST
    exec_request.sql = SQL_CREATE_TYPES;
    exec_request.sql_length = strlen(SQL_CREATE_TYPES);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_OK) fail_screen("SQLCREATE", rc);
    rc = rsql_table_find("sqltypes", &table_info);
    if (rc != RSQL_OK || table_info.column_count != 8u ||
        table_info.row_width != 33u) {
        fail_screen("SQLTABLE", rc ? rc : 0xD0u);
    }
    rc = rsql_column_info(table_info.table_page, 2u, &column_info);
    if (rc != RSQL_OK || column_info.type.tag != RSQL_TYPE_I16 ||
        !(column_info.type.flags & RSQL_TYPE_FLAG_NULLABLE)) {
        fail_screen("SQLNULL", rc ? rc : 0xD1u);
    }
    rc = rsql_column_info(table_info.table_page, 7u, &column_info);
    if (rc != RSQL_OK || column_info.type.tag != RSQL_TYPE_CHAR ||
        column_info.type.parameter != 9u) {
        fail_screen("SQLCHAR", rc ? rc : 0xD2u);
    }
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_ERR_ALREADY_EXISTS) fail_screen("SQLDUP", rc);

    exec_request.sql = SQL_CREATE_VARIABLES;
    exec_request.sql_length = strlen(SQL_CREATE_VARIABLES);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_OK) fail_screen("SQLVAR", rc);
    rc = rsql_table_find("SQLVAR", &table_info);
    if (rc != RSQL_OK || table_info.column_count != 2u ||
        table_info.row_width != 9u) {
        fail_screen("SQLVARTAB", rc ? rc : 0xD3u);
    }

    exec_request.sql = SQL_CREATE_DML;
    exec_request.sql_length = strlen(SQL_CREATE_DML);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_OK) fail_screen("SQLDML", rc);
    exec_request.sql = SQL_INSERT_DML1;
    exec_request.sql_length = strlen(SQL_INSERT_DML1);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_OK || exec_request.output.affected_rows.bytes[0] != 1u) {
        fail_screen("SQLINS1", rc ? rc : 0xD5u);
    }
    exec_request.sql = SQL_INSERT_DML2;
    exec_request.sql_length = strlen(SQL_INSERT_DML2);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_OK || exec_request.output.affected_rows.bytes[0] != 1u) {
        fail_screen("SQLINS2", rc ? rc : 0xD6u);
    }
    rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail_screen("SQLMETA", rc);
    rc = rsql_table_find("SQLDML", &table_info);
    if (rc != RSQL_OK || table_info.row_width != 16u) {
        fail_screen("SQLDMLTAB", rc ? rc : 0xD7u);
    }
    rc = rsql_overlay_load(1u);
    if (rc != RSQL_OK) fail_screen("SQLROW", rc);
    rc = rsql_row_first(table_info.table_page, &row_id);
    if (rc != RSQL_OK) fail_screen("SQLFIRST", rc);
    memset(row_readback, 0, sizeof(row_readback));
    rc = rsql_row_read(table_info.table_page, &row_id, row_readback,
                       sizeof(row_readback));
    if (rc != RSQL_OK || row_readback[0] != 0x08u ||
        row_readback[1] != 42u || row_readback[2] != 0u ||
        memcmp(&row_readback[3], "ADA     ", 8u) != 0 ||
        row_readback[11] != 1u) {
        fail_screen("SQLREAD1", rc ? rc : 0xD8u);
    }
    rc = rsql_row_next(table_info.table_page, &row_id, &row_id);
    if (rc != RSQL_OK) fail_screen("SQLNEXT", rc);
    memset(row_readback, 0, sizeof(row_readback));
    rc = rsql_row_read(table_info.table_page, &row_id, row_readback,
                       sizeof(row_readback));
    if (rc != RSQL_OK || row_readback[0] != 0u ||
        row_readback[1] != 0xF9u || row_readback[2] != 0xFFu ||
        memcmp(&row_readback[3], "O'NEIL  ", 8u) != 0 ||
        row_readback[11] != 0u || row_readback[12] != 0x40u ||
        row_readback[13] != 0xE2u || row_readback[14] != 0x01u ||
        row_readback[15] != 0u) {
        fail_screen("SQLREAD2", rc ? rc : 0xD9u);
    }
    if (rsql_row_next(table_info.table_page, &row_id, &row_id) !=
        RSQL_ERR_NOT_FOUND) fail_screen("SQLEND", 0xDAu);
    exec_request.sql = SQL_INSERT_RANGE;
    exec_request.sql_length = strlen(SQL_INSERT_RANGE);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_ERR_TYPE_MISMATCH) fail_screen("SQLRANGE", rc);

    query_open.sql = SQL_SELECT_COUNT;
    query_open.sql_length = strlen(SQL_SELECT_COUNT);
    rc = rsql_query_open(&query_open);
    if (rc != RSQL_OK || query_open.column_count != 1u) {
        fail_screen("QCOUNTOPEN", rc ? rc : 0xDBu);
    }
    cursor_next.cursor = query_open.cursor;
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || !cursor_next.has_row) {
        fail_screen("QCOUNTNEXT", rc ? rc : 0xDCu);
    }
    cursor_column.cursor = query_open.cursor;
    cursor_column.column = 0u;
    rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || cursor_column.value.type.tag != RSQL_TYPE_I64 ||
        cursor_column.value.is_null || cursor_column.value.length != 8u ||
        cursor_column.value.bytes[0] != 2u ||
        cursor_column.value.bytes[1] != 0u) {
        fail_screen("QCOUNTCOL", rc ? rc : 0xDDu);
    }
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || cursor_next.has_row) {
        fail_screen("QCOUNTEND", rc ? rc : 0xDEu);
    }
    query_close.cursor = query_open.cursor;
    rc = rsql_query_close(&query_close);
    if (rc != RSQL_OK) fail_screen("QCOUNTCLOSE", rc);

    query_open.sql = SQL_SELECT_COUNT_NONNULL;
    query_open.sql_length = strlen(SQL_SELECT_COUNT_NONNULL);
    rc = rsql_query_open(&query_open);
    if (rc != RSQL_OK) fail_screen("QWHEREOPEN", rc);
    cursor_next.cursor = query_open.cursor;
    rc = rsql_cursor_next(&cursor_next);
    cursor_column.cursor = query_open.cursor;
    cursor_column.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || !cursor_next.has_row ||
        cursor_column.value.bytes[0] != 1u) {
        fail_screen("QWHERECOUNT", rc ? rc : 0xB1u);
    }
    query_close.cursor = query_open.cursor;
    rc = rsql_query_close(&query_close);
    if (rc != RSQL_OK) fail_screen("QWHERECLOSE", rc);

    query_open.sql = SQL_SELECT_NEGATIVE;
    query_open.sql_length = strlen(SQL_SELECT_NEGATIVE);
    rc = rsql_query_open(&query_open);
    if (rc != RSQL_OK) fail_screen("QNEGOPEN", rc);
    cursor_next.cursor = query_open.cursor;
    rc = rsql_cursor_next(&cursor_next);
    cursor_column.cursor = query_open.cursor;
    cursor_column.column = 0u;
    if (rc == RSQL_OK) rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || !cursor_next.has_row ||
        cursor_column.value.bytes[0] != 0xF9u ||
        cursor_column.value.bytes[1] != 0xFFu) {
        fail_screen("QNEGVALUE", rc ? rc : 0xB2u);
    }
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || cursor_next.has_row) {
        fail_screen("QNEGEND", rc ? rc : 0xB3u);
    }
    query_close.cursor = query_open.cursor;
    rc = rsql_query_close(&query_close);
    if (rc != RSQL_OK) fail_screen("QNEGCLOSE", rc);

    query_open.sql = SQL_SELECT_PROJECT;
    query_open.sql_length = strlen(SQL_SELECT_PROJECT);
    rc = rsql_query_open(&query_open);
    if (rc != RSQL_OK || query_open.column_count != 3u) {
        fail_screen("QPROJOPEN", rc ? rc : 0xDFu);
    }
    cursor_next.cursor = query_open.cursor;
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || !cursor_next.has_row) {
        fail_screen("QPROJNEXT", rc ? rc : 0xC1u);
    }
    cursor_column.cursor = query_open.cursor;
    cursor_column.column = 1u;
    rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || !cursor_column.value.is_null ||
        cursor_column.value.type.tag != RSQL_TYPE_I32) {
        fail_screen("QPROJNULL", rc ? rc : 0xC2u);
    }
    cursor_column.column = 2u;
    rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || cursor_column.value.bytes[0] != 42u ||
        cursor_column.value.bytes[1] != 0u) {
        fail_screen("QPROJID", rc ? rc : 0xC3u);
    }
    memset(row_readback, 0, sizeof(row_readback));
    value_read.cursor = query_open.cursor;
    value_read.column = 0u;
    value_read.offset = 0u;
    value_read.destination = row_readback;
    value_read.capacity = 8u;
    rc = rsql_value_read(&value_read);
    if (rc != RSQL_OK || value_read.bytes_read != 8u ||
        memcmp(row_readback, "ADA     ", 8u) != 0) {
        fail_screen("QREAD1", rc ? rc : 0xC4u);
    }
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || !cursor_next.has_row) {
        fail_screen("QPROJNEXT2", rc ? rc : 0xC5u);
    }
    cursor_column.column = 1u;
    rc = rsql_cursor_column(&cursor_column);
    if (rc != RSQL_OK || cursor_column.value.is_null ||
        cursor_column.value.bytes[0] != 0x40u ||
        cursor_column.value.bytes[1] != 0xE2u ||
        cursor_column.value.bytes[2] != 0x01u) {
        fail_screen("QPROJSCORE", rc ? rc : 0xC6u);
    }
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_OK || cursor_next.has_row) {
        fail_screen("QPROJEND", rc ? rc : 0xC7u);
    }
    query_close.cursor = query_open.cursor;
    rc = rsql_query_close(&query_close);
    if (rc != RSQL_OK) fail_screen("QPROJCLOSE", rc);
    rc = rsql_cursor_next(&cursor_next);
    if (rc != RSQL_ERR_CURSOR_STATE) fail_screen("QSTATE", rc);

    exec_request.sql = SQL_BAD_CHAR;
    exec_request.sql_length = strlen(SQL_BAD_CHAR);
    rc = rsql_exec(&exec_request);
    error_info = rsql_last_error();
    if (rc != RSQL_ERR_SYNTAX) fail_screen("SQLRCBAD", rc ? rc : 0xD1u);
    if (error_info->code != RSQL_ERR_SYNTAX) {
        fail_screen("SQLCODE", error_info->code ? error_info->code : 0xD2u);
    }
    if (error_info->byte_offset == 0u) fail_screen("SQLOFF", 0xD3u);
    exec_request.sql = SQL_UNSUPPORTED;
    exec_request.sql_length = strlen(SQL_UNSUPPORTED);
    rc = rsql_exec(&exec_request);
    if (rc != RSQL_ERR_UNSUPPORTED_SQL) fail_screen("SQLUNSUP", rc);
#endif

    old_cpu_port = CPU_PORT;
    CPU_PORT = (unsigned char)(old_cpu_port & 0xFEu);
    ((volatile unsigned char*)RSQL_OVERLAY_WINDOW)[0] = 0u;
    ((volatile unsigned char*)RSQL_OVERLAY_WINDOW)[RSQL_OVERLAY_SIZE - 1u] = 0u;
    CPU_PORT = old_cpu_port;
    rc = rsql_overlay_load(0u);
    if (rc != RSQL_OK) fail_screen("OVLRESTORE", rc);
    rc = rsql_catalog_open();
    if (rc != RSQL_OK) fail_screen("OVLENTER", rc);

    FOUNDATION_SENTINEL = 0xA5u;
    BORDER_COLOR = COLOR_GREEN;
    for (;;) {}
    return 0;
}

#include <string.h>

#include "rsql.h"
#include "rsql_export.h"

#define FOUNDATION_SENTINEL (*(volatile rsql_u8*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile rsql_u8*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile rsql_u8*)0xCFF2)
#define FAILURE_STAGE (*(volatile rsql_u8*)0xCFF3)
#define FAILURE_DETAIL (*(volatile rsql_u8*)0xCFF5)
#define CHECKPOINT_CONTROL (*(volatile rsql_u8*)0xCFFF)
#define BORDER_COLOR (*(volatile rsql_u8*)0xD020)

static const char SQL_CREATE[] =
    "CREATE TABLE CP(ID I16,NOTE TEXT NULL,STATUS STATE)";
static const char SQL_TYPE[] =
    "CREATE TYPE STATE AS ENUM8(NEW=1,DONE=2)";
static const char SQL_INDEX[] = "CREATE INDEX CP_ID ON CP(ID)";
static const char SQL_INSERT1[] =
    "INSERT INTO CP VALUES(1,'ALPHA',STATE.NEW)";
static const char SQL_INSERT2[] =
    "INSERT INTO CP VALUES(2,'BETA',STATE.DONE)";
static const char SQL_TEMP[] =
    "CREATE TEMP TABLE SCRATCH(ID I16)";
static const char SQL_DELETE[] = "DELETE FROM CP";
static const char SQL_SELECT[] = "SELECT ID,NOTE FROM CP ORDER BY ID";
static const char SQL_SELECT_TEMP[] = "SELECT ID FROM SCRATCH";
static const char SQL_EXPORT[] = "SELECT ID,NOTE,STATUS FROM CP ORDER BY ID";
/* Lower-case source text maps to unshifted PETSCII file-name bytes in cc65. */
static const char EXPORT_FILE[] = "@0:cpexport,s,w";
static const char SQL_SHOW_DATABASE[] = "SHOW DATABASE";
static const char SQL_SHOW_TABLES[] = "SHOW TABLES";
static const char SQL_SHOW_COLUMNS[] = "SHOW COLUMNS FROM CP";
static const char SQL_SHOW_INDEXES[] = "SHOW INDEXES";
static const char SQL_SHOW_TYPES[] = "SHOW TYPES";
static const char SQL_SHOW_MEMBERS[] = "SHOW MEMBERS FROM STATE";

typedef union InspectRecord {
    RsqlDatabaseInfo database;
    RsqlSchemaTableInfo table;
    RsqlSchemaColumnInfo column;
    RsqlSchemaIndexInfo index;
    RsqlSchemaTypeInfo type;
    RsqlSchemaMemberInfo member;
} InspectRecord;

static InspectRecord inspect_record;

static void fail(rsql_u8 stage, rsql_u8 detail) {
    FAILURE_STAGE = stage;
    FAILURE_DETAIL = detail;
    FOUNDATION_SENTINEL = detail ? detail : 0xFFu;
    BORDER_COLOR = 2u;
    for (;;) {}
}

static void exec_ok(RsqlExecRequest* request, const char* sql,
                    rsql_u8 stage) {
    rsql_u8 rc;
    request->sql = sql;
    request->sql_length = strlen(sql);
    rc = rsql_exec(request);
    if (rc != RSQL_OK) fail(stage, rc);
}

static void inspect_ok(RsqlExecRequest* request, const char* sql,
                       rsql_u16 size, rsql_u16 start, rsql_u8 stage) {
    rsql_u8 rc;
    memset(&inspect_record, 0, sizeof(inspect_record));
    request->sql = sql;
    request->sql_length = strlen(sql);
    request->output.inspect.records = &inspect_record;
    request->output.inspect.capacity = size;
    request->output.inspect.start = start;
    request->output.inspect.returned = 0u;
    rc = rsql_exec(request);
    if (rc != RSQL_OK || request->output.inspect.returned != 1u) {
        fail(stage, rc ? rc : 0xEBu);
    }
}

static rsql_u16 i32_low(const RsqlI32* value) {
    return (rsql_u16)value->bytes[0] | ((rsql_u16)value->bytes[1] << 8u);
}

static void test_inspection(RsqlExecRequest* exec) {
    rsql_u16 capacity;
    rsql_u16 used;
    rsql_u16 free_pages;

    inspect_ok(exec, SQL_SHOW_DATABASE, sizeof(RsqlDatabaseInfo), 0u, 0x60u);
    capacity = i32_low(&inspect_record.database.database_capacity_pages);
    used = i32_low(&inspect_record.database.database_used_pages);
    free_pages = i32_low(&inspect_record.database.database_free_pages);
    if (capacity == 0u || used == 0u || (rsql_u16)(used + free_pages) != capacity ||
        inspect_record.database.table_count != 1u ||
        inspect_record.database.index_count != 1u ||
        inspect_record.database.type_count != 1u) {
        fail(0x61u, 0xECu);
    }

    inspect_ok(exec, SQL_SHOW_TABLES, sizeof(RsqlSchemaTableInfo), 0u, 0x62u);
    if (inspect_record.table.flags != 0u ||
        inspect_record.table.column_count != 3u ||
        i32_low(&inspect_record.table.row_count) != 2u ||
        i32_low(&inspect_record.table.row_pages) == 0u ||
        strcmp(inspect_record.table.name, "CP") != 0) {
        fail(0x63u, 0xEDu);
    }

    inspect_ok(exec, SQL_SHOW_COLUMNS, sizeof(RsqlSchemaColumnInfo), 1u, 0x64u);
    if (inspect_record.column.type.tag != RSQL_TYPE_TEXT) {
        fail(0x65u, inspect_record.column.type.tag);
    }
    if (inspect_record.column.offset != 3u) {
        fail(0x65u, (rsql_u8)inspect_record.column.offset);
    }
    if (strcmp(inspect_record.column.name, "NOTE") != 0) {
        fail(0x65u, (rsql_u8)inspect_record.column.name[0]);
    }

    inspect_ok(exec, SQL_SHOW_INDEXES, sizeof(RsqlSchemaIndexInfo), 0u, 0x66u);
    if (inspect_record.index.column_count != 1u ||
        inspect_record.index.columns[0] != 0u ||
        i32_low(&inspect_record.index.entry_count) != 2u ||
        i32_low(&inspect_record.index.leaf_pages) == 0u ||
        strcmp(inspect_record.index.name, "CP_ID") != 0) {
        fail(0x67u, 0xEFu);
    }

    inspect_ok(exec, SQL_SHOW_TYPES, sizeof(RsqlSchemaTypeInfo), 0u, 0x68u);
    if (inspect_record.type.width != 1u ||
        inspect_record.type.member_count != 2u ||
        i32_low(&inspect_record.type.member_pages) == 0u ||
        strcmp(inspect_record.type.name, "STATE") != 0) {
        fail(0x69u, 0xF0u);
    }

    inspect_ok(exec, SQL_SHOW_MEMBERS, sizeof(RsqlSchemaMemberInfo), 1u, 0x6Au);
    if (inspect_record.member.value != 2u ||
        strcmp(inspect_record.member.name, "DONE") != 0) {
        fail(0x6Bu, 0xF1u);
    }
}

static void expect_row(RsqlCursorHandle cursor, rsql_u8 id,
                       const char* text, rsql_u8 stage) {
    RsqlCursorColumnRequest column;
    RsqlValueReadRequest read;
    char bytes[8];
    rsql_u8 rc;

    column.cursor = cursor;
    column.column = 0u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_I16 ||
        column.value.bytes[0] != id || column.value.bytes[1] != 0u) {
        fail(stage, rc ? rc : 0xE1u);
    }

    column.column = 1u;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK || column.value.is_null ||
        column.value.type.tag != RSQL_TYPE_TEXT ||
        column.value.length != strlen(text)) {
        fail(stage, rc ? rc : 0xE2u);
    }
    memset(bytes, 0, sizeof(bytes));
    read.cursor = cursor;
    read.column = 1u;
    read.offset = 0u;
    read.destination = bytes;
    read.capacity = sizeof(bytes);
    rc = rsql_value_read(&read);
    if (rc != RSQL_OK || read.bytes_read != strlen(text) ||
        memcmp(bytes, text, read.bytes_read) != 0) {
        fail(stage, rc ? rc : 0xE3u);
    }
}

static void test_old_format_rejected(RsqlInitRequest* init) {
    unsigned long address;
    rsql_u8 checksum;
    rsql_u8 page;
    rsql_u8 rc;

    for (page = 0u; page < 2u; ++page) {
        address = rsql_reu_page_address(page);
        rc = rsql_reu_read_byte(address + 12ul, &checksum);
        if (rc != RSQL_OK) fail(0x6Du, rc);
        rc = rsql_reu_write_byte(address + 4ul, 1u);
        if (rc != RSQL_OK) fail(0x6Du, rc);
        /* The superblock checksum is XOR-based. Convert a valid v2 copy into
         * a checksummed v1 copy so this tests version rejection, not damage. */
        rc = rsql_reu_write_byte(address + 12ul,
                                 (rsql_u8)(checksum ^ 2u ^ 1u));
        if (rc != RSQL_OK) fail(0x6Du, rc);
    }
    rc = rsql_restore(init);
    if (rc != RSQL_ERR_CORRUPT_STORAGE) fail(0x6Eu, rc ? rc : 0xF2u);
}

int main(void) {
    RsqlInitRequest init;
    RsqlExecRequest exec;
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlQueryCloseRequest close;
    RsqlD81ExportRequest export_request;
    rsql_u8 rc;

    BORDER_COLOR = 0u;
    FOUNDATION_SENTINEL = 0u;
    CHECKPOINT_CONTROL = 0u;
    memset(&init, 0, sizeof(init));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail(0x10u, rc);
    if (rsql_reu_size_kib() != (rsql_u16)(512u << REU_SIZE_SELECTOR)) {
        fail(0x11u, 0xE4u);
    }

    memset(&exec, 0, sizeof(exec));
    exec_ok(&exec, SQL_TYPE, 0x20u);
    exec_ok(&exec, SQL_CREATE, 0x21u);
    exec_ok(&exec, SQL_INSERT1, 0x22u);
    exec_ok(&exec, SQL_INSERT2, 0x23u);
    exec_ok(&exec, SQL_INDEX, 0x24u);
    exec_ok(&exec, SQL_TEMP, 0x25u);

    rc = rsql_checkpoint();
    if (rc != RSQL_OK) fail(0x30u, rc);
    FOUNDATION_SENTINEL = 0xC1u;
    while (CHECKPOINT_CONTROL == 0u) {}

    /* A VICE snapshot fallback resumes here, whereas a direct REU-image load
     * resumes at the second wait below. Control value 2 handles both paths. */
    if (CHECKPOINT_CONTROL != 2u) {
        exec_ok(&exec, SQL_DELETE, 0x40u);
        if (exec.output.affected_rows.bytes[0] != 2u ||
            exec.output.affected_rows.bytes[1] != 0u) {
            fail(0x41u, 0xE5u);
        }
        FOUNDATION_SENTINEL = 0xC2u;
        while (CHECKPOINT_CONTROL != 2u) {}
    }

    init.format_if_missing = 0u;
    rc = rsql_restore(&init);
    if (rc != RSQL_OK) fail(0x50u, rc);

    test_inspection(&exec);

    memset(&export_request, 0, sizeof(export_request));
    export_request.query = SQL_EXPORT;
    export_request.query_length = strlen(SQL_EXPORT);
    export_request.filename = EXPORT_FILE;
    export_request.device = 8u;
    export_request.logical_file = 2u;
    rc = rsql_export_d81(&export_request);
    if (rc != RSQL_OK || export_request.rows_written.bytes[0] != 2u ||
        export_request.rows_written.bytes[1] != 0u ||
        export_request.bytes_written.bytes[0] != 52u ||
        export_request.bytes_written.bytes[1] != 0u) {
        fail(0x6Cu, rc ? rc : export_request.bytes_written.bytes[0]);
    }

    memset(&open, 0, sizeof(open));
    open.sql = SQL_SELECT_TEMP;
    open.sql_length = strlen(SQL_SELECT_TEMP);
    rc = rsql_query_open(&open);
    if (rc != RSQL_ERR_NOT_FOUND) fail(0x51u, rc ? rc : 0xE6u);

    memset(&open, 0, sizeof(open));
    open.sql = SQL_SELECT;
    open.sql_length = strlen(SQL_SELECT);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK || open.column_count != 2u) {
        fail(0x52u, rc ? rc : 0xE7u);
    }
    next.cursor = open.cursor;
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(0x53u, rc ? rc : 0xE8u);
    expect_row(open.cursor, 1u, "ALPHA", 0x54u);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || !next.has_row) fail(0x55u, rc ? rc : 0xE9u);
    expect_row(open.cursor, 2u, "BETA", 0x56u);
    rc = rsql_cursor_next(&next);
    if (rc != RSQL_OK || next.has_row) fail(0x57u, rc ? rc : 0xEAu);
    close.cursor = open.cursor;
    rc = rsql_query_close(&close);
    if (rc != RSQL_OK) fail(0x58u, rc);

    test_old_format_rejected(&init);

    FOUNDATION_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    for (;;) {}
    return 0;
}

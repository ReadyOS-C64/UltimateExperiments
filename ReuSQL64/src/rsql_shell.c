#include <string.h>

#include "rsql.h"
#include "rsql_export.h"
#include "rsql_shell.h"

typedef union ShellInspectRecord {
    RsqlDatabaseInfo database;
    RsqlSchemaTableInfo table;
    RsqlSchemaColumnInfo column;
    RsqlSchemaIndexInfo index;
    RsqlSchemaTypeInfo type;
    RsqlSchemaMemberInfo member;
} ShellInspectRecord;

static ShellInspectRecord g_record;
static char g_export_name[32];
static char g_translated[40];

static rsql_u8 fold(char value) {
    return value >= 'a' && value <= 'z'
        ? (rsql_u8)(value - ('a' - 'A')) : (rsql_u8)value;
}

static rsql_u8 word(const char* text, const char* expected) {
    while (*expected) {
        if (fold(*text++) != (rsql_u8)*expected++) return 0u;
    }
    return *text == 0 || *text == ' ' || *text == '\t';
}

static const char* skip_space(const char* text) {
    while (*text == ' ' || *text == '\t') ++text;
    return text;
}

static void write_bytes(RsqlShell* shell, const char* bytes, rsql_u16 length) {
    if (shell->write && length) shell->write(bytes, length, shell->user);
}

static void write_text(RsqlShell* shell, const char* text) {
    write_bytes(shell, text, (rsql_u16)strlen(text));
}

static void write_char(RsqlShell* shell, char value) {
    write_bytes(shell, &value, 1u);
}

static void write_u16(RsqlShell* shell, rsql_u16 value) {
    char digits[5];
    rsql_u8 used = 0u;
    do {
        digits[used++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value);
    while (used) write_char(shell, digits[--used]);
}

static rsql_u8 negative_bytes(const rsql_u8* value, rsql_u8 width) {
    return (value[width - 1u] & 0x80u) != 0u;
}

static void write_integer(RsqlShell* shell, const rsql_u8* source,
                          rsql_u8 width) {
    rsql_u8 value[8];
    char digits[20];
    rsql_u8 negative;
    rsql_u8 carry;
    rsql_u8 quotient;
    rsql_u8 remainder;
    rsql_u8 used = 0u;
    rsql_u8 index;
    memcpy(value, source, width);
    negative = negative_bytes(value, width);
    if (negative) {
        carry = 1u;
        for (index = 0u; index < width; ++index) {
            quotient = (rsql_u8)(~value[index] + carry);
            carry = carry && quotient == 0u;
            value[index] = quotient;
        }
        write_char(shell, '-');
    }
    do {
        remainder = 0u;
        for (index = width; index != 0u; --index) {
            quotient = value[index - 1u];
            value[index - 1u] = (rsql_u8)(((rsql_u16)remainder << 8u |
                                           quotient) / 10u);
            remainder = (rsql_u8)(((rsql_u16)remainder << 8u |
                                    quotient) % 10u);
        }
        digits[used++] = (char)('0' + remainder);
        for (index = 0u; index < width && value[index] == 0u; ++index) {}
    } while (index != width);
    while (used) write_char(shell, digits[--used]);
}

static void write_i32(RsqlShell* shell, const RsqlI32* value) {
    write_integer(shell, value->bytes, 4u);
}

static void write_hex_byte(RsqlShell* shell, rsql_u8 value) {
    static const char hex[] = "0123456789ABCDEF";
    write_char(shell, hex[value >> 4u]);
    write_char(shell, hex[value & 15u]);
}

static const char* type_name(rsql_u8 tag) {
    switch (tag) {
        case RSQL_TYPE_BOOLEAN: return "BOOLEAN";
        case RSQL_TYPE_I8: return "I8";
        case RSQL_TYPE_I16: return "I16";
        case RSQL_TYPE_I32: return "I32";
        case RSQL_TYPE_I64: return "I64";
        case RSQL_TYPE_FIXED8_8: return "FIXED8_8";
        case RSQL_TYPE_FLOAT5: return "FLOAT";
        case RSQL_TYPE_CHAR: return "CHAR";
        case RSQL_TYPE_TEXT: return "TEXT";
        case RSQL_TYPE_BLOB: return "BLOB";
        case RSQL_TYPE_ENUM8: return "ENUM8";
        case RSQL_TYPE_ENUM16: return "ENUM16";
    }
    return "?";
}

static void write_error(RsqlShell* shell, rsql_u8 rc) {
    const RsqlErrorInfo* error = rsql_last_error();
    write_text(shell, "ERROR ");
    write_u16(shell, rc);
    if (error) {
        write_text(shell, " AT ");
        write_u16(shell, error->byte_offset);
        if (error->message) {
            write_char(shell, ' ');
            write_text(shell, error->message);
        }
    }
    write_char(shell, '\n');
}

static rsql_u8 write_variable(RsqlShell* shell, RsqlCursorHandle cursor,
                              rsql_u8 column, rsql_u16 length) {
    RsqlValueReadRequest read;
    char chunk[32];
    rsql_u16 offset = 0u;
    rsql_u8 rc;
    while (offset < length) {
        read.cursor = cursor;
        read.column = column;
        read.offset = offset;
        read.destination = chunk;
        read.capacity = sizeof(chunk);
        read.bytes_read = 0u;
        rc = rsql_value_read(&read);
        if (rc != RSQL_OK) return rc;
        if (!read.bytes_read) return RSQL_ERR_INTERNAL;
        write_bytes(shell, chunk, read.bytes_read);
        offset += read.bytes_read;
    }
    return RSQL_OK;
}

static rsql_u8 write_value(RsqlShell* shell, RsqlCursorHandle cursor,
                           rsql_u8 column_index) {
    RsqlCursorColumnRequest column;
    rsql_i16 fixed;
    rsql_u16 magnitude;
    rsql_u16 fraction;
    rsql_u8 index;
    rsql_u8 rc;
    column.cursor = cursor;
    column.column = column_index;
    rc = rsql_cursor_column(&column);
    if (rc != RSQL_OK) return rc;
    if (column.value.is_null) {
        write_text(shell, "NULL");
        return RSQL_OK;
    }
    switch (column.value.type.tag) {
        case RSQL_TYPE_BOOLEAN:
            write_text(shell, column.value.bytes[0] ? "TRUE" : "FALSE");
            return RSQL_OK;
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8:
            write_integer(shell, column.value.bytes, 1u);
            return RSQL_OK;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_ENUM16:
            write_integer(shell, column.value.bytes, 2u);
            return RSQL_OK;
        case RSQL_TYPE_I32:
            write_integer(shell, column.value.bytes, 4u);
            return RSQL_OK;
        case RSQL_TYPE_I64:
            write_integer(shell, column.value.bytes, 8u);
            return RSQL_OK;
        case RSQL_TYPE_FIXED8_8:
            fixed = (rsql_i16)((rsql_u16)column.value.bytes[0] |
                               ((rsql_u16)column.value.bytes[1] << 8u));
            if (fixed < 0) {
                write_char(shell, '-');
                magnitude = (rsql_u16)(0u - (rsql_u16)fixed);
            } else magnitude = (rsql_u16)fixed;
            write_u16(shell, magnitude >> 8u);
            write_char(shell, '.');
            fraction = (rsql_u16)(((magnitude & 255u) * 100u + 128u) >> 8u);
            if (fraction < 10u) write_char(shell, '0');
            write_u16(shell, fraction);
            return RSQL_OK;
        case RSQL_TYPE_FLOAT5:
            /* Exact round-trippable physical form until the shell gets a
             * BASIC-ROM FOUT bridge of its own. */
            write_text(shell, "FLOAT($");
            for (index = 0u; index < 5u; ++index) write_hex_byte(shell, column.value.bytes[index]);
            write_char(shell, ')');
            return RSQL_OK;
        case RSQL_TYPE_CHAR:
        case RSQL_TYPE_TEXT:
            return write_variable(shell, cursor, column_index,
                                  column.value.length);
        case RSQL_TYPE_BLOB:
            write_text(shell, "<BLOB ");
            write_u16(shell, column.value.length);
            write_char(shell, '>');
            return RSQL_OK;
    }
    return RSQL_ERR_TYPE_MISMATCH;
}

static rsql_u8 run_select(RsqlShell* shell, const char* sql) {
    RsqlQueryOpenRequest open;
    RsqlCursorNextRequest next;
    RsqlQueryCloseRequest close;
    rsql_u16 rows = 0u;
    rsql_u8 column;
    rsql_u8 rc;
    memset(&open, 0, sizeof(open));
    open.sql = sql;
    open.sql_length = (rsql_u16)strlen(sql);
    rc = rsql_query_open(&open);
    if (rc != RSQL_OK) {
        write_error(shell, rc);
        return rc;
    }
    next.cursor = open.cursor;
    for (;;) {
        rc = rsql_cursor_next(&next);
        if (rc != RSQL_OK || !next.has_row) break;
        for (column = 0u; column < open.column_count; ++column) {
            if (column) write_text(shell, ", ");
            rc = write_value(shell, open.cursor, column);
            if (rc != RSQL_OK) break;
        }
        if (rc != RSQL_OK) break;
        write_char(shell, '\n');
        ++rows;
    }
    close.cursor = open.cursor;
    if (rsql_query_close(&close) != RSQL_OK && rc == RSQL_OK) {
        rc = RSQL_ERR_CURSOR_STATE;
    }
    if (rc != RSQL_OK) {
        write_error(shell, rc);
        return rc;
    }
    write_char(shell, '(');
    write_u16(shell, rows);
    write_text(shell, rows == 1u ? " ROW)\n" : " ROWS)\n");
    return RSQL_OK;
}

static rsql_u16 show_record_size(const char* sql) {
    if (word(sql, "SHOW DATABASE")) return sizeof(RsqlDatabaseInfo);
    if (word(sql, "SHOW TABLES")) return sizeof(RsqlSchemaTableInfo);
    if (word(sql, "SHOW COLUMNS")) return sizeof(RsqlSchemaColumnInfo);
    if (word(sql, "SHOW INDEXES")) return sizeof(RsqlSchemaIndexInfo);
    if (word(sql, "SHOW TYPES")) return sizeof(RsqlSchemaTypeInfo);
    if (word(sql, "SHOW MEMBERS")) return sizeof(RsqlSchemaMemberInfo);
    return 0u;
}

static void write_show_record(RsqlShell* shell, const char* sql) {
    if (word(sql, "SHOW DATABASE")) {
        write_text(shell, "DATABASE REU=");
        write_i32(shell, &g_record.database.reu_pages);
        write_text(shell, " PAGES=");
        write_i32(shell, &g_record.database.database_capacity_pages);
        write_text(shell, " USED=");
        write_i32(shell, &g_record.database.database_used_pages);
        write_text(shell, " FREE=");
        write_i32(shell, &g_record.database.database_free_pages);
        write_text(shell, " TABLES="); write_u16(shell, g_record.database.table_count);
        write_text(shell, " INDEXES="); write_u16(shell, g_record.database.index_count);
        write_text(shell, " TYPES="); write_u16(shell, g_record.database.type_count);
    } else if (word(sql, "SHOW TABLES")) {
        write_text(shell, "TABLE "); write_text(shell, g_record.table.name);
        write_text(shell, " ROWS="); write_i32(shell, &g_record.table.row_count);
        write_text(shell, " COLUMNS="); write_u16(shell, g_record.table.column_count);
        write_text(shell, " WIDTH="); write_u16(shell, g_record.table.row_width);
        if (g_record.table.flags) write_text(shell, " TEMP");
    } else if (word(sql, "SHOW COLUMNS")) {
        write_text(shell, "COLUMN "); write_text(shell, g_record.column.name);
        write_char(shell, ' '); write_text(shell, type_name(g_record.column.type.tag));
        if (g_record.column.type.tag == RSQL_TYPE_CHAR) {
            write_char(shell, '('); write_u16(shell, g_record.column.type.parameter); write_char(shell, ')');
        }
        if (g_record.column.type.flags & RSQL_TYPE_FLAG_NULLABLE) write_text(shell, " NULL");
        write_text(shell, " OFFSET="); write_u16(shell, g_record.column.offset);
    } else if (word(sql, "SHOW INDEXES")) {
        write_text(shell, "INDEX "); write_text(shell, g_record.index.name);
        write_text(shell, " ENTRIES="); write_i32(shell, &g_record.index.entry_count);
        write_text(shell, " PAGES="); write_i32(shell, &g_record.index.leaf_pages);
        write_text(shell, " KEYS="); write_u16(shell, g_record.index.column_count);
    } else if (word(sql, "SHOW TYPES")) {
        write_text(shell, "TYPE "); write_text(shell, g_record.type.name);
        write_text(shell, g_record.type.width == 1u ? " ENUM8" : " ENUM16");
        write_text(shell, " MEMBERS="); write_u16(shell, g_record.type.member_count);
    } else {
        write_text(shell, "MEMBER "); write_text(shell, g_record.member.name);
        write_char(shell, '='); write_u16(shell, g_record.member.value);
    }
    write_char(shell, '\n');
}

static rsql_u8 run_show(RsqlShell* shell, const char* sql) {
    RsqlExecRequest exec;
    rsql_u16 size = show_record_size(sql);
    rsql_u16 start = 0u;
    rsql_u8 rc;
    if (!size) {
        write_error(shell, RSQL_ERR_UNSUPPORTED_SQL);
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    for (;;) {
        memset(&exec, 0, sizeof(exec));
        memset(&g_record, 0, sizeof(g_record));
        exec.sql = sql;
        exec.sql_length = (rsql_u16)strlen(sql);
        exec.output.inspect.records = &g_record;
        exec.output.inspect.capacity = size;
        exec.output.inspect.start = start;
        rc = rsql_exec(&exec);
        if (rc != RSQL_OK) {
            write_error(shell, rc);
            return rc;
        }
        if (!exec.output.inspect.returned) break;
        write_show_record(shell, sql);
        ++start;
    }
    return RSQL_OK;
}

static rsql_u8 run_exec(RsqlShell* shell, const char* sql) {
    RsqlExecRequest exec;
    rsql_u8 rc;
    memset(&exec, 0, sizeof(exec));
    exec.sql = sql;
    exec.sql_length = (rsql_u16)strlen(sql);
    rc = rsql_exec(&exec);
    if (rc != RSQL_OK) {
        write_error(shell, rc);
        return rc;
    }
    write_text(shell, "OK ");
    write_integer(shell, exec.output.affected_rows.bytes, 8u);
    write_text(shell, " AFFECTED\n");
    return RSQL_OK;
}

static rsql_u8 run_export(RsqlShell* shell, const char* arguments) {
    RsqlD81ExportRequest request;
    const char* query;
    rsql_u8 name_length = 0u;
    rsql_u8 rc;
    arguments = skip_space(arguments);
    query = arguments;
    while (*query && *query != ' ' && *query != '\t') ++query;
    if (query == arguments || !*query || (rsql_u16)(query - arguments) > 16u) {
        write_text(shell, "ERROR EXPORT SYNTAX\n");
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    g_export_name[name_length++] = '@';
    g_export_name[name_length++] = '0';
    g_export_name[name_length++] = ':';
    while (arguments != query) g_export_name[name_length++] = *arguments++;
    g_export_name[name_length++] = ',';
    g_export_name[name_length++] = 's';
    g_export_name[name_length++] = ',';
    g_export_name[name_length++] = 'w';
    g_export_name[name_length] = 0;
    query = skip_space(query);
    if (!word(query, "SELECT")) {
        write_text(shell, "ERROR EXPORT REQUIRES SELECT\n");
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    memset(&request, 0, sizeof(request));
    request.query = query;
    request.query_length = (rsql_u16)strlen(query);
    request.filename = g_export_name;
    request.device = shell->device;
    request.logical_file = shell->logical_file;
    rc = rsql_export_d81(&request);
    if (rc != RSQL_OK) {
        write_error(shell, rc);
        return rc;
    }
    write_text(shell, "EXPORTED ");
    write_i32(shell, &request.rows_written);
    write_text(shell, " ROWS ");
    write_i32(shell, &request.bytes_written);
    write_text(shell, " BYTES\n");
    return RSQL_OK;
}

void rsql_shell_init(RsqlShell* shell, RsqlShellWriteFn write, void* user) {
    memset(shell, 0, sizeof(*shell));
    shell->write = write;
    shell->user = user;
    shell->device = 8u;
    shell->logical_file = 3u;
}

rsql_u8 rsql_shell_run_line(RsqlShell* shell, const char* input) {
    const char* line;
    const char* argument;
    rsql_u16 length;
    if (!shell || !input) return RSQL_ERR_INVALID_ARGUMENT;
    line = skip_space(input);
    if (!*line) return RSQL_OK;
    if (*line != '.') {
        if (word(line, "SELECT")) return run_select(shell, line);
        if (word(line, "SHOW")) return run_show(shell, line);
        return run_exec(shell, line);
    }
    ++line;
    if (word(line, "HELP")) {
        write_text(shell, "SQL: SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, SHOW\n");
        write_text(shell, "META: .DATABASE .TABLES .SCHEMA T .INDEXES .TYPES .MEMBERS T\n");
        write_text(shell, "      .CHECKPOINT .EXPORT FILE SELECT... .QUIT\n");
        return RSQL_OK;
    }
    if (word(line, "QUIT")) {
        shell->quit_requested = 1u;
        write_text(shell, "BYE\n");
        return RSQL_OK;
    }
    if (word(line, "CHECKPOINT")) {
        rsql_u8 rc = rsql_checkpoint();
        if (rc != RSQL_OK) write_error(shell, rc);
        else write_text(shell, "CHECKPOINT READY\n");
        return rc;
    }
    if (word(line, "EXPORT")) return run_export(shell, line + 6u);
    if (word(line, "DATABASE")) line = "SHOW DATABASE";
    else if (word(line, "TABLES")) line = "SHOW TABLES";
    else if (word(line, "INDEXES")) line = "SHOW INDEXES";
    else if (word(line, "TYPES")) line = "SHOW TYPES";
    else if (word(line, "SCHEMA")) {
        argument = skip_space(line + 6u);
        length = (rsql_u16)strlen(argument);
        if (!length || length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_INVALID_ARGUMENT;
        memcpy(g_translated, "SHOW COLUMNS FROM ", 18u);
        memcpy(g_translated + 18u, argument, length + 1u);
        line = g_translated;
    } else if (word(line, "MEMBERS")) {
        argument = skip_space(line + 7u);
        length = (rsql_u16)strlen(argument);
        if (!length || length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_INVALID_ARGUMENT;
        memcpy(g_translated, "SHOW MEMBERS FROM ", 18u);
        memcpy(g_translated + 18u, argument, length + 1u);
        line = g_translated;
    } else {
        write_text(shell, "ERROR UNKNOWN META COMMAND\n");
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    return run_show(shell, line);
}

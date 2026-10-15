#include <string.h>

#include "rsql_errors.h"
#include "rsql_index.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"

static rsql_u8 signed_fits(const RsqlI64* value, rsql_u8 width) {
    rsql_u8 fill = (value->bytes[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = width; index < sizeof(value->bytes); ++index) {
        if (value->bytes[index] != fill) return 0u;
    }
    return 1u;
}

static rsql_u8 encode_value(rsql_u8 index) {
    const RsqlParsedValue* value = &g_rsql_statement.values[index];
    const RsqlColumnInfo* column = &g_rsql_execution.columns[index];
    rsql_u8* destination = &g_rsql_execution.row[column->offset];
    rsql_u8 width;
    rsql_u8 byte;

    if (value->kind == RSQL_VALUE_NULL) {
        if (!(column->type.flags & RSQL_TYPE_FLAG_NULLABLE)) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_execution.row[index >> 3u] |=
            (rsql_u8)(1u << (index & 7u));
        return RSQL_OK;
    }
    switch (column->type.tag) {
        case RSQL_TYPE_BOOLEAN:
            if (value->kind != RSQL_VALUE_BOOLEAN) return RSQL_ERR_TYPE_MISMATCH;
            destination[0] = value->integer.bytes[0];
            return RSQL_OK;
        case RSQL_TYPE_I8: width = 1u; break;
        case RSQL_TYPE_I16: width = 2u; break;
        case RSQL_TYPE_I32: width = 4u; break;
        case RSQL_TYPE_I64: width = 8u; break;
        case RSQL_TYPE_ENUM8: width = 1u; break;
        case RSQL_TYPE_ENUM16: width = 2u; break;
        case RSQL_TYPE_FIXED8_8:
            if (value->kind != RSQL_VALUE_INTEGER ||
                !signed_fits(&value->integer, 1u)) return RSQL_ERR_TYPE_MISMATCH;
            destination[0] = 0u;
            destination[1] = value->integer.bytes[0];
            return RSQL_OK;
        case RSQL_TYPE_FLOAT5:
            byte = value->kind;
            if (byte == RSQL_VALUE_FLOAT) {
                memcpy(destination, value->integer.bytes, 5u);
                return RSQL_OK;
            }
            return RSQL_ERR_TYPE_MISMATCH;
        case RSQL_TYPE_CHAR:
            if (value->kind != RSQL_VALUE_STRING ||
                value->length > column->type.parameter) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            memset(destination, ' ', column->type.parameter);
            memcpy(destination, value->string, value->length);
            return RSQL_OK;
        case RSQL_TYPE_TEXT:
            if (value->kind != RSQL_VALUE_STRING) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            return RSQL_OK;
        case RSQL_TYPE_BLOB:
            if (value->kind != RSQL_VALUE_BINARY) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            return RSQL_OK;
        default:
            return RSQL_ERR_UNSUPPORTED_SQL;
    }
    if (value->kind != RSQL_VALUE_INTEGER) return RSQL_ERR_TYPE_MISMATCH;
    if (column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        for (byte = width; byte < sizeof(value->integer.bytes); ++byte) {
            if (value->integer.bytes[byte] != 0u) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        }
    } else if (!signed_fits(&value->integer, width)) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    for (byte = 0u; byte < width; ++byte) {
        destination[byte] = value->integer.bytes[byte];
    }
    return RSQL_OK;
}

rsql_u8 rsql_query_exec_prepare(void) {
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE &&
        g_rsql_statement.column_count != 0u) return RSQL_OK;
    if (g_rsql_statement.kind == RSQL_STMT_INSERT) {
        rsql_u8 index;
        rsql_u8 rc;
        if (g_rsql_statement.value_count != g_rsql_execution.column_count ||
            g_rsql_execution.row_width > sizeof(g_rsql_execution.row)) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        memset(g_rsql_execution.row, 0, g_rsql_execution.row_width);
        for (index = 0u; index < g_rsql_execution.column_count; ++index) {
            rc = encode_value(index);
            if (rc != RSQL_OK) return rc;
        }
        return RSQL_OK;
    }
    if ((g_rsql_statement.kind == RSQL_STMT_SELECT ||
         g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE_AS) &&
        g_rsql_statement.select_mode != 0u) {
        return rsql_index_scan_open();
    }
    if (g_rsql_statement.kind == RSQL_STMT_DELETE) return RSQL_OK;
    if (g_rsql_statement.kind == RSQL_STMT_UPDATE) return RSQL_OK;
    return RSQL_ERR_UNSUPPORTED_SQL;
}

rsql_u8 rsql_query_exec_phase_id(void) {
    return 0x58u;
}

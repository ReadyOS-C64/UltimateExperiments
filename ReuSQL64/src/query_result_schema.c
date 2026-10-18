#include <string.h>

#include "rsql_errors.h"
#include "rsql_query.h"

extern const RsqlColumnInfo* __fastcall__
rsql_result_source_column(rsql_u8 source);

static rsql_u8 result_source_nullable(rsql_u8 source) {
    const RsqlColumnInfo* column = rsql_result_source_column(source);
    return (column->type.flags & RSQL_TYPE_FLAG_NULLABLE) != 0u ||
        ((source & RSQL_SOURCE_INNER) != 0u &&
         g_rsql_cursor.join_type == RSQL_JOIN_LEFT);
}

static rsql_u16 result_u16(const rsql_u8* bytes) {
    return (rsql_u16)bytes[0] | ((rsql_u16)bytes[1] << 8u);
}

static rsql_u8 result_scalar_variable(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u8 source = g_rsql_cursor.projection[result];
    if (base == RSQL_SCALAR_STRING || source == 0xFFu) return 0u;
    if (rsql_result_source_column(source)->type.tag == RSQL_TYPE_TEXT) return 1u;
    return base == RSQL_SCALAR_CONCAT &&
        !(operation & (RSQL_PROJECTION_LITERAL_LEFT |
                       RSQL_PROJECTION_LITERAL_RIGHT)) &&
        rsql_result_source_column(
            g_rsql_cursor.update_columns[result])->type.tag == RSQL_TYPE_TEXT;
}

static rsql_u16 result_scalar_declared_length(rsql_u8 result) {
    const RsqlColumnInfo* column;
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u16 left;
    rsql_u16 right;
    rsql_u16 start;
    rsql_u16 count;
    if (base == RSQL_SCALAR_STRING) return RSQL_SCALAR_LITERAL_LENGTH(result);
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        left = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        column = rsql_result_source_column(g_rsql_cursor.projection[result]);
        left = column->type.parameter;
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        start = result_u16(g_rsql_cursor.aggregate_counts[result].bytes);
        count = result_u16(&g_rsql_cursor.aggregate_counts[result].bytes[2]);
        if (start > left) return 0u;
        left = (rsql_u16)(left - (start - 1u));
        if (count != 0xFFFFu && left > count) left = count;
        return left;
    }
    if (base != RSQL_SCALAR_CONCAT) return left;
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        right = rsql_result_source_column(
            g_rsql_cursor.projection[result])->type.parameter;
    } else if (operation & RSQL_PROJECTION_LITERAL_RIGHT) {
        right = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        right = rsql_result_source_column(
            g_rsql_cursor.update_columns[result])->type.parameter;
    }
    return (rsql_u16)(left + right);
}

static rsql_u8 result_scalar_nullable(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    if (base == RSQL_SCALAR_STRING) return 0u;
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        return result_source_nullable(g_rsql_cursor.projection[result]);
    }
    if (operation & RSQL_PROJECTION_LITERAL_RIGHT ||
        base != RSQL_SCALAR_CONCAT) {
        return result_source_nullable(g_rsql_cursor.projection[result]);
    }
    return result_source_nullable(g_rsql_cursor.projection[result]) ||
        result_source_nullable(g_rsql_cursor.update_columns[result]);
}

rsql_u8 rsql_query_prepare_result_table_phase_c(void) {
    RsqlColumnDefinition* columns =
        (RsqlColumnDefinition*)g_rsql_execution.row;
    char* name = (char*)&columns[RSQL_TABLE_COLUMNS_MAX];
    const RsqlColumnInfo* source_column;
    RsqlTypeSpec* type;
    rsql_u8 operation;
    rsql_u8 source;
    rsql_u8 result;
    rsql_u8 base;
    rsql_u16 row_width = (rsql_u16)
        ((g_rsql_cursor.result_column_count + 7u) >> 3u);
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        name[0] = 'C';
        name[1] = (char)('1' + result);
        name[2] = '\0';
        columns[result].name = name;
        name += 3;
        type = &columns[result].type;
        memset(type, 0, sizeof(*type));
        operation = g_rsql_cursor.projection_aggregate[result];
        if (RSQL_PROJECTION_IS_SCALAR(operation)) {
            base = operation & RSQL_PROJECTION_OP_MASK;
            if (base == RSQL_SCALAR_LENGTH) {
                type->tag = result_scalar_variable(result)
                    ? RSQL_TYPE_I32 : RSQL_TYPE_I16;
            } else if (result_scalar_variable(result)) {
                type->tag = RSQL_TYPE_TEXT;
            } else {
                type->tag = RSQL_TYPE_CHAR;
                type->parameter = result_scalar_declared_length(result);
                if (type->parameter == 0u) type->parameter = 1u;
            }
            if (result_scalar_nullable(result)) {
                type->flags = RSQL_TYPE_FLAG_NULLABLE;
            }
            goto add_result_width;
        }
        if (operation == RSQL_AGG_COUNT_STAR || operation == RSQL_AGG_COUNT) {
            type->tag = RSQL_TYPE_I64;
            goto add_result_width;
        }
        source = g_rsql_cursor.projection[result];
        source_column = rsql_result_source_column(source);
        if (operation != RSQL_AGG_NONE) {
            type->tag = (source_column->type.tag == RSQL_TYPE_FLOAT5 ||
                         source_column->type.tag == RSQL_TYPE_FIXED8_8)
                ? source_column->type.tag : RSQL_TYPE_I64;
            type->flags = RSQL_TYPE_FLAG_NULLABLE;
        } else {
            *type = source_column->type;
            if (result_source_nullable(source)) {
                type->flags |= RSQL_TYPE_FLAG_NULLABLE;
            }
        }
add_result_width:
        if (type->tag == RSQL_TYPE_BOOLEAN || type->tag == RSQL_TYPE_I8 ||
            type->tag == RSQL_TYPE_ENUM8) row_width += 1u;
        else if (type->tag == RSQL_TYPE_I16 ||
                 type->tag == RSQL_TYPE_FIXED8_8 ||
                 type->tag == RSQL_TYPE_ENUM16) row_width += 2u;
        else if (type->tag == RSQL_TYPE_I32 || type->tag == RSQL_TYPE_TEXT ||
                 type->tag == RSQL_TYPE_BLOB) row_width += 4u;
        else if (type->tag == RSQL_TYPE_I64) row_width += 8u;
        else if (type->tag == RSQL_TYPE_FLOAT5) row_width += 5u;
        else if (type->tag == RSQL_TYPE_CHAR) row_width += type->parameter;
        else return RSQL_ERR_TYPE_MISMATCH;
    }
    g_rsql_execution.column_count = g_rsql_cursor.result_column_count;
    g_rsql_statement.error_offset = row_width;
    return RSQL_OK;
}

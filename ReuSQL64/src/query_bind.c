#include <string.h>

#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_enum.h"
#include "rsql_float.h"
#include "rsql_page.h"
#include "rsql_query.h"

/* The cc65 software stack makes the two-part streamed concatenation loop much
 * larger than its data.  A compact ca65 helper owns this non-reentrant query
 * workspace; payload bytes remain in the REU and are still read by blob.c. */
extern RsqlValueReadRequest* g_scalar_concat_request;
extern const rsql_u8* g_scalar_concat_left;
extern const rsql_u8* g_scalar_concat_right;
extern rsql_u16 g_scalar_concat_left_length;
extern rsql_u16 g_scalar_concat_right_length;
extern rsql_u8 g_scalar_concat_text_mask;
extern rsql_u8 rsql_scalar_variable_concat(void);

static rsql_u8 folded(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 null_mask(rsql_u8 column) {
    switch (column) {
        case 0u: return 0x01u;
        case 1u: return 0x02u;
        case 2u: return 0x04u;
        case 3u: return 0x08u;
        case 4u: return 0x10u;
        case 5u: return 0x20u;
        case 6u: return 0x40u;
        case 7u: return 0x80u;
    }
    return 0u;
}

static rsql_u8 same_name(const char* left, const char* right) {
    while (*left && *right) {
        if (folded(*left++) != folded(*right++)) return 0u;
    }
    return *left == '\0' && *right == '\0';
}

static rsql_u8 predicate_type_ok(rsql_u8 op, const RsqlColumnInfo* column,
                                 const RsqlParsedValue* value) {
    if (op == RSQL_PRED_LIKE) {
        return (column->type.tag == RSQL_TYPE_CHAR ||
                column->type.tag == RSQL_TYPE_TEXT) &&
               value->kind == RSQL_VALUE_STRING;
    }
    if (value->kind == RSQL_VALUE_NULL) return 1u;
    if (column->type.tag == RSQL_TYPE_BOOLEAN) {
        return value->kind == RSQL_VALUE_BOOLEAN;
    }
    if (column->type.tag == RSQL_TYPE_CHAR) {
        return value->kind == RSQL_VALUE_STRING &&
               value->length <= column->type.parameter;
    }
    if (column->type.tag == RSQL_TYPE_TEXT) {
        return value->kind == RSQL_VALUE_STRING;
    }
    if (column->type.tag == RSQL_TYPE_BLOB) {
        return value->kind == RSQL_VALUE_BINARY;
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return value->kind == RSQL_VALUE_FLOAT;
    }
    if (column->type.tag == RSQL_TYPE_I8 ||
        column->type.tag == RSQL_TYPE_I16 ||
        column->type.tag == RSQL_TYPE_I32 ||
        column->type.tag == RSQL_TYPE_I64 ||
        column->type.tag == RSQL_TYPE_FIXED8_8 ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return value->kind == RSQL_VALUE_INTEGER;
    }
    return 0u;
}

static rsql_u8 resolve_column(const char* name, rsql_u8 column_count,
                              rsql_u8* source_out) {
    const char* dot = strchr(name, '.');
    const char* qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* column_name = name;
    rsql_u8 source;
    rsql_u8 index;
    if (dot) {
        for (index = 0u; &name[index] < dot; ++index) {
            if (!qualifier[index] ||
                folded(name[index]) != folded(qualifier[index])) {
                return RSQL_ERR_NOT_FOUND;
            }
        }
        if (qualifier[index]) return RSQL_ERR_NOT_FOUND;
        column_name = dot + 1;
    }
    for (source = 0u; source < column_count; ++source) {
        if (same_name(column_name, g_rsql_cursor.columns[source].name)) {
            *source_out = source;
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 aggregate_numeric(const RsqlColumnInfo* column) {
    return column->type.tag == RSQL_TYPE_I8 ||
           column->type.tag == RSQL_TYPE_I16 ||
           column->type.tag == RSQL_TYPE_I32 ||
           column->type.tag == RSQL_TYPE_I64 ||
           column->type.tag == RSQL_TYPE_FIXED8_8 ||
           column->type.tag == RSQL_TYPE_FLOAT5;
}

static rsql_u8 grouped_source(rsql_u8 source) {
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        if (g_rsql_cursor.group_columns[index] == source) return 1u;
    }
    return 0u;
}

static rsql_u8 bind_source_table(RsqlTableInfo* table) {
    rsql_u8 source;
    rsql_u8 rc;
    rc = rsql_table_find(g_rsql_statement.table_name, table);
    if (rc != RSQL_OK) return rc;
    memset(&g_rsql_cursor, 0, sizeof(g_rsql_cursor));
    g_rsql_cursor.table_page = table->table_page;
    g_rsql_cursor.row_width = table->row_width;
    g_rsql_cursor.source_column_count = table->column_count;
    for (source = 0u; source < table->column_count; ++source) {
        rc = rsql_column_info(table->table_page, source,
                              &g_rsql_cursor.columns[source]);
        if (rc != RSQL_OK) return rc;
    }
    /* Later query overlays cannot call back into this metadata overlay. Keep
       the variable-value root with every bound source so predicate, shaping,
       and grouping phases can stream values without reopening the catalog. */
    rc = rsql_catalog_blob_directory(&g_rsql_cursor.blob_directory);
    if (rc != RSQL_OK) return rc;
    RSQL_VARIABLE_PREDICATE_MASK = 0u;
    RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
    return RSQL_OK;
}

static rsql_u8 bind_where(rsql_u8 column_count) {
    rsql_u8 source;
    rsql_u8 index;
    rsql_u8 rc;
    if (!g_rsql_statement.where_present) return RSQL_OK;
    g_rsql_cursor.predicate_count = g_rsql_statement.predicate_count;
    g_rsql_cursor.bool_program_count = g_rsql_statement.bool_program_count;
    memcpy(g_rsql_cursor.bool_program, g_rsql_statement.bool_program,
           g_rsql_statement.bool_program_count);
    for (index = 0u; index < g_rsql_statement.predicate_count; ++index) {
        rc = resolve_column(g_rsql_statement.predicates[index].column,
                            column_count, &source);
        if (rc != RSQL_OK) return rc;
        rc = rsql_query_resolve_enum_value(
            &g_rsql_cursor.columns[source],
            &g_rsql_statement.predicates[index].value);
        if (rc != RSQL_OK) return rc;
        rc = rsql_query_resolve_float_value(
            &g_rsql_cursor.columns[source],
            &g_rsql_statement.predicates[index].value);
        if (rc != RSQL_OK) return rc;
        if (!predicate_type_ok(g_rsql_statement.predicates[index].op,
                &g_rsql_cursor.columns[source],
                &g_rsql_statement.predicates[index].value)) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.predicates[index].column = source;
        g_rsql_cursor.predicates[index].op =
            g_rsql_statement.predicates[index].op;
        memcpy(&g_rsql_cursor.predicates[index].value,
               &g_rsql_statement.predicates[index].value,
               sizeof(g_rsql_cursor.predicates[index].value));
        if ((g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_TEXT ||
             g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_BLOB) &&
            g_rsql_statement.predicates[index].op != RSQL_PRED_IS_NULL &&
            g_rsql_statement.predicates[index].op != RSQL_PRED_IS_NOT_NULL) {
            /* String/binary literals do not use ParsedValue.integer.  Cache
             * the physical variable-column access here so slot 6 does not
             * need source-schema dispatch while streaming each candidate. */
            g_rsql_cursor.predicates[index].value.integer.bytes[0] =
                (rsql_u8)g_rsql_cursor.columns[source].offset;
            g_rsql_cursor.predicates[index].value.integer.bytes[1] =
                g_rsql_cursor.columns[source].type.tag;
            g_rsql_cursor.predicates[index].value.integer.bytes[2] = 0u;
            RSQL_VARIABLE_PREDICATE_MASK |=
                (rsql_u8)(1u << index);
        }
    }
    g_rsql_cursor.where_present = 1u;
    return RSQL_OK;
}

static rsql_u8 bind_join_source(void) {
    RsqlTableInfo inner;
    RsqlTableInfo subquery;
    rsql_u8 source;
    rsql_u8 rc;
    if (g_rsql_statement.using_index &&
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN &&
        (g_rsql_statement.join_type == RSQL_JOIN_NONE ||
         g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE ||
         g_rsql_statement.select_mode != RSQL_SELECT_SCAN)) {
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    rc = rsql_table_find(g_rsql_statement.join_type != RSQL_JOIN_NONE ||
                         g_rsql_statement.nested_exists
        ? g_rsql_statement.join_table_name
        : g_rsql_statement.subquery_table_name, &inner);
    if (rc != RSQL_OK) return rc;
    for (source = 0u; source < inner.column_count; ++source) {
        rc = rsql_column_info(inner.table_page, source,
                              &g_rsql_cursor.join_columns[source]);
        if (rc != RSQL_OK) return rc;
    }
    g_rsql_cursor.join_type = g_rsql_statement.join_type;
    g_rsql_cursor.subquery_kind = g_rsql_statement.subquery_kind;
    g_rsql_cursor.join_table_page = inner.table_page;
    g_rsql_cursor.join_row_width = inner.row_width;
    g_rsql_cursor.join_inner_column_count = inner.column_count;
    if ((g_rsql_statement.join_type != RSQL_JOIN_NONE ||
         g_rsql_statement.nested_exists) &&
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE) {
        rc = rsql_table_find(g_rsql_statement.subquery_table_name, &subquery);
        if (rc != RSQL_OK) return rc;
        g_rsql_cursor.subquery_table_page = subquery.table_page;
        g_rsql_cursor.subquery_row_width = subquery.row_width;
        g_rsql_cursor.subquery_column_count = subquery.column_count;
        for (source = 0u; source < subquery.column_count; ++source) {
            rc = rsql_column_info(subquery.table_page, source,
                                  &g_rsql_execution.columns[source]);
            if (rc != RSQL_OK) return rc;
        }
    }
    if (g_rsql_statement.nested_exists) {
        g_rsql_statement.join_type = RSQL_JOIN_INNER;
        rc = rsql_query_resolve_join_enums();
        g_rsql_statement.join_type = RSQL_JOIN_NONE;
        return rc;
    }
    return rsql_query_resolve_join_enums();
}

rsql_u8 __fastcall__ rsql_query_bind_select(RsqlQueryOpenRequest* request) {
    RsqlTableInfo table;
    rsql_u8 source;
    rsql_u8 result;
    rsql_u8 aggregate;
    rsql_u8 rc;
    rc = bind_source_table(&table);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.mode = g_rsql_statement.select_mode;
    if (g_rsql_statement.join_type != RSQL_JOIN_NONE ||
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE) {
        rc = bind_join_source();
        if (rc != RSQL_OK ||
            g_rsql_statement.join_type != RSQL_JOIN_NONE) return rc;
    }
    g_rsql_cursor.using_index = g_rsql_statement.using_index;
    g_rsql_cursor.group_count = g_rsql_statement.group_count;
    for (result = 0u; result < g_rsql_statement.group_count; ++result) {
        rc = resolve_column(RSQL_AGGREGATE_GROUP_NAME(g_rsql_statement,
                                                      result),
                            table.column_count, &source);
        if (rc != RSQL_OK) return rc;
        if (g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_TEXT ||
            g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_BLOB) {
            /* SELECT does not use the mutation-only update_variable byte.
             * Retain a bounded flag so row/slot-5 continuations compare
             * logical payloads rather than four-byte handle identities. */
            g_rsql_cursor.update_variable = 1u;
        }
        g_rsql_cursor.group_columns[result] = source;
    }
    if (g_rsql_statement.select_all) {
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        g_rsql_cursor.result_column_count = table.column_count;
        for (result = 0u; result < table.column_count; ++result) {
            g_rsql_cursor.projection[result] = result;
        }
    } else {
        g_rsql_cursor.result_column_count = g_rsql_statement.projection_count;
        for (result = 0u; result < g_rsql_statement.projection_count; ++result) {
            aggregate = g_rsql_statement.projection_aggregate[result];
            g_rsql_cursor.projection_aggregate[result] = aggregate;
            if (RSQL_PROJECTION_IS_SCALAR(aggregate)) {
                g_rsql_cursor.projection[result] = 0xFFu;
                continue;
            }
            if (aggregate == RSQL_AGG_COUNT_STAR) {
                g_rsql_cursor.projection[result] = 0xFFu;
                continue;
            }
            rc = resolve_column(g_rsql_statement.projections[result],
                                table.column_count, &source);
            if (rc != RSQL_OK) return rc;
            if ((aggregate == RSQL_AGG_SUM || aggregate == RSQL_AGG_AVG ||
                 aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) &&
                !aggregate_numeric(&g_rsql_cursor.columns[source])) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
                aggregate == RSQL_AGG_NONE && !grouped_source(source)) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
            g_rsql_cursor.projection[result] = source;
        }
    }
    if (g_rsql_statement.subquery_kind == RSQL_SUBQUERY_NONE) {
        rc = bind_where(table.column_count);
        if (rc != RSQL_OK) return rc;
    }
    if (RSQL_VARIABLE_PREDICATE_MASK != 0u &&
        ((g_rsql_cursor.mode != RSQL_SELECT_SCAN &&
          g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE) ||
         g_rsql_statement.join_type != RSQL_JOIN_NONE ||
         g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE ||
         ((g_rsql_statement.distinct |
           g_rsql_statement.order_count) &&
          g_rsql_cursor.mode != RSQL_SELECT_SCAN))) {
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    request->column_count = g_rsql_cursor.result_column_count;
    return RSQL_OK;
}

rsql_u8 rsql_query_bind_delete(void) {
    RsqlTableInfo table;
    rsql_u8 rc = bind_source_table(&table);
    if (rc != RSQL_OK) return rc;
    return bind_where(table.column_count);
}

static rsql_u8 update_signed_fits(const RsqlI64* value, rsql_u8 width) {
    rsql_u8 fill = (value->bytes[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = width; index < sizeof(value->bytes); ++index) {
        if (value->bytes[index] != fill) return 0u;
    }
    return 1u;
}

#define UPDATE_VALUE \
    (*(const RsqlParsedValue**)&g_rsql_execution.row[0])
#define UPDATE_COLUMN \
    (*(const RsqlColumnInfo**)&g_rsql_execution.row[2])
#define UPDATE_ASSIGNMENT (g_rsql_execution.row[4])
#define UPDATE_WIDTH      (g_rsql_execution.row[5])
#define UPDATE_BYTE       (g_rsql_execution.row[6])

static rsql_u8 validate_update_assignments(void) {
    for (UPDATE_ASSIGNMENT = 0u;
         UPDATE_ASSIGNMENT < g_rsql_cursor.update_count;
         ++UPDATE_ASSIGNMENT) {
        UPDATE_VALUE = &g_rsql_statement.values[UPDATE_ASSIGNMENT];
        UPDATE_COLUMN = &g_rsql_cursor.columns[
            g_rsql_cursor.update_columns[UPDATE_ASSIGNMENT]];
        if (UPDATE_VALUE->kind == RSQL_VALUE_NULL) {
            if (!(UPDATE_COLUMN->type.flags & RSQL_TYPE_FLAG_NULLABLE)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            continue;
        }
        if (!predicate_type_ok(RSQL_PRED_EQ, UPDATE_COLUMN, UPDATE_VALUE)) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        if (UPDATE_VALUE->kind != RSQL_VALUE_INTEGER) continue;
        if (UPDATE_COLUMN->type.tag == RSQL_TYPE_FIXED8_8 ||
            UPDATE_COLUMN->type.tag == RSQL_TYPE_I8) UPDATE_WIDTH = 1u;
        else if (UPDATE_COLUMN->type.tag == RSQL_TYPE_I16 ||
                 UPDATE_COLUMN->type.tag == RSQL_TYPE_ENUM16) UPDATE_WIDTH = 2u;
        else if (UPDATE_COLUMN->type.tag == RSQL_TYPE_I32) UPDATE_WIDTH = 4u;
        else if (UPDATE_COLUMN->type.tag == RSQL_TYPE_I64) UPDATE_WIDTH = 8u;
        else if (UPDATE_COLUMN->type.tag == RSQL_TYPE_ENUM8) UPDATE_WIDTH = 1u;
        else return RSQL_ERR_UNSUPPORTED_SQL;
        if (UPDATE_COLUMN->type.tag == RSQL_TYPE_ENUM8 ||
            UPDATE_COLUMN->type.tag == RSQL_TYPE_ENUM16) {
            for (UPDATE_BYTE = UPDATE_WIDTH;
                 UPDATE_BYTE < sizeof(UPDATE_VALUE->integer.bytes);
                 ++UPDATE_BYTE) {
                if (UPDATE_VALUE->integer.bytes[UPDATE_BYTE] != 0u) {
                    return RSQL_ERR_TYPE_MISMATCH;
                }
            }
        } else if (!update_signed_fits(&UPDATE_VALUE->integer, UPDATE_WIDTH)) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
    }
    return RSQL_OK;
}

rsql_u8 rsql_query_bind_update(void) {
    RsqlTableInfo table;
    rsql_u8 source;
    rsql_u8 prior;
    rsql_u8 index;
    rsql_u8 rc = bind_source_table(&table);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.update_count = g_rsql_statement.column_count;
    for (index = 0u; index < g_rsql_statement.column_count; ++index) {
        rc = resolve_column(g_rsql_statement.columns[index].name,
                            table.column_count, &source);
        if (rc != RSQL_OK) return rc;
        for (prior = 0u; prior < index; ++prior) {
            if (g_rsql_cursor.update_columns[prior] == source) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
        }
        g_rsql_cursor.update_columns[index] = source;
        if (g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_TEXT ||
            g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_BLOB) {
            g_rsql_cursor.update_variable = 1u;
        }
        rc = rsql_query_resolve_enum_value(
            &g_rsql_cursor.columns[source],
            &g_rsql_statement.values[index]);
        if (rc != RSQL_OK) return rc;
        rc = rsql_query_resolve_float_value(
            &g_rsql_cursor.columns[source],
            &g_rsql_statement.values[index]);
        if (rc != RSQL_OK) return rc;
    }
    rc = bind_where(table.column_count);
    return rc == RSQL_OK ? validate_update_assignments() : rc;
}

rsql_u8 rsql_query_materialize_insert(void) {
    RsqlBlobHandle handle;
    const RsqlParsedValue* value;
    const RsqlColumnInfo* column;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_execution.column_count; ++index) {
        value = &g_rsql_statement.values[index];
        column = &g_rsql_execution.columns[index];
        if (value->kind == RSQL_VALUE_NULL) continue;
        if (column->type.tag != RSQL_TYPE_TEXT &&
            column->type.tag != RSQL_TYPE_BLOB) continue;
        rc = rsql_query_create_blob_value(column, value, &handle);
        if (rc != RSQL_OK) return rc;
        memcpy(&g_rsql_execution.row[column->offset], handle.bytes, 4u);
    }
    return RSQL_OK;
}

extern const RsqlColumnInfo* __fastcall__
rsql_query_scalar_source_column(rsql_u8 source);
extern const rsql_u8* __fastcall__
rsql_query_scalar_source_row(rsql_u8 source);
#define scalar_source_column rsql_query_scalar_source_column
#define scalar_source_row rsql_query_scalar_source_row

static rsql_u8 scalar_source_null(rsql_u8 source) {
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    return (scalar_source_row(source)[0] &
        null_mask(source & RSQL_SOURCE_COLUMN_MASK)) != 0u;
}

static rsql_u8 scalar_source_info(rsql_u8 source, RsqlBlobHandle* handle,
                                  RsqlBlobInfo* info) {
    const RsqlColumnInfo* column = scalar_source_column(source);
    rsql_u8 rc;
    if (column->type.tag != RSQL_TYPE_TEXT) return RSQL_ERR_TYPE_MISMATCH;
    memcpy(handle->bytes, &scalar_source_row(source)[column->offset],
           sizeof(handle->bytes));
    rc = rsql_blob_info(handle, info);
    if (rc != RSQL_OK) return rc;
    if (info->kind != RSQL_TYPE_TEXT || info->length > 65535ul) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 scalar_concat_resolve(void) {
    static RsqlBlobHandle handle;
    static RsqlBlobInfo info;
    static const rsql_u8* data;
    static rsql_u8 right;
    static rsql_u8 rc;
    if (g_scalar_concat_text_mask & 0x80u) return RSQL_OK;
    for (right = 0u; right != 2u; ++right) {
        if (!(g_scalar_concat_text_mask & (right ? 2u : 1u))) continue;
        data = right ? g_scalar_concat_right : g_scalar_concat_left;
        memcpy(handle.bytes, data, sizeof(handle.bytes));
        rc = rsql_blob_info(&handle, &info);
        if (rc != RSQL_OK) return rc;
        if (info.kind != RSQL_TYPE_TEXT || info.length > 65535ul) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        if (right) g_scalar_concat_right_length = (rsql_u16)info.length;
        else g_scalar_concat_left_length = (rsql_u16)info.length;
    }
    if (g_scalar_concat_left_length >
        (rsql_u16)(65535u - g_scalar_concat_right_length)) {
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    return RSQL_OK;
}

static rsql_u16 scalar_text_bound(rsql_u8 result, rsql_u8 high) {
    const rsql_u8* bytes = &g_rsql_cursor.aggregate_counts[result].bytes[
        high ? 2u : 0u];
    return (rsql_u16)bytes[0] | ((rsql_u16)bytes[1] << 8u);
}

static rsql_u16 scalar_text_substr_length(rsql_u8 result,
                                          rsql_u16 source_length) {
    rsql_u16 start = scalar_text_bound(result, 0u);
    rsql_u16 count = scalar_text_bound(result, 1u);
    if (start > source_length) return 0u;
    source_length = (rsql_u16)(source_length - (start - 1u));
    if (count != 0xFFFFu && source_length > count) source_length = count;
    return source_length;
}

static rsql_u8 scalar_variable_column(RsqlCursorColumnRequest* request) {
    RsqlBlobHandle handle;
    RsqlBlobInfo info;
    rsql_u8 base = g_rsql_cursor.projection_aggregate[request->column] &
        RSQL_PROJECTION_OP_MASK;
    rsql_u16 length;
    rsql_u8 rc;
    memset(&request->value, 0, sizeof(request->value));
    if (base == RSQL_SCALAR_CONCAT) {
        request->value.type.tag = RSQL_TYPE_TEXT;
        rc = scalar_concat_resolve();
        if (rc != RSQL_OK) return rc;
        request->value.is_null =
            (g_scalar_concat_text_mask & 0x80u) != 0u;
        if (request->value.is_null) return RSQL_OK;
        request->value.length = (rsql_u16)(g_scalar_concat_left_length +
                                           g_scalar_concat_right_length);
        return RSQL_OK;
    }
    request->value.is_null = scalar_source_null(
        g_rsql_cursor.projection[request->column]);
    if (base == RSQL_SCALAR_LENGTH) {
        request->value.type.tag = RSQL_TYPE_I32;
        request->value.length = 4u;
    } else request->value.type.tag = RSQL_TYPE_TEXT;
    if (request->value.is_null) return RSQL_OK;
    rc = scalar_source_info(g_rsql_cursor.projection[request->column],
                            &handle, &info);
    if (rc != RSQL_OK) return rc;
    length = (rsql_u16)info.length;
    if (base == RSQL_SCALAR_LENGTH) {
        request->value.bytes[0] = (rsql_u8)length;
        request->value.bytes[1] = (rsql_u8)(length >> 8u);
    } else request->value.length =
        scalar_text_substr_length(request->column, length);
    return RSQL_OK;
}

static rsql_u8 scalar_variable_read(RsqlValueReadRequest* request) {
    RsqlBlobHandle handle;
    RsqlBlobInfo info;
    rsql_u8 number[4];
    rsql_u8 base = g_rsql_cursor.projection_aggregate[request->column] &
        RSQL_PROJECTION_OP_MASK;
    rsql_u16 length;
    rsql_u16 available;
    rsql_u16 offset;
    rsql_u8 rc;
    request->bytes_read = 0u;
    if (base == RSQL_SCALAR_CONCAT) {
        rc = scalar_concat_resolve();
        if (rc != RSQL_OK) return rc;
        if (g_scalar_concat_text_mask & 0x80u) return RSQL_OK;
        g_scalar_concat_request = request;
        return rsql_scalar_variable_concat();
    }
    if (scalar_source_null(g_rsql_cursor.projection[request->column])) {
        return RSQL_OK;
    }
    rc = scalar_source_info(g_rsql_cursor.projection[request->column],
                            &handle, &info);
    if (rc != RSQL_OK) return rc;
    length = (rsql_u16)info.length;
    if (base == RSQL_SCALAR_LENGTH) {
        number[0] = (rsql_u8)length;
        number[1] = (rsql_u8)(length >> 8u);
        number[2] = 0u;
        number[3] = 0u;
        if (request->offset >= 4u) return RSQL_OK;
        available = (rsql_u16)(4u - request->offset);
        if (available > request->capacity) available = request->capacity;
        memcpy(request->destination, &number[request->offset], available);
        request->bytes_read = available;
        return RSQL_OK;
    }
    length = scalar_text_substr_length(request->column, length);
    if (request->offset >= length) return RSQL_OK;
    available = (rsql_u16)(length - request->offset);
    if (available > request->capacity) available = request->capacity;
    offset = (rsql_u16)(scalar_text_bound(request->column, 0u) - 1u +
                        request->offset);
    return rsql_blob_read(&handle, offset, request->destination, available,
                          &request->bytes_read);
}

rsql_u8 __fastcall__ rsql_query_variable_column_phase(
    RsqlCursorColumnRequest* request) {
    RsqlBlobHandle handle;
    RsqlBlobInfo info;
    rsql_u8 rc;
    if (request && request->cursor == 1u && g_rsql_cursor.active &&
        g_rsql_cursor.positioned &&
        request->column < g_rsql_cursor.result_column_count &&
        RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return scalar_variable_column(request);
    }
    if (!request || request->value.is_null ||
        (request->value.type.tag != RSQL_TYPE_TEXT &&
         request->value.type.tag != RSQL_TYPE_BLOB)) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    memcpy(handle.bytes, request->value.bytes, sizeof(handle.bytes));
    rc = rsql_blob_info(&handle, &info);
    if (rc != RSQL_OK) return rc;
    if (info.kind != request->value.type.tag || info.length > 65535ul) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    request->value.length = (rsql_u16)info.length;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_variable_read_phase(
    RsqlValueReadRequest* request) {
    RsqlBlobHandle handle;
    const RsqlColumnInfo* column;
    const rsql_u8* row;
    rsql_u8 source;
    if (request && request->destination && request->cursor == 1u &&
        g_rsql_cursor.active && g_rsql_cursor.positioned &&
        request->column < g_rsql_cursor.result_column_count &&
        RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return scalar_variable_read(request);
    }
    if (!request || !request->destination || request->cursor != 1u ||
        !g_rsql_cursor.active || !g_rsql_cursor.positioned ||
        request->column >= g_rsql_cursor.result_column_count ||
        g_rsql_cursor.projection_aggregate[request->column] != RSQL_AGG_NONE) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->bytes_read = 0u;
    source = g_rsql_cursor.projection[request->column];
    if (source & RSQL_SOURCE_SUBQUERY) {
        column = &g_rsql_execution.columns[
            source & RSQL_SOURCE_COLUMN_MASK];
        row = g_rsql_execution.row;
    } else if (source & RSQL_SOURCE_INNER) {
        column = &g_rsql_cursor.join_columns[
            source & RSQL_SOURCE_COLUMN_MASK];
        row = g_rsql_cursor.scan_row;
    } else {
        column = &g_rsql_cursor.columns[
            source & RSQL_SOURCE_COLUMN_MASK];
        row = g_rsql_cursor.row;
    }
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return RSQL_OK;
    }
    if (row[0] & null_mask(source & RSQL_SOURCE_COLUMN_MASK)) return RSQL_OK;
    memcpy(handle.bytes, &row[column->offset], sizeof(handle.bytes));
    return rsql_blob_read(&handle, request->offset, request->destination,
                          request->capacity, &request->bytes_read);
}

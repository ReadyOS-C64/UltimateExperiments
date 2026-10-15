#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define SQL_FALSE   0u
#define SQL_TRUE    1u
#define SQL_UNKNOWN 2u

#define SHAPE_BLOB_DIR_NEXT       6u
#define SHAPE_BLOB_DIR_ENTRIES    8u
#define SHAPE_BLOB_ENTRY_BYTES   20u
#define SHAPE_BLOB_ENTRY_COUNT   12u
#define SHAPE_BLOB_ENTRY_KIND     1u
#define SHAPE_BLOB_ENTRY_HANDLE   2u
#define SHAPE_BLOB_ENTRY_FIRST    6u
#define SHAPE_BLOB_ENTRY_LENGTH   8u


/* Initialized file-scope continuation state avoids cc65 emitting deep local
 * temporaries before the exported function entry label. */
static RsqlRowId g_join_candidate = { 0xFFFFu, 0xFFu };
static rsql_u8 g_join_next_rc = 0xFFu;
static rsql_u8 g_subquery_rc;
#ifdef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 g_nested_eval;
#else
rsql_u8 g_nested_eval;
rsql_u8 g_nested_saved_kind;
rsql_u8 g_nested_saved_projection;
rsql_u8 g_nested_saved_compare;
static RsqlRowId g_join_shape_best_outer;
static RsqlRowId g_join_shape_best_inner;
static RsqlRowId g_join_shape_target_outer;
static RsqlRowId g_join_shape_target_inner;
static rsql_u8 g_join_shape_best_inner_null;
static rsql_u8 g_join_shape_target_inner_null;
static rsql_u8 g_join_shape_last_inner_null;
static rsql_u8 g_join_shape_have_best;
static rsql_u8 g_join_shape_duplicate;
rsql_u8 g_join_shape_rc;
rsql_u8 g_shape_scalar_result;
rsql_u8* g_shape_scalar_buffer;
#endif

#ifdef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 subquery_truth(rsql_u8 predicate_column);
#else
rsql_u8 subquery_truth(rsql_u8 predicate_column);
#endif
#ifndef RSQL_JOIN_AGGREGATE_CORE
extern rsql_u8 __fastcall__
rsql_nested_subquery_truth(RsqlParsedColumn* predicate);
#endif

#ifndef RSQL_JOIN_AGGREGATE_CORE
extern rsql_i8 __fastcall__ rsql_shape_compare_scalar(rsql_u8 result);
#endif

#ifndef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 folded_name(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 same_name(const char* left, const char* right) {
    while (*left && *right) {
        if (folded_name(*left++) != folded_name(*right++)) return 0u;
    }
    return *left == 0 && *right == 0;
}

static const RsqlColumnInfo* source_column(rsql_u8 source);

static rsql_u8 same_name_part(const char* part, rsql_u8 length,
                              const char* value) {
    rsql_u8 index;
    if ((rsql_u8)strlen(value) != length) return 0u;
    for (index = 0u; index < length; ++index) {
        if (folded_name(part[index]) != folded_name(value[index])) return 0u;
    }
    return 1u;
}

static const RsqlColumnInfo* bound_source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static rsql_u8 resolve_join_column(const char* name_value,
                                   rsql_u8* source_out) {
    const char* dot = strchr(name_value, '.');
    const char* column_name = name_value;
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    rsql_u8 qualifier_length;
    rsql_u8 source;
    rsql_u8 outer_found = 0u;
    rsql_u8 inner_found = 0u;
    rsql_u8 outer_source = 0u;
    rsql_u8 inner_source = 0u;
    if (dot) {
        qualifier_length = (rsql_u8)(dot - name_value);
        column_name = dot + 1;
        if (same_name_part(name_value, qualifier_length, outer_qualifier)) {
            for (source = 0u; source < g_rsql_cursor.source_column_count;
                 ++source) {
                if (same_name(column_name, g_rsql_cursor.columns[source].name)) {
                    *source_out = source;
                    return RSQL_OK;
                }
            }
            return RSQL_ERR_NOT_FOUND;
        }
        if (same_name_part(name_value, qualifier_length, inner_qualifier)) {
            for (source = 0u; source < g_rsql_cursor.join_inner_column_count;
                 ++source) {
                if (same_name(column_name,
                              g_rsql_cursor.join_columns[source].name)) {
                    *source_out = (rsql_u8)(RSQL_SOURCE_INNER | source);
                    return RSQL_OK;
                }
            }
        }
        return RSQL_ERR_NOT_FOUND;
    }
    for (source = 0u; source < g_rsql_cursor.source_column_count; ++source) {
        if (same_name(column_name, g_rsql_cursor.columns[source].name)) {
            outer_found = 1u;
            outer_source = source;
        }
    }
    for (source = 0u; source < g_rsql_cursor.join_inner_column_count;
         ++source) {
        if (same_name(column_name, g_rsql_cursor.join_columns[source].name)) {
            inner_found = 1u;
            inner_source = source;
        }
    }
    if (outer_found && inner_found) return RSQL_ERR_TYPE_MISMATCH;
    if (outer_found) {
        *source_out = outer_source;
        return RSQL_OK;
    }
    if (inner_found) {
        *source_out = (rsql_u8)(RSQL_SOURCE_INNER | inner_source);
        return RSQL_OK;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 signed_integer_type(rsql_u8 tag) {
    return tag == RSQL_TYPE_I8 || tag == RSQL_TYPE_I16 ||
           tag == RSQL_TYPE_I32 || tag == RSQL_TYPE_I64;
}

static rsql_u8 aggregate_numeric(const RsqlColumnInfo* column) {
    return signed_integer_type(column->type.tag) ||
           column->type.tag == RSQL_TYPE_FIXED8_8 ||
           column->type.tag == RSQL_TYPE_FLOAT5;
}

static rsql_u8 grouped_join_source(rsql_u8 source) {
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        if (g_rsql_cursor.group_columns[index] == source) return 1u;
    }
    return 0u;
}

static rsql_u8 reference_types_ok(const RsqlColumnInfo* left,
                                  const RsqlColumnInfo* right) {
    if (left->type.tag == RSQL_TYPE_TEXT || left->type.tag == RSQL_TYPE_BLOB ||
        right->type.tag == RSQL_TYPE_TEXT || right->type.tag == RSQL_TYPE_BLOB) {
        return 0u;
    }
    if (signed_integer_type(left->type.tag) &&
        signed_integer_type(right->type.tag)) return 1u;
    if (left->type.tag != right->type.tag) return 0u;
    if ((left->type.tag == RSQL_TYPE_ENUM8 ||
         left->type.tag == RSQL_TYPE_ENUM16) &&
        left->type.auxiliary != right->type.auxiliary) return 0u;
    return 1u;
}

static rsql_u8 literal_type_ok(rsql_u8 op, const RsqlColumnInfo* column,
                               const RsqlParsedValue* value) {
    rsql_u8 index;
    rsql_u8 fill;
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
    if (signed_integer_type(column->type.tag) ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return value->kind == RSQL_VALUE_INTEGER;
    }
    if (column->type.tag != RSQL_TYPE_FIXED8_8 ||
        value->kind != RSQL_VALUE_INTEGER) return 0u;
    fill = (value->integer.bytes[0] & 0x80u) ? 0xFFu : 0u;
    for (index = 1u; index < sizeof(value->integer.bytes); ++index) {
        if (value->integer.bytes[index] != fill) return 0u;
    }
    return 1u;
}

rsql_u8 rsql_query_bind_join_phase(void) {
    const RsqlColumnInfo* left;
    const RsqlColumnInfo* right;
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    rsql_u8 source;
    rsql_u8 reference;
    rsql_u8 aggregate;
    rsql_u8 result;
    rsql_u8 index;
    rsql_u8 rc;
    if (same_name(outer_qualifier, inner_qualifier)) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    g_rsql_cursor.group_count = g_rsql_statement.group_count;
    for (index = 0u; index < g_rsql_statement.group_count; ++index) {
        rc = resolve_join_column(
            RSQL_AGGREGATE_GROUP_NAME(g_rsql_statement, index), &source);
        if (rc != RSQL_OK) return rc;
        left = bound_source_column(source);
        if (left->type.tag == RSQL_TYPE_TEXT ||
            left->type.tag == RSQL_TYPE_BLOB) {
            g_rsql_cursor.update_variable = 1u;
        }
        g_rsql_cursor.group_columns[index] = source;
    }
    if (g_rsql_statement.select_all) {
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        if ((rsql_u8)(g_rsql_cursor.source_column_count +
            g_rsql_cursor.join_inner_column_count) >
            RSQL_TABLE_COLUMNS_MAX) return RSQL_ERR_UNSUPPORTED_SQL;
        g_rsql_cursor.result_column_count = (rsql_u8)
            (g_rsql_cursor.source_column_count +
             g_rsql_cursor.join_inner_column_count);
        for (result = 0u; result < g_rsql_cursor.source_column_count;
             ++result) g_rsql_cursor.projection[result] = result;
        for (source = 0u;
             source < g_rsql_cursor.join_inner_column_count; ++source) {
            g_rsql_cursor.projection[result++] =
                (rsql_u8)(RSQL_SOURCE_INNER | source);
        }
    } else {
        g_rsql_cursor.result_column_count =
            g_rsql_statement.projection_count;
        for (result = 0u; result < g_rsql_statement.projection_count;
             ++result) {
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
            rc = resolve_join_column(g_rsql_statement.projections[result],
                                     &source);
            if (rc != RSQL_OK) return rc;
            left = bound_source_column(source);
            if ((aggregate == RSQL_AGG_SUM || aggregate == RSQL_AGG_AVG ||
                 aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) &&
                !aggregate_numeric(left)) return RSQL_ERR_TYPE_MISMATCH;
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
                aggregate == RSQL_AGG_NONE &&
                !grouped_join_source(source)) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
            g_rsql_cursor.projection[result] = source;
        }
    }
    g_rsql_cursor.predicate_count = g_rsql_statement.predicate_count;
    g_rsql_cursor.bool_program_count = g_rsql_statement.bool_program_count;
    g_rsql_cursor.join_predicate_count =
        g_rsql_statement.join_predicate_count;
    g_rsql_cursor.join_bool_program_count =
        g_rsql_statement.join_bool_program_count;
    memcpy(g_rsql_cursor.bool_program, g_rsql_statement.bool_program,
           g_rsql_statement.bool_program_count);
    for (index = 0u; index < g_rsql_statement.predicate_count; ++index) {
        if (g_rsql_statement.predicates[index].op == RSQL_PRED_SUBQUERY) {
            if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_EXISTS) {
                source = 0u;
            } else {
                rc = resolve_join_column(
                    g_rsql_statement.predicates[index].column, &source);
                if (rc != RSQL_OK) return rc;
                if (!reference_types_ok(bound_source_column(source),
                        source_column(g_rsql_cursor.subquery_projection))) {
                    return RSQL_ERR_TYPE_MISMATCH;
                }
            }
            g_rsql_cursor.predicates[index].column = source;
            g_rsql_cursor.predicates[index].op = RSQL_PRED_SUBQUERY;
            continue;
        }
        rc = resolve_join_column(g_rsql_statement.predicates[index].column,
                                 &source);
        if (rc != RSQL_OK) return rc;
        left = bound_source_column(source);
        if (g_rsql_statement.predicates[index].value.kind ==
                RSQL_VALUE_ENUM &&
            resolve_join_column(
                g_rsql_statement.predicates[index].value.string,
                &reference) == RSQL_OK) {
            if (g_rsql_statement.predicates[index].op == RSQL_PRED_LIKE) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            right = bound_source_column(reference);
            if (!reference_types_ok(left, right)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            g_rsql_statement.predicates[index].value.kind =
                RSQL_VALUE_REFERENCE;
            g_rsql_statement.predicates[index].value.integer.bytes[0] =
                reference;
        } else {
            if (g_rsql_statement.predicates[index].value.kind ==
                RSQL_VALUE_ENUM) return RSQL_ERR_TYPE_MISMATCH;
            rc = rsql_query_resolve_float_value(
                left, &g_rsql_statement.predicates[index].value);
            if (rc != RSQL_OK) return rc;
            if (!literal_type_ok(g_rsql_statement.predicates[index].op,
                    left, &g_rsql_statement.predicates[index].value)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        }
        g_rsql_cursor.predicates[index].column = source;
        g_rsql_cursor.predicates[index].op =
            g_rsql_statement.predicates[index].op;
        memcpy(&g_rsql_cursor.predicates[index].value,
               &g_rsql_statement.predicates[index].value,
               sizeof(g_rsql_cursor.predicates[index].value));
        if ((left->type.tag == RSQL_TYPE_TEXT ||
             left->type.tag == RSQL_TYPE_BLOB) &&
            g_rsql_cursor.predicates[index].op != RSQL_PRED_IS_NULL &&
            g_rsql_cursor.predicates[index].op != RSQL_PRED_IS_NOT_NULL) {
            g_rsql_cursor.predicates[index].value.integer.bytes[0] =
                (rsql_u8)left->offset;
            g_rsql_cursor.predicates[index].value.integer.bytes[1] =
                left->type.tag;
            g_rsql_cursor.predicates[index].value.integer.bytes[2] =
                (source & RSQL_SOURCE_INNER) ? 1u : 0u;
            RSQL_VARIABLE_PREDICATE_MASK |= (rsql_u8)(1u << index);
        }
    }
    if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
        if (g_rsql_cursor.mode != RSQL_SELECT_SCAN ||
            g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        RSQL_VARIABLE_PREDICATE_SOURCE = 2u;
    }
    g_rsql_cursor.where_present = g_rsql_statement.where_present;
    return RSQL_OK;
}

static rsql_u8 resolve_source_only(const char* name_value,
                                   const char* qualifier,
                                   const RsqlColumnInfo* columns,
                                   rsql_u8 column_count, rsql_u8 source_flag,
                                   rsql_u8* source_out) {
    const char* dot = strchr(name_value, '.');
    const char* column_name = name_value;
    rsql_u8 qualifier_length;
    rsql_u8 source;
    if (dot) {
        qualifier_length = (rsql_u8)(dot - name_value);
        if (!same_name_part(name_value, qualifier_length, qualifier)) {
            return RSQL_ERR_NOT_FOUND;
        }
        column_name = dot + 1;
    }
    for (source = 0u; source < column_count; ++source) {
        if (same_name(column_name, columns[source].name)) {
            *source_out = (rsql_u8)(source_flag | source);
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 resolve_subquery_column(const char* name_value,
                                       rsql_u8* source_out) {
    const char* dot = strchr(name_value, '.');
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = (g_rsql_statement.nested_exists |
                                   g_rsql_cursor.join_type)
        ? (g_rsql_statement.subquery_table_alias[0]
            ? g_rsql_statement.subquery_table_alias :
              g_rsql_statement.subquery_table_name)
        : (g_rsql_statement.join_table_alias[0]
            ? g_rsql_statement.join_table_alias :
              g_rsql_statement.join_table_name);
    const RsqlColumnInfo* inner_columns =
        (g_rsql_statement.nested_exists | g_rsql_cursor.join_type)
            ? g_rsql_execution.columns : g_rsql_cursor.join_columns;
    rsql_u8 inner_count = (g_rsql_statement.nested_exists |
                           g_rsql_cursor.join_type)
        ? g_rsql_cursor.subquery_column_count
        : g_rsql_cursor.join_inner_column_count;
    rsql_u8 inner_flag = (g_rsql_statement.nested_exists |
                          g_rsql_cursor.join_type)
        ? RSQL_SOURCE_SUBQUERY : RSQL_SOURCE_INNER;
    rsql_u8 rc;
    if (dot) {
        rc = resolve_source_only(name_value, inner_qualifier,
            inner_columns, inner_count, inner_flag, source_out);
        if (rc == RSQL_OK) return rc;
        if (g_rsql_statement.nested_exists | g_rsql_cursor.join_type) {
            return resolve_join_column(name_value, source_out);
        }
        return resolve_source_only(name_value, outer_qualifier,
            g_rsql_cursor.columns, g_rsql_cursor.source_column_count, 0u,
            source_out);
    }
    rc = resolve_source_only(name_value, inner_qualifier,
        inner_columns, inner_count, inner_flag, source_out);
    if (rc == RSQL_OK) return rc;
    if (g_rsql_statement.nested_exists | g_rsql_cursor.join_type) {
        return resolve_join_column(name_value, source_out);
    }
    return resolve_source_only(name_value, outer_qualifier,
        g_rsql_cursor.columns, g_rsql_cursor.source_column_count, 0u,
        source_out);
}

static rsql_u8 resolve_depth_column(const char* name_value, rsql_u8 index,
                                    rsql_u8* source_out) {
    rsql_u8 saved = g_rsql_statement.nested_exists;
    rsql_u8 nested = saved &&
        index >= g_rsql_statement.nested_predicate_start &&
        index < (rsql_u8)(g_rsql_statement.nested_predicate_start +
                          g_rsql_statement.nested_predicate_count);
    rsql_u8 rc;
    g_rsql_statement.nested_exists = nested;
    rc = resolve_subquery_column(name_value, source_out);
    g_rsql_statement.nested_exists = saved;
    return rc;
}

rsql_u8 rsql_query_bind_subquery_phase(void) {
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = g_rsql_statement.nested_exists
        ? (g_rsql_statement.join_table_alias[0]
            ? g_rsql_statement.join_table_alias :
              g_rsql_statement.join_table_name)
        : (g_rsql_statement.subquery_table_alias[0]
            ? g_rsql_statement.subquery_table_alias :
              g_rsql_statement.subquery_table_name);
    const char* join_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    const RsqlColumnInfo* left;
    const RsqlColumnInfo* right;
    RsqlParsedValue* value;
    rsql_u8 source;
    rsql_u8 reference;
    rsql_u8 result;
    rsql_u8 index;
    rsql_u8 op;
    rsql_u8 rc;
    if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE ||
        same_name(outer_qualifier, inner_qualifier) ||
        (g_rsql_cursor.join_type != RSQL_JOIN_NONE &&
         same_name(join_qualifier, inner_qualifier))) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
        g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE &&
        g_rsql_statement.select_all) {
        g_rsql_cursor.result_column_count =
            g_rsql_cursor.source_column_count;
        for (result = 0u; result < g_rsql_cursor.source_column_count;
             ++result) g_rsql_cursor.projection[result] = result;
    } else if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
               g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE) {
        g_rsql_cursor.result_column_count =
            g_rsql_statement.projection_count;
        for (result = 0u; result < g_rsql_statement.projection_count;
             ++result) {
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_statement.projection_aggregate[result])) {
                g_rsql_cursor.projection_aggregate[result] =
                    g_rsql_statement.projection_aggregate[result];
                g_rsql_cursor.projection[result] = 0xFFu;
                continue;
            }
            if (g_rsql_statement.projection_aggregate[result] !=
                RSQL_AGG_NONE) return RSQL_ERR_UNSUPPORTED_SQL;
            rc = resolve_source_only(
                g_rsql_statement.projections[result], outer_qualifier,
                g_rsql_cursor.columns, g_rsql_cursor.source_column_count,
                0u, &source);
            if (rc != RSQL_OK) return rc;
            g_rsql_cursor.projection[result] = source;
        }
    }
    if (g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_EXISTS) {
        rc = resolve_subquery_column(g_rsql_statement.subquery_projection,
            &g_rsql_cursor.subquery_projection);
        if (rc != RSQL_OK) return rc;
        right = source_column(g_rsql_cursor.subquery_projection);
    } else right = 0;

    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE) {
      g_rsql_cursor.predicate_count = g_rsql_statement.predicate_count;
      g_rsql_cursor.bool_program_count =
          g_rsql_statement.bool_program_count;
      memcpy(g_rsql_cursor.bool_program, g_rsql_statement.bool_program,
             g_rsql_statement.bool_program_count);
      for (index = 0u; index < g_rsql_statement.predicate_count; ++index) {
        op = g_rsql_statement.predicates[index].op;
        if (op == RSQL_PRED_SUBQUERY &&
            g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_EXISTS) {
            source = 0u;
        } else {
            rc = resolve_source_only(
                g_rsql_statement.predicates[index].column,
                outer_qualifier, g_rsql_cursor.columns,
                g_rsql_cursor.source_column_count, 0u, &source);
            if (rc != RSQL_OK) return rc;
        }
        left = &g_rsql_cursor.columns[source];
        if (op == RSQL_PRED_SUBQUERY) {
            if (g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_EXISTS &&
                !reference_types_ok(left, right)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        } else {
            value = &g_rsql_statement.predicates[index].value;
            if (value->kind == RSQL_VALUE_ENUM) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            rc = rsql_query_resolve_float_value(left, value);
            if (rc != RSQL_OK) return rc;
            if (!literal_type_ok(op, left, value)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        }
        g_rsql_cursor.predicates[index].column = source;
        g_rsql_cursor.predicates[index].op = op;
        memcpy(&g_rsql_cursor.predicates[index].value,
               &g_rsql_statement.predicates[index].value,
               sizeof(g_rsql_cursor.predicates[index].value));
      }
    }
    for (index = 0u; index <
         g_rsql_statement.subquery_predicate_count; ++index) {
        op = g_rsql_statement.columns[index].type.tag;
        if (op == RSQL_PRED_SUBQUERY) {
            g_rsql_statement.columns[index].type.parameter = 0u;
            continue;
        }
        rc = resolve_depth_column(g_rsql_statement.columns[index].name,
                                  index, &source);
        if (rc != RSQL_OK) return rc;
        left = source_column(source);
        value = &g_rsql_statement.values[index];
        if (value->kind == RSQL_VALUE_ENUM) {
            rc = resolve_depth_column(value->string, index, &reference);
        } else rc = RSQL_ERR_NOT_FOUND;
        if (value->kind == RSQL_VALUE_ENUM && rc == RSQL_OK) {
            if (op == RSQL_PRED_LIKE ||
                !reference_types_ok(left, source_column(reference))) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            value->kind = RSQL_VALUE_REFERENCE;
            value->integer.bytes[0] = reference;
        } else {
            if (value->kind == RSQL_VALUE_ENUM) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            rc = rsql_query_resolve_float_value(left, value);
            if (rc != RSQL_OK) return rc;
            if (!literal_type_ok(op, left, value)) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        }
        g_rsql_statement.columns[index].type.parameter = source;
    }
    g_rsql_cursor.where_present = 1u;
    return RSQL_OK;
}
#endif

static const rsql_u8 BIT_MASKS[8] = {
    0x01u, 0x02u, 0x04u, 0x08u, 0x10u, 0x20u, 0x40u, 0x80u
};

static rsql_u8 column_mask(rsql_u8 column) {
    return BIT_MASKS[column & RSQL_SOURCE_COLUMN_MASK];
}

#define slot_mask column_mask

static rsql_u8 slot_used(rsql_u8 slot) {
    return (g_rsql_meta_page1[RSQL_ROW_BITMAP + (slot >> 3u)] &
            slot_mask(slot)) != 0u;
}

static rsql_u8 valid_table(rsql_u16 row_width) {
    return g_rsql_meta_page0[0] == 'R' && g_rsql_meta_page0[1] == 'T' &&
           g_rsql_meta_page0[2] == 'B' && g_rsql_meta_page0[3] == 'L' &&
           g_rsql_meta_page0[4] == RSQL_STORAGE_VERSION &&
           rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_WIDTH]) ==
               row_width &&
           g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] ==
               rsql_page_checksum(g_rsql_meta_page0);
}

static rsql_u8 valid_row(rsql_u16 row_width) {
    rsql_u8 capacity;
    if (g_rsql_meta_page1[0] != 'R' || g_rsql_meta_page1[1] != 'R' ||
        g_rsql_meta_page1[2] != 'O' || g_rsql_meta_page1[3] != 'W' ||
        g_rsql_meta_page1[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_WIDTH]) != row_width) {
        return 0u;
    }
    capacity = g_rsql_meta_page1[RSQL_ROW_CAPACITY];
    return capacity != 0u && capacity <= 32u &&
        (rsql_u16)(RSQL_ROW_DATA + (rsql_u16)capacity * row_width) <=
            RSQL_REU_PAGE_SIZE;
}

static rsql_u8 read_table(rsql_u16 table_page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(table_page),
                               g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_table(row_width) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 read_row_page(rsql_u16 page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
                               g_rsql_meta_page1, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_row(row_width) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 raw_first(rsql_u16 table_page, rsql_u16 row_width,
                         RsqlRowId* row_id) {
    rsql_u16 page;
    rsql_u8 slot;
    rsql_u8 rc = read_table(table_page, row_width);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY]; ++slot) {
            if (slot_used(slot)) {
                row_id->page = page;
                row_id->slot = slot;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 raw_locate(rsql_u16 table_page, rsql_u16 row_width,
                          rsql_u16 wanted_page) {
    rsql_u16 page;
    rsql_u8 rc = read_table(table_page, row_width);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        if (page == wanted_page) return RSQL_OK;
        page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 raw_next(rsql_u16 table_page, rsql_u16 row_width,
                        const RsqlRowId* current, RsqlRowId* next_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u8 slot;
    rsql_u8 rc = raw_locate(table_page, row_width, current->page);
    if (rc != RSQL_OK) return rc;
    if (current->slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY] ||
        !slot_used(current->slot)) return RSQL_ERR_NOT_FOUND;
    page = current->page;
    slot = (rsql_u8)(current->slot + 1u);
    for (;;) {
        while (slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY]) {
            if (slot_used(slot)) {
                next_out->page = page;
                next_out->slot = slot;
                return RSQL_OK;
            }
            ++slot;
        }
        next = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
        if (next == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
        page = next;
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        slot = 0u;
    }
}

#ifdef RSQL_JOIN_AGGREGATE_CORE
rsql_u8 rsql_query_join_aggregate_read(
#else
static rsql_u8 raw_read(
#endif
                        rsql_u16 table_page, rsql_u16 row_width,
                        const RsqlRowId* row_id, rsql_u8* destination) {
    rsql_u16 offset;
    rsql_u8 rc = raw_locate(table_page, row_width, row_id->page);
    if (rc != RSQL_OK) return rc;
    if (row_id->slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY] ||
        !slot_used(row_id->slot)) return RSQL_ERR_NOT_FOUND;
    offset = (rsql_u16)(RSQL_ROW_DATA +
                        (rsql_u16)row_id->slot * row_width);
    memcpy(destination, &g_rsql_meta_page1[offset], row_width);
    return RSQL_OK;
}

#ifdef RSQL_JOIN_AGGREGATE_CORE
#define raw_read rsql_query_join_aggregate_read
#endif

static const RsqlColumnInfo* source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static const rsql_u8* source_row(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) return g_rsql_execution.row;
    return (source & RSQL_SOURCE_INNER)
        ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
}

static rsql_u8 source_null(rsql_u8 source) {
    const rsql_u8* row;
    rsql_u8 column = source & RSQL_SOURCE_COLUMN_MASK;
    if ((source & RSQL_SOURCE_INNER) &&
        !(source & RSQL_SOURCE_SUBQUERY) &&
        g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    row = source_row(source);
    return (row[0] & column_mask(column)) != 0u;
}

static rsql_u16 value_width(const RsqlTypeSpec* type) {
    switch (type->tag) {
        case RSQL_TYPE_BOOLEAN:
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8: return 1u;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_FIXED8_8:
        case RSQL_TYPE_ENUM16: return 2u;
        case RSQL_TYPE_I32:
        case RSQL_TYPE_TEXT:
        case RSQL_TYPE_BLOB: return 4u;
        case RSQL_TYPE_I64: return 8u;
        case RSQL_TYPE_FLOAT5: return 5u;
        case RSQL_TYPE_CHAR: return type->parameter;
    }
    return 0u;
}

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ('a' - 'A'));
    }
    return value;
}

static rsql_i8 compare_signed(const rsql_u8* left, rsql_u8 left_width,
                              const rsql_u8* right, rsql_u8 right_width) {
    rsql_u8 left_fill = (left[left_width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 right_fill = (right[right_width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index = 8u;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (left_fill != right_fill) return left_fill ? -1 : 1;
    while (index != 0u) {
        --index;
        left_byte = index < left_width ? left[index] : left_fill;
        right_byte = index < right_width ? right[index] : right_fill;
        if (left_byte < right_byte) return -1;
        if (left_byte > right_byte) return 1;
    }
    return 0;
}

static rsql_i8 compare_unsigned(const rsql_u8* left, const rsql_u8* right,
                                rsql_u8 width) {
    rsql_u8 index = width;
    while (index != 0u) {
        --index;
        if (left[index] < right[index]) return -1;
        if (left[index] > right[index]) return 1;
    }
    return 0;
}

static rsql_i8 compare_float(const rsql_u8* left, const rsql_u8* right) {
    rsql_u8 left_negative;
    rsql_u8 right_negative;
    rsql_u8 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (left[0] == 0u && right[0] == 0u) return 0;
    left_negative = left[0] != 0u && (left[1] & 0x80u) != 0u;
    right_negative = right[0] != 0u && (right[1] & 0x80u) != 0u;
    if (left_negative != right_negative) return left_negative ? -1 : 1;
    for (index = 0u; index < RSQL_FLOAT5_BYTES; ++index) {
        left_byte = left[index];
        right_byte = right[index];
        if (index == 1u) {
            left_byte &= 0x7Fu;
            right_byte &= 0x7Fu;
        }
        if (left_byte == right_byte) continue;
        if (left_negative) return left_byte < right_byte ? 1 : -1;
        return left_byte < right_byte ? -1 : 1;
    }
    return 0;
}

static rsql_i8 compare_chars(const rsql_u8* left, rsql_u16 left_width,
                             const rsql_u8* right, rsql_u16 right_width) {
    rsql_u16 width = left_width > right_width ? left_width : right_width;
    rsql_u16 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    for (index = 0u; index < width; ++index) {
        left_byte = index < left_width ? folded(left[index]) : (rsql_u8)' ';
        right_byte = index < right_width ? folded(right[index]) :
            (rsql_u8)' ';
        if (left_byte < right_byte) return -1;
        if (left_byte > right_byte) return 1;
    }
    return 0;
}

static rsql_i8 compare_literal(rsql_u8 source,
                               const RsqlParsedValue* literal) {
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* value = &source_row(source)[column->offset];
    rsql_u8 width = (rsql_u8)value_width(&column->type);
    if (column->type.tag == RSQL_TYPE_CHAR) {
        return compare_chars(value, column->type.parameter,
                             (const rsql_u8*)literal->string,
                             literal->length);
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(value, literal->integer.bytes);
    }
    if (column->type.tag == RSQL_TYPE_FIXED8_8) {
        if (compare_signed(&value[1], 1u,
                           literal->integer.bytes, 8u) < 0) return -1;
        if (compare_signed(&value[1], 1u,
                           literal->integer.bytes, 8u) > 0) return 1;
        return value[0] == 0u ? 0 : 1;
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(value, literal->integer.bytes, width);
    }
    return compare_signed(value, width, literal->integer.bytes, 8u);
}

static rsql_i8 compare_reference(rsql_u8 left_source,
                                 rsql_u8 right_source) {
    const RsqlColumnInfo* left_column = source_column(left_source);
    const RsqlColumnInfo* right_column = source_column(right_source);
    const rsql_u8* left = &source_row(left_source)[left_column->offset];
    const rsql_u8* right = &source_row(right_source)[right_column->offset];
    rsql_u8 left_width = (rsql_u8)value_width(&left_column->type);
    rsql_u8 right_width = (rsql_u8)value_width(&right_column->type);
    if (left_column->type.tag == RSQL_TYPE_CHAR) {
        return compare_chars(left, left_column->type.parameter,
                             right, right_column->type.parameter);
    }
    if (left_column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(left, right);
    }
    if (left_column->type.tag == RSQL_TYPE_BOOLEAN ||
        left_column->type.tag == RSQL_TYPE_ENUM8 ||
        left_column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(left, right, left_width);
    }
    return compare_signed(left, left_width, right, right_width);
}

static rsql_u8 comparison_matches(rsql_i8 comparison, rsql_u8 op) {
    if (op == RSQL_PRED_EQ) return comparison == 0;
    if (op == RSQL_PRED_NE) return comparison != 0;
    if (op == RSQL_PRED_LT) return comparison < 0;
    if (op == RSQL_PRED_LE) return comparison <= 0;
    if (op == RSQL_PRED_GT) return comparison > 0;
    if (op == RSQL_PRED_GE) return comparison >= 0;
    return 0u;
}

static rsql_u8 like_char(const rsql_u8* row, rsql_u16 width,
                         const RsqlParsedValue* pattern) {
    rsql_u16 row_length = width;
    rsql_u16 row_index = 0u;
    rsql_u16 pattern_index = 0u;
    rsql_u16 star_pattern = 0xFFFFu;
    rsql_u16 star_row = 0u;
    rsql_u8 pattern_byte;
    while (row_length != 0u && row[row_length - 1u] == (rsql_u8)' ') {
        --row_length;
    }
    while (row_index < row_length) {
        if (pattern_index < pattern->length) {
            pattern_byte = (rsql_u8)pattern->string[pattern_index];
            if (pattern_byte == (rsql_u8)'_' ||
                folded(pattern_byte) == folded(row[row_index])) {
                ++pattern_index;
                ++row_index;
                continue;
            }
            if (pattern_byte == (rsql_u8)'%') {
                star_pattern = pattern_index++;
                star_row = row_index;
                continue;
            }
        }
        if (star_pattern != 0xFFFFu) {
            pattern_index = (rsql_u16)(star_pattern + 1u);
            row_index = (rsql_u16)(++star_row);
            continue;
        }
        return 0u;
    }
    while (pattern_index < pattern->length &&
           pattern->string[pattern_index] == '%') ++pattern_index;
    return pattern_index == pattern->length;
}

static rsql_u8 predicate_truth(rsql_u8 index) {
    const RsqlBoundPredicate* predicate = &g_rsql_cursor.predicates[index];
    const RsqlColumnInfo* column = source_column(predicate->column);
    const rsql_u8* row = source_row(predicate->column);
    rsql_u8 left_null = source_null(predicate->column);
    rsql_u8 right_null = 0u;
    rsql_i8 comparison;
    if (RSQL_VARIABLE_PREDICATE_MASK & (rsql_u8)(1u << index)) {
        return RSQL_VARIABLE_PREDICATE_TRUTH[index];
    }
    if (predicate->op == RSQL_PRED_SUBQUERY) {
        return subquery_truth(predicate->column);
    }
    if (predicate->op == RSQL_PRED_IS_NULL) {
        return left_null ? SQL_TRUE : SQL_FALSE;
    }
    if (predicate->op == RSQL_PRED_IS_NOT_NULL) {
        return left_null ? SQL_FALSE : SQL_TRUE;
    }
    if (predicate->value.kind == RSQL_VALUE_REFERENCE) {
        right_null = source_null(predicate->value.integer.bytes[0]);
    } else if (predicate->value.kind == RSQL_VALUE_NULL) {
        right_null = 1u;
    }
    if (left_null || right_null) return SQL_UNKNOWN;
    if (predicate->op == RSQL_PRED_LIKE) {
        return like_char(&row[column->offset], column->type.parameter,
                         &predicate->value) ? SQL_TRUE : SQL_FALSE;
    }
    if (predicate->value.kind == RSQL_VALUE_REFERENCE) {
        comparison = compare_reference(predicate->column,
                         predicate->value.integer.bytes[0]);
    } else comparison = compare_literal(predicate->column, &predicate->value);
    return comparison_matches(comparison, predicate->op)
        ? SQL_TRUE : SQL_FALSE;
}

#ifdef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 aggregate_nested_subquery_truth(
    const RsqlParsedColumn* predicate) {
    rsql_u8 saved_kind = g_rsql_cursor.subquery_kind;
    rsql_u8 saved_projection = g_rsql_cursor.subquery_projection;
    rsql_u8 saved_compare = g_rsql_statement.subquery_compare_op;
    rsql_u8 result;
    g_nested_eval = 1u;
    g_rsql_cursor.join_type = RSQL_JOIN_INNER;
    g_rsql_cursor.subquery_kind = predicate->type.flags;
    g_rsql_cursor.subquery_projection =
        (rsql_u8)(predicate->type.parameter >> 8u);
    g_rsql_statement.subquery_compare_op =
        (rsql_u8)predicate->type.auxiliary;
    result = subquery_truth((rsql_u8)predicate->type.parameter);
    g_rsql_statement.subquery_compare_op = saved_compare;
    g_rsql_cursor.subquery_projection = saved_projection;
    g_rsql_cursor.subquery_kind = saved_kind;
    g_rsql_cursor.join_type = RSQL_JOIN_NONE;
    g_nested_eval = 0u;
    return result;
}
#endif

static rsql_u8 evaluate_program(rsql_u8 start, rsql_u8 count) {
    rsql_u8 stack[RSQL_PREDICATES_MAX];
    rsql_u8 stack_count = 0u;
    rsql_u8 opcode;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    if (count == 0u) return 1u;
    for (index = start; index < (rsql_u8)(start + count); ++index) {
        opcode = g_rsql_cursor.bool_program[index];
        if (opcode < RSQL_PREDICATES_MAX) {
            if (opcode >= g_rsql_cursor.predicate_count ||
                stack_count >= RSQL_PREDICATES_MAX) return 0u;
            stack[stack_count++] = predicate_truth(opcode);
        } else if (opcode == RSQL_BOOL_NOT) {
            if (stack_count == 0u) return 0u;
            if (stack[stack_count - 1u] == SQL_TRUE) {
                stack[stack_count - 1u] = SQL_FALSE;
            } else if (stack[stack_count - 1u] == SQL_FALSE) {
                stack[stack_count - 1u] = SQL_TRUE;
            }
        } else {
            if (stack_count < 2u) return 0u;
            right = stack[--stack_count];
            left = stack[stack_count - 1u];
            if (opcode == RSQL_BOOL_AND) {
                if (left == SQL_FALSE || right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else if (left == SQL_TRUE && right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else if (opcode == RSQL_BOOL_OR) {
                if (left == SQL_TRUE || right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else if (left == SQL_FALSE && right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else return 0u;
        }
    }
    return stack_count == 1u && stack[0] == SQL_TRUE;
}

static rsql_u8 subquery_predicate_truth(rsql_u8 index) {
    const RsqlParsedColumn* predicate = &g_rsql_statement.columns[index];
    const RsqlParsedValue* right = &g_rsql_statement.values[index];
    rsql_u8 source = (rsql_u8)predicate->type.parameter;
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* row = source_row(source);
    rsql_u8 left_null = source_null(source);
    rsql_u8 right_null = 0u;
    rsql_u8 op = predicate->type.tag;
    rsql_i8 comparison;
    if (op == RSQL_PRED_SUBQUERY) {
#ifdef RSQL_JOIN_AGGREGATE_CORE
        return aggregate_nested_subquery_truth(predicate);
#else
        return rsql_nested_subquery_truth((RsqlParsedColumn*)predicate);
#endif
    }
    if (op == RSQL_PRED_IS_NULL) return left_null ? SQL_TRUE : SQL_FALSE;
    if (op == RSQL_PRED_IS_NOT_NULL) {
        return left_null ? SQL_FALSE : SQL_TRUE;
    }
    if (right->kind == RSQL_VALUE_REFERENCE) {
        right_null = source_null(right->integer.bytes[0]);
    } else if (right->kind == RSQL_VALUE_NULL) right_null = 1u;
    if (left_null || right_null) return SQL_UNKNOWN;
    if (op == RSQL_PRED_LIKE) {
        return like_char(&row[column->offset], column->type.parameter, right)
            ? SQL_TRUE : SQL_FALSE;
    }
    if (right->kind == RSQL_VALUE_REFERENCE) {
        comparison = compare_reference(source, right->integer.bytes[0]);
    } else comparison = compare_literal(source, right);
    return comparison_matches(comparison, op) ? SQL_TRUE : SQL_FALSE;
}

static rsql_u8 evaluate_subquery_program(void) {
    rsql_u8 stack[RSQL_PREDICATES_MAX];
    rsql_u8 stack_count = 0u;
    rsql_u8 opcode;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    const rsql_u8* program = g_nested_eval
        ? RSQL_NESTED_BOOL_PROGRAM :
          g_rsql_statement.subquery_bool_program;
    rsql_u8 count = g_nested_eval
        ? g_rsql_statement.nested_bool_program_count :
          g_rsql_statement.subquery_bool_program_count;
    if (count == 0u) return SQL_TRUE;
    for (index = 0u; index < count; ++index) {
        opcode = program[index];
        if (opcode < RSQL_PREDICATES_MAX) {
            if (opcode >= g_rsql_statement.subquery_predicate_count ||
                stack_count >= RSQL_PREDICATES_MAX) return SQL_FALSE;
            stack[stack_count++] = subquery_predicate_truth(opcode);
        } else if (opcode == RSQL_BOOL_NOT) {
            if (stack_count == 0u) return SQL_FALSE;
            if (stack[stack_count - 1u] == SQL_TRUE) {
                stack[stack_count - 1u] = SQL_FALSE;
            } else if (stack[stack_count - 1u] == SQL_FALSE) {
                stack[stack_count - 1u] = SQL_TRUE;
            }
        } else {
            if (stack_count < 2u) return SQL_FALSE;
            right = stack[--stack_count];
            left = stack[stack_count - 1u];
            if (opcode == RSQL_BOOL_AND) {
                if (left == SQL_FALSE || right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else if (left == SQL_TRUE && right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else if (opcode == RSQL_BOOL_OR) {
                if (left == SQL_TRUE || right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else if (left == SQL_FALSE && right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else return SQL_FALSE;
        }
    }
    return stack_count == 1u ? stack[0] : SQL_FALSE;
}

#ifdef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 subquery_truth(rsql_u8 predicate_column) {
#else
rsql_u8 subquery_truth(rsql_u8 predicate_column) {
#endif
    rsql_u8 found = 0u;
    rsql_u8 saw_null = 0u;
    rsql_u8 scalar_truth = SQL_UNKNOWN;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_i8 comparison;
    rsql_u16 table_page = g_rsql_cursor.join_type != RSQL_JOIN_NONE
        ? g_rsql_cursor.subquery_table_page : g_rsql_cursor.join_table_page;
    rsql_u16 row_width = g_rsql_cursor.join_type != RSQL_JOIN_NONE
        ? g_rsql_cursor.subquery_row_width : g_rsql_cursor.join_row_width;
    RsqlRowId* row_id = g_rsql_cursor.join_type != RSQL_JOIN_NONE
        ? &g_rsql_cursor.subquery_row_id : &g_rsql_cursor.join_row_id;
    rsql_u8* row = g_rsql_cursor.join_type != RSQL_JOIN_NONE
        ? g_rsql_execution.row : g_rsql_cursor.scan_row;
    g_subquery_rc = raw_first(table_page, row_width, &g_join_candidate);
    while (g_subquery_rc == RSQL_OK) {
        row_id->page = g_join_candidate.page;
        row_id->slot = g_join_candidate.slot;
        g_subquery_rc = raw_read(table_page, row_width, &g_join_candidate,
            row);
        if (g_subquery_rc != RSQL_OK) return SQL_UNKNOWN;
        if (g_rsql_cursor.join_type == RSQL_JOIN_NONE) {
            g_rsql_cursor.join_inner_null = 0u;
        }
        right_null = evaluate_subquery_program();
        /* A nested scalar subquery reports cardinality and I/O failures via
         * the shared side channel.  Do not let the enclosing scan overwrite
         * that error with its next-row result. */
        if (g_subquery_rc != RSQL_OK) return SQL_UNKNOWN;
        if (right_null == SQL_TRUE) {
            if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_EXISTS) {
                return SQL_TRUE;
            }
            left_null = source_null(predicate_column);
            right_null = source_null(g_rsql_cursor.subquery_projection);
            if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_IN) {
                if (left_null || right_null) saw_null = 1u;
                else if (compare_reference(predicate_column,
                         g_rsql_cursor.subquery_projection) == 0) {
                    return SQL_TRUE;
                }
            } else {
                if (found) {
                    g_subquery_rc = RSQL_ERR_SUBQUERY_ROWS;
                    return SQL_UNKNOWN;
                }
                found = 1u;
                if (left_null || right_null) scalar_truth = SQL_UNKNOWN;
                else {
                    comparison = compare_reference(predicate_column,
                        g_rsql_cursor.subquery_projection);
                    scalar_truth = comparison_matches(comparison,
                        g_rsql_statement.subquery_compare_op)
                        ? SQL_TRUE : SQL_FALSE;
                }
            }
        }
        g_subquery_rc = raw_next(table_page, row_width, row_id,
                                &g_join_candidate);
    }
    if (g_subquery_rc != RSQL_ERR_NOT_FOUND) return SQL_UNKNOWN;
    g_subquery_rc = RSQL_OK;
    if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_EXISTS) return SQL_FALSE;
    if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_IN) {
        return saw_null ? SQL_UNKNOWN : SQL_FALSE;
    }
    return found ? scalar_truth : SQL_UNKNOWN;
}

static rsql_u8 on_matches(void) {
    if (g_rsql_cursor.join_type == RSQL_JOIN_CROSS) return 1u;
    return evaluate_program(0u, g_rsql_cursor.join_bool_program_count);
}

static rsql_u8 where_matches(void) {
    if (!g_rsql_cursor.where_present) return 1u;
    return evaluate_program(g_rsql_cursor.join_bool_program_count,
        (rsql_u8)(g_rsql_cursor.bool_program_count -
                  g_rsql_cursor.join_bool_program_count));
}

#define JOIN_VARIABLE_INNER 1u
#define JOIN_VARIABLE_LEFT  2u

#ifndef RSQL_JOIN_AGGREGATE_CORE
rsql_u8 __fastcall__ rsql_query_join_predicate_phase(
    RsqlCursorNextRequest* request) {
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        RSQL_VARIABLE_PREDICATE_MASK == 0u) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.update_scan_started == JOIN_VARIABLE_INNER) {
        g_subquery_rc = RSQL_OK;
        if (on_matches()) {
            if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
            g_rsql_cursor.join_outer_matched = 1u;
            if (where_matches()) {
                if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
                g_rsql_cursor.positioned = 1u;
                request->has_row = 1u;
                return RSQL_OK;
            }
        }
        if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
        return rsql_query_join_next_phase(request);
    }
    if (g_rsql_cursor.update_scan_started != JOIN_VARIABLE_LEFT) {
        return RSQL_ERR_CURSOR_STATE;
    }
    g_subquery_rc = RSQL_OK;
    g_rsql_cursor.join_outer_pending_advance = 1u;
    if (where_matches()) {
        if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
        g_rsql_cursor.positioned = 1u;
        request->has_row = 1u;
        return RSQL_OK;
    }
    if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
    return rsql_query_join_next_phase(request);
}
#endif

static rsql_u8 advance_outer(rsql_u8 next_row) {
    rsql_u8 rc;
    if (next_row) {
        rc = raw_next(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                      &g_rsql_cursor.row_id, &g_join_candidate);
    } else {
        rc = raw_first(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                       &g_join_candidate);
    }
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.row_id.page = g_join_candidate.page;
    g_rsql_cursor.row_id.slot = g_join_candidate.slot;
    rc = raw_read(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                  &g_join_candidate, g_rsql_cursor.row);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.join_outer_started = 1u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    g_rsql_cursor.join_inner_null = 0u;
    return RSQL_OK;
}

#ifdef RSQL_JOIN_AGGREGATE_CORE
static rsql_u8 aggregate_subquery_source_next(
    RsqlCursorNextRequest* request) {
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.positioned) {
        g_join_next_rc = raw_next(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
            &g_join_candidate);
    } else {
        g_join_next_rc = raw_first(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_candidate);
    }
    while (g_join_next_rc == RSQL_OK) {
        g_rsql_cursor.row_id = g_join_candidate;
        g_join_next_rc = raw_read(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_candidate,
            g_rsql_cursor.row);
        if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
        g_rsql_cursor.join_inner_null = 1u;
        g_subquery_rc = RSQL_OK;
        if (evaluate_program(0u, g_rsql_cursor.bool_program_count)) {
            if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
            g_rsql_cursor.positioned = 1u;
            request->has_row = 1u;
            return RSQL_OK;
        }
        if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
        g_join_next_rc = raw_next(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
            &g_join_candidate);
    }
    if (g_join_next_rc != RSQL_ERR_NOT_FOUND) return g_join_next_rc;
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}
#endif

#ifdef RSQL_JOIN_AGGREGATE_CORE
rsql_u8 __fastcall__ rsql_query_join_aggregate_source_next_phase_c(
#else
rsql_u8 __fastcall__ rsql_query_join_next_phase_c(
#endif
    RsqlCursorNextRequest* request) {
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
         g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE)) {
        return RSQL_ERR_CURSOR_STATE;
    }
#ifdef RSQL_JOIN_AGGREGATE_CORE
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE) {
        return aggregate_subquery_source_next(request);
    }
#endif
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.join_outer_pending_advance) {
        g_join_next_rc = advance_outer(1u);
        if (g_join_next_rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
    } else if (!g_rsql_cursor.join_outer_started) {
        g_join_next_rc = advance_outer(0u);
        if (g_join_next_rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
    }
    for (;;) {
        if (g_rsql_cursor.join_inner_started) {
            g_join_next_rc = raw_next(g_rsql_cursor.join_table_page,
                          g_rsql_cursor.join_row_width,
                          &g_rsql_cursor.join_row_id, &g_join_candidate);
        } else {
            g_join_next_rc = raw_first(g_rsql_cursor.join_table_page,
                           g_rsql_cursor.join_row_width, &g_join_candidate);
        }
        while (g_join_next_rc == RSQL_OK) {
            g_rsql_cursor.join_inner_started = 1u;
            g_rsql_cursor.join_row_id.page = g_join_candidate.page;
            g_rsql_cursor.join_row_id.slot = g_join_candidate.slot;
            g_join_next_rc = raw_read(g_rsql_cursor.join_table_page,
                          g_rsql_cursor.join_row_width, &g_join_candidate,
                          g_rsql_cursor.scan_row);
            if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
            g_rsql_cursor.join_inner_null = 0u;
            g_subquery_rc = RSQL_OK;
#ifndef RSQL_JOIN_AGGREGATE_CORE
            if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
                g_rsql_cursor.update_scan_started = JOIN_VARIABLE_INNER;
                RSQL_VARIABLE_PREDICATE_SOURCE = 2u;
                return RSQL_QUERY_PHASE_PREDICATE;
            }
#endif
            if (on_matches()) {
                if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
                g_rsql_cursor.join_outer_matched = 1u;
                if (where_matches()) {
                    if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
                    g_rsql_cursor.positioned = 1u;
                    request->has_row = 1u;
                    return RSQL_OK;
                }
                if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
            }
            if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
            g_join_next_rc = raw_next(g_rsql_cursor.join_table_page,
                          g_rsql_cursor.join_row_width,
                          &g_rsql_cursor.join_row_id, &g_join_candidate);
        }
        if (g_join_next_rc != RSQL_ERR_NOT_FOUND) return g_join_next_rc;
        if (g_rsql_cursor.join_type == RSQL_JOIN_LEFT &&
            !g_rsql_cursor.join_outer_matched) {
            g_rsql_cursor.join_inner_null = 1u;
            g_rsql_cursor.join_outer_matched = 1u;
            g_subquery_rc = RSQL_OK;
#ifndef RSQL_JOIN_AGGREGATE_CORE
            if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
                g_rsql_cursor.update_scan_started = JOIN_VARIABLE_LEFT;
                RSQL_VARIABLE_PREDICATE_SOURCE = 2u;
                return RSQL_QUERY_PHASE_PREDICATE;
            }
#endif
            if (where_matches()) {
                if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
                g_rsql_cursor.join_outer_pending_advance = 1u;
                g_rsql_cursor.positioned = 1u;
                request->has_row = 1u;
                return RSQL_OK;
            }
            if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
        }
        g_join_next_rc = advance_outer(1u);
        if (g_join_next_rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
    }

finished:
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}

#ifndef RSQL_JOIN_AGGREGATE_CORE
static rsql_i8 shape_compare_source(rsql_u8 source) {
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* left = source_row(source);
    const rsql_u8* right;
    rsql_u8 left_null = source_null(source);
    rsql_u8 right_null;
    rsql_u8 width = (rsql_u8)value_width(&column->type);
    if (source & RSQL_SOURCE_INNER) {
        right_null = g_join_shape_target_inner_null;
        if (!right_null) {
            g_join_shape_rc = raw_read(g_rsql_cursor.join_table_page,
                g_rsql_cursor.join_row_width, &g_join_shape_target_inner,
                g_rsql_execution.row);
            if (g_join_shape_rc == RSQL_OK) {
                right_null = (g_rsql_execution.row[0] &
                    column_mask(source & RSQL_SOURCE_COLUMN_MASK)) != 0u;
            }
        }
    } else {
        g_join_shape_rc = raw_read(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_shape_target_outer,
            g_rsql_execution.row);
        right_null = (g_rsql_execution.row[0] &
            column_mask(source & RSQL_SOURCE_COLUMN_MASK)) != 0u;
    }
    if (g_join_shape_rc != RSQL_OK) return 0;
    if (left_null != right_null) return left_null ? -1 : 1;
    if (left_null) return 0;
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        memcpy(g_rsql_variable_compare_left,
               &left[column->offset], 4u);
        memcpy(g_rsql_variable_compare_right,
               &g_rsql_execution.row[column->offset], 4u);
        g_rsql_variable_compare_kind = column->type.tag;
        g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_HANDLES;
        g_join_shape_rc = rsql_query_variable_compare_owner(4u);
        if (g_join_shape_rc != RSQL_OK) return 0;
        return g_rsql_variable_compare_result;
    }
    right = &g_rsql_execution.row[column->offset];
    left += column->offset;
    if (column->type.tag == RSQL_TYPE_CHAR) {
        return compare_chars(left, column->type.parameter,
                             right, column->type.parameter);
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(left, right);
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(left, right, width);
    }
    return compare_signed(left, width, right, width);
}

static const rsql_u8* shape_scalar_source_row(rsql_u8 source,
                                               rsql_u8 target) {
    if (!target) return source_row(source);
    if (source & RSQL_SOURCE_INNER) {
        g_join_shape_rc = raw_read(g_rsql_cursor.join_table_page,
            g_rsql_cursor.join_row_width, &g_join_shape_target_inner,
            g_rsql_execution.row);
    } else {
        g_join_shape_rc = raw_read(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_shape_target_outer,
            g_rsql_execution.row);
    }
    return g_rsql_execution.row;
}

static rsql_u8 shape_scalar_source_null(rsql_u8 source, rsql_u8 target) {
    const rsql_u8* row;
    if (!target) return source_null(source);
    if ((source & RSQL_SOURCE_INNER) &&
        g_join_shape_target_inner_null) return 1u;
    row = shape_scalar_source_row(source, 1u);
    if (g_join_shape_rc != RSQL_OK) return 0u;
    return (row[0] & column_mask(source & RSQL_SOURCE_COLUMN_MASK)) != 0u;
}

static rsql_u16 shape_scalar_bound(rsql_u8 result, rsql_u8 high) {
    const rsql_u8* bytes = &g_rsql_cursor.aggregate_counts[result].bytes[
        high ? 2u : 0u];
    return (rsql_u16)bytes[0] | ((rsql_u16)bytes[1] << 8u);
}

static rsql_u8 shape_scalar_null(rsql_u8 result, rsql_u8 target);

static rsql_u8 shape_scalar_text_info(RsqlScalarComparePart* part,
                                      const rsql_u8* handle) {
    rsql_u16 page = g_rsql_cursor.blob_directory;
    rsql_u16 base;
    rsql_u8 slot;
    while (page != RSQL_PAGE_NONE) {
        g_join_shape_rc = rsql_reu_read(rsql_reu_page_address(page),
            g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
        if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
        if (g_rsql_meta_page0[0] != 'R' ||
            g_rsql_meta_page0[1] != 'B' ||
            g_rsql_meta_page0[2] != 'D' ||
            g_rsql_meta_page0[3] != 'R' ||
            g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
                rsql_page_checksum(g_rsql_meta_page0)) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        for (slot = 0u; slot < SHAPE_BLOB_ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(SHAPE_BLOB_DIR_ENTRIES +
                (rsql_u16)slot * SHAPE_BLOB_ENTRY_BYTES);
            if (g_rsql_meta_page0[base] == 1u &&
                g_rsql_meta_page0[base + SHAPE_BLOB_ENTRY_KIND] ==
                    RSQL_TYPE_TEXT &&
                memcmp(&g_rsql_meta_page0[
                    base + SHAPE_BLOB_ENTRY_HANDLE], handle, 4u) == 0) {
                if (g_rsql_meta_page0[base + SHAPE_BLOB_ENTRY_LENGTH + 2u] ||
                    g_rsql_meta_page0[
                        base + SHAPE_BLOB_ENTRY_LENGTH + 3u]) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
                part->kind = 1u;
                part->first_page = rsql_get_u16(&g_rsql_meta_page0[
                    base + SHAPE_BLOB_ENTRY_FIRST]);
                part->next_page = part->first_page;
                part->length = rsql_get_u16(&g_rsql_meta_page0[
                    base + SHAPE_BLOB_ENTRY_LENGTH]);
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page0[SHAPE_BLOB_DIR_NEXT]);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static void shape_prepare_scalar_part(RsqlScalarComparePart* part,
                                      rsql_u8 result, rsql_u8 right,
                                      rsql_u8 target,
                                      rsql_u8* fixed_target) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 source;
    const RsqlColumnInfo* column;
    const rsql_u8* row;
    const rsql_u8* data;
    memset(part, 0, sizeof(*part));
    if ((!right && (operation & RSQL_PROJECTION_LITERAL_LEFT)) ||
        (right && (operation & RSQL_PROJECTION_LITERAL_RIGHT))) {
        part->data = RSQL_SCALAR_LITERAL_DATA(result);
        part->length = RSQL_SCALAR_LITERAL_LENGTH(result);
        return;
    }
    source = right && !(operation & RSQL_PROJECTION_LITERAL_LEFT)
        ? g_rsql_cursor.update_columns[result]
        : g_rsql_cursor.projection[result];
    column = source_column(source);
    row = shape_scalar_source_row(source, target);
    if (g_join_shape_rc != RSQL_OK) return;
    data = &row[column->offset];
    if (column->type.tag == RSQL_TYPE_TEXT) {
        g_join_shape_rc = shape_scalar_text_info(part, data);
        return;
    }
    if (column->type.tag != RSQL_TYPE_CHAR) {
        g_join_shape_rc = RSQL_ERR_UNSUPPORTED_SQL;
        return;
    }
    part->length = column->type.parameter;
    while (part->length != 0u && data[part->length - 1u] == ' ') {
        --part->length;
    }
    if (!target) part->data = data;
    else if (!right) {
        memcpy(fixed_target, data, part->length);
        part->data = fixed_target;
    } else part->data = data;
}

static void shape_prepare_scalar_value(RsqlScalarCompareValue* value,
                                       rsql_u8 result, rsql_u8 target,
                                       rsql_u8* fixed_target) {
    rsql_u8 base = g_rsql_cursor.projection_aggregate[result] &
        RSQL_PROJECTION_OP_MASK;
    rsql_u16 start;
    rsql_u16 count;
    memset(value, 0, sizeof(*value));
    value->is_null = shape_scalar_null(result, target);
    if (g_join_shape_rc != RSQL_OK || value->is_null) return;
    value->part_count = base == RSQL_SCALAR_CONCAT ? 2u : 1u;
    shape_prepare_scalar_part(&value->parts[0], result, 0u, target,
        fixed_target);
    if (g_join_shape_rc == RSQL_OK && value->part_count > 1u) {
        shape_prepare_scalar_part(&value->parts[1], result, 1u, target,
            fixed_target);
    }
    if (g_join_shape_rc != RSQL_OK || base != RSQL_SCALAR_SUBSTR) return;
    start = shape_scalar_bound(result, 0u);
    count = shape_scalar_bound(result, 1u);
    if (start > value->parts[0].length) value->parts[0].length = 0u;
    else {
        value->parts[0].start = (rsql_u16)(start - 1u);
        value->parts[0].length = (rsql_u16)
            (value->parts[0].length - value->parts[0].start);
        if (count != 0xFFFFu && value->parts[0].length > count) {
            value->parts[0].length = count;
        }
    }
}

rsql_i8 rsql_shape_compare_scalar_c(void) {
    rsql_u8 result = g_shape_scalar_result;
    shape_prepare_scalar_value(RSQL_SCALAR_COMPARE_LEFT, result, 0u, 0);
    if (g_join_shape_rc == RSQL_OK) {
        shape_prepare_scalar_value(RSQL_SCALAR_COMPARE_RIGHT, result, 1u,
            g_shape_scalar_buffer);
    }
    if (g_join_shape_rc != RSQL_OK) return 0;
    g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_SCALAR;
    g_rsql_variable_compare_kind = result;
    g_join_shape_rc = rsql_query_variable_compare_owner(4u);
    return g_rsql_variable_compare_result;
}

static rsql_u8 shape_scalar_null(rsql_u8 result, rsql_u8 target) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    if (base == RSQL_SCALAR_STRING) return 0u;
    if (base == RSQL_SCALAR_LENGTH || base == RSQL_SCALAR_SUBSTR) {
        if (operation & RSQL_PROJECTION_LITERAL_LEFT) return 0u;
        return shape_scalar_source_null(
            g_rsql_cursor.projection[result], target);
    }
    if (operation & (RSQL_PROJECTION_LITERAL_LEFT |
                     RSQL_PROJECTION_LITERAL_RIGHT)) {
        return shape_scalar_source_null(
            g_rsql_cursor.projection[result], target);
    }
    return shape_scalar_source_null(g_rsql_cursor.projection[result], target) ||
        shape_scalar_source_null(g_rsql_cursor.update_columns[result], target);
}

static rsql_i8 shape_compare_pair(void) {
    rsql_i8 comparison;
    rsql_u8 source;
    rsql_u8 index;
    g_join_shape_rc = RSQL_OK;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        /* Projection bit 6 must remain distinct from source bit 7, which is
         * an ordinary inner-table column in this producer. */
        comparison = (source & RSQL_ORDER_PROJECTION)
            ? rsql_shape_compare_scalar(source & RSQL_ORDER_PROJECTION_MASK)
            : shape_compare_source(source);
        if (g_join_shape_rc != RSQL_OK) return 0;
        if (comparison != 0) {
            if (g_rsql_cursor.order_desc_mask & column_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            return comparison;
        }
    }
    if (g_rsql_cursor.row_id.page < g_join_shape_target_outer.page) return -1;
    if (g_rsql_cursor.row_id.page > g_join_shape_target_outer.page) return 1;
    if (g_rsql_cursor.row_id.slot < g_join_shape_target_outer.slot) return -1;
    if (g_rsql_cursor.row_id.slot > g_join_shape_target_outer.slot) return 1;
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) return 0;
    if (g_rsql_cursor.join_inner_null != g_join_shape_target_inner_null) {
        return g_rsql_cursor.join_inner_null ? -1 : 1;
    }
    if (g_rsql_cursor.join_inner_null) return 0;
    if (g_rsql_cursor.join_row_id.page < g_join_shape_target_inner.page) return -1;
    if (g_rsql_cursor.join_row_id.page > g_join_shape_target_inner.page) return 1;
    if (g_rsql_cursor.join_row_id.slot < g_join_shape_target_inner.slot) return -1;
    if (g_rsql_cursor.join_row_id.slot > g_join_shape_target_inner.slot) return 1;
    return 0;
}

static void shape_target_last(void) {
    g_join_shape_target_outer = g_rsql_cursor.update_next_row_id;
    g_join_shape_target_inner.page = g_rsql_cursor.index_page;
    g_join_shape_target_inner.slot = g_rsql_cursor.index_leaf_slot;
    g_join_shape_target_inner_null = g_join_shape_last_inner_null;
}

static void shape_target_best(void) {
    g_join_shape_target_outer = g_join_shape_best_outer;
    g_join_shape_target_inner = g_join_shape_best_inner;
    g_join_shape_target_inner_null = g_join_shape_best_inner_null;
}

static void shape_store_best(void) {
    g_join_shape_best_outer = g_rsql_cursor.row_id;
    g_join_shape_best_inner = g_rsql_cursor.join_row_id;
    g_join_shape_best_inner_null = g_rsql_cursor.join_inner_null;
    g_join_shape_have_best = 1u;
}

static void shape_restart_complex(void) {
    g_rsql_cursor.finished = 0u;
    g_rsql_cursor.positioned = 0u;
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) return;
    g_rsql_cursor.join_outer_started = 0u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    g_rsql_cursor.join_inner_null = 0u;
}

static rsql_u8 shape_complex_next(RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    do {
        if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
            g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) {
            rc = rsql_query_subquery_next_phase(request);
        } else if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE &&
                   g_rsql_cursor.mode == RSQL_SELECT_SCAN) {
            g_rsql_variable_compare_source =
                RSQL_VARIABLE_COMPARE_INDEXED_JOIN_NEXT;
            rc = rsql_query_variable_compare_owner(4u);
        } else {
            rc = rsql_query_join_next_phase(request);
        }
        if (rc != RSQL_QUERY_PHASE_PREDICATE) return rc;
        g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_PREDICATE;
        rc = rsql_query_variable_compare_owner(4u);
        if (rc != RSQL_OK) return rc;
        rc = rsql_query_join_predicate_phase(request);
    } while (rc == RSQL_QUERY_PHASE_PREDICATE);
    return rc;
}

static rsql_u8 shape_same_complex_projection(void) {
    rsql_u8 index;
    rsql_u8 source;
    for (index = 0u; index < g_rsql_cursor.result_column_count; ++index) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[index])) {
            if (rsql_shape_compare_scalar(index) != 0) return 0u;
        } else {
            source = g_rsql_cursor.projection[index];
            if (shape_compare_source(source) != 0) return 0u;
        }
        if (g_join_shape_rc != RSQL_OK) return 0u;
    }
    return 1u;
}

static rsql_u8 shape_is_duplicate_target(void) {
    if (g_rsql_cursor.row_id.page != g_join_shape_target_outer.page ||
        g_rsql_cursor.row_id.slot != g_join_shape_target_outer.slot) return 0u;
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) return 1u;
    if (g_rsql_cursor.join_inner_null != g_join_shape_target_inner_null) {
        return 0u;
    }
    if (g_rsql_cursor.join_inner_null) return 1u;
    return g_rsql_cursor.join_row_id.page == g_join_shape_target_inner.page &&
        g_rsql_cursor.join_row_id.slot == g_join_shape_target_inner.slot;
}

static rsql_u8 shape_complex_duplicate(RsqlCursorNextRequest* request) {
    g_join_shape_target_outer = g_rsql_cursor.row_id;
    g_join_shape_target_inner = g_rsql_cursor.join_row_id;
    g_join_shape_target_inner_null = g_rsql_cursor.join_inner_null;
    g_join_shape_duplicate = 0u;
    shape_restart_complex();
    for (;;) {
        g_join_shape_rc = shape_complex_next(request);
        if (g_join_shape_rc != RSQL_OK || !request->has_row) break;
        if (shape_is_duplicate_target()) break;
        if (!g_join_shape_duplicate && shape_same_complex_projection()) {
            g_join_shape_duplicate = 1u;
        }
        if (g_join_shape_rc != RSQL_OK) break;
    }
    if (g_join_shape_rc == RSQL_OK && !request->has_row) {
        g_join_shape_rc = RSQL_ERR_CORRUPT_STORAGE;
    }
    return g_join_shape_duplicate;
}

rsql_u8 __fastcall__ rsql_query_join_result_next_phase(
    RsqlCursorNextRequest* request) {
    rsql_i8 comparison;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
         g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE) ||
        (!g_rsql_cursor.distinct && g_rsql_cursor.order_count == 0u)) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.limit_present &&
        g_rsql_cursor.returned_rows >= g_rsql_cursor.limit) {
        g_rsql_cursor.finished = 1u;
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    for (;;) {
        g_join_shape_have_best = 0u;
        shape_restart_complex();
        for (;;) {
            g_join_shape_rc = shape_complex_next(request);
            if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
            if (!request->has_row) break;
            if (g_rsql_cursor.returned_rows != 0u ||
                g_rsql_cursor.skipped_rows != 0u) {
                shape_target_last();
                comparison = shape_compare_pair();
                if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
                if (comparison <= 0) continue;
            }
            if (g_rsql_cursor.distinct) {
                comparison = (rsql_i8)shape_complex_duplicate(request);
                if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
                if (comparison != 0) continue;
            }
            if (g_join_shape_have_best) {
                shape_target_best();
                comparison = shape_compare_pair();
                if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
                if (comparison >= 0) continue;
            }
            shape_store_best();
        }
        if (!g_join_shape_have_best) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            request->has_row = 0u;
            return RSQL_OK;
        }
        g_rsql_cursor.row_id = g_join_shape_best_outer;
        g_rsql_cursor.join_row_id = g_join_shape_best_inner;
        g_rsql_cursor.join_inner_null = g_join_shape_best_inner_null;
        g_join_shape_rc = raw_read(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
            g_rsql_cursor.row);
        if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
        if (g_rsql_cursor.join_type != RSQL_JOIN_NONE &&
            !g_rsql_cursor.join_inner_null) {
            g_join_shape_rc = raw_read(g_rsql_cursor.join_table_page,
                g_rsql_cursor.join_row_width, &g_rsql_cursor.join_row_id,
                g_rsql_cursor.scan_row);
            if (g_join_shape_rc != RSQL_OK) return g_join_shape_rc;
        }
        g_rsql_cursor.update_next_row_id = g_rsql_cursor.row_id;
        if (g_rsql_cursor.join_type != RSQL_JOIN_NONE) {
            g_rsql_cursor.index_page = g_rsql_cursor.join_row_id.page;
            g_rsql_cursor.index_leaf_slot = g_rsql_cursor.join_row_id.slot;
            g_join_shape_last_inner_null = g_rsql_cursor.join_inner_null;
        }
        g_rsql_cursor.finished = 0u;
        g_rsql_cursor.positioned = 1u;
        request->has_row = 1u;
        if (g_rsql_cursor.skipped_rows < g_rsql_cursor.offset) {
            ++g_rsql_cursor.skipped_rows;
            continue;
        }
        ++g_rsql_cursor.returned_rows;
        return RSQL_OK;
    }
}

rsql_u8 __fastcall__ rsql_query_subquery_next_phase(
    RsqlCursorNextRequest* request) {
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.positioned) {
        g_join_next_rc = raw_next(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
            &g_join_candidate);
    } else {
        g_join_next_rc = raw_first(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_candidate);
    }
    while (g_join_next_rc == RSQL_OK) {
        g_rsql_cursor.row_id.page = g_join_candidate.page;
        g_rsql_cursor.row_id.slot = g_join_candidate.slot;
        g_join_next_rc = raw_read(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_join_candidate,
            g_rsql_cursor.row);
        if (g_join_next_rc != RSQL_OK) return g_join_next_rc;
        g_subquery_rc = RSQL_OK;
        if (evaluate_program(0u, g_rsql_cursor.bool_program_count)) {
            if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
            g_rsql_cursor.positioned = 1u;
            request->has_row = 1u;
            return RSQL_OK;
        }
        if (g_subquery_rc != RSQL_OK) return g_subquery_rc;
        g_join_next_rc = raw_next(g_rsql_cursor.table_page,
            g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
            &g_join_candidate);
    }
    if (g_join_next_rc != RSQL_ERR_NOT_FOUND) return g_join_next_rc;
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}
#endif

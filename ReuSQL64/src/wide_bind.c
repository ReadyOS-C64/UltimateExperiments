#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"
#include "wide_internal.h"

#define WIDE_ORDER_AGGREGATE 0x20u
#define WIDE_ORDER_SCALAR    0x10u

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

static rsql_u8 same_name_part(const char* part, rsql_u8 length,
                              const char* value) {
    rsql_u8 index;
    if ((rsql_u8)strlen(value) != length) return 0u;
    for (index = 0u; index < length; ++index) {
        if (folded_name(part[index]) != folded_name(value[index])) return 0u;
    }
    return 1u;
}

static const RsqlColumnInfo* bind_source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static rsql_u8 find_bind_source_column(const char* column_name,
                                  const RsqlColumnInfo* columns,
                                  rsql_u8 count, rsql_u8 flag,
                                  rsql_u8* source_out) {
    rsql_u8 index;
    for (index = 0u; index < count; ++index) {
        if (same_name(column_name, columns[index].name)) {
            *source_out = (rsql_u8)(flag | index);
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 resolve_wide_column(const char* name, rsql_u8* source_out) {
    const char* dot = strchr(name, '.');
    const char* column_name = dot ? dot + 1 : name;
    const char* outer = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* middle = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    const char* inner = g_rsql_statement.subquery_table_alias[0]
        ? g_rsql_statement.subquery_table_alias :
          g_rsql_statement.subquery_table_name;
    rsql_u8 length;
    rsql_u8 source;
    rsql_u8 found = 0u;
    rsql_u8 result = 0u;
    if (dot) {
        length = (rsql_u8)(dot - name);
        if (same_name_part(name, length, outer)) {
            return find_bind_source_column(column_name, g_rsql_cursor.columns,
                g_rsql_cursor.source_column_count, 0u, source_out);
        }
        if (same_name_part(name, length, middle)) {
            return find_bind_source_column(column_name,
                g_rsql_cursor.join_columns,
                g_rsql_cursor.join_inner_column_count,
                RSQL_SOURCE_INNER, source_out);
        }
        if (same_name_part(name, length, inner)) {
            return find_bind_source_column(column_name, g_rsql_execution.columns,
                g_rsql_cursor.subquery_column_count,
                RSQL_SOURCE_SUBQUERY, source_out);
        }
        return RSQL_ERR_NOT_FOUND;
    }
    if (find_bind_source_column(column_name, g_rsql_cursor.columns,
            g_rsql_cursor.source_column_count, 0u, &source) == RSQL_OK) {
        found = 1u;
        result = source;
    }
    if (find_bind_source_column(column_name, g_rsql_cursor.join_columns,
            g_rsql_cursor.join_inner_column_count, RSQL_SOURCE_INNER,
            &source) == RSQL_OK) {
        if (found) return RSQL_ERR_TYPE_MISMATCH;
        found = 1u;
        result = source;
    }
    if (find_bind_source_column(column_name, g_rsql_execution.columns,
            g_rsql_cursor.subquery_column_count, RSQL_SOURCE_SUBQUERY,
            &source) == RSQL_OK) {
        if (found) return RSQL_ERR_TYPE_MISMATCH;
        found = 1u;
        result = source;
    }
    if (!found) return RSQL_ERR_NOT_FOUND;
    *source_out = result;
    return RSQL_OK;
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

static rsql_u8 fixed_source(const RsqlColumnInfo* column) {
    return column->type.tag != RSQL_TYPE_TEXT &&
           column->type.tag != RSQL_TYPE_BLOB;
}

static rsql_u8 grouped_source(rsql_u8 source) {
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        if (g_rsql_cursor.group_columns[index] == source) return 1u;
    }
    return 0u;
}

rsql_u8 __fastcall__ rsql_wide_bind_aggregate_scalar(rsql_u8 result) {
    const RsqlColumnInfo* column;
    rsql_u8 operation = g_rsql_statement.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u8 source;
    rsql_u8 rc;
    if (base == RSQL_SCALAR_STRING) {
        g_rsql_cursor.projection[result] = 0xFFu;
        return RSQL_OK;
    }
    if (!(operation & RSQL_PROJECTION_LITERAL_LEFT) ||
        base == RSQL_SCALAR_CONCAT) {
        rc = resolve_wide_column(g_rsql_statement.projections[result],
                                 &source);
        if (rc != RSQL_OK) return rc;
        column = bind_source_column(source);
        if ((rsql_u8)(column->type.tag - RSQL_TYPE_CHAR) > 1u) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.projection[result] = source;
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
            !grouped_source(source)) return RSQL_ERR_UNSUPPORTED_SQL;
    } else g_rsql_cursor.projection[result] = 0xFFu;
    if (base == RSQL_SCALAR_CONCAT &&
        !(operation & (RSQL_PROJECTION_LITERAL_LEFT |
                       RSQL_PROJECTION_LITERAL_RIGHT))) {
        rc = resolve_wide_column(g_rsql_statement.group_columns[result],
                                 &source);
        if (rc != RSQL_OK) return rc;
        if ((rsql_u8)(bind_source_column(source)->type.tag -
                      RSQL_TYPE_CHAR) > 1u) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.update_columns[result] = source;
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
            !grouped_source(source)) return RSQL_ERR_UNSUPPORTED_SQL;
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        g_rsql_cursor.aggregate_counts[result].bytes[0] =
            (rsql_u8)g_rsql_statement.enum_values[result];
        g_rsql_cursor.aggregate_counts[result].bytes[1] =
            (rsql_u8)(g_rsql_statement.enum_values[result] >> 8u);
        g_rsql_cursor.aggregate_counts[result].bytes[2] =
            (rsql_u8)g_rsql_statement.enum_values[
                RSQL_TABLE_COLUMNS_MAX + result];
        g_rsql_cursor.aggregate_counts[result].bytes[3] =
            (rsql_u8)(g_rsql_statement.enum_values[
                RSQL_TABLE_COLUMNS_MAX + result] >> 8u);
    }
    return RSQL_OK;
}

static rsql_u8 reference_types_ok(const RsqlColumnInfo* left,
                                  const RsqlColumnInfo* right) {
    if (!fixed_source(left) || !fixed_source(right)) return 0u;
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

static rsql_u8 bind_value(rsql_u8 op, rsql_u8 source,
                          RsqlParsedValue* value) {
    const RsqlColumnInfo* left = bind_source_column(source);
    const RsqlColumnInfo* right;
    rsql_u8 reference;
    rsql_u8 rc;
    if (value->kind == RSQL_VALUE_ENUM &&
        resolve_wide_column(value->string, &reference) == RSQL_OK) {
        if (op == RSQL_PRED_LIKE) return RSQL_ERR_TYPE_MISMATCH;
        right = bind_source_column(reference);
        if (!reference_types_ok(left, right)) return RSQL_ERR_TYPE_MISMATCH;
        value->kind = RSQL_VALUE_REFERENCE;
        value->integer.bytes[0] = reference;
        return RSQL_OK;
    }
    if (value->kind == RSQL_VALUE_ENUM) return RSQL_ERR_TYPE_MISMATCH;
    rc = rsql_query_resolve_float_value(left, value);
    if (rc != RSQL_OK) return rc;
    return literal_type_ok(op, left, value)
        ? RSQL_OK : RSQL_ERR_TYPE_MISMATCH;
}

static rsql_u8 stored_index_name_equal(const char* wanted,
                                       const rsql_u8* stored,
                                       rsql_u8 length) {
    rsql_u8 index;
    for (index = 0u; index < length; ++index) {
        if (!wanted[index] ||
            folded_name(wanted[index]) != folded_name((char)stored[index])) {
            return 0u;
        }
    }
    return wanted[length] == 0;
}

static rsql_u8 bind_index_source(RsqlWideIndexIterator* iterator,
                                 const char* name, rsql_u16 table_page) {
    rsql_u16 page;
    rsql_u8 length;
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(
        rsql_page_catalog_root()), g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (g_rsql_meta_page0[0] != 'R' || g_rsql_meta_page0[1] != 'C' ||
        g_rsql_meta_page0[2] != 'A' || g_rsql_meta_page0[3] != 'T' ||
        g_rsql_meta_page0[4] != RSQL_STORAGE_VERSION ||
        g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_rsql_meta_page0)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_ROOT_FIRST_INDEX]);
    while (page != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(page),
                           g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) return rc;
        length = g_rsql_meta_page0[RSQL_INDEX_NAME_LENGTH];
        if (g_rsql_meta_page0[0] != 'R' ||
            g_rsql_meta_page0[1] != 'I' ||
            g_rsql_meta_page0[2] != 'D' ||
            g_rsql_meta_page0[3] != 'X' ||
            g_rsql_meta_page0[4] != RSQL_STORAGE_VERSION ||
            length > RSQL_TABLE_NAME_MAX ||
            g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
                rsql_page_checksum(g_rsql_meta_page0)) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        if (!(g_rsql_meta_page0[RSQL_INDEX_FLAGS] &
                RSQL_INDEX_FLAG_DROPPING) &&
            stored_index_name_equal(name,
                &g_rsql_meta_page0[RSQL_INDEX_NAME], length)) {
            if (rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_TABLE]) !=
                table_page) return RSQL_ERR_TYPE_MISMATCH;
            iterator->head = rsql_get_u16(
                &g_rsql_meta_page0[RSQL_INDEX_LEAF_HEAD]);
            iterator->page = iterator->head;
            iterator->slot = 0u;
            return RSQL_OK;
        }
        page = rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 bind_wide_indexes(void) {
    rsql_u8 rc;
    RSQL_WIDE_OUTER_INDEX.head = RSQL_PAGE_NONE;
    RSQL_WIDE_MIDDLE_INDEX.head = RSQL_PAGE_NONE;
    RSQL_WIDE_INNER_INDEX.head = RSQL_PAGE_NONE;
    if (g_rsql_statement.using_index & 1u) {
        rc = bind_index_source(&RSQL_WIDE_OUTER_INDEX,
            g_rsql_statement.index_name, g_rsql_cursor.table_page);
        if (rc != RSQL_OK) return rc;
    }
    if (g_rsql_statement.using_index & 2u) {
        rc = bind_index_source(&RSQL_WIDE_MIDDLE_INDEX,
            RSQL_WIDE_MIDDLE_INDEX_NAME, g_rsql_cursor.join_table_page);
        if (rc != RSQL_OK) return rc;
    }
    if (g_rsql_statement.using_index & 4u) {
        rc = bind_index_source(&RSQL_WIDE_INNER_INDEX,
            RSQL_WIDE_INNER_INDEX_NAME, g_rsql_cursor.subquery_table_page);
        if (rc != RSQL_OK) return rc;
    }
    g_rsql_cursor.using_index = g_rsql_statement.using_index;
    return RSQL_OK;
}

rsql_u8 rsql_join_bind_indexes_admin_phase(void) {
    rsql_u8 rc;
    RSQL_JOIN_OUTER_INDEX.head = RSQL_PAGE_NONE;
    RSQL_JOIN_INNER_INDEX.head = RSQL_PAGE_NONE;
    if (g_rsql_statement.using_index & 1u) {
        rc = bind_index_source(&RSQL_JOIN_OUTER_INDEX,
            g_rsql_statement.index_name, g_rsql_cursor.table_page);
        if (rc != RSQL_OK) return rc;
    }
    if (g_rsql_statement.using_index & 2u) {
        rc = bind_index_source(&RSQL_JOIN_INNER_INDEX,
            RSQL_WIDE_MIDDLE_INDEX_NAME, g_rsql_cursor.join_table_page);
        if (rc != RSQL_OK) return rc;
    }
    g_rsql_cursor.using_index = g_rsql_statement.using_index;
    return RSQL_OK;
}

rsql_u8 rsql_wide_bind_admin_phase(void) {
    const char* outer = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* middle = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    const char* inner = g_rsql_statement.subquery_table_alias[0]
        ? g_rsql_statement.subquery_table_alias :
          g_rsql_statement.subquery_table_name;
    RsqlParsedColumn* private_predicate;
    RsqlParsedValue* value;
    rsql_u8 source;
    rsql_u8 reference;
    rsql_u8 aggregate;
    rsql_u8 result;
    rsql_u8 index;
    rsql_u8 rc;
    if (g_rsql_statement.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN ||
        same_name(outer, middle) || same_name(outer, inner) ||
        same_name(middle, inner)) return RSQL_ERR_TYPE_MISMATCH;
    if (g_rsql_statement.using_index > 1u &&
        g_rsql_statement.subquery_predicate_count > 6u) {
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    if (g_rsql_statement.subquery_compare_op == RSQL_JOIN_LEFT) {
        for (index = 0u; index < g_rsql_cursor.subquery_column_count;
             ++index) {
            g_rsql_execution.columns[index].type.flags |=
                RSQL_TYPE_FLAG_NULLABLE;
        }
    }
    g_rsql_cursor.group_count = g_rsql_statement.group_count;
    for (index = 0u; index < g_rsql_statement.group_count; ++index) {
        rc = resolve_wide_column(
            RSQL_AGGREGATE_GROUP_NAME(g_rsql_statement, index), &source);
        if (rc != RSQL_OK) return rc;
        if (!fixed_source(bind_source_column(source))) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        g_rsql_cursor.group_columns[index] = source;
    }
    if (g_rsql_statement.select_all) {
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        result = (rsql_u8)(g_rsql_cursor.source_column_count +
            g_rsql_cursor.join_inner_column_count +
            g_rsql_cursor.subquery_column_count);
        if (result > RSQL_TABLE_COLUMNS_MAX) return RSQL_ERR_UNSUPPORTED_SQL;
        g_rsql_cursor.result_column_count = result;
        result = 0u;
        for (source = 0u; source < g_rsql_cursor.source_column_count;
             ++source) {
            g_rsql_cursor.projection[result++] = source;
        }
        for (source = 0u; source < g_rsql_cursor.join_inner_column_count;
             ++source) {
            g_rsql_cursor.projection[result++] =
                (rsql_u8)(RSQL_SOURCE_INNER | source);
        }
        for (source = 0u; source < g_rsql_cursor.subquery_column_count;
             ++source) {
            g_rsql_cursor.projection[result++] =
                (rsql_u8)(RSQL_SOURCE_SUBQUERY | source);
        }
    } else {
        g_rsql_cursor.result_column_count =
            g_rsql_statement.projection_count;
        for (result = 0u; result < g_rsql_statement.projection_count;
             ++result) {
            aggregate = g_rsql_statement.projection_aggregate[result];
            g_rsql_cursor.projection_aggregate[result] = aggregate;
            if (RSQL_PROJECTION_IS_SCALAR(aggregate)) {
                rc = rsql_wide_bind_aggregate_scalar(result);
                if (rc != RSQL_OK) return rc;
                continue;
            }
            if (aggregate == RSQL_AGG_COUNT_STAR) {
                g_rsql_cursor.projection[result] = 0xFFu;
                continue;
            }
            rc = resolve_wide_column(g_rsql_statement.projections[result],
                                     &source);
            if (rc != RSQL_OK) return rc;
            if (!fixed_source(bind_source_column(source)) &&
                g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
            if ((aggregate == RSQL_AGG_SUM || aggregate == RSQL_AGG_AVG ||
                 aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) &&
                !aggregate_numeric(bind_source_column(source))) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
                aggregate == RSQL_AGG_NONE && !grouped_source(source)) {
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
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        rc = resolve_wide_column(g_rsql_statement.predicates[index].column,
                                 &source);
        if (rc != RSQL_OK) return rc;
        if (index < g_rsql_statement.join_predicate_count &&
            (source & RSQL_SOURCE_SUBQUERY)) return RSQL_ERR_NOT_FOUND;
        value = &g_rsql_statement.predicates[index].value;
        if (value->kind == RSQL_VALUE_ENUM &&
            resolve_wide_column(value->string, &reference) == RSQL_OK &&
            index < g_rsql_statement.join_predicate_count &&
            (reference & RSQL_SOURCE_SUBQUERY)) return RSQL_ERR_NOT_FOUND;
        rc = bind_value(g_rsql_statement.predicates[index].op,
                        source, value);
        if (rc != RSQL_OK) return rc;
        g_rsql_cursor.predicates[index].op =
            g_rsql_statement.predicates[index].op;
        g_rsql_cursor.predicates[index].column = source;
        memcpy(&g_rsql_cursor.predicates[index].value, value,
               sizeof(*value));
    }
    for (index = 0u; index < g_rsql_statement.subquery_predicate_count;
         ++index) {
        private_predicate = &g_rsql_statement.columns[index];
        if (private_predicate->type.tag == RSQL_PRED_SUBQUERY) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        rc = resolve_wide_column(private_predicate->name, &source);
        if (rc != RSQL_OK) return rc;
        rc = bind_value(private_predicate->type.tag, source,
                        &g_rsql_statement.values[index]);
        if (rc != RSQL_OK) return rc;
        private_predicate->type.parameter = source;
    }
    rc = rsql_wide_bind_variable_predicates();
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.where_present = g_rsql_statement.where_present;
    g_rsql_cursor.distinct = g_rsql_statement.distinct;
    g_rsql_cursor.order_count = g_rsql_statement.order_count;
    g_rsql_cursor.order_desc_mask = g_rsql_statement.order_desc_mask;
    for (index = 0u; index < g_rsql_statement.order_count; ++index) {
        if ((rsql_u8)g_rsql_statement.enum_members[index][0] ==
                RSQL_ORDER_PROJECTION_MARKER) {
            result = (rsql_u8)g_rsql_statement.enum_members[index][1];
            if (result >= g_rsql_cursor.result_column_count) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
                g_rsql_cursor.projection_aggregate[result] != RSQL_AGG_NONE) {
                source = (rsql_u8)(WIDE_ORDER_AGGREGATE | result);
            } else if (g_rsql_cursor.mode == RSQL_SELECT_SCAN &&
                RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[result])) {
                source = (rsql_u8)(WIDE_ORDER_SCALAR | result);
            } else {
                source = g_rsql_cursor.projection[result];
            }
        } else {
            rc = resolve_wide_column(g_rsql_statement.enum_members[index],
                                     &source);
            if (rc != RSQL_OK) return rc;
        }
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
            !(source & WIDE_ORDER_AGGREGATE) && !grouped_source(source)) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        for (result = 0u; result < index; ++result) {
            if ((g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE
                    ? RSQL_AGGREGATE_ORDER_COLUMNS[result]
                    : g_rsql_cursor.group_columns[result]) == source) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
        }
        if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
            RSQL_AGGREGATE_ORDER_COLUMNS[index] = source;
        } else g_rsql_cursor.group_columns[index] = source;
    }
    g_rsql_cursor.limit_present = g_rsql_statement.limit_present & 1u;
    g_rsql_cursor.limit = g_rsql_statement.limit;
    g_rsql_cursor.offset = g_rsql_statement.offset;
    g_rsql_cursor.update_scan_started = 0u;
    return bind_wide_indexes();
}

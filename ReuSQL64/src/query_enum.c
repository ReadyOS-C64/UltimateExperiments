#include <string.h>

#include "rsql_enum.h"
#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_query.h"

static const RsqlColumnInfo* g_insert_resolve_column;
static RsqlParsedValue* g_insert_resolve_value;

rsql_u8 rsql_query_resolve_enum_value(const RsqlColumnInfo* column,
                                      RsqlParsedValue* value) {
    RsqlEnumInfo info;
    rsql_u16 number;
    rsql_u8 width;
    rsql_u8 index;
    char* member;
    rsql_u8 rc;
    if (column->type.tag != RSQL_TYPE_ENUM8 &&
        column->type.tag != RSQL_TYPE_ENUM16) {
        return value->kind == RSQL_VALUE_ENUM
            ? RSQL_ERR_TYPE_MISMATCH : RSQL_OK;
    }
    if (value->kind == RSQL_VALUE_NULL) return RSQL_OK;
    width = column->type.tag == RSQL_TYPE_ENUM8 ? 1u : 2u;
    if (value->kind == RSQL_VALUE_INTEGER) {
        for (index = width; index < sizeof(value->integer.bytes); ++index) {
            if (value->integer.bytes[index] != 0u) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
        }
        return RSQL_OK;
    }
    if (value->kind != RSQL_VALUE_ENUM) return RSQL_ERR_TYPE_MISMATCH;
    member = value->string;
    while (*member && *member != '.') ++member;
    if (*member != '.') return RSQL_ERR_TYPE_MISMATCH;
    *member = 0;
    rc = rsql_enum_find(value->string, &info);
    *member++ = '.';
    if (rc != RSQL_OK) return rc;
    if (info.enum_id != column->type.auxiliary) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    rc = rsql_enum_member_value(info.enum_id, member, &number);
    if (rc != RSQL_OK) return rc;
    memset(value->integer.bytes, 0, sizeof(value->integer.bytes));
    value->integer.bytes[0] = (rsql_u8)number;
    value->integer.bytes[1] = (rsql_u8)(number >> 8u);
    value->kind = RSQL_VALUE_INTEGER;
    return RSQL_OK;
}

rsql_u8 rsql_query_resolve_insert_enums(void) {
    rsql_u8 index;
    rsql_u8 rc;
    g_insert_resolve_column = g_rsql_execution.columns;
    g_insert_resolve_value = g_rsql_statement.values;
    for (index = 0u; index < g_rsql_execution.column_count; ++index) {
        rc = rsql_query_resolve_enum_value(
            g_insert_resolve_column, g_insert_resolve_value);
        if (rc != RSQL_OK) return rc;
        rc = rsql_query_resolve_float_value(
            g_insert_resolve_column, g_insert_resolve_value);
        if (rc != RSQL_OK) return rc;
        ++g_insert_resolve_column;
        ++g_insert_resolve_value;
    }
    return RSQL_OK;
}

static rsql_u8 folded(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 same_name(const char* left, const char* right) {
    while (*left && *right) {
        if (folded(*left++) != folded(*right++)) return 0u;
    }
    return *left == 0 && *right == 0;
}

static rsql_u8 same_prefix(const char* value, rsql_u8 length,
                           const char* expected) {
    rsql_u8 index;
    if ((rsql_u8)strlen(expected) != length) return 0u;
    for (index = 0u; index < length; ++index) {
        if (folded(value[index]) != folded(expected[index])) return 0u;
    }
    return 1u;
}

static const RsqlColumnInfo* enum_source_column(
    const char* name_value, const char* qualifier,
    const RsqlColumnInfo* columns, rsql_u8 column_count) {
    const char* dot = strchr(name_value, '.');
    const char* column_name = dot ? dot + 1 : name_value;
    rsql_u8 index;
    if (dot && !same_prefix(name_value, (rsql_u8)(dot - name_value),
                            qualifier)) return 0;
    for (index = 0u; index < column_count; ++index) {
        if (same_name(column_name, columns[index].name)) {
            return &columns[index];
        }
    }
    return 0;
}

static const RsqlColumnInfo* join_enum_column(const char* name_value,
                                               rsql_u8* ambiguous) {
    const char* dot = strchr(name_value, '.');
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* join_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    const char* subquery_qualifier = g_rsql_statement.subquery_table_alias[0]
        ? g_rsql_statement.subquery_table_alias :
          g_rsql_statement.subquery_table_name;
    const RsqlColumnInfo* found = 0;
    const RsqlColumnInfo* candidate;
    *ambiguous = 0u;
    found = enum_source_column(name_value, outer_qualifier,
        g_rsql_cursor.columns, g_rsql_cursor.source_column_count);
    if (dot && found) return found;
    candidate = enum_source_column(name_value, join_qualifier,
        g_rsql_cursor.join_columns, g_rsql_cursor.join_inner_column_count);
    if (dot && candidate) return candidate;
    if (candidate) {
        if (found) *ambiguous = 1u;
        found = candidate;
    }
    if (g_rsql_statement.join_type != RSQL_JOIN_NONE &&
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE) {
        candidate = enum_source_column(name_value, subquery_qualifier,
            g_rsql_execution.columns, g_rsql_cursor.subquery_column_count);
        if (dot && candidate) return candidate;
        if (candidate) {
            if (found) *ambiguous = 1u;
            found = candidate;
        }
    }
    if (dot) return 0;
    if (*ambiguous) return 0;
    return found;
}

rsql_u8 rsql_query_resolve_join_enums(void) {
    const RsqlColumnInfo* column;
    const char* member_dot;
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    const char* subquery_qualifier = g_rsql_statement.subquery_table_alias[0]
        ? g_rsql_statement.subquery_table_alias :
          g_rsql_statement.subquery_table_name;
    rsql_u8 ambiguous;
    rsql_u8 prefix_length;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_statement.predicate_count; ++index) {
        if (g_rsql_statement.predicates[index].value.kind !=
            RSQL_VALUE_ENUM) continue;
        member_dot = strchr(g_rsql_statement.predicates[index].value.string,
                            '.');
        if (!member_dot) return RSQL_ERR_TYPE_MISMATCH;
        prefix_length = (rsql_u8)(member_dot -
            g_rsql_statement.predicates[index].value.string);
        /* A table-qualified RHS remains a column reference for executor bind. */
        if (same_prefix(g_rsql_statement.predicates[index].value.string,
                        prefix_length, outer_qualifier) ||
            same_prefix(g_rsql_statement.predicates[index].value.string,
                        prefix_length, inner_qualifier) ||
            same_prefix(g_rsql_statement.predicates[index].value.string,
                        prefix_length, subquery_qualifier)) continue;
        column = join_enum_column(
            g_rsql_statement.predicates[index].column, &ambiguous);
        if (ambiguous) return RSQL_ERR_TYPE_MISMATCH;
        if (!column) return RSQL_ERR_NOT_FOUND;
        rc = rsql_query_resolve_enum_value(
            column, &g_rsql_statement.predicates[index].value);
        if (rc != RSQL_OK) return rc;
    }
    for (index = 0u; index <
         g_rsql_statement.subquery_predicate_count; ++index) {
        if (g_rsql_statement.values[index].kind != RSQL_VALUE_ENUM) continue;
        member_dot = strchr(g_rsql_statement.values[index].string, '.');
        if (!member_dot) return RSQL_ERR_TYPE_MISMATCH;
        prefix_length = (rsql_u8)(member_dot -
            g_rsql_statement.values[index].string);
        if (same_prefix(g_rsql_statement.values[index].string,
                        prefix_length, outer_qualifier) ||
            same_prefix(g_rsql_statement.values[index].string,
                        prefix_length, inner_qualifier) ||
            same_prefix(g_rsql_statement.values[index].string,
                        prefix_length, subquery_qualifier)) continue;
        column = join_enum_column(
            g_rsql_statement.columns[index].name, &ambiguous);
        if (!column) return RSQL_ERR_TYPE_MISMATCH;
        rc = rsql_query_resolve_enum_value(
            column, &g_rsql_statement.values[index]);
        if (rc != RSQL_OK) return rc;
    }
    return RSQL_OK;
}

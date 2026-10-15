#include <string.h>

#include "rsql_errors.h"
#include "rsql_query.h"

static rsql_u8 folded(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 same_name(const char* left, const char* right) {
    while (*left && *right) {
        if (folded(*left++) != folded(*right++)) return 0u;
    }
    return *left == '\0' && *right == '\0';
}

static rsql_u8 qualifier_matches(const char* name, const char* qualifier) {
    const char* dot = strchr(name, '.');
    rsql_u8 length;
    rsql_u8 index;
    if (!dot) return 1u;
    length = (rsql_u8)(dot - name);
    if ((rsql_u8)strlen(qualifier) != length) return 0u;
    for (index = 0u; index < length; ++index) {
        if (folded(name[index]) != folded(qualifier[index])) return 0u;
    }
    return 1u;
}

static rsql_u8 resolve_one(const char* name, const char* qualifier,
                           const RsqlColumnInfo* columns, rsql_u8 count,
                           rsql_u8 flag, rsql_u8* source_out) {
    const char* dot = strchr(name, '.');
    const char* column = dot ? dot + 1 : name;
    rsql_u8 index;
    if (!qualifier_matches(name, qualifier)) return RSQL_ERR_NOT_FOUND;
    for (index = 0u; index < count; ++index) {
        if (same_name(column, columns[index].name)) {
            *source_out = (rsql_u8)(flag | index);
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static const char* source_qualifier(rsql_u8 source) {
    if (source == 0u) return g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    if (source == 1u) return g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias : g_rsql_statement.join_table_name;
    return g_rsql_statement.subquery_table_alias[0]
        ? g_rsql_statement.subquery_table_alias :
          g_rsql_statement.subquery_table_name;
}

static rsql_u8 resolve_source(const char* name, rsql_u8 order,
                              rsql_u8* source_out) {
    rsql_u8 rc;
    if (order == 0u) {
        rc = resolve_one(name, source_qualifier(1u),
            g_rsql_cursor.join_columns,
            g_rsql_cursor.join_inner_column_count, RSQL_SOURCE_INNER,
            source_out);
        if (rc == RSQL_OK) return rc;
        return resolve_one(name, source_qualifier(0u), g_rsql_cursor.columns,
            g_rsql_cursor.source_column_count, 0u, source_out);
    }
    rc = resolve_one(name, source_qualifier(2u), g_rsql_execution.columns,
        g_rsql_cursor.subquery_column_count, RSQL_SOURCE_SUBQUERY, source_out);
    if (rc == RSQL_OK) return rc;
    rc = resolve_one(name, source_qualifier(0u), g_rsql_cursor.columns,
        g_rsql_cursor.source_column_count, 0u, source_out);
    if (rc == RSQL_OK) return rc;
    return resolve_one(name, source_qualifier(1u),
        g_rsql_cursor.join_columns, g_rsql_cursor.join_inner_column_count,
        RSQL_SOURCE_INNER, source_out);
}

static const RsqlColumnInfo* source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static rsql_u8 compatible(const RsqlColumnInfo* left,
                          const RsqlColumnInfo* right) {
    if (left->type.tag == right->type.tag) {
        if (left->type.tag != RSQL_TYPE_ENUM8 &&
            left->type.tag != RSQL_TYPE_ENUM16) return 1u;
        return left->type.auxiliary == right->type.auxiliary;
    }
    return (left->type.tag >= RSQL_TYPE_I8 &&
            left->type.tag <= RSQL_TYPE_I64) &&
           (right->type.tag >= RSQL_TYPE_I8 &&
            right->type.tag <= RSQL_TYPE_I64);
}

rsql_u8 rsql_query_bind_nested_admin_phase(void) {
    RsqlParsedColumn* predicate;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_statement.nested_predicate_start; ++index) {
        predicate = &g_rsql_statement.columns[index];
        if (predicate->type.tag != RSQL_PRED_SUBQUERY) continue;
        if (predicate->type.flags == RSQL_SUBQUERY_EXISTS) return RSQL_OK;
        rc = resolve_source(predicate->name, 0u, &left);
        if (rc != RSQL_OK) return rc;
        rc = resolve_source(predicate->type_name, 1u, &right);
        if (rc != RSQL_OK) return rc;
        if (!compatible(source_column(left), source_column(right))) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        predicate->type.parameter = (rsql_u16)left |
            ((rsql_u16)right << 8u);
        return RSQL_OK;
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

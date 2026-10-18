#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_query.h"

/* CREATE INDEX has no live enum-member production. Its parsed enum-value
 * vector is stable scratch across metadata overlay calls and avoids five
 * resident bytes in the stack-constrained work region. */
#define INDEX_BIND_TABLE_PAGE (g_rsql_statement.enum_values[0])
#define INDEX_BIND_ROW_WIDTH (g_rsql_statement.enum_values[1])
#define INDEX_BIND_COLUMN_COUNT \
    (*(rsql_u8*)&g_rsql_statement.enum_values[2])

static rsql_u8 folded(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 same_name(const char* left, const char* right) {
    while (*left && *right) {
        if (folded(*left++) != folded(*right++)) return 0u;
    }
    return *left == 0u && *right == 0u;
}

rsql_u8 rsql_query_bind_create_index(void) {
    RsqlTableInfo table;
    rsql_u8 source;
    rsql_u8 requested;
    rsql_u8 prior;
    rsql_u8 rc;
    rc = rsql_table_find(g_rsql_statement.table_name, &table);
    if (rc != RSQL_OK) return rc;
    INDEX_BIND_TABLE_PAGE = table.table_page;
    INDEX_BIND_ROW_WIDTH = table.row_width;
    INDEX_BIND_COLUMN_COUNT = table.column_count;
    for (source = 0u; source < table.column_count; ++source) {
        rc = rsql_column_info(table.table_page, source,
                              &g_rsql_execution.columns[source]);
        if (rc != RSQL_OK) return rc;
    }
    /* Dynamic column destinations can reuse the scalar prefix calculation in
     * cc65. Publish authoritative table scalars only after all column calls. */
    g_rsql_execution.table_page = INDEX_BIND_TABLE_PAGE;
    g_rsql_execution.row_width = INDEX_BIND_ROW_WIDTH;
    g_rsql_execution.column_count = INDEX_BIND_COLUMN_COUNT;
    for (requested = 0u; requested < g_rsql_statement.column_count;
         ++requested) {
        for (source = 0u; source < table.column_count; ++source) {
            if (same_name(g_rsql_statement.columns[requested].name,
                          g_rsql_execution.columns[source].name)) break;
        }
        if (source == table.column_count) return RSQL_ERR_NOT_FOUND;
        for (prior = 0u; prior < requested; ++prior) {
            if (g_rsql_statement.values[prior].integer.bytes[0] == source) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
        }
        g_rsql_statement.values[requested].integer.bytes[0] = source;
    }
    return RSQL_OK;
}

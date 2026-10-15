#include "rsql_catalog.h"
#include "rsql_enum.h"
#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_query.h"

#define CREATE_ENUM_INFO (*(RsqlEnumInfo*)&g_rsql_execution.row[\
    sizeof(RsqlColumnDefinition) * RSQL_TABLE_COLUMNS_MAX])

rsql_u8 rsql_query_create_phase(void) {
    /* CREATE TABLE and CREATE TYPE are mutually exclusive. Reuse the idle
     * execution row as definition-vector scratch instead of placing both
     * arrays on cc65's small software stack. This phase-neutral coordinator
     * runs resident while the metadata overlay remains loaded. */
    RsqlColumnDefinition* columns =
        (RsqlColumnDefinition*)g_rsql_execution.row;
    RsqlEnumMemberDefinition* members =
        (RsqlEnumMemberDefinition*)g_rsql_execution.row;
    union {
        RsqlCreateTableRequest table;
        RsqlCreateEnumRequest enumeration;
    } request;
    rsql_u8 rc;
    rsql_u8 index;
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE) {
        for (index = 0u; index < g_rsql_statement.column_count; ++index) {
            columns[index].name = g_rsql_statement.columns[index].name;
            columns[index].type = g_rsql_statement.columns[index].type;
            if (columns[index].type.tag == 0u) {
                rc = rsql_enum_find(
                    g_rsql_statement.columns[index].type_name,
                    &CREATE_ENUM_INFO);
                if (rc != RSQL_OK) return rc;
                columns[index].type.tag = CREATE_ENUM_INFO.width == 1u
                    ? RSQL_TYPE_ENUM8 : RSQL_TYPE_ENUM16;
                columns[index].type.auxiliary = CREATE_ENUM_INFO.enum_id;
            }
        }
        request.table.name = g_rsql_statement.table_name;
        request.table.column_count = g_rsql_statement.column_count;
        request.table.columns = columns;
        request.table.flags = g_rsql_statement.enum_width
            ? RSQL_TABLE_FLAG_TEMPORARY : 0u;
        request.table.table_page = RSQL_PAGE_NONE;
        return rsql_table_create(&request.table);
    }
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_TABLE_AS) {
        request.table.name =
            g_rsql_statement.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN
            ? RSQL_WIDE_CTAS_NAME(g_rsql_statement)
            : g_rsql_statement.columns[0].name;
        request.table.column_count = g_rsql_execution.column_count;
        request.table.columns = columns;
        request.table.flags = RSQL_TABLE_FLAG_BUILDING |
            (g_rsql_statement.enum_width ? RSQL_TABLE_FLAG_TEMPORARY : 0u);
        request.table.table_page = RSQL_PAGE_NONE;
        rc = rsql_table_create(&request.table);
        if (rc == RSQL_OK) {
            g_rsql_execution.table_page = request.table.table_page;
            g_rsql_execution.row_width = g_rsql_statement.error_offset;
        }
        return rc;
    }
    if (g_rsql_statement.kind == RSQL_STMT_CREATE_ENUM) {
        for (index = 0u; index < g_rsql_statement.enum_member_count; ++index) {
            members[index].name = g_rsql_statement.enum_members[index];
            members[index].value = g_rsql_statement.enum_values[index];
        }
        request.enumeration.name = g_rsql_statement.table_name;
        request.enumeration.width = g_rsql_statement.enum_width;
        request.enumeration.member_count = g_rsql_statement.enum_member_count;
        request.enumeration.members = members;
        request.enumeration.enum_id = 0u;
        return rsql_enum_create(&request.enumeration);
    }
    return RSQL_ERR_UNSUPPORTED_SQL;
}

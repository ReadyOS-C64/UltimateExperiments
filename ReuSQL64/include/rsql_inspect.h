#ifndef RSQL_INSPECT_H
#define RSQL_INSPECT_H

#include "rsql_catalog.h"
#include "rsql_types.h"

typedef struct RsqlDatabaseInfo {
    RsqlI32 reu_pages;
    RsqlI32 database_capacity_pages;
    RsqlI32 database_used_pages;
    RsqlI32 database_free_pages;
    rsql_u16 table_count;
    rsql_u16 index_count;
    rsql_u16 type_count;
} RsqlDatabaseInfo;

typedef struct RsqlSchemaTableInfo {
    rsql_u16 table_page;
    rsql_u8 flags;
    rsql_u8 column_count;
    rsql_u16 row_width;
    RsqlI32 row_count;
    RsqlI32 row_pages;
    rsql_u8 name_length;
    char name[RSQL_TABLE_NAME_MAX + 1u];
} RsqlSchemaTableInfo;

typedef struct RsqlSchemaColumnInfo {
    RsqlTypeSpec type;
    rsql_u16 offset;
    rsql_u8 name_length;
    char name[RSQL_COLUMN_NAME_MAX + 1u];
} RsqlSchemaColumnInfo;

typedef struct RsqlSchemaIndexInfo {
    rsql_u16 index_page;
    rsql_u16 table_page;
    RsqlI32 entry_count;
    RsqlI32 leaf_pages;
    rsql_u8 key_width;
    rsql_u8 column_count;
    rsql_u8 columns[RSQL_TABLE_COLUMNS_MAX];
    rsql_u8 name_length;
    char name[RSQL_TABLE_NAME_MAX + 1u];
} RsqlSchemaIndexInfo;

typedef struct RsqlSchemaTypeInfo {
    rsql_u16 type_page;
    rsql_u16 type_id;
    rsql_u16 member_count;
    RsqlI32 member_pages;
    rsql_u8 width;
    rsql_u8 name_length;
    char name[RSQL_TABLE_NAME_MAX + 1u];
} RsqlSchemaTypeInfo;

typedef struct RsqlSchemaMemberInfo {
    rsql_u16 value;
    rsql_u8 name_length;
    char name[RSQL_COLUMN_NAME_MAX + 1u];
} RsqlSchemaMemberInfo;

#endif

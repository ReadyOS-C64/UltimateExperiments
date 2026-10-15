#ifndef RSQL_CATALOG_H
#define RSQL_CATALOG_H

#include "rsql_types.h"

#define RSQL_TABLE_NAME_MAX 24u
#define RSQL_COLUMN_NAME_MAX 15u
#define RSQL_TABLE_COLUMNS_MAX 8u

#define RSQL_TABLE_FLAG_TEMPORARY 0x01u
#define RSQL_TABLE_FLAG_DROPPING  0x02u
#define RSQL_TABLE_FLAG_BUILDING  0x04u

typedef struct RsqlColumnDefinition {
    const char* name;
    RsqlTypeSpec type;
} RsqlColumnDefinition;

typedef struct RsqlCreateTableRequest {
    const char* name;
    rsql_u8 column_count;
    const RsqlColumnDefinition* columns;
    rsql_u16 table_page;
    rsql_u8 flags;
} RsqlCreateTableRequest;

typedef struct RsqlTableInfo {
    rsql_u16 table_page;
    rsql_u16 row_width;
    rsql_u8 column_count;
    rsql_u8 name_length;
    char name[RSQL_TABLE_NAME_MAX + 1u];
} RsqlTableInfo;

typedef struct RsqlColumnInfo {
    RsqlTypeSpec type;
    rsql_u16 offset;
    rsql_u8 name_length;
    char name[RSQL_COLUMN_NAME_MAX + 1u];
} RsqlColumnInfo;

rsql_u8 rsql_catalog_format(void);
rsql_u8 rsql_catalog_open(void);
rsql_u8 rsql_table_create(RsqlCreateTableRequest* request);
rsql_u8 rsql_table_find(const char* name, RsqlTableInfo* info_out);
rsql_u8 rsql_table_info(rsql_u16 table_page, RsqlTableInfo* info_out);
rsql_u8 rsql_column_info(rsql_u16 table_page, rsql_u8 column,
                         RsqlColumnInfo* info_out);

/* Storage-overlay services used by the variable-value heap. */
rsql_u8 rsql_catalog_blob_directory(rsql_u16* page_out);
rsql_u8 rsql_catalog_set_blob_directory(rsql_u16 page);
rsql_u8 rsql_catalog_reserve_blob_handle(unsigned long* handle_out);
rsql_u8 rsql_catalog_enum_state(rsql_u16* first_page_out,
                                rsql_u16* next_id_out);
rsql_u8 rsql_catalog_link_enum(rsql_u16 enum_page, rsql_u16 next_id);

#endif

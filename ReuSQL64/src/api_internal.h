#ifndef RSQL_API_INTERNAL_H
#define RSQL_API_INTERNAL_H

#include "rsql_types.h"

struct RsqlQueryOpenRequest;
struct RsqlCursorColumnRequest;
struct RsqlColumnInfo;
struct RsqlBlobHandle;
struct RsqlRowId;

extern struct RsqlCursorColumnRequest g_result_value;
extern struct RsqlColumnInfo g_result_destination;
extern struct RsqlBlobHandle g_result_handle;
extern struct RsqlRowId g_result_row_id;
extern rsql_u16 g_result_copy;
extern rsql_u16 g_result_table_page;

rsql_u8 rsql_api_error(rsql_u8 code, rsql_u16 offset);
rsql_u8 __fastcall__ rsql_query_open_parsed(
    struct RsqlQueryOpenRequest* request);
rsql_u8 rsql_query_variable_predicate_test(void);

#endif

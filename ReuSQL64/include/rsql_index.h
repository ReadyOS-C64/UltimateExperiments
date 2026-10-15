#ifndef RSQL_INDEX_H
#define RSQL_INDEX_H

#include "rsql_query.h"

#define RSQL_INDEX_KEY_MAX 96u

rsql_u8 rsql_index_create_phase(void);
rsql_u8 __fastcall__ rsql_index_rebuild_table(rsql_u16 table_page);
rsql_u8 rsql_index_scan_open(void);
rsql_u8 __fastcall__ rsql_index_scan_next(RsqlRowId* row_id_out);

#endif

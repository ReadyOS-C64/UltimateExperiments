#ifndef RSQL_ROW_H
#define RSQL_ROW_H

#include "rsql_types.h"

typedef struct RsqlRowId {
    rsql_u16 page;
    rsql_u8 slot;
} RsqlRowId;

rsql_u8 rsql_row_insert(rsql_u16 table_page, const void* row,
                        rsql_u16 row_length, RsqlRowId* row_id_out);
rsql_u8 rsql_row_read(rsql_u16 table_page, const RsqlRowId* row_id,
                      void* destination, rsql_u16 capacity);
rsql_u8 rsql_row_delete(rsql_u16 table_page, const RsqlRowId* row_id);
rsql_u8 rsql_row_update(rsql_u16 table_page, const RsqlRowId* row_id,
                        const void* row, rsql_u16 row_length);
/* Private CTAS continuation. The resident coordinator has populated its
 * bounded request globals before loading the row sidecar. */
rsql_u8 rsql_ctas_patch_phase(void);
rsql_u8 rsql_row_first(rsql_u16 table_page, RsqlRowId* row_id_out);
rsql_u8 rsql_row_next(rsql_u16 table_page, const RsqlRowId* current,
                      RsqlRowId* row_id_out);

#endif

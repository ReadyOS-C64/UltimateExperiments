#ifndef RSQL_WIDE_INTERNAL_H
#define RSQL_WIDE_INTERNAL_H

#include "rsql_query.h"

typedef struct WideTripleId {
    RsqlRowId outer;
    RsqlRowId middle;
    RsqlRowId inner;
} WideTripleId;

typedef struct WideScalarState {
    const WideTripleId* left;
    const WideTripleId* right;
    rsql_i8* comparison;
    rsql_u8 result;
    rsql_u8* buffer;
    rsql_u8 left_null;
    rsql_u16 left_length;
    rsql_u8 fixed_null;
    rsql_u8 fixed_part_count;
    const rsql_u8* fixed_data[2];
    rsql_u16 fixed_length[2];
    rsql_u8 fixed_text_mask;
    rsql_u16 fixed_first_page[2];
    rsql_u16 fixed_start[2];
} WideScalarState;

typedef struct RsqlWideIndexIterator {
    rsql_u16 head;
    rsql_u16 page;
    rsql_u8 slot;
} RsqlWideIndexIterator;

#define RSQL_WIDE_OUTER_INDEX \
    (*(RsqlWideIndexIterator*)&g_rsql_statement.enum_members[0][0])
#define RSQL_WIDE_MIDDLE_INDEX \
    (*(RsqlWideIndexIterator*)&g_rsql_statement.enum_members[0][5])
#define RSQL_WIDE_INNER_INDEX \
    (*(RsqlWideIndexIterator*)&g_rsql_statement.enum_members[0][10])
#define RSQL_JOIN_OUTER_INDEX \
    (*(RsqlWideIndexIterator*)&g_rsql_join_index_state[0])
#define RSQL_JOIN_INNER_INDEX \
    (*(RsqlWideIndexIterator*)&g_rsql_join_index_state[5])
#define RSQL_WIDE_MIDDLE_INDEX_NAME \
    ((const char*)g_rsql_statement.columns[6].type_name)
#define RSQL_WIDE_INNER_INDEX_NAME \
    ((const char*)g_rsql_statement.columns[7].type_name)

/* Binding has copied scalar bounds and all executable predicate state into
 * the cursor before wide replay begins. The otherwise-idle parsed enum-value
 * vector provides 32 bytes of phase-local state without growing work BSS. */
#define RSQL_WIDE_SCALAR_STATE \
    (*(WideScalarState*)&g_rsql_statement.enum_values[0])

/* Wide scalar replay owns the resident variable-comparison bridge while these
 * fields are live. Reuse its four-byte handle scratch rather than extending
 * persistent BSS into the fixed C stack. */
#define RSQL_WIDE_SCALAR_OFFSET \
    (*(rsql_u16*)&g_rsql_variable_compare_left[0])
#define RSQL_WIDE_SCALAR_PHASE (g_rsql_variable_compare_left[2])
#define RSQL_WIDE_SCALAR_MORE (g_rsql_variable_compare_left[3])

const RsqlColumnInfo* source_column(rsql_u8 source);
const rsql_u8* source_row(rsql_u8 source);
rsql_u8 source_null(rsql_u8 source);
rsql_u8 load_triple(const WideTripleId* triple);
rsql_u8 rsql_wide_compare_scalar(const WideTripleId* left,
                                 const WideTripleId* right,
                                 rsql_u8 result,
                                 rsql_i8* comparison_out);
rsql_u8 rsql_wide_bind_variable_predicates(void);
rsql_u8 rsql_wide_bind_admin_phase(void);
rsql_u8 __fastcall__ rsql_wide_bind_aggregate_scalar(rsql_u8 result);
rsql_u8 rsql_join_bind_indexes_admin_phase(void);

#endif

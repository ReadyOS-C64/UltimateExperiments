#include "rsql_errors.h"
#include "rsql_query.h"
#include "wide_internal.h"

rsql_u8 rsql_wide_scalar_compare_entry(void);

rsql_u8 rsql_wide_compare_scalar(const WideTripleId* left,
                                 const WideTripleId* right,
                                 rsql_u8 result,
                                 rsql_i8* comparison_out) {
    RSQL_WIDE_SCALAR_STATE.left = left;
    RSQL_WIDE_SCALAR_STATE.right = right;
    RSQL_WIDE_SCALAR_STATE.result = result;
    RSQL_WIDE_SCALAR_STATE.comparison = comparison_out;
    return rsql_wide_scalar_compare_entry();
}

rsql_u8 __fastcall__ rsql_wide_scalar_compare_c(rsql_u8* buffer) {
    rsql_u8 rc;
    RSQL_WIDE_SCALAR_STATE.buffer = buffer;
    RSQL_WIDE_SCALAR_OFFSET = 0u;
    g_rsql_variable_compare_kind = RSQL_WIDE_SCALAR_STATE.result;
    g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_WIDE_SCALAR;
    do {
        RSQL_WIDE_SCALAR_PHASE = 0u;
        RSQL_WIDE_SCALAR_MORE = 0u;
        rc = load_triple(RSQL_WIDE_SCALAR_STATE.left);
        if (rc == RSQL_OK) rc = rsql_query_variable_compare_owner(7u);
        if (rc == RSQL_OK) rc = load_triple(RSQL_WIDE_SCALAR_STATE.right);
        if (rc == RSQL_OK) rc = rsql_query_variable_compare_owner(7u);
        RSQL_WIDE_SCALAR_OFFSET =
            (rsql_u16)(RSQL_WIDE_SCALAR_OFFSET + 240u);
    } while (rc == RSQL_OK && RSQL_WIDE_SCALAR_MORE);
    *RSQL_WIDE_SCALAR_STATE.comparison = g_rsql_variable_compare_result;
    return rc;
}

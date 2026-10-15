#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"
#include "rsql_index.h"
#include "rsql_overlay.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"
#include "api_internal.h"

/* cc65 2.18 may reuse Y after rsql_query_close_phase() to address the local
 * return-code slot.  The phase clears a cursor larger than 255 bytes and its
 * memset path legitimately clobbers Y, so keep this wrapper state global. */
static RsqlQueryCloseRequest* g_query_close_request;
static rsql_u8 g_query_close_rc;
RsqlCursorNextRequest* g_cursor_next_request;

/* Resident because query sidecars reuse both cursor and execution-row scratch
 * while a shaped producer is replayed. */
rsql_u8 g_rsql_variable_predicate_mask;
rsql_u8 g_rsql_variable_predicate_source;
rsql_u8 g_rsql_variable_predicate_truth[RSQL_PREDICATES_MAX];
rsql_u8 g_rsql_variable_compare_source;
rsql_i8 g_rsql_variable_compare_result;
rsql_u8 g_rsql_variable_compare_kind;
rsql_u8 g_rsql_aggregate_scalar_bridge_mode;
rsql_u8 g_rsql_variable_compare_left[4];
rsql_u8 g_rsql_variable_compare_right[4];
rsql_u8 g_rsql_join_index_state[10];

void rsql_aggregate_reset_state(void) {
    rsql_u8 result;
    memset(g_rsql_cursor.aggregate_values, 0,
           sizeof(g_rsql_cursor.aggregate_values));
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        if (!RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[result])) {
            memset(&g_rsql_cursor.aggregate_counts[result], 0,
                   sizeof(g_rsql_cursor.aggregate_counts[result]));
        }
    }
    g_rsql_cursor.aggregate_nulls = 0u;
}

rsql_u8 rsql_query_variable_predicate_test(void) {
    rsql_u8 rc;
    do {
        rc = rsql_overlay_load(6u);
        if (rc == RSQL_OK) rc = rsql_query_variable_predicates_phase();
        if (rc == RSQL_OK) rc = rsql_overlay_load(1u);
        if (rc == RSQL_OK) rc = rsql_query_predicate_match_phase();
        if (g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE) return rc;
        if (rc != RSQL_OK && rc != RSQL_QUERY_PHASE_INDEX_SKIP) return rc;
        if (rc == RSQL_OK && g_rsql_cursor.update_variable &&
            g_rsql_cursor.update_scan_started > 1u) {
            rc = rsql_overlay_load(5u);
            if (rc == RSQL_OK) rc = rsql_query_variable_group_match_phase();
            if (rc != RSQL_OK && rc != RSQL_QUERY_PHASE_INDEX_SKIP) return rc;
            RSQL_VARIABLE_PREDICATE_SOURCE = rc == RSQL_OK;
            rc = rsql_overlay_load(1u);
            if (rc != RSQL_OK) return rc;
            rc = rsql_query_aggregate_predicate_phase(
                RSQL_VARIABLE_PREDICATE_SOURCE);
            continue;
        }
        rc = rsql_query_aggregate_predicate_phase(rc == RSQL_OK);
    } while (rc == RSQL_QUERY_PHASE_PREDICATE);
    return rc;
}

static rsql_u8 variable_predicate_match(void) {
    rsql_u8 rc = rsql_query_variable_predicate_test();
    g_cursor_next_request->has_row = 0u;
    if (rc == RSQL_OK) g_cursor_next_request->has_row = 1u;
    return rc;
}

static rsql_u8 cursor_next_unshaped(void) {
    rsql_u8 rc;
    if (g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN) {
        rc = rsql_overlay_load(7u);
        if (rc == RSQL_OK) {
            rc = rsql_query_wide_join_next_phase(g_cursor_next_request);
        }
        return rc;
    }
    if (g_rsql_cursor.join_type != RSQL_JOIN_NONE ||
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) {
        rc = rsql_overlay_load(g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE
            ? 6u : (g_rsql_cursor.join_type != RSQL_JOIN_NONE &&
                    g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE
                ? 7u : 4u));
        if (rc == RSQL_OK) {
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
                rc = rsql_query_join_aggregate_next_phase(
                    g_cursor_next_request);
            } else if (g_rsql_cursor.join_type != RSQL_JOIN_NONE &&
                       g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE) {
                rc = rsql_query_indexed_join_next_phase(
                    g_cursor_next_request);
            } else if (g_rsql_cursor.join_type != RSQL_JOIN_NONE) {
                rc = rsql_query_join_next_phase(g_cursor_next_request);
            } else rc = rsql_query_subquery_next_phase(g_cursor_next_request);
        }
        while (rc == RSQL_QUERY_PHASE_PREDICATE) {
            rc = rsql_overlay_load(6u);
            if (rc == RSQL_OK) rc = rsql_query_variable_predicates_phase();
            if (rc == RSQL_OK) rc = rsql_overlay_load(4u);
            if (rc == RSQL_OK) {
                rc = rsql_query_join_predicate_phase(g_cursor_next_request);
            }
        }
        return rc;
    }
    if (!g_rsql_cursor.using_index ||
        g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
        for (;;) {
            rc = rsql_overlay_load(1u);
            if (rc == RSQL_OK) {
                rc = rsql_query_cursor_next_phase(g_cursor_next_request);
            }
            if (rc == RSQL_QUERY_PHASE_PREDICATE) {
                rc = variable_predicate_match();
                if (rc == RSQL_QUERY_PHASE_INDEX_SKIP) continue;
            }
            return rc;
        }
    }
    g_cursor_next_request->has_row = 0u;
    while (!g_rsql_cursor.finished) {
        rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) rc = rsql_index_scan_next(&g_rsql_cursor.row_id);
        if (rc == RSQL_ERR_NOT_FOUND) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        if (rc != RSQL_OK) return rc;
        rc = rsql_overlay_load(1u);
        if (rc == RSQL_OK) {
            rc = rsql_query_cursor_index_row_phase(g_cursor_next_request);
        }
        if (rc == RSQL_QUERY_PHASE_PREDICATE) {
            rc = variable_predicate_match();
        }
        if (rc == RSQL_QUERY_PHASE_INDEX_SKIP) continue;
        return rc;
    }
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_open_parsed(RsqlQueryOpenRequest* request) {
    rsql_u8 rc;
    if (!request) return RSQL_ERR_INVALID_ARGUMENT;
    if (g_rsql_cursor.active) return RSQL_ERR_CURSOR_STATE;
    if (g_rsql_statement.kind != RSQL_STMT_SELECT &&
        g_rsql_statement.kind != RSQL_STMT_CREATE_TABLE_AS) {
        return RSQL_ERR_UNSUPPORTED_SQL;
    }
    rc = rsql_overlay_load(0u);
    if (rc == RSQL_OK) rc = rsql_query_bind_select(request);
    if (rc != RSQL_OK) return rc;
    if (g_rsql_statement.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN) {
        rc = rsql_overlay_load(7u);
        if (rc == RSQL_OK) rc = rsql_query_bind_wide_join_phase();
    } else if (g_rsql_statement.join_type != RSQL_JOIN_NONE ||
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE) {
        rc = rsql_overlay_load(4u);
        if (rc == RSQL_OK) rc = rsql_query_bind_complex_phase();
    } else {
        rc = rsql_overlay_load(3u);
        if (rc == RSQL_OK) rc = rsql_query_exec_prepare();
    }
    if (rc == RSQL_OK &&
        g_rsql_statement.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN &&
        (g_rsql_statement.distinct || g_rsql_statement.order_count != 0u ||
         g_rsql_statement.limit_present || g_rsql_statement.offset != 0u)) {
        rc = rsql_overlay_load(5u);
        if (rc == RSQL_OK) rc = rsql_query_bind_result_phase();
    }
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.active = 1u;
    request->cursor = 1u;
    request->column_count = g_rsql_cursor.result_column_count;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_open(RsqlQueryOpenRequest* request) {
    rsql_u8 rc;
    if (!request || !request->sql || request->sql_length == 0u) {
        return rsql_api_error(RSQL_ERR_INVALID_ARGUMENT, 0u);
    }
    rc = rsql_overlay_load(2u);
    if (rc == RSQL_OK) rc = rsql_query_parse(request->sql, request->sql_length);
    if (rc == RSQL_OK) rc = rsql_query_open_parsed(request);
    return rsql_api_error(rc, rc == RSQL_ERR_SYNTAX
        ? g_rsql_statement.error_offset : 0u);
}

rsql_u8 __fastcall__ rsql_cursor_next(RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    g_cursor_next_request = request;
    if (g_rsql_cursor.distinct || g_rsql_cursor.order_count != 0u) {
        rc = rsql_query_result_next_dispatch(g_cursor_next_request);
        return rsql_api_error(rc, 0u);
    }
    if (!request || request->cursor != 1u || !g_rsql_cursor.active) {
        return rsql_api_error(RSQL_ERR_CURSOR_STATE, 0u);
    }
    request->has_row = 0u;
    if (g_rsql_cursor.limit_present &&
        g_rsql_cursor.returned_rows >= g_rsql_cursor.limit) {
        g_rsql_cursor.finished = 1u;
        g_rsql_cursor.positioned = 0u;
        return rsql_api_error(RSQL_OK, 0u);
    }
    for (;;) {
        rc = cursor_next_unshaped();
        if (rc != RSQL_OK) return rsql_api_error(rc, 0u);
        if (!g_cursor_next_request->has_row) return rsql_api_error(RSQL_OK, 0u);
        if (g_rsql_cursor.skipped_rows < g_rsql_cursor.offset) {
            ++g_rsql_cursor.skipped_rows;
            continue;
        }
        ++g_rsql_cursor.returned_rows;
        return rsql_api_error(RSQL_OK, 0u);
    }
}

rsql_u8 __fastcall__ rsql_value_read(RsqlValueReadRequest* request) {
    rsql_u8 rc = rsql_overlay_load(1u);
    if (rc == RSQL_OK) rc = rsql_query_value_read_phase(request);
    if (rc == RSQL_QUERY_PHASE_SCALAR) {
        rc = rsql_overlay_load(5u);
        if (rc == RSQL_OK) rc = rsql_query_scalar_read_phase(request);
    }
    if (rc == RSQL_QUERY_PHASE_VARIABLE) {
        rc = rsql_overlay_load(0u);
        if (rc == RSQL_OK) rc = rsql_query_variable_read_phase(request);
    }
    return rsql_api_error(rc, 0u);
}

rsql_u8 __fastcall__ rsql_query_close(RsqlQueryCloseRequest* request) {
    g_query_close_request = request;
    g_query_close_rc = rsql_overlay_load(1u);
    if (g_query_close_rc == RSQL_OK) {
        g_query_close_rc = rsql_query_close_phase(g_query_close_request);
    }
    return rsql_api_error(g_query_close_rc, 0u);
}

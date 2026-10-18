#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_index.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define SQL_FALSE 0u
#define SQL_TRUE 1u
#define SQL_UNKNOWN 2u

extern const rsql_u8* g_scalar_concat_left;
extern const rsql_u8* g_scalar_concat_right;
extern rsql_u16 g_scalar_concat_left_length;
extern rsql_u16 g_scalar_concat_right_length;
extern rsql_u8 g_scalar_concat_text_mask;

static rsql_u16 g_sort_scan_page;
static rsql_u16 g_sort_best_page;
static rsql_u16 g_sort_prior_page;
static rsql_u16 g_sort_current_page;
static rsql_u16 g_sort_read_page;
static rsql_u8 g_sort_scan_slot;
static rsql_u8 g_sort_best_slot;
static rsql_u8 g_sort_prior_slot;
static rsql_u8 g_sort_current_slot;
static rsql_u8 g_sort_read_slot;
static rsql_u16 g_sort_page;
static rsql_u16 g_sort_offset;
static rsql_u8 g_sort_slot;
static rsql_u8 g_sort_rc;
static rsql_u8 g_sort_mask;
static rsql_u8 g_sort_read_target;
static rsql_u8 g_sort_found;
static rsql_u8 g_sort_duplicate;
static rsql_u8 g_sort_have_best;
static rsql_u8 g_sort_compare_source;
static rsql_u8 g_sort_compare_target;
static rsql_i8 g_sort_comparison;
static const rsql_u8* g_scalar_row;

static rsql_u8 sort_find_blob(const rsql_u8* handle, rsql_u8 kind,
                              rsql_u8 right);
static rsql_u8 sort_blob_left_byte(rsql_u16 offset, rsql_u8* value_out);

#define SORT_READ_SCAN 1u
#define SORT_READ_EXECUTION 2u
#define SORT_READ_CURSOR 3u
#define SORT_COMPARE_CURSOR 1u
#define SORT_COMPARE_BEST 2u
#define SORT_COMPARE_PRIOR 3u

#define SORT_BLOB_DIR_NEXT 6u
#define SORT_BLOB_DIR_ENTRIES 8u
#define SORT_BLOB_DIR_ENTRY_BYTES 20u
#define SORT_BLOB_DIR_ENTRY_COUNT 12u
#define SORT_BLOB_ENTRY_KIND 1u
#define SORT_BLOB_ENTRY_HANDLE 2u
#define SORT_BLOB_ENTRY_FIRST 6u
#define SORT_BLOB_ENTRY_LENGTH 8u
#define SORT_BLOB_PAGE_NEXT 6u
#define SORT_BLOB_PAGE_USED 8u
#define SORT_BLOB_PAGE_DATA 10u
#define SORT_BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - SORT_BLOB_PAGE_DATA)

typedef struct SortBlobState {
    rsql_u16 left_page;
    rsql_u16 left_first;
    rsql_u16 left_start;
    rsql_u16 right_page;
    rsql_u16 left_length;
    rsql_u16 right_length;
    rsql_u16 left_used;
    rsql_u16 right_used;
    rsql_u16 left_offset;
    rsql_u16 right_offset;
} SortBlobState;

/* Ordinary shaping does not use the correlated subquery schema cache. Reuse
 * its leading bytes while slot 5 owns execution instead of consuming the
 * last bytes below the fixed C stack. */
#define SORT_BLOB_STATE (*(SortBlobState*)g_rsql_execution.columns)
#define g_sort_blob_left_page SORT_BLOB_STATE.left_page
#define g_sort_blob_left_first SORT_BLOB_STATE.left_first
#define g_sort_blob_left_start SORT_BLOB_STATE.left_start
#define g_sort_blob_right_page SORT_BLOB_STATE.right_page
#define g_sort_blob_left_length SORT_BLOB_STATE.left_length
#define g_sort_blob_right_length SORT_BLOB_STATE.right_length
#define g_sort_blob_left_used SORT_BLOB_STATE.left_used
#define g_sort_blob_right_used SORT_BLOB_STATE.right_used
#define g_sort_blob_left_offset SORT_BLOB_STATE.left_offset
#define g_sort_blob_right_offset SORT_BLOB_STATE.right_offset

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ('a' - 'A'));
    }
    return value;
}

static rsql_u8 column_mask(rsql_u8 column) {
    rsql_u8 mask = 1u;
    if (column >= 8u) return 0u;
    while (column != 0u) {
        mask <<= 1u;
        --column;
    }
    return mask;
}

static rsql_u8 resolve_column(const char* name) {
    const char* qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    rsql_u8 column_start = 0u;
    rsql_u8 index;
    rsql_u8 name_index;
    rsql_u8 equal;
    while (name[column_start] && name[column_start] != '.') ++column_start;
    if (name[column_start] == '.') {
        for (index = 0u; index < column_start; ++index) {
            if (!qualifier[index] ||
                folded((rsql_u8)name[index]) !=
                folded((rsql_u8)qualifier[index])) return RSQL_ERR_NOT_FOUND;
        }
        if (qualifier[column_start]) return RSQL_ERR_NOT_FOUND;
        ++column_start;
    } else {
        column_start = 0u;
    }
    for (index = 0u; index < g_rsql_cursor.source_column_count; ++index) {
        name_index = 0u;
        equal = 1u;
        while (name[column_start + name_index] ||
               g_rsql_cursor.columns[index].name[name_index]) {
            if (folded((rsql_u8)name[column_start + name_index]) !=
                folded((rsql_u8)g_rsql_cursor.columns[index].name[name_index])) {
                equal = 0u;
                break;
            }
            ++name_index;
        }
        if (equal) {
            g_sort_compare_source = index;
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u16 value_width(const RsqlTypeSpec* type) {
    switch (type->tag) {
        case RSQL_TYPE_BOOLEAN:
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8: return 1u;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_FIXED8_8:
        case RSQL_TYPE_ENUM16: return 2u;
        case RSQL_TYPE_I32:
        case RSQL_TYPE_TEXT:
        case RSQL_TYPE_BLOB: return 4u;
        case RSQL_TYPE_FLOAT5: return 5u;
        case RSQL_TYPE_I64: return 8u;
        case RSQL_TYPE_CHAR: return type->parameter;
    }
    return 0u;
}

static rsql_u8 scalar_same_name(const char* left, const char* right) {
    while (*left || *right) {
        if (folded((rsql_u8)*left) != folded((rsql_u8)*right)) return 0u;
        ++left;
        ++right;
    }
    return 1u;
}

static rsql_u8 scalar_same_qualifier(const char* name, rsql_u8 length,
                                     const char* qualifier) {
    rsql_u8 index;
    for (index = 0u; index < length; ++index) {
        if (!qualifier[index] ||
            folded((rsql_u8)name[index]) !=
            folded((rsql_u8)qualifier[index])) return 0u;
    }
    return qualifier[length] == '\0';
}

static rsql_u8 scalar_find_source(const char* name,
                                  const RsqlColumnInfo* columns,
                                  rsql_u8 count, rsql_u8 source_flag,
                                  rsql_u8* source_out) {
    rsql_u8 index;
    for (index = 0u; index < count; ++index) {
        if (scalar_same_name(name, columns[index].name)) {
            *source_out = (rsql_u8)(source_flag | index);
            return RSQL_OK;
        }
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 scalar_resolve_source(const char* name,
                                     rsql_u8* source_out) {
    const char* outer_qualifier = g_rsql_statement.table_alias[0]
        ? g_rsql_statement.table_alias : g_rsql_statement.table_name;
    const char* inner_qualifier = g_rsql_statement.join_table_alias[0]
        ? g_rsql_statement.join_table_alias :
          g_rsql_statement.join_table_name;
    rsql_u8 dot = 0u;
    rsql_u8 outer_rc;
    rsql_u8 inner_rc;
    rsql_u8 outer_source;
    rsql_u8 inner_source;
    while (name[dot] && name[dot] != '.') ++dot;
    if (name[dot] == '.') {
        if (scalar_same_qualifier(name, dot, outer_qualifier)) {
            return scalar_find_source(&name[dot + 1u],
                g_rsql_cursor.columns, g_rsql_cursor.source_column_count,
                0u, source_out);
        }
        if (g_rsql_cursor.join_type != RSQL_JOIN_NONE &&
            scalar_same_qualifier(name, dot, inner_qualifier)) {
            return scalar_find_source(&name[dot + 1u],
                g_rsql_cursor.join_columns,
                g_rsql_cursor.join_inner_column_count,
                RSQL_SOURCE_INNER, source_out);
        }
        return RSQL_ERR_NOT_FOUND;
    }
    outer_rc = scalar_find_source(name, g_rsql_cursor.columns,
        g_rsql_cursor.source_column_count, 0u, &outer_source);
    if (g_rsql_cursor.join_type == RSQL_JOIN_NONE) {
        if (outer_rc == RSQL_OK) *source_out = outer_source;
        return outer_rc;
    }
    inner_rc = scalar_find_source(name, g_rsql_cursor.join_columns,
        g_rsql_cursor.join_inner_column_count, RSQL_SOURCE_INNER,
        &inner_source);
    if (outer_rc == RSQL_OK && inner_rc == RSQL_OK) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    if (outer_rc == RSQL_OK) {
        *source_out = outer_source;
        return RSQL_OK;
    }
    if (inner_rc == RSQL_OK) {
        *source_out = inner_source;
        return RSQL_OK;
    }
    return RSQL_ERR_NOT_FOUND;
}

static const RsqlColumnInfo* scalar_source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static rsql_u8 aggregate_grouped_source(rsql_u8 source) {
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        if (g_rsql_cursor.group_columns[index] == source) return 1u;
    }
    return 0u;
}

static rsql_u8 aggregate_distinct_redundant(void) {
    rsql_u8 group;
    rsql_u8 result;
    rsql_u8 found;
    for (group = 0u; group < g_rsql_cursor.group_count; ++group) {
        found = 0u;
        for (result = 0u; result < g_rsql_cursor.result_column_count;
             ++result) {
            if (g_rsql_cursor.projection_aggregate[result] == RSQL_AGG_NONE &&
                g_rsql_cursor.projection[result] ==
                    g_rsql_cursor.group_columns[group]) {
                found = 1u;
                break;
            }
        }
        if (!found) return 0u;
    }
    return 1u;
}

static rsql_u8 bind_scalar_projection(rsql_u8 result) {
    const RsqlColumnInfo* column;
    rsql_u8 operation = g_rsql_statement.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u8 source;
    rsql_u8 rc;
    if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
        g_rsql_aggregate_scalar_bridge_mode =
            RSQL_AGGREGATE_SCALAR_BRIDGE_BIND;
        g_rsql_variable_compare_source =
            RSQL_VARIABLE_COMPARE_AGGREGATE_SCALAR;
        g_rsql_variable_compare_kind = result;
        rc = rsql_query_variable_compare_owner(5u);
        g_rsql_aggregate_scalar_bridge_mode =
            RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE;
        g_rsql_variable_compare_source = 0u;
        return rc;
    }
    if (base == RSQL_SCALAR_STRING) {
        g_rsql_cursor.projection[result] = 0xFFu;
        return RSQL_OK;
    }
    if (!(operation & RSQL_PROJECTION_LITERAL_LEFT)) {
        rc = scalar_resolve_source(g_rsql_statement.projections[result],
                                   &source);
        if (rc != RSQL_OK) return rc;
        column = scalar_source_column(source);
        if (column->type.tag != RSQL_TYPE_CHAR &&
            column->type.tag != RSQL_TYPE_TEXT) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.projection[result] = source;
    } else if (base == RSQL_SCALAR_CONCAT) {
        rc = scalar_resolve_source(g_rsql_statement.projections[result],
                                   &source);
        if (rc != RSQL_OK) return rc;
        column = scalar_source_column(source);
        if (column->type.tag != RSQL_TYPE_CHAR &&
            column->type.tag != RSQL_TYPE_TEXT) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.projection[result] = source;
    } else {
        g_rsql_cursor.projection[result] = 0xFFu;
    }
    if (base == RSQL_SCALAR_CONCAT &&
        !(operation & (RSQL_PROJECTION_LITERAL_LEFT |
                       RSQL_PROJECTION_LITERAL_RIGHT))) {
        rc = scalar_resolve_source(g_rsql_statement.group_columns[result],
                                   &source);
        if (rc != RSQL_OK) return rc;
        column = scalar_source_column(source);
        if (column->type.tag != RSQL_TYPE_CHAR &&
            column->type.tag != RSQL_TYPE_TEXT) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        g_rsql_cursor.update_columns[result] = source;
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        g_rsql_cursor.aggregate_counts[result].bytes[0] =
            (rsql_u8)g_rsql_statement.enum_values[result];
        g_rsql_cursor.aggregate_counts[result].bytes[1] =
            (rsql_u8)(g_rsql_statement.enum_values[result] >> 8u);
        g_rsql_cursor.aggregate_counts[result].bytes[2] =
            (rsql_u8)g_rsql_statement.enum_values[
                RSQL_TABLE_COLUMNS_MAX + result];
        g_rsql_cursor.aggregate_counts[result].bytes[3] =
            (rsql_u8)(g_rsql_statement.enum_values[
                RSQL_TABLE_COLUMNS_MAX + result] >> 8u);
    }
    return RSQL_OK;
}

static rsql_u8 scalar_projection_variable(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u8 source = g_rsql_cursor.projection[result];
    if (base == RSQL_SCALAR_STRING || source == 0xFFu) return 0u;
    if (scalar_source_column(source)->type.tag == RSQL_TYPE_TEXT) return 1u;
    return base == RSQL_SCALAR_CONCAT &&
        !(operation & (RSQL_PROJECTION_LITERAL_LEFT |
                       RSQL_PROJECTION_LITERAL_RIGHT)) &&
        scalar_source_column(g_rsql_cursor.update_columns[result])->type.tag ==
            RSQL_TYPE_TEXT;
}

rsql_u8 rsql_query_bind_result_phase(void) {
    rsql_u8 source;
    rsql_u8 prior;
    rsql_u8 index;
    rsql_u8 rc;
    g_rsql_cursor.distinct = g_rsql_statement.distinct;
    g_rsql_cursor.order_count = g_rsql_statement.order_count;
    g_rsql_cursor.order_desc_mask = g_rsql_statement.order_desc_mask;
    g_rsql_cursor.limit_present =
        g_rsql_statement.limit_present & 1u;
    g_rsql_cursor.limit = g_rsql_statement.limit;
    g_rsql_cursor.offset = g_rsql_statement.offset;
    for (index = 0u; index < g_rsql_cursor.result_column_count; ++index) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[index])) {
            rc = bind_scalar_projection(index);
            if (rc != RSQL_OK) return rc;
        }
    }
    if (!g_rsql_cursor.distinct && g_rsql_cursor.order_count == 0u) {
        return RSQL_OK;
    }
    if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
        /* An ungrouped aggregate has one row. A grouped projection is already
         * distinct when it exposes every group key. Prove either case, then
         * remove the redundant runtime pass; omitted-key tuple elimination
         * still needs its own bounded comparison pass. */
        if (g_rsql_cursor.distinct && aggregate_distinct_redundant()) {
            g_rsql_cursor.distinct = 0u;
        }
        for (index = 0u; index < g_rsql_statement.order_count; ++index) {
            if ((rsql_u8)g_rsql_statement.enum_members[index][0] ==
                    RSQL_ORDER_PROJECTION_MARKER) {
                source = (rsql_u8)g_rsql_statement.enum_members[index][1];
                if (source >= g_rsql_cursor.result_column_count) {
                    return RSQL_ERR_CORRUPT_STORAGE;
                }
                if (g_rsql_cursor.projection_aggregate[source] !=
                        RSQL_AGG_NONE) {
                    source = (rsql_u8)(RSQL_ORDER_PROJECTION | source);
                } else {
                    source = g_rsql_cursor.projection[source];
                    if (!aggregate_grouped_source(source)) {
                        return RSQL_ERR_UNSUPPORTED_SQL;
                    }
                }
            } else {
                if (g_rsql_cursor.join_type != RSQL_JOIN_NONE) {
                    rc = scalar_resolve_source(
                        g_rsql_statement.enum_members[index], &source);
                } else {
                    rc = resolve_column(g_rsql_statement.enum_members[index]);
                    source = g_sort_compare_source;
                }
                if (rc != RSQL_OK) return rc;
                if (!aggregate_grouped_source(source)) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
            }
            for (prior = 0u; prior < index; ++prior) {
                if (RSQL_AGGREGATE_ORDER_COLUMNS[prior] == source) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
            }
            RSQL_AGGREGATE_ORDER_COLUMNS[index] = source;
        }
        return RSQL_OK;
    }
    for (index = 0u; index < g_rsql_statement.order_count; ++index) {
        if ((rsql_u8)g_rsql_statement.enum_members[index][0] ==
                RSQL_ORDER_PROJECTION_MARKER) {
            source = (rsql_u8)g_rsql_statement.enum_members[index][1];
            if (source >= g_rsql_cursor.result_column_count) {
                return RSQL_ERR_CORRUPT_STORAGE;
            }
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[source])) {
                source = (rsql_u8)(RSQL_ORDER_PROJECTION | source);
            } else {
                source = g_rsql_cursor.projection[source];
            }
        } else {
            if (g_rsql_cursor.join_type != RSQL_JOIN_NONE) {
                rc = scalar_resolve_source(
                    g_rsql_statement.enum_members[index], &source);
            } else {
                rc = resolve_column(g_rsql_statement.enum_members[index]);
                source = g_sort_compare_source;
            }
            if (rc != RSQL_OK) return rc;
        }
        for (prior = 0u; prior < index; ++prior) {
            if (g_rsql_cursor.group_columns[prior] == source) {
                return RSQL_ERR_UNSUPPORTED_SQL;
            }
        }
        g_rsql_cursor.group_columns[index] = source;
    }
    if (g_rsql_cursor.distinct) {
        for (index = 0u; index < g_rsql_cursor.result_column_count; ++index) {
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[index])) {
                continue;
            }
            source = g_rsql_cursor.projection[index];
        }
    }
    return RSQL_OK;
}

static const rsql_u8* scalar_source_bytes(rsql_u8 source) {
    const RsqlColumnInfo* column = scalar_source_column(source);
    const rsql_u8* row;
    if (source & RSQL_SOURCE_SUBQUERY) row = g_rsql_execution.row;
    else if (source & RSQL_SOURCE_INNER) row = g_rsql_cursor.scan_row;
    else {
        row = g_scalar_row;
        if (!row) row = g_rsql_cursor.row;
    }
    return &row[column->offset];
}

static rsql_u8 scalar_source_null(rsql_u8 source) {
    const rsql_u8* row;
    rsql_u8 column = source & RSQL_SOURCE_COLUMN_MASK;
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    if (source & RSQL_SOURCE_SUBQUERY) row = g_rsql_execution.row;
    else if (source & RSQL_SOURCE_INNER) row = g_rsql_cursor.scan_row;
    else {
        row = g_scalar_row;
        if (!row) row = g_rsql_cursor.row;
    }
    return (row[0] & column_mask(column)) != 0u;
}

static rsql_u16 scalar_source_length(rsql_u8 source) {
    const RsqlColumnInfo* column = scalar_source_column(source);
    const rsql_u8* bytes = scalar_source_bytes(source);
    rsql_u16 length = column->type.parameter;
    while (length != 0u && bytes[length - 1u] == ' ') --length;
    return length;
}

void __fastcall__ rsql_query_scalar_variable_prepare(rsql_u8 result) {
    const RsqlColumnInfo* column;
    const rsql_u8* data;
    rsql_u8 operation;
    rsql_u8 source;
    rsql_u8 right;
    rsql_u8 mask = 0u;
    rsql_u16 length;
    operation = g_rsql_cursor.projection_aggregate[result];
    if ((operation & RSQL_PROJECTION_OP_MASK) != RSQL_SCALAR_CONCAT) {
        return;
    }
    /* Result shaping may leave a representative row in g_scalar_row. Public
     * column/read calls must always describe the cursor's current pair. */
    g_scalar_row = 0;
    for (right = 0u; right != 2u; ++right) {
        if ((!right && (operation & RSQL_PROJECTION_LITERAL_LEFT)) ||
            (right && (operation & RSQL_PROJECTION_LITERAL_RIGHT))) {
            data = RSQL_SCALAR_LITERAL_DATA(result);
            length = RSQL_SCALAR_LITERAL_LENGTH(result);
        } else {
            if (!right || (operation & RSQL_PROJECTION_LITERAL_LEFT)) {
                source = g_rsql_cursor.projection[result];
            } else source = g_rsql_cursor.update_columns[result];
            if (scalar_source_null(source)) {
                mask = 0x80u;
                break;
            }
            data = scalar_source_bytes(source);
            column = scalar_source_column(source);
            if (column->type.tag == RSQL_TYPE_TEXT) {
                length = 0u;
                mask |= right ? 2u : 1u;
            } else length = scalar_source_length(source);
        }
        if (right) {
            g_scalar_concat_right = data;
            g_scalar_concat_right_length = length;
        } else {
            g_scalar_concat_left = data;
            g_scalar_concat_left_length = length;
        }
    }
    g_scalar_concat_text_mask = mask;
}

static rsql_u16 scalar_u16(const rsql_u8* bytes) {
    return (rsql_u16)bytes[0] | ((rsql_u16)bytes[1] << 8u);
}

static rsql_u8 scalar_is_null(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    if (base == RSQL_SCALAR_STRING) return 0u;
    if (base == RSQL_SCALAR_LENGTH || base == RSQL_SCALAR_SUBSTR) {
        if (operation & RSQL_PROJECTION_LITERAL_LEFT) return 0u;
        return scalar_source_null(g_rsql_cursor.projection[result]);
    }
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        return scalar_source_null(g_rsql_cursor.projection[result]);
    }
    if (operation & RSQL_PROJECTION_LITERAL_RIGHT) {
        return scalar_source_null(g_rsql_cursor.projection[result]);
    }
    return scalar_source_null(g_rsql_cursor.projection[result]) ||
        scalar_source_null(g_rsql_cursor.update_columns[result]);
}

static rsql_u16 scalar_input_length(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        return RSQL_SCALAR_LITERAL_LENGTH(result);
    }
    return scalar_source_length(g_rsql_cursor.projection[result]);
}

static rsql_u16 scalar_result_length(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u16 length;
    rsql_u16 start;
    rsql_u16 count;
    if (base == RSQL_SCALAR_LENGTH) return 2u;
    if (base == RSQL_SCALAR_STRING) {
        return RSQL_SCALAR_LITERAL_LENGTH(result);
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        length = scalar_input_length(result);
        start = scalar_u16(g_rsql_cursor.aggregate_counts[result].bytes);
        count = scalar_u16(&g_rsql_cursor.aggregate_counts[result].bytes[2]);
        if (start > length) return 0u;
        length = (rsql_u16)(length - (start - 1u));
        if (count != 0xFFFFu && length > count) length = count;
        return length;
    }
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        return (rsql_u16)RSQL_SCALAR_LITERAL_LENGTH(result) +
            scalar_source_length(g_rsql_cursor.projection[result]);
    }
    if (operation & RSQL_PROJECTION_LITERAL_RIGHT) {
        return scalar_source_length(g_rsql_cursor.projection[result]) +
            RSQL_SCALAR_LITERAL_LENGTH(result);
    }
    return scalar_source_length(g_rsql_cursor.projection[result]) +
        scalar_source_length(g_rsql_cursor.update_columns[result]);
}

static rsql_u16 scalar_declared_length(rsql_u8 result) {
    const RsqlColumnInfo* column;
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    rsql_u16 left;
    rsql_u16 right;
    rsql_u16 start;
    rsql_u16 count;
    if (base == RSQL_SCALAR_STRING) {
        return RSQL_SCALAR_LITERAL_LENGTH(result);
    }
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        left = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        column = scalar_source_column(g_rsql_cursor.projection[result]);
        left = column->type.parameter;
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        start = scalar_u16(g_rsql_cursor.aggregate_counts[result].bytes);
        count = scalar_u16(&g_rsql_cursor.aggregate_counts[result].bytes[2]);
        if (start > left) return 0u;
        left = (rsql_u16)(left - (start - 1u));
        if (count != 0xFFFFu && left > count) left = count;
        return left;
    }
    if (base != RSQL_SCALAR_CONCAT) return left;
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        column = scalar_source_column(g_rsql_cursor.projection[result]);
        right = column->type.parameter;
    } else if (operation & RSQL_PROJECTION_LITERAL_RIGHT) {
        right = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        column = scalar_source_column(g_rsql_cursor.update_columns[result]);
        right = column->type.parameter;
    }
    return (rsql_u16)(left + right);
}

static rsql_u16 scalar_copy_part(const rsql_u8* source, rsql_u16 length,
                                 rsql_u16 offset, rsql_u8* destination,
                                 rsql_u16 capacity) {
    rsql_u16 available;
    if (offset >= length || capacity == 0u) return 0u;
    available = (rsql_u16)(length - offset);
    if (available > capacity) available = capacity;
    memcpy(destination, source + offset, available);
    return available;
}

static rsql_u16 scalar_copy(rsql_u8 result, rsql_u16 offset,
                            rsql_u8* destination, rsql_u16 capacity) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    const rsql_u8* left;
    const rsql_u8* right;
    rsql_u8 number[2];
    rsql_u16 left_length;
    rsql_u16 right_length;
    rsql_u16 start;
    rsql_u16 count;
    rsql_u16 copied;
    if (base == RSQL_SCALAR_LENGTH) {
        left_length = scalar_input_length(result);
        number[0] = (rsql_u8)left_length;
        number[1] = (rsql_u8)(left_length >> 8u);
        return scalar_copy_part(number, 2u, offset, destination, capacity);
    }
    if (base == RSQL_SCALAR_STRING) {
        return scalar_copy_part(RSQL_SCALAR_LITERAL_DATA(result),
            RSQL_SCALAR_LITERAL_LENGTH(result),
            offset, destination, capacity);
    }
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        left = RSQL_SCALAR_LITERAL_DATA(result);
        left_length = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        left = scalar_source_bytes(g_rsql_cursor.projection[result]);
        left_length = scalar_source_length(g_rsql_cursor.projection[result]);
    }
    if (base == RSQL_SCALAR_SUBSTR) {
        start = scalar_u16(g_rsql_cursor.aggregate_counts[result].bytes);
        count = scalar_result_length(result);
        if (start > left_length) return 0u;
        return scalar_copy_part(left + (start - 1u), count, offset,
                                destination, capacity);
    }
    if (operation & RSQL_PROJECTION_LITERAL_LEFT) {
        right = scalar_source_bytes(g_rsql_cursor.projection[result]);
        right_length = scalar_source_length(g_rsql_cursor.projection[result]);
    } else if (operation & RSQL_PROJECTION_LITERAL_RIGHT) {
        right = RSQL_SCALAR_LITERAL_DATA(result);
        right_length = RSQL_SCALAR_LITERAL_LENGTH(result);
    } else {
        right = scalar_source_bytes(g_rsql_cursor.update_columns[result]);
        right_length = scalar_source_length(
            g_rsql_cursor.update_columns[result]);
    }
    copied = scalar_copy_part(left, left_length, offset,
                              destination, capacity);
    if (copied == capacity) return copied;
    if (offset >= left_length) offset = (rsql_u16)(offset - left_length);
    else offset = 0u;
    copied += scalar_copy_part(right, right_length, offset,
                               destination + copied,
                               (rsql_u16)(capacity - copied));
    return copied;
}

static void prepare_scalar_part(RsqlScalarComparePart* part, rsql_u8 result,
                                rsql_u8 right) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 source;
    const RsqlColumnInfo* column;
    memset(part, 0, sizeof(*part));
    if ((!right && (operation & RSQL_PROJECTION_LITERAL_LEFT)) ||
        (right && (operation & RSQL_PROJECTION_LITERAL_RIGHT))) {
        part->data = RSQL_SCALAR_LITERAL_DATA(result);
        part->length = RSQL_SCALAR_LITERAL_LENGTH(result);
        return;
    }
    source = right && !(operation & RSQL_PROJECTION_LITERAL_LEFT)
        ? g_rsql_cursor.update_columns[result]
        : g_rsql_cursor.projection[result];
    column = scalar_source_column(source);
    part->data = scalar_source_bytes(source);
    if (column->type.tag == RSQL_TYPE_TEXT) {
        part->kind = 1u;
        g_sort_rc = sort_find_blob(part->data, RSQL_TYPE_TEXT, 0u);
        part->first_page = g_sort_blob_left_first;
        part->next_page = part->first_page;
        part->length = g_sort_blob_left_length;
    } else part->length = scalar_source_length(source);
}

static void prepare_scalar_value(RsqlScalarCompareValue* value,
                                 rsql_u8 result, const rsql_u8* row) {
    rsql_u8 base = g_rsql_cursor.projection_aggregate[result] &
        RSQL_PROJECTION_OP_MASK;
    rsql_u16 start;
    rsql_u16 count;
    memset(value, 0, sizeof(*value));
    g_scalar_row = row;
    value->is_null = scalar_is_null(result);
    if (value->is_null) return;
    value->part_count = base == RSQL_SCALAR_CONCAT ? 2u : 1u;
    prepare_scalar_part(&value->parts[0], result, 0u);
    if (value->part_count > 1u) {
        prepare_scalar_part(&value->parts[1], result, 1u);
    }
    if (base != RSQL_SCALAR_SUBSTR) return;
    start = scalar_u16(g_rsql_cursor.aggregate_counts[result].bytes);
    count = scalar_u16(&g_rsql_cursor.aggregate_counts[result].bytes[2]);
    if (start > value->parts[0].length) value->parts[0].length = 0u;
    else {
        value->parts[0].start = (rsql_u16)(start - 1u);
        value->parts[0].length = (rsql_u16)
            (value->parts[0].length - value->parts[0].start);
        if (count != 0xFFFFu && value->parts[0].length > count) {
            value->parts[0].length = count;
        }
    }
}

static rsql_i8 compare_shaped_scalar(rsql_u8 result,
                                     const rsql_u8* left_row,
                                     const rsql_u8* right_row) {
    g_sort_rc = RSQL_OK;
    prepare_scalar_value(RSQL_SCALAR_COMPARE_LEFT, result, left_row);
    if (g_sort_rc == RSQL_OK) {
        prepare_scalar_value(RSQL_SCALAR_COMPARE_RIGHT, result, right_row);
    }
    if (g_sort_rc != RSQL_OK) return 0;
    g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_SCALAR;
    g_rsql_variable_compare_kind = result;
    g_sort_rc = rsql_query_variable_compare_owner(5u);
    return g_rsql_variable_compare_result;
}

rsql_u8 __fastcall__ rsql_query_scalar_column_phase(
    RsqlCursorColumnRequest* request) {
    rsql_u8 operation;
    rsql_u8 base;
    rsql_u16 copied;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        !g_rsql_cursor.positioned ||
        request->column >= g_rsql_cursor.result_column_count ||
        !RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return RSQL_ERR_CURSOR_STATE;
    }
    if (scalar_projection_variable(request->column)) {
        rsql_query_scalar_variable_prepare(request->column);
        return RSQL_QUERY_PHASE_VARIABLE;
    }
    memset(&request->value, 0, sizeof(request->value));
    g_scalar_row = g_rsql_cursor.row;
    operation = g_rsql_cursor.projection_aggregate[request->column];
    base = operation & RSQL_PROJECTION_OP_MASK;
    request->value.is_null = scalar_is_null(request->column);
    if (base == RSQL_SCALAR_LENGTH) {
        request->value.type.tag = RSQL_TYPE_I16;
        request->value.length = 2u;
    } else {
        request->value.type.tag = RSQL_TYPE_CHAR;
        request->value.type.parameter = scalar_declared_length(request->column);
        request->value.length = request->value.is_null ? 0u :
            scalar_result_length(request->column);
    }
    if (!request->value.is_null) {
        copied = scalar_copy(request->column, 0u, request->value.bytes,
                             sizeof(request->value.bytes));
        (void)copied;
    }
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_scalar_read_phase(
    RsqlValueReadRequest* request) {
    if (!request || !request->destination || request->cursor != 1u ||
        !g_rsql_cursor.active || !g_rsql_cursor.positioned ||
        request->column >= g_rsql_cursor.result_column_count ||
        !RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return RSQL_ERR_CURSOR_STATE;
    }
    if (scalar_projection_variable(request->column)) {
        rsql_query_scalar_variable_prepare(request->column);
        return RSQL_QUERY_PHASE_VARIABLE;
    }
    request->bytes_read = 0u;
    g_scalar_row = g_rsql_cursor.row;
    if (scalar_is_null(request->column)) return RSQL_OK;
    request->bytes_read = scalar_copy(request->column, request->offset,
        (rsql_u8*)request->destination, request->capacity);
    return RSQL_OK;
}

static rsql_u8 slot_mask(rsql_u8 slot) {
    return column_mask((rsql_u8)(slot & 7u));
}

static rsql_u8 valid_table(rsql_u16 row_width) {
    return g_rsql_meta_page0[0] == 'R' && g_rsql_meta_page0[1] == 'T' &&
        g_rsql_meta_page0[2] == 'B' && g_rsql_meta_page0[3] == 'L' &&
        g_rsql_meta_page0[4] == RSQL_STORAGE_VERSION &&
        rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_WIDTH]) ==
            row_width &&
        g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] ==
            rsql_page_checksum(g_rsql_meta_page0);
}

static rsql_u8 valid_row(rsql_u16 row_width) {
    rsql_u8 capacity = g_rsql_meta_page1[RSQL_ROW_CAPACITY];
    return g_rsql_meta_page1[0] == 'R' && g_rsql_meta_page1[1] == 'R' &&
        g_rsql_meta_page1[2] == 'O' && g_rsql_meta_page1[3] == 'W' &&
        g_rsql_meta_page1[4] == RSQL_STORAGE_VERSION && capacity != 0u &&
        capacity <= 32u && rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_WIDTH]) ==
            row_width &&
        (rsql_u16)(RSQL_ROW_DATA + (rsql_u16)capacity * row_width) <=
            RSQL_REU_PAGE_SIZE;
}

static rsql_u8 read_table(rsql_u16 table_page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(table_page),
        g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_table(row_width) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 read_row_page(rsql_u16 page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
        g_rsql_meta_page1, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_row(row_width) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 read_index_page(rsql_u16 page, char third, char fourth) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
        g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return g_rsql_meta_page0[0] == 'R' && g_rsql_meta_page0[1] == 'I' &&
        g_rsql_meta_page0[2] == (rsql_u8)third &&
        g_rsql_meta_page0[3] == (rsql_u8)fourth &&
        g_rsql_meta_page0[4] == RSQL_STORAGE_VERSION &&
        g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] ==
            rsql_page_checksum(g_rsql_meta_page0)
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 next_index_scan(void) {
    while (g_rsql_cursor.index_leaf_page != RSQL_PAGE_NONE) {
        g_sort_rc = read_index_page(g_rsql_cursor.index_leaf_page, 'L', 'F');
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        g_sort_mask = g_rsql_meta_page0[RSQL_INDEX_LEAF_COUNT];
        g_sort_slot = g_rsql_meta_page0[RSQL_INDEX_LEAF_KEY_WIDTH];
        if (g_sort_slot == 0u || g_sort_slot > RSQL_INDEX_KEY_MAX ||
            g_sort_mask > g_rsql_meta_page0[RSQL_INDEX_LEAF_CAPACITY]) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        if (g_rsql_cursor.index_leaf_slot < g_sort_mask) {
            g_sort_offset = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                (rsql_u16)g_rsql_cursor.index_leaf_slot *
                (rsql_u16)(g_sort_slot + 3u));
            if ((rsql_u16)(g_sort_offset + g_sort_slot + 3u) >
                RSQL_PAGE_CHECKSUM_OFFSET) return RSQL_ERR_CORRUPT_STORAGE;
            g_sort_scan_page = rsql_get_u16(
                &g_rsql_meta_page0[g_sort_offset + g_sort_slot]);
            g_sort_scan_slot = g_rsql_meta_page0[
                g_sort_offset + g_sort_slot + 2u];
            ++g_rsql_cursor.index_leaf_slot;
            return RSQL_OK;
        }
        g_rsql_cursor.index_leaf_page = rsql_get_u16(
            &g_rsql_meta_page0[RSQL_INDEX_LEAF_NEXT]);
        g_rsql_cursor.index_leaf_slot = 0u;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 first_index_scan(void) {
    g_sort_rc = read_index_page(g_rsql_cursor.index_page, 'D', 'X');
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    if (rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_TABLE]) !=
        g_rsql_cursor.table_page) return RSQL_ERR_CORRUPT_STORAGE;
    g_rsql_cursor.index_leaf_page = rsql_get_u16(
        &g_rsql_meta_page0[RSQL_INDEX_LEAF_HEAD]);
    g_rsql_cursor.index_leaf_slot = 0u;
    return next_index_scan();
}

/* cc65 2.18 has miscompiled both multi-argument calls and persistent pointers
 * in this overlay.  Row identities cross helper boundaries only as scalar
 * globals, and the zero-local wrappers below copy them explicitly. */
static rsql_u8 first_scan(void) {
    if (g_rsql_cursor.using_index) return first_index_scan();
    g_sort_rc = read_table(g_rsql_cursor.table_page,
                           g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (g_sort_page != RSQL_PAGE_NONE) {
        g_sort_rc = read_row_page(g_sort_page, g_rsql_cursor.row_width);
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        for (g_sort_slot = 0u;
             g_sort_slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY];
             ++g_sort_slot) {
            if (g_rsql_meta_page1[RSQL_ROW_BITMAP + (g_sort_slot >> 3u)] &
                slot_mask(g_sort_slot)) {
                g_sort_scan_page = g_sort_page;
                g_sort_scan_slot = g_sort_slot;
                return RSQL_OK;
            }
        }
        g_sort_page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 first_prior(void) {
    g_sort_rc = read_table(g_rsql_cursor.table_page,
                           g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (g_sort_page != RSQL_PAGE_NONE) {
        g_sort_rc = read_row_page(g_sort_page, g_rsql_cursor.row_width);
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        for (g_sort_slot = 0u;
             g_sort_slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY];
             ++g_sort_slot) {
            if (g_rsql_meta_page1[RSQL_ROW_BITMAP + (g_sort_slot >> 3u)] &
                slot_mask(g_sort_slot)) {
                g_sort_prior_page = g_sort_page;
                g_sort_prior_slot = g_sort_slot;
                return RSQL_OK;
            }
        }
        g_sort_page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 next_selected(void) {
    g_sort_rc = read_table(g_rsql_cursor.table_page,
                           g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_rc = read_row_page(g_sort_current_page,
                              g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_slot = g_sort_current_slot;
    if (g_sort_slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY]) {
        return RSQL_ERR_NOT_FOUND;
    }
    g_sort_mask = slot_mask(g_sort_slot);
    if ((g_rsql_meta_page1[RSQL_ROW_BITMAP + (g_sort_slot >> 3u)] &
         g_sort_mask) == 0u) return RSQL_ERR_NOT_FOUND;
    g_sort_page = g_sort_current_page;
    ++g_sort_slot;
    for (;;) {
        while (g_sort_slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY]) {
            if (g_rsql_meta_page1[RSQL_ROW_BITMAP + (g_sort_slot >> 3u)] &
                slot_mask(g_sort_slot)) {
                g_sort_current_page = g_sort_page;
                g_sort_current_slot = g_sort_slot;
                return RSQL_OK;
            }
            ++g_sort_slot;
        }
        g_sort_page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
        if (g_sort_page == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
        g_sort_rc = read_row_page(g_sort_page, g_rsql_cursor.row_width);
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        g_sort_slot = 0u;
    }
}

static rsql_u8 read_selected(void) {
    g_sort_rc = read_table(g_rsql_cursor.table_page,
                           g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_rc = read_row_page(g_sort_read_page,
                              g_rsql_cursor.row_width);
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_sort_slot = g_sort_read_slot;
    if (g_sort_slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY])
        return RSQL_ERR_NOT_FOUND;
    g_sort_mask = slot_mask(g_sort_slot);
    if ((g_rsql_meta_page1[RSQL_ROW_BITMAP + (g_sort_slot >> 3u)] &
         g_sort_mask) == 0u) return RSQL_ERR_NOT_FOUND;
    g_sort_offset = (rsql_u16)(RSQL_ROW_DATA +
        (rsql_u16)g_sort_read_slot * g_rsql_cursor.row_width);
    if (g_sort_read_target == SORT_READ_SCAN) {
        memcpy(g_rsql_cursor.scan_row, &g_rsql_meta_page1[g_sort_offset],
               g_rsql_cursor.row_width);
    } else if (g_sort_read_target == SORT_READ_EXECUTION) {
        memcpy(g_rsql_execution.row, &g_rsql_meta_page1[g_sort_offset],
               g_rsql_cursor.row_width);
    } else if (g_sort_read_target == SORT_READ_CURSOR) {
        memcpy(g_rsql_cursor.row, &g_rsql_meta_page1[g_sort_offset],
               g_rsql_cursor.row_width);
    } else return RSQL_ERR_CORRUPT_STORAGE;
    return RSQL_OK;
}

static rsql_u8 next_scan(void) {
    if (g_rsql_cursor.using_index) return next_index_scan();
    g_sort_current_page = g_sort_scan_page;
    g_sort_current_slot = g_sort_scan_slot;
    g_sort_rc = next_selected();
    if (g_sort_rc == RSQL_OK) {
        g_sort_scan_page = g_sort_current_page;
        g_sort_scan_slot = g_sort_current_slot;
    }
    return g_sort_rc;
}

static rsql_u8 next_prior(void) {
    g_sort_current_page = g_sort_prior_page;
    g_sort_current_slot = g_sort_prior_slot;
    g_sort_rc = next_selected();
    if (g_sort_rc == RSQL_OK) {
        g_sort_prior_page = g_sort_current_page;
        g_sort_prior_slot = g_sort_current_slot;
    }
    return g_sort_rc;
}

static rsql_u8 read_scan(void) {
    g_sort_read_page = g_sort_scan_page;
    g_sort_read_slot = g_sort_scan_slot;
    g_sort_read_target = SORT_READ_SCAN;
    return read_selected();
}

static rsql_u8 read_prior(void) {
    g_sort_read_page = g_sort_prior_page;
    g_sort_read_slot = g_sort_prior_slot;
    g_sort_read_target = SORT_READ_EXECUTION;
    return read_selected();
}

static rsql_u8 read_best_execution(void) {
    g_sort_read_page = g_sort_best_page;
    g_sort_read_slot = g_sort_best_slot;
    g_sort_read_target = SORT_READ_EXECUTION;
    return read_selected();
}

static rsql_u8 read_best_cursor(void) {
    g_sort_read_page = g_sort_best_page;
    g_sort_read_slot = g_sort_best_slot;
    g_sort_read_target = SORT_READ_CURSOR;
    return read_selected();
}

static rsql_i8 compare_signed_literal(const rsql_u8* left, rsql_u8 width,
                                      const rsql_u8* right) {
    rsql_u8 left_fill = (left[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 right_negative = (right[7] & 0x80u) != 0u;
    rsql_u8 index = 8u;
    rsql_u8 left_byte;
    if ((left_fill != 0u) != right_negative) return left_fill ? -1 : 1;
    while (index != 0u) {
        --index;
        left_byte = index < width ? left[index] : left_fill;
        if (left_byte < right[index]) return -1;
        if (left_byte > right[index]) return 1;
    }
    return 0;
}

static rsql_i8 compare_unsigned(const rsql_u8* left, const rsql_u8* right,
                                rsql_u8 width) {
    rsql_u8 index = width;
    while (index != 0u) {
        --index;
        if (left[index] < right[index]) return -1;
        if (left[index] > right[index]) return 1;
    }
    return 0;
}

static rsql_i8 compare_float(const rsql_u8* left, const rsql_u8* right) {
    rsql_u8 ln = left[0] && (left[1] & 0x80u);
    rsql_u8 rn = right[0] && (right[1] & 0x80u);
    rsql_u8 index;
    rsql_u8 lb;
    rsql_u8 rb;
    if (left[0] == 0u && right[0] == 0u) return 0;
    if (ln != rn) return ln ? -1 : 1;
    for (index = 0u; index < 5u; ++index) {
        lb = left[index]; rb = right[index];
        if (index == 1u) { lb &= 0x7Fu; rb &= 0x7Fu; }
        if (lb == rb) continue;
        if (ln) return lb < rb ? 1 : -1;
        return lb < rb ? -1 : 1;
    }
    return 0;
}

static rsql_i8 compare_char_literal(const rsql_u8* left, rsql_u16 width,
                                    const RsqlParsedValue* literal) {
    rsql_u16 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    for (index = 0u; index < width; ++index) {
        left_byte = folded(left[index]);
        right_byte = index < literal->length
            ? folded((rsql_u8)literal->string[index]) : (rsql_u8)' ';
        if (left_byte < right_byte) return -1;
        if (left_byte > right_byte) return 1;
    }
    return 0;
}

static rsql_u8 sort_find_blob(const rsql_u8* handle, rsql_u8 kind,
                              rsql_u8 right) {
    rsql_u16 page = g_rsql_cursor.blob_directory;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(page), g_rsql_meta_page0,
                           RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) return rc;
        if (g_rsql_meta_page0[0] != 'R' || g_rsql_meta_page0[1] != 'B' ||
            g_rsql_meta_page0[2] != 'D' || g_rsql_meta_page0[3] != 'R' ||
            g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
                rsql_page_checksum(g_rsql_meta_page0)) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        for (slot = 0u; slot < SORT_BLOB_DIR_ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(SORT_BLOB_DIR_ENTRIES +
                (rsql_u16)slot * SORT_BLOB_DIR_ENTRY_BYTES);
            if (g_rsql_meta_page0[base] == 1u &&
                g_rsql_meta_page0[base + SORT_BLOB_ENTRY_KIND] == kind &&
                memcmp(&g_rsql_meta_page0[base + SORT_BLOB_ENTRY_HANDLE],
                       handle, 4u) == 0) {
                if (g_rsql_meta_page0[base + SORT_BLOB_ENTRY_LENGTH + 2u] ||
                    g_rsql_meta_page0[base + SORT_BLOB_ENTRY_LENGTH + 3u]) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
                if (right) {
                    g_sort_blob_right_page = rsql_get_u16(
                        &g_rsql_meta_page0[base + SORT_BLOB_ENTRY_FIRST]);
                    g_sort_blob_right_length = rsql_get_u16(
                        &g_rsql_meta_page0[base + SORT_BLOB_ENTRY_LENGTH]);
                } else {
                    g_sort_blob_left_page = rsql_get_u16(
                        &g_rsql_meta_page0[base + SORT_BLOB_ENTRY_FIRST]);
                    g_sort_blob_left_first = g_sort_blob_left_page;
                    g_sort_blob_left_length = rsql_get_u16(
                        &g_rsql_meta_page0[base + SORT_BLOB_ENTRY_LENGTH]);
                }
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page0[SORT_BLOB_DIR_NEXT]);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 sort_load_blob_page(rsql_u8 right) {
    rsql_u8* target = right ? g_rsql_meta_page1 : g_rsql_meta_page0;
    rsql_u16 page = right ? g_sort_blob_right_page : g_sort_blob_left_page;
    rsql_u16 used;
    rsql_u8 rc;
    if (page == RSQL_PAGE_NONE) return RSQL_ERR_CORRUPT_STORAGE;
    rc = rsql_reu_read(rsql_reu_page_address(page), target,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    used = rsql_get_u16(&target[SORT_BLOB_PAGE_USED]);
    if (target[0] != 'R' || target[1] != 'B' || target[2] != 'L' ||
        target[3] != 'B' || used == 0u || used > SORT_BLOB_PAGE_PAYLOAD) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    if (right) {
        g_sort_blob_right_page = rsql_get_u16(&target[SORT_BLOB_PAGE_NEXT]);
        g_sort_blob_right_used = used;
        g_sort_blob_right_offset = 0u;
    } else {
        g_sort_blob_left_page = rsql_get_u16(&target[SORT_BLOB_PAGE_NEXT]);
        g_sort_blob_left_used = used;
        g_sort_blob_left_offset = 0u;
    }
    return RSQL_OK;
}

static rsql_u8 sort_compare_blob(const rsql_u8* left, const rsql_u8* right,
                                 rsql_u8 kind, rsql_i8* comparison_out) {
    rsql_u16 common;
    rsql_u16 compared = 0u;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    rsql_u8 rc = sort_find_blob(left, kind, 0u);
    if (rc == RSQL_OK) rc = sort_find_blob(right, kind, 1u);
    if (rc != RSQL_OK) return rc;
    common = g_sort_blob_left_length < g_sort_blob_right_length
        ? g_sort_blob_left_length : g_sort_blob_right_length;
    g_sort_blob_left_used = 0u;
    g_sort_blob_right_used = 0u;
    g_sort_blob_left_offset = 0u;
    g_sort_blob_right_offset = 0u;
    while (compared < common) {
        if (g_sort_blob_left_offset == g_sort_blob_left_used) {
            rc = sort_load_blob_page(0u);
            if (rc != RSQL_OK) return rc;
        }
        if (g_sort_blob_right_offset == g_sort_blob_right_used) {
            rc = sort_load_blob_page(1u);
            if (rc != RSQL_OK) return rc;
        }
        left_byte = g_rsql_meta_page0[SORT_BLOB_PAGE_DATA +
            g_sort_blob_left_offset++];
        right_byte = g_rsql_meta_page1[SORT_BLOB_PAGE_DATA +
            g_sort_blob_right_offset++];
        if (kind == RSQL_TYPE_TEXT) {
            left_byte = folded(left_byte);
            right_byte = folded(right_byte);
        }
        if (left_byte != right_byte) {
            *comparison_out = left_byte < right_byte ? -1 : 1;
            return RSQL_OK;
        }
        ++compared;
    }
    if (g_sort_blob_left_length < g_sort_blob_right_length) {
        *comparison_out = -1;
    } else if (g_sort_blob_left_length > g_sort_blob_right_length) {
        *comparison_out = 1;
    } else *comparison_out = 0;
    return RSQL_OK;
}

rsql_u8 rsql_query_variable_group_match_phase(void) {
    const RsqlColumnInfo* column;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 source;
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        column = &g_rsql_cursor.columns[source];
        if (column->type.tag != RSQL_TYPE_TEXT &&
            column->type.tag != RSQL_TYPE_BLOB) continue;
        left_null = (g_rsql_cursor.row[0] & column_mask(source)) != 0u;
        right_null = (g_rsql_cursor.scan_row[0] & column_mask(source)) != 0u;
        if (left_null != right_null) return RSQL_QUERY_PHASE_INDEX_SKIP;
        if (left_null) continue;
        g_sort_rc = sort_compare_blob(
            &g_rsql_cursor.row[column->offset],
            &g_rsql_cursor.scan_row[column->offset],
            column->type.tag, &g_sort_comparison);
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        if (g_sort_comparison != 0) return RSQL_QUERY_PHASE_INDEX_SKIP;
    }
    return RSQL_OK;
}

rsql_u8 rsql_query_variable_compare_phase(void) {
    const RsqlColumnInfo* column;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 source = g_rsql_variable_compare_source;
    if (source == 0xFFu) return rsql_query_variable_group_match_phase();
    if (source & RSQL_VARIABLE_COMPARE_HANDLES) {
        return sort_compare_blob(
            g_rsql_variable_compare_left, g_rsql_variable_compare_right,
            g_rsql_variable_compare_kind,
            &g_rsql_variable_compare_result);
    }
    if (source & RSQL_VARIABLE_COMPARE_COMPLEX) {
        const rsql_u8* right;
        source &= (rsql_u8)~RSQL_VARIABLE_COMPARE_COMPLEX;
        if (source & RSQL_SOURCE_SUBQUERY) return RSQL_ERR_CURSOR_STATE;
        column = scalar_source_column(source);
        right = (source & RSQL_SOURCE_INNER)
            ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
        return sort_compare_blob(
            &g_rsql_execution.row[column->offset],
            &right[column->offset], column->type.tag,
            &g_rsql_variable_compare_result);
    }
    if (source & (RSQL_SOURCE_INNER | RSQL_SOURCE_SUBQUERY)) {
        return RSQL_ERR_CURSOR_STATE;
    }
    column = &g_rsql_cursor.columns[source];
    if (column->type.tag != RSQL_TYPE_TEXT &&
        column->type.tag != RSQL_TYPE_BLOB) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    left_null = (g_rsql_execution.row[0] & column_mask(source)) != 0u;
    right_null = (g_rsql_cursor.scan_row[0] & column_mask(source)) != 0u;
    if (left_null != right_null) {
        g_rsql_variable_compare_result = left_null ? -1 : 1;
        return RSQL_OK;
    }
    if (left_null) {
        g_rsql_variable_compare_result = 0;
        return RSQL_OK;
    }
    return sort_compare_blob(
        &g_rsql_execution.row[column->offset],
        &g_rsql_cursor.scan_row[column->offset], column->type.tag,
        &g_rsql_variable_compare_result);
}

static rsql_u8 sort_compare_blob_literal(const rsql_u8* handle,
        rsql_u8 kind, const RsqlParsedValue* literal,
        rsql_i8* comparison_out) {
    rsql_u16 common;
    rsql_u16 index = 0u;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    rsql_u8 rc = sort_find_blob(handle, kind, 0u);
    if (rc != RSQL_OK) return rc;
    common = g_sort_blob_left_length < literal->length
        ? g_sort_blob_left_length : literal->length;
    g_sort_blob_left_used = 0u;
    g_sort_blob_left_offset = 0u;
    while (index < common) {
        if (g_sort_blob_left_offset == g_sort_blob_left_used) {
            rc = sort_load_blob_page(0u);
            if (rc != RSQL_OK) return rc;
        }
        left_byte = g_rsql_meta_page0[SORT_BLOB_PAGE_DATA +
            g_sort_blob_left_offset++];
        right_byte = (rsql_u8)literal->string[index++];
        if (kind == RSQL_TYPE_TEXT) {
            left_byte = folded(left_byte);
            right_byte = folded(right_byte);
        }
        if (left_byte != right_byte) {
            *comparison_out = left_byte < right_byte ? -1 : 1;
            return RSQL_OK;
        }
    }
    if (g_sort_blob_left_length < literal->length) *comparison_out = -1;
    else if (g_sort_blob_left_length > literal->length) *comparison_out = 1;
    else *comparison_out = 0;
    return RSQL_OK;
}

static rsql_u8 sort_blob_left_byte(rsql_u16 offset, rsql_u8* value_out) {
    rsql_u16 page;
    rsql_u16 start;
    rsql_u8 rc;
    if (offset >= g_sort_blob_left_length) return RSQL_ERR_CORRUPT_STORAGE;
    if (g_sort_blob_left_used && offset >= g_sort_blob_left_start &&
        offset < g_sort_blob_left_start + g_sort_blob_left_used) {
        *value_out = g_rsql_meta_page0[SORT_BLOB_PAGE_DATA +
            (rsql_u16)(offset - g_sort_blob_left_start)];
        return RSQL_OK;
    }
    if (g_sort_blob_left_used &&
        offset == g_sort_blob_left_start + g_sort_blob_left_used) {
        page = g_sort_blob_left_page;
        start = offset;
    } else {
        page = g_sort_blob_left_first;
        start = 0u;
    }
    while (page != RSQL_PAGE_NONE) {
        g_sort_blob_left_page = page;
        rc = sort_load_blob_page(0u);
        if (rc != RSQL_OK) return rc;
        g_sort_blob_left_start = start;
        if (offset < start + g_sort_blob_left_used) {
            *value_out = g_rsql_meta_page0[SORT_BLOB_PAGE_DATA +
                (rsql_u16)(offset - start)];
            return RSQL_OK;
        }
        start = (rsql_u16)(start + g_sort_blob_left_used);
        page = g_sort_blob_left_page;
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 sort_like_blob(const rsql_u8* handle,
        const RsqlParsedValue* pattern, rsql_u8* truth_out) {
    rsql_u16 input = 0u;
    rsql_u16 retry_input = 0u;
    rsql_u8 position = 0u;
    rsql_u8 retry_pattern = 0xFFu;
    rsql_u8 byte;
    rsql_u8 pattern_byte;
    rsql_u8 rc = sort_find_blob(handle, RSQL_TYPE_TEXT, 0u);
    if (rc != RSQL_OK) return rc;
    g_sort_blob_left_used = 0u;
    while (input < g_sort_blob_left_length) {
        rc = sort_blob_left_byte(input, &byte);
        if (rc != RSQL_OK) return rc;
        if (position < pattern->length) {
            pattern_byte = (rsql_u8)pattern->string[position];
            if (pattern_byte == '_' ||
                folded(pattern_byte) == folded(byte)) {
                ++position;
                ++input;
                continue;
            }
            if (pattern_byte == '%') {
                retry_pattern = position++;
                retry_input = input;
                continue;
            }
        }
        if (retry_pattern != 0xFFu) {
            position = (rsql_u8)(retry_pattern + 1u);
            input = ++retry_input;
            continue;
        }
        *truth_out = SQL_FALSE;
        return RSQL_OK;
    }
    while (position < pattern->length && pattern->string[position] == '%') {
        ++position;
    }
    *truth_out = position == pattern->length ? SQL_TRUE : SQL_FALSE;
    return RSQL_OK;
}

static rsql_i8 compare_selected_column(void) {
    const rsql_u8* left;
    const rsql_u8* right;
    const RsqlColumnInfo* column =
        &g_rsql_cursor.columns[g_sort_compare_source];
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 width = (rsql_u8)value_width(&column->type);
    rsql_u8 left_negative;
    rsql_u8 right_negative;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    rsql_u16 index;
    if (g_sort_compare_target == SORT_COMPARE_CURSOR) {
        left = g_rsql_cursor.scan_row;
        right = g_rsql_cursor.row;
    } else if (g_sort_compare_target == SORT_COMPARE_BEST) {
        left = g_rsql_cursor.scan_row;
        right = g_rsql_execution.row;
    } else {
        left = g_rsql_execution.row;
        right = g_rsql_cursor.scan_row;
    }
    left_null = (left[0] & column_mask(g_sort_compare_source)) != 0u;
    right_null = (right[0] & column_mask(g_sort_compare_source)) != 0u;
    if (left_null != right_null) return left_null ? -1 : 1;
    if (left_null) return 0;
    left += column->offset; right += column->offset;
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        g_sort_rc = sort_compare_blob(left, right, column->type.tag,
                                      &g_sort_comparison);
        return g_sort_comparison;
    }
    if (column->type.tag == RSQL_TYPE_CHAR) {
        for (index = 0u; index < column->type.parameter; ++index) {
            left_byte = folded(left[index]);
            right_byte = folded(right[index]);
            if (left_byte < right_byte) return -1;
            if (left_byte > right_byte) return 1;
        }
        return 0;
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        left_negative = left[0] && (left[1] & 0x80u);
        right_negative = right[0] && (right[1] & 0x80u);
        if (left[0] == 0u && right[0] == 0u) return 0;
        if (left_negative != right_negative) return left_negative ? -1 : 1;
        for (index = 0u; index < 5u; ++index) {
            left_byte = left[index];
            right_byte = right[index];
            if (index == 1u) {
                left_byte &= 0x7Fu;
                right_byte &= 0x7Fu;
            }
            if (left_byte == right_byte) continue;
            if (left_negative) return left_byte < right_byte ? 1 : -1;
            return left_byte < right_byte ? -1 : 1;
        }
        return 0;
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        index = width;
        while (index != 0u) {
            --index;
            if (left[index] < right[index]) return -1;
            if (left[index] > right[index]) return 1;
        }
        return 0;
    }
    left_negative = (left[width - 1u] & 0x80u) != 0u;
    right_negative = (right[width - 1u] & 0x80u) != 0u;
    if (left_negative != right_negative) return left_negative ? -1 : 1;
    index = width;
    while (index != 0u) {
        --index;
        if (left[index] < right[index]) return -1;
        if (left[index] > right[index]) return 1;
    }
    return 0;
}

static rsql_i8 compare_literal(const rsql_u8* row,
                               const RsqlBoundPredicate* predicate) {
    const RsqlColumnInfo* column = &g_rsql_cursor.columns[predicate->column];
    const rsql_u8* value = &row[column->offset];
    if (column->type.tag == RSQL_TYPE_CHAR) {
        return compare_char_literal(value, column->type.parameter,
                                    &predicate->value);
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(value, predicate->value.integer.bytes);
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(value, predicate->value.integer.bytes,
                                (rsql_u8)value_width(&column->type));
    }
    return compare_signed_literal(value,
        (rsql_u8)value_width(&column->type),
        predicate->value.integer.bytes);
}

static rsql_u8 comparison_matches(rsql_i8 comparison, rsql_u8 op) {
    if (op == RSQL_PRED_EQ) return comparison == 0;
    if (op == RSQL_PRED_NE) return comparison != 0;
    if (op == RSQL_PRED_LT) return comparison < 0;
    if (op == RSQL_PRED_LE) return comparison <= 0;
    if (op == RSQL_PRED_GT) return comparison > 0;
    return op == RSQL_PRED_GE && comparison >= 0;
}

static rsql_u8 like_char(const rsql_u8* row, rsql_u16 width,
                         const RsqlParsedValue* pattern) {
    rsql_u16 length = width;
    rsql_u16 ri = 0u;
    rsql_u16 pi = 0u;
    rsql_u16 star = 0xFFFFu;
    rsql_u16 retry = 0u;
    rsql_u8 byte;
    while (length && row[length - 1u] == ' ') --length;
    while (ri < length) {
        if (pi < pattern->length) {
            byte = (rsql_u8)pattern->string[pi];
            if (byte == '_' || folded(byte) == folded(row[ri])) {
                ++pi; ++ri; continue;
            }
            if (byte == '%') { star = pi++; retry = ri; continue; }
        }
        if (star != 0xFFFFu) { pi = (rsql_u16)(star + 1u); ri = ++retry; continue; }
        return 0u;
    }
    while (pi < pattern->length && pattern->string[pi] == '%') ++pi;
    return pi == pattern->length;
}

static rsql_u8 predicate_truth(const rsql_u8* row, rsql_u8 index) {
    const RsqlBoundPredicate* predicate = &g_rsql_cursor.predicates[index];
    const RsqlColumnInfo* column = &g_rsql_cursor.columns[predicate->column];
    rsql_u8 is_null = (row[0] & column_mask(predicate->column)) != 0u;
    rsql_u8 truth;
    rsql_i8 comparison;
    if (predicate->op == RSQL_PRED_IS_NULL) return is_null ? SQL_TRUE : SQL_FALSE;
    if (predicate->op == RSQL_PRED_IS_NOT_NULL) return is_null ? SQL_FALSE : SQL_TRUE;
    if (is_null || predicate->value.kind == RSQL_VALUE_NULL) return SQL_UNKNOWN;
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        if (predicate->op == RSQL_PRED_LIKE) {
            g_sort_rc = sort_like_blob(&row[column->offset],
                &predicate->value, &truth);
            return g_sort_rc == RSQL_OK ? truth : SQL_FALSE;
        }
        g_sort_rc = sort_compare_blob_literal(&row[column->offset],
            column->type.tag, &predicate->value, &comparison);
        if (g_sort_rc != RSQL_OK) return SQL_FALSE;
        return comparison_matches(comparison, predicate->op)
            ? SQL_TRUE : SQL_FALSE;
    }
    if (predicate->op == RSQL_PRED_LIKE) {
        return like_char(&row[column->offset], column->type.parameter,
            &predicate->value) ? SQL_TRUE : SQL_FALSE;
    }
    comparison = compare_literal(row, predicate);
    return comparison_matches(comparison, predicate->op) ? SQL_TRUE : SQL_FALSE;
}

static rsql_u8 row_matches(const rsql_u8* row) {
    rsql_u8 stack[8];
    rsql_u8 count = 0u;
    rsql_u8 opcode;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    if (!g_rsql_cursor.where_present) return 1u;
    for (index = 0u; index < g_rsql_cursor.bool_program_count; ++index) {
        opcode = g_rsql_cursor.bool_program[index];
        if (opcode < RSQL_PREDICATES_MAX) {
            if (opcode >= g_rsql_cursor.predicate_count ||
                count >= RSQL_PREDICATES_MAX) return 0u;
            stack[count++] = predicate_truth(row, opcode);
        }
        else if (opcode == RSQL_BOOL_NOT) {
            if (!count) return 0u;
            if (stack[count - 1u] == SQL_TRUE) stack[count - 1u] = SQL_FALSE;
            else if (stack[count - 1u] == SQL_FALSE) stack[count - 1u] = SQL_TRUE;
        } else {
            if (count < 2u) return 0u;
            right = stack[--count]; left = stack[count - 1u];
            if (opcode == RSQL_BOOL_AND) {
                stack[count - 1u] = (left == SQL_FALSE || right == SQL_FALSE)
                    ? SQL_FALSE : (left == SQL_TRUE && right == SQL_TRUE
                        ? SQL_TRUE : SQL_UNKNOWN);
            } else if (opcode == RSQL_BOOL_OR) {
                stack[count - 1u] = (left == SQL_TRUE || right == SQL_TRUE)
                    ? SQL_TRUE : (left == SQL_FALSE && right == SQL_FALSE
                        ? SQL_FALSE : SQL_UNKNOWN);
            } else return 0u;
        }
    }
    return count == 1u && stack[0] == SQL_TRUE;
}

static rsql_i8 compare_scan_cursor_id(void) {
    if (g_sort_scan_page < g_rsql_cursor.row_id.page) return -1;
    if (g_sort_scan_page > g_rsql_cursor.row_id.page) return 1;
    if (g_sort_scan_slot < g_rsql_cursor.row_id.slot) return -1;
    if (g_sort_scan_slot > g_rsql_cursor.row_id.slot) return 1;
    return 0;
}

static rsql_i8 compare_scan_best_id(void) {
    if (g_sort_scan_page < g_sort_best_page) return -1;
    if (g_sort_scan_page > g_sort_best_page) return 1;
    if (g_sort_scan_slot < g_sort_best_slot) return -1;
    if (g_sort_scan_slot > g_sort_best_slot) return 1;
    return 0;
}

static rsql_i8 compare_scan_cursor(void) {
    rsql_i8 comparison;
    rsql_u8 index;
    rsql_u8 source;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        if (source & RSQL_ORDER_PROJECTION) {
            comparison = compare_shaped_scalar(
                source & RSQL_ORDER_PROJECTION_MASK,
                g_rsql_cursor.scan_row, g_rsql_cursor.row);
        } else {
            g_sort_compare_source = source;
            g_sort_compare_target = SORT_COMPARE_CURSOR;
            comparison = compare_selected_column();
        }
        if (comparison != 0) {
            if (g_rsql_cursor.order_desc_mask & column_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            return comparison;
        }
    }
    return compare_scan_cursor_id();
}

static rsql_i8 compare_scan_best(void) {
    rsql_i8 comparison;
    rsql_u8 index;
    rsql_u8 source;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        if (source & RSQL_ORDER_PROJECTION) {
            comparison = compare_shaped_scalar(
                source & RSQL_ORDER_PROJECTION_MASK,
                g_rsql_cursor.scan_row, g_rsql_execution.row);
        } else {
            g_sort_compare_source = source;
            g_sort_compare_target = SORT_COMPARE_BEST;
            comparison = compare_selected_column();
        }
        if (comparison != 0) {
            if (g_rsql_cursor.order_desc_mask & column_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            return comparison;
        }
    }
    return compare_scan_best_id();
}

static rsql_u8 same_prior_projection(void) {
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.result_column_count; ++index) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[index])) {
            if (compare_shaped_scalar(index, g_rsql_execution.row,
                    g_rsql_cursor.scan_row) != 0) return 0u;
        } else {
            g_sort_compare_source = g_rsql_cursor.projection[index];
            g_sort_compare_target = SORT_COMPARE_PRIOR;
            if (compare_selected_column() != 0) return 0u;
        }
    }
    return 1u;
}

static rsql_u8 duplicate_before(void) {
    g_sort_duplicate = 0u;
    g_sort_rc = first_prior();
    while (g_sort_rc == RSQL_OK) {
        if (g_sort_prior_page == g_sort_scan_page &&
            g_sort_prior_slot == g_sort_scan_slot) return RSQL_OK;
        g_sort_rc = read_prior();
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        if (row_matches(g_rsql_execution.row) &&
            same_prior_projection()) {
            g_sort_duplicate = 1u;
            return RSQL_OK;
        }
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        g_sort_rc = next_prior();
    }
    return g_sort_rc == RSQL_ERR_NOT_FOUND
        ? RSQL_ERR_CORRUPT_STORAGE : g_sort_rc;
}

static rsql_u8 select_next(void) {
    g_sort_have_best = 0u;
    g_sort_rc = first_scan();
    g_sort_found = 0u;
    while (g_sort_rc == RSQL_OK) {
        g_sort_rc = read_scan();
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        if (row_matches(g_rsql_cursor.scan_row) &&
            (!g_rsql_cursor.positioned ||
             compare_scan_cursor() > 0)) {
            if (g_sort_rc != RSQL_OK) return g_sort_rc;
            g_sort_duplicate = 0u;
            if (g_rsql_cursor.distinct) {
                g_sort_rc = duplicate_before();
                if (g_sort_rc != RSQL_OK) return g_sort_rc;
            }
            if (!g_sort_duplicate) {
                if (g_sort_have_best) {
                    g_sort_rc = read_best_execution();
                    if (g_sort_rc != RSQL_OK) return g_sort_rc;
                }
                g_sort_comparison = g_sort_have_best
                    ? compare_scan_best() : -1;
                if (g_sort_rc != RSQL_OK) return g_sort_rc;
                if (g_sort_comparison < 0) {
                    g_sort_best_page = g_sort_scan_page;
                    g_sort_best_slot = g_sort_scan_slot;
                    g_sort_have_best = 1u;
                }
            }
        }
        if (g_sort_rc != RSQL_OK) return g_sort_rc;
        g_sort_rc = next_scan();
    }
    if (g_sort_rc != RSQL_ERR_NOT_FOUND) return g_sort_rc;
    if (!g_sort_have_best) return RSQL_OK;
    g_sort_rc = read_best_cursor();
    if (g_sort_rc != RSQL_OK) return g_sort_rc;
    g_rsql_cursor.row_id.page = g_sort_best_page;
    g_rsql_cursor.row_id.slot = g_sort_best_slot;
    g_rsql_cursor.positioned = 1u;
    g_sort_found = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_result_next_phase(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.finished ||
        (g_rsql_cursor.limit_present &&
         g_rsql_cursor.returned_rows >= g_rsql_cursor.limit)) {
        g_rsql_cursor.finished = 1u;
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    for (;;) {
        rc = select_next();
        if (rc != RSQL_OK) return rc;
        if (!g_sort_found) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        if (g_rsql_cursor.skipped_rows < g_rsql_cursor.offset) {
            ++g_rsql_cursor.skipped_rows;
            continue;
        }
        ++g_rsql_cursor.returned_rows;
        request->has_row = 1u;
        return RSQL_OK;
    }
}

#include <string.h>

#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"
#include "wide_internal.h"

#define WIDE_FIXED_NULL (RSQL_WIDE_SCALAR_STATE.fixed_null)
#define WIDE_FIXED_PART_COUNT (RSQL_WIDE_SCALAR_STATE.fixed_part_count)
#define WIDE_FIXED_DATA (RSQL_WIDE_SCALAR_STATE.fixed_data)
#define WIDE_FIXED_LENGTH (RSQL_WIDE_SCALAR_STATE.fixed_length)
#define WIDE_FIXED_TEXT_MASK (RSQL_WIDE_SCALAR_STATE.fixed_text_mask)
#define WIDE_FIXED_FIRST_PAGE (RSQL_WIDE_SCALAR_STATE.fixed_first_page)
#define WIDE_FIXED_START (RSQL_WIDE_SCALAR_STATE.fixed_start)

#define WIDE_BLOB_DIR_NEXT 6u
#define WIDE_BLOB_DIR_ENTRIES 8u
#define WIDE_BLOB_DIR_ENTRY_BYTES 20u
#define WIDE_BLOB_DIR_ENTRY_COUNT 12u
#define WIDE_BLOB_ENTRY_KIND 1u
#define WIDE_BLOB_ENTRY_HANDLE 2u
#define WIDE_BLOB_ENTRY_FIRST 6u
#define WIDE_BLOB_ENTRY_LENGTH 8u
#define WIDE_BLOB_PAGE_NEXT 6u
#define WIDE_BLOB_PAGE_USED 8u
#define WIDE_BLOB_PAGE_DATA 10u
#define WIDE_BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - WIDE_BLOB_PAGE_DATA)

static const RsqlColumnInfo* wide_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static const rsql_u8* wide_row(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) return g_rsql_execution.row;
    if (source & RSQL_SOURCE_INNER) return g_rsql_cursor.scan_row;
    return g_rsql_cursor.row;
}

static rsql_u8 wide_null(rsql_u8 source) {
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    return (wide_row(source)[0] &
        (rsql_u8)(1u << (source & RSQL_SOURCE_COLUMN_MASK))) != 0u;
}

static rsql_u8 scalar_null(rsql_u8 result) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 base = operation & RSQL_PROJECTION_OP_MASK;
    if (base == RSQL_SCALAR_STRING) return 0u;
    if (base != RSQL_SCALAR_CONCAT) {
        return (operation & RSQL_PROJECTION_LITERAL_LEFT) ? 0u :
            wide_null(g_rsql_cursor.projection[result]);
    }
    if (wide_null(g_rsql_cursor.projection[result])) return 1u;
    return !(operation & (RSQL_PROJECTION_LITERAL_LEFT |
                          RSQL_PROJECTION_LITERAL_RIGHT)) &&
        wide_null(g_rsql_cursor.update_columns[result]);
}

static rsql_u8 find_text(const rsql_u8* handle, rsql_u8 right) {
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
        for (slot = 0u; slot < WIDE_BLOB_DIR_ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(WIDE_BLOB_DIR_ENTRIES +
                (rsql_u16)slot * WIDE_BLOB_DIR_ENTRY_BYTES);
            if (g_rsql_meta_page0[base] == 1u &&
                g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_KIND] ==
                    RSQL_TYPE_TEXT &&
                memcmp(&g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_HANDLE],
                       handle, 4u) == 0) {
                if (g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_LENGTH + 2u] ||
                    g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_LENGTH + 3u]) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
                WIDE_FIXED_FIRST_PAGE[right] = rsql_get_u16(
                    &g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_FIRST]);
                WIDE_FIXED_LENGTH[right] = rsql_get_u16(
                    &g_rsql_meta_page0[base + WIDE_BLOB_ENTRY_LENGTH]);
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page0[WIDE_BLOB_DIR_NEXT]);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 load_text_page(rsql_u16 page, rsql_u16* next_out,
                              rsql_u16* used_out) {
    rsql_u8 rc;
    if (page == RSQL_PAGE_NONE) return RSQL_ERR_CORRUPT_STORAGE;
    rc = rsql_reu_read(rsql_reu_page_address(page), g_rsql_meta_page0,
                       RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    *used_out = rsql_get_u16(&g_rsql_meta_page0[WIDE_BLOB_PAGE_USED]);
    if (g_rsql_meta_page0[0] != 'R' || g_rsql_meta_page0[1] != 'B' ||
        g_rsql_meta_page0[2] != 'L' || g_rsql_meta_page0[3] != 'B' ||
        *used_out == 0u || *used_out > WIDE_BLOB_PAGE_PAYLOAD) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    *next_out = rsql_get_u16(&g_rsql_meta_page0[WIDE_BLOB_PAGE_NEXT]);
    return RSQL_OK;
}

static rsql_u8 text_copy(rsql_u16 page, rsql_u16 offset,
                         rsql_u8* destination, rsql_u16 length) {
    rsql_u16 available;
    rsql_u16 next;
    rsql_u16 used;
    rsql_u8 rc;
    while (length != 0u) {
        rc = load_text_page(page, &next, &used);
        if (rc != RSQL_OK) return rc;
        if (offset >= used) {
            offset = (rsql_u16)(offset - used);
            page = next;
            continue;
        }
        available = (rsql_u16)(used - offset);
        if (available > length) available = length;
        memcpy(destination, &g_rsql_meta_page0[
            WIDE_BLOB_PAGE_DATA + offset], available);
        destination += available;
        length = (rsql_u16)(length - available);
        offset = 0u;
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 prepare_part(rsql_u8 result, rsql_u8 right) {
    rsql_u8 operation = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 source;
    const RsqlColumnInfo* column;
    const rsql_u8* data;
    WIDE_FIXED_START[right] = 0u;
    if ((!right && (operation & RSQL_PROJECTION_LITERAL_LEFT)) ||
        (right && (operation & RSQL_PROJECTION_LITERAL_RIGHT))) {
        WIDE_FIXED_DATA[right] = RSQL_SCALAR_LITERAL_DATA(result);
        WIDE_FIXED_LENGTH[right] = RSQL_SCALAR_LITERAL_LENGTH(result);
        return RSQL_OK;
    }
    source = right && !(operation & RSQL_PROJECTION_LITERAL_LEFT)
        ? g_rsql_cursor.update_columns[result]
        : g_rsql_cursor.projection[result];
    column = wide_column(source);
    data = &wide_row(source)[column->offset];
    WIDE_FIXED_DATA[right] = data;
    if (column->type.tag == RSQL_TYPE_TEXT) {
        WIDE_FIXED_TEXT_MASK |= right ? 2u : 1u;
        return find_text(data, right);
    }
    WIDE_FIXED_LENGTH[right] = column->type.parameter;
    while (WIDE_FIXED_LENGTH[right] &&
           data[WIDE_FIXED_LENGTH[right] - 1u] == ' ') {
        --WIDE_FIXED_LENGTH[right];
    }
    return RSQL_OK;
}

static rsql_u8 prepare_scalar(rsql_u8 result) {
    rsql_u8 base = g_rsql_cursor.projection_aggregate[result] &
        RSQL_PROJECTION_OP_MASK;
    rsql_u8 rc;
    rsql_u16 start;
    rsql_u16 count;
    WIDE_FIXED_NULL = scalar_null(result);
    if (WIDE_FIXED_NULL) return RSQL_OK;
    WIDE_FIXED_TEXT_MASK = 0u;
    WIDE_FIXED_PART_COUNT = base == RSQL_SCALAR_CONCAT ? 2u : 1u;
    rc = prepare_part(result, 0u);
    if (rc != RSQL_OK) return rc;
    if (WIDE_FIXED_PART_COUNT == 2u) {
        rc = prepare_part(result, 1u);
        if (rc != RSQL_OK) return rc;
    }
    if (base != RSQL_SCALAR_SUBSTR) return RSQL_OK;
    start = (rsql_u16)g_rsql_cursor.aggregate_counts[result].bytes[0] |
        ((rsql_u16)g_rsql_cursor.aggregate_counts[result].bytes[1] << 8u);
    count = (rsql_u16)g_rsql_cursor.aggregate_counts[result].bytes[2] |
        ((rsql_u16)g_rsql_cursor.aggregate_counts[result].bytes[3] << 8u);
    if (start > WIDE_FIXED_LENGTH[0]) WIDE_FIXED_LENGTH[0] = 0u;
    else {
        --start;
        if (WIDE_FIXED_TEXT_MASK & 1u) WIDE_FIXED_START[0] = start;
        else WIDE_FIXED_DATA[0] += start;
        WIDE_FIXED_LENGTH[0] -= start;
        if (count != 0xFFFFu && count < WIDE_FIXED_LENGTH[0]) {
            WIDE_FIXED_LENGTH[0] = count;
        }
    }
    return RSQL_OK;
}

static rsql_u16 scalar_length(void) {
    return WIDE_FIXED_PART_COUNT == 2u
        ? (rsql_u16)(WIDE_FIXED_LENGTH[0] + WIDE_FIXED_LENGTH[1])
        : WIDE_FIXED_LENGTH[0];
}

rsql_u8 rsql_wide_bind_variable_predicates(void) {
    const RsqlColumnInfo* column;
    RsqlBoundPredicate* predicate;
    rsql_u8 source;
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.predicate_count; ++index) {
        predicate = &g_rsql_cursor.predicates[index];
        source = predicate->column;
        column = wide_column(source);
        if ((column->type.tag != RSQL_TYPE_TEXT &&
             column->type.tag != RSQL_TYPE_BLOB) ||
            predicate->op == RSQL_PRED_IS_NULL ||
            predicate->op == RSQL_PRED_IS_NOT_NULL) continue;
        if (index < g_rsql_cursor.join_predicate_count) {
            return RSQL_ERR_UNSUPPORTED_SQL;
        }
        predicate->value.integer.bytes[0] = (rsql_u8)column->offset;
        predicate->value.integer.bytes[1] = column->type.tag;
        predicate->value.integer.bytes[2] = source;
        RSQL_VARIABLE_PREDICATE_MASK |= (rsql_u8)(1u << index);
    }
    for (index = 0u; index < g_rsql_statement.subquery_predicate_count;
         ++index) {
        source = (rsql_u8)g_rsql_statement.columns[index].type.parameter;
        column = wide_column(source);
        if ((column->type.tag == RSQL_TYPE_TEXT ||
             column->type.tag == RSQL_TYPE_BLOB) &&
            g_rsql_statement.columns[index].type.tag != RSQL_PRED_IS_NULL &&
            g_rsql_statement.columns[index].type.tag !=
                RSQL_PRED_IS_NOT_NULL) return RSQL_ERR_UNSUPPORTED_SQL;
    }
    if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
        RSQL_VARIABLE_PREDICATE_SOURCE = 3u;
    }
    return RSQL_OK;
}

static rsql_u8 scalar_copy_chunk(rsql_u16 offset, rsql_u16 end,
                                 rsql_u8* destination) {
    rsql_u16 part_offset;
    rsql_u16 remaining = (rsql_u16)(end - offset);
    rsql_u16 available;
    rsql_u8 part;
    rsql_u8 rc;
    for (part = 0u; part < WIDE_FIXED_PART_COUNT && remaining; ++part) {
        if (offset >= WIDE_FIXED_LENGTH[part]) {
            offset = (rsql_u16)(offset - WIDE_FIXED_LENGTH[part]);
            continue;
        }
        part_offset = offset;
        available = (rsql_u16)(WIDE_FIXED_LENGTH[part] - part_offset);
        if (available > remaining) available = remaining;
        if (WIDE_FIXED_TEXT_MASK & (part ? 2u : 1u)) {
            rc = text_copy(WIDE_FIXED_FIRST_PAGE[part],
                (rsql_u16)(WIDE_FIXED_START[part] + part_offset),
                destination, available);
            if (rc != RSQL_OK) return rc;
        } else memcpy(destination, &WIDE_FIXED_DATA[part][part_offset],
                      available);
        destination += available;
        remaining = (rsql_u16)(remaining - available);
        offset = 0u;
    }
    return RSQL_OK;
}

rsql_u8 rsql_wide_scalar_admin_phase(void) {
    rsql_u16 right_length;
    rsql_u16 offset;
    rsql_u16 end;
    rsql_u16 common;
    rsql_u8 right_byte;
    rsql_u8 left_byte;
    rsql_u8 rc;
    if (g_rsql_variable_compare_source ==
            RSQL_VARIABLE_COMPARE_AGGREGATE_SCALAR) {
        return rsql_wide_bind_aggregate_scalar(
            g_rsql_variable_compare_kind);
    }
    if (g_rsql_variable_compare_kind == 0xFDu) {
        return rsql_wide_bind_admin_phase();
    }
    if (g_rsql_variable_compare_kind == 0xFFu) {
        return rsql_wide_bind_variable_predicates();
    }
    rc = prepare_scalar(g_rsql_variable_compare_kind);
    if (rc != RSQL_OK) return rc;
    if (!RSQL_WIDE_SCALAR_PHASE) {
        RSQL_WIDE_SCALAR_STATE.left_null = WIDE_FIXED_NULL;
        RSQL_WIDE_SCALAR_STATE.left_length = scalar_length();
        end = (rsql_u16)(RSQL_WIDE_SCALAR_OFFSET + 240u);
        if (end > RSQL_WIDE_SCALAR_STATE.left_length) {
            end = RSQL_WIDE_SCALAR_STATE.left_length;
        }
        rc = scalar_copy_chunk(RSQL_WIDE_SCALAR_OFFSET, end,
                               RSQL_WIDE_SCALAR_STATE.buffer);
        if (rc != RSQL_OK) return rc;
        RSQL_WIDE_SCALAR_PHASE = 1u;
        return RSQL_OK;
    }
    right_length = scalar_length();
    RSQL_WIDE_SCALAR_MORE = 0u;
    if (RSQL_WIDE_SCALAR_STATE.left_null != WIDE_FIXED_NULL) {
        g_rsql_variable_compare_result =
            RSQL_WIDE_SCALAR_STATE.left_null ? -1 : 1;
        return RSQL_OK;
    }
    if (RSQL_WIDE_SCALAR_STATE.left_null) {
        g_rsql_variable_compare_result = 0;
        return RSQL_OK;
    }
    if ((g_rsql_cursor.projection_aggregate[g_rsql_variable_compare_kind] &
            RSQL_PROJECTION_OP_MASK) == RSQL_SCALAR_LENGTH) {
        g_rsql_variable_compare_result =
            RSQL_WIDE_SCALAR_STATE.left_length < right_length ? -1 :
            (RSQL_WIDE_SCALAR_STATE.left_length > right_length ? 1 : 0);
        return RSQL_OK;
    }
    common = RSQL_WIDE_SCALAR_STATE.left_length < right_length
        ? RSQL_WIDE_SCALAR_STATE.left_length : right_length;
    end = (rsql_u16)(RSQL_WIDE_SCALAR_OFFSET + 240u);
    if (end > common) end = common;
    rc = scalar_copy_chunk(RSQL_WIDE_SCALAR_OFFSET, end,
                           g_rsql_meta_page1);
    if (rc != RSQL_OK) return rc;
    for (offset = RSQL_WIDE_SCALAR_OFFSET; offset < end; ++offset) {
        left_byte = RSQL_WIDE_SCALAR_STATE.buffer[
            offset - RSQL_WIDE_SCALAR_OFFSET];
        right_byte = g_rsql_meta_page1[offset - RSQL_WIDE_SCALAR_OFFSET];
        if (left_byte >= 'a' && left_byte <= 'z') left_byte -= 'a' - 'A';
        if (right_byte >= 'a' && right_byte <= 'z') right_byte -= 'a' - 'A';
        if (left_byte != right_byte) {
            g_rsql_variable_compare_result = left_byte < right_byte ? -1 : 1;
            return RSQL_OK;
        }
    }
    if (end < common) {
        RSQL_WIDE_SCALAR_MORE = 1u;
        g_rsql_variable_compare_result = 0;
        return RSQL_OK;
    }
    g_rsql_variable_compare_result =
        RSQL_WIDE_SCALAR_STATE.left_length < right_length ? -1 :
        (RSQL_WIDE_SCALAR_STATE.left_length > right_length ? 1 : 0);
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_aggregate_scalar_compare_admin_c(rsql_u8* buffer) {
    rsql_u8 rc = RSQL_OK;
    rsql_u8 row_owner =
        (g_rsql_cursor.join_type != RSQL_JOIN_NONE ||
         (g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE &&
          g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN)) ? 6u : 1u;
    RSQL_WIDE_SCALAR_STATE.buffer = buffer;
    RSQL_WIDE_SCALAR_OFFSET = 0u;
    do {
        RSQL_WIDE_SCALAR_PHASE = 0u;
        RSQL_WIDE_SCALAR_MORE = 0u;
        g_rsql_aggregate_scalar_bridge_mode =
            RSQL_AGGREGATE_SCALAR_BRIDGE_ROW;
        g_rsql_variable_compare_source = row_owner;
        rc = rsql_query_variable_compare_owner(8u);
        g_rsql_aggregate_scalar_bridge_mode =
            RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE;
        g_rsql_variable_compare_kind = RSQL_WIDE_SCALAR_STATE.result;
        g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_WIDE_SCALAR;
        if (rc == RSQL_OK) rc = rsql_wide_scalar_admin_phase();
        if (rc == RSQL_OK) {
            g_rsql_aggregate_scalar_bridge_mode =
                RSQL_AGGREGATE_SCALAR_BRIDGE_ROW;
            g_rsql_variable_compare_source = row_owner;
            rc = rsql_query_variable_compare_owner(8u);
            g_rsql_aggregate_scalar_bridge_mode =
                RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE;
        }
        g_rsql_variable_compare_kind = RSQL_WIDE_SCALAR_STATE.result;
        g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_WIDE_SCALAR;
        if (rc == RSQL_OK) rc = rsql_wide_scalar_admin_phase();
        RSQL_WIDE_SCALAR_OFFSET =
            (rsql_u16)(RSQL_WIDE_SCALAR_OFFSET + 240u);
    } while (rc == RSQL_OK && RSQL_WIDE_SCALAR_MORE);
    *RSQL_WIDE_SCALAR_STATE.comparison = g_rsql_variable_compare_result;
    return rc;
}

#include <string.h>

#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define SQL_FALSE   0u
#define SQL_TRUE    1u
#define SQL_UNKNOWN 2u

#define DIR_NEXT    6u
#define DIR_ENTRIES 8u
#define ENTRY_BYTES 20u
#define ENTRY_COUNT 12u
#define ENTRY_HANDLE 2u
#define ENTRY_FIRST  6u
#define ENTRY_LENGTH 8u

#define BLOB_NEXT 6u
#define BLOB_USED 8u
#define BLOB_DATA 10u
#define BLOB_PAYLOAD (RSQL_REU_PAGE_SIZE - BLOB_DATA)

typedef struct VariablePredicateState {
    rsql_u16 value_first;
    rsql_u16 value_length;
    rsql_u16 cache_page;
    rsql_u16 cache_start;
    rsql_u16 cache_used;
    rsql_u16 cache_next;
} VariablePredicateState;

#define VP_STATE (*(VariablePredicateState*)RSQL_VARIABLE_PREDICATE_STATE)
#define g_value_first  VP_STATE.value_first
#define g_value_length VP_STATE.value_length
#define g_cache_page   VP_STATE.cache_page
#define g_cache_start  VP_STATE.cache_start
#define g_cache_used   VP_STATE.cache_used
#define g_cache_next   VP_STATE.cache_next

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ('a' - 'A'));
    }
    return value;
}

static rsql_u8 find_value(const rsql_u8* handle, rsql_u8 kind) {
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
        for (slot = 0u; slot < ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(DIR_ENTRIES + (rsql_u16)slot * ENTRY_BYTES);
            if (g_rsql_meta_page0[base] == 1u &&
                memcmp(&g_rsql_meta_page0[base + ENTRY_HANDLE], handle, 4u)
                    == 0) {
                if (g_rsql_meta_page0[base + 1u] != kind) {
                    return RSQL_ERR_CORRUPT_STORAGE;
                }
                g_value_first = rsql_get_u16(
                    &g_rsql_meta_page0[base + ENTRY_FIRST]);
                if (g_rsql_meta_page0[base + ENTRY_LENGTH + 2u] != 0u ||
                    g_rsql_meta_page0[base + ENTRY_LENGTH + 3u] != 0u) {
                    return RSQL_ERR_UNSUPPORTED_SQL;
                }
                g_value_length = rsql_get_u16(
                    &g_rsql_meta_page0[base + ENTRY_LENGTH]);
                g_cache_page = RSQL_PAGE_NONE;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page0[DIR_NEXT]);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 load_cache(rsql_u16 page, rsql_u16 start) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
        g_rsql_meta_page1, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (g_rsql_meta_page1[0] != 'R' || g_rsql_meta_page1[1] != 'B' ||
        g_rsql_meta_page1[2] != 'L' || g_rsql_meta_page1[3] != 'B') {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    g_cache_used = rsql_get_u16(&g_rsql_meta_page1[BLOB_USED]);
    if (g_cache_used == 0u || g_cache_used > BLOB_PAYLOAD) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    g_cache_page = page;
    g_cache_start = start;
    g_cache_next = rsql_get_u16(&g_rsql_meta_page1[BLOB_NEXT]);
    return RSQL_OK;
}

static rsql_u8 value_byte(rsql_u16 offset, rsql_u8* value_out) {
    rsql_u16 page;
    rsql_u16 start;
    rsql_u8 rc;
    if (offset >= g_value_length) return RSQL_ERR_CORRUPT_STORAGE;
    if (g_cache_page != RSQL_PAGE_NONE && offset >= g_cache_start &&
        offset < g_cache_start + g_cache_used) {
        *value_out = g_rsql_meta_page1[BLOB_DATA +
            (rsql_u16)(offset - g_cache_start)];
        return RSQL_OK;
    }
    if (g_cache_page != RSQL_PAGE_NONE &&
        offset == g_cache_start + g_cache_used) {
        page = g_cache_next;
        start = offset;
    } else {
        page = g_value_first;
        start = 0u;
    }
    while (page != RSQL_PAGE_NONE) {
        rc = load_cache(page, start);
        if (rc != RSQL_OK) return rc;
        if (offset < start + g_cache_used) {
            *value_out = g_rsql_meta_page1[BLOB_DATA +
                (rsql_u16)(offset - start)];
            return RSQL_OK;
        }
        start += g_cache_used;
        if (start > g_value_length) return RSQL_ERR_CORRUPT_STORAGE;
        page = g_cache_next;
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 op_matches(rsql_i8 comparison, rsql_u8 op) {
    if (op == RSQL_PRED_EQ) return comparison == 0;
    if (op == RSQL_PRED_NE) return comparison != 0;
    if (op == RSQL_PRED_LT) return comparison < 0;
    if (op == RSQL_PRED_LE) return comparison <= 0;
    if (op == RSQL_PRED_GT) return comparison > 0;
    return comparison >= 0;
}

static rsql_u8 compare_value(const RsqlBoundPredicate* predicate,
                             rsql_u8 kind, rsql_u8* truth_out) {
    rsql_u16 length = g_value_length;
    rsql_u8 limit = predicate->value.length;
    rsql_u8 index;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 rc;
    rsql_i8 comparison = 0;
    if (length < limit) limit = (rsql_u8)length;
    for (index = 0u; index < limit; ++index) {
        rc = value_byte(index, &left);
        if (rc != RSQL_OK) return rc;
        right = (rsql_u8)predicate->value.string[index];
        if (kind == RSQL_TYPE_TEXT) {
            left = folded(left);
            right = folded(right);
        }
        if (left < right) comparison = -1;
        else if (left > right) comparison = 1;
        if (comparison != 0) break;
    }
    if (comparison == 0) {
        if (length < predicate->value.length) comparison = -1;
        else if (length > predicate->value.length) comparison = 1;
    }
    *truth_out = op_matches(comparison, predicate->op)
        ? SQL_TRUE : SQL_FALSE;
    return RSQL_OK;
}

static rsql_u8 like_value(const RsqlParsedValue* pattern,
                          rsql_u8* truth_out) {
    rsql_u16 input = 0u;
    rsql_u16 retry_input = 0u;
    rsql_u8 position = 0u;
    rsql_u8 retry_pattern = 0xFFu;
    rsql_u8 byte;
    rsql_u8 pattern_byte;
    rsql_u8 rc;
    while (input < g_value_length) {
        rc = value_byte(input, &byte);
        if (rc != RSQL_OK) return rc;
        if (position < pattern->length) {
            pattern_byte = (rsql_u8)pattern->string[position];
            if (pattern_byte == '_' || folded(pattern_byte) == folded(byte)) {
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

rsql_u8 rsql_query_variable_predicates_phase(void) {
    const RsqlBoundPredicate* predicate;
    rsql_u8 index;
    rsql_u8 mask = 1u;
    rsql_u8 source;
    rsql_u8 rc;
    const rsql_u8* row;
    for (index = 0u; index < g_rsql_cursor.predicate_count; ++index) {
        if (!(RSQL_VARIABLE_PREDICATE_MASK & mask)) {
            mask <<= 1u;
            continue;
        }
        predicate = &g_rsql_cursor.predicates[index];
        source = RSQL_VARIABLE_PREDICATE_SOURCE;
        if (source == 2u || source == 3u) {
            source = predicate->value.integer.bytes[2];
        }
        if (RSQL_VARIABLE_PREDICATE_SOURCE == 3u) {
            if (source & RSQL_SOURCE_SUBQUERY) row = g_rsql_execution.row;
            else if (source & RSQL_SOURCE_INNER) {
                row = g_rsql_cursor.scan_row;
            } else row = g_rsql_cursor.row;
        } else row = source ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
        if (RSQL_VARIABLE_PREDICATE_SOURCE == 2u &&
            source && g_rsql_cursor.join_inner_null) {
            RSQL_VARIABLE_PREDICATE_TRUTH[index] = SQL_UNKNOWN;
            mask <<= 1u;
            continue;
        }
        source = predicate->column & RSQL_SOURCE_COLUMN_MASK;
        if (row[0] & (rsql_u8)(1u << source)) {
            RSQL_VARIABLE_PREDICATE_TRUTH[index] = SQL_UNKNOWN;
            mask <<= 1u;
            continue;
        }
        rc = find_value(&row[predicate->value.integer.bytes[0]],
                        predicate->value.integer.bytes[1]);
        if (rc != RSQL_OK) return rc;
        if (predicate->op == RSQL_PRED_LIKE) {
            rc = like_value(&predicate->value,
                &RSQL_VARIABLE_PREDICATE_TRUTH[index]);
        } else {
            rc = compare_value(predicate,
                predicate->value.integer.bytes[1],
                &RSQL_VARIABLE_PREDICATE_TRUTH[index]);
        }
        if (rc != RSQL_OK) return rc;
        mask <<= 1u;
    }
    return RSQL_OK;
}

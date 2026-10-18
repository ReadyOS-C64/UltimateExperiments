#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_query.h"

static const rsql_u8 FLOAT_ONE[5] = { 0x81u, 0u, 0u, 0u, 0u };

typedef struct JoinPairId {
    RsqlRowId outer;
    RsqlRowId inner;
    rsql_u8 inner_null;
} JoinPairId;

/* Prefix-compatible with the administrative WideScalarState. Slot 6 only
 * owns the pair identities and result target; the admin overlay owns the
 * streamed buffer and comparison scratch that follow this prefix. */
typedef struct JoinAggregateScalarState {
    const JoinPairId* left;
    const JoinPairId* right;
    rsql_i8* comparison;
    rsql_u8 result;
} JoinAggregateScalarState;

#define RSQL_JOIN_AGGREGATE_SCALAR_STATE \
    (*(JoinAggregateScalarState*)&g_rsql_statement.enum_values[0])
#define RSQL_JOIN_AGGREGATE_SCALAR_PHASE \
    (g_rsql_variable_compare_left[2])

rsql_u8 __fastcall__ rsql_join_aggregate_column_mask(rsql_u8 column);
void __fastcall__ rsql_join_aggregate_i64_increment(RsqlI64* value);
rsql_u8 __fastcall__ rsql_join_aggregate_i64_zero(const RsqlI64* value);
void __fastcall__ rsql_join_aggregate_i64_negate(RsqlI64* value);
rsql_u8 __fastcall__ rsql_join_aggregate_integer_width(rsql_u8 tag);

#define column_mask rsql_join_aggregate_column_mask
#define i64_increment rsql_join_aggregate_i64_increment
#define i64_zero_value rsql_join_aggregate_i64_zero
#define i64_negate rsql_join_aggregate_i64_negate
#define integer_width rsql_join_aggregate_integer_width

static const RsqlColumnInfo* source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static const rsql_u8* source_row(rsql_u8 source) {
    return (source & RSQL_SOURCE_INNER)
        ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
}

static rsql_u8 source_null(rsql_u8 source) {
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    return (source_row(source)[0] & column_mask(source)) != 0u;
}

static void i64_add_signed(RsqlI64* total, const rsql_u8* value,
                           rsql_u8 width) {
    rsql_u16 carry = 0u;
    rsql_u8 fill = (value[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = 0u; index < sizeof(total->bytes); ++index) {
        carry = (rsql_u16)total->bytes[index] +
            (index < width ? value[index] : fill) + carry;
        total->bytes[index] = (rsql_u8)carry;
        carry >>= 8u;
    }
}

static void i64_set_signed(RsqlI64* destination, const rsql_u8* value,
                           rsql_u8 width) {
    rsql_u8 fill = (value[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = 0u; index < sizeof(destination->bytes); ++index) {
        destination->bytes[index] = index < width ? value[index] : fill;
    }
}

static rsql_i8 i64_unsigned_compare(const RsqlI64* left,
                                    const RsqlI64* right) {
    rsql_u8 index = sizeof(left->bytes);
    while (index != 0u) {
        --index;
        if (left->bytes[index] < right->bytes[index]) return -1;
        if (left->bytes[index] > right->bytes[index]) return 1;
    }
    return 0;
}

static rsql_i8 i64_signed_compare(const RsqlI64* left,
                                  const RsqlI64* right) {
    rsql_u8 left_negative = (left->bytes[7] & 0x80u) != 0u;
    rsql_u8 right_negative = (right->bytes[7] & 0x80u) != 0u;
    if (left_negative != right_negative) return left_negative ? -1 : 1;
    return i64_unsigned_compare(left, right);
}

static void i64_shift_left(RsqlI64* value) {
    rsql_u8 carry = 0u;
    rsql_u8 next;
    rsql_u8 index;
    for (index = 0u; index < sizeof(value->bytes); ++index) {
        next = (value->bytes[index] & 0x80u) != 0u;
        value->bytes[index] = (rsql_u8)((value->bytes[index] << 1u) | carry);
        carry = next;
    }
}

static void i64_unsigned_subtract(RsqlI64* left, const RsqlI64* right) {
    rsql_u16 borrow = 0u;
    rsql_u16 subtrahend;
    rsql_u8 index;
    for (index = 0u; index < sizeof(left->bytes); ++index) {
        subtrahend = (rsql_u16)right->bytes[index] + borrow;
        borrow = left->bytes[index] < subtrahend ? 1u : 0u;
        left->bytes[index] = (rsql_u8)((rsql_u16)left->bytes[index] -
                                      subtrahend);
    }
}

static void i64_divide_signed(RsqlI64* numerator,
                              const RsqlI64* denominator) {
    RsqlI64 magnitude;
    RsqlI64 remainder;
    RsqlI64 quotient;
    rsql_u8 negative = (numerator->bytes[7] & 0x80u) != 0u;
    rsql_u8 bit = 64u;
    memcpy(&magnitude, numerator, sizeof(magnitude));
    if (negative) i64_negate(&magnitude);
    memset(&remainder, 0, sizeof(remainder));
    memset(&quotient, 0, sizeof(quotient));
    while (bit != 0u) {
        --bit;
        i64_shift_left(&remainder);
        remainder.bytes[0] |= (rsql_u8)
            ((magnitude.bytes[bit >> 3u] >> (bit & 7u)) & 1u);
        if (i64_unsigned_compare(&remainder, denominator) >= 0) {
            i64_unsigned_subtract(&remainder, denominator);
            quotient.bytes[bit >> 3u] |= (rsql_u8)(1u << (bit & 7u));
        }
    }
    if (negative) i64_negate(&quotient);
    memcpy(numerator, &quotient, sizeof(*numerator));
}

static void float_add(rsql_u8* accumulator, const rsql_u8* value) {
    memcpy(rsql_float_a, accumulator, RSQL_FLOAT5_BYTES);
    memcpy(rsql_float_b, value, RSQL_FLOAT5_BYTES);
    rsql_float_destination = accumulator;
    rsql_float_add_abi();
}

static void float_divide(rsql_u8* numerator, const rsql_u8* denominator) {
    memcpy(rsql_float_a, numerator, RSQL_FLOAT5_BYTES);
    memcpy(rsql_float_b, denominator, RSQL_FLOAT5_BYTES);
    rsql_float_destination = numerator;
    rsql_float_div_abi();
}

static rsql_i8 float_compare(const rsql_u8* left, const rsql_u8* right) {
    rsql_u8 left_negative;
    rsql_u8 right_negative;
    rsql_u8 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (left[0] == 0u && right[0] == 0u) return 0;
    left_negative = left[0] != 0u && (left[1] & 0x80u) != 0u;
    right_negative = right[0] != 0u && (right[1] & 0x80u) != 0u;
    if (left_negative != right_negative) return left_negative ? -1 : 1;
    for (index = 0u; index < RSQL_FLOAT5_BYTES; ++index) {
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

static void aggregate_reset(void) {
    rsql_aggregate_reset_state();
}

static void aggregate_pair(void) {
    const RsqlColumnInfo* column;
    const rsql_u8* value;
    RsqlI64 candidate;
    rsql_i8 comparison;
    rsql_u8 aggregate;
    rsql_u8 source;
    rsql_u8 width;
    rsql_u8 result;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        aggregate = g_rsql_cursor.projection_aggregate[result];
        if (aggregate == RSQL_AGG_NONE ||
            RSQL_PROJECTION_IS_SCALAR(aggregate)) continue;
        if (aggregate == RSQL_AGG_COUNT_STAR) {
            i64_increment(&g_rsql_cursor.aggregate_values[result]);
            continue;
        }
        source = g_rsql_cursor.projection[result];
        if (source_null(source)) continue;
        if (aggregate == RSQL_AGG_COUNT) {
            i64_increment(&g_rsql_cursor.aggregate_values[result]);
            continue;
        }
        column = source_column(source);
        value = &source_row(source)[column->offset];
        if (column->type.tag == RSQL_TYPE_FLOAT5) {
            if (aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) {
                if (g_rsql_cursor.aggregate_counts[result].bytes[0] == 0u) {
                    memcpy(g_rsql_cursor.aggregate_values[result].bytes,
                           value, RSQL_FLOAT5_BYTES);
                } else {
                    comparison = float_compare(value,
                        g_rsql_cursor.aggregate_values[result].bytes);
                    if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                        (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                        memcpy(g_rsql_cursor.aggregate_values[result].bytes,
                               value, RSQL_FLOAT5_BYTES);
                    }
                }
            } else {
                float_add(g_rsql_cursor.aggregate_values[result].bytes,
                          value);
            }
            float_add(g_rsql_cursor.aggregate_counts[result].bytes,
                      FLOAT_ONE);
            continue;
        }
        width = integer_width(column->type.tag);
        if (aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) {
            i64_set_signed(&candidate, value, width);
            if (i64_zero_value(&g_rsql_cursor.aggregate_counts[result])) {
                g_rsql_cursor.aggregate_values[result] = candidate;
            } else {
                comparison = i64_signed_compare(&candidate,
                    &g_rsql_cursor.aggregate_values[result]);
                if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                    (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                    g_rsql_cursor.aggregate_values[result] = candidate;
                }
            }
        } else {
            i64_add_signed(&g_rsql_cursor.aggregate_values[result], value,
                           width);
        }
        i64_increment(&g_rsql_cursor.aggregate_counts[result]);
    }
}

static void aggregate_finalize(void) {
    const RsqlColumnInfo* column;
    rsql_u8 aggregate;
    rsql_u8 source;
    rsql_u8 result;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        aggregate = g_rsql_cursor.projection_aggregate[result];
        if (aggregate != RSQL_AGG_SUM && aggregate != RSQL_AGG_AVG &&
            aggregate != RSQL_AGG_MIN && aggregate != RSQL_AGG_MAX) continue;
        source = g_rsql_cursor.projection[result];
        column = source_column(source);
        if (column->type.tag == RSQL_TYPE_FLOAT5) {
            if (g_rsql_cursor.aggregate_counts[result].bytes[0] == 0u) {
                g_rsql_cursor.aggregate_nulls |= column_mask(result);
            } else if (aggregate == RSQL_AGG_AVG) {
                float_divide(g_rsql_cursor.aggregate_values[result].bytes,
                    g_rsql_cursor.aggregate_counts[result].bytes);
            }
        } else if (i64_zero_value(&g_rsql_cursor.aggregate_counts[result])) {
            g_rsql_cursor.aggregate_nulls |= column_mask(result);
        } else if (aggregate == RSQL_AGG_AVG) {
            i64_divide_signed(&g_rsql_cursor.aggregate_values[result],
                              &g_rsql_cursor.aggregate_counts[result]);
        }
    }
}

static void restart_join(void) {
    g_rsql_cursor.finished = 0u;
    g_rsql_cursor.positioned = 0u;
    g_rsql_cursor.join_outer_started = 0u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    g_rsql_cursor.join_inner_null = 0u;
}

static void current_pair(JoinPairId* pair) {
    pair->outer = g_rsql_cursor.row_id;
    pair->inner = g_rsql_cursor.join_row_id;
    pair->inner_null = g_rsql_cursor.join_inner_null;
}

static rsql_u8 same_pair(const JoinPairId* left, const JoinPairId* right) {
    if (left->outer.page != right->outer.page ||
        left->outer.slot != right->outer.slot ||
        left->inner_null != right->inner_null) return 0u;
    if (left->inner_null) return 1u;
    return left->inner.page == right->inner.page &&
           left->inner.slot == right->inner.slot;
}

static rsql_u16 group_width(const RsqlColumnInfo* column) {
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_I8 ||
        column->type.tag == RSQL_TYPE_ENUM8) return 1u;
    if (column->type.tag == RSQL_TYPE_I16 ||
        column->type.tag == RSQL_TYPE_FIXED8_8 ||
        column->type.tag == RSQL_TYPE_ENUM16) return 2u;
    if (column->type.tag == RSQL_TYPE_I32) return 4u;
    if (column->type.tag == RSQL_TYPE_I64) return 8u;
    if (column->type.tag == RSQL_TYPE_FLOAT5) return RSQL_FLOAT5_BYTES;
    return column->type.parameter;
}

static rsql_u8 read_pair_source(const JoinPairId* pair, rsql_u8 source,
                                rsql_u8* destination) {
    if (source & RSQL_SOURCE_INNER) {
        if (pair->inner_null) return RSQL_OK;
        return rsql_query_join_aggregate_read(
            g_rsql_cursor.join_table_page, g_rsql_cursor.join_row_width,
            &pair->inner, destination);
    }
    return rsql_query_join_aggregate_read(
        g_rsql_cursor.table_page, g_rsql_cursor.row_width,
        &pair->outer, destination);
}

static rsql_u8 pair_source_null(const JoinPairId* pair, rsql_u8 source,
                                const rsql_u8* row) {
    if ((source & RSQL_SOURCE_INNER) && pair->inner_null) return 1u;
    return (row[0] & column_mask(source)) != 0u;
}

static rsql_u8 compare_pair_source(const JoinPairId* left,
                                   const JoinPairId* right,
                                   rsql_u8 source,
                                   rsql_i8* comparison_out);

/* Compare a saved candidate with the pair currently positioned by the raw
 * join producer. Candidate reads use the execution scratch row, leaving the
 * producer's outer/inner rows intact so its continuation remains resumable. */
static rsql_u8 same_candidate_group(const JoinPairId* candidate,
                                    rsql_u8* same_out) {
    static JoinPairId current;
    static rsql_i8 comparison;
    static rsql_u8 source;
    static rsql_u8 index;
    static rsql_u8 rc;
    *same_out = 0u;
    current_pair(&current);
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        rc = compare_pair_source(candidate, &current, source, &comparison);
        if (rc != RSQL_OK || comparison != 0) return rc;
    }
    *same_out = 1u;
    return RSQL_OK;
}

/* A group representative is the first matching join pair with that key.
 * This bounded prefix rescan detects earlier equal keys and deliberately
 * leaves the raw producer positioned back on candidate for the caller. */
static rsql_u8 candidate_duplicate(const JoinPairId* candidate,
                                   rsql_u8* duplicate_out,
                                   RsqlCursorNextRequest* request) {
    JoinPairId current;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_pair(&current);
        if (same_pair(candidate, &current)) return RSQL_OK;
        rc = same_candidate_group(candidate, &same);
        if (rc != RSQL_OK) return rc;
        if (same) *duplicate_out = 1u;
    }
}

static rsql_u8 load_pair(const JoinPairId* pair) {
    rsql_u8 rc;
    rc = rsql_query_join_aggregate_read(
        g_rsql_cursor.table_page, g_rsql_cursor.row_width,
        &pair->outer, g_rsql_cursor.row);
    if (rc != RSQL_OK) return rc;
    if (!pair->inner_null) {
        rc = rsql_query_join_aggregate_read(
            g_rsql_cursor.join_table_page, g_rsql_cursor.join_row_width,
            &pair->inner, g_rsql_cursor.scan_row);
        if (rc != RSQL_OK) return rc;
    }
    g_rsql_cursor.row_id = pair->outer;
    g_rsql_cursor.join_row_id = pair->inner;
    g_rsql_cursor.join_inner_null = pair->inner_null;
    return RSQL_OK;
}

rsql_u8 rsql_query_join_aggregate_scalar_row_phase(void) {
    const JoinPairId* pair = RSQL_JOIN_AGGREGATE_SCALAR_PHASE
        ? RSQL_JOIN_AGGREGATE_SCALAR_STATE.right
        : RSQL_JOIN_AGGREGATE_SCALAR_STATE.left;
    return load_pair(pair);
}

static rsql_u8 aggregate_group(const JoinPairId* representative,
                               RsqlCursorNextRequest* request) {
    rsql_u8 same;
    rsql_u8 rc;
    aggregate_reset();
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        rc = same_candidate_group(representative, &same);
        if (rc != RSQL_OK) return rc;
        if (same) aggregate_pair();
    }
    aggregate_finalize();
    rc = load_pair(representative);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.finished = 0u;
    g_rsql_cursor.positioned = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

static rsql_u8 next_group(RsqlCursorNextRequest* request) {
    JoinPairId prior;
    JoinPairId candidate;
    JoinPairId current;
    rsql_u8 after_prior = g_rsql_cursor.positioned ? 0u : 1u;
    rsql_u8 duplicate;
    rsql_u8 rc;
    if (!after_prior) current_pair(&prior);
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        current_pair(&current);
        if (!after_prior) {
            if (same_pair(&prior, &current)) after_prior = 1u;
            continue;
        }
        candidate = current;
        rc = candidate_duplicate(&candidate, &duplicate, request);
        if (rc != RSQL_OK) return rc;
        if (!duplicate) return aggregate_group(&candidate, request);
    }
}

static rsql_u8 folded(rsql_u8 value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - 32u);
    return value;
}

static rsql_i8 compare_group_values(const RsqlColumnInfo* column,
                                    const rsql_u8* left,
                                    const rsql_u8* right) {
    RsqlI64 left_integer;
    RsqlI64 right_integer;
    rsql_u16 width = group_width(column);
    rsql_u16 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (column->type.tag == RSQL_TYPE_CHAR) {
        for (index = 0u; index < width; ++index) {
            left_byte = folded(left[index]);
            right_byte = folded(right[index]);
            if (left_byte < right_byte) return -1;
            if (left_byte > right_byte) return 1;
        }
        return 0;
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return float_compare(left, right);
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        memset(&left_integer, 0, sizeof(left_integer));
        memset(&right_integer, 0, sizeof(right_integer));
        memcpy(left_integer.bytes, left, width);
        memcpy(right_integer.bytes, right, width);
        return i64_unsigned_compare(&left_integer, &right_integer);
    }
    i64_set_signed(&left_integer, left, (rsql_u8)width);
    i64_set_signed(&right_integer, right, (rsql_u8)width);
    return i64_signed_compare(&left_integer, &right_integer);
}

static rsql_u8 compare_pair_source(const JoinPairId* left,
                                   const JoinPairId* right,
                                   rsql_u8 source,
                                   rsql_i8* comparison_out) {
    static const RsqlColumnInfo* column;
    static rsql_u8* right_row;
    static rsql_u8 left_null;
    static rsql_u8 right_null;
    static rsql_u8 rc;
    column = source_column(source);
    right_row = (source & RSQL_SOURCE_INNER)
        ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
    rc = read_pair_source(left, source, g_rsql_execution.row);
    if (rc != RSQL_OK) return rc;
    left_null = pair_source_null(left, source, g_rsql_execution.row);
    rc = read_pair_source(right, source, right_row);
    if (rc != RSQL_OK) return rc;
    right_null = pair_source_null(right, source, right_row);
    if (left_null != right_null) {
        *comparison_out = left_null ? -1 : 1;
    } else if (left_null) {
        *comparison_out = 0;
    } else if (column->type.tag == RSQL_TYPE_TEXT ||
               column->type.tag == RSQL_TYPE_BLOB) {
        g_rsql_variable_compare_source =
            source | RSQL_VARIABLE_COMPARE_COMPLEX;
        rc = rsql_query_variable_compare_owner(6u);
        if (rc != RSQL_OK) return rc;
        *comparison_out = g_rsql_variable_compare_result;
    } else {
        *comparison_out = compare_group_values(column,
            &g_rsql_execution.row[column->offset],
            &right_row[column->offset]);
    }
    return RSQL_OK;
}

static rsql_u8 position_producer(const JoinPairId* pair,
                                 RsqlCursorNextRequest* request) {
    JoinPairId current;
    rsql_u8 rc;
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_pair(&current);
        if (same_pair(pair, &current)) return RSQL_OK;
    }
}

static rsql_u8 compare_pair_aggregate(const JoinPairId* left,
                                      const JoinPairId* right,
                                      rsql_u8 result,
                                      RsqlCursorNextRequest* request,
                                      rsql_i8* comparison_out) {
    RsqlI64 saved;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 source = g_rsql_cursor.projection[result];
    rsql_u8 aggregate = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 is_float;
    rsql_u8 rc;
    rc = aggregate_group(left, request);
    if (rc != RSQL_OK) return rc;
    left_null = (g_rsql_cursor.aggregate_nulls & column_mask(result)) != 0u;
    saved = g_rsql_cursor.aggregate_values[result];
    rc = aggregate_group(right, request);
    if (rc != RSQL_OK) return rc;
    right_null = (g_rsql_cursor.aggregate_nulls & column_mask(result)) != 0u;
    if (left_null != right_null) {
        *comparison_out = left_null ? -1 : 1;
        return RSQL_OK;
    }
    if (left_null) {
        *comparison_out = 0;
        return RSQL_OK;
    }
    is_float = aggregate != RSQL_AGG_COUNT_STAR &&
        aggregate != RSQL_AGG_COUNT &&
        source_column(source)->type.tag == RSQL_TYPE_FLOAT5;
    *comparison_out = is_float
        ? float_compare(saved.bytes,
            g_rsql_cursor.aggregate_values[result].bytes)
        : i64_signed_compare(&saved,
            &g_rsql_cursor.aggregate_values[result]);
    return RSQL_OK;
}

static rsql_u8 compare_pair_scalar(const JoinPairId* left,
                                   const JoinPairId* right,
                                   rsql_u8 result,
                                   rsql_i8* comparison_out) {
    rsql_u8 rc;
    RSQL_JOIN_AGGREGATE_SCALAR_STATE.left = left;
    RSQL_JOIN_AGGREGATE_SCALAR_STATE.right = right;
    RSQL_JOIN_AGGREGATE_SCALAR_STATE.result = result;
    RSQL_JOIN_AGGREGATE_SCALAR_STATE.comparison = comparison_out;
    g_rsql_aggregate_scalar_bridge_mode =
        RSQL_AGGREGATE_SCALAR_BRIDGE_REPLAY;
    rc = rsql_query_variable_compare_owner(6u);
    g_rsql_aggregate_scalar_bridge_mode =
        RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE;
    return rc;
}

static rsql_i8 compare_pair_identity(const JoinPairId* left,
                                     const JoinPairId* right) {
    if (left->outer.page < right->outer.page) return -1;
    if (left->outer.page > right->outer.page) return 1;
    if (left->outer.slot < right->outer.slot) return -1;
    if (left->outer.slot > right->outer.slot) return 1;
    if (left->inner_null != right->inner_null) {
        return left->inner_null ? -1 : 1;
    }
    if (left->inner_null) return 0;
    if (left->inner.page < right->inner.page) return -1;
    if (left->inner.page > right->inner.page) return 1;
    if (left->inner.slot < right->inner.slot) return -1;
    if (left->inner.slot > right->inner.slot) return 1;
    return 0;
}

/* Compare complete group results, then restore the raw producer to left so a
 * bounded selection scan can continue immediately after that candidate. */
static rsql_u8 compare_group_results(const JoinPairId* left,
                                     const JoinPairId* right,
                                     RsqlCursorNextRequest* request,
                                     rsql_i8* comparison_out) {
    rsql_u8 descriptor;
    rsql_u8 index;
    rsql_u8 rc;
    rsql_i8 comparison = 0;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        descriptor = RSQL_AGGREGATE_ORDER_COLUMNS[index];
        if (descriptor & RSQL_ORDER_PROJECTION) {
            descriptor &= RSQL_ORDER_PROJECTION_MASK;
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[descriptor])) {
                rc = compare_pair_scalar(left, right, descriptor,
                                         &comparison);
            } else {
                rc = compare_pair_aggregate(left, right, descriptor,
                                            request, &comparison);
            }
        } else {
            rc = compare_pair_source(left, right, descriptor, &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison != 0) {
            if (g_rsql_cursor.order_desc_mask & column_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            break;
        }
    }
    if (comparison == 0) comparison = compare_pair_identity(left, right);
    rc = position_producer(left, request);
    if (rc != RSQL_OK) return rc;
    *comparison_out = comparison;
    return RSQL_OK;
}

static rsql_u8 same_group_projection(const JoinPairId* left,
                                     const JoinPairId* right,
                                     RsqlCursorNextRequest* request,
                                     rsql_u8* same_out) {
    rsql_i8 comparison;
    rsql_u8 result;
    rsql_u8 rc;
    *same_out = 0u;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[result])) {
            rc = compare_pair_scalar(left, right, result, &comparison);
        } else if (g_rsql_cursor.projection_aggregate[result] !=
                   RSQL_AGG_NONE) {
            rc = compare_pair_aggregate(left, right, result,
                                        request, &comparison);
        } else {
            rc = compare_pair_source(left, right,
                g_rsql_cursor.projection[result], &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison != 0) {
            rc = position_producer(left, request);
            return rc;
        }
    }
    rc = position_producer(left, request);
    if (rc != RSQL_OK) return rc;
    *same_out = 1u;
    return RSQL_OK;
}

static rsql_u8 group_projection_duplicate(
    const JoinPairId* candidate, RsqlCursorNextRequest* request,
    rsql_u8* duplicate_out) {
    JoinPairId prior;
    JoinPairId current;
    rsql_u8 duplicate;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_pair(&current);
        if (same_pair(candidate, &current)) {
            return position_producer(candidate, request);
        }
        prior = current;
        rc = candidate_duplicate(&prior, &duplicate, request);
        if (rc != RSQL_OK) return rc;
        if (!duplicate) {
            rc = same_group_projection(candidate, &prior, request, &same);
            if (rc != RSQL_OK) return rc;
            if (same) {
                *duplicate_out = 1u;
                return position_producer(candidate, request);
            }
            rc = position_producer(&prior, request);
            if (rc != RSQL_OK) return rc;
        }
    }
}

static void last_group(JoinPairId* pair) {
    pair->outer = g_rsql_cursor.update_next_row_id;
    pair->inner.page = g_rsql_cursor.index_page;
    pair->inner.slot = g_rsql_cursor.index_leaf_slot;
    pair->inner_null = g_rsql_cursor.update_scan_started;
}

static void store_last_group(const JoinPairId* pair) {
    g_rsql_cursor.update_next_row_id = pair->outer;
    g_rsql_cursor.index_page = pair->inner.page;
    g_rsql_cursor.index_leaf_slot = pair->inner.slot;
    g_rsql_cursor.update_scan_started = pair->inner_null;
}

static rsql_u8 select_shaped_group(RsqlCursorNextRequest* request,
                                   rsql_u8* found_out) {
    JoinPairId candidate;
    JoinPairId current;
    JoinPairId best;
    JoinPairId last;
    rsql_i8 comparison;
    rsql_u8 duplicate;
    rsql_u8 have_best = 0u;
    rsql_u8 have_last = (g_rsql_cursor.returned_rows != 0u ||
                         g_rsql_cursor.skipped_rows != 0u);
    rsql_u8 rc;
    *found_out = 0u;
    if (have_last) last_group(&last);
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        current_pair(&current);
        candidate = current;
        rc = candidate_duplicate(&candidate, &duplicate, request);
        if (rc != RSQL_OK) return rc;
        if (duplicate) continue;
        if (g_rsql_cursor.distinct) {
            rc = group_projection_duplicate(&candidate, request, &duplicate);
            if (rc != RSQL_OK) return rc;
            if (duplicate) continue;
        }
        if (have_last) {
            rc = compare_group_results(
                &candidate, &last, request, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison <= 0) continue;
        }
        if (have_best) {
            rc = compare_group_results(
                &candidate, &best, request, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison >= 0) continue;
        }
        best = candidate;
        have_best = 1u;
    }
    if (!have_best) return RSQL_OK;
    rc = aggregate_group(&best, request);
    if (rc != RSQL_OK) return rc;
    store_last_group(&best);
    *found_out = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_join_aggregate_result_next_phase(
    RsqlCursorNextRequest* request) {
    rsql_u8 found;
    rsql_u8 rc;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
         g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE) ||
        g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE ||
        (!g_rsql_cursor.distinct && g_rsql_cursor.order_count == 0u)) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.limit_present &&
        g_rsql_cursor.returned_rows >= g_rsql_cursor.limit) {
        g_rsql_cursor.finished = 1u;
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    /* An ungrouped aggregate is intrinsically one row. Ordering and DISTINCT
     * cannot change it, including for an empty join input. */
    if (g_rsql_cursor.group_count == 0u) {
        if (g_rsql_cursor.offset != 0u) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        rc = rsql_query_join_aggregate_next_phase(request);
        if (rc == RSQL_OK && request->has_row) ++g_rsql_cursor.returned_rows;
        return rc;
    }
    for (;;) {
        rc = select_shaped_group(request, &found);
        if (rc != RSQL_OK) return rc;
        if (!found) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            request->has_row = 0u;
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

rsql_u8 __fastcall__ rsql_query_join_aggregate_next_phase(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        (g_rsql_cursor.join_type == RSQL_JOIN_NONE &&
         g_rsql_cursor.subquery_kind == RSQL_SUBQUERY_NONE) ||
        g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.group_count != 0u) return next_group(request);
    aggregate_reset();
    restart_join();
    for (;;) {
        rc = rsql_query_join_aggregate_source_next_phase(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        aggregate_pair();
    }
    aggregate_finalize();
    g_rsql_cursor.positioned = 1u;
    g_rsql_cursor.finished = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

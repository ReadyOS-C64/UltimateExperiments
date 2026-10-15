#include <string.h>

#include "rsql.h"
#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"
#include "rsql_row.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"
#include "wide_internal.h"

#define SQL_FALSE   0u
#define SQL_TRUE    1u
#define SQL_UNKNOWN 2u

#define DELETE_BLOB_DIRECTORY_NEXT 6u
#define DELETE_BLOB_ENTRIES 8u
#define DELETE_BLOB_ENTRY_BYTES 20u
#define DELETE_BLOB_ENTRY_COUNT 12u
#define DELETE_BLOB_ENTRY_STATE 0u
#define DELETE_BLOB_ENTRY_HANDLE 2u
#define DELETE_BLOB_STATE_ACTIVE 1u
#define DELETE_BLOB_STATE_DELETED 2u

#define g_delete_blob_directory g_rsql_meta_page0
static const rsql_u8 FLOAT_ONE[5] = { 0x81u, 0u, 0u, 0u, 0u };

typedef struct RsqlAggregateScan {
    rsql_u16 leaf_page;
    rsql_u8 leaf_slot;
} RsqlAggregateScan;

extern RsqlAggregateScan* g_aggregate_index_scan;
extern RsqlRowId* g_aggregate_index_row;
extern rsql_u8 rsql_aggregate_index_next(void);

static const RsqlColumnInfo* __fastcall__ result_source_column(rsql_u8 source);

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

static rsql_u8 valid_cursor(rsql_u8 cursor) {
    return cursor == 1u && g_rsql_cursor.active;
}

static rsql_u8 column_mask(rsql_u8 column) {
    switch (column) {
        case 0u: return 0x01u;
        case 1u: return 0x02u;
        case 2u: return 0x04u;
        case 3u: return 0x08u;
        case 4u: return 0x10u;
        case 5u: return 0x20u;
        case 6u: return 0x40u;
        case 7u: return 0x80u;
    }
    return 0u;
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
        case RSQL_TYPE_I64: return 8u;
        case RSQL_TYPE_FLOAT5: return 5u;
        case RSQL_TYPE_CHAR: return type->parameter;
    }
    return 0u;
}

static rsql_i8 compare_integer(const rsql_u8* row, rsql_u8 width,
                               const RsqlI64* literal) {
    rsql_u8 row_fill = (row[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 row_negative = row_fill != 0u;
    rsql_u8 literal_negative =
        (literal->bytes[sizeof(literal->bytes) - 1u] & 0x80u) ? 1u : 0u;
    rsql_u8 index = sizeof(literal->bytes);
    rsql_u8 row_byte;
    rsql_u8 literal_byte;
    if (row_negative != literal_negative) {
        if (row_negative) return -1;
        return 1;
    }
    while (index != 0u) {
        --index;
        row_byte = index < width ? row[index] : row_fill;
        literal_byte = literal->bytes[index];
        if (row_byte < literal_byte) return -1;
        if (row_byte > literal_byte) return 1;
    }
    return 0;
}

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ('a' - 'A'));
    }
    return value;
}

static rsql_i8 compare_char(const rsql_u8* row, rsql_u16 width,
                            const RsqlParsedValue* literal) {
    rsql_u16 index;
    rsql_u8 row_byte;
    rsql_u8 literal_byte;
    for (index = 0u; index < width; ++index) {
        row_byte = folded(row[index]);
        literal_byte = index < literal->length
            ? folded((rsql_u8)literal->string[index]) : (rsql_u8)' ';
        if (row_byte < literal_byte) return -1;
        if (row_byte > literal_byte) return 1;
    }
    return 0;
}

static rsql_u8 comparison_matches(rsql_i8 comparison, rsql_u8 op) {
    if (op == RSQL_PRED_EQ) return comparison == 0;
    if (op == RSQL_PRED_NE) return comparison != 0;
    if (op == RSQL_PRED_LT) return comparison < 0;
    if (op == RSQL_PRED_LE) return comparison <= 0;
    if (op == RSQL_PRED_GT) return comparison > 0;
    if (op == RSQL_PRED_GE) return comparison >= 0;
    return 0u;
}

static rsql_u8 like_char(const rsql_u8* row, rsql_u16 width,
                         const RsqlParsedValue* pattern) {
    rsql_u16 row_length = width;
    rsql_u16 row_index = 0u;
    rsql_u16 pattern_index = 0u;
    rsql_u16 star_pattern = 0xFFFFu;
    rsql_u16 star_row = 0u;
    rsql_u8 pattern_byte;
    while (row_length != 0u && row[row_length - 1u] == (rsql_u8)' ') {
        --row_length;
    }
    while (row_index < row_length) {
        if (pattern_index < pattern->length) {
            pattern_byte = (rsql_u8)pattern->string[pattern_index];
            if (pattern_byte == (rsql_u8)'_' ||
                folded(pattern_byte) == folded(row[row_index])) {
                ++pattern_index;
                ++row_index;
                continue;
            }
            if (pattern_byte == (rsql_u8)'%') {
                star_pattern = pattern_index++;
                star_row = row_index;
                continue;
            }
        }
        if (star_pattern != 0xFFFFu) {
            pattern_index = (rsql_u16)(star_pattern + 1u);
            row_index = (rsql_u16)(++star_row);
            continue;
        }
        return 0u;
    }
    while (pattern_index < pattern->length &&
           pattern->string[pattern_index] == '%') ++pattern_index;
    return pattern_index == pattern->length;
}

static rsql_u8 predicate_truth(const rsql_u8* row, rsql_u8 index) {
    const RsqlBoundPredicate* predicate = &g_rsql_cursor.predicates[index];
    const RsqlColumnInfo* column;
    const rsql_u8* value;
    rsql_u8 source;
    rsql_u8 is_null;
    rsql_u8 width;
    rsql_i8 comparison;
    source = predicate->column;
    column = &g_rsql_cursor.columns[source];
    /* Tables are capped at eight columns, so the null map is one byte.  A
     * constant base also avoids cc65 losing the carry source for this indexed
     * access after the preceding structure-pointer calculation. */
    if (row[0] & column_mask(source)) {
        is_null = 1u;
    } else {
        is_null = 0u;
    }
    if (predicate->op == RSQL_PRED_IS_NULL) {
        if (is_null) return SQL_TRUE;
        return SQL_FALSE;
    }
    if (predicate->op == RSQL_PRED_IS_NOT_NULL) {
        if (is_null) return SQL_FALSE;
        return SQL_TRUE;
    }
    if (is_null || predicate->value.kind == RSQL_VALUE_NULL) {
        return SQL_UNKNOWN;
    }
    value = &row[column->offset];
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        return RSQL_VARIABLE_PREDICATE_TRUTH[index];
    }
    if (predicate->op == RSQL_PRED_LIKE) {
        if (like_char(value, column->type.parameter, &predicate->value)) {
            return SQL_TRUE;
        }
        return SQL_FALSE;
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN) {
        if (value[0] < predicate->value.integer.bytes[0]) {
            comparison = -1;
        } else if (value[0] > predicate->value.integer.bytes[0]) {
            comparison = 1;
        } else comparison = 0;
    } else if (column->type.tag == RSQL_TYPE_CHAR) {
        comparison = compare_char(value, column->type.parameter,
                                  &predicate->value);
    } else if (column->type.tag == RSQL_TYPE_FLOAT5) {
        comparison = float_compare(value, predicate->value.integer.bytes);
    } else {
        width = (rsql_u8)value_width(&column->type);
        comparison = compare_integer(value, width, &predicate->value.integer);
    }
    if (comparison_matches(comparison, predicate->op)) return SQL_TRUE;
    return SQL_FALSE;
}

static rsql_u8 row_matches(const rsql_u8* row) {
    rsql_u8 stack[RSQL_PREDICATES_MAX];
    rsql_u8 stack_count = 0u;
    rsql_u8 opcode;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    if (!g_rsql_cursor.where_present) return 1u;
    for (index = 0u; index < g_rsql_cursor.bool_program_count; ++index) {
        opcode = g_rsql_cursor.bool_program[index];
        if (opcode < RSQL_PREDICATES_MAX) {
            if (opcode >= g_rsql_cursor.predicate_count ||
                stack_count >= RSQL_PREDICATES_MAX) return 0u;
            stack[stack_count++] = predicate_truth(row, opcode);
        } else if (opcode == RSQL_BOOL_NOT) {
            if (stack_count == 0u) return 0u;
            if (stack[stack_count - 1u] == SQL_TRUE) {
                stack[stack_count - 1u] = SQL_FALSE;
            } else if (stack[stack_count - 1u] == SQL_FALSE) {
                stack[stack_count - 1u] = SQL_TRUE;
            }
        } else {
            if (stack_count < 2u) return 0u;
            right = stack[--stack_count];
            left = stack[stack_count - 1u];
            if (opcode == RSQL_BOOL_AND) {
                if (left == SQL_FALSE || right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else if (left == SQL_TRUE && right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else {
                    stack[stack_count - 1u] = SQL_UNKNOWN;
                }
            } else if (opcode == RSQL_BOOL_OR) {
                if (left == SQL_TRUE || right == SQL_TRUE) {
                    stack[stack_count - 1u] = SQL_TRUE;
                } else if (left == SQL_FALSE && right == SQL_FALSE) {
                    stack[stack_count - 1u] = SQL_FALSE;
                } else {
                    stack[stack_count - 1u] = SQL_UNKNOWN;
                }
            } else return 0u;
        }
    }
    if (stack_count != 1u || stack[0] != SQL_TRUE) return 0u;
    return 1u;
}

static void i64_zero(RsqlI64* value) {
    memset(value->bytes, 0, sizeof(value->bytes));
}

static rsql_u8 i64_is_zero(const RsqlI64* value) {
    rsql_u8 index;
    for (index = 0u; index < sizeof(value->bytes); ++index) {
        if (value->bytes[index] != 0u) return 0u;
    }
    return 1u;
}

static void i64_increment(RsqlI64* value) {
    rsql_u8 index;
    for (index = 0u; index < sizeof(value->bytes); ++index) {
        ++value->bytes[index];
        if (value->bytes[index] != 0u) break;
    }
}

static rsql_u8 valid_delete_blob_directory(void) {
    return g_delete_blob_directory[0] == 'R' &&
           g_delete_blob_directory[1] == 'B' &&
           g_delete_blob_directory[2] == 'D' &&
           g_delete_blob_directory[3] == 'R' &&
           g_delete_blob_directory[4] == RSQL_STORAGE_VERSION &&
           g_delete_blob_directory[RSQL_PAGE_CHECKSUM_OFFSET] ==
               rsql_page_checksum(g_delete_blob_directory);
}

static rsql_u8 delete_blob_handle(const rsql_u8* handle) {
    rsql_u16 page = g_rsql_cursor.blob_directory;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(page),
                           g_delete_blob_directory,
                           sizeof(g_delete_blob_directory));
        if (rc != RSQL_OK) return rc;
        if (!valid_delete_blob_directory()) return RSQL_ERR_CORRUPT_STORAGE;
        for (slot = 0u; slot < DELETE_BLOB_ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(DELETE_BLOB_ENTRIES +
                              (rsql_u16)slot * DELETE_BLOB_ENTRY_BYTES);
            if (g_delete_blob_directory[base + DELETE_BLOB_ENTRY_STATE] ==
                    DELETE_BLOB_STATE_ACTIVE &&
                memcmp(&g_delete_blob_directory[
                           base + DELETE_BLOB_ENTRY_HANDLE], handle, 4u) == 0) {
                g_delete_blob_directory[base + DELETE_BLOB_ENTRY_STATE] =
                    DELETE_BLOB_STATE_DELETED;
                g_delete_blob_directory[RSQL_PAGE_CHECKSUM_OFFSET] =
                    rsql_page_checksum(g_delete_blob_directory);
                return rsql_reu_write(rsql_reu_page_address(page),
                                      g_delete_blob_directory,
                                      sizeof(g_delete_blob_directory));
            }
        }
        page = rsql_get_u16(
            &g_delete_blob_directory[DELETE_BLOB_DIRECTORY_NEXT]);
    }
    return RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 delete_row_blobs(const rsql_u8* row) {
    const RsqlColumnInfo* column;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_cursor.source_column_count; ++index) {
        column = &g_rsql_cursor.columns[index];
        if ((column->type.tag == RSQL_TYPE_TEXT ||
             column->type.tag == RSQL_TYPE_BLOB) &&
            !(row[0] & column_mask(index))) {
            rc = delete_blob_handle(&row[column->offset]);
            if (rc != RSQL_OK) return rc;
        }
    }
    return RSQL_OK;
}

static rsql_u8 mutation_begin(RsqlI64* affected_rows) {
    if (!affected_rows) return RSQL_ERR_INVALID_ARGUMENT;
    i64_zero(affected_rows);
    g_rsql_cursor.update_scan_started = 0u;
    g_rsql_cursor.update_next_valid = 0u;
    return RSQL_OK;
}

static rsql_u8 mutation_next(void) {
    RsqlRowId current;
    RsqlRowId next;
    rsql_u8 next_rc;
    rsql_u8 rc;
    if (!g_rsql_cursor.update_scan_started) {
        g_rsql_cursor.update_scan_started = 1u;
        rc = rsql_row_first(g_rsql_cursor.table_page, &current);
    } else if (g_rsql_cursor.update_next_valid) {
        current = g_rsql_cursor.update_next_row_id;
        rc = RSQL_OK;
    } else return RSQL_ERR_NOT_FOUND;
    while (rc == RSQL_OK) {
        rc = rsql_row_read(g_rsql_cursor.table_page, &current,
                           g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
        if (rc != RSQL_OK) return rc;
        next_rc = rsql_row_next(g_rsql_cursor.table_page, &current, &next);
        if (next_rc != RSQL_OK && next_rc != RSQL_ERR_NOT_FOUND) {
            return next_rc;
        }
        g_rsql_cursor.update_next_valid = next_rc == RSQL_OK ? 1u : 0u;
        if (g_rsql_cursor.update_next_valid) {
            g_rsql_cursor.update_next_row_id = next;
        }
        g_rsql_cursor.row_id = current;
        if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
            return RSQL_QUERY_PHASE_PREDICATE;
        }
        if (row_matches(g_rsql_cursor.row)) return RSQL_OK;
        if (!g_rsql_cursor.update_next_valid) return RSQL_ERR_NOT_FOUND;
        current = next;
    }
    return rc;
}

rsql_u8 __fastcall__ rsql_query_delete_begin_phase(RsqlI64* affected_rows) {
    return mutation_begin(affected_rows);
}

rsql_u8 rsql_query_delete_next_phase(void) {
    return mutation_next();
}

rsql_u8 __fastcall__ rsql_query_delete_apply_phase(RsqlI64* affected_rows) {
    rsql_u8 rc;
    if (!affected_rows) return RSQL_ERR_INVALID_ARGUMENT;
    rc = delete_row_blobs(g_rsql_cursor.row);
    if (rc == RSQL_OK) {
        rc = rsql_row_delete(g_rsql_cursor.table_page, &g_rsql_cursor.row_id);
    }
    if (rc == RSQL_OK) i64_increment(affected_rows);
    return rc;
}

rsql_u8 __fastcall__ rsql_query_delete_phase(RsqlI64* affected_rows) {
    rsql_u8 rc = rsql_query_delete_begin_phase(affected_rows);
    while (rc == RSQL_OK) {
        rc = rsql_query_delete_next_phase();
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc == RSQL_OK) rc = rsql_query_delete_apply_phase(affected_rows);
    }
    return rc;
}

static rsql_u8 update_row_value(rsql_u8* row, rsql_u8 assignment) {
    const RsqlParsedValue* value = &g_rsql_statement.values[assignment];
    rsql_u8 source = g_rsql_cursor.update_columns[assignment];
    const RsqlColumnInfo* column = &g_rsql_cursor.columns[source];
    rsql_u8* destination = &row[column->offset];
    rsql_u16 width = value_width(&column->type);
    rsql_u8 byte;
    if (value->kind == RSQL_VALUE_NULL) {
        row[0] |= column_mask(source);
        memset(destination, 0, width);
        return RSQL_OK;
    }
    row[0] &= (rsql_u8)~column_mask(source);
    if (column->type.tag == RSQL_TYPE_BOOLEAN) {
        destination[0] = value->integer.bytes[0];
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_FIXED8_8) {
        destination[0] = 0u;
        destination[1] = value->integer.bytes[0];
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        memcpy(destination, value->integer.bytes, 5u);
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_CHAR) {
        memset(destination, ' ', width);
        memcpy(destination, value->string, value->length);
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) return RSQL_OK;
    if (column->type.tag == RSQL_TYPE_I8 ||
        column->type.tag == RSQL_TYPE_I16 ||
        column->type.tag == RSQL_TYPE_I32 ||
        column->type.tag == RSQL_TYPE_I64 ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        for (byte = 0u; byte < (rsql_u8)width; ++byte) {
            destination[byte] = value->integer.bytes[byte];
        }
        return RSQL_OK;
    }
    return RSQL_ERR_UNSUPPORTED_SQL;
}

rsql_u8 __fastcall__ rsql_query_update_begin_phase(RsqlI64* affected_rows) {
    return mutation_begin(affected_rows);
}

rsql_u8 rsql_query_update_next_phase(void) {
    return mutation_next();
}

rsql_u8 __fastcall__ rsql_query_update_apply_phase(RsqlI64* affected_rows) {
    rsql_u8 assignment;
    rsql_u8 rc;
    if (!affected_rows) return RSQL_ERR_INVALID_ARGUMENT;
    for (assignment = 0u; assignment < g_rsql_cursor.update_count;
         ++assignment) {
        rc = update_row_value(g_rsql_cursor.row, assignment);
        if (rc != RSQL_OK) return rc;
    }
    rc = rsql_row_update(g_rsql_cursor.table_page, &g_rsql_cursor.row_id,
                         g_rsql_cursor.row, g_rsql_cursor.row_width);
    if (rc == RSQL_OK) i64_increment(affected_rows);
    return rc;
}

rsql_u8 __fastcall__ rsql_query_update_phase(RsqlI64* affected_rows) {
    rsql_u8 rc = rsql_query_update_begin_phase(affected_rows);
    while (rc == RSQL_OK) {
        rc = rsql_query_update_next_phase();
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc == RSQL_OK) rc = rsql_query_update_apply_phase(affected_rows);
    }
    return rc;
}

static void i64_negate(RsqlI64* value) {
    rsql_u16 carry = 1u;
    rsql_u8 index;
    for (index = 0u; index < sizeof(value->bytes); ++index) {
        carry = (rsql_u16)((rsql_u8)~value->bytes[index]) + carry;
        value->bytes[index] = (rsql_u8)carry;
        carry >>= 8u;
    }
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

static rsql_i8 i64_unsigned_compare(const RsqlI64* left,
                                    const RsqlI64* right);

static void i64_set_signed(RsqlI64* destination, const rsql_u8* value,
                           rsql_u8 width) {
    rsql_u8 fill = (value[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = 0u; index < sizeof(destination->bytes); ++index) {
        destination->bytes[index] = index < width ? value[index] : fill;
    }
}

static rsql_i8 i64_signed_compare(const RsqlI64* left,
                                  const RsqlI64* right) {
    rsql_u8 left_negative = (left->bytes[7] & 0x80u) ? 1u : 0u;
    rsql_u8 right_negative = (right->bytes[7] & 0x80u) ? 1u : 0u;
    if (left_negative != right_negative) return left_negative ? -1 : 1;
    return i64_unsigned_compare(left, right);
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

static void i64_shift_left(RsqlI64* value) {
    rsql_u8 carry = 0u;
    rsql_u8 next;
    rsql_u8 index;
    for (index = 0u; index < sizeof(value->bytes); ++index) {
        next = (value->bytes[index] & 0x80u) ? 1u : 0u;
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
    rsql_u8 negative = (numerator->bytes[7] & 0x80u) ? 1u : 0u;
    rsql_u8 bit = 64u;
    memcpy(&magnitude, numerator, sizeof(magnitude));
    if (negative) i64_negate(&magnitude);
    i64_zero(&remainder);
    i64_zero(&quotient);
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

static rsql_u8 row_is_null(const rsql_u8* row, rsql_u8 source) {
    if (row[0] & column_mask(source)) return 1u;
    return 0u;
}

static rsql_u8 same_group(const rsql_u8* left, const rsql_u8* right) {
    const RsqlColumnInfo* column;
    rsql_u16 width;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 source;
    rsql_u8 index;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        left_null = row_is_null(left, source);
        right_null = row_is_null(right, source);
        if (left_null != right_null) return 0u;
        if (left_null) continue;
        column = &g_rsql_cursor.columns[source];
        if (column->type.tag == RSQL_TYPE_TEXT ||
            column->type.tag == RSQL_TYPE_BLOB) continue;
        width = value_width(&column->type);
        if (memcmp(&left[column->offset], &right[column->offset], width) != 0) {
            return 0u;
        }
    }
    return 1u;
}

static rsql_u8 complete_group_match(rsql_u8* same_out) {
    rsql_u8 rc;
    *same_out = same_group(g_rsql_cursor.row, g_rsql_cursor.scan_row);
    if (!*same_out || !g_rsql_cursor.update_variable) return RSQL_OK;
    g_rsql_variable_compare_source = 0xFFu;
    rc = rsql_query_variable_compare_owner(1u);
    if (rc == RSQL_QUERY_PHASE_INDEX_SKIP) {
        *same_out = 0u;
        return RSQL_OK;
    }
    if (rc != RSQL_OK) return rc;
    *same_out = 1u;
    return RSQL_OK;
}

static void aggregate_reset(void) {
    rsql_aggregate_reset_state();
}

static void aggregate_row(const rsql_u8* row) {
    const RsqlColumnInfo* column;
    const rsql_u8* value;
    rsql_u8 aggregate;
    rsql_u8 source;
    rsql_u8 result;
    RsqlI64 candidate;
    rsql_i8 comparison;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        aggregate = g_rsql_cursor.projection_aggregate[result];
        if (aggregate == RSQL_AGG_NONE ||
            RSQL_PROJECTION_IS_SCALAR(aggregate)) continue;
        if (aggregate == RSQL_AGG_COUNT_STAR) {
            i64_increment(&g_rsql_cursor.aggregate_values[result]);
            continue;
        }
        source = g_rsql_cursor.projection[result];
        if (row_is_null(row, source)) continue;
        if (aggregate == RSQL_AGG_COUNT) {
            i64_increment(&g_rsql_cursor.aggregate_values[result]);
            continue;
        }
        column = &g_rsql_cursor.columns[source];
        value = &row[column->offset];
        if (column->type.tag == RSQL_TYPE_FLOAT5) {
            if (aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) {
                if (g_rsql_cursor.aggregate_counts[result].bytes[0] == 0u) {
                    memcpy(g_rsql_cursor.aggregate_values[result].bytes,
                           value, 5u);
                } else {
                    comparison = float_compare(
                        value, g_rsql_cursor.aggregate_values[result].bytes);
                    if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                        (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                        memcpy(g_rsql_cursor.aggregate_values[result].bytes,
                               value, 5u);
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
        if (aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) {
            i64_set_signed(&candidate, value,
                           (rsql_u8)value_width(&column->type));
            if (i64_is_zero(&g_rsql_cursor.aggregate_counts[result])) {
                memcpy(&g_rsql_cursor.aggregate_values[result], &candidate,
                       sizeof(candidate));
            } else {
                comparison = i64_signed_compare(
                    &candidate, &g_rsql_cursor.aggregate_values[result]);
                if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                    (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                    memcpy(&g_rsql_cursor.aggregate_values[result], &candidate,
                           sizeof(candidate));
                }
            }
        } else {
            i64_add_signed(&g_rsql_cursor.aggregate_values[result], value,
                           (rsql_u8)value_width(&column->type));
        }
        i64_increment(&g_rsql_cursor.aggregate_counts[result]);
    }
}

static void aggregate_finalize(void) {
    rsql_u8 aggregate;
    rsql_u8 source;
    rsql_u8 result;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        aggregate = g_rsql_cursor.projection_aggregate[result];
        if (aggregate != RSQL_AGG_SUM && aggregate != RSQL_AGG_AVG &&
            aggregate != RSQL_AGG_MIN && aggregate != RSQL_AGG_MAX) continue;
        source = g_rsql_cursor.projection[result];
        if (g_rsql_cursor.columns[source].type.tag == RSQL_TYPE_FLOAT5) {
            if (g_rsql_cursor.aggregate_counts[result].bytes[0] == 0u) {
                g_rsql_cursor.aggregate_nulls |= column_mask(result);
            } else if (aggregate == RSQL_AGG_AVG) {
                float_divide(
                    g_rsql_cursor.aggregate_values[result].bytes,
                    g_rsql_cursor.aggregate_counts[result].bytes);
            }
            continue;
        }
        if (i64_is_zero(&g_rsql_cursor.aggregate_counts[result])) {
            g_rsql_cursor.aggregate_nulls |= column_mask(result);
        } else if (aggregate == RSQL_AGG_AVG) {
            i64_divide_signed(&g_rsql_cursor.aggregate_values[result],
                              &g_rsql_cursor.aggregate_counts[result]);
        }
    }
}

/* FIXED8_8 aggregate values remain signed Q8.8 in the shared I64
 * accumulator. AVG, MIN, and MAX cannot exceed the source width, but SUM may;
 * report that at value access instead of silently exposing wrapped bytes. */
static rsql_u8 fixed_sum_overflow(rsql_u8 result) {
    rsql_u8 source;
    rsql_u8 fill;
    rsql_u8 index;
    if (g_rsql_cursor.projection_aggregate[result] != RSQL_AGG_SUM) return 0u;
    source = g_rsql_cursor.projection[result];
    if (result_source_column(source)->type.tag != RSQL_TYPE_FIXED8_8) return 0u;
    fill = (g_rsql_cursor.aggregate_values[result].bytes[1] & 0x80u)
        ? 0xFFu : 0u;
    for (index = 2u; index < 8u; ++index) {
        if (g_rsql_cursor.aggregate_values[result].bytes[index] != fill) {
            return 1u;
        }
    }
    return 0u;
}

static rsql_u8 aggregate_source_first(RsqlAggregateScan* scan,
                                      RsqlRowId* row_id) {
    if (!g_rsql_cursor.using_index) {
        return rsql_row_first(g_rsql_cursor.table_page, row_id);
    }
    scan->leaf_page = g_rsql_cursor.index_leaf_head;
    scan->leaf_slot = 0u;
    g_aggregate_index_scan = scan;
    g_aggregate_index_row = row_id;
    return rsql_aggregate_index_next();
}

static rsql_u8 aggregate_source_next(RsqlAggregateScan* scan,
                                     RsqlRowId* row_id) {
    if (g_rsql_cursor.using_index) {
        g_aggregate_index_scan = scan;
        g_aggregate_index_row = row_id;
        return rsql_aggregate_index_next();
    }
    return rsql_row_next(g_rsql_cursor.table_page, row_id, row_id);
}

static rsql_u8 aggregate_scan(rsql_u8 grouped) {
    RsqlAggregateScan iterator;
    RsqlRowId scan;
    rsql_u8 same;
    rsql_u8 rc;
    aggregate_reset();
    rc = aggregate_source_first(&iterator, &scan);
    while (rc == RSQL_OK) {
        rc = rsql_row_read(g_rsql_cursor.table_page, &scan,
                           g_rsql_cursor.scan_row,
                           sizeof(g_rsql_cursor.scan_row));
        if (rc != RSQL_OK) return rc;
        if (row_matches(g_rsql_cursor.scan_row)) {
            same = 1u;
            if (grouped) {
                rc = complete_group_match(&same);
                if (rc != RSQL_OK) return rc;
            }
            if (same) aggregate_row(g_rsql_cursor.scan_row);
        }
        rc = aggregate_source_next(&iterator, &scan);
    }
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    aggregate_finalize();
    return RSQL_OK;
}

static rsql_u8 candidate_duplicate(const RsqlRowId* candidate,
                                   rsql_u8* duplicate_out) {
    RsqlAggregateScan iterator;
    RsqlRowId scan;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    rc = aggregate_source_first(&iterator, &scan);
    while (rc == RSQL_OK) {
        if (scan.page == candidate->page && scan.slot == candidate->slot) {
            return RSQL_OK;
        }
        rc = rsql_row_read(g_rsql_cursor.table_page, &scan,
                           g_rsql_cursor.scan_row,
                           sizeof(g_rsql_cursor.scan_row));
        if (rc != RSQL_OK) return rc;
        if (row_matches(g_rsql_cursor.scan_row)) {
            rc = complete_group_match(&same);
            if (rc != RSQL_OK) return rc;
            if (same) {
                *duplicate_out = 1u;
                return RSQL_OK;
            }
        }
        rc = aggregate_source_next(&iterator, &scan);
    }
    return rc == RSQL_ERR_NOT_FOUND ? RSQL_ERR_CORRUPT_STORAGE : rc;
}

static rsql_u8 compare_group_source_rows(const rsql_u8* left,
                                         const rsql_u8* right,
                                         rsql_u8 source,
                                         rsql_i8* comparison_out) {
    static const RsqlColumnInfo* column;
    static rsql_u16 width;
    static rsql_u16 index;
    static RsqlI64* left_integer;
    static RsqlI64* right_integer;
    static rsql_u8 left_null;
    static rsql_u8 right_null;
    static rsql_u8 left_byte;
    static rsql_u8 right_byte;
    static rsql_u8 rc;
    column = &g_rsql_cursor.columns[source];
    width = value_width(&column->type);
    left_integer = &g_rsql_statement.values[1].integer;
    right_integer = &g_rsql_statement.values[2].integer;
    left_null = row_is_null(left, source);
    right_null = row_is_null(right, source);
    if (left_null != right_null) {
        *comparison_out = left_null ? -1 : 1;
        return RSQL_OK;
    }
    if (left_null) {
        *comparison_out = 0;
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        g_rsql_variable_compare_source = source;
        rc = rsql_query_variable_compare_owner(1u);
        if (rc != RSQL_OK) return rc;
        *comparison_out = g_rsql_variable_compare_result;
        return RSQL_OK;
    }
    left += column->offset;
    right += column->offset;
    if (column->type.tag == RSQL_TYPE_CHAR) {
        for (index = 0u; index < width; ++index) {
            left_byte = folded(left[index]);
            right_byte = folded(right[index]);
            if (left_byte < right_byte) {
                *comparison_out = -1;
                return RSQL_OK;
            }
            if (left_byte > right_byte) {
                *comparison_out = 1;
                return RSQL_OK;
            }
        }
        *comparison_out = 0;
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        *comparison_out = float_compare(left, right);
        return RSQL_OK;
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        memset(left_integer, 0, sizeof(*left_integer));
        memset(right_integer, 0, sizeof(*right_integer));
        memcpy(left_integer, left, width);
        memcpy(right_integer, right, width);
        *comparison_out = i64_unsigned_compare(left_integer, right_integer);
        return RSQL_OK;
    }
    i64_set_signed(left_integer, left, (rsql_u8)width);
    i64_set_signed(right_integer, right, (rsql_u8)width);
    *comparison_out = i64_signed_compare(left_integer, right_integer);
    return RSQL_OK;
}

static rsql_u8 load_group_aggregate(const RsqlRowId* row_id) {
    static rsql_u8 rc;
    rc = rsql_row_read(g_rsql_cursor.table_page, row_id,
                       g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
    if (rc != RSQL_OK) return rc;
    return aggregate_scan(1u);
}

rsql_u8 rsql_query_aggregate_scalar_row_phase(void) {
    const RsqlRowId* row_id = RSQL_WIDE_SCALAR_PHASE
        ? (const RsqlRowId*)RSQL_WIDE_SCALAR_STATE.right
        : (const RsqlRowId*)RSQL_WIDE_SCALAR_STATE.left;
    return rsql_row_read(g_rsql_cursor.table_page, row_id,
                         g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
}

static rsql_u8 compare_group_scalar(const RsqlRowId* left,
                                    const RsqlRowId* right,
                                    rsql_u8 result,
                                    rsql_i8* comparison_out) {
    RSQL_WIDE_SCALAR_STATE.left = (const WideTripleId*)left;
    RSQL_WIDE_SCALAR_STATE.right = (const WideTripleId*)right;
    RSQL_WIDE_SCALAR_STATE.result = result;
    RSQL_WIDE_SCALAR_STATE.comparison = comparison_out;
    g_rsql_aggregate_scalar_bridge_mode =
        RSQL_AGGREGATE_SCALAR_BRIDGE_REPLAY;
    result = rsql_query_variable_compare_owner(1u);
    g_rsql_aggregate_scalar_bridge_mode =
        RSQL_AGGREGATE_SCALAR_BRIDGE_IDLE;
    if (result == RSQL_OK) result = load_group_aggregate(left);
    return result;
}

static rsql_u8 compare_group_aggregate(const RsqlRowId* left,
                                       const RsqlRowId* right,
                                       rsql_u8 result,
                                       rsql_i8* comparison_out) {
    static RsqlI64* saved;
    static rsql_u8 aggregate;
    static rsql_u8 left_null;
    static rsql_u8 right_null;
    static rsql_u8 is_float;
    static rsql_u8 rc;
    saved = &g_rsql_statement.values[0].integer;
    aggregate = g_rsql_cursor.projection_aggregate[result];
    rc = load_group_aggregate(left);
    if (rc != RSQL_OK) return rc;
    left_null = (g_rsql_cursor.aggregate_nulls & column_mask(result)) != 0u;
    memcpy(saved, &g_rsql_cursor.aggregate_values[result], sizeof(*saved));
    rc = load_group_aggregate(right);
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
        g_rsql_cursor.columns[g_rsql_cursor.projection[result]].type.tag ==
            RSQL_TYPE_FLOAT5;
    *comparison_out = is_float
        ? float_compare(saved->bytes,
            g_rsql_cursor.aggregate_values[result].bytes)
        : i64_signed_compare(saved, &g_rsql_cursor.aggregate_values[result]);
    return RSQL_OK;
}

static rsql_u8 compare_group_ids(const RsqlRowId* left,
                                 const RsqlRowId* right,
                                 rsql_i8* comparison_out) {
    static rsql_u8 descriptor;
    static rsql_u8 index;
    static rsql_i8 comparison;
    static rsql_u8 rc;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        descriptor = RSQL_AGGREGATE_ORDER_COLUMNS[index];
        if (descriptor & RSQL_ORDER_PROJECTION) {
            descriptor &= RSQL_ORDER_PROJECTION_MASK;
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[descriptor])) {
                rc = compare_group_scalar(left, right, descriptor,
                                          &comparison);
            } else {
                rc = compare_group_aggregate(left, right, descriptor,
                                             &comparison);
            }
        } else {
            rc = rsql_row_read(g_rsql_cursor.table_page, left,
                               g_rsql_execution.row,
                               sizeof(g_rsql_execution.row));
            if (rc == RSQL_OK) {
                rc = rsql_row_read(g_rsql_cursor.table_page, right,
                                   g_rsql_cursor.scan_row,
                                   sizeof(g_rsql_cursor.scan_row));
            }
            if (rc == RSQL_OK) rc = compare_group_source_rows(
                g_rsql_execution.row, g_rsql_cursor.scan_row, descriptor,
                &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison != 0) {
            if (g_rsql_cursor.order_desc_mask & column_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            *comparison_out = comparison;
            return RSQL_OK;
        }
    }
    if (left->page < right->page) comparison = -1;
    else if (left->page > right->page) comparison = 1;
    else if (left->slot < right->slot) comparison = -1;
    else if (left->slot > right->slot) comparison = 1;
    else comparison = 0;
    *comparison_out = comparison;
    return RSQL_OK;
}

static rsql_u8 same_group_projection(const RsqlRowId* left,
                                     const RsqlRowId* right,
                                     rsql_u8* same_out) {
    static rsql_i8 comparison;
    static rsql_u8 result;
    static rsql_u8 rc;
    *same_out = 0u;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[result])) {
            rc = compare_group_scalar(left, right, result, &comparison);
        } else if (g_rsql_cursor.projection_aggregate[result] !=
                   RSQL_AGG_NONE) {
            rc = compare_group_aggregate(left, right, result, &comparison);
        } else {
            rc = rsql_row_read(g_rsql_cursor.table_page, left,
                               g_rsql_execution.row,
                               sizeof(g_rsql_execution.row));
            if (rc == RSQL_OK) rc = rsql_row_read(
                g_rsql_cursor.table_page, right, g_rsql_cursor.scan_row,
                sizeof(g_rsql_cursor.scan_row));
            if (rc == RSQL_OK) rc = compare_group_source_rows(
                g_rsql_execution.row, g_rsql_cursor.scan_row,
                g_rsql_cursor.projection[result], &comparison);
        }
        if (rc != RSQL_OK || comparison != 0) return rc;
    }
    *same_out = 1u;
    return RSQL_OK;
}

static rsql_u8 group_projection_duplicate(const RsqlRowId* candidate,
                                           rsql_u8* duplicate_out) {
    static RsqlAggregateScan iterator;
    static RsqlRowId scan;
    static rsql_u8 same;
    static rsql_u8 rc;
    *duplicate_out = 0u;
    rc = aggregate_source_first(&iterator, &scan);
    while (rc == RSQL_OK) {
        if (scan.page == candidate->page && scan.slot == candidate->slot) {
            return RSQL_OK;
        }
        rc = rsql_row_read(g_rsql_cursor.table_page, &scan,
                           g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
        if (rc != RSQL_OK) return rc;
        if (row_matches(g_rsql_cursor.row)) {
            rc = same_group_projection(candidate, &scan, &same);
            if (rc != RSQL_OK) return rc;
            if (same) {
                *duplicate_out = 1u;
                return RSQL_OK;
            }
        }
        rc = aggregate_source_next(&iterator, &scan);
    }
    return rc == RSQL_ERR_NOT_FOUND ? RSQL_ERR_CORRUPT_STORAGE : rc;
}

static rsql_u8 select_next_group(rsql_u8* found_out) {
    static RsqlAggregateScan iterator;
    static RsqlRowId scan;
    static RsqlRowId best;
    static RsqlRowId prior;
    static rsql_i8 comparison;
    static rsql_u8 duplicate;
    static rsql_u8 have_best;
    static rsql_u8 have_prior;
    static rsql_u8 rc;
    have_best = 0u;
    have_prior = g_rsql_cursor.positioned;
    *found_out = 0u;
    if (have_prior) prior = g_rsql_cursor.row_id;
    rc = aggregate_source_first(&iterator, &scan);
    while (rc == RSQL_OK) {
        rc = rsql_row_read(g_rsql_cursor.table_page, &scan,
                           g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
        if (rc != RSQL_OK) return rc;
        if (row_matches(g_rsql_cursor.row)) {
            rc = candidate_duplicate(&scan, &duplicate);
            if (rc != RSQL_OK) return rc;
            if (!duplicate && g_rsql_cursor.distinct) {
                rc = group_projection_duplicate(&scan, &duplicate);
                if (rc != RSQL_OK) return rc;
            }
            if (!duplicate) {
                comparison = 1;
                if (have_prior) {
                    rc = compare_group_ids(&scan, &prior, &comparison);
                    if (rc != RSQL_OK) return rc;
                }
                if (comparison > 0) {
                    comparison = -1;
                    if (have_best) {
                        rc = compare_group_ids(&scan, &best, &comparison);
                        if (rc != RSQL_OK) return rc;
                    }
                    if (comparison < 0) {
                        best = scan;
                        have_best = 1u;
                    }
                }
            }
        }
        rc = aggregate_source_next(&iterator, &scan);
    }
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    if (!have_best) return RSQL_OK;
    g_rsql_cursor.row_id = best;
    rc = load_group_aggregate(&best);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.positioned = 1u;
    *found_out = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_aggregate_result_next_phase(
    RsqlCursorNextRequest* request) {
    static rsql_u8 found;
    static rsql_u8 rc;
    if (!request || !valid_cursor(request->cursor) ||
        g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE) {
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
        if (g_rsql_cursor.group_count == 0u) {
            rc = rsql_query_cursor_next_phase(request);
            if (rc != RSQL_OK || !request->has_row) return rc;
        } else {
            rc = select_next_group(&found);
            if (rc != RSQL_OK) return rc;
            if (!found) {
                g_rsql_cursor.finished = 1u;
                g_rsql_cursor.positioned = 0u;
                return RSQL_OK;
            }
        }
        if (g_rsql_cursor.skipped_rows < g_rsql_cursor.offset) {
            ++g_rsql_cursor.skipped_rows;
            request->has_row = 0u;
            continue;
        }
        ++g_rsql_cursor.returned_rows;
        request->has_row = 1u;
        return RSQL_OK;
    }
}

static rsql_u8 aggregate_variable_begin(RsqlCursorNextRequest* request) {
    RsqlAggregateScan iterator;
    RsqlRowId next;
    rsql_u8 rc;
    aggregate_reset();
    g_rsql_cursor.update_scan_started = 1u;
    rc = aggregate_source_first(&iterator, &next);
    if (rc == RSQL_OK) {
        g_rsql_cursor.index_leaf_page = iterator.leaf_page;
        g_rsql_cursor.index_leaf_slot = iterator.leaf_slot;
        g_rsql_cursor.row_id = next;
        rc = rsql_row_read(g_rsql_cursor.table_page, &next,
                           g_rsql_cursor.scan_row,
                           sizeof(g_rsql_cursor.scan_row));
        if (rc == RSQL_OK) {
            RSQL_VARIABLE_PREDICATE_SOURCE = 1u;
            return RSQL_QUERY_PHASE_PREDICATE;
        }
        return rc;
    }
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    aggregate_finalize();
    RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
    g_rsql_cursor.positioned = 1u;
    g_rsql_cursor.finished = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

#define VARIABLE_GROUP_OUTER 1u
#define VARIABLE_GROUP_DUP   2u
#define VARIABLE_GROUP_ACCUM 3u

static rsql_u8 aggregate_variable_group_outer(rsql_u8 first) {
    RsqlRowId next;
    rsql_u8 rc = first
        ? rsql_row_first(g_rsql_cursor.table_page, &next)
        : rsql_row_next(g_rsql_cursor.table_page, &g_rsql_cursor.row_id,
                        &next);
    if (rc == RSQL_ERR_NOT_FOUND) {
        g_rsql_cursor.finished = 1u;
        g_rsql_cursor.positioned = 0u;
        RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
        /* No new group was produced.  Tell the resident dispatcher to
         * continue once so the finished cursor reports has_row = 0 rather
         * than manufacturing a final phantom group. */
        return RSQL_QUERY_PHASE_INDEX_SKIP;
    }
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.row_id = next;
    rc = rsql_row_read(g_rsql_cursor.table_page, &next,
                       g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.update_scan_started = VARIABLE_GROUP_OUTER;
    RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
    return RSQL_QUERY_PHASE_PREDICATE;
}

static rsql_u8 aggregate_variable_group_scan(rsql_u8 stage) {
    rsql_u8 rc;
    if (stage == VARIABLE_GROUP_ACCUM) aggregate_reset();
    rc = rsql_row_first(g_rsql_cursor.table_page,
                        &g_rsql_cursor.update_next_row_id);
    if (rc != RSQL_OK) return rc;
    if (stage == VARIABLE_GROUP_DUP &&
        g_rsql_cursor.update_next_row_id.page == g_rsql_cursor.row_id.page &&
        g_rsql_cursor.update_next_row_id.slot == g_rsql_cursor.row_id.slot) {
        return aggregate_variable_group_scan(VARIABLE_GROUP_ACCUM);
    }
    rc = rsql_row_read(g_rsql_cursor.table_page,
                       &g_rsql_cursor.update_next_row_id,
                       g_rsql_cursor.scan_row,
                       sizeof(g_rsql_cursor.scan_row));
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.update_scan_started = stage;
    RSQL_VARIABLE_PREDICATE_SOURCE = 1u;
    return RSQL_QUERY_PHASE_PREDICATE;
}

static rsql_u8 aggregate_variable_group_continue(rsql_u8 matched) {
    RsqlRowId next;
    rsql_u8 stage = g_rsql_cursor.update_scan_started;
    rsql_u8 rc;
    if (stage == VARIABLE_GROUP_OUTER) {
        return matched ? aggregate_variable_group_scan(VARIABLE_GROUP_DUP)
                       : aggregate_variable_group_outer(0u);
    }
    if (stage != VARIABLE_GROUP_DUP && stage != VARIABLE_GROUP_ACCUM) {
        return RSQL_ERR_CURSOR_STATE;
    }
    if (matched && same_group(g_rsql_cursor.row,
                              g_rsql_cursor.scan_row)) {
        if (stage == VARIABLE_GROUP_DUP) {
            return aggregate_variable_group_outer(0u);
        }
        aggregate_row(g_rsql_cursor.scan_row);
    }
    rc = rsql_row_next(g_rsql_cursor.table_page,
                       &g_rsql_cursor.update_next_row_id, &next);
    if (rc == RSQL_ERR_NOT_FOUND && stage == VARIABLE_GROUP_ACCUM) {
        aggregate_finalize();
        g_rsql_cursor.update_scan_started = 0u;
        g_rsql_cursor.positioned = 1u;
        RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
        return RSQL_OK;
    }
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.update_next_row_id = next;
    if (stage == VARIABLE_GROUP_DUP &&
        next.page == g_rsql_cursor.row_id.page &&
        next.slot == g_rsql_cursor.row_id.slot) {
        return aggregate_variable_group_scan(VARIABLE_GROUP_ACCUM);
    }
    rc = rsql_row_read(g_rsql_cursor.table_page, &next,
                       g_rsql_cursor.scan_row,
                       sizeof(g_rsql_cursor.scan_row));
    return rc == RSQL_OK ? RSQL_QUERY_PHASE_PREDICATE : rc;
}

rsql_u8 __fastcall__ rsql_query_aggregate_predicate_phase(rsql_u8 matched) {
    RsqlAggregateScan iterator;
    RsqlRowId next;
    rsql_u8 rc;
    if (g_rsql_cursor.mode != RSQL_SELECT_AGGREGATE ||
        !g_rsql_cursor.update_scan_started) return RSQL_ERR_CURSOR_STATE;
    if (g_rsql_cursor.group_count != 0u) {
        return aggregate_variable_group_continue(matched);
    }
    next = g_rsql_cursor.row_id;
    if (matched) aggregate_row(g_rsql_cursor.scan_row);
    iterator.leaf_page = g_rsql_cursor.index_leaf_page;
    iterator.leaf_slot = g_rsql_cursor.index_leaf_slot;
    rc = aggregate_source_next(&iterator, &next);
    g_rsql_cursor.index_leaf_page = iterator.leaf_page;
    g_rsql_cursor.index_leaf_slot = iterator.leaf_slot;
    if (rc == RSQL_OK) {
        g_rsql_cursor.row_id = next;
        rc = rsql_row_read(g_rsql_cursor.table_page, &next,
                           g_rsql_cursor.scan_row,
                           sizeof(g_rsql_cursor.scan_row));
        return rc == RSQL_OK ? RSQL_QUERY_PHASE_PREDICATE : rc;
    }
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    aggregate_finalize();
    RSQL_VARIABLE_PREDICATE_SOURCE = 0u;
    g_rsql_cursor.positioned = 1u;
    g_rsql_cursor.finished = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_cursor_next_phase(RsqlCursorNextRequest* request) {
    RsqlAggregateScan iterator;
    RsqlRowId next;
    rsql_u8 duplicate;
    rsql_u8 rc;
    if (!request || !valid_cursor(request->cursor)) return RSQL_ERR_CURSOR_STATE;
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
        g_rsql_cursor.group_count == 0u) {
        if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
            return aggregate_variable_begin(request);
        }
        rc = aggregate_scan(0u);
        if (rc != RSQL_OK) return rc;
        g_rsql_cursor.positioned = 1u;
        g_rsql_cursor.finished = 1u;
        request->has_row = 1u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
        RSQL_VARIABLE_PREDICATE_MASK != 0u) {
        return aggregate_variable_group_outer(!g_rsql_cursor.positioned);
    }
    iterator.leaf_page = g_rsql_cursor.index_leaf_page;
    iterator.leaf_slot = g_rsql_cursor.index_leaf_slot;
    if (!g_rsql_cursor.positioned) {
        rc = aggregate_source_first(&iterator, &next);
    } else {
        next = g_rsql_cursor.row_id;
        rc = aggregate_source_next(&iterator, &next);
    }
    g_rsql_cursor.index_leaf_page = iterator.leaf_page;
    g_rsql_cursor.index_leaf_slot = iterator.leaf_slot;
    while (rc == RSQL_OK) {
        g_rsql_cursor.row_id = next;
        rc = rsql_row_read(g_rsql_cursor.table_page, &g_rsql_cursor.row_id,
                           g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
        if (rc != RSQL_OK) return rc;
        if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
            g_rsql_cursor.positioned = 1u;
            return RSQL_QUERY_PHASE_PREDICATE;
        }
        if (row_matches(g_rsql_cursor.row)) {
            if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE) {
                rc = candidate_duplicate(&g_rsql_cursor.row_id, &duplicate);
                if (rc != RSQL_OK) return rc;
                if (duplicate) {
                    rc = aggregate_source_next(&iterator, &next);
                    g_rsql_cursor.index_leaf_page = iterator.leaf_page;
                    g_rsql_cursor.index_leaf_slot = iterator.leaf_slot;
                    continue;
                }
                rc = aggregate_scan(1u);
                if (rc != RSQL_OK) return rc;
                rc = rsql_row_read(g_rsql_cursor.table_page,
                                   &g_rsql_cursor.row_id, g_rsql_cursor.row,
                                   sizeof(g_rsql_cursor.row));
                if (rc != RSQL_OK) return rc;
            }
            g_rsql_cursor.positioned = 1u;
            request->has_row = 1u;
            return RSQL_OK;
        }
        rc = aggregate_source_next(&iterator, &next);
        g_rsql_cursor.index_leaf_page = iterator.leaf_page;
        g_rsql_cursor.index_leaf_slot = iterator.leaf_slot;
    }
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_cursor_index_row_phase(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    if (!request || !valid_cursor(request->cursor) ||
        !g_rsql_cursor.using_index) return RSQL_ERR_CURSOR_STATE;
    request->has_row = 0u;
    rc = rsql_row_read(g_rsql_cursor.table_page, &g_rsql_cursor.row_id,
                       g_rsql_cursor.row, sizeof(g_rsql_cursor.row));
    if (rc == RSQL_ERR_NOT_FOUND) return RSQL_QUERY_PHASE_INDEX_SKIP;
    if (rc != RSQL_OK) return rc;
    if (RSQL_VARIABLE_PREDICATE_MASK != 0u) {
        g_rsql_cursor.positioned = 1u;
        return RSQL_QUERY_PHASE_PREDICATE;
    }
    if (!row_matches(g_rsql_cursor.row)) return RSQL_QUERY_PHASE_INDEX_SKIP;
    g_rsql_cursor.positioned = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

rsql_u8 rsql_query_predicate_match_phase(void) {
    const rsql_u8* row;
    if (RSQL_VARIABLE_PREDICATE_MASK == 0u &&
        !g_rsql_cursor.update_variable) return RSQL_ERR_CURSOR_STATE;
    row = RSQL_VARIABLE_PREDICATE_SOURCE
        ? g_rsql_cursor.scan_row : g_rsql_cursor.row;
    return row_matches(row)
        ? RSQL_OK : RSQL_QUERY_PHASE_INDEX_SKIP;
}

static const RsqlColumnInfo* __fastcall__ result_source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

static const rsql_u8* __fastcall__ result_source_row(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) return g_rsql_execution.row;
    if (source & RSQL_SOURCE_INNER) return g_rsql_cursor.scan_row;
    return g_rsql_cursor.row;
}

static rsql_u8 __fastcall__ result_source_null(rsql_u8 source) {
    const rsql_u8* row;
    rsql_u8 column = source & RSQL_SOURCE_COLUMN_MASK;
    if ((source & RSQL_SOURCE_INNER) && g_rsql_cursor.join_inner_null) {
        return 1u;
    }
    row = result_source_row(source);
    return (row[0] & column_mask(column)) != 0u;
}

rsql_u8 __fastcall__ rsql_query_cursor_column_phase(RsqlCursorColumnRequest* request) {
    const RsqlColumnInfo* column;
    const rsql_u8* source;
    rsql_u16 width;
    rsql_u8 source_index;
    rsql_u8 copy;
    if (!request || !valid_cursor(request->cursor) ||
        !g_rsql_cursor.positioned ||
        request->column >= g_rsql_cursor.result_column_count) {
        return RSQL_ERR_CURSOR_STATE;
    }
    memset(&request->value, 0, sizeof(request->value));
    if (RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return RSQL_QUERY_PHASE_SCALAR;
    }
    if (g_rsql_cursor.projection_aggregate[request->column] != RSQL_AGG_NONE) {
        source_index = g_rsql_cursor.projection[request->column];
        if (fixed_sum_overflow(request->column)) {
            return RSQL_ERR_NUMERIC_OVERFLOW;
        }
        if (g_rsql_cursor.projection_aggregate[request->column] !=
                RSQL_AGG_COUNT_STAR &&
            g_rsql_cursor.projection_aggregate[request->column] !=
                RSQL_AGG_COUNT &&
            result_source_column(source_index)->type.tag ==
                RSQL_TYPE_FLOAT5) {
            request->value.type.tag = RSQL_TYPE_FLOAT5;
            request->value.length = 5u;
        } else if (g_rsql_cursor.projection_aggregate[request->column] !=
                       RSQL_AGG_COUNT_STAR &&
                   g_rsql_cursor.projection_aggregate[request->column] !=
                       RSQL_AGG_COUNT &&
                   result_source_column(source_index)->type.tag ==
                       RSQL_TYPE_FIXED8_8) {
            request->value.type.tag = RSQL_TYPE_FIXED8_8;
            request->value.length = 2u;
        } else {
            request->value.type.tag = RSQL_TYPE_I64;
            request->value.length = 8u;
        }
        request->value.is_null =
            (g_rsql_cursor.aggregate_nulls & column_mask(request->column))
            != 0u;
        memcpy(request->value.bytes,
               g_rsql_cursor.aggregate_values[request->column].bytes,
               request->value.length);
        return RSQL_OK;
    }
    source_index = g_rsql_cursor.projection[request->column];
    column = result_source_column(source_index);
    request->value.type = column->type;
    width = value_width(&column->type);
    request->value.length = width;
    request->value.is_null = result_source_null(source_index);
    if (!request->value.is_null) {
        source = &result_source_row(source_index)[column->offset];
        copy = width > 8u ? 8u : (rsql_u8)width;
        memcpy(request->value.bytes, source, copy);
        if (column->type.tag == RSQL_TYPE_TEXT ||
            column->type.tag == RSQL_TYPE_BLOB) {
            return RSQL_QUERY_PHASE_VARIABLE;
        }
    } else if (column->type.tag == RSQL_TYPE_TEXT ||
               column->type.tag == RSQL_TYPE_BLOB) {
        request->value.length = 0u;
    }
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_value_read_phase(RsqlValueReadRequest* request) {
    const rsql_u8* source;
    rsql_u16 length;
    rsql_u16 available;
    rsql_u8 source_index;
    if (!request || !request->destination || !valid_cursor(request->cursor) ||
        !g_rsql_cursor.positioned ||
        request->column >= g_rsql_cursor.result_column_count) {
        return RSQL_ERR_CURSOR_STATE;
    }
    if (RSQL_PROJECTION_IS_SCALAR(
            g_rsql_cursor.projection_aggregate[request->column])) {
        return RSQL_QUERY_PHASE_SCALAR;
    }
    if (g_rsql_cursor.projection_aggregate[request->column] != RSQL_AGG_NONE) {
        if (fixed_sum_overflow(request->column)) {
            return RSQL_ERR_NUMERIC_OVERFLOW;
        }
        source = g_rsql_cursor.aggregate_values[request->column].bytes;
        source_index = g_rsql_cursor.projection[request->column];
        if (g_rsql_cursor.projection_aggregate[request->column] !=
                RSQL_AGG_COUNT_STAR &&
            g_rsql_cursor.projection_aggregate[request->column] !=
                RSQL_AGG_COUNT &&
            result_source_column(source_index)->type.tag ==
                RSQL_TYPE_FLOAT5) {
            length = 5u;
        } else if (g_rsql_cursor.projection_aggregate[request->column] !=
                       RSQL_AGG_COUNT_STAR &&
                   g_rsql_cursor.projection_aggregate[request->column] !=
                       RSQL_AGG_COUNT &&
                   result_source_column(source_index)->type.tag ==
                       RSQL_TYPE_FIXED8_8) length = 2u;
        else length = 8u;
    } else {
        source_index = g_rsql_cursor.projection[request->column];
        if (result_source_column(source_index)->type.tag == RSQL_TYPE_TEXT ||
            result_source_column(source_index)->type.tag == RSQL_TYPE_BLOB) {
            return RSQL_QUERY_PHASE_VARIABLE;
        }
        if (result_source_null(source_index)) {
            request->bytes_read = 0u;
            return RSQL_OK;
        }
        source = &result_source_row(source_index)[
            result_source_column(source_index)->offset];
        length = value_width(&result_source_column(source_index)->type);
    }
    request->bytes_read = 0u;
    if (request->offset >= length) return RSQL_OK;
    available = (rsql_u16)(length - request->offset);
    if (available > request->capacity) available = request->capacity;
    memcpy(request->destination, source + request->offset, available);
    request->bytes_read = available;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_close_phase(RsqlQueryCloseRequest* request) {
    if (!request || !valid_cursor(request->cursor)) return RSQL_ERR_CURSOR_STATE;
    memset(&g_rsql_cursor, 0, sizeof(g_rsql_cursor));
    return RSQL_OK;
}

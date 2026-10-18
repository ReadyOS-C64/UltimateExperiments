#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"
#include "wide_internal.h"

#define SQL_FALSE   0u
#define SQL_TRUE    1u
#define SQL_UNKNOWN 2u
#define WIDE_ORDER_AGGREGATE 0x20u
#define WIDE_ORDER_SCALAR    0x10u

/* Keep the continuation candidate initialized at file scope.  cc65 otherwise
 * emits anonymous local words before the exported continuation entry. */
RsqlRowId g_wide_candidate = { 0xFFFFu, 0xFFu };
static const RsqlI64 ZERO_I64 = {{ 0u, 0u, 0u, 0u, 0u, 0u, 0u, 0u }};
void __fastcall__ rsql_wide_i64_divide(RsqlI64* numerator);

static rsql_u8 folded_name(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

const RsqlColumnInfo* source_column(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        return &g_rsql_execution.columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    if (source & RSQL_SOURCE_INNER) {
        return &g_rsql_cursor.join_columns[source & RSQL_SOURCE_COLUMN_MASK];
    }
    return &g_rsql_cursor.columns[source & RSQL_SOURCE_COLUMN_MASK];
}

const rsql_u8* source_row(rsql_u8 source) {
    if (source & RSQL_SOURCE_SUBQUERY) return g_rsql_execution.row;
    if (source & RSQL_SOURCE_INNER) return g_rsql_cursor.scan_row;
    return g_rsql_cursor.row;
}

rsql_u8 source_null(rsql_u8 source) {
    rsql_u8 column = source & RSQL_SOURCE_COLUMN_MASK;
    return (source_row(source)[0] & (rsql_u8)(1u << column)) != 0u;
}

rsql_u8 rsql_query_bind_wide_join_phase(void) {
    g_rsql_variable_compare_kind = 0xFDu;
    g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_WIDE_SCALAR;
    return rsql_query_variable_compare_owner(7u);
}

static rsql_u8 slot_mask(rsql_u8 slot) {
    return (rsql_u8)(1u << (slot & 7u));
}

static rsql_u8 slot_used(rsql_u8 slot) {
    return (g_rsql_meta_page1[RSQL_ROW_BITMAP + (slot >> 3u)] &
            slot_mask(slot)) != 0u;
}

static rsql_u8 read_table(rsql_u16 table_page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(table_page),
        g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (g_rsql_meta_page0[0] != 'R' || g_rsql_meta_page0[1] != 'T' ||
        g_rsql_meta_page0[2] != 'B' || g_rsql_meta_page0[3] != 'L' ||
        g_rsql_meta_page0[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_WIDTH]) != row_width ||
        g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_rsql_meta_page0)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 read_row_page(rsql_u16 page, rsql_u16 row_width) {
    rsql_u8 capacity;
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
        g_rsql_meta_page1, RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    capacity = g_rsql_meta_page1[RSQL_ROW_CAPACITY];
    if (g_rsql_meta_page1[0] != 'R' || g_rsql_meta_page1[1] != 'R' ||
        g_rsql_meta_page1[2] != 'O' || g_rsql_meta_page1[3] != 'W' ||
        g_rsql_meta_page1[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_WIDTH]) != row_width ||
        capacity == 0u || capacity > 32u ||
        (rsql_u16)(RSQL_ROW_DATA + (rsql_u16)capacity * row_width) >
            RSQL_REU_PAGE_SIZE) return RSQL_ERR_CORRUPT_STORAGE;
    return RSQL_OK;
}

static rsql_u8 raw_first(rsql_u16 table_page, rsql_u16 row_width,
                         RsqlRowId* row_id) {
    rsql_u16 page;
    rsql_u8 slot;
    rsql_u8 rc = read_table(table_page, row_width);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY]; ++slot) {
            if (slot_used(slot)) {
                row_id->page = page;
                row_id->slot = slot;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 raw_locate(rsql_u16 table_page, rsql_u16 row_width,
                          rsql_u16 wanted_page) {
    rsql_u16 page;
    rsql_u8 rc = read_table(table_page, row_width);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_rsql_meta_page0[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        if (page == wanted_page) return RSQL_OK;
        page = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 raw_next(rsql_u16 table_page, rsql_u16 row_width,
                        const RsqlRowId* current, RsqlRowId* next_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u8 slot;
    rsql_u8 rc = raw_locate(table_page, row_width, current->page);
    if (rc != RSQL_OK) return rc;
    if (current->slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY] ||
        !slot_used(current->slot)) return RSQL_ERR_NOT_FOUND;
    page = current->page;
    slot = (rsql_u8)(current->slot + 1u);
    for (;;) {
        while (slot < g_rsql_meta_page1[RSQL_ROW_CAPACITY]) {
            if (slot_used(slot)) {
                next_out->page = page;
                next_out->slot = slot;
                return RSQL_OK;
            }
            ++slot;
        }
        next = rsql_get_u16(&g_rsql_meta_page1[RSQL_ROW_NEXT]);
        if (next == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
        page = next;
        rc = read_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        slot = 0u;
    }
}

static rsql_u8 index_next(RsqlWideIndexIterator* iterator,
                          RsqlRowId* row_id) {
    rsql_u16 base;
    rsql_u16 next;
    rsql_u8 capacity;
    rsql_u8 count;
    rsql_u8 key_width;
    rsql_u8 rc;
    while (iterator->page != RSQL_PAGE_NONE) {
        rc = rsql_reu_read(rsql_reu_page_address(iterator->page),
                           g_rsql_meta_page0, RSQL_REU_PAGE_SIZE);
        if (rc != RSQL_OK) return rc;
        capacity = g_rsql_meta_page0[RSQL_INDEX_LEAF_CAPACITY];
        count = g_rsql_meta_page0[RSQL_INDEX_LEAF_COUNT];
        key_width = g_rsql_meta_page0[RSQL_INDEX_LEAF_KEY_WIDTH];
        if (g_rsql_meta_page0[0] != 'R' ||
            g_rsql_meta_page0[1] != 'I' ||
            g_rsql_meta_page0[2] != 'L' ||
            g_rsql_meta_page0[3] != 'F' ||
            g_rsql_meta_page0[4] != RSQL_STORAGE_VERSION ||
            capacity == 0u || count > capacity || key_width > 96u ||
            (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                (rsql_u16)capacity * (key_width + 3u)) >
                    RSQL_PAGE_CHECKSUM_OFFSET ||
            g_rsql_meta_page0[RSQL_PAGE_CHECKSUM_OFFSET] !=
                rsql_page_checksum(g_rsql_meta_page0)) {
            return RSQL_ERR_CORRUPT_STORAGE;
        }
        if (iterator->slot < count) {
            base = (rsql_u16)(RSQL_INDEX_LEAF_DATA +
                (rsql_u16)iterator->slot * (key_width + 3u));
            row_id->page = rsql_get_u16(
                &g_rsql_meta_page0[base + key_width]);
            row_id->slot = g_rsql_meta_page0[base + key_width + 2u];
            ++iterator->slot;
            return RSQL_OK;
        }
        next = rsql_get_u16(&g_rsql_meta_page0[RSQL_INDEX_LEAF_NEXT]);
        iterator->page = next;
        iterator->slot = 0u;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 access_next(rsql_u8 indexed,
                           RsqlWideIndexIterator* iterator,
                           rsql_u16 table_page, rsql_u16 row_width,
                           const RsqlRowId* current, RsqlRowId* next_out,
                           rsql_u8 advance) {
    if (indexed) {
        if (!advance) {
            iterator->page = iterator->head;
            iterator->slot = 0u;
        }
        return index_next(iterator, next_out);
    }
    return advance ? raw_next(table_page, row_width, current, next_out) :
        raw_first(table_page, row_width, next_out);
}

static rsql_u8 raw_read(rsql_u16 table_page, rsql_u16 row_width,
                        const RsqlRowId* row_id, rsql_u8* destination) {
    rsql_u16 offset;
    rsql_u8 rc = raw_locate(table_page, row_width, row_id->page);
    if (rc != RSQL_OK) return rc;
    if (row_id->slot >= g_rsql_meta_page1[RSQL_ROW_CAPACITY] ||
        !slot_used(row_id->slot)) return RSQL_ERR_NOT_FOUND;
    offset = (rsql_u16)(RSQL_ROW_DATA +
        (rsql_u16)row_id->slot * row_width);
    memcpy(destination, &g_rsql_meta_page1[offset], row_width);
    return RSQL_OK;
}

static void null_row(rsql_u8* row, rsql_u16 width, rsql_u8 columns) {
    memset(row, 0, width);
    row[0] = columns == 8u
        ? 0xFFu : (rsql_u8)(slot_mask(columns) - 1u);
}

static rsql_u16 value_width(const RsqlTypeSpec* type) {
    switch (type->tag) {
        case RSQL_TYPE_BOOLEAN:
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8: return 1u;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_FIXED8_8:
        case RSQL_TYPE_ENUM16: return 2u;
        case RSQL_TYPE_I32: return 4u;
        case RSQL_TYPE_I64: return 8u;
        case RSQL_TYPE_FLOAT5: return 5u;
        case RSQL_TYPE_CHAR: return type->parameter;
        case RSQL_TYPE_TEXT:
        case RSQL_TYPE_BLOB: return sizeof(RsqlBlobHandle);
    }
    return 0u;
}

static rsql_i8 compare_signed(const rsql_u8* left, rsql_u8 left_width,
                              const rsql_u8* right, rsql_u8 right_width) {
    rsql_u8 left_fill = (left[left_width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 right_fill = (right[right_width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index = 8u;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (left_fill != right_fill) return left_fill ? -1 : 1;
    while (index) {
        --index;
        left_byte = index < left_width ? left[index] : left_fill;
        right_byte = index < right_width ? right[index] : right_fill;
        if (left_byte < right_byte) return -1;
        if (left_byte > right_byte) return 1;
    }
    return 0;
}

static rsql_i8 compare_unsigned(const rsql_u8* left, const rsql_u8* right,
                                rsql_u8 width) {
    while (width) {
        --width;
        if (left[width] < right[width]) return -1;
        if (left[width] > right[width]) return 1;
    }
    return 0;
}

static rsql_i8 compare_float(const rsql_u8* left, const rsql_u8* right) {
    rsql_u8 left_negative;
    rsql_u8 right_negative;
    rsql_u8 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    if (left[0] == 0u && right[0] == 0u) return 0;
    left_negative = left[0] && (left[1] & 0x80u);
    right_negative = right[0] && (right[1] & 0x80u);
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

static rsql_i8 compare_chars(const rsql_u8* left, rsql_u16 left_width,
                             const rsql_u8* right, rsql_u16 right_width) {
    rsql_u16 width = left_width > right_width ? left_width : right_width;
    rsql_u16 index;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    for (index = 0u; index < width; ++index) {
        left_byte = index < left_width ? folded_name((char)left[index]) : ' ';
        right_byte = index < right_width ? folded_name((char)right[index]) : ' ';
        if (left_byte < right_byte) return -1;
        if (left_byte > right_byte) return 1;
    }
    return 0;
}

static rsql_i8 compare_reference(rsql_u8 left_source,
                                 rsql_u8 right_source) {
    const RsqlColumnInfo* left_column = source_column(left_source);
    const RsqlColumnInfo* right_column = source_column(right_source);
    const rsql_u8* left = &source_row(left_source)[left_column->offset];
    const rsql_u8* right = &source_row(right_source)[right_column->offset];
    rsql_u8 left_width = (rsql_u8)value_width(&left_column->type);
    rsql_u8 right_width = (rsql_u8)value_width(&right_column->type);
    if (left_column->type.tag == RSQL_TYPE_CHAR) {
        return compare_chars(left, left_width, right, right_width);
    }
    if (left_column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(left, right);
    }
    if (left_column->type.tag == RSQL_TYPE_BOOLEAN ||
        left_column->type.tag == RSQL_TYPE_ENUM8 ||
        left_column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(left, right, left_width);
    }
    return compare_signed(left, left_width, right, right_width);
}

static rsql_i8 compare_literal(rsql_u8 source,
                               const RsqlParsedValue* literal) {
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* value = &source_row(source)[column->offset];
    rsql_u8 width = (rsql_u8)value_width(&column->type);
    if (column->type.tag == RSQL_TYPE_CHAR) {
        return compare_chars(value, width, (const rsql_u8*)literal->string,
                             literal->length);
    }
    if (column->type.tag == RSQL_TYPE_FLOAT5) {
        return compare_float(value, literal->integer.bytes);
    }
    if (column->type.tag == RSQL_TYPE_FIXED8_8) {
        if (compare_signed(&value[1], 1u, literal->integer.bytes, 8u) < 0)
            return -1;
        if (compare_signed(&value[1], 1u, literal->integer.bytes, 8u) > 0)
            return 1;
        return value[0] == 0u ? 0 : 1;
    }
    if (column->type.tag == RSQL_TYPE_BOOLEAN ||
        column->type.tag == RSQL_TYPE_ENUM8 ||
        column->type.tag == RSQL_TYPE_ENUM16) {
        return compare_unsigned(value, literal->integer.bytes, width);
    }
    return compare_signed(value, width, literal->integer.bytes, 8u);
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
    while (row_length && row[row_length - 1u] == ' ') --row_length;
    while (row_index < row_length) {
        if (pattern_index < pattern->length) {
            pattern_byte = (rsql_u8)pattern->string[pattern_index];
            if (pattern_byte == '_' ||
                folded_name((char)pattern_byte) ==
                    folded_name((char)row[row_index])) {
                ++pattern_index;
                ++row_index;
                continue;
            }
            if (pattern_byte == '%') {
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

static rsql_u8 predicate_truth(rsql_u8 source, rsql_u8 op,
                               const RsqlParsedValue* value) {
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* row = source_row(source);
    rsql_u8 left_null = source_null(source);
    rsql_u8 right_null = value->kind == RSQL_VALUE_NULL;
    rsql_i8 comparison;
    if (op == RSQL_PRED_IS_NULL) return left_null ? SQL_TRUE : SQL_FALSE;
    if (op == RSQL_PRED_IS_NOT_NULL) return left_null ? SQL_FALSE : SQL_TRUE;
    if (value->kind == RSQL_VALUE_REFERENCE) {
        right_null = source_null(value->integer.bytes[0]);
    }
    if (left_null || right_null) return SQL_UNKNOWN;
    if (op == RSQL_PRED_LIKE) {
        return like_char(&row[column->offset], column->type.parameter, value)
            ? SQL_TRUE : SQL_FALSE;
    }
    comparison = value->kind == RSQL_VALUE_REFERENCE
        ? compare_reference(source, value->integer.bytes[0])
        : compare_literal(source, value);
    return comparison_matches(comparison, op) ? SQL_TRUE : SQL_FALSE;
}

static rsql_u8 combine_program(const rsql_u8* program, rsql_u8 start,
                               rsql_u8 count, rsql_u8 private_program) {
    rsql_u8 stack[RSQL_PREDICATES_MAX];
    rsql_u8 stack_count = 0u;
    rsql_u8 opcode;
    rsql_u8 left;
    rsql_u8 right;
    rsql_u8 index;
    rsql_u8 source;
    rsql_u8 op;
    const RsqlParsedValue* value;
    if (count == 0u) return 1u;
    for (index = start; index < (rsql_u8)(start + count); ++index) {
        opcode = program[index];
        if (opcode < RSQL_PREDICATES_MAX) {
            if (stack_count >= RSQL_PREDICATES_MAX) return 0u;
            if (private_program) {
                if (opcode >= g_rsql_statement.subquery_predicate_count)
                    return 0u;
                source = (rsql_u8)
                    g_rsql_statement.columns[opcode].type.parameter;
                op = g_rsql_statement.columns[opcode].type.tag;
                value = &g_rsql_statement.values[opcode];
            } else {
                if (opcode >= g_rsql_cursor.predicate_count) return 0u;
                source = g_rsql_cursor.predicates[opcode].column;
                op = g_rsql_cursor.predicates[opcode].op;
                value = &g_rsql_cursor.predicates[opcode].value;
            }
            if (!private_program &&
                (RSQL_VARIABLE_PREDICATE_MASK & slot_mask(opcode))) {
                stack[stack_count++] =
                    RSQL_VARIABLE_PREDICATE_TRUTH[opcode];
            } else stack[stack_count++] = predicate_truth(source, op, value);
        } else if (opcode == RSQL_BOOL_NOT) {
            if (!stack_count) return 0u;
            if (stack[stack_count - 1u] == SQL_TRUE)
                stack[stack_count - 1u] = SQL_FALSE;
            else if (stack[stack_count - 1u] == SQL_FALSE)
                stack[stack_count - 1u] = SQL_TRUE;
        } else {
            if (stack_count < 2u) return 0u;
            right = stack[--stack_count];
            left = stack[stack_count - 1u];
            if (opcode == RSQL_BOOL_AND) {
                if (left == SQL_FALSE || right == SQL_FALSE)
                    stack[stack_count - 1u] = SQL_FALSE;
                else if (left == SQL_TRUE && right == SQL_TRUE)
                    stack[stack_count - 1u] = SQL_TRUE;
                else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else if (opcode == RSQL_BOOL_OR) {
                if (left == SQL_TRUE || right == SQL_TRUE)
                    stack[stack_count - 1u] = SQL_TRUE;
                else if (left == SQL_FALSE && right == SQL_FALSE)
                    stack[stack_count - 1u] = SQL_FALSE;
                else stack[stack_count - 1u] = SQL_UNKNOWN;
            } else return 0u;
        }
    }
    return stack_count == 1u && stack[0] == SQL_TRUE;
}

static rsql_u8 first_on_matches(void) {
    if (g_rsql_cursor.join_type == RSQL_JOIN_CROSS) return 1u;
    return combine_program(g_rsql_cursor.bool_program, 0u,
        g_rsql_cursor.join_bool_program_count, 0u);
}

static rsql_u8 second_on_matches(void) {
    if (g_rsql_statement.subquery_compare_op == RSQL_JOIN_CROSS) return 1u;
    return combine_program(g_rsql_statement.subquery_bool_program, 0u,
        g_rsql_statement.subquery_bool_program_count, 1u);
}

static rsql_u8 where_matches(void) {
    if (!g_rsql_cursor.where_present) return 1u;
    return combine_program(g_rsql_cursor.bool_program,
        g_rsql_cursor.join_bool_program_count,
        (rsql_u8)(g_rsql_cursor.bool_program_count -
                  g_rsql_cursor.join_bool_program_count), 0u);
}

static rsql_u8 variable_predicates(void) {
    rsql_u8 rc;
    if (RSQL_VARIABLE_PREDICATE_MASK == 0u) return RSQL_OK;
    g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_PREDICATE;
    rc = rsql_query_variable_compare_owner(7u);
    return rc;
}

static rsql_u8 load_outer(rsql_u8 advance) {
    rsql_u8 rc;
    rc = access_next(g_rsql_cursor.using_index & 1u,
        &RSQL_WIDE_OUTER_INDEX, g_rsql_cursor.table_page,
        g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
        &g_wide_candidate, advance);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.row_id = g_wide_candidate;
    rc = raw_read(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                  &g_rsql_cursor.row_id, g_rsql_cursor.row);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.join_outer_started = 1u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_inner_null = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    g_rsql_cursor.update_scan_started = 0u;
    g_rsql_cursor.update_variable = 0u;
    return RSQL_OK;
}

static rsql_u8 load_indexed_join_outer(rsql_u8 advance) {
    rsql_u8 rc = access_next(g_rsql_cursor.using_index & 1u,
        &RSQL_JOIN_OUTER_INDEX, g_rsql_cursor.table_page,
        g_rsql_cursor.row_width, &g_rsql_cursor.row_id,
        &g_wide_candidate, advance);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.row_id = g_wide_candidate;
    rc = raw_read(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                  &g_rsql_cursor.row_id, g_rsql_cursor.row);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.join_outer_started = 1u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_inner_null = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_indexed_join_next_phase_c(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        g_rsql_cursor.join_type == RSQL_JOIN_NONE ||
        g_rsql_cursor.mode != RSQL_SELECT_SCAN ||
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_NONE) {
        return RSQL_ERR_CURSOR_STATE;
    }
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.join_outer_pending_advance) {
        rc = load_indexed_join_outer(1u);
        if (rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (rc != RSQL_OK) return rc;
    } else if (!g_rsql_cursor.join_outer_started) {
        rc = load_indexed_join_outer(0u);
        if (rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (rc != RSQL_OK) return rc;
    }
    for (;;) {
        rc = access_next(g_rsql_cursor.using_index & 2u,
            &RSQL_JOIN_INNER_INDEX, g_rsql_cursor.join_table_page,
            g_rsql_cursor.join_row_width, &g_rsql_cursor.join_row_id,
            &g_wide_candidate, g_rsql_cursor.join_inner_started);
        while (rc == RSQL_OK) {
            g_rsql_cursor.join_inner_started = 1u;
            g_rsql_cursor.join_row_id = g_wide_candidate;
            rc = raw_read(g_rsql_cursor.join_table_page,
                g_rsql_cursor.join_row_width, &g_rsql_cursor.join_row_id,
                g_rsql_cursor.scan_row);
            if (rc != RSQL_OK) return rc;
            g_rsql_cursor.join_inner_null = 0u;
            rc = variable_predicates();
            if (rc != RSQL_OK) return rc;
            if (first_on_matches()) {
                g_rsql_cursor.join_outer_matched = 1u;
                if (where_matches()) {
                    g_rsql_cursor.positioned = 1u;
                    request->has_row = 1u;
                    return RSQL_OK;
                }
            }
            rc = access_next(g_rsql_cursor.using_index & 2u,
                &RSQL_JOIN_INNER_INDEX, g_rsql_cursor.join_table_page,
                g_rsql_cursor.join_row_width, &g_rsql_cursor.join_row_id,
                &g_wide_candidate, 1u);
        }
        if (rc != RSQL_ERR_NOT_FOUND) return rc;
        if (g_rsql_cursor.join_type == RSQL_JOIN_LEFT &&
            !g_rsql_cursor.join_outer_matched) {
            null_row(g_rsql_cursor.scan_row,
                g_rsql_cursor.join_row_width,
                g_rsql_cursor.join_inner_column_count);
            g_rsql_cursor.join_row_id.page = RSQL_PAGE_NONE;
            g_rsql_cursor.join_row_id.slot = 0xFFu;
            g_rsql_cursor.join_inner_null = 1u;
            g_rsql_cursor.join_outer_matched = 1u;
            g_rsql_cursor.join_outer_pending_advance = 1u;
            rc = variable_predicates();
            if (rc != RSQL_OK) return rc;
            if (where_matches()) {
                g_rsql_cursor.positioned = 1u;
                request->has_row = 1u;
                return RSQL_OK;
            }
        }
        rc = load_indexed_join_outer(1u);
        if (rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (rc != RSQL_OK) return rc;
    }

finished:
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_wide_raw_next_c(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (!g_rsql_cursor.join_outer_started) {
        rc = load_outer(0u);
        if (rc == RSQL_ERR_NOT_FOUND) goto finished;
        if (rc != RSQL_OK) return rc;
    }
    for (;;) {
        if (!g_rsql_cursor.update_scan_started) {
            if (g_rsql_cursor.join_outer_pending_advance) {
                rc = load_outer(1u);
                if (rc == RSQL_ERR_NOT_FOUND) goto finished;
                if (rc != RSQL_OK) return rc;
                continue;
            } else if (g_rsql_cursor.join_inner_started) {
                rc = access_next(g_rsql_cursor.using_index & 2u,
                    &RSQL_WIDE_MIDDLE_INDEX,
                    g_rsql_cursor.join_table_page,
                    g_rsql_cursor.join_row_width,
                    &g_rsql_cursor.join_row_id, &g_wide_candidate, 1u);
            } else {
                rc = access_next(g_rsql_cursor.using_index & 2u,
                    &RSQL_WIDE_MIDDLE_INDEX,
                    g_rsql_cursor.join_table_page,
                    g_rsql_cursor.join_row_width,
                    &g_rsql_cursor.join_row_id, &g_wide_candidate, 0u);
            }
            if (rc == RSQL_ERR_NOT_FOUND) {
                if (g_rsql_cursor.join_type == RSQL_JOIN_LEFT &&
                    !g_rsql_cursor.join_outer_matched) {
                    null_row(g_rsql_cursor.scan_row,
                        g_rsql_cursor.join_row_width,
                        g_rsql_cursor.join_inner_column_count);
                    g_rsql_cursor.join_row_id.page = RSQL_PAGE_NONE;
                    g_rsql_cursor.join_row_id.slot = 0xFFu;
                    g_rsql_cursor.join_inner_started = 1u;
                    g_rsql_cursor.join_inner_null = 1u;
                    g_rsql_cursor.join_outer_matched = 1u;
                    g_rsql_cursor.join_outer_pending_advance = 1u;
                    g_rsql_cursor.update_variable = 0u;
                    goto scan_third;
                }
                rc = load_outer(1u);
                if (rc == RSQL_ERR_NOT_FOUND) goto finished;
                if (rc != RSQL_OK) return rc;
                continue;
            }
            if (rc != RSQL_OK) return rc;
            g_rsql_cursor.join_row_id = g_wide_candidate;
            rc = raw_read(g_rsql_cursor.join_table_page,
                g_rsql_cursor.join_row_width, &g_rsql_cursor.join_row_id,
                g_rsql_cursor.scan_row);
            if (rc != RSQL_OK) return rc;
            g_rsql_cursor.join_inner_started = 1u;
            if (!first_on_matches()) continue;
            g_rsql_cursor.join_outer_matched = 1u;
            g_rsql_cursor.join_inner_null = 0u;
            g_rsql_cursor.update_variable = 0u;
        }
scan_third:
        if (g_rsql_cursor.update_scan_started) {
            if (g_rsql_cursor.subquery_row_id.page == RSQL_PAGE_NONE) {
                rc = RSQL_ERR_NOT_FOUND;
            } else {
                rc = access_next(g_rsql_cursor.using_index & 4u,
                    &RSQL_WIDE_INNER_INDEX,
                    g_rsql_cursor.subquery_table_page,
                    g_rsql_cursor.subquery_row_width,
                    &g_rsql_cursor.subquery_row_id, &g_wide_candidate, 1u);
            }
        } else {
            rc = access_next(g_rsql_cursor.using_index & 4u,
                &RSQL_WIDE_INNER_INDEX,
                g_rsql_cursor.subquery_table_page,
                g_rsql_cursor.subquery_row_width,
                &g_rsql_cursor.subquery_row_id, &g_wide_candidate, 0u);
        }
        while (rc == RSQL_OK) {
            g_rsql_cursor.subquery_row_id = g_wide_candidate;
            rc = raw_read(g_rsql_cursor.subquery_table_page,
                g_rsql_cursor.subquery_row_width,
                &g_rsql_cursor.subquery_row_id, g_rsql_execution.row);
            if (rc != RSQL_OK) return rc;
            g_rsql_cursor.update_scan_started = 1u;
            rc = variable_predicates();
            if (rc != RSQL_OK) return rc;
            if (second_on_matches()) {
                g_rsql_cursor.update_variable = 1u;
                if (where_matches()) {
                    g_rsql_cursor.positioned = 1u;
                    request->has_row = 1u;
                    return RSQL_OK;
                }
            }
            rc = access_next(g_rsql_cursor.using_index & 4u,
                &RSQL_WIDE_INNER_INDEX,
                g_rsql_cursor.subquery_table_page,
                g_rsql_cursor.subquery_row_width,
                &g_rsql_cursor.subquery_row_id, &g_wide_candidate, 1u);
        }
        if (rc != RSQL_ERR_NOT_FOUND) return rc;
        if (g_rsql_statement.subquery_compare_op == RSQL_JOIN_LEFT &&
            !g_rsql_cursor.update_variable) {
            null_row(g_rsql_execution.row,
                g_rsql_cursor.subquery_row_width,
                g_rsql_cursor.subquery_column_count);
            g_rsql_cursor.subquery_row_id.page = RSQL_PAGE_NONE;
            g_rsql_cursor.subquery_row_id.slot = 0xFFu;
            g_rsql_cursor.update_scan_started = 1u;
            g_rsql_cursor.update_variable = 1u;
            rc = variable_predicates();
            if (rc != RSQL_OK) return rc;
            if (where_matches()) {
                g_rsql_cursor.positioned = 1u;
                request->has_row = 1u;
                return RSQL_OK;
            }
        }
        g_rsql_cursor.update_scan_started = 0u;
        g_rsql_cursor.update_variable = 0u;
    }

finished:
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 0u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_wide_raw_next_entry(
    RsqlCursorNextRequest* request);
void aggregate_current_entry(void);

static void restart_wide(void) {
    g_rsql_cursor.finished = 0u;
    g_rsql_cursor.positioned = 0u;
    g_rsql_cursor.join_outer_started = 0u;
    g_rsql_cursor.join_inner_started = 0u;
    g_rsql_cursor.join_inner_null = 0u;
    g_rsql_cursor.join_outer_matched = 0u;
    g_rsql_cursor.join_outer_pending_advance = 0u;
    g_rsql_cursor.update_scan_started = 0u;
    g_rsql_cursor.update_variable = 0u;
    RSQL_WIDE_OUTER_INDEX.page = RSQL_WIDE_OUTER_INDEX.head;
    RSQL_WIDE_OUTER_INDEX.slot = 0u;
    RSQL_WIDE_MIDDLE_INDEX.page = RSQL_WIDE_MIDDLE_INDEX.head;
    RSQL_WIDE_MIDDLE_INDEX.slot = 0u;
    RSQL_WIDE_INNER_INDEX.page = RSQL_WIDE_INNER_INDEX.head;
    RSQL_WIDE_INNER_INDEX.slot = 0u;
}

static void current_triple(WideTripleId* triple) {
    triple->outer = g_rsql_cursor.row_id;
    triple->middle = g_rsql_cursor.join_row_id;
    triple->inner = g_rsql_cursor.subquery_row_id;
}

static rsql_u8 same_triple(const WideTripleId* left,
                           const WideTripleId* right) {
    return memcmp(left, right, sizeof(*left)) == 0;
}

static rsql_u8 read_triple_source(const WideTripleId* triple, rsql_u8 source,
                                  rsql_u8* destination) {
    if (source & RSQL_SOURCE_SUBQUERY) {
        if (triple->inner.page == RSQL_PAGE_NONE) {
            null_row(destination, g_rsql_cursor.subquery_row_width,
                     g_rsql_cursor.subquery_column_count);
            return RSQL_OK;
        }
        return raw_read(g_rsql_cursor.subquery_table_page,
            g_rsql_cursor.subquery_row_width, &triple->inner, destination);
    }
    if (source & RSQL_SOURCE_INNER) {
        if (triple->middle.page == RSQL_PAGE_NONE) {
            null_row(destination, g_rsql_cursor.join_row_width,
                     g_rsql_cursor.join_inner_column_count);
            return RSQL_OK;
        }
        return raw_read(g_rsql_cursor.join_table_page,
            g_rsql_cursor.join_row_width, &triple->middle, destination);
    }
    return raw_read(g_rsql_cursor.table_page, g_rsql_cursor.row_width,
                    &triple->outer, destination);
}

rsql_u8 load_triple(const WideTripleId* triple) {
    rsql_u8 rc = read_triple_source(triple, 0u, g_rsql_cursor.row);
    if (rc == RSQL_OK) rc = read_triple_source(
        triple, RSQL_SOURCE_INNER, g_rsql_cursor.scan_row);
    if (rc == RSQL_OK) rc = read_triple_source(
        triple, RSQL_SOURCE_SUBQUERY, g_rsql_execution.row);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.row_id = triple->outer;
    g_rsql_cursor.join_row_id = triple->middle;
    g_rsql_cursor.subquery_row_id = triple->inner;
    g_rsql_cursor.join_outer_started = 1u;
    g_rsql_cursor.join_inner_started = 1u;
    g_rsql_cursor.join_inner_null =
        triple->middle.page == RSQL_PAGE_NONE;
    g_rsql_cursor.join_outer_matched = 1u;
    g_rsql_cursor.join_outer_pending_advance =
        g_rsql_cursor.join_inner_null;
    g_rsql_cursor.update_scan_started = 1u;
    g_rsql_cursor.update_variable = 1u;
    return RSQL_OK;
}

rsql_u8 rsql_query_wide_restore_phase_c(void) {
    return load_triple((const WideTripleId*)&g_rsql_cursor.row_id);
}

static rsql_u8 same_group(const WideTripleId* representative,
                          rsql_u8* same_out) {
    const RsqlColumnInfo* column;
    const rsql_u8* current;
    rsql_u16 width;
    rsql_u8 source;
    rsql_u8 null_mask;
    rsql_u8 representative_null;
    rsql_u8 current_null;
    rsql_u8 index;
    rsql_u8 rc;
    *same_out = 0u;
    for (index = 0u; index < g_rsql_cursor.group_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        column = source_column(source);
        current = source_row(source);
        null_mask = (rsql_u8)(1u << (source & RSQL_SOURCE_COLUMN_MASK));
        current_null = (current[0] & null_mask) != 0u;
        rc = read_triple_source(representative, source, g_rsql_meta_page0);
        if (rc != RSQL_OK) return rc;
        representative_null = (g_rsql_meta_page0[0] & null_mask) != 0u;
        if (current_null != representative_null) return RSQL_OK;
        if (current_null) continue;
        width = value_width(&column->type);
        if (column->type.tag == RSQL_TYPE_CHAR) {
            if (compare_chars(&current[column->offset], width,
                    &g_rsql_meta_page0[column->offset], width) != 0) {
                return RSQL_OK;
            }
        } else if (column->type.tag == RSQL_TYPE_FLOAT5) {
            if (compare_float(&current[column->offset],
                    &g_rsql_meta_page0[column->offset]) != 0) return RSQL_OK;
        } else if (memcmp(&current[column->offset],
                          &g_rsql_meta_page0[column->offset], width) != 0) {
            return RSQL_OK;
        }
    }
    *same_out = 1u;
    return RSQL_OK;
}

static rsql_u8 i64_zero(const RsqlI64* value) {
    return memcmp(value, &ZERO_I64, sizeof(*value)) == 0;
}

static void i64_set(RsqlI64* destination, const rsql_u8* value,
                    rsql_u8 width) {
    rsql_u8 fill = (value[width - 1u] & 0x80u) ? 0xFFu : 0u;
    rsql_u8 index;
    for (index = 0u; index < sizeof(destination->bytes); ++index) {
        destination->bytes[index] = index < width ? value[index] : fill;
    }
}

static void i64_add(RsqlI64* total, const rsql_u8* value, rsql_u8 width) {
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

static void float_add(rsql_u8* total, const rsql_u8* value) {
    memcpy(rsql_float_a, total, RSQL_FLOAT5_BYTES);
    memcpy(rsql_float_b, value, RSQL_FLOAT5_BYTES);
    rsql_float_destination = total;
    rsql_float_add_abi();
}

static void float_divide(rsql_u8* total, const rsql_u8* count) {
    memcpy(rsql_float_a, total, RSQL_FLOAT5_BYTES);
    memcpy(rsql_float_b, count, RSQL_FLOAT5_BYTES);
    rsql_float_destination = total;
    rsql_float_div_abi();
}

static void aggregate_reset(void) {
    rsql_aggregate_reset_state();
}

void aggregate_current_c(void) {
    static const rsql_u8 float_one[5] = { 0x81u, 0u, 0u, 0u, 0u };
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
            rsql_i64_increment(&g_rsql_cursor.aggregate_values[result]);
            continue;
        }
        source = g_rsql_cursor.projection[result];
        if (source_null(source)) continue;
        if (aggregate == RSQL_AGG_COUNT) {
            rsql_i64_increment(&g_rsql_cursor.aggregate_values[result]);
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
                    comparison = compare_float(value,
                        g_rsql_cursor.aggregate_values[result].bytes);
                    if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                        (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                        memcpy(g_rsql_cursor.aggregate_values[result].bytes,
                               value, RSQL_FLOAT5_BYTES);
                    }
                }
            } else float_add(g_rsql_cursor.aggregate_values[result].bytes,
                             value);
            float_add(g_rsql_cursor.aggregate_counts[result].bytes,
                      float_one);
            continue;
        }
        width = (rsql_u8)value_width(&column->type);
        if (aggregate == RSQL_AGG_MIN || aggregate == RSQL_AGG_MAX) {
            i64_set(&candidate, value, width);
            if (i64_zero(&g_rsql_cursor.aggregate_counts[result])) {
                g_rsql_cursor.aggregate_values[result] = candidate;
            } else {
                comparison = compare_signed(candidate.bytes, 8u,
                    g_rsql_cursor.aggregate_values[result].bytes, 8u);
                if ((aggregate == RSQL_AGG_MIN && comparison < 0) ||
                    (aggregate == RSQL_AGG_MAX && comparison > 0)) {
                    g_rsql_cursor.aggregate_values[result] = candidate;
                }
            }
        } else i64_add(&g_rsql_cursor.aggregate_values[result], value, width);
        rsql_i64_increment(&g_rsql_cursor.aggregate_counts[result]);
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
                g_rsql_cursor.aggregate_nulls |= (rsql_u8)(1u << result);
            } else if (aggregate == RSQL_AGG_AVG) {
                float_divide(g_rsql_cursor.aggregate_values[result].bytes,
                    g_rsql_cursor.aggregate_counts[result].bytes);
            }
        } else if (i64_zero(&g_rsql_cursor.aggregate_counts[result])) {
            g_rsql_cursor.aggregate_nulls |= (rsql_u8)(1u << result);
        } else if (aggregate == RSQL_AGG_AVG) {
            rsql_wide_i64_divide(
                &g_rsql_cursor.aggregate_values[result]);
        }
    }
}

static rsql_u8 candidate_duplicate(const WideTripleId* candidate,
                                   RsqlCursorNextRequest* request,
                                   rsql_u8* duplicate_out) {
    WideTripleId current;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_triple(&current);
        if (same_triple(candidate, &current)) return RSQL_OK;
        rc = same_group(candidate, &same);
        if (rc != RSQL_OK) return rc;
        if (same) *duplicate_out = 1u;
    }
}

static rsql_u8 aggregate_group(const WideTripleId* representative,
                               RsqlCursorNextRequest* request) {
    rsql_u8 same;
    rsql_u8 rc;
    aggregate_reset();
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        rc = same_group(representative, &same);
        if (rc != RSQL_OK) return rc;
        if (same) aggregate_current_entry();
    }
    aggregate_finalize();
    rc = load_triple(representative);
    if (rc != RSQL_OK) return rc;
    g_rsql_cursor.finished = 0u;
    g_rsql_cursor.positioned = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

static rsql_u8 next_group(RsqlCursorNextRequest* request) {
    WideTripleId prior;
    WideTripleId candidate;
    WideTripleId current;
    rsql_u8 after_prior = g_rsql_cursor.positioned ? 0u : 1u;
    rsql_u8 duplicate;
    rsql_u8 rc;
    if (!after_prior) current_triple(&prior);
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_OK;
        current_triple(&current);
        if (!after_prior) {
            if (same_triple(&prior, &current)) after_prior = 1u;
            continue;
        }
        candidate = current;
        rc = candidate_duplicate(&candidate, request, &duplicate);
        if (rc != RSQL_OK) return rc;
        if (!duplicate) return aggregate_group(&candidate, request);
    }
}

rsql_u8 __fastcall__ rsql_wide_aggregate_next_c(
    RsqlCursorNextRequest* request) {
    rsql_u8 rc;
    request->has_row = 0u;
    if (g_rsql_cursor.finished) {
        g_rsql_cursor.positioned = 0u;
        return RSQL_OK;
    }
    if (g_rsql_cursor.group_count) return next_group(request);
    aggregate_reset();
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        aggregate_current_entry();
    }
    aggregate_finalize();
    g_rsql_cursor.finished = 1u;
    g_rsql_cursor.positioned = 1u;
    request->has_row = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_wide_aggregate_next_entry(
    RsqlCursorNextRequest* request);

static rsql_i8 compare_triple_identity(const WideTripleId* left,
                                       const WideTripleId* right) {
    rsql_i8 comparison = memcmp(&left->outer, &right->outer,
                                sizeof(RsqlRowId));
    if (comparison) return comparison < 0 ? -1 : 1;
    comparison = memcmp(&left->middle, &right->middle, sizeof(RsqlRowId));
    if (comparison) return comparison < 0 ? -1 : 1;
    comparison = memcmp(&left->inner, &right->inner, sizeof(RsqlRowId));
    if (comparison) return comparison < 0 ? -1 : 1;
    return 0;
}

/* The current triple remains in its three normal row buffers. Read only the
 * requested source from the target into a different row buffer, so a fixed
 * comparison never needs a fourth materialized row. */
static rsql_u8 compare_current_source(const WideTripleId* target,
                                      rsql_u8 source,
                                      rsql_i8* comparison_out) {
    const RsqlColumnInfo* column = source_column(source);
    const rsql_u8* left_row = source_row(source);
    rsql_u8* right_row = (source & (RSQL_SOURCE_INNER |
                                    RSQL_SOURCE_SUBQUERY))
        ? g_rsql_cursor.row : g_rsql_cursor.scan_row;
    rsql_u8 column_index = source & RSQL_SOURCE_COLUMN_MASK;
    rsql_u8 mask = slot_mask(column_index);
    rsql_u8 left_null = (left_row[0] & mask) != 0u;
    rsql_u8 right_null;
    rsql_u8 width;
    rsql_u8 rc = read_triple_source(target, source, right_row);
    if (rc != RSQL_OK) return rc;
    right_null = (right_row[0] & mask) != 0u;
    if (left_null != right_null) {
        *comparison_out = left_null ? -1 : 1;
        return RSQL_OK;
    }
    if (left_null) {
        *comparison_out = 0;
        return RSQL_OK;
    }
    width = (rsql_u8)value_width(&column->type);
    if (column->type.tag == RSQL_TYPE_TEXT ||
        column->type.tag == RSQL_TYPE_BLOB) {
        memcpy(g_rsql_statement.enum_values, g_rsql_execution.columns,
               RSQL_VARIABLE_COMPARE_STATE_BYTES);
        memcpy(g_rsql_variable_compare_left,
               &left_row[column->offset], 4u);
        memcpy(g_rsql_variable_compare_right,
               &right_row[column->offset], 4u);
        g_rsql_variable_compare_kind = column->type.tag;
        g_rsql_variable_compare_source = RSQL_VARIABLE_COMPARE_HANDLES;
        rc = rsql_query_variable_compare_owner(7u);
        memcpy(g_rsql_execution.columns, g_rsql_statement.enum_values,
               RSQL_VARIABLE_COMPARE_STATE_BYTES);
        if (rc != RSQL_OK) return rc;
        *comparison_out = g_rsql_variable_compare_result;
    } else if (column->type.tag == RSQL_TYPE_CHAR) {
        *comparison_out = compare_chars(&left_row[column->offset], width,
                                        &right_row[column->offset], width);
    } else if (column->type.tag == RSQL_TYPE_FLOAT5) {
        *comparison_out = compare_float(&left_row[column->offset],
                                        &right_row[column->offset]);
    } else if (column->type.tag == RSQL_TYPE_BOOLEAN ||
               column->type.tag == RSQL_TYPE_ENUM8 ||
               column->type.tag == RSQL_TYPE_ENUM16) {
        *comparison_out = compare_unsigned(&left_row[column->offset],
                                           &right_row[column->offset], width);
    } else {
        *comparison_out = compare_signed(&left_row[column->offset], width,
                                         &right_row[column->offset], width);
    }
    return RSQL_OK;
}

static rsql_u8 compare_raw_triples(const WideTripleId* left,
                                   const WideTripleId* right,
                                   rsql_i8* comparison_out) {
    rsql_i8 comparison;
    rsql_u8 source;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        source = g_rsql_cursor.group_columns[index];
        if (source & WIDE_ORDER_SCALAR) {
            rc = rsql_wide_compare_scalar(left, right,
                source & RSQL_ORDER_PROJECTION_MASK, &comparison);
        } else {
            rc = load_triple(left);
            if (rc != RSQL_OK) return rc;
            rc = compare_current_source(right, source, &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison) {
            if (g_rsql_cursor.order_desc_mask & slot_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            *comparison_out = comparison;
            return RSQL_OK;
        }
    }
    *comparison_out = compare_triple_identity(left, right);
    return RSQL_OK;
}

static rsql_u8 same_raw_projection(const WideTripleId* left,
                                   const WideTripleId* right,
                                   rsql_u8* same_out) {
    rsql_i8 comparison;
    rsql_u8 result;
    rsql_u8 rc;
    *same_out = 0u;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[result])) {
            rc = rsql_wide_compare_scalar(left, right, result, &comparison);
        } else {
            rc = load_triple(left);
            if (rc != RSQL_OK) return rc;
            rc = compare_current_source(right,
                g_rsql_cursor.projection[result], &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison) return RSQL_OK;
    }
    *same_out = 1u;
    return RSQL_OK;
}

static rsql_u8 raw_projection_duplicate(const WideTripleId* candidate,
                                        RsqlCursorNextRequest* request,
                                        rsql_u8* duplicate_out) {
    WideTripleId prior;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_triple(&prior);
        if (same_triple(candidate, &prior)) return RSQL_OK;
        rc = same_raw_projection(candidate, &prior, &same);
        if (rc != RSQL_OK) return rc;
        if (same) *duplicate_out = 1u;
        rc = load_triple(&prior);
        if (rc != RSQL_OK) return rc;
    }
}

static void wide_last_triple(WideTripleId* triple) {
    triple->outer = g_rsql_cursor.update_next_row_id;
    triple->middle.page = g_rsql_cursor.index_page;
    triple->middle.slot = g_rsql_cursor.index_leaf_slot;
    triple->inner.page = g_rsql_cursor.index_leaf_page;
    triple->inner.slot = g_rsql_cursor.update_next_valid;
}

static void wide_store_last(const WideTripleId* triple) {
    g_rsql_cursor.update_next_row_id = triple->outer;
    g_rsql_cursor.index_page = triple->middle.page;
    g_rsql_cursor.index_leaf_slot = triple->middle.slot;
    g_rsql_cursor.index_leaf_page = triple->inner.page;
    g_rsql_cursor.update_next_valid = triple->inner.slot;
}

static rsql_u8 select_raw_triple(RsqlCursorNextRequest* request,
                                 rsql_u8* found_out) {
    WideTripleId current;
    WideTripleId best;
    WideTripleId last;
    rsql_i8 comparison;
    rsql_u8 duplicate;
    rsql_u8 have_best = 0u;
    rsql_u8 have_last = g_rsql_cursor.returned_rows != 0u ||
                        g_rsql_cursor.skipped_rows != 0u;
    rsql_u8 rc;
    *found_out = 0u;
    if (have_last) wide_last_triple(&last);
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        current_triple(&current);
        if (have_last) {
            rc = compare_raw_triples(&current, &last, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison <= 0) {
                rc = load_triple(&current);
                if (rc != RSQL_OK) return rc;
                continue;
            }
        }
        if (g_rsql_cursor.distinct) {
            rc = raw_projection_duplicate(&current, request, &duplicate);
            if (rc != RSQL_OK) return rc;
            if (duplicate) continue;
        }
        if (have_best) {
            rc = compare_raw_triples(&current, &best, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison >= 0) {
                rc = load_triple(&current);
                if (rc != RSQL_OK) return rc;
                continue;
            }
        }
        best = current;
        have_best = 1u;
        rc = load_triple(&current);
        if (rc != RSQL_OK) return rc;
    }
    if (!have_best) return RSQL_OK;
    rc = load_triple(&best);
    if (rc != RSQL_OK) return rc;
    wide_store_last(&best);
    *found_out = 1u;
    return RSQL_OK;
}

static rsql_u8 compare_group_aggregate(const WideTripleId* left,
                                       const WideTripleId* right,
                                       rsql_u8 result,
                                       RsqlCursorNextRequest* request,
                                       rsql_i8* comparison_out) {
    RsqlI64 saved;
    rsql_u8 left_null;
    rsql_u8 right_null;
    rsql_u8 aggregate = g_rsql_cursor.projection_aggregate[result];
    rsql_u8 source = g_rsql_cursor.projection[result];
    rsql_u8 rc = aggregate_group(left, request);
    if (rc != RSQL_OK) return rc;
    left_null = (g_rsql_cursor.aggregate_nulls & slot_mask(result)) != 0u;
    saved = g_rsql_cursor.aggregate_values[result];
    rc = aggregate_group(right, request);
    if (rc != RSQL_OK) return rc;
    right_null = (g_rsql_cursor.aggregate_nulls & slot_mask(result)) != 0u;
    if (left_null != right_null) *comparison_out = left_null ? -1 : 1;
    else if (left_null) *comparison_out = 0;
    else if (aggregate != RSQL_AGG_COUNT_STAR &&
             aggregate != RSQL_AGG_COUNT &&
             source_column(source)->type.tag == RSQL_TYPE_FLOAT5) {
        *comparison_out = compare_float(saved.bytes,
            g_rsql_cursor.aggregate_values[result].bytes);
    } else *comparison_out = compare_signed(saved.bytes, 8u,
        g_rsql_cursor.aggregate_values[result].bytes, 8u);
    return RSQL_OK;
}

static rsql_u8 compare_group_results(const WideTripleId* left,
                                     const WideTripleId* right,
                                     RsqlCursorNextRequest* request,
                                     rsql_i8* comparison_out) {
    rsql_i8 comparison = 0;
    rsql_u8 descriptor;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_rsql_cursor.order_count; ++index) {
        descriptor = RSQL_AGGREGATE_ORDER_COLUMNS[index];
        if (descriptor & WIDE_ORDER_AGGREGATE) {
            descriptor &= RSQL_ORDER_PROJECTION_MASK;
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_cursor.projection_aggregate[descriptor])) {
                rc = rsql_wide_compare_scalar(left, right, descriptor,
                                              &comparison);
            } else {
                rc = compare_group_aggregate(left, right, descriptor,
                                             request, &comparison);
            }
        } else {
            rc = load_triple(left);
            if (rc == RSQL_OK) {
                rc = compare_current_source(right, descriptor, &comparison);
            }
        }
        if (rc != RSQL_OK) return rc;
        if (comparison) {
            if (g_rsql_cursor.order_desc_mask & slot_mask(index)) {
                comparison = (rsql_i8)-comparison;
            }
            break;
        }
    }
    if (!comparison) comparison = compare_triple_identity(left, right);
    rc = load_triple(left);
    if (rc != RSQL_OK) return rc;
    *comparison_out = comparison;
    return RSQL_OK;
}

static rsql_u8 same_group_projection(const WideTripleId* left,
                                     const WideTripleId* right,
                                     RsqlCursorNextRequest* request,
                                     rsql_u8* same_out) {
    rsql_i8 comparison;
    rsql_u8 result;
    rsql_u8 rc;
    *same_out = 0u;
    for (result = 0u; result < g_rsql_cursor.result_column_count; ++result) {
        if (RSQL_PROJECTION_IS_SCALAR(
                g_rsql_cursor.projection_aggregate[result])) {
            rc = rsql_wide_compare_scalar(left, right, result, &comparison);
        } else if (g_rsql_cursor.projection_aggregate[result] !=
                   RSQL_AGG_NONE) {
            rc = compare_group_aggregate(left, right, result,
                                         request, &comparison);
        } else {
            rc = load_triple(left);
            if (rc == RSQL_OK) rc = compare_current_source(right,
                g_rsql_cursor.projection[result], &comparison);
        }
        if (rc != RSQL_OK) return rc;
        if (comparison) return load_triple(left);
    }
    rc = load_triple(left);
    if (rc == RSQL_OK) *same_out = 1u;
    return rc;
}

static rsql_u8 group_projection_duplicate(
    const WideTripleId* candidate, RsqlCursorNextRequest* request,
    rsql_u8* duplicate_out) {
    WideTripleId prior;
    rsql_u8 duplicate;
    rsql_u8 same;
    rsql_u8 rc;
    *duplicate_out = 0u;
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) return RSQL_ERR_CORRUPT_STORAGE;
        current_triple(&prior);
        if (same_triple(candidate, &prior)) return load_triple(candidate);
        rc = candidate_duplicate(&prior, request, &duplicate);
        if (rc != RSQL_OK) return rc;
        if (!duplicate) {
            rc = same_group_projection(candidate, &prior, request, &same);
            if (rc != RSQL_OK) return rc;
            if (same) {
                *duplicate_out = 1u;
                return load_triple(candidate);
            }
        }
        rc = load_triple(&prior);
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 select_group(RsqlCursorNextRequest* request,
                            rsql_u8* found_out) {
    WideTripleId candidate;
    WideTripleId best;
    WideTripleId last;
    rsql_i8 comparison;
    rsql_u8 duplicate;
    rsql_u8 have_best = 0u;
    rsql_u8 have_last = g_rsql_cursor.returned_rows != 0u ||
                        g_rsql_cursor.skipped_rows != 0u;
    rsql_u8 rc;
    *found_out = 0u;
    if (have_last) wide_last_triple(&last);
    restart_wide();
    for (;;) {
        rc = rsql_wide_raw_next_entry(request);
        if (rc != RSQL_OK) return rc;
        if (!request->has_row) break;
        current_triple(&candidate);
        rc = candidate_duplicate(&candidate, request, &duplicate);
        if (rc != RSQL_OK) return rc;
        if (duplicate) continue;
        if (g_rsql_cursor.distinct) {
            rc = group_projection_duplicate(&candidate, request, &duplicate);
            if (rc != RSQL_OK) return rc;
            if (duplicate) continue;
        }
        if (have_last) {
            rc = compare_group_results(&candidate, &last,
                                       request, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison <= 0) continue;
        }
        if (have_best) {
            rc = compare_group_results(&candidate, &best,
                                       request, &comparison);
            if (rc != RSQL_OK) return rc;
            if (comparison >= 0) continue;
        }
        best = candidate;
        have_best = 1u;
    }
    if (!have_best) return RSQL_OK;
    rc = aggregate_group(&best, request);
    if (rc != RSQL_OK) return rc;
    wide_store_last(&best);
    *found_out = 1u;
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_query_wide_result_next_phase(
    RsqlCursorNextRequest* request) {
    rsql_u8 found;
    rsql_u8 rc;
    if (!request || request->cursor != 1u || !g_rsql_cursor.active ||
        g_rsql_cursor.subquery_kind != RSQL_SUBQUERY_WIDE_JOIN ||
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
    if (g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE &&
        g_rsql_cursor.group_count == 0u) {
        if (g_rsql_cursor.offset != 0u) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        rc = rsql_wide_aggregate_next_entry(request);
        if (rc == RSQL_OK && request->has_row) ++g_rsql_cursor.returned_rows;
        return rc;
    }
    for (;;) {
        rc = g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE
            ? select_group(request, &found)
            : select_raw_triple(request, &found);
        if (rc != RSQL_OK) return rc;
        if (!found) {
            g_rsql_cursor.finished = 1u;
            g_rsql_cursor.positioned = 0u;
            return RSQL_OK;
        }
        if (g_rsql_cursor.skipped_rows < g_rsql_cursor.offset) {
            ++g_rsql_cursor.skipped_rows;
            continue;
        }
        ++g_rsql_cursor.returned_rows;
        g_rsql_cursor.finished = 0u;
        g_rsql_cursor.positioned = 1u;
        request->has_row = 1u;
        return RSQL_OK;
    }
}

rsql_u8 __fastcall__ rsql_query_wide_join_next_phase_c(
    RsqlCursorNextRequest* request) {
    return g_rsql_cursor.mode == RSQL_SELECT_AGGREGATE
        ? rsql_wide_aggregate_next_entry(request)
        : rsql_wide_raw_next_entry(request);
}

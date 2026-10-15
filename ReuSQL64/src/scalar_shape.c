#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define SCALAR_PART_TEXT 1u
#define SCALAR_PAGE_NEXT 6u
#define SCALAR_PAGE_USED 8u
#define SCALAR_PAGE_DATA 10u
#define SCALAR_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - SCALAR_PAGE_DATA)

RsqlScalarComparePart* g_rsql_scalar_compare_part;
rsql_u16 g_rsql_scalar_compare_offset;
rsql_u16 g_rsql_scalar_compare_page_start;
rsql_u8 g_rsql_scalar_compare_right;
rsql_u8* g_rsql_scalar_compare_value;

extern rsql_u8 rsql_scalar_compare_part_byte(void);

static rsql_u8 scalar_fold(rsql_u8 value) {
    return value >= 'a' && value <= 'z'
        ? (rsql_u8)(value - ('a' - 'A')) : value;
}

static rsql_u16 scalar_value_length(const RsqlScalarCompareValue* value) {
    rsql_u16 length = value->parts[0].length;
    if (value->part_count > 1u) length = (rsql_u16)
        (length + value->parts[1].length);
    return length;
}

static rsql_u8 scalar_value_byte(RsqlScalarCompareValue* value,
                                 rsql_u16 offset, rsql_u8 right,
                                 rsql_u8* byte) {
    if (offset < value->parts[0].length) {
        g_rsql_scalar_compare_part = &value->parts[0];
    } else {
        offset = (rsql_u16)(offset - value->parts[0].length);
        g_rsql_scalar_compare_part = &value->parts[1];
    }
    g_rsql_scalar_compare_offset = offset;
    g_rsql_scalar_compare_right = right;
    g_rsql_scalar_compare_value = byte;
    return rsql_scalar_compare_part_byte();
}

rsql_u8 rsql_query_variable_scalar_compare_phase(void) {
    RsqlScalarCompareValue* left = RSQL_SCALAR_COMPARE_LEFT;
    RsqlScalarCompareValue* right = RSQL_SCALAR_COMPARE_RIGHT;
    rsql_u16 left_length;
    rsql_u16 right_length;
    rsql_u16 common;
    rsql_u16 offset;
    rsql_u8 left_byte;
    rsql_u8 right_byte;
    rsql_u8 rc;
    if (left->is_null != right->is_null) {
        g_rsql_variable_compare_result = left->is_null ? -1 : 1;
        return RSQL_OK;
    }
    if (left->is_null) {
        g_rsql_variable_compare_result = 0;
        return RSQL_OK;
    }
    left_length = scalar_value_length(left);
    right_length = scalar_value_length(right);
    if ((g_rsql_cursor.projection_aggregate[g_rsql_variable_compare_kind] &
            RSQL_PROJECTION_OP_MASK) == RSQL_SCALAR_LENGTH) {
        g_rsql_variable_compare_result = left_length < right_length ? -1 :
            (left_length > right_length ? 1 : 0);
        return RSQL_OK;
    }
    common = left_length < right_length ? left_length : right_length;
    for (offset = 0u; offset < common; ++offset) {
        rc = scalar_value_byte(left, offset, 0u, &left_byte);
        if (rc == RSQL_OK) {
            rc = scalar_value_byte(right, offset, 1u, &right_byte);
        }
        if (rc != RSQL_OK) return rc;
        left_byte = scalar_fold(left_byte);
        right_byte = scalar_fold(right_byte);
        if (left_byte != right_byte) {
            g_rsql_variable_compare_result = left_byte < right_byte ? -1 : 1;
            return RSQL_OK;
        }
    }
    g_rsql_variable_compare_result = left_length < right_length ? -1 :
        (left_length > right_length ? 1 : 0);
    return RSQL_OK;
}

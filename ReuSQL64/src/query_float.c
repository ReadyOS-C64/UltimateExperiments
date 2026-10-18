#include <string.h>

#include "rsql_errors.h"
#include "rsql_float.h"

rsql_u8 rsql_query_resolve_float_value(const RsqlColumnInfo* column,
                                       RsqlParsedValue* value) {
    if (column->type.tag != RSQL_TYPE_FLOAT5) {
        return value->kind == RSQL_VALUE_FLOAT
            ? RSQL_ERR_TYPE_MISMATCH : RSQL_OK;
    }
    if (value->kind == RSQL_VALUE_NULL) return RSQL_OK;
    if (value->kind != RSQL_VALUE_INTEGER &&
        value->kind != RSQL_VALUE_FLOAT) return RSQL_ERR_TYPE_MISMATCH;
    if (value->length == 0u || value->length > RSQL_VALUE_STRING_MAX) {
        return RSQL_ERR_TYPE_MISMATCH;
    }
    if (value->string[0] == '-') rsql_float_negative = 1u;
    else rsql_float_negative = 0u;
    if (value->string[0] == '-' || value->string[0] == '+') {
        if (value->length == 1u) return RSQL_ERR_TYPE_MISMATCH;
        memcpy(rsql_float_text, &value->string[1], value->length - 1u);
        rsql_float_text[value->length - 1u] = 0u;
    } else {
        memcpy(rsql_float_text, value->string, value->length);
        rsql_float_text[value->length] = 0u;
    }
    value->kind = RSQL_VALUE_FLOAT;
    rsql_float_destination = value->integer.bytes;
    rsql_float_eval_abi();
    return RSQL_OK;
}

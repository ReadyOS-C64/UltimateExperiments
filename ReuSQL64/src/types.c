#include "rsql_errors.h"
#include "rsql_types.h"

rsql_u8 rsql_type_width(const RsqlTypeSpec* type, rsql_u16* width_out) {
    if (!type || !width_out) return RSQL_ERR_INVALID_ARGUMENT;
    switch (type->tag) {
        case RSQL_TYPE_BOOLEAN:
        case RSQL_TYPE_I8:
        case RSQL_TYPE_ENUM8:
            *width_out = 1u;
            return RSQL_OK;
        case RSQL_TYPE_I16:
        case RSQL_TYPE_FIXED8_8:
        case RSQL_TYPE_ENUM16:
            *width_out = 2u;
            return RSQL_OK;
        case RSQL_TYPE_I32:
            *width_out = 4u;
            return RSQL_OK;
        case RSQL_TYPE_I64:
            *width_out = 8u;
            return RSQL_OK;
        case RSQL_TYPE_FLOAT5:
            *width_out = 5u;
            return RSQL_OK;
        case RSQL_TYPE_CHAR:
            if (type->parameter == 0u || type->parameter > 223u) {
                return RSQL_ERR_TYPE_MISMATCH;
            }
            *width_out = type->parameter;
            return RSQL_OK;
        case RSQL_TYPE_TEXT:
        case RSQL_TYPE_BLOB:
            /* Stable 32-bit directory handle; payload is stored elsewhere. */
            *width_out = 4u;
            return RSQL_OK;
        default:
            return RSQL_ERR_TYPE_MISMATCH;
    }
}

#pragma code-name ("ABI")

rsql_u8 rsql_type_is_variable(const RsqlTypeSpec* type) {
    if (!type) return 0u;
    return type->tag == RSQL_TYPE_TEXT || type->tag == RSQL_TYPE_BLOB;
}

#pragma code-name ("OVERLAY0")

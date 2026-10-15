#include <string.h>

#include "rsql_blob.h"
#include "rsql_errors.h"
#include "rsql_query.h"

static rsql_u8 null_mask(rsql_u8 column) {
    return (rsql_u8)(1u << column);
}

rsql_u8 rsql_query_create_blob_value(const RsqlColumnInfo* column,
                                     const RsqlParsedValue* value,
                                     RsqlBlobHandle* handle) {
    if (column->type.tag == RSQL_TYPE_TEXT) {
        if (value->kind != RSQL_VALUE_STRING) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        return rsql_blob_create(RSQL_BLOB_KIND_TEXT, value->string,
                                value->length, handle);
    }
    if (column->type.tag == RSQL_TYPE_BLOB) {
        if (value->kind != RSQL_VALUE_BINARY) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        return rsql_blob_create(RSQL_BLOB_KIND_BINARY, value->string,
                                value->length, handle);
    }
    return RSQL_ERR_UNSUPPORTED_SQL;
}

rsql_u8 rsql_query_materialize_update(void) {
    RsqlBlobHandle old_handle;
    RsqlBlobHandle new_handle;
    const RsqlParsedValue* value;
    const RsqlColumnInfo* column;
    rsql_u8 source;
    rsql_u8 assignment;
    rsql_u8 rc;
    for (assignment = 0u; assignment < g_rsql_cursor.update_count;
         ++assignment) {
        source = g_rsql_cursor.update_columns[assignment];
        column = &g_rsql_cursor.columns[source];
        if (column->type.tag != RSQL_TYPE_TEXT &&
            column->type.tag != RSQL_TYPE_BLOB) continue;
        value = &g_rsql_statement.values[assignment];
        if (!(g_rsql_cursor.row[0] & null_mask(source))) {
            memcpy(old_handle.bytes, &g_rsql_cursor.row[column->offset], 4u);
        }
        if (value->kind != RSQL_VALUE_NULL) {
            rc = rsql_query_create_blob_value(column, value, &new_handle);
            if (rc != RSQL_OK) return rc;
        }
        if (!(g_rsql_cursor.row[0] & null_mask(source))) {
            rc = rsql_blob_delete(&old_handle);
            if (rc != RSQL_OK) return rc;
        }
        if (value->kind == RSQL_VALUE_NULL) {
            g_rsql_cursor.row[0] |= null_mask(source);
            memset(&g_rsql_cursor.row[column->offset], 0, 4u);
        } else {
            g_rsql_cursor.row[0] &= (rsql_u8)~null_mask(source);
            memcpy(&g_rsql_cursor.row[column->offset], new_handle.bytes, 4u);
        }
    }
    return RSQL_OK;
}

#include <cbm.h>
#include <string.h>

#include "rsql_errors.h"
#include "rsql_export.h"

static RsqlQueryOpenRequest g_export_open;
static RsqlCursorNextRequest g_export_next;
static RsqlCursorColumnRequest g_export_column;
static RsqlValueReadRequest g_export_read;
static RsqlQueryCloseRequest g_export_close;
static rsql_u8 g_export_buffer[64];

static void increment32(RsqlI32* value) {
    rsql_u8 index;
    for (index = 0u; index < 4u; ++index) {
        ++value->bytes[index];
        if (value->bytes[index] != 0u) break;
    }
}

static void add_bytes(RsqlI32* value, rsql_u16 amount) {
    rsql_u16 sum = (rsql_u16)value->bytes[0] + (amount & 0xFFu);
    value->bytes[0] = (rsql_u8)sum;
    sum = (rsql_u16)value->bytes[1] + (amount >> 8u) + (sum >> 8u);
    value->bytes[1] = (rsql_u8)sum;
    if ((sum >> 8u) != 0u) {
        if (++value->bytes[2] == 0u) ++value->bytes[3];
    }
}

static rsql_u8 write_bytes(RsqlD81ExportRequest* request,
                           const void* bytes, rsql_u16 length) {
    int written = cbm_write(request->logical_file, bytes, length);
    if (written != (int)length) return RSQL_ERR_IO;
    add_bytes(&request->bytes_written, length);
    return RSQL_OK;
}

static rsql_u8 write_field(RsqlD81ExportRequest* request, rsql_u8 column) {
    rsql_u16 offset;
    rsql_u16 remaining;
    rsql_u16 chunk;
    rsql_u8 header[4];
    rsql_u8 rc;

    g_export_column.cursor = g_export_open.cursor;
    g_export_column.column = column;
    rc = rsql_cursor_column(&g_export_column);
    if (rc != RSQL_OK) return rc;
    header[0] = g_export_column.value.type.tag;
    header[1] = g_export_column.value.is_null;
    header[2] = (rsql_u8)g_export_column.value.length;
    header[3] = (rsql_u8)(g_export_column.value.length >> 8u);
    rc = write_bytes(request, header, sizeof(header));
    if (rc != RSQL_OK || g_export_column.value.is_null) return rc;

    if (!rsql_type_is_variable(&g_export_column.value.type)) {
        return write_bytes(request, g_export_column.value.bytes,
                           g_export_column.value.length);
    }
    offset = 0u;
    remaining = g_export_column.value.length;
    while (remaining != 0u) {
        chunk = remaining > sizeof(g_export_buffer)
            ? sizeof(g_export_buffer) : remaining;
        g_export_read.cursor = g_export_open.cursor;
        g_export_read.column = column;
        g_export_read.offset = offset;
        g_export_read.destination = g_export_buffer;
        g_export_read.capacity = chunk;
        rc = rsql_value_read(&g_export_read);
        if (rc != RSQL_OK || g_export_read.bytes_read != chunk) {
            return rc == RSQL_OK ? RSQL_ERR_IO : rc;
        }
        rc = write_bytes(request, g_export_buffer, chunk);
        if (rc != RSQL_OK) return rc;
        offset += chunk;
        remaining -= chunk;
    }
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_export_d81(RsqlD81ExportRequest* request) {
    /* Numeric magic bytes keep the on-disk signature independent of cc65's
     * target character-map translation. Row strings remain raw C64 bytes. */
    static const rsql_u8 header[] = { 0x52u, 0x53u, 0x51u, 0x58u,
                                      RSQL_EXPORT_VERSION };
    rsql_u8 marker;
    rsql_u8 column;
    rsql_u8 rc;
    rsql_u8 close_rc;
    rsql_u8 file_open = 0u;
    rsql_u8 cursor_open = 0u;

    if (!request || !request->query || !request->filename ||
        request->device == 0u || request->logical_file == 0u) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    memset(&request->rows_written, 0, sizeof(request->rows_written));
    memset(&request->bytes_written, 0, sizeof(request->bytes_written));
    memset(&g_export_open, 0, sizeof(g_export_open));
    g_export_open.sql = request->query;
    g_export_open.sql_length = request->query_length;
    rc = rsql_query_open(&g_export_open);
    if (rc != RSQL_OK) return rc;
    cursor_open = 1u;

    if (cbm_open(request->logical_file, request->device, CBM_WRITE,
                 request->filename) != 0u) {
        rc = RSQL_ERR_IO;
        goto done;
    }
    file_open = 1u;
    rc = write_bytes(request, header, sizeof(header));
    if (rc != RSQL_OK) goto done;
    rc = write_bytes(request, &g_export_open.column_count, 1u);
    if (rc != RSQL_OK) goto done;

    g_export_next.cursor = g_export_open.cursor;
    for (;;) {
        rc = rsql_cursor_next(&g_export_next);
        if (rc != RSQL_OK || !g_export_next.has_row) break;
        marker = 0x52u;
        rc = write_bytes(request, &marker, 1u);
        if (rc != RSQL_OK) break;
        for (column = 0u; column < g_export_open.column_count; ++column) {
            rc = write_field(request, column);
            if (rc != RSQL_OK) break;
        }
        if (rc != RSQL_OK) break;
        increment32(&request->rows_written);
    }
    if (rc == RSQL_OK) {
        marker = 0xFFu;
        rc = write_bytes(request, &marker, 1u);
        if (rc == RSQL_OK) {
            rc = write_bytes(request, request->rows_written.bytes, 4u);
        }
    }

done:
    if (file_open) cbm_close(request->logical_file);
    if (cursor_open) {
        g_export_close.cursor = g_export_open.cursor;
        close_rc = rsql_query_close(&g_export_close);
        if (rc == RSQL_OK) rc = close_rc;
    }
    return rc;
}

#ifndef RSQL_H
#define RSQL_H

#include "rsql_errors.h"
#include "rsql_inspect.h"
#include "rsql_reu.h"
#include "rsql_types.h"

#define RSQL_ABI_MAJOR 0u
#define RSQL_ABI_MINOR 6u

typedef struct RsqlInitRequest {
    rsql_u8 abi_major;
    rsql_u8 abi_minor;
    RsqlReuConfig reu;
    rsql_u8 format_if_missing;
    /* Bit per 16KB cache slot. Host harnesses preload directly; zero asks the
     * standalone target to load all seven sidecars from device 8. */
    rsql_u8 preloaded_overlay_mask;
} RsqlInitRequest;

typedef struct RsqlInspectOutput {
    void* records;
    rsql_u16 capacity;
    rsql_u16 start;
    rsql_u16 returned;
} RsqlInspectOutput;

typedef union RsqlExecOutput {
    RsqlI64 affected_rows;
    RsqlInspectOutput inspect;
} RsqlExecOutput;

typedef struct RsqlExecRequest {
    const char* sql;
    rsql_u16 sql_length;
    /* Mutations report affected_rows. SHOW statements instead use inspect;
     * the union preserves the original compact request size on the C64. */
    RsqlExecOutput output;
} RsqlExecRequest;

typedef struct RsqlErrorInfo {
    rsql_u8 code;
    rsql_u16 byte_offset;
    const char* message;
} RsqlErrorInfo;

typedef rsql_u8 RsqlCursorHandle;

typedef struct RsqlQueryOpenRequest {
    const char* sql;
    rsql_u16 sql_length;
    RsqlCursorHandle cursor;
    rsql_u8 column_count;
} RsqlQueryOpenRequest;

typedef struct RsqlCursorNextRequest {
    RsqlCursorHandle cursor;
    rsql_u8 has_row;
} RsqlCursorNextRequest;

typedef struct RsqlValueInfo {
    RsqlTypeSpec type;
    rsql_u8 is_null;
    rsql_u16 length;
    rsql_u8 bytes[8];
} RsqlValueInfo;

typedef struct RsqlCursorColumnRequest {
    RsqlCursorHandle cursor;
    rsql_u8 column;
    RsqlValueInfo value;
} RsqlCursorColumnRequest;

typedef struct RsqlValueReadRequest {
    RsqlCursorHandle cursor;
    rsql_u8 column;
    rsql_u16 offset;
    void* destination;
    rsql_u16 capacity;
    rsql_u16 bytes_read;
} RsqlValueReadRequest;

typedef struct RsqlQueryCloseRequest {
    RsqlCursorHandle cursor;
} RsqlQueryCloseRequest;

rsql_u16 rsql_api_version(void);
rsql_u8 __fastcall__ rsql_init(RsqlInitRequest* request);
rsql_u8 rsql_shutdown(void);
rsql_u8 __fastcall__ rsql_exec(RsqlExecRequest* request);
rsql_u8 __fastcall__ rsql_query_open(RsqlQueryOpenRequest* request);
rsql_u8 __fastcall__ rsql_cursor_next(RsqlCursorNextRequest* request);
rsql_u8 __fastcall__ rsql_cursor_column(RsqlCursorColumnRequest* request);
rsql_u8 __fastcall__ rsql_value_read(RsqlValueReadRequest* request);
rsql_u8 __fastcall__ rsql_query_close(RsqlQueryCloseRequest* request);
/* Quiesce durable state before an external adapter captures the whole REU. */
rsql_u8 rsql_checkpoint(void);
/* Reopen a whole REU image already restored by the host/device adapter.
 * Callers must set format_if_missing to zero. */
rsql_u8 __fastcall__ rsql_restore(RsqlInitRequest* request);
const RsqlErrorInfo* rsql_last_error(void);

#endif

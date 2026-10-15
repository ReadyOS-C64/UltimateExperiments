#ifndef RSQL_BLOB_H
#define RSQL_BLOB_H

#include "rsql_types.h"

#define RSQL_BLOB_KIND_TEXT RSQL_TYPE_TEXT
#define RSQL_BLOB_KIND_BINARY RSQL_TYPE_BLOB

typedef struct RsqlBlobHandle {
    rsql_u8 bytes[4];
} RsqlBlobHandle;

typedef struct RsqlBlobInfo {
    RsqlBlobHandle handle;
    unsigned long length;
    rsql_u8 kind;
    /* Internal page identity also lets a phase stream into a newly allocated
     * blank chain without sharing the source value's handle. */
    rsql_u16 first_page;
} RsqlBlobInfo;

typedef struct RsqlBlobWriteCursor {
    rsql_u16 page;
    rsql_u16 page_offset;
    rsql_u16 expected_length;
    rsql_u16 written;
} RsqlBlobWriteCursor;

rsql_u8 rsql_blob_create(rsql_u8 kind, const void* source, rsql_u16 length,
                         RsqlBlobHandle* handle_out);
rsql_u8 rsql_blob_info(const RsqlBlobHandle* handle, RsqlBlobInfo* info_out);
rsql_u8 rsql_blob_read(const RsqlBlobHandle* handle, unsigned long offset,
                       void* destination, rsql_u16 capacity,
                       rsql_u16* bytes_read_out);
rsql_u8 rsql_blob_delete(const RsqlBlobHandle* handle);
rsql_u8 rsql_blob_compact(rsql_u16* reclaimed_pages_out);
/* CTAS-only owned growth: the zero-length handle is already stored in a
 * hidden BUILDING row before page-sized payload transactions begin. */
rsql_u8 rsql_blob_append(const RsqlBlobHandle* handle,
                         const void* source, rsql_u16 length);

#endif

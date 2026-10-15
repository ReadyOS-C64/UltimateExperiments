#ifndef RSQL_EXPORT_H
#define RSQL_EXPORT_H

#include "rsql.h"

#define RSQL_EXPORT_VERSION 1u

typedef struct RsqlD81ExportRequest {
    const char* query;
    rsql_u16 query_length;
    const char* filename;
    rsql_u8 device;
    rsql_u8 logical_file;
    RsqlI32 rows_written;
    RsqlI32 bytes_written;
} RsqlD81ExportRequest;

/* Optional client-side adapter. It streams a SELECT result into a sequential
 * file on device 8/9, normally a D81/1581. Keeping this outside the resident
 * engine preserves the complete $0801-$30FF application region. */
rsql_u8 __fastcall__ rsql_export_d81(RsqlD81ExportRequest* request);

#endif

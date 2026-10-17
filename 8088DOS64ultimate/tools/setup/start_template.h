#ifndef DOS64_START_TEMPLATE_H
#define DOS64_START_TEMPLATE_H
#include "template_limits.h"
/* UI-phase utility. Byte-reader and byte-writer use file-relative offsets.
   st_io_error is a callback-owned sticky failure flag; byte0 is valid data.
   Caller owns immutable/read-only source, fresh disposable output, and the
   fast-CRC table workspace exclusively throughout each call. Never publish
   partial output. No filesystem, browser lease, OPEN or CLOSE is done here. */
typedef unsigned char st_u8;
typedef unsigned int st_u16;
typedef unsigned long st_u32;
extern st_u8 st_descriptor[64],st_home[128],st_cancel,st_io_error;
extern st_u16 st_base;
extern st_u8 st_error,st_done;
extern st_u32 st_copied,st_template_bytes;
/* Set template_bytes from actual verified SIZE/count/EOF of the owned source;
   descriptor size is not evidence of received file length. */
/* Implement with the existing context/REU owner in SETUP. No second engine. */
st_u8 st_read(st_u32 offset);
void st_write(st_u32 offset,st_u8 value);
/* validate captures metadata/home/base privately; no output bytes on failure.
   copy_patch consumes one-shot authority before any output, checks sourceCRC
   again, and changes only owner/base/home131B. All other bytes are copied.
   error:1descriptor,2settings,3CRC/bounds,4sourceIO,5outputIO,6cancel,7authority.
   First observed error is retained. Inputs/public result cannot forge authority.
   Cancel remains set until caller starts a fresh explicit validate. */
st_u8 st_validate(void);
st_u8 st_copy_patch(void);
st_u8 st_ready(void);
#endif

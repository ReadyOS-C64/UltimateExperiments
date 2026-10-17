#ifndef DOS64_FILE_ERROR_H
#define DOS64_FILE_ERROR_H
#include "bulk_reu.h"
#ifndef DOS64_ALL_FILE_DIAGNOSTICS
#define DOS64_ALL_FILE_DIAGNOSTICS 0
#endif
#if DOS64_ALL_FILE_DIAGNOSTICS
/* Presentation only. Existing request home is retired on first fatal cause;
 * private operation snapshots/ownership never consult this borrowed copy. */
extern br_u8 fd_code,fd_op,fd_leaf,fd_transport,fd_closed,fd_origin;
extern char fd_path[128];
#pragma zpsym ("fd_origin")
extern br_u16 fd_tail;
void __fastcall__ fd_set_path(const char* path);
#define FD_CAPTURE(path,code,operation,leaf,transport) do { if(!fd_code){fd_set_path(path);fd_op=(operation);fd_leaf=(leaf);fd_transport=(transport);fd_code=(code);} } while(0)
#endif
#endif

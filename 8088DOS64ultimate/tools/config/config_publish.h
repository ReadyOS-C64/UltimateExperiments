#ifndef DOS64_CONFIG_PUBLISH_H
#define DOS64_CONFIG_PUBLISH_H
#include "bulk_reu.h"
#define CP_IDLE 0u
#define CP_BUSY 1u
#define CP_DONE 2u
#define CP_FAILED 3u
#define CP_INPUT 1u
#define CP_OWNER 2u
#define CP_FILE 3u
#define CP_SIZE 4u
#define CP_DMA 5u
#define CP_COMPARE 6u
#define CP_CANCEL 7u
#define CP_CLOCK 8u
#define CP_TIMEOUT 9u
#define CP_LIMIT 10u
#define CP_ASSET 11u
#define CP_CONFIG 12u
struct cp_request_t {br_u8 owner;br_u16 timeout;};
struct cp_result_t {br_u8 state,error,stage,file,leaf,transport,cleanup,mask;br_u32 identity;};
extern struct cp_request_t cp_request;
extern struct cp_result_t cp_result; /* observation only */
/* Standalone CONFIG, no running guest. Same BC engine, private CG+RI+RM
 * remain live throughout. Release-bound assets from selected source directory;
 * outputs CREATE_NEW only in distinct selected generation directory, CFG last.
 * Partial outputs retained on failure. Filesystem/mount aliases are caller
 * exclusion; receipts are not external file locks. */
br_u8 cp_begin(void);void cp_poll(void),cp_cancel(void);
br_u8 cp_state(void),cp_error(void),cp_closed_quiet(void),cp_get(void);
#endif

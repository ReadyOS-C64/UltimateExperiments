#ifndef DOS64_INI_IO_H
#define DOS64_INI_IO_H
#include "bulk_reu.h"
/* Prelaunch code only. The resident loader must first verify/install the bound
 * overlay. Caller exclusively suspends its closed/quiet single-context engine,
 * keeps br_config fixed, and supplies a canonical owned path. No raw UI lease.
 * Observation globals cannot authorize this private one-shot workflow. */
extern br_u16 ii_now;
extern br_u8 ii_error_observed,ii_parser_observed;
extern br_u16 ii_line_observed;
br_u8 ii_begin(const char *path);
void ii_poll(void),ii_cancel(void),ii_clock_fail(void);
br_u8 ii_state(void),ii_columns(void),ii_error(void),ii_cleanup(void);
/* Last clock/key/quiet fence, one-shot; returns private40/80 or0. */
br_u8 ii_commit(void);
br_u8 ii_failed_op(void),ii_leaf_error(void),ii_transport(void);
#endif

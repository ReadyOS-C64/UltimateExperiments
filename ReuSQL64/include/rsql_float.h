#ifndef RSQL_FLOAT_H
#define RSQL_FLOAT_H

#include "rsql_catalog.h"
#include "rsql_query.h"

#define RSQL_FLOAT5_BYTES 5u

/* BASIC-ROM bridge storage lives in the ABI page so it remains visible while
 * the ROM is banked over the active $7C00-$BFFF sidecar. */
extern rsql_u8 rsql_float_text[RSQL_VALUE_STRING_MAX + 1u];
extern rsql_u8 rsql_float_a[RSQL_FLOAT5_BYTES];
extern rsql_u8 rsql_float_b[RSQL_FLOAT5_BYTES];
extern rsql_u8 rsql_float_out[RSQL_FLOAT5_BYTES];
extern rsql_u8* rsql_float_destination;
extern rsql_u8 rsql_float_negative;

void rsql_float_eval_abi(void);
void rsql_float_add_abi(void);
void rsql_float_div_abi(void);

rsql_u8 rsql_query_resolve_float_value(const RsqlColumnInfo* column,
                                       RsqlParsedValue* value);

#endif

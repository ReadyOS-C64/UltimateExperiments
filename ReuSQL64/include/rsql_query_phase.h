#ifndef RSQL_QUERY_PHASE_H
#define RSQL_QUERY_PHASE_H

#include "rsql_types.h"

struct RsqlExecRequest;

/* Private continuation returned from a sidecar to resident orchestration. */
#define RSQL_QUERY_PHASE_VARIABLE 254u
#define RSQL_QUERY_PHASE_INDEX_SKIP 253u
#define RSQL_QUERY_PHASE_SCALAR 252u
#define RSQL_QUERY_PHASE_PREDICATE 251u

rsql_u8 rsql_query_parse_phase_id(void);
rsql_u8 rsql_query_exec_phase_id(void);
rsql_u8 __fastcall__ rsql_inspect_phase(struct RsqlExecRequest* request);

#endif

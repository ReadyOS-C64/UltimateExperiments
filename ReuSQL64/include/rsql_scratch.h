#ifndef RSQL_SCRATCH_H
#define RSQL_SCRATCH_H

#include "rsql_reu.h"
#include "rsql_types.h"

/* Metadata services are mutually sequenced. Blob compaction runs in the
 * maintenance phase and is the only path that needs both images concurrently,
 * so catalog/blob/enum/maintenance share this resident two-page work set. */
extern rsql_u8 g_rsql_meta_page0[RSQL_REU_PAGE_SIZE];
extern rsql_u8 g_rsql_meta_page1[RSQL_REU_PAGE_SIZE];

#endif

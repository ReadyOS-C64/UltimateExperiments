#ifndef RSQL_OVERLAY_H
#define RSQL_OVERLAY_H

#include "rsql_types.h"

#define RSQL_OVERLAY_COUNT 8u
#define RSQL_OVERLAY_VALID_MASK 0xFFu
#define RSQL_OVERLAY_WINDOW ((void*)0x7C00)
#define RSQL_OVERLAY_SIZE 0x4400u
#define RSQL_OVERLAY_SLOT_PAGES 68ul

rsql_u8 rsql_overlay_init(void);
rsql_u8 rsql_overlay_mark_valid(rsql_u8 mask);
rsql_u8 rsql_overlay_bootstrap_disk(void);
rsql_u8 rsql_overlay_store(rsql_u8 slot);
rsql_u8 rsql_overlay_load(rsql_u8 slot);
rsql_u8 rsql_overlay_load_admin(void);
rsql_u8 rsql_overlay_is_valid(rsql_u8 slot);
unsigned long rsql_overlay_reu_address(rsql_u8 slot);

#endif

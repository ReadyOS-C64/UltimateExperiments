#include <cbm.h>
#include <errno.h>

#include "rsql_errors.h"
#include "rsql_overlay.h"
#include "rsql_reu.h"

#define CPU_PORT (*(volatile rsql_u8*)0x0001)
#define CPU_PORT_BASIC_VISIBLE 0x01u

static rsql_u8 g_overlay_valid_mask;
/* Bootstrap-only names live with initialized work data.  Keeping this table
 * in the resident code bank would spend scarce always-executable bytes on
 * strings that are never consulted after the overlay cache is populated. */
static char OVL_META_FILE[] = "0:rsqlmeta,p";
static char OVL_ROW_FILE[] = "0:rsqlrow,p";
static char OVL_PARSE_FILE[] = "0:rsqlparse,p";
static char OVL_EXEC_FILE[] = "0:rsqlexec,p";
static char OVL_QUERY_FILE[] = "0:rsqlsubq,p";
static char OVL_SORT_FILE[] = "0:rsqlsort,p";
static char OVL_JOIN_AGG_FILE[] = "0:rsqljagg,p";
static char OVL_ADMIN_FILE[] = "0:rsqladmin,p";
static char OVL_WIDE_FILE[] = "0:rsqlwide,p";
static const char* OVL_FILES[RSQL_OVERLAY_COUNT] = {
    OVL_META_FILE, OVL_ROW_FILE, OVL_PARSE_FILE, OVL_EXEC_FILE,
    OVL_QUERY_FILE, OVL_SORT_FILE, OVL_JOIN_AGG_FILE, OVL_WIDE_FILE
};

#define OVL_DIAG_SLOT   (*(volatile rsql_u8*)0xCFF3)
#define OVL_DIAG_LOW    (*(volatile rsql_u8*)0xCFF4)
#define OVL_DIAG_HIGH   (*(volatile rsql_u8*)0xCFF5)
#define OVL_DIAG_OSERR  (*(volatile rsql_u8*)0xCFF6)

unsigned long rsql_overlay_reu_address(rsql_u8 slot) {
    unsigned long top_page;
    if (slot >= RSQL_OVERLAY_COUNT) return 0ul;
    top_page = rsql_reu_page_count() - RSQL_REU_OVERLAY_PAGES;
    return (top_page + ((unsigned long)slot * RSQL_OVERLAY_SLOT_PAGES)) << 8u;
}

rsql_u8 rsql_overlay_init(void) {
    if (rsql_reu_page_count() < 2048ul) return RSQL_ERR_REU_TOO_SMALL;
    g_overlay_valid_mask = 0u;
    return RSQL_OK;
}

rsql_u8 rsql_overlay_mark_valid(rsql_u8 mask) {
    if (mask != RSQL_OVERLAY_VALID_MASK) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    g_overlay_valid_mask = RSQL_OVERLAY_VALID_MASK;
    return RSQL_OK;
}

rsql_u8 rsql_overlay_bootstrap_disk(void) {
    rsql_u16 loaded;
    rsql_u8 slot;
    rsql_u8 rc;
    cbm_k_clrch();
    cbm_k_clall();
    for (slot = 0u; slot < RSQL_OVERLAY_COUNT; ++slot) {
        OVL_DIAG_SLOT = slot;
        loaded = cbm_load(OVL_FILES[slot], 8u, 0);
        OVL_DIAG_LOW = (rsql_u8)loaded;
        OVL_DIAG_HIGH = (rsql_u8)(loaded >> 8u);
        OVL_DIAG_OSERR = _oserror;
        cbm_k_clrch();
        cbm_k_clall();
        /* cc65 documents a byte count, while the C64 KERNAL-backed path
         * returns the exclusive end address when data is null.  Accept both
         * representations, but still reject a short or failed sidecar. */
        if (loaded != RSQL_OVERLAY_SIZE && loaded != 0xC000u) {
            return RSQL_ERR_IO;
        }
        rc = rsql_overlay_store(slot);
        if (rc != RSQL_OK) return rc;
    }
    OVL_DIAG_SLOT = 8u;
    loaded = cbm_load(OVL_ADMIN_FILE, 8u, 0);
    OVL_DIAG_LOW = (rsql_u8)loaded;
    OVL_DIAG_HIGH = (rsql_u8)(loaded >> 8u);
    OVL_DIAG_OSERR = _oserror;
    cbm_k_clrch();
    cbm_k_clall();
    if (loaded != RSQL_OVERLAY_SIZE && loaded != 0xC000u) {
        return RSQL_ERR_IO;
    }
    rc = rsql_reu_write(
        rsql_reu_page_address(RSQL_REU_ADMIN_CACHE_PAGE),
        RSQL_OVERLAY_WINDOW, RSQL_OVERLAY_SIZE);
    return rc;
}

rsql_u8 rsql_overlay_store(rsql_u8 slot) {
    rsql_u8 old_port;
    rsql_u8 rc;
    if (slot >= RSQL_OVERLAY_COUNT) return RSQL_ERR_INVALID_ARGUMENT;
    old_port = CPU_PORT;
    CPU_PORT = (rsql_u8)(old_port & (rsql_u8)~CPU_PORT_BASIC_VISIBLE);
    rc = rsql_reu_write(rsql_overlay_reu_address(slot), RSQL_OVERLAY_WINDOW,
                        RSQL_OVERLAY_SIZE);
    CPU_PORT = old_port;
    if (rc == RSQL_OK) g_overlay_valid_mask |= (rsql_u8)(1u << slot);
    return rc;
}

rsql_u8 rsql_overlay_load(rsql_u8 slot) {
    rsql_u8 old_port;
    rsql_u8 rc;
    if (slot >= RSQL_OVERLAY_COUNT) return RSQL_ERR_INVALID_ARGUMENT;
    if (!rsql_overlay_is_valid(slot)) return RSQL_ERR_CORRUPT_STORAGE;
    old_port = CPU_PORT;
    CPU_PORT = (rsql_u8)(old_port & (rsql_u8)~CPU_PORT_BASIC_VISIBLE);
    rc = rsql_reu_read(rsql_overlay_reu_address(slot), RSQL_OVERLAY_WINDOW,
                       RSQL_OVERLAY_SIZE);
    CPU_PORT = old_port;
    return rc;
}

rsql_u8 rsql_overlay_is_valid(rsql_u8 slot) {
    if (slot >= RSQL_OVERLAY_COUNT) return 0u;
    return (g_overlay_valid_mask & (rsql_u8)(1u << slot)) ? 1u : 0u;
}

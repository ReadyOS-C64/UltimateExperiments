#include <string.h>

#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"

#define RSQL_FORMAT_VERSION 2u
#define RSQL_BITMAP_ADDRESS_PAGE 2u
#define RSQL_BITMAP_BYTES 8192u

typedef struct RsqlSuperblock {
    rsql_u8 magic[4];
    rsql_u8 version;
    rsql_u8 flags;
    rsql_u16 size_kib;
    rsql_u8 page_count_lo;
    rsql_u8 page_count_mid;
    rsql_u8 page_count_hi;
    rsql_u8 generation;
    rsql_u8 checksum;
    rsql_u16 catalog_root;
    rsql_u8 reserved[241];
} RsqlSuperblock;

#define g_page_buffer g_rsql_meta_page0
static unsigned long g_page_limit;
static rsql_u16 g_catalog_root = RSQL_PAGE_NONE;
static rsql_u8 g_super_generation;

static rsql_u8 super_checksum(const RsqlSuperblock* block) {
    const rsql_u8* bytes;
    rsql_u8 value;
    rsql_u16 i;
    bytes = (const rsql_u8*)block;
    value = 0xA5u;
    for (i = 0u; i < (rsql_u16)sizeof(*block); ++i) {
        if (i != 12u) {
            value ^= bytes[i];
        }
    }
    return value;
}

static rsql_u8 super_valid(const RsqlSuperblock* block) {
    return block->magic[0] == 'R' && block->magic[1] == 'S' &&
           block->magic[2] == 'Q' && block->magic[3] == 'L' &&
           block->version == RSQL_FORMAT_VERSION &&
           block->size_kib == rsql_reu_size_kib() &&
           block->checksum == super_checksum(block);
}

static void prepare_super(rsql_u16 catalog_root, rsql_u8 generation) {
    RsqlSuperblock* super;
    unsigned long total_pages = rsql_reu_page_count();
    memset(g_page_buffer, 0, sizeof(g_rsql_meta_page0));
    super = (RsqlSuperblock*)g_page_buffer;
    super->magic[0] = 'R';
    super->magic[1] = 'S';
    super->magic[2] = 'Q';
    super->magic[3] = 'L';
    super->version = RSQL_FORMAT_VERSION;
    super->size_kib = rsql_reu_size_kib();
    super->page_count_lo = (rsql_u8)(total_pages & 0xFFul);
    super->page_count_mid = (rsql_u8)((total_pages >> 8u) & 0xFFul);
    super->page_count_hi = (rsql_u8)((total_pages >> 16u) & 0x01ul);
    super->generation = generation;
    super->catalog_root = catalog_root;
    super->checksum = super_checksum(super);
}

static unsigned long bitmap_byte_address(rsql_u16 page) {
    return rsql_reu_page_address(RSQL_BITMAP_ADDRESS_PAGE) +
           (unsigned long)(page >> 3u);
}

static rsql_u8 bitmap_set(rsql_u16 page, rsql_u8 allocated) {
    unsigned long address;
    rsql_u8 value;
    rsql_u8 mask;
    rsql_u8 rc;
    address = bitmap_byte_address(page);
    rc = rsql_reu_read_byte(address, &value);
    if (rc != RSQL_OK) return rc;
    mask = (rsql_u8)(1u << (page & 7u));
    value = allocated ? (rsql_u8)(value | mask)
                      : (rsql_u8)(value & (rsql_u8)~mask);
    return rsql_reu_write_byte(address, value);
}

rsql_u8 rsql_page_is_allocated(rsql_u16 page, rsql_u8* allocated_out) {
    unsigned long address;
    rsql_u8 value;
    rsql_u8 rc;
    if (!allocated_out || (unsigned long)page >= rsql_reu_page_count()) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    address = bitmap_byte_address(page);
    rc = rsql_reu_read_byte(address, &value);
    if (rc != RSQL_OK) return rc;
    *allocated_out = (value & (rsql_u8)(1u << (page & 7u))) ? 1u : 0u;
    return RSQL_OK;
}

rsql_u8 rsql_page_format(void) {
    RsqlSuperblock* super;
    unsigned long address;
    unsigned long total_pages;
    unsigned long overlay_start;
    rsql_u16 i;
    rsql_u8 rc;

    total_pages = rsql_reu_page_count();
    if (total_pages < 2048ul) return RSQL_ERR_REU_TOO_SMALL;
    overlay_start = total_pages - RSQL_REU_OVERLAY_PAGES;

    memset(g_page_buffer, 0, sizeof(g_page_buffer));
    for (i = 0u; i < 32u; ++i) {
        address = rsql_reu_page_address((rsql_u16)(RSQL_BITMAP_ADDRESS_PAGE + i));
        rc = rsql_reu_write(address, g_page_buffer, sizeof(g_page_buffer));
        if (rc != RSQL_OK) return rc;
    }

    for (i = 0u; i < RSQL_REU_SYSTEM_PAGES; ++i) {
        rc = bitmap_set(i, 1u);
        if (rc != RSQL_OK) return rc;
    }
    for (i = (rsql_u16)overlay_start; (unsigned long)i < total_pages; ++i) {
        rc = bitmap_set(i, 1u);
        if (rc != RSQL_OK) return rc;
        if (i == 0xFFFFu) break;
    }

    prepare_super(RSQL_PAGE_NONE, 1u);
    super = (RsqlSuperblock*)g_page_buffer;
    rc = rsql_reu_write(rsql_reu_page_address(0u), super, sizeof(*super));
    if (rc != RSQL_OK) return rc;
    rc = rsql_reu_write(rsql_reu_page_address(1u), super, sizeof(*super));
    if (rc == RSQL_OK) {
        g_super_generation = 1u;
        g_catalog_root = RSQL_PAGE_NONE;
    }
    return rc;
}

rsql_u8 rsql_page_allocator_open(void) {
    RsqlSuperblock* super;
    rsql_u8 have_super;
    rsql_u8 rc;
    unsigned long total_pages;
    have_super = 0u;
    rc = rsql_reu_read(rsql_reu_page_address(0u), g_page_buffer,
                       sizeof(RsqlSuperblock));
    if (rc != RSQL_OK) return rc;
    super = (RsqlSuperblock*)g_page_buffer;
    if (super_valid(super)) {
        g_super_generation = super->generation;
        g_catalog_root = super->catalog_root;
        have_super = 1u;
    }
    rc = rsql_reu_read(rsql_reu_page_address(1u), g_page_buffer,
                       sizeof(RsqlSuperblock));
    if (rc != RSQL_OK) return rc;
    super = (RsqlSuperblock*)g_page_buffer;
    if (super_valid(super) &&
        (!have_super ||
         (rsql_i8)(super->generation - g_super_generation) > 0)) {
        g_super_generation = super->generation;
        g_catalog_root = super->catalog_root;
        have_super = 1u;
    }
    if (!have_super) return RSQL_ERR_CORRUPT_STORAGE;
    total_pages = rsql_reu_page_count();
    g_page_limit = total_pages - RSQL_REU_OVERLAY_PAGES -
                   RSQL_REU_JOURNAL_PAGES;
    return RSQL_OK;
}

rsql_u8 rsql_page_allocate(rsql_u16* page_out) {
    unsigned long page;
    rsql_u8 allocated;
    rsql_u8 rc;
    if (!page_out) return RSQL_ERR_INVALID_ARGUMENT;
    for (page = RSQL_REU_SYSTEM_PAGES; page < g_page_limit; ++page) {
        rc = rsql_page_is_allocated((rsql_u16)page, &allocated);
        if (rc != RSQL_OK) return rc;
        if (!allocated) {
            rc = bitmap_set((rsql_u16)page, 1u);
            if (rc != RSQL_OK) return rc;
            *page_out = (rsql_u16)page;
            return RSQL_OK;
        }
    }
    return RSQL_ERR_OUT_OF_REU_PAGES;
}

rsql_u8 rsql_page_free(rsql_u16 page) {
    if (page < RSQL_REU_SYSTEM_PAGES || (unsigned long)page >= g_page_limit) {
        return RSQL_ERR_PAGE_RESERVED;
    }
    return bitmap_set(page, 0u);
}

rsql_u16 rsql_page_first_usable(void) {
    return RSQL_REU_SYSTEM_PAGES;
}

unsigned long rsql_page_limit(void) {
    return g_page_limit;
}

rsql_u16 rsql_page_catalog_root(void) {
    return g_catalog_root;
}

rsql_u8 rsql_page_set_catalog_root(rsql_u16 page) {
    RsqlSuperblock* super;
    rsql_u8 rc;
    if (page < RSQL_REU_SYSTEM_PAGES || (unsigned long)page >= g_page_limit) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    prepare_super(page, (rsql_u8)(g_super_generation + 1u));
    super = (RsqlSuperblock*)g_page_buffer;
    /* Secondary first: either the old primary or new secondary remains valid
     * if execution is interrupted between these writes. */
    rc = rsql_reu_write(rsql_reu_page_address(1u), super, sizeof(*super));
    if (rc != RSQL_OK) return rc;
    rc = rsql_reu_write(rsql_reu_page_address(0u), super, sizeof(*super));
    if (rc == RSQL_OK) {
        g_catalog_root = page;
        g_super_generation = super->generation;
    }
    return rc;
}

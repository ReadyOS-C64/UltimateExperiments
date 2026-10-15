#include <string.h>

#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define BLOB_DIRECTORY_NEXT 6u
#define BLOB_DIRECTORY_ENTRIES 8u
#define BLOB_DIRECTORY_ENTRY_BYTES 20u
#define BLOB_DIRECTORY_ENTRY_COUNT 12u

#define BLOB_ENTRY_STATE 0u
#define BLOB_ENTRY_FIRST_PAGE 6u
#define BLOB_STATE_DELETED 2u

#define BLOB_PAGE_CHECKSUM 5u
#define BLOB_PAGE_NEXT 6u
#define BLOB_PAGE_USED 8u
#define BLOB_PAGE_DATA 10u
#define BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - BLOB_PAGE_DATA)

#define g_compact_directory g_rsql_meta_page0
#define g_compact_data g_rsql_meta_page1

static rsql_u8 compact_blob_checksum(const rsql_u8* page) {
    rsql_u8 value = 0xB7u;
    rsql_u16 index;
    for (index = 0u; index < RSQL_REU_PAGE_SIZE; ++index) {
        if (index != BLOB_PAGE_CHECKSUM) value ^= page[index];
    }
    return value;
}

static rsql_u8 compact_load_directory(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
                               g_compact_directory,
                               sizeof(g_rsql_meta_page0));
    if (rc != RSQL_OK) return rc;
    if (g_compact_directory[0] != 'R' ||
        g_compact_directory[1] != 'B' ||
        g_compact_directory[2] != 'D' ||
        g_compact_directory[3] != 'R' ||
        g_compact_directory[4] != RSQL_STORAGE_VERSION ||
        g_compact_directory[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_compact_directory)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 compact_store_directory(rsql_u16 page) {
    g_compact_directory[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(g_compact_directory);
    return rsql_reu_write(rsql_reu_page_address(page),
                          g_compact_directory,
                          sizeof(g_rsql_meta_page0));
}

static rsql_u8 compact_load_blob_page(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_compact_data,
                               sizeof(g_rsql_meta_page1));
    if (rc != RSQL_OK) return rc;
    if (g_compact_data[0] != 'R' || g_compact_data[1] != 'B' ||
        g_compact_data[2] != 'L' || g_compact_data[3] != 'B' ||
        g_compact_data[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_compact_data[BLOB_PAGE_USED]) > BLOB_PAGE_PAYLOAD ||
        g_compact_data[BLOB_PAGE_CHECKSUM] !=
            compact_blob_checksum(g_compact_data)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 compact_free_chain(rsql_u16 first, rsql_u16* count_out) {
    rsql_u16 page = first;
    rsql_u16 next;
    rsql_u16 count = 0u;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = compact_load_blob_page(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&g_compact_data[BLOB_PAGE_NEXT]);
        rc = rsql_page_free(page);
        if (rc != RSQL_OK) return rc;
        ++count;
        page = next;
    }
    *count_out = count;
    return RSQL_OK;
}

static rsql_u8 compact_first_directory(rsql_u16* page_out) {
    rsql_u16 root = rsql_page_catalog_root();
    rsql_u8 rc;
    if (root == RSQL_PAGE_NONE) return RSQL_ERR_CORRUPT_STORAGE;
    rc = rsql_reu_read(rsql_reu_page_address(root), g_compact_directory,
                       sizeof(g_rsql_meta_page0));
    if (rc != RSQL_OK) return rc;
    if (g_compact_directory[0] != 'R' ||
        g_compact_directory[1] != 'C' ||
        g_compact_directory[2] != 'A' ||
        g_compact_directory[3] != 'T' ||
        g_compact_directory[4] != RSQL_STORAGE_VERSION ||
        g_compact_directory[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_compact_directory)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    *page_out = rsql_get_u16(
        &g_compact_directory[RSQL_ROOT_FIRST_BLOB_DIRECTORY]);
    return RSQL_OK;
}

rsql_u8 __fastcall__ rsql_blob_compact_phase(
    rsql_u16* reclaimed_pages_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 first;
    rsql_u16 reclaimed;
    rsql_u16 total = 0u;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 changed;
    rsql_u8 rc;
    if (!reclaimed_pages_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = compact_first_directory(&page);
    if (rc != RSQL_OK) return rc;
    while (page != RSQL_PAGE_NONE) {
        rc = compact_load_directory(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&g_compact_directory[BLOB_DIRECTORY_NEXT]);
        changed = 0u;
        for (slot = 0u; slot < BLOB_DIRECTORY_ENTRY_COUNT; ++slot) {
            base = (rsql_u16)(BLOB_DIRECTORY_ENTRIES +
                (rsql_u16)slot * BLOB_DIRECTORY_ENTRY_BYTES);
            if (g_compact_directory[base + BLOB_ENTRY_STATE] ==
                    BLOB_STATE_DELETED) {
                first = rsql_get_u16(
                    &g_compact_directory[base + BLOB_ENTRY_FIRST_PAGE]);
                rc = compact_free_chain(first, &reclaimed);
                if (rc != RSQL_OK) return rc;
                total = (rsql_u16)(total + reclaimed);
                memset(&g_compact_directory[base], 0,
                       BLOB_DIRECTORY_ENTRY_BYTES);
                changed = 1u;
            }
        }
        if (changed) {
            rc = compact_store_directory(page);
            if (rc != RSQL_OK) return rc;
        }
        page = next;
    }
    *reclaimed_pages_out = total;
    return RSQL_OK;
}

#include <string.h>

#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_journal.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define BLOB_PAGE_CHECKSUM 5u
#define BLOB_PAGE_NEXT 6u
#define BLOB_PAGE_USED 8u
#define BLOB_PAGE_DATA 10u
#define BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - BLOB_PAGE_DATA)

/* A BUILDING table owns the handle before this bounded appender runs. */
#define BLOB_DIRECTORY_NEXT 6u
#define BLOB_DIRECTORY_ENTRIES 8u
#define BLOB_DIRECTORY_ENTRY_BYTES 20u
#define BLOB_DIRECTORY_ENTRY_COUNT 12u
#define BLOB_ENTRY_STATE 0u
#define BLOB_ENTRY_HANDLE 2u
#define BLOB_ENTRY_FIRST_PAGE 6u
#define BLOB_ENTRY_LENGTH 8u
#define BLOB_STATE_ACTIVE 1u

#define g_write_directory g_rsql_meta_page0
#define g_write_page g_rsql_meta_page1

static rsql_u16 g_append_directory;
static rsql_u16 g_append_base;
static rsql_u16 g_append_tail;
static rsql_u16 g_append_new_page;
static unsigned long g_append_length;

static rsql_u8 write_checksum(const rsql_u8* page) {
    rsql_u8 value = 0xB7u;
    rsql_u16 i;
    for (i = 0u; i < RSQL_REU_PAGE_SIZE; ++i) {
        if (i != BLOB_PAGE_CHECKSUM) value ^= page[i];
    }
    return value;
}

static rsql_u8 load_write_page(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_write_page,
                               sizeof(g_write_page));
    if (rc != RSQL_OK) return rc;
    if (g_write_page[0] != 'R' || g_write_page[1] != 'B' ||
        g_write_page[2] != 'L' || g_write_page[3] != 'B' ||
        g_write_page[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_write_page[BLOB_PAGE_USED]) > BLOB_PAGE_PAYLOAD ||
        g_write_page[BLOB_PAGE_CHECKSUM] != write_checksum(g_write_page)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 load_directory(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page),
                               g_write_directory,
                               sizeof(g_write_directory));
    if (rc != RSQL_OK) return rc;
    if (g_write_directory[0] != 'R' || g_write_directory[1] != 'B' ||
        g_write_directory[2] != 'D' || g_write_directory[3] != 'R' ||
        g_write_directory[4] != RSQL_STORAGE_VERSION ||
        g_write_directory[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_write_directory)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 store_directory(void) {
    g_write_directory[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(g_write_directory);
    return rsql_reu_write(rsql_reu_page_address(g_append_directory),
                          g_write_directory, sizeof(g_write_directory));
}

static rsql_u8 same_handle(const rsql_u8* stored,
                           const RsqlBlobHandle* handle) {
    return stored[0] == handle->bytes[0] &&
           stored[1] == handle->bytes[1] &&
           stored[2] == handle->bytes[2] &&
           stored[3] == handle->bytes[3];
}

static rsql_u8 find_handle(const RsqlBlobHandle* handle) {
    rsql_u16 page;
    rsql_u8 slot;
    rsql_u8 rc = rsql_reu_read(
        rsql_reu_page_address(rsql_page_catalog_root()),
        g_write_directory, sizeof(g_write_directory));
    if (rc != RSQL_OK) return rc;
    if (g_write_directory[0] != 'R' || g_write_directory[1] != 'C' ||
        g_write_directory[2] != 'A' || g_write_directory[3] != 'T' ||
        g_write_directory[4] != RSQL_STORAGE_VERSION ||
        g_write_directory[RSQL_PAGE_CHECKSUM_OFFSET] !=
            rsql_page_checksum(g_write_directory)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    page = rsql_get_u16(&g_write_directory[
        RSQL_ROOT_FIRST_BLOB_DIRECTORY]);
    while (page != RSQL_PAGE_NONE) {
        rc = load_directory(page);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < BLOB_DIRECTORY_ENTRY_COUNT; ++slot) {
            g_append_base = (rsql_u16)(BLOB_DIRECTORY_ENTRIES +
                (rsql_u16)slot * BLOB_DIRECTORY_ENTRY_BYTES);
            if (g_write_directory[g_append_base + BLOB_ENTRY_STATE] ==
                    BLOB_STATE_ACTIVE &&
                same_handle(&g_write_directory[g_append_base +
                    BLOB_ENTRY_HANDLE], handle)) {
                g_append_directory = page;
                g_append_length = rsql_get_u32(&g_write_directory[
                    g_append_base + BLOB_ENTRY_LENGTH]);
                g_append_tail = rsql_get_u16(&g_write_directory[
                    g_append_base + BLOB_ENTRY_FIRST_PAGE]);
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_write_directory[BLOB_DIRECTORY_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_blob_append(const RsqlBlobHandle* handle,
                         const void* source, rsql_u16 length) {
    rsql_u16 next;
    rsql_u8 rc;
    if (!handle || !source || length == 0u || length > BLOB_PAGE_PAYLOAD) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = find_handle(handle);
    if (rc != RSQL_OK) return rc;
    if (g_append_tail != RSQL_PAGE_NONE) {
        for (;;) {
            rc = load_write_page(g_append_tail);
            if (rc != RSQL_OK) return rc;
            next = rsql_get_u16(&g_write_page[BLOB_PAGE_NEXT]);
            if (next == RSQL_PAGE_NONE) break;
            g_append_tail = next;
        }
    }
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rc = rsql_page_allocate(&g_append_new_page);
    if (rc == RSQL_OK) {
        memset(g_write_page, 0, sizeof(g_write_page));
        g_write_page[0] = 'R';
        g_write_page[1] = 'B';
        g_write_page[2] = 'L';
        g_write_page[3] = 'B';
        g_write_page[4] = RSQL_STORAGE_VERSION;
        rsql_put_u16(&g_write_page[BLOB_PAGE_NEXT], RSQL_PAGE_NONE);
        rsql_put_u16(&g_write_page[BLOB_PAGE_USED], length);
        memcpy(&g_write_page[BLOB_PAGE_DATA], source, length);
        g_write_page[BLOB_PAGE_CHECKSUM] = write_checksum(g_write_page);
        rc = rsql_reu_write(rsql_reu_page_address(g_append_new_page),
                            g_write_page, sizeof(g_write_page));
    }
    if (rc == RSQL_OK && g_append_tail != RSQL_PAGE_NONE) {
        rc = load_write_page(g_append_tail);
        if (rc == RSQL_OK) {
            rsql_put_u16(&g_write_page[BLOB_PAGE_NEXT], g_append_new_page);
            g_write_page[BLOB_PAGE_CHECKSUM] = write_checksum(g_write_page);
            rc = rsql_reu_write(rsql_reu_page_address(g_append_tail),
                                g_write_page, sizeof(g_write_page));
        }
    }
    if (rc == RSQL_OK) rc = load_directory(g_append_directory);
    if (rc == RSQL_OK && g_append_tail == RSQL_PAGE_NONE) {
        rsql_put_u16(&g_write_directory[g_append_base +
            BLOB_ENTRY_FIRST_PAGE], g_append_new_page);
    }
    if (rc == RSQL_OK) {
        rsql_put_u32(&g_write_directory[g_append_base + BLOB_ENTRY_LENGTH],
                     g_append_length + length);
        rc = store_directory();
    }
    return rsql_finish_mutation(rc);
}

#include <string.h>

#include "rsql_blob.h"
#include "rsql_catalog.h"
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
#define BLOB_ENTRY_KIND 1u
#define BLOB_ENTRY_HANDLE 2u
#define BLOB_ENTRY_FIRST_PAGE 6u
#define BLOB_ENTRY_LENGTH 8u

#define BLOB_STATE_EMPTY 0u
#define BLOB_STATE_ACTIVE 1u
#define BLOB_STATE_DELETED 2u

#define BLOB_PAGE_CHECKSUM 5u
#define BLOB_PAGE_NEXT 6u
#define BLOB_PAGE_USED 8u
#define BLOB_PAGE_DATA 10u
#define BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - BLOB_PAGE_DATA)

#define g_blob_directory g_rsql_meta_page0
#define g_blob_data g_rsql_meta_page1

static rsql_u8 blob_page_checksum(const rsql_u8* page) {
    rsql_u8 value = 0xB7u;
    rsql_u16 i;
    for (i = 0u; i < RSQL_REU_PAGE_SIZE; ++i) {
        if (i != BLOB_PAGE_CHECKSUM) value ^= page[i];
    }
    return value;
}

static rsql_u8 valid_directory(void) {
    return g_blob_directory[0] == 'R' && g_blob_directory[1] == 'B' &&
           g_blob_directory[2] == 'D' && g_blob_directory[3] == 'R' &&
           g_blob_directory[4] == RSQL_STORAGE_VERSION &&
           g_blob_directory[RSQL_PAGE_CHECKSUM_OFFSET] ==
               rsql_page_checksum(g_blob_directory);
}

static rsql_u8 valid_blob_page(void) {
    return g_blob_data[0] == 'R' && g_blob_data[1] == 'B' &&
           g_blob_data[2] == 'L' && g_blob_data[3] == 'B' &&
           g_blob_data[4] == RSQL_STORAGE_VERSION &&
           rsql_get_u16(&g_blob_data[BLOB_PAGE_USED]) <= BLOB_PAGE_PAYLOAD &&
           g_blob_data[BLOB_PAGE_CHECKSUM] == blob_page_checksum(g_blob_data);
}

static rsql_u8 load_directory(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_blob_directory,
                               sizeof(g_blob_directory));
    if (rc != RSQL_OK) return rc;
    return valid_directory() ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 store_directory(rsql_u16 page) {
    g_blob_directory[RSQL_PAGE_CHECKSUM_OFFSET] =
        rsql_page_checksum(g_blob_directory);
    return rsql_reu_write(rsql_reu_page_address(page), g_blob_directory,
                          sizeof(g_blob_directory));
}

static rsql_u8 load_blob_page(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_blob_data,
                               sizeof(g_blob_data));
    if (rc != RSQL_OK) return rc;
    return valid_blob_page() ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u16 entry_offset(rsql_u8 slot) {
    return (rsql_u16)(BLOB_DIRECTORY_ENTRIES +
                      (rsql_u16)slot * BLOB_DIRECTORY_ENTRY_BYTES);
}

static rsql_u8 handles_equal(const rsql_u8* stored,
                             const RsqlBlobHandle* handle) {
    return stored[0] == handle->bytes[0] && stored[1] == handle->bytes[1] &&
           stored[2] == handle->bytes[2] && stored[3] == handle->bytes[3];
}

static rsql_u8 find_entry(const RsqlBlobHandle* handle, rsql_u16* page_out,
                          rsql_u8* slot_out, rsql_u8 include_deleted) {
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 state;
    rsql_u8 rc;
    if (!handle || !page_out || !slot_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = rsql_catalog_blob_directory(&page);
    if (rc != RSQL_OK) return rc;
    while (page != RSQL_PAGE_NONE) {
        rc = load_directory(page);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < BLOB_DIRECTORY_ENTRY_COUNT; ++slot) {
            base = entry_offset(slot);
            state = g_blob_directory[base + BLOB_ENTRY_STATE];
            if ((state == BLOB_STATE_ACTIVE ||
                 (include_deleted && state == BLOB_STATE_DELETED)) &&
                handles_equal(&g_blob_directory[base + BLOB_ENTRY_HANDLE], handle)) {
                *page_out = page;
                *slot_out = slot;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_blob_directory[BLOB_DIRECTORY_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 new_directory(rsql_u16* page_out) {
    rsql_u16 page;
    rsql_u8 rc = rsql_page_allocate(&page);
    if (rc != RSQL_OK) return rc;
    memset(g_blob_directory, 0, sizeof(g_blob_directory));
    g_blob_directory[0] = 'R';
    g_blob_directory[1] = 'B';
    g_blob_directory[2] = 'D';
    g_blob_directory[3] = 'R';
    g_blob_directory[4] = RSQL_STORAGE_VERSION;
    rsql_put_u16(&g_blob_directory[BLOB_DIRECTORY_NEXT], RSQL_PAGE_NONE);
    rc = store_directory(page);
    if (rc != RSQL_OK) {
        rsql_page_free(page);
        return rc;
    }
    *page_out = page;
    return RSQL_OK;
}

static rsql_u8 find_empty_entry(rsql_u16* page_out, rsql_u8* slot_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 last = RSQL_PAGE_NONE;
    rsql_u16 new_page;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc = rsql_catalog_blob_directory(&page);
    if (rc != RSQL_OK) return rc;
    if (page == RSQL_PAGE_NONE) {
        rc = new_directory(&page);
        if (rc != RSQL_OK) return rc;
        rc = rsql_catalog_set_blob_directory(page);
        if (rc != RSQL_OK) {
            rsql_page_free(page);
            return rc;
        }
    }
    for (;;) {
        rc = load_directory(page);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < BLOB_DIRECTORY_ENTRY_COUNT; ++slot) {
            base = entry_offset(slot);
            if (g_blob_directory[base + BLOB_ENTRY_STATE] == BLOB_STATE_EMPTY) {
                *page_out = page;
                *slot_out = slot;
                return RSQL_OK;
            }
        }
        next = rsql_get_u16(&g_blob_directory[BLOB_DIRECTORY_NEXT]);
        if (next == RSQL_PAGE_NONE) {
            last = page;
            break;
        }
        page = next;
    }
    rc = new_directory(&new_page);
    if (rc != RSQL_OK) return rc;
    rc = load_directory(last);
    if (rc == RSQL_OK) {
        rsql_put_u16(&g_blob_directory[BLOB_DIRECTORY_NEXT], new_page);
        rc = store_directory(last);
    }
    if (rc != RSQL_OK) {
        rsql_page_free(new_page);
        return rc;
    }
    rc = load_directory(new_page);
    if (rc != RSQL_OK) return rc;
    *page_out = new_page;
    *slot_out = 0u;
    return RSQL_OK;
}

static rsql_u8 free_blob_chain(rsql_u16 first, rsql_u16* count_out) {
    rsql_u16 page = first;
    rsql_u16 next;
    rsql_u16 count = 0u;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = load_blob_page(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&g_blob_data[BLOB_PAGE_NEXT]);
        rc = rsql_page_free(page);
        if (rc != RSQL_OK) return rc;
        ++count;
        page = next;
    }
    if (count_out) *count_out = count;
    return RSQL_OK;
}

static rsql_u8 create_blob_chain(const rsql_u8* source, rsql_u16 length,
                                 rsql_u16* first_out) {
    rsql_u16 first = RSQL_PAGE_NONE;
    rsql_u16 previous = RSQL_PAGE_NONE;
    rsql_u16 page;
    rsql_u16 remaining = length;
    rsql_u16 used;
    rsql_u8 rc;
    while (remaining != 0u) {
        used = remaining > BLOB_PAGE_PAYLOAD ? BLOB_PAGE_PAYLOAD : remaining;
        rc = rsql_page_allocate(&page);
        if (rc != RSQL_OK) {
            if (first != RSQL_PAGE_NONE) free_blob_chain(first, 0);
            return rc;
        }
        memset(g_blob_data, 0, sizeof(g_blob_data));
        g_blob_data[0] = 'R';
        g_blob_data[1] = 'B';
        g_blob_data[2] = 'L';
        g_blob_data[3] = 'B';
        g_blob_data[4] = RSQL_STORAGE_VERSION;
        rsql_put_u16(&g_blob_data[BLOB_PAGE_NEXT], RSQL_PAGE_NONE);
        rsql_put_u16(&g_blob_data[BLOB_PAGE_USED], used);
        /* The whole page was cleared above, so a NULL source deliberately
         * leaves a blank chain for the streamed CTAS writer. */
        if (source) memcpy(&g_blob_data[BLOB_PAGE_DATA], source, used);
        g_blob_data[BLOB_PAGE_CHECKSUM] = blob_page_checksum(g_blob_data);
        rc = rsql_reu_write(rsql_reu_page_address(page), g_blob_data,
                            sizeof(g_blob_data));
        if (rc != RSQL_OK) {
            rsql_page_free(page);
            if (first != RSQL_PAGE_NONE) free_blob_chain(first, 0);
            return rc;
        }
        if (first == RSQL_PAGE_NONE) first = page;
        if (previous != RSQL_PAGE_NONE) {
            rc = load_blob_page(previous);
            if (rc != RSQL_OK) return rc;
            rsql_put_u16(&g_blob_data[BLOB_PAGE_NEXT], page);
            g_blob_data[BLOB_PAGE_CHECKSUM] = blob_page_checksum(g_blob_data);
            rc = rsql_reu_write(rsql_reu_page_address(previous), g_blob_data,
                                sizeof(g_blob_data));
            if (rc != RSQL_OK) return rc;
        }
        previous = page;
        if (source) source += used;
        remaining = (rsql_u16)(remaining - used);
    }
    *first_out = first;
    return RSQL_OK;
}

rsql_u8 rsql_blob_create(rsql_u8 kind, const void* source, rsql_u16 length,
                         RsqlBlobHandle* handle_out) {
    unsigned long handle;
    rsql_u16 first;
    rsql_u16 directory;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!handle_out ||
        (kind != RSQL_BLOB_KIND_TEXT && kind != RSQL_BLOB_KIND_BINARY)) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = create_blob_chain((const rsql_u8*)source, length, &first);
    if (rc != RSQL_OK) return rc;
    rc = find_empty_entry(&directory, &slot);
    if (rc == RSQL_OK) rc = rsql_catalog_reserve_blob_handle(&handle);
    if (rc != RSQL_OK) {
        if (first != RSQL_PAGE_NONE) free_blob_chain(first, 0);
        return rc;
    }
    rc = load_directory(directory);
    if (rc != RSQL_OK) return rc;
    base = entry_offset(slot);
    memset(&g_blob_directory[base], 0, BLOB_DIRECTORY_ENTRY_BYTES);
    g_blob_directory[base + BLOB_ENTRY_STATE] = BLOB_STATE_ACTIVE;
    g_blob_directory[base + BLOB_ENTRY_KIND] = kind;
    rsql_put_u32(&g_blob_directory[base + BLOB_ENTRY_HANDLE], handle);
    rsql_put_u16(&g_blob_directory[base + BLOB_ENTRY_FIRST_PAGE], first);
    rsql_put_u32(&g_blob_directory[base + BLOB_ENTRY_LENGTH], length);
    rc = store_directory(directory);
    if (rc == RSQL_OK) {
        rsql_put_u32(handle_out->bytes, handle);
    } else if (first != RSQL_PAGE_NONE) {
        free_blob_chain(first, 0);
    }
    return rc;
}

rsql_u8 rsql_blob_info(const RsqlBlobHandle* handle, RsqlBlobInfo* info_out) {
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!info_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = find_entry(handle, &page, &slot, 0u);
    if (rc != RSQL_OK) return rc;
    base = entry_offset(slot);
    memcpy(info_out->handle.bytes,
           &g_blob_directory[base + BLOB_ENTRY_HANDLE], 4u);
    info_out->length = rsql_get_u32(&g_blob_directory[base + BLOB_ENTRY_LENGTH]);
    info_out->kind = g_blob_directory[base + BLOB_ENTRY_KIND];
    info_out->first_page =
        rsql_get_u16(&g_blob_directory[base + BLOB_ENTRY_FIRST_PAGE]);
    return RSQL_OK;
}

rsql_u8 rsql_blob_read(const RsqlBlobHandle* handle, unsigned long offset,
                       void* destination, rsql_u16 capacity,
                       rsql_u16* bytes_read_out) {
    unsigned long length;
    rsql_u16 directory;
    rsql_u16 base;
    rsql_u16 page;
    rsql_u16 used;
    rsql_u16 take;
    rsql_u16 total = 0u;
    rsql_u8 slot;
    rsql_u8 rc;
    rsql_u8* output = (rsql_u8*)destination;
    if (!handle || !bytes_read_out || (capacity != 0u && !destination)) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = find_entry(handle, &directory, &slot, 0u);
    if (rc != RSQL_OK) return rc;
    base = entry_offset(slot);
    length = rsql_get_u32(&g_blob_directory[base + BLOB_ENTRY_LENGTH]);
    page = rsql_get_u16(&g_blob_directory[base + BLOB_ENTRY_FIRST_PAGE]);
    if (offset >= length || capacity == 0u) {
        *bytes_read_out = 0u;
        return RSQL_OK;
    }
    while (page != RSQL_PAGE_NONE && total < capacity) {
        rc = load_blob_page(page);
        if (rc != RSQL_OK) return rc;
        used = rsql_get_u16(&g_blob_data[BLOB_PAGE_USED]);
        if (offset >= used) {
            offset -= used;
        } else {
            take = (rsql_u16)(used - (rsql_u16)offset);
            if (take > (rsql_u16)(capacity - total)) {
                take = (rsql_u16)(capacity - total);
            }
            memcpy(output + total, &g_blob_data[BLOB_PAGE_DATA + (rsql_u16)offset],
                   take);
            total = (rsql_u16)(total + take);
            offset = 0ul;
        }
        page = rsql_get_u16(&g_blob_data[BLOB_PAGE_NEXT]);
    }
    *bytes_read_out = total;
    return RSQL_OK;
}

rsql_u8 rsql_blob_delete(const RsqlBlobHandle* handle) {
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 slot;
    rsql_u8 rc = find_entry(handle, &page, &slot, 0u);
    if (rc != RSQL_OK) return rc;
    base = entry_offset(slot);
    g_blob_directory[base + BLOB_ENTRY_STATE] = BLOB_STATE_DELETED;
    return store_directory(page);
}

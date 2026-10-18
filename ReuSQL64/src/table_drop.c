#include <string.h>

#include "rsql_catalog.h"
#include "rsql_errors.h"
#include "rsql_journal.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define DROP_A g_rsql_meta_page0
#define DROP_B g_rsql_meta_page1

#define BLOB_DIRECTORY_NEXT 6u
#define BLOB_DIRECTORY_ENTRIES 8u
#define BLOB_DIRECTORY_ENTRY_BYTES 20u
#define BLOB_DIRECTORY_ENTRY_COUNT 12u
#define BLOB_ENTRY_STATE 0u
#define BLOB_ENTRY_HANDLE 2u
#define BLOB_ENTRY_FIRST_PAGE 6u
#define BLOB_STATE_EMPTY 0u
#define BLOB_STATE_ACTIVE 1u
#define BLOB_PAGE_CHECKSUM 5u
#define BLOB_PAGE_NEXT 6u
#define BLOB_PAGE_USED 8u
#define BLOB_PAGE_DATA 10u
#define BLOB_PAGE_PAYLOAD (RSQL_REU_PAGE_SIZE - BLOB_PAGE_DATA)

#define DROP_ENUM_ID 6u
#define DROP_ENUM_NEXT 8u
#define DROP_ENUM_FIRST_MEMBERS 10u
#define DROP_ENUM_NAME_LENGTH 14u
#define DROP_ENUM_NAME 15u
#define DROP_MEMBER_NEXT 6u

static rsql_u16 g_drop_table;
static rsql_u16 g_drop_page;
static rsql_u16 g_drop_next;
static rsql_u16 g_drop_previous;
static rsql_u16 g_drop_base;
static rsql_u16 g_drop_row_width;
static rsql_u16 g_drop_row_page;
static rsql_u8 g_drop_slot;
static rsql_u8 g_drop_column;

static rsql_u8 folded(rsql_u8 value) {
    if (value >= (rsql_u8)'a' && value <= (rsql_u8)'z') {
        return (rsql_u8)(value - ((rsql_u8)'a' - (rsql_u8)'A'));
    }
    return value;
}

static rsql_u8 name_equal(const char* wanted, const rsql_u8* stored,
                          rsql_u8 stored_length) {
    rsql_u8 index;
    for (index = 0u; index < stored_length; ++index) {
        if (wanted[index] == 0u ||
            folded((rsql_u8)wanted[index]) != folded(stored[index])) {
            return 0u;
        }
    }
    return wanted[stored_length] == 0u;
}

static rsql_u8 valid_page(const rsql_u8* page, char a, char b,
                          char c, char d) {
    return page[0] == (rsql_u8)a && page[1] == (rsql_u8)b &&
           page[2] == (rsql_u8)c && page[3] == (rsql_u8)d &&
           page[4] == RSQL_STORAGE_VERSION &&
           page[RSQL_PAGE_CHECKSUM_OFFSET] == rsql_page_checksum(page);
}

static rsql_u8 load_checked(rsql_u16 page, rsql_u8* destination,
                            char a, char b, char c, char d) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), destination,
                               RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    return valid_page(destination, a, b, c, d)
        ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 store_checked(rsql_u16 page, rsql_u8* source) {
    source[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(source);
    return rsql_reu_write(rsql_reu_page_address(page), source,
                          RSQL_REU_PAGE_SIZE);
}

/* Row pages predate per-page checksums in storage format v2; validate the
 * same structural invariants as row.c instead of applying descriptor rules. */
static rsql_u8 load_row_page(rsql_u16 page) {
    rsql_u8 capacity;
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), DROP_A,
                               RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    capacity = DROP_A[RSQL_ROW_CAPACITY];
    if (DROP_A[0] != 'R' || DROP_A[1] != 'R' || DROP_A[2] != 'O' ||
        DROP_A[3] != 'W' || DROP_A[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&DROP_A[RSQL_ROW_WIDTH]) != g_drop_row_width ||
        capacity == 0u || capacity > 32u ||
        (rsql_u16)(RSQL_ROW_DATA + (rsql_u16)capacity * g_drop_row_width) >
            RSQL_REU_PAGE_SIZE) return RSQL_ERR_CORRUPT_STORAGE;
    return RSQL_OK;
}

static rsql_u8 mutate_finish(rsql_u8 rc) {
    return rsql_finish_mutation(rc);
}

static rsql_u8 mark_dropping(rsql_u16 table) {
    rsql_u8 rc = load_checked(table, DROP_A, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    if (DROP_A[RSQL_TABLE_FLAGS] & RSQL_TABLE_FLAG_DROPPING) return RSQL_OK;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    DROP_A[RSQL_TABLE_FLAGS] |= RSQL_TABLE_FLAG_DROPPING;
    rc = store_checked(table, DROP_A);
    return mutate_finish(rc);
}

static rsql_u8 find_temporary(rsql_u16* table_out) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_TABLE]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_TABLE_NEXT]);
        if (DROP_A[RSQL_TABLE_FLAGS] &
            (RSQL_TABLE_FLAG_TEMPORARY | RSQL_TABLE_FLAG_DROPPING |
             RSQL_TABLE_FLAG_BUILDING)) {
            *table_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 find_named_table(const char* name, rsql_u16* table_out) {
    rsql_u8 length;
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_TABLE]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_TABLE_NEXT]);
        length = DROP_A[RSQL_TABLE_NAME_LENGTH];
        if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(DROP_A[RSQL_TABLE_FLAGS] &
              (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING)) &&
            name_equal(name, &DROP_A[RSQL_TABLE_NAME], length)) {
            *table_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 find_named_index(const char* name, rsql_u16* descriptor_out) {
    rsql_u8 length;
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_INDEX]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_INDEX_NEXT]);
        length = DROP_A[RSQL_INDEX_NAME_LENGTH];
        if (length > RSQL_TABLE_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(DROP_A[RSQL_INDEX_FLAGS] & RSQL_INDEX_FLAG_DROPPING) &&
            name_equal(name, &DROP_A[RSQL_INDEX_NAME], length)) {
            *descriptor_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 find_dropping_index(rsql_u16* descriptor_out) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_INDEX]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_INDEX_NEXT]);
        if (DROP_A[RSQL_INDEX_FLAGS] & RSQL_INDEX_FLAG_DROPPING) {
            *descriptor_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 find_named_enum(const char* name, rsql_u16* enum_out) {
    rsql_u8 length;
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_ENUM]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[DROP_ENUM_NEXT]);
        length = DROP_A[DROP_ENUM_NAME_LENGTH];
        if (length > RSQL_ENUM_NAME_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(DROP_A[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING) &&
            name_equal(name, &DROP_A[DROP_ENUM_NAME], length)) {
            *enum_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 find_dropping_enum(rsql_u16* enum_out) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_ENUM]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[DROP_ENUM_NEXT]);
        if (DROP_A[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING) {
            *enum_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 blob_checksum(const rsql_u8* page) {
    rsql_u8 value = 0xB7u;
    rsql_u16 index;
    for (index = 0u; index < RSQL_REU_PAGE_SIZE; ++index) {
        if (index != BLOB_PAGE_CHECKSUM) value ^= page[index];
    }
    return value;
}

static rsql_u8 load_blob_page(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), DROP_B,
                               RSQL_REU_PAGE_SIZE);
    if (rc != RSQL_OK) return rc;
    if (DROP_B[0] != 'R' || DROP_B[1] != 'B' || DROP_B[2] != 'L' ||
        DROP_B[3] != 'B' || DROP_B[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&DROP_B[BLOB_PAGE_USED]) > BLOB_PAGE_PAYLOAD ||
        DROP_B[BLOB_PAGE_CHECKSUM] != blob_checksum(DROP_B)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

static rsql_u8 handle_equal(const rsql_u8* left, const rsql_u8* right) {
    return left[0] == right[0] && left[1] == right[1] &&
           left[2] == right[2] && left[3] == right[3];
}

static rsql_u8 find_blob_entry(const rsql_u8* handle,
                               rsql_u16* directory_out,
                               rsql_u16* base_out) {
    rsql_u8 slot;
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_BLOB_DIRECTORY]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'B', 'D', 'R');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[BLOB_DIRECTORY_NEXT]);
        for (slot = 0u; slot < BLOB_DIRECTORY_ENTRY_COUNT; ++slot) {
            g_drop_base = (rsql_u16)(BLOB_DIRECTORY_ENTRIES +
                (rsql_u16)slot * BLOB_DIRECTORY_ENTRY_BYTES);
            if (DROP_A[g_drop_base + BLOB_ENTRY_STATE] == BLOB_STATE_ACTIVE &&
                handle_equal(&DROP_A[g_drop_base + BLOB_ENTRY_HANDLE],
                             handle)) {
                *directory_out = g_drop_page;
                *base_out = g_drop_base;
                return RSQL_OK;
            }
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

/* Advance the stable directory entry before releasing each payload page. If
 * power is lost, the visible dropping table still owns the handle and the
 * next initialization resumes from the updated first-page link. */
static rsql_u8 reclaim_blob(const rsql_u8* handle) {
    rsql_u16 directory;
    rsql_u16 base;
    rsql_u16 first;
    rsql_u8 rc;
    for (;;) {
        rc = find_blob_entry(handle, &directory, &base);
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc != RSQL_OK) return rc;
        first = rsql_get_u16(&DROP_A[base + BLOB_ENTRY_FIRST_PAGE]);
        if (first == RSQL_PAGE_NONE) {
            rc = rsql_journal_begin();
            if (rc != RSQL_OK) return rc;
            memset(&DROP_A[base], 0, BLOB_DIRECTORY_ENTRY_BYTES);
            rc = store_checked(directory, DROP_A);
            return mutate_finish(rc);
        }
        rc = load_blob_page(first);
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_B[BLOB_PAGE_NEXT]);
        rc = load_checked(directory, DROP_A, 'R', 'B', 'D', 'R');
        if (rc != RSQL_OK) return rc;
        rc = rsql_journal_begin();
        if (rc != RSQL_OK) return rc;
        rsql_put_u16(&DROP_A[base + BLOB_ENTRY_FIRST_PAGE], g_drop_next);
        rc = store_checked(directory, DROP_A);
        if (rc == RSQL_OK) rc = rsql_page_free(first);
        rc = mutate_finish(rc);
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 load_first_row(rsql_u8* found_out) {
    rsql_u16 offset;
    rsql_u8 capacity;
    rsql_u8 rc = load_checked(g_drop_table, DROP_A, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    g_drop_row_width = rsql_get_u16(&DROP_A[RSQL_TABLE_ROW_WIDTH]);
    g_rsql_execution.column_count = DROP_A[RSQL_TABLE_COLUMN_COUNT];
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_TABLE_ROW_HEAD]);
    g_drop_row_page = g_drop_page;
    if (g_drop_page == RSQL_PAGE_NONE) {
        *found_out = 0u;
        return RSQL_OK;
    }
    for (g_drop_column = 0u;
         g_drop_column < g_rsql_execution.column_count; ++g_drop_column) {
        g_drop_base = (rsql_u16)(RSQL_TABLE_COLUMNS +
            (rsql_u16)g_drop_column * RSQL_COLUMN_BYTES);
        g_rsql_execution.columns[g_drop_column].type.tag =
            DROP_A[g_drop_base + RSQL_COLUMN_TYPE];
        g_rsql_execution.columns[g_drop_column].offset =
            rsql_get_u16(&DROP_A[g_drop_base + RSQL_COLUMN_OFFSET]);
    }
    rc = load_row_page(g_drop_page);
    if (rc != RSQL_OK) return rc;
    capacity = DROP_A[RSQL_ROW_CAPACITY];
    if (capacity == 0u || capacity > 32u) return RSQL_ERR_CORRUPT_STORAGE;
    for (g_drop_slot = 0u; g_drop_slot < capacity; ++g_drop_slot) {
        if (DROP_A[RSQL_ROW_BITMAP + (g_drop_slot >> 3u)] &
            (rsql_u8)(1u << (g_drop_slot & 7u))) {
            offset = (rsql_u16)(RSQL_ROW_DATA +
                (rsql_u16)g_drop_slot * g_drop_row_width);
            memcpy(g_rsql_execution.row, &DROP_A[offset], g_drop_row_width);
            *found_out = 1u;
            return RSQL_OK;
        }
    }
    *found_out = 0u;
    return RSQL_OK;
}

static rsql_u8 remove_loaded_row(void) {
    rsql_u16 offset;
    rsql_u8 mask = (rsql_u8)(1u << (g_drop_slot & 7u));
    rsql_u8 rc = load_row_page(g_drop_row_page);
    if (rc != RSQL_OK) return rc;
    if (!(DROP_A[RSQL_ROW_BITMAP + (g_drop_slot >> 3u)] & mask)) {
        return RSQL_OK;
    }
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    offset = (rsql_u16)(RSQL_ROW_DATA +
        (rsql_u16)g_drop_slot * g_drop_row_width);
    memset(&DROP_A[offset], 0, g_drop_row_width);
    DROP_A[RSQL_ROW_BITMAP + (g_drop_slot >> 3u)] &= (rsql_u8)~mask;
    rc = rsql_reu_write(rsql_reu_page_address(g_drop_row_page), DROP_A,
                        RSQL_REU_PAGE_SIZE);
    if (rc == RSQL_OK) {
        rc = load_checked(g_drop_table, DROP_A, 'R', 'T', 'B', 'L');
    }
    if (rc == RSQL_OK) {
        rsql_decrement_u32(&DROP_A[RSQL_TABLE_ROW_COUNT]);
        rc = store_checked(g_drop_table, DROP_A);
    }
    return mutate_finish(rc);
}

static rsql_u8 release_empty_head(void) {
    rsql_u8 rc = load_row_page(g_drop_row_page);
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_A[RSQL_ROW_NEXT]);
    rc = load_checked(g_drop_table, DROP_A, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[RSQL_TABLE_ROW_HEAD], g_drop_next);
    if (g_drop_next == RSQL_PAGE_NONE) {
        rsql_put_u16(&DROP_A[RSQL_TABLE_ROW_TAIL], RSQL_PAGE_NONE);
    }
    rc = store_checked(g_drop_table, DROP_A);
    if (rc == RSQL_OK) rc = rsql_page_free(g_drop_row_page);
    return mutate_finish(rc);
}

static rsql_u8 reclaim_rows(void) {
    rsql_u8 found;
    rsql_u8 rc;
    for (;;) {
        rc = load_first_row(&found);
        if (rc != RSQL_OK) return rc;
        if (g_drop_row_page == RSQL_PAGE_NONE) return RSQL_OK;
        if (!found) {
            rc = release_empty_head();
            if (rc != RSQL_OK) return rc;
            continue;
        }
        for (g_drop_column = 0u;
             g_drop_column < g_rsql_execution.column_count; ++g_drop_column) {
            if ((g_rsql_execution.columns[g_drop_column].type.tag ==
                    RSQL_TYPE_TEXT ||
                 g_rsql_execution.columns[g_drop_column].type.tag ==
                    RSQL_TYPE_BLOB) &&
                !(g_rsql_execution.row[g_drop_column >> 3u] &
                  (rsql_u8)(1u << (g_drop_column & 7u)))) {
                rc = reclaim_blob(&g_rsql_execution.row[
                    g_rsql_execution.columns[g_drop_column].offset]);
                if (rc != RSQL_OK) return rc;
            }
        }
        rc = remove_loaded_row();
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 mark_index_dropping(rsql_u16 descriptor) {
    rsql_u8 rc = load_checked(descriptor, DROP_A, 'R', 'I', 'D', 'X');
    if (rc != RSQL_OK) return rc;
    if (DROP_A[RSQL_INDEX_FLAGS] & RSQL_INDEX_FLAG_DROPPING) return RSQL_OK;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    DROP_A[RSQL_INDEX_FLAGS] |= RSQL_INDEX_FLAG_DROPPING;
    rc = store_checked(descriptor, DROP_A);
    return mutate_finish(rc);
}

static rsql_u8 find_owned_index(rsql_u16* descriptor_out) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_INDEX]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_INDEX_NEXT]);
        if (rsql_get_u16(&DROP_A[RSQL_INDEX_TABLE]) == g_drop_table) {
            *descriptor_out = g_drop_page;
            return RSQL_OK;
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 release_index_leaf(rsql_u16 descriptor, rsql_u16 leaf) {
    rsql_u8 rc = load_checked(leaf, DROP_B, 'R', 'I', 'L', 'F');
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_B[RSQL_INDEX_LEAF_NEXT]);
    rc = load_checked(descriptor, DROP_A, 'R', 'I', 'D', 'X');
    if (rc != RSQL_OK) return rc;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[RSQL_INDEX_LEAF_HEAD], g_drop_next);
    if (g_drop_next == RSQL_PAGE_NONE) {
        rsql_put_u16(&DROP_A[RSQL_INDEX_LEAF_TAIL], RSQL_PAGE_NONE);
    }
    rc = store_checked(descriptor, DROP_A);
    if (rc == RSQL_OK) rc = rsql_page_free(leaf);
    return mutate_finish(rc);
}

static rsql_u8 unlink_index(rsql_u16 descriptor) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_previous = RSQL_PAGE_NONE;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_INDEX]);
    while (g_drop_page != RSQL_PAGE_NONE && g_drop_page != descriptor) {
        g_drop_previous = g_drop_page;
        rc = load_checked(g_drop_page, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        g_drop_page = rsql_get_u16(&DROP_A[RSQL_INDEX_NEXT]);
    }
    if (g_drop_page == RSQL_PAGE_NONE) return RSQL_OK;
    rc = load_checked(descriptor, DROP_B, 'R', 'I', 'D', 'X');
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_B[RSQL_INDEX_NEXT]);
    if (g_drop_previous == RSQL_PAGE_NONE) {
        rc = load_checked(rsql_page_catalog_root(), DROP_A,
                          'R', 'C', 'A', 'T');
        if (rc != RSQL_OK) return rc;
    } else {
        rc = load_checked(g_drop_previous, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
    }
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[g_drop_previous == RSQL_PAGE_NONE
        ? RSQL_ROOT_FIRST_INDEX : RSQL_INDEX_NEXT], g_drop_next);
    rc = store_checked(g_drop_previous == RSQL_PAGE_NONE
        ? rsql_page_catalog_root() : g_drop_previous, DROP_A);
    if (rc == RSQL_OK) rc = rsql_page_free(descriptor);
    return mutate_finish(rc);
}

static rsql_u8 reclaim_indexes(void) {
    rsql_u16 descriptor;
    rsql_u16 leaf;
    rsql_u8 rc;
    for (;;) {
        rc = find_owned_index(&descriptor);
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc != RSQL_OK) return rc;
        rc = load_checked(descriptor, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        leaf = rsql_get_u16(&DROP_A[RSQL_INDEX_LEAF_HEAD]);
        if (leaf != RSQL_PAGE_NONE) rc = release_index_leaf(descriptor, leaf);
        else rc = unlink_index(descriptor);
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 reclaim_index(rsql_u16 descriptor) {
    rsql_u16 leaf;
    rsql_u8 rc;
    for (;;) {
        rc = load_checked(descriptor, DROP_A, 'R', 'I', 'D', 'X');
        if (rc != RSQL_OK) return rc;
        leaf = rsql_get_u16(&DROP_A[RSQL_INDEX_LEAF_HEAD]);
        if (leaf != RSQL_PAGE_NONE) {
            rc = release_index_leaf(descriptor, leaf);
        } else {
            return unlink_index(descriptor);
        }
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 enum_referenced(rsql_u16 descriptor) {
    rsql_u8 count;
    rsql_u8 type;
    rsql_u8 rc = load_checked(descriptor, DROP_A, 'R', 'E', 'N', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_base = rsql_get_u16(&DROP_A[DROP_ENUM_ID]);
    rc = load_checked(rsql_page_catalog_root(), DROP_A, 'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_TABLE]);
    while (g_drop_page != RSQL_PAGE_NONE) {
        rc = load_checked(g_drop_page, DROP_A, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        g_drop_next = rsql_get_u16(&DROP_A[RSQL_TABLE_NEXT]);
        count = DROP_A[RSQL_TABLE_COLUMN_COUNT];
        if (count > RSQL_TABLE_COLUMNS_MAX) return RSQL_ERR_CORRUPT_STORAGE;
        if (!(DROP_A[RSQL_TABLE_FLAGS] &
              (RSQL_TABLE_FLAG_DROPPING | RSQL_TABLE_FLAG_BUILDING))) {
            for (g_drop_column = 0u; g_drop_column < count; ++g_drop_column) {
                g_drop_row_width = (rsql_u16)(RSQL_TABLE_COLUMNS +
                    (rsql_u16)g_drop_column * RSQL_COLUMN_BYTES);
                type = DROP_A[g_drop_row_width + RSQL_COLUMN_TYPE];
                if ((type == RSQL_TYPE_ENUM8 || type == RSQL_TYPE_ENUM16) &&
                    rsql_get_u16(&DROP_A[g_drop_row_width +
                        RSQL_COLUMN_AUXILIARY]) == g_drop_base) {
                    return RSQL_ERR_DEPENDENT_OBJECT;
                }
            }
        }
        g_drop_page = g_drop_next;
    }
    return RSQL_OK;
}

static rsql_u8 mark_enum_dropping(rsql_u16 descriptor) {
    rsql_u8 rc = load_checked(descriptor, DROP_A, 'R', 'E', 'N', 'T');
    if (rc != RSQL_OK) return rc;
    if (DROP_A[RSQL_ENUM_FLAGS] & RSQL_ENUM_FLAG_DROPPING) return RSQL_OK;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    DROP_A[RSQL_ENUM_FLAGS] |= RSQL_ENUM_FLAG_DROPPING;
    rc = store_checked(descriptor, DROP_A);
    return mutate_finish(rc);
}

static rsql_u8 release_enum_member(rsql_u16 descriptor, rsql_u16 member) {
    rsql_u8 rc = load_checked(member, DROP_B, 'R', 'E', 'M', 'B');
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_B[DROP_MEMBER_NEXT]);
    rc = load_checked(descriptor, DROP_A, 'R', 'E', 'N', 'T');
    if (rc != RSQL_OK) return rc;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[DROP_ENUM_FIRST_MEMBERS], g_drop_next);
    rc = store_checked(descriptor, DROP_A);
    if (rc == RSQL_OK) rc = rsql_page_free(member);
    return mutate_finish(rc);
}

static rsql_u8 unlink_enum(rsql_u16 descriptor) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_previous = RSQL_PAGE_NONE;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_ENUM]);
    while (g_drop_page != RSQL_PAGE_NONE && g_drop_page != descriptor) {
        g_drop_previous = g_drop_page;
        rc = load_checked(g_drop_page, DROP_A, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        g_drop_page = rsql_get_u16(&DROP_A[DROP_ENUM_NEXT]);
    }
    if (g_drop_page == RSQL_PAGE_NONE) return RSQL_OK;
    rc = load_checked(descriptor, DROP_B, 'R', 'E', 'N', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_B[DROP_ENUM_NEXT]);
    if (g_drop_previous == RSQL_PAGE_NONE) {
        rc = load_checked(rsql_page_catalog_root(), DROP_A,
                          'R', 'C', 'A', 'T');
    } else {
        rc = load_checked(g_drop_previous, DROP_A, 'R', 'E', 'N', 'T');
    }
    if (rc != RSQL_OK) return rc;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[g_drop_previous == RSQL_PAGE_NONE
        ? RSQL_ROOT_FIRST_ENUM : DROP_ENUM_NEXT], g_drop_next);
    rc = store_checked(g_drop_previous == RSQL_PAGE_NONE
        ? rsql_page_catalog_root() : g_drop_previous, DROP_A);
    if (rc == RSQL_OK) {
        rc = load_checked(rsql_page_catalog_root(), DROP_A,
                          'R', 'C', 'A', 'T');
    }
    if (rc == RSQL_OK) {
        if (DROP_A[RSQL_ROOT_ENUM_COUNT] == 0u) {
            rc = RSQL_ERR_CORRUPT_STORAGE;
        } else {
            --DROP_A[RSQL_ROOT_ENUM_COUNT];
            rc = store_checked(rsql_page_catalog_root(), DROP_A);
        }
    }
    if (rc == RSQL_OK) rc = rsql_page_free(descriptor);
    return mutate_finish(rc);
}

static rsql_u8 reclaim_enum(rsql_u16 descriptor) {
    rsql_u16 member;
    rsql_u8 rc;
    for (;;) {
        rc = load_checked(descriptor, DROP_A, 'R', 'E', 'N', 'T');
        if (rc != RSQL_OK) return rc;
        member = rsql_get_u16(&DROP_A[DROP_ENUM_FIRST_MEMBERS]);
        if (member == RSQL_PAGE_NONE) return unlink_enum(descriptor);
        rc = release_enum_member(descriptor, member);
        if (rc != RSQL_OK) return rc;
    }
}

static rsql_u8 unlink_table(void) {
    rsql_u8 rc = load_checked(rsql_page_catalog_root(), DROP_A,
                              'R', 'C', 'A', 'T');
    if (rc != RSQL_OK) return rc;
    g_drop_previous = RSQL_PAGE_NONE;
    g_drop_page = rsql_get_u16(&DROP_A[RSQL_ROOT_FIRST_TABLE]);
    while (g_drop_page != RSQL_PAGE_NONE && g_drop_page != g_drop_table) {
        g_drop_previous = g_drop_page;
        rc = load_checked(g_drop_page, DROP_A, 'R', 'T', 'B', 'L');
        if (rc != RSQL_OK) return rc;
        g_drop_page = rsql_get_u16(&DROP_A[RSQL_TABLE_NEXT]);
    }
    if (g_drop_page == RSQL_PAGE_NONE) return RSQL_OK;
    rc = load_checked(g_drop_table, DROP_B, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    g_drop_next = rsql_get_u16(&DROP_B[RSQL_TABLE_NEXT]);
    if (g_drop_previous == RSQL_PAGE_NONE) {
        rc = load_checked(rsql_page_catalog_root(), DROP_A,
                          'R', 'C', 'A', 'T');
    } else {
        rc = load_checked(g_drop_previous, DROP_A, 'R', 'T', 'B', 'L');
    }
    if (rc != RSQL_OK) return rc;
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    rsql_put_u16(&DROP_A[g_drop_previous == RSQL_PAGE_NONE
        ? RSQL_ROOT_FIRST_TABLE : RSQL_TABLE_NEXT], g_drop_next);
    rc = store_checked(g_drop_previous == RSQL_PAGE_NONE
        ? rsql_page_catalog_root() : g_drop_previous, DROP_A);
    if (rc == RSQL_OK) {
        rc = load_checked(rsql_page_catalog_root(), DROP_A,
                          'R', 'C', 'A', 'T');
    }
    if (rc == RSQL_OK) {
        if (DROP_A[RSQL_ROOT_TABLE_COUNT] == 0u) rc = RSQL_ERR_CORRUPT_STORAGE;
        else {
            --DROP_A[RSQL_ROOT_TABLE_COUNT];
            rc = store_checked(rsql_page_catalog_root(), DROP_A);
        }
    }
    if (rc == RSQL_OK) rc = rsql_page_free(g_drop_table);
    return mutate_finish(rc);
}

rsql_u8 __fastcall__ rsql_table_drop_phase(rsql_u16 table_page) {
    rsql_u8 rc;
    g_drop_table = table_page;
    rc = mark_dropping(g_drop_table);
    if (rc == RSQL_OK) rc = reclaim_indexes();
    if (rc == RSQL_OK) rc = reclaim_rows();
    if (rc == RSQL_OK) rc = unlink_table();
    return rc;
}

rsql_u8 __fastcall__ rsql_table_publish_phase(rsql_u16 table_page) {
    rsql_u8 rc = load_checked(table_page, DROP_A, 'R', 'T', 'B', 'L');
    if (rc != RSQL_OK) return rc;
    if (!(DROP_A[RSQL_TABLE_FLAGS] & RSQL_TABLE_FLAG_BUILDING)) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    rc = rsql_journal_begin();
    if (rc != RSQL_OK) return rc;
    DROP_A[RSQL_TABLE_FLAGS] &= (rsql_u8)~RSQL_TABLE_FLAG_BUILDING;
    rc = store_checked(table_page, DROP_A);
    return mutate_finish(rc);
}

rsql_u8 rsql_query_drop_phase(void) {
    rsql_u16 descriptor;
    rsql_u8 rc;
    if (g_rsql_statement.kind == RSQL_STMT_DROP_TABLE) {
        rc = find_named_table(g_rsql_statement.table_name, &descriptor);
        if (rc != RSQL_OK) return rc;
        return rsql_table_drop_phase(descriptor);
    }
    if (g_rsql_statement.kind == RSQL_STMT_DROP_INDEX) {
        rc = find_named_index(g_rsql_statement.index_name, &descriptor);
        if (rc != RSQL_OK) return rc;
        rc = mark_index_dropping(descriptor);
        return rc == RSQL_OK ? reclaim_index(descriptor) : rc;
    }
    if (g_rsql_statement.kind == RSQL_STMT_DROP_ENUM) {
        rc = find_named_enum(g_rsql_statement.table_name, &descriptor);
        if (rc != RSQL_OK) return rc;
        rc = enum_referenced(descriptor);
        if (rc != RSQL_OK) return rc;
        rc = mark_enum_dropping(descriptor);
        return rc == RSQL_OK ? reclaim_enum(descriptor) : rc;
    }
    return RSQL_ERR_UNSUPPORTED_SQL;
}

rsql_u8 rsql_temp_cleanup_phase(void) {
    rsql_u16 descriptor;
    rsql_u8 rc;
    for (;;) {
        rc = find_dropping_index(&descriptor);
        if (rc == RSQL_ERR_NOT_FOUND) break;
        if (rc != RSQL_OK) return rc;
        rc = reclaim_index(descriptor);
        if (rc != RSQL_OK) return rc;
    }
    for (;;) {
        rc = find_dropping_enum(&descriptor);
        if (rc == RSQL_ERR_NOT_FOUND) break;
        if (rc != RSQL_OK) return rc;
        rc = reclaim_enum(descriptor);
        if (rc != RSQL_OK) return rc;
    }
    for (;;) {
        rc = find_temporary(&g_drop_table);
        if (rc == RSQL_ERR_NOT_FOUND) return RSQL_OK;
        if (rc != RSQL_OK) return rc;
        rc = rsql_table_drop_phase(g_drop_table);
        if (rc != RSQL_OK) return rc;
    }
}

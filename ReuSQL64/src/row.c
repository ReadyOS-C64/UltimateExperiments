#include <string.h>

#include "rsql_errors.h"
#include "rsql.h"
#include "rsql_blob.h"
#include "rsql_catalog.h"
#include "rsql_page.h"
#include "rsql_query.h"
#include "rsql_reu.h"
#include "rsql_row.h"
#include "rsql_scratch.h"
#include "storage_layout.h"
#include "api_internal.h"

/* Row calls and wide traversal never execute concurrently: both occupy the
 * same overlay window. Reuse metadata page 1 for the table descriptor while
 * retaining an independent row page; CTAS keeps its projected bytes in page
 * 0 across this phase. */
#define g_table_page g_rsql_meta_page1
static rsql_u8 g_row_page[RSQL_REU_PAGE_SIZE];

static rsql_u8 valid_table(void) {
    return g_table_page[0] == 'R' && g_table_page[1] == 'T' &&
           g_table_page[2] == 'B' && g_table_page[3] == 'L' &&
           g_table_page[4] == RSQL_STORAGE_VERSION &&
           g_table_page[RSQL_PAGE_CHECKSUM_OFFSET] ==
               rsql_page_checksum(g_table_page);
}

static rsql_u8 load_table(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_table_page,
                               sizeof(g_table_page));
    if (rc != RSQL_OK) return rc;
    return valid_table() ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 store_table(rsql_u16 page) {
    g_table_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_table_page);
    return rsql_reu_write(rsql_reu_page_address(page), g_table_page,
                          sizeof(g_table_page));
}

static rsql_u8 valid_row_page(rsql_u16 row_width) {
    rsql_u8 capacity;
    if (g_row_page[0] != 'R' || g_row_page[1] != 'R' ||
        g_row_page[2] != 'O' || g_row_page[3] != 'W' ||
        g_row_page[4] != RSQL_STORAGE_VERSION ||
        rsql_get_u16(&g_row_page[RSQL_ROW_WIDTH]) != row_width) {
        return 0u;
    }
    capacity = g_row_page[RSQL_ROW_CAPACITY];
    return capacity != 0u && capacity <= 32u &&
           (rsql_u16)(RSQL_ROW_DATA + (rsql_u16)capacity * row_width) <=
               RSQL_REU_PAGE_SIZE;
}

static rsql_u8 load_row_page(rsql_u16 page, rsql_u16 row_width) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_row_page,
                               sizeof(g_row_page));
    if (rc != RSQL_OK) return rc;
    return valid_row_page(row_width) ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 slot_used(rsql_u8 slot) {
    return (g_row_page[RSQL_ROW_BITMAP + (slot >> 3u)] &
            (rsql_u8)(1u << (slot & 7u))) ? 1u : 0u;
}

static void set_slot(rsql_u8 slot, rsql_u8 used) {
    rsql_u8* byte = &g_row_page[RSQL_ROW_BITMAP + (slot >> 3u)];
    rsql_u8 mask = (rsql_u8)(1u << (slot & 7u));
    *byte = used ? (rsql_u8)(*byte | mask)
                 : (rsql_u8)(*byte & (rsql_u8)~mask);
}

static rsql_u8 find_free_slot(rsql_u8* slot_out) {
    rsql_u8 slot;
    for (slot = 0u; slot < g_row_page[RSQL_ROW_CAPACITY]; ++slot) {
        if (!slot_used(slot)) {
            *slot_out = slot;
            return 1u;
        }
    }
    return 0u;
}

static rsql_u8 write_row_to_loaded_page(rsql_u16 page, rsql_u16 row_width,
                                        rsql_u8 slot, const void* row) {
    rsql_u16 offset = (rsql_u16)(RSQL_ROW_DATA +
                                 (rsql_u16)slot * row_width);
    memcpy(&g_row_page[offset], row, row_width);
    set_slot(slot, 1u);
    return rsql_reu_write(rsql_reu_page_address(page), g_row_page,
                          sizeof(g_row_page));
}

static rsql_u8 update_row_count(rsql_u16 table_page, rsql_u8 increment) {
    rsql_u8 rc = load_table(table_page);
    if (rc != RSQL_OK) return rc;
    if (increment) rsql_increment_u32(&g_table_page[RSQL_TABLE_ROW_COUNT]);
    else rsql_decrement_u32(&g_table_page[RSQL_TABLE_ROW_COUNT]);
    return store_table(table_page);
}

static rsql_u8 locate_row_page(rsql_u16 table_page, rsql_u16 wanted_page,
                               rsql_u16* row_width_out) {
    rsql_u16 page;
    rsql_u16 row_width;
    rsql_u8 rc = load_table(table_page);
    if (rc != RSQL_OK) return rc;
    row_width = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_WIDTH]);
    page = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = load_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        if (page == wanted_page) {
            *row_width_out = row_width;
            return RSQL_OK;
        }
        page = rsql_get_u16(&g_row_page[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_row_insert(rsql_u16 table_page, const void* row,
                        rsql_u16 row_length, RsqlRowId* row_id_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 tail;
    rsql_u16 row_width;
    rsql_u16 new_page;
    rsql_u8 capacity;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!row || !row_id_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = load_table(table_page);
    if (rc != RSQL_OK) return rc;
    row_width = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_WIDTH]);
    if (row_length != row_width) return RSQL_ERR_TYPE_MISMATCH;
    page = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_HEAD]);
    tail = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_TAIL]);

    while (page != RSQL_PAGE_NONE) {
        rc = load_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&g_row_page[RSQL_ROW_NEXT]);
        if (find_free_slot(&slot)) {
            rc = write_row_to_loaded_page(page, row_width, slot, row);
            if (rc == RSQL_OK) rc = update_row_count(table_page, 1u);
            if (rc == RSQL_OK) {
                row_id_out->page = page;
                row_id_out->slot = slot;
            }
            return rc;
        }
        page = next;
    }

    capacity = (rsql_u8)((RSQL_REU_PAGE_SIZE - RSQL_ROW_DATA) / row_width);
    if (capacity > 32u) capacity = 32u;
    if (capacity == 0u) return RSQL_ERR_ROW_TOO_WIDE;
    rc = rsql_page_allocate(&new_page);
    if (rc != RSQL_OK) return rc;
    memset(g_row_page, 0, sizeof(g_row_page));
    g_row_page[0] = 'R';
    g_row_page[1] = 'R';
    g_row_page[2] = 'O';
    g_row_page[3] = 'W';
    g_row_page[4] = RSQL_STORAGE_VERSION;
    g_row_page[RSQL_ROW_CAPACITY] = capacity;
    rsql_put_u16(&g_row_page[RSQL_ROW_WIDTH], row_width);
    rsql_put_u16(&g_row_page[RSQL_ROW_NEXT], RSQL_PAGE_NONE);
    rsql_put_u16(&g_row_page[RSQL_ROW_PREVIOUS], tail);
    rc = write_row_to_loaded_page(new_page, row_width, 0u, row);
    if (rc != RSQL_OK) {
        rsql_page_free(new_page);
        return rc;
    }

    if (tail != RSQL_PAGE_NONE) {
        rc = load_row_page(tail, row_width);
        if (rc != RSQL_OK) return rc;
        rsql_put_u16(&g_row_page[RSQL_ROW_NEXT], new_page);
        rc = rsql_reu_write(rsql_reu_page_address(tail), g_row_page,
                            sizeof(g_row_page));
        if (rc != RSQL_OK) return rc;
    }
    rc = load_table(table_page);
    if (rc != RSQL_OK) return rc;
    if (tail == RSQL_PAGE_NONE) {
        rsql_put_u16(&g_table_page[RSQL_TABLE_ROW_HEAD], new_page);
    }
    rsql_put_u16(&g_table_page[RSQL_TABLE_ROW_TAIL], new_page);
    rsql_increment_u32(&g_table_page[RSQL_TABLE_ROW_COUNT]);
    rc = store_table(table_page);
    if (rc == RSQL_OK) {
        row_id_out->page = new_page;
        row_id_out->slot = 0u;
    }
    return rc;
}

rsql_u8 rsql_row_read(rsql_u16 table_page, const RsqlRowId* row_id,
                      void* destination, rsql_u16 capacity) {
    rsql_u16 row_width;
    rsql_u16 offset;
    rsql_u8 rc;
    if (!row_id || !destination) return RSQL_ERR_INVALID_ARGUMENT;
    rc = locate_row_page(table_page, row_id->page, &row_width);
    if (rc != RSQL_OK) return rc;
    if (capacity < row_width) return RSQL_ERR_BUFFER_TOO_SMALL;
    if (row_id->slot >= g_row_page[RSQL_ROW_CAPACITY] ||
        !slot_used(row_id->slot)) return RSQL_ERR_NOT_FOUND;
    offset = (rsql_u16)(RSQL_ROW_DATA +
                        (rsql_u16)row_id->slot * row_width);
    memcpy(destination, &g_row_page[offset], row_width);
    return RSQL_OK;
}

rsql_u8 rsql_row_delete(rsql_u16 table_page, const RsqlRowId* row_id) {
    rsql_u16 row_width;
    rsql_u16 offset;
    rsql_u8 rc;
    if (!row_id) return RSQL_ERR_INVALID_ARGUMENT;
    rc = locate_row_page(table_page, row_id->page, &row_width);
    if (rc != RSQL_OK) return rc;
    if (row_id->slot >= g_row_page[RSQL_ROW_CAPACITY] ||
        !slot_used(row_id->slot)) return RSQL_ERR_NOT_FOUND;
    offset = (rsql_u16)(RSQL_ROW_DATA +
                        (rsql_u16)row_id->slot * row_width);
    memset(&g_row_page[offset], 0, row_width);
    set_slot(row_id->slot, 0u);
    rc = rsql_reu_write(rsql_reu_page_address(row_id->page), g_row_page,
                        sizeof(g_row_page));
    if (rc == RSQL_OK) rc = update_row_count(table_page, 0u);
    return rc;
}

rsql_u8 rsql_row_update(rsql_u16 table_page, const RsqlRowId* row_id,
                        const void* row, rsql_u16 row_length) {
    rsql_u16 row_width;
    rsql_u16 offset;
    rsql_u8 rc;
    if (!row_id || !row) return RSQL_ERR_INVALID_ARGUMENT;
    rc = locate_row_page(table_page, row_id->page, &row_width);
    if (rc != RSQL_OK) return rc;
    if (row_length != row_width) return RSQL_ERR_TYPE_MISMATCH;
    if (row_id->slot >= g_row_page[RSQL_ROW_CAPACITY] ||
        !slot_used(row_id->slot)) return RSQL_ERR_NOT_FOUND;
    offset = (rsql_u16)(RSQL_ROW_DATA +
                        (rsql_u16)row_id->slot * row_width);
    memcpy(&g_row_page[offset], row, row_width);
    return rsql_reu_write(rsql_reu_page_address(row_id->page), g_row_page,
                          sizeof(g_row_page));
}

rsql_u8 rsql_ctas_patch_phase(void) {
    rsql_u8 rc = rsql_row_read(g_result_table_page, &g_result_row_id,
        g_rsql_execution.row, sizeof(g_rsql_execution.row));
    if (rc != RSQL_OK) return rc;
    if (g_result_value.value.is_null) {
        g_rsql_execution.row[g_result_value.column >> 3u] |=
            (rsql_u8)(1u << (g_result_value.column & 7u));
    } else if (g_result_destination.type.tag == RSQL_TYPE_TEXT ||
               g_result_destination.type.tag == RSQL_TYPE_BLOB) {
        memcpy(&g_rsql_execution.row[g_result_destination.offset],
               g_result_handle.bytes, sizeof(g_result_handle.bytes));
    } else {
        if (g_result_destination.type.tag == RSQL_TYPE_CHAR) {
            memset(&g_rsql_execution.row[g_result_destination.offset], ' ',
                   g_result_destination.type.parameter);
        }
        memcpy(&g_rsql_execution.row[g_result_destination.offset],
               g_rsql_meta_page0, g_result_copy);
    }
    return rsql_row_update(g_result_table_page, &g_result_row_id,
        g_rsql_execution.row, g_rsql_statement.error_offset);
}

rsql_u8 rsql_row_first(rsql_u16 table_page, RsqlRowId* row_id_out) {
    rsql_u16 page;
    rsql_u16 row_width;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!row_id_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = load_table(table_page);
    if (rc != RSQL_OK) return rc;
    row_width = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_WIDTH]);
    page = rsql_get_u16(&g_table_page[RSQL_TABLE_ROW_HEAD]);
    while (page != RSQL_PAGE_NONE) {
        rc = load_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        for (slot = 0u; slot < g_row_page[RSQL_ROW_CAPACITY]; ++slot) {
            if (slot_used(slot)) {
                row_id_out->page = page;
                row_id_out->slot = slot;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_row_page[RSQL_ROW_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_row_next(rsql_u16 table_page, const RsqlRowId* current,
                      RsqlRowId* row_id_out) {
    rsql_u16 page;
    rsql_u16 next;
    rsql_u16 row_width;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!current || !row_id_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = locate_row_page(table_page, current->page, &row_width);
    if (rc != RSQL_OK) return rc;
    if (current->slot >= g_row_page[RSQL_ROW_CAPACITY] ||
        !slot_used(current->slot)) return RSQL_ERR_NOT_FOUND;
    page = current->page;
    slot = (rsql_u8)(current->slot + 1u);
    for (;;) {
        while (slot < g_row_page[RSQL_ROW_CAPACITY]) {
            if (slot_used(slot)) {
                row_id_out->page = page;
                row_id_out->slot = slot;
                return RSQL_OK;
            }
            ++slot;
        }
        next = rsql_get_u16(&g_row_page[RSQL_ROW_NEXT]);
        if (next == RSQL_PAGE_NONE) return RSQL_ERR_NOT_FOUND;
        page = next;
        rc = load_row_page(page, row_width);
        if (rc != RSQL_OK) return rc;
        slot = 0u;
    }
}

#include <string.h>

#include "rsql_catalog.h"
#include "rsql_enum.h"
#include "rsql_errors.h"
#include "rsql_page.h"
#include "rsql_reu.h"
#include "rsql_scratch.h"
#include "storage_layout.h"

#define ENUM_WIDTH 5u
#define ENUM_ID 6u
#define ENUM_NEXT 8u
#define ENUM_FIRST_MEMBERS 10u
#define ENUM_MEMBER_COUNT 12u
#define ENUM_NAME_LENGTH 14u
#define ENUM_NAME 15u

#define MEMBER_PAGE_COUNT 5u
#define MEMBER_PAGE_NEXT 6u
#define MEMBER_PAGE_ENTRIES 8u
#define MEMBER_ENTRY_BYTES 18u
#define MEMBER_PAGE_CAPACITY 13u
#define MEMBER_VALUE 0u
#define MEMBER_NAME_LENGTH 2u
#define MEMBER_NAME 3u

#define g_enum_page g_rsql_meta_page0
#define g_member_page g_rsql_meta_page0

static rsql_u8 fold(rsql_u8 value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return value;
}

static rsql_u8 text_length(const char* text, rsql_u8 maximum,
                           rsql_u8* length_out) {
    rsql_u8 length = 0u;
    if (!text || !length_out) return RSQL_ERR_INVALID_ARGUMENT;
    while (text[length] != 0) {
        if (length == maximum) return RSQL_ERR_SCHEMA_LIMIT;
        ++length;
    }
    if (length == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    *length_out = length;
    return RSQL_OK;
}

static rsql_u8 equal_name(const char* wanted, const rsql_u8* stored,
                          rsql_u8 length) {
    rsql_u8 i;
    if (!wanted) return 0u;
    for (i = 0u; i < length; ++i) {
        if (wanted[i] == 0 || fold((rsql_u8)wanted[i]) != fold(stored[i])) {
            return 0u;
        }
    }
    return wanted[length] == 0;
}

static rsql_u8 valid_enum_page(void) {
    return g_enum_page[0] == 'R' && g_enum_page[1] == 'E' &&
           g_enum_page[2] == 'N' && g_enum_page[3] == 'T' &&
           g_enum_page[4] == RSQL_STORAGE_VERSION &&
           g_enum_page[RSQL_PAGE_CHECKSUM_OFFSET] == rsql_page_checksum(g_enum_page);
}

static rsql_u8 valid_member_page(void) {
    return g_member_page[0] == 'R' && g_member_page[1] == 'E' &&
           g_member_page[2] == 'M' && g_member_page[3] == 'B' &&
           g_member_page[4] == RSQL_STORAGE_VERSION &&
           g_member_page[MEMBER_PAGE_COUNT] <= MEMBER_PAGE_CAPACITY &&
           g_member_page[RSQL_PAGE_CHECKSUM_OFFSET] ==
               rsql_page_checksum(g_member_page);
}

static rsql_u8 load_enum(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_enum_page,
                               sizeof(g_enum_page));
    if (rc != RSQL_OK) return rc;
    return valid_enum_page() ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 load_members(rsql_u16 page) {
    rsql_u8 rc = rsql_reu_read(rsql_reu_page_address(page), g_member_page,
                               sizeof(g_member_page));
    if (rc != RSQL_OK) return rc;
    return valid_member_page() ? RSQL_OK : RSQL_ERR_CORRUPT_STORAGE;
}

static rsql_u8 find_enum_id(rsql_u16 enum_id, RsqlEnumInfo* info_out) {
    rsql_u16 page;
    rsql_u16 next_id;
    rsql_u8 length;
    rsql_u8 rc = rsql_catalog_enum_state(&page, &next_id);
    (void)next_id;
    if (rc != RSQL_OK) return rc;
    while (page != RSQL_PAGE_NONE) {
        rc = load_enum(page);
        if (rc != RSQL_OK) return rc;
        if (g_enum_page[RSQL_ENUM_FLAGS] == 0u &&
            rsql_get_u16(&g_enum_page[ENUM_ID]) == enum_id) {
            if (info_out) {
                length = g_enum_page[ENUM_NAME_LENGTH];
                info_out->enum_id = enum_id;
                info_out->enum_page = page;
                info_out->member_count = rsql_get_u16(
                    &g_enum_page[ENUM_MEMBER_COUNT]);
                info_out->width = g_enum_page[ENUM_WIDTH];
                info_out->name_length = length;
                memcpy(info_out->name, &g_enum_page[ENUM_NAME], length);
                info_out->name[length] = 0;
            }
            return RSQL_OK;
        }
        page = rsql_get_u16(&g_enum_page[ENUM_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_enum_find(const char* name, RsqlEnumInfo* info_out) {
    rsql_u16 page;
    rsql_u16 next_id;
    rsql_u8 rc;
    if (!name || !info_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = rsql_catalog_enum_state(&page, &next_id);
    (void)next_id;
    if (rc != RSQL_OK) return rc;
    while (page != RSQL_PAGE_NONE) {
        rc = load_enum(page);
        if (rc != RSQL_OK) return rc;
        if (equal_name(name, &g_enum_page[ENUM_NAME],
                       g_enum_page[ENUM_NAME_LENGTH])) {
            return find_enum_id(rsql_get_u16(&g_enum_page[ENUM_ID]), info_out);
        }
        page = rsql_get_u16(&g_enum_page[ENUM_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

static rsql_u8 free_member_chain(rsql_u16 first) {
    rsql_u16 page = first;
    rsql_u16 next;
    rsql_u8 rc;
    while (page != RSQL_PAGE_NONE) {
        rc = load_members(page);
        if (rc != RSQL_OK) return rc;
        next = rsql_get_u16(&g_member_page[MEMBER_PAGE_NEXT]);
        rc = rsql_page_free(page);
        if (rc != RSQL_OK) return rc;
        page = next;
    }
    return RSQL_OK;
}

static rsql_u8 create_member_pages(const RsqlCreateEnumRequest* request,
                                   rsql_u16* first_out) {
    rsql_u16 first = RSQL_PAGE_NONE;
    rsql_u16 previous = RSQL_PAGE_NONE;
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 member = 0u;
    rsql_u8 count;
    rsql_u8 slot;
    rsql_u8 length;
    rsql_u8 rc;
    while (member < request->member_count) {
        rc = rsql_page_allocate(&page);
        if (rc != RSQL_OK) return rc;
        memset(g_member_page, 0, sizeof(g_member_page));
        g_member_page[0] = 'R';
        g_member_page[1] = 'E';
        g_member_page[2] = 'M';
        g_member_page[3] = 'B';
        g_member_page[4] = RSQL_STORAGE_VERSION;
        rsql_put_u16(&g_member_page[MEMBER_PAGE_NEXT], RSQL_PAGE_NONE);
        count = (rsql_u8)(request->member_count - member);
        if (count > MEMBER_PAGE_CAPACITY) count = MEMBER_PAGE_CAPACITY;
        g_member_page[MEMBER_PAGE_COUNT] = count;
        for (slot = 0u; slot < count; ++slot, ++member) {
            base = (rsql_u16)(MEMBER_PAGE_ENTRIES +
                              (rsql_u16)slot * MEMBER_ENTRY_BYTES);
            text_length(request->members[member].name,
                        RSQL_ENUM_MEMBER_NAME_MAX, &length);
            rsql_put_u16(&g_member_page[base + MEMBER_VALUE],
                         request->members[member].value);
            g_member_page[base + MEMBER_NAME_LENGTH] = length;
            memcpy(&g_member_page[base + MEMBER_NAME],
                   request->members[member].name, length);
        }
        g_member_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_member_page);
        rc = rsql_reu_write(rsql_reu_page_address(page), g_member_page,
                            sizeof(g_member_page));
        if (rc != RSQL_OK) return rc;
        if (first == RSQL_PAGE_NONE) first = page;
        if (previous != RSQL_PAGE_NONE) {
            rc = load_members(previous);
            if (rc != RSQL_OK) return rc;
            rsql_put_u16(&g_member_page[MEMBER_PAGE_NEXT], page);
            g_member_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_member_page);
            rc = rsql_reu_write(rsql_reu_page_address(previous), g_member_page,
                                sizeof(g_member_page));
            if (rc != RSQL_OK) return rc;
        }
        previous = page;
    }
    *first_out = first;
    return RSQL_OK;
}

rsql_u8 rsql_enum_create(RsqlCreateEnumRequest* request) {
    RsqlEnumInfo existing;
    rsql_u16 first_enum;
    rsql_u16 enum_id;
    rsql_u16 enum_page;
    rsql_u16 member_page;
    rsql_u8 name_length;
    rsql_u8 member_name_length;
    rsql_u8 i;
    rsql_u8 j;
    rsql_u8 rc;
    if (!request || !request->name || !request->members ||
        request->member_count == 0u ||
        (request->width != 1u && request->width != 2u)) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    rc = text_length(request->name, RSQL_ENUM_NAME_MAX, &name_length);
    if (rc != RSQL_OK) return rc;
    rc = rsql_enum_find(request->name, &existing);
    if (rc == RSQL_OK) return RSQL_ERR_ALREADY_EXISTS;
    if (rc != RSQL_ERR_NOT_FOUND) return rc;
    for (i = 0u; i < request->member_count; ++i) {
        rc = text_length(request->members[i].name, RSQL_ENUM_MEMBER_NAME_MAX,
                         &member_name_length);
        if (rc != RSQL_OK) return rc;
        if (request->width == 1u && request->members[i].value > 255u) {
            return RSQL_ERR_TYPE_MISMATCH;
        }
        for (j = 0u; j < i; ++j) {
            if (request->members[j].value == request->members[i].value ||
                equal_name(request->members[i].name,
                           (const rsql_u8*)request->members[j].name,
                           (rsql_u8)strlen(request->members[j].name))) {
                return RSQL_ERR_ALREADY_EXISTS;
            }
        }
    }
    rc = rsql_catalog_enum_state(&first_enum, &enum_id);
    if (rc != RSQL_OK || enum_id == 0u || enum_id == RSQL_PAGE_NONE) {
        return rc != RSQL_OK ? rc : RSQL_ERR_SCHEMA_LIMIT;
    }
    rc = create_member_pages(request, &member_page);
    if (rc != RSQL_OK) return rc;
    rc = rsql_page_allocate(&enum_page);
    if (rc != RSQL_OK) {
        free_member_chain(member_page);
        return rc;
    }
    memset(g_enum_page, 0, sizeof(g_enum_page));
    g_enum_page[0] = 'R';
    g_enum_page[1] = 'E';
    g_enum_page[2] = 'N';
    g_enum_page[3] = 'T';
    g_enum_page[4] = RSQL_STORAGE_VERSION;
    g_enum_page[ENUM_WIDTH] = request->width;
    rsql_put_u16(&g_enum_page[ENUM_ID], enum_id);
    rsql_put_u16(&g_enum_page[ENUM_NEXT], first_enum);
    rsql_put_u16(&g_enum_page[ENUM_FIRST_MEMBERS], member_page);
    rsql_put_u16(&g_enum_page[ENUM_MEMBER_COUNT], request->member_count);
    g_enum_page[ENUM_NAME_LENGTH] = name_length;
    memcpy(&g_enum_page[ENUM_NAME], request->name, name_length);
    g_enum_page[RSQL_PAGE_CHECKSUM_OFFSET] = rsql_page_checksum(g_enum_page);
    rc = rsql_reu_write(rsql_reu_page_address(enum_page), g_enum_page,
                        sizeof(g_enum_page));
    if (rc == RSQL_OK) rc = rsql_catalog_link_enum(enum_page, enum_id + 1u);
    if (rc == RSQL_OK) request->enum_id = enum_id;
    return rc;
}

rsql_u8 rsql_enum_member_value(rsql_u16 enum_id, const char* member,
                               rsql_u16* value_out) {
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 count;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!member || !value_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = find_enum_id(enum_id, 0);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_enum_page[ENUM_FIRST_MEMBERS]);
    while (page != RSQL_PAGE_NONE) {
        rc = load_members(page);
        if (rc != RSQL_OK) return rc;
        count = g_member_page[MEMBER_PAGE_COUNT];
        for (slot = 0u; slot < count; ++slot) {
            base = (rsql_u16)(MEMBER_PAGE_ENTRIES +
                              (rsql_u16)slot * MEMBER_ENTRY_BYTES);
            if (equal_name(member, &g_member_page[base + MEMBER_NAME],
                           g_member_page[base + MEMBER_NAME_LENGTH])) {
                *value_out = rsql_get_u16(&g_member_page[base + MEMBER_VALUE]);
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_member_page[MEMBER_PAGE_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

rsql_u8 rsql_enum_member_name(rsql_u16 enum_id, rsql_u16 value,
                              char* destination, rsql_u8 capacity) {
    rsql_u16 page;
    rsql_u16 base;
    rsql_u8 count;
    rsql_u8 length;
    rsql_u8 slot;
    rsql_u8 rc;
    if (!destination || capacity == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    rc = find_enum_id(enum_id, 0);
    if (rc != RSQL_OK) return rc;
    page = rsql_get_u16(&g_enum_page[ENUM_FIRST_MEMBERS]);
    while (page != RSQL_PAGE_NONE) {
        rc = load_members(page);
        if (rc != RSQL_OK) return rc;
        count = g_member_page[MEMBER_PAGE_COUNT];
        for (slot = 0u; slot < count; ++slot) {
            base = (rsql_u16)(MEMBER_PAGE_ENTRIES +
                              (rsql_u16)slot * MEMBER_ENTRY_BYTES);
            if (rsql_get_u16(&g_member_page[base + MEMBER_VALUE]) == value) {
                length = g_member_page[base + MEMBER_NAME_LENGTH];
                if (capacity <= length) return RSQL_ERR_BUFFER_TOO_SMALL;
                memcpy(destination, &g_member_page[base + MEMBER_NAME], length);
                destination[length] = 0;
                return RSQL_OK;
            }
        }
        page = rsql_get_u16(&g_member_page[MEMBER_PAGE_NEXT]);
    }
    return RSQL_ERR_NOT_FOUND;
}

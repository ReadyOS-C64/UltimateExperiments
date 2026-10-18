#include "rsql_errors.h"
#include "rsql_journal.h"
#include "rsql_reu.h"

#define REU_STATUS      (*(volatile rsql_u8*)0xDF00)
#define REU_COMMAND     (*(volatile rsql_u8*)0xDF01)
#define REU_C64_LO      (*(volatile rsql_u8*)0xDF02)
#define REU_C64_HI      (*(volatile rsql_u8*)0xDF03)
#define REU_ADDR_LO     (*(volatile rsql_u8*)0xDF04)
#define REU_ADDR_HI     (*(volatile rsql_u8*)0xDF05)
#define REU_BANK        (*(volatile rsql_u8*)0xDF06)
#define REU_LEN_LO      (*(volatile rsql_u8*)0xDF07)
#define REU_LEN_HI      (*(volatile rsql_u8*)0xDF08)
#define REU_IRQ_MASK    (*(volatile rsql_u8*)0xDF09)
#define REU_ADDR_CTRL   (*(volatile rsql_u8*)0xDF0A)

#define REU_CMD_STASH   0x90u
#define REU_CMD_FETCH   0x91u
#define REU_CMD_VERIFY  0x93u
#define REU_STATUS_FAULT 0x20u

static rsql_u16 g_reu_size_kib;
static rsql_u8 g_probe_byte;
static rsql_u8 g_journal_active;
static rsql_u8 g_journal_count;
static rsql_u8 g_journal_write_count;
static rsql_u8 g_journal_fail_after = 0xFFu;
static rsql_u8 g_journal_fail_transaction;
static rsql_u8 g_journal_fail_write;
static rsql_u16 g_journal_pages[RSQL_REU_JOURNAL_PAGES];
static rsql_u8 g_journal_buffer[RSQL_REU_PAGE_SIZE];
/* Keep this at file scope. With code and rodata sharing a segment, cc65 can
 * otherwise place a function-local static object at the exported entry. */
static const rsql_u16 PROBE_CANDIDATES_KIB[] = {
    512u, 1024u, 2048u, 4096u, 8192u
};


static rsql_u8 valid_size(rsql_u16 size_kib) {
    return (size_kib == 512u || size_kib == 1024u ||
            size_kib == 2048u || size_kib == 4096u ||
            size_kib == 8192u || size_kib == 16384u) ? 1u : 0u;
}

static rsql_u8 transfer(rsql_u8 command, unsigned long address,
                        const void* c64_address, rsql_u16 length) {
    unsigned int ptr;
    rsql_u8 status;

    if (!c64_address || length == 0u) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    ptr = (unsigned int)c64_address;
    REU_C64_LO = (rsql_u8)(ptr & 0xFFu);
    REU_C64_HI = (rsql_u8)(ptr >> 8u);
    REU_ADDR_LO = (rsql_u8)(address & 0xFFul);
    REU_ADDR_HI = (rsql_u8)((address >> 8u) & 0xFFul);
    REU_BANK = (rsql_u8)((address >> 16u) & 0xFFul);
    REU_LEN_LO = (rsql_u8)(length & 0xFFu);
    REU_LEN_HI = (rsql_u8)(length >> 8u);
    REU_IRQ_MASK = 0u;
    REU_ADDR_CTRL = 0u;
    REU_COMMAND = command;
    status = REU_STATUS;
    if (command == REU_CMD_VERIFY && (status & REU_STATUS_FAULT) != 0u) {
        return RSQL_ERR_CORRUPT_STORAGE;
    }
    return RSQL_OK;
}

rsql_u8 rsql_reu_init(const RsqlReuConfig* config) {
    rsql_u16 detected;
    rsql_u8 rc;
    if (!config) {
        return RSQL_ERR_INVALID_ARGUMENT;
    }
    if (config->probe_hardware) {
        rc = rsql_reu_probe(&detected);
        if (rc != RSQL_OK) return rc;
        g_reu_size_kib = detected;
        return RSQL_OK;
    }
    if (!valid_size(config->size_kib)) return RSQL_ERR_REU_TOO_SMALL;
    g_reu_size_kib = config->size_kib;
    return RSQL_OK;
}

rsql_u8 rsql_reu_probe(rsql_u16* size_kib_out) {
    rsql_u8 original_zero;
    rsql_u8 original_candidate;
    rsql_u8 observed;
    rsql_u8 rc;
    rsql_u8 i;
    unsigned long candidate_address;

    if (!size_kib_out) return RSQL_ERR_INVALID_ARGUMENT;
    rc = rsql_reu_read(0x0000F7ul, &original_zero, 1u);
    if (rc != RSQL_OK) return RSQL_ERR_REU_NOT_FOUND;
    g_probe_byte = 0x5Au;
    rc = rsql_reu_write(0x0000F7ul, &g_probe_byte, 1u);
    if (rc != RSQL_OK) return RSQL_ERR_REU_NOT_FOUND;
    observed = 0u;
    rc = rsql_reu_read(0x0000F7ul, &observed, 1u);
    if (rc != RSQL_OK || observed != 0x5Au) {
        return RSQL_ERR_REU_NOT_FOUND;
    }
    g_probe_byte = 0xA5u;
    rsql_reu_write(0x0000F7ul, &g_probe_byte, 1u);
    observed = 0u;
    rsql_reu_read(0x0000F7ul, &observed, 1u);
    rsql_reu_write(0x0000F7ul, &original_zero, 1u);
    if (observed != 0xA5u) return RSQL_ERR_REU_NOT_FOUND;

    for (i = 0u; i < (rsql_u8)(sizeof(PROBE_CANDIDATES_KIB) /
                               sizeof(PROBE_CANDIDATES_KIB[0])); ++i) {
        candidate_address = ((unsigned long)PROBE_CANDIDATES_KIB[i]) << 10u;
        rc = rsql_reu_read(candidate_address + 0xF7ul, &original_candidate, 1u);
        if (rc != RSQL_OK) return RSQL_ERR_REU_NOT_FOUND;
        g_probe_byte = 0x35u;
        rsql_reu_write(0x0000F7ul, &g_probe_byte, 1u);
        g_probe_byte = 0xCAu;
        rsql_reu_write(candidate_address + 0xF7ul, &g_probe_byte, 1u);
        observed = 0u;
        rsql_reu_read(0x0000F7ul, &observed, 1u);
        if (observed == 0xCAu) {
            rsql_reu_write(0x0000F7ul, &original_zero, 1u);
            *size_kib_out = PROBE_CANDIDATES_KIB[i];
            return RSQL_OK;
        }
        rsql_reu_write(0x0000F7ul, &original_zero, 1u);
        rsql_reu_write(candidate_address + 0xF7ul, &original_candidate, 1u);
    }
    *size_kib_out = 16384u;
    return RSQL_OK;
}

rsql_u16 rsql_reu_size_kib(void) {
    return g_reu_size_kib;
}

unsigned long rsql_reu_page_count(void) {
    return ((unsigned long)g_reu_size_kib) << 2u;
}

rsql_u8 rsql_reu_read(unsigned long address, void* destination, rsql_u16 length) {
    return transfer(REU_CMD_FETCH, address, destination, length);
}

static unsigned long journal_base_page(void) {
    return rsql_reu_page_count() - RSQL_REU_OVERLAY_PAGES -
           RSQL_REU_JOURNAL_PAGES;
}

static rsql_u8 journal_log_page(rsql_u16 page) {
    unsigned long slot_page;
    rsql_u8 index;
    rsql_u8 rc;
    for (index = 0u; index < g_journal_count; ++index) {
        if (g_journal_pages[index] == page) return RSQL_OK;
    }
    if (g_journal_count >= RSQL_REU_JOURNAL_PAGES) {
        return RSQL_ERR_JOURNAL_FULL;
    }
    rc = transfer(REU_CMD_FETCH, rsql_reu_page_address(page),
                  g_journal_buffer, sizeof(g_journal_buffer));
    if (rc != RSQL_OK) return rc;
    slot_page = journal_base_page() + g_journal_count;
    rc = transfer(REU_CMD_STASH, slot_page << 8u, g_journal_buffer,
                  sizeof(g_journal_buffer));
    if (rc != RSQL_OK) return rc;
    g_journal_pages[g_journal_count++] = page;
    return RSQL_OK;
}

rsql_u8 rsql_reu_write(unsigned long address, const void* source, rsql_u16 length) {
    unsigned long first_page;
    unsigned long last_page;
    unsigned long page;
    rsql_u8 rc;
    if (!source || length == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    if (g_journal_active) {
        first_page = address >> 8u;
        last_page = (address + length - 1u) >> 8u;
        for (page = first_page; page <= last_page; ++page) {
            rc = journal_log_page((rsql_u16)page);
            if (rc != RSQL_OK) return rc;
        }
        if (g_journal_write_count == g_journal_fail_after) {
            return RSQL_ERR_IO;
        }
    }
    rc = transfer(REU_CMD_STASH, address, source, length);
    if (rc == RSQL_OK && g_journal_active) ++g_journal_write_count;
    return rc;
}

rsql_u8 rsql_reu_compare(unsigned long address, const void* source, rsql_u16 length) {
    return transfer(REU_CMD_VERIFY, address, source, length);
}

rsql_u8 rsql_reu_read_byte(unsigned long address, rsql_u8* value) {
    return rsql_reu_read(address, value, 1u);
}

rsql_u8 rsql_reu_write_byte(unsigned long address, rsql_u8 value) {
    return rsql_reu_write(address, &value, 1u);
}

unsigned long rsql_reu_page_address(rsql_u16 page) {
    return ((unsigned long)page) << 8u;
}

rsql_u8 rsql_journal_begin(void) {
    if (g_journal_active) return RSQL_ERR_INTERNAL;
    g_journal_count = 0u;
    g_journal_write_count = 0u;
    if (g_journal_fail_transaction != 0u) {
        --g_journal_fail_transaction;
        g_journal_fail_after = g_journal_fail_transaction == 0u
            ? g_journal_fail_write : 0xFFu;
    }
    g_journal_active = 1u;
    return RSQL_OK;
}

rsql_u8 rsql_journal_commit(void) {
    if (!g_journal_active) return RSQL_ERR_INTERNAL;
    g_journal_active = 0u;
    g_journal_count = 0u;
    g_journal_fail_after = 0xFFu;
    return RSQL_OK;
}

rsql_u8 rsql_journal_rollback(void) {
    unsigned long slot_page;
    rsql_u16 page;
    rsql_u8 rc;
    g_journal_active = 0u;
    g_journal_fail_after = 0xFFu;
    while (g_journal_count != 0u) {
        --g_journal_count;
        page = g_journal_pages[g_journal_count];
        slot_page = journal_base_page() + g_journal_count;
        rc = transfer(REU_CMD_FETCH, slot_page << 8u, g_journal_buffer,
                      sizeof(g_journal_buffer));
        if (rc != RSQL_OK) return rc;
        rc = transfer(REU_CMD_STASH, rsql_reu_page_address(page),
                      g_journal_buffer, sizeof(g_journal_buffer));
        if (rc != RSQL_OK) return rc;
    }
    return RSQL_OK;
}

void __fastcall__ rsql_journal_test_fail_after(rsql_u8 write_index) {
    g_journal_fail_transaction = 0u;
    g_journal_fail_after = write_index;
}

void rsql_journal_test_fail_transaction(rsql_u8 transaction_index,
                                        rsql_u8 write_index) {
    g_journal_fail_transaction = transaction_index;
    g_journal_fail_write = write_index;
    g_journal_fail_after = 0xFFu;
}

rsql_u8 rsql_journal_test_write_count(void) {
    return g_journal_write_count;
}

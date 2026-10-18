#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_journal.h"

static unsigned char storage[1024];
static int fails;

static unsigned char write_journal(unsigned int offset, const void *data,
                                   unsigned int length) {
    if (offset > sizeof(storage) || length > sizeof(storage) - offset) return 0u;
    memcpy(storage + offset, data, length);
    return 1u;
}

static unsigned char read_journal(unsigned int offset, void *data,
                                  unsigned int length) {
    if (offset > sizeof(storage) || length > sizeof(storage) - offset) return 0u;
    memcpy(data, storage + offset, length);
    return 1u;
}

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL journal %s\n", message);
        ++fails;
    }
}

int main(void) {
    ReadyFsJournal journal;
    ReadyFsJournalRecord record;
    ReadyFsJournalCall call;
    char stem[256];
    unsigned int cursor;
    unsigned int next;
    unsigned int used;

    memset(storage, 0xA5, sizeof(storage));
    readyfs_journal_init(&journal, 2u, sizeof(storage), write_journal,
                         read_journal);
    check(journal.open && journal.used == 16u &&
          memcmp(storage, "RFJ1", 4u) == 0 && storage[4] == 1u,
          "versioned header");
    check(readyfs_journal_first(&journal) == RF_JOURNAL_END,
          "empty first");
    check(readyfs_journal_append(&journal, 1u, 0u, 3u, 2u, 42u, 9u,
                                 "one"), "append success");
    check(readyfs_journal_append(&journal, 2u, 7u, 4u, 1u, 82u, 22u,
                                 "one/file.prg"), "append failure");
    check(journal.count == 2u && journal.completed == 1u &&
          journal.failed == 1u, "result counters");
    cursor = readyfs_journal_first(&journal);
    check(readyfs_journal_read(&journal, cursor, &record, stem, sizeof(stem),
                               &next) && record.action == 1u &&
          record.result == 0u && record.backend == 3u &&
          record.kind == 2u && record.detail == 42u &&
          record.plan_offset == 9u && strcmp(stem, "one") == 0,
          "read first record");
    cursor = next;
    check(readyfs_journal_read(&journal, cursor, &record, stem, sizeof(stem),
                               &next) && record.action == 2u &&
          record.result == 7u && record.detail == 82u &&
          strcmp(stem, "one/file.prg") == 0 && next == RF_JOURNAL_END,
          "read second record");
    check(readyfs_journal_finish(&journal) && !journal.open && storage[6] == 0u,
          "finish persists terminal state");
    check(!readyfs_journal_append(&journal, 1u, 0u, 0u, 0u, 0u, 0u, "late"),
          "closed journal rejects append");

    readyfs_journal_init(&journal, 1u, 30u, write_journal, read_journal);
    check(readyfs_journal_append(&journal, 1u, 0u, 0u, 1u, 0u, 0u, "abc"),
          "exact small append");
    used = journal.used;
    check(!readyfs_journal_append(&journal, 2u, 0u, 0u, 1u, 0u, 0u, "x") &&
          journal.overflow && journal.used == used && journal.count == 1u,
          "overflow is pre-commit");

    memset(&call, 0, sizeof(call));
    call.operation = RF_JOURNAL_CALL_READ;
    call.journal = &journal;
    call.offset = readyfs_journal_first(&journal);
    call.record = &record;
    call.output = stem;
    call.output_capacity = sizeof(stem);
    check(readyfs_journal_dispatch(&call) && strcmp(stem, "abc") == 0,
          "overlay dispatcher read");
    check(readyfs_journal_selftest(write_journal, read_journal,
                                   sizeof(storage)), "portable selftest");

    if (fails != 0) return 1;
    puts("readyfs journal tests passed");
    return 0;
}

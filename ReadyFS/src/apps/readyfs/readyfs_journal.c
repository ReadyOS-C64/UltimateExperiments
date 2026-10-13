#include "readyfs_journal.h"

#include <string.h>

#ifdef __CC65__
#include "readyfs_reu.h"
#endif

#define RF_JOURNAL_RECORD_BYTES 10u

/* Journal commands are single-threaded. Keep serialization buffers out of
 * cc65's software stack because append persists a header after its record. */
static unsigned char journal_header_data[RF_JOURNAL_HEADER_BYTES];
static unsigned char journal_record_data[RF_JOURNAL_RECORD_BYTES];
static ReadyFsJournalWrite journal_write_fn;
static ReadyFsJournalRead journal_read_fn;

static void put_u16(unsigned char *data, unsigned int value) {
    data[0] = (unsigned char)(value & 0xFFu);
    data[1] = (unsigned char)(value >> 8u);
}

static unsigned int get_u16(const unsigned char *data) {
    return (unsigned int)(data[0] | ((unsigned int)data[1] << 8u));
}

/* cc65 can miscompile a multi-argument indirect call made directly through a
 * function-pointer member of a struct. Load the callback first, then call it.
 * The plan overlay uses the same callback ABI and all journal I/O stays behind
 * these two helpers. */
static unsigned char call_write(const ReadyFsJournal *journal,
                                unsigned int offset, const void *data,
                                unsigned int length) {
#ifdef __CC65__
    (void)journal;
    if (offset > RF_REU_JOURNAL_BYTES ||
        length > (unsigned int)(RF_REU_JOURNAL_BYTES - offset)) return 0u;
    return readyfs_reu_session_store((unsigned int)(RF_REU_JOURNAL_OFF +
                                     offset), data, length);
#else
    ReadyFsJournalWrite write_fn;

    (void)journal;
    write_fn = journal_write_fn;
    return write_fn != 0 && write_fn(offset, data, length);
#endif
}

static unsigned char call_read(const ReadyFsJournal *journal,
                               unsigned int offset, void *data,
                               unsigned int length) {
#ifdef __CC65__
    (void)journal;
    if (offset > RF_REU_JOURNAL_BYTES ||
        length > (unsigned int)(RF_REU_JOURNAL_BYTES - offset)) return 0u;
    return readyfs_reu_session_fetch((unsigned int)(RF_REU_JOURNAL_OFF +
                                     offset), data, length);
#else
    ReadyFsJournalRead read_fn;

    (void)journal;
    read_fn = journal_read_fn;
    return read_fn != 0 && read_fn(offset, data, length);
#endif
}

static unsigned char write_header(const ReadyFsJournal *journal) {
    /* RFJ1 is a host-readable wire format. Use numeric ASCII bytes because
     * cc65 character literals compile to PETSCII. */
    journal_header_data[0] = 0x52u;
    journal_header_data[1] = 0x46u;
    journal_header_data[2] = 0x4Au;
    journal_header_data[3] = 0x31u;
    journal_header_data[4] = RF_JOURNAL_VERSION;
    journal_header_data[5] = journal->mode;
    journal_header_data[6] = journal->open;
    journal_header_data[7] = journal->overflow;
    put_u16(journal_header_data + 8u, journal->used);
    put_u16(journal_header_data + 10u, journal->count);
    put_u16(journal_header_data + 12u, journal->completed);
    put_u16(journal_header_data + 14u, journal->failed);
    return call_write(journal, 0u, journal_header_data,
                      RF_JOURNAL_HEADER_BYTES);
}

unsigned int readyfs_journal_abi(void) { return RF_JOURNAL_ABI; }

void readyfs_journal_init(ReadyFsJournal *journal, unsigned char mode,
                          unsigned int capacity,
                          ReadyFsJournalWrite write_fn,
                          ReadyFsJournalRead read_fn) {
    memset(journal, 0, sizeof(*journal));
    journal->write = write_fn;
    journal->read = read_fn;
    journal_write_fn = write_fn;
    journal_read_fn = read_fn;
    journal->capacity = capacity;
    journal->used = RF_JOURNAL_HEADER_BYTES;
    journal->mode = mode;
    journal->open = 1u;
    if (write_fn == 0 || capacity < RF_JOURNAL_HEADER_BYTES ||
        !write_header(journal)) journal->open = 0u;
}

unsigned char readyfs_journal_append(ReadyFsJournal *journal,
                                     unsigned char action,
                                     unsigned char result,
                                     unsigned char backend,
                                     unsigned char kind,
                                     unsigned int detail,
                                     unsigned int plan_offset,
                                     const char *stem) {
    unsigned int length;
    unsigned int record_bytes;

    if (journal == 0 || !journal->open || journal->write == 0 || stem == 0) {
        return 0u;
    }
    length = strlen(stem);
    if (length > 255u) return 0u;
    record_bytes = (unsigned int)(RF_JOURNAL_RECORD_BYTES + length + 1u);
    if (journal->used > journal->capacity ||
        record_bytes > (unsigned int)(journal->capacity - journal->used)) {
        journal->overflow = 1u;
        (void)write_header(journal);
        return 0u;
    }
    journal_record_data[0] = action;
    journal_record_data[1] = result;
    journal_record_data[2] = backend;
    journal_record_data[3] = kind;
    put_u16(journal_record_data + 4u, detail);
    put_u16(journal_record_data + 6u, plan_offset);
    put_u16(journal_record_data + 8u, length);
    if (!call_write(journal, journal->used, journal_record_data,
                    RF_JOURNAL_RECORD_BYTES)) return 0u;
    if (!call_write(journal, (unsigned int)(journal->used +
                    RF_JOURNAL_RECORD_BYTES), stem,
                    (unsigned int)(length + 1u))) return 0u;
    journal->used = (unsigned int)(journal->used + record_bytes);
    ++journal->count;
    if (result == 0u) ++journal->completed;
    else ++journal->failed;
    if (!write_header(journal)) {
        journal->used = (unsigned int)(journal->used - record_bytes);
        --journal->count;
        if (result == 0u) --journal->completed;
        else --journal->failed;
        return 0u;
    }
    return 1u;
}

unsigned char readyfs_journal_finish(ReadyFsJournal *journal) {
    if (journal == 0 || !journal->open || journal->write == 0) return 0u;
    journal->open = 0u;
    if (!write_header(journal)) {
        journal->open = 1u;
        return 0u;
    }
    return 1u;
}

unsigned char readyfs_journal_read(const ReadyFsJournal *journal,
                                   unsigned int offset,
                                   ReadyFsJournalRecord *record, char *stem,
                                   unsigned int stem_capacity,
                                   unsigned int *next) {
    unsigned int length;
    unsigned int end;

    if (journal == 0 || journal->read == 0 || record == 0 || stem == 0 ||
        next == 0 || offset < RF_JOURNAL_HEADER_BYTES ||
        offset >= journal->used) return 0u;
    if (!call_read(journal, offset, journal_record_data,
                   RF_JOURNAL_RECORD_BYTES)) return 0u;
    length = get_u16(journal_record_data + 8u);
    end = (unsigned int)(offset + RF_JOURNAL_RECORD_BYTES + length + 1u);
    if (length >= stem_capacity || end <= offset || end > journal->used) {
        return 0u;
    }
    if (!call_read(journal, (unsigned int)(offset + RF_JOURNAL_RECORD_BYTES),
                   stem, (unsigned int)(length + 1u))) return 0u;
    if (stem[length] != 0) return 0u;
    record->action = journal_record_data[0];
    record->result = journal_record_data[1];
    record->backend = journal_record_data[2];
    record->kind = journal_record_data[3];
    record->detail = get_u16(journal_record_data + 4u);
    record->plan_offset = get_u16(journal_record_data + 6u);
    record->stem_len = length;
    *next = end == journal->used ? RF_JOURNAL_END : end;
    return 1u;
}

unsigned int readyfs_journal_first(const ReadyFsJournal *journal) {
    return journal != 0 && journal->count != 0u ? RF_JOURNAL_HEADER_BYTES :
                                                 RF_JOURNAL_END;
}

unsigned char readyfs_journal_dispatch(ReadyFsJournalCall *call) {
#ifdef __CC65__
    if (call != 0 && call->operation == RF_JOURNAL_CALL_ONE) {
        return readyfs_journal_one((ReadyFsJournalOne *)call);
    }
#endif
    if (call == 0 || call->journal == 0) return 0u;
    if (call->operation == RF_JOURNAL_CALL_INIT) {
        readyfs_journal_init(call->journal, call->mode, call->capacity,
                             call->write, call->read);
        call->call_result = call->journal->open;
    } else if (call->operation == RF_JOURNAL_CALL_APPEND) {
        call->call_result = readyfs_journal_append(
            call->journal, call->action, call->result, call->backend,
            call->kind, call->detail, call->plan_offset, call->stem);
    } else if (call->operation == RF_JOURNAL_CALL_READ) {
        call->call_result = readyfs_journal_read(
            call->journal, call->offset, call->record, call->output,
            call->output_capacity, &call->next);
    } else if (call->operation == RF_JOURNAL_CALL_FINISH) {
        call->call_result = readyfs_journal_finish(call->journal);
    } else call->call_result = 0u;
    return call->call_result;
}

#ifdef __CC65__
static ReadyFsJournal one_journal;

/* Compact C64-only gateway for recording one completed backend action. It
 * keeps the bulky journal setup in the roomy help/journal sidecar. */
unsigned char readyfs_journal_one(ReadyFsJournalOne *call) {
    if (call == 0) return 0u;
    readyfs_journal_init(&one_journal, 1u, RF_REU_JOURNAL_BYTES,
                         readyfs_reu_session_store,
                         readyfs_reu_session_fetch);
    return one_journal.open &&
        readyfs_journal_append(&one_journal, call->action, call->result,
                               call->backend, call->kind, call->detail,
                               call->plan_offset, call->stem) &&
        readyfs_journal_finish(&one_journal);
}
#endif

static ReadyFsJournal selftest_journal;
static ReadyFsJournalRecord selftest_record;
static char selftest_stem[3];
static unsigned int selftest_next;
#ifndef __CC65__
static unsigned char selftest_probe;
#endif

unsigned char readyfs_journal_selftest(ReadyFsJournalWrite write_fn,
                                       ReadyFsJournalRead read_fn,
                                       unsigned int capacity) {

    if (write_fn == 0 || read_fn == 0 || capacity < 16u) return 0u;
#ifndef __CC65__
    selftest_probe = 0x5Au;
    if (!write_fn((unsigned int)(capacity - 1u), &selftest_probe, 1u)) return 0u;
    selftest_probe = 0u;
    if (!read_fn((unsigned int)(capacity - 1u), &selftest_probe, 1u) ||
        selftest_probe != 0x5Au) return 0u;
#endif
    readyfs_journal_init(&selftest_journal, 0xFEu, capacity, write_fn, read_fn);
    if (!selftest_journal.open) return 0u;
    if (!readyfs_journal_append(&selftest_journal, 1u, 0u, 2u, 1u, 0x1234u, 7u,
                                "ok")) return 0u;
    if (!readyfs_journal_read(&selftest_journal,
                              readyfs_journal_first(&selftest_journal),
                              &selftest_record, selftest_stem,
                              sizeof(selftest_stem), &selftest_next)) return 0u;
    if (selftest_record.action != 1u || selftest_record.result != 0u ||
        selftest_record.backend != 2u || selftest_record.kind != 1u ||
        selftest_record.detail != 0x1234u ||
        selftest_record.plan_offset != 7u ||
        strcmp(selftest_stem, "ok") != 0 ||
        selftest_next != RF_JOURNAL_END ||
        !readyfs_journal_finish(&selftest_journal)) return 0u;
    return 1u;
}

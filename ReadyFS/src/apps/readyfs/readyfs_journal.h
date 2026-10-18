#ifndef READYFS_JOURNAL_H
#define READYFS_JOURNAL_H

#define RF_JOURNAL_ABI 0x524Au
#define RF_JOURNAL_VERSION 1u
#define RF_JOURNAL_END 0xFFFFu
#define RF_JOURNAL_HEADER_BYTES 16u

#define RF_JOURNAL_CALL_INIT   1u
#define RF_JOURNAL_CALL_APPEND 2u
#define RF_JOURNAL_CALL_READ   3u
#define RF_JOURNAL_CALL_FINISH 4u
#define RF_JOURNAL_CALL_ONE    5u

typedef unsigned char (*ReadyFsJournalWrite)(unsigned int offset,
                                              const void *data,
                                              unsigned int length);
typedef unsigned char (*ReadyFsJournalRead)(unsigned int offset, void *data,
                                             unsigned int length);

typedef struct {
    ReadyFsJournalWrite write;
    ReadyFsJournalRead read;
    unsigned int capacity;
    unsigned int used;
    unsigned int count;
    unsigned int completed;
    unsigned int failed;
    unsigned char mode;
    unsigned char open;
    unsigned char overflow;
} ReadyFsJournal;

typedef struct {
    unsigned char action;
    unsigned char result;
    unsigned char backend;
    unsigned char kind;
    unsigned int detail;
    unsigned int plan_offset;
    unsigned int stem_len;
} ReadyFsJournalRecord;

typedef struct {
    unsigned char operation;
    unsigned char mode;
    unsigned char action;
    unsigned char result;
    unsigned char backend;
    unsigned char kind;
    unsigned char call_result;
    ReadyFsJournal *journal;
    ReadyFsJournalWrite write;
    ReadyFsJournalRead read;
    unsigned int capacity;
    unsigned int detail;
    unsigned int plan_offset;
    const char *stem;
    ReadyFsJournalRecord *record;
    char *output;
    unsigned int output_capacity;
    unsigned int offset;
    unsigned int next;
} ReadyFsJournalCall;

typedef struct {
    unsigned char operation;
    unsigned char action;
    unsigned char result;
    unsigned char backend;
    unsigned char kind;
    unsigned int detail;
    unsigned int plan_offset;
    const char *stem;
} ReadyFsJournalOne;

unsigned int readyfs_journal_abi(void);
void readyfs_journal_init(ReadyFsJournal *journal, unsigned char mode,
                          unsigned int capacity,
                          ReadyFsJournalWrite write_fn,
                          ReadyFsJournalRead read_fn);
unsigned char readyfs_journal_append(ReadyFsJournal *journal,
                                     unsigned char action,
                                     unsigned char result,
                                     unsigned char backend,
                                     unsigned char kind,
                                     unsigned int detail,
                                     unsigned int plan_offset,
                                     const char *stem);
unsigned char readyfs_journal_finish(ReadyFsJournal *journal);
unsigned char readyfs_journal_read(const ReadyFsJournal *journal,
                                   unsigned int offset,
                                   ReadyFsJournalRecord *record, char *stem,
                                   unsigned int stem_capacity,
                                   unsigned int *next);
unsigned int readyfs_journal_first(const ReadyFsJournal *journal);
unsigned char readyfs_journal_dispatch(ReadyFsJournalCall *call);
#ifdef __CC65__
unsigned char readyfs_journal_one(ReadyFsJournalOne *call);
#endif
unsigned char readyfs_journal_selftest(ReadyFsJournalWrite write_fn,
                                       ReadyFsJournalRead read_fn,
                                       unsigned int capacity);

#endif

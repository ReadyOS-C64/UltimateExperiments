#ifndef READYFS_PLAN_H
#define READYFS_PLAN_H

#define RF_PLAN_HEADER_BYTES 6u
#define RF_PLAN_END       0xFFFFu
#define RF_PLAN_KIND_FILE 1u
#define RF_PLAN_KIND_DIR  2u
#define RF_PLAN_SELECTED  0x01u
#define RF_PLAN_ABI       0x5246u

#define RF_PLAN_CALL_INIT 1u
#define RF_PLAN_CALL_ADD  2u
#define RF_PLAN_CALL_READ 3u

typedef unsigned char (*ReadyFsPlanWrite)(unsigned int offset,
                                          const void *data,
                                          unsigned int length);
typedef unsigned char (*ReadyFsPlanRead)(unsigned int offset,
                                         void *data,
                                         unsigned int length);

typedef struct {
    ReadyFsPlanWrite write;
    ReadyFsPlanRead read;
    unsigned int capacity;
    unsigned int used;
    unsigned int last;
    unsigned int count;
    unsigned int files;
    unsigned int directories;
    unsigned int selected_files;
    unsigned int selected_directories;
    unsigned char overflow;
} ReadyFsPlan;

typedef struct {
    unsigned char kind;
    unsigned char flags;
    unsigned int stem_len;
    unsigned int previous;
} ReadyFsPlanRecord;

typedef struct {
    unsigned char operation;
    unsigned char kind;
    unsigned char flags;
    unsigned char result;
    ReadyFsPlan *plan;
    unsigned int capacity;
    ReadyFsPlanWrite write;
    ReadyFsPlanRead read;
    const char *stem;
    ReadyFsPlanRecord *record;
    char *output;
    unsigned int output_capacity;
    unsigned int offset;
    unsigned int next;
} ReadyFsPlanCall;

void readyfs_plan_init(ReadyFsPlan *plan, unsigned int capacity,
                       ReadyFsPlanWrite write_fn, ReadyFsPlanRead read_fn);
unsigned char readyfs_plan_add(ReadyFsPlan *plan, unsigned char kind,
                               unsigned char flags, const char *stem);
unsigned char readyfs_plan_read(const ReadyFsPlan *plan, unsigned int offset,
                                ReadyFsPlanRecord *record, char *stem,
                                unsigned int stem_capacity,
                                unsigned int *next);
unsigned int readyfs_plan_first(const ReadyFsPlan *plan);
unsigned int readyfs_plan_abi(void);
unsigned char readyfs_plan_dispatch(ReadyFsPlanCall *call);

#endif

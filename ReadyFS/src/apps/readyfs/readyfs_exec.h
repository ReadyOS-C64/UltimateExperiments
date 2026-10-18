#ifndef READYFS_EXEC_H
#define READYFS_EXEC_H

#include "readyfs_plan.h"

#define RF_EXEC_ABI 0x5245u

#define RF_EXEC_MODE_COPY   1u
#define RF_EXEC_MODE_MOVE   2u
#define RF_EXEC_MODE_DELETE 3u

#define RF_EXEC_ACTION_DONE        0u
#define RF_EXEC_ACTION_MKDIR       1u
#define RF_EXEC_ACTION_COPY_FILE   2u
#define RF_EXEC_ACTION_MOVE_FILE   3u
#define RF_EXEC_ACTION_DELETE_FILE 4u
#define RF_EXEC_ACTION_RMDIR       5u
#define RF_EXEC_ACTION_ERROR       255u

#define RF_EXEC_CALL_INIT 1u
#define RF_EXEC_CALL_NEXT 2u
#define RF_EXEC_CALL_ACK  3u

#define RF_ACTION_CALL_BEGIN 1u
#define RF_ACTION_CALL_ACK   2u

typedef struct {
    ReadyFsPlan *plan;
    unsigned int cursor;
    unsigned int pending;
    unsigned int attempted;
    unsigned int completed;
    unsigned int failed;
    unsigned char mode;
    unsigned char reverse;
    unsigned char action;
    unsigned char pending_valid;
    unsigned char stop_on_error;
    unsigned char stopped;
} ReadyFsExecutor;

typedef struct {
    unsigned char operation;
    unsigned char mode;
    unsigned char stop_on_error;
    unsigned char succeeded;
    ReadyFsExecutor *exec;
    ReadyFsPlan *plan;
    ReadyFsPlanRecord *record;
    char *stem;
    unsigned int stem_capacity;
} ReadyFsExecCall;

typedef struct {
    ReadyFsPlan plan;
    ReadyFsExecutor executor;
    ReadyFsPlanRecord record;
    unsigned char action;
    char stem[2];
} ReadyFsActionState;

typedef struct {
    unsigned char operation;
    unsigned char action;
    unsigned char succeeded;
    ReadyFsActionState *state;
#ifndef __CC65__
    unsigned int capacity;
    ReadyFsPlanWrite write;
    ReadyFsPlanRead read;
#endif
} ReadyFsActionCall;

unsigned int readyfs_exec_abi(void);
unsigned char readyfs_exec_init(ReadyFsExecutor *exec, ReadyFsPlan *plan,
                                unsigned char mode,
                                unsigned char stop_on_error);
unsigned char readyfs_exec_next(ReadyFsExecutor *exec,
                                ReadyFsPlanRecord *record, char *stem,
                                unsigned int stem_capacity);
unsigned char readyfs_exec_ack(ReadyFsExecutor *exec,
                               unsigned char succeeded);
unsigned char readyfs_exec_dispatch(ReadyFsExecCall *call);
unsigned char readyfs_action_dispatch(ReadyFsActionCall *call);
#ifdef __CC65__
unsigned char readyfs_action_selftest(void);
#endif

#endif

#ifndef READYFS_OVERLAY_H
#define READYFS_OVERLAY_H

#include "readyfs_plan.h"
#include "readyfs_exec.h"
#include "readyfs_journal.h"
#include "readyfs_backend.h"
#include "readyfs_help.h"
#include "readyfs_driver.h"
#include "readyfs_driveui.h"
#include "readyfs_recursive.h"
#include "readyfs_nativeplan.h"
#include "readyfs_utility.h"
#include "readyfs_tree.h"
#include "readyfs_batch.h"
#include "readyfs_script.h"
#include "readyfs_tape.h"
#include "readyfs_present.h"
#include "readyfs_stream.h"
#include "readyfs_udos_files.h"
#include "readyfs_iec.h"
#include "readyfs_files.h"

#define RF_NESTED_PLAN    1u
#define RF_NESTED_EXEC    2u
#define RF_NESTED_JOURNAL 3u
#define RF_NESTED_ACTION  4u
#define RF_NESTED_CMDPATH 5u
#define RF_NESTED_BACKEND 6u
#define RF_NESTED_RECURSIVE 7u
#define RF_NESTED_MATCH     8u
#define RF_NESTED_RETURN_BACKEND 0x20u
#define RF_NESTED_RETURN_DRIVE 0x40u
#define RF_NESTED_RESIDENT 0x80u

typedef struct {
    unsigned char operation;
    void *call;
} ReadyFsNestedCall;

unsigned char readyfs_overlay_init(unsigned char reu_available);
unsigned char readyfs_overlay_match(const char *pattern,
                                    const char *relative_stem);
unsigned char readyfs_overlay_plan_available(void);
unsigned char readyfs_overlay_plan_call(ReadyFsPlanCall *call);
unsigned char readyfs_overlay_exec_call(ReadyFsExecCall *call);
unsigned char readyfs_overlay_journal_call(ReadyFsJournalCall *call);
unsigned char readyfs_overlay_journal_available(void);
unsigned char readyfs_overlay_backend_available(void);
unsigned char readyfs_overlay_backend_call(ReadyFsBackendCall *call);
unsigned char readyfs_overlay_recursive(ReadyFsRecursiveCall *call);
unsigned char readyfs_overlay_native(ReadyFsNativeUiCall *call);
unsigned char readyfs_overlay_drive(ReadyFsDriveUiCall *call);
unsigned char readyfs_overlay_utility(ReadyFsUtilityCall *call);
unsigned char readyfs_overlay_tree(ReadyFsTreeCall *call);
unsigned char readyfs_overlay_batch(ReadyFsBatchCall *call);
unsigned char readyfs_overlay_batch_available(void);
unsigned char readyfs_overlay_script(ReadyFsBatchCall *call);
#ifdef __CC65__
unsigned char __fastcall__ readyfs_script_exists(const char *path);
#else
unsigned char readyfs_script_exists(const char *path);
#endif
unsigned char readyfs_overlay_tape(ReadyFsTapeCall *call);
unsigned char readyfs_overlay_nested_from_backend(ReadyFsNestedCall *nested);
unsigned char readyfs_overlay_iec(ReadyFsIecCall *call);
unsigned char readyfs_overlay_files(ReadyFsFilesCall *call);
unsigned char readyfs_overlay_udos(ReadyFsUdosFilesCall *call);
unsigned char readyfs_overlay_stream(ReadyFsStreamCall *call);
unsigned char readyfs_overlay_help(void);
unsigned char readyfs_overlay_present(ReadyFsUtilityCall *call);

#endif

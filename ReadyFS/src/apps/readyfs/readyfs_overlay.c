#include "readyfs_overlay.h"
#include "readyfs_result.h"

#include "readyfs_match.h"
#include "readyfs_exec.h"
#include "readyfs_help.h"
#include "readyfs_journal.h"
#include "readyfs_backend.h"
#include "readyfs_cmdpath.h"
#include "readyfs_driver.h"
#include "readyfs_recursive.h"
#include "readyfs_reu.h"
#include "readyfs_utility.h"
#include "readyfs_tree.h"
#include "readyfs_content.h"
#include "readyfs_batch.h"
#include "readyfs_ui.h"
#include "readyfs_console.h"
#include "readyfs_tape.h"

#ifdef READYFS_OVERLAY_RUNTIME

#include <cbm.h>

#define RF_CPU_PORT (*(volatile unsigned char *)0x0001u)

extern unsigned char _OVERLAY1_LOAD__[];
extern unsigned char _OVERLAY1_SIZE__[];
extern unsigned char _OVERLAY2_SIZE__[];
extern unsigned char _OVERLAY3_SIZE__[];
extern unsigned char _OVERLAY4_SIZE__[];
extern unsigned char _OVERLAY5_SIZE__[];
extern unsigned char _OVERLAY6_SIZE__[];
extern unsigned char _OVERLAY7_SIZE__[];
extern unsigned char _OVERLAY8_SIZE__[];
extern unsigned char _OVERLAY9_SIZE__[];
extern unsigned char _OVERLAY10_SIZE__[];
extern unsigned char _OVERLAY11_SIZE__[];
extern unsigned char _OVERLAY12_SIZE__[];
extern unsigned char _OVERLAY13_SIZE__[];
extern unsigned char _OVERLAY14_SIZE__[];
extern unsigned char _OVERLAY15_SIZE__[];
extern unsigned char _OVERLAY16_SIZE__[];
extern unsigned char _OVERLAY17_SIZE__[];

/* Linker-visible admission sentinels let post-stop automation bind to the
 * current BSS layout rather than a stale hard-coded address. */
unsigned char plan_loaded;
unsigned char help_loaded;
unsigned char backend_loaded;
unsigned char drive_loaded;
unsigned char utility_loaded;
unsigned char batch_loaded;
unsigned char tape_loaded;
static unsigned char overlay_old_port;

static const char * const sidecar_names[] = {
    "rfplan", "rfhelp", "rfbackend", "rfcmdpath",
    "rfdrive", "rfutil", "rftree", "rfcontent", "rfrecur"
};

static const unsigned int sidecar_offsets[] = {
    RF_REU_OVERLAY_PLAN_OFF, RF_REU_OVERLAY_HELP_OFF,
    RF_REU_OVERLAY_BACKEND_OFF, RF_REU_OVERLAY_CMDPATH_OFF,
    RF_REU_OVERLAY_DRIVE_OFF, RF_REU_OVERLAY_UTILITY_OFF,
    RF_REU_OVERLAY_TREE_OFF, RF_REU_OVERLAY_CONTENT_OFF,
    RF_REU_OVERLAY_RECURSIVE_OFF
};

static const unsigned char * const sidecar_sizes[] = {
    _OVERLAY2_SIZE__, _OVERLAY3_SIZE__, _OVERLAY4_SIZE__, _OVERLAY5_SIZE__,
    _OVERLAY6_SIZE__, _OVERLAY7_SIZE__, _OVERLAY8_SIZE__, _OVERLAY9_SIZE__,
    _OVERLAY11_SIZE__
};

static unsigned int overlay_size(void) {
    return (unsigned int)_OVERLAY1_SIZE__;
}

/* Defaults to the documented lab drive. A launcher may choose another
 * already prepared lab drive before entry, without replacing user media. */
unsigned char readyfs_boot_device = 8u;
static unsigned int load_sidecar(const char *name) {
    unsigned int end_address;

    cbm_k_clall();
    end_address = cbm_load(name, readyfs_boot_device, 0);
    cbm_k_clall();
    return end_address >= (unsigned int)_OVERLAY1_LOAD__ ?
           (unsigned int)(end_address - (unsigned int)_OVERLAY1_LOAD__) : 0u;
}

static unsigned char fetch_cached(unsigned int reu_offset,
                                  unsigned int size) {
    return readyfs_reu_overlay_fetch(reu_offset, _OVERLAY1_LOAD__, size);
}

static unsigned char open_cached(unsigned int reu_offset,
                                 unsigned int size) {
    overlay_old_port = RF_CPU_PORT;
    RF_CPU_PORT = (unsigned char)(overlay_old_port & 0xFEu);
    if (!fetch_cached(reu_offset, size)) {
        RF_CPU_PORT = overlay_old_port;
        return 0u;
    }
    return 1u;
}

static void close_cached(void) { RF_CPU_PORT = overlay_old_port; }

/* Load a PRG into the shared window and cache its exact mapped payload. The
 * caller receives the window banked in so it can run the sidecar ABI probe. */
static unsigned char load_cached(unsigned char slot) {
    unsigned char index;
    unsigned int reu_offset;
    unsigned int size;

    if (slot < 2u || slot > 10u) return 0u;
    index = (unsigned char)(slot - 2u);
    reu_offset = sidecar_offsets[index];
    size = (unsigned int)sidecar_sizes[index];
    if (size == 0u || size > RF_REU_OVERLAY_MATCH_BYTES ||
        load_sidecar(sidecar_names[index]) != size) return 0u;
    overlay_old_port = RF_CPU_PORT;
    RF_CPU_PORT = (unsigned char)(overlay_old_port & 0xFEu);
    if (!readyfs_reu_overlay_store(reu_offset, _OVERLAY1_LOAD__, size)) {
        RF_CPU_PORT = overlay_old_port;
        return 0u;
    }
    return 1u;
}

static void restore_match(void) {
    (void)fetch_cached(RF_REU_OVERLAY_MATCH_OFF, overlay_size());
    close_cached();
}

static unsigned char restore_recursive(void) {
    return fetch_cached(RF_REU_OVERLAY_RECURSIVE_OFF,
                        (unsigned int)_OVERLAY11_SIZE__);
}

static const char * const batch_names[] = { "rfbatch", "rfui", "rftape", "rfshow", "rfexamples", "rfstream", "rfiec" };
static const unsigned char * const batch_sizes[] = {
    _OVERLAY10_SIZE__, _OVERLAY13_SIZE__, _OVERLAY12_SIZE__, _OVERLAY14_SIZE__, _OVERLAY15_SIZE__, _OVERLAY16_SIZE__, _OVERLAY17_SIZE__ };
static const unsigned int batch_offsets[] = {
    RF_REU_BATCH_CACHE_OFF, RF_UI_CACHE_OFF, RF_REU_TAPE_CACHE_OFF, RF_PRESENT_CACHE_OFF, RF_COMMAND_HELP_CACHE_OFF, RF_REU_STREAM_CACHE_OFF, RF_REU_IEC_CACHE_OFF };
static unsigned char open_batch_cached(unsigned char slot) {
    overlay_old_port = RF_CPU_PORT;
    RF_CPU_PORT = (unsigned char)(overlay_old_port & 0xFEu);
    if (readyfs_reu_batch_fetch(batch_offsets[slot], _OVERLAY1_LOAD__,
                               (unsigned int)batch_sizes[slot])) return 1u;
    close_cached(); return 0u;
}
static unsigned char load_batch_cached(unsigned char slot) {
    unsigned int size;
    size = (unsigned int)batch_sizes[slot];
    if (size == 0u || size > 0x1000u || load_sidecar(batch_names[slot]) != size) return 0u;
    overlay_old_port = RF_CPU_PORT;
    RF_CPU_PORT = (unsigned char)(overlay_old_port & 0xFEu);
    if (readyfs_reu_batch_store(batch_offsets[slot], _OVERLAY1_LOAD__, size)) return 1u;
    close_cached(); return 0u;
}

unsigned char readyfs_overlay_init(unsigned char reu_available) {
    unsigned int loaded;
    unsigned int size;
    unsigned char old_port;

    plan_loaded = 0u;
    help_loaded = 0u;
    backend_loaded = 0u;
    drive_loaded = 0u;
    utility_loaded = 0u;
    batch_loaded = 0u;
    tape_loaded = 0u;
    if (!reu_available) return 0u;
    size = overlay_size();
    /* Autostart can leave its LOAD channel selected. ReadyShell's proven
     * overlay path closes all logical channels before any sidecar I/O. */
    /* Sidecars are normal PRGs whose headers name the shared $B600 window.
     * Passing NULL makes cbm_load honor that header and return the end address. */
    loaded = load_sidecar("rfmatch");
    if (loaded != size || size == 0u ||
        size > RF_REU_OVERLAY_MATCH_BYTES) return 0u;
    old_port = RF_CPU_PORT;
    RF_CPU_PORT = (unsigned char)(old_port & 0xFEu);
    if (!readyfs_reu_overlay_store(RF_REU_OVERLAY_MATCH_OFF,
                                   _OVERLAY1_LOAD__, size)) {
        RF_CPU_PORT = old_port;
        return 0u;
    }
    RF_CPU_PORT = old_port;
        if (load_cached(2u)) {
            /* Execute a tiny ABI probe while OVERLAY2 is present. This proves
             * the cached sidecar is callable, not merely loadable. */
            if (readyfs_plan_abi() == RF_PLAN_ABI &&
                readyfs_exec_abi() == RF_EXEC_ABI &&
                readyfs_action_selftest()) plan_loaded = 1u;
            restore_match();
        }
        if (load_cached(3u)) {
            if (readyfs_help_abi() == RF_HELP_ABI &&
                readyfs_journal_abi() == RF_JOURNAL_ABI &&
                readyfs_journal_selftest(readyfs_reu_session_store,
                                         readyfs_reu_session_fetch,
                                         RF_REU_JOURNAL_BYTES)) {
                help_loaded = 1u;
            }
            restore_match();
        }
        if (load_cached(4u)) {
            if (readyfs_backend_abi() == RF_BACKEND_ABI &&
                readyfs_backend_selftest()) backend_loaded = 1u;
            restore_match();
        }
        if (!load_cached(5u)) return 0u;
        if (readyfs_cmdpath_abi() != RF_CMDPATH_ABI ||
            !readyfs_cmdpath_selftest()) {
            restore_match();
            return 0u;
        }
        restore_match();
        if (load_cached(6u)) {
            if (readyfs_driver_abi() == RF_DRIVER_ABI &&
                readyfs_driveui_abi() == RF_DRIVEUI_ABI &&
                readyfs_driveui_reset()) drive_loaded = 1u;
            restore_match();
        }
        if (load_cached(7u)) {
            if (readyfs_utility_abi() != RF_UTILITY_ABI) {
                restore_match(); return 0u;
            }
            utility_loaded |= 0x01u;
            restore_match();
        }
        if (load_cached(8u)) {
            if (readyfs_tree_abi() != RF_TREE_ABI) {
                restore_match(); return 0u;
            }
            utility_loaded |= 0x02u;
            restore_match();
        }
        if (load_cached(9u)) {
            if (readyfs_content_abi() == RF_CONTENT_ABI) utility_loaded |= 0x04u;
            else { restore_match(); return 0u; }
            restore_match();
        }
        if (!load_cached(10u)) return 0u;
        restore_match();
        if (load_batch_cached(0u)) {
            batch_loaded = (unsigned char)(readyfs_batch_abi() == RF_BATCH_ABI);
            restore_match();
        }
        if (load_batch_cached(1u)) restore_match();
        else batch_loaded = 0u;
        if (load_batch_cached(2u)) {
            tape_loaded = (unsigned char)(readyfs_tape_abi() == RF_TAPE_ABI);
            restore_match();
        }
    if (!load_batch_cached(3u)) return 0u;
    loaded = readyfs_present_abi();
    restore_match();
    if (loaded != RF_PRESENT_ABI || !load_batch_cached(4u)) return 0u;
    loaded = readyfs_command_help_abi();
    restore_match();
    if (loaded != RF_COMMAND_HELP_ABI || !load_batch_cached(5u)) return 0u;
    loaded = readyfs_stream_abi();
    restore_match();
    if (loaded != RF_STREAM_ABI || !load_batch_cached(6u)) return 0u;
    loaded = readyfs_iec_plan_abi();
    restore_match();
    return (unsigned char)(loaded == RF_IEC_PLAN_ABI);
}

unsigned char readyfs_overlay_match(const char *pattern,
                                    const char *relative_stem) {
    unsigned char result;

    /* OVERLAY1 executes in RAM under BASIC ROM. Keep KERNAL/I/O visible and
     * restore the caller's exact CPU-port configuration after the call. */
    if (!open_cached(RF_REU_OVERLAY_MATCH_OFF, overlay_size())) return 0u;
    result = readyfs_match(pattern, relative_stem);
    close_cached();
    return result;
}

unsigned char readyfs_overlay_plan_available(void) { return plan_loaded; }

unsigned char readyfs_overlay_iec(ReadyFsIecCall *call) {
    unsigned char result;
    *call->status = RF_RESULT_UNAVAILABLE;
    if (!open_batch_cached(6u)) return 0u;
    result = readyfs_iec_plan(call);
    restore_match();
    if (!result || !open_batch_cached(5u)) return 0u;
    *call->status = RF_RESULT_OK;
    result = readyfs_iec_execute(call);
    restore_match(); return result;
}

unsigned char readyfs_overlay_stream(ReadyFsStreamCall *call) {
    unsigned char result;
    if (!open_batch_cached(5u)) return 0u;
    result = readyfs_stream_prepare(call);
    restore_match(); return result;
}

unsigned char readyfs_overlay_present(ReadyFsUtilityCall *call) {
    unsigned char help, result;
    help = (unsigned char)(call->operation == RF_PRESENT_HELP || call->operation == RF_PRESENT_PLAN);
    if (!open_batch_cached(help ? 4u : 3u)) return 0u;
    result = 1u;
    if (call->operation == RF_PRESENT_PLAN) result = readyfs_transfer_plan(call);
    else if (help) readyfs_command_help(call);
    else result = readyfs_present(call);
    restore_match(); return result;
}

unsigned char readyfs_overlay_help(void) {
    if (!help_loaded) return 0u;
    if (!open_cached(RF_REU_OVERLAY_HELP_OFF,
                     (unsigned int)_OVERLAY3_SIZE__)) return 0u;
    readyfs_help_show();
    close_cached();
    return 1u;
}

unsigned char readyfs_overlay_journal_available(void) { return help_loaded; }

unsigned char readyfs_overlay_backend_available(void) {
    return backend_loaded;
}

unsigned char readyfs_overlay_backend_call(ReadyFsBackendCall *call) {
    unsigned char result;

    if (!backend_loaded ||
        !open_cached(RF_REU_OVERLAY_BACKEND_OFF,
                     (unsigned int)_OVERLAY4_SIZE__)) {
        return 0u;
    }
    result = readyfs_backend_dispatch(call);
    /* Unlike ordinary UI overlays, backend calls restore the matcher before
     * returning. This keeps resident libc and the next command independent of
     * the larger backend payload left in the shared window. */
    restore_match();
    return result;
}

unsigned char readyfs_overlay_recursive(ReadyFsRecursiveCall *call) {
    unsigned char result;

    /* The recursive controller has its own sidecar because a real filesystem
     * walker no longer fits beside the matcher. Its cache shares the batch
     * REU bank but has a disjoint, explicitly bounded 4 KB slot. */
    if (!open_cached(RF_REU_OVERLAY_RECURSIVE_OFF,
                     (unsigned int)_OVERLAY11_SIZE__)) return 0u;
    result = readyfs_recursive_dispatch(call);
    restore_match();
    return result;
}

unsigned char readyfs_overlay_native(ReadyFsNativeUiCall *call) {
    unsigned char result;

    if (!help_loaded ||
        !open_cached(RF_REU_OVERLAY_HELP_OFF,
                     (unsigned int)_OVERLAY3_SIZE__)) return 0u;
    result = readyfs_help_native(call);
    restore_match();
    return result;
}

unsigned char readyfs_overlay_drive(ReadyFsDriveUiCall *call) {
    unsigned char result;

    if (call->operation == RF_UTILITY_FORMAT_MEDIA) {
        return readyfs_overlay_utility((ReadyFsUtilityCall *)(void *)call);
    }
    if (!drive_loaded ||
        !open_cached(RF_REU_OVERLAY_DRIVE_OFF,
                     (unsigned int)_OVERLAY6_SIZE__)) return 0u;
    result = readyfs_driveui_dispatch(call);
    restore_match();
    return result;
}

unsigned char readyfs_overlay_utility(ReadyFsUtilityCall *call) {
    unsigned char result;

    if (call->operation >= RF_UTILITY_CONTENT_INIT) {
        if ((utility_loaded & 0x04u) == 0u) return 0u;
        if (!open_cached(RF_REU_OVERLAY_CONTENT_OFF,
                         (unsigned int)_OVERLAY9_SIZE__)) return 0u;
        result = readyfs_content_dispatch(call);
    } else {
        if ((utility_loaded & 0x01u) == 0u) return 0u;
        if (!open_cached(RF_REU_OVERLAY_UTILITY_OFF,
                         (unsigned int)_OVERLAY7_SIZE__)) return 0u;
        result = readyfs_utility_dispatch(call);
    }
    restore_match();
    return result;
}

unsigned char readyfs_overlay_tree(ReadyFsTreeCall *call) {
    unsigned char result;

    if (call->operation == RF_TREE_CALL_COMMAND_ID) {
        if (!open_batch_cached(1u)) return 0u;
        result = readyfs_ui_prepare(call);
        restore_match(); return result;
    }
    if ((utility_loaded & 0x02u) == 0u ||
        !open_cached(RF_REU_OVERLAY_TREE_OFF,
                     (unsigned int)_OVERLAY8_SIZE__)) return 0u;
    result = readyfs_tree_dispatch(call);
    restore_match();
    return result;
}

unsigned char readyfs_overlay_batch(ReadyFsBatchCall *call) {
    unsigned char result;
    if (!batch_loaded) return 0u;
    if (!open_batch_cached(call->operation == RF_BATCH_EDITOR ? 1u : 0u)) return 0u;
    result = call->operation == RF_BATCH_EDITOR ?
             readyfs_ui_editor(call) : readyfs_batch_dispatch(call);
    restore_match();
    return result;
}

unsigned char readyfs_overlay_batch_available(void) { return batch_loaded; }

unsigned char readyfs_overlay_tape(ReadyFsTapeCall *call) {
    unsigned char result;

    if (!tape_loaded) return 0u;
    if (!open_batch_cached(2u)) return 0u;
    result = readyfs_tape_dispatch(call);
    restore_match();
    return result;
}

/* Called while a sidecar is executing. Mutable call/state storage must be
 * resident or in REU, never inside the overwritten overlay window. Restore
 * the caller sidecar before RTS so its return address is executable. */
unsigned char readyfs_overlay_nested_from_backend(ReadyFsNestedCall *nested) {
    unsigned char result;
    unsigned char operation;

    if (nested == 0 || nested->call == 0) return 0u;
    operation = (unsigned char)(nested->operation & 0x1Fu);
    if (operation == RF_NESTED_PLAN || operation == RF_NESTED_EXEC ||
        operation == RF_NESTED_ACTION) {
        if (!fetch_cached(RF_REU_OVERLAY_PLAN_OFF,
                          (unsigned int)_OVERLAY2_SIZE__)) return 0u;
        if (operation == RF_NESTED_PLAN) {
            result = readyfs_plan_dispatch((ReadyFsPlanCall *)nested->call);
        } else if (operation == RF_NESTED_EXEC) {
            result = readyfs_exec_dispatch((ReadyFsExecCall *)nested->call);
        } else result = readyfs_action_dispatch(
            (ReadyFsActionCall *)nested->call);
    } else if (operation == RF_NESTED_JOURNAL) {
        if (!fetch_cached(RF_REU_OVERLAY_HELP_OFF,
                          (unsigned int)_OVERLAY3_SIZE__)) return 0u;
        result = readyfs_journal_dispatch((ReadyFsJournalCall *)nested->call);
    } else if (operation == RF_NESTED_CMDPATH) {
        if (!fetch_cached(RF_REU_OVERLAY_CMDPATH_OFF,
                          (unsigned int)_OVERLAY5_SIZE__)) return 0u;
        result = readyfs_cmdpath_dispatch((ReadyFsCmdPathCall *)nested->call);
        if ((nested->operation &
             (RF_NESTED_RETURN_DRIVE | RF_NESTED_RETURN_BACKEND)) == 0u) {
            if (!fetch_cached(RF_REU_OVERLAY_HELP_OFF,
                              (unsigned int)_OVERLAY3_SIZE__)) return 0u;
            return result;
        }
    } else if (operation == RF_NESTED_BACKEND) {
        if (!fetch_cached(RF_REU_OVERLAY_BACKEND_OFF,
                          (unsigned int)_OVERLAY4_SIZE__)) return 0u;
        result = readyfs_backend_dispatch((ReadyFsBackendCall *)nested->call);
    } else if (operation == RF_NESTED_RECURSIVE) {
        if (!restore_recursive()) return 0u;
        result = readyfs_recursive_dispatch(
            (ReadyFsRecursiveCall *)nested->call);
    } else if (operation == RF_NESTED_MATCH) {
        ReadyFsMatchCall *match;
        if (!fetch_cached(RF_REU_OVERLAY_MATCH_OFF,
                          overlay_size())) return 0u;
        match = (ReadyFsMatchCall *)nested->call;
        result = readyfs_match(match->pattern, match->stem);
    } else return 0u;
    if ((nested->operation & RF_NESTED_RETURN_DRIVE) != 0u) {
        if (!fetch_cached(RF_REU_OVERLAY_DRIVE_OFF,
                          (unsigned int)_OVERLAY6_SIZE__)) return 0u;
        return result;
    }
    if ((nested->operation & RF_NESTED_RESIDENT) != 0u) {
        if (!restore_recursive()) return 0u;
        return result;
    }
    if (!fetch_cached(RF_REU_OVERLAY_BACKEND_OFF,
                      (unsigned int)_OVERLAY4_SIZE__)) return 0u;
    return result;
}

#else

unsigned char readyfs_overlay_init(unsigned char reu_available) {
    (void)reu_available;
    return 1u;
}

unsigned char readyfs_overlay_match(const char *pattern,
                                    const char *relative_stem) {
    return readyfs_match(pattern, relative_stem);
}

unsigned char readyfs_overlay_plan_available(void) { return 1u; }

unsigned char readyfs_overlay_recursive(ReadyFsRecursiveCall *call) {
    (void)call;
    return 0u;
}

unsigned char readyfs_overlay_plan_call(ReadyFsPlanCall *call) {
    return readyfs_plan_dispatch(call);
}

unsigned char readyfs_overlay_present(ReadyFsUtilityCall *call) {
    return readyfs_present(call);
}

unsigned char readyfs_overlay_help(void) {
    readyfs_help_show();
    return 1u;
}

unsigned char readyfs_overlay_utility(ReadyFsUtilityCall *call) {
    return readyfs_utility_dispatch(call);
}

unsigned char readyfs_overlay_tree(ReadyFsTreeCall *call) {
    (void)call;
    return 0u;
}

unsigned char readyfs_overlay_batch(ReadyFsBatchCall *call) {
    (void)call;
    return 0u;
}

unsigned char readyfs_overlay_batch_available(void) { return 0u; }

unsigned char readyfs_overlay_tape(ReadyFsTapeCall *call) {
    (void)call;
    return 0u;
}


#endif

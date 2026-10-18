#include "readyfs_tree.h"
#include "readyfs_console.h"

#include "readyfs_commands.h"
#include "readyfs_reu.h"
#include "readyfs_result.h"

#include <string.h>

#ifdef READYFS_TREE_SIDECAR
#include <conio.h>
#endif

#define RF_TREE_MAGIC 0x54u
#define RF_TREE_RECORD_DEPTH    0x3Fu
#define RF_TREE_RECORD_SELECTED 0x40u
#define RF_TREE_RECORD_FILE     0x80u

typedef struct {
    unsigned char magic;
    unsigned char max_depth;
    unsigned char overflow;
    unsigned int limit;
    unsigned int scan;
    unsigned int used;
    unsigned int entries;
    unsigned int files;
    unsigned int directories;
    unsigned int selected_entries;
} ReadyFsTreeState;

static ReadyFsTreeState tree_state;
static unsigned char tree_header[2];

#ifdef READYFS_TREE_SIDECAR
static void print_u16(unsigned int value) {
    char reverse[5];
    unsigned char used;
    used = 0u;
    do {
        reverse[used++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    while (used != 0u) cputc(reverse[--used]);
}
#endif

#ifndef __CC65__
static unsigned char host_state[RF_REU_TREE_STATE_BYTES];
static unsigned char host_queue[RF_REU_TREE_QUEUE_BYTES];
#endif

static unsigned char state_store(void) {
#ifdef __CC65__
    return readyfs_reu_session_store(RF_REU_TREE_STATE_OFF, &tree_state,
                                     sizeof(tree_state));
#else
    memcpy(host_state, &tree_state, sizeof(tree_state));
    return 1u;
#endif
}

static unsigned char state_fetch(void) {
#ifdef __CC65__
    return readyfs_reu_session_fetch(RF_REU_TREE_STATE_OFF, &tree_state,
                                     sizeof(tree_state));
#else
    memcpy(&tree_state, host_state, sizeof(tree_state));
    return 1u;
#endif
}

static unsigned char queue_store(unsigned int offset, const void *data,
                                 unsigned int length) {
    if (offset > RF_REU_TREE_QUEUE_BYTES ||
        length > (unsigned int)(RF_REU_TREE_QUEUE_BYTES - offset)) return 0u;
#ifdef __CC65__
    return readyfs_reu_overlay_store(
        (unsigned int)(RF_REU_TREE_QUEUE_OFF + offset), data, length);
#else
    memcpy(host_queue + offset, data, length);
    return 1u;
#endif
}

static unsigned char queue_fetch(unsigned int offset, void *data,
                                 unsigned int length) {
    if (offset > RF_REU_TREE_QUEUE_BYTES ||
        length > (unsigned int)(RF_REU_TREE_QUEUE_BYTES - offset)) return 0u;
#ifdef __CC65__
    return readyfs_reu_overlay_fetch(
        (unsigned int)(RF_REU_TREE_QUEUE_OFF + offset), data, length);
#else
    memcpy(data, host_queue + offset, length);
    return 1u;
#endif
}

static unsigned char stem_depth(const char *stem) {
    unsigned char depth;
    depth = stem[0] == 0 ? 0u : 1u;
    while (*stem != 0) if (*stem++ == '/') ++depth;
    return depth;
}

static void report(ReadyFsTreeCall *call) {
    call->entries = tree_state.entries;
    call->files = tree_state.files;
    call->directories = tree_state.directories;
    call->selected_entries = tree_state.selected_entries;
    call->queue_used = tree_state.used;
}

static unsigned char initialize(ReadyFsTreeCall *call) {
    memset(&tree_state, 0, sizeof(tree_state));
    tree_state.magic = RF_TREE_MAGIC;
    tree_state.max_depth = call->max_depth == 0u ? 32u : call->max_depth;
    tree_state.limit = call->limit == 0u ? 512u : call->limit;
    /* Queue record: one-byte stem length, one-byte depth, then NUL. */
    tree_header[0] = 0u;
    tree_header[1] = 0u;
    if (!queue_store(0u, tree_header, sizeof(tree_header)) ||
        !queue_store(2u, "", 1u)) return 0u;
    tree_state.used = 3u;
    call->result = RF_TREE_OK;
    report(call);
    return state_store();
}

static unsigned char next_directory(ReadyFsTreeCall *call) {
    unsigned int bytes;
    char *relative;
    unsigned int relative_capacity;
    unsigned int root_len;
    unsigned int relative_len;
    relative = call->relative == 0 ? call->output : call->relative;
    relative_capacity = call->relative == 0 ? call->output_capacity :
                                               call->relative_capacity;
    if (call->output == 0 || call->output_capacity == 0u || relative == 0 ||
        relative_capacity == 0u ||
        !state_fetch() || tree_state.magic != RF_TREE_MAGIC) return 0u;
    for (;;) {
        if (tree_state.scan == tree_state.used) {
            call->result = RF_TREE_DONE;
            report(call);
            return state_store();
        }
        if (tree_state.scan > tree_state.used ||
            !queue_fetch(tree_state.scan, tree_header, sizeof(tree_header))) {
            call->result = RF_TREE_CORRUPT;
            return 1u;
        }
        bytes = (unsigned int)tree_header[0] + 1u;
        if (bytes > relative_capacity ||
            bytes + 2u > (unsigned int)(tree_state.used - tree_state.scan) ||
            !queue_fetch((unsigned int)(tree_state.scan + 2u), relative,
                         bytes) || relative[bytes - 1u] != 0) {
            call->result = RF_TREE_CORRUPT;
            return 1u;
        }
        tree_state.scan = (unsigned int)(tree_state.scan + bytes + 2u);
        if (tree_header[1] & RF_TREE_RECORD_FILE) continue;
        if (call->relative != 0) {
            if (call->name == 0) { call->result = RF_TREE_CORRUPT; return 1u; }
            root_len = strlen(call->name);
            relative_len = (unsigned int)(bytes - 1u);
            if (root_len + relative_len +
                (root_len != 0u && relative_len != 0u ? 1u : 0u) + 1u >
                    call->output_capacity) {
                call->result = RF_TREE_BAD_NAME;
                return 1u;
            }
            strcpy(call->output, call->name);
            if (root_len != 0u && relative_len != 0u &&
                call->output[root_len - 1u] != '/') strcat(call->output, "/");
            strcat(call->output, relative);
        }
        call->depth = (unsigned char)(tree_header[1] & RF_TREE_RECORD_DEPTH);
        call->result = RF_TREE_OK;
        report(call);
        return state_store();
    }
}

static unsigned char add_child(ReadyFsTreeCall *call) {
    unsigned int parent_len;
    unsigned int name_len;
    unsigned int length;
    unsigned int bytes;
    unsigned char depth;

    if (call->parent == 0 || call->name == 0 || call->output == 0 ||
        call->output_capacity == 0u || !state_fetch() ||
        tree_state.magic != RF_TREE_MAGIC) return 0u;
    parent_len = strlen(call->parent);
    name_len = strlen(call->name);
    depth = stem_depth(call->parent);
    length = (unsigned int)(parent_len + name_len +
                            (parent_len == 0u ? 0u : 1u));
    if (name_len == 0u || name_len > 255u || length > 255u ||
        length >= call->output_capacity || strchr(call->name, '/') != 0 ||
        strchr(call->name, '!') != 0 || strcmp(call->name, ".") == 0 ||
        strcmp(call->name, "..") == 0 ||
        (call->kind != RF_TREE_KIND_FILE &&
         call->kind != RF_TREE_KIND_DIR)) {
        call->result = RF_TREE_BAD_NAME;
        return 1u;
    }
    if (call->kind == RF_TREE_KIND_DIR && depth >= tree_state.max_depth) {
        call->result = RF_TREE_TOO_DEEP;
        return 1u;
    }
    if (tree_state.entries >= tree_state.limit) {
        tree_state.overflow = 1u;
        call->result = RF_TREE_FULL;
        (void)state_store();
        return 1u;
    }
    if (parent_len != 0u) {
        memcpy(call->output, call->parent, parent_len);
        call->output[parent_len++] = '/';
    }
    memcpy(call->output + parent_len, call->name,
           (unsigned int)(name_len + 1u));
    call->depth = (unsigned char)(depth + 1u);
    bytes = (unsigned int)(length + 3u);
    if (tree_state.used > RF_REU_TREE_QUEUE_BYTES ||
        bytes > (unsigned int)(RF_REU_TREE_QUEUE_BYTES - tree_state.used)) {
        tree_state.overflow = 1u;
        call->result = RF_TREE_FULL;
        (void)state_store();
        return 1u;
    }
    tree_header[0] = (unsigned char)length;
    tree_header[1] = call->depth;
    if (call->selected) tree_header[1] |= RF_TREE_RECORD_SELECTED;
    if (call->kind == RF_TREE_KIND_FILE) tree_header[1] |= RF_TREE_RECORD_FILE;
    if (!queue_store(tree_state.used, tree_header, sizeof(tree_header)) ||
        !queue_store((unsigned int)(tree_state.used + 2u), call->output,
                     (unsigned int)(length + 1u))) return 0u;
    tree_state.used = (unsigned int)(tree_state.used + bytes);
    if (call->kind == RF_TREE_KIND_DIR) ++tree_state.directories;
    else ++tree_state.files;
    ++tree_state.entries;
    if (call->selected) ++tree_state.selected_entries;
    call->result = RF_TREE_OK;
    report(call);
    if (!state_store()) return 0u;
#ifdef READYFS_TREE_SIDECAR
    if (call->display) {
        cputc(call->kind == RF_TREE_KIND_DIR ? '/' : ' ');
        cputs(call->output); cputs("\r\n");
    }
#endif
    return 1u;
}

unsigned int readyfs_tree_abi(void) { return RF_TREE_ABI; }

#ifdef READYFS_TREE_SIDECAR
static unsigned char render_status(ReadyFsTreeCall *call) {
    unsigned int flags;
    unsigned char i, name;
    extern unsigned char reu_available, overlay_available;
    extern unsigned char plan_loaded, help_loaded, backend_loaded, batch_loaded;
    flags = RF_STATUS_UTILITY | RF_STATUS_TREE;
    call->entries = 0u;
    call->limit = reu_available ? readyfs_reu_bank_count() : 0u;
    if (reu_available) {
        flags |= RF_STATUS_REU;
        for (i = 0u; i < 8u; ++i)
            if (readyfs_reu_session_fetch((unsigned int)i * 273u, &name, 1u) && name) ++call->entries;
    }
    if (overlay_available) flags |= RF_STATUS_OVERLAY;
    if (plan_loaded) flags |= RF_STATUS_PLAN;
    if (help_loaded) flags |= RF_STATUS_JOURNAL;
    if (backend_loaded) flags |= RF_STATUS_BACKEND;
    if (batch_loaded) flags |= RF_STATUS_BATCH;
    cputs("cwd "); cputs(call->parent); cputs("\r\n");
    cputs("aliases "); print_u16(call->entries); cputs("\r\n");
    cputs("reu "); print_u16(call->limit); cputs(" banks\r\n");
    cputs("ready:");
    if (flags & RF_STATUS_REU) cputs(" reu");
    if (flags & RF_STATUS_OVERLAY) cputs(" overlay");
    if (flags & RF_STATUS_PLAN) cputs(" plan");
    if (flags & RF_STATUS_JOURNAL) cputs(" journal");
    if (flags & RF_STATUS_BACKEND) cputs(" backend");
    if (flags & RF_STATUS_UTILITY) cputs(" utility");
    if (flags & RF_STATUS_TREE) cputs(" tree");
    if (flags & RF_STATUS_BATCH) cputs(" batch");
    cputs("\r\nlast result: ");
    print_u16(call->result);
    cputs("\r\n");
    return 1u;
}
#endif

unsigned char readyfs_tree_dispatch(ReadyFsTreeCall *call) {
    if (call == 0) return 0u;
#ifdef READYFS_TREE_SIDECAR
    if (call->operation == RF_TREE_CALL_STATUS) return render_status(call);
#endif
    if (call->operation == RF_TREE_CALL_INIT) return initialize(call);
    if (call->operation == RF_TREE_CALL_NEXT) return next_directory(call);
    if (call->operation == RF_TREE_CALL_ADD) return add_child(call);
    if (call->operation == RF_TREE_CALL_REPORT) {
        if (!state_fetch() || tree_state.magic != RF_TREE_MAGIC) return 0u;
        call->result = tree_state.overflow ? RF_TREE_FULL : RF_TREE_OK;
        report(call);
#ifdef READYFS_TREE_SIDECAR
        if (call->display) {
            if (call->display == 2u) {
                cputs(call->selected && call->result == RF_TREE_OK ?
                      RF_SUMMARY "find done n" : RF_ERROR "find failed n");
                print_u16(call->selected_entries); cputs(" f");
            } else cputs(call->selected && call->result == RF_TREE_OK ?
                         RF_SUMMARY "tree done f" : RF_ERROR "tree failed f");
            print_u16(call->files); cputs(" d");
            print_u16(call->directories); cputs("\r\n");
        }
#endif
        return 1u;
    }
    return 0u;
}

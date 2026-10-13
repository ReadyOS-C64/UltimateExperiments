#include "readyfs_script.h"
#include "readyfs_reu.h"
#include "readyfs_result.h"
#include <conio.h>
#include <string.h>

static ReadyFsBatchState state;
static char label[RF_SCRIPT_NAME + 1u];
static char variable_name[RF_SCRIPT_NAME + 1u];
static unsigned char cache[128];
static unsigned int cache_start, cache_size;
static unsigned char fetch_state(void) {
    return readyfs_reu_batch_fetch(RF_REU_BATCH_STATE_OFF, &state, sizeof(state));
}
static unsigned char store_state(void) {
    return readyfs_reu_batch_store(RF_REU_BATCH_STATE_OFF, &state, sizeof(state));
}
static unsigned char byte_at(unsigned int offset) {
    if (offset < cache_start || offset >= cache_start + cache_size) {
        cache_start = offset; cache_size = state.size - offset;
        if (cache_size > sizeof(cache)) cache_size = sizeof(cache);
        if (!readyfs_reu_batch_fetch(RF_REU_BATCH_DATA_OFF + offset, cache, cache_size)) return 0u;
    }
    return cache[offset - cache_start];
}
static unsigned char jump(const char *target) {
    unsigned int offset;
    unsigned char c, len;
    if (*target == ':') ++target;
    if (!*target || strlen(target) > RF_SCRIPT_NAME) return 0u;
    cache_size = 0u; cache_start = 0u; offset = 0u;
    while (offset < state.size) {
        while (offset < state.size && ((c = byte_at(offset)) == ' ' || c == '\t')) ++offset;
        len = 0u;
        if (offset < state.size && byte_at(offset) == ':') {
            ++offset;
            while (offset < state.size && (c = byte_at(offset)) != '\r' && c != '\n' && c != ' ' && c != '\t') {
                if (len < RF_SCRIPT_NAME) label[len++] = c;
                else len = RF_SCRIPT_NAME + 1u;
                ++offset;
            }
            if (len <= RF_SCRIPT_NAME) {
                label[len] = 0;
                if (readyfs_same_word(label, target)) {
                    while (offset < state.size && byte_at(offset) != '\r' && byte_at(offset) != '\n') ++offset;
                    state.offset = offset; return 1u;
                }
            }
        }
        while (offset < state.size && byte_at(offset) != '\r' && byte_at(offset) != '\n') ++offset;
        while (offset < state.size && (byte_at(offset) == '\r' || byte_at(offset) == '\n')) ++offset;
    }
    return 0u;
}
static unsigned char number(const char *text, unsigned int *out) {
    unsigned int n;
    if (!*text) return 0u;
    n = 0u;
    while (*text) {
        if (*text < '0' || *text > '9' || n > 6553u ||
            (n == 6553u && *text > '5')) return 0u;
        n = n * 10u + (unsigned char)(*text++ - '0');
    }
    *out = n; return 1u;
}
static unsigned char defined(const char *name) {
    unsigned char i;
    if (readyfs_same_word(name, "errorlevel")) return 1u;
    for (i = 0u; i < RF_SCRIPT_VARS; ++i) {
        if (!readyfs_reu_script_fetch(RF_SCRIPT_VARS_OFF + (unsigned int)i * RF_SCRIPT_RECORD_BYTES,
                                      variable_name, sizeof(variable_name))) return 0u;
        if (readyfs_same_word(name, variable_name) && variable_name[0]) return 1u;
    }
    return 0u;
}
static unsigned char error(ReadyFsBatchCall *call) {
    cputs("batch flow error\r\n");
    call->rc = RF_RESULT_USAGE; state.last_rc = call->rc;
    state.have_rc = state.stopped = 1u; call->action = RF_BATCH_SKIP;
    return store_state();
}
static void shift(ReadyFsBatchCall *call, unsigned char count) {
    unsigned char i;
    call->argc -= count;
    for (i = 0u; i < call->argc; ++i) call->args[i] = call->args[i + count];
}
unsigned int readyfs_flow_abi(void) { return RF_SCRIPT_ABI; }
unsigned char readyfs_flow(ReadyFsBatchCall *call) {
    unsigned char first, negate, yes;
    unsigned int left, right;
    char *equal;
    if (!fetch_state()) return 0u;
    if (kbhit() && cgetc() == CH_STOP) {
        state.last_rc = RF_RESULT_INTERACTION; state.have_rc = state.stopped = 1u;
        call->action = RF_BATCH_SKIP; return store_state();
    }
    call->action = RF_BATCH_SKIP;
    while (call->argc) {
        if (call->args[0][0] == ':' || call->args[0][0] == '#' ||
            readyfs_same_word(call->args[0], "rem")) return 1u;
        if (readyfs_same_word(call->args[0], "goto") || readyfs_same_word(call->args[0], "call")) {
            if (call->argc != 2u) return error(call);
            if (readyfs_same_word(call->args[0], "call")) {
                if (state.depth == RF_SCRIPT_DEPTH) return error(call);
                state.returns[state.depth++] = state.offset;
            } else if (readyfs_same_word(call->args[1], ":eof")) {
                if (state.depth) state.offset = state.returns[--state.depth];
                else state.stopped = 1u;
                return store_state();
            }
            if (!jump(call->args[1])) return error(call);
            return store_state();
        }
        if (readyfs_same_word(call->args[0], "exit")) {
            if (call->argc == 1u) { state.stopped = 1u; return store_state(); }
            if (call->argc < 2u || !readyfs_same_word(call->args[1], "/b") || call->argc > 3u) return error(call);
            if (call->argc == 3u) {
                if (!number(call->args[2], &right) || right > 255u) return error(call);
                state.last_rc = (unsigned char)right; state.have_rc = 1u;
            }
            if (state.depth) state.offset = state.returns[--state.depth];
            else state.stopped = 1u;
            return store_state();
        }
        if (!readyfs_same_word(call->args[0], "if")) {
            call->action = RF_BATCH_COMMAND; return 1u;
        }
        first = 1u; negate = 0u;
        if (call->argc > first && readyfs_same_word(call->args[first], "not")) { negate = 1u; ++first; }
        if (call->argc <= first + 1u) return error(call);
        if (readyfs_same_word(call->args[first], "errorlevel")) {
            if (!number(call->args[first + 1u], &right) || right > 255u) return error(call);
            yes = state.last_rc >= right; first += 2u;
        } else if (readyfs_same_word(call->args[first], "defined")) {
            yes = defined(call->args[first + 1u]); first += 2u;
        } else if (readyfs_same_word(call->args[first], "exist")) {
            call->test = call->args[first + 1u]; first += 2u;
            if (call->argc <= first) return error(call);
            shift(call, first); call->finish = negate; call->action = RF_BATCH_EXISTS;
            return 1u;
        } else if ((equal = strstr(call->args[first], "==")) != 0) {
            *equal = 0;
            yes = strcmp(call->args[first], equal + 2u) == 0; ++first;
        } else if (call->argc > first + 3u && readyfs_same_word(call->args[first + 1u], "==")) {
            yes = strcmp(call->args[first], call->args[first + 2u]) == 0; first += 3u;
        } else {
            if (call->argc <= first + 3u || !number(call->args[first], &left) ||
                !number(call->args[first + 2u], &right)) return error(call);
            equal = call->args[first + 1u];
            if (readyfs_same_word(equal, "equ")) yes = left == right;
            else if (readyfs_same_word(equal, "neq")) yes = left != right;
            else if (readyfs_same_word(equal, "lss")) yes = left < right;
            else if (readyfs_same_word(equal, "leq")) yes = left <= right;
            else if (readyfs_same_word(equal, "gtr")) yes = left > right;
            else if (readyfs_same_word(equal, "geq")) yes = left >= right;
            else return error(call);
            first += 3u;
        }
        if (call->argc <= first) return error(call);
        if (yes == negate) return 1u;
        shift(call, first);
    }
    return 1u;
}

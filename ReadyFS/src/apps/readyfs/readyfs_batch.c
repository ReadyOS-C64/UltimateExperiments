#include "readyfs_console.h"
#include "readyfs_batch.h"

#include "readyfs_reu.h"
#include "readyfs_result.h"
#include "readyfs_path.h"

#include <conio.h>
#include <string.h>

#define RF_BATCH_MAGIC 0x42u
#define RF_BATCH_POLICY_STOP 1u
#define RF_CH_END 147u

typedef struct {
    unsigned char magic;
    unsigned char policy;
    unsigned char have_rc;
    unsigned char last_rc;
    unsigned char stopped;
    unsigned int size;
    unsigned int offset;
    unsigned int lines;
} ReadyFsBatchState;

static ReadyFsBatchState state;

static unsigned char state_fetch(void) {
    return readyfs_reu_batch_fetch(RF_REU_BATCH_STATE_OFF, &state,
                                   sizeof(state));
}

static unsigned char state_store(void) {
    return readyfs_reu_batch_store(RF_REU_BATCH_STATE_OFF, &state,
                                   sizeof(state));
}

#ifdef __CC65__
extern unsigned char __fastcall__ readyfs_same_word(const char *left, const char *right);
#define same_word readyfs_same_word
#else
static unsigned char same_word(const char *left, const char *right) {
    unsigned char a;
    unsigned char b;
    while (*left != 0 && *right != 0) {
        a = (unsigned char)*left++;
        b = (unsigned char)*right++;
        if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + 32u);
        if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + 32u);
        if (a != b) return 0u;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

#endif

static unsigned char split_args(ReadyFsBatchCall *call) {
    unsigned char count;
    unsigned char quote;
    char *readp;
    char *writep;

    count = 0u;
    readp = call->buffer;
    writep = call->buffer;
    while (*readp != 0 && count < 12u) {
        while (*readp == ' ') ++readp;
        if (*readp == 0) break;
        call->args[count++] = writep;
        quote = 0u;
        if (*readp == '"') { quote = 1u; ++readp; }
        while (*readp != 0) {
            if (quote) {
                if (*readp == '"') { ++readp; break; }
            } else if (*readp == ' ') break;
            *writep++ = *readp++;
        }
        if (!quote && *readp == ' ') ++readp;
        *writep++ = 0;
        while (*readp == ' ') ++readp;
    }
    return count;
}

static void set_error(void) {
    state.last_rc = RF_RESULT_INTERACTION;
    state.have_rc = 1u;
    if (state.policy == RF_BATCH_POLICY_STOP) state.stopped = 1u;
}

static unsigned char read_script_line(ReadyFsBatchCall *call) {
    unsigned int length;
    unsigned char value;

    length = 0u;
    while (state.offset < state.size) {
        if (!readyfs_reu_batch_fetch(
                (unsigned int)(RF_REU_BATCH_DATA_OFF + state.offset),
                &value, 1u)) return 0u;
        ++state.offset;
        if (value == '\r' || value == '\n') {
            call->buffer[length] = 0;
            ++state.lines;
            return 1u;
        }
        if (length + 1u >= call->capacity) {
            cputs(RF_ERROR "line too long\r\n");
            set_error();
            return 0u;
        }
        call->buffer[length++] = (char)value;
    }
    call->buffer[length] = 0;
    ++state.lines;
    return 1u;
}

static unsigned char initialize(ReadyFsBatchCall *call) {
    if (call->size > RF_REU_BATCH_DATA_BYTES) return 0u;
    memset(&state, 0, sizeof(state));
    state.magic = RF_BATCH_MAGIC;
    state.policy = RF_BATCH_POLICY_STOP;
    state.size = call->size;
    return state_store();
}

static unsigned char next(ReadyFsBatchCall *call) {
    unsigned char expected;
    if (call->buffer == 0 || call->args == 0 || call->capacity < 2u ||
        !state_fetch() || state.magic != RF_BATCH_MAGIC) return 0u;
    call->action = RF_BATCH_DONE;
    while (!state.stopped && state.offset < state.size) {
        if (!read_script_line(call)) {
            (void)state_store();
            return state.stopped ? 1u : 0u;
        }
        call->argc = split_args(call);
        if (call->argc == 0u || call->args[0][0] == '#') continue;
        if (same_word(call->args[0], "onerror")) {
            if (call->argc == 2u && same_word(call->args[1], "stop"))
                state.policy = RF_BATCH_POLICY_STOP;
            else if (call->argc == 2u && same_word(call->args[1], "continue"))
                state.policy = 0u;
            else { cputs("onerror stop|continue\r\n"); set_error(); }
            continue;
        }
        if (same_word(call->args[0], "expect")) {
            if (call->argc != 3u || !same_word(call->args[1], "rc") ||
                call->args[2][0] < '0' || call->args[2][0] > '9' ||
                call->args[2][1] != 0 || !state.have_rc) {
                cputs("expect rc N after command\r\n");
                set_error();
            } else if ((expected = (unsigned char)(call->args[2][0] - '0')) ==
                       state.last_rc) cputs("expect rc ok\r\n");
            else { cputs(RF_ERROR "expect rc mismatch\r\n"); set_error(); }
            continue;
        }
        if (same_word(call->args[0], "run") ||
            same_word(call->args[0], "ru")) {
            cputs(RF_ERROR "nested run off\r\n");
            set_error();
            continue;
        }
        call->action = RF_BATCH_COMMAND;
        return state_store();
    }
    return state_store();
}

static unsigned char acknowledge(ReadyFsBatchCall *call) {
    if (!state_fetch() || state.magic != RF_BATCH_MAGIC) return 0u;
    state.last_rc = call->rc;
    state.have_rc = 1u;
    if (call->finish || (call->rc != 0u &&
                         state.policy == RF_BATCH_POLICY_STOP))
        state.stopped = 1u;
    return state_store();
}

static unsigned char report(ReadyFsBatchCall *call) {
    if (!state_fetch() || state.magic != RF_BATCH_MAGIC) return 0u;
    call->size = state.lines;
    call->rc = state.have_rc ? state.last_rc : 0u;
    return 1u;
}

typedef struct { char name[17]; char root[256]; } UiAlias;
static UiAlias alias;
static unsigned char alias_fetch(unsigned char slot) {
    return readyfs_reu_session_fetch((unsigned int)slot * sizeof(alias),
                                      &alias, sizeof(alias));
}
static unsigned char alias_store(unsigned char slot) {
    return readyfs_reu_session_store((unsigned int)slot * sizeof(alias),
                                      &alias, sizeof(alias));
}
static unsigned char alias_command(ReadyFsBatchCall *call) {
    unsigned char i, empty, found, len;
    ReadyFsPath path;
    if (!call->reu_available) { cputs(RF_ERROR "need reu\r\n"); return 1u; }
    if (!call->finish && call->argc == 1u) {
        for (i=0u;i<8u;++i) if (alias_fetch(i) && alias.name[0]) {
            cputc('@'); cputs(alias.name); cputs(": "); cputs(alias.root); cputs("\r\n");
        }
        return 1u;
    }
    if (call->argc < (call->finish ? 2u : 3u)) {
        cputs(call->finish ? "unalias N\r\n" : "alias N PATH\r\n"); return 1u;
    }
    len = strlen(call->args[1]);
    if (!len || len > 16u || strchr(call->args[1], ':') ||
        strchr(call->args[1], '/') || strchr(call->args[1], '@')) {
        cputs(RF_ERROR "bad alias\r\n"); return 1u;
    }
    if (!call->finish && (readyfs_path_parse(call->buffer, &path) != RF_PATH_OK ||
        path.endpoint == RF_EP_ALIAS || !path.absolute)) {
        cputs("abs root\r\n"); return 1u;
    }
    empty = found = 255u;
    for (i=0u;i<8u;++i) if (alias_fetch(i)) {
        if (!alias.name[0] && empty == 255u) empty = i;
        if (same_word(alias.name, call->args[1])) { found=i; break; }
    }
    if (call->finish) {
        if (found == 255u) { cputs(RF_ERROR "noalias\r\n"); return 1u; }
        memset(&alias, 0, sizeof(alias));
    } else {
        if (found == 255u) found = empty;
        if (found == 255u) { cputs(RF_ERROR "aliases full\r\n"); return 1u; }
        strcpy(alias.name, call->args[1]); strcpy(alias.root, call->buffer);
    }
    if (!alias_store(found)) cputs("alias reu\r\n");
    else cputs(call->finish ? RF_SUMMARY "removed\r\n" : RF_SUMMARY "alias set\r\n");
    return 1u;
}

unsigned int readyfs_batch_abi(void) { return RF_BATCH_ABI; }

unsigned char readyfs_batch_dispatch(ReadyFsBatchCall *call) {
    if (call == 0) return 0u;
    if (call->operation == RF_BATCH_ALIAS) return alias_command(call);
    if (call->operation == RF_BATCH_INIT) return initialize(call);
    if (call->operation == RF_BATCH_NEXT) return next(call);
    if (call->operation == RF_BATCH_ACK) return acknowledge(call);
    if (call->operation == RF_BATCH_REPORT) return report(call);
    return 0u;
}

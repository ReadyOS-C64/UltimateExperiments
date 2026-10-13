#include "readyfs_tape.h"
#include "readyfs_reu.h"

#include <string.h>

/* cc65 Commodore file-type values, kept explicit so the pure host oracle and the
 * target sidecar share the exact ABI without a host-only compatibility shim. */
#define TAPE_CBM_SEQ 0x10u
#define TAPE_CBM_PRG 0x11u
#define TAPE_CBM_USR 0x12u
#define TAPE_CBM_REL 0x13u

/* Pure tape/core sidecar.  KERNAL device-1 and all other filesystem I/O stay
 * resident; this overlay owns only bounded transfer signatures and policy. */

unsigned int readyfs_tape_abi(void) { return RF_TAPE_ABI; }

static unsigned char same_word(const char *left, const char *right) {
    unsigned char a;
    unsigned char b;
    while (*left != 0 && *right != 0) {
        a = (unsigned char)*left++ & 0x7Fu;
        b = (unsigned char)*right++ & 0x7Fu;
        if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + 32u);
        if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + 32u);
        if (a != b) return 0u;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

static unsigned char option_present(ReadyFsTapeCall *call) {
    unsigned char i;
    unsigned char accept_yes;
    accept_yes = same_word(call->text, "--force");
    for (i = 1u; i < call->argc; ++i) {
        if (same_word(call->args[i], call->text) ||
            (accept_yes && same_word(call->args[i], "--yes"))) return 1u;
    }
    return 0u;
}

#ifndef __CC65__
static void open_name(ReadyFsTapeCall *call) {
    static const char letters[4] = { 's', 'p', 'u', 'l' };
    unsigned char len;
    strcpy(call->output, call->text);
    len = strlen(call->output);
    call->output[len++] = ',';
    call->output[len++] = letters[call->value & 3u];
    call->output[len++] = ',';
    call->output[len++] = (char)call->value2;
    call->output[len] = 0;
}
#else
extern unsigned char __fastcall__
readyfs_tape_open_name_dispatch(ReadyFsTapeCall *call);
#endif

static void path_prepare(ReadyFsTapeCall *call) {
    char *name;
    unsigned char rc;

    rc = readyfs_path_parse(call->text, call->path);
    if (rc != RF_PATH_OK) {
        call->result = rc;
        call->value = 0u;
        return;
    }
    call->value = 1u;
    if (!call->path->absolute ||
        (call->path->endpoint != RF_EP_IEC &&
         call->path->endpoint != RF_EP_SOFTIEC &&
         call->path->endpoint != RF_EP_ULTIMATE &&
         call->path->endpoint != RF_EP_TAPE)) {
        call->result = RF_TAPE_PATH_UNSUPPORTED;
        return;
    }
    name = (char *)call->text + call->path->path_offset;
    if (call->path->endpoint == RF_EP_IEC ||
        call->path->endpoint == RF_EP_TAPE) while (*name == '/') ++name;
    else if (call->path->endpoint == RF_EP_SOFTIEC)
        name = (char *)call->text + 1u;
    call->found = name;
    if (*name == 0 || (call->path->endpoint == RF_EP_ULTIMATE &&
                       name[0] == '/' && name[1] == 0)) {
        call->result = RF_TAPE_PATH_REQUIRED;
    } else if (call->path->endpoint == RF_EP_IEC &&
               (strchr(name, '/') != 0 || strchr(name, '!') != 0)) {
        call->result = RF_TAPE_PATH_CMD;
    } else if (call->path->endpoint == RF_EP_ULTIMATE &&
               strchr(name, '!') != 0) {
        call->result = RF_TAPE_PATH_IMAGE;
    } else if (call->path->endpoint == RF_EP_TAPE &&
               (strlen(name) > 16u || strchr(name, '/') != 0 ||
                strchr(name, '!') != 0)) {
        call->result = RF_TAPE_PATH_LEAF;
    } else call->result = RF_TAPE_PATH_OK;
}

static void signature_add(ReadyFsSignature *sig,
                          const unsigned char *data,
                          unsigned int len) {
    unsigned int before;
    unsigned int crc;
    unsigned int i;
    unsigned char bit;

    before = sig->bytes_lo;
    sig->bytes_lo = (unsigned int)(sig->bytes_lo + len);
    if (sig->bytes_lo < before) ++sig->bytes_hi;
    crc = sig->crc;
    for (i = 0u; i < len; ++i) {
        crc ^= (unsigned int)data[i] << 8u;
        for (bit = 0u; bit < 8u; ++bit) {
            if (crc & 0x8000u)
                crc = (unsigned int)((crc << 1u) ^ 0x1021u);
            else crc <<= 1u;
        }
    }
    sig->crc = crc;
}

#ifdef __CC65__
extern unsigned char __fastcall__
readyfs_tape_spool_dispatch(ReadyFsTapeCall *call);
#else
static unsigned char spool_transfer(ReadyFsTapeCall *call) {
    ReadyFsTapeSpoolState *state;
    unsigned int bank_count;
    unsigned int before;
    unsigned int end;
    unsigned int amount;
    unsigned char saved_bank;

    state = call->spool;
    if (call->operation == RF_TAPE_SPOOL_INIT) {
        memset(state, 0, sizeof(*state));
        call->length = 0u;
        return 1u;
    }
    if (call->data == 0 || call->length == 0u) return 0u;
    bank_count = readyfs_reu_bank_count();
    if (call->operation == RF_TAPE_SPOOL_STORE) {
        /* Banks count-4 through count-1 hold console and overlay state. */
        end = (state->bytes_lo + call->length) & 0xFFFFu;
        if ((unsigned int)state->bytes_bank + 5u >= bank_count ||
            (end < state->bytes_lo && end != 0u &&
             (unsigned int)state->bytes_bank + 6u >= bank_count)) return 0u;
        saved_bank = readyfs_reu_batch_bank_value;
        readyfs_reu_batch_bank_value = (unsigned char)(state->bytes_bank + 1u);
        call->result = readyfs_reu_batch_store(state->bytes_lo, call->data,
                                               call->length);
        readyfs_reu_batch_bank_value = saved_bank;
        if (!call->result) return 0u;
        before = state->bytes_lo;
        state->bytes_lo = end;
        if (state->bytes_lo < before) ++state->bytes_bank;
        return 1u;
    }
    if (state->replay_bank > state->bytes_bank ||
        (state->replay_bank == state->bytes_bank &&
         state->replay_lo >= state->bytes_lo)) {
        call->length = 0u;
        return 1u;
    }
    amount = call->length;
    if (state->replay_bank == state->bytes_bank &&
        amount > (unsigned int)(state->bytes_lo - state->replay_lo))
        amount = (unsigned int)(state->bytes_lo - state->replay_lo);
    if ((unsigned int)state->replay_bank + 1u == state->bytes_bank &&
        state->bytes_lo < state->replay_lo &&
        amount > ((state->bytes_lo - state->replay_lo) & 0xFFFFu))
        amount = (state->bytes_lo - state->replay_lo) & 0xFFFFu;
    end = (state->replay_lo + amount) & 0xFFFFu;
    if ((unsigned int)state->replay_bank + 5u >= bank_count ||
        (end < state->replay_lo && end != 0u &&
         (unsigned int)state->replay_bank + 6u >= bank_count)) return 0u;
    saved_bank = readyfs_reu_batch_bank_value;
    readyfs_reu_batch_bank_value = (unsigned char)(state->replay_bank + 1u);
    call->result = readyfs_reu_batch_fetch(state->replay_lo,
                                           (void *)call->data, amount);
    readyfs_reu_batch_bank_value = saved_bank;
    if (!call->result) return 0u;
    before = state->replay_lo;
    state->replay_lo = end;
    if (state->replay_lo < before) ++state->replay_bank;
    call->length = amount;
    return 1u;
}
#endif

static unsigned char split_args(ReadyFsTapeCall *call) {
    unsigned char count;
    unsigned char quote;
    char *readp;
    char *writep;

    count = 0u;
    readp = (char *)call->text;
    writep = readp;
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

static unsigned char designator(ReadyFsTapeCall *call) {
    ReadyFsPath path;
    if (readyfs_path_parse(call->text, &path) != RF_PATH_OK ||
        path.endpoint != call->value ||
        (call->value == RF_EP_IEC && path.partition != 0u) ||
        call->text[path.path_offset] != 0) return 0u;
    *call->output = (char)path.unit;
    return 1u;
}

unsigned char readyfs_tape_dispatch(ReadyFsTapeCall *call) {
    if (call == 0) return 0u;
    if (call->operation == RF_TAPE_SIGNATURE_INIT &&
        call->signature != 0) {
        call->signature->bytes_lo = 0u;
        call->signature->bytes_hi = 0u;
        call->signature->crc = 0xFFFFu;
        call->result = 1u;
    } else if (call->operation == RF_TAPE_SIGNATURE_ADD &&
               call->signature != 0 &&
               (call->data != 0 || call->length == 0u)) {
        signature_add(call->signature, call->data, call->length);
        call->result = 1u;
    } else if (call->operation == RF_TAPE_SIGNATURE_EQUAL &&
               call->signature != 0 &&
               call->other != 0) {
        call->result = (unsigned char)
            (call->signature->bytes_lo == call->other->bytes_lo &&
             call->signature->bytes_hi == call->other->bytes_hi &&
             call->signature->crc == call->other->crc);
    } else if (call->operation == RF_TAPE_OPTION_PRESENT &&
               call->args != 0 && call->text != 0) {
        call->result = option_present(call);
    } else if (call->operation == RF_TAPE_OPTION_VALUE &&
               call->args != 0 && call->text != 0) {
        unsigned char i;
        call->found = 0;
        for (i = 1u; i + 1u < call->argc; ++i) {
            if (same_word(call->args[i], call->text)) {
                call->found = call->args[i + 1u];
                break;
            }
        }
    } else if (call->operation == RF_TAPE_OPEN_NAME &&
               call->text != 0 && call->output != 0) {
#ifdef __CC65__
        call->result = readyfs_tape_open_name_dispatch(call);
#else
        open_name(call);
        call->result = 1u;
#endif
    } else if (call->operation == RF_TAPE_PATH_PREPARE &&
               call->text != 0 && call->path != 0) {
        path_prepare(call);
    } else if (call->operation == RF_TAPE_FILE_TYPE && call->args != 0) {
        unsigned char i;
        call->found = 0;
        for (i = 1u; i + 1u < call->argc; ++i) {
            if (same_word(call->args[i], "--type")) {
                call->found = call->args[i + 1u];
                break;
            }
        }
        if (call->found == 0 || same_word(call->found, "seq"))
            call->result = TAPE_CBM_SEQ;
        else if (same_word(call->found, "prg"))
            call->result = TAPE_CBM_PRG;
        else if (same_word(call->found, "usr"))
            call->result = TAPE_CBM_USR;
        else call->result = 0xFFu;
    } else if (call->operation == RF_TAPE_SAME_WORD &&
               call->text != 0 && call->text2 != 0) {
        call->result = same_word(call->text, call->text2);
    } else if (call->operation >= RF_TAPE_SPOOL_INIT &&
               call->operation <= RF_TAPE_SPOOL_FETCH && call->spool != 0) {
#ifdef __CC65__
        call->result = readyfs_tape_spool_dispatch(call);
#else
        call->result = spool_transfer(call);
#endif
    } else if (call->operation == RF_TAPE_SPLIT_ARGS &&
               call->text != 0 && call->args != 0) {
        call->result = split_args(call);
    } else if (call->operation == RF_TAPE_DESIGNATOR &&
               call->text != 0 && call->output != 0) {
        call->result = designator(call);
    } else return 0u;
    return 1u;
}

#include "readyfs_script.h"
#include "readyfs_reu.h"
#include "readyfs_result.h"
#include <conio.h>
#include <string.h>

static char expanded[256];
static ReadyFsVariable variable;
static char name[RF_SCRIPT_NAME + 1u];
static unsigned int used;

static unsigned char add(const char *text) {
    unsigned int len;
    len = strlen(text);
    if (used + len >= sizeof(expanded)) return 0u;
    memcpy(expanded + used, text, len); used += len;
    return 1u;
}
static unsigned char syntax(ReadyFsBatchCall *call) {
    call->rc = RF_RESULT_USAGE;
    call->action = RF_BATCH_ERROR;
    cputs("bad expansion/quotes/args\r\n");
    return 1u;
}
static unsigned char tokenize(ReadyFsBatchCall *call) {
    char *readp, *writep;
    unsigned char quote, count;
    readp = writep = call->buffer; count = 0u;
    while (*readp) {
        while (*readp == ' ' || *readp == '\t') ++readp;
        if (!*readp) break;
        if (count == 12u) return syntax(call);
        call->args[count++] = writep;
        quote = 0u;
        while (*readp && (quote || (*readp != ' ' && *readp != '\t'))) {
            if (*readp == '"') { quote = !quote; ++readp; }
            else *writep++ = *readp++;
        }
        if (quote) return syntax(call);
        if (*readp) ++readp;
        *writep++ = 0;
    }
    call->argc = count;
    call->action = count ? RF_BATCH_COMMAND : RF_BATCH_SKIP;
    return 1u;
}
unsigned int readyfs_expand_abi(void) { return RF_SCRIPT_ABI; }
unsigned char readyfs_expand(ReadyFsBatchCall *call) {
    char *p;
    unsigned char i, len, number, prior;
    unsigned int index;
    if (call->operation == RF_ENV_ARGUMENTS) {
        /* Store %0 and up to nine arguments before RUN reuses line_buf. */
        if (call->argc < 2u || call->argc > 11u) return syntax(call);
        for (i = 0u; i < 10u; ++i) {
            memset(expanded, 0, sizeof(expanded));
            if (i + 1u < call->argc) strcpy(expanded, call->args[i + 1u]);
            if (!readyfs_reu_script_store(RF_SCRIPT_ARGS_OFF + (unsigned int)i * 256u,
                                          expanded, sizeof(expanded))) return 0u;
        }
        return 1u;
    }
    prior = call->rc; call->rc = 0u;
    p = call->buffer; used = 0u;
    /* Comment text never triggers expansion or quote errors. */
    while (*p == ' ' || *p == '\t') ++p;
    if (*p == '#' || *p == ':') { call->argc = 0u; call->action = RF_BATCH_SKIP; call->rc = prior; return 1u; }
    if (strlen(p) >= 3u) {
        memcpy(name, p, 3u); name[3] = 0;
        if (readyfs_same_word(name, "rem") && (!p[3] || p[3] == ' ' || p[3] == '\t')) {
            call->argc = 0u; call->action = RF_BATCH_SKIP; call->rc = prior; return 1u;
        }
    }
    while (*p) {
        if (*p != '%') {
            if (used + 1u >= sizeof(expanded)) return syntax(call);
            expanded[used++] = *p++; continue;
        }
        ++p;
        if (*p == '%') {
            if (used + 1u >= sizeof(expanded)) return syntax(call);
            expanded[used++] = *p++; continue;
        }
        if (*p >= '0' && *p <= '9') {
            number = (unsigned char)(*p++ - '0');
            if (!call->finish) { /* Interactive context has no positional arguments. */
                continue;
            }
            index = RF_SCRIPT_ARGS_OFF + (unsigned int)number * 256u;
            /* Read through a bounded value scratch; args are max 255 bytes. */
            for (i = 0u; ; ++i) {
                char c;
                if (!readyfs_reu_script_fetch(index++, &c, 1u)) return 0u;
                if (!c) break;
                if (used + 1u >= sizeof(expanded)) return syntax(call);
                expanded[used++] = c;
                if (i == 254u) break;
            }
            continue;
        }
        len = 0u;
        while (*p && *p != '%') {
            if (len == RF_SCRIPT_NAME) return syntax(call);
            name[len++] = *p++;
        }
        if (!*p || !len) return syntax(call);
        ++p; name[len] = 0;
        if (readyfs_same_word(name, "errorlevel")) {
            number = prior; len = 0u;
            if (number >= 100u) { name[len++] = '0' + number / 100u; number %= 100u; }
            if (prior >= 10u) { name[len++] = '0' + number / 10u; number %= 10u; }
            name[len++] = '0' + number; name[len] = 0;
            if (!add(name)) return syntax(call);
        } else for (i = 0u; i < RF_SCRIPT_VARS; ++i) {
            if (!readyfs_reu_script_fetch(RF_SCRIPT_VARS_OFF + (unsigned int)i * RF_SCRIPT_RECORD_BYTES,
                                          &variable, sizeof(variable))) return 0u;
            if (readyfs_same_word(name, variable.name)) {
                if (!add(variable.value)) return syntax(call);
                break;
            }
        }
    }
    expanded[used] = 0;
    if (used >= call->capacity) return syntax(call);
    memcpy(call->buffer, expanded, used + 1u);
    i = tokenize(call);
    if (call->action == RF_BATCH_SKIP) call->rc = prior;
    return i;
}

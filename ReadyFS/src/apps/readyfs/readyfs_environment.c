#include "readyfs_script.h"
#include "readyfs_reu.h"
#include "readyfs_result.h"
#include <conio.h>
#include <string.h>

static ReadyFsVariable item;
static ReadyFsVariable candidate;

static unsigned int slot(unsigned int base, unsigned char index) {
    return base + (unsigned int)index * RF_SCRIPT_RECORD_BYTES;
}
static unsigned char fetch(unsigned int base, unsigned char index) {
    return readyfs_reu_script_fetch(slot(base, index), &item, sizeof(item));
}
static unsigned char store(unsigned int base, unsigned char index) {
    return readyfs_reu_script_store(slot(base, index), &item, sizeof(item));
}
static unsigned char valid_name(const char *name) {
    unsigned char c, len;
    len = 0u;
    while ((c = (unsigned char)*name++) != 0u) {
        if (++len > RF_SCRIPT_NAME ||
            !((c >= 0x41u && c <= 0x5Au) ||
              (c >= 0x61u && c <= 0x7Au) || c == '_' ||
              (len > 1u && c >= '0' && c <= '9'))) return 0u;
    }
    return len != 0u;
}
static unsigned char find(unsigned int base, const char *name) {
    unsigned char i;
    for (i = 0u; i < RF_SCRIPT_VARS; ++i) {
        if (!fetch(base, i)) break;
        if (readyfs_same_word(item.name, name)) return i;
    }
    return RF_SCRIPT_VARS;
}
static unsigned char empty(unsigned int base) {
    unsigned char i;
    for (i = 0u; i < RF_SCRIPT_VARS; ++i)
        if (fetch(base, i) && !item.name[0]) return i;
    return RF_SCRIPT_VARS;
}
static unsigned char error(ReadyFsBatchCall *call) {
    call->rc = RF_RESULT_USAGE;
    cputs("bad set/config variable\r\n");
    return 1u;
}
static unsigned char integer(const char *text, unsigned int *out) {
    unsigned int n;
    if (valid_name(text)) {
        if (find(RF_SCRIPT_VARS_OFF, text) == RF_SCRIPT_VARS) { *out = 0u; return 1u; }
        text = item.value;
    }
    if (!*text) return 0u;
    n = 0u;
    while (*text) {
        if (*text < '0' || *text > '9' || n > 6553u || (n == 6553u && *text > '5')) return 0u;
        n = n * 10u + (unsigned char)(*text++ - '0');
    }
    *out = n; return 1u;
}
static unsigned char arithmetic(char *text) {
    char *op;
    char digits[6];
    unsigned char count, subtract;
    unsigned int left, right;
    op = strpbrk(text, "+-");
    if (op) {
        subtract = *op == '-'; *op++ = 0;
        if (!integer(text, &left) || !integer(op, &right)) return 0u;
        left = (subtract ? left - right : left + right) & 65535u;
    } else if (!integer(text, &left)) return 0u;
    count = 0u;
    do { digits[count++] = '0' + left % 10u; left /= 10u; } while (left);
    right = 0u;
    while (count) candidate.value[right++] = digits[--count];
    candidate.value[right] = 0;
    return 1u;
}
static unsigned char command(ReadyFsBatchCall *call) {
    unsigned char first, i, index, persist, math;
    char *equal;
    unsigned int len;
    call->action = RF_BATCH_COMMAND;
    if (!call->argc) { call->action = RF_BATCH_SKIP; return 1u; }
    if (call->argc == 2u && (readyfs_same_word(call->args[0], "help") || readyfs_same_word(call->args[0], "h"))) {
        static const char * const topics[] = { "batch", "set", "echo", "if", "goto", "call", "run" };
        for (i = 0u; i < 7u; ++i) if (readyfs_same_word(call->args[1], topics[i])) {
            call->action = RF_BATCH_HELP; return 1u;
        }
    }
    if (readyfs_same_word(call->args[0], "rem")) {
        call->action = RF_BATCH_SKIP; return 1u;
    }
    if (readyfs_same_word(call->args[0], "echo")) {
        for (i = 1u; i < call->argc; ++i) {
            if (i > 1u) cputc(' ');
            cputs(call->args[i]);
        }
        cputs("\r\n"); call->action = RF_BATCH_SKIP; return 1u;
    }
    if (!readyfs_same_word(call->args[0], "set")) return 1u;
    call->action = RF_BATCH_SKIP;
    persist = math = 0u; first = 1u;
    while (call->argc > first && call->args[first][0] == '/') {
        if (readyfs_same_word(call->args[first], "/p")) persist = 1u;
        else if (readyfs_same_word(call->args[first], "/a")) math = 1u;
        else return error(call);
        ++first;
    }
    if (call->argc == first) {
        for (i = 0u; i < RF_SCRIPT_VARS; ++i) if (fetch(RF_SCRIPT_VARS_OFF, i) && item.name[0]) {
            if (item.persistent) cputs("/p ");
            cputs(item.name); cputc('='); cputs(item.value); cputs("\r\n");
        }
        return 1u;
    }
    equal = strchr(call->args[first], '=');
    if (!equal) {
        if (call->argc != first + 1u || !valid_name(call->args[first])) return error(call);
        index = find(RF_SCRIPT_VARS_OFF, call->args[first]);
        if (index < RF_SCRIPT_VARS) { cputs(item.value); cputs("\r\n"); }
        else call->rc = RF_RESULT_NOT_FOUND;
        return 1u;
    }
    *equal++ = 0;
    if (!valid_name(call->args[first]) || readyfs_same_word(call->args[first], "errorlevel")) return error(call);
    memset(&candidate, 0, sizeof(candidate));
    strcpy(candidate.name, call->args[first]);
    candidate.persistent = persist;
    len = strlen(equal);
    if (len > RF_SCRIPT_VALUE) return error(call);
    strcpy(candidate.value, equal);
    for (i = first + 1u; i < call->argc; ++i) {
        len += 1u + strlen(call->args[i]);
        if (len > RF_SCRIPT_VALUE) return error(call);
        strcat(candidate.value, " "); strcat(candidate.value, call->args[i]);
    }
    if (math && (call->argc != first + 1u || !arithmetic(equal))) return error(call);
    index = find(RF_SCRIPT_VARS_OFF, candidate.name);
    if (!candidate.value[0] && index == RF_SCRIPT_VARS) return 1u;
    if (index == RF_SCRIPT_VARS) index = empty(RF_SCRIPT_VARS_OFF);
    if (index == RF_SCRIPT_VARS) { call->rc = RF_RESULT_CONFLICT; return 1u; }
    memcpy(&item, &candidate, sizeof(item));
    if (!item.value[0]) memset(&item, 0, sizeof(item));
    return store(RF_SCRIPT_VARS_OFF, index);
}

unsigned int readyfs_environment_abi(void) { return RF_SCRIPT_ABI; }
unsigned char readyfs_environment(ReadyFsBatchCall *call) {
    unsigned char i, j;
    if (call->operation == RF_ENV_COMMAND) return command(call);
    if (call->operation == RF_ENV_INIT) {
        memset(&item, 0, sizeof(item));
        for (i = 0u; i < RF_SCRIPT_VARS; ++i) if (!store(RF_SCRIPT_VARS_OFF, i)) return 0u;
        return 1u;
    }
    i = (unsigned char)call->size;
    if (call->operation == RF_ENV_EXPORT) {
        if (i >= RF_SCRIPT_VARS || !fetch(RF_SCRIPT_VARS_OFF, i)) return 0u;
        if (!item.persistent) memset(&item, 0, sizeof(item));
        memcpy(call->buffer, &item, sizeof(item)); return 1u;
    }
    if (call->operation == RF_ENV_STAGE) {
        if (i >= RF_SCRIPT_VARS) return 0u;
        memcpy(&item, call->buffer, sizeof(item));
        if (item.name[RF_SCRIPT_NAME] || item.value[RF_SCRIPT_VALUE] ||
            item.persistent > 1u || (item.name[0] && (!valid_name(item.name) ||
            !item.persistent || !item.value[0] || readyfs_same_word(item.name, "errorlevel")))) return error(call);
        return store(RF_SCRIPT_STAGE_OFF, i);
    }
    if (call->operation == RF_ENV_MERGE) {
        /* Build a complete replacement before touching live variables. */
        memset(&item, 0, sizeof(item));
        for (i = 0u; i < RF_SCRIPT_VARS; ++i) if (!store(RF_SCRIPT_MERGE_OFF, i)) return 0u;
        for (i = 0u; i < RF_SCRIPT_VARS; ++i) {
            if (!fetch(RF_SCRIPT_STAGE_OFF, i)) return 0u;
            if (!item.name[0]) continue;
            memcpy(&candidate, &item, sizeof(item));
            if (find(RF_SCRIPT_MERGE_OFF, candidate.name) != RF_SCRIPT_VARS) return error(call);
            memcpy(&item, &candidate, sizeof(item));
            if (!store(RF_SCRIPT_MERGE_OFF, i)) return 0u;
        }
        for (i = 0u; i < RF_SCRIPT_VARS; ++i) {
            if (!fetch(RF_SCRIPT_VARS_OFF, i)) return 0u;
            if (!item.name[0] || item.persistent) continue;
            memcpy(&candidate, &item, sizeof(item));
            if (find(RF_SCRIPT_MERGE_OFF, candidate.name) < RF_SCRIPT_VARS) continue;
            j = empty(RF_SCRIPT_MERGE_OFF);
            if (j == RF_SCRIPT_VARS) { call->rc = RF_RESULT_CONFLICT; return 1u; }
            memcpy(&item, &candidate, sizeof(item));
            if (!store(RF_SCRIPT_MERGE_OFF, j)) return 0u;
        }
        return 1u;
    }
    if (call->operation == RF_ENV_COMMIT) {
        for (i = 0u; i < RF_SCRIPT_VARS; ++i)
            if (!fetch(RF_SCRIPT_MERGE_OFF, i) || !store(RF_SCRIPT_VARS_OFF, i)) return 0u;
        return 1u;
    }
    return 0u;
}

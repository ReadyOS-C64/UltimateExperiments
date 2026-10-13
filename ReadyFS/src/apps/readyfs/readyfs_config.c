/* Config validation and REU transaction policy. Device I/O stays resident. */
#include "readyfs_script.h"
#include "readyfs_reu.h"
#include "readyfs_path.h"
#include "readyfs_result.h"
#include <string.h>
#include <conio.h>

typedef struct { char name[17]; char root[256]; } ConfigAlias;
static ConfigAlias item;
static ReadyFsPath parsed;

static unsigned int offset(unsigned char index) {
    return index ? 256u + (unsigned int)(index - 1u) * sizeof(item) : 0u;
}
static unsigned char restore(ReadyFsBatchCall *call) {
    unsigned char i;
    if (!readyfs_reu_session_fetch(RF_REU_CONFIG_BACKUP_OFF, (void *)call->test, 256u)) return 0u;
    for (i = 0u; i < 8u; ++i) {
        if (!readyfs_reu_session_fetch(RF_REU_CONFIG_BACKUP_OFF + 256u + (unsigned int)i * sizeof(item), &item, sizeof(item)) ||
            !readyfs_reu_session_store((unsigned int)i * sizeof(item), &item, sizeof(item))) return 0u;
    }
    return 1u;
}
static unsigned char invoke(ReadyFsBatchCall *call, unsigned char operation) {
    call->operation = operation; call->rc = 0u;
    return readyfs_config_io(call) && call->rc == 0u;
}
static unsigned char load(ReadyFsBatchCall *call) {
    ReadyFsBatchCall work;
    unsigned char header[8];
    unsigned char i, ok;
    unsigned int bytes;
    memcpy(&work, call, sizeof(work));
    work.size = sizeof(header);
    ok = invoke(&work, RF_CONFIG_READ);
    memcpy(header, work.buffer, sizeof(header));
    for (i = 0u; ok && i < 9u; ++i) {
        bytes = i ? sizeof(item) : 256u;
        work.size = bytes;
        ok = invoke(&work, RF_CONFIG_READ) &&
             readyfs_reu_session_store(RF_REU_CONFIG_STAGE_OFF + offset(i), work.buffer, bytes);
    }
    if (ok && header[3] == '2') for (i = 0u; ok && i < RF_SCRIPT_VARS; ++i) {
        work.size = RF_SCRIPT_RECORD_BYTES;
        ok = invoke(&work, RF_CONFIG_READ);
        work.size = i;
        if (ok) ok = invoke(&work, RF_ENV_STAGE);
    }
    if (ok) ok = invoke(&work, RF_CONFIG_EOF);
    if (!invoke(&work, RF_CONFIG_CLOSE)) ok = 0u;
    if (ok && header[3] == '2') ok = invoke(&work, RF_ENV_MERGE);
    if (ok) {
        memcpy(work.buffer, header, sizeof(header));
        work.operation = RF_CONFIG_APPLY;
        ok = readyfs_config(&work) && work.rc == 0u;
    }
    if (ok && header[3] == '2' && !invoke(&work, RF_ENV_COMMIT)) {
        (void)restore(&work); ok = 0u;
    }
    call->rc = ok ? RF_RESULT_OK : RF_RESULT_USAGE;
    return 1u;
}
static unsigned char export_record(ReadyFsBatchCall *call) {
    unsigned char index;
    static const unsigned char header[8] = { 'R','F','C','2',8u,16u,255u,0u };
    index = (unsigned char)call->size;
    if (!index) { memcpy(call->buffer, header, sizeof(header)); call->size = sizeof(header); }
    else if (index == 1u) { memcpy(call->buffer, call->test, 256u); call->size = 256u; }
    else if (index < 10u) {
        call->size = sizeof(item);
        return readyfs_reu_session_fetch((unsigned int)(index - 2u) * sizeof(item), call->buffer, sizeof(item));
    } else if (index < 26u) {
        call->size = RF_SCRIPT_RECORD_BYTES;
        if (!readyfs_reu_script_fetch(RF_SCRIPT_VARS_OFF + (unsigned int)(index - 10u) * RF_SCRIPT_RECORD_BYTES,
                                      call->buffer, RF_SCRIPT_RECORD_BYTES)) return 0u;
        if (!((ReadyFsVariable *)call->buffer)->persistent) memset(call->buffer, 0, RF_SCRIPT_RECORD_BYTES);
    } else return 0u;
    return 1u;
}
unsigned int readyfs_config_abi(void) { return RF_SCRIPT_ABI; }
unsigned char readyfs_config(ReadyFsBatchCall *call) {
    unsigned char i, j;
    unsigned int bytes;
    if (call->operation == RF_CONFIG_HELP) {
        clrscr();
        cputs("run file [arg1..arg9]\r\n"
              "set name=value  session\r\n"
              "set /p name=value  save with config\r\n"
              "set name=  remove; set  list\r\n"
              "set /a n=n+1  16-bit + or -\r\n"
              "echo text; rem comment\r\n"
              "%name% %errorlevel% %0..%9 %%\r\n"
              "if [not] errorlevel n command\r\n"
              "if [not] defined name command\r\n"
              "if [not] exist path command\r\n"
              "if [not] a==b command\r\n"
              "if n equ|neq|lss|leq|gtr|geq n cmd\r\n"
              ":label; goto label; call :label\r\n"
              "exit /b [rc]; goto :eof\r\n"
              "loops: labels + if + goto\r\n"
              "onerror stop|continue; expect rc n\r\n"
              "16 vars; names 16; values 127 bytes\r\n"
              "16k script; 255-byte lines; 12 args\r\n"
              "8 call levels; 10000 steps; stop cancels\r\n");
        call->action = RF_BATCH_SKIP; call->rc = RF_RESULT_OK; return 1u;
    }
    if (call->operation == RF_CONFIG_EXPORT) return export_record(call);
    if (call->operation == RF_CONFIG_LOAD) return load(call);
    if (call->operation == RF_CONFIG_ROLLBACK) return restore(call);
    call->rc = RF_RESULT_USAGE;
    if ((memcmp(call->buffer, "RFC1", 4u) && memcmp(call->buffer, "RFC2", 4u)) ||
        (unsigned char)call->buffer[4] != 8u || (unsigned char)call->buffer[5] != 16u ||
        (unsigned char)call->buffer[6] != 255u || (unsigned char)call->buffer[7] != 0u) return 1u;
    for (i = 0u; i < 9u; ++i) {
        bytes = i ? sizeof(item) : 256u;
        if (!readyfs_reu_session_fetch(RF_REU_CONFIG_STAGE_OFF + offset(i), &item, bytes)) return 0u;
        if (!i) {
            if (((char *)&item)[255] || readyfs_path_parse((char *)&item, &parsed) != RF_PATH_OK ||
                !parsed.absolute || parsed.endpoint == RF_EP_ALIAS) return 1u;
        } else if (item.name[16] || item.root[255]) return 1u;
        else if (item.name[0]) {
            for (j = 0u; item.name[j]; ++j)
                if (item.name[j] == ':' || item.name[j] == '/' || item.name[j] == '@') return 1u;
            if (readyfs_path_parse(item.root, &parsed) != RF_PATH_OK || !parsed.absolute || parsed.endpoint == RF_EP_ALIAS) return 1u;
        }
    }
    /* Snapshot all live state before applying a validated file. */
    if (!readyfs_reu_session_store(RF_REU_CONFIG_BACKUP_OFF, call->test, 256u)) return 0u;
    for (i = 0u; i < 8u; ++i) {
        if (!readyfs_reu_session_fetch((unsigned int)i * sizeof(item), &item, sizeof(item)) ||
            !readyfs_reu_session_store(RF_REU_CONFIG_BACKUP_OFF + 256u + (unsigned int)i * sizeof(item), &item, sizeof(item))) return 0u;
    }
    if (!readyfs_reu_session_fetch(RF_REU_CONFIG_STAGE_OFF, (void *)call->test, 256u)) return 0u;
    for (i = 0u; i < 8u; ++i) {
        if (!readyfs_reu_session_fetch(RF_REU_CONFIG_STAGE_OFF + 256u + (unsigned int)i * sizeof(item), &item, sizeof(item)) ||
            !readyfs_reu_session_store((unsigned int)i * sizeof(item), &item, sizeof(item))) {
            (void)restore(call); return 0u;
        }
    }
    call->rc = RF_RESULT_OK; return 1u;
}

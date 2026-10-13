/* Cached stream policy. This leaf overlay never invokes another overlay.
 * UCI detection and path parsing are resident services; no OPEN/read/write or
 * filesystem mutation occurs here. Returned names point into resident data. */
#include "readyfs_stream.h"
#include "readyfs_uci.h"
#include "readyfs_console.h"
#include "readyfs_result.h"
#include <conio.h>
#include <string.h>

unsigned int readyfs_stream_abi(void) { return RF_STREAM_ABI; }

static unsigned char reject(ReadyFsStreamCall *call, unsigned char status,
                            const char *message) {
    if (status) *call->status = status;
    cputs(RF_ERROR); cputs(message);
    return 0u;
}

unsigned char readyfs_stream_prepare(ReadyFsStreamCall *call) {
    ReadyFsStream *stream;
    char *name;
    unsigned char rc;
    if (!call || !call->stream || !call->status) return 0u;
    stream = call->stream;
    stream->open = 0u;
    stream->native_mode = stream->native_partition = 0u;
    rc = readyfs_path_parse(stream->canonical, &stream->path);
    if (rc != RF_PATH_OK) {
        cputs(RF_ERROR); cputs(readyfs_path_error(rc)); cputs("\r\n");
        return 0u;
    }
    if (!stream->path.absolute ||
        (stream->path.endpoint != RF_EP_IEC &&
         stream->path.endpoint != RF_EP_SOFTIEC &&
         stream->path.endpoint != RF_EP_ULTIMATE &&
         stream->path.endpoint != RF_EP_TAPE)) {
        return reject(call, RF_RESULT_UNSUPPORTED, "use 8:/file\r\n");
    }
    name = stream->canonical + stream->path.path_offset;
    if (stream->path.endpoint == RF_EP_IEC ||
        stream->path.endpoint == RF_EP_TAPE) while (*name == '/') ++name;
    else if (stream->path.endpoint == RF_EP_SOFTIEC)
        name = stream->canonical + 1u;
    if (!*name || (stream->path.endpoint == RF_EP_ULTIMATE &&
                  name[0] == '/' && name[1] == 0)) {
        return reject(call, 0u, "file required\r\n");
    }
    if (stream->path.endpoint == RF_EP_IEC &&
        strchr(name, '!')) {
        return reject(call, RF_RESULT_UNSUPPORTED, "cmd path\r\n");
    }
    if (stream->path.endpoint == RF_EP_ULTIMATE && strchr(name, '!')) {
        return reject(call, RF_RESULT_UNSUPPORTED, "image off\r\n");
    }
    if (stream->path.endpoint == RF_EP_TAPE &&
        (strlen(name) > 16u || strchr(name, '/') || strchr(name, '!'))) {
        return reject(call, RF_RESULT_UNSUPPORTED, "tape leaf 1-16\r\n");
    }
    if (stream->path.endpoint == RF_EP_SOFTIEC) {
        if (!readyfs_uci_detect())
            return reject(call, RF_RESULT_UNAVAILABLE, "softiec off\r\n");
        stream->device = readyfs_uci_softiec_bus();
        if (stream->device < 8u || stream->device > 30u)
            return reject(call, 0u, "bad soft bus\r\n");
    } else stream->device = stream->path.endpoint == RF_EP_TAPE ? 1u :
                                                               stream->path.unit;
    stream->text = stream->canonical;
    stream->native_name = name;
    return 1u;
}

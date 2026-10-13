#include "src/apps/readyfs/readyfs_stream.h"
#include "src/apps/readyfs/readyfs_result.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned char detected = 1u, soft_bus = 11u;
static char output[256];
static unsigned used;
unsigned char readyfs_uci_detect(void) { return detected; }
unsigned char readyfs_uci_softiec_bus(void) { return soft_bus; }
void cputs(const char *text) {
    assert(strlen(text)+used < sizeof(output));
    strcpy(output+used,text);used+=strlen(text);
}
static unsigned char prepare(ReadyFsStream *stream, const char *text,
                             unsigned char *status) {
    ReadyFsStreamCall call;
    strcpy(stream->canonical,text);stream->open=1u;
    call.stream=stream;call.status=status;output[0]=0;used=0;
    return readyfs_stream_prepare(&call);
}
int main(void) {
    ReadyFsStream source,destination;
    unsigned char status=RF_RESULT_OK;
    memset(&source,0,sizeof(source));memset(&destination,0,sizeof(destination));
    assert(readyfs_stream_abi()==RF_STREAM_ABI);
    assert(prepare(&source,"8:/hello",&status));
    assert(source.device==8 && !source.open && !strcmp(source.native_name,"hello"));
    assert(source.text==source.canonical && source.native_name==source.canonical+3);
    assert(prepare(&destination,"u:/usb1/nested/target.seq",&status));
    assert(!strcmp(destination.native_name,"/usb1/nested/target.seq"));
    assert(!strcmp(source.native_name,"hello")); /* independent live stream names */
    assert(prepare(&destination,"s0:/usb1/test/file.seq",&status));
    assert(destination.device==11 && !strcmp(destination.native_name,"0:/usb1/test/file.seq"));
    assert(prepare(&destination,"t:/notes",&status));
    assert(destination.device==1 && !strcmp(destination.native_name,"notes"));
    assert(!prepare(&destination,"t:/12345678901234567",&status));
    assert(status==RF_RESULT_UNSUPPORTED && strstr(output,"tape leaf"));
    status=RF_RESULT_OK;detected=0;
    assert(!prepare(&destination,"s3:/notes",&status));
    assert(status==RF_RESULT_UNAVAILABLE && strstr(output,"softiec off"));
    detected=1;status=RF_RESULT_OK;
    assert(!prepare(&destination,"8:/",&status) && strstr(output,"file required"));
    assert(!prepare(&destination,"u:/",&status) && strstr(output,"file required"));
    assert(prepare(&destination,"8:/dir/file",&status)); /* native classification follows */
    assert(prepare(&destination,"10.1:/hello",&status) && destination.path.partition==1);
    assert(!prepare(&destination,"u:/disk.d81!/file",&status) && strstr(output,"image off"));
    assert(!readyfs_stream_prepare(NULL));
    puts("readyfs stream policy tests passed: persistent descriptors, endpoints, tape limits and typed rejection");
    return 0;
}

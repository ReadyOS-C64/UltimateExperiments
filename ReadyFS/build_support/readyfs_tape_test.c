#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_tape.h"

unsigned char readyfs_reu_batch_bank_value = 13u;
static unsigned char spool[16u * 65536u];

unsigned int readyfs_reu_bank_count(void) { return 16u; }

unsigned char readyfs_reu_batch_store(unsigned int offset, const void *data,
                                      unsigned int length) {
    offset += readyfs_reu_batch_bank_value * 65536u;
    if (offset + length > sizeof(spool)) return 0u;
    memcpy(spool + offset, data, length);
    return 1u;
}

unsigned char readyfs_reu_batch_fetch(unsigned int offset, void *data,
                                      unsigned int length) {
    offset += readyfs_reu_batch_bank_value * 65536u;
    if (offset + length > sizeof(spool)) return 0u;
    memcpy(data, spool + offset, length);
    return 1u;
}

static void check(int condition, const char *label) {
    if (!condition) {
        fprintf(stderr, "readyfs tape test failed: %s\n", label);
        exit(1);
    }
}

int main(void) {
    ReadyFsTapeCall call;
    ReadyFsSignature a;
    ReadyFsSignature b;
    ReadyFsTapeSpoolState spool_state;
    ReadyFsPath path;
    unsigned char fetched[9];
    unsigned char boundary[32];
    unsigned int i;
    char open_text[24];
    char *write_args[] = {"write", "t:/rfseq", "data", "--line"};
    char *typed_args[] = {"new", "t:/rfseq", "--type", "prg"};

    memset(&call, 0, sizeof(call));
    call.operation = RF_TAPE_FILE_TYPE;
    call.argc = 4u;
    call.args = write_args;
    check(readyfs_tape_dispatch(&call) && call.result == 0x10u,
          "default sequential type");
    call.args = typed_args;
    check(readyfs_tape_dispatch(&call) && call.result == 0x11u,
          "explicit PRG type");

    memset(&call, 0, sizeof(call));
    call.operation = RF_TAPE_OPEN_NAME;
    call.text = "rf~01";
    call.output = open_text;
    call.value = 0x10u;
    call.value2 = 'w';
    check(readyfs_tape_dispatch(&call) && call.result &&
          strcmp(open_text, "rf~01,s,w") == 0,
          "IEC sequential write open name");

    memset(&call, 0, sizeof(call));
    call.operation = RF_TAPE_PATH_PREPARE;
    call.text = "t:/sixteen-byte-nam";
    call.path = &path;
    check(readyfs_tape_dispatch(&call) &&
          call.result == RF_TAPE_PATH_OK &&
          strcmp(call.found, "sixteen-byte-nam") == 0,
          "bounded tape leaf");
    call.text = "t:/sixteen-byte-name";
    check(readyfs_tape_dispatch(&call) &&
          call.result == RF_TAPE_PATH_LEAF,
          "overlong tape leaf rejection");

    memset(&call, 0, sizeof(call));
    call.operation = RF_TAPE_SIGNATURE_INIT;
    call.signature = &a;
    check(readyfs_tape_dispatch(&call), "signature init");
    call.operation = RF_TAPE_SIGNATURE_ADD;
    call.data = (const unsigned char *)"tape data";
    call.length = 9u;
    check(readyfs_tape_dispatch(&call), "signature add");
    b = a;
    call.operation = RF_TAPE_SIGNATURE_EQUAL;
    call.other = &b;
    check(readyfs_tape_dispatch(&call) && call.result,
          "signature equality");
    memset(&call, 0, sizeof(call));
    call.operation = RF_TAPE_SPOOL_INIT;
    call.spool = &spool_state;
    check(readyfs_tape_dispatch(&call) && call.result,
          "spool initialize");
    call.operation = RF_TAPE_SPOOL_STORE;
    call.data = (const unsigned char *)"tape data";
    call.length = 9u;
    check(readyfs_tape_dispatch(&call) && call.result &&
          readyfs_reu_batch_bank_value == 13u,
          "spool store and bank restore");
    call.operation = RF_TAPE_SPOOL_FETCH;
    call.data = fetched;
    call.length = sizeof(fetched);
    check(readyfs_tape_dispatch(&call) && call.result &&
          memcmp(fetched, "tape data", 9u) == 0 &&
          readyfs_reu_batch_bank_value == 13u,
          "spool fetch and bank restore");
    memset(spool + 12u * 65536u, 0xA7, 4u * 65536u);
    memset(boundary, 0x5C, sizeof(boundary));
    spool_state.bytes_bank = 10u; /* actual bank 11 is the last spool bank */
    spool_state.bytes_lo = 0xFFF0u;
    spool_state.replay_bank = 10u;
    spool_state.replay_lo = 0xFFF0u;
    call.operation = RF_TAPE_SPOOL_STORE;
    call.data = boundary;
    call.length = 17u;
    check(readyfs_tape_dispatch(&call) && !call.result &&
          spool_state.bytes_lo == 0xFFF0u, "reject one-byte console overlap");
    call.length = 16u;
    check(readyfs_tape_dispatch(&call) && call.result &&
          spool_state.bytes_lo == 0u && spool_state.bytes_bank == 11u,
          "allow exact last spool boundary");
    call.length = 1u;
    check(readyfs_tape_dispatch(&call) && !call.result,
          "reject first byte in reserved console bank");
    call.operation = RF_TAPE_SPOOL_FETCH;
    call.length = 32u; /* request spans the adjacent end cursor */
    memset(boundary, 0, sizeof(boundary));
    check(readyfs_tape_dispatch(&call) && call.result && call.length == 16u &&
          spool_state.replay_bank == 11u && spool_state.replay_lo == 0u,
          "fetch caps oversized final request across bank boundary");
    for (i = 0; i < 16u; ++i) check(boundary[i] == 0x5C, "boundary data intact");
    call.length = 1u;
    check(readyfs_tape_dispatch(&call) && call.result && call.length == 0u,
          "EOF at reserved boundary");
    for (i = 12u * 65536u; i < sizeof(spool); ++i)
        check(spool[i] == 0xA7, "all four reserved banks unchanged");
    check(readyfs_reu_batch_bank_value == 13u, "batch bank restored");
    puts("readyfs tape policy/signature/spool tests passed");
    return 0;
}

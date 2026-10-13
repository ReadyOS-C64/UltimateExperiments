#include "src/apps/readyfs/readyfs_content.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static char output[2048];
static unsigned int output_used;

void cputc(char value) {
    assert(output_used + 1u < sizeof(output));
    output[output_used++] = value;
    output[output_used] = 0;
}

void cputs(const char *text) {
    while (*text != 0) cputc(*text++);
}

static void clear_output(void) {
    output_used = 0u;
    output[0] = 0;
}

static void init_call(ReadyFsUtilityCall *call, char *workspace,
                      char **args, unsigned char argc,
                      unsigned char mode) {
    memset(call, 0, sizeof(*call));
    memset(workspace, 0, 256u);
    call->operation = RF_UTILITY_CONTENT_INIT;
    call->argc = argc;
    call->args = args;
    call->value_high = mode;
    call->workspace = workspace;
}

static void add_bytes(ReadyFsUtilityCall *call, const char *bytes,
                      unsigned int count) {
    call->operation = RF_UTILITY_CONTENT_ADD;
    call->buffer = (char *)bytes;
    call->capacity = count;
    assert(readyfs_content_dispatch(call) == 1u);
}

static void report(ReadyFsUtilityCall *call) {
    call->operation = RF_UTILITY_CONTENT_REPORT;
    assert(readyfs_content_dispatch(call) == 1u);
}

static void test_invalid_count(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char *args[] = {"head", "8:/RFVIEW", "0"};
    clear_output();
    init_call(&call, workspace, args, 3u, RF_CONTENT_HEAD);
    assert(readyfs_content_dispatch(&call) == 1u);
    assert(call.value_low == 0u);
    assert(strcmp(output, "head path [lines]\r\n") == 0);
}

static void test_head_chunks(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char *args[] = {"head", "8:/RFVIEW", "3"};
    clear_output();
    init_call(&call, workspace, args, 3u, RF_CONTENT_HEAD);
    assert(readyfs_content_dispatch(&call) == 1u && call.value_low == 1u);
    add_bytes(&call, "A\nB", 3u);
    assert(call.value_low == 1u);
    add_bytes(&call, "\nC\nD\n", 5u);
    assert(call.value_low == 0u);
    report(&call);
    assert(strcmp(output, "A\r\nB\r\nC\r\nhead; read 8 bytes\r\n") == 0);
}

static void test_tail_chunks(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char *args[] = {"tail", "8:/RFVIEW", "2"};
    clear_output();
    init_call(&call, workspace, args, 3u, RF_CONTENT_TAIL);
    assert(readyfs_content_dispatch(&call) == 1u && call.value_low == 1u);
    add_bytes(&call, "A\nB\nC", 5u);
    add_bytes(&call, "\nD\n", 3u);
    report(&call);
    assert(strcmp(output, "C\r\nD\r\n\r\ntail; read 8 bytes\r\n") == 0);
}

static void test_tail_bounded_truncation(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char input[400];
    char line[24];
    char *args[] = {"tail", "8:/RFLONG", "2"};
    unsigned int used;
    unsigned int i;
    used = 0u;
    for (i = 1u; i <= 20u; ++i) {
        sprintf(line, "LONG%02u-ABCDEFGHIJ\n", i);
        strcpy(input + used, line);
        used += (unsigned int)strlen(line);
    }
    clear_output();
    init_call(&call, workspace, args, 3u, RF_CONTENT_TAIL);
    assert(readyfs_content_dispatch(&call) == 1u && call.value_low == 1u);
    add_bytes(&call, input, 113u);
    add_bytes(&call, input + 113u, 127u);
    add_bytes(&call, input + 240u, (unsigned int)(used - 240u));
    report(&call);
    assert(strstr(output, "LONG19-ABCDEFGHIJ\r\nLONG20-ABCDEFGHIJ\r\n") != 0);
    assert(strstr(output, "LONG18-ABCDEFGHIJ") == 0);
    assert(strstr(output, "tail truncated") != 0);
    assert(strstr(output, "tail; read 360 bytes") != 0);
}

static void test_crc32_chunks(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char input[96];
    char line[16];
    char *args[] = {"crc32", "8:/RFVIEW"};
    unsigned int used;
    unsigned int i;
    used = 0u;
    for (i = 1u; i <= 12u; ++i) {
        sprintf(line, "VIEW%02u\n", i);
        strcpy(input + used, line);
        used += (unsigned int)strlen(line);
    }
    assert(used == 84u);
    clear_output();
    init_call(&call, workspace, args, 2u, RF_CONTENT_CRC32);
    assert(readyfs_content_dispatch(&call) == 1u && call.value_low == 1u);
    add_bytes(&call, input, 31u);
    add_bytes(&call, input + 31u, 29u);
    add_bytes(&call, input + 60u, used - 60u);
    report(&call);
    if (strcmp(output, "crc32 $6126e7f6\r\n") != 0)
        fprintf(stderr, "unexpected crc output: %s", output);
    assert(strcmp(output, "crc32 $6126e7f6\r\n") == 0);
}

static void test_rejects_non_view_mode(void) {
    ReadyFsUtilityCall call;
    char workspace[256];
    char *run_args[] = {"test"};
    clear_output();
    init_call(&call, workspace, run_args, 1u, RF_CONTENT_TEST);
    assert(readyfs_content_dispatch(&call) == 1u && call.value_low == 0u);
    assert(strcmp(output, "type path\r\n") == 0);
}

int main(void) {
    assert(readyfs_content_abi() == RF_CONTENT_ABI);
    test_invalid_count();
    test_head_chunks();
    test_tail_chunks();
    test_tail_bounded_truncation();
    test_crc32_chunks();
    test_rejects_non_view_mode();
    puts("readyfs bounded content-view tests passed");
    return 0;
}

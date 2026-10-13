#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_cmdpath.h"


static int fails;
static char output[256];
static char followup[256];

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL cmdpath %s\n", message);
        ++fails;
    }
}

static ReadyFsCmdPathCall make_call(unsigned char operation,
                                   const char *source) {
    ReadyFsCmdPathCall call;
    memset(&call, 0, sizeof(call));
    memset(output, 0, sizeof(output));
    memset(followup, 0, sizeof(followup));
    call.operation = operation;
    call.source = source;
    call.output = output;
    call.output_capacity = sizeof(output);
    call.followup = followup;
    call.followup_capacity = sizeof(followup);
    return call;
}

int main(void) {
    ReadyFsCmdPathCall call;
    char long_component[40];
    char path[256];
    unsigned char index;

    call = make_call(RF_CMDPATH_OPEN_FILE, "11.3:/games/HELLO.PRG");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "3//games/:HELLO.PRG") == 0 &&
          call.device == 11u && call.partition == 3u,
          "absolute file reference");

    call = make_call(RF_CMDPATH_DIRECTORY, "11.3:/games/tools");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "$3//games/tools/") == 0,
          "absolute directory reference");

    call = make_call(RF_CMDPATH_DIRECTORY, "11.3:/");
    check(readyfs_cmdpath_dispatch(&call) && strcmp(output, "$3//") == 0,
          "partition root directory reference");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "8:/A*.PRG");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "$:A*.PRG") == 0 &&
          call.device == 8u && call.partition == 0u,
          "legacy IEC native directory pattern");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "30:/FILE?");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "$:FILE?") == 0 && call.device == 30u,
          "maximum IEC native question-mark pattern");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "8:/PLAIN");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_PATTERN_REQUIRED,
          "native directory pattern requires wildcard");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "8:/DIR/*.PRG");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_BAD_PATH,
          "legacy native directory pattern remains flat");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "11.3:/*.PRG");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_BAD_PATH,
          "partitioned native pattern not silently translated");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "u:/USB1/*.PRG");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_BAD_PATH,
          "Ultimate path not sent to IEC native pattern");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "8:/ABCDEFGHIJKLMNOP*");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_COMPONENT_TOO_LONG,
          "native pattern honors 16-character IEC limit");

    call = make_call(RF_CMDPATH_NATIVE_DIR, "8:/*.PRG");
    call.output_capacity = 4u;
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_OUTPUT_TOO_SMALL,
          "native pattern output capacity checked");

    call = make_call(RF_CMDPATH_SCRATCH, "11.3:/games/OLD.SEQ");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "S3//games/:OLD.SEQ") == 0,
          "scratch command");

    call = make_call(RF_CMDPATH_MKDIR, "11.3:/games/newdir");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "MD3//games/:newdir") == 0,
          "mkdir command");

    call = make_call(RF_CMDPATH_RMDIR, "11.3:/games/old");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "RD3//games/:old") == 0,
          "rmdir command");

    strcpy(path, "11.3:/games/tools");
    call = make_call(RF_CMDPATH_DIRECTORY, path);
    call.output = path;
    call.output_capacity = sizeof(path);
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(path, "$3//games/tools/") == 0,
          "in-place directory translation");

    strcpy(path, "11.3:/games/newdir");
    call = make_call(RF_CMDPATH_MKDIR, path);
    call.output = path;
    call.output_capacity = sizeof(path);
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(path, "MD3//games/:newdir") == 0,
          "in-place mkdir translation");

    strcpy(path, "11.3:/games/old");
    call = make_call(RF_CMDPATH_RMDIR, path);
    call.output = path;
    call.output_capacity = sizeof(path);
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(path, "RD3//games/:old") == 0,
          "in-place rmdir translation");

    call = make_call(RF_CMDPATH_RENAME, "11.3:/games/OLD.SEQ");
    call.destination = "11.3:/archive/NEW.SEQ";
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output,
                 "R3//archive/:NEW.SEQ=3//games/:OLD.SEQ") == 0,
          "rename command");

    call = make_call(RF_CMDPATH_RENAME, "11.3:/games/OLD.SEQ");
    call.destination = "11.4:/games/NEW.SEQ";
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_CROSS_LOCATION,
          "cross-partition rename rejected");

    call = make_call(RF_CMDPATH_MOUNT, "11.3:/games/demo.d64");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "CD3//games/demo.d64") == 0,
          "sd2iec image mount command");

    call = make_call(RF_CMDPATH_MOUNT, "11.254:/images/WORK.D81");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "CD254//images/WORK.D81") == 0,
          "maximum partition and case-insensitive image extension");

    call = make_call(RF_CMDPATH_UNMOUNT, "11.3:/");
    check(readyfs_cmdpath_dispatch(&call) &&
          strcmp(output, "CD//") == 0 &&
          followup[0] == 'C' && followup[1] == 'D' &&
          (unsigned char)followup[2] == RF_CMDPATH_SD2IEC_BACK &&
          followup[3] == 0,
          "sd2iec root then image-unmount sequence");

    call = make_call(RF_CMDPATH_MOUNT, "11.3:/games/readme.seq");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_IMAGE_REQUIRED,
          "non-image mount rejected");

    call = make_call(RF_CMDPATH_OPEN_FILE,
                     "11.3:/games/demo.d64!/HELLO");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_IMAGE_STATEFUL,
          "contained image access explicitly stateful");

    memset(long_component, 'a', 17u);
    long_component[17] = 0;
    strcpy(path, "11.3:/");
    strcat(path, long_component);
    call = make_call(RF_CMDPATH_OPEN_FILE, path);
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_COMPONENT_TOO_LONG,
          "long native component rejected");

    strcpy(path, "11.3:/");
    for (index = 0u; index < 14u; ++index) {
        strcat(path, "abcdefghijklmnop/");
    }
    strcat(path, "leaf");
    call = make_call(RF_CMDPATH_OPEN_FILE, path);
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_NATIVE_TOO_LONG,
          "long native directory path rejected");

    call = make_call(RF_CMDPATH_OPEN_FILE, "11.3:/games/HELLO.PRG");
    call.output_capacity = 8u;
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_OUTPUT_TOO_SMALL,
          "small translated-command buffer rejected");

    call = make_call(RF_CMDPATH_OPEN_FILE, "8:/HELLO");
    check(!readyfs_cmdpath_dispatch(&call) &&
          call.result == RF_CMDPATH_BAD_PATH,
          "legacy IEC path does not enter CMD translator");

    call = make_call(RF_CMDPATH_OPEN_FILE, "u:/usb1/HELLO");
    check(!readyfs_cmdpath_dispatch(&call) &&
          strcmp(readyfs_cmdpath_error(call.result),
                 "not an absolute partitioned iec path") == 0,
          "non-IEC path rejected with stable diagnostic");

    if (fails != 0) return 1;
    puts("readyfs CMD/SD2IEC path tests passed");
    return 0;
}

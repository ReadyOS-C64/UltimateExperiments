#include "src/apps/readyfs/readyfs_utility.h"

#include <stdio.h>
#include <string.h>

static int failures;
static char printed[1024];
static unsigned print_offset;

void cputc(char value) { if (print_offset+1u < sizeof(printed)) { printed[print_offset++]=value; printed[print_offset]=0; } }
void cputs(const char *text) { while (*text) cputc(*text++); }

unsigned char readyfs_reu_history_count(void) { return 0u; }
unsigned char readyfs_reu_history_get(unsigned char age, char *out) {
    (void)age;
    (void)out;
    return 0u;
}

static void expect_step(ReadyFsUtilityCall *call, const char *expected,
                        unsigned char more) {
    if (!readyfs_utility_dispatch(call)) {
        fprintf(stderr, "soft CD dispatch failed\n");
        ++failures;
        return;
    }
    if (call->capacity != more) {
        fprintf(stderr, "soft CD continuation: got %u expected %u\n",
                call->capacity, more);
        ++failures;
    }
    if (expected != 0 && strcmp(call->workspace, expected) != 0) {
        fprintf(stderr, "soft CD command: got '%s' expected '%s'\n",
                call->workspace, expected);
        ++failures;
    }
}

int main(void) {
    ReadyFsUtilityCall call;
    char output[256];
    char path[] = "s0:/READYFS_TEST/run/file";
    char petscii_path[] = "s0:/READYFS\xA4" "TEST/run/file_name";
    char root_file[] = "s0:/file";

    memset(&call, 0, sizeof(call));
    call.operation = RF_UTILITY_SOFT_CD;
    call.buffer = path;
    call.workspace = output;
    expect_step(&call, "cd:usb1", 1u);
    expect_step(&call, "cd:READYFS_TEST", 1u);
    expect_step(&call, "cd:run", 1u);
    expect_step(&call, 0, 0u);

    memset(&call, 0, sizeof(call));
    call.operation = RF_UTILITY_SOFT_CD;
    call.buffer = petscii_path;
    call.workspace = output;
    expect_step(&call, "cd:usb1", 1u);
    if ((unsigned char)petscii_path[11] != 0x5Fu ||
        (unsigned char)petscii_path[25] != 0x5Fu) {
        fprintf(stderr, "soft CD PETSCII underscore normalization failed\n");
        ++failures;
    }
    expect_step(&call, "cd:READYFS_TEST", 1u);
    expect_step(&call, "cd:run", 1u);
    expect_step(&call, 0, 0u);

    memset(&call, 0, sizeof(call));
    call.operation = RF_UTILITY_SOFT_CD;
    call.buffer = root_file;
    call.workspace = output;
    expect_step(&call, "cd:usb1", 1u);
    expect_step(&call, 0, 0u);

    {
        static const char *names[]={"nw","wr","ap","rn","cp","mv","dl","rd","md","mo","um","sw","fm","cf"};
        static const char *plans[]={"w1 d0 m0","w1 d0 m0","w1 d0 m0","w1 d0 m0","w1 d0 m0","w1 d1 m0","w0 d1 m0","w0 d1 m0","w1 d0 m0","w0 d0 m1","w0 d0 m1","w0 d0 m1","w0 d0 m1","w1 d0 m0"};
        unsigned i;
        char *args[]={0,"save","8:/unused","--dry-run","--apply"};
        for(i=0;i<sizeof(names)/sizeof(names[0]);++i) {
            memset(&call,0,sizeof(call));
            args[0]=(char *)names[i]; call.args=args;call.argc=5;
            call.operation=RF_UTILITY_PREVIEW;
            call.value_low=readyfs_command_id(names[i]);
            print_offset=0;printed[0]=0;
            if (!readyfs_utility_dispatch(&call) || !strstr(printed,plans[i]) ||
                !strstr(printed,"done w0 d0 m0")) {
                fprintf(stderr,"alias preview %s failed: %s\n",names[i],printed);++failures;
            }
        }
    }
    if (failures != 0) return 1;
    puts("readyfs SoftwareIEC component-CD and alias preview tests passed");
    return 0;
}

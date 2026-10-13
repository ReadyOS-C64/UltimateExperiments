#include "readyfs_present.h"
#include <conio.h>
#ifndef READYFS_MONOLITHIC
#include "readyfs_help_data.h"
static void help_emit(unsigned char token) {
    if (token < 128u) cputc((char)token);
    else {
        token -= 128u;
        help_emit(help_pairs[token][0]);
        help_emit(help_pairs[token][1]);
    }
}

#endif

unsigned int readyfs_command_help_abi(void) { return RF_COMMAND_HELP_ABI; }
void readyfs_command_help(ReadyFsUtilityCall *call) {
    unsigned int n;
    const char *name;

#ifndef READYFS_MONOLITHIC
        n = call->value_low;
        if (n == RF_COMMAND_MOUNT && (call->buffer[0] == 'f' || call->buffer[0] == 'F')) n = 41u;
        if (n > 41u) n = 0u;
        name = (const char *)topics[n];
        while (*name) help_emit((unsigned char)*name++);
        if (n == 20u || n == 21u || n == 23u) {
            cputs("-r --recursive  -w --whatif/--dry-run\r\n");
            cputs("-i --include P  -x --exclude P\r\n");
            cputs("-f --force overwrite; -y --yes delete\r\n");
            cputs("whatif makes no changes; inspect first.\r\n");
        }
#endif


}

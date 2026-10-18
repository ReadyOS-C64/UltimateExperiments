#include "src/apps/readyfs/readyfs_commands.h"

#include <assert.h>
#include <stdio.h>

int main(void) {
    assert(readyfs_command_id("copy") == RF_COMMAND_COPY);
    assert(readyfs_command_id("COPY") == RF_COMMAND_COPY);
    assert(readyfs_command_id("prg") == RF_COMMAND_FILE_PRG);
    assert(readyfs_command_id("USR") == RF_COMMAND_FILE_USR);
    assert(readyfs_command_id("seq") == RF_COMMAND_FILE_SEQ);
    assert((RF_COMMAND_FILE_PRG & 0x7Fu) == 0x11u);
    assert((RF_COMMAND_FILE_USR & 0x7Fu) == 0x12u);
    assert((RF_COMMAND_FILE_SEQ & 0x7Fu) == 0x10u);
    assert(readyfs_command_id("bogus") == RF_COMMAND_UNKNOWN);
    assert(readyfs_command_id("q") == RF_COMMAND_EXIT);
    assert(readyfs_command_id("h") == RF_COMMAND_HELP);
    assert(readyfs_command_id("pb") == RF_COMMAND_PROBE);
    assert(readyfs_command_id("pf") == RF_COMMAND_PROFILE);
    assert(readyfs_command_id("nt") == RF_COMMAND_NATIVE);
    assert(readyfs_command_id("dv") == RF_COMMAND_DRIVES);
    assert(readyfs_command_id("pw") == RF_COMMAND_PWD);
    assert(readyfs_command_id("hi") == RF_COMMAND_HISTORY);
    assert(readyfs_command_id("cl") == RF_COMMAND_CLEAR);
    assert(readyfs_command_id("al") == RF_COMMAND_ALIAS);
    assert(readyfs_command_id("ua") == RF_COMMAND_UNALIAS);
    assert(readyfs_command_id("cf") == RF_COMMAND_CONFIG);
    assert(readyfs_command_id("d") == RF_COMMAND_DIR);
    assert(readyfs_command_id("tr") == RF_COMMAND_TREE);
    assert(readyfs_command_id("st") == RF_COMMAND_STAT);
    assert(readyfs_command_id("vl") == RF_COMMAND_VOLUME);
    assert(readyfs_command_id("mt") == RF_COMMAND_MATCH);
    assert(readyfs_command_id("ty") == RF_COMMAND_TYPE);
    assert(readyfs_command_id("rn") == RF_COMMAND_RENAME);
    assert(readyfs_command_id("dl") == RF_COMMAND_DELETE);
    assert(readyfs_command_id("cm") == RF_COMMAND_COMPARE);
    assert(readyfs_command_id("nw") == RF_COMMAND_NEW);
    assert(readyfs_command_id("wr") == RF_COMMAND_WRITE);
    assert(readyfs_command_id("ap") == RF_COMMAND_APPEND);
    assert(readyfs_command_id("mo") == RF_COMMAND_MOUNT);
    assert(readyfs_command_id("um") == RF_COMMAND_DISMOUNT);
    assert(readyfs_command_id("sw") == RF_COMMAND_SWAP);
    assert(readyfs_command_id("ca") == RF_COMMAND_CAPABILITIES);
    assert(readyfs_command_id("ss") == RF_COMMAND_STATUS);
    assert(readyfs_command_id("fi") == RF_COMMAND_FIND);
    assert(readyfs_command_id("hd") == RF_COMMAND_HEAD);
    assert(readyfs_command_id("tl") == RF_COMMAND_TAIL);
    assert(readyfs_command_id("cr") == RF_COMMAND_CRC32);
    assert(readyfs_command_id("ts") == RF_COMMAND_TEST);
    assert(readyfs_command_id("ru") == RF_COMMAND_RUN);
    assert(readyfs_command_id("cd") == RF_COMMAND_CD);
    assert(readyfs_command_id("ls") == RF_COMMAND_DIR);
    assert(readyfs_command_id("cp") == RF_COMMAND_COPY);
    assert(readyfs_command_id("mv") == RF_COMMAND_MOVE);
    assert(readyfs_command_id("rm") == RF_COMMAND_DELETE);
    assert(readyfs_command_id("md") == RF_COMMAND_MKDIR);
    assert(readyfs_command_id("rd") == RF_COMMAND_RMDIR);
    assert(readyfs_command_id("fm") == RF_COMMAND_MOUNT);
    assert(readyfs_command_id("c") == RF_COMMAND_UNKNOWN);
    assert(readyfs_command_id("co") == RF_COMMAND_UNKNOWN);
    puts("readyfs command/file-type lookup tests passed");
    return 0;
}

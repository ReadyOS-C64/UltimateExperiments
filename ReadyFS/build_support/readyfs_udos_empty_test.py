#!/usr/bin/env python3
"""Exercise the resident OPEN_DIR/lookup/enumeration bodies with firmware replies."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parent.parent
source=(root/'src/apps/readyfs/readyfs.c').read_text()
def body(name):
    start=source.index(name+'(')
    start=source.rfind('static ',0,start)
    opening=source.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
preamble=r'''
#include <assert.h>
#include <string.h>
#include "readyfs_udos_status.h"
#define READYFS_OVERLAY_RUNTIME
#define RF_RESULT_OK 0
#define RF_RESULT_IO 3
typedef void (*ReadyFsUciBlockHandler)(void);
typedef struct { const char *native_name; } ReadyFsStream;
#define RF_UDOS_FIND 2
#define RF_UDOS_HOST_LOOKUP 3
#define RF_LOOKUP_FOUND 1
static unsigned char udos_file(ReadyFsStream *s,unsigned char t,unsigned char o) {(void)s;(void)t;(void)o;return RF_UDOS_HOST_LOOKUP;}
static unsigned char uci_stat[80],uci_cmd[8],last_result,udos_lookup_failed;
static char temp_text[256];
static const char *udos_find_wanted;
static struct { unsigned int stat_len; ReadyFsUciBlockHandler on_block; } uci_xfer;
static unsigned char transport=1,read_result=1;
static unsigned int opens,reads;
static unsigned char uci_call(unsigned char t,unsigned char op,const char *s) {
    assert(t==1 && op==0x13 && s==0); ++opens; return transport;
}
static unsigned char udos_change_absolute(unsigned char t,const char *p) {(void)t;(void)p;return 1;}

static void udos_find_block(void) {}
static void setup_xfer(void) {}
static unsigned char readyfs_uci_command(unsigned char *b,unsigned int n,void *x) {
    (void)x;assert(n==2 && b[0]==1 && b[1]==0x14);++reads;
    if(read_result) {last_result=RF_RESULT_OK;strcpy(temp_text,"wanted");}
    return read_result;
}
'''
tests=r'''
static void reply(const char *s,unsigned int n) {memset(uci_stat,0,sizeof(uci_stat));memcpy(uci_stat,s,n);uci_xfer.stat_len=n;opens=reads=0;transport=1;read_result=1;strcpy(temp_text,"stale");}
int main(void) {
    ReadyFsStream s={"/wanted"};
    reply("",0);assert(!uci_status_ok(1) && !uci_status_ok(5));
    reply("\0",1);assert(!uci_status_ok(1) && uci_status_ok(5));
    reply("00,OK",5);assert(uci_status_ok(1) && uci_status_ok(5));
    reply("01,ERROR",8);assert(!uci_status_ok(1) && !uci_status_ok(5));
    reply("01,DIRECTORY EMPTY",18);
    assert(udos_find_leaf(&s,1)==0 && last_result==RF_RESULT_OK && temp_text[0]==0 && opens==1 && reads==0);
    reply("01,DIRECTORY EMPTY",18);
    assert(dir_ultimate_run("/empty",udos_find_block)==1 && opens==1 && reads==0);
    reply("01,DIRECTORY EMPTY",18);transport=0;
    assert(udos_find_leaf(&s,1)==0 && last_result==RF_RESULT_IO && reads==0);
    reply("01,OTHER DOS ERROR",18);
    assert(udos_find_leaf(&s,1)==0 && last_result==RF_RESULT_IO && reads==0);
    reply("01,DIRECTORY EMPTY",19);
    assert(udos_find_leaf(&s,1)==0 && last_result==RF_RESULT_OK && opens==1 && reads==0);
    reply("01,DIRECTORY EMPTYX",19);
    assert(dir_ultimate_run("/empty",udos_find_block)==0 && reads==0);
    reply("01,DIRECTORY EMPT",17);
    assert(udos_open_directory(1)==0);
    reply("00,OK",5);
    assert(udos_find_leaf(&s,1)==temp_text && !strcmp(temp_text,"wanted") && last_result==RF_RESULT_OK && reads==1);
    reply("00,OK",5);read_result=0;
    assert(udos_find_leaf(&s,1)==0 && last_result==RF_RESULT_IO && reads==1);
    reply("00,OK",5);
    assert(dir_ultimate_run("/normal",udos_find_block)==1 && reads==1);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='readyfs-udos-empty-') as tmp:
    p=Path(tmp)/'test.c';exe=Path(tmp)/'test'
    p.write_text(preamble+'\n'.join(body(n) for n in ('uci_status_ok','udos_open_directory','dir_ultimate_run','udos_find_leaf'))+tests)
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-I'+str(root/'src/apps/readyfs'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS resident Ultimate OPEN_DIR empty/normal/error lookup and enumeration')

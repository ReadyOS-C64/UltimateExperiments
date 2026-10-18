/* Public display contract: every topic, 16-bit blocks, host bounds, CD errors. */
#include "src/apps/readyfs/readyfs_present.h"
#include "src/apps/readyfs/readyfs_path.h"
#include "src/apps/readyfs/readyfs_uci.h"
#include "src/apps/readyfs/readyfs_reu.h"
#include "src/apps/readyfs/readyfs_plan.h"
#include "src/apps/readyfs/readyfs_exec.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char reu[65536];
static unsigned char session[65536];
unsigned char readyfs_reu_session_fetch(unsigned int offset, void *data, unsigned int n) { assert(offset+n<=sizeof(session));memcpy(data,session+offset,n);return 1; }
static unsigned char row; static unsigned pages;
unsigned char wherey(void) { return row; }
char cgetc(void) { return 32; }
void clrscr(void) { row=0; ++pages; }
unsigned char readyfs_reu_batch_store(unsigned int offset, const void *data, unsigned int n) { assert(offset+n<=RF_REU_BATCH_BANK_BYTES);memcpy(reu+offset,data,n);return 1; }
unsigned char readyfs_reu_batch_fetch(unsigned int offset, void *data, unsigned int n) { assert(offset+n<=RF_REU_BATCH_BANK_BYTES);memcpy(data,reu+offset,n);return 1; }
unsigned char readyfs_iec_present(unsigned char d) {return d==8 || d==9;}
unsigned char readyfs_uci_detect(void) {return 1;}
unsigned char readyfs_uci_softiec_bus(void) {return 11;}
static char output[2048]; static unsigned used;
void cputc(char value) { assert(used+1 < sizeof(output)); output[used++]=value; output[used]=0; if(value=='\n')++row; }
void cputs(const char *s) { while (*s) cputc(*s++); }
void cputhex8(unsigned char v) { static const char hex[]="0123456789abcdef"; cputc(hex[v>>4]); cputc(hex[v&15]); }
unsigned char revers(unsigned char on) { return on; }
static void show(ReadyFsUtilityCall *call) { used=0; row=0; output[0]=0; if(call->operation==RF_PRESENT_HELP)readyfs_command_help(call);else assert(readyfs_present(call)); }
static unsigned int plan_entry(unsigned int at,unsigned char kind,unsigned char selected,const char *stem) {
    unsigned int n=strlen(stem); unsigned char *h=session+RF_REU_PLAN_OFF+at;
    h[0]=kind; h[1]=selected; h[2]=n&255; h[3]=n>>8; h[4]=0;h[5]=0;
    memcpy(h+6,stem,n+1);return at+6+n+1;
}
static void transfer_tests(void) {
    ReadyFsUtilityCall call; char scratch[256]; unsigned int at,hash=0,after=0;unsigned i;
    memset(&call,0,sizeof(call));call.operation=RF_PRESENT_COPY;call.buffer="u:/usb1/test/nested/leaf.seq";
    call.argc=0;show(&call);assert(strstr(output,"copying u:/usb1/test/nested/leaf.seq"));
    call.argc=8;show(&call);assert(strstr(output,"moving u:/usb1/test/nested/leaf.seq"));
    call.argc=1;call.value_low=10;show(&call);assert(strstr(output,"verify: identical") && strstr(output,"copied leaf.seq: 10 bytes"));
    call.argc=5;call.value_high=65535;call.value_low=65535;show(&call);assert(strstr(output,"verify: skipped") && strstr(output,"4294967295 bytes"));
    call.argc=9;show(&call);assert(strstr(output,"unavailable for tape"));
    call.argc=2;show(&call);assert((unsigned char)output[0]==0x1c && strstr(output,"copy failed leaf.seq"));
    strcpy((char *)session+RF_REU_RECURSIVE_ROOTS_OFF,"u:/usb1/test/source");
    strcpy((char *)session+RF_REU_RECURSIVE_ROOTS_OFF+RF_PATH_MAX+1u,"u:/usb1/test/target");
    at=plan_entry(0,RF_PLAN_KIND_DIR,RF_PLAN_SELECTED,"nested");
    at=plan_entry(at,RF_PLAN_KIND_FILE,RF_PLAN_SELECTED,"nested/leaf.seq");
    plan_entry(at,RF_PLAN_KIND_FILE,0,"excluded.seq");
    for(i=0;i<sizeof(session);++i)hash=hash*31u+session[i];
    call.operation=RF_PRESENT_PLAN;call.buffer=scratch;call.value_low=3;
    for(i=RF_EXEC_MODE_COPY;i<=RF_EXEC_MODE_DELETE;++i) {
        call.argc=i;used=0;row=0;output[0]=0;assert(readyfs_transfer_plan(&call));
        assert(strstr(output,"from u:/usb1/test/source") && strstr(output,"nested/leaf.seq") && !strstr(output,"excluded.seq"));
        assert(strstr(output,i==RF_EXEC_MODE_COPY?"would copy dir nested":i==RF_EXEC_MODE_MOVE?"would move dir nested":"would delete dir nested"));
        assert(strstr(output,"whatif: no files changed"));
    }
    for(i=0;i<sizeof(session);++i)after=after*31u+session[i];assert(hash==after);
    used=0;row=20;output[0]=0;pages=0;assert(readyfs_transfer_plan(&call));assert(pages && strstr(output,"\x9e-- more --"));
    session[RF_REU_PLAN_OFF+2]=255;session[RF_REU_PLAN_OFF+3]=255;
    assert(!readyfs_transfer_plan(&call));
    call.value_low=0;used=0;output[0]=0;assert(readyfs_transfer_plan(&call));assert(!strstr(output,"would delete") && strstr(output,"no files changed"));
}
int main(void) {
    ReadyFsUtilityCall call; ReadyFsDirectoryEntry entry; ReadyFsUciTransfer xfer; unsigned i; char cwd[256]="8:/"; char stage[256];
    memset(&call,0,sizeof(call)); call.operation=RF_PRESENT_HELP;call.buffer="mount";
    for(i=1;i<=40;++i) {call.value_low=i;show(&call);assert(strstr(output,"unknown")==0);assert(strlen(output)>20);assert(strstr(output,"examples:"));}
    call.value_low=20;show(&call);assert(strstr(output,"copy 8:/sheet2 u:/usb1/sheet2 -w"));assert(strstr(output,"cp @disk:/sheet2 @usb:/sheet2"));
    call.value_low=25;show(&call);assert(strstr(output,"--type seq") && strstr(output,"-t prg"));
    call.value_low=32;show(&call);assert(strstr(output,"swap drive:"));assert(!strstr(output,"swap image"));
    call.value_low=65535;show(&call);assert(strstr(output,"unknown command"));
    call.buffer="FM";call.value_low=30;show(&call);assert(strstr(output,"format path"));
    call.value_low=0;show(&call);assert(strstr(output,"unknown command"));
    call.operation=RF_PRESENT_DIR;strcpy(entry.name,"hello");entry.size=1;entry.type=0x11;call.buffer=(char *)&entry;show(&call);
    assert(strcmp(output,"1    \"hello\"            prg\r\n")==0);
    call.operation=RF_PRESENT_FREE;call.value_low=3160;show(&call);assert(strcmp(output,"3160 blocks free.\r\n")==0);
    call.operation=RF_PRESENT_HOST;call.buffer="folderX";call.capacity=6;call.value_high=2;show(&call);
    assert(strstr(output,"?    \"folder\"") && strstr(output,"dir\r\n") && !strchr(output,'X'));
    call.operation=RF_PRESENT_CD;call.buffer="u:/usb1/test";call.workspace=cwd;call.value_low=0;show(&call);assert(strcmp(cwd,call.buffer)==0);
    call.buffer="8:relative";show(&call);assert(strstr(output,"absolute"));assert(strcmp(cwd,"u:/usb1/test")==0);
    call.value_low=RF_PATH_ESCAPE;show(&call);assert(strcmp(cwd,"u:/usb1/test")==0);
    call.operation=RF_PRESENT_STAGE_NAME;call.buffer="u:/usb1/out.seq";call.workspace=stage;call.argc=RF_EP_ULTIMATE;call.value_low=0xAF;show(&call);assert(!strcmp(stage,"u:/usb1/rftaf"));
    call.argc=RF_EP_IEC;call.buffer="9:/old";show(&call);assert(!strcmp(stage,"9:/rftaf"));
    call.buffer="30:/old";show(&call);assert(!strcmp(stage,"30:/rftaf"));
    call.buffer="10:1:/test/nested/original";show(&call);assert(!strcmp(stage,"10:1:/test/nested/rftaf"));
    call.buffer="10:2:/test/media.d81!/original";show(&call);assert(!strcmp(stage,"10:2:/test/media.d81!/rftaf"));
    call.argc=RF_EP_ULTIMATE;call.buffer="bad-parent";assert(!readyfs_present(&call));
    memset(cwd,'a',sizeof(cwd));cwd[248]='/';cwd[249]='x';cwd[250]=0;call.buffer=cwd;assert(readyfs_present(&call));assert(strlen(stage)==254);
    cwd[248]='a';cwd[249]='/';cwd[250]='x';cwd[251]=0;assert(!readyfs_present(&call));
    call.operation=RF_PRESENT_DATA_TEXT;call.buffer="ok\x01!\x7f";call.value_low=5;show(&call);assert(!strcmp(output,"ok.!."));
    memset(&xfer,0,sizeof(xfer));xfer.flags=1;xfer.last_status=0x10;xfer.data_seen=513;xfer.stat_seen=2;call.operation=RF_PRESENT_UCI_ERROR;call.buffer=(char *)&xfer;show(&call);assert((unsigned char)output[0]==0x1c);assert(strstr(output,"transport $01 st $10 d/s 513/2"));
    xfer.flags=0;xfer.stat=(unsigned char *)"bad\x01";xfer.stat_len=4;show(&call);assert(strstr(output,"target: bad$01 "));
    readyfs_media_reset();call.operation=RF_PRESENT_MEDIA;call.value_low=8;call.value_high=RF_MEDIA_SHOW;show(&call);assert(strstr(output,"8: image path unknown"));
    call.value_high=RF_MEDIA_REMEMBER;call.buffer="u:/usb1/test/my disk.d81";show(&call);assert(strstr(output,"last mounted by readyfs") && strstr(output,call.buffer) && strstr(output,"may have changed elsewhere"));
    call.value_low=9;call.value_high=RF_MEDIA_SHOW;show(&call);assert(strstr(output,"unknown"));
    call.value_low=8;show(&call);assert(strstr(output,"my disk.d81"));
    call.value_high=RF_MEDIA_FORGET;show(&call);call.value_high=RF_MEDIA_SHOW;show(&call);assert(strstr(output,"unknown"));
    memset(stage,'x',255);stage[255]=0;call.value_low=30;call.buffer=stage;call.value_high=RF_MEDIA_REMEMBER;show(&call);assert(strstr(output,stage));
    call.value_high=RF_MEDIA_DRIVES;show(&call);assert(strstr(output,"8: image path unknown") && strstr(output,"9: image path unknown") && !strstr(output,"30:"));
    readyfs_media_reset();call.value_high=RF_MEDIA_SHOW;show(&call);assert(strstr(output,"30: image path unknown"));
    call.value_low=7;assert(!readyfs_present(&call));call.value_low=31;assert(!readyfs_present(&call));
    call.operation=RF_PRESENT_STAT;call.argc=0;call.buffer="HELLO";call.value_low=0x11;show(&call);assert(strstr(output,"display: HELLO") && strstr(output,"type: $11"));
    call.argc=1;call.value_low=65535;show(&call);assert(strstr(output,"raw: HELLO") && strstr(output,"size est: 65535 c64 blocks"));
    call.argc=2;show(&call);assert(strstr(output,"sequential unknown"));
    transfer_tests(); puts("readyfs presentation tests passed"); return 0;
}

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "src/apps/readyfs/readyfs_iec.h"
#include "src/apps/readyfs/readyfs_reu.h"
#include "src/apps/readyfs/readyfs_result.h"

static ReadyFsIecCall call;
static unsigned char command[256], reply[256], status;
static char output[4096];
static unsigned int used;
static unsigned long profiles, media;
static unsigned char listener = 0x80u;
typedef struct {
    unsigned char device;
    const unsigned char *command;
    unsigned int length;
    const unsigned char *reply;
    unsigned int reply_length;
    unsigned char fail_open, short_write, wrote;
} Step;
static Step steps[8];
static unsigned int step, total;
static unsigned char listing[] = {
    1,8, 1,1, 1,0, '"','s','d','"',0,
    1,1, 0,0, '"','s','y','s','t','e','m','"',' ','s','y','s',0,
    1,1, 1,0, '"','b','o','o','t','"',' ','n','a','t',0, 0,0
};
static unsigned int list_offset;
static unsigned char list_open;

static void check(int ok, const char *why) {
    if (!ok) { fprintf(stderr,"IEC test: %s (step %u/%u)\n",why,step,total); exit(1); }
}
unsigned char readyfs_same_word(const char *a, const char *b) {
    while (*a && *b) {
        unsigned char x = (unsigned char)*a++ & 127u, y = (unsigned char)*b++ & 127u;
        if (x >= 65u && x <= 90u) x += 32u;
        if (y >= 65u && y <= 90u) y += 32u;
        if (x != y) return 0;
    }
    return *a == *b;
}
void cputs(const char *s) { size_t n = strlen(s); check(used+n<sizeof(output),"output capacity"); memcpy(output+used,s,n+1);used+=(unsigned int)n; }
void cputc(char c) { char s[2] = {c,0}; cputs(s); }
void cputhex8(unsigned char n) { char s[3]; snprintf(s,sizeof(s),"%02X",n); cputs(s); }
unsigned char cgetc(void) { return 13u; }
unsigned char readyfs_reu_session_store(unsigned int off,const void *data,unsigned int size) {
    check(off>=RF_REU_DRIVE_PROFILE_OFF && off<RF_REU_DRIVE_PROFILE_OFF+92u && size==4u && !*(const unsigned char *)data,"profile invalidation bound");
    profiles |= 1ul << ((off-RF_REU_DRIVE_PROFILE_OFF)/4u); return 1;
}
unsigned char readyfs_reu_batch_store(unsigned int off,const void *data,unsigned int size) {
    check(off>=RF_REU_MEDIA_OFF && off<RF_REU_MEDIA_OFF+RF_REU_MEDIA_BYTES && size==1u && !*(const unsigned char *)data,"media invalidation bound");
    media |= 1ul << ((off-RF_REU_MEDIA_OFF)/256u); return 1;
}
unsigned char cbm_open(unsigned char lfn,unsigned char device,unsigned char sa,const char *name) {
    if (lfn == 2u) { check(device==10u && sa==0u && !strcmp(name,"$=p"),"partition directory OPEN"); list_open=1;list_offset=0;return 0; }
    check(lfn==15u && sa==15u && !*name && step<total,"command channel OPEN");
    check(device==steps[step].device,"command destination"); return steps[step].fail_open;
}
int cbm_write(unsigned char lfn,const void *data,unsigned int length) {
    check(lfn==15u && step<total && length==steps[step].length && !memcmp(data,steps[step].command,length),"exact transmitted command");
    steps[step].wrote=1;return steps[step].short_write ? (int)length-1 : (int)length;
}
int cbm_read(unsigned char lfn,void *data,unsigned int length) {
    if (lfn==2u) {
        check(list_open,"listing open");
        if (length>sizeof(listing)-list_offset) length=sizeof(listing)-list_offset;
        memcpy(data,listing+list_offset,length);list_offset+=length;return (int)length;
    }
    check(lfn==15u && step<total && length>=steps[step].reply_length,"reply capacity");
    memcpy(data,steps[step].reply,steps[step].reply_length);return (int)steps[step].reply_length;
}
void cbm_close(unsigned char lfn) {
    if (lfn==2u) {list_open=0;return;}
    check(lfn==15u && step<total,"balanced close");
    check(steps[step].fail_open || !steps[step].length || steps[step].wrote,"command sent before close");++step;
}
void cbm_k_clrch(void) {}
void cbm_k_listen(unsigned char device) {check(device==13u,"collision checked at new address");}
void cbm_k_second(unsigned char sa) {check(sa==0x6Fu,"command listener secondary");}
unsigned char cbm_k_readst(void) {return listener;}
void cbm_k_unlsn(void) {}

static void reset(void) {
    memset(&call,0,sizeof(call));memset(steps,0,sizeof(steps));
    call.command=command;call.reply=reply;call.status=&status;status=0;
    step=total=used=0;output[0]=0;profiles=media=0;listener=0x80u;
}
static unsigned char plan(unsigned char n, char **args) {call.argc=n;call.args=args;return readyfs_iec_plan(&call);}
static void add(unsigned char dev,const void *cmd,unsigned int len,const void *rep,unsigned int size) {
    Step *s=&steps[total++];s->device=dev;s->command=cmd;s->length=len;s->reply=rep;s->reply_length=size;
}
static void sd(void) {static const char id[]="73,SD2IEC V1.0,00,00\r";add(10,"ui",2,id,sizeof(id)-1);}
#define ARGS(...) (char *[]){__VA_ARGS__}
#define PLAN(n,...) plan(n,ARGS(__VA_ARGS__))
#define REPLY(dev,cmd,text) add(dev,cmd,sizeof(cmd)-1,text,sizeof(text)-1)

int main(void) {
    unsigned char gp[31]={1,0,1};
    unsigned char address[]={ 'u','0','>',13,13 };
    unsigned char raw[]={0x55,0xCA,0};
    char longcmd[121];
    reset();check(PLAN(3,"iec","10:","partition") && call.length==3 && !memcmp(command,"g-p",3),"current G-P omits binary partition");
    check(PLAN(4,"iec","10:","partition","0") && call.length==5 && command[3]==0 && command[4]==13,"explicit SYSTEM partition preserves zero");
    check(PLAN(4,"iec","10:","partition","13") && command[3]==13 && command[4]==13,"partition 13 survives CR stripping");
    check(PLAN(5,"iec","10:","partition","255","--select") && !strcmp((char *)command,"cp255") && call.expected==2,"partition selection is explicit");
    check(!PLAN(5,"iec","10:","partition","0","--select"),"reject selecting system");
    check(!PLAN(4,"iec","10:","partition","256"),"partition range");
    check(!PLAN(3,"iec","10:/file","status"),"device only");
    check(!PLAN(3,"iec","10:","extensions"),"bare XE never sent");
    check(PLAN(4,"iec","10:","images","both") && !strcmp((char *)command,"xi2") && call.expected==0,"XI mapping/status");
    check(PLAN(4,"iec","10:","extensions","4") && !strcmp((char *)command,"xe4") && call.expected==3,"XE mapping/status");
    check(PLAN(4,"iec","10:","hide-extensions","off") && !strcmp((char *)command,"xe-"),"hide off");
    check(PLAN(4,"iec","10:","wildcard","1581") && !strcmp((char *)command,"x*+"),"1581 matching");
    check(PLAN(5,"iec","10:","dos","--hex","55 CA 00") && call.length==3 && !memcmp(command,raw,3),"raw embedded zero");
    check(!PLAN(5,"iec","10:","dos","--hex","55CA"),"require complete separated hex bytes");
    memset(longcmd,'x',120);longcmd[120]=0;
    check(!PLAN(4,"iec","10:","dos",longcmd),"120-byte command rejected");longcmd[119]=0;
    check(PLAN(4,"iec","10:","dos",longcmd) && call.length==119,"119-byte command allowed");
    reset();check(PLAN(3,"iec","10:","status"),"status plan");REPLY(10,"","73,SD2IEC,00,00\r");
    check(readyfs_iec_execute(&call) && step==total && !profiles,"status sends no UI and invalidates nothing");
    reset();check(PLAN(3,"iec","10:","config"),"config plan");sd();REPLY(10,"x","03,E01,10,00\r");
    check(readyfs_iec_execute(&call) && step==total && !profiles,"config read only");
    reset();check(PLAN(4,"iec","10:","images","dirs"),"images plan");sd();REPLY(10,"xi1","00,OK,00,00\r");
    check(readyfs_iec_execute(&call) && step==total,"XI00 succeeds without XW");
    reset();check(PLAN(3,"iec","10:","config"),"other device plan");REPLY(10,"ui","73,CBM DOS,00,00\r");
    check(!readyfs_iec_execute(&call) && status==RF_RESULT_UNSUPPORTED && step==total,"no X sent to non SD2IEC");
    reset();check(PLAN(3,"iec","10:","partition"),"partition plan");sd();gp[30]=13;memcpy(gp+3,"BOOT",4);add(10,"g-p",3,gp,31);
    check(readyfs_iec_execute(&call) && strstr(output,"fat or dnp"),"type1 is ambiguous");
    reset();check(PLAN(4,"iec","10:","partition","99"),"missing partition plan");sd();memset(gp,0,30);add(10,command,5,gp,31);
    check(!readyfs_iec_execute(&call) && status==RF_RESULT_NOT_FOUND,"zero record is absent");
    reset();check(PLAN(3,"iec","10:","partitions"),"partitions plan");sd();
    check(readyfs_iec_execute(&call) && list_offset==sizeof(listing) && !list_open && strstr(output,"boot"),"partition directory EOF without blocks-free footer");
    reset();check(PLAN(5,"iec","10:","address","13","--save") && !memcmp(command,address,5),"address13 bytes");sd();listener=0;
    check(!readyfs_iec_execute(&call) && status==RF_RESULT_CONFLICT && step==total && !profiles,"occupied address never changed");
    reset();check(PLAN(5,"iec","10:","address","13","--save"),"saved address plan");sd();add(10,address,5,"",0);REPLY(13,"ui","73,uIEC,00,00\r");REPLY(13,"xw","03,E01,13,00\r");
    check(readyfs_iec_execute(&call) && step==total && profiles==((1ul<<2)|(1ul<<5)) && media==profiles,"verify new address before save; invalidate only old/new");
    reset();check(PLAN(4,"iec","10:","dos","x?"),"long version escape");REPLY(10,"x?","09,LONG VERSION,00,00\r");
    check(readyfs_iec_execute(&call) && profiles==0x7ffffful,"long version09 is information");
    reset();check(PLAN(3,"iec","10:","initialize"),"initialize plan");REPLY(10,"i","00,OK,00,00\r");steps[0].short_write=1;
    check(!readyfs_iec_execute(&call) && status==RF_RESULT_IO && step==total,"short command write fails with balanced close");
    puts("readyfs native IEC configuration protocol tests passed");return 0;
}

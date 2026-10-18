#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <cbm.h>
#include <cbm_filetype.h>
#include "src/apps/readyfs/readyfs_volume.h"
#include "src/apps/readyfs/readyfs_uci.h"
#include "src/apps/readyfs/readyfs_result.h"
static char output[2048];
static unsigned char requests[8][80],lengths[8],count,available,transport,binary,dos_error;
static unsigned char directory_index,directory_error,closed,result;
static const char *directory;
void cputs(const char *s) {strcat(output,s);}
void cputc(char c) {unsigned n=strlen(output);output[n]=c;output[n+1]=0;}
unsigned char readyfs_uci_detect(void) {return available;}
unsigned char readyfs_uci_softiec_bus(void) {return 11;}
unsigned char readyfs_uci_command(const unsigned char *cmd,unsigned int n,ReadyFsUciTransfer *t) {
    assert(count<8 && n<80);memcpy(requests[count],cmd,n);lengths[count++]=n;
    if(!transport)return 0;
    if(binary) {t->stat[0]=dos_error?8:0;t->stat_len=1;}
    else {memcpy(t->stat,dos_error?"62,ERROR":"00,OK",5);t->stat_len=5;}
    memcpy(t->data,"/USB1/",6);t->data_len=6;return 1;
}
unsigned char cbm_opendir(unsigned char lfn,unsigned int device,...) {
    va_list ap;assert(lfn==6 && device==10);va_start(ap,device);
    assert(!strcmp(va_arg(ap,const char*),directory));va_end(ap);return directory_error==1;
}
unsigned char cbm_readdir(unsigned char lfn,struct cbm_dirent *e) {
    assert(lfn==6);memset(e,0,sizeof(*e));
    if(!directory_index++) {e->type=CBM_T_HEADER;strcpy(e->name,"SD TEST");return 0;}
    e->size=65535;return directory_error?3:2;
}
void cbm_closedir(unsigned char lfn) {assert(lfn==6);closed++;}
void cbm_k_clrch(void) {}
static void reset(void) {
    count=directory_index=directory_error=closed=result=binary=dos_error=0;
    available=transport=1;output[0]=0;memset(requests,0,sizeof(requests));
}
static void run(const char *text) {
    ReadyFsPath path;ReadyFsVolumeCall c={&path,text,directory,&result};
    assert(readyfs_path_parse(text,&path)==RF_PATH_OK);readyfs_volume(&c);
}
int main(void) {
    reset();directory="$1//folder/:*";run("10.1:/folder/");
    assert(closed==1 && !count && !result && strstr(output,"SD TEST") && strstr(output,"65535 c64 blocks"));
    reset();directory_error=1;run("10.1:/folder/");assert(!closed && result==RF_RESULT_IO);
    reset();directory_error=2;run("10.1:/folder/");assert(closed==1 && result==RF_RESULT_IO);
    reset();run("u:/usb1/test");assert(count==4 && !result);
    assert(lengths[0]==3 && !memcmp(requests[0],"\1\21/",3));
    assert(lengths[1]==6 && !memcmp(requests[1],"\1\21usb1",6));
    assert(lengths[2]==6 && !memcmp(requests[2],"\1\21test",6));
    assert(lengths[3]==2 && requests[3][1]==0x12 && strstr(output,"raw path: /USB1/"));
    reset();binary=1;run("s254:/");assert(count==1 && !result && lengths[0]==7);
    assert(requests[0][0]==5 && requests[0][1]==0x22 && !requests[0][2] && !memcmp(requests[0]+3,"254:",4));
    reset();run("s0:/");assert(!result && lengths[0]==5 && requests[0][3]=='0' && requests[0][4]==':');
    reset();binary=dos_error=1;run("s1:/");assert(result==RF_RESULT_IO && strstr(output,"unmapped"));
    reset();available=0;run("u:/");assert(!count && result==RF_RESULT_UNAVAILABLE);
    reset();transport=0;run("u:/folder");assert(count==1 && result==RF_RESULT_IO);
    reset();run("u:/abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnop");
    assert(count==1 && result==RF_RESULT_USAGE && strstr(output,"too long"));
    reset();run("t:/");assert(!count && !result && strstr(output,"no tape free"));
    puts("readyfs volume overlay tests passed");return 0;
}

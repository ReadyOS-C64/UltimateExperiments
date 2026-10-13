#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <cbm.h>
#include <cbm_filetype.h>
#include "src/apps/readyfs/readyfs_files.h"
#include "src/apps/readyfs/readyfs_result.h"
static ReadyFsStream stream,other;
static ReadyFsFilesCall call;
static unsigned char reply[256],result_status;
static struct cbm_dirent entries[3];
static unsigned count,entry_index,end_code,open_error,closed,channel15;
static unsigned pos,input,transport,write_error,sent;
static char command[256];
static const char *dos_reply;
static unsigned char fold(unsigned char c) { c &= 127;return c>='a'&&c<='z'?c-32:c; }
unsigned char readyfs_same_word(const char *a,const char *b) {
    while (*a && *b) if (fold(*a++)!=fold(*b++)) return 0;
    return !*a && !*b;
}
void cputs(const char *s) {(void)s;}
unsigned char cbm_opendir(unsigned char lfn,unsigned char device,...) {
    va_list args; const char *name;
    assert(lfn==6 && device==10);va_start(args,device);name=va_arg(args,const char *);va_end(args);
    assert(!strcmp(name,call.directory?call.directory:"$"));return open_error;
}
unsigned char cbm_readdir(unsigned char lfn,struct cbm_dirent *out) {
    assert(lfn==6);if(entry_index==count)return end_code;*out=entries[entry_index++];return 0;
}
void cbm_closedir(unsigned char lfn) {assert(lfn==6);++closed;}
void cbm_k_talk(unsigned char d) {assert(d==10);input=1;pos=0;}
void cbm_k_tksa(unsigned char s) {assert(s==0x6f);}
unsigned char cbm_k_acptr(void) {assert(input && pos<strlen(dos_reply));return dos_reply[pos++];}
unsigned char cbm_k_readst(void) {return input?(transport?transport:(pos==strlen(dos_reply)?64:0)):write_error;}
void cbm_k_untlk(void) {assert(input);input=0;}
void cbm_k_clrch(void) {}
void cbm_k_listen(unsigned char d) {assert(d==10);sent=0;}
void cbm_k_second(unsigned char s) {assert(s==0x6f);}
void cbm_k_ciout(unsigned char b) {assert(sent+1<sizeof(command));command[sent++]=b;command[sent]=0;}
void cbm_k_unlsn(void) {}
unsigned char cbm_open(unsigned char lfn,unsigned char d,unsigned char sa,const char *name) {
    assert(stream.path.endpoint==RF_EP_SOFTIEC && lfn==15 && sa==15 && d==10);
    strcpy(command,name);++channel15;return 0;
}
void cbm_close(unsigned char lfn) {assert(stream.path.endpoint==RF_EP_SOFTIEC && lfn==15);++channel15;}
static void reset(void) {
    memset(&stream,0,sizeof(stream));memset(&other,0,sizeof(other));memset(&call,0,sizeof(call));
    strcpy(stream.canonical,"hello");stream.native_name=stream.canonical;stream.device=10;stream.path.endpoint=RF_EP_IEC;
    strcpy(other.canonical,"new");other.native_name=other.canonical;
    call.stream=&stream;call.other=&other;call.reply=reply;call.status=&result_status;call.operation=RF_FILES_FIND;
    result_status=0;count=entry_index=closed=channel15=pos=input=transport=write_error=sent=open_error=0;
    end_code=2;dos_reply="00, OK,00,00\r";command[0]=0;
}
static void entry(unsigned char type,const char *name) {entries[count].type=type;strcpy(entries[count++].name,name);}
int main(void) {
    reset();assert(readyfs_files_abi()==RF_FILES_ABI);
    entry(CBM_T_HEADER,"hello");assert(readyfs_files(&call)==RF_LOOKUP_MISSING && closed==1 && channel15==0);
    reset();entry(CBM_T_PRG,"\xC8\xC5\xCC\xCC\xCF");assert(readyfs_files(&call)==RF_LOOKUP_FOUND);
    assert(stream.type==CBM_T_PRG && (unsigned char)stream.native_name[0]==0xc8 && closed==1 && !channel15);
    reset();call.directory="$1//test/nested/";entry(CBM_T_SEQ,"other");assert(readyfs_files(&call)==RF_LOOKUP_MISSING);
    reset();end_code=3;assert(readyfs_files(&call)==RF_LOOKUP_ERROR && result_status==RF_RESULT_IO && closed==1);
    reset();open_error=5;assert(readyfs_files(&call)==RF_LOOKUP_ERROR && !pos);
    reset();entry(CBM_T_SEQ,"hello");dos_reply="62, FILE NOT FOUND,00,00\r";assert(readyfs_files(&call)==RF_LOOKUP_ERROR);
    reset();call.operation=RF_FILES_STATUS;dos_reply="62, FILE NOT FOUND,00,00\r";assert(readyfs_files(&call)==RF_LOOKUP_FOUND && call.dos==62 && !closed && !channel15);
    reset();transport=2;assert(readyfs_files(&call)==RF_LOOKUP_ERROR && !input);
    reset();call.operation=RF_FILES_SCRATCH;dos_reply="01,FILES SCRATCHED,01,00\r";assert(readyfs_files(&call)==RF_LOOKUP_FOUND && !strcmp(command,"s:hello") && !channel15);
    reset();call.operation=RF_FILES_RENAME;assert(readyfs_files(&call)==RF_LOOKUP_FOUND && !strcmp(command,"r:new=hello") && !channel15);
    reset();call.operation=RF_FILES_SCRATCH;assert(readyfs_files(&call)==RF_LOOKUP_ERROR); /* 00 is not SCRATCH success */
    reset();call.operation=RF_FILES_RENAME;write_error=0x80;assert(readyfs_files(&call)==RF_LOOKUP_ERROR && !pos);
    reset();call.operation=RF_FILES_SCRATCH;stream.path.endpoint=RF_EP_SOFTIEC;assert(readyfs_files(&call)==RF_LOOKUP_FOUND && channel15==2);
    puts("native filesystem leaf tests passed: typed lookup, native channel lifetime, scratch/rename status");
    return 0;
}

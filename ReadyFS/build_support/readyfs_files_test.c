#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <cbm.h>
#include <cbm_filetype.h>
#include "src/apps/readyfs/readyfs_files.h"
#include "src/apps/readyfs/readyfs_result.h"
#include "src/apps/readyfs/readyfs_reu.h"
#include "src/apps/readyfs/readyfs_driver.h"
static ReadyFsStream stream,other;
static ReadyFsFilesCall call;
static unsigned char reply[256],result_status;
static char request[120];
static struct cbm_dirent entries[3];
static unsigned count,entry_index,end_code,open_error,closed,channel15;
static unsigned pos,input,transport,write_error,sent;
static char command[256], first_command[256];
static const char *dos_reply;
static unsigned char profile[4],partition_reply[31];
static unsigned native_auto,reply_length,transactions,cache_error;
static const char *identity;
static unsigned response_length(void) {return reply_length ? reply_length : strlen(dos_reply);}
unsigned char readyfs_reu_session_fetch(unsigned int offset,void *out,unsigned int n) {
    assert(offset==RF_REU_DRIVE_PROFILE_OFF+8 && n==4);memcpy(out,profile,4);return !cache_error;
}
unsigned char readyfs_reu_session_store(unsigned int offset,const void *data,unsigned int n) {
    assert(offset==RF_REU_DRIVE_PROFILE_OFF+8 && n==4);memcpy(profile,data,4);return !cache_error;
}
static unsigned char fold(unsigned char c) { c &= 127;return c>='a'&&c<='z'?c-32:c; }
unsigned char readyfs_same_word(const char *a,const char *b) {
    while (*a && *b) if (fold(*a++)!=fold(*b++)) return 0;
    return !*a && !*b;
}
void cputs(const char *s) {(void)s;}
unsigned char cbm_opendir(unsigned char lfn,unsigned int device,...) {
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
unsigned char cbm_k_acptr(void) {assert(input && pos<response_length());return dos_reply[pos++];}
unsigned char cbm_k_readst(void) {return input?(transport?transport:(pos==response_length()?64:0)):write_error;}
void cbm_k_untlk(void) {assert(input);input=0;}
void cbm_k_clrch(void) {}
void cbm_k_listen(unsigned char d) {assert(d==10);sent=0;}
void cbm_k_second(unsigned char s) {assert(s==0x6f);}
void cbm_k_ciout(unsigned char b) {assert(sent+1<sizeof(command));command[sent++]=b;command[sent]=0;}
void cbm_k_unlsn(void) {
    if (!transactions) strcpy(first_command,command);
    ++transactions;
    if(native_auto) {
        if(!strcmp(command,"ui")) {dos_reply=identity;reply_length=0;}
        else {assert(sent==3 || sent==5);assert(!memcmp(command,"g-p",3));dos_reply=(const char*)partition_reply;reply_length=31;}
    }
}
unsigned char cbm_open(unsigned char lfn,unsigned char d,unsigned char sa,const char *name) {
    assert(d==10 && sa==lfn);
    if(lfn==15) { assert(stream.path.endpoint==RF_EP_SOFTIEC);++channel15; }
    else assert(lfn==2);
    strcpy(command,name);return open_error;
}
void cbm_close(unsigned char lfn) {
    if(lfn==15) {assert(stream.path.endpoint==RF_EP_SOFTIEC);++channel15;}
    else {assert(lfn==2);++closed;}
}
static void reset(void) {
    memset(&stream,0,sizeof(stream));memset(&other,0,sizeof(other));memset(&call,0,sizeof(call));
    strcpy(stream.canonical,"hello");stream.native_name=stream.canonical;stream.device=10;stream.path.endpoint=RF_EP_IEC;
    strcpy(other.canonical,"new");other.native_name=other.canonical;other.device=10;
    call.stream=&stream;call.other=&other;call.reply=reply;call.request=request;call.status=&result_status;call.operation=RF_FILES_FIND;
    result_status=0;count=entry_index=closed=channel15=pos=input=transport=write_error=sent=open_error=0;
    memset(profile,0,sizeof(profile));memset(partition_reply,0,sizeof(partition_reply));
    partition_reply[0]=1;partition_reply[1]=0xe2;partition_reply[2]=7;partition_reply[30]=13;
    identity="73,SD2IEC V1.0.0,00,00\r";native_auto=reply_length=transactions=cache_error=0;
    end_code=2;dos_reply="00, OK,00,00\r";command[0]=0;
}
static unsigned char execute(void) {
    unsigned char result = readyfs_files_plan(&call);
    return result == RF_LOOKUP_FOUND ? readyfs_files(&call) : result;
}
static unsigned char prepare_native(void) {
    ReadyFsStreamCall c={&stream,&result_status,reply};native_auto=1;
    return readyfs_files_prepare(&c);
}
static void entry(unsigned char type,const char *name) {entries[count].type=type;strcpy(entries[count++].name,name);}
int main(void) {
    reset();assert(readyfs_files_abi()==RF_FILES_ABI);
    entry(CBM_T_HEADER,"hello");assert(execute()==RF_LOOKUP_MISSING && closed==1 && channel15==0);
    reset();entry(CBM_T_PRG,"\xC8\xC5\xCC\xCC\xCF");assert(execute()==RF_LOOKUP_FOUND);
    assert(stream.type==CBM_T_PRG && (unsigned char)stream.native_name[0]==0xc8 && closed==1 && !channel15);
    reset();strcpy(stream.canonical,"test/nested/hello");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=1;entry(CBM_T_SEQ,"other");assert(execute()==RF_LOOKUP_MISSING);
    reset();end_code=3;assert(execute()==RF_LOOKUP_ERROR && result_status==RF_RESULT_IO && closed==1);
    reset();open_error=5;assert(execute()==RF_LOOKUP_ERROR && !pos);
    reset();entry(CBM_T_SEQ,"hello");dos_reply="62, FILE NOT FOUND,00,00\r";assert(execute()==RF_LOOKUP_ERROR);
    reset();call.operation=RF_FILES_STATUS;dos_reply="62, FILE NOT FOUND,00,00\r";assert(execute()==RF_LOOKUP_FOUND && call.dos==62 && !closed && !channel15);
    reset();transport=2;assert(execute()==RF_LOOKUP_ERROR && !input);
    reset();call.operation=RF_FILES_SCRATCH;dos_reply="01,FILES SCRATCHED,01,00\r";assert(execute()==RF_LOOKUP_FOUND && !strcmp(command,"s:hello") && !channel15);
    reset();call.operation=RF_FILES_RENAME;assert(execute()==RF_LOOKUP_FOUND && !strcmp(command,"r:new=hello") && !channel15);
    reset();call.operation=RF_FILES_SCRATCH;assert(execute()==RF_LOOKUP_ERROR); /* 00 is not SCRATCH success */
    reset();call.operation=RF_FILES_RENAME;write_error=0x80;assert(execute()==RF_LOOKUP_ERROR && !pos);
    reset();call.operation=RF_FILES_SCRATCH;stream.path.endpoint=RF_EP_SOFTIEC;assert(execute()==RF_LOOKUP_FOUND && channel15==2);
    reset();stream.lfn=2;stream.type=CBM_T_SEQ;call.operation=RF_FILES_OPEN_READ;
    assert(execute()==RF_LOOKUP_FOUND && !strcmp(command,"hello,s,r") && !closed && !channel15);
    reset();stream.lfn=2;stream.type=CBM_T_USR;call.operation=RF_FILES_OPEN_WRITE;
    assert(execute()==RF_LOOKUP_FOUND && !strcmp(command,"hello,u,w") && !closed);
    reset();stream.lfn=2;stream.type=CBM_T_PRG;call.operation=RF_FILES_OPEN_WRITE;dos_reply="63,FILE EXISTS,00,00\r";
    assert(execute()==RF_LOOKUP_ERROR && closed==1 && !channel15);
    reset();stream.lfn=2;stream.type=CBM_T_SEQ;call.operation=RF_FILES_OPEN_READ;open_error=5;
    assert(execute()==RF_LOOKUP_ERROR && closed==1 && !pos);
    reset();stream.lfn=2;stream.type=CBM_T_REL;call.operation=RF_FILES_OPEN_WRITE;
    assert(execute()==RF_LOOKUP_ERROR && result_status==RF_RESULT_UNSUPPORTED && !*command);
    reset();stream.lfn=2;stream.open=1;call.operation=RF_FILES_CLOSE;
    assert(execute()==RF_LOOKUP_FOUND && closed==1 && !stream.open && !channel15);
    reset();stream.lfn=2;stream.open=1;call.operation=RF_FILES_CLOSE;write_error=0x80;
    assert(execute()==RF_LOOKUP_ERROR && closed==1 && !stream.open && !pos);
    reset();stream.lfn=2;stream.open=1;call.operation=RF_FILES_CLOSE;dos_reply="72,DISK FULL,00,00\r";
    assert(execute()==RF_LOOKUP_ERROR && closed==1 && !stream.open && result_status==RF_RESULT_IO);
    reset();stream.lfn=2;stream.type=CBM_T_SEQ;stream.path.endpoint=RF_EP_SOFTIEC;call.operation=RF_FILES_OPEN_READ;
    assert(execute()==RF_LOOKUP_FOUND && !pos && !channel15); /* preserve SoftIEC lifecycle */
    reset();strcpy(stream.canonical,"test/nested/hello");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=13;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(call.directory,"$13//test/nested/:*"));
    call.operation=RF_FILES_OPEN_READ;assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"13//test/nested/:hello"));
    assert(!strcmp(stream.native_name,"test/nested/hello"));
    call.operation=RF_FILES_SCRATCH;assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"s13//test/nested/:hello"));
    other.native_mode=RF_NATIVE_HIER;other.native_partition=13;strcpy(other.canonical,"test/nested/new");
    call.operation=RF_FILES_RENAME;assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"r13//test/nested/:new=13//test/nested/:hello"));
    strcpy(other.canonical,"test/another/new");assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    strcpy(other.canonical,"TEST/NESTED/new");assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND);
    other.native_partition=1;assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();stream.native_mode=RF_NATIVE_FLAT;stream.native_partition=254;call.operation=RF_FILES_OPEN_READ;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"254:hello"));
    call.operation=RF_FILES_FIND;assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"$254:*"));
    stream.native_partition=0;assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    stream.native_partition=255;assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"test/hello");stream.native_mode=RF_NATIVE_FLAT;stream.native_partition=1;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"@hello");assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR && !closed && !channel15);
    reset();strcpy(stream.canonical,"$hello");assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"#");assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"$hello");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=1;call.operation=RF_FILES_OPEN_READ;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,"1//:$hello"));
    reset();strcpy(stream.canonical,"hello,s,w");assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"dir/../hello");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=1;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR);
    reset();strcpy(stream.canonical,"abcdefghijklmnop/more/hello");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=1;
    entry(CBM_T_SEQ,"\xC8\xC5\xCC\xCC\xCF");assert(execute()==RF_LOOKUP_FOUND);
    assert(!strncmp(stream.native_name,"abcdefghijklmnop/more/",22) && (unsigned char)stream.native_name[22]==0xc8);
    reset();strcpy(stream.canonical,"abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop");stream.native_mode=RF_NATIVE_HIER;stream.native_partition=254;call.operation=RF_FILES_OPEN_WRITE;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_ERROR); /* includes suffix budget */
    reset();strcpy(stream.canonical,"long softwareiec logical name");stream.path.endpoint=RF_EP_SOFTIEC;call.operation=RF_FILES_OPEN_READ;
    assert(readyfs_files_plan(&call)==RF_LOOKUP_FOUND && !strcmp(request,stream.native_name));
    reset();assert(prepare_native() && transactions==2 && !channel15);
    assert(stream.native_mode==RF_NATIVE_HIER && stream.native_partition==7 && profile[2]==RF_DRIVER_SD2IEC);
    assert(prepare_native() && transactions==3); /* cached identity, fresh G-P */
    stream.path.partition=13;partition_reply[0]=4;partition_reply[2]=13;
    assert(prepare_native() && sent==5 && (unsigned char)command[3]==13 && command[4]==13 && stream.native_mode==RF_NATIVE_FLAT && stream.native_partition==13);
    reset();identity="73,uIEC TEST,00,00\r";assert(prepare_native() && stream.native_partition==7);
    reset();identity="73,CBM DOS V10 1581,00,00\r";assert(prepare_native() && transactions==1 && !stream.native_mode && profile[2]==RF_DRIVER_LEGACY);
    stream.path.partition=1;assert(!prepare_native() && result_status==RF_RESULT_UNSUPPORTED && transactions==1);
    reset();partition_reply[0]=0;assert(!prepare_native() && result_status==RF_RESULT_NOT_FOUND);
    reset();partition_reply[2]=0;assert(!prepare_native() && result_status==RF_RESULT_IO);
    reset();stream.path.partition=1;assert(!prepare_native() && result_status==RF_RESULT_IO); /* mismatched partition */
    reset();partition_reply[30]=0;assert(!prepare_native() && result_status==RF_RESULT_IO);
    reset();partition_reply[0]=255;assert(!prepare_native() && result_status==RF_RESULT_UNSUPPORTED);
    reset();write_error=0x80;assert(!prepare_native() && !pos && result_status==RF_RESULT_IO);
    reset();cache_error=1;assert(!prepare_native() && transactions==1 && result_status==RF_RESULT_IO);
    reset();assert(readyfs_files_plan_abi()==RF_FILES_PLAN_ABI);
    stream.native_mode=RF_NATIVE_HIER;stream.native_partition=13;strcpy(stream.canonical,"test/nested/leaf");
    call.operation=RF_FILES_MKDIR;assert(execute()==RF_LOOKUP_FOUND && !strcmp(command,"md13//test/nested/:leaf"));
    call.operation=RF_FILES_RMDIR;transactions=0;
    assert(execute()==RF_LOOKUP_FOUND && !strcmp(first_command,"cd13//test/nested/") && !strcmp(command,"rd13:leaf") && transactions==2 && !channel15);
    reset();stream.native_mode=RF_NATIVE_HIER;stream.native_partition=1;call.operation=RF_FILES_RMDIR;
    dos_reply="62,FILE NOT FOUND,00,00\r";assert(execute()==RF_LOOKUP_ERROR && transactions==1); /* never RD when CD failed */
    reset();stream.native_mode=RF_NATIVE_FLAT;stream.native_partition=1;call.operation=RF_FILES_MKDIR;
    assert(execute()==RF_LOOKUP_ERROR && !transactions);
    reset();stream.native_mode=RF_NATIVE_HIER;stream.native_partition=254;strcpy(stream.canonical,"abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghijklmnop/abcdefghij");call.operation=RF_FILES_RMDIR;
    assert(execute()==RF_LOOKUP_ERROR && !transactions);
    reset();call.operation=RF_FILES_UDOS_TYPE;memcpy(reply+8,"prg",3);assert(execute()==CBM_T_PRG && !transactions);
    memcpy(reply+8,"USR",3);assert(execute()==CBM_T_USR);
    memcpy(reply+8,"\xD2\xC5\xCC",3);assert(execute()==CBM_T_REL);
    memcpy(reply+8,"txt",3);assert(execute()==CBM_T_SEQ);
    puts("native filesystem leaf tests passed: typed lookup, native channel lifetime, scratch/rename status");
    return 0;
}

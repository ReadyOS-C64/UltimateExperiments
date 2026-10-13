/* Exercise actual cold phases against independent DOS replies, including the
 * transport's callback reset and file-handle ownership rules. */
#include <assert.h>
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include "../src/apps/readyfs/readyfs_udos_files.h"
#include "../src/apps/readyfs/readyfs_uci.h"
#include "../src/apps/readyfs/readyfs_result.h"
#include <cbm_filetype.h>

struct File {char name[17];unsigned char type;int payload,live;} files[24];
static int count,cwd[3],handle[3],commands,opens,creates;
static int bad_stat,bad_info,bad_close,bad_directory,fail_rename,transport_open;
static const char *open_error;
static unsigned char result,live_targets;
static char access_name[80],decoded_name[17],wire_name[40];
static ReadyFsStream stream,other;
static ReadyFsUdosFilesCall call;
void cputs(const char *s) {(void)s;}
void cputc(char c) {(void)c;}
static const char *extension(unsigned char type) {
    if(type==CBM_T_PRG)return "PRG";
    if(type==CBM_T_SEQ)return "SEQ";
    if(type==CBM_T_USR)return "USR";
    if(type==CBM_T_REL)return "REL";
    return "???";
}
static unsigned char parse(const char *wire,char *name) {
    const char *end=wire+strlen(wire),*dot=strrchr(wire,'.');
    unsigned char type=0;int n=0,hex=0;
    if(dot && strlen(dot)==4) {
        if(!strcasecmp(dot,".seq"))type=CBM_T_SEQ;
        if(!strcasecmp(dot,".prg"))type=CBM_T_PRG;
        if(!strcasecmp(dot,".usr"))type=CBM_T_USR;
        if(!strcasecmp(dot,".rel"))type=CBM_T_REL;
        if(type)end=dot;
    }
    while(wire<end) {
        if(*wire=='{'){hex=1;++wire;continue;}
        if(*wire=='}'){hex=0;++wire;continue;}
        assert(n<16);
        if(hex) {unsigned value;assert(sscanf(wire,"%2x",&value)==1);name[n++]=(char)value;wire+=2;}
        else name[n++]=(char)toupper((unsigned char)*wire++);
    }
    name[n]=0;return type;
}
static int find_file(const char *wire) {
    char name[17];unsigned char type=parse(wire,name);int i;
    for(i=0;i<count;++i)if(files[i].live && !strcmp(files[i].name,name) && (!type || type==files[i].type))return i;
    return -1;
}
static int add(const char *name,unsigned char type,int payload) {
    int i=count++;assert(i<24);strcpy(files[i].name,name);files[i].type=type;files[i].payload=payload;files[i].live=1;return i;
}
static void reply(ReadyFsUciTransfer *x,const char *status) {
    size_t n=strlen(status)+1;assert(n<=x->stat_cap);memcpy(x->stat,status,n);x->stat_len=(unsigned int)n;
}
static void info(ReadyFsUciTransfer *x,const char *name,unsigned char type,unsigned char attributes) {
    size_t n=strlen(name);assert(n+12<=x->data_cap);memset(x->data,0,n+12);
    memcpy(x->data+8,extension(type),3);x->data[11]=attributes;memcpy(x->data+12,name,n);x->data_len=(unsigned int)(n+12);reply(x,"00,OK");
}
static void block(ReadyFsUciTransfer *x,const char *name,unsigned char attributes,const char *status) {
    unsigned char data[80];size_t n=strlen(name);data[0]=attributes;memcpy(data+1,name,n);
    x->on_block(data,(unsigned int)n+1,(const unsigned char *)status,(unsigned int)strlen(status));
    /* Real transport clears both lengths after the callback, including LAST. */
    x->data_len=x->stat_len=0;
}
unsigned char readyfs_uci_command(const unsigned char *cmd,unsigned int n,ReadyFsUciTransfer *x) {
    int target=cmd[0],i;const char *name=(const char *)cmd+2;
    ++commands;assert(target==1 || target==2);x->data_len=x->stat_len=0;
    switch(cmd[1]) {
    case 0x11:
        assert(cmd[n-1]==0);
        if(!strcmp(name,"/"))cwd[target]=0;
        else if(!strcasecmp(name,"usb1") && cwd[target]==0)cwd[target]=1;
        else if(!strcasecmp(name,"disk.d64") && cwd[target]==1)cwd[target]=2;
        else if(!strcasecmp(name,"fake.d64") && cwd[target]==1)cwd[target]=3;
        else {reply(x,"PATH DOESN'T EXIST");return 1;}
        reply(x,"00,OK");break;
    case 0x08:
        assert(cmd[n-1]==0); /* Required by the firmware's FILE_STAT handler. */
        if(cwd[target]==1 && !strcasecmp(name,"disk.d64"))info(x,"disk.d64",0,0);
        else if(cwd[target]==1 && !strcasecmp(name,"fake.d64"))info(x,"fake.d64",0,0x10);
        else if(!bad_stat && (i=find_file(name))>=0)info(x,files[i].name,files[i].type,0);
        else reply(x,"82,FILE NOT FOUND");break;
    case 0x13:reply(x,"00,OK");break;
    case 0x14:
        assert(x->on_block);
        if(cwd[target]==1) {block(x,"disk.d64",0,"");block(x,"fake.d64",0x10,bad_directory?"DISK ERROR":"00,OK");}
        else {
            for(i=0;i<count;++i)if(files[i].live && files[i].name[0]!='.')block(x,files[i].name,0,"");
            x->on_block(0,0,(const unsigned char *)(bad_directory?"DISK ERROR":"00,OK"),bad_directory?10:5);x->data_len=x->stat_len=0;
        }
        break;
    case 0x02:
        ++opens;assert(handle[target]<0);assert(cmd[n-1]==0);name=(const char *)cmd+3;
        if(open_error){reply(x,open_error);return 1;}
        i=find_file(name);
        if(cmd[2]==6) {
            char raw[17];unsigned char type=parse(name,raw);++creates;
            if(i>=0){reply(x,"FILE EXISTS");return 1;}
            i=add(raw,type?type:CBM_T_PRG,0);
        }
        if(i<0){reply(x,"FILE DOESN'T EXIST");return 1;}
        handle[target]=i;
        if(transport_open){x->flags=RF_UCI_TIMEOUT;return 0;}
        reply(x,"00,OK");break;
    case 0x07:
        assert(handle[target]>=0);i=handle[target];
        if(bad_info)reply(x,"82,FILE NOT FOUND");
        else info(x,files[i].name,files[i].type,0);break;
    case 0x03:
        if(bad_close){reply(x,"DISK ERROR");return 1;}
        assert(handle[target]>=0);handle[target]=-1;reply(x,"00,OK");break;
    case 0x0a: {
        char raw[17];unsigned char type;const char *destination=name+strlen(name)+1;
        assert(cmd[n-1]==0);i=find_file(name);assert(i>=0);
        if(fail_rename){fail_rename=0;reply(x,"DISK ERROR");return 1;}
        assert(find_file(destination)<0);type=parse(destination,raw);
        strcpy(files[i].name,raw);files[i].type=type?type:CBM_T_PRG;reply(x,"00,OK");break;
    }
    default:assert(!"unexpected opcode");
    }
    return 1;
}
static void path(ReadyFsStream *s,const char *name) {
    memset(s,0,sizeof(*s));strcpy(s->canonical,name);s->native_name=s->canonical+2;s->text=s->canonical;s->path.endpoint=RF_EP_ULTIMATE;
}
static void reset(void) {
    memset(files,0,sizeof(files));count=commands=opens=creates=0;cwd[1]=cwd[2]=0;handle[1]=handle[2]=-1;
    bad_stat=bad_info=bad_close=bad_directory=fail_rename=transport_open=0;open_error=0;live_targets=0;
    memset(&call,0,sizeof(call));call.stream=&stream;call.other=&other;call.access=access_name;call.name=decoded_name;call.wire=wire_name;
    call.status=&result;call.open_targets=&live_targets;call.target=1;call.type=CBM_T_SEQ;
    path(&stream,"u:/usb1/disk.d64/NOTE");path(&other,"u:/usb1/disk.d64/DEST");
}
/* Use the production resident gateway. Mock only cache transfers here; the
 * machine-code test separately executes real cc65 frame and DMA boundaries. */
static unsigned char phase_active,phase_fail=255u;
static unsigned int phase_restores;
static unsigned char open_batch_cached(unsigned char slot) {
    assert(!phase_active && slot>=10u && slot<=13u);
    if(slot==phase_fail)return 0u;
    phase_active=slot;return 1u;
}
static void restore_match(void) {assert(phase_active);phase_active=0u;++phase_restores;}
#include "gateway.inc"
static unsigned char run(unsigned char operation) {
    call.operation=operation;
    return readyfs_overlay_udos(&call);
}
int main(void) {
    int before,i;unsigned char types[]={CBM_T_SEQ,CBM_T_PRG,CBM_T_USR};
    for(i=0;i<3;++i) {
        reset();add("NOTE",types[i],42);assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);assert(stream.type==types[i]);assert(!live_targets);
        assert(run(RF_UDOS_READ)==RF_LOOKUP_FOUND);assert(stream.type==types[i] && live_targets==1);assert(run(RF_UDOS_CLOSE)==RF_LOOKUP_FOUND && !live_targets);
        path(&stream,"u:/usb1/disk.d64/STAGE");call.type=types[i];assert(run(RF_UDOS_NEW)==RF_LOOKUP_FOUND);assert(files[handle[1]].type==types[i]);assert(run(RF_UDOS_CLOSE)==RF_LOOKUP_FOUND);
        assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);call.source_access=access_name;assert(run(RF_UDOS_RENAME)==RF_LOOKUP_FOUND);assert(files[1].type==types[i] && !strcmp(files[1].name,"DEST"));
    }
    reset();add("NOTE",CBM_T_SEQ,42);bad_stat=1;path(&stream,"u:/usb1/disk.d64/NOTE.seq");assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);assert(opens==1 && !live_targets && handle[1]<0);
    path(&stream,"u:/usb1/disk.d64/MISSING.seq");assert(run(RF_UDOS_FIND)==RF_LOOKUP_MISSING && result==RF_RESULT_OK);
    open_error="DISK ERROR";assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && result==RF_RESULT_IO);
    open_error="PATH DOESN'T EXIST";assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR);
    reset();add("NOTE",CBM_T_SEQ,42);bad_directory=1;assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR);
    reset();add("NOTE",CBM_T_SEQ,42);add("NOTE",CBM_T_PRG,77);assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && result==RF_RESULT_CONFLICT);
    path(&stream,"u:/usb1/disk.d64/NOTE.prg");assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND && stream.type==CBM_T_PRG);
    reset();path(&stream,"u:/usb1/fake.d64/HOST");assert(run(RF_UDOS_FIND)==RF_UDOS_HOST_LOOKUP && !stream.native_mode);
    reset();path(&stream,"u:/usb1/disk.d64/ABCDEFGHIJKLMNOPQ.seq");before=creates;assert(run(RF_UDOS_NEW)==RF_LOOKUP_ERROR && creates==before);
    path(&stream,"u:/usb1/disk.d64/{4142434445464748494a4b4c4d4e4f50}.seq");assert(run(RF_UDOS_NEW)==RF_LOOKUP_FOUND);assert(!strcmp(files[0].name,"ABCDEFGHIJKLMNOP"));assert(run(RF_UDOS_CLOSE)==RF_LOOKUP_FOUND);
    path(&stream,"u:/usb1/disk.d64/BAD{41.seq");assert(run(RF_UDOS_NEW)==RF_LOOKUP_ERROR);
    path(&stream,"u:/usb1/disk.d64/WRONG.prg");assert(run(RF_UDOS_NEW)==RF_LOOKUP_ERROR && result==RF_RESULT_CONFLICT);
    reset();add("NOTE",CBM_T_SEQ,42);assert(run(RF_UDOS_READ)==RF_LOOKUP_FOUND);before=commands;assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && commands==before);
    bad_close=1;assert(run(RF_UDOS_CLOSE)==RF_LOOKUP_ERROR && live_targets==1);before=commands;assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && commands==before);
    reset();add("NOTE",CBM_T_SEQ,42);path(&stream,"u:/usb1/disk.d64/NOTE.seq");bad_stat=bad_info=1;assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && !live_targets && handle[1]<0);
    reset();add("NOTE",CBM_T_SEQ,42);transport_open=1;assert(run(RF_UDOS_READ)==RF_LOOKUP_ERROR && !live_targets && handle[1]<0);
    reset();add("NOTE",CBM_T_SEQ,42);assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);call.source_access=access_name;path(&other,"u:/usb1/disk.d64/BACKUP");assert(run(RF_UDOS_RENAME)==RF_LOOKUP_FOUND);assert(files[0].type==CBM_T_SEQ && files[0].payload==42);
    path(&stream,"u:/usb1/disk.d64/BACKUP");path(&other,"u:/usb1/disk.d64/NOTE");assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);call.source_access=access_name;fail_rename=1;assert(run(RF_UDOS_RENAME)==RF_LOOKUP_ERROR && !strcmp(files[0].name,"BACKUP"));assert(run(RF_UDOS_RENAME)==RF_LOOKUP_FOUND);assert(files[0].type==CBM_T_SEQ && files[0].payload==42);
    reset();add(".NOTE",CBM_T_SEQ,42);path(&stream,"u:/usb1/disk.d64/.NOTE");assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND && stream.type==CBM_T_SEQ && !live_targets);
    add(".NOTE",CBM_T_USR,77);assert(run(RF_UDOS_FIND)==RF_LOOKUP_ERROR && result==RF_RESULT_CONFLICT && !live_targets);
    path(&stream,"u:/usb1/disk.d64/.NOTE.usr");assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND && stream.type==CBM_T_USR);
    reset();path(&stream,"u:/usb1/disk.d6?/NOTE");assert(run(RF_UDOS_PARENT)==RF_LOOKUP_ERROR && result==RF_RESULT_USAGE);
    path(&stream,"u:/usb1/disk.d*/NOTE");assert(run(RF_UDOS_PARENT)==RF_LOOKUP_ERROR && result==RF_RESULT_USAGE);
    reset();path(&stream,"u:/usb1/ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ");assert(run(RF_UDOS_PARENT)==RF_LOOKUP_FOUND && !stream.native_mode);
    reset();add("NOTE",CBM_T_SEQ,42);path(&stream,"u:/usb1/disk.d64/NOTE.seq");
    assert(run(RF_UDOS_FIND)==RF_LOOKUP_FOUND);
    path(&other,"u:/USB1/DISK.D64/{4e4f5445}");other.type=CBM_T_SEQ;
    before=creates;assert(run(RF_UDOS_DISTINCT)==RF_LOOKUP_ERROR && result==RF_RESULT_CONFLICT && creates==before);
    path(&other,"u:/usb1/disk.d64/NOTE.usr");other.type=CBM_T_USR;
    assert(run(RF_UDOS_DISTINCT)==RF_LOOKUP_FOUND);
    path(&other,"u:/usb1/disk.d64/DIFFERENT");assert(run(RF_UDOS_DISTINCT)==RF_LOOKUP_FOUND);
    for(i=10;i<=13;++i) {
        reset();add("NOTE",CBM_T_SEQ,42);phase_fail=(unsigned char)i;
        assert(run(RF_UDOS_READ)==RF_LOOKUP_ERROR && result==RF_RESULT_IO);
        assert(!live_targets && !phase_active && !creates);
    }
    phase_fail=255u;assert(phase_restores);
    reset();live_targets=2u;before=commands;assert(run(RF_UDOS_RENAME)==RF_LOOKUP_ERROR && result==RF_RESULT_IO && commands==before);
    puts("ReadyFS UltimateDOS cold phases: PASS (typed lookup, errors, context, ownership, names, stage/rename/rollback type)");return 0;
}

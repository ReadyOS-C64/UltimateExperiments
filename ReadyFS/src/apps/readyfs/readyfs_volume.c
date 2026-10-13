/* Cold volume queries share slot16 with pure stream policy. No nested overlay
 * calls: transport is the resident UCI state machine, formatting is local. */
#include "readyfs_volume.h"
#include "readyfs_uci.h"
#include "readyfs_console.h"
#include "readyfs_result.h"
#include <cbm.h>
#include <cbm_filetype.h>
#include <conio.h>
#include <string.h>
static unsigned char command[70],data[128],status[80];
static ReadyFsUciTransfer transfer;
static struct cbm_dirent entry;
static unsigned char *result_status;
static void number(unsigned int n) {
    char out[6]; unsigned char i;
    i=5u; out[i]=0;
    do { out[--i]='0'+n%10u; n/=10u; } while(n);
    cputs(out+i);
}
static void text(void) {
    unsigned int i;
    for(i=0u;i<transfer.data_len;++i)
        cputc(data[i]>=32u && data[i]<127u ? data[i] : '.');
    cputs("\r\n");
}
static unsigned char query(unsigned char target,unsigned char opcode,
                           const char *arg) {
    unsigned int n;
    command[0]=target; command[1]=opcode; n=2u;
    if(target==5u && opcode==0x22u)command[n++]=0u;
    if(arg) { strcpy((char*)command+n,arg); n+=strlen(arg); }
    memset(&transfer,0,sizeof(transfer));
    transfer.data=data; transfer.data_cap=sizeof(data);
    transfer.stat=status; transfer.stat_cap=sizeof(status);
    if(!readyfs_uci_command(command,n,&transfer)) {
        *result_status=RF_RESULT_IO;cputs(RF_ERROR "uci failed\r\n");return 0u;
    }
    if((target==5u && transfer.stat_len!=0u && status[0]==0u) ||
       (transfer.stat_len>=2u && status[0]=='0' && status[1]=='0'))return 1u;
    *result_status=RF_RESULT_IO;
    if(target==5u && transfer.stat_len && status[0]==8u)cputs("unmapped\r\n");
    else cputs(RF_ERROR "dos failed\r\n");
    return 0u;
}
static unsigned char change(const char *path) {
    char part[64]; unsigned char n;
    if(!query(1u,0x11u,"/"))return 0u;
    while(*path=='/')++path;
    while(*path) {
        n=0u;
        while(*path && *path!='/' && *path!='!') {
            if(n==sizeof(part)-1u) {
                *result_status=RF_RESULT_USAGE;
                cputs(RF_ERROR "path component too long\r\n");return 0u;
            }
            part[n++]=*path++;
        }
        part[n]=0;
        while(*path=='/' || *path=='!')++path;
        if(n && !query(1u,0x11u,part))return 0u;
    }
    return 1u;
}
void readyfs_volume(ReadyFsVolumeCall *c) {
    unsigned char rc,saw;
    char mapping[6];
    result_status=c->status;
    cputs("path: ");cputs(c->text);cputs("\r\n");
    if(c->path->endpoint==RF_EP_IEC) {
        cputs("backend: iec device ");number(c->path->unit);cputs("\r\n");
        if(cbm_opendir(6u,c->path->unit,c->directory)!=0u) {
            *result_status=RF_RESULT_IO;cputs(RF_ERROR "dir open failed\r\n");return;
        }
        saw=0u;
        do {
            rc=cbm_readdir(6u,&entry);
            if(!rc && entry.type==CBM_T_HEADER && !saw) {
                cputs("volume: ");cputs(entry.name);cputs("\r\n");saw=1u;
            }
        }while(!rc);
        cbm_closedir(6u);cbm_k_clrch();
        if(rc==2u) { cputs("free: ");number(entry.size);cputs(" c64 blocks\r\n"); }
        else { *result_status=RF_RESULT_IO;cputs(RF_ERROR "free unavailable\r\n"); }
        return;
    }
    if(c->path->endpoint==RF_EP_TAPE) {
        cputs("tape backend\r\nno tape free\r\n");return;
    }
    if(!readyfs_uci_detect()) {
        *result_status=RF_RESULT_UNAVAILABLE;cputs(RF_ERROR "uci unavailable\r\n");return;
    }
    if(c->path->endpoint==RF_EP_ULTIMATE) {
        cputs("ultimate dos\r\n");
        if(!change(c->text+c->path->path_offset))return;
        if(query(1u,0x12u,0)) { cputs("raw path: ");text(); }
    }else if(c->path->endpoint==RF_EP_SOFTIEC) {
        cputs("backend: softiec partition ");number(c->path->unit);
        cputs(" on bus ");number(readyfs_uci_softiec_bus());cputs("\r\n");
        /* GET_FATNAME receives binary channel0 then decimal partition ':'. */
        rc=0u;saw=c->path->unit;
        if(saw>=100u) { mapping[rc++]='0'+saw/100u;saw%=100u; }
        if(c->path->unit>=10u)mapping[rc++]='0'+saw/10u;
        mapping[rc++]='0'+saw%10u;mapping[rc++]=':';mapping[rc]=0;
        if(query(5u,0x22u,mapping)) { cputs("raw mapping: ");text(); }
    }
    cputs(RF_ERROR "free unavailable\r\n");
}

/* UltimateDOS file control. Pumps remain resident. Embedded CBM image names
 * are typed on the wire, including temporary, backup and rollback names. */
#include "readyfs_udos_files.h"
#include "readyfs_uci.h"
#include "readyfs_result.h"
#include "readyfs_udos_status.h"
#include "readyfs_console.h"
#include <cbm_filetype.h>
#include <conio.h>
#include <string.h>

#ifndef RF_UDOS_PHASE
#error RF_UDOS_PHASE must select prepare(1), lookup(2), execute(3), or name policy(4)
#endif
static ReadyFsUdosFilesCall *call;
#if RF_UDOS_PHASE != 4
static ReadyFsUciTransfer transfer;
#if RF_UDOS_PHASE == 1
static unsigned char command[70], data[256], status[80];
static char part[64];
#elif RF_UDOS_PHASE == 2
static unsigned char command[44], data[80], status[80];
#elif RF_UDOS_PHASE == 3
static unsigned char command[259], data[256], status[80];
#endif
#if RF_UDOS_PHASE <= 2
static char wanted[64];
static unsigned char matches, enumeration_error, enumeration_complete;
#endif
static char found[64];
static unsigned char attributes, image_context;
#endif
#define decoded (call->name)
#define wire_name (call->wire)
#define selector (call->selector)
static unsigned char fold(unsigned char c) {
    c &= 0x7fu;
    if (c>=97u && c<=122u) c-=32u;
    return c;
}
#if RF_UDOS_PHASE <= 2
static unsigned char equal(const char *a,const char *b) {
    while (*a && fold((unsigned char)*a)==fold((unsigned char)*b)) { ++a; ++b; }
    return (unsigned char)(!*a && !*b);
}
#endif
static unsigned char failure(unsigned char result,const char *text) {
    *call->status=result;
    cputs(RF_ERROR);cputs(text);cputs("\r\n");
    return RF_LOOKUP_ERROR;
}
#if RF_UDOS_PHASE != 4
static unsigned char status_ok(void) {
    return (unsigned char)(transfer.stat_len>=2u && status[0]==48u && status[1]==48u);
}
#if RF_UDOS_PHASE <= 2
static const char empty_status[]=RF_UDOS_EMPTY_BYTES;
#if RF_UDOS_PHASE == 2
static const char missing_status[]=RF_UDOS_MISSING_BYTES;
#endif
static unsigned char status_is(const char *s) {
    unsigned int n;
    n=strlen(s);
    return (unsigned char)((transfer.stat_len==n ||
        (transfer.stat_len==n+1u && status[n]==0u)) && !memcmp(status,s,n));
}
#endif
static unsigned char send(unsigned int length) {
    memset(&transfer,0,sizeof(transfer));
    transfer.data=data;transfer.data_cap=sizeof(data);
    transfer.stat=status;transfer.stat_cap=sizeof(status);
    return readyfs_uci_command(command,length,&transfer);
}
static unsigned char query(unsigned char opcode,const char *arg) {
    unsigned int n;
    command[0]=call->target;command[1]=opcode;n=2u;
    if(arg) {
        if(strlen(arg)>sizeof(command)-3u)return 0u;
        strcpy((char *)command+n,arg);n+=strlen(arg)+1u;
    }
    /* FILE_STAT in this firmware does not append its own NUL. Include it;
     * all other textual DOS operations also accept the terminator. */
    return send(n);
}
static unsigned char dos_failure(void) {
    unsigned int i;
    *call->status=RF_RESULT_IO;cputs(RF_ERROR "dos: ");
    for(i=0u;i<transfer.stat_len;++i)cputc(status[i]>=32u && status[i]<127u?status[i]:'.');
    cputs("\r\n");return RF_LOOKUP_ERROR;
}
#endif
#if RF_UDOS_PHASE != 1
static unsigned char ext_type(const unsigned char *ext) {
    if(fold(ext[0])==80u && fold(ext[1])==82u && fold(ext[2])==71u)return CBM_T_PRG;
    if(fold(ext[0])==83u && fold(ext[1])==69u && fold(ext[2])==81u)return CBM_T_SEQ;
    if(fold(ext[0])==85u && fold(ext[1])==83u && fold(ext[2])==82u)return CBM_T_USR;
    if(fold(ext[0])==82u && fold(ext[1])==69u && fold(ext[2])==76u)return CBM_T_REL;
    return 0u;
}
#endif
#if RF_UDOS_PHASE == 1
static unsigned char image_extension(const char *name) {
    const char *p;
    p=strrchr(name,'.');if(!p || strlen(p)!=4u)return 0u;
    ++p;
    return (unsigned char)(fold(p[0])==68u &&
        ((p[1]=='6' && p[2]=='4') || (p[1]=='7' && p[2]=='1') ||
         (p[1]=='8' && p[2]=='1') || (fold(p[1])==78u && fold(p[2])==80u)));
}
#endif
#if RF_UDOS_PHASE <= 2
static void directory_block(const unsigned char *bytes,unsigned int length,
                             const unsigned char *reply,unsigned int reply_length) {
    char entry[64];
    if(reply_length) {
        if(reply_length<2u || reply[0]!=48u || reply[1]!=48u)enumeration_error=1u;
        else enumeration_complete=1u;
    }
    if(transfer.flags & RF_UCI_TRUNC_DATA)enumeration_error=1u;
    if(length<2u || length>sizeof(entry))return;
    memcpy(entry,bytes+1u,length-1u);entry[length-1u]=0;
    if(equal(wanted,entry)) {
        if(matches<2u)++matches;
        attributes=bytes[0];strcpy(found,entry);
    }
}
#endif
#if RF_UDOS_PHASE <= 2
static unsigned char enumerate(const char *name) {
    strcpy(wanted,name);matches=enumeration_error=enumeration_complete=0u;found[0]=0;
    if(!query(0x13u,0))return dos_failure();
    if(status_is(empty_status))return RF_LOOKUP_MISSING;
    if(!status_ok())return dos_failure();
    command[0]=call->target;command[1]=0x14u;
    memset(&transfer,0,sizeof(transfer));
    transfer.data=data;transfer.data_cap=sizeof(data);
    transfer.stat=status;transfer.stat_cap=sizeof(status);
    transfer.on_block=directory_block;
    if(!readyfs_uci_command(command,2u,&transfer) || enumeration_error || !enumeration_complete)return dos_failure();
    if(matches>1u)return failure(RF_RESULT_CONFLICT,"ambiguous image name; use type");
    return matches?RF_LOOKUP_FOUND:RF_LOOKUP_MISSING;
}
#endif
#if RF_UDOS_PHASE == 1
static unsigned char change(const char *path,const char *end) {
    unsigned char n,entry_is_image,result;
    image_context=0u;
    if(!query(0x11u,"/") || !status_ok())return dos_failure();
    while(path<end) {
        while(path<end && *path=='/')++path;
        n=0u;
        while(path<end && *path!='/') {
            if(n==sizeof(part)-1u)return failure(RF_RESULT_USAGE,"path component too long");
            if(*path=='*' || *path=='?')return failure(RF_RESULT_USAGE,"exact parent required");
            part[n++]=*path++;
        }
        part[n]=0;if(!n)continue;
        entry_is_image=0u;
        if(image_extension(part)) {
            if(!query(0x08u,part))return dos_failure();
            if(status_ok() && transfer.data_len>=12u)attributes=data[11u];
            else {
                result=enumerate(part);
                if(result!=RF_LOOKUP_FOUND)return failure(RF_RESULT_IO,"image context unknown");
            }
            entry_is_image=(unsigned char)((attributes&0x10u)==0u);
        }
        if(!query(0x11u,part) || !status_ok())return dos_failure();
        if(entry_is_image)image_context=RF_UDOS_CBM;
    }
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 1
static const char *parent(void) {
    const char *leaf;
    leaf=strrchr(call->stream->native_name,'/');
    if(!leaf || !leaf[1]) {
        failure(RF_RESULT_USAGE,"file leaf required");return 0;
    }
    if(change(call->stream->native_name,leaf)!=RF_LOOKUP_FOUND)return 0;
    call->stream->native_mode=image_context;
    return leaf+1u;
}
#endif
#if RF_UDOS_PHASE == 4
static unsigned char hex_value(unsigned char c) {
    c=fold(c);
    if(c>=48u && c<=57u)return c-48u;
    if(c>=65u && c<=70u)return c-55u;
    return 255u;
}
/* Strict subset of firmware {hex} spelling: no silent truncation, incomplete
 * escapes or wildcard injection. Limit the decoded CBM name, not wire bytes. */
#endif
#if RF_UDOS_PHASE == 4
static unsigned char decode(const char *name) {
    const char *end;
    unsigned char n,escaped,hi,lo,value;
    end=name+strlen(name);selector=0u;
    if(end-name>=4 && end[-4]=='.') {
        selector=ext_type((const unsigned char *)end-3u);
        if(selector)end-=4;
    }
    n=escaped=0u;
    while(name<end) {
        if((unsigned char)*name==0x7Bu || (unsigned char)*name==0xB3u) {
            if(escaped)return failure(RF_RESULT_USAGE,"bad image escape");
            escaped=1u;++name;continue;
        }
        if((unsigned char)*name==0x7Du || (unsigned char)*name==0xABu) {
            if(!escaped)return failure(RF_RESULT_USAGE,"bad image escape");
            escaped=0u;++name;continue;
        }
        if(escaped) {
            if(end-name<2)return failure(RF_RESULT_USAGE,"bad image escape");
            hi=hex_value((unsigned char)name[0]);lo=hex_value((unsigned char)name[1]);
            if(hi==255u || lo==255u)return failure(RF_RESULT_USAGE,"bad image escape");
            value=(unsigned char)((hi<<4u)|lo);name+=2;
        }else value=fold((unsigned char)*name++);
        if(n==16u || value<32u || value==160u || value=='*' || value=='?')
            return failure(RF_RESULT_USAGE,"image name invalid or too long");
        decoded[n++]=(char)value;
    }
    if(!n || escaped)return failure(RF_RESULT_USAGE,"bad image name");
    decoded[n]=0;return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 4
static const char *type_suffix(unsigned char type) {
    if(type==CBM_T_PRG)return ".prg";
    if(type==CBM_T_SEQ)return ".seq";
    if(type==CBM_T_USR)return ".usr";
    if(type==CBM_T_REL)return ".rel";
    return "";
}
#endif
#if RF_UDOS_PHASE == 4
static void wire(const char *raw,unsigned char type) {
    unsigned char n,v;
    n=0u;wire_name[n++]=0x7Bu;
    while(*raw) {
        v=(unsigned char)*raw++;
        wire_name[n++]="0123456789abcdef"[v>>4u];
        wire_name[n++]="0123456789abcdef"[v&15u];
    }
    wire_name[n++]=0x7Du;wire_name[n]=0;
    strcat(wire_name,type_suffix(type));
}
#endif
#if RF_UDOS_PHASE == 2 || RF_UDOS_PHASE == 3
static unsigned char bit(void) { return (unsigned char)(1u<<(call->target-1u)); }
#endif
#if RF_UDOS_PHASE == 2 || RF_UDOS_PHASE == 3
static unsigned char close_handle(void) {
    if(!query(0x03u,0) || !status_ok())return dos_failure();
    *call->open_targets &= (unsigned char)~bit();
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 2 || RF_UDOS_PHASE == 3
static unsigned char open_handle(const char *name,unsigned char flags) {
    unsigned int n;
    command[0]=call->target;command[1]=0x02u;command[2]=flags;
    n=strlen(name);if(n>sizeof(command)-4u)return failure(RF_RESULT_USAGE,"file name too long");
    memcpy(command+3u,name,n+1u);
    *call->open_targets |= bit();
    if(!send(n+4u)) {
        /* This target was free before the request. A CLOSE may recover an
         * uncertain OPEN; an unconfirmed recovery leaves its live bit set. */
        (void)close_handle();return failure(RF_RESULT_IO,"open completion unknown");
    }
    if(!status_ok()) {
        *call->open_targets &= (unsigned char)~bit();
        return RF_LOOKUP_MISSING; /* caller classifies the actual DOS reply */
    }
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 2 || RF_UDOS_PHASE == 3
static unsigned char metadata(void) {
    unsigned int n;
    if(!status_ok() || transfer.data_len<13u)
        return failure(RF_RESULT_IO,"file metadata unavailable");
    n=transfer.data_len-12u;
    if(image_context && n>16u)return failure(RF_RESULT_IO,"invalid image metadata");
    if(image_context) { memcpy(found,data+12u,n);found[n]=0; }
    attributes=data[11u];
    call->stream->type=(attributes&0x10u)?CBM_T_DIR:ext_type(data+8u);
    if(image_context && !call->stream->type)return failure(RF_RESULT_IO,"unknown image file type");
    if(!image_context && !call->stream->type)call->stream->type=CBM_T_SEQ;
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 2
static unsigned char image_find(const char *leaf) {
    unsigned char rc,saved_type,hidden,n,i;
    static const unsigned char types[4]={CBM_T_SEQ,CBM_T_PRG,CBM_T_USR,CBM_T_REL};
    static const char suffixes[]=".seq.prg.usr.rel";
    (void)leaf;
    hidden=0u;
    if(!selector) {
        rc=enumerate(decoded);
        if(rc==RF_LOOKUP_ERROR)return rc;
        /* Firmware hides dot-prefixed leaves from READ_DIR. A miss must
         * continue through authoritative OPEN, never become false absence. */
        hidden=(unsigned char)(rc==RF_LOOKUP_MISSING);
    }
    if(!query(0x08u,wire_name))return dos_failure();
    if(status_ok()) {
        if(metadata()!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    }else {
        /* FILE_STAT collapses errors to NOT FOUND. Only a read-only OPEN's
         * exact missing reply is authoritative; never probe a live target. */
        rc=open_handle(wire_name,0x01u);
        if(rc==RF_LOOKUP_ERROR)return rc;
        if(rc==RF_LOOKUP_MISSING) {
            if(status_is(missing_status)) {
                call->stream->type=0u;return RF_LOOKUP_MISSING;
            }
            return dos_failure();
        }
        rc=(unsigned char)(query(0x07u,0) && metadata()==RF_LOOKUP_FOUND);
        saved_type=call->stream->type;
        if(close_handle()!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
        call->stream->type=saved_type;
        if(!rc)return failure(RF_RESULT_IO,"file metadata unavailable");
    }
    if(!equal(found,decoded) || (selector && selector!=call->stream->type))
        return failure(RF_RESULT_IO,"image metadata mismatch");
    if(hidden) {
        /* Bare hidden names may have several file types, all omitted from
         * enumeration. Prove the other selectors absent before accepting. */
        saved_type=call->stream->type;n=strlen(wire_name);
        for(i=0u;i<4u;++i) {
            if(types[i]==saved_type)continue;
            memcpy(wire_name+n,suffixes+(unsigned int)i*4u,4u);wire_name[n+4u]=0;
            rc=open_handle(wire_name,0x01u);
            if(rc==RF_LOOKUP_ERROR)return rc;
            if(rc==RF_LOOKUP_FOUND) {
                if(close_handle()!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
                return failure(RF_RESULT_CONFLICT,"ambiguous image name; use type");
            }
            if(!status_is(missing_status))return dos_failure();
        }
        wire_name[n]=0;
    }
    strcpy(call->name,found);
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 4
static unsigned char validate_type(const char *leaf,unsigned char type) {
    if(type!=CBM_T_PRG && type!=CBM_T_SEQ && type!=CBM_T_USR)
        return failure(RF_RESULT_UNSUPPORTED,"image stream type unsupported");
    if(decode(leaf)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    if(selector && selector!=type)return failure(RF_RESULT_CONFLICT,"image type conflicts with source");
    return RF_LOOKUP_FOUND;
}
#endif
#if RF_UDOS_PHASE == 3
static unsigned char rename_file(const char *leaf) {
    const char *destination;
    const char *source_parent;
    unsigned int n,parent_length;
    source_parent=strrchr(call->stream->native_name,'/');
    destination=strrchr(call->other->native_name,'/');
    if(!source_parent || !destination || !destination[1])return failure(RF_RESULT_USAGE,"rename leaf required");
    parent_length=(unsigned int)(source_parent-call->stream->native_name);
    if((unsigned int)(destination-call->other->native_name)!=parent_length ||
        memcmp(call->stream->native_name,call->other->native_name,parent_length))
        return failure(RF_RESULT_UNSUPPORTED,"rename requires same parent");
    ++destination;
    if(image_context) {
        destination=wire_name;
    }
    if(strlen(leaf)+strlen(destination)+4u>sizeof(command))return failure(RF_RESULT_USAGE,"rename name too long");
    command[0]=call->target;command[1]=0x0au;
    strcpy((char *)command+2u,leaf);n=strlen(leaf)+3u;
    strcpy((char *)command+n,destination);n+=strlen(destination)+1u;
    if(!send(n) || !status_ok())return dos_failure();
    return RF_LOOKUP_FOUND;
}
#endif

static unsigned char enter_call(ReadyFsUdosFilesCall *c) {
    unsigned char mask;
    if(!c || !c->status || !c->open_targets || c->target<1u || c->target>2u)return RF_LOOKUP_ERROR;
    call=c;*call->status=RF_RESULT_OK;
    /* Keep this byte-sized: cc65 2.18 can optimize away the rejection when
     * the dynamic 16-bit shift is used directly as the && condition. */
    mask=(unsigned char)(1u<<(c->target-1u));
    if(c->operation!=RF_UDOS_CLOSE && (unsigned char)(*c->open_targets & mask))
        return failure(RF_RESULT_IO,"dos target still open");
#if RF_UDOS_PHASE != 4
    image_context=c->stream?c->stream->native_mode:0u;
#endif
    return RF_LOOKUP_FOUND;
}
#if RF_UDOS_PHASE == 1
unsigned int readyfs_udos_prepare_abi(void) { return RF_UDOS_PREPARE_ABI; }
unsigned char readyfs_udos_prepare(ReadyFsUdosFilesCall *c) {
    if(enter_call(c)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    if(c->operation==RF_UDOS_CHANGE) {
        if(!c->path)return failure(RF_RESULT_USAGE,"path required");
        return change(c->path,c->path+strlen(c->path));
    }
    if(!c->stream)return failure(RF_RESULT_USAGE,"stream required");
    return parent()?RF_LOOKUP_FOUND:RF_LOOKUP_ERROR;
}
#elif RF_UDOS_PHASE == 2
unsigned int readyfs_udos_lookup_abi(void) { return RF_UDOS_LOOKUP_ABI; }
unsigned char readyfs_udos_lookup(ReadyFsUdosFilesCall *c) {
    const char *leaf;
    if(enter_call(c)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    if(!image_context)return RF_UDOS_HOST_LOOKUP;
    if(!c->stream || !c->access)return failure(RF_RESULT_USAGE,"lookup storage required");
    leaf=strrchr(c->stream->native_name,'/');
    if(!leaf)return failure(RF_RESULT_USAGE,"file leaf required");
    return image_find(leaf+1u);
}
#elif RF_UDOS_PHASE == 3
unsigned int readyfs_udos_execute_abi(void) { return RF_UDOS_EXECUTE_ABI; }
unsigned char readyfs_udos_execute(ReadyFsUdosFilesCall *c) {
    const char *leaf;
    unsigned char rc;
    if(enter_call(c)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    if(c->operation==RF_UDOS_CLOSE) {
        rc=close_handle();
        if(rc==RF_LOOKUP_FOUND && c->stream)c->stream->open=0u;
        return rc;
    }
    if(!c->stream)return failure(RF_RESULT_USAGE,"stream required");
    leaf=strrchr(c->stream->native_name,'/');
    if(!leaf)return failure(RF_RESULT_USAGE,"file leaf required");
    ++leaf;
    if(c->operation==RF_UDOS_RENAME) {
        if(!c->other || !c->source_access)return failure(RF_RESULT_USAGE,"rename storage required");
        return rename_file(c->source_access);
    }
    if(c->operation==RF_UDOS_READ) {
        if(image_context) {
            if(!c->access || c->stream->type==CBM_T_REL || c->stream->type==CBM_T_DIR)
                return failure(RF_RESULT_UNSUPPORTED,"image stream type unsupported");
            leaf=c->access;
        }
        rc=open_handle(leaf,0x01u);
        if(rc!=RF_LOOKUP_FOUND)return rc==RF_LOOKUP_MISSING?dos_failure():rc;
        if(!query(0x07u,0) || metadata()!=RF_LOOKUP_FOUND) {
            if(close_handle()!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
            return failure(RF_RESULT_IO,"source metadata unavailable");
        }
        if(c->stream->type==CBM_T_REL) {
            if(close_handle()!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
            return failure(RF_RESULT_UNSUPPORTED,"rel stream unsupported");
        }
    }else if(c->operation==RF_UDOS_NEW) {
        if(image_context) {
            leaf=wire_name;
        }
        rc=open_handle(leaf,0x06u);
        if(rc!=RF_LOOKUP_FOUND)return rc==RF_LOOKUP_MISSING?dos_failure():rc;
        c->stream->type=c->type;
    }else return failure(RF_RESULT_USAGE,"unknown dos operation");
    c->stream->open=1u;c->stream->target=c->target;
    return RF_LOOKUP_FOUND;
}
#else
/* Typed suffixes and {hex} spellings can name the same directory entry.
 * Reject self-copy/move/rename before a stage or backup is created. */
static unsigned char distinct(void) {
    const char *a,*b,*ae,*be;
    unsigned char destination_type;
    a=call->stream->native_name;b=call->other->native_name;
    ae=strrchr(a,'/');be=strrchr(b,'/');
    if(!ae || !be)return failure(RF_RESULT_USAGE,"file leaf required");
    if(ae-a!=be-b)return RF_LOOKUP_FOUND;
    while(a<ae)if(fold(*a++)!=fold(*b++))return RF_LOOKUP_FOUND;
    if(decode(ae+1u)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    strcpy(call->access,decoded);
    if(decode(be+1u)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    destination_type=selector?selector:call->other->type;
    if(!destination_type)destination_type=call->stream->type;
    a=call->access;b=decoded;
    while(*a && fold(*a)==fold(*b)){++a;++b;}
    if(!*a && !*b && destination_type==call->stream->type)
        return failure(RF_RESULT_CONFLICT,"same image entry");
    return RF_LOOKUP_FOUND;
}
unsigned int readyfs_udos_name_abi(void) { return RF_UDOS_NAME_ABI; }
unsigned char readyfs_udos_name(ReadyFsUdosFilesCall *c) {
    const char *leaf;
    unsigned char type;
    if(enter_call(c)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    if(!c->name || !c->wire || !c->access || !c->stream)return failure(RF_RESULT_USAGE,"name storage required");
    if(c->policy==RF_UDOS_NAME_DISTINCT)return distinct();
    if(c->policy==RF_UDOS_NAME_OUTPUT) {
        if(c->stream->type==CBM_T_DIR)strcpy(c->access,c->name);
        else { wire(c->name,c->stream->type);strcpy(c->access,c->wire); }
        return RF_LOOKUP_FOUND;
    }
    leaf=strrchr(c->policy==RF_UDOS_NAME_RENAME?c->other->native_name:c->stream->native_name,'/');
    if(!leaf)return failure(RF_RESULT_USAGE,"file leaf required");
    ++leaf;
    if(c->policy==RF_UDOS_NAME_INPUT) {
        if(decode(leaf)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
        wire(decoded,selector);return RF_LOOKUP_FOUND;
    }
    type=c->policy==RF_UDOS_NAME_RENAME?c->stream->type:c->type;
    if(validate_type(leaf,type)!=RF_LOOKUP_FOUND)return RF_LOOKUP_ERROR;
    wire(decoded,type);return RF_LOOKUP_FOUND;
}
#endif


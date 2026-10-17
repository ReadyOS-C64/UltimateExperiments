#include "bulk_reu.h"
/* Ultimate3.14 primary sources pinned830665cd; see HANDOFF. ReadyOS uz_dos.c
 * transfer/count contracts informed this independently written strict parser;
 * no ReadyOS implementation code copied. Existing FILES/UCI ASM copied exact. */
extern void uci_init(void),uci_poll(void),uci_accept(void),uci_abort(void);
extern br_u8 uci_start(void),files_start(void);
extern void files_init(void),files_poll(void);
extern br_u8 uci_state,uci_error,uci_recovery_failed,uci_flags,uci_last_status;
extern br_u8 uci_command[],uci_data[],uci_status[];
extern br_u16 uci_command_len,uci_data_len,uci_status_len,uci_now;
extern br_u16 uci_data_capacity,uci_status_capacity;
extern br_u8 files_state,files_error,files_transport_error,files_handle;
extern br_u8 files_target,files_op,files_mode,files_path_len,files_count_known,files_uncertain;
extern br_u16 files_now,files_actual,files_count;
extern br_u8 files_offset[];
struct br_config_t br_config={0,1,0x400000UL,{0}};
struct br_request_t br_request;
struct br_result_t br_result;
br_u16 br_now;
static struct br_request_t q;
static struct br_config_t owned;
static br_u8 bulk,seen,cancelled,external,access_mode;
static br_u8 root_len,path_len;
static br_u32 value;
static br_u8 i,digit;
static br_u8 quiet(void) { return uci_state==0||uci_state==9||(uci_state==10&&!uci_recovery_failed&&uci_error>=3); }
static br_u8 same_config(void) {
 br_u8 j; if(br_config.owner!=owned.owner || br_config.target!=owned.target || br_config.capacity!=owned.capacity)return 0;
 for(j=0;j<128;++j)if(br_config.root[j]!=owned.root[j])return 0;
 return 1;
}
/* Canonical printable ASCII components, including internal spaces. FatFs
 * strips trailing spaces/dots, so reject those aliases before ownership checks.
 * Embedded '..' is harmless; only complete dot/dotdot components are refused. */
static br_u8 printable(br_u8 c) {return c>=32&&c<=126&&c!='\\'&&c!=':'&&c!='\"'&&c!='*'&&c!='<'&&c!='>'&&c!='?'&&c!='|';}
static br_u8 validate_root(void) {
 br_u8 j,begin=1,c,last=0;
 if(br_config.owner!=0xa5 || (br_config.target!=1&&br_config.target!=2))return 0;
 if(br_config.capacity<0x400000UL||br_config.capacity>0x1000000UL||(br_config.capacity&0xffffUL))return 0;
 if(br_config.root[0]!='/')return 0;
 for(j=1;j<128;++j) {
  c=br_config.root[j];
  if(!c){root_len=j;return j>begin&&last!=' '&&last!='.';}
  if(c=='/'){if(j==begin||last==' '||last=='.')return 0;begin=j+1;last=0;}
  else {if(!printable(c))return 0;last=c;}
 }
 return 0;
}
static br_u8 validate_path(void) {
 br_u8 j,begin,c,last=0;
 if(root_len>125)return 0;
 for(j=0;j<root_len;++j)if(q.path[j]!=br_config.root[j])return 0;
 if(q.path[j++]!='/')return 0;
 begin=j;
 for(;j<128;++j) {
  c=q.path[j];
  if(!c){path_len=j+1;return j>begin&&last!=' '&&last!='.';}
  if(!printable(c)||c=='/')return 0;last=c;
 }
 return 0;
}
static void first(br_u8 error) { if(!br_result.error)br_result.error=error; }
static void terminal(void) {
 br_result.handle=files_handle;
 if(!files_handle)access_mode=0;
 else if(!br_result.error&&q.op==BR_OPEN)access_mode=q.mode;
 br_result.state=br_result.error?BR_FAILED:BR_DONE;
}
static void clock_copy(void) { uci_now=br_now;files_now=br_now; }
static void put32(br_u8 *at,br_u32 n) { br_u8 j;for(j=0;j<4;++j){at[j]=(br_u8)n;n>>=8;} }
#pragma code-name(push,"HIGH_CODE")
static br_u8 cpu_read_admit(void){if(!(access_mode&1)||!q.length||q.length>512UL)return 0;files_count=(br_u16)q.length;return 1;}
static void cpu_read_reply(void){br_result.actual=files_actual;br_result.known=files_count_known;if(!br_result.known||br_result.actual!=q.length)first(BR_COUNT);}
#pragma code-name(pop)
void br_init(void) {
 uci_init();files_init();br_result.state=BR_IDLE;br_result.error=0;br_result.transport=0;br_result.handle=0;
 br_result.known=0;br_result.uncertain=0;br_result.rejected=0;br_result.accepted=0;br_result.actual=0;br_result.size=0;br_result.op=0;
 bulk=seen=cancelled=external=access_mode=0;br_now=0;
}
br_u8 br_start(void) {
 br_u8 j;
 br_result.rejected=BR_INPUT;
 if(external||br_result.state==BR_BUSY || !quiet() || !validate_root())return 0;
 if(files_handle&&!same_config())return 0;
 q=br_request;
 if(q.op!=BR_OPEN&&q.op!=BR_CLOSE&&q.op!=BR_READ&&q.op!=BR_SEEK&&q.op!=BR_INFO&&q.op!=BR_LOAD&&q.op!=BR_SAVE)return 0;
 if(q.op==BR_OPEN) {
  if(files_handle||!validate_path())return 0;
  if(q.mode!=1&&q.mode!=2&&q.mode!=3&&q.mode!=6&&q.mode!=7)return 0;
 } else {
  if(!files_handle || (files_handle==2&&q.op!=BR_CLOSE))return 0;
 }
 if(q.op==BR_READ&&!cpu_read_admit())return 0;
 bulk=q.op==BR_LOAD||q.op==BR_SAVE;
 if(bulk) {
  if((q.op==BR_LOAD&&!(access_mode&1))||(q.op==BR_SAVE&&!(access_mode&2)))return 0;
  if(!q.length || q.length>0x400000UL || q.address>=br_config.capacity || q.length>br_config.capacity-q.address)return 0;
  if(!quiet())return 0;
 }
 br_result.rejected=0;br_result.error=0;br_result.transport=0;br_result.known=0;br_result.actual=0;br_result.size=0;br_result.op=q.op;seen=cancelled=0;
 clock_copy();
 if(bulk) {
  uci_command[0]=br_config.target;uci_command[1]=q.op;put32(uci_command+2,q.address);put32(uci_command+6,q.length);
  uci_command_len=10;uci_data_capacity=64;uci_status_capacity=80;
  if(uci_start()) {first(BR_TRANSPORT);br_result.transport=uci_error;terminal();return 0;}
  if(q.op==BR_SAVE)br_result.uncertain=1;
 } else {
  files_target=br_config.target;files_op=q.op;files_mode=q.mode;
  if(q.op==BR_OPEN) {files_path_len=path_len;for(j=0;j<path_len;++j)uci_command[3+j]=q.path[j];}
  if(q.op==BR_SEEK)put32(files_offset,q.offset);
  if(files_start()) {first(BR_TRANSPORT);br_result.transport=files_transport_error;terminal();return 0;}
 }
 owned=br_config;br_result.state=BR_BUSY;++br_result.accepted;return 1;
}
static br_u8 hex6(br_u8 at) {
 br_u8 j,started=0;value=0;
 for(j=0;j<6;++j) {
  digit=uci_data[at+j];
  if(digit==' '&&!started)continue;
  started=1;
  if(digit>='0'&&digit<='9')digit-='0';
  else if(digit>='a'&&digit<='f')digit=digit-'a'+10;
  else return 0;
  value=(value<<4)|digit;
 }
 return started;
}
static void reply(void) {
 const char *suffix; br_u8 n,addr;
 if(seen++||uci_flags||(uci_last_status&0x10)) {first(BR_PROTOCOL);return;}
 if(uci_status_len!=5) {first(BR_STATUS);return;}
 for(i=0;i<5;++i)if(uci_status[i]!="00,OK"[i]){first(BR_STATUS);return;}
 n=q.op==BR_LOAD?35:36;addr=n-7;suffix=q.op==BR_LOAD?" BYTES LOADED TO REU $":" BYTES SAVED FROM REU $";
 if(uci_data_len!=n||uci_data[0]!='$'){first(BR_PROTOCOL);return;}
 for(i=7;i<=addr;++i)if(uci_data[i]!=suffix[i-7]){first(BR_PROTOCOL);return;}
 if(!hex6(1)){first(BR_PROTOCOL);return;}
 br_result.actual=value;br_result.known=1;
 if(!hex6(addr+1)||value!=q.address){first(BR_PROTOCOL);return;}
 if(br_result.actual!=q.length){first(BR_COUNT);return;}
}
void br_poll(void) {
 if(br_result.state!=BR_BUSY)return;
 clock_copy();
 if(!bulk) {
  files_poll();
  if(files_error){br_result.transport=files_transport_error;first(files_error==2?BR_TRANSPORT:(files_error==3?BR_STATUS:BR_PROTOCOL));}
  if(uci_state==8&&uci_error){br_result.transport=uci_error;first(BR_TRANSPORT);}
  if(files_state==1)return;
  if(files_state!=2){br_result.transport=files_transport_error;first(cancelled?BR_CANCEL:(files_error==2?BR_TRANSPORT:(files_error==3?BR_STATUS:BR_PROTOCOL)));}
  else if(q.op==BR_INFO){br_result.size=(br_u32)uci_data[0]|((br_u32)uci_data[1]<<8)|((br_u32)uci_data[2]<<16)|((br_u32)uci_data[3]<<24);br_result.known=files_count_known;}
  if(q.op==BR_READ&&files_state==2)cpu_read_reply();
  terminal();return;
 }
 uci_poll();
 if(uci_state==8&&uci_error){br_result.transport=uci_error;first(BR_TRANSPORT);}
 if(uci_state==5){reply();if(br_result.error==BR_PROTOCOL)uci_abort();else uci_accept();return;}
 if(uci_state==10){br_result.transport=uci_error;files_handle=2;first(cancelled?BR_CANCEL:BR_TRANSPORT);terminal();return;}
 if(uci_state==9){if(!seen)first(BR_PROTOCOL);terminal();}
}
void br_cancel(void) {
 if(br_result.state!=BR_BUSY||cancelled)return;
 cancelled=1;first(BR_CANCEL);clock_copy();uci_abort();
}

/* Serialized raw UI lease: no open FILE handle can cross this boundary.
 * External owner may use this same UCI engine for directory-only commands;
 * it must not OPEN/CLOSE files behind FILES, mutate configs, or reinitialize. */
br_u8 br_ui_acquire(void) {
 if(external||br_result.state==BR_BUSY||files_handle)return 0;
 if(!quiet())return 0;
 external=1;return 1;
}
br_u8 br_ui_release(void) {
 if(!external)return 0;
 if(!quiet())return 0;
 external=0;return 1;
}
const br_u8 br_abi_sizes[]={sizeof(struct br_config_t),sizeof(struct br_request_t),sizeof(struct br_result_t)};

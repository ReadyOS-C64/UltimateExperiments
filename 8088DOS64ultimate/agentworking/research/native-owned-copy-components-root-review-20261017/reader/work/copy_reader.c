#include <string.h>
#include "copy_reader.h"
#include "bulk_uci.h"
#include "platform.h"
#include "startup_close.h"
#include "crc32.h"
extern br_u8 files_handle,files_target,files_op,files_state,files_error,files_transport_error,files_count_known;
extern br_u16 files_now,files_count,files_actual;
extern br_u8 files_start(void);
extern void files_poll(void);
struct cr_control_t cr_control={0,{0},{0}};
static struct cr_control_t owned;
static struct br_config_t engine;
char cr_p_previous_cwd[128];
br_u8 cr_p_cwd_changed;
br_u8 cr_p_used,cr_p_phase,cr_p_first,cr_p_cleanup,cr_p_raw,cr_p_aborted,cr_p_initialclosed,cr_p_copy_attempts,cr_p_copy_uncertain,cr_p_eof,cr_p_frame_live;
br_u16 cr_p_last,cr_p_fill,cr_p_frame,cr_p_j;
br_u32 cr_p_offset,cr_p_elapsed,cr_p_checksum,cr_p_mismatch;
#define TOTAL 0x1400000UL
#define FRAME ((br_u8*)0x4000)
#define P_START 1
#define P_CD 2
#define P_COPY 3
#define P_OPEN 4
#define P_INFO 5
#define P_READ 6
#define P_WAIT 7
#define P_EOF 8
#define P_CLOSE 9
#define P_FAIL 10
#define P_CLEAN 11
#define P_STOP 12
#define P_GET 13
#define P_RESTORE 14
#define P_STAT 15
#define ACTIVE (cr_p_phase!=P_FAIL&&cr_p_phase!=P_CLEAN&&cr_p_phase!=P_STOP)
static const char source_root[]="/usb1/DOS64_TEST/ac-media-20261016-081300";
static const char leaf[]="DOSHD.IMG";
static br_u8 quiet(void){return uci_state==0||uci_state==9||(uci_state==10&&!uci_recovery_failed&&uci_error>=3);}
static void result(void){
 memcpy((void*)cr_result.magic,"CCR1",4);cr_result.error=cr_p_first;cr_result.cleanup=cr_p_cleanup;cr_result.closed=cr_p_initialclosed&&!files_handle&&!cr_p_raw&&!cr_p_copy_uncertain&&!cr_p_cwd_changed&&quiet();cr_result.phase=cr_p_phase;cr_result.eof=cr_p_eof;cr_result.copy_attempts=cr_p_copy_attempts;cr_result.copy_uncertain=cr_p_copy_uncertain;cr_result.read=cr_p_offset;cr_result.ticks=cr_p_elapsed;cr_result.mismatch=cr_p_mismatch;cr_result.file_error=files_error;cr_result.transport=files_transport_error;cr_result.raw=cr_p_raw;cr_result.handle=files_handle;cr_result.cwd_changed=cr_p_cwd_changed;cr_result.state=cr_p_phase==P_STOP?(cr_p_first?0xff:(cr_p_eof?4:0)):1;
}
static void fail(br_u8 why){if(!cr_p_first)cr_p_first=why;cr_p_phase=P_FAIL;}
static br_u8 valid(void){br_u8 i,c,nonzero=0;if(owned.owner!=0xa5||!memcmp(owned.root,source_root,sizeof(source_root))||memcmp(owned.root,"/usb1/DOS64_TEST/",17))return 0;for(i=0;i<16;++i)nonzero|=owned.nonce[i];if(!nonzero)return 0;for(i=17;i<82&&owned.root[i];++i){c=owned.root[i];if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'))return 0;}if(i<=17||i>=82)return 0;for(++i;i<128;++i)if(owned.root[i])return 0;return 1;}
static void raw_start(br_u8 op){br_u16 n;const char *directory;
 if(!br_ui_acquire()){fail(3);return;}cr_p_raw=1;uci_command[0]=1;uci_command[1]=op;
 if(op==0x12){uci_command_len=2;}
 else if(op==0x11){directory=source_root;if(cr_p_phase==P_RESTORE)directory=cr_p_previous_cwd;n=strlen(directory);memcpy(uci_command+2,directory,n);uci_command_len=n+2;}
 else if(op==0x08){memcpy(uci_command+2,leaf,sizeof(leaf));uci_command_len=2+sizeof(leaf);}
 else{n=sizeof(leaf);memcpy(uci_command+2,leaf,n);cr_p_j=strlen(owned.root);memcpy(uci_command+2+n,owned.root,cr_p_j);uci_command_len=2+n+cr_p_j;cr_p_copy_attempts=1;cr_p_copy_uncertain=1;}
 uci_data_capacity=128;uci_status_capacity=80;if(uci_start())fail(3);
}
static void file_issue(br_u8 op,br_u8 next){br_request.op=op;if(op==BR_OPEN){memset(br_request.path,0,128);strcpy(br_request.path,owned.root);strcat(br_request.path,"/");strcat(br_request.path,leaf);br_request.mode=1;}if(!br_start()){fail(3);return;}cr_p_phase=next;}
static void read_issue(br_u8 final){
 for(cr_p_j=0;cr_p_j<512;++cr_p_j)uci_data[cr_p_j]^=0xff;
 files_target=2;files_op=4;files_count=final?1:512;files_now=ps_ticks;cr_p_raw=2;
 if(files_start()){cr_p_raw=0;fail(3);return;}cr_p_phase=final?P_EOF:P_READ;
}
static void header(br_u8 state,br_u16 count){
 cr_header.state=1;memcpy((void*)cr_header.magic,"CFR1",4);cr_header.version=1;cr_header.frame=cr_p_frame;memcpy((void*)cr_header.nonce,owned.nonce,16);cr_header.offset=count?cr_p_offset-count:cr_p_offset;cr_header.count=count;cr_header.reserved=0;cr_header.crc=cr_p_checksum;cr_header.read=cr_p_offset;cr_header.total=TOTAL;
 memcpy((void*)0x0400,(const void*)&cr_header,44);*(br_u8*)0x0405=state;
 c32_address=0x0400;c32_length=44;if(!c32_reset()||!c32_update()||!c32_finish()){fail(6);return;}cr_header.header_crc=c32_crc;cr_header.state=state; /* READY LAST */
}
void cr_init(void){
 if(cr_p_used){result();return;}cr_p_used=1;owned=cr_control;cr_p_phase=P_STOP;cr_p_first=cr_p_cleanup=cr_p_raw=cr_p_aborted=cr_p_initialclosed=cr_p_copy_attempts=cr_p_copy_uncertain=cr_p_eof=cr_p_frame_live=cr_p_cwd_changed=0;memset(cr_p_previous_cwd,0,128);cr_p_fill=cr_p_frame=0;cr_p_offset=cr_p_elapsed=cr_p_checksum=0;cr_p_mismatch=0xffffffffUL;
 memset((void*)&cr_result,0,sizeof(cr_result));
 if(!valid()){result();return;}if(cr_ack.frame||cr_ack.cancel||cr_ack.go){cr_p_first=1;result();return;}
 memset((void*)&cr_header,0,sizeof(cr_header));br_config.owner=0xa5;br_config.target=2;br_config.capacity=0x400000UL;memcpy(br_config.root,owned.root,128);br_init();engine=br_config;uci_timeout=30000;uci_recovery_timeout=500;
 if(!c32_init()||!ps_clock_poll()){cr_p_first=7;result();return;}cr_p_last=ps_ticks;
 if(!sc_begin(0xa5)){cr_p_first=2;result();return;}cr_p_phase=P_START;result();
}
/* Capture only the matching active FILES operation's published error. Startup
 * CLOSE84 is owned by SC and must not leak into this module's first cause. */
static void observe_file_first(void){
 if(!cr_p_first&&cr_p_raw==2&&files_state==1&&files_error)cr_p_first=3;
}
void cr_step(void){br_u8 state; br_u16 delta;
 if(cr_p_phase==P_STOP){result();return;}
 observe_file_first();
 if(!ps_clock_poll()){if(!cr_p_first)cr_p_first=7;cr_p_cleanup=7;cr_p_phase=P_STOP;result();return;}
 delta=ps_ticks-cr_p_last;cr_p_last=ps_ticks;cr_p_elapsed+=delta;if((delta>=32768U||cr_p_elapsed>600000UL)&&ACTIVE)fail(7);
 br_now=ps_ticks;sc_now=ps_ticks;uci_now=ps_ticks;files_now=ps_ticks;
 if(memcmp(&owned,&cr_control,sizeof(owned))||memcmp(&engine,&br_config,sizeof(engine))){br_config=engine;if(cr_p_phase==P_START){if(!cr_p_first)cr_p_first=1;}else if(ACTIVE)fail(1);}
 if(cr_ack.go&&cr_p_phase!=P_WAIT&&ACTIVE){if(cr_p_phase==P_START){if(!cr_p_first)cr_p_first=9;sc_cancel();}else fail(9);}
 if(cr_p_phase==P_START){if(cr_ack.cancel){if(!cr_p_first)cr_p_first=8;sc_cancel();}state=sc_poll();if(state==SC_BUSY){result();return;}if(!sc_ready())fail(2);else if(cr_p_first){cr_p_initialclosed=1;cr_p_phase=P_STOP;}else{cr_p_initialclosed=1;cr_p_phase=P_GET;raw_start(0x12);}result();return;}
 if(cr_ack.cancel&&ACTIVE)fail(8);
 if(cr_p_phase==P_FAIL){
  if(cr_p_raw==1){if(!cr_p_aborted&&uci_state!=9&&uci_state!=10){uci_abort();cr_p_aborted=1;}uci_poll();if(uci_state!=9&&uci_state!=10){result();return;}if(!br_ui_release()){cr_p_cleanup=3;cr_p_phase=P_STOP;result();return;}cr_p_raw=0;}
  if(cr_p_raw==2){if(!cr_p_aborted&&files_state==1){uci_abort();cr_p_aborted=1;}files_poll();if(files_state==1){result();return;}cr_p_raw=0;}
  if(br_result.state==BR_BUSY){br_cancel();br_poll();if(br_result.state==BR_BUSY){result();return;}}
  if(!files_handle){cr_p_phase=P_STOP;result();return;}br_request.op=BR_CLOSE;if(!br_start()){cr_p_cleanup=3;cr_p_phase=P_STOP;}else cr_p_phase=P_CLEAN;result();return;
 }
 if(cr_p_phase==P_CLEAN){br_poll();if(br_result.state!=BR_BUSY){if(br_result.state!=BR_DONE||files_handle)cr_p_cleanup=3;cr_p_phase=P_STOP;}result();return;}
 if(cr_p_phase==P_GET||cr_p_phase==P_CD||cr_p_phase==P_COPY||cr_p_phase==P_RESTORE||cr_p_phase==P_STAT){
  uci_poll();if(uci_state==BR_UCI_BLOCK){
   if(uci_flags||uci_status_len!=5||memcmp(uci_status,"00,OK",5)||(uci_last_status&0x10))fail(3);
   else if(cr_p_phase==P_GET){if(!uci_data_len||uci_data_len>=128||uci_data[0]!='/')fail(3);else{for(cr_p_j=0;cr_p_j<uci_data_len;++cr_p_j)if(uci_data[cr_p_j]<32||uci_data[cr_p_j]>126)break;if(cr_p_j!=uci_data_len)fail(3);else{memcpy(cr_p_previous_cwd,uci_data,uci_data_len);uci_accept();}}}
   else if(cr_p_phase==P_STAT){if(uci_data_len!=21||(uci_data[11]&0x18)||memcmp(uci_data+12,leaf,9))fail(4);else{memcpy(&cr_p_checksum,uci_data,4);if(cr_p_checksum!=TOTAL)fail(4);else uci_accept();}}
   else if(uci_data_len)fail(3);else uci_accept();
  }
  else if(uci_state==BR_UCI_FAILED)fail(3);
  else if(uci_state==BR_UCI_DONE){if(!br_ui_release())fail(3);else{cr_p_raw=0;if(cr_p_phase==P_GET){cr_p_phase=P_CD;cr_p_cwd_changed=1;raw_start(0x11);}else if(cr_p_phase==P_CD){cr_p_phase=P_STAT;raw_start(0x08);}else if(cr_p_phase==P_STAT){cr_p_phase=P_COPY;raw_start(0x0b);}else if(cr_p_phase==P_COPY){cr_p_copy_uncertain=0;cr_p_phase=P_RESTORE;raw_start(0x11);}else{cr_p_cwd_changed=0;file_issue(BR_OPEN,P_OPEN);}}}result();return;
 }
 if(cr_p_phase==P_WAIT){
  if(cr_ack.go){if(cr_ack.go!=0xa5||cr_ack.frame!=cr_p_frame){fail(9);result();return;}cr_ack.go=0;cr_ack.frame=0;cr_p_frame_live=0;cr_header.state=1;cr_p_fill=0;if(cr_p_offset==TOTAL)read_issue(1);else read_issue(0);}result();return;
 }
 if(cr_p_phase==P_READ||cr_p_phase==P_EOF){
  files_poll();observe_file_first();if(files_state==1){result();return;}cr_p_raw=0;
  if(files_state!=2||files_error||!files_count_known){fail(3);result();return;}
  if(cr_p_phase==P_EOF){if(files_actual)fail(4);else{cr_p_eof=1;file_issue(BR_CLOSE,P_CLOSE);}result();return;}
  if(files_actual!=512){fail(4);result();return;}memcpy(FRAME+cr_p_fill,uci_data,512);cr_p_offset+=512;cr_p_fill+=512;
  if(cr_p_fill==32768U){c32_address=0x4000;c32_length=32768U;if(!c32_reset()||!c32_update()||!c32_finish())fail(6);else{cr_p_checksum=c32_crc;++cr_p_frame;header(2,32768U);if(cr_p_phase!=P_FAIL){cr_p_frame_live=1;cr_p_phase=P_WAIT;}}}else read_issue(0);result();return;
 }
 br_poll();if(br_result.state==BR_BUSY){result();return;}if(br_result.state!=BR_DONE){if(cr_p_phase==P_CLOSE){if(!cr_p_first)cr_p_first=3;cr_p_cleanup=3;cr_p_phase=P_STOP;}else fail(3);result();return;}
 switch(cr_p_phase){case P_OPEN:file_issue(BR_INFO,P_INFO);break;case P_INFO:if(!br_result.known||br_result.size!=TOTAL)fail(4);else read_issue(0);break;case P_CLOSE:if(files_handle||!cr_p_eof||cr_p_offset!=TOTAL||cr_p_frame!=640)fail(3);else{header(4,0);if(cr_p_phase!=P_FAIL)cr_p_phase=P_STOP;}break;default:fail(3);break;}result();
}
void cr_entry(void){ps_init();cr_init();while(cr_p_phase!=P_STOP)cr_step();}
const br_u8 cr_abi_sizes[]={sizeof(struct cr_control_t),sizeof(struct cr_header_t),sizeof(struct cr_ack_t),sizeof(struct cr_result_t)};

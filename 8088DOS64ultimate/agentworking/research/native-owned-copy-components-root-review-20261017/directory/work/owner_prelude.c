#include <string.h>
#include "owner_prelude.h"
#include "bulk_uci.h"
#include "platform.h"
#include "startup_close.h"
extern br_u8 files_handle,files_target,files_op,files_state,files_error,files_transport_error,files_count_known;
extern br_u16 files_now,files_count,files_actual;
extern br_u8 files_start(void);
extern void files_poll(void);
struct dp_control_t dp_control={0,{0},{0}};
static struct dp_control_t owned;
static struct br_config_t engine;
br_u8 dp_p_used,dp_p_phase,dp_p_first,dp_p_cleanup,dp_p_raw,dp_p_aborted,dp_p_initialclosed,dp_p_mkdir_attempts,dp_p_created,dp_p_uncertain,dp_p_verified,dp_p_cwd_changed;
br_u8 dp_p_marker[52],dp_p_readback[52];char dp_p_cwd[128];
br_u16 dp_p_last,dp_p_j; br_u32 dp_p_elapsed;
#define SC 1
#define GET 2
#define CD 3
#define MKDIR 4
#define RESTORE 5
#define OPENW 6
#define WRITE 7
#define CLOSEW 8
#define OPENR 9
#define INFO 10
#define READ 11
#define EOFPROBE 12
#define CLOSER 13
#define FAIL 14
#define CLEAN 15
#define STOP 16
#define ACTIVE (dp_p_phase!=FAIL&&dp_p_phase!=CLEAN&&dp_p_phase!=STOP)
static const char prefix[]="/usb1/DOS64_TEST/copy20m-";
static const char parent[]="/usb1/DOS64_TEST";
static const br_u8 expected_sha[32]={0x78,0xb9,0x41,0x71,0x10,0x81,0xe5,0xee,0x8b,0x1e,0x28,0x55,0xb1,0xca,0x4d,0x48,0x76,0x16,0x0f,0x97,0xa5,0xdf,0xdb,0x1e,0x47,0x5f,0xa6,0x5a,0x69,0x9d,0x10,0x2c};
static br_u8 closing(void){return dp_p_phase==CLOSEW||dp_p_phase==CLOSER;}
static br_u8 quiet(void){return uci_state==0||uci_state==9||(uci_state==10&&!uci_recovery_failed&&uci_error>=3);}
static void result(void){
 dp_result.state=1;memcpy((void*)dp_result.magic,"DPR1",4);dp_result.error=dp_p_first;dp_result.cleanup=dp_p_cleanup;dp_result.closed=dp_p_initialclosed&&!files_handle&&!dp_p_raw&&!dp_p_uncertain&&!dp_p_cwd_changed&&quiet();dp_result.phase=dp_p_phase;dp_result.mkdir_attempts=dp_p_mkdir_attempts;dp_result.created=dp_p_created;dp_result.owner_verified=dp_p_verified;dp_result.cwd_changed=dp_p_cwd_changed;dp_result.raw=dp_p_raw;dp_result.handle=files_handle;dp_result.reserved=0;memcpy((void*)dp_result.nonce,owned.nonce,16);memcpy((void*)dp_result.readback,dp_p_readback,52);if(dp_p_phase==STOP)dp_result.state=dp_p_first?0xff:(dp_p_verified?4:0);
}
static void fail(br_u8 e){if(!dp_p_first)dp_p_first=e;if(!closing())dp_p_phase=FAIL;}
static void observed(void){if(dp_p_first||dp_p_phase==SC)return;if((dp_p_raw==2||((dp_p_phase>=OPENW&&dp_p_phase<=CLOSER)&&br_result.state==BR_BUSY))&&files_state==1&&files_error)dp_p_first=3;else if(dp_p_raw==1&&uci_error)dp_p_first=3;}
static br_u8 valid(void){br_u8 i,c,n=0;if(owned.owner!=0xa5||memcmp(owned.root,prefix,sizeof(prefix)-1))return 0;for(i=0;i<16;++i)n|=owned.nonce[i];if(!n)return 0;for(i=sizeof(prefix)-1;i<82&&owned.root[i];++i){c=owned.root[i];if(!((c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='-'||c=='_'))return 0;}if(i<=sizeof(prefix)-1||i>=82)return 0;for(++i;i<128;++i)if(owned.root[i])return 0;return 1;}
static void raw_start(br_u8 op){const char *s; br_u16 n;if(!br_ui_acquire()){fail(3);return;}dp_p_raw=1;uci_command[0]=1;uci_command[1]=op;uci_command_len=2;
 if(op==0x11){s=parent;if(dp_p_phase==RESTORE)s=dp_p_cwd;n=strlen(s);memcpy(uci_command+2,s,n);uci_command_len=n+2;}
 if(op==0x16){s=owned.root+sizeof(parent);n=strlen(s);memcpy(uci_command+2,s,n);uci_command_len=n+2;dp_p_mkdir_attempts=1;dp_p_uncertain=1;}
 uci_data_capacity=128;uci_status_capacity=80;if(uci_start())fail(3);
}
static void file_issue(br_u8 op,br_u8 next){br_request.op=op;if(op==BR_OPEN){br_request.mode=next==OPENW?6:1;memset(br_request.path,0,128);strcpy(br_request.path,owned.root);strcat(br_request.path,"/OWNER");}dp_p_phase=next;if(!br_start())fail(3);}
static void data_issue(br_u8 op,br_u8 next){if(op==5)memcpy(uci_command+4,dp_p_marker,52);else for(dp_p_j=0;dp_p_j<52;++dp_p_j)uci_data[dp_p_j]^=0xff;files_target=2;files_op=op;files_count=next==EOFPROBE?1:52;files_now=ps_ticks;dp_p_raw=2;dp_p_phase=next;if(files_start()){dp_p_raw=0;fail(3);}}
void dp_init(void){if(dp_p_used){result();return;}dp_p_used=1;owned=dp_control;dp_p_phase=STOP;memset((void*)&dp_result,0,sizeof(dp_result));if(!valid())return;if(dp_cancel){dp_p_first=1;result();return;}memcpy(dp_p_marker,"DCR1",4);memcpy(dp_p_marker+4,owned.nonce,16);memcpy(dp_p_marker+20,expected_sha,32);br_config.owner=0xa5;br_config.target=2;br_config.capacity=0x400000UL;memcpy(br_config.root,owned.root,128);br_init();engine=br_config;uci_timeout=30000;uci_recovery_timeout=500;if(!ps_clock_poll()){dp_p_first=7;result();return;}dp_p_last=ps_ticks;if(!sc_begin(0xa5)){dp_p_first=2;result();return;}dp_p_phase=SC;result();}
void dp_step(void){br_u8 state;br_u16 delta;if(dp_p_phase==STOP){result();return;}observed();if(!ps_clock_poll()){if(!dp_p_first)dp_p_first=7;dp_p_cleanup=7;dp_p_phase=STOP;result();return;}delta=ps_ticks-dp_p_last;dp_p_last=ps_ticks;dp_p_elapsed+=delta;if((delta>=32768U||dp_p_elapsed>60000UL)&&ACTIVE)fail(7);br_now=sc_now=uci_now=files_now=ps_ticks;
 if(memcmp(&owned,&dp_control,sizeof(owned))||memcmp(&engine,&br_config,sizeof(engine))){br_config=engine;if(dp_p_phase==SC){if(!dp_p_first)dp_p_first=1;sc_cancel();}else if(ACTIVE)fail(1);}
 if(dp_p_phase==SC){if(dp_cancel){if(!dp_p_first)dp_p_first=8;sc_cancel();}state=sc_poll();if(state==SC_BUSY){result();return;}if(!sc_ready())fail(2);else{dp_p_initialclosed=1;if(dp_p_first)dp_p_phase=STOP;else{dp_p_phase=GET;raw_start(0x12);}}result();return;}
 if(dp_cancel&&ACTIVE)fail(8);
 if(dp_p_phase==FAIL){if(dp_p_raw==1){if(!dp_p_aborted&&uci_state!=9&&uci_state!=10){uci_abort();dp_p_aborted=1;}uci_poll();if(uci_state!=9&&uci_state!=10){result();return;}if(!br_ui_release()){dp_p_cleanup=3;dp_p_phase=STOP;result();return;}dp_p_raw=0;}if(dp_p_raw==2){if(!dp_p_aborted&&files_state==1){uci_abort();dp_p_aborted=1;}files_poll();if(files_state==1){result();return;}dp_p_raw=0;}if(br_result.state==BR_BUSY){br_cancel();br_poll();if(br_result.state==BR_BUSY){result();return;}}if(!files_handle){dp_p_phase=STOP;result();return;}br_request.op=BR_CLOSE;if(!br_start()){dp_p_cleanup=3;dp_p_phase=STOP;}else dp_p_phase=CLEAN;result();return;}
 if(dp_p_phase==CLEAN){br_poll();if(br_result.state!=BR_BUSY){if(br_result.state!=BR_DONE||files_handle)dp_p_cleanup=3;dp_p_phase=STOP;}result();return;}
 if(dp_p_raw==1){uci_poll();observed();if(uci_state==BR_UCI_BLOCK){if(uci_flags||uci_status_len!=5||memcmp(uci_status,"00,OK",5)||(uci_last_status&0x10))fail(3);else if(dp_p_phase==GET){if(!uci_data_len||uci_data_len>=128||uci_data[0]!='/')fail(3);else{for(dp_p_j=0;dp_p_j<uci_data_len;++dp_p_j)if(uci_data[dp_p_j]<32||uci_data[dp_p_j]>126)break;if(dp_p_j!=uci_data_len)fail(3);else{memcpy(dp_p_cwd,uci_data,uci_data_len);uci_accept();}}}else if(uci_data_len)fail(3);else uci_accept();}else if(uci_state==BR_UCI_FAILED)fail(3);else if(uci_state==BR_UCI_DONE){if(!br_ui_release())fail(3);else{dp_p_raw=0;if(dp_p_phase==GET){dp_p_cwd_changed=1;dp_p_phase=CD;raw_start(0x11);}else if(dp_p_phase==CD){dp_p_phase=MKDIR;raw_start(0x16);}else if(dp_p_phase==MKDIR){dp_p_created=1;dp_p_uncertain=0;dp_p_phase=RESTORE;raw_start(0x11);}else{dp_p_cwd_changed=0;file_issue(BR_OPEN,OPENW);}}}result();return;}
 if(dp_p_raw==2){files_poll();observed();if(files_state==1){result();return;}dp_p_raw=0;if(files_state!=2||files_error){fail(3);result();return;}if(dp_p_phase==WRITE){file_issue(BR_CLOSE,CLOSEW);}else if(!files_count_known||files_actual!=(dp_p_phase==READ?52:0)){fail(4);}else if(dp_p_phase==READ){memcpy(dp_p_readback,uci_data,52);if(memcmp(dp_p_readback,dp_p_marker,52))fail(6);else data_issue(4,EOFPROBE);}else file_issue(BR_CLOSE,CLOSER);result();return;}
 br_poll();observed();if(br_result.state==BR_BUSY){result();return;}if(br_result.state!=BR_DONE){if(closing()){if(!dp_p_first)dp_p_first=3;dp_p_cleanup=3;dp_p_phase=STOP;}else fail(3);result();return;}if(dp_p_first){dp_p_phase=STOP;result();return;}
 switch(dp_p_phase){case OPENW:data_issue(5,WRITE);break;case CLOSEW:if(files_handle)fail(3);else file_issue(BR_OPEN,OPENR);break;case OPENR:file_issue(BR_INFO,INFO);break;case INFO:if(!br_result.known||br_result.size!=52)fail(4);else data_issue(4,READ);break;case CLOSER:if(files_handle||dp_p_uncertain||dp_p_cwd_changed)fail(3);else{dp_p_verified=1;dp_p_phase=STOP;}break;default:fail(3);break;}result();}
void dp_entry(void){ps_init();dp_init();while(dp_p_phase!=STOP)dp_step();}

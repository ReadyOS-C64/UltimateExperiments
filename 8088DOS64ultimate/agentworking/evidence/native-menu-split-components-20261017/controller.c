#include "controller.h"
#include "bulk_uci.h"
#include "install_config.h"
#include "release.h"
#include "crc32.h"
#if D64_START_OPTIONS
#include "ini_io.h"
#endif
#include <string.h>

struct lc_control_t lc_control={0xffu,0xdf1cu,{0xffu,0}};
struct lc_result_t lc_result;
br_u16 lc_now;
br_u16 lc_dma_c64,lc_dma_length;
br_u32 lc_dma_reu;
br_u8 lc_dma_direction;
extern br_u8 lc_dma(void);
extern br_u16 lc_uci_base;

/* Everything used for decisions is private; observation globals are output. */
static br_u8 state,error,cleanup,phase,io,cancelled,loaded_count;
static br_u8 failed_op,io_error,transport;
static struct br_result_t leaf_result;
static br_u8 launch_ticket;
static br_u8 buffer[256],header[32],cfg[576],release[64];
static char home[128],path[128];
static br_u16 base;
static br_u32 capacity,bytes,address,checked,crc,expect_crc,main_crc;
#if D64_START_OPTIONS
extern br_u8 so_overlay_spec[16];
static br_u8 overlay_installed;
#define P_OVERLAY 9u
#define P_OPTIONS 10u
#endif
#if D64_START_MODAL
extern br_u8 sm_modal_spec[16],sm_modal_header[64];
#define P_MODAL 11u
#define P_MODAL_COPY 12u
#define P_MODAL_FINAL 13u
#endif
#define P_CFG 1u
#define P_RELEASE 2u
#define P_MAIN 3u
#define P_A 4u
#define P_B 5u
#define P_PATCH 6u
#define P_PATCH_CRC 7u
#define P_PUBLISH 8u

static void restore_leaf(void) {br_result=leaf_result;}
static void capture_leaf(void) {
    leaf_result=br_result;
    /* A validated leaf failure precedes a later user cancel even while BUSY.
     * Keep draining/recovering first; cleanup starts only at terminal state. */
    if(state==1u && br_result.error && !error) {
        error=2u;failed_op=br_result.op;io_error=br_result.error;
        transport=br_result.transport;
    }
}
static br_u8 leaf_start(void) {br_u8 ok=br_start();capture_leaf();return ok;}
static br_u8 leaf_ui_acquire(void) {br_u8 ok=br_ui_acquire();capture_leaf();return ok;}
static br_u8 leaf_ui_release(void) {br_u8 ok=br_ui_release();capture_leaf();return ok;}

static br_u32 wide(const br_u8 *p) {
    return (br_u32)p[0]|((br_u32)p[1]<<8)|((br_u32)p[2]<<16)|((br_u32)p[3]<<24);
}
static void put32(br_u8 *p,br_u32 v) {
    br_u8 i;for(i=0;i<4u;++i){p[i]=(br_u8)v;v>>=8;}
}
static br_u32 crc_bytes(br_u32 v,const br_u8 *p,br_u16 n) {
    /* Only fixed private buffers are passed; checked CRC bounds reject errors. */
    c32_crc=v;c32_address=(br_u16)p;c32_length=n;
    if(!c32_update())return 0UL;
    return c32_crc;
}
static void publish(void) {
    lc_result.state=state;lc_result.error=error;lc_result.cleanup=cleanup;
    lc_result.phase=phase;lc_result.checked=checked;lc_result.main_crc=main_crc;
    lc_result.loaded=loaded_count;lc_result.failed_op=failed_op;
    lc_result.io_error=io_error;lc_result.transport=transport;
}
static br_u8 dma(void *p,br_u32 at,br_u16 n,br_u8 dir) {
    lc_dma_c64=(br_u16)p;lc_dma_reu=at;lc_dma_length=n;lc_dma_direction=dir;
    return lc_dma();
}
static br_u8 clear_ready(void) {
#if D64_START_OPTIONS
 br_u8 a,b;buffer[0]=0;a=dma(buffer,0x3ff005UL,1u,0u);b=dma(buffer,0x3ff505UL,1u,0u);
#if D64_START_MODAL
 {br_u8 c;c=dma(buffer,0x3da005UL,1u,0u);return a&&b&&c;}
#else
 return a&&b;
#endif
#else
 buffer[0]=0;return dma(buffer,0x3ff005UL,1u,0u);
#endif
}
static void fail(br_u8 reason) {
    if(!error){error=reason;if(reason==2u){failed_op=br_result.op;
        io_error=br_result.error;transport=br_result.transport;}}
    if(!clear_ready() && !cleanup)cleanup=7u;
    if(br_result.handle) {
        br_request.op=BR_CLOSE;
        if(leaf_start()){io=5u;publish();return;}
        if(!cleanup)cleanup=2u;
    }
    state=3u;publish();
}
static br_u8 job(br_u8 op) {
    br_request.op=op;
    if(leaf_start())return 1u;
    fail(2u);return 0u;
}
static br_u8 set_path(const char *p) {
    memcpy(d64_path_source,p,128);
    if(!d64_path_parent())return 0u;
    memcpy(br_config.root,d64_path_output,128);
    memcpy(br_request.path,p,128);
    return 1u;
}
static br_u8 named(const char *name) {
    memset(d64_path_relative,0,128);strcpy((char *)d64_path_relative,name);
    memcpy(d64_path_source,home,128);
    if(!d64_path_join())return 0u;
    memcpy(path,d64_path_output,128);return 1u;
}
static br_u8 file(const char *p,br_u32 size,br_u32 at) {
    if(!set_path(p)){fail(1u);return 0u;}
    bytes=size;address=at;checked=0;crc=0xffffffffUL;
    br_request.mode=1u;io=1u;
    return job(BR_OPEN);
}
void lc_init(void) {
    br_init();capture_leaf();c32_init();state=error=cleanup=phase=io=cancelled=0u;
    loaded_count=failed_op=io_error=transport=launch_ticket=0u;
#if D64_START_OPTIONS
    overlay_installed=0u;
#endif
    memset(&lc_result,0,sizeof(lc_result));publish();
}
br_u8 lc_validate_start(void) {
    restore_leaf();
    if(state!=0u || lc_control.owner!=0xa5u || br_result.handle ||
       (lc_control.uci_base!=0xdf1cu && lc_control.uci_base!=0xde1cu &&
        lc_control.uci_base!=0xdffcu))return 0u;
    memcpy(home,lc_control.home,128);
    if(!named("DOS64.CFG"))return 0u;
    base=lc_control.uci_base;lc_uci_base=base;return 1u;
}
br_u8 lc_begin(void) {
    if(!lc_validate_start())return 0u;
    br_now=lc_now;
    state=1u;error=cleanup=cancelled=0u;main_crc=0;phase=P_CFG;
    loaded_count=failed_op=io_error=transport=0u;capacity=0x400000UL;
    br_config.owner=0xa5u;br_config.target=1u;br_config.capacity=capacity;
    if(!clear_ready()){fail(7u);return 1u;}
    #if D64_START_OPTIONS
    if(memcmp(so_overlay_spec,"D64I\1\20",6u) ||
       so_overlay_spec[12]!=0u || so_overlay_spec[13]!=0x60u ||
       so_overlay_spec[14] || so_overlay_spec[15]){fail(5u);return 1u;}
    bytes=(br_u16)so_overlay_spec[6]|((br_u16)so_overlay_spec[7]<<8);
    if(!bytes || bytes>0x2000UL || !named("START.INO")){fail(5u);return 1u;}
    phase=P_OVERLAY;expect_crc=wide(so_overlay_spec+8u);
    file(path,bytes,0x3f8000UL);
#else
    file(path,576UL,0x3ff020UL);
#endif
    publish();return 1u;
}
static br_u8 fetch(br_u8 *out,br_u32 at,br_u16 n) {
    br_u16 part;
    while(n){part=n>256u?256u:n;if(!dma(out,at,part,1u))return 0u;
        out+=part;at+=part;n-=part;}
    return 1u;
}
static br_u8 stash(const br_u8 *in,br_u32 at,br_u16 n) {
    br_u16 part;
    while(n){part=n>256u?256u:n;memcpy(buffer,in,part);
        if(!dma(buffer,at,part,0u))return 0u;in+=part;at+=part;n-=part;}
    return 1u;
}
#if D64_START_MODAL
#pragma code-name(push,"PRELAUNCH")
static void modal_main(void) {
 phase=P_MAIN;expect_crc=wide(release+12u);
 if(!named("DOS64.PRG")){fail(1u);return;}
 file(path,wide(release+8u),0x3e0000UL);
}
static void modal_begin(void) {
 if(memcmp(sm_modal_spec,"D64M\1\20",6u)||wide(sm_modal_spec+12u)!=0x3da000UL||
    memcmp(sm_modal_header,"D64M\1\1\100\0",8u)) {fail(5u);return;}
 bytes=(br_u16)sm_modal_spec[6]|((br_u16)sm_modal_spec[7]<<8);
 if(bytes<64UL||bytes>0x8000UL||!named("DOS64.MNU")){fail(5u);return;}
 phase=P_MODAL;expect_crc=wide(sm_modal_spec+8u);
 file(path,bytes,0x3e0000UL);
}
/* The extra8KiB retires SETUP's source-cache lifetime; it never extends
 * backward into the complete third floppy at380000..3D9FFF. */
static br_u32 modal_target(br_u32 offset) {
 return offset<0x6000UL?0x3da000UL+offset:0x3f0000UL+(offset-0x6000UL);
}
static void modal_copy(void) {
 br_u16 part;
 if(checked<bytes){
  part=bytes-checked>256UL?256u:(br_u16)(bytes-checked);
  if(!dma(buffer,0x3e0000UL+checked,part,1u)){fail(7u);return;}
  if(!checked){
   if(memcmp(buffer,sm_modal_header,64u)){fail(5u);return;}
   buffer[5]=0u; /* invalid until every target byte passes the second CRC */
  }
  if(!dma(buffer,modal_target(checked),part,0u)){fail(7u);return;}
  checked+=part;return;
 }
 phase=P_MODAL_FINAL;checked=0;crc=0xffffffffUL;address=0x3da000UL;io=6u;
}
static void modal_ready(void) {
 buffer[0]=1u;
 if(!dma(buffer,0x3da005UL,1u,0u)){fail(7u);return;}
 buffer[0]=0xa5u;
 if(!dma(buffer,0x3da005UL,1u,1u)||buffer[0]!=1u){fail(7u);return;}
 modal_main();
}
#pragma code-name(pop)
#endif
static void loaded(void) {
    ++loaded_count;io=0u;
    if(phase==P_CFG) {
#if D64_START_OPTIONS
        if(!overlay_installed){fail(5u);return;}
#endif
        if(!fetch(cfg,0x3ff020UL,576u)){fail(7u);return;}
        memcpy(d64_cfg_input,cfg,576u);
        if(!d64_config_validate() || memcmp(cfg+8u,home,128u)){fail(6u);return;}
        capacity=wide(cfg+538u);br_config.capacity=capacity;
        phase=P_RELEASE;if(!named("DOS64.REL")){fail(1u);return;}
        file(path,64UL,0x3ff400UL);
    } else if(phase==P_RELEASE) {
        if(!fetch(release,0x3ff400UL,64u)){fail(7u);return;}
        memcpy(d64_release_input,release,64u);
        if(!d64_release_validate()){fail(5u);return;}
#if D64_START_MODAL
        modal_begin();
#else
        phase=P_MAIN;expect_crc=wide(release+12u);
        if(!named("DOS64.PRG")){fail(1u);return;}
        file(path,wide(release+8u),0x3e0000UL);
#endif
    } else {io=6u;}
}
static br_u8 patch_main(void) {
    br_u32 at;
    /* Bounds/nonoverlap validated descriptor before fetching template spans. */
    at=0x3e0000UL+wide(release+28u);
    if(!fetch(buffer,at,142u) || memcmp(buffer,"D64N\0",5u))return 0u;
    memset(buffer,0,142u);memcpy(buffer,"D64N",4u);buffer[4]=0xa5u;
    buffer[5]=(br_u8)(capacity>>20);buffer[6]=1u;
    buffer[7]=(br_u8)(strlen((char *)cfg+136u)+1u);
    buffer[8]=(br_u8)base;buffer[9]=(br_u8)(base>>8);
    memcpy(buffer+10u,cfg+528u,4u);memcpy(buffer+14u,cfg+136u,128u);
    if(!dma(buffer,at,142u,0u))return 0u;
    at=0x3e0000UL+wide(release+32u);
    if(!fetch(buffer,at,140u) || memcmp(buffer,"D64H\0",5u))return 0u;
    memset(buffer,0,140u);memcpy(buffer,"D64H",4u);
    if(cfg[525u]&4u) {
        buffer[4]=0xa5u;buffer[5]=1u;buffer[6]=cfg[522u];
        buffer[7]=(cfg[524u]>>2)&1u;buffer[8]=0u;buffer[9]=2u;
        buffer[10]=32u;buffer[11]=(br_u8)(strlen((char *)cfg+392u)+1u);
        memcpy(buffer+12u,cfg+392u,128u);
    }
    if(!dma(buffer,at,140u,0u))return 0u;
    at=0x3e0000UL+wide(release+36u);
    if(!fetch(buffer,at,1u) || buffer[0])return 0u;
    buffer[0]=0xa5u;if(!dma(buffer,at,1u,0u))return 0u;
    #if D64_START_OPTIONS
    at=0x3e0000UL+wide(release+56u);
    if(!fetch(buffer,at,1u)||buffer[0])return 0u;
    buffer[0]=0xa5u;if(!dma(buffer,at,1u,0u))return 0u;
#endif
    if(!fetch(buffer,0x3e0000UL,2u) || buffer[0]!=1u || buffer[1]!=8u)return 0u;
    if(!fetch(buffer,0x3e0000UL+(0x5882UL-0x0801UL+2UL),1u) || buffer[0]!=0x40u)return 0u;
    return 1u;
}
static void crc_poll(void) {
    br_u16 part;
    if(checked<bytes) {
        part=bytes-checked>256UL?256u:(br_u16)(bytes-checked);
#if D64_START_MODAL
        if(phase==P_MODAL_FINAL){
         if(!dma(buffer,modal_target(checked),part,1u)){fail(7u);return;}
        }else
#endif
        if(!dma(buffer,address+checked,part,1u)){fail(7u);return;}
#if D64_START_MODAL
        if(phase==P_MODAL_FINAL&&!checked){
         buffer[5]=1u;
         if(memcmp(buffer,sm_modal_header,64u)){fail(5u);return;}
        }
#endif
        crc=crc_bytes(crc,buffer,part);if(c32_error){fail(7u);return;}checked+=part;return;
    }
    crc^=0xffffffffUL;
    if(phase==P_PATCH_CRC){main_crc=crc;
#if D64_START_OPTIONS
        phase=P_OPTIONS;
#else
        phase=P_PUBLISH;
#endif
        io=0u;return;}
    if(crc!=expect_crc){fail(4u);return;}
    io=0u;
#if D64_START_MODAL
    if(phase==P_MODAL){phase=P_MODAL_COPY;checked=0;return;}
    if(phase==P_MODAL_FINAL){modal_ready();return;}
#endif
    #if D64_START_OPTIONS
    if(phase==P_OVERLAY){io=7u;checked=0;crc=0xffffffffUL;return;}
#endif
    if(phase==P_MAIN){phase=P_A;expect_crc=wide(cfg+528u);file((char *)cfg+136u,0x5a000UL,0x100000UL);}
    else if(phase==P_A && (cfg[525u]&2u)){phase=P_B;expect_crc=wide(cfg+532u);file((char *)cfg+264u,0x5a000UL,0x180000UL);}
    else phase=P_PATCH;
}
#if D64_START_OPTIONS
/* cfg is not populated until this source-bound overlay installation finishes.
 * Two independent initialized FETCHes prevent suppressed/partial reads from
 * comparing a buffer to itself. Final RAM CRC binds the executed bytes. */
static void overlay_poll(void) {
    br_u16 part;
    if(checked<bytes) {
        part=bytes-checked>256UL?256u:(br_u16)(bytes-checked);
        memset(buffer,0xa5u,part);memset(cfg,0x5au,part);
        if(!dma(buffer,0x3f8000UL+checked,part,1u) ||
           !dma(cfg,0x3f8000UL+checked,part,1u) || memcmp(buffer,cfg,part)){
            fail(7u);return;
        }
        memcpy((br_u8 *)(0x6000u+(br_u16)checked),buffer,part);
        if(memcmp((br_u8 *)(0x6000u+(br_u16)checked),buffer,part)){
            fail(7u);return;
        }
        crc=crc_bytes(crc,(br_u8 *)(0x6000u+(br_u16)checked),part);
        if(c32_error){fail(7u);return;}checked+=part;return;
    }
    if((crc^0xffffffffUL)!=expect_crc){fail(4u);return;}
    overlay_installed=1u;phase=P_CFG;io=0u;
}
#endif
#if D64_START_OPTIONS
#pragma code-name(push,"PRELAUNCH")
static void ini_first(void) {
    br_u8 e=ii_error();
    if(!error&&e){error=e==1u?2u:e==2u?6u:e==3u?8u:10u;
        if(e==1u){failed_op=ii_failed_op();io_error=ii_leaf_error();transport=ii_transport();}}
}
static void ini_poll(void) {
    ii_now=lc_now;ii_poll();ini_first();
    if(ii_state()==3u){leaf_result=br_result;cleanup=ii_cleanup()?2u:0u;
        if(!clear_ready()&&!cleanup)cleanup=7u;state=3u;return;}
    if(ii_state()==2u){leaf_result=br_result;io=0u;phase=P_PUBLISH;}
}
static br_u8 options_publish(void) {
    br_u8 n,columns=ii_commit();
    if(!columns){ini_first();return 0u;}
    memset(header,0,32u);memcpy(header,"D64O",4u);header[4]=1u;header[5]=0xa5u;header[6]=32u;
    memcpy(header+8u,cfg+572u,4u);put32(header+12u,main_crc);header[16]=columns;
    put32(header+28u,crc_bytes(0xffffffffUL,header,28u)^0xffffffffUL);if(c32_error)return 0u;
    header[5]=0u;if(!stash(header,0x3ff500UL,32u))return 0u;
    for(n=0;n<32u;++n)buffer[n]=~header[n];
    if(!fetch(buffer,0x3ff500UL,32u)||memcmp(buffer,header,32u))return 0u;
    buffer[0]=0xa5u;if(!dma(buffer,0x3ff505UL,1u,0u))return 0u;
    header[5]=0xa5u;for(n=0;n<32u;++n)buffer[n]=~header[n];
    return fetch(buffer,0x3ff500UL,32u)&&!memcmp(buffer,header,32u);
}
#pragma code-name(pop)
#endif
static void anchor(void) {
    memset(header,0,32u);memcpy(header,"D64R",4u);header[4]=1u;header[5]=0xa5u;header[6]=32u;
    memcpy(header+8u,cfg+572u,4u);put32(header+12u,main_crc);
    memcpy(header+16u,cfg+528u,8u);header[24]=(br_u8)base;header[25]=(br_u8)(base>>8);
    header[26]=1u;header[27]=2u;put32(header+28u,crc_bytes(0xffffffffUL,header,28u)^0xffffffffUL);
    if(c32_error){fail(7u);return;}
    /* Final exact CFG and header are published only with all handles closed. */
    if(br_result.handle || !leaf_ui_acquire()){fail(2u);return;}
    if(!leaf_ui_release()){fail(2u);return;}
    if(!stash(cfg,0x3ff020UL,576u)){fail(7u);return;}
    header[5]=0u;if(!stash(header,0x3ff000UL,32u)){fail(7u);return;}
    #if D64_START_OPTIONS
    if(!options_publish()){fail(error?error:7u);return;}
#endif
    buffer[0]=0xa5u;if(!dma(buffer,0x3ff005UL,1u,0u)){fail(7u);return;}
    state=2u;
}
void lc_poll(void) {
    restore_leaf();
    if(state!=1u)return;
    br_now=lc_now;
#if D64_START_OPTIONS
    if(io==8u){ini_poll();publish();return;}
    if(phase==P_OPTIONS&&!io){
        if(!overlay_installed||!named("DOS64.INI")||!set_path(path)){fail(1u);return;}
        ii_now=lc_now;if(!ii_begin(path)){ini_first();fail(error?error:2u);return;}
        io=8u;publish();return;
    }
#endif
    if(io>=1u && io<=5u) {
        br_poll();capture_leaf();
        if(br_result.state==BR_BUSY){publish();return;}
        if(io==5u){if(br_result.state!=BR_DONE || br_result.handle)cleanup=2u;state=3u;publish();return;}
        if(br_result.state!=BR_DONE){fail(cancelled?8u:2u);return;}
        if(cancelled){fail(8u);return;}
        if(io==1u){io=2u;job(BR_INFO);}
        else if(io==2u){if(br_result.size!=bytes){fail(3u);return;}io=3u;br_request.address=address;br_request.length=bytes;job(BR_LOAD);}
        else if(io==3u){io=4u;job(BR_CLOSE);}
        else loaded();
    } else if(cancelled)fail(8u);
    else if(io==6u)crc_poll();
#if D64_START_OPTIONS
    else if(io==7u)overlay_poll();
    else if(phase==P_CFG && overlay_installed) {
        if(!named("DOS64.CFG")){fail(1u);return;}
        file(path,576UL,0x3ff020UL);
    }
#endif
#if D64_START_MODAL
    else if(phase==P_MODAL_COPY)modal_copy();
#endif
    else if(phase==P_PATCH) {
        if(!patch_main()){fail(5u);return;}
        phase=P_PATCH_CRC;address=0x3e0000UL;bytes=wide(release+8u);checked=0;crc=0xffffffffUL;io=6u;
    } else if(phase==P_PUBLISH)anchor();
    publish();
}
void lc_cancel(void) {
    restore_leaf();
    if(state==2u || state==4u || state==5u) {
        launch_ticket=2u;fail(8u);return;
    }
    if(state!=1u || cancelled)return;
#if D64_START_OPTIONS
    if(io==8u){ii_now=lc_now;ii_cancel();ini_first();cancelled=1u;publish();return;}
#endif
    cancelled=1u;if(!error)error=8u;
    br_now=lc_now;
    if(io>=1u && io<=4u && br_result.state==BR_BUSY){br_cancel();capture_leaf();}
    publish();
}

/* READY/PREPARED/CONSUMED are private and one-shot; result is observation. */
static br_u8 handoff_reject(void) {
    if(!error)error=9u;
    launch_ticket=2u;
    if(state==1u)lc_cancel();
    else state=3u;
    if(!clear_ready() && !cleanup)cleanup=7u;
    publish();return 0u;
}
br_u8 lc_prepare_handoff(void) {
    restore_leaf();
    if(state!=2u || error || cleanup || launch_ticket || br_result.handle ||
       br_result.state==BR_BUSY)return handoff_reject();
    launch_ticket=1u;
    if(!leaf_ui_acquire() || !leaf_ui_release()){fail(2u);return 0u;}
    memcpy(d64_release_input,release,64u);
    if(!d64_release_validate()){fail(5u);return 0u;}
    state=4u;publish();return 1u;
}
br_u8 lc_consume_handoff(void) {
    restore_leaf();
    if(state!=4u || launch_ticket!=1u || error || cleanup || br_result.handle ||
       memcmp(d64_release_output,release,64u))return handoff_reject();
    if(!leaf_ui_acquire() || !leaf_ui_release()){fail(2u);return 0u;}
    launch_ticket=2u;state=5u;publish();return 1u;
}

#if D64_START_OPTIONS
void lc_clock_fail(void) {
    if(state==1u&&io==8u){ii_now=lc_now;ii_clock_fail();ini_first();cancelled=1u;publish();return;}
    lc_cancel();
}
#endif

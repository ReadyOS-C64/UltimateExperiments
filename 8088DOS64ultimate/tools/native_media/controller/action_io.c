#include "action_shell.h"
#include <string.h>
/* The generated readonly table is bound to exact role-specific linked phase
 * products. It is never filled from menu observations or a disk filename. */
#include "action_assets.h"
extern ac_u8 ac_transfer(void);
ac_u16 ac_dma_host,ac_dma_count;
ac_u32 ac_dma_reu;
static ac_u32 payload_crc(ac_u16 address,ac_u16 count){
 ac_u32 crc=0xffffffffUL;ac_u16 i;ac_u8 bit;
 for(i=0;i<count;++i){crc^=((const ac_u8*)address)[i];for(bit=0;bit<8u;++bit)crc=(crc>>1)^((crc&1UL)?0xedb88320UL:0UL);}
 return crc^0xffffffffUL;
}
static ac_u8 copy(ac_u16 host,ac_u32 reu,ac_u16 count,ac_u32 crc){
 ac_dma_host=host;ac_dma_reu=reu;ac_dma_count=count;
 return ac_transfer()&&payload_crc(host,count)==crc;
}
ac_u8 ac_load(ac_u8 phase){
 const struct ac_asset *a;ac_u16 limit;
 if(phase<1u||phase>6u)return 0u;
 a=&ac_assets[phase-1u];limit=(phase==1u||phase==5u)?0x7e80u:0x7dd0u;
 if(a->host<0xa000u||!a->bytes||a->host+a->bytes>0xb800u||a->host+a->bytes<a->host||a->bss<0x7d00u||a->bss>=limit||a->bss_bytes>0x180u||a->bss+a->bss_bytes>limit)return 0u;
 if((phase==3u||phase==4u||phase==6u)!=!!a->wrapper_bytes)return 0u;
 if((phase==6u)!=!!a->aux_bytes)return 0u;
 if(!copy(a->host,a->reu,a->bytes,a->crc))return 0u;
 if(a->wrapper_bytes){
  if(a->wrapper_bytes>0xb0u||!copy(0x7dd0u,a->wrapper_reu,a->wrapper_bytes,a->wrapper_crc))return 0u;
 }
 if(a->aux_bytes){
  if(a->aux_bytes>0x700u||!copy(0x6600u,a->aux_reu,a->aux_bytes,a->aux_crc))return 0u;
 }
 memset((void*)a->bss,0,a->bss_bytes);
 return 1u;
}

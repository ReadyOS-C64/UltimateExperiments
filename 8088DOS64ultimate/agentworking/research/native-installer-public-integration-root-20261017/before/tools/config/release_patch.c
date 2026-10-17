#include "release_patch.h"
#include "crc32.h"
#include <string.h>
#pragma code-name("CONFIG_HIGH")
#pragma rodata-name("CONFIG_HRO")
#define RP_CONSTANTS_ONLY 1
#include "release_assets.h"
#pragma bss-name("BSS")
br_u8 rp_error;
br_u32 rp_output_crc;
static br_u8 consumed;
static br_u32 original,changed;
static br_u8 crc_part(br_u8*p,br_u16 n,br_u8 out){c32_crc=out?changed:original;c32_address=(br_u16)p;c32_length=n;if(!c32_update()||c32_error)return 0;if(out)changed=c32_crc;else original=c32_crc;return 1;}
br_u8 rp_patch(void){br_u16 at,n,i,control;const char*home;br_u8 v,w,relative;
 static const br_u8 basic[14]={1,8,11,8,10,0,0x9e,'2','0','6','1',0,0,0};
 rp_error=0;if(consumed)return rp_error=1,0;consumed=1;home=rp_admit();if(!home)return rp_error=1,0;
 /* Canonical non-root absolute padded home, exact supported suffix room. */
 for(n=0;n<128&&home[n];++n){}if(n<2||n>117||home[0]!='/')return rp_error=2,0;
 for(i=n+1;i<128;++i)if(home[i])return rp_error=2,0;
 for(i=1;i<=n;++i){v=home[i];if(i==n||v=='/'){if(home[i-1]=='/'||home[i-1]==' '||home[i-1]=='.')return rp_error=2,0;}else if(v<32||v>126||v=='\\'||v==':'||v=='"'||v=='*'||v=='<'||v=='>'||v=='?'||v=='|')return rp_error=2,0;}
 /* This offset is from the exact linked D64S descriptor, never caller input. */
 control=RP_CONTROL;original=changed=0xffffffffUL;
 for(at=0;at<18432u;at+=n){n=18432u-at>256u?256u:18432u-at;
  memset(rp_buffer,0xa7,256);if(!rp_read(at,n))return rp_error=3,0;
  if(!crc_part(rp_buffer,n,0))return rp_error=4,0;
  for(i=0;i<n;++i){v=rp_buffer[i];w=v;if(at+i<14&&v!=basic[at+i])return rp_error=5,0;
   if(at+i>=control&&at+i-control<131u){relative=(br_u8)(at+i-control);w=relative==0||relative==3?255u:(relative==1?0x1cu:(relative==2?0xdfu:0u));if(v!=w)return rp_error=5,0;if(!relative)w=0xa5u;else if(relative==1)w=0x1cu;else if(relative==2)w=0xdfu;else w=home[relative-3u];}
   rp_buffer[256u+i]=w;
  }
  if(!crc_part(rp_buffer+256,n,1))return rp_error=4,0;
  if(!rp_write(at,n)||memcmp(rp_buffer,rp_buffer+256,n))return rp_error=6,0;
 }
 if((original^0xffffffffUL)!=RP_TEMPLATE_CRC)return rp_error=7,0;
 rp_output_crc=changed^0xffffffffUL;return 1;
}

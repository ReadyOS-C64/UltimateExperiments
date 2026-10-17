#include "start_template.h"
#include "crc32.h"
#include <string.h>
st_u8 st_descriptor[64],st_home[128],st_cancel,st_io_error;
st_u16 st_base;
st_u8 st_error,st_done;
st_u32 st_copied,st_template_bytes;
#if DOS64_SETUP_COLD_INVENTORY
#include "publish_construct.h"
#define desc pub_construct.st.desc
#define home pub_construct.st.home
#define buffer pub_construct.st.buffer
#define base pub_construct.st.base
#define size pub_construct.st.size
#define control pub_construct.st.control
#define checksum pub_construct.st.checksum
#define raw pub_construct.st.raw
static st_u8 valid,error;
#else
static st_u8 desc[64],home[128],buffer[256],valid,error;
static st_u16 base;
static st_u32 size,control,checksum,raw;
#endif
static st_u16 word(st_u8 at){return (st_u16)desc[at]|((st_u16)desc[at+1u]<<8);}
static st_u32 wide(st_u8 at){return (st_u32)word(at)|((st_u32)word(at+2u)<<16);}
static st_u8 fail(st_u8 e){
#if DOS64_SETUP_COLD_INVENTORY
 if(pub_construct_owner==2u)pub_construct_owner=3u;
#endif
 if(!error)error=e;st_error=error;valid=st_done=0;return 0;}
static st_u8 crc_part(st_u16 n){
 c32_crc=raw;c32_address=(st_u16)buffer;c32_length=n;
 if(!c32_update()||c32_error)return fail(3u);
 raw=c32_crc;return 1;
}
static st_u8 settings(void){
 st_u8 n,i,start;
 if(base!=0xdf1cu&&base!=0xde1cu&&base!=0xdffcu)return 0;
 for(n=0;n<128u&&home[n];++n){}
 if(n<2u||n>117u||home[0]!='/')return 0;
 for(i=n+1u;i<128u;++i)if(home[i])return 0;
 start=1;
 for(i=1;i<=n;++i){
  if(i==n||home[i]=='/'){
   if(i==start||home[i-1u]==' '||home[i-1u]=='.')return 0;
   start=i+1u;
  }else if(home[i]<32u||home[i]>126u||home[i]=='\\'||home[i]==':'||home[i]=='"'||home[i]=='*'||home[i]=='<'||home[i]=='>'||home[i]=='?'||home[i]=='|')return 0;
 }
 return 1;
}
static st_u8 header(void){
 st_u32 data,delta;st_u16 n;st_u8 i;
 if(memcmp(desc,"D64S\1\1\100\0",8))return 0;
 if(word(16)!=0x0801u||word(20)!=0x080du||word(22)!=131u)return 0;
 if(memcmp(desc+34u,"\0\1\3\200\377\377\34\337\0",9))return 0;
 for(i=43;i<60u;++i)if(desc[i])return 0;
 size=wide(8);checksum=wide(12);control=wide(24);data=wide(28);n=word(32);
 if(size!=st_template_bytes||size<16UL||size>ST_TEMPLATE_MAX||word(18)!=size-2UL||data<14UL||data>size||!n||n>size-data||control<data||control>size||131UL>size-control)return 0;
 delta=control-data;if(delta>n||131UL>(st_u32)n-delta)return 0;
 return 1;
}
static st_u8 transfer(st_u8 output){
 static const st_u8 basic[14]={1,8,11,8,10,0,0x9e,'2','0','6','1',0,0,0};
 st_u32 at=0,relative;st_u16 n,i;st_u8 v,w;
 raw=0xffffffffUL;
 while(at<size){
  n=size-at>256UL?256u:(st_u16)(size-at);
  for(i=0;i<n;++i){
   if(st_cancel)return fail(6u);
   v=st_read(at+i);if(st_io_error)return fail(4u);buffer[i]=v;
   if(at+i<14UL&&v!=basic[(st_u8)(at+i)])return fail(1u);
   if(at+i>=control&&at+i-control<131UL){
    relative=at+i-control;
    w=relative==0UL||relative==3UL?255u:(relative==1UL?0x1cu:(relative==2UL?0xdfu:0u));
    if(v!=w)return fail(1u);
    if(output){if(!relative)w=0xa5u;else if(relative==1UL)w=(st_u8)base;else if(relative==2UL)w=(st_u8)(base>>8);else w=home[(st_u8)(relative-3UL)];}
   }else w=v;
   if(output){st_write(at+i,w);if(st_io_error)return fail(5u);++st_copied;}
  }
  if(!crc_part(n))return 0;at+=n;
 }
 if((raw^0xffffffffUL)!=checksum)return fail(3u);
 return 1;
}
st_u8 st_validate(void){
#if DOS64_SETUP_COLD_INVENTORY
 if(pub_construct_owner)return fail(7u);
#endif
 valid=error=st_error=st_done=0;st_copied=0;st_io_error=0;
#if DOS64_SETUP_COLD_INVENTORY
 pub_construct_owner=2u;
#endif
 memcpy(desc,st_descriptor,64);memcpy(home,st_home,128);base=st_base;
 if(st_cancel)return fail(6u);if(!settings())return fail(2u);
 if(!c32_init()||c32_error)return fail(3u);
 memcpy(buffer,desc,60);raw=0xffffffffUL;if(!crc_part(60u))return 0;
 if((raw^0xffffffffUL)!=wide(60))return fail(1u);
 if(!header())return fail(1u);
 if(!transfer(0u))return 0;valid=1;return 1;
}
st_u8 st_ready(void){st_error=error;return valid&&!error&&!st_cancel&&!st_io_error;}
st_u8 st_copy_patch(void){
 if(st_cancel)return fail(6u);if(!st_ready())return fail(7u);valid=0;st_copied=0;
 if(!transfer(1u))return 0;st_done=1;
#if DOS64_SETUP_COLD_INVENTORY
 pub_construct_owner=0u;
#endif
 return 1;
}

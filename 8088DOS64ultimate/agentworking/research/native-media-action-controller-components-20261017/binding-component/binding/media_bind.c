#include "media_bind.h"
#include <string.h>
extern unsigned char mb_buffer[576],mb_compare[576],mb_ledger[183],mb_token[70];
extern unsigned char mb_service(void),mb_owner(void),mb_clean(void),mb_dma(void);
extern unsigned int mb_dma_c64,mb_dma_count;
extern unsigned long mb_dma_address;
extern unsigned char mb_dma_write,mb_uci_base[2];
extern unsigned long __fastcall__ mp_crc(const unsigned char*,unsigned int,unsigned long);
#define BUF mb_buffer
#define CMP mb_compare
#define crc mp_crc
static unsigned char state,error,verify[64],readonly,columns,oldbody[4],newbody[4],maincrc[4],header[32];

unsigned char mb_cancel_seen;
static unsigned char fail(unsigned char e){extern unsigned char mb_block; if(!error)error=e;state=3u;mb_block=0xe1u;return 0u;}
static unsigned char service(void){return mb_service()?1u:fail(3u);}
static unsigned char transfer(unsigned int c,unsigned long a,unsigned int n,unsigned char w){if(!n||n>64u)return fail(4u);mb_dma_c64=c;mb_dma_address=a;mb_dma_count=n;mb_dma_write=w;if(!mb_dma())return fail(5u);return service();}
static unsigned char read_at(unsigned long a,unsigned int n){unsigned int off,k;for(off=0;off<n;off+=64u){k=n-off;if(k>64u)k=64u;memset(BUF+off,0xa5u,k);memset(verify,0x5au,k);if(!transfer((unsigned int)(BUF+off),a+off,k,0u)||!transfer((unsigned int)verify,a+off,k,0u))return 0u;if(memcmp(BUF+off,verify,k))return fail(6u);}return 1u;}
static unsigned char write_at(unsigned long a,unsigned int n){unsigned int off,k,i;for(off=0;off<n;off+=64u){k=n-off;if(k>64u)k=64u;if(!transfer((unsigned int)(BUF+off),a+off,k,1u))return 0u;for(i=0;i<k;++i)verify[i]=~BUF[off+i];if(!transfer((unsigned int)verify,a+off,k,0u))return 0u;if(memcmp(BUF+off,verify,k))return fail(6u);}return 1u;}
#include "semantic.inc"
unsigned char mb_ledger_check(void){return state==1u&&mb_token[1]==1u&&(crc(mb_token+1u,65u,0xffffffffUL)^0xffffffffUL)==get32(mb_token+66u)&&(crc(mb_ledger,183u,0xffffffffUL)^0xffffffffUL)==get32(mb_token+5u);}
static unsigned char header_valid(unsigned char options){unsigned int i;unsigned long c;if(memcmp(BUF,options==1u?"D64O":"D64R",4u)||BUF[4]!=1u||BUF[5]||BUF[6]!=32u||BUF[7]||memcmp(BUF+8u,oldbody,4u))return 0u;
BUF[5]=0xa5u;c=crc(BUF,28u,0xffffffffUL)^0xffffffffUL;BUF[5]=0u;if(c!=get32(BUF+28u))return 0u;
if(options==1u){if(memcmp(BUF+12u,maincrc,4u)||(BUF[16]!=40u&&BUF[16]!=80u))return 0u;if(columns&&columns!=BUF[16])return 0u;columns=BUF[16];for(i=17u;i<28u;++i)if(BUF[i])return 0u;}
else{if((!options&&memcmp(BUF+16u,mb_token+54u,8u))||(options&&memcmp(BUF+16u,CMP+528u,8u))||BUF[26]!=1u||BUF[27]!=2u||memcmp(BUF+24u,mb_uci_base,2u))return 0u;if(!((BUF[24]==0x1cu&&(BUF[25]==0xdeu||BUF[25]==0xdfu))||(BUF[24]==0xfcu&&BUF[25]==0xdfu)))return 0u;if(options){if(memcmp(maincrc,BUF+12u,4u))return 0u;}else memcpy(maincrc,BUF+12u,4u);}
return 1u;}
static unsigned char patch_options(void){if(!read_at(0x3ff500UL,32u)||!header_valid(1u))return fail(9u);memcpy(BUF+8u,newbody,4u);BUF[5]=0xa5u;put32(BUF+28u,crc(BUF,28u,0xffffffffUL)^0xffffffffUL);BUF[5]=0u;memcpy(header,BUF,32u);if(!write_at(0x3ff500UL,32u)||!read_at(0x3ff500UL,32u)||memcmp(BUF,header,32u))return fail(6u);return 1u;}
unsigned char mb_bind(void){unsigned int off;unsigned long c;unsigned char mask;if(state)return 0u;state=1u;error=0u;mb_cancel_seen=0u;
if(mb_token[0]!=0xa5u)return fail(1u);mb_token[0]=0u;
if(mb_token[1]!=1u||!(mb_token[3]|mb_token[4])||mb_ledger[0]!=2u||mb_ledger[2]>1u||mb_ledger[3]!=0xa5u||mb_ledger[178]||
 !mb_owner()||!service())return fail(1u);
/* The immutable receipt binds the journal used by the completed file job. */
c=0xffffffffUL;for(off=0;off<1280u;off+=64u){if(!read_at(0x3e0600UL+off,64u))return 0u;c=crc(BUF,64u,c);}c^=0xffffffffUL;if(c!=get32(mb_ledger+179u)||!read_at(0x3e0b00UL,4u)||get32(BUF)!=get32(mb_ledger+179u))return fail(7u);
if(!read_at(0x3e0600UL,64u)||memcmp(BUF,"D64J\1\4\5",7u)||BUF[7]||BUF[8]!=mb_ledger[2]||BUF[9]>1u||memcmp(BUF+10u,mb_token+3u,2u)||memcmp(BUF+12u,mb_ledger+132u,42u)||get32(BUF+54u)!=get32(mb_ledger+174u))return fail(7u);readonly=BUF[9];
if(!read_at(0x3ff020UL,576u)||!valid())return fail(8u);memcpy(CMP,BUF,576u);memcpy(oldbody,BUF+572u,4u);if((crc(BUF+8u,128u,0xffffffffUL)^0xffffffffUL)!=get32(mb_token+34u)||memcmp(mb_token+54u,BUF+528u,8u))return fail(8u);
if(!read_at(0x3e0000UL,576u)||memcmp(BUF,CMP,576u)||!read_at(0x3e0680UL,576u)||memcmp(BUF,CMP,576u))return fail(8u);
if(!read_at(0x3e0300UL,576u)||!valid())return fail(8u);off=mb_ledger[2]?264u:136u;mask=mb_ledger[2]?2u:1u;if(memcmp(BUF+off,mb_ledger+4u,128u)||get32(BUF+(mb_ledger[2]?532u:528u))!=get32(mb_ledger+174u)||!!(BUF[524]&mask)!=readonly)return fail(8u);memcpy(CMP+off,BUF+off,128u);CMP[524]=(CMP[524]&~mask)|(BUF[524]&mask);off=mb_ledger[2]?532u:528u;memcpy(CMP+off,BUF+off,4u);memcpy(CMP+572u,BUF+572u,4u);if(memcmp(BUF,CMP,576u))return fail(8u);
memcpy(newbody,BUF+572u,4u);memcpy(CMP,BUF,576u);if(!read_at(0x3e08c0UL,576u)||memcmp(BUF,CMP,576u))return fail(8u);
/* Validate both consumed headers BEFORE changing even one accepted byte. */
/* R's old A/B cookies live in the retained receipt, not new CMP. */
if(!read_at(0x3ff000UL,32u)||!header_valid(0u))return fail(9u);c=crc(BUF,28u,0xffffffffUL);
if(!read_at(0x3ff500UL,32u)||!header_valid(1u)||(crc(BUF,28u,c)^0xffffffffUL)!=get32(mb_token+62u)||!mb_owner()||!service())return fail(9u);
/* Header update needs the original cookie comparison; rebuild without hidden state. */
if(!read_at(0x3ff000UL,32u))return 0u;memcpy(BUF+8u,newbody,4u);memcpy(BUF+16u,CMP+528u,8u);BUF[5]=0xa5u;put32(BUF+28u,crc(BUF,28u,0xffffffffUL)^0xffffffffUL);BUF[5]=0u;memcpy(header,BUF,32u);
if(!write_at(0x3ff000UL,32u)||!read_at(0x3ff000UL,32u)||memcmp(BUF,header,32u))return fail(6u);
if(!patch_options())return 0u;memcpy(oldbody,newbody,4u);
memcpy(BUF,CMP,576u);if(!write_at(0x3ff020UL,576u)||!read_at(0x3ff020UL,576u)||memcmp(BUF,CMP,576u)||!valid()||!mb_owner()||!service())return fail(10u);
if(!read_at(0x3ff000UL,32u)||!header_valid(2u)||!read_at(0x3ff500UL,32u)||!header_valid(1u))return fail(10u);
/* No callback after this final fresh owner/clock gate until atomic CLEAN. */
if(!mb_clean())return fail(11u);state=2u;return 1u;
}
unsigned char mb_state(void){return state;}
unsigned char mb_error(void){return error;}

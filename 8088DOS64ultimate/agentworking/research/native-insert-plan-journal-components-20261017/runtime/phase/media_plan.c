#include "media_plan.h"
#include <string.h>
#ifndef MP_RUNTIME_RECEIPT
#define MP_RUNTIME_RECEIPT 0
#endif
#if MP_RUNTIME_RECEIPT
extern unsigned char mp_ledger[256];
#endif
#pragma code-name ("CODE")
#pragma rodata-name ("RODATA")
unsigned char mp_drive,mp_readonly,mp_cancel,mp_error,mp_current_missing;
unsigned int mp_sequence;
unsigned long mp_capacity,mp_image_crc;
unsigned char mp_image_path[128],mp_snapshot[42];
extern unsigned char mp_dma(void);
extern unsigned long mp_dma_address;
extern unsigned int mp_dma_count;
extern unsigned char mp_dma_write;
static unsigned char state,first;
#define BUF mp_buffer
extern unsigned char mp_buffer[576];
#define CMP mp_compare
extern unsigned char mp_compare[576];
#define OLD_OFF 128u
#define NEW_OFF 704u
extern unsigned long __fastcall__ mp_crc(const unsigned char*p,unsigned int n,unsigned long c);
#define crc mp_crc
static unsigned char fail(unsigned char e){if(!first)first=e;mp_error=first;state=3u;return 0u;}
extern unsigned char mp_service(void);
static unsigned char stopped(void){if(mp_cancel)return fail(7u);
#if MP_RUNTIME_RECEIPT
if(!mp_service())return fail(mp_cancel?7u:13u);
#endif
return 1u;}
static unsigned char transfer(unsigned long a,unsigned int n,unsigned char wr){if(a>mp_capacity||n>mp_capacity-a||n>576u)return fail(8u);mp_dma_address=a;mp_dma_count=n;mp_dma_write=wr;if(!mp_dma())return fail(9u);return stopped();}
static unsigned char fetch(unsigned long a,unsigned int n){return transfer(a,n,0u);}
static unsigned char store(unsigned long a,unsigned int n){unsigned int i;memcpy(CMP,BUF,n);if(!transfer(a,n,1u))return 0u;for(i=0;i<n;++i)BUF[i]=~CMP[i];if(!fetch(a,n))return 0u;for(i=0;i<n;++i)if(BUF[i]!=CMP[i])return fail(10u);return 1u;}
static unsigned char plen(const unsigned char*p){unsigned char i;for(i=0;i<128u;++i)if(!p[i])return i;return 255u;}
static unsigned char path(const unsigned char*p,unsigned char present){unsigned char n=plen(p),i,start;if(!present){for(i=0;i<128u;++i)if(p[i])return 0u;return 1u;}if(!n||n==255u||p[0]!='/')return 0u;for(i=n+1u;i<128u;++i)if(p[i])return 0u;if(n==1u)return 1u;start=1u;for(i=1u;i<=n;++i){if(i!=n&&p[i]!='/'){if(p[i]<32u||p[i]>126u||p[i]=='\\'||p[i]==':'||p[i]=='"'||p[i]=='*'||p[i]=='<'||p[i]=='>'||p[i]=='?'||p[i]=='|')return 0u;}else{if(i==start||p[i-1u]==' '||p[i-1u]=='.')return 0u;start=i+1u;}}return 1u;}
static unsigned long get32(const unsigned char*p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
static void put32(unsigned char*p,unsigned long n){unsigned char i;for(i=0;i<4u;++i){p[i]=(unsigned char)n;n>>=8;}}
static unsigned char valid(void){unsigned char p=BUF[525],r=BUF[524];unsigned int i;if(memcmp(BUF,"D64C",4u)||BUF[4]!=1u||BUF[5]!=64u||BUF[6]!=2u||BUF[7]||BUF[526]||BUF[527])return 0u;for(i=542u;i<572u;++i)if(BUF[i])return 0u;if(!(p&1u)||(p&248u)||(r&248u)||(r&~p))return 0u;if(!path(BUF+8u,1u)||!path(BUF+136u,1u)||!path(BUF+264u,p&2u)||!path(BUF+392u,p&4u))return 0u;if(plen(BUF+136u)<2u||((p&2u)&&plen(BUF+264u)<2u)||((p&4u)&&plen(BUF+392u)<2u))return 0u;if(BUF[520]||BUF[521]||BUF[522]>1u||BUF[523]||(!(p&4u)&&BUF[522]))return 0u;if(!(p&2u)&&get32(BUF+532u))return 0u;if(BUF[536]!=1u||BUF[537]||BUF[538]||BUF[539]||BUF[541]>1u||(BUF[541]&&BUF[540])||(!BUF[541]&&BUF[540]<64u))return 0u;return (crc(BUF,572u,0xffffffffUL)^0xffffffffUL)==get32(BUF+572u);}
/* Snapshot describes the OLD mounted state. An incoming verified image may
 * replace an ejected disk or create the first B binding. All-zero descriptor
 * is canonical only for never-configured B; CFG presence is checked below. */
static unsigned char snapshot_valid(const unsigned char*p,unsigned char d){unsigned char i;if(p[9]>1u)return 0u;for(i=0;i<10u&&!p[i];++i){}if(i==10u)return d==1u;if(p[0]||p[1]||(p[2]!=0x10u&&p[2]!=0x18u&&p[2]!=0x38u))return 0u;return !memcmp(p+3u,"\xd0\x02\x28\x00\x02\x09",6u);}
static unsigned char shape(void){const unsigned char*p=mp_snapshot+(mp_drive?10u:0u);if(mp_drive>1u||mp_readonly>1u||!mp_sequence||mp_capacity<0x400000UL||mp_capacity>0x1000000UL||(mp_capacity&65535UL))return 0u;if(!snapshot_valid(p,mp_drive))return 0u;return path(mp_image_path,1u)&&plen(mp_image_path)>1u;}
unsigned char mp_state(void){mp_error=first;return state;}
unsigned char mp_first_error(void){mp_error=first;return first;}
unsigned char mp_build(void){unsigned int i,off;unsigned long c;unsigned char mask;if(state)return fail(1u);state=1u;first=mp_error=0u;if(!shape())return fail(2u);
#if MP_RUNTIME_RECEIPT
if(mp_ledger[0]!=2u||mp_ledger[3]!=0xa5u||mp_drive!=mp_ledger[2]||memcmp(mp_image_path,mp_ledger+4u,128u)||memcmp(mp_snapshot,mp_ledger+132u,42u)||mp_image_crc!=get32(mp_ledger+174u))return fail(14u);
mp_ledger[178]=0u;
#endif
if(!stopped()||!fetch(0x3ff020UL,576u))return 0u;if(!valid())return fail(3u);/* caller's independently read exact original lives in OLD */memcpy(CMP,BUF,576u);if(!fetch(MP_OLD,576u))return 0u;if(memcmp(BUF,CMP,576u))return fail(4u);mask=mp_drive?2u:1u;off=mp_drive?10u:0u;if(!mp_snapshot[off+2u]&&(BUF[525]&mask))return fail(2u);off=mp_drive?264u:136u;memcpy(BUF+off,mp_image_path,128u);BUF[525]|=mask;BUF[524]=(BUF[524]&~mask)|(mp_readonly?mask:0u);put32(BUF+(mp_drive?532u:528u),mp_image_crc);put32(BUF+572u,crc(BUF,572u,0xffffffffUL)^0xffffffffUL);if(!valid())return fail(3u);if(!store(MP_NEW,576u))return 0u;memset(BUF,0,128u);memcpy(BUF,"D64J",4u);BUF[4]=1u;BUF[5]=4u;BUF[6]=5u;BUF[8]=mp_drive;BUF[9]=mp_readonly;BUF[10]=(unsigned char)mp_sequence;BUF[11]=(unsigned char)(mp_sequence>>8);memcpy(BUF+12u,mp_snapshot,42u);put32(BUF+54u,mp_image_crc);if(!store(MP_JOURNAL,128u))return 0u;for(off=0;off<576u;off+=256u){i=576u-off;if(i>256u)i=256u;if(!fetch(MP_OLD+off,i)||!store(MP_JOURNAL+OLD_OFF+off,i))return 0u;if(!fetch(MP_NEW+off,i)||!store(MP_JOURNAL+NEW_OFF+off,i))return 0u;}c=0xffffffffUL;for(off=0;off<1280u;off+=256u){if(!fetch(MP_JOURNAL+off,256u))return 0u;c=crc(BUF,256u,c);}put32(BUF,c^0xffffffffUL);if(!store(MP_JOURNAL+1280u,4u))return 0u;
#if MP_RUNTIME_RECEIPT
memcpy(mp_ledger+179u,BUF,4u);mp_ledger[178]=0xa5u;
#endif
state=2u;return 1u;}
#ifndef MP_BUILD_ONLY
unsigned char mp_journal_check(void){unsigned int off,i;unsigned long c=0xffffffffUL;unsigned char drive,ro,base;unsigned long image;if(first)return 0u;if(!stopped()||!fetch(MP_JOURNAL,128u))return 0u;if(memcmp(BUF,"D64J",4u)||BUF[4]!=1u||BUF[5]!=4u||BUF[6]!=5u||BUF[7]||BUF[8]>1u||BUF[9]>1u||!(BUF[10]|BUF[11]))return fail(11u);for(i=58u;i<128u;++i)if(BUF[i])return fail(11u);drive=BUF[8];ro=BUF[9];image=get32(BUF+54u);if(!snapshot_valid(BUF+12u+(drive?10u:0u),drive))return fail(11u);base=BUF[12u+(drive?10u:0u)+2u];for(off=0;off<1280u;off+=256u){if(!fetch(MP_JOURNAL+off,256u))return 0u;c=crc(BUF,256u,c);}if(!fetch(MP_JOURNAL+1280u,4u))return 0u;if((c^0xffffffffUL)!=get32(BUF))return fail(11u);if(!fetch(MP_JOURNAL+OLD_OFF,576u)||!valid())return fail(11u);if(!base&&(BUF[525]&(drive?2u:1u)))return fail(11u);if(!store(MP_OLD,576u))return 0u;if(!fetch(MP_JOURNAL+NEW_OFF,576u)||!valid())return fail(11u);if(!(BUF[525]&(drive?2u:1u))||get32(BUF+(drive?532u:528u))!=image||!!(BUF[524]&(drive?2u:1u))!=ro)return fail(11u);/* Compare preserved fields after normalizing only permitted changes. */memcpy(CMP,BUF,576u);if(!fetch(MP_OLD,576u))return 0u;off=drive?264u:136u;memcpy(CMP+off,BUF+off,128u);if((CMP[524]^BUF[524])&~(drive?2u:1u))return fail(11u);CMP[524]=BUF[524];if((CMP[525]^BUF[525])&~(drive?2u:1u))return fail(11u);CMP[525]=BUF[525];memcpy(CMP+(drive?532u:528u),BUF+(drive?532u:528u),4u);memcpy(CMP+572u,BUF+572u,4u);if(memcmp(BUF,CMP,576u))return fail(11u);return 1u;}
unsigned char mp_recovery_classify(void){if(!mp_journal_check())return 0u;if(mp_current_missing)return 3u;/* current exact file bytes supplied at3E1000 after exact READ/EOF/CLOSE */if(!fetch(0x3e1000UL,576u))return 0u;memcpy(CMP,BUF,576u);if(!fetch(MP_JOURNAL+OLD_OFF,576u))return 0u;if(!memcmp(BUF,CMP,576u))return 1u;if(!fetch(MP_JOURNAL+NEW_OFF,576u))return 0u;if(!memcmp(BUF,CMP,576u))return 2u;return fail(12u);}

#endif

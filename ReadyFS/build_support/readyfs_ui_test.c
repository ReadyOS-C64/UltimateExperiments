/* Behavioral screen-write oracle: catches needless repainting and stale tails. */
#include "src/apps/readyfs/readyfs_ui.h"
#include "src/apps/readyfs/readyfs_reu.h"
#include "src/apps/readyfs/readyfs_console.h"
#include "src/apps/readyfs/readyfs_commands.h"
#include <conio.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
unsigned char readyfs_ui_test_screen[1000], readyfs_ui_test_color[1000];
unsigned char readyfs_ui_test_modifier, readyfs_console_recording;
unsigned char readyfs_reu_console_bank_value;
unsigned int readyfs_console_head,readyfs_console_used;
static unsigned char bank[0x8000];
static char history[2][256] = {"PWD","HELP"};
static unsigned char x,y,color;
static unsigned writes,key_index;
static const unsigned char *keys;
static const int *expected_writes;
static unsigned key_count;
static unsigned char paging_test;
const char readyfs_long_options[] = "--recursive\0--dry-run\0--exclude\0--force\0--include\0--line\0--name\0--native-pattern\0--type\0--yes\0--apply\0--continue\0--label\0--id\0--disposable\0--no-verify\0";
void cputc(char value) {
    assert(x<40 && y<25);
    readyfs_ui_test_color[y*40+x]=color;
    if (readyfs_console_recording) assert(color==COLOR_CYAN);
    readyfs_ui_test_screen[y*40+x]=value; ++writes;
    if (++x==40) {x=0;if(y<24)++y;}
}
void cputs(const char *s) {while(*s)cputc(*s++);}
void gotoxy(unsigned char xx,unsigned char yy){x=xx;y=yy;}
unsigned char wherey(void){return y;}
unsigned char textcolor(unsigned char c){unsigned char old=color;color=c;return old;}
void clrscr(void){memset(readyfs_ui_test_screen,' ',1000);x=y=0;}
void readyfs_console_scroll(void){}
unsigned char cgetc(void){
    assert(key_index<key_count);
    if (paging_test && (key_index==2 || key_index==4)) {
        assert(readyfs_ui_test_color[0]==COLOR_CYAN);
        assert(readyfs_ui_test_color[40]==COLOR_WHITE);
    }
    if (paging_test && key_index==5) assert(readyfs_ui_test_color[804]==COLOR_CYAN);
    if(key_index && expected_writes[key_index-1]>=0)
        { if(writes!=(unsigned)expected_writes[key_index-1]) fprintf(stderr,"key %u (%u) writes %u expected %d\n",key_index-1,keys[key_index-1],writes,expected_writes[key_index-1]); assert(writes==(unsigned)expected_writes[key_index-1]); }
    writes=0;
    return keys[key_index++];
}
unsigned char readyfs_reu_batch_store(unsigned int off,const void *data,unsigned int size){assert(off+size<=sizeof(bank));memcpy(bank+off,data,size);return 1;}
unsigned char readyfs_reu_batch_fetch(unsigned int off,void *data,unsigned int size){assert(off+size<=sizeof(bank));memcpy(data,bank+off,size);return 1;}
unsigned char readyfs_reu_console_fetch(unsigned int off,void *data,unsigned int size){
    memset(data, off%80==40 ? ((off/80)%2 ? COLOR_CYAN : COLOR_WHITE) : 32, size);return 1;
}
unsigned char readyfs_reu_history_count(void){return 2;}
unsigned char readyfs_reu_history_get(unsigned char age,char *out){assert(age<2);strcpy(out,history[age]);return 1;}
unsigned char readyfs_same_word(const char *a,const char *b){unsigned char ca,cb;do{ca=*a++&127;cb=*b++&127;if(ca>='A'&&ca<='Z')ca+=32;if(cb>='A'&&cb<='Z')cb+=32;if(ca!=cb)return 0;}while(ca);return 1;}
static void editor(const unsigned char *input,const int *counts,unsigned n,const char *expected){
    char text[256]; ReadyFsBatchCall call;
    memset(&call,0,sizeof(call));call.buffer=text;call.capacity=sizeof(text);
    x=y=0;writes=key_index=0;keys=input;expected_writes=counts;key_count=n;
    assert(readyfs_ui_editor(&call)); assert(strcmp(text,expected)==0);
    assert(key_index==n);
    assert(color==COLOR_WHITE);
}
int main(void){
    static const unsigned char edits[]={ 'P','W','D',157,29,20,157,'X',19,148,29,'Z',20,13 };
    static const int counts[]={1,1,1,0,0,1,0,2,0,16,0,1,2,-1};
    static const unsigned char draft[]={ 'D','R','A','F','T',145,145,145,17,17,13 };
    static const int draft_counts[]={1,1,1,1,1,144,144,0,144,160,-1};
    static const unsigned char join[]={ 'P','W','\\',13,'D',13 };
    static const int join_counts[]={1,1,1,-1,1,-1};
    static const unsigned char explicit_join[]={ 'P',136,'W',141,'D',13 };
    static const int explicit_counts[]={1,-1,1,1,1,-1};
    static const unsigned char quote_join[]={ 'X',' ',34,'A',13,'B',34,13 };
    static const int quote_counts[]={1,1,1,1,-1,1,1,-1};
    static const unsigned char controls[]={134,135,137,127,13};
    static const int control_counts[]={0,0,0,0,-1};
    unsigned char long_keys[258]; int long_counts[258];unsigned i;
    ReadyFsTreeCall call; char *args[]={"cp","-f","-y","-r","-w","-x","-f","-np","-nv"};
    editor(controls,control_counts,sizeof(controls),"");
    editor(edits,counts,sizeof(edits),"PW");
    editor(draft,draft_counts,sizeof(draft),"DRAFT");
    editor(join,join_counts,sizeof(join),"PW D");
    editor(explicit_join,explicit_counts,sizeof(explicit_join),"P W D");
    editor(quote_join,quote_counts,sizeof(quote_join),"X \"A B\"");
    for(i=0;i<256;++i){long_keys[i]='A';long_counts[i]=(i&&i%36==0&&i>=144)?160:1;}
    /* At 144,180,216,252 characters the cursor moves the viewport. */
    for(i=143;i<255;i+=36)long_counts[i]=160;
    for(i=144;i<255;i+=36)long_counts[i]=1;
    long_counts[255]=0;long_keys[256]=20;long_counts[256]=1;long_keys[257]=13;long_counts[257]=-1;
    {char expected[256];memset(expected,'A',254);expected[254]=0;editor(long_keys,long_counts,258,expected);}
    {static const unsigned char page_keys[]={'P',133,133,134,3,13};
     static const int page_counts[]={1,-1,-1,-1,-1,-1};
     readyfs_console_used=readyfs_console_head=24;paging_test=1;
     editor(page_keys,page_counts,6,"P");paging_test=0;readyfs_console_used=0;}
    memset(&call,0,sizeof(call));call.name="cp";call.command_args=args;call.command_argc=9;
    assert(readyfs_ui_prepare(&call));assert(call.result==RF_COMMAND_COPY);
    assert(strcmp(args[1],"-f")==0&&strcmp(args[2],"-y")==0);
    assert(strcmp(args[3],"--recursive")==0&&strcmp(args[4],"--dry-run")==0);
    assert(strcmp(args[5],"--exclude")==0&&strcmp(args[6],"-f")==0);
    assert(strcmp(args[7],"--native-pattern")==0);
    assert(strcmp(args[8],"--no-verify")==0);
    puts("ReadyFS UI: minimal screen writes, wrap, 255-byte bound, editable history/draft, continuation, exact option aliases PASS");
    return 0;
}

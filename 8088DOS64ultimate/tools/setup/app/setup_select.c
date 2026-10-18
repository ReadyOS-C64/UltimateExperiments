#include "setup_select.h"
#include "directory_browser.h"
#include "platform.h"
#include <string.h>

static struct ss_choices_t choices;
const struct ss_choices_t * const ss_choices=&choices;
br_u8 ss_error,ss_stage;
static char current[128];
static br_u16 limit,view;
static br_u8 state,stage,loading,row,cancelled,dirty,error;
static const char * const titles[]={
 "Choose the DOS64 home folder", "Choose DOS disk 1", "Choose DOS disk 2",
 "Choose DOS disk 3", "Import an existing C image?", "Choose C drive size", "Review installation choices"
};
static void text(br_u8 y,br_u8 x,const char *s){
 ps_row=y;ps_col=x;ps_color=1;
 while(*s&&ps_col<40){ps_ascii=(br_u8)*s++;if(ps_ascii<32||ps_ascii>126)ps_ascii='?';ps_put();++ps_col;}
}
static br_u8 escape(br_u8 c){
 return c<32||c>126||c=='%'||c=='_'||c=='`'||c=='{'||c=='}'||c=='~'||c=='^'||c=='\\'||c=='|';
}
/* Percent is escaped too, so raw names never alias their displayed encoding.
 * Offset counts encoded cells; all127-byte canonical paths can be reviewed. */
static void encoded(br_u8 y,br_u8 x,const char *s,br_u16 offset,br_u8 width){
 static const char hex[]="0123456789ABCDEF";
 br_u8 c,i,n,out; br_u16 position=0;
 ps_row=y;ps_col=x;ps_color=1;
 while(*s&&ps_col<x+width){
  c=(br_u8)*s++;n=escape(c)?3:1;
  for(i=0;i<n&&ps_col<x+width;i++){
   out=n==1?c:(i==0?'%':hex[i==1?c>>4:c&15]);
   if(position++>=offset){ps_ascii=out;ps_put();++ps_col;}
  }
 }
}
static void line(br_u8 y,const char *s,br_u16 offset){encoded(y,0,s,offset,40);}
static void publish(void){ss_error=error;ss_stage=stage;}
static void fail(br_u8 reason){if(!error)error=reason;state=SS_FAILED;dirty=1;publish();}
static void refresh(br_u16 first){
 memset(&db_request,0,sizeof(db_request));db_request.owner=0xa5;db_request.target=1;
 db_request.folders_only=stage==0;db_request.timeout=limit;db_request.first=first;
 memcpy(db_request.path,current,128);db_now=ps_ticks;
 if(!db_begin()){fail(SS_DIRECTORY);return;}loading=1;row=view=0;dirty=1;
}
static void next_stage(void){
 ++stage;ss_stage=stage;row=view=0;dirty=1;
 if(stage<5)refresh(0);
}
static const char *detail(void){
 if(stage==6){if(row==0)return choices.home;if(row<4)return choices.dos[row-1];return choices.existing_present?choices.existing:"No existing C import";}
 if(stage<5&&!loading&&db_page->count&&row<db_page->count){
  if(db_select(row))return db_selected_path;
 }
 return current;
}
static void render(void){
 br_u8 i;ps_color=1;ps_clear();text(0,0,"DOS64 setup");text(1,0,titles[stage]);
 if(state==SS_FAILED){text(4,0,error==SS_CANCEL?"Cancelled":"Selection stopped safely");text(6,0,"No installation files have been written.");return;}
 if(stage<5){
  line(3,current,0);
  if(loading)text(5,0,"Reading folder...");
  else for(i=0;i<db_page->count;i++){
   text(5+i,0,i==row?">":" ");text(5+i,1,(db_page->rows[i].attr&16)?"/":" ");
   encoded(5+i,2,(const char*)(db_page->rows[i].usable?db_page->rows[i].raw:db_page->rows[i].display),0,38);
  }
  text(18,0,"Return: open folder / choose file");text(19,0,"Up/down: select  Backspace: parent");
  text(20,0,"F3: previous page  F5: next page");
  if(stage==0)text(21,0,"F1: use this folder as DOS64 home");
  if(stage==4)text(21,0,"F1: skip existing C image import");
 }else if(stage==5){
  text(5,0,row==0?"> 2 MiB hard drive":"  2 MiB hard drive");
  text(7,0,row==1?"> 20 MiB hard drive":"  20 MiB hard drive");
  text(11,0,"Up/down: select  Return: continue");
  text(14,0,"Creates a fresh image on the Ultimate.");
 }else{
  text(5,0,row==0?"> Home folder":"  Home folder");
  text(7,0,row==1?"> DOS disk 1":"  DOS disk 1");text(9,0,row==2?"> DOS disk 2":"  DOS disk 2");
  text(11,0,row==3?"> DOS disk 3":"  DOS disk 3");text(13,0,row==4?"> Existing C source":"  Existing C source");
  text(15,0,choices.profile?"New C: 20 MiB":"New C: 2 MiB");
  text(18,0,"Return: confirm choices");text(19,0,"Source images will remain unchanged.");
 }
 text(22,0,"Left/right: view path  Run/Stop: cancel");line(24,detail(),view);
}
static void choose(void){
 br_u8 i;
 if(!db_page->count||row>=db_page->count||!db_select(row)){dirty=1;return;}
 if(db_page->rows[row].attr&16){memcpy(current,db_selected_path,128);refresh(0);return;}
 if(stage<1||stage>4)return;
 for(i=0;i<3;i++)if(choices.dos[i][0]&&!strcmp(choices.dos[i],db_selected_path)){text(23,0,"Choose a different source file.");return;}
 if(stage<4)memcpy(choices.dos[stage-1],db_selected_path,128);
 else {memcpy(choices.existing,db_selected_path,128);choices.existing_present=1;}
 next_stage();
}
br_u8 ss_begin(br_u8 owner,br_u16 timeout){
 if(owner!=0xa5||!timeout||timeout>=0x8000U||state)return 0;
 memset(&choices,0,sizeof(choices));memset(current,0,128);
 error=ss_error=ss_stage=stage=loading=row=view=cancelled=0;state=SS_BUSY;dirty=1;limit=timeout;current[0]='/';
 if(!ps_clock_poll()){fail(SS_CLOCK);return 1;}refresh(0);return 1;
}
void ss_cancel(void){
 if(state!=SS_BUSY)return;
 if(loading&&db_error()&&!error)error=SS_DIRECTORY;
 if(!error)error=SS_CANCEL;cancelled=1;
 if(loading)db_cancel();else fail(error);publish();
}
br_u8 ss_poll(void){
 br_u8 key,conflicts;
 if(state!=SS_BUSY){if(dirty){render();dirty=0;}publish();return state;}
 if(loading&&db_error()&&!error)error=SS_DIRECTORY;
 if(!ps_clock_poll()){if(!error)error=SS_CLOCK;ss_cancel();}
 if(ps_key_poll()&&ps_key==27)ss_cancel();
 else if(ps_key) {
  key=ps_key;
  if(!loading&&!cancelled){
   if(key==PS_LEFT){if(view){--view;dirty=1;}}
   else if(key==PS_RIGHT){if(view<381){++view;dirty=1;}}
   else if(key==PS_UP){if(row){--row;view=0;dirty=1;}}
   else if(key==PS_DOWN){br_u8 count=stage==5?2:(stage==6?5:db_page->count);if(row+1<count){++row;view=0;dirty=1;}}
   else if(stage<5){
    if(key==8&&db_parent()){memcpy(current,db_selected_path,128);refresh(0);}
    else if(key==PS_F1&&stage==0){
     conflicts=db_output_conflicts(current);
     if(conflicts==DB_CONFLICT_UNKNOWN)text(23,0,"Folder check failed; reopen this folder.");
     else if(conflicts)text(23,0,"Files exist; choose another home folder.");
     else if(current[1]&&strlen(current)<=SS_HOME_MAX){memcpy(choices.home,current,128);next_stage();}
     else text(23,0,"Choose a folder with room for filenames.");
    }else if(key==PS_F1&&stage==4)next_stage();
    else if(key==PS_F1+2&&db_page->previous)refresh(db_page->first-DB_ROWS);
    else if(key==PS_F1+4&&db_page->next)refresh(db_page->first+DB_ROWS);
    else if(key==13)choose();
   }else if(key==13){if(stage==5){choices.profile=row;next_stage();}else{state=SS_DONE;dirty=1;}}
  }
 }
 if(loading){db_now=ps_ticks;db_poll();if(db_state()!=DB_BUSY){loading=0;dirty=1;if(cancelled)fail(error);else if(db_state()!=DB_DONE)fail(SS_DIRECTORY);}}
 if(dirty){render();dirty=0;}publish();return state;
}

br_u8 ss_state(void){publish();return state;}

br_u8 ss_error_code(void){return error;}

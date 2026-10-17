#include "panel.h"
#include <string.h>
struct mu_view_t mu_view;
struct mu_event_t mu_event;
struct mu_result_t mu_result;
ps_u16 mu_reply_ticket;
ps_u8 mu_reply_error,mu_reply_safe,mu_block_error;
static struct mu_view_t view;
static struct mu_event_t intent;
static ps_u8 mode,drive,action,error,queued,delivered,after,finish_scan,finish_discard,cancelled;
static ps_u8 blocked;
static ps_u8 path_action,path_len,path_cursor,discard;
static ps_u16 path_scroll,view_scroll;
static char path[128],incoming[128];
static ps_u16 ticket;
static ps_u8 limit(const char*p,ps_u8 n){ps_u8 i;for(i=0;i<n;++i)if(!p[i])return i;return n;}
static void observed(void){mu_result.mode=mode;mu_result.drive=drive;mu_result.action=action;mu_result.error=error;mu_result.ticket=ticket;}
static void cell(ps_u8 row,ps_u8 col,ps_u8 c){ps_row=row;ps_col=col;ps_ascii=c;ps_put();}
static void text(ps_u8 row,ps_u8 col,const char*s){while(*s&&col<40u)cell(row,col++,*s++);}
static ps_u8 hex(ps_u8 n){return n<10u?'0'+n:'A'+n-10u;}
static ps_u8 plain(ps_u8 c){return c>=32u&&c<=126u&&c!='%'&&c!='\\'&&c!='|'&&c!='{'&&c!='}'&&c!='~'&&c!='^'&&c!='`'&&c!='_';}
static ps_u16 encoded(const char*s,ps_u8 count){ps_u8 i;ps_u16 n=0;for(i=0;i<count&&s[i];++i)n+=plain(s[i])?1u:3u;return n;}
static void safe_text(ps_u8 row,const char*s,ps_u16 offset){ps_u8 raw=0,col=0,c,part,n=limit(s,128);while(raw<n&&col<40u){c=s[raw++];if(plain(c)){if(offset)--offset;else cell(row,col++,c);}else for(part=0;part<3u&&col<40u;++part){if(offset)--offset;else cell(row,col++,part==0?'%':hex(part==1?c>>4:c&15));}}}
static void scroll_path(void){ps_u16 pos=encoded(path,path_cursor);if(pos<path_scroll)path_scroll=pos;if(pos-path_scroll>=40u)path_scroll=pos-39u;}
static void render(void){ps_color=1;ps_clear();text(0,0,"DOS64 DISK CONTROLS");text(1,0,"DOS is paused");cell(3,0,drive?' ':'>');text(3,2,"A:");cell(4,0,drive?'>' :' ');text(4,2,"B:");
 text(3,5,view.drive[0].flags&MU_PRESENT?"mounted":"empty");text(4,5,view.drive[1].flags&MU_PRESENT?"mounted":"empty");
 if(view.drive[drive].flags&MU_PRESENT){text(6,0,view.drive[drive].flags&MU_READONLY?"Read only":"Writable");text(6,12,view.drive[drive].flags&MU_UNCERTAIN?"Save uncertain":(view.drive[drive].flags&MU_DIRTY?"Modified":"Saved"));}else text(6,0,"No floppy inserted");safe_text(7,view.drive[drive].path,view_scroll);safe_text(8,view.drive[drive].path,view_scroll+40u);if(mode==MU_MENU&&encoded(view.drive[drive].path,127)>80u)text(9,0,"Left/right View full path");
 if(mode==MU_MENU){text(11,0,"A/B Select drive    S Save");text(12,0,"N Save as           I Insert/change");text(13,0,"E Eject             W Write protect");text(15,0,"R Resume DOS        F Finish session");text(18,0,"Save copies the complete floppy image.");text(19,0,"Finish flushes and closes C safely.");}
 else if(mode==MU_CONFIRM){text(11,0,"This floppy has unsaved changes.");text(13,0,"S Save first        D Discard changes");text(15,0,"C Cancel");}
 else if(mode==MU_PATH){text(10,0,path_action==MU_INSERT?"Image path to insert:":"New image path to save:");safe_text(12,path,path_scroll);text(15,0,"Return Accept       Run/Stop Cancel");text(16,0,"Left/right Move     Delete Backspace");text(18,0,"Absolute path, maximum127 characters.");cell(13,encoded(path,path_cursor)-path_scroll,'^');}
 else if(mode==MU_WAIT){text(11,0,"Working...");text(12,0,view.operation);text(15,0,"Run/Stop Request cancel");text(18,0,"Keep power on until completion.");}
 else if(mode==MU_ERROR){text(11,0,blocked?"Session blocked; cannot resume.":"Operation did not complete.");text(12,0,view.operation);text(14,0,"Error code:");cell(14,12,hex(error>>4));cell(14,13,hex(error&15));text(16,0,"Working floppy remains in memory.");text(18,0,view.can_resume?"Return Back to disk controls":"Closure unconfirmed; keep this screen.");}
 else if(mode==MU_SAFE){text(11,0,"Files are closed.");text(13,0,"It is safe to restart the C64.");}
 observed();}
void mu_refresh(void){ps_u8 i;view_scroll=0;for(i=0;i<2u;++i){view.drive[i].flags=mu_view.drive[i].flags&15u;memcpy(view.drive[i].path,mu_view.drive[i].path,128);view.drive[i].path[127]=0;}view.can_resume=!blocked&&mu_view.can_resume?1u:0u;view.percent=mu_view.percent>100u?100u:mu_view.percent;memcpy(view.operation,mu_view.operation,40);view.operation[39]=0;render();}
static void emit(ps_u8 op,ps_u8 flags,const char*p){if(blocked||queued||delivered)return;if(ticket==65535u){mode=MU_ERROR;error=255;render();return;}++ticket;cancelled=0;memset(&intent,0,sizeof(intent));intent.ticket=ticket;intent.action=op;intent.drive=drive;intent.flags=flags;if(p)memcpy(intent.path,p,128);action=op;queued=1;mode=MU_WAIT;error=0;render();}
static void ask_path(ps_u8 op){ps_u8 i,last=0;path_action=op;memset(path,0,128);if(op==MU_SAVE_AS){for(i=0;i<127u&&view.drive[drive].path[i];++i)if(view.drive[drive].path[i]=='/')last=i+1u;if(last)memcpy(path,view.drive[drive].path,last);}path_len=path_cursor=last;path_scroll=0;scroll_path();mode=MU_PATH;render();}
static void next_finish(void){while(finish_scan<2u){drive=finish_scan++;if(view.drive[drive].flags&(MU_DIRTY|MU_UNCERTAIN)){after=MU_FINISH;mode=MU_CONFIRM;render();return;}}after=0;emit(MU_FINISH,finish_discard,0);}
static void request(ps_u8 op){after=0;discard=0;if(op==MU_RESUME){if(view.can_resume)emit(op,0,0);return;}if(op==MU_FINISH){finish_scan=finish_discard=0;next_finish();return;}if(op==MU_INSERT){ask_path(op);return;}if(!(view.drive[drive].flags&MU_PRESENT))return;if(op==MU_SAVE_AS){ask_path(op);return;}if(op==MU_SAVE){if(view.drive[drive].flags&MU_READONLY)ask_path(MU_SAVE_AS);else emit(op,0,0);return;}if(op==MU_EJECT&&(view.drive[drive].flags&(MU_DIRTY|MU_UNCERTAIN))){after=op;mode=MU_CONFIRM;render();return;}emit(op,0,0);}
void mu_init(void){blocked=0;mode=MU_MENU;drive=action=error=queued=delivered=after=finish_scan=finish_discard=discard=cancelled=0;ticket=0;view_scroll=path_scroll=0;ps_key_reset();memset(&intent,0,sizeof(intent));memset(path,0,128);memset(incoming,0,128);mu_refresh();}
void mu_block(void){if(!blocked){blocked=1;if(!error)error=mu_block_error?mu_block_error:254u;}view.can_resume=0;mode=MU_ERROR;render();}
ps_u8 mu_take(void){if(blocked||!queued||delivered){observed();return 0;}mu_event=intent;queued=0;delivered=1;observed();return 1;}
ps_u8 mu_cancel_requested(void){return !blocked&&mode==MU_WAIT&&delivered&&cancelled;}
ps_u8 mu_reply(void){ps_u8 previous;if(blocked||mode!=MU_WAIT||!delivered||mu_reply_ticket!=intent.ticket)return 0;previous=action;delivered=cancelled=0;if(mu_reply_error){error=mu_reply_error;mode=MU_ERROR;after=0;render();return 1;}if(previous==MU_FINISH){if(!mu_reply_safe){mode=MU_ERROR;error=254;view.can_resume=0;}else mode=MU_SAFE;render();return 1;}if(previous==MU_CANCEL){mode=MU_MENU;after=0;render();return 1;}if(after==MU_FINISH){next_finish();return 1;}if(after==MU_EJECT){after=0;emit(MU_EJECT,0,0);return 1;}if(after==MU_INSERT){after=0;emit(MU_INSERT,discard,incoming);return 1;}mode=MU_MENU;render();return 1;}
static void path_key(ps_u8 c){ps_u8 i;if(c==27u){mode=MU_MENU;after=0;render();return;}if(c==13u){if(!path_len||path[0]!='/')return;if(path_action==MU_INSERT){memcpy(incoming,path,128);if(view.drive[drive].flags&(MU_DIRTY|MU_UNCERTAIN)){after=MU_INSERT;mode=MU_CONFIRM;render();}else emit(MU_INSERT,0,incoming);}else emit(MU_SAVE_AS,0,path);return;}if(c==PS_LEFT){if(path_cursor)--path_cursor;}else if(c==PS_RIGHT){if(path_cursor<path_len)++path_cursor;}else if(c==8u){if(path_cursor){for(i=path_cursor-1u;i<path_len;++i)path[i]=path[i+1u];--path_cursor;--path_len;}}else if(c==PS_DELETE){if(path_cursor<path_len){for(i=path_cursor;i<path_len;++i)path[i]=path[i+1u];--path_len;}}else if(c>=32u&&c<=126u&&path_len<127u){for(i=path_len+1u;i>path_cursor;--i)path[i]=path[i-1u];path[path_cursor++]=c;++path_len;}scroll_path();render();}
void mu_poll(void){ps_u8 c;if(!ps_key_poll())return;if(blocked){observed();return;}c=ps_key;if(c>='A'&&c<='Z')c+=32;if(mode==MU_PATH){/* Preserve original case of path bytes. */path_key(ps_key);return;}if(mode==MU_WAIT){if(c==27u){if(queued){queued=0;after=0;mode=MU_MENU;render();}else if(delivered){cancelled=1;mu_result.action=MU_CANCEL;}}return;}if(mode==MU_SAFE)return;if(mode==MU_ERROR){if(c==13u&&view.can_resume){mode=MU_MENU;render();}return;}if(mode==MU_CONFIRM){if(c=='c'||c==27u){mode=MU_MENU;after=0;render();return;}if(c=='d'){if(after==MU_FINISH){finish_discard|=(1u<<drive);next_finish();return;}c=after;after=0;emit(c,MU_DISCARD,c==MU_INSERT?incoming:0);return;}if(c=='s'){if(view.drive[drive].flags&MU_READONLY)ask_path(MU_SAVE_AS);else emit(MU_SAVE,0,0);}return;}if(c==PS_LEFT||c==PS_RIGHT){if(c==PS_LEFT)view_scroll=view_scroll>=40u?view_scroll-40u:0;else if(view_scroll+80u<encoded(view.drive[drive].path,127))view_scroll+=40u;render();return;}if(c=='a'||c=='b'){drive=c=='b';view_scroll=0;render();return;}if(c=='s')request(MU_SAVE);else if(c=='n')request(MU_SAVE_AS);else if(c=='i')request(MU_INSERT);else if(c=='e')request(MU_EJECT);else if(c=='w')request(MU_PROTECT);else if(c=='r')request(MU_RESUME);else if(c=='f')request(MU_FINISH);}

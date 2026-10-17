#include "directory_browser.h"
#include "bulk_uci.h"
#include "install_config.h"
#include <string.h>

struct db_request_t db_request;
struct db_result_t db_result;
static struct db_result_t result;
br_u16 db_now;
char db_selected_path[128];
static struct db_page_t committed,prepared;
const struct db_page_t * const db_page=&committed;
static struct db_request_t q;
static br_u16 began,last_now,matched;
static br_u8 phase,seen,final_seen,aborted,empty_directory,path_length;
static br_u8 output_seen,output_committed;

static void first(br_u8 error){if(!result.error)result.error=error;}
static br_u8 status(const char *text,br_u8 n){
 br_u8 i;if(uci_status_len!=n)return 0;
 for(i=0;i<n;i++)if(uci_status[i]!=(br_u8)text[i])return 0;
 return 1;
}
static void abort_job(br_u8 error){
 first(error);if(!aborted){aborted=1;uci_now=db_now;uci_abort();}
}
static void terminal(br_u8 success){
 result.recovery_failed=uci_recovery_failed;
 if(result.lease){
  if(db_lease_release())result.lease=0;
  else {first(DB_TRANSPORT);success=0;}
 }
 if(success&&!result.error){
  if(q.first&&q.first>=matched)first(DB_RANGE);
  else {
   prepared.total=matched;prepared.scanned=result.scanned;
   prepared.previous=q.first!=0;prepared.next=matched>q.first+prepared.count;
   prepared.generation=committed.generation+1U;prepared.valid=0xa5;
   committed=prepared;output_committed=output_seen;
  }
 }
 result.state=result.error?DB_FAILED:DB_DONE;
}
static br_u8 canonical_request(void){
 br_u16 i; br_u8 n;
 if(db_request.owner!=0xa5||(db_request.target!=1&&db_request.target!=2)||
    db_request.folders_only>1||db_request.first>=DB_MAX_ENTRIES||
    !db_request.timeout||db_request.timeout>=0x8000U)return 0;
 memcpy(d64_path_source,db_request.path,128);
 if(!d64_path_parent())return 0;
 n=(br_u8)strlen(db_request.path);
 for(i=(br_u16)n+1U;i<128;i++)if(db_request.path[i])return 0;
 path_length=n;return 1;
}
static void command(br_u8 opcode){
 uci_command[0]=q.target;uci_command[1]=opcode;uci_command_len=2;
 if(opcode==0x11){memcpy(uci_command+2,q.path,path_length);uci_command_len+=path_length;}
 uci_data_capacity=512;uci_status_capacity=80;uci_now=db_now;seen=final_seen=0;
 if(uci_start()){result.transport=uci_error;first(DB_TRANSPORT);terminal(0);}
}
static br_u8 begin_job(void){
 result.rejected=DB_INPUT;
 if(result.state==DB_BUSY||result.lease||!canonical_request())return 0;
 if(!db_lease_acquire()){result.rejected=DB_LEASE;return 0;}
 q=db_request;memset(&prepared,0,sizeof(prepared));memcpy(prepared.path,q.path,128);prepared.first=q.first;
 result.state=DB_BUSY;result.error=result.transport=result.rejected=result.recovery_failed=0;
 result.lease=1;result.blocks=result.scanned=matched=0;
 began=last_now=db_now;phase=1;aborted=empty_directory=output_seen=0;command(0x11);return 1;
}
static br_u8 name_usable(const br_u8 *name,br_u16 length,br_u8 attr,const char *path){
 br_u16 i,n;
 if(!length||length>127||(attr&0xc8u)||attr==0x0fu)return 0;
 if(name[length-1]==' '||name[length-1]=='.')return 0;
 if((length==1&&name[0]=='.')||(length==2&&name[0]=='.'&&name[1]=='.'))return 0;
 for(i=0;i<length;i++){
  n=name[i];if(n<32||n>126||n=='/'||n=='\\'||n==':'||n=='"'||n=='*'||n=='<'||n=='>'||n=='?'||n=='|')return 0;
 }
 n=(br_u16)strlen(path);if(n!=1)n++;
 return n+length<128U;
}
/* Check every raw entry, before page selection or folders-only filtering.
 * This advisory scan cannot resolve FatFs aliases or prevent later changes;
 * CREATE_NEW is still mandatory at publication. Directories also conflict. */
static void output_name(const br_u8 *name,br_u16 length){
 static const char * const names[]={"A.IMG","B.IMG","C.IMG","START.PRG","DOS64.CFG"};
 br_u8 i,j,c;
 for(i=0;i<5;i++){
  if(length!=strlen(names[i]))continue;
  for(j=0;j<length;j++){
   c=name[j];if(c>='a'&&c<='z')c-=32;
   if(c!=(br_u8)names[i][j])break;
  }
  if(j==length)output_seen|=(br_u8)(1u<<i);
 }
}
static void row_record(void){
 struct db_row_t *row;br_u16 length,i; br_u8 attr,more;
 more=(uci_last_status&0x10)!=0;
 if(uci_flags||uci_data_len<2||uci_data_len>512){abort_job(DB_PROTOCOL);return;}
 if((more&&uci_status_len)||(!more&&!status("00,OK",5))){abort_job(DB_STATUS);return;}
 if(result.scanned>=DB_MAX_ENTRIES){abort_job(DB_LIMIT);return;}
 ++result.scanned;if(more&&result.scanned==DB_MAX_ENTRIES){abort_job(DB_LIMIT);return;}
 attr=uci_data[0];length=uci_data_len-1;output_name(uci_data+1,length);
 if(!q.folders_only||(attr&0x10)){
  if(matched>=q.first&&prepared.count<DB_ROWS){
   row=&prepared.rows[prepared.count++];row->raw_length=length;row->attr=attr;
   if(length<=127){memcpy(row->raw,uci_data+1,length);row->raw[length]=0;}
   for(i=0;i<length&&i<39;i++)row->display[i]=(uci_data[i+1]>=32&&uci_data[i+1]<=126)?uci_data[i+1]:'?';
   row->display_cut=length>39;row->usable=name_usable(uci_data+1,length,attr,q.path);
  }
  ++matched;
 }
 if(!more)final_seen=1;
}
static void poll_job(void){
 br_u16 elapsed;
 if(result.state!=DB_BUSY)return;
 elapsed=db_now-last_now;last_now=db_now;uci_now=db_now;
 if(elapsed>=0x8000U||(br_u16)(db_now-began)>=q.timeout)abort_job(DB_TIMEOUT);
 uci_poll();
 if(uci_state==8&&uci_error){result.transport=uci_error;first(DB_TRANSPORT);}
 if(uci_state==BR_UCI_BLOCK){
  ++result.blocks;
  if(phase==3)row_record();
  else {
   if(seen||uci_flags||uci_data_len||(uci_last_status&0x10))abort_job(DB_PROTOCOL);
   else if(phase==2&&status("01,DIRECTORY EMPTY",18))empty_directory=1;
   else if(!status("00,OK",5))abort_job(DB_STATUS);
   seen=1;
  }
  if(!result.error)uci_accept();
  return;
 }
 if(uci_state==BR_UCI_FAILED){result.transport=uci_error;first(DB_TRANSPORT);terminal(0);return;}
 if(uci_state!=BR_UCI_DONE)return;
 if(result.error){terminal(0);return;}
 if(phase==3){if(!final_seen)first(DB_PROTOCOL);terminal(!result.error);}
 else if(!seen){first(DB_PROTOCOL);terminal(0);}
 else if(phase==1){phase=2;command(0x13);}
 else if(empty_directory)terminal(1);
 else {phase=3;command(0x14);}
}
static void cancel_job(void){if(result.state==DB_BUSY)abort_job(DB_CANCEL);}
br_u8 db_select(br_u8 index){
 const struct db_row_t *row;br_u16 i;
 db_result=result;
 if(committed.valid!=0xa5||index>=committed.count)return 0;
 row=&committed.rows[index];
 if(!row->usable||!name_usable(row->raw,row->raw_length,row->attr,committed.path))return 0;
 for(i=row->raw_length;i<128;i++)if(row->raw[i])return 0;
 memcpy(d64_path_source,committed.path,128);memcpy(d64_path_relative,row->raw,128);
 if(!d64_path_join())return 0;
 memcpy(db_selected_path,d64_path_output,128);return 1;
}
br_u8 db_parent(void){
 db_result=result;
 if(committed.valid!=0xa5)return 0;
 memcpy(d64_path_source,committed.path,128);if(!d64_path_parent())return 0;
 memcpy(db_selected_path,d64_path_output,128);return 1;
}
const br_u16 db_abi_sizes[]={sizeof(struct db_request_t),sizeof(struct db_result_t),sizeof(struct db_row_t),sizeof(struct db_page_t)};

/* The public result is an observation, never a state/lease/error authority.
 * Restore it even on rejected starts, idle polls and getter-only calls. */
br_u8 db_begin(void){
 br_u8 accepted;db_result=result;accepted=begin_job();db_result=result;return accepted;
}
void db_poll(void){db_result=result;poll_job();db_result=result;}
void db_cancel(void){db_result=result;cancel_job();db_result=result;}
br_u8 db_state(void){db_result=result;return result.state;}
br_u8 db_error(void){db_result=result;return result.error;}

/* The public page/result/request are observations, not scan authority. The
 * caller supplies a complete canonical128-byte path. No transport is polled. */
br_u8 __fastcall__ db_output_conflicts(const char *path){
 if(result.state!=DB_DONE||result.error||result.lease||memcmp(path,q.path,128))return DB_CONFLICT_UNKNOWN;
 return output_committed;
}

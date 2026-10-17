#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
#include "uci_model.h"
struct HdFileModel {
 std::vector<uint8_t> source,floppy;
 std::vector<uint8_t> hd_path={'H','D','.','I','M','G'};
 bool on_floppy=false;uint8_t target=0;
 std::vector<std::vector<uint8_t>> history;
 struct Write {uint32_t offset,owner;uint8_t phase;std::vector<uint8_t> data;};
 std::vector<Write> writes;uint32_t owner=0xffffffff;uint8_t phase=0;
 uint32_t position=0;
 bool opened=false;uint8_t mode=0;
 bool aligned_dma_alias=false;uint32_t alias_hits=0;
 int fail_command=-1,short_offset=-1,partial_write=-1;
 bool prepare(UciModel &w,uint16_t a,uint8_t v){
  if(a!=w.base || !(v&1))return true;
  const auto &c=w.command;history.push_back(c);
  if(c.size()<2 || (c[0]!=1 && c[0]!=2)){w.fault=true;return false;}
  std::vector<uint8_t>d,s={'0','0',',','O','K'};
  if(int(history.size())==fail_command)s={'8','5',',','E','R','R'};
  else switch(c[1]){
   case 2:{
    if(opened||c.size()<5||c.back()!=0||(c[2]!=1&&c[2]!=3)){w.fault=true;return false;}
    std::vector<uint8_t> path(c.begin()+3,c.end()-1);
    const std::vector<uint8_t> fp={'d','i','s','k','.','i','m','g'};
    if(path==fp&&!floppy.empty()){if(c[2]!=1){w.fault=true;return false;}on_floppy=true;}
    else if(path==hd_path&&!source.empty())on_floppy=false;
    else{s={'8','2',',','F','I','L','E',' ','N','O','T',' ','F','O','U','N','D'};break;}
    opened=true;target=c[0];mode=c[2];position=0;break;}
   case 3:if(c.size()!=2){w.fault=true;return false;}if(!opened)s={'8','4',',','N','O',' ','F','I','L','E',' ','T','O',' ','C','L','O','S','E'};else if(c[0]!=target){w.fault=true;return false;}else opened=false;break;
   case 6:if(!opened||c[0]!=target||c.size()!=6){w.fault=true;return false;}position=uint32_t(c[2])|(uint32_t(c[3])<<8)|(uint32_t(c[4])<<16)|(uint32_t(c[5])<<24);break;
   case 4:{if(!opened||c[0]!=target||c.size()!=4){w.fault=true;return false;}size_t n=c[2]+256*c[3];
    if(!n||n>512){w.fault=true;return false;}auto &backing=on_floppy?floppy:source;size_t count=position<backing.size()?std::min(n,backing.size()-position):0;
    if(int(position)==short_offset&&count)--count;
    d.assign(backing.begin()+std::min(size_t(position),backing.size()),backing.begin()+std::min(size_t(position)+count,backing.size()));
    position+=count;s.clear();break;}
   case 5:{if(!opened||on_floppy||c[0]!=target||mode!=3||c.size()<4){w.fault=true;return false;}size_t n=c[2]+256*c[3];
    if(!n||n>512||c.size()!=n+4||position+n>source.size()){w.fault=true;return false;}
    writes.push_back({position,owner,phase,std::vector<uint8_t>(c.begin()+4,c.end())});
    size_t count=partial_write>=0?std::min(n,size_t(partial_write)):n;
    if(aligned_dma_alias&&position%512==0&&n==512){++alias_hits;for(size_t i=0;i<count;++i)source[position+i]=uint8_t((i*29)^(i>>3)^0x23);}
    else std::copy_n(c.begin()+4,count,source.begin()+position);
    position+=count;break;}
   default:w.fault=true;return false;
  }
  w.blocks.clear();w.blocks.push_back({d,s});return true;
 }
};
extern "C" {
#endif
void hd_model_source(void*,const uint8_t*,size_t);
void hd_model_dma_alias(void*,int);
uint32_t hd_model_alias_hits(void*);
void hd_model_floppy(void*,const uint8_t*,size_t);
void hd_model_path(void*,const uint8_t*,size_t);
uint32_t hd_model_count_op(void*,uint8_t);
uint8_t hd_model_handle_open(void*);
void hd_model_faults(void*,int,int,int);
uint32_t hd_model_commands(void*);
uint8_t hd_model_byte(void*,uint32_t);
uint32_t hd_model_reads_at(void*,uint32_t);
#ifdef __cplusplus
}
#endif

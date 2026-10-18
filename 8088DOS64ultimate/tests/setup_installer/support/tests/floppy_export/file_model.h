#pragma once
#include "uci_model.h"
// Independent in-memory file system layered over the existing FPGA wire model.
// Never reads exporter state, target RAM, or REU. Deliberate faults model silent
// short writes/status loss/corruption; no physical durability claim.
#ifdef __cplusplus
struct FloppyExportModel {
 std::vector<uint8_t> output, path;
 std::vector<std::vector<uint8_t>> history;
 bool exists=false, opened=false;
 uint8_t target=0,mode=0;
 size_t position=0;
 int fail_command=-1,partial_command=-1,corrupt_offset=-1,short_offset=-1;
 bool extra=false,bad_cleanup=false;
 // Opt-in platform hypothesis: full aligned WRITE wrongly DMA-aliases IO BRAM.
 // This model reproduces the observed corruption class, not installed RTL proof.
 bool aligned_dma_alias=false;uint32_t alias_hits=0;
 int64_t info_size=-1;int info_fault=0;
 bool prepare(UciModel &w,uint16_t address,uint8_t value) {
  if(address!=w.base || !(value&1))return true;
  const auto &c=w.command;history.push_back(c);
  std::vector<uint8_t>d,s={'0','0',',','O','K'};
  if(c.size()<2 || (c[0]!=1 && c[0]!=2)){w.fault=true;return false;}
  if(int(history.size())==fail_command) s={'8','5',',','E','R','R'};
  else switch(c[1]) {
   case 2:{
    if(opened || c.size()<5 || c.back()!=0 || (c[2]!=6 && c[2]!=1)){w.fault=true;return false;}
    std::vector<uint8_t> p(c.begin()+3,c.end()-1);
    if(c[2]==6) {
     if(exists){s={'6','3',',','E','X','I','S','T'};break;}
     exists=true;path=p;output.clear();
    } else if(!exists || p!=path){s={'8','2',',','F','I','L','E',' ','N','O','T',' ','F','O','U','N','D'};break;}
    opened=true;target=c[0];mode=c[2];position=0;break;
   }
   case 3:
    if(c.size()!=2){w.fault=true;return false;}
    if(bad_cleanup){s={'8','5',',','E','R','R'};break;}
    if(!opened){s={'8','4',',','N','O',' ','F','I','L','E',' ','T','O',' ','C','L','O','S','E'};break;}
    if(c[0]!=target){w.fault=true;return false;}
    if(mode==6 && extra)output.push_back(0x57);
    opened=false;break;
   case 5:{
    if(!opened || mode!=6 || c[0]!=target || c.size()<4){w.fault=true;return false;}
    size_t requested=c[2]+256*c[3];
    if((requested!=256 && requested!=512) || c.size()!=requested+4){w.fault=true;return false;}
    size_t n=int(history.size())==partial_command?17:requested;
    if(aligned_dma_alias && position%512==0 && requested==512) {
     ++alias_hits;
     for(size_t i=0;i<n;++i)output.push_back(uint8_t((i*29)^(i>>3)^0x23));
    } else output.insert(output.end(),c.begin()+4,c.begin()+4+n);
    position+=n;break;
   }
   case 7:{
    if(!opened || c[0]!=target || c.size()!=2){w.fault=true;return false;}
    uint32_t size=info_size<0?uint32_t(output.size()):uint32_t(info_size);
    d={uint8_t(size),uint8_t(size>>8),uint8_t(size>>16),uint8_t(size>>24),0,0,0,0,'I','M','G',0x20,'W','O','R','K','.','I','M','G'};
    switch(info_fault){
     case 1:d.clear();break;
     case 2:d.resize(12);break;
     case 3:d.resize(76,'Q');break;
     case 4:d[11]=0x10;break;
     case 5:d[11]=8;break;
     case 6:d[14]=0;break;
     case 7:s.clear();break;
     case 8:s={'8','5',',','E','R','R'};break;
     case 9:break;
     case 10:d.resize(75,'Q');break;
     case 11:d.resize(13,'Q');break;
     case 12:d.clear();s={'8','5',',','E','R','R'};break;
     case 13:d.clear();s.clear();break;
    }
    break;
   }
   case 4:{
    if(!opened || mode!=1 || c[0]!=target || c.size()!=4){w.fault=true;return false;}
    size_t n=c[2]+256*c[3];if(n!=512 && n!=1){w.fault=true;return false;}
    size_t count=position<output.size()?std::min(n,output.size()-position):0;
    if(int(position)==short_offset && count)--count;
    d.assign(output.begin()+std::min(position,output.size()),output.begin()+std::min(position+count,output.size()));
    if(corrupt_offset>=int(position) && corrupt_offset<int(position+count))d[corrupt_offset-position]^=0x80;
    position+=count;s.clear();break;
   }
   default:w.fault=true;return false;
  }
  w.blocks.clear();w.blocks.push_back({d,s});if(c[1]==7 && info_fault==9)w.blocks.push_back({{}, {}});return true;
 }
};
extern "C" {
#endif
void export_model_enable(void*,int);
void export_model_dma_alias(void*,int);
uint32_t export_model_alias_hits(void*);
uint32_t export_model_write_size(void*,uint32_t);
void export_model_info(void*,int64_t,int);
void export_model_faults(void*,int,int,int,int,int,int);
uint32_t export_model_size(void*);
uint8_t export_model_byte(void*,uint32_t);
uint32_t export_model_count(void*,uint8_t);
uint8_t export_model_open(void*);
#ifdef __cplusplus
}
#endif

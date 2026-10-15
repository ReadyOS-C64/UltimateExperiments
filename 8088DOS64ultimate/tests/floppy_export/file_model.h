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
    if(!opened || mode!=6 || c[0]!=target || c.size()!=516 || c[2]!=0 || c[3]!=2){w.fault=true;return false;}
    size_t n=int(history.size())==partial_command?17:512;
    output.insert(output.end(),c.begin()+4,c.begin()+4+n);position+=n;break;
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
  w.blocks.clear();w.blocks.push_back({d,s});return true;
 }
};
extern "C" {
#endif
void export_model_enable(void*,int);
void export_model_faults(void*,int,int,int,int,int,int);
uint32_t export_model_size(void*);
uint8_t export_model_byte(void*,uint32_t);
uint32_t export_model_count(void*,uint8_t);
uint8_t export_model_open(void*);
#ifdef __cplusplus
}
#endif

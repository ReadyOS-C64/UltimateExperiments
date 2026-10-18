#pragma once
#ifdef __cplusplus
#include "uci_model.h"
// Independent single-read-only-file source atop the separately modeled FPGA
// register protocol. Never consults importer state or changes target RAM/REU.
struct ImageImportModel {
 std::vector<uint8_t> source;
 std::vector<std::vector<uint8_t>> history;
 std::vector<uint8_t> path;
 size_t position=0;
 bool opened=false;
 int fail_command=-1, corrupt_at=-1, short_at=-1;
 bool bad_close=false;
 bool prepare(UciModel &wire,uint16_t a,uint8_t v) {
  if (a==wire.base && (v&1)) {
   const auto &command=wire.command;
   history.push_back(command);
   std::vector<uint8_t> data, status={'0','0',',','O','K'};
   if(command.size()<2 || command[0]!=1) {wire.fault=true;return false;}
   if (int(history.size())==fail_command) status={'8','5',',','E','R','R'};
   else switch(command[1]) {
    case 2:
     if(opened || command.size()!=path.size()+4 || command[2]!=1 || command.back()!=0 || !std::equal(path.begin(),path.end(),command.begin()+3)) {wire.fault=true;return false;}
     opened=true;position=0;break;
    case 4: {
     if(!opened || command.size()!=4) {wire.fault=true;return false;}
     size_t count=command[2]+256*command[3];
     if(count!=512 && count!=1) {wire.fault=true;return false;}
     size_t end=std::min(source.size(),position+count);
     if(int(position)==short_at && end>position) --end;
     data.assign(source.begin()+position,source.begin()+end);
     if(corrupt_at>=int(position) && corrupt_at<int(end)) data[corrupt_at-position]^=0x80;
     position=end;status.clear();break;
    }
    case 3:
     if(command.size()!=2) {wire.fault=true;return false;}
     if(bad_close) status={'8','5',',','E','R','R'};
     else if (!opened) status={'8','4',',','N','O',' ','F','I','L','E',' ','T','O',' ','C','L','O','S','E'};
     else opened=false;
     break;
    default:wire.fault=true;return false;
   }
   wire.blocks.clear();wire.blocks.push_back({data,status});
  }
  return true;
 }
};
#endif
#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>
#include <stddef.h>
void import_model_source(void*,const uint8_t*,size_t);
void import_model_faults(void*,int,int,int,int);
uint32_t import_model_commands(void*);
uint32_t import_model_position(void*);
uint8_t import_model_open(void*);
#ifdef __cplusplus
}
#endif

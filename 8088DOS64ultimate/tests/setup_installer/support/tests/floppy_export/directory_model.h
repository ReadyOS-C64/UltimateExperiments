#pragma once
#include "uci_model.h"
#include <map>
#include <string>
/* Wire oracle derived from pinned830665cd dos.cc: cd responseempty/00,
 * OPEN_DIR empty/00 or exact01,DIRECTORY EMPTY, READ_DIR one attrib+strlen
 * filename perblock (NO transmitted NUL), intermediate empty status/final00.
 * Consumes only actual UCI command bytes, never browser/page/C globals. */
struct DirectoryModel{
 struct Row{uint8_t attr;std::vector<uint8_t> name;};
 std::map<std::string,std::vector<Row>> dirs;
 std::string cwd[3]={"/","/","/"};
 std::vector<std::vector<uint8_t>> history;
 int fault_op=0,fault_index=-1,fault_kind=0;
 bool owns(const UciModel&w,uint16_t a,uint8_t v)const{return a==w.base&&(v&1)&&w.command.size()>=2&&(w.command[1]==0x11||w.command[1]==0x13||w.command[1]==0x14);}
 bool prepare(UciModel&w){
  auto c=w.command;history.push_back(c);if(c[0]<1||c[0]>2){w.fault=true;return false;}
  const std::vector<uint8_t> ok={'0','0',',','O','K'};std::vector<UciModel::Block> blocks;
  if(c[1]==0x11){
   if(c.size()<3||std::find(c.begin()+2,c.end(),0)!=c.end()){w.fault=true;return false;}
   std::string path(c.begin()+2,c.end());if(!dirs.contains(path))blocks.push_back({{}, {'8','3',',','N','O',' ','S','U','C','H',' ','D','I','R','E','C','T','O','R','Y'}});
   else {cwd[c[0]]=path;blocks.push_back({{},ok});}
  }else if(c.size()!=2){w.fault=true;return false;}
  else if(c[1]==0x13){if(dirs[cwd[c[0]]].empty())blocks.push_back({{}, {'0','1',',','D','I','R','E','C','T','O','R','Y',' ','E','M','P','T','Y'}});else blocks.push_back({{},ok});}
  else {
   const auto&rows=dirs[cwd[c[0]]];
   if(rows.empty())blocks.push_back({{}, {'8','7',',','I','N','T','E','R','N','A','L',' ','E','R','R','O','R'}});
   for(size_t i=0;i<rows.size();i++){std::vector<uint8_t>data={rows[i].attr};data.insert(data.end(),rows[i].name.begin(),rows[i].name.end());blocks.push_back({data,i+1==rows.size()?ok:std::vector<uint8_t>{}});}
  }
  if(c[1]==fault_op){size_t at=fault_index<0?0:size_t(fault_index);if(at<blocks.size())switch(fault_kind){
   case 1:blocks[at].status={'8','6',',','C','A','N','T',' ','R','E','A','D'};break;
   case 2:blocks[at].data.resize(513,'X');break;
   case 3:blocks[at].status=ok;break;
   case 4:blocks[at].data.clear();break;
   case 5:blocks[at].status={'0','1',',','D','I','R','E','C','T','O','R','Y',' ','E','M','P','T','Y'};break;
   case 6:blocks[at].status.push_back(0);break;
   case 7:blocks.push_back({{0x20,'X'},ok});break;
  }}
  w.blocks=std::move(blocks);return true;
 }
};
extern "C"{
void dir_model_enable(void*);
void dir_model_path(void*,const char*);
void dir_model_row(void*,const char*,uint8_t,const uint8_t*,uint32_t);
void dir_model_fault(void*,int,int,int);
uint32_t dir_model_commands(void*);
uint32_t dir_model_cmd_size(void*,uint32_t);
uint8_t dir_model_cmd_byte(void*,uint32_t,uint32_t);
}

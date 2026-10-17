#pragma once
#include "uci_model.h"
#include "reu_model.h"
#include <map>
#include <string>
#include <cstdio>
// Independent firmware-file/REU model: consumes only actual captured wire
// commands and modeled REU bytes, never C coordinator/diagnostic state.
struct BulkModel {
 struct Handle {bool open=false;uint8_t mode=0;size_t pos=0;std::string name;};
 Handle handles[3];std::map<std::string,std::vector<uint8_t>> files;
 std::vector<std::vector<uint8_t>> history;
 int fail_at=-1,short_at=-1,reply_at=-1,reply_fault=0,corrupt_at=-1;
 static uint32_t le(const std::vector<uint8_t>&c,size_t at){return uint32_t(c[at])|(uint32_t(c[at+1])<<8)|(uint32_t(c[at+2])<<16)|(uint32_t(c[at+3])<<24);}
 bool prepare(UciModel &w,ReuModel *r,uint16_t a,uint8_t v) {
  if(a!=w.base||!(v&1))return true;
  const auto c=w.command;history.push_back(c);std::vector<uint8_t>d,s={'0','0',',','O','K'};
  if(c.size()<2||c[0]<1||c[0]>2){w.fault=true;return false;}auto &h=handles[c[0]];
  auto error=[&](){s={'8','5',',','E','R','R'};};
  if(int(history.size())==fail_at)error();else switch(c[1]){
   case 2:{if(h.open||c.size()<5||c.back()!=0){w.fault=true;return false;}
    std::string path(c.begin()+3,c.end()-1);if(c[2]&4){if(files.contains(path)){error();break;}files[path]={};}
    if(!files.contains(path)){error();break;}h={true,c[2],0,path};break;}
   case 3:if(!h.open){s={'8','4',',','N','O',' ','F','I','L','E',' ','T','O',' ','C','L','O','S','E'};}else h.open=false;break;
   case 6:if(!h.open||c.size()!=6){w.fault=true;return false;}h.pos=le(c,2);if(!(h.mode&2))h.pos=std::min(h.pos,files[h.name].size());else if(h.pos>files[h.name].size()){if(h.pos>0x2000000){error();break;}files[h.name].resize(h.pos,0xcc);}break;
   case 7:{if(!h.open||c.size()!=2){w.fault=true;return false;}auto n=files[h.name].size();d={uint8_t(n),uint8_t(n>>8),uint8_t(n>>16),uint8_t(n>>24),0,0,0,0,'B','I','N',0x20,'B','U','L','K','.','B','I','N'};break;}
   // Test-only generic READ04 matches independent HdFileModel/firmware:
   // little-endian requested count, data-only response, bounded sector read.
   case 4:{if(!h.open||!(h.mode&1)||c.size()!=4){error();break;}
    size_t n=size_t(c[2])|(size_t(c[3])<<8);if(!n||n>512){w.fault=true;return false;}
    auto &file=files[h.name];n=h.pos<file.size()?std::min<size_t>(n,file.size()-h.pos):0;
    if(int(history.size())==short_at&&n)--n;
    d.assign(file.begin()+std::min<size_t>(h.pos,file.size()),file.begin()+std::min<size_t>(h.pos+n,file.size()));h.pos+=n;s.clear();break;}
   case 0x21:case 0x22:{
    if(!r||!h.open||c.size()!=10){w.fault=true;return false;}
    uint32_t addr=le(c,2),n=le(c,6);if(addr>=r->bytes.size()||n>r->bytes.size()-addr){w.fault=true;return false;}
    if(!(h.mode&(c[1]==0x21?1:2))){error();break;}
    auto &file=files[h.name];if(c[1]==0x21)n=h.pos<file.size()?std::min<size_t>(n,file.size()-h.pos):0;
    if(int(history.size())==short_at&&n)--n;
    if(c[1]==0x22){if(h.pos+n>0x2000000){error();break;}if(file.size()<h.pos+n)file.resize(h.pos+n,0xcc);std::copy_n(r->bytes.begin()+addr,n,file.begin()+h.pos);}
    else {if(corrupt_at!=-2)std::copy_n(file.begin()+std::min(h.pos,file.size()),n,r->bytes.begin()+addr);if(corrupt_at>=0&&uint32_t(corrupt_at)<n)r->bytes[addr+corrupt_at]^=0x80;}
    h.pos+=n;char msg[80];std::snprintf(msg,sizeof msg,c[1]==0x21?"$%6X BYTES LOADED TO REU $%6X":"$%6X BYTES SAVED FROM REU $%6X",n,addr);d.assign(msg,msg+std::char_traits<char>::length(msg));break;}
   default:w.fault=true;return false;
  }
  bool more=false;
  if(int(history.size())==reply_at){switch(reply_fault){case 1:s={};break;case 2:s={'0','2',',','R','E','Q','U','E','S','T',' ','T','R','U','N','C','A','T','E','D'};break;case 3:if(d.size()>6)d[6]='g';break;case 4:if(d.size())d.back()=d.back()=='0'?'1':'0';break;case 5:d.push_back('X');break;case 6:more=true;break;case 7:if(d.size()>14)d[14]='X';break;case 8:if(d.size()>6)d[1]='f';break;case 9:if(d.size()>6)d[6]=0;break;case 10:case 11:for(size_t j=0;j<d.size();++j)if((j>=1&&j<=6)||j+6>=d.size())if(d[j]>='A'&&d[j]<='F'&&(reply_fault==10||(j&1)))d[j]+=32;break;}}
  w.blocks.clear();w.blocks.push_back({d,s});if(more)w.blocks.push_back({{}, {}});return true;
 }
};
extern "C" {
void bulk_model_enable(void*);
void bulk_model_faults(void*,int,int,int,int,int);
uint32_t bulk_model_commands(void*);
uint8_t bulk_model_command(void*,uint32_t,uint32_t);
uint32_t bulk_model_size(void*,const char*);
uint8_t bulk_model_open(void*,uint8_t);
uint8_t bulk_model_read(void*,const char*,uint8_t*,uint32_t);
void bulk_model_seed(void*,const char*,const uint8_t*,uint32_t);
void bulk_reu_seed(void*,uint32_t,const uint8_t*,uint32_t);
}

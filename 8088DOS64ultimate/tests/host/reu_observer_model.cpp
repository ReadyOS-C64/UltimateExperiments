// Synthetic device fault model, not a claim about installed FPGA behavior.
#include "Peddle.h"
#include "reu_model.h"
#include <array>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <cassert>
class Machine:public peddle::Peddle {
public:
 std::array<uint8_t,65536> ram{},written{};ReuModel reu;int delay=0,remaining=-1,override_first=-1,override_completion=-1;bool consume_override=false,active=false,first=true;unsigned commands=0,status_reads=0;uint8_t command=0;
 Machine(){setModel(peddle::MOS_6510);reset();reg.pport.direction=0x2f;reg.pport.data=0x37;}
 void begin(const std::vector<uint8_t>&code){std::copy(code.begin(),code.end(),ram.begin()+0x800);reg.pc=reg.pc0=0x800;next=peddle::fetch;reg.sp=0xfd;reg.a=0x18;reg.x=0x42;reg.y=0x93;setP(0x28);ram[0x1fe]=0xff;ram[0x1ff]=1;std::array<uint8_t,10> request={0,0xc0,0,0,0x34,16,0,1,0xee,0xee};std::copy(request.begin(),request.end(),ram.begin()+0xe000);for(unsigned i=0;i<16;i++)reu.bytes[0x340000+i]=uint8_t(i*17+3);}
 void step(){for(unsigned n=0;n<32;n++){if(remaining>=0){if(remaining==0){remaining=-1;reu.write(1,command,ram,written);if(override_completion>=0)reu.regs[0]=override_completion;}else --remaining;}execute();++clock;if(inFetchPhase())return;}assert(false);}
 bool io(uint16_t a){auto p=readPort();return a>=0xd000&&a<=0xdfff&&(p&3)&&(p&4);}
protected:
 uint8_t externalPortBits() const override{return 0xff;}
 uint8_t read(uint16_t a) override {
  if(io(a)&&a>=0xdf00&&a<=0xdf0a){
   if(a==0xdf00&&active){++status_reads;if(first){first=false;if(override_first>=0){if(consume_override)reu.read(0);return uint8_t(override_first);}}}
   return reu.read(a-0xdf00);
  }
  return ram[a];
 }
 void write(uint16_t a,uint8_t v) override {
  written[a]=1;
  if(io(a)&&a>=0xdf00&&a<=0xdf0a){if(a==0xdf01&&(v&0x80)){++commands;command=v;remaining=delay;active=true;first=true;return;}reu.write(a-0xdf00,v,ram,written);return;}ram[a]=v;
 }
 uint8_t readDasm(uint16_t a)const override{return ram[a];}
};
std::vector<uint8_t> load(const char*name){std::ifstream f(name,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
struct Case {const char*name;int delay,first,completion;bool consume,success;};
int main(int argc,char**argv){assert(argc==3);auto original=load(argv[1]),candidate=load(argv[2]);
 std::vector<Case> cases={{"immediate-completion",0,-1,-1,false,true},{"early-valid10",100,-1,-1,false,true},{"early-stale91",100,0x91,-1,false,true},{"stale91-consumes-EOB",0,0x91,-1,true,false},{"verify-error70",0,-1,0x70,false,false},{"verify-error20",0,-1,0x20,false,false},{"never-completes",100000,-1,-1,false,false},{"late-beyond-readbound",10000,-1,-1,false,false}};
 for(unsigned variant=0;variant<2;variant++)for(const auto&c:cases){Machine m;m.delay=c.delay;m.override_first=c.first;m.override_completion=c.completion;m.consume_override=c.consume;m.begin(variant?candidate:original);unsigned steps=0;while(m.reg.pc!=0x200&&steps++<20000)m.step();assert(m.reg.pc==0x200);assert(m.commands==1);assert(m.reg.y==0x93);assert((m.getP()&0xfe)==0x28);assert(m.reg.pport.direction==0x2f);assert((m.reg.pport.data&7)==7);bool success=!(m.getP()&1);bool expected=variant?c.success:std::string(c.name)=="immediate-completion";assert(success==expected);assert(m.ram[0xe009]==(success?0:4));assert(m.status_reads<=(variant?256:1));if(success)for(unsigned i=0;i<16;i++)assert(m.ram[0xc000+i]==uint8_t(i*17+3));if(variant)assert(m.ram[0xe00a]==(c.first>=0?c.first:(c.delay>4?0x10:(c.completion>=0?c.completion:0x50))));std::cout<<(variant?"candidate":"original")<<" "<<c.name<<" success="<<success<<" status="<<unsigned(m.ram[0xe008])<<" first="<<unsigned(m.ram[0xe00a])<<" reads="<<m.status_reads<<" cycles="<<m.clock<<" DMA="<<m.reu.transfers<<" commands="<<m.commands<<"\n";}
 for(unsigned raw=0;raw<256;raw++){Machine m;m.override_first=raw;m.consume_override=true;m.begin(candidate);unsigned steps=0;while(m.reg.pc!=0x200&&steps++<20000)m.step();assert(m.reg.pc==0x200);assert(m.commands==1);assert(m.ram[0xe00a]==raw);assert(m.status_reads<=256);bool expected=(raw&0x60)==0x40;assert((!(m.getP()&1))==expected);assert(m.reg.y==0x93);assert((m.getP()&0xfe)==0x28);}
 for(unsigned flags=0;flags<256;flags++)for(unsigned failure=0;failure<2;failure++){uint8_t observed[2];for(unsigned variant=0;variant<2;variant++){Machine m;m.override_completion=failure?0x20:-1;m.begin(variant?candidate:original);m.setP(flags);unsigned steps=0;while(m.reg.pc!=0x200&&steps++<20000)m.step();assert(m.reg.pc==0x200);observed[variant]=m.getP();assert(m.reg.y==0x93);assert(m.reg.pport.direction==0x2f);assert((m.reg.pport.data&7)==7);}assert(observed[0]==observed[1]);}
 std::cout<<"PASS512 initial-P success/error differential cases\n";
 std::cout<<"PASS16 actual6510 delayed/stale adversary comparisons +256 first-status masks; native-only attempt-bound observer\n";
}

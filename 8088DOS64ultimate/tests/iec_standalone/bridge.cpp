// Explicit KERNAL API model only. No ROM code/serial timing is simulated.
// All importer/CRC/guard/cleanup/REU instructions execute in real Peddle.
#include "bridge.h"
#include "Peddle.h"
#include "reu_model.h"
#include <array>
#include <vector>
#include <cstring>
#include <algorithm>
class IecCpu:public peddle::Peddle {
public:
 std::array<uint8_t,65536> ram{},written{};
 std::array<uint8_t,4096> io{};
 ReuModel reu{4096};std::vector<uint8_t> source;
 uint8_t fault=0,lfn=0,device=0,secondary=0,input=0;
 uint16_t name=0;uint8_t name_len=0;
 size_t position=0,status_position=0;
 uint64_t instructions=0,calls=0,reads=0;
 bool bad=false;uint8_t cia1mask=0x81,cia2mask=0x81;
 IecCpu(const uint8_t*p,size_t n,const uint8_t*s,size_t len,uint8_t f):source(s,s+len),fault(f){
  setModel(peddle::MOS_6510);reset();reg.sp=0xff;reg.pc=0x080d;reg.pc0=reg.pc;next=peddle::fetch;setP(0x24);
  reg.pport.direction=0x2f;reg.pport.data=0x37;
  if(n<2 || size_t(p[0]|(unsigned(p[1])<<8))+n-2>65536){bad=true;return;}
  std::memcpy(ram.data()+(p[0]|(unsigned(p[1])<<8)),p+2,n-2);
  for(size_t i=0;i<reu.bytes.size();++i)reu.bytes[i]=uint8_t(i^(i>>8)^(i>>16)^0xa7);
  if(fault==8){reu.fault_armed=true;reu.fault_skip=0;reu.fault_prefix=11;}
 }
 void value(uint8_t v){reg.a=v;setP((getP()&~0x82)|(v?0:2)|(v&0x80));}
 void set_pc(uint16_t pc){reg.pc=pc;reg.pc0=pc;next=peddle::fetch;}
 void carry(bool c){setP((getP()&~1)|(c?1:0));}
 bool has(uint8_t f){for(unsigned i=0;i<ram[0x98];++i)if(ram[0x259+i]==f)return true;return false;}
 void publish(uint8_t f){if(has(f)||ram[0x98]>=10){bad=true;return;}ram[0x259+ram[0x98]]=f;ram[0x263+ram[0x98]]=8;ram[0x26d+ram[0x98]]=f;ram[0x98]++;}
 void release(uint8_t f){for(unsigned i=0;i<ram[0x98];++i)if(ram[0x259+i]==f){for(unsigned j=i+1;j<ram[0x98];++j){ram[0x258+j]=ram[0x259+j];ram[0x262+j]=ram[0x263+j];ram[0x26c+j]=ram[0x26d+j];}--ram[0x98];return;}}
 bool kernal(uint16_t a){
  switch(a){case 0xffba:case 0xffbd:case 0xffc0:case 0xffc3:case 0xffc6:case 0xffcc:case 0xffcf:case 0xffb7:break;default:return false;}
  if((readPort()&7)!=7){bad=true;return true;}++calls;carry(false);
  switch(a){
   case 0xffba:lfn=reg.a;device=reg.x;secondary=reg.y;break;
   case 0xffbd:name_len=reg.a;name=reg.x|(uint16_t(reg.y)<<8);break;
   case 0xffc0:
    if(device!=8 || (lfn!=2 && lfn!=15) || secondary!=lfn){bad=true;break;}
    if(lfn==2){static const char expected[]="PCDISK,S,R";if(name_len!=10||std::memcmp(ram.data()+name,expected,10))bad=true;position=0;}
    else if(name_len!=0)bad=true;
    publish(lfn);ram[0x90]=0;status_position=0;
    if(fault==2 && lfn==2){ram[0x90]=0x80;carry(true);}
    break;
   case 0xffc6:
    if(!has(reg.x)){bad=true;break;}input=reg.x;
    if(fault==3 && input==2)carry(true);
    break;
   case 0xffcf:
    if(input==2){
     if(!has(2)){bad=true;break;}
     if(fault==1){value(0);ram[0x90]|=0x42;}
     else if(fault==4 && position==13){value(0);ram[0x90]|=2;}
     else if(position>=source.size()){bad=true;break;}
     else {value(source[position++]);++reads;if(position==source.size())ram[0x90]|=0x40;}
    } else if(input==15){
     if(!has(15)){bad=true;break;}
     const char*text=fault==1?"62, FILE NOT FOUND,00,00\r":(fault==5?"74, DRIVE NOT READY,00,00\r":"00, OK,00,00\r");
     const auto length=std::strlen(text);if(status_position>=length){bad=true;break;}
     value(uint8_t(text[status_position++]));if(status_position==length)ram[0x90]|=0x40;
    } else bad=true;
    break;
   case 0xffb7:value(ram[0x90]);break;
   case 0xffcc:input=0;break;
   case 0xffc3:
    release(reg.a);if(reg.a==15 && fault==6){ram[0x90]=2;carry(true);}
    if(reg.a==15 && fault==7)ram[0xc200]=0x17;
    break;
  }
  // Original serial routines/traps enable interrupts; masking sources belongs
  // to the real target rather than a conveniently preserved model I bit.
  if(a==0xffc0||a==0xffc3||a==0xffc6||a==0xffcc||a==0xffcf)setP(getP()&~4);
  return true;
 }
 void step(){
  if(reg.pc>=0xe000 && (readPort()&2))if(!kernal(reg.pc)){bad=true;return;}
  for(unsigned i=0;i<32;++i){execute();++clock;if(inFetchPhase()){++instructions;return;}}bad=true;
 }
protected:
 peddle::u8 externalPortBits()const override{return 0xff;}
 void writePort(uint8_t v)override{
  if((v&7)==5 && ((ram[0xfffa]|(uint16_t(ram[0xfffb])<<8))==0 || (ram[0xfffe]|(uint16_t(ram[0xffff])<<8))==0 || cia1mask||cia2mask||io[0x1a]))bad=true;
  peddle::Peddle::writePort(v);ram[1]=v;written[1]=1;
 }
 void writePortDir(uint8_t v)override{peddle::Peddle::writePortDir(v);ram[0]=v;written[0]=1;}
 peddle::u8 read(peddle::u16 a)override{
  const auto port=readPort();
  if(a>=0xa000 && a<=0xbfff && (port&3)==3)return 0xba;
  if(a>=0xe000 && (port&2))return 0x60; // actual RTS for explicit API entries; step rejects all others
  if(a>=0xd000 && a<=0xdfff && (port&3)){
   if(!(port&4))return 0xcc;
   if(a>=0xdf00 && a<=0xdf0a)return reu.read(a-0xdf00);
   if(a==0xdc0d||a==0xdd0d)return 0;
   bad=true;return 0;
  }
  return ram[a];
 }
 void write(peddle::u16 a,peddle::u8 v)override{
  written[a]=1;const auto port=readPort();
  if(a>=0xd000 && a<=0xdfff && (port&3)&&(port&4)){
   if(a>=0xdf00&&a<=0xdf0a){reu.write(a-0xdf00,v,ram,written);return;}
   if(a==0xdc0d){cia1mask=v&0x80?(cia1mask|(v&0x1f)):(cia1mask&~(v&0x1f));cia1mask&=31;return;}
   if(a==0xdd0d){cia2mask=v&0x80?(cia2mask|(v&0x1f)):(cia2mask&~(v&0x1f));cia2mask&=31;return;}
   if(a==0xd01a||a==0xd019){io[a-0xd000]=v;return;}
   bad=true;return;
  }
  ram[a]=v;
 }
 peddle::u8 readDasm(peddle::u16 a)const override{return ram[a];}
};
struct IecMachine{IecCpu cpu;IecMachine(const uint8_t*p,size_t n,const uint8_t*s,size_t len,uint8_t f):cpu(p,n,s,len,f){}};
IecMachine*iec_create(const uint8_t*p,size_t n,const uint8_t*s,size_t len,uint8_t f){return new IecMachine(p,n,s,len,f);}
void iec_destroy(IecMachine*m){delete m;}
IecRun iec_run(IecMachine*m,uint16_t entry,uint16_t stop,uint64_t budget){
 auto&c=m->cpu;c.set_pc(entry);
 const uint64_t begin=c.clock;uint8_t status=0;
 while(c.reg.pc!=stop && !c.bad && !c.reu.unsupported){if(c.clock-begin>=budget){status=2;break;}c.step();}
 if(c.bad||c.reu.unsupported)status=1;
 return{uint64_t(c.clock),c.instructions,c.calls,c.reads,uint32_t(c.reu.transfers),uint32_t(c.reu.dma_bytes),c.reg.pc,c.reg.sp,uint8_t(c.bad||c.reu.unsupported),status};
}
const uint8_t*iec_ram(IecMachine*m){return m->cpu.ram.data();}
const uint8_t*iec_reu(IecMachine*m){return m->cpu.reu.bytes.data();}
void iec_poke(IecMachine*m,uint16_t a,uint8_t v){m->cpu.ram[a]=v;}

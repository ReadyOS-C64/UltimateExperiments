"""Editor-only half CCITT table: actual6510 against independent binascii oracle.
Private build only. Generic full-table binary compared with acceptedc39 source.
"""
from pathlib import Path
from datetime import datetime,timezone
import binascii,ctypes as C,hashlib,json,random,re,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR,library
BASE=ROOT/'agentsworking/evidence/M5/20261025T014555415130Z-editor-warm-native/compiled-inputs.zip'
def run(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def symbols(p):return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
def build(out,half=False,old=False):
 out.mkdir(parents=True,exist_ok=True);source=ROOT/'src'
 if old:
  source=out/'baseline/src'
  with zipfile.ZipFile(BASE) as z:
   for n in ['src/overlay/crc_fast.s','src/overlay/crc_tables.inc']:
    p=out/'baseline'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 table=0x3F00 if half else 0x3E00;size=256 if half else 512
 (out/'crc.cfg').write_text(f'MEMORY {{ C:start=$1000,size=$0100,file=%O,fill=yes; T:start=${table:04X},size=${size:04X},file=%O,fill=yes; S:start=$C000,size=$0600,file=""; }} SEGMENTS {{ CODE:load=C,type=ro,define=yes; CRC_TABLE:load=T,type=ro,define=yes; BSS:load=S,type=bss,define=yes; }}')
 args=['ca65','-g','-I',source,'-o',out/'crc.o',source/'overlay/crc_fast.s']
 if half:args[1:1]=['-D','EDITOR_HALF_CRC=1']
 run(*args);run('ld65','-C',out/'crc.cfg','-o',out/'crc.bin','-Ln',out/'crc.lbl','-m',out/'crc.map',out/'crc.o');return symbols(out/'crc.lbl')
def driver(out):
 library();cpp=out/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
static uint32_t failure=0;extern "C" uint32_t ch_failure(){return failure;}
extern "C" uint64_t ch_cases(ZeroPagePeddle*m,uint16_t pc,uint16_t crc,const uint8_t*p,uint32_t n){uint8_t zp[256];for(int j=0;j<256;j++)zp[j]=zeropage_peddle_read(m,j);auto start=zeropage_peddle_regs(m).instructions;
for(uint32_t i=0;i<n;i++,p+=5){zeropage_peddle_write(m,crc,p[0]);zeropage_peddle_write(m,crc+1,p[1]);zeropage_peddle_write(m,0x1fe,0xfe);zeropage_peddle_write(m,0x1ff,2);zeropage_peddle_set_pc(m,pc);zeropage_peddle_set_sp(m,0xfd);zeropage_peddle_set_a(m,p[2]);zeropage_peddle_set_x(m,0xa7);uint8_t y=(i*17+31)&255;zeropage_peddle_set_y(m,y);zeropage_peddle_set_p(m,0x24);
int step=0;for(;step<100;step++){if(zeropage_peddle_regs(m).pc==0x2ff)break;zeropage_peddle_step_instruction(m);}if(step==100){failure=1;return i+1;}if(zeropage_peddle_read(m,crc)!=p[3]||zeropage_peddle_read(m,crc+1)!=p[4]){failure=2;return i+1;}if(zeropage_peddle_regs(m).y!=y){failure=3;return i+1;}for(int j=0;j<256;j++)if(zeropage_peddle_read(m,j)!=zp[j]){failure=4;return i+1;}}
failure=0;return zeropage_peddle_regs(m).instructions-start;}
''')
 ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('runner'+ext);run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',path);dll=C.CDLL(str(path));dll.ch_cases.argtypes=[C.c_void_p,C.c_uint16,C.c_uint16,C.c_void_p,C.c_uint32];dll.ch_cases.restype=C.c_uint64;dll.ch_failure.restype=C.c_uint32;return dll
def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/crc-half'/stamp;out.mkdir(parents=True);half=build(out/'half',True);generic=build(out/'generic');old=build(out/'accepted-c39',old=True)
 assert (out/'generic/crc.bin').read_bytes()==(out/'accepted-c39/crc.bin').read_bytes(),'generic default binary changed'
 assert half['se_crc_table_low']==0x3F00 and half['se_crc_table_high']==0x3F80 and half['__CRC_TABLE_SIZE__']==256 and half['__BSS_SIZE__']==generic['__BSS_SIZE__']==2
 rng=random.Random(0x1021);states=sorted({0,1,0xFF,0x100,0xFFFF,0x8000,0x7FFF,0x1234,0xABCD,*[rng.randrange(65536) for _ in range(64)]});data=bytearray()
 def case(state,byte):data.extend(struct.pack('<HBH',state,byte,binascii.crc_hqx(bytes([byte]),state)))
 for state in states:
  for byte in range(256):case(state,byte)
 representative=[0,1,0x7F,0x80,0xA5,0xFE,0xFF]
 for state in range(65536):
  for byte in representative:case(state,byte)
 dll=driver(out);metrics={}
 for name,s,table in [('half',half,0x3F00),('generic',generic,0x3E00)]:
  m=Machine()
  try:
   m.load(0,bytes((i*73+19)&255 for i in range(65536)));image=(out/name/'crc.bin').read_bytes();m.load(0x1000,image[:256]);m.load(table,image[256:]);before=bytes(m.read(i) for i in range(65536));instructions=dll.ch_cases(m.handle,s['se_crc_byte'],s['se_crc_value'],C.create_string_buffer(bytes(data)),len(data)//5);assert dll.ch_failure()==0,(name,'case',instructions-1,'type',dll.ch_failure(),data[(instructions-1)*5:instructions*5].hex());after=bytes(m.read(i) for i in range(65536));want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];at=s['se_crc_value'];want[at:at+2]=after[at:at+2];assert after==want,(name,'RAM/ZP/source/table/shim guard')
   m.call(s['se_crc_init']);assert m.read(at)==m.read(at+1)==255
   for b in b'123456789':
    reg,_=m.call(s['se_crc_byte'],a=b,y=0x6D);assert reg.y==0x6D
   assert m.read(at)|(m.read(at+1)<<8)==0x29B1
   metrics[name]=dict(code_bytes=s['__CODE_SIZE__'],table_bytes=s['__CRC_TABLE_SIZE__'],instructions=instructions,cases=len(data)//5)
  finally:m.close()
 result=dict(status='passed',metrics=metrics,diverse_states=len(states),all256_input_bytes=True,all65536_previous_states_for=representative,Y_preserved_each_case=True,ZP256_unchanged_each_case=True,whole_RAM_guard_bytes=65536,half_table=[0x3F00,0x3FFF],new_BSS=0,new_ZP=0,generic_byte_identity_sha256=hashlib.sha256((out/'generic/crc.bin').read_bytes()).hexdigest(),oracle='Python binascii.crc_hqx(singlebyte,previous), CRC16/CCITT-FALSE known123456789=29B1',source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/overlay/crc_fast.s','src/overlay/crc_tables.inc','tests/test_crc_half.py']})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

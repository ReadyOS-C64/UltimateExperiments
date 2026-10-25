"""Read-only actual C6/R30/C32 PC and dynamic-subroutine profiler.

CPU cycles/instructions only; no IRQ/VIC/physical-key timing claim. Immutable
packaged payloads are rebuilt byte-identically solely to recover debug labels.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,importlib.util,json,shutil,subprocess,sys,zipfile,hashlib,bisect
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
import test_fold_retention as retention
from test_editor_kernal_stack import OPS
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T133435860867Z/fixture'

def symbols(p):
 d={}
 for line in p.read_text().splitlines():
  t=line.split()
  if len(t)==3 and t[0]=='al':d[t[2].lstrip('.')]=int(t[1],16)
 return d

def rebuild(out,base):
 src=out/'source'
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 (src/'tools').mkdir(exist_ok=True)
 for n in ['overlays.py','bindings.py','module_bindings.py']:shutil.copy2(ROOT/'tools'/n,src/'tools'/n)
 shutil.copy2(ROOT/'src/render/geos/style-typing/build.py',src/'src/render/geos/style-typing/build.py')
 spec=importlib.util.spec_from_file_location('hotbuild',src/'src/render/geos/style-typing/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 images,budget=b.build(out/'labels',base);identity=json.loads((base/'freeze.json').read_text())
 checks={}
 for tag,data in images.items():
  name=next(n for n in identity['names']if(base/'build/overlays'/f'{n}.seo').read_bytes()[5:7]==data[5:7])
  assert data==(base/'build/overlays'/f'{name}.seo').read_bytes(),('rebuildidentity',tag,name)
  checks[tag]=dict(name=name,sha256=hashlib.sha256(data).hexdigest())
 (out/'rebuild-identity.json').write_text(json.dumps(dict(byteidentical=checks,budget=budget),indent=2)+'\n')
 return symbols(out/'labels/stage.lbl'),symbols(out/'labels/worker.lbl')

def runner(out):
 retention.runner(out);p=out/'runner.cpp';src=p.read_text()
 costs=[];pages=[]
 for item in OPS:
  if item is None:costs.append(0);pages.append(0);continue
  op,mode=item;page=0
  if mode=='r':cost=2
  elif op in ('ASL','LSR','ROL','ROR','INC','DEC'):cost=dict(a=2,z=5,zx=6,b=6,bx=7)[mode]
  elif op in ('STA','STX','STY'):cost=dict(z=3,zx=4,zy=4,b=4,bx=5,by=5,ix=6,iy=6)[mode]
  elif op in ('JSR','RTS','RTI'):cost=6
  elif op in ('PHA','PHP'):cost=3
  elif op in ('PLA','PLP'):cost=4
  elif op=='JMP':cost=5 if mode=='ind'else 3
  elif op=='BRK':cost=7
  elif mode=='i':cost=2
  else:
   cost=dict(n=2,z=3,zx=4,zy=4,b=4,bx=4,by=4,ix=6,iy=5)[mode]
   page=dict(bx=1,by=2,iy=3).get(mode,0)
  costs.append(cost);pages.append(page)
 tables='static const uint8_t hp_base[256]={'+','.join(map(str,costs))+'};\nstatic const uint8_t hp_page[256]={'+','.join(map(str,pages))+'};\n'

 marker='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 extra='''
static uint16_t hp_active=0;static uint8_t hp_r30=0;
extern "C" void hp_scope(uint16_t active,uint8_t tag){hp_active=active;hp_r30=tag;}
static uint16_t hp_dma_pc=0,hp_dma_len=0;static uint64_t hp_dma_calls[2]={},hp_dma_bytes[2]={};
extern "C" void hp_dma(uint16_t pc,uint16_t len){hp_dma_pc=pc;hp_dma_len=len;}
extern "C" uint64_t hp_dma_get(int i,int field){return field?hp_dma_bytes[i]:hp_dma_calls[i];}
static uint64_t hp_time=0;static int hp_cost=0;static uint32_t hp_invalid=0;
static bool hp_on=false;static uint64_t hp_n[65536],hp_c[65536];
struct Spec {uint16_t pc;uint8_t which;uint64_t n,c,ins;};static Spec specs[128];static int ns=0;
struct Frame{int i;uint16_t ret;uint8_t sp;uint64_t c,ins;};static Frame fs[128];static int nf=0;
extern "C" void hp_spec(int i,uint16_t pc,uint8_t which){specs[i]={pc,which,0,0,0};if(i>=ns)ns=i+1;}
extern "C" void hp_start(){memset(hp_n,0,sizeof(hp_n));memset(hp_c,0,sizeof(hp_c));for(int i=0;i<ns;i++)specs[i].n=specs[i].c=specs[i].ins=0;nf=0;hp_time=0;hp_invalid=0;memset(hp_dma_calls,0,sizeof(hp_dma_calls));memset(hp_dma_bytes,0,sizeof(hp_dma_bytes));hp_on=true;}
extern "C" void hp_stop(){hp_on=false;}
extern "C" uint32_t hp_bad(){return hp_invalid;}
extern "C" uint64_t hp_get(int i,int field){return field==0?specs[i].n:field==1?specs[i].c:specs[i].ins;}
extern "C" void hp_hist(uint64_t*n,uint64_t*c){memcpy(n,hp_n,sizeof(hp_n));memcpy(c,hp_c,sizeof(hp_c));}
static void hp_before(ZeroPagePeddle*m,const ZeroPagePeddleRegs&r){if(!hp_on)return;
 if(r.pc==hp_dma_pc && r.a<2){uint32_t n=zeropage_peddle_read(m,hp_dma_len)|(zeropage_peddle_read(m,hp_dma_len+1)<<8);if(!n)n=65536;hp_dma_calls[r.a]++;hp_dma_bytes[r.a]+=n;}
 uint8_t op=zeropage_peddle_read(m,r.pc),a=zeropage_peddle_read(m,r.pc+1);hp_cost=hp_base[op];if(!hp_cost)hp_invalid++;
 if((op&31)==16){bool taken=false;switch(op){case 0x10:taken=!(r.p&128);break;case 0x30:taken=r.p&128;break;case 0x50:taken=!(r.p&64);break;case 0x70:taken=r.p&64;break;case 0x90:taken=!(r.p&1);break;case 0xb0:taken=r.p&1;break;case 0xd0:taken=!(r.p&2);break;case 0xf0:taken=r.p&2;break;}
 if(taken){auto next=uint16_t(r.pc+2),dest=uint16_t(next+int8_t(a));hp_cost+=1+((next&0xff00)!=(dest&0xff00));}}
 else if(hp_page[op]){uint16_t base=0;uint8_t index=0;
 if(hp_page[op]==3){base=zeropage_peddle_read(m,a)|(zeropage_peddle_read(m,uint8_t(a+1))<<8);index=r.y;}
 else{base=a|(zeropage_peddle_read(m,r.pc+2)<<8);index=hp_page[op]==1?r.x:r.y;}
 hp_cost+=((base&255)+index)>255;}
 for(int i=0;i<ns;i++)if(r.pc==specs[i].pc && (specs[i].which==255||(specs[i].which==254?zeropage_peddle_read(m,hp_active)==hp_r30:zeropage_peddle_read(m,0x8bd8)==specs[i].which))){
 auto ret=uint16_t(zeropage_peddle_read(m,0x100+uint8_t(r.sp+1))|(zeropage_peddle_read(m,0x100+uint8_t(r.sp+2))<<8))+1;
 if(nf<128){fs[nf++]={i,uint16_t(ret),r.sp,hp_time,r.instructions};specs[i].n++;}}}
static void hp_after(ZeroPagePeddle*m,const ZeroPagePeddleRegs&r){if(!hp_on)return;auto z=zeropage_peddle_regs(m);hp_n[r.pc]++;hp_c[r.pc]+=hp_cost;hp_time+=hp_cost;
 while(nf && z.pc==fs[nf-1].ret && z.sp==uint8_t(fs[nf-1].sp+2)){auto f=fs[--nf];specs[f.i].c+=hp_time-f.c;specs[f.i].ins+=z.instructions-f.ins;}}
'''
 assert src.count(marker)==1
 src=src.replace(marker,tables+extra+marker+'hp_before(m,r);')
 needle='zeropage_peddle_step_instruction(m);';assert src.count(needle)==1;src=src.replace(needle,needle+'hp_after(m,r);');p.write_text(src)
 ext='.dylib'if sys.platform=='darwin'else'.so';target=out/('hotspots'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(fold.geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(target)],check=True)
 dll=C.CDLL(str(target))
 # Set identical ABI to released retention wrapper.
 dll.gm_rom.argtypes=[C.c_void_p,C.c_void_p];dll.gm_rom_count.restype=C.c_uint64
 dll.gm_profile.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint16,C.c_uint16,C.c_uint16,C.c_uint16]
 dll.gm_metric.argtypes=[C.c_int];dll.gm_metric.restype=C.c_uint64
 for n in ['gm_run','gm_idle']:getattr(dll,n).restype=C.c_uint64
 dll.gm_run.argtypes=[C.c_void_p,C.c_uint64];dll.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64]
 dll.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
 dll.fr_begin.argtypes=[C.c_uint16]*7;dll.fr_mask.argtypes=[C.c_void_p];dll.fr_bad.restype=C.c_uint32;dll.fr_writes.restype=C.c_uint32
 dll.hp_scope.argtypes=[C.c_uint16,C.c_uint8]
 dll.hp_dma.argtypes=[C.c_uint16,C.c_uint16];dll.hp_dma_get.argtypes=[C.c_int,C.c_int];dll.hp_dma_get.restype=C.c_uint64
 dll.hp_bad.restype=C.c_uint32
 dll.hp_spec.argtypes=[C.c_int,C.c_uint16,C.c_uint8];dll.hp_get.argtypes=[C.c_int,C.c_int];dll.hp_get.restype=C.c_uint64;dll.hp_hist.argtypes=[C.c_void_p,C.c_void_p]
 return dll

def run(out,base):
 frozen=out/'fixture';shutil.copytree(base,frozen);stage,worker=rebuild(out,frozen)
 identity=json.loads((frozen/'freeze.json').read_text());grid=fold.geos.grid;grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names']
 dll=runner(out);f=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)}
 targets=[]
 def add(name,address,which=255):dll.hp_spec(len(targets),address,which);targets.append((name,address))
 for n in ['se_gst_transaction','begin','step','commit','scanlines','block','se_typing_patch','se_typing_validate','se_gst_prepare','se_gst_transform']:
  add('C32:'+n,stage[n])
 add('C32:scanlines_gather',stage['scanlines'],0);add('C32:scanlines_scatter',stage['scanlines'],1)
 for n in ['se_gct_stage','se_gtt_admit','se_gtt_current','se_gp_cache_read','se_gp_cache_write','se_gp_cache_slot','se_gcc_status','tui_editor_status40']:add('R30:'+n,worker[n],254)
 for n in ['se_view_init','se_view_peek','se_doc_validate','se_object_validate','se_reu_copy','se_reu_validate','se_crc_byte']:
  if n in f.s:add('resident:'+n,f.s[n])
 # Independently known dynamic NMOS cycle calibration, separate CPU only.
 cal=grid.Machine();calibration=[]
 for tag,address,code,want in [('basic',0x800,bytes([0xa9,1,0xaa,0xe8,0x48,0x68,0x60]),19),('branch-cross',0x8fc,bytes([0xa2,2,0xca,0xd0,0xfd,0x60]),18),('absx-cross',0xa00,bytes([0xa2,1,0xbd,0xff,8,0x60]),13),('indy-cross',0xa20,bytes([0xa0,1,0xb1,0x10,0x60]),14)]:
  cal.load(address,code);cal.write(0x10,255);cal.write(0x11,8);dll.hp_start()
  for n,v in [('pc',address),('sp',0xfd),('p',0x24)]:getattr(cal.lib,'zeropage_peddle_set_'+n)(cal.handle,v)
  cal.write(0x1fe,0xfe);cal.write(0x1ff,2);assert dll.gm_run(cal.handle,100)
  dll.hp_stop();ns=(C.c_uint64*65536)();cs=(C.c_uint64*65536)();dll.hp_hist(ns,cs);assert sum(cs)==want and not dll.hp_bad(),(tag,sum(cs),want);calibration.append(dict(tag=tag,cycles=want))
 cal.close();(out/'cycle-calibration.json').write_text(json.dumps(calibration,indent=2)+'\n')
 dll.hp_scope(f.s['se_overlay_active'],identity['names'].index(json.loads((out/'rebuild-identity.json').read_text())['byteidentical']['worker']['name'])+1)
 dll.hp_dma(f.s['se_reu_copy'],f.s['se_reu_length'])
 frames=[]
 def snapshot(tag):
  ns=(C.c_uint64*65536)();cs=(C.c_uint64*65536)();dll.hp_hist(ns,cs)
  assert not dll.hp_bad(),'unofficial/unmodeled opcode reached'
  hist=[dict(pc=i,instructions=ns[i],cycles=cs[i])for i in range(65536)if ns[i]]
  sums={}
  for x in hist:
   p=x['pc'];name='resident'if p<0x4000 else 'C32-stage'if 0x5000<=p<0x6000 else 'R30'if 0xa000<=p<0xb000 else 'C6'if 0xb000<=p<0xc000 else 'other'
   q=sums.setdefault(name,dict(cycles=0,instructions=0));q['cycles']+=x['cycles'];q['instructions']+=x['instructions']
  funcs=[dict(name=n,pc=a,calls=dll.hp_get(i,0),cycles=dll.hp_get(i,1),instructions=dll.hp_get(i,2))for i,(n,a)in enumerate(targets)if dll.hp_get(i,0)]
  r=dict(tag=tag,total_cycles=sum(cs),total_instructions=sum(ns),regions=sums,inclusive_functions=funcs,DMA=[dict(direction=i,calls=dll.hp_dma_get(i,0),bytes=dll.hp_dma_get(i,1))for i in range(2)])
  (out/(tag+'-histogram.json')).write_text(json.dumps(hist)+'\n');return r
 data=grid.native_text('Alpha **interiorwords** omega.\rAlpha *interiorwords* omega.\rAlpha ***interiorwords*** omega.\rAlpha interiorwords omega.\rSecond plain row.\rTail.')
 try:
  for tag,needle,key in [('bold','**interiorwords',grid.native_text('X')[0]),('italic','*interiorwords',grid.native_text('X')[0]),('combined','***interiorwords',grid.native_text('X')[0]),('plain','Alpha interiorwords',grid.native_text('X')[0])]:
   f.source(data);f.command(99);raw=grid.native_text(needle);at=data.index(raw)+(len(raw)-len('interiorwords'))+2
   if tag=='italic':at=data.index(raw,data.index(b'\r')+1)+1+2
   f.position(at);f.render()
   for op,k in [('insert-prime',key),('backspace-warm',0x14),('insert-warm',key),('backspace-warm2',0x14)]:
    tagop=tag+'-'+op;dll.hp_start();f.key(k);dll.hp_stop();inputprofile=snapshot(tagop+'-input')
    canonical=f.canonical();oldreu=f.reu();catalog=f.catalog();f.audit_begin();dll.hp_start();f.render();dll.hp_stop();f.dll.fr_end();profile=snapshot(tagop+'-render');writes=f.audit_end(oldreu,tagop)
    assert f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
    assert f.m.read(0xcbd5)==0x42 and f.m.read(0xcf90)==1 and not f.get('se_f_owner',1) and not f.get('se_e_error',1)
    actual=f.merged();bits,attrs,_,_=semantic.expected(f,actual,fonts)
    assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tagop,'independentpixels')
    fold.geos.png(bits,attrs,out/(tagop+'.png'));profile.update(key=k,input=inputprofile,derived_DMA_writes=writes,source_bytes=len(actual));frames.append(profile)
    print('PASS',tagop,profile['total_cycles'],profile['total_instructions'],flush=True)
    (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
  result=dict(status='passed',identity=identity,frames=frames,scope='Actual public input+render with frozen47 assets and byte-identical rebuilt C32/R30 labels. Dynamic official NMOS6510 opcode cycles reconstructed from actual PC/flags/indexed page crossings (Peddle clock is0); exclude native IRQ/VIC/RDY/REU stall time; not PAL latency. Histograms exclusive by PC; dynamic subroutine totals inclusive and overlap intentionally. Every frame independent full8000byte bitmap/1000attrs/source/history/catalog/shim and whole16MiB typed-DMA guards. No product edits.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=DEFAULT);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/geos-style-hotspots'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);print('RUN',out,flush=True);run(out,a.base)

"""Read-only actual C35/C37 two-case53 profile; optional native diverse source."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, re, shutil, subprocess, sys, zlib, bisect
import test_cache_observer as observer
import test_plain_geos as plain
import test_grid_editor_vice as diverse
from cache_job_build import editor_pair_index
ROOT=observer.ROOT
N=65536+64*4096
ORIGINAL=observer.runner

def runner(out):
 old=ORIGINAL(out);p=out/'runner.cpp';s=p.read_text()
 needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 add=r'''
static uint64_t cp_self[327680],cp_inc[327680],cp_calls[327680],cp_total,cp_modules[65];
static uint16_t cp_active;static bool cp_on=false;
struct CPFrame{uint32_t key;uint16_t ret;uint8_t sp;};static CPFrame cp_stack[128];static unsigned cp_depth=0;
extern "C" void cp_begin(uint16_t a){cp_active=a;memset(cp_self,0,sizeof(cp_self));memset(cp_inc,0,sizeof(cp_inc));memset(cp_calls,0,sizeof(cp_calls));cp_total=0;memset(cp_modules,0,sizeof(cp_modules));cp_depth=0;cp_on=true;}
extern "C" void cp_end(){cp_on=false;}
extern "C" uint64_t cp_count(){return cp_total;}
extern "C" uint64_t cp_module(unsigned n){return cp_modules[n];}
extern "C" void cp_dump(unsigned type,uint64_t*out){memcpy(out,type==0?cp_self:type==1?cp_inc:cp_calls,sizeof(cp_self));}
static void cp_step(ZeroPagePeddle*m,uint16_t pc,uint8_t sp){if(!cp_on)return;
 while(cp_depth && pc==cp_stack[cp_depth-1].ret && sp==cp_stack[cp_depth-1].sp)cp_depth--;
 unsigned tag=0;if(pc>=0xa000&&pc<0xc000)tag=zeropage_peddle_read(m,cp_active+(pc>=0xb000));
 uint32_t k=tag&&tag<=64?65536+(tag-1)*4096+(pc&4095):pc;
 cp_self[k]++;cp_total++;
 uint64_t seen=tag&&tag<=64?uint64_t(1)<<(tag-1):0;
 for(unsigned i=0;i<cp_depth;i++)if(cp_stack[i].key>=65536)seen|=uint64_t(1)<<((cp_stack[i].key-65536)/4096);
 while(seen){unsigned bit=__builtin_ctzll(seen);cp_modules[bit+1]++;seen&=seen-1;}
 if(zeropage_peddle_read(m,pc)==0x20 && cp_depth<128){cp_calls[k]++;cp_stack[cp_depth++]={k,uint16_t(pc+3),sp};}
 for(unsigned i=0;i<cp_depth;i++)cp_inc[cp_stack[i].key]++;
}
'''
 assert s.count(needle)==1;s=s.replace(needle,add+needle+'cp_step(m,r.pc,r.sp);');p.write_text(s)
 ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('cost-runner'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(observer.geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
 dll=C.CDLL(str(lib))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_end','fr_mask','fr_bad','fr_writes','pb_config','pb_begin','pb_end','pb_get','pb_fault_get','ob_ring','ob_ring_get'):
  a,b=getattr(old,name),getattr(dll,name);b.argtypes,b.restype=a.argtypes,a.restype
 dll.cp_module.argtypes=[C.c_uint];dll.cp_module.restype=C.c_uint64;dll.cp_begin.argtypes=[C.c_uint16];dll.cp_count.restype=C.c_uint64;dll.cp_dump.argtypes=[C.c_uint,C.c_void_p]
 return dll

def labels(p):return [(int(a,16),n)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\S+)',p.read_text())]
def run(out,base,profile_label="source-matched",dataset="251"):
 observer.runner=runner;g=observer.Gate(out,base);f=g.f;names=g.identity['names']; stems={};syms={};cases=[]
 try:
  indexes={name:(editor_pair_index(f.assets[name][5],f.assets[name][6]) if 'catalog_index' in f.s else order) for order,name in enumerate(names)}
  slot_names={index:name for name,index in indexes.items()};assert len(slot_names)==len(names)
  for name in names:
   stem=ROOT/'build/cache-editor'/name if name in ('fold','sema','inln','page')else ROOT/'build/overlays'/name
   if stem.with_suffix('.bin').exists() and stem.with_suffix('.lbl').exists() and stem.with_suffix('.bin').read_bytes()==f.assets[name][36:]:
    stems[name]=stem;shutil.copy2(stem.with_suffix('.lbl'),out/(name+'.lbl'));syms[name]=labels(stem.with_suffix('.lbl'))
  assert 'inln'in syms and len(f.assets['inln'][36:])<=4096
  query_symbols=dict((n,a)for a,n in syms['inln'])
  boundaries=[0]+[query_symbols[n]-0xB000 for n in ('se_bc_query_begin','bq_authority','read_record','bca_owner','se_bc_arena_open','se_bc_page_begin')]+[len(f.assets['inln'][36:])]
  assert boundaries==sorted(boundaries),('query code sections',boundaries)
  resident=labels(g.frozen/'build/editor.lbl');syms['resident']=resident
  def decode(k):
   if k<65536:return 'resident',k
   a=(k-65536)//4096;name=slot_names[a];entry=next(pc for pc,n in syms[name]if n=='entry');return name,(entry&0xF000)+((k-65536)&4095)
  # Header byte slot is not assumed by symbolization; actual label address supplies it.
  def decoded(k):
   name,pc=decode(k)
   if name!='resident':
    labelpcs=[a for a,n in syms.get(name,[])if n=='entry']
    pc=(labelpcs[0]&0xF000 if labelpcs else (0xB000 if name in ('inln','sema')else pc&0xF000))+(k&4095)
   near=[(a,n)for a,n in syms.get(name,[])if a<=pc and not n.startswith('@') and (name=='resident'or (a&0xF000)==(pc&0xF000))]
   a,n=max(near,default=(pc,'?'))
   return dict(asset=name,pc=f'{pc:04X}',symbol=n,offset=pc-a)
  fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)};data=plain.SOURCE if dataset=='251'else diverse.fixture()
  def full():
   f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
  f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render()
  assert f.get('se_bc_flags',1)&15==1 and f.get('se_bc_count',1)==0
  for tag,move in [('cached-full',False),('viewport-miss',True)]:
   if move:f.position(1)
   before=g.reu();stable=g.stable();initial=f.total_instructions;g.dll.cp_begin(f.s['se_overlay_active'])
   try:full()
   finally:g.dll.cp_end()
   total=int(g.dll.cp_count());assert total==f.total_instructions-initial,(total,f.total_instructions-initial)
   arrays=[]
   for typ in range(3):
    ar=(C.c_uint64*N)();g.dll.cp_dump(typ,ar);raw=bytes(ar);(out/(tag+f'-hist{typ}.z')).write_bytes(zlib.compress(raw));arrays.append(list(ar))
   selfs,inc,calls=arrays;by={}
   for k,v in enumerate(selfs):
    if v:
     name,_=decode(k);by[name]=by.get(name,0)+v
   topcalls=[dict(**decoded(k),calls=calls[k],inclusive=inc[k])for k in sorted(range(N),key=lambda k:inc[k],reverse=True)[:100]if inc[k]]
   crcs=[];crc=f.s['se_crc_byte']
   # Use exact payload bytes to identify direct CRC JSRs, never infer CRC work from event counts.
   for k,v in enumerate(calls):
    if not v:continue
    name,pc=decode(k)
    if name=='resident':raw=f.read(pc,3)
    else:
     off=(k-65536)&4095;raw=f.assets[name][36+off:39+off]
    if len(raw)==3 and raw[0]==0x20 and int.from_bytes(raw[1:],'little')==crc:crcs.append(dict(**decoded(k),calls=v,inclusive=inc[k]))
   bits,attrs,rows=plain.expected(f,data,fonts,1)
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'pixels')
   assert f.merged()==data and g.stable()==stable and f.read(0xC600,1024)==f.shim
   assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
   _,bank=f.raw_cache();after=g.reu();expected=bytearray(before)
   spans=[(0,64),(0x600,0x680),(0xB200,0xD568),(0xE568,0xEA88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
   for lo,hi in spans:expected[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]

   if after!=expected:
    diffs=[]
    for b in range(256):
     offsets=[i for i,(a,v)in enumerate(zip(expected[b*65536:(b+1)*65536],after[b*65536:(b+1)*65536]))if a!=v]
     if offsets:diffs.append(dict(bank=b,first=offsets[:24],last=offsets[-24:],count=len(offsets),owner=f.m.read(f.s['se_reu_physical_owner']+b)))
    (out/(tag+'-unexpected.json')).write_text(json.dumps(diffs,indent=2))
   assert after==expected,(tag,'16MiB outside exact FE extents')
   observer.geos.png(bits,attrs,out/(tag+'.png'))
   c35base=65536+indexes['inln']*4096
   sections=list(zip(('selector','query','source_exchange','record','arena_core','root_open','page'),boundaries,boundaries[1:]))
   detail=dict(c35_inclusive=sum(selfs[c35base:c35base+boundaries[1]])+sum(inc[c35base:c35base+boundaries[1]]),c35_self={name:sum(selfs[c35base+lo:c35base+hi])for name,lo,hi in sections},entries={name:{symbol:selfs[65536+indexes[name]*4096+(pc&4095)]for pc,symbol in syms.get(name,[])if symbol in ('entry','se_sm_feed','se_bc_query_begin','se_bc_query_step','se_bc_query_ack')}for name in ('inln','sema','geossema')})
   detail['module_inclusive']={name:int(g.dll.cp_module(indexes[name]+1))for name in names if g.dll.cp_module(indexes[name]+1)}
   detail['entries_all']={name:{symbol:selfs[65536+indexes[name]*4096+(pc&4095)]for pc,symbol in syms.get(name,[])if (symbol in ('entry','se_fs_begin','se_fs_guard','se_fs_read','se_sm_feed','se_bc_query_begin','se_bc_query_step','se_bc_query_ack','gsc_cached_carry','bcq_restore_page'))}for name in ('inln','page','rangeio','viewsource','geossema','sema')}
   item=dict(tag=tag,instructions=total,detail=detail,exclusive=by,top_calls=topcalls,crc_calls=crcs,flags=f.get('se_bc_flags',1),queue=f.get('se_bc_count',1))
   cases.append(item);(out/(tag+'.json')).write_text(json.dumps(item,indent=2)+'\n');print('PASS',tag,total,sorted(by.items(),key=lambda x:-x[1]),flush=True)
  result=dict(status='PASS',source_bytes=len(data),dataset=dataset,fixture=str(base),profile_label=profile_label,query_bytes=len(f.assets['inln'][36:]),query_sha256=hashlib.sha256(f.assets['inln'][36:]).hexdigest(),resident=f.report['sha256'],cases=cases,scope='Read-only PC self time and overlapping inclusive JSR callsites; CPU instructions, not cycles. Exact source/pixels/shim and whole16MiB outside published FE spans per case.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--profile-label',default='source-matched');p.add_argument('--dataset',choices=['251','422'],default='251');a=p.parse_args();out=ROOT/'build/cache-lookup53-cost'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.profile_label,a.dataset)

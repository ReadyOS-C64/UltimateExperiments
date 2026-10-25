"""Actual fullpage C26 windows/R14 source requests, no product changes."""
from pathlib import Path
from datetime import datetime,timezone
import json,ctypes as C,subprocess,sys
import test_geos_page_cost_profile as old
import test_geos_semantic_editor as semantic
import test_geos_fold_editor as fold
import test_grid_editor_vice
ROOT=old.ROOT
BASE=ROOT/'build/geos-paint-batch-native-input/20261025T190648774509Z/fixture'
def runner(out):
 old.runner(out);p=out/'runner.cpp';s=p.read_text();s=s.replace('#include <cstdlib>',r'''#include <cstdlib>
static uint16_t iq_active,iq_frame,iq_offset,iq_count;static uint8_t iq_tag,iq_reader;static bool iq_on=false;static uint32_t iq_n=0,iq_v[4096][8];
static uint32_t get24(ZeroPagePeddle*m,uint16_t p){return zeropage_peddle_read(m,p)|(zeropage_peddle_read(m,p+1)<<8)|(zeropage_peddle_read(m,p+2)<<16);}
extern "C" void iq_begin(uint16_t active,uint16_t frame,uint16_t offset,uint16_t count,uint8_t tag,uint8_t reader){iq_active=active;iq_frame=frame;iq_offset=offset;iq_count=count;iq_tag=tag;iq_reader=reader;iq_n=0;iq_on=true;}
extern "C" void iq_end(){iq_on=false;}
extern "C" uint32_t iq_records(uint32_t*out){memcpy(out,iq_v,iq_n*32);return iq_n;}
static void iq(ZeroPagePeddle*m){if(!iq_on)return;auto r=zeropage_peddle_regs(m);uint8_t op=zeropage_peddle_read(m,iq_frame);bool q=r.pc==0xb010&&zeropage_peddle_read(m,iq_active+1)==iq_tag&&(op==0||op==3||op==4);bool read=r.pc==0xa010&&zeropage_peddle_read(m,iq_active)==iq_reader&&op==2;if(!(q||read))return;if(iq_n>=4096)abort();uint32_t*v=iq_v[iq_n++];v[0]=q?26:14;v[1]=op;v[2]=zeropage_peddle_read(m,0x9135);v[3]=get24(m,q?0x8b40:iq_offset);v[4]=zeropage_peddle_read(m,q?0x8b44:iq_count);v[5]=get24(m,0x8b4f);v[6]=get24(m,0x8b4c);v[7]=get24(m,0x8b49);}
''')
 needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);';assert s.count(needle)==1;s=s.replace(needle,needle+'iq(m);');p.write_text(s)
 from peddle import VENDOR
 ext='.dylib'if sys.platform=='darwin'else'.so';q=out/('profile'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(q)],check=True)
 #Load under a new filename to avoid dlopen reusing the old libraryhandle.
 import shutil
 q2=out/('query'+ext);shutil.copy2(q,q2);d=C.CDLL(str(q2));d.gm_run.argtypes=[C.c_void_p,C.c_uint64];d.gm_run.restype=C.c_uint64;d.gm_idle.argtypes=[C.c_void_p,C.c_uint16,C.c_uint64];d.gm_idle.restype=C.c_uint64;d.gm_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];d.gm_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];d.fr_begin.argtypes=[C.c_uint16]*7;d.fr_mask.argtypes=[C.c_void_p];d.fr_bad.restype=d.fr_writes.restype=C.c_uint32;d.iq_begin.argtypes=[C.c_uint16]*4+[C.c_uint8]*2;d.iq_records.argtypes=[C.c_void_p];d.iq_records.restype=C.c_uint32;return d

def run(out,base=BASE):
 fixture,identity=semantic.geos.freeze(out,base);semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=fixture;names=identity['names'];semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=names
 gate=out/'gate';gate.mkdir();dll=runner(gate);f=fold.Fixture(gate,fixture,dll,True);records=[]
 try:
  fonts={n:(fixture/'fonts'/n).read_bytes()for n in semantic.geos.GEOS_FONTS+('native8.bin',)}
  for tag,data in [('diverse422',test_grid_editor_vice.fixture()),('inline408',semantic.INLINE_FIXTURE),('long-lookahead',semantic.geos.native_text('**'+('Wim. '*170)+'end**\rTail.'))]:
   f.source(data);f.command(99);f.position(0);f.put('se_v_top',0);f.render()
   for n in['se_r_valid','se_gc_valid','se_gc_width']:f.put(n,0,1)
   f.m.write(0xCF90,0);f.m.write(0xCFE8,0);canonical,catalog,reu=f.canonical(),f.catalog(),f.reu();f.audit_begin();before=f.total_instructions
   dll.iq_begin(f.s['se_overlay_active'],f.s['se_overlay_frame'],f.s['se_fs_offset'],f.s['se_fs_count'],names.index('geosinln')+1,names.index('viewsource')+1);f.render();dll.iq_end();f.dll.fr_end();f.audit_end(reu,tag)
   assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xC600,1024)==f.shim
   want=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==want[0]and f.read(0x4000,1000)==want[1]
   buf=(C.c_uint32*(4096*8))();count=dll.iq_records(buf);events=[dict(zip(('id','operation','rootrequest','query','count','body','end','start'),list(buf[i*8:i*8+8])))for i in range(count)]
   q=[e for e in events if e['id']==26];reads=[e for e in events if e['id']==14];byworker={str(w):sum(e['count']for e in reads if e['rootrequest']==w)for w in(20,24,25,26)}
   rec=dict(tag=tag,source_bytes=len(data),instructions=f.total_instructions-before,inline_queries=len(q),C20_queries=sum(e['operation']==3 for e in q),C21_queries=sum(e['operation']in(0,4)for e in q),R14_reads=len(reads),requested_source_bytes_by_worker=byworker,events=events);records.append(rec);(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print({k:v for k,v in rec.items()if k!='events'},flush=True)
  result=dict(status='passed',records=records,scope='Read-only instructionobserver ofactualpublicfullpage; independentallpixels/attrs/source/history/catalog/shim+typed16MiBREUguards. Requestedbytecounts includeadapterclamping/shortreads; notactualDMAbytes or walltime. No product/cachecandidateimplementation.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-inline-query-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

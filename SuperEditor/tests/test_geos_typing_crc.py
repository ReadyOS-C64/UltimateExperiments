"""Private whole-table glyph CRC typing candidate against actual packaged root.

Candidate replaces only C6/R30 sidecars; source, IRQ-facing dispatch and producer
are the immutable product. No shared build, native run or latency claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,importlib.util,json,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic

BASE=ROOT/'build/geos-incremental-editor/20261025T093421198503Z/fixture'

def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 def module(name):
  spec=importlib.util.spec_from_file_location('typing_crc_'+name,ROOT/'src/render/geos/typing-crc-candidate'/('build-'+name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 labels,payload,image=module('worker').build(out/'worker',base)
 window,c6=module('c6').build(out/'c6',base)
 assert len(payload)<=4096 and len(window)<=4096
 # Verify every sealed table entry against the existing expanded normal face.
 font=(base/'fonts/bsw9.bin').read_bytes();widths=(base/'fonts/bsw9-widths.bin').read_bytes()
 for code in range(128):
  glyph=bytes(font[code*18+y*2]for y in range(9))+bytes([widths[code]])
  expected=binascii.crc_hqx(glyph,65535)
  actual=payload[labels['gtf_crc_low']-0xa000+code]|payload[labels['gtf_crc_high']-0xa000+code]<<8
  assert actual==expected,('sealedfontCRC',code,actual,expected)
 return payload,image,window,c6

def run(out,base,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen)
 payload,image,window,c6=build(out,frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
 names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};frames=[];faults=[]
 def install(x,seo):
  slot,ident=seo[5:7]
  for i in range(x.s['se_overlay_capacity']):
   if x.m.read(x.s['se_overlay_ids']+i)==ident and x.m.read(x.s['image_slot']+i)==slot:x.m.write(x.s['se_overlay_ids']+i,0)
  x.m.write(x.s['se_overlay_active']+slot,0);x.m.load(x.s['se_overlay_header'],seo[:36]);x.m.load(0x5000,seo[36:]);assert not x.call('se_overlay_import').p&1
 def setup(data,at=7):
  for x in (f,g):x.source(data);x.command(99);x.position(at);x.render()
  install(g,c6);install(g,image)
  assert f.raw_cache()[0][0xea68]==g.raw_cache()[0][0xea68]==0xa5
 def check(tag,byte):
  for x in(f,g):x.key(byte)
  before=[x.canonical()for x in(f,g)];before_reu=[x.reu()for x in(f,g)];start=[x.total_instructions for x in(f,g)];loads=[x.get('se_overlay_loads',2)for x in(f,g)]
  for x in(f,g):x.render()
  counts=[x.total_instructions-a for x,a in zip((f,g),start)];extra_loads=[(x.get('se_overlay_loads',2)-a)&65535 for x,a in zip((f,g),loads)]
  assert f.merged()==g.merged() and f.canonical()==before[0] and g.canonical()==before[1],(tag,'source/history')
  expected,attrs,_,_=semantic.expected(g,g.merged(),fonts)
  assert g.read(0x6000,8000)==f.read(0x6000,8000)==expected,(tag,'allpixels')
  assert g.read(0x4000,1000)==f.read(0x4000,1000)==attrs,(tag,'attributes')
  fc,fp=f.raw_cache();gc,gp=g.raw_cache();assert fc==gc,(tag,'entireFEbank',[(hex(i),a,b)for i,(a,b)in enumerate(zip(fc,gc))if a!=b][:12])
  for x,reu in zip((f,g),before_reu):
   now=x.reu();bank=x.m.read(x.s['se_reu_map']+x.get('se_gc_handle',1));at=bank*65536
   assert now[:at]==reu[:at] and now[at+65536:]==reu[at+65536:],(tag,'otherREU')
   assert x.read(0xc600,1024)==x.shim and not x.get('se_f_owner',1) and x.m.read(0xcf90)==1
  fold.geos.png(expected,attrs,out/(tag+'.png'))
  item=dict(tag=tag,baseline_instructions=counts[0],candidate_instructions=counts[1],reduction=1-counts[1]/counts[0],overlay_loads=extra_loads);frames.append(item);print('PASS',item,flush=True)
 def write_fe(offset,raw):
  g.m.load(0x8080,raw);g.put('se_reu_logical',g.get('se_gc_handle',1),1);g.put('se_reu_offset',offset,2);g.put('se_reu_c64',0x8080,2);g.put('se_reu_length',len(raw),2);assert not g.call('se_reu_copy',0).p&1
 def declined(tag,carry=False):
  before=g.canonical();reu=g.reu();pixels=g.read(0x6000,8000);attrs=g.read(0x4000,1000);gcc=g.m.read(0xcf90);gec=g.m.read(0xcfe8)
  g.m.write(g.s['se_overlay_frame'],3);r,n=g.fast_call(g.s['se_overlay_call'],a=30,x=0)
  assert bool(r.p&1)==carry and (r.a if carry else r.a==2),(tag,r.a,r.p)
  assert g.canonical()==before and g.reu()==reu and g.read(0x6000,8000)==pixels and g.read(0x4000,1000)==attrs and not g.get('se_f_owner',1),(tag,'refusalguard')
  if not carry:assert g.m.read(0xcf90)==gcc and g.m.read(0xcfe8)==gec,(tag,'fallbackcertificate')
  faults.append(dict(tag=tag,code=r.a,carry=r.p&1,instructions=n));print('FAULT',faults[-1],flush=True)
 try:
  data=fold.geos.native_text('Plain row having ample room\rSecond plain row\rTail.')
  setup(data)
  for tag,byte in [('insert-X',fold.geos.native_text('X')[0]),('insert-i',fold.geos.native_text('i')[0]),('backspace',0x14)]:check(tag,byte)
  if not smoke:
   setup(data,data.index(fold.geos.native_text('plain'))+3)
   for tag,byte in [('secondrow-insert',fold.geos.native_text('Q')[0]),('secondrow-delete',0x14)]:check(tag,byte)
   # Every ordinary native letter/digit is authenticated independently, including
   # uppercase aliases that resolve through the real shared PETSCII converter.
   for i,byte in enumerate(fold.geos.native_text('Az09q')):
    check('repeat-'+str(i),byte)
   # Used cached glyph/advance corruption before MARK: C6 prefetches it, but
   # the sealed R30 table must reject it before any derived/source writes.
   for kind in ['glyph','width']:
    setup(data);cache,_=g.raw_cache();code=fold.geos.native(fold.geos.native_text('X')[0]);offset=0xe568+code*9 if kind=='glyph' else 0xe9e8+code
    write_fe(offset,bytes([cache[offset]^1]));g.key(fold.geos.native_text('X')[0]);assert g.m.read(0x9149)==1;declined('cached-'+kind)
   # Bit flips in the retired glyph plane after MARK are also rejected even
   # when the source, FE page and the certificate itself remain unchanged.
   for index in [0,4,8]:
    setup(data);g.key(fold.geos.native_text('X')[0]);g.m.write(0x8b40+10+index,g.m.read(0x8b40+10+index)^1);declined('prefetched-glyph-'+str(index))
   setup(data);g.key(fold.geos.native_text('X')[0]);g.m.write(0x8b43,g.m.read(0x8b43)^1);declined('prefetched-width')
   # Every single bit of the exact nine-row plane and advance is checked by
   # actual 6510 CRC code. The retired certificate is restored, not reissued;
   # no source/cache writes happen in any refusal.
   setup(data);g.key(fold.geos.native_text('X')[0]);cert=g.read(0x9149,47);plane=g.read(0x8b4a,9);advance=g.m.read(0x8b43);reu=g.reu();canonical=g.canonical();pixels=g.read(0x6000,8000);attributes=g.read(0x4000,1000)
   for offset in [3,*range(10,19)]:
    for bit in range(8):
     g.m.load(0x9149,cert);g.m.load(0x8b4a,plane);g.m.write(0x8b43,advance);g.m.write(0x8b40+offset,g.m.read(0x8b40+offset)^(1<<bit));g.m.write(g.s['se_overlay_frame'],3)
     r,n=g.fast_call(g.s['se_overlay_call'],a=30,x=0)
     assert r.a==2 and not r.p&1 and g.m.read(0xcf90)==g.m.read(0xcfe8)==1 and not g.get('se_f_owner',1),(offset,bit,r.a,r.p)
     assert g.canonical()==canonical and g.reu()==reu and g.read(0x6000,8000)==pixels and g.read(0x4000,1000)==attributes
   faults.append(dict(tag='all80-prefetched-glyph-width-bit-flips',cases=80));print('FAULT all80-prefetched bits PASS',flush=True)
   setup(data);g.key(fold.geos.native_text('X')[0]);g.m.write(0x9149+40,g.m.read(0x9149+40)^1);declined('certificate-CRC')
   setup(data);g.key(fold.geos.native_text('X')[0]);g.m.write(g.s['se_doc_original']+1,g.m.read(g.s['se_doc_original']+1)^1);declined('source-generation',True)
  result=dict(status='passed',R30=len(payload),C6=len(window),frames=frames,faults=faults,whole_REU=16777216,shim=1024,scope='Actual immutable packaged root with private C6/R30 replacements; full sealed per-glyph CRC16 table in R30. Independent full pixels, exactFE/source/history and fault refusals. CPU instruction counts only, no native/latency claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(g.read(0,65536));(out/'failure-reu.bin').write_bytes(g.reu());raise
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-typing-crc-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)

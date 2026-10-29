"""Private actual-C6/R31 complete-code-row transaction; C21 language publisher seam."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
from geos_packet import rows
BASE=ROOT/'build/geos-incremental-editor/20261025T095507963106Z/fixture'
def module(name):
 spec=importlib.util.spec_from_file_location('gct_'+name,ROOT/'src/render/geos/code-typing-candidate'/('build-'+name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(out,base,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen);payload,image,budget=module('worker').build(out/'worker',frozen);page=module('page').build(out/'page',frozen);stage=(out/'worker/stage.seo').read_bytes()
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};frames=[];faults=[]
 def install(x,seo):
  slot,ident=seo[5:7]
  for i in range(x.s['se_overlay_capacity']):
   if x.m.read(x.s['se_overlay_ids']+i)==ident and x.m.read(x.s['image_slot']+i)==slot:x.m.write(x.s['se_overlay_ids']+i,0)
  x.m.write(x.s['se_overlay_active']+slot,0);x.m.load(x.s['se_overlay_header'],seo[:36]);x.m.load(0x5000,seo[36:]);assert not x.call('se_overlay_import').p&1
 def setup(data,at):
  for x in(f,g):
   x.source(data);install(x,page);x.command(99);x.position(at);x.render()
  install(g,stage);install(g,image)
  assert g.m.read(0xcfe8)==0
 def write_bank(handle,offset,data):
  g.m.load(0x8080,data);g.put('se_reu_logical',handle,1);g.put('se_reu_offset',offset,2);g.put('se_reu_c64',0x8080,2);g.put('se_reu_length',len(data),2);assert not g.call('se_reu_copy',0).p&1
 def stage_index():
  return next(i for i in range(g.s['se_overlay_capacity'])if g.m.read(g.s['se_overlay_ids']+i)==31 and g.m.read(g.s['image_slot']+i)==1)
 def stage_patch(offset):
  i=stage_index();handle=g.m.read(g.s['se_overlay_asset']+(i>>4));physical=g.m.read(g.s['se_reu_map']+handle);old=g.reu()[physical*65536+(i&15)*4096+offset];write_bank(handle,(i&15)*4096+offset,bytes([old^1]))
 def declined(tag,code=2,carry=False):
  canonical=g.canonical();reu=g.reu();bits=g.read(0x6000,8000);attrs=g.read(0x4000,1000);gcc=g.m.read(0xcf90);gec=g.m.read(0xcfe8);phase=g.read(0x8d00,0x480);owner=g.get('se_f_owner',1)
  g.m.write(g.s['se_overlay_frame'],3);r,n=g.fast_call(g.s['se_overlay_call'],a=31,x=0)
  assert r.a==code and bool(r.p&1)==carry,(tag,r.a,r.p)
  assert g.canonical()==canonical and g.reu()==reu and g.read(0x6000,8000)==bits and g.read(0x4000,1000)==attrs and g.m.read(0xcf90)==gcc and g.m.read(0xcfe8)==gec,(tag,'readonlyfallback')
  assert g.get('se_f_owner',1)==owner and g.read(0xc600,1024)==g.shim,(tag,'owner/shim')
  if owner:assert g.read(0x8d00,0x480)==phase,(tag,'foreignphaseopacity')
  faults.append(dict(tag=tag,code=code,carry=carry,instructions=n));print('FAULT',faults[-1],flush=True)
 def check(tag,key):
  for x in(f,g):x.key(key)
  canonical=g.canonical();reu=g.reu();loads=g.get('se_overlay_loads',2);g.m.write(g.s['se_overlay_frame'],3)
  r,n=g.fast_call(g.s['se_overlay_call'],a=31,x=0)
  assert r.a==0 and not r.p&1,(tag,r.a,r.p,hex(g.m.read(0x8b87)),g.read(0x8d3c,32).hex(),g.read(0x90ca,64).hex())
  assert not g.get('se_f_owner',1) and g.m.read(0xcf90)==1 and g.m.read(0xcfe8)==0 and g.m.read(0xcbd5)==0x41
  assert g.canonical()==canonical,(tag,'source/history/clipboard')
  assert not g.call('se_er_published').p&1
  start=f.total_instructions;f.render();baseline=f.total_instructions-start
  expected,attrs,_,_=semantic.expected(g,g.merged(),fonts)
  gb,ga=g.read(0x6000,8000),g.read(0x4000,1000)
  if gb!=expected or ga!=attrs:
   (out/(tag+'-actual.bin')).write_bytes(gb+ga);(out/(tag+'-expected.bin')).write_bytes(expected+attrs)
   fold.geos.png(gb,ga,out/(tag+'-actual.png'));fold.geos.png(expected,attrs,out/(tag+'-expected.png'))
   raise AssertionError((tag,'pixels',[(i,a,b)for i,(a,b)in enumerate(zip(gb,expected))if a!=b][:12],[(i,a,b)for i,(a,b)in enumerate(zip(ga,attrs))if a!=b][:12]))
  assert gb==f.read(0x6000,8000) and ga==f.read(0x4000,1000),(tag,'forcedrealrenderer')
  fc,_=f.raw_cache();gc,bank=g.raw_cache();fr,gr=rows(fc),rows(gc)
  for i,(a,b) in enumerate(zip(fr,gr)):
   assert a['prefix'][:30]==b['prefix'][:30],(tag,'prefix',i,a['prefix'].hex(),b['prefix'].hex())
   at=0x200+i*0x800;count=a['count']
   for offset,size in [(32,count),(194,count),(356,count),(518,(count+1)*2)]:assert fc[at+offset:at+offset+size]==gc[at+offset:at+offset+size],(tag,'livepacket',i,offset)
  assert fc[:64]==gc[:64],(tag,'header')
  for a,z in [(0xb200+640,0xb200+7680),(0xd140+80,0xd140+960)]:assert fc[a:z]==gc[a:z],(tag,'caret-free-body-base',hex(a))
  now=g.reu();at=bank*65536;assert now[:at]==reu[:at] and now[at+65536:]==reu[at+65536:],(tag,'foreign16MiB')
  assert g.read(0xc600,1024)==g.shim and g.merged()==f.merged()
  fold.geos.png(gb,ga,out/(tag+'.png'));item=dict(tag=tag,instructions=n,baseline_instructions=baseline,loads=(g.get('se_overlay_loads',2)-loads)&65535,source=len(g.merged()));frames.append(item);print('PASS',item,flush=True)
 try:
  for language,line,at in [('basic','10 PRINT "HELLO":REM KEEP','HELLO'),('asm','start: lda #$2A ; comment','comment')]:
   data=fold.geos.native_text('Intro.\r:::'+language+'\r'+line+'\r'+('20 GOTO 10' if language=='basic' else 'next: sta $D020')+'\r:::\rTail.')
   position=data.index(fold.geos.native_text(at))+2;setup(data,position)
   check(language+'-insert',fold.geos.native_text('X')[0]);check(language+'-backspace',0x14)
   if language=='basic' and not smoke:
    # Actual generic overlay CRC failure writes the shared staging window but
    # must preserve C6/R31 executable bytes and retire its borrower namespace.
    i=next(i for i in range(g.s['se_overlay_capacity'])if g.m.read(g.s['se_overlay_ids']+i)==30 and g.m.read(g.s['image_slot']+i)==0)
    h=g.m.read(g.s['se_overlay_asset']+(i>>4));bank=g.m.read(g.s['se_reu_map']+h);off=(i&15)*4096+40;oldbyte=g.reu()[bank*65536+off];write_bank(h,off,bytes([oldbyte^1]));slots=g.read(0xa000,8192);assert g.m.read(0xcbd5)==0x41
    r,n=g.fast_call(g.s['se_overlay_call'],a=30,x=0);assert r.p&1 and g.m.read(0xcbd5)==0 and g.read(0xa000,8192)==slots,('actual CRC-failed5000 fence',r.a)
    faults.append(dict(tag='actual-overlay-CRC-fence',code=r.a,carry=True,instructions=n))
    check('after-CRC-stage-overwrite-insert',fold.geos.native_text('Q')[0]);check('after-CRC-stage-overwrite-delete',0x14)

  if not smoke:
   for language,line,offset in [('basic','10 PRINT "HELLO":REM KEEP',1),('asm','start: lda #$2A ; comment',1)]:
    data=fold.geos.native_text(':::'+language+'\r'+line+'\r:::\rTail.');start=data.index(fold.geos.native_text(line));setup(data,start+len(line))
    check(language+'-CR-insert',fold.geos.native_text('i')[0]);check(language+'-CR-delete',0x14)
   # EOF inside an unclosed code block is still a complete current line.
   data=fold.geos.native_text(':::asm\rlabel: lda #42');setup(data,len(data));check('EOF-insert',fold.geos.native_text('X')[0]);check('EOF-delete',0x14)
   data=fold.geos.native_text(':::basic\r10 PRINT "HI"\r:::\rTail.');at=data.index(fold.geos.native_text('HI'))+1
   for kind in ['owner1','currentguard-GEC0','currentguard-GECFF','currentguard-GCC0','old-language0','language-complement','unbound-source','stage-binding','stage-body','catalog-crc','catalog-owner','physical-owner','stale-epoch','missing-stage','leading-fence-edit','page-source-mismatch']:
    setup(data,at);g.key(fold.geos.native_text('X')[0]);code=2;carry=False
    if kind=='owner1':g.put('se_f_owner',1,1)
    elif kind=='currentguard-GEC0':g.m.write(0xcfe8,0)
    elif kind=='currentguard-GECFF':g.m.write(0xcfe8,255)
    elif kind=='currentguard-GCC0':g.m.write(0xcf90,0)
    elif kind in ('old-language0','language-complement','page-source-mismatch'):
     cache,_=g.raw_cache();row=cache[42];offset=0x200+row*0x800+(30 if kind=='old-language0' else 31 if kind=='language-complement' else 32+5);write_bank(g.get('se_gc_handle',1),offset,bytes([0 if kind=='old-language0' else cache[offset]^1]))
    elif kind=='unbound-source':g.m.write(g.s['se_doc_original']+1,g.m.read(g.s['se_doc_original']+1)^1);code=0x74;carry=True
    elif kind=='stage-binding':stage_patch(0);code=0x11;carry=True
    elif kind=='stage-body':stage_patch(40);code=0x94;carry=True
    elif kind=='catalog-crc':i=stage_index();g.m.write(g.s['image_crc_lo']+i,g.m.read(g.s['image_crc_lo']+i)^1);code=0x94;carry=True
    elif kind=='catalog-owner':h=g.m.read(g.s['se_overlay_asset']+1);g.m.write(g.s['se_reu_logical_owner']+h,99);code=0x18;carry=True
    elif kind=='physical-owner':i=stage_index();h=g.m.read(g.s['se_overlay_asset']+(i>>4));physical=g.m.read(g.s['se_reu_map']+h);g.m.write(g.s['se_reu_physical_owner']+physical,99);code=4;carry=True
    elif kind=='stale-epoch':g.m.write(g.s['asset_epoch'],g.m.read(g.s['asset_epoch'])^1);code=0x18;carry=True
    elif kind=='missing-stage':g.m.write(g.s['se_overlay_ids']+stage_index(),0);code=0x17;carry=True
    elif kind=='leading-fence-edit':
     setup(data,data.index(b'10'));g.key(ord(':'))
    declined(kind,code,carry)
  result=dict(status='passed' ,budget=budget,frames=frames,faults=faults,scope='Private real C21 language publication and actual C6 mutation → explicit R31 root-entry call; no production router/native claim. Independent full pixels and actual full-render reference, exact live packet/header, all16MiB outsideownedFE.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(g.read(0,65536));(out/'failure-reu.bin').write_bytes(g.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-code-typing-transaction'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)

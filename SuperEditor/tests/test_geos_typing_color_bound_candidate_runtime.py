"""Private actualpendingC6/R30supervisor+C32 genuine styled suffix transaction."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,shutil,importlib.util,argparse,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
from geos_packet import rows
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
def run(out,base=BASE,smoke=False):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('style_build',ROOT/'src/render/geos/typing-color-bound-candidate/build-runtime.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'candidate',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};frames=[];faults=[]
 def install(x,seo):
  slot,ident=seo[5:7]
  for i in range(x.s['se_overlay_capacity']):
   if x.m.read(x.s['se_overlay_ids']+i)==ident and (x.m.read(x.s['image_slot']+i)&1)==slot:x.m.write(x.s['se_overlay_ids']+i,0)
  x.m.write(x.s['se_overlay_active']+slot,0);x.m.load(x.s['se_overlay_header'],seo[:36]);x.m.load(0x5000,seo[36:]);assert not x.call('se_overlay_import').p&1
 def setup(text,word):
  data=fold.geos.native_text(text);at=data.index(fold.geos.native_text(word))+2
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
  for tag in('stage','worker','window'):install(g,images[tag])
 def check(tag,key):
  for x in(f,g):x.key(key)
  assert g.m.read(0x9149)==1,(tag,'C6certificate',g.m.read(0x9149))
  canonical=g.canonical();reu=g.reu();loads=g.get('se_overlay_loads',2);g.m.write(g.s['se_overlay_frame'],3);r,n=g.fast_call(g.s['se_overlay_call'],a=30,x=0)
  assert r.a==0 and not r.p&1,(tag,'worker',r.a,r.p,g.read(0x8bcf,32).hex(),g.read(0x8a44,38).hex())
  assert not g.get('se_f_owner',1) and g.m.read(0xcbd5)==0x42 and g.m.read(0xcf90)==1
  assert g.canonical()==canonical and not g.call('se_er_published').p&1
  f.m.write(0xcf90,0);start=f.total_instructions;f.render();baseline=f.total_instructions-start
  expected,attrs,_,_=semantic.expected(g,g.merged(),fonts);gb,ga=g.read(0x6000,8000),g.read(0x4000,1000)
  if gb!=expected or ga!=attrs:
   fold.geos.png(gb,ga,out/(tag+'-actual.png'));fold.geos.png(expected,attrs,out/(tag+'-expected.png'));(out/(tag+'-actual.bin')).write_bytes(gb+ga);(out/(tag+'-expected.bin')).write_bytes(expected+attrs)
   raise AssertionError((tag,'oracle',[(i,a,b)for i,(a,b)in enumerate(zip(gb,expected))if a!=b][:20],[(i,a,b)for i,(a,b)in enumerate(zip(ga,attrs))if a!=b][:20]))
  assert gb==f.read(0x6000,8000) and ga==f.read(0x4000,1000),(tag,'actualforcedfull')
  fc,_=f.raw_cache();gc,bank=g.raw_cache();fr,gr=rows(fc),rows(gc)
  for i,(a,z)in enumerate(zip(fr,gr)):
   assert a['prefix'][:30]==z['prefix'][:30],(tag,'prefix',i,a['prefix'].hex(),z['prefix'].hex())
   at=0x200+i*0x800;count=a['count']
   for offset,size in[(32,count),(194,count),(356,count),(518,(count+1)*2)]:assert fc[at+offset:at+offset+size]==gc[at+offset:at+offset+size],(tag,'packet',i,offset)
  assert fc[:64]==gc[:64],(tag,'header')
  at=bank*65536;now=g.reu();assert now[:at]==reu[:at] and now[at+65536:]==reu[at+65536:],(tag,'foreign16MiB')
  assert g.read(0xc600,1024)==g.shim and g.merged()==f.merged();fold.geos.png(gb,ga,out/(tag+'.png'));item=dict(tag=tag,instructions=n,forced_full_instructions=baseline,loads=(g.get('se_overlay_loads',2)-loads)&65535,source=len(g.merged()));frames.append(item);print('PASS',item,flush=True)
 def write_bank(handle,offset,data):
  g.m.load(0x8080,data);g.put('se_reu_logical',handle,1);g.put('se_reu_offset',offset,2);g.put('se_reu_c64',0x8080,2);g.put('se_reu_length',len(data),2);assert not g.call('se_reu_copy',0).p&1
 def stage_index():return next(i for i in range(g.s['se_overlay_capacity'])if g.m.read(g.s['se_overlay_ids']+i)==32 and (g.m.read(g.s['image_slot']+i)&1)==1)
 def stage_patch(offset):
  i=stage_index();h=g.m.read(g.s['se_overlay_asset']+(i>>4));bank=g.m.read(g.s['se_reu_map']+h);at=(i&15)*4096+offset;old=g.reu()[bank*65536+at];write_bank(h,at,bytes([old^1]))
 def declined(tag,code=2,carry=False):
  canonical=g.canonical();reu=g.reu();bits=g.read(0x6000,8000);attrs=g.read(0x4000,1000);gcc=g.m.read(0xcf90);owner=g.get('se_f_owner',1);phase=g.read(0x8d00,0x480)
  g.m.write(g.s['se_overlay_frame'],3);r,n=g.fast_call(g.s['se_overlay_call'],a=30,x=0)
  assert r.a==code and bool(r.p&1)==carry,(tag,r.a,r.p)
  assert g.canonical()==canonical and g.reu()==reu and g.read(0x6000,8000)==bits and g.read(0x4000,1000)==attrs and g.m.read(0xcf90)==(0 if tag=='source-token'else gcc),(tag,'readonlyfallback')
  assert g.get('se_f_owner',1)==owner and g.read(0xc600,1024)==g.shim,(tag,'owner/shim')
  if owner:assert g.read(0x8d00,0x480)==phase,(tag,'foreignphaseopaque')
  item=dict(tag=tag,code=code,carry=carry,instructions=n);faults.append(item);print('FAULT',item,flush=True)
 try:
  for tag,text,word in [('natural','# Heading\rPlain row having ample room\rTail.','having'),('pangram','# Heading\rA quick brown fox jumps over the lazy dog.\rTail.','brown'),('alpha','# Heading\rAlpha interiorwords omega.\rTail.','interiorwords')]:
   setup(text,word);check(tag+'-insert',fold.geos.native_text('X')[0]);check(tag+'-backspace',0x14)
   if smoke:break
  if not smoke:
   setup('Alpha ***interiorwords*** omega.\rSecond plain row\rTail.','interiorwords')
   check('combined-repeat-insert1',fold.geos.native_text('W')[0]);check('combined-repeat-insert2',fold.geos.native_text('M')[0]);check('combined-repeat-delete1',0x14);check('combined-repeat-delete2',0x14)
   # Conservative lexical authority: ordinary interioralnum edits only when
   # syntax was present. Spaces/punctuation/delimiteredges never mutatecache.
   for tag,text,word,offset,key in[
    ('space-in-styled','Alpha **interiorwords** omega.\rTail.','interiorwords',2,32),
    ('opening-edge','Alpha **interiorwords** omega.\rTail.','interiorwords',0,ord('X')),
    ('closing-edge','Alpha **interiorwords** omega.\rTail.','interiorwords',len('interiorwords'),ord('X')),
    ('delete-style-edge','Alpha **interiorwords** omega.\rTail.','interiorwords',1,0x14),
    ('inlinecode','Alpha @@interiorwords@@ omega.\rTail.','interiorwords',2,ord('X'))]:
    data=fold.geos.native_text(text);at=data.index(fold.geos.native_text(word))+offset
    for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
    for which in('stage','worker','window'):install(g,images[which])
    g.key(key);declined(tag)
   for tag in['foreign-owner1','foreign-owner2','foreign-owner3','GEC0','font-glyph','font-width','stage-binding','stage-body','catalog-crc','catalog-size','catalog-owner','physical-owner','stale-epoch','missing-stage','source-token','certificate-mode2']:
    setup('Alpha **interiorwords** omega.\rSecond plain row\rTail.','interiorwords');g.key(ord('X'));assert g.m.read(0x9149)==1;code=2;carry=False
    if tag=='certificate-mode2':
     g.m.write(0x9149+44,2);v=g.read(0x914a,44);crc=binascii.crc_hqx(v,65535);g.m.write(0x9149+45,crc&255);g.m.write(0x9149+46,crc>>8)
    elif tag.startswith('foreign-owner'):g.put('se_f_owner',int(tag[-1]),1)
    elif tag=='GEC0':g.m.write(0xcfe8,0)
    elif tag.startswith('font-'):
     g.m.write(0x8b4a if tag=='font-glyph'else 0x8b43,g.m.read(0x8b4a if tag=='font-glyph'else 0x8b43)^1)
    elif tag=='stage-binding':stage_patch(0);code=0x11;carry=True
    elif tag=='stage-body':stage_patch(40);code=0x94;carry=True
    elif tag.startswith('catalog-'):
     i=stage_index()
     if tag=='catalog-crc':g.m.write(g.s['image_crc_lo']+i,g.m.read(g.s['image_crc_lo']+i)^1);code=0x94
     elif tag=='catalog-size':g.m.write(g.s['image_size_lo']+i,g.m.read(g.s['image_size_lo']+i)^1);code=0x94
     else:h=g.m.read(g.s['se_overlay_asset']+(i>>4));g.m.write(g.s['se_reu_logical_owner']+h,99);code=0x18
     carry=True
    elif tag=='physical-owner':i=stage_index();h=g.m.read(g.s['se_overlay_asset']+(i>>4));bank=g.m.read(g.s['se_reu_map']+h);g.m.write(g.s['se_reu_physical_owner']+bank,99);code=4;carry=True
    elif tag=='stale-epoch':g.m.write(g.s['asset_epoch'],g.m.read(g.s['asset_epoch'])^1);code=0x18;carry=True
    elif tag=='missing-stage':g.m.write(g.s['se_overlay_ids']+stage_index(),0);code=0x17;carry=True
    elif tag=='source-token':g.m.write(g.s['se_doc_original']+1,g.m.read(g.s['se_doc_original']+1)^1);code=0x74;carry=True
    declined(tag,code,carry)
  result=dict(status='passed',budget=budget,frames=frames,faults=faults,scope='PrivateactualC6 pendingedit → R30explicitentry +typedsealedC32stage. Everypixel/attribute andexactlivepacket againstactualforcedfull andindependenthostmodel, canonical/history/shim/fullforeign16MiB. No integratedrouter/nativeclaim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-c64.bin').write_bytes(g.read(0,65536));(out/'failure-reu.bin').write_bytes(g.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-typing-two-transaction'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.base,a.smoke)

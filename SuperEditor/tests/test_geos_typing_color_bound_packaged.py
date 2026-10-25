"""Private substituted sealed C6/R30/C32, actual public root publication/fallback."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
from geos_packet import rows
BASE=ROOT/'build/geos-incremental-editor/20261025T161722424199Z/fixture'
def run(out,base):
 frozen=out/'fixture';shutil.copytree(base,frozen)
 images={k:(frozen/'build/overlays'/(n+'.seo')).read_bytes()for k,n in [('stage','type'),('worker','gtype'),('window','window')]};budget={k:len(v)-36 for k,v in images.items()};budget['source']='actual packaged immutable images; no private build or substitution'
 assert images['worker'][36:].count(bytes.fromhex('ad4991c902'))==2,'both packaged worker GTC consumers requiregeneration2'
 assert bytes.fromhex('a9028d4991')in images['window'][36:],'packaged producer publishesVALID2'
 identity=json.loads((frozen/'freeze.json').read_text());fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names'];dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def install(x,seo):
  slot,ident=seo[5:7]
  for i in range(x.s['se_overlay_capacity']):
   if x.m.read(x.s['se_overlay_ids']+i)==ident and (x.m.read(x.s['image_slot']+i)&1)==slot:x.m.write(x.s['se_overlay_ids']+i,0)
  x.m.write(x.s['se_overlay_active']+slot,0);x.m.load(x.s['se_overlay_header'],seo[:36]);x.m.load(0x5000,seo[36:]);assert not x.call('se_overlay_import').p&1
 def setup(text,needle,delta):
  data=fold.geos.native_text(text);at=data.index(fold.geos.native_text(needle))+delta
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
  # Actual fixture boot/source() already imported the packaged catalog. No substitutions.
  return data
 def check(tag,key,want):
  for x in(f,g):x.key(key)
  assert f.merged()==g.merged();assert g.m.read(0x9149)==2,(tag,'packaged-certificate-generation2',g.m.read(0x9149));certificate_kind=g.m.read(0x9149+44);canonical=g.canonical();before=g.read(0,65536);reu=g.reu();loads=g.get('se_overlay_loads',2);start=g.total_instructions;g.render();n=g.total_instructions-start;active=g.get('se_overlay_active',1);direct=bool(active)and g.m.read(g.s['se_overlay_ids']+active-1)==30
  assert direct==want,(tag,'actual-public-path',direct,g.m.read(0x9148),g.get('se_e_error',1));assert g.canonical()==canonical
  f.m.write(0xcfe8,0);f.m.write(0xcf90,0);start=f.total_instructions;f.render();full=f.total_instructions-start
  eb,ea,_,_=semantic.expected(g,g.merged(),fonts);assert g.read(0x6000,8000)==eb==f.read(0x6000,8000),(tag,'bitmap');assert g.read(0x4000,1000)==ea==f.read(0x4000,1000),(tag,'attributes')
  # Whole RAM: only the root's declared display/workspace/derived state may move.
  after=g.read(0,65536);allowed=[(2,0x1c),(0x100,0x200),(0x4000,0x43e8),(0x5000,0x9180),(0xa000,0xc600),(0xca00,0xd000),(0xd000,0xe000)];expected=bytearray(before)
  for a,z in allowed:expected[a:z]=after[a:z]
  assert after==expected,(tag,'whole64KiB',[(hex(i),a,z)for i,(a,z)in enumerate(zip(after,expected))if a!=z][:8])
  oldcache,bank=g.raw_cache()
  if direct:
   control,_=f.raw_cache();assert oldcache[:64]==control[:64],(tag,'published-header')
   for index,(a,z)in enumerate(zip(rows(oldcache),rows(control))):
    assert a['prefix'][:30]==z['prefix'][:30],(tag,'cached-prefix',index)
    for field in ['chars','styles','roles','x']:assert a[field]==z[field],(tag,'cached-live-field',index,field)
   assert oldcache[0xb200+640:0xb200+7680]==control[0xb200+640:0xb200+7680],(tag,'body-authoritative-caretfree-base')
  baseoff=bank*65536;now=g.reu();assert now[:baseoff]==reu[:baseoff]and now[baseoff+65536:]==reu[baseoff+65536:],(tag,'foreign16MiB')
  # FE writes are header, packet prefixes/edited live packet, and caret-free
  # body snapshot. Font tables, retired affinity arrays and previewcache stayexact.
  allowed=[(0,64),(0xb200,0xd140)]
  rs=rows(oldcache)
  for i,r in enumerate(rs):allowed.append((0x200+i*0x800,0x200+i*0x800+32))
  if not direct:allowed=[(0,64),(0x200,0xe568)] #actualfull/dirty fallback writes declared pagecache
  expected=bytearray(reu[baseoff:baseoff+65536])
  for a,z in allowed:expected[a:z]=now[baseoff+a:baseoff+z]
  # Edited-row number comes from the certified publication, not a guessedsymbol.
  if direct:
   row=g.m.read(0x8ba1);a=0x200+row*0x800;expected[a:a+842]=now[baseoff+a:baseoff+a+842]
  assert bytes(expected)==now[baseoff:baseoff+65536],(tag,'ownedFEextent',[(hex(i),a,z)for i,(a,z)in enumerate(zip(expected,now[baseoff:baseoff+65536]))if a!=z][:8])
  assert g.read(0xc600,1024)==g.shim and not g.get('se_f_owner',1)and not g.get('se_doc_read_locks',1)
  fold.geos.png(eb,ea,out/(tag+'.png'));cases.append(dict(tag=tag,direct=direct,instructions=n,full_instructions=full,loads=(g.get('se_overlay_loads',2)-loads)&65535,certificate_kind=certificate_kind));print('PASS',cases[-1],flush=True)
 try:
  for name,line,word in [('natural','Plain row having ample room','having'),('pangram','A quick brown fox jumps over the lazy dog.','brown'),('alpha','Alpha interiorwords omega.','interiorwords')]:
   setup('# Heading\r'+line+'\rTail.',word,2);check(name+'-insert',ord('X'),True);check(name+'-delete',0x14,True)
  for marker in ['*','**','***']:
   setup('# Heading\rAlpha '+marker+'interiorwords'+marker+' omega.\rTail.','interiorwords',2);check('styled'+str(len(marker))+'-insert',ord('X'),True);check('styled'+str(len(marker))+'-delete',0x14,True)
  setup('Alpha interiorwords omega.\rSecond source line.\rTail.','interiorwords',2);check('unchanged-allwhite-insert',ord('X'),True);check('unchanged-allwhite-delete',0x14,True);assert cases[-1]['certificate_kind']==0
  # Yellow may remain dominant; changing the winner must decline beforepublish.
  for tag,line,delta,key,want in [('yellow-stable','jjj',2,0x14,True),('yellow-white','jjj',1,ord('X'),False),('white-yellow','jjjjj',2,0x14,False)]:
   setup('# .\r'+line+'\rTail.',line,delta);check(tag,key,want)
  setup('Intro.\rjjj\r- .\rTail.','jjj',2);check('minority-LSN190',0x14,False)
  # Width>192 exercises both complete cachedVICtilebands and repeatpublication.
  for count in [35,38,39]:
   setup('# Heading\r'+'M'*count+'\rTail.','M'*count,count//2);check('dense'+str(count)+'-insert',ord('X'),True);check('dense'+str(count)+'-delete',0x14,True)
  faultcases=[]
  for kind in ['missing-worker','missing-stage','stage-binding','stage-body']:
   original=setup('# Heading\rPlain row having ample room\rTail.','having',2)
   for x in(f,g):x.key(ord('X'))
   canonical=g.canonical();reu=g.reu();pixels=g.read(0x4000,1000)+g.read(0x6000,8000)
   ident=30 if kind=='missing-worker'else 32;slot=0 if ident==30 else 1
   index=next(i for i in range(g.s['se_overlay_capacity'])if g.m.read(g.s['se_overlay_ids']+i)==ident and(g.m.read(g.s['image_slot']+i)&1)==slot)
   if kind.startswith('missing'):g.m.write(g.s['se_overlay_ids']+index,0)
   else:
    handle=g.m.read(g.s['se_overlay_asset']+(index>>4));bank=g.m.read(g.s['se_reu_map']+handle);off=(index&15)*4096+(0 if kind=='stage-binding'else 40);old=g.reu()[bank*65536+off];g.m.load(0x8080,bytes([old^1]));g.put('se_reu_logical',handle,1);g.put('se_reu_offset',off,2);g.put('se_reu_c64',0x8080,2);g.put('se_reu_length',1,2);assert not g.call('se_reu_copy',0).p&1
   damaged=g.reu();r=g.call('se_editor_render');error=g.get('se_e_error',1);assert r.p&1 and error==({'stage-binding':0x11,'stage-body':0x94}.get(kind,0x17)),(kind,r.a,r.p,error)
   assert g.canonical()==canonical and g.reu()==damaged and g.read(0x4000,1000)+g.read(0x6000,8000)==pixels and not g.get('se_f_owner',1)and not g.get('se_doc_read_locks',1),(kind,'failed-publication')
   install(g,images['worker'if ident==30 else 'stage']);g.put('se_e_error',0,1);g.m.write(0xcfe8,0);g.m.write(0xcf90,0);g.render();eb,ea,_,_=semantic.expected(g,g.merged(),fonts);assert g.read(0x6000,8000)==eb and g.read(0x4000,1000)==ea and g.canonical()==canonical,(kind,'recovery-full-render')
   g.typed(fold.geos.native_text('undo'));g.render();assert g.merged()==original and g.read(0xc600,1024)==g.shim,(kind,'recovery-undo')
   faultcases.append(dict(kind=kind,error=error,readonly_failure=True,recovery_undo=True));print('RECOVERY',faultcases[-1],flush=True)
  # Actual canonical undo/redo retains history and reconstructs exactsource.
  original=setup('# Heading\rPlain row having ample room\rTail.','having',2);check('before-undo',ord('X'),True);edited=g.merged()
  for x in(f,g):x.typed(fold.geos.native_text('undo'));x.render()
  assert g.merged()==f.merged()==original and g.read(0xc600,1024)==g.shim
  for x in(f,g):x.typed(fold.geos.native_text('redo'));x.render()
  assert g.merged()==f.merged()==edited and g.read(0x6000,8000)==f.read(0x6000,8000)and g.read(0x4000,1000)==f.read(0x4000,1000)
  result=dict(status='passed',identity=identity,budget=budget,cases=cases,faults=faultcases,undo_redo=True,scope='Actual packaged frozen images without initial substitutions; actual public root dispatch, canonical/history and whole64KiB/16MiB guards plus independent pixels and forcedfull. CPU model; native evidence is separate.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(g.read(0,65536));(out/'failure-reu.bin').write_bytes(g.reu());raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-typing-two-packaged'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve())

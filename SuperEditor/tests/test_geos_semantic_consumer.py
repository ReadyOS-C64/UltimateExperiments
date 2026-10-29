"""Private actual C21 first-classify checkpoint consumption vs original renderer."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
from test_geos_semantic_checkpoint_codec import Fixture as GuardFixture
geos=heading.geos;semantic=heading.semantic;D=ROOT/'src/render/geos/semantic-consumer-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T191455863964Z/fixture';F=0x8b40

def outside_cache(x,before,tag):
 # Current R28 declares dead row backups reserved but unused. Their entire
 # D568..E567 span remains exact; only the64B oldheader is mutable.
 _,bank=x.raw_cache();after=x.reu();allowed=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)];cursor=0
 for a,b in sorted((bank*65536+a,bank*65536+b)for a,b in allowed):
  assert after[cursor:a]==before[cursor:a],(tag,'foreignREU',cursor,a);cursor=max(cursor,b)
 assert after[cursor:]==before[cursor:],(tag,'foreignREUtail')

def exact_pixels(x,data,fonts,tag):
 bits,attrs,rows,_=semantic.expected(x,data,fonts)
 assert x.read(0x6000,8000)==bits and x.read(0x4000,1000)==attrs,(tag,'independentpixels')
 cache,_=x.raw_cache();assert cache[0]==1 and cache[1]==len(rows),(tag,'count')
 for i,row in enumerate(rows):
  p=cache[0x200+i*0x800:0x220+i*0x800]
  assert int.from_bytes(p[:3],'little')==row.start and int.from_bytes(p[3:6],'little')==row.end and int.from_bytes(p[6:9],'little')==row.next and p[14]==row.height and p[15]==row.top,(tag,'allanchors/geometry',i,row,p.hex())
 assert x.get('se_v_bottom')==rows[-1].next,(tag,'bottom')
 return bits,attrs,rows

class Fixture(GuardFixture):
 def __init__(self,*a,**k):self.trace=False;self.events=[];super().__init__(*a,**k)
 def call(self,n,a=0):
  active=self.trace and n=='se_editor_service'and self.get('se_e_job',1)==11 and self.get('se_f_owner',1)==4 and self.m.read(0x9135)==24
  if active:op=self.m.read(0x9136);selector=self.m.read(F+183);before=self.total_instructions
  r=super().call(n,a)
  if active:self.events.append(dict(op=op,selector=selector,proof=self.m.read(F+180),READS=int.from_bytes(self.read(F+164,3),'little'),anchor=int.from_bytes(self.read(F+170,3),'little'),instructions=self.total_instructions-before))
  return r

def run(out,base,smoke=False):
 spec=importlib.util.spec_from_file_location('consumer_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);g=Fixture(out,frozen,dll,True);f.assets['geossema']=(out/'link/seed/geossema.seo').read_bytes();f.assets['geospage']=(out/'link/producer/geospage.seo').read_bytes();fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};cases=[];data=b''
 def setup(raw,at):
  nonlocal data
  data=bytes(raw)
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
 def check(tag,want_hit=None):
  snapshots=[(x.reu(),x.canonical(),x.catalog(),x.total_instructions)for x in(f,g)];f.events=[];f.trace=True
  f.render();f.trace=False;g.m.write(0xcf90,0);g.m.write(0xcfe8,0);g.render();bits,attrs,rows=exact_pixels(f,data,fonts,tag);exact_pixels(g,data,fonts,tag+'-original')
  assert f.merged()==g.merged()==data and f.read(0x6000,8000)==g.read(0x6000,8000)==bits and f.read(0x4000,1000)==g.read(0x4000,1000)==attrs,(tag,'source/pixels')
  for x,(before,canonical,catalog,_)in zip((f,g),snapshots):
   assert x.canonical()==canonical and x.catalog()==catalog and x.read(0xc600,1024)==x.shim and not any(x.get(n,1)for n in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])
   outside_cache(x,before,tag)
  hit=any(e['op']==3 and e['proof']in(1,2)for e in f.events)
  if want_hit is not None:assert hit==want_hit,(tag,'hit',hit,want_hit,f.events)
  geos.png(bits,attrs,out/(tag+'.png'));entry=dict(tag=tag,source_bytes=len(data),TOP=f.get('se_v_top'),hit=hit,instructions=f.total_instructions-snapshots[0][3],original_full_instructions=g.total_instructions-snapshots[1][3],queries=f.events);cases.append(entry);print('PASS',{k:v for k,v in entry.items()if k!='queries'}|{'services':len(f.events)},flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 def edit(tag,key,want_hit=True):
  nonlocal data
  at=f.get('se_hot_caret');assert g.get('se_hot_caret')==at
  if key==0x14:data=data[:at-1]+data[at:]
  else:data=data[:at]+bytes([key])+data[at:]
  for x in(f,g):x.key(key)
  check(tag,want_hit)
 try:
  raw=geos.native_text('# Heading words.\rFollowing row.\rTail.');setup(raw,5);edit('near-body-insert',geos.native_text('Q')[0]);edit('near-body-BACK',0x14)
  if not smoke:
   setup(raw,5);edit('near-CR-split',13)
   setup(raw,0);edit('near-prefix-class-change',geos.native_text('Q')[0])
   pre=geos.native_text('prefix\r')*9400;raw=pre+geos.native_text('# Heading words.\rFollowing row.\rTail.');setup(raw,len(pre)+5);edit('far-body-insert',geos.native_text('Q')[0]);edit('far-body-BACK',0x14)
   setup(raw,len(pre)+5);edit('far-CR-split',13)
  result=dict(status='passed',budget=budget,cases=cases,identity=identity,scope='Actual public mode3/C6/C21/C24/R14 with two privately sealed SEO replacements, originalfullrenderer plus independentpixel/canonical/source oracle, exactsource/catalog/shim/whole16MiB scopes. No C23 or publicpreflushrouting changed.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-semantic-consumer'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve(),a.smoke);print('RESULT',r['status'],r['budget'],'cases',len(r['cases']))

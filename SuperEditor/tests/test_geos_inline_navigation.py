"""Frozen actual C24 full-event marker and public styled C23 metric/hit gate.

Independent canonical block/inline/font model; no emitted arrays choose targets.
No shared build, VICE, pixel/native or physical-key claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,zipfile
import test_geos_editor as geos
import test_geos_semantic_editor as semantic
from supermark_model import blocks
ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T033116850492Z/fixture'
F=0x8B40;L=0x8D00


def run(out,previous=DEFAULT,smoke=False):
 frozen,identity=geos.freeze(out,previous);assert len(identity['names'])==32
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);widths=(frozen/'fonts/bsw9-widths.bin').read_bytes()
 markers=[];moves=[];hits=[];pages=[];f=None
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 class Fixture(geos.Fixture):
  def __init__(self,*a):self.requests=[];self.hits=[];self.host_data=b'';super().__init__(*a)
  def call(self,name,a=0):
   job=self.get('se_e_job',1)
   req=(self.m.read(0x9135),self.m.read(0x9136)) if name=='se_editor_service' and job==12 else None
   if req:self.requests.append(req)
   want=None
   if req==(20,3):
    data=self.host_data;cls=semantic.classify(data);start=int.from_bytes(self.read(L+4,3),'little')
    advance=[8 if cls.code[i] else widths[geos.native(v)]+(cls.styles[i]&1)+(cls.styles[i]&2) for i,v in enumerate(data)]
    mode=self.m.read(L);pan=int.from_bytes(self.read(L+7,3),'little')
    row=geos.line_break(data,advance,start,320,mode,pan,-1,0)
    count=int.from_bytes(self.read(L+50,2),'little');maps=[int.from_bytes(self.read(L+176+i*2,2),'little') for i in range(count+1)]
    assert maps==row['maps'],('public HIT map',start,maps,row['maps'])
    assert int.from_bytes(self.read(L+47,3),'little')==row['first']
    x=min(320,int.from_bytes(self.read(L+30,2),'little'));idx=min(range(len(maps)),key=lambda i:(abs(row['maps'][i]-x),-i))
    want=(row['first']+idx,start,x)
   r=super().call(name,a)
   if want:
    actual=int.from_bytes(self.read(L+56,3),'little');assert actual==want[0],('public HIT source',actual,want)
    self.hits.append(dict(start=want[1],x=want[2],source=actual))
   return r
 def start(data,caret=0,geosmode=False):
  nonlocal f
  if f:f.close()
  f=Fixture(out,frozen,dll,True);f.source(data);f.host_data=data
  if caret:f.position(caret)
  if geosmode:f.command(99);f.render()
 def marker(data,anchor,reuse=False):
  f.put('se_f_owner',4,1)
  if reuse:f.m.load(F,anchor.to_bytes(3,'little')+b'\x02\xA0')
  else:f.m.load(F,anchor.to_bytes(3,'little')+b'\x02\xA0'+bytes([0xA5])*187);f.m.write(F+28,0)
  f.m.load(0x8D00,bytes([0xDA])*832)
  parent=bytes((i*31+17)&255 for i in range(68));scratch=bytes((i*47+29)&255 for i in range(768))
  f.m.load(0x9134,parent);f.m.load(0x8100,scratch)
  canonical,reu,catalog=f.canonical(),whole(),f.catalog()
  def invoke(op):
   f.put('se_overlay_frame',op,1);r,_=f.fast_call(f.s['se_overlay_call'],a=24,x=1)
   assert f.read(0x8100,768)==scratch and f.read(0xC600,1024)==f.shim
   p=f.read(0x9134,68);assert p[:1]+p[3:]==parent[:1]+parent[3:]
   return r
  r=invoke(0);steps=0
  while r.a and not r.p&1:r=invoke(1);steps+=1;assert steps<len(data)//32+10
  assert not r.p&1,('C24 query',anchor,hex(r.a))
  event=next((e for e in blocks(data) if e['start']<=anchor<=e['end']),None)
  if event is None:assert anchor==len(data) and (not data or data[-1]==13);a=b=anchor
  else:a,b=event['start'],event['end']
  want=int(any(c in b'*@' for c in data[a:b]));actual=f.m.read(F+169)
  assert actual==want,('full logical event marker',anchor,a,b,actual,want,data[a:b])
  assert (int.from_bytes(f.read(F+9,3),'little'),int.from_bytes(f.read(F+12,3),'little'))==(a,b)
  assert f.canonical()==canonical and whole()==reu and f.catalog()==catalog
  assert not f.get('se_doc_read_locks',1) and not f.m.read(0x912D)
  reads=int.from_bytes(f.read(F+164,3),'little');f.put('se_f_owner',0,1)
  record=dict(anchor=anchor,start=a,end=b,marker=actual,reads=reads,steps=steps,reuse=reuse);markers.append(record);return record
 def cache_markers(data):
  cache,_=f.cache();cls=semantic.classify(data);records=[]
  for i in range(cache[1]):
   p=cache[0x200+i*0x800:0x220+i*0x800];start=int.from_bytes(p[:3],'little')
   event=next((e for e in cls.events if e['start']<=start<=e['end']),None)
   want=int(event is not None and any(c in b'*@' for c in data[event['start']:event['end']]))
   assert p[23]==want,('GPR_INLINE23',i,start,p[23],want)
   records.append(dict(start=start,inline=p[23]))
  pages.append(dict(top=f.get('se_v_top'),records=records))
 def render(data):
  before,catalog,reu=f.canonical(),f.catalog(),whole();f.render();assert f.canonical()==before and f.catalog()==catalog
  assert f.merged()==data and f.read(0xC600,1024)==f.shim
  cache_markers(data);after=whole();_,bank=f.cache();pos=0;start_=bank*65536
  for a,b in [(start_,start_+64)]+[(start_+0x200+i*0x800,start_+0x200+(i+1)*0x800) for i in range(22)]:
   assert after[pos:a]==reu[pos:a];pos=b
  assert after[pos:]==reu[pos:]
 def vertical(data,cmd,preferred=None,expect_semantic=None):
  old=f.get('se_hot_caret');target,wanted,index,rows=semantic.navigation(data,widths,old,cmd,preferred)
  # No flush is needed for a committed source; pending typing is exercised
  # separately, where a legitimate public navigation flush updates history.
  pending=f.get('se_hot_pending',1);before=f.canonical();catalog,reu=f.catalog(),whole();f.requests=[];f.hits=[]
  f.command(cmd)
  assert f.get('se_hot_caret')==target,('styled target',old,cmd,target,f.get('se_hot_caret'))
  assert f.get('se_l_preferred')==wanted and f.get('se_n_preferred_valid',1)==2
  assert f.merged()==data and f.catalog()==catalog and f.read(0xC600,1024)==f.shim
  if not pending:assert whole()==reu #navigation only reads authenticated FE cache
  count=sum(id_==24 for id_,op in f.requests)
  if expect_semantic is not None:assert bool(count)==expect_semantic,('C24 cached route',old,cmd,count,expect_semantic,f.requests)
  assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job'])
  moves.append(dict(before=old,command=cmd,target=target,row=index,preferred=wanted,C24_service_calls=count,requests=f.requests))
  hits.extend(f.hits);render(data);return wanted
 try:
  data=geos.native_text('plain\r'+('x'*150)+' **late**\r# '+('y'*135)+' @\r- **item**\rEOF *tail*')
  start(data)
  anchors=[0,6,38,134,160,data.index(13,6),data.index(b'#'),data.index(b'-'),len(data)]
  for anchor in anchors:marker(data,anchor)
  # Last-event certificate retains the full-event marker even when the marker
  # was beyond the first32/128 bytes and the next query needs no actual READ.
  a=data.index(b'#');assert marker(data,a)['marker']==1
  assert marker(data,a+1,True)['reads']==0
  assert marker(data,a+100,True)['reads']==0
  assert marker(data,data.index(b'-'),True)['marker']==1
  assert marker(data,0,True)['reads']>0
  for suffix in ['\r','\rplain\r','\r*late*','\rplain']:
   d=geos.native_text('@@code@@'+suffix);start(d)
   for anchor in [0,len(d)-1,len(d)]:marker(d,anchor)
  d=geos.native_text('*changed*\rplain');start(d);marker(d,0);assert marker(d,1,True)['reads']==0
  f.put('se_r_revision',f.get('se_r_revision',4)+1,4);assert marker(d,2,True)['reads']>0
  f.put('se_l_mode',1,1);assert marker(d,3,True)['reads']>0
  f.put('se_l_mode',0,1);assert marker(d,4,True)['reads']>0
  f.position(0);f.key(ord('Q'));d=b'Q'+d;assert f.get('se_hot_pending',1);assert marker(d,5,True)['reads']>0
  # A forward certificate must clear a previous event's marker on plain text.
  d=geos.native_text('**yes**\rplain\r@tail');start(d);marker(d,0)
  assert marker(d,8,True)['marker']==0
  assert marker(d,10,True)['marker']==0 and marker(d,10,True)['reads']==0
  assert marker(d,len(d),True)['marker']==1
  # Canonical source-only independent GG metrics, including markers beyond a
  # physical32B packet and beyond128B. Public C23 invokes actual C20 HIT.
  data=geos.native_text('**WWWW** iii *italic*\r***bold italic*** narrow\r'+('Wim '*40)+' **late close**\r'+('Tail *narrow*\r'*4))
  start(data,5,True);render(data);preferred=None
  for cmd in [37,37,37,36,36,37]:preferred=vertical(data,cmd,preferred,True)
  if not smoke:
   # Public GOTO is exact canonical logical start; RIGHT remains source-affine.
   line=3;f.typed(geos.native_text('goto '+str(line)));wanted=data.index(13,data.index(13)+1)+1
   assert f.get('se_hot_caret')==wanted,('public GOTO',f.get('se_hot_caret'),wanted);render(data)
   f.key(ord('Q'));at=wanted;data=data[:at]+b'Q'+data[at:];f.host_data=data
   assert f.get('se_hot_pending',1);render(data);vertical(data,37,None,True)
   # GOTO above enters internal E_POSITION reveal through its supported public
   # command-line route. Command47 itself is intentionally not a public ID.
   # Long plain page: authenticated GPR_INLINE0 skips C24 on both cached rows,
   # even beyond64KiB. This guards against per-arrow cold semantic scans.
   data=b'x'*65530+geos.native_text('\rWim plain\rIII\rTail\r');start(data,65535,True);render(data)
   preferred=vertical(data,37,None,False);vertical(data,36,preferred,False)
  result=dict(status='passed',identity=identity,marker_queries=markers,public_moves=moves,actual_HITs=hits,pages=pages,full_REU_guard_bytes=16*1024*1024,scope='Actual frozen C24 marker169/GPR23 and public C23 styled metric/HIT navigation; no raster/native claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  archive=ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-inline-navigation');archive.mkdir(parents=True)
  shutil.copy2(out/'result.json',archive/'result.json');shutil.copy2(Path(__file__),archive/Path(__file__).name)
  for name in ['freeze.json','product-sources.zip']:shutil.copy2(frozen/name,archive/name)
  pointer=dict(status='passed',evidence=str(archive.relative_to(ROOT)),prg_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],marker_queries=len(markers),moves=len(moves),actual_HITs=len(hits))
  (ROOT/'agentsworking/evidence/M7/geos-inline-navigation-checkpoint.json').write_text(json.dumps(pointer,indent=2)+'\n');print(json.dumps(pointer,indent=2));return result
 finally:
  if f:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-inline-navigation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture,a.smoke)

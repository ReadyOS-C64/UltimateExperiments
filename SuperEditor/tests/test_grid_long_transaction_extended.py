"""Exact private long-prose caller/fault/ownership test; no shared assets."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,shutil,hashlib,binascii,importlib.util,argparse
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/geos-preflush-product/20261025T193429355750Z/fixture'
def run(out,previous=None):
 if previous:
  frozen,ident=fold.geos.freeze(out,previous)
  budget={n:dict(payload=len((frozen/'build/overlays'/(n+'.seo')).read_bytes())-36,sha256=ident['assets'][n])for n in('styler','viewsource','geostail','grid')}
 else:
  frozen=out/'fixture';shutil.copytree(BASE,frozen);spec=importlib.util.spec_from_file_location('longbuild',ROOT/'src/render/grid/long-prose-candidate/build-long.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen);ident=json.load(open(frozen/'freeze.json'))
  for n,image in seos.items():(frozen/'build/overlays'/(n+'.seo')).write_bytes(image);ident['assets'][n]=hashlib.sha256(image).hexdigest()
  (frozen/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
 dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];f=fold.Fixture(out,frozen,dll,True);cases=[];faults=[]
 def ready():f.render();f.finish_style()
 def setup(raw,width,at):
  f.source(raw);f.command(97 if width==60 else 98);f.position(at);ready();assert f.merged()==raw
 def bank():
  h=f.get('se_gc_handle',1);assert h and f.m.read(f.s['se_reu_logical_owner']+h)==254;z=f.m.read(f.s['se_reu_map']+h);assert z and f.m.read(f.s['se_reu_physical_owner']+z)==254;return z
 def check(tag,expected,before,canonical,mode='accepted'):
  want,attrs=grid.expected(f,expected)[0];bits=f.read(0x6000,8000);at=f.read(0x4000,1000)
  assert bits==want,(tag,'bitmap',[(i,a,z)for i,(a,z)in enumerate(zip(bits,want))if a!=z][:12]);assert at==attrs,(tag,'attrs');assert f.merged()==expected and f.canonical()==canonical and f.read(0xc600,1024)==f.shim,(tag,'source/shim')
  after=f.reu();start=bank()*65536;allowed=bytearray(before)
  for lo,hi in [(0,22*240),(0x1500,0x1680)]:allowed[start+lo:start+hi]=after[start+lo:start+hi]
  assert bytes(allowed)==after,(tag,'whole16MiB + exact FE extent',[(i,a,z)for i,(a,z)in enumerate(zip(allowed,after))if a!=z][:4])
  cert=after[start+0x1600:start+0x1680];assert cert[:4]==b'SP\2\xa5' and binascii.crc_hqx(cert[:126],65535)==int.from_bytes(cert[126:],'little');assert cert[4:37]==f.read(f.s['se_st_descriptor'],33)and cert[42:111]==f.read(f.s['se_v_rows'],66)+f.read(f.s['se_v_bottom'],3)
 def edit(tag,key):
  f.key(key);expected=f.merged();canonical=f.canonical();before=f.reu();loads=f.get('se_overlay_loads',2);start=f.total_instructions;f.render();first=f.total_instructions-start
  assert f.m.read(0x89ff)==2,(tag,'actual long transaction',f.m.read(0x89ff),f.debug());f.finish_style();r=dict(tag=tag,key=key,first_instructions=first,settled_instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,caret=f.get('se_hot_caret'),top=f.get('se_v_top'));assert r['first_instructions']==r['settled_instructions'],(tag,'no deferred wholeparser work');check(tag,expected,before,canonical);cases.append(r);print('PASS',r,flush=True)
 try:
  prefix=grid.native_text(':::basic\r10 PRINT 1\r:::\r:::asm\rlda #1\r:::\r:::region Closed\rregion body\r:::end\r')
  for width in(60,80):
   for tag,p,chars,offset in [('body',prefix,506,2*width+10),('early',b'',3*width+9,10),('bottom',b'',23*width+9,20*width+10),('graphics',b'',5*width+9,width+11)]:
    body=grid.native_text('Alpha '+('word '*((chars+4)//5)))[:chars]
    if tag=='graphics':body=body[:50]+bytes((0xa0,0xff,0x5f,0xe0))+body[54:]
    raw=p+body+grid.native_text('\rTail.');setup(raw,width,len(p)+offset)
    for k in(81,82,20,20):edit(str(width)+'-'+tag+'-'+str(k),k)
  high=grid.native_text(':::asm\r')+b'X'*65540+grid.native_text('\r:::\rAlpha ')+grid.native_text('word '*110)+grid.native_text('ends.\rTail.')
  for width in(60,80):
   at=high.index(grid.native_text('Alpha'))+2*width+10;setup(high,width,at);edit(str(width)+'-far-insert',81);edit(str(width)+'-far-back',20)
  huge=grid.native_text('Alpha '+('word '*14000)+'\rTail.')
  setup(huge,80,69080);edit('80-logicalspan-over64KiB-insert',81);edit('80-logicalspan-over64KiB-back',20)
  # Refusals are actualC33publicentry. Derivedphase scratch may change only
  # after owner4; noVIC/source/history/cache publication is allowed.
  normal=grid.native_text('Alpha '+('word '*90)+'\rTail.');at=172
  def miss(tag,raw=normal,pos=at,key=81,change=None):
   setup(raw,80,pos);f.key(key)
   if change:change()
   source=f.canonical();before=f.reu();opaque=f.read(0x8880,0x400)+f.read(0x8d00,0x480);pixels=f.read(0x6000,8000)+f.read(0x4000,1000);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1);assert r.a==2 and not r.p&1,(tag,'optional miss',r.a,r.p);assert before==f.reu()and pixels==f.read(0x6000,8000)+f.read(0x4000,1000)and source==f.canonical(),(tag,'readonly refusal');
   if tag=='se_f_owner':assert opaque==f.read(0x8880,0x400)+f.read(0x8d00,0x480),(tag,'phase/scratch owneropacity')
   faults.append(dict(tag=tag,instructions=n));print('MISS',tag,n,flush=True)
  for tag,raw,pos,key in [('inline-late',normal[:-10]+b'*'+normal[-9:],at,81),('escape-late',normal[:-10]+b'\\'+normal[-9:],at,81),('structural-space',normal,at,32),('caret-right-edge',normal,159,81),('caret-left-edge',normal,160,81),('wrap-growth',b'A'*239+b'\rTail.',12,81),('wrap-shrink',b'A'*240+b'\rTail.',12,20),('bottom-tailCR',b'A'*1760+b'\rTail.',1600+10,20)]:miss(tag,raw,pos,key)
  def cert_fault(offset,recrc=True):
   z=bank();q=bytearray(f.reu()[z*65536+0x1600:z*65536+0x1680]);q[offset]^=1
   if recrc:q[126:]=binascii.crc_hqx(q[:126],65535).to_bytes(2,'little')
   f.m.load(0x8b00,q);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',0x1600,2);f.put('se_reu_c64',0x8b00,2);f.put('se_reu_length',128,2);assert not f.call('se_reu_copy',0).p&1
  for offset in(2,3,4,20,25,37,39,41,42,126):miss('SP2-field-'+str(offset),change=lambda o=offset:cert_fault(o,o!=126))
  for name,w,v in [('se_f_owner',1,1),('se_f_owner',1,2),('se_f_owner',1,3),('se_f_owner',1,4),('se_sel_mark',1,1),('se_ef_valid',1,1),('se_reu_retired',1,1),('se_st_request',1,1),('se_st_valid',1,0),('se_hot_delete',1,2)]:miss(name,change=lambda n=name,w=w,v=v:f.put(n,v,w))
  for tag,change in [('FElogical',lambda:f.m.write(f.s['se_reu_logical_owner']+f.get('se_gc_handle',1),253)),('FEphysical',lambda:f.m.write(f.s['se_reu_physical_owner']+bank(),253)),('FEepoch',lambda:f.put('se_gc_epoch',f.get('se_gc_epoch',2)^1,2)),('attribute',lambda:f.m.write(0x4000+40*(f.get('se_v_caret_row',1)+2)+15,0x76))]:miss(tag,change=change)
  # Actual history replay and ordinarycaret publication after the new packet
  # commit must agree with the independentfullrender, then re-admit nextedit.
  replay=[]
  raw=grid.native_text(':::asm\rlda #1\r:::\rAlpha '+('word '*100)+'ends.\rTail.');at=raw.index(grid.native_text('Alpha'))+172
  setup(raw,80,at);edit('pre-undo-insert',81)
  for command in(16,17):
   f.command(command);ready();expected=f.merged();want,attrs=grid.expected(f,expected)[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs and f.read(0xc600,1024)==f.shim;replay.append(dict(command=command,source_sha256=hashlib.sha256(expected).hexdigest()))
  edit('post-redo-insert',82)
  motions=[]
  for key in(0x1d,0x9d):
   f.key(key);expected=f.merged();f.render();f.finish_style();want,attrs=grid.expected(f,expected)[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs;motions.append(dict(key=key,caret=f.get('se_hot_caret')))
  # Force old catalog producer metadata while a genuinely completed SC2
  # remains: the new consumer must decline before even its phase borrowing.
  for producer in('styler','viewsource','geostail'):
   old=(BASE/'build/overlays'/(producer+'.seo')).read_bytes();idx=ident['names'].index(producer)
   def substitute(o=old,j=idx):
    f.m.write(f.s['image_size_lo']+j,o[8]);f.m.write(f.s['image_size_hi']+j,o[9]);f.m.write(f.s['image_crc_lo']+j,o[12]);f.m.write(f.s['image_crc_hi']+j,o[13]);f.m.write(f.s['image_slot']+j,o[5]|128)
   miss('mixed-old-'+producer+'-catalog-with-retained-SC2',change=substitute)
  # C14/R14 must have actually passed immutablebacking verification; raw
  # payload metadata alone cannot certify a publisher which never executed.
  for producer in('styler','viewsource'):
   j=ident['names'].index(producer);miss('unverified-'+producer,change=lambda j=j:f.m.write(f.s['image_slot']+j,f.m.read(f.s['image_slot']+j)&127))
  result=dict(status='passed',identity=ident,budget=budget,cases=cases,faults=faults,replay=replay,motions=motions,packaged_fixture=bool(previous),scope='Bounded no-inline SM_PROSE reflow within retained22rows; no wrap-rowcount change,selection,fold,pan or mixedroles. --fixture runs actual packaged images without substitutions.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);a=p.parse_args();out=ROOT/'build/grid-long-transaction-extended'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)

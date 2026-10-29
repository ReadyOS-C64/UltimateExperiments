"""Private actual raw short-row typing authority; no parser/cache carry fiction."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,inspect,hashlib,binascii,shutil
import test_grid_plain_caret as caret
ROOT=caret.ROOT

def matrix(out,base,actions=('right','down','up','insert','delete')):
 source=inspect.getsource(caret.profile.run)
 def rep(a,b):
  nonlocal source
  assert source.count(a)==1,a;source=source.replace(a,b)
 rep('for mode in ([2]if smoke else(0,2,3)):', 'for mode in (1,2):')
 rep("for action in ('right','down','up','insert'):", 'for action in ACTIONS:')
 rep("'insert':observer.Q}[action]", "'insert':observer.Q,'delete':20}[action]")
 rep("source=data[:at]+bytes((key,))+data[at:]if action=='insert'else data", "source=data[:at]+bytes((key,))+data[at:]if action=='insert'else data[:at-1]+data[at:]if action=='delete'else data")
 rep("if action!='insert':assert g.stable()==stable", "if action not in ('insert','delete'):assert g.stable()==stable")
 rep("if action=='insert':f.command(16);", "if action in ('insert','delete'):f.command(16);")
 rep("at=f.get('se_hot_caret');before=", "semantic_before=f.read(f.s['se_st_descriptor'],37);at=f.get('se_hot_caret');before=")
 rep("used=f.total_instructions-initial;", "assert caps!=0 or f.get('se_st_valid',1)==0;used=f.total_instructions-initial;")
 rep('out.mkdir(parents=True)','out.mkdir(parents=True,exist_ok=True)')
 out.mkdir(parents=True);(out/'executed-profile.py').write_text(source)
 ns=dict(caret.profile.__dict__,ACTIONS=actions);exec(compile(source,str(out/'executed-profile.py'),'exec'),ns);return ns['run'](out,base)

def operations(out,base):
 out.mkdir();g=caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 def setup(data,width,at):
  f.source(data,physical=256);f.typed(caret.profile.observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);caret.profile.drain(f);f.position(at);caret.profile.drain(f)
 def packetbase():
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));return bank*65536
 def pixels(data,tag):
  (bits,attrs),_,_,_=caret.profile.observer.geos.grid.expected(f,data)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
  return hashlib.sha256(bits+attrs).hexdigest()
 try:
  for width in (60,80):
   specs=[('ordinary-'+str(k),b'Alpha words.\rTail.',5,k)for k in(32,34,39,42,64,92,46,44,33,63,20)]
   specs += [('column0',b'Alpha words.\rTail.',0,81),('endCR',b'Alpha words.\rTail.',12,81),('endEOF',b'Alpha words.',12,32),('emptyCR',b'\rTail.',0,81),('emptyEOF',b'',0,81),('rawmarkers',b'* @ \\ words\rTail.',5,32),('lastsafe',b'A'*(width-2)+b'\rTail.',width-2,81),('lastdelete',b'A'*(width-1)+b'\rTail.',width-1,20)]
   high=b'Prefix\r'*9400+b'Alpha words.\rTail.';specs += [('above64KiB',high,len(b'Prefix\r')*9400+5,64)]
   for tag,data,at,key in specs:
    setup(data,width,at);phase=f.read(0x8d00,1152);start=f.total_instructions;loads=f.get('se_overlay_loads',2);before=g.audit_begin();sem=f.read(f.s['se_st_descriptor'],37);raw=g.reu();fe=packetbase();sp=raw[fe+0x1600:fe+0x1680]
    f.key(key);caret.profile.drain(f);g.audit_end(before,tag);expected=data[:at]+bytes((key,))+data[at:]if key!=20 else data[:at-1]+data[at:]
    assert f.merged()==expected and f.get('se_st_valid',1)==0 and f.read(f.s['se_st_descriptor'],37)==sem,(tag,'source/semantic')
    assert f.m.read(0x89ff)==1,(width,tag,'actual raw branch')
    now=g.reu();want=bytearray(raw);row=f.get('se_v_caret_row',1)
    for lo,hi in((fe+row*240,fe+(row+1)*240),(fe+0x1500,fe+0x1600)):
     want[lo:hi]=now[lo:hi]
    # Input history/source edits are independently covered by exact checked-DMA
    # masks above. Across the paint transaction itself, source writes may have
    # occurred before snapshot; raw must not publish or rekey SP2 authority.
    assert now[fe+0x1600:fe+0x1680]==sp and f.read(0x8d00,1152)==phase,(tag,'no SP2/phase publication')
    digest=pixels(expected,tag);assert now[fe+0x1500+253]==0
    item=dict(width=width,tag=tag,key=key,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,pixels=digest);cases.append(item);print('RAW PASS',item,flush=True)
    f.command(16);caret.profile.drain(f);assert f.merged()==data;pixels(data,tag+'-undo')
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()

def faults(out,base):
 out.mkdir();g=caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 def setup(width=80,caps=0,text=b'Alpha words.\rTail.',at=5,key=81):
  f.source(text,physical=256);f.typed(caret.profile.observer.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(97 if width==60 else 98);caret.profile.drain(f);f.position(at);caret.profile.drain(f)
  f.put('se_hot_byte',key,1)
  if key==20:assert not f.call('se_hot_call',4).p&1
  else:assert not f.call('se_hot_call',3).p&1
 def header():return f.raw_cache()[0][0x1500:0x1600]
 def write(raw,offset):
  f.m.load(0x8a00,raw);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8a00,2);f.put('se_reu_length',len(raw),2);assert not f.call('se_reu_copy',0).p&1
 def corrupt(offset,value=None,crc=False):
  h=bytearray(header());h[offset]=h[offset]^1 if value is None else value
  if crc:h[254:]=binascii.crc_hqx(h[:254],65535).to_bytes(2,'little')
  write(h,0x1500)
 def slot(ident,kind):return next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==kind)
 def snap():return(f.canonical(),g.reu(),f.read(0x6000,8000)+f.read(0x4000,1000),f.read(0x8d00,1152))
 def invoke():
  f.put('se_overlay_frame',1,1);return f.fast_call(f.s['se_overlay_call'],a=33,x=1)
 try:
  for width in (60,80):
   for tag in ('caps-CRC','caps-validCRC-full','caps-validCRC-markdown','livecaps-changed','header-source','header-epoch','header-length','header-revision','header-row','header-CRC','packet-CRC','packet-role','packet-flag','selection','fold','pan','nowrap','manual','foreign-owner','retired','FE-owner','FE-epoch','FE-map','bad-font','missing-helper','bad-helper','double-revision','wrong-delete','pending0','source-CR','softwrap'):
    setup(width,text=b'A'*100+b'\rTail.'if tag=='softwrap'else b'Alpha words.\rTail.',key=13 if tag=='source-CR'else 81)
    owner=0
    if tag=='caps-CRC':corrupt(253)
    if tag=='caps-validCRC-full':corrupt(253,3,True)
    if tag=='caps-validCRC-markdown':corrupt(253,1,True)
    if tag=='livecaps-changed':f.put('se_render_caps',3,1)
    for label,offset in [('header-source',4),('header-epoch',28),('header-length',25),('header-revision',21),('header-row',124)]:
     if tag==label:corrupt(offset,crc=True)
    if tag=='header-CRC':corrupt(254)
    if tag.startswith('packet-'):
     h=header();row=h[200];raw,_=f.raw_cache();offset=row*240+{'packet-CRC':0,'packet-role':80,'packet-flag':160}[tag];packet=bytearray(raw[row*240:(row+1)*240]);packet[offset-row*240]^=1;write(packet,row*240)
     if tag!='packet-CRC':
      h=bytearray(header());h[209+row*2:211+row*2]=binascii.crc_hqx(packet,65535).to_bytes(2,'little');h[254:]=binascii.crc_hqx(h[:254],65535).to_bytes(2,'little');write(h,0x1500)
    for label,name,size,value in [('selection','se_sel_mark',1,1),('fold','se_ef_valid',1,1),('pan','se_l_pan',3,1),('nowrap','se_l_mode',1,1),('manual','se_l_manual',1,1),('retired','se_reu_retired',1,1),('FE-epoch','se_gc_epoch',2,f.get('se_gc_epoch',2)^1),('double-revision','se_r_revision',4,f.get('se_r_revision',4)+1),('wrong-delete','se_hot_delete',1,1),('pending0','se_hot_pending',1,0)]:
     if tag==label:f.put(name,value,size)
    if tag=='foreign-owner':f.put('se_f_owner',1,1);owner=1
    if tag=='FE-owner':f.m.write(f.s['se_reu_logical_owner']+f.get('se_gc_handle',1),253)
    if tag=='FE-map':f.m.write(f.s['se_reu_map']+f.get('se_gc_handle',1),0)
    if tag in ('missing-helper','bad-helper','bad-font'):
     i=slot(25 if tag!='bad-font'else(17 if width==60 else 16),0);a=f.s['se_overlay_ids'if tag=='missing-helper'else'image_crc_lo']+i;f.m.write(a,0 if tag=='missing-helper'else f.m.read(a)^1)
    before=snap();r,n=invoke();assert r.a==2 and not r.p&1,(width,tag,r.a,r.p);assert snap()==before,(width,tag,'readonly refusal')
    assert f.get('se_f_owner',1)==owner and not f.get('se_doc_read_locks',1) and f.read(0xc600,1024)==f.shim
    item=dict(width=width,tag=tag,instructions=n);cases.append(item);print('REFUSE PASS',item,flush=True)
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()

def supplemental(out,base,original):
 out.mkdir();cases=[]
 # Cross-generation tests import real sealed mixtures at startup; no catalogue
 # IDs/CRC/verification flags are fabricated to make a positive result.
 for tag,replace in [('newC33-oldR25','geostail'),('oldC33-newR25','grid')]:
  fixture=out/(tag+'-fixture');shutil.copytree(base,fixture);image=(original/'build/overlays'/(replace+'.seo')).read_bytes();(fixture/'build/overlays'/(replace+'.seo')).write_bytes(image);identity=json.loads((fixture/'freeze.json').read_text());identity['assets'][replace]=hashlib.sha256(image).hexdigest();(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
  result=matrix(out/tag,fixture,('insert','delete'))
  cases.append(dict(tag=tag,cases=result['cases']))
 direct=out/'direct';direct.mkdir();g=caret.profile.observer.Gate(direct,base);f=g.f
 def setup(width,caps=0):
  data=b'Alpha words.\rTail.';f.source(data,physical=256);f.typed(caret.profile.observer.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(97 if width==60 else 98);caret.profile.drain(f);f.position(5);caret.profile.drain(f);f.key(81);return data[:5]+b'Q'+data[5:]
 try:
  for width in (60,80):
   for caps in (0,3):
    for ident,kind in ((14,0),(14,1)):
     source=setup(width,caps);i=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==kind);f.m.write(f.s['se_overlay_ids']+i,0)
     canonical=f.canonical();before=g.reu();ram=f.read(0,65536);phase=f.read(0x8d00,1152);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
     assert not r.p&1 and r.a==(0 if caps==0 else 2),(width,caps,kind,r.a,r.p)
     assert f.canonical()==canonical and f.read(0x8d00,1152)==phase
     after=g.reu()
     if caps==0:
      (bits,attrs),_,_,_=caret.profile.observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
      bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));row=f.get('se_v_caret_row',1);wanted=bytearray(before)
      for a,z in((row*240,(row+1)*240),(0x1500,0x1600)):
       a+=bank*65536;z+=bank*65536;wanted[a:z]=after[a:z]
      assert after==wanted and f.get('se_st_valid',1)==0,(width,kind,'only exact packet/header may change')
      current=f.read(0,65536);want=bytearray(ram)
      for a,z in ((2,0x1c),(0x100,0x200),(0x4000,0x43e8),(0x5000,0x8d00),(0xa000,0xc600),(0xca00,0xd000),(0xd000,0xe000)):want[a:z]=current[a:z]
      for name,size in [('read_budget',2),('se_object_id',5),('validate_index',3)]:a=f.s[name];want[a:a+size]=current[a:a+size]
      assert current==want,('outside declared whole64KiB guard',[(hex(i),a,b)for i,(a,b)in enumerate(zip(want,current))if a!=b][:20])
     else:assert before==after and f.read(0x6000,8000)+f.read(0x4000,1000)==ram[0x6000:0x7f40]+ram[0x4000:0x43e8]
     item=dict(tag='raw-allowed'if caps==0 else'Full-refused',width=width,missing_slot=kind,instructions=n);cases.append(item);print('AUTH PASS',item,flush=True)
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()

def fallback_costs(out,fixtures):
 out.mkdir();allcases={}
 for lane,base in fixtures.items():
  folder=out/lane;folder.mkdir();g=caret.profile.observer.Gate(folder,base);f=g.f;cases=[]
  try:
   for width in (60,80):
    for tag,data,key in [('softwrapped',b'Alpha words '*12+b'\rTail.',81),('introduce-wrap',b'A'*(width-1)+b'\rTail.',81),('insert-CR',b'Alpha words.\rTail.',13)]:
     f.source(data,physical=256);f.typed(caret.profile.observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);caret.profile.drain(f);f.position(5);caret.profile.drain(f);start=f.total_instructions;loads=f.get('se_overlay_loads',2);before=g.audit_begin();f.key(key);caret.profile.drain(f);g.audit_end(before,tag);source=data[:5]+bytes((key,))+data[5:];assert f.merged()==source
     (bits,attrs),_,_,_=caret.profile.observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
     item=dict(tag=tag,width=width,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,pixels=hashlib.sha256(bits+attrs).hexdigest());cases.append(item);print('FALLBACK PASS',lane,item,flush=True)
     f.command(16);caret.profile.drain(f);assert f.merged()==data
   allcases[lane]=cases
  finally:f.close()
 for a,b,c in zip(*allcases.values()):assert a['tag']==b['tag']==c['tag']and a['pixels']==b['pixels']==c['pixels']
 (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=allcases),indent=2)+'\n');return allcases

def run(out,base,smoke=False):
 out.mkdir(parents=True)
 spec=importlib.util.spec_from_file_location('raw_typing_build',ROOT/'src/render/grid/probes/raw-typing/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 candidate,budget=b.build(out/'pair',base)
 result=matrix(out/'candidate',candidate,('insert',)if smoke else('right','down','up','insert','delete'))
 assert len(result['cases'])==(4 if smoke else 20)
 for c in result['cases']:
  if c['caps']==0 and c['action']in('insert','delete'):
   assert 'styler'not in c['entries']and'viewsource'not in c['entries'],c['entries']
   assert c['loads']<=4,(c['tag'],c['loads'],c['entries'])
 controls={}
 if not smoke:
  for tag,fixture in [('original',base),('caret',Path(budget['caret_release']))]:
   controls[tag]=matrix(out/tag,fixture)
   for a,c in zip(controls[tag]['cases'],result['cases']):
    assert a['tag']==c['tag']and a['pixels_sha256']==c['pixels_sha256']and a['caret']==c['caret']and a['top']==c['top']
 extra=operations(out/'operations',candidate) if not smoke else []
 negative=faults(out/'faults',candidate) if not smoke else []
 extra_auth=supplemental(out/'supplemental',candidate,base) if not smoke else []
 fallback=fallback_costs(out/'fallback',dict(original=base,caret=Path(budget['caret_release']),raw=candidate))if not smoke else {}
 other=caret.matrix(out/'source40-geos',candidate,(0,3),('right','insert'))if not smoke else {}
 if not smoke:assert all(x['loads']==0 for x in other['cases']if x['mode']==0 and x['action']=='right')
 final=dict(status='PASS',budget=budget,cases=result['cases'],controls=controls,operations=extra,faults=negative,supplemental=extra_auth,fallback=fallback,other=other)
 (out/'result.json').write_text(json.dumps(final,indent=2)+'\n');return final
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=caret.profile.BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/grid-raw-typing'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke)

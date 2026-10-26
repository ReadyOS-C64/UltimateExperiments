"""Private raw fixed-row carry, independently rendered and checked wholeREU."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,binascii,re,shutil
import test_grid_raw_typing as raw
import font_fixture # bind released immutable-PACK_SHA transport before extracted tools affect sys.path
ROOT=raw.ROOT

def packet_check(f,source,tag):
 grid=raw.caret.profile.observer.geos.grid;width=f.get('se_v_columns',1);anchors=grid.row_starts(source,f.get('se_v_top'),width,False);cache,bank=f.raw_cache();h=cache[0x1500:0x1600];assert h[:4]==b'NC\1\xa5'and h[253]==f.get('se_render_caps',1) and binascii.crc_hqx(h[:254],65535)==int.from_bytes(h[254:],'little'),(tag,'NC authority')
 assert h[124:193]==b''.join(a.to_bytes(3,'little')for a in anchors),(tag,'all row/bottom anchors')
 seen=False
 for row,(start,stop)in enumerate(zip(anchors,anchors[1:])):
  end=stop-1 if stop>start and source[stop-1]==13 else stop;chars=[];flags=[]
  for col in range(width):
   at=start+col;chars.append(source[at]if at<end else 32);caret=at==f.get('se_hot_caret')and at<=end and not seen;flags.append(4 if caret else 0);seen|=caret
  p=cache[row*240:(row+1)*240];assert p[:width]==bytes(chars)and p[80:80+width]==bytes(width)and p[160:160+width]==bytes(flags),(tag,'exact packet',row)
  assert binascii.crc_hqx(p,65535)==int.from_bytes(h[209+row*2:211+row*2],'little'),(tag,'row CRC',row)

def frames(out,base,full=False,only=None,expected_route=2):
 out.mkdir();g=raw.caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 try:
  for width in(60,80):
   pattern=(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ '*1000)
   specs=[('first',b'Alpha words '*12+b'\rTail.',5,(81,20)),('continuation',b'Alpha words '*18+b'\rTail.',width+5,(32,20)),('literal',b'Alpha * @ \\ words '*16+b'\rTail.',width+7,(34,20)),('zeros',b'Alpha\0 words '*16+b'\rTail.',width+5,(81,20)),('col0',pattern[:width*2+10]+b'\rTail.',width,(81,20)),('lastcol',pattern[:width*2+10]+b'\rTail.',width-1,(81,20)),('col0-BACK',pattern[:width*2+10]+b'\rTail.',width,(20,pattern[width-1])),('col1-BACK',pattern[:width*2+10]+b'\rTail.',width+1,(20,pattern[width])),('clipped',pattern[:width*24]+b'\rTail.',5,(81,20)),('bottomrow',pattern[:width*24]+b'\rTail.',width*21+5,(81,20))]
   prefix=b'Prefix\r'*9400;specs.append(('above64KiB',prefix+b'Alpha words '*18+b'\rTail.',len(prefix)+width+5,(32,20)))
   if full:specs=specs[:2]
   if only:specs=[x for x in specs if x[0]in only]
   for tag,data,at,keys in specs:
    f.source(data,physical=256);f.typed(raw.caret.profile.observer.geos.native_text('syntax full'if full else'syntax plain'));f.command(97 if width==60 else 98);raw.caret.profile.drain(f);f.position(at);raw.caret.profile.drain(f);source=data;where=at
    for key in keys:
     before=g.audit_begin();canonical=f.canonical();semantic=f.read(f.s['se_st_descriptor'],37);sp2=f.raw_cache()[0][0x1600:0x1680];initial=f.total_instructions;loads=f.get('se_overlay_loads',2);f.key(key);raw.caret.profile.drain(f);g.audit_end(before,tag)
     source=source[:where]+bytes((key,))+source[where:]if key!=20 else source[:where-1]+source[where:];where+=1 if key!=20 else -1
     assert f.merged()==source and f.get('se_st_valid',1)==int(full) and f.read(0xc600,1024)==f.shim
     if not full:assert f.read(f.s['se_st_descriptor'],37)==semantic and f.raw_cache()[0][0x1600:0x1680]==sp2,(width,tag,key,'raw has no semantic publication')
     (bits,attrs),_,_,_=raw.caret.profile.observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(width,tag,key,'independent pixels')
     route=f.m.read(0x89ff)
     if not full:assert route==expected_route,(width,tag,key,'actual raw path')
     packet_check(f,source,(width,tag,key))
     raw.caret.profile.observer.geos.png(bits,attrs,out/(str(width)+'-'+tag+'-'+str(key)+'.png'))
     item=dict(width=width,tag=tag,key=key,route=route,instructions=f.total_instructions-initial,loads=(f.get('se_overlay_loads',2)-loads)&65535,pixels=hashlib.sha256(bits+attrs).hexdigest());cases.append(item);print('PASS',item,flush=True)
     f.key(0x1d);raw.caret.profile.drain(f);packet_check(f,source,(tag,'right'));f.key(0x9d);raw.caret.profile.drain(f);packet_check(f,source,(tag,'left'))
    assert source==data
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()

def mixed(out,candidate,raw_short):
 out.mkdir();cases=[]
 for tag,replacements in [('newC33-oldR14',{'viewsource':raw_short}),('oldC33-newR14',{'grid':raw_short,'geostail':raw_short})]:
  fixture=out/(tag+'-fixture');shutil.copytree(candidate,fixture);ident=json.loads((fixture/'freeze.json').read_text())
  for name,origin in replacements.items():
   image=(origin/'build/overlays'/(name+'.seo')).read_bytes();(fixture/'build/overlays'/(name+'.seo')).write_bytes(image);ident['assets'][name]=hashlib.sha256(image).hexdigest()
  (fixture/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
  result=raw.matrix(out/tag,fixture,('insert','delete'));long=frames(out/(tag+'-wrapped'),fixture,only=('first',),expected_route=0);cases.append(dict(tag=tag,cases=result['cases'],wrapped=long))
 (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases,scope='Actual sealed cross-generation imports; no verified-bit, catalogue CRC or dependency forgery.'),indent=2)+'\n');return cases
def dispatch_proof(out,leaf,base):
 from peddle import Machine
 out.mkdir();labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(leaf/'viewsource.lbl').read_text())};s=json.loads((base/'build/editor-report.json').read_text())['symbols'];image=(leaf/'viewsource.bin').read_bytes();targets=['se_fs_begin','se_fs_guard','read','se_sc_begin','se_sc_event','se_sc_finish','pixel_prime','se_lp_shift_row']
 m=Machine();cases=[]
 try:
  m.load(0xa000,image)
  for op in range(8):
   for initialX in (0,127,255):
    m.write(s['se_overlay_frame'],op);m.write(s['se_f_owner'],4)
    for n,v in [('pc',0xa010),('sp',0xfd),('p',0x24),('a',93),('x',initialX),('y',77)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
    m.write(0x1fe,0xfe);m.write(0x1ff,2);minimum=0xfd
    for n in range(80):
     r=m.regs();minimum=min(minimum,r.sp)
     if r.pc==labels[targets[op]]:break
     m.lib.zeropage_peddle_step_instruction(m.handle)
    else:raise AssertionError(('dispatch did not reach sealed target',op,hex(m.regs().pc)))
    assert r.a==op and r.sp==0xfd and r.y==77 and minimum==0xfd,(op,'restored opcode/callerstack/Y',r.a,r.sp,r.y,minimum)
    cases.append(dict(op=op,initialX=initialX,target=targets[op],transientStack=0))
  for op in (6,7,8,255):
   for owner in (0,1,2,3,255):
    m.write(s['se_overlay_frame'],op);m.write(s['se_f_owner'],owner);before=bytes(m.read(i)for i in range(65536));r,n=m.call(0xa010)
    assert r.a==0xb0 and r.p&1
    after=bytes(m.read(i)for i in range(65536));assert after[:0x100]==before[:0x100]and after[0x200:]==before[0x200:],(op,owner,'opaque outside stack')
    cases.append(dict(op=op,owner=owner,refused=True))
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases,scope='Exact sealed ordinary branch dispatch targets/stack component; no source-service execution is substituted in public frames.'),indent=2)+'\n');return cases
 finally:m.close()

def refusals(out,base):
 out.mkdir();g=raw.caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 def setup(width):
  data=b'Alpha words '*12+b'\rTail.';f.source(data,physical=256);f.typed(raw.caret.profile.observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);raw.caret.profile.drain(f);f.position(5);raw.caret.profile.drain(f);f.key(81)
 def slot(ident,kind):return next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==kind)
 def write(payload,offset,logical=None):
  f.m.load(0x8a00,payload);f.put('se_reu_logical',f.get('se_gc_handle',1)if logical is None else logical,1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8a00,2);f.put('se_reu_length',len(payload),2);assert not f.call('se_reu_copy',0).p&1
 try:
  for width in(60,80):
   for tag in ('missing-worker','wrong-workerCRC','wrong-workerSIZE','worker-codeCRC','late-packet-byte','late-packet-role','caps','FE-owner','FE-epoch','foreign-owner','fold','selection'):
    setup(width);i=slot(14,0)
    if tag=='missing-worker':f.m.write(f.s['se_overlay_ids']+i,0)
    if tag=='wrong-workerCRC':f.m.write(f.s['image_crc_lo']+i,f.m.read(f.s['image_crc_lo']+i)^1)
    if tag=='wrong-workerSIZE':f.m.write(f.s['image_size_lo']+i,f.m.read(f.s['image_size_lo']+i)^1)
    if tag=='worker-codeCRC':
     assert not f.m.read(f.s['image_slot']+i)&128,'requires actual cold/unverified worker before injection'
     logical=f.m.read(f.s['se_overlay_asset']+(i>>4));write(b'\0',((i&15)*4096)+16,logical)
    if tag.startswith('late-packet'):
     cache,_=f.raw_cache();row=1;packet=bytearray(cache[row*240:(row+1)*240]);packet[7 if tag.endswith('byte')else 80]=packet[7 if tag.endswith('byte')else 80]^1;write(packet,row*240);header=bytearray(cache[0x1500:0x1600]);header[209+row*2:211+row*2]=binascii.crc_hqx(packet,65535).to_bytes(2,'little');header[254:]=binascii.crc_hqx(header[:254],65535).to_bytes(2,'little');write(header,0x1500)
    if tag=='caps':f.put('se_render_caps',3,1)
    if tag=='FE-owner':f.m.write(f.s['se_reu_physical_owner']+f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1)),253)
    if tag=='FE-epoch':f.put('se_gc_epoch',f.get('se_gc_epoch',2)^1,2)
    if tag=='foreign-owner':f.put('se_f_owner',1,1)
    if tag=='fold':f.put('se_ef_valid',1,1)
    if tag=='selection':f.put('se_sel_mark',1,1)
    before=(f.canonical(),g.reu(),f.read(0x6000,8000)+f.read(0x4000,1000));phase=f.read(0x8d00,1152);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
    assert r.a==2 and not r.p&1,(tag,r.a,r.p);assert before==(f.canonical(),g.reu(),f.read(0x6000,8000)+f.read(0x4000,1000)),(tag,'refused before source/cache/pixels')
    assert not f.get('se_doc_read_locks',1)and f.read(0xc600,1024)==f.shim
    if tag=='foreign-owner':assert f.read(0x8d00,1152)==phase and f.get('se_f_owner',1)==1
    else:assert not f.get('se_f_owner',1)
    item=dict(width=width,tag=tag,instructions=n);cases.append(item);print('REFUSE',item,flush=True)
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()

def run(out,base):
 out.mkdir(parents=True);spec=importlib.util.spec_from_file_location('raw_wrapped_build',ROOT/'src/render/grid/probes/raw-wrapped/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);fixture,budget=b.build(out/'pair',base);cases=frames(out/'candidate',fixture);full=frames(out/'Full-long',fixture,True);dispatch=dispatch_proof(out/'dispatch',out/'pair/r14-candidate',base);matrix=raw.matrix(out/'public-matrix',fixture);faults=refusals(out/'faults',fixture);cross=mixed(out/'mixed',fixture,out/'pair/raw-release/fixture');costs=raw.fallback_costs(out/'threeway-costs',dict(original=base,raw_short=out/'pair/raw-release/fixture',wrapped=fixture));other=raw.caret.matrix(out/'source40-geos',fixture,(0,3),('right','insert'));assert all(c['loads']==0 for c in other['cases']if c['mode']==0 and c['action']=='right');r=dict(status='PASS',budget=budget,cases=cases,full=full,dispatch=dispatch,matrix=matrix,faults=faults,mixed=cross,costs=costs,other=other);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=raw.caret.profile.BASE);a=p.parse_args();out=ROOT/'build/grid-raw-wrapped'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())

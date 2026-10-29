"""Private R23 ink-only specialization: genuineFD/allfaces/scalars/opaqueowner.

Candidate deliberately exports no genericmeasure/glyph APIs; generic sources
are untouched. Controls are exact packagedR23. No sharedmake/native/editorchange.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,hashlib
import test_geos_catalog_byte_candidate as old
ROOT=old.ROOT
CANDIDATE=ROOT/'src/render/geos/preview-only-candidate'
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T115028786969Z/fixture'
class Fixture(old.Fixture):
 def __init__(self,*args):
  super().__init__(*args)
  # Parent adapter evaluates the genericsymbolname before selecting explicitINK.
  # This Pythonalias is not an exported executable API or a code substitution.
  if 'se_geos_catalog_glyph'not in self.symbols:self.symbols['se_geos_catalog_glyph']=self.symbols['se_geos_catalog_ink_preview']

def run(out,previous,smoke):
 frozen,identity=old.geos.freeze(out,previous);old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names']
 cs,control_bytes=old.build(out/'control',frozen,False);ss,candidate_bytes=old.build(out/'candidate',frozen,True,CANDIDATE);print('LINK',control_bytes,candidate_bytes,flush=True)
 assert 'se_geos_catalog_measure'not in ss and 'se_geos_catalog_glyph'not in ss and 'se_geos_catalog_measure_preview'not in ss and 'se_geos_catalog_glyph_preview'not in ss
 dll=old.geos.grid.runner(out);a=Fixture(out,frozen,dll,out/'control');b=Fixture(out,frozen,dll,out/'candidate');pack=(out/'control/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)];fallback=(frozen/'fonts/native8.bin').read_bytes();faces=[];total=0;faults=[];native_cases=0
 try:
  reua,reub=a.reu(),b.reu()
  def check(e,raw,value,style,inverse,clip=None,encoding=0,native=False):
   nonlocal total
   ar,af,au=a.glyph(e,value,style,inverse,clip,encoding=encoding,native=native,ink=clip is not None);br,bf,bu=b.glyph(e,value,style,inverse,clip,encoding=encoding,native=native,ink=clip is not None)
   assert not(ar.p&1 or br.p&1),(value,style,inverse,ar.a,br.a)
   h=bf[18];assert af[:20]==bf[:20] and 1<=h<=24,('metrics',value,style,af[:20].hex(),bf[:20].hex())
   met,ink,cov=old.oracle(b''if native else raw,fallback,value,encoding,style,inverse,clip or(0,32,0,24),native_only=native)
   assert bf[14:20]==met and bf[20:20+h*4]==af[20:20+h*4]==ink[:h*4],('oracle',value,style,inverse,clip)
   for f,frame in((a,af),(b,bf)):assert frame[20+h*4:212]==f.last_before[0x8800+20+h*4:0x8800+212],('unusedcoveragewritten',value,style)
   total+=1;return au,bu
  for face,e in enumerate(entries[:1]if smoke else entries):
   offset=int.from_bytes(e[8:11],'little');raw=pack[offset:offset+int.from_bytes(e[11:13],'little')];ua=ub=0;start=total
   samples=[(0x41,0,0),(0x47,7,1),(0xc1,3,0)]if smoke else[(v,v&7,(v>>3)&1)for v in range(256)]
   for args in samples:x,y=check(e,raw,*args);ua+=x;ub+=y
   if not smoke:
    for value in range(32,32+e[13]):
     for style in range(8):
      for inverse in range(2):x,y=check(e,raw,value,style,inverse,(0,32,0,24),encoding=2);ua+=x;ub+=y
    for style in range(8):
     for clip in[(0,0,0,0),(1,32,0,24),(0,31,0,24),(3,17,1,7),(32,0,24,0),(0,32,1,23),(7,19,8,18)]:x,y=check(e,raw,0x47,style,style&1,clip);ua+=x;ub+=y
   assert a.reu()==reua and b.reu()==reub,'all16MiB changed'
   item=dict(face=face,cases=total-start,control_instructions=ua,candidate_instructions=ub,ratio=ua/ub);faces.append(item);print('FACE',item,flush=True)
  packed_cases=total
  if not smoke:
   for value in range(256):
    for style in range(8):
     for inverse in range(2):check(entries[0],b'',value,style,inverse,native=True);native_cases+=1
   e=entries[0];offset=int.from_bytes(e[8:11],'little');length=int.from_bytes(e[11:13],'little');raw=pack[offset:offset+length]
   def inputs(**kw):
    d=dict(font=0x5000,length=length,native=0x4800,value=0x47,encoding=0,style=0,flags=0,clip=(0,32,0,24));d.update(kw);return d['font'].to_bytes(2,'little')+d['length'].to_bytes(2,'little')+d['native'].to_bytes(2,'little')+bytes((d['value'],d['encoding'],d['style'],d['flags'],*d['clip']))
   def arm(f):
    f.m.write(f.s['se_f_owner'],4);f.m.load(0xcbd0,e[:4]);f.m.write(0xcbd5,0);assert not f.fast_call(f.symbols['se_gf_fetch_preview'])[0].p&1
   def direct(f,data,ctx=0x8800):
    if ctx==0x8800:f.m.load(ctx,data+bytes([0xa7])*226)
    before=f.read(0,65536);r,n=f.fast_call(f.symbols['se_geos_catalog_ink_preview'],x=ctx&255,y=ctx>>8);after=f.read(0,65536);want=bytearray(before)
    allowed=[(0x100,0x200)]
    if ctx==0x8800 and f.m.read(f.s['se_f_owner'])==4:allowed +=[(ctx+14,ctx+240),(0x5000,0x6072),(0xcbc0,0xcc00),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2),(f.s['se_reu_c64'],f.s['dma_physical']+1),(f.s['se_crc_value'],f.s['se_crc_value']+2),(0xdf00,0xdf0b)]
    for x,y in allowed:want[x:y]=after[x:y]
    assert after==want,('faultfullRAM',ctx,next((hex(i),x,y)for i,(x,y)in enumerate(zip(after,want))if x!=y));return r,f.read(ctx,240)if ctx==0x8800 else None
   invalid=[dict(encoding=3),dict(encoding=2,value=31),dict(encoding=2,value=129),dict(style=8),dict(flags=2),dict(clip=(33,32,0,24)),dict(clip=(0,33,0,24)),dict(clip=(0,32,25,24)),dict(clip=(0,32,0,25)),dict(font=0),dict(length=0),dict(font=0xc500),dict(font=0xfff0),dict(native=0xfff0),dict(native=0xc300),dict(native=0x8800),dict(font=0x8800),dict(font=0x6000),dict(length=length-1)]
   for kw in invalid:
    for f in(a,b):arm(f)
    ar,_=direct(a,inputs(**kw));br,_=direct(b,inputs(**kw));assert ar.p&1 and br.p&1 and ar.a==br.a==0x90,('argument',kw,ar.a,br.a);faults.append(dict(tag='scalar-span',input=kw,error=0x90))
   for owner in(0,1,2,3,5,255):
    for f in(a,b):
     f.m.write(f.s['se_f_owner'],owner)
     for label in('entry','se_geos_catalog_ink_preview'):
      before=f.read(0,65536);r,_=f.fast_call(f.symbols[label],x=0,y=0x88);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];assert r.p&1 and r.a==0xb2 and after==want
    faults.append(dict(tag='foreign-owner',owner=owner,error=0xb2))
   for ctx in(0,0x8801,0x8700,0x8d00,0xb100,0xc510,0xc600,0xff80):
    for f in(a,b):f.m.write(f.s['se_f_owner'],4)
    ar,_=direct(a,inputs(),ctx);br,_=direct(b,inputs(),ctx);assert ar.p&1 and br.p&1 and ar.a==br.a==0x90;faults.append(dict(tag='context',context=ctx,error=0x90))
   for field,value,error in[(0xcbc0,0,0x18),(0xcbc5,1,0x91),(0xcbc1,0,0x18),(0xcbc2,0,0x18),(0xcbc3,255,0x18),(0xcbc4,255,0x18)]:
    for f in(a,b):
     arm(f);oldvalue=f.m.read(field);f.m.write(field,value);r,frame=direct(f,inputs());assert r.p&1 and r.a==error and frame[14]==0 and not f.m.read(0xcbd5),(field,r.a);f.m.write(field,oldvalue)
    faults.append(dict(tag='font-capability',field=field,error=error))
   for table in('se_reu_logical_owner','se_reu_physical_owner'):
    for which in(0,1):
     for f in(a,b):
      arm(f);h=f.m.read(0xcbc1+which);index=h if table.endswith('logical_owner')else f.m.read(f.s['se_reu_map']+h);at=f.s[table]+index;oldvalue=f.m.read(at);f.m.write(at,0x77);r,frame=direct(f,inputs());assert r.p&1 and r.a==0x18 and frame[14]==0 and not f.m.read(0xcbd5);f.m.write(at,oldvalue)
     faults.append(dict(tag=table,bank=which,error=0x18))
   for change in('borrow','loads'):
    for f in(a,b):
     arm(f)
     if change=='borrow':
      f.m.load(0x5000,bytes([0xa5])*length);f.m.write(0xcbd5,0)
     else:f.m.load(f.s['se_overlay_loads'],((f.get('se_overlay_loads',2)+1)&65535).to_bytes(2,'little'))
     r,frame=direct(f,inputs());assert not r.p&1 and f.read(0x5000,length)==raw
    faults.append(dict(tag=change+'-verifiedrefill',error=0))
   for stride in(1,2,16,128,511):
    for end in(0,1,stride*8,stride*8+1,65535):
     for f in(a,b):
      f.m.load(0x8800+214,end.to_bytes(2,'little'));f.m.load(0x8800+216,stride.to_bytes(2,'little'));f.m.load(f.s['text_ptr'],(0x8800).to_bytes(2,'little'));r,_=f.fast_call(f.symbols['preview_selected_bounds']);assert bool(r.p&1)==(end>stride*8)
     faults.append(dict(tag='selected-index',stride=stride,end=end,error=end>stride*8))
   assert a.reu()==reua and b.reu()==reub,'faults changed16MiBREU'
  result=dict(status='passed',identity=identity,control_bytes=control_bytes,candidate_bytes=candidate_bytes,saved_bytes=control_bytes-candidate_bytes,free_bytes=4096-candidate_bytes,faces=faces,packed_cases=packed_cases,native_cases=native_cases,faults=faults,total_cases=total,newBSS=0,newZP=0,scope='Explicitowner4/context8800 INKonly; generic API source/defaults unchanged and omitted onlyfromR23candidate. Exactpackagedcontrol +independentfontoracle; full64KiBRAM eachcall andactualwhole16MiBREU perface/faultgroup. No production/nativeclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True);return result
 finally:a.close();b.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-preview-only'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke)

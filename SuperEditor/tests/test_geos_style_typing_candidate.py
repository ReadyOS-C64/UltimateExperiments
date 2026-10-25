"""Private genuine styledFEglyph transform and actual inline grammar locality proof.
No bitmap transaction/root fastpath claim; real pendingC6 and ownedFE font data.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,shutil,importlib.util,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
from supermark_model import inline
BASE=ROOT/'build/geos-incremental-editor/20261025T104900415766Z/fixture'
F=0x8b40;G=0x8a00

def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('style_component',ROOT/'src/render/geos/style-typing-candidate/build-component.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);image,s=b.build(out/'component',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);cases=0;peak=0;failures=0;parser_cases=0;locality=0;maxgrammar=0
 def get(name,n=1):return int.from_bytes(f.read(s[name],n),'little')
 def call(name,a=0,x=0,y=0):return f.fast_call(s[name],a=a,x=x,y=y)
 def real_inline(data,start=0):
  nonlocal parser_cases,maxgrammar
  r,n=call('se_si_init');assert not r.p&1;f.m.load(s['se_si_pos'],start.to_bytes(3,'little'));events=[]
  def event():
   if get('se_si_ready'):events.append(tuple(get('se_si_'+k,w)for k,w in [('kind',1),('style',1),('width',1),('open',3),('close',3)]))
  for byte in data:r,n=call('se_si_feed',byte);assert not r.p&1;event();maxgrammar=max(maxgrammar,n)
  r,n=call('se_si_finish');assert not r.p&1;event();expected=inline(data,start);assert events==expected,('actualgrammar/oracle',data,events,expected);parser_cases+=1;return events
 def alnum(v):return 48<=v<=57 or 65<=v<=90 or 193<=v<=218
 def styled(data,events):
  styles=bytearray(len(data));roles=bytearray(len(data))
  for kind,style,width,a,z in events:
   if kind!=1:continue
   for i in range(a+width,z):
    if style==4:roles[i]=4;styles[i]=0
    elif not roles[i]:styles[i]|=(1 if style&2 else 0)|(2 if style&1 else 0)
  return styles,roles
 try:
  data=fold.geos.native_text('Plain **boldword** and *italicword* plus ***bothword***.\rTail.')
  at=data.index(fold.geos.native_text('boldword'))+3;f.source(data);f.command(99);f.position(at);f.render();f.key(ord('X'));assert f.m.read(0xcfe8)==1 and not f.m.read(0x9149),'actualpendingC6stylefallsbacktoday'
  f.put('se_i_ready',0,1);f.put('se_i_count',0,2);f.put('se_n_cache_count',0,1)
  canonical=f.canonical();reu=f.reu();handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle);assert f.m.read(f.s['se_reu_logical_owner']+handle)==f.m.read(f.s['se_reu_physical_owner']+physical)==0xfe
  f.put('se_f_owner',4,1);f.m.load(0xa000,image)
  for code in range(128):
   # Real typed REU reads; no host-built glyph/cache substitutes.
   for offset,host,length in [(0xe568+code*9,F,9),(0xe9e8+code,F+9,1)]:
    f.put('se_reu_logical',handle,1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',host,2);f.put('se_reu_length',length,2);assert not f.call('se_reu_copy',1).p&1
   normal=f.read(F,9);width=f.m.read(F+9)
   for style in range(4):
    for inverse in range(2):
     f.m.load(F+10,bytes([style,inverse])+b'\xa7'*26)
     frame=bytes([code,1,style,inverse])+s['se_geos_packed'].to_bytes(2,'little')+s['se_geos_widths'].to_bytes(2,'little')+(0x4800).to_bytes(2,'little')+bytes([0,16,0,9]);f.m.load(G,frame+bytes([0xa7])*63)
     r,n=call('se_geos_glyph',x=G&255,y=G>>8);assert not r.p&1
     expected=f.read(G+21,18);advance=f.m.read(G+18);before=f.read(0,65536);r,n=call('se_gst_transform');after=f.read(0,65536);peak=max(peak,n);assert not r.p&1 and r.a==0 and after[F+12]==advance and after[F+13]==1 and after[F+14:F+32]==expected,(code,style,inverse,advance,after[F+14:F+32].hex(),expected.hex())
     wanted=bytearray(before);wanted[F+12:F+38]=after[F+12:F+38];wanted[0x100:0x200]=after[0x100:0x200];assert after==wanted,('wholeRAM/source/font/shim',code,style,inverse,next(hex(i)for i,(a,b)in enumerate(zip(after,wanted))if a!=b));cases+=1
  # Invalid dimensions/styles/inverse and impossible suppliedink are refused
  # before even outputVALID changes; only hardwarestack may differ.
  for width,style,inverse,normal in [(0,1,0,bytes(9)),(9,1,0,bytes(9)),(3,4,0,bytes(9)),(3,1,2,bytes(9)),(1,1,0,b'\x40'+bytes(8))]:
   f.m.load(F,normal+bytes([width,style,inverse])+b'\xa7'*26);before=f.read(0,65536);r,n=call('se_gst_transform');after=f.read(0,65536);assert r.a==0x90 and r.p&1;wanted=bytearray(before);wanted[0x100:0x200]=after[0x100:0x200];assert after==wanted;failures+=1
  # Reuse actual complete-body inline parser. Alphanumeric edit with both
  # neighboring bytesalphanumeric cannot split/merge a delimiter or escape.
  fragments=['**boldword**','*italicword*','***bothword***','**outer *nestedword* tail**','*outer **nestedword** tail*','@@codeword@@','£*escapedword*','**unclosedword','@@@@literalword@@@@','****literalword****','££priceword','ordinaryword']
  rng=random.Random(0x5711E)
  documents=[fold.geos.native_text('Plain '+text+' suffixword.')for text in fragments]
  documents +=[fold.geos.native_text('Plain '+' '.join(rng.choice(fragments)for _ in range(4)))for _ in range(80)]
  for data in documents:
   old=real_inline(data);styles,roles=styled(data,old)
   if any(roles):continue #wholeproserowroles0 admission, excludes actualinlinecode
   for at in range(1,len(data)-1):
    if not alnum(data[at-1])or not alnum(data[at])or not alnum(data[at+1])or not(styles[at-1]==styles[at]==styles[at+1])or not styles[at]:continue
    for op in [0,1]:
     new=data[:at]+(b'X'+data[at:]if op==0 else data[at+1:]);events=real_inline(new)
     def shifted(v):return v+(int(v>=at)if op==0 else -int(v>at))
     expected=[(k,s,w,shifted(a),shifted(z))for k,s,w,a,z in old]
     assert events==expected,('local-pairing-proof',data,at,op,events,expected)
     ns,nr=styled(new,events);wanted=styles[:at]+(bytes([styles[at]])+styles[at:]if op==0 else styles[at+1:]);assert ns==wanted and not any(nr);locality+=1
  assert f.canonical()==canonical and f.reu()==reu and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',component_bytes=len(image),transform_bytes=269,GG_equivalence_cases=cases,invalid_inputs=failures,peak_transform_instructions=peak,actual_parser_cases=parser_cases,locality_edits=locality,peak_parser_feed_instructions=maxgrammar,newBSS=0,newZP=0,caller_frame38=38,actual_pending_C6=True,actual_owned_FE=True,whole_RAM=65536,whole_REU=16777216,scope='Genuine style transform+actualinlinegrammar locality proof, using actualpendingC6/ownedFEfont. No bitmapshift/attributeelection/controller/certificate/rootfastpath/latency claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-style-typing-component'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

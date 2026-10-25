"""Single uninterrupted wrapper fetch versus fullyguardeddirectentry proof."""
from pathlib import Path
from datetime import datetime,timezone
import json,importlib.util,shutil,sys
import test_geos_preview_glyph_cache as c

def run(out,base):
 frozen,identity=c.old.geos.freeze(out,base);c.old.geos.grid.editor_fixture.ROOT=c.old.geos.grid.cpu_editor.ROOT=frozen;c.old.geos.grid.editor_fixture.NAMES=c.old.geos.grid.cpu_editor.NAMES=identity['names'];spec=importlib.util.spec_from_file_location('cachebuild',c.D/'build-once.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);budget=m.build(out/'leaf',frozen)
 for ext in('bin','lbl'):shutil.copy2(out/'leaf'/('cache.'+ext),out/'leaf'/('r23.'+ext))
 f=c.Fixture(out,frozen,c.old.geos.grid.runner(out),out/'leaf');pack=(out/'leaf/base/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)];cases=[];original=f.fast_call
 def traced(address,a=0,x=0,y=0,limit=8_000_000):
  fetch=f.symbols['se_gf_fetch_preview'];inside=f.symbols['se_geos_catalog_ink_fetched'];calls=0;phase=False;window=None;descriptor=None;span=[];needle=bytes((0x20,fetch&255,fetch>>8));pos=f.read(f.symbols['entry'],240).find(needle);assert pos>=0;afterfetch=f.symbols['entry']+pos+3
  for name,v in [('pc',address),('sp',253),('p',0x24),('a',a),('x',x),('y',y)]:getattr(f.m.lib,'zeropage_peddle_set_'+name)(f.m.handle,v)
  f.m.write(0x1fe,254);f.m.write(0x1ff,2);start=f.m.regs().instructions
  for _ in range(limit):
   r=f.m.regs()
   if r.pc==0x2ff:
    f.last_trace=dict(fetches=calls,between=span);return r,r.instructions-start
   if r.pc==fetch:calls+=1
   # Once FETCHreturns to the wrapper, onlyCPUstores tofontptr/length and
   # pointerregisterloads occur. Snapshotfontwindow/fullFDgraph at thatboundary.
   if address==f.symbols['entry'] and not phase and calls and r.pc==afterfetch:
    phase=True;window=f.read(0x5000,4210);descriptor=f.read(0xcbc0,64)
   if phase and r.pc==inside:
    assert f.read(0x5000,4210)==window and f.read(0xcbc0,64)==descriptor,'windoworcapwriterbetweenfetchandentry'
    phase=False
   if phase:span.append(r.pc)
   f.m.lib.zeropage_peddle_step_instruction(f.m.handle)
  raise AssertionError('trace-no-return')
 try:
  # Seeding makes traces short; realFDguard still executes in each count.
  for e,native in [(entries[-1],False),(entries[0],False),(entries[0],True)]:
   f.fast_call=original;f.glyph(e,65,3,1,native=native)
   f.fast_call=traced;r,frame,n=f.glyph(e,65,3,1,native=native);assert not r.p&1;assert f.last_trace['fetches']==(0 if native else 1),(native,f.last_trace);assert native or f.last_trace['between'];cases.append(dict(kind='wrapper-native'if native else'wrapper-packed',face=e[:4].hex(),fetches=f.last_trace['fetches'],instructions=n))
  # Directguardedentry has no caller fetchcertificate; it still invokes real
  # FETCHeven when entryscratch contains the preceding internal marker.
  f.fast_call=original;f.glyph(entries[-1],65,3,1);f.m.write(0x8aa0,0x50);f.fast_call=traced;r,frame,n=f.glyph(entries[-1],65,3,1,(0,32,0,24));assert not r.p&1 and f.last_trace['fetches']==1;cases.append(dict(kind='direct-guarded',fetches=1,instructions=n))
  result=dict(status='passed',budget=budget,cases=cases,scope='Actual6510 count realFETCHentry. Packedwrapperone/nativezero;directguardedAPIone regardlessstaleinternalmarker. FullglyphRAMguard remains, fullfault/publicsuite separate. No nativeclaim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
 finally:f.close()
if __name__=='__main__':
 out=c.ROOT/'build/geos-preview-glyph-cache-once'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve())

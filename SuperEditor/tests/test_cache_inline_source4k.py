"""Private v3: unchanged C20, optional4KiB C26 gate, SOURCE_ONLY<=8 events."""
from pathlib import Path
from datetime import datetime,timezone
import sys,inspect,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_event_bound as event_bound
import test_cache_inline_adaptive as adaptive

def build_adapter(out,base):
 code=inspect.getsource(adaptive.build_adapter).replace('probes/adaptive-source','probes/source4k');ns=dict(vars(adaptive));exec(compile(code,str(out/'consumer4k.py'),'exec'),ns);return ns['build_adapter'](out,base)

def source_images(out,base):
 code=inspect.getsource(adaptive.source_images).replace('probes/adaptive-source','probes/source4k');ns=dict(vars(adaptive));exec(compile(code,str(out/'images4k.py'),'exec'),ns);return ns['source_images'](out,base)

def gate_contract(out,base):
 code=inspect.getsource(adaptive.gate_contract).replace('probes/adaptive-source','probes/source4k').replace('>=512','>=4096');ns=dict(vars(adaptive));exec(compile(code,str(out/'gate4k.py'),'exec'),ns);return ns['gate_contract'](out,base)

def run(out):
 code=inspect.getsource(event_bound.run)
 code=code.replace("content=ns['prepare']()", "content=ns['prepare']().replace('body_length>=512','body_length>=4096')")
 code=code.replace("content=content.replace('bad_cert=False','bad_cert=False,hostile_count=None')", "content=content.replace('bad_cert=False','bad_cert=False,hostile_count=None,packed=False')")
 # Only the long-data hostile cases should still enter39 with the4K gate.
 code=code.replace("line(samples[3],cached=True,hostile_count=hostile)", "line(sem.geos.native_text('Word **'+'w '*2100+'tail**\\\\rNext.'),cached=True,hostile_count=hostile)")
 # Prepare a real packed page:254 separate CRs each contribute one actual pair,
 # then the target's one real pair makes exactly255 events on that INLpage.
 extra="""  for size in (4096,5120):
   for events in ((1,4,8) if size==4096 else (8,)):
    text='**x** '*events+'w ' *((size-events*6)//2)
    assert len(text)==size
    line(sem.geos.native_text(text+'\\rNext.'),cached=False);line(sem.geos.native_text(text+'\\rNext.'),cached=True)
  nested='**bold *em* tail** and @@code@@ £* end. '
  nested=nested+'w '*((4096-len(nested))//2)
  data=sem.geos.native_text(nested+'\\rNext.')
  line(data,cached=False);line(data,cached=True)
  for events in (1,8):
   prefix=sem.geos.native_text('**x**\\r')*(255-events)
   size=4096 if events==1 else 5120
   text='**x** '*events+'w ' *((size-events*6)//2)
   data=prefix+sem.geos.native_text(text+'\\rNext.')
   line(data,start=len(prefix),cached=False,packed=True);line(data,start=len(prefix),cached=True,packed=True)
"""
 code=code.replace("content=content.replace(\"  result['source_cases']=source_cases\",", "content=content.replace(\"  result['source_cases']=source_cases\", EXTRA+ ")
 code=code.replace("content=content.replace('   # Only this sourceconstant path',CHECKS+'   # Only this sourceconstant path')", "content=content.replace('   # Only this sourceconstant path',PACKED_CHECK+CHECKS+'   # Only this sourceconstant path')")
 code=code.replace("ns.update(build_adapter=build_adapter,PREPARED=content)", "ns.update(build_adapter=build_adapter,source_images=source_images,gate_contract=gate_contract,PREPARED=content)")
 # A certificate identifies the selected CR, not necessarily root's firstCR.
 packed_check="""   if packed:
    page=f.m.read(G+29+72);slot=f.m.read(G+114);cr=transfer(page*4096+64+slot*96,length=96);ipage=cr[40];header=transfer(ipage*4096,length=64)
    assert header[23]==255 and int.from_bytes(header[21:23],'little')==2550,'notactualpackedINLpage'
"""
 ns=dict(vars(event_bound));ns.update(build_adapter=build_adapter,source_images=source_images,gate_contract=gate_contract,EXTRA=extra,PACKED_CHECK=packed_check)
 (out/'driver4k.py').write_text(code);exec(compile(code,str(out/'driver4k.py'),'exec'),ns);ns['run'](out)
 r=json.loads((out/'result.json').read_text());r['body_threshold']=4096;r['profile']='v3';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
 out=ROOT/'build/cache-inline-source4k'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

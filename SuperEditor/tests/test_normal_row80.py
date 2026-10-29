"""Private R16 normal-role raster A/B; independent pixels and whole-RAM guard.

No editor, hardware, VICE or persistent cache authority is substituted here.
Both actual6502 row implementations use the same immutable fonts and oracle.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,random,sys
import test_narrow_rows as row
ROOT=row.ROOT;D=ROOT/'src/render/grid/probes/normal-row80'

def run(out,smoke=False):
 out.mkdir(parents=True);spec=importlib.util.spec_from_file_location('normal_row80_builder',D/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);budget=builder.build(out/'packaged')
 rng=random.Random(0x8016510);cases=[]
 phases=range(8)if smoke else range(256)
 for encoding in (0,1):
  for phase in phases:
   chars=bytes((phase+i)&255 for i in range(80));flags=bytes((phase+i*7)&255 for i in range(80));palette=bytes((phase+i*3)&255 for i in range(14))
   cases.append(dict(tag=f'normal-{encoding}-{phase}',kind='normal',mode=80,chars=chars,roles=bytes(80),flags=flags,palette=palette,bg=phase,row=phase%25,encoding=encoding,ctx=0xc0fb if phase%2 else 0xc000))
   if phase%4==0:
    for kind in ('unknown-normal','mixed-fallback'):
     roles=bytearray((14+i+phase)%256 for i in range(80))
     for i,v in enumerate(roles):
      if 0<v<14:roles[i]=0
     if kind=='mixed-fallback':roles[phase%80]=1+phase%13
     cases.append(dict(tag=f'{kind}-{encoding}-{phase}',kind=kind,mode=80,chars=chars,roles=bytes(roles),flags=flags,palette=palette,bg=phase,row=phase%25,encoding=encoding,ctx=0xc0fb))
 for count in ([0,1,2,79,80,81,255]if smoke else [*range(82),255]):
  chars=rng.randbytes(count)
  for encoding in (0,1):
   cases.append(dict(tag=f'count-{count}-{encoding}',kind='count',mode=80,chars=chars,roles=bytes(count),flags=rng.randbytes(count),palette=rng.randbytes(14),bg=0x86,row=count%25,encoding=encoding))
 invalid=[dict(mode=0),dict(mode=40),dict(mode=60),dict(mode=255),dict(row=25),dict(row=255),dict(encoding=2),dict(bitmap=0),dict(bitmap=0x1000),dict(bitmap=0x2001),dict(bitmap=0xc000),dict(bitmap=0xe000),dict(attributes=0),dict(attributes=0xc400),dict(attributes=0xc600),dict(attributes=0xffff),dict(attributes=0x8001)]
 records={}
 for variant,source in [('control',str(out/'packaged/tree/src/render/narrow/row80')),('candidate','render/grid/probes/normal-row80/row80')]:
  row.OUT=out/variant;row.OUT.mkdir();row.SOURCES=[source,'render/narrow/arbitrate','render/narrow/font4','render/narrow/font5','render/narrow/probe','tui/petscii'];symbols=row.build();f=row.Fixture(symbols);cost=[]
  try:
   for index,case in enumerate(cases):
    kw={k:v for k,v in case.items()if k not in ('tag','kind')};f.render(**kw);cost.append(f.last_instructions)
    if index%128==0:print(variant,index,flush=True)
   for changes in invalid:
    kw=dict(mode=80,chars=b'A',roles=b'\0',flags=b'\0',palette=bytes(range(14)),invalid=True);kw.update(changes);f.render(**kw)
   assert f.reu()==f.reu_before,'whole512KiB REU unchanged'
   records[variant]=dict(instructions=cost,invalid=len(invalid),calls=f.calls,peak=f.peak_instructions)
  finally:f.close()
 groups={}
 for kind in sorted({c['kind']for c in cases}):
  selected=[i for i,c in enumerate(cases)if c['kind']==kind];a=sum(records['control']['instructions'][i]for i in selected);b=sum(records['candidate']['instructions'][i]for i in selected)
  groups[kind]=dict(calls=len(selected),control=a,candidate=b,change_percent=(b/a-1)*100)
 result=dict(status='PASS',scope=__doc__,smoke=smoke,budget=budget,rows_per_variant=len(cases),invalid_per_variant=len(invalid),groups=groups,records=records,pixels_per_row=2560,attributes_per_row=40,full_RAM_per_call=0xd000,shim_unchanged=True,REU_unchanged=512*1024,font4_sha256=hashlib.sha256((ROOT/'assets/fonts/generated/narrow4.bin').read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',json.dumps(groups),flush=True);return result
def public(out,fixture):
 """Real public key paths, genuine checked capsules and whole-REU DMA masks."""
 import test_grid_raw_typing as raw
 import test_grid_raw_wrapped as wrapped
 out.mkdir(parents=True)
 assert fixture.exists(),'Build the private authenticated packaged fixture first.'
 control=raw.matrix(out/'control',raw.ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture')
 candidate=raw.matrix(out/'candidate',fixture)
 assert len(control['cases'])==len(candidate['cases'])==20
 comparison=[]
 for a,b in zip(control['cases'],candidate['cases']):
  assert(a['tag'],a['pixels_sha256'],a['caret'],a['top'])==(b['tag'],b['pixels_sha256'],b['caret'],b['top'])
  comparison.append(dict(tag=a['tag'],control=a['settled_instructions'],candidate=b['settled_instructions'],change_percent=(b['settled_instructions']/a['settled_instructions']-1)*100,loads=[a['loads'],b['loads']]))
 carry=wrapped.frames(out/'wrapped',fixture,only=('first','col0','lastcol','bottomrow','above64KiB'))
 faults=wrapped.refusals(out/'faults',fixture)
 result=dict(status='PASS',scope='Actual packaged public-key CPU comparison, current59 control/candidate; independent pixels/source/history and exact whole16MiB checked-DMA masks. Not native VIC/PAL or physical-key proof.',comparison=comparison,wrapped=carry,faults=faults)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PUBLIC_PASS',json.dumps(comparison),flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--public',action='store_true');p.add_argument('--fixture',type=Path,default=ROOT/'build/normal-row80-unrolled2/fixture');a=p.parse_args();out=ROOT/'build/normal-row80'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);public(out,a.fixture.resolve())if a.public else run(out,a.smoke)

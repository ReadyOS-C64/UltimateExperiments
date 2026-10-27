"""Actual editor baseline→cached classification→fallback with pixel oracle.

No worker/frame/parser output substitution. Counter symbols must match frozen
capsules exactly. Inline presentation still uses the real legacy C26 worker.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,re,shutil,zipfile
import test_cache_observer as observer
import test_plain_geos as plain
ROOT=observer.ROOT

def run(out,base):
 gate=observer.Gate(out,base);f=gate.f;targets=[];cases=[]
 try:
  with zipfile.ZipFile(gate.frozen/'product-sources.zip') as z:
   committed_identity=b'BCQ_COMMITTED_IDENTITY=1' in z.read('src/cache/editor/build.py')
  for asset,stem in [('sema',ROOT/'build/cache-editor/sema'),('inln',ROOT/'build/cache-editor/inln'),('page',ROOT/'build/cache-editor/page'),
                     ('geossema',ROOT/'build/overlays/geossema'),('geosinln',ROOT/'build/overlays/geosinln')]:
   raw=stem.with_suffix('.bin').read_bytes();assert raw==f.assets[asset][36:],(asset,'incoherent labels')
   shutil.copy2(stem.with_suffix('.lbl'),out/(asset+'.lbl'))
   symbols={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',stem.with_suffix('.lbl').read_text())}
   for name in ('entry','se_sm_init','se_sm_feed','se_sm_finish','se_si_init','se_si_feed','se_si_finish'):
    if name in symbols:targets.append((asset+':'+name,symbols[name],2,gate.identity['names'].index(asset)+1))
  gate.dll.pb_config(f.s['se_overlay_active'],len(targets),
   (C.c_uint16*len(targets))(*(t[1]for t in targets)),(C.c_uint8*len(targets))(*(t[2]for t in targets)),
   (C.c_uint8*len(targets))(*(t[3]for t in targets)),(C.c_uint8*(16*len(targets)))())
  fonts={n:(gate.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
  data=plain.SOURCE
  def counted(tag,op,caps=1,source=None):
   source=data if source is None else source
   before=f.total_instructions;gate.dll.pb_begin()
   try:op()
   finally:gate.dll.pb_end()
   counts={t[0]:int(gate.dll.pb_get(i))for i,t in enumerate(targets)}
   bits,attrs,rows=plain.expected(f,source,fonts,caps)
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independentpixels')
   assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
   assert f.read(0xC600,1024)==f.shim and f.merged()==source
   observer.geos.png(bits,attrs,out/(tag+'.png'))
   item=dict(tag=tag,counts=counts,instructions=f.total_instructions-before,flags=f.get('se_bc_flags',1),queue=f.get('se_bc_count',1))
   cases.append(item);print('PASS',item,flush=True);return counts
  def full():
   f.put('se_gc_width',0,1)
   f.m.write(0xCF90,0);f.m.write(0xCFE8,0)
   f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
   f.render()
  f.source(data);f.typed(observer.geos.native_text('syntax markdown'))
  counts=counted('first-baseline',lambda:(f.command(99),f.render()))
  assert counts['sema:se_sm_feed']==len(data) and counts['inln:entry']>0
  assert counts.get('geossema:se_sm_feed',0)==0
  assert f.get('se_bc_flags',1)&15==1 and f.get('se_bc_count',1)==0
  before=gate.reu();canonical=gate.stable()
  counts=counted('cached-classification-full-repaint',full)
  assert counts['inln:entry']>0
  cached_query_calls=counts['inln:entry']
  assert counts['page:entry']>0
  assert not any(v for k,v in counts.items()if k.startswith(('sema:','geossema:'))and(k.endswith(('_feed','_finish','_init'))or k.endswith(':entry')))
  assert gate.stable()==canonical
  # Only the existing derived pixel/page cache may change; semantic arena53
  # is immutable on this repaint. Compare its whole logical allocation.
  try:
   # f.reu() in the historical renderer fixture covers2MiB. This gate's
   # snapshots cover16MiB, so compare equal full extents with exact FE spans.
   _,bank=f.raw_cache();after=gate.reu();wanted=bytearray(before)
   spans=[(0,64),(0x600,0x680),(0xB200,0xD8B2),(0xE568,0xEA88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]
   for lo,hi in spans:
    lo+=bank*65536;hi+=bank*65536;wanted[lo:hi]=after[lo:hi]
   assert after==wanted,'whole16MiB outside exact FE cache spans'
  except AssertionError:
   after=gate.reu();changes=[]
   for bank in range(256):
    lo=bank*65536;old,new=before[lo:lo+65536],after[lo:lo+65536]
    if old!=new:
     offsets=[i for i,(a,b)in enumerate(zip(old,new))if a!=b]
     changes.append(dict(physical=bank,owner=f.m.read(f.s['se_reu_physical_owner']+bank),changed=len(offsets),first=offsets[:32],last=offsets[-8:]))
   (out/'unexpected-reu-changes.json').write_text(json.dumps(dict(changes=changes,objects={n:f.read(f.s[n],8 if n!='object_extents'else 128).hex()for n in ('object_owner','object_banks','object_extents')}),indent=2)+'\n')
   raise
  # A committed-only window move may reuse content classifications. The lease
  # still captures and guards the actual current full source snapshot.
  f.position(1)
  counts=counted('hot-window-committed-reuse' if committed_identity else 'hot-window-cache-miss',full)
  assert counts.get('sema:entry',0)==0 and f.get('se_bc_count',1)==0
  if committed_identity:
   assert counts['inln:entry']>=cached_query_calls and counts['page:entry']>0
   assert not any(v for k,v in counts.items() if k.startswith('geossema:'))
  else:
   assert 0<counts['inln:entry']<cached_query_calls and counts.get('geossema:se_sm_feed',0)>0
  f.position(0)
  f.key(observer.Q);f.render();changed=bytes([observer.Q])+data
  assert f.get('se_bc_count',1)>0
  counts=counted('observed-edit-safe-fallback',full,source=changed)
  assert counts.get('sema:entry',0)==0 and counts.get('inln:entry',0)==0
  assert counts.get('geossema:se_sm_feed',0)>0
  f.typed(observer.geos.native_text('syntax plain'))
  counts=counted('plain-bypass',full,caps=0,source=changed)
  assert not any(counts.values()),counts
  result=dict(status='PASS',resident=f.report['sha256'],binding=f.report['resident_binding']['digest'],cases=cases,
   scope='Actual C7/R33/C34/root/C21/C35/C37 baseline and forward block classification cache. Inline C26 and code C25 fallback remain; no edit rebase/layout reuse/native latency claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);a=p.parse_args()
 out=ROOT/'build/cache-editor-product'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 print('RUN',out,flush=True);run(out,a.fixture)

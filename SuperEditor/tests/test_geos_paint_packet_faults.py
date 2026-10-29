"""Private packet-gather count/refusal/cancel proof, actual catalog/source cache."""
from pathlib import Path
from datetime import datetime,timezone
import json,ctypes as C
import test_geos_paint_packet_candidate as candidate
import test_geos_identity_candidate as identity
import test_geos_semantic_editor as semantic
ROOT=candidate.ROOT

def run(out,base):
 fixture=candidate.install(out,base,'candidate');identity.semantic.geos.grid.editor_fixture.ROOT=identity.semantic.geos.grid.cpu_editor.ROOT=fixture
 names=json.loads((fixture/'freeze.json').read_text())['names'];identity.semantic.geos.grid.editor_fixture.NAMES=identity.semantic.geos.grid.cpu_editor.NAMES=names
 dll=identity.fold.retention.runner(out);f=identity.Fixture(out,fixture,dll,True);cases=[]
 def source():
  f.source(semantic.geos.native_text('Ordinary prose with enough text.\rAnother line.'));f.command(99);f.m.write(0xCF90,0);f.render();f.put('se_f_owner',4,1);f.m.load(0x8B40,bytes(192));f.m.write(0x9148,0)
 def phase():
  r,n=f.invoke(0);assert not r.p&1 and r.a==1
  for _ in range(200):
   if f.m.read(0x8B43)==2:return
   r,n=f.invoke(1);assert not r.p&1 and r.a==1,(r.a,r.p)
  raise AssertionError('no actual CHARS phase')
 def protected():return f.canonical(),f.reu(),f.read(0xC600,1024),f.read(0x6000,8000)+f.read(0x4000,1000)
 def unchanged(b,paint=True):
  assert (f.canonical(),f.reu(),f.read(0xC600,1024))==b[:3]
  if paint:assert f.read(0x6000,8000)+f.read(0x4000,1000)==b[3]
 try:
  for count in(0,65,255):
   source();phase();f.m.write(0x8B48,count);before=protected();f.audit_begin();r,n=f.invoke(1);f.dll.fr_end();assert r.p&1 and r.a==0x90,('countrefusal',count,r.a,r.p);unchanged(before);cases.append(dict(tag='count-'+str(count),error=r.a,instructions=n));f.put('se_f_owner',0,1)
  source();phase();before=protected();f.audit_begin();r,n=f.invoke(2);f.dll.fr_end();assert not r.p&1 and r.a==0 and f.m.read(0x8B40)==0;unchanged(before);cases.append(dict(tag='cancel-before-gather',instructions=n));f.put('se_f_owner',0,1)
  source();phase();r,n=f.invoke(1);assert not r.p&1 and r.a==1;before=protected();f.audit_begin();r,n=f.invoke(2);f.dll.fr_end();assert not r.p&1 and r.a==0;unchanged(before);cases.append(dict(tag='cancel-after-gather',instructions=n));f.put('se_f_owner',0,1)
  source();phase();f.put('se_sel_anchor',f.get('se_sel_anchor')+1);before=protected();f.audit_begin();r,n=f.invoke(1);f.dll.fr_end();assert r.p&1 and r.a==0x74;unchanged(before);cases.append(dict(tag='selection-change',error=r.a,instructions=n));f.put('se_f_owner',0,1)
  source();phase();before=protected();handle=f.get('se_gc_handle',1);address=f.s['se_reu_logical_owner']+handle;owner=f.m.read(address);f.m.write(address,0xA5);f.audit_begin();r,n=f.invoke(1);f.dll.fr_end();assert r.p&1;unchanged(before);f.m.write(address,owner);cases.append(dict(tag='foreign-FE-owner',error=r.a,instructions=n));f.put('se_f_owner',0,1)
  source();phase();revision=f.get('se_r_revision',4);f.put('se_r_revision',revision+1,4);before=protected();f.audit_begin();r,n=f.invoke(1);f.dll.fr_end();assert r.p&1 and r.a==0x74;unchanged(before);cases.append(dict(tag='injected-source-revision-change',error=r.a,instructions=n));f.put('se_r_revision',revision,4);f.put('se_f_owner',0,1)
  for field,value,tag in [(194,4,'invalid-prose-style'),(356,14,'invalid-prose-role')]:
   source();phase();handle=f.get('se_gc_handle',1);line=f.m.read(0x8B45);offset=f.m.read(0x8B46)+256*f.m.read(0x8B47);f.m.write(0x9000,value);f.put('se_reu_logical',handle,1);f.put('se_reu_offset',0x200+line*2048+field+offset,2);f.put('se_reu_c64',0x9000,2);f.put('se_reu_length',1,2);r=f.call('se_reu_copy',0);assert not r.p&1
   before=protected();f.audit_begin();steps=0
   while True:
    r,n=f.invoke(1);steps+=1
    if r.p&1:break
    assert r.a==1 and steps<100
   f.dll.fr_end();assert r.a==0x90,(tag,r.a);unchanged(before);cases.append(dict(tag=tag,error=r.a,steps=steps));f.put('se_f_owner',0,1)
  result=dict(status='passed',cases=cases,scope='Actual source-built C21 cache/C22 catalog; count refusals and selection/provider faults before pixel writes; both packet-side cancellation points; whole16MiB/canonical/shim and all64KiB allowlist retained. Caller release explicit.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-paint-packet-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);print(json.dumps(run(out,candidate.BASE),indent=2))

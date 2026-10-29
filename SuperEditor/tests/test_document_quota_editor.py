"""Actual editor quota admission, including pending and history boundaries.

The initial source is an explicit immutable import fixture. All mutations use
public root commands, with one-bank declared document quota and16 physical banks.
--candidate is an isolated, clearly labeled C6 prototype; no shared build writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_geos_editor as geos
import font_fixture
from overlays import wrap
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-semantic-editor/20261025T060655745558Z/fixture'
PRG='8fd8a96c27052ee14ce59070981e863b53b3afc7cb4a4e3ced4728975747f232'

def run(out,previous,candidate=None):
 out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(previous,frozen)
 identity=json.loads((frozen/'freeze.json').read_text());assert identity['prg_sha256']==PRG or previous!=BASE
 pack=frozen/'build/geos-font-catalog/font-pack.bin';pack.parent.mkdir(exist_ok=True)
 shutil.copy2(ROOT/'agentsworking/evidence/M7/20261025T063145901590Z-reu-1024-native/font-pack.bin',pack)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=font_fixture.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);cases=[];failures=[]
 def fixture(n,banks=1):
  f=geos.Fixture(out,frozen,dll,True)
  if candidate:
   f.assets['window']=candidate.read_bytes()
   # Explicit private resident proof seam: suppress the old premature clear.
   # The production fix moves this same JSR to the successful-edit branch;
   # this seam exercises rejection only and is not an integrated-build claim.
   pattern=b'\x20'+f.s['se_selection_clear'].to_bytes(2,'little')+b'\xAD'+f.s['se_e_command'].to_bytes(2,'little')+b'\xAA'
   ram=f.read(0x1000,0x3000);at=ram.index(pattern)+0x1000;assert ram.count(pattern)==1
   f.m.load(at,b'\xEA'*3)
  data=(geos.native_text('Capacity 0123456789 abcdefghijk\r')*((n//30)+1))[:n]
  assert len(data)==n
  f.source(data,banks=banks,physical=16);return f,data
 def command(f,c):
  f.put('se_e_error',0,1);f.call('se_editor_command',c)
  for _ in range(25000):
   if not f.get('se_e_job',1):break
   f.call('se_editor_service')
  assert not f.get('se_e_job',1)
  return f.get('se_e_error',1)
 def key(f,c):
  f.put('se_e_mods',0,1);f.put('se_e_key',c,1);f.put('se_e_error',0,1);f.call('se_editor_input')
  for _ in range(25000):
   if not f.get('se_e_job',1):break
   f.call('se_editor_service')
  assert not f.get('se_e_job',1)
  return f.get('se_e_error',1)
 def expect_refusal(f,c):
  before=f.canonical();optional=f.read(f.s['se_ej_position'],15)+f.read(f.s['se_ej_generation'],5)+f.read(f.s['se_h_dirty'],1);source=f.merged();rev=f.get('se_r_revision',4);pending=f.get('se_hot_pending',1);reu=f.reu()
  fault=f.get('se_hot_fault',1);error=key(f,c)
  assert error==0x32,('expected pre-mutation capacity error32',error)
  assert f.canonical()==before and f.merged()==source,'source/caret/selection/history/pending changed'
  assert f.get('se_r_revision',4)==rev and f.get('se_hot_fault',1)==0x32 and f.get('se_hot_pending',1)==pending
  assert f.reu()==reu,'rejected input changed REU'
  assert optional==f.read(f.s['se_ej_position'],15)+f.read(f.s['se_ej_generation'],5)+f.read(f.s['se_h_dirty'],1),'journal observer/save dirty changed'
  assert not f.get('se_doc_read_locks',1) and not f.get('se_f_owner',1)
  assert f.read(0xc600,1024)==f.shim
 def case(name,n,body,banks=1):
  f,data=fixture(n,banks)
  try:
   body(f,data);assert f.read(0xc600,1024)==f.shim
   cases.append(dict(id=name,status='passed',length=f.get('se_doc_length'),pending=f.get('se_hot_pending',1),merged=len(f.merged()),history=f.get('se_h_end',2)))
  except Exception as e:
   failures.append(dict(id=name,error=repr(e),length=f.get('se_doc_length'),merged=len(f.merged()),caret=f.get('se_hot_caret'),pending=f.get('se_hot_pending',1),errorcode=f.get('se_e_error',1)))
   (out/(name+'-ram.bin')).write_bytes(f.read(0,65536));(out/(name+'-reu.bin')).write_bytes(f.reu()[:1048576])
  finally:f.close()
 q=geos.native_text('Q')[0]
 for name,pos,mark in [('full-start',0,False),('full-middle',32768,False),('full-eof',65536,False),('full-empty-mark',65536,True)]:
  def body(f,data,pos=pos,mark=mark):
   f.position(pos)
   if mark:assert command(f,68)==0
   expect_refusal(f,q)
  case(name,65536,body)
 def exact(f,data):
  f.typed(geos.native_text('bottom'));assert key(f,q)==0 and f.merged()==data+bytes([q])
  expect_refusal(f,q);assert command(f,16)==0 and f.merged()==data
  assert command(f,17)==0 and f.merged()==data+bytes([q]);expect_refusal(f,q)
  assert command(f,16)==0 and f.merged()==data
 case('below-to-exact-undo-redo',65535,exact)
 def replace(f,data):
  f.typed(geos.native_text('bottom'));assert command(f,3)==0
  assert f.merged()==data[:-1];assert key(f,q)==0 and f.merged()==data[:-1]+bytes([q])
  expect_refusal(f,q);assert command(f,16)==0 and f.merged()==data
 case('pending-delete-replace-exact',65536,replace)
 def selected(f,data):
  f.position(32768);assert command(f,68)==0 and command(f,2)==0
  assert key(f,q)==0 and f.merged()==data[:32768]+bytes([q])+data[32769:]
  assert command(f,16)==0 and f.merged()==data
 case('selected-replace-equal-quota',65536,selected)
 def paste(f,data):
  assert command(f,68)==0 and command(f,2)==0 and command(f,69)==0
  assert command(f,50)==0;f.typed(geos.native_text('bottom'))
  before=f.canonical();assert command(f,71)==0x32 and f.canonical()==before and f.merged()==data
 case('paste-above-quota-atomic',65536,paste)
 def append_size(f,size):
  f.m.load(f.s['se_object_id'],f.read(f.s['se_doc_append'],5));f.put('se_object_offset',size)
  assert not f.call('se_object_resize').p&1
 def append_full(f,data):
  append_size(f,65536);expect_refusal(f,q)
  assert command(f,4)==0 and f.merged()==data[1:]
  assert command(f,16)==0 and f.merged()==data
 case('append-full-insert-refused-delete-undo-works',100,append_full)
 def append_exact(f,data):
  append_size(f,65535);assert key(f,q)==0 and f.merged()==bytes([q])+data
  expect_refusal(f,q);assert command(f,16)==0 and f.merged()==data
  assert command(f,17)==0 and f.merged()==bytes([q])+data
 case('append-one-free-exact-and-replay',100,append_exact)
 def append_delete(f,data):
  append_size(f,65536);assert command(f,4)==0 and f.merged()==data[1:]
  # Root movement flushes; direct documented hot movement isolates a pending
  # disjoint deletion which would append retained middle bytes on flush.
  assert not f.call('se_hot_call',7).p&1
  before=f.canonical();merged=f.merged();assert command(f,4)==0x32
  assert f.canonical()==before and f.merged()==merged
  assert command(f,16)==0 and f.merged()==data
 case('append-full-disjoint-delete-refused',100,append_delete)
 def shrink(f,data):
  f.position(32768);assert command(f,68)==0 and command(f,2)==0 and command(f,2)==0
  assert key(f,q)==0 and f.merged()==data[:32768]+bytes([q])+data[32770:]
  assert command(f,16)==0 and f.merged()==data
 case('selected-replacement-shrinks-at-quota',65536,shrink)
 def copy_prefix(f,count):
  assert command(f,68)==0
  for _ in range(count):assert command(f,2)==0
  assert command(f,69)==0 and command(f,50)==0
 def paste_exact(f,data):
  copy_prefix(f,1);f.typed(geos.native_text('bottom'));assert command(f,71)==0 and f.merged()==data+data[:1]
  before=f.canonical();assert command(f,71)==0x32 and f.canonical()==before and f.merged()==data+data[:1]
  assert command(f,16)==0 and f.merged()==data
 case('paste-below-to-exact-next-refused',65535,paste_exact)
 def paste_replace(f,data):
  copy_prefix(f,2);f.position(32768);assert command(f,68)==0 and command(f,2)==0 and command(f,2)==0
  assert command(f,71)==0 and f.merged()==data[:32768]+data[:2]+data[32770:]
  assert command(f,16)==0 and f.merged()==data
 case('selected-paste-equal-quota',65536,paste_replace)
 def paste_over(f,data):
  copy_prefix(f,2);f.position(32768);assert command(f,68)==0 and command(f,2)==0
  before=f.canonical();reu=f.reu();assert command(f,71)==0x32 and f.canonical()==before and f.merged()==data
  assert f.reu()==reu and f.get('se_sel_mark',1)==1 and not f.get('se_clip_busy',1)
 case('selected-paste-above-quota-atomic',65536,paste_over)
 def wider_quota(f,data):
  f.typed(geos.native_text('bottom'));assert key(f,q)==0 and f.merged()==data+bytes([q])
  assert command(f,16)==0 and f.merged()==data and f.get('se_hot_caret')==65536
 case('same-source-two-bank-control',65536,wider_quota,banks=2)
 result=dict(status='failed'  if failures else 'passed',prg_sha256=identity['prg_sha256'],candidate=str(candidate) if candidate else None,private_resident_rejection_seam=bool(candidate),quota_bytes=65536,physical_banks=16,cases=cases,failures=failures)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--candidate',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
 if a.run:
  out=a.out or ROOT/'build/document-quota-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
  r=run(out,a.fixture,a.candidate);sys.exit(bool(r['failures']))
 else:print('Prepared actual public root document-quota acceptance; --run freezes then executes.')

"""Certified edited hints through actual C17/C18/R18 and merged-source R14.
Private output only. C19/journal certification is caller-owned, not simulated here.
"""
from pathlib import Path
from dataclasses import replace
import ctypes as C,hashlib,importlib.util,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from supermark_probe import petscii
OUT=ROOT/'build/fold-edited-hints';BASE=ROOT/'agentsworking/evidence/M5/20261025T004901311531Z-fold-editor-native'
def load(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
leaf=load('edited_leaf','tests/test_fold_leaves.py');model=leaf.model

def freeze():
 base=OUT/'fixture';(base/'build/overlays').mkdir(parents=True,exist_ok=True)
 for name in ['editor.prg','editor-report.json','editor.lbl','editor.map','editor-bindings.json']:
  shutil.copy2(BASE/name,base/'build'/name)
 for n in cpu_editor.NAMES:shutil.copy2(BASE/(n+'.seo'),base/'build/overlays'/(n+'.seo'))
 (base/'freeze.json').write_text(json.dumps(dict(names=cpu_editor.NAMES,source=str(BASE)),indent=2)+'\n')
 assert hashlib.sha256((base/'build/editor.prg').read_bytes()).hexdigest()=='800ef98ec5ab478b1049b3f9bb13879056887ef7dee25a874083921b713625e5'
 with zipfile.ZipFile(BASE/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith('src/') and not n.endswith('/'):
    p=OUT/'baseline'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 return base

def generic_build(name,source):
 out=OUT/name;out.mkdir(parents=True,exist_ok=True);objects=[]
 for n in model.NAMES:
  p=out/(n.replace('/','-')+'.o');objects.append(p);leaf.run('ca65','-g','-I',source,'-o',p,source/(n+'.s'))
 leaf.run('ld65','-C',ROOT/'src/fold/builder-probe.cfg','-o',out/'probe.bin','-m',out/'probe.map','-Ln',out/'probe.lbl',*objects)
 return (out/'probe.bin').read_bytes()

class Fixture(leaf.Fixture):
 def reu(self):
  b=C.create_string_buffer(16*65536*16);self.runner.fl_reu(self.m.handle,len(b),b);return b.raw
 def write_object(self,token,data):
  self.m.load(self.s['se_object_id'],token);self.put('se_object_offset',len(data));assert not self.call('se_object_resize').p&1
  for i in range(0,len(data),512):
   part=data[i:i+512];self.m.load(0x8000,part);self.m.load(self.s['se_object_id'],token);self.put('se_object_offset',i);self.put('se_object_length',len(part),2);self.put('se_object_c64',0x8000,2);assert not self.call('se_object_copy').p&1
 def old_object(self,data,owner=0x46):
  r,_=self.m.call(self.s['se_object_create'],a=owner,x=1);assert not r.p&1;token=self.read(self.s['se_object_id'],5);self.write_object(token,data);return token
 def object_raw(self,token,count):
  logical=self.m.read(self.s['object_extents']+token[0]*16);bank=self.m.read(self.s['se_reu_map']+logical);return self.reu()[bank*65536:bank*65536+count],bank
 def prepare(self,baseline,pending=True):
  self.source(baseline,physical=256)
  merged=baseline
  if pending:
   pos=baseline.index(petscii('body'))+2;self.position(pos);self.key(13);merged=baseline[:pos]+b'\r'+baseline[pos:]
   assert self.get('se_hot_pending',1)==1
  return merged
 def seed_inputs(self,old,count,merged,valid=2):
  self.seed();self.cp('se_fb_source',self.read(self.s['se_doc_original'],5));self.cp('se_fb_old_token',old);self.cp('se_fb_old_count',count,2);self.cp('se_fb_old_source',self.read(self.s['se_doc_original'],5));self.cp('se_fb_old_epoch',self.get('se_r_revision',4),4);self.cp('se_fb_old_length',len(merged),3);self.cp('se_fb_old_valid',valid)
 def foreign_guard(self,before,bank):
  after=self.reu();assert all(after[i*65536:(i+1)*65536]==before[i*65536:(i+1)*65536] for i in range(256) if i!=bank)

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True);base=freeze()
 old=generic_build('generic-before',OUT/'baseline/src');new=generic_build('generic-after',ROOT/'src');assert old==new
 original=leaf.run
 def run(*args):
  a=list(args)
  if str(a[0])=='ca65' and str(a[-1]).endswith('fold/builder-retain.s'):a[1:1]=['-D','SE_FOLD_EDITOR_SOURCE=1']
  return original(*a)
 leaf.run=run
 try:report,records=leaf.build(OUT/'leaves',base)
 finally:leaf.run=original
 cpu_editor.ROOT=editor_fixture.ROOT=base;f=Fixture(records,OUT/'leaves',base);cases=[]
 old_source=petscii('# Main\ninside\n## Child\nbody\n# Tail\nend\n');prefix=petscii('# Preface\nintro\n');baseline=prefix+old_source
 try:
  # Exact transformed source intervals survive a newly inserted preceding fold.
  # Its child still has old parent0, while the freshly parsed parent is1.
  merged=f.prepare(baseline);tree,_,_,error=model.oracle(merged);assert not error and len(tree)==4
  old_tree,_,_,error=model.oracle(old_source);assert not error
  pending_at=baseline.index(petscii('body'))+2
  def moved(p):
   p+=len(prefix);return p+int(p>=pending_at)
  hints=[replace(x,start=moved(x.start),hidden=moved(x.hidden),end=moved(x.end),flags=3,saved=7,motion=99) for x in old_tree]
  assert hints[1].parent==0 and tree[2].parent==1 and hints[0].lines!=tree[1].lines
  hintbytes=b''.join(x.bytes() for x in hints);token=f.old_object(hintbytes);f.allocate();f.claim();f.seed_inputs(token,len(hints),merged)
  before=f.preserved();reu=f.reu();candidate_bank=f.object_raw(f.token,0)[1];locks=f.get('se_doc_read_locks',1)
  r=f.invoke('foldparse',0);assert not r.p&1 and r.a==2;assert f.cg('se_fb_keep')==2
  # Admission has frozen certification in KEEP, not a mutable input flag.
  f.cp('se_fb_old_valid',1);r=f.finish();assert not r.p&1 and r.a==0
  wanted=[replace(x,flags=int(i>0),saved=0,motion=0) for i,x in enumerate(tree)]
  actual,_=f.map_bytes();assert actual==b''.join(x.bytes() for x in wanted) and f.cg('se_fb_retained',2)==3
  assert f.preserved()==before and f.get('se_doc_read_locks',1)==locks and not f.get('se_fs_owned',1)
  assert f.object_raw(token,len(hintbytes))[0]==hintbytes;f.foreign_guard(reu,candidate_bank);f.release();assert f.document()==baseline
  cases.append('certified2 actual pending CR / transformed ranges / inserted preceding parent ordinal / stale line counts / saved state cleared')
  # Fresh ranges/kind/level and legal flag mask are all required. Numeric
  # ancestry/line metadata intentionally have no certification authority.
  for field,value in [('start',hints[1].start+1),('hidden',hints[1].hidden+1),('end',hints[1].end-1),('kind',3),('level',3),('flags',5)]:
   merged=f.prepare(baseline);bad=[replace(x) for x in hints];bad[1]=replace(bad[1],**{field:value});raw=b''.join(x.bytes() for x in bad);token=f.old_object(raw);f.allocate();f.claim();f.seed_inputs(token,len(bad),merged);before=f.preserved();reu=f.reu();bank=f.object_raw(f.token,0)[1]
   assert not f.invoke('foldparse',0).p&1;r=f.finish();assert not r.p&1 and r.a==0
   wanted=[replace(x,flags=int(i in (1,3)),saved=0,motion=0) for i,x in enumerate(tree)]
   assert f.map_bytes()[0]==b''.join(x.bytes() for x in wanted),(field,f.map_bytes()[0].hex());assert f.cg('se_fb_retained',2)==2;assert f.preserved()==before;f.foreign_guard(reu,bank);f.release()
  cases.append('SUMMARY/HIDDEN/END/KIND/LEVEL/unknown flag mismatches do not transfer')
  # Full current-source proof remains mandatory. A stale proof safely drops
  # retention while completing the fresh expanded map.
  for name,width in [('se_fb_old_source',5),('se_fb_old_epoch',4),('se_fb_old_length',3)]:
   merged=f.prepare(baseline);token=f.old_object(hintbytes);f.allocate();f.claim();f.seed_inputs(token,len(hints),merged);f.cp(name,f.cg(name,width)^1,width)
   assert not f.invoke('foldparse',0).p&1;r=f.finish();assert not r.p&1 and f.cg('se_fb_retained',2)==0 and f.map_bytes()[0]==b''.join(x.bytes() for x in tree);f.release()
  cases.append('current source token/revision/merged length mismatch retains nothing')
  for valid in [1,3,255]:
   merged=f.prepare(baseline);token=f.old_object(hintbytes);f.allocate();f.claim();f.seed_inputs(token,len(hints),merged,valid);snap=f.read(0x8D00,1152);reu=f.reu();r=f.invoke('foldparse',0);assert r.p&1 and r.a==0xB0 and f.read(0x8D00,1152)==snap and f.reu()==reu and not f.get('se_fs_owned',1);f.release()
  cases.append('uncertified1/3/255 rejects before lease or phase writes')
  for fault in ['alias','wrongtype','revoked','count','sourcechange','oldchange','cancel']:
   merged=f.prepare(baseline);token=f.old_object(hintbytes,owner=0x45 if fault=='wrongtype' else 0x46);f.allocate();f.claim();f.seed_inputs(token,len(hints),merged)
   if fault=='alias':f.cp('se_fb_old_token',f.token)
   if fault=='revoked':f.cp('se_fb_old_token',bytes([token[0],token[1]^1])+token[2:])
   if fault=='count':f.cp('se_fb_old_count',32769,2)
   before=f.preserved();reu=f.reu();r=f.invoke('foldparse',0)
   if fault in ['sourcechange','oldchange','cancel']:
    assert not r.p&1
    if fault=='sourcechange':f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    elif fault=='oldchange':f.cp('se_fb_old_count',len(hints)+1,2)
    r=f.invoke('foldparse',2 if fault=='cancel' else 1)
    assert bool(r.p&1)==(fault!='cancel')
   else:assert r.p&1
   assert f.reu()==reu and f.get('se_doc_read_locks',1)==0 and not f.get('se_fs_owned',1) and not f.cg('se_fold_valid')
   if fault!='sourcechange':assert f.preserved()==before
   f.release()
  cases.append('distinct candidate/type/generation/count guards, source/old binding changes and cancellation release owned lease without writes')
  result=dict(status='passed',resident_sha256=report['sha256'],payload_bytes={n:r['payload_bytes'] for n,r in records.items()},generic_default_byte_identity=hashlib.sha256(new).hexdigest(),generic_probe_bytes=len(new),cases=cases,source_bytes=len(merged),fresh_records=len(tree),retained_records=3,steps=f.steps,max_feed_per_step=f.max_feed,checked_reu_bytes=16*1024*1024,added_state_bytes=0,source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['src/fold/builder.s','src/fold/builder-retain.s','tests/test_fold_edited_hints.py']},scope='Actual rebound C17/C18/R18 with sealed800 R14 merged-source reader. Trusted certification is supplied by test; C19 journal/R20 admission integration remains parent-owned. No native claim.')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()

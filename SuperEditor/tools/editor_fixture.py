"""CPU fixture for actual resident editor services; ROM file imports only mocked."""
import json
from pathlib import Path
from peddle import Machine
from cpu_editor import startup,NAMES
from overlays import HEADER
ROOT=Path(__file__).resolve().parents[1]
class EditorFixture:
 def __init__(self):
  self.report=json.loads((ROOT/'build/editor-report.json').read_text());self.s=self.report['symbols'];self.m=Machine()
  self.assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES};self.max_service=0;self.total_instructions=0
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
  startup(self.m,self.s,self.assets);self.settle()
 def read(self,a,n):return bytes(self.m.read(a+i) for i in range(n))
 def get(self,n,w=3):return int.from_bytes(self.read(self.s[n],w),'little')
 def put(self,n,v,w=3):self.m.load(self.s[n],v.to_bytes(w,'little'))
 def call(self,n,a=0):
  regs,used=self.m.call(self.s[n],a=a,limit=2_000_000);self.total_instructions+=used
  if n=='se_editor_service':self.max_service=max(self.max_service,used)
  return regs
 def settle(self,error=0,render=False):
  steps=0
  while self.get('se_e_job',1):
   self.call('se_editor_service');steps+=1
   assert steps<25000,(self.get('se_e_job',1),self.get('se_e_error',1))
  assert self.get('se_e_error',1)==error,(hex(self.get('se_e_error',1)),hex(error))
  for n in ['se_doc_read_locks','se_s_owned','se_s_active','se_v_nav_busy','se_n_owned','se_b_phase','se_clip_busy']:assert self.get(n,1)==0,n
  if render and not error:
   self.render()
   assert self.get('se_v_seen',1)==1
  return steps
 def render(self):
  # Explicitly drain the public bounded-layout job before requiring pixels.
  # call('se_editor_render') remains a single invocation for scheduling tests.
  for _ in range(8):
   regs=self.call('se_editor_render');assert not regs.p&1,('render',hex(regs.a))
   if self.get('se_e_job',1):
    assert self.get('se_e_job',1) in (7,10) #layout or canonical-caret fold reveal
    self.settle()
   else:return regs
  raise AssertionError('layout did not converge')
 def command(self,c,error=0,render=False):
  self.put('se_e_error',0,1);self.call('se_editor_command',c);return self.settle(error,render)
 def key(self,c,error=0,mods=0):
  self.put('se_e_mods',mods,1)
  self.put('se_e_key',c,1);self.call('se_editor_input');return self.settle(error)
 def typed(self,text,error=0):
  self.key(0x88)
  for c in text:self.key(c)
  return self.key(13,error)
 def position(self,p):
  self.put('se_e_error',0,1)
  self.put('se_hot_position',p);assert not self.call('se_hot_call',1).p&1
  self.put('se_e_job',1,1);self.settle()
 def source(self,data,banks=2,physical=256):
  self.call('se_clear_state');self.put('se_reu_banks',physical,2)
  for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_overlay_init',0),('se_doc_init',banks)]:
   regs=self.call(name,a);assert not regs.p&1,(name,hex(regs.a))
  token=self.read(self.s['se_doc_original'],5)
  for i in range(0,len(data),1024):
   part=data[i:i+1024];self.m.load(self.s['se_object_id'],token);self.m.load(0x8000,part)
   self.put('se_object_offset',i);self.put('se_object_length',len(part),2);self.put('se_object_c64',0x8000,2);assert not self.call('se_object_copy').p&1
  self.put('se_doc_source_length',len(data));assert not self.call('se_doc_adopt_original').p&1
  for image in self.assets.values():
   self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);assert not self.call('se_overlay_import').p&1
  from font_fixture import install_font_pack
  install_font_pack(self)
  self.m.load(self.s['se_editor_settings'],self.read(self.s['session_defaults'],64))
  for name in ['se_history_cold','se_hot_cold']:assert not self.call(name).p&1
  assert not self.call('se_history_call',1).p&1
  self.put('se_hot_group',1,1);self.position(0);self.render()
 def document(self):
  out=bytearray()
  for i in range(0,self.get('se_doc_length'),1024):
   n=min(1024,self.get('se_doc_length')-i);self.put('se_doc_offset',i);self.put('se_doc_count',n,2);self.put('se_doc_c64',0x8000,2)
   assert not self.call('se_doc_read').p&1;out.extend(self.read(0x8000,n))
  return bytes(out)
 def close(self):self.m.close()

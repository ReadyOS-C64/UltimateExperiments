"""Actual C16 mode op3, checked R16/R17 admission and warm charset lifecycle.

Uses the same immutable46c8 capsule and private build as test_grid_editor.
Peddle executes real code; this does not claim character-ROM banking pixels or
native physical F8/CTRL-F8 behavior. No shared build or VICE calls.
"""
from pathlib import Path
import hashlib,json,sys
from test_grid_editor import ROOT,OUT,BASE,NAMES,Fixture,build
import cpu_editor,editor_fixture

def main():
 report,extras=build();cpu_editor.ROOT=editor_fixture.ROOT=BASE;cpu_editor.NAMES=editor_fixture.NAMES=NAMES
 f=Fixture(extras);cases=0;failures=0;busy=0;irqs=[]
 def call(command,mods=0,irq=False,error=None):
  f.put('se_e_command',command,1);f.put('se_e_mods',mods,1);f.put('se_overlay_frame',3,1)
  for n,v in [('pc',f.s['se_overlay_call']),('sp',0xFD),('a',16),('x',1),('y',0),('p',0x20|(4 if irq else 0))]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
  f.m.write(0x1FE,0xFE);f.m.write(0x1FF,2);n=f.runner.gr_run(f.m.handle,3_000_000);assert n,('nonreturn',hex(f.m.regs().pc));r=f.m.regs()
  assert bool(r.p&1)==(error is not None) and r.a==(error or 0),(command,mods,r.a,error)
  assert bool(r.p&4)==irq,('IRQ state',command,irq,r.p)
  return n
 def canonical():
  fields={n:f.read(f.s[n],w) for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_doc_read_locks',1),('se_sel_anchor',3),('se_sel_mark',1),('se_clip_token',5),('se_clip_length',3),('se_clip_generation',2),('se_f_owner',1),('se_e_ui',1)]}
  for start,end in [('se_hot_state_start','se_hot_state_end'),('se_h_state_start','se_h_state_end')]:fields[start]=f.read(f.s[start],f.s[end]-f.s[start])
  return fields|{'hot':f.read(0x9200,2048),'phase':f.read(0x8D00,1152),'nav':f.read(0x9180,128),'diag':f.read(0x8800,128),'shim':f.read(0xC600,1024),'catalog':f.read(0x7F40,192)}
 def settings():
  names=[('se_mode',1),('se_v_columns',1),('se_r_valid',1),('se_l_valid',1),('se_st_valid',1),('se_st_request',1),('se_st_cp_valid',1),('se_n_preferred_valid',1),('se_l_manual',1),('se_l_pan',3),('se_v_top',3),('se_l_need_wrap',1),('se_e_redraw',1)]
  return {n:f.read(f.s[n],w) for n,w in names}|{'VIC':f.read(0xD000,64),'CIA':f.read(0xDD00,4),'port':f.read(1,1),'screen':f.read(0x4000,1024),'bitmap':f.read(0x6000,8192),'font':f.read(0x4800,2048)}
 def seed(old):
  f.put('se_mode',old,1);f.put('se_v_columns',[0,60,80][old],1);f.put('se_e_ui',2,1)
  for n in ['se_r_valid','se_l_valid','se_st_valid','se_st_request','se_st_cp_valid','se_n_preferred_valid','se_l_manual']:f.put(n,0x55,1)
  f.put('se_l_pan',0x10203);f.put('se_v_top',0x123);f.put('se_l_need_wrap',0,1);f.put('se_e_redraw',0,1)
  for a,v in [(1,0x36),(0xDD00,0xA6),(0xDD02,0xF3),(0xD011,0x1B if old==0 else 0x3B),(0xD018,2 if old==0 else 8),(0xD016,8),(0xD015,0xA5)]:f.m.write(a,v)
 try:
  f.source(b'A mixed-case source\rSecond line\r');f.position(2);f.command(68);f.position(7);f.command(69);f.command(50);f.position(10);f.key(0xC2);assert f.get('se_hot_pending',1)
  f.put('se_sel_mark',1,1);f.put('se_sel_anchor',3)
  reu=f.reu()
  for old in range(3):
   for cmd,mods,target in [(96,0,0),(97,0,1),(98,0,2),(100,0,(old+1)%3),(100,4,(old-1)%3),(101,0,(old-1)%3),(101,4,(old-1)%3)]:
    for irq in [False,True]:
     seed(old);before=canonical();bits=f.read(0x6000,8192);port=f.read(1,1);cia=f.read(0xDD00,4);call(cmd,mods,irq)
     assert canonical()==before and f.reu()==reu,('canonical',old,cmd,mods)
     assert f.get('se_mode',1)==target and f.get('se_v_columns',1)==[0,60,80][target]
     for n in ['se_r_valid','se_l_valid','se_st_valid','se_st_request','se_st_cp_valid','se_n_preferred_valid','se_l_manual']:assert f.get(n,1)==0,n
     for n in ['se_l_pan','se_v_top']:assert f.get(n)==0,n
     assert f.get('se_l_need_wrap',1)==f.get('se_e_redraw',1)==1
     assert f.read(1,1)==port and f.read(0xDD00,4)==cia and f.read(0x6000,8192)==bits
     if target:assert [f.m.read(a) for a in [0xD018,0xD011,0xD016,0xD015]]==[8,0x3B,8,0]
     elif old:assert [f.m.read(a) for a in [0xD018,0xD011,0xD016,0xD015]]==[2,0x1B,8,0] and f.read(0x4000,1024)==b' '*1024
     else:assert f.m.read(0xD015)==0xA5 #same40 does not clear/reinitialize display
     cases+=1
  # An unavailable requested leaf must not publish even invalidation bytes.
  for old,cmd,leaf in [(0,97,17),(0,98,16),(1,98,16),(2,97,17)]:
   seed(old);ids=f.read(f.s['se_overlay_ids'],24);f.m.write(f.s['se_overlay_ids']+ids.index(leaf),0);before=canonical();state=settings();call(cmd,error=0x17);assert canonical()==before and settings()==state and f.reu()==reu;f.m.load(f.s['se_overlay_ids'],ids);failures+=1
  # Active navigation and every nonzero phase owner refuse before admission.
  for name,value in [('se_f_owner',1),('se_f_owner',2),('se_f_owner',255),('se_v_nav_busy',1),('se_n_owned',1)]:
   seed(0);f.put(name,value,1);before=canonical();state=settings();call(97,error=0x7A);assert canonical()==before and settings()==state;f.put(name,0,1);busy+=1
  for old,cmd in [(0,99),(1,95),(2,102),(3,96),(255,96)]:
   seed(0);f.put('se_mode',old,1);before=canonical();state=settings();call(cmd,error=0x77);assert canonical()==before and settings()==state;failures+=1
  result=dict(status='passed',resident_sha256=report['sha256'],payload_bytes=len((OUT/'grid.bin').read_bytes()),switches=cases,admission_or_unavailable_failures=failures,busy_refusals=busy,IRQ_states=[0,1],source_pending_preserved=True,clipboard_history_selection_preserved=True,whole_REU_bytes=2*1024*1024,shim_bytes=1024,new_BSS=0,new_ZP=0,scope='Actual C16 op3 and real checked R16/R17 imports, warm resident display initializer executed; CPU register/ownership proof, no native character-ROM pixel or physical-key claim')
  (OUT/'mode-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()

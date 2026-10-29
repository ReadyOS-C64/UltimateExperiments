"""Standalone C29/R26 native lifecycle, controlled same-process warm restore.

Real File/Open/IRQ bytes precede and follow the experiment. Monitor PC/SP and
fresh cold bootstrap writes are explicit seams. Bounded component calls mask
IRQ as required by the checked R26 ABI and restore it between every slice.
No old overlay or stack continuation is resumed, no ReadyOS handoff claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,subprocess,zipfile,sys
import test_geos_fold_native as native
import test_lifecycle_editor as component
import test_geos_semantic_editor as semantic
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
from vice_config import step
import vice_plan
from cache_job_build import editor_pair_index
ROOT=native.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture'


class Plan(native.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=7900;p['global_defaults']['monitor_port_span']=1;p['global_defaults']['timeouts']['step_s']=120;return p
 def condition(self,ui=0,owner=0):
  pairs=[('se_e_ui',ui),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0),('se_doc_read_locks',0),('se_f_owner',owner),('se_input_nmi_pending',0)]
  return ' && '.join(f'(@cpu:${self.s[n]:04x} == ${v:02x})'for n,v in pairs)+f' && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'
 def stop(self,ui=0,owner=0):return ['delete',f'break exec ${self.idle_pc:04x} if {self.condition(ui,owner)}','x','delete']
 def store(self,at,data):return [f'> {at+i:04x} '+data[i:i+128].hex(' ')for i in range(0,len(data),128)]
 def call_cold(self,ident,entry,*,ui=0,owner=0,after=()):
  caps=self.out/'captures';caps.mkdir(exist_ok=True)
  self.raw(ident+'_coherent',[*self.stop(ui,owner),f'registers PC=${entry:04x}, SP=$ff, FL=$20',f'until $0b70',*after,f'bsave "{caps}/{ident}-ram.bin" 0 $0000 $cfff',f'registers PC=${self.s["se_idle"]:04x}, SP=$ff, FL=$20',f'bsave "{caps}/{ident}-colors.bin" 0 $d800 $dbe7'])
 def capture(self,ident,data,caret,node,*,current='DIVERSE',pending=0,ui=0):
  self.memory(ident+'_caret','se_hot_caret',caret,3);self.memory(ident+'_pending','se_hot_pending',pending);self.memory(ident+'_node','se_h_current',node,4)
  if self.test_mode<3:
   self.memory(ident+'_style_valid','se_st_valid',1);self.memory(ident+'_style_complete','se_st_request',0)
  self.snapshot(ident,data,self.test_mode,ui);self.cases[-1].update(caret=caret,node=node,current=current,pending=pending,preview=ui==4)


def prepare(source):
 e=native.freeze(source);target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-lifecycle-native');target.parent.mkdir(exist_ok=True);shutil.move(e,target);e=target
 images=component.build(e/'component',source)
 for n,b in images.items():assert b==(e/(n+'.seo')).read_bytes(),(n,'private labels differ from sealed asset')
 labels={x[2].lstrip('.'):int(x[1],16)for line in(e/'component/lifecopy.lbl').read_text().splitlines()if len(x:=line.split())==3 and x[0]=='al'}
 (e/'copy-symbols.json').write_text(json.dumps(labels,indent=2)+'\n')
 return e


def bootstrap(n):
 binding=bytes.fromhex(json.loads((n.e/'freeze.json').read_text())['resident_binding']);resume=(n.e/'lifectrl.seo').read_bytes()[36+0x800:36+0x900]
 # Cold one-shot call at0B00: exact IRQ/status result at08F0/1; normal IRQs
 # restored after each bounded call. The monitor stop is after the PLP.
 code=bytes.fromhex('08 78 d8 a9 02 20 e0 0a 8d f0 08 08 68 8d f1 08 28 4c 70 0b')
 n.raw('fresh_cold_descriptor',[*n.stop(),*n.store(0x800,binding+bytes(0x40)),*n.store(0xA00,resume),*n.store(0xB00,code)])
 return code


def scenario(e,mode=3,preview=False):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'lifecycle');n.test_mode=mode;data=native.live.grid.fixture();q=native.live.grid.native_text('Q');r=native.live.grid.native_text('R');pending=q+data
 labels=json.loads((e/'copy-symbols.json').read_text());caps=n.out/'captures';caps.mkdir(exist_ok=True)
 n.boot();n.open('open_diverse',b'DIVERSE')
 if mode==3:n.typed('enter_geos','mode hires')
 elif mode:n.mode_to(mode)
 code=bootstrap(n)
 # Prime C29 using its idempotent CANCEL before the cheap FILE admission check.
 n.modal('actual_file_modal','O');n.call_cold('prime_C29',0xB00,ui=3,owner=1)
 n.raw('modal_before_coherent',[f'bsave "{caps}/modal-before-ram.bin" 0 $0000 $cfff',f'bsave "{caps}/modal-before-colors.bin" 0 $d800 $dbe7'])
 n.steps.append(step('modal-before-reu','dump.reu',mode='full',stage_tag='modal-before_reu'))
 n.raw('set_begin',[*n.store(0xB04,b'\x00')])
 n.call_cold('modal_refusal',0xB00,ui=3,owner=1);n.memory('modal_busy_A',0x8F0,0xD5)
 n.memory('modal_no_phase',0x820,0);n.steps.append(step('modal-after-reu','dump.reu',mode='full',stage_tag='modal-after_reu'))
 n.raw('resume_modal',[f'registers PC=${n.s["se_idle"]:04x}, SP=$ff, FL=$20'])
 n.send('modal_cancel',b'\3',owner=0);n.send('pending_Q',q)
 if preview:n.typed('formatted_preview','preview',ui=4)
 n.capture('pending-before',pending,1,1,pending=1,ui=4 if preview else 0)
 # Cold driver BEGIN then381 bounded STEP calls. PLP restores IRQ between
 # calls; no foreground source/input event is injected during the capture.
 asm=''' .setcpu "6502"
.segment "CODE"
entry:
 lda #0
 sta $0BF0
 lda #0
 sta $0BF1
 sta $0BF2
loop:
 php
 sei
 cld
 lda $0BF0
 jsr $0AE0
 sta $08F0
 php
 pla
 sta $08F1
 plp
 lda $08F1
 and #1
 bne done
 lda $0BF0
 beq next
 inc $0BF1
 bne :+
 inc $0BF2
:
 lda $08F0
 beq done
next:
 lda #1
 sta $0BF0
 nop
 nop
 jmp loop
done:
 jmp $0B70
'''
 (e/'capture-driver.s').write_text(asm);(e/'capture-driver.cfg').write_text('MEMORY {O:file=%O,start=$0B00,size=$70;} SEGMENTS {CODE:load=O,type=ro;}')
 component.command('ca65','-o',e/'capture-driver.o',e/'capture-driver.s');component.command('ld65','-C',e/'capture-driver.cfg','-o',e/'capture-driver.bin',e/'capture-driver.o')
 n.raw('install_capture_driver',n.store(0xB00,(e/'capture-driver.bin').read_bytes()))
 n.call_cold('prepared',0xB00,ui=4 if preview else 0);n.memory('capture_committed_A',0x8F0,0);n.memory('capture_phase_idle',0x820,0);n.memory('exact381_steps',0xBF1,381,2)
 n.steps.append(step('prepared_reu','dump.reu',mode='full',stage_tag='prepared_reu'))
 # Quiesce IRQ before perturbation; saved provider bytes are the live same-
 # process authority, restored exactly before checked fresh R26 validation.
 provider=[('map','se_reu_map',256),('logical','se_reu_logical_owner',256),('physical','se_reu_physical_owner',256),('epoch','se_reu_epoch',2),('retired','se_reu_retired',1)]
 commands=['registers FL=$24']
 for tag,name,count in provider:
  at=n.s[name];commands.append(f'bsave "{caps}/provider-{tag}.bin" 0 ${at:04x} ${at+count-1:04x}')
 commands += ['fill $1000 $c5ff $a5','fill $ca00 $cfff $5a','fill $0002 $0019 $3c']
 for tag,name,count in provider:commands.append(f'bload "{caps}/provider-{tag}.bin" 0 ${n.s[name]:04x}')
 commands += n.store(0xA000,(e/'lifecopy.seo').read_bytes()[36:])+n.store(0xA00,(e/'component/resume.bin').read_bytes())
 # Restoring R26 runs entirely in fresh A-slot code; final STEP enters a new
 # 0900 DMA thunk ->fresh0A00 prelude, resets SP, then real foreground idle.
 restore=''' .setcpu "6502"
.segment "CODE"
entry:
 sei
 cld
 jsr RESTORE_BEGIN
 bcs done
loop:
 jsr COPY_STEP
 bcs done
 jmp loop
done:
 sta $08F0
 php
 pla
 sta $08F1
 jmp $0B70
'''.replace('RESTORE_BEGIN',f'${labels["se_lc_restore_begin"]:04X}').replace('COPY_STEP',f'${labels["se_lc_copy_step"]:04X}')
 (e/'restore-driver.s').write_text(restore);component.command('ca65','-o',e/'restore-driver.o',e/'restore-driver.s');component.command('ld65','-C',e/'capture-driver.cfg','-o',e/'restore-driver.bin',e/'restore-driver.o')
 commands += n.store(0xB00,(e/'restore-driver.bin').read_bytes())+[f'bsave "{caps}/scrambled-ram.bin" 0 $0000 $cfff',f'registers PC=$0b00, SP=$ff, FL=$24',f'until $0a00',f'bsave "{caps}/exact-restored-ram.bin" 0 $0000 $cfff',f'bsave "{caps}/restore-boundary-colors.bin" 0 $d800 $dbe7',f'until ${n.s["se_idle"]:04x}']
 n.raw('fresh_restore_coherent',commands+[f'bsave "{caps}/prelude-finished-ram.bin" 0 $0000 $cfff',f'bsave "{caps}/prelude-finished-colors.bin" 0 $d800 $dbe7'])
 n.capture('pending-resumed',pending,1,1,pending=1,ui=4 if preview else 0)
 if preview:n.send('return_literal_after_restore',b'\r')
 n.send('type_after_resume',r);n.capture('typed-after',q+r+data,2,1,pending=1)
 n.send('undo_actual',b'\x1A');n.capture('undo',data,0,1)
 saved=b'LIFEPV' if preview else b'LIFE'+str((40,60,80,3)[mode]).encode()
 n.save_as('save_after_restore',saved);n.capture('saved',data,0,1,current=saved.decode())
 n.open('reopen_after_restore',saved);n.capture('reopened',data,0,1,current=saved.decode())
 return n



def evaluate(e):
 e=Path(e);out=e/'lifecycle';caps=out/'captures';report=json.loads((e/'editor-report.json').read_text());s=report['symbols'];identity=json.loads((e/'freeze.json').read_text());cases=json.loads((out/'cases.json').read_text());images=native.live.grid.reu_images(out/'run')
 fonts={name:(e/name).read_bytes()for name in native.live.geos.GEOS_FONTS+('native8.bin',)};palette={};observed=[]
 def ram(name):return(caps/(name+'-ram.bin')).read_bytes()
 def field(data,name,n=1):return int.from_bytes(data[s[name]:s[name]+n],'little')
 def canonical(data):
  fields=[('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_hot_ready',1),('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),('se_hot_before',3),('se_hot_group',1),('se_hot_left',2),('se_hot_right',2),('se_sel_mark',1),('se_sel_anchor',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_h_group',1),('se_h_open_group',1),('se_clip_token',5),('se_clip_length',3)]
  return data[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(data[s[n]:s[n]+w]for n,w in fields)+data[0x9200:0x9A00]
 before,refused=ram('modal-before'),ram('modal_refusal')
 assert images['modal-before']==images['modal-after'],'FILE refusal changed REU'
 assert refused[0x8F0]==0xD5 and refused[0x8F1]&1 and refused[0x820]==0 and refused[0x810]==0,'FILE refusal did not precede allocation/capture'
 assert canonical(before)==canonical(refused) and before[0x8D00:0x9053]==refused[0x8D00:0x9053],'FILE opaque frame/source changed'
 # CANCEL primed actual C29 after entering the real File modal. Thus BEGIN is
 # an actual catalog hit; no staging/code load occurred. Permit only the real
 # resident call bookkeeping and independent IRQ tick counter between stops.
 allowed=[('se_input_irq_ticks',2),('se_overlay_frame',1),('se_overlay_hits',2),('se_overlay_calls',2),('call_result',1)]
 want=bytearray(before)
 for name,count in allowed:want[s[name]:s[name]+count]=refused[s[name]:s[name]+count]
 for lo,hi in((0x1000,0xC600),(0xCA00,0xD000)):assert refused[lo:hi]==want[lo:hi],('FILE refusal unexpected warm writer',hex(lo))
 assert field(before,'se_overlay_loads',2)==field(refused,'se_overlay_loads',2),'primed FILE refusal unexpectedly loaded a leaf'

 prepared=ram('prepared');reu=images['prepared'];handle=prepared[0x810];bank=prepared[0x811];assert handle and bank
 assert prepared[s['se_reu_map']+handle]==bank and prepared[s['se_reu_logical_owner']+handle]==prepared[s['se_reu_physical_owner']+bank]==0xFC
 payload=reu[bank*65536:bank*65536+0xBC18];header=reu[bank*65536+0xBC20:bank*65536+0xBC60]
 assert header[:8]==b'LCA1'+bytes([1,0xA5,3,0xFC]) and int.from_bytes(header[51:53],'little')==binascii.crc_hqx(payload,0xffff) and int.from_bytes(header[62:64],'little')==binascii.crc_hqx(header[:62],0xffff)
 baseline=images['pending-before'];at=bank*65536;wanted=bytearray(baseline);wanted[at:at+0xBC18]=payload;wanted[at+0xBC20:at+0xBC60]=header
 assert reu==wanted,'capture wrote outside exact owned FC payload/header extents'
 resumed_reu=images['pending-resumed'];resumed_ram=ram('pending-resumed');wanted=bytearray(reu)
 cache_handle=field(resumed_ram,'se_gc_handle');cache_bank=resumed_ram[s['se_reu_map']+cache_handle] if cache_handle else 0
 if cache_handle:
  assert resumed_ram[s['se_reu_logical_owner']+cache_handle]==resumed_ram[s['se_reu_physical_owner']+cache_bank]==0xFE
  wanted[cache_bank*65536:(cache_bank+1)*65536]=resumed_reu[cache_bank*65536:(cache_bank+1)*65536]
 assert resumed_reu==wanted,'warm restoration/redraw changed foreign/source/catalog/font/FC REU'

 restored=ram('exact-restored');scrambled=ram('scrambled')
 for at,length,offset in component.EXTENTS:
  assert restored[at:at+length]==payload[offset:offset+length],('actual exact warm/ZP restore',hex(at))
 assert restored[0xC600:0xCA00]==before[0xC600:0xCA00]==bytes((i*73+29)&255 for i in range(1024))
 warm=bytearray([0xA5])*(0xC0DC-0x1000);fresh=(e/'lifecopy.seo').read_bytes()[36:]
 warm[0xA000-0x1000:0xA000-0x1000+len(fresh)]=fresh #explicit trusted bootstrap exception
 assert scrambled[0x1000:0xC0DC]==warm and scrambled[0xCA00:0xD000]==bytes([0x5A])*0x600 and scrambled[2:26]==bytes([0x3C])*24
 for tag,name,length in [('map','se_reu_map',256),('logical','se_reu_logical_owner',256),('physical','se_reu_physical_owner',256),('epoch','se_reu_epoch',2),('retired','se_reu_retired',1)]:
  saved=(caps/('provider-'+tag+'.bin')).read_bytes();assert len(saved)==length and scrambled[s[name]:s[name]+length]==saved and restored[s[name]:s[name]+length]==saved,(name,'live provider authority')
 assert canonical(ram('pending-before'))==canonical(ram('pending-resumed')),'canonical pending/history/clipboard warm lifetime'
 assert reu[bank*65536:bank*65536+0xBC60]==images['pending-resumed'][bank*65536:bank*65536+0xBC60],'restore altered FC image'
 for c in cases:
  ident=c['id'];data=bytes.fromhex(c['source']);memory=ram(ident);colors=(caps/(ident+'-colors.bin')).read_bytes();image=images[ident];f=Captured(s,memory,colors,e);f.colored=True
  assert native.live.merged(f,image)==data and f.get('se_hot_caret')==c['caret'] and f.get('se_h_current',4)==c['node'] and f.get('se_hot_pending',1)==c['pending'],(ident,'canonical source/caret/history')
  assert f.get('se_e_ui',1)==c['ui'] and f.get('se_mode',1)==c['mode'] and not any(f.get(k,1)for k in('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_f_owner','se_e_error')),(ident,'native resumed quiescence') #owner0 makes FILE/source phase bytes opaque
  assert f.read(0xC600,1024)==before[0xC600:0xCA00]
  if c.get('preview'):
   from geos_preview_model import render
   from test_geos_preview_vice import pack_catalog
   catalog=pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin']);page=render(data,f.read(0xCB80,64),catalog=catalog,top=f.get('se_v_top'));matrix,colors_,_=native.live.geos.grid.logical_ui(f,data);bits,attrs=native.live.geos.with_chrome(page.bitmap,page.attrs,matrix,colors_,fonts['native8.bin'])
  elif c['mode']==3:bits,attrs,_,_=semantic.expected(f,data,fonts)
  else:
   (bits,attrs),_,_,_=native.live.geos.grid.expected(f,data)
   if c['mode']==0:
    assert memory[0x4000:0x43E8]==bits and bytes(v&15 for v in colors)==attrs,(ident,'source40 chars/colors')
    font=(e/'chargen.bin').read_bytes()[2048:4096];assert memory[0x4800:0x5000]==font,(ident,'full native256 font')
    matrix,inks=bits,attrs;bits=bytearray(8000);attrs=bytearray(1000)
    for row in range(25):
     for col in range(40):
      at=row*40+col;code=matrix[at];bits[row*320+col*8:row*320+col*8+8]=font[code*8:code*8+8];attrs[at]=(inks[at]<<4)|6
    bits,attrs=bytes(bits),bytes(attrs)
  if c['mode']:assert memory[0x6000:0x7F40]==bits and memory[0x4000:0x43E8]==attrs,(ident,'independent bitmap/attrs')
  width,height,pixels=read_png(out/('native-'+ident+'.png'));assert(width,height)==(384,272)
  for y in range(200):
   for x in range(320):
    attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x&7));color=attr>>4 if ink else attr&15;actual=pixels[(y+35)*width+x+32]
    assert actual==palette.setdefault(color,actual),(ident,'native VIC pixel',x,y)
  for order,name in enumerate(identity['catalog']):
   capsule=(e/(name+'.seo')).read_bytes();index=editor_pair_index(capsule[5],capsule[6]) if 'catalog_index' in s else order
   asset=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[index>>4],1);physical=memory[s['se_reu_map']+asset];blob=capsule[36:];at=physical*65536+(index&15)*4096
   assert memory[s['se_reu_logical_owner']+asset]==memory[s['se_reu_physical_owner']+physical]==2 and image[at:at+len(blob)]==blob,(ident,'all sealed assets',name)
  observed.append(dict(id=ident,source_bytes=len(data),caret=c['caret'],pending=c['pending'],bitmap_sha256=hashlib.sha256(bits).hexdigest()))
 disk=D81Image((e/'working.d81').read_bytes());initial=D81Image((e/'initial-fixtures.d81').read_bytes());original={v.name for v in initial.entries()};data=native.live.grid.fixture()
 saved=next(c['current'].encode()for c in cases if c['id']=='saved')
 assert {v.name for v in disk.entries()}==original|{saved} and disk.read(saved,kind=1).data==data
 for name in original:assert disk.read(name).data==initial.read(name).data and disk.read(name).sectors==initial.read(name).sectors,(name,'unrelated file')
 result=dict(status='passed',identity=identity,modes=sorted({c['mode']for c in cases}),preview=any(c.get('preview')for c in cases),frames=observed,native_pixels=len(cases)*64000,attributes=len(cases)*1000,prepare_steps=381,file_refusal_warm_allowlist=allowed,file_refusal_overlay_loads=0,restored_bytes=0xBC18,shim_bytes=1024,catalog_assets=len(identity['catalog']),saved_bytes=len(data),scope='Actual IRQ FileOpen/pending typing, packaged C29/R26 bounded masked calls with IRQ restored between slices, controlled fresh trusted bootstrap and same-process live-provider warm restore, new prelude, native typing/Undo/SaveAs/reopen. No old stack continuation, ReadyOS, physical RESTORE or external IRQ/NMI ownership claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--verify',type=Path);p.add_argument('--mode',type=int,choices=range(4),default=3);p.add_argument('--preview',action='store_true');a=p.parse_args()
 if a.verify:return evaluate(a.verify)
 if not a.run:print('Prepared native lifecycle controlled bootstrap proof; --run uses private7900/text8000.');return
 assert not a.preview or a.mode==3,'preview requires mode3'
 e=prepare(a.fixture);n=scenario(e,a.mode,a.preview);plan=n.plan();assert len({v['id']for v in plan['steps']})==len(plan['steps'])
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 project=native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;component.command('dotnet','build',project,'--nologo')
 print('NATIVE',e,'steps',len(n.steps),flush=True);vice_plan.run_plan(plan,n.out);evaluate(e)

if __name__=='__main__':main()

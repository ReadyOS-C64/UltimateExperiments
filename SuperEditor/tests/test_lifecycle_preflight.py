"""Actual current-editor lifecycle admission component; NOT snapshot/resume.

Runs real source/history/clipboard services and a newly linked read-only gate.
No general DMA, product build, native emulator, cold initialization or cleanup
is substituted into the gate. Existing editor fixture source setup/ROM import
seams are explicit, frozen with the current resident and all SEO assets.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess,sys,shutil,hashlib,re
import test_fold_controller as editor
from overlays import wrap,HEADER
ROOT=editor.ROOT
BUSY=['se_e_job','se_e_draw_busy','se_e_redraw','se_f_owner','se_v_nav_busy','se_n_owned','se_l_active','se_s_active','se_s_owned','se_diag_active','se_diag_owned','se_ef_active','se_doc_busy','se_doc_read_locks','se_snapshot_busy','se_hot_phase','se_hot_owned','se_h_phase','se_h_owned_lease','se_h_owned_capture','se_h_owned_splice','se_b_phase','se_b_history_owned','se_b_clip_owned','se_clip_busy','se_clip_copy_frame_has_object','se_clip_copy_frame_has_lease','se_input_nmi_pending']
FIELDS=[('se_reu_epoch',2),('se_doc_epoch',2),('se_doc_generation',2),('se_doc_meta',5),('se_doc_original',5),('se_doc_append',5),('se_doc_length',3),('se_doc_root_count',1),('se_r_revision',4),('se_hot_ready',1),('se_hot_pending',1),('se_hot_phase',1),('se_hot_owned',1),('se_hot_fault',1),('se_hot_epoch',2),('se_hot_generation',2),('se_hot_original',5),('se_hot_append',5),('se_hot_base',3),('se_hot_old_length',2),('se_hot_length',2),('se_hot_left',2),('se_hot_right',2)]
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise AssertionError(p.stdout+p.stderr)
def build(out,base):
 out.mkdir();objects=[]
 for flag,tag in [(False,'direct'),(True,'c29')]:
  o=out/(tag+'.o');command('ca65','-g','-I','src',*(['-D','LC_PREFLIGHT_IN_C29=1'] if flag else []),'-o',o,'src/lifecycle/preflight.s')
  command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),o)
  command('ca65','-g','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s'))
  (out/'leaf.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }')
  command('ld65','-C',out/'leaf.cfg','-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),o,out/(tag+'-aliases.o'))
  objects.append((out/(tag+'.bin')).read_bytes())
 digest=json.loads((base/'build/editor-report.json').read_text())['resident_binding']['digest']
 (out/'entry.s').write_text('.setcpu "6502"\n.import se_lc_preflight\n.segment "CODE"\n.byte '+','.join('$'+digest[i:i+2] for i in range(0,32,2))+'\njmp se_lc_preflight\n')
 command('ca65','-g','-o',out/'entry.o',out/'entry.s')
 command('ld65','-C',out/'leaf.cfg','-o',out/'sealed.bin','-m',out/'sealed.map',out/'entry.o',out/'c29.o',out/'c29-aliases.o')
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];sealed=wrap((out/'sealed.bin').read_bytes(),1,29,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'preflight.seo').write_bytes(sealed)
 return *objects,sealed

def run(out,smoke=False):
 base,r,names=editor.freeze(out);(base/'build/geos-font-catalog').mkdir();shutil.copy2(ROOT/'build/geos-font-catalog/font-pack.bin',base/'build/geos-font-catalog/font-pack.bin')
 editor.cpu_editor.ROOT=editor.editor_fixture.ROOT=base;editor.cpu_editor.NAMES=editor.editor_fixture.NAMES=names
 import font_fixture;font_fixture.ROOT=base
 direct,c29,sealed=build(out/'leaf',base);f=editor.Fixture(out);checks=[];calls=[]
 try:
  f.source(editor.native_text('# Main\rPending source is preserved.\r# Tail\rLast line.\r'),banks=1);assert not f.call('se_clip_init').p&1
  original_boot=f.read(0x800,2048)
  f.put('se_status',1,1);f.m.load(0x800,bytes.fromhex(r['resident_binding']['digest']));f.m.write(0xC6,0);f.m.write(0x98,0)
  def gate(expected=0,variant=direct,cheap=False):
   f.m.load(0xB000,variant);before=f.read(0,65536);reu=f.reu();canonical=f.canonical();r0,used=f.m.call(0xB000);after=f.read(0,65536)
   assert r0.a==expected and bool(r0.p&1)==bool(expected),(hex(expected),hex(r0.a),hex(r0.p))
   want=bytearray(before)
   allowed=[(0x100,0x200)]
   if not cheap:allowed += [(0xC40,0xC7B),(0xC80,0xC89),(f.s['se_object_id'],f.s['se_object_id']+12)]+[(f.s[n],f.s[n]+1) for n in ('validate_index','validate_extent','validate_type')]
   for a,b in allowed:want[a:b]=after[a:b]
   assert after==want,('fullRAM',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
   assert f.reu()==reu and f.canonical()==canonical
   if not expected:
    assert f.read(0xC40,59)==b''.join(f.read(f.s[n],w) for n,w in FIELDS)
    assert int.from_bytes(f.read(0xC80,3),'little')==f.get('se_doc_length')-f.get('se_hot_old_length',2)+f.get('se_hot_length',2)
   # Private direct load replaced C-slot bytes outside the product loader.
   # Explicit fixture invalidation forces the next real root operation to
   # reload its genuine SEO, rather than trusting the displaced active tag.
   f.m.write(f.s['se_overlay_active']+1,0)
   calls.append(dict(error=expected,instructions=used));return r0
  gate();checks.append('actual-source-history-clipboard/full59identity/wholeRAMand16MiBREU')
  f.command(68)
  for _ in range(5):f.command(2)
  f.command(69);f.key(3);f.render();assert f.get('se_clip_active',1)==1 and f.get('se_clip_length')==5;gate();checks.append('actual5byteclipboard/type5validated-andretained')
  f.position(12);f.key(0xD1);f.render();assert f.get('se_hot_pending',1)==1;gate();checks.append('actualpendinginsertaccepted-withoutflush-group/savepoint/sourcechanges')
  print('FIRST LIFECYCLE PREFLIGHT PASS: real pending editor +source/history/clipboard validators,59-bytecold witness; phase/shim/fullRAM/16MiB exact',flush=True)
  if not smoke:
   # Corrupt state through public fields; busy refusals must not write even
   # the cold identity/scratch or object request, and foreign phases are opaque.
   for name in BUSY:
    at=f.s[name];old=f.m.read(at);f.m.write(at,1);gate(0xD5,cheap=True);f.m.write(at,old)
   for a in (0xC6,0x98,f.s['se_gf_state']+5,f.s['se_gf_state']+8,f.s['se_overlay_busy'],f.s['se_overlay_busy']+1):
    old=f.m.read(a);f.m.write(a,1);gate(0xD5,cheap=True);f.m.write(a,old)
   for owner in (1,2,3,4,255):
    old=f.read(0x8D00,1152);f.m.load(0x8D00,bytes((i*37+owner)&255 for i in range(1152)));f.put('se_f_owner',owner,1);gate(0xD5,cheap=True);f.put('se_f_owner',0,1);f.m.load(0x8D00,old)
   checks.append('39busy/job/channel/lease/phase/overlay/FD predicates plusforeignopaque1152bytes')
   for name,value,code in [('se_status',0,0xD6),('se_mode',4,0xD6),('se_v_columns',60,0xD6),('se_l_mode',2,0xD6),('se_l_manual',2,0xD6),('se_input_head',64,0xD6),('se_input_tail',1,0xD5),('se_e_ui',1,0xD5),('se_e_ui',2,0xD5),('se_e_ui',3,0xD5),('se_e_ui',4,0xD6),('se_r_presentation',1,0xD6),('se_reu_retired',1,0xD6)]:
    old=f.get(name,1);f.put(name,value,1);gate(code,cheap=True);f.put(name,old,1)
   for n in range(16):
    old=f.m.read(0x800+n);f.m.write(0x800+n,old^1);gate(0xD8,cheap=True);f.m.write(0x800+n,old)
   checks.append('UI/mode/dimension/queue/retired validation andall16bindingbytes')
   for name,width,value in [('se_hot_right',2,2049),('se_hot_left',2,2049),('se_hot_length',2,2049),('se_hot_old_length',2,2049),('se_hot_base',3,0xFFFFF0),('se_hot_caret',3,f.get('se_hot_caret')+1),('se_hot_pending',1,2),('se_hot_epoch',2,f.get('se_hot_epoch',2)^1),('se_hot_generation',2,f.get('se_hot_generation',2)^1)]:
    old=f.read(f.s[name],width);f.put(name,value,width);gate(0xD9);f.m.load(f.s[name],old)
   checks.append('9fullpendinggapshape/lifetime/24bitoverflow/caretgeometryrefusals')
   for name in ('se_doc_meta','se_doc_original','se_doc_append'):
    token=f.read(f.s[name],5)
    for n in range(5):
     f.m.load(f.s[name],token);f.m.write(f.s[name]+n,token[n]^0x80);gate(0x31)
    f.m.load(f.s[name],token)
   token=f.read(f.s['se_doc_original'],5);handle=f.m.read(f.s['object_extents']+token[0]*16);physical=f.m.read(f.s['se_reu_map']+handle)
   for field,index in [('se_reu_logical_owner',handle),('se_reu_physical_owner',physical)]:
    at=f.s[field]+index;old=f.m.read(at);f.m.write(at,0xFE);gate(0x34);f.m.write(at,old)
   checks.append('all15fullsource-tokenbytes +actualforeignlogical/physicalowners')
   for name,width,value,code in [('se_doc_ready',1,0,0x40),('se_h_ready',1,0,0x60),('se_h_fault',1,1,0x65),('se_clip_epoch',2,f.get('se_clip_epoch',2)^1,0x50)]:
    old=f.read(f.s[name],width);f.put(name,value,width);gate(code);f.m.load(f.s[name],old)
   old=f.m.read(f.s['se_gf_state']);f.m.write(f.s['se_gf_state'],0);gate(0xD6,cheap=True);f.m.write(f.s['se_gf_state'],old)
   checks.append('actualdoc/history/fault/clipboardserviceerrors andcoldfontnotready refusal')
   f.command(16);f.render();gate();assert f.get('se_h_cursor',2)<f.get('se_h_end',2)
   f.command(17);f.render();gate();checks.append('actualpendingundo/redo journalandsavepoint-retainedbyadmission')
   # C29 variant accounts for its own trampoline busy byte, never another slot.
   f.m.write(f.s['se_overlay_busy']+1,1);gate(variant=c29);f.m.write(f.s['se_overlay_busy'],1);gate(0xD5,variant=c29,cheap=True);f.m.write(f.s['se_overlay_busy'],0);f.m.write(f.s['se_overlay_busy']+1,0);gate(0xD5,variant=c29,cheap=True)
   checks.append('C29own-Cbusy1valid/Rbusyrefused/missing-own-busyrefused')
   # Modes/proportional preview state are valid geometry, not a request to
   # invoke C16 and reset the saved viewport. No pixels are drawn by this gate.
   for mode,width in [(1,60),(2,80),(3,0)]:
    f.put('se_mode',mode,1);f.put('se_v_columns',width,1);gate()
   f.put('se_r_presentation',1,1);f.put('se_e_ui',4,1);gate();checks.append('all4modewidths+previewaccepted-nohardware/viewport/sourcechanges')
   # Actual current catalog import + C29 trampoline: its own busy1 is supplied
   # by production code, not seeded by the fixture for this integration gate.
   f.m.load(f.s['se_overlay_header'],sealed[:HEADER]);f.m.load(0x5000,sealed[HEADER:]);assert not f.call('se_overlay_import').p&1
   for expected,badjob,badbinding in [(0,False,False),(0xD5,True,False),(0xD8,False,True)]:
    f.put('se_e_job',int(badjob),1);old=f.m.read(0x800)
    if badbinding:f.m.write(0x800,old^1)
    source=f.canonical();reu=f.reu();phase=f.read(0x8D00,1152);r0,used=f.m.call(f.s['se_overlay_call'],a=29,x=1)
    assert r0.a==expected and bool(r0.p&1)==bool(expected) and f.get('se_overlay_busy',2)==0,(r0.a,r0.p)
    assert f.canonical()==source and f.reu()==reu and f.read(0x8D00,1152)==phase
    f.put('se_e_job',0,1);f.m.write(0x800,old);calls.append(dict(error=expected,instructions=used,sealed_C29=True))
   checks.append('actualsealedC29/import/realtrampoline-ownbusy+refusals/sourceandphase/wholeREU')
   # Actual maximum16-bank original AND append allocations: named validators
   # must inspect the final extent too, not just the first source bank.
   # A NEW cold fixture context, not a warm operation: the descriptor at0800
   # intentionally displaced BOOT. Reinstall frozen BOOT before source()
   # invokes its explicit cold factory, then recreate the fresh descriptor.
   f.m.load(0x800,original_boot)
   f.source(editor.native_text('# Large\r')+b'X'*2600,banks=16);assert not f.call('se_clip_init').p&1
   f.put('se_status',1,1);f.m.load(0x800,bytes.fromhex(r['resident_binding']['digest']));gate()
   t=f.read(f.s['se_doc_original'],5);h=f.m.read(f.s['object_extents']+t[0]*16+15);p=f.m.read(f.s['se_reu_map']+h)
   for field,index in [('se_reu_logical_owner',h),('se_reu_physical_owner',p)]:
    at=f.s[field]+index;old=f.m.read(at);f.m.write(at,0xFE);gate(0x34);f.m.write(at,old)
   checks.append('actual16bankoriginal+append/final16thextentlogicalandphysicalownerfaults')
  result=dict(status='passed',scope='actual assembled admission/source component only; no snapshot/restore/fullcapabilitygraph/IRQ/native claim',resident_sha256=r['sha256'],binding=r['resident_binding']['digest'],direct_bytes=len(direct),c29_bytes=len(c29),sealed_payload_bytes=len(sealed)-HEADER,bss=0,zp=0,checks=checks,calls=len(calls),max_instructions=max(x['instructions'] for x in calls),max_direct_instructions=max(x['instructions'] for x in calls if not x.get('sealed_C29')),call_metrics=calls)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=a.out or ROOT/'build/lifecycle-preflight'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);run(out,a.smoke)

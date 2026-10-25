"""Private full resident link of the managed-write verification candidate.

Reads/copies current46 objects, first proves their byteidentity to the immutable
fixture, then replaces only private objects. No Make invocation/shared writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shlex,shutil,subprocess,zipfile
import test_overlay_verification_candidate as memo
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T104351424394Z/fixture'

def command(args,cwd):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True)
 if p.returncode:raise AssertionError(p.stdout+p.stderr)
 return p.stdout

def cold_relocation(private):
 p=private/'src/history/dispatch.s';s=p.read_text();s=memo.replace(s,'se_history_cold:\n','.segment "COLD"\nse_history_cold:\n');s=memo.replace(s,'se_history_call:\n','.segment "CODE"\nse_history_call:\n');p.write_text(s)
 p=private/'src/hot/dispatch.s';s=p.read_text();s=memo.replace(s,'se_hot_cold:\n','.segment "COLD"\nse_hot_cold:\n');s=s.replace('    bcs return\n','    jcs return\n',1).replace('    beq okay\n','    jeq okay\n',1);s=memo.replace(s,'okay:\n','    jmp okay\n.segment "CODE"\nokay:\n');p.write_text(s)
 p=private/'src/editor/startup.s';s=p.read_text();s=memo.replace(s,'    lda sample+$100,x\n    sta $8100,x\n    inx\n    bne @sample','    inx\n    bne @sample\n    ldx #0\n@sample_tail:\n    lda sample+$100,x\n    sta $8100,x\n    inx\n    cpx #<(sample_end-sample)\n    bcc @sample_tail');s=memo.replace(s,'    .res 512-(sample_end-sample),0','');s=memo.replace(s,'.segment "RODATA"\nfailure_title:','.segment "COLD"\nfailure_title:');s=s.replace('Check disk assets and REU capacity.','Check disk and REU.');p.write_text(s)

def run(base,direct=False):
 out=ROOT/'build/overlay-verification-resident'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 private=out/'product';private.mkdir();(private/'cfg').mkdir();shutil.copy2(ROOT/'cfg/standalone.cfg',private/'cfg/standalone.cfg');shutil.copy2(ROOT/'cfg/lifecycle-controller.cfg',private/'cfg/lifecycle-controller.cfg')
 # Explicit list from root's successful46 production link, not a guessed list.
 line=next(x for x in (ROOT/'build/geos-code-production-build.log').read_text().splitlines()if x.startswith('ld65 -C cfg/standalone.cfg '));args=shlex.split(line)
 for name in args:
  if name.endswith('.o'):
   p=private/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
 (out/'copied-object-sha256.json').write_text(json.dumps({n:hashlib.sha256((private/n).read_bytes()).hexdigest()for n in args if n.endswith('.o')},indent=2)+'\n')
 for name in ('bindings.py','check_build.py','module_bindings.py'):
  p=private/'tools'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'tools'/name,p)
 command(args,private);command(['python3','tools/bindings.py','--stem','editor'],private)
 old=(private/'build/editor.prg').read_bytes();expected=(base/'build/editor.prg').read_bytes();assert old==expected,'Current object copy is not the exact released46 resident'
 shutil.copy2(private/'build/editor.prg',out/'before.prg');shutil.copy2(private/'build/editor.map',out/'before.map')
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and n.endswith(('.s','.inc')):
    p=private/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 for name in ('bindings.py','check_build.py','module_bindings.py'):
  p=private/'tools'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'tools'/name,p)
 report=json.loads((base/'build/editor-report.json').read_text());sym=report['symbols'];load=int.from_bytes(old[:2],'little');at=sym['session_defaults']-load+2
 p=private/'build/editor-settings/editor-defaults.bin';p.parent.mkdir(exist_ok=True);p.write_bytes(old[at:at+64])
 memo.candidate(private);cold_relocation(private)
 if direct:
  memo.direct_warm(private)
  # Coldvalidity initialization usesoverlayinit's documentedA0success.
  p=private/'src/editor/startup.s';s=p.read_text();s=memo.replace(s,'    jsr se_overlay_init\n    jcs failed','    jsr se_overlay_init\n    jcs failed\n    sta $CF90\n    sta $CFE8');s=memo.replace(s,'Check disk and REU.','Disk / REU?');p.write_text(s)
  p=private/'src/iec/overlay_read.s';s=p.read_text();s=memo.replace(s,'    lda #<OVL_STAGE','    lda #0\n    sta $CBD5\n    lda #<OVL_STAGE');p.write_text(s)
 modules=[('overlay/cache.s','build/editor/overlay-cache.o',['FAST_EDITOR_CRC=1','EDITOR_HALF_CRC=1','EDITOR_CATALOG_TAIL=1','EDITOR_FIXED_ENTRY=1','OVL_LIMIT=64']),('reu/provider.s','build/editor-memory/provider.o',['SE_EDITOR_COLD_PROVIDER_INIT=1']),('reu/dma.s','build/reu/dma.o',[]),('hot/dispatch.s','build/editor/hot-dispatch.o',['EDITOR_FAST_HOT_FEED=1']),('history/dispatch.s','build/history/dispatch.o',[]),('editor/startup.s','build/editor/startup.o',[])]
 if direct:modules.append(('iec/overlay_read.s','build/iec/overlay_read.o',[]))
 for source,obj,flags in modules:
  cc=['ca65','-g','-I','src','-o',obj,'-l',obj.removesuffix('.o')+'.lst']
  for flag in flags:cc+=['-D',flag]
  cc+=['src/'+source];command(cc,private)
 command(args,private);command(['python3','tools/bindings.py','--stem','editor'],private);checked=command(['python3','tools/check_build.py','--stem','editor'],private);(out/'checker.txt').write_text(checked)
 result=json.loads((private/'build/editor-report.json').read_text());segments={s['name']:s for s in result['segments']};cold=segments['COLD'];rodata=segments['RODATA'];assert cold['end']<0xf00 and rodata['end']<0x3f00
 # New prelude disarms bits restored from a warm snapshot before loading C29.
 p=private/'src/lifecycle/resume.s';s=p.read_text();s=s.replace('.import se_overlay_busy,se_overlay_active,se_overlay_frame,se_overlay_call','.import se_overlay_busy,se_overlay_active,se_overlay_frame,se_overlay_call,se_overlay_unverify');s=memo.replace(s,' jsr se_doc_invalidate',' jsr se_overlay_unverify\n jsr se_doc_invalidate');p.write_text(s)
 import test_lifecycle_editor as lc
 original=lc.ROOT;lc.ROOT=private
 try:images=lc.build(out/'lifecycle',private)
 finally:lc.ROOT=original
 # Exercise the exact whole newly linked resident, not merely the six-module
 # cache capsule. The only loading seam seeds its trusted cold/PRG bytes into
 # each isolated CPU before the unchanged64-slot/provider/DMA oracle runs.
 catalog=memo.catalog;probe=out/'actual-resident-gate';probe.mkdir()
 newprg=(private/'build/editor.prg').read_bytes();(probe/'probe.bin').write_bytes(newprg[2+0x1000-load:])
 catalog.previous.OUT=out/'accelerator';catalog.previous.DLL=catalog.previous.accelerator()
 machine_class=catalog.previous.tail.Machine;old_digest=catalog.previous.DIGEST
 def machine():
  m=machine_class();m.load(load,newprg[2:]);return m
 catalog.previous.tail.Machine=machine;catalog.previous.DIGEST=bytes.fromhex(result['resident_binding']['digest'])
 try:
  safety=catalog.full(probe,result['symbols'])+memo.extra(probe,result['symbols'])
  if direct:
   f=catalog.Fixture(probe,result['symbols'])
   try:
    one=f.image(11,0);two=f.image(12,0);f.imported(one);f.imported(two);f.call('se_overlay_call',11,0);f.call('se_overlay_call',12,0)
    window=bytes((i*37+17)&255 for i in range(4210));f.m.load(0x5000,window);f.m.write(0xcbd5,0x81)
    before=f.get('se_reu_dma_calls',2);f.call('se_overlay_call',11,0)
    assert f.get('se_reu_dma_calls',2)-before==1 and f.read(0x5000,4210)==window and f.m.read(0xcbd5)==0x81
    safety.append('verifiedwarmreload usesoneDMA andpreservesall4210font/windowbytes+stickyvalidtag')
    f.call('se_overlay_call',12,0);handle=f.handles()[0];bank=f.m.read(result['symbols']['se_reu_map']+handle)
    for a,v in [(0xdf02,0),(0xdf03,0x70),(0xdf04,0),(0xdf05,0),(0xdf06,bank),(0xdf07,1),(0xdf08,0),(0xdf09,0),(0xdf0a,0)]:f.m.write(a,v)
    f.m.write(0x7000,one[36]^1);f.m.write(0xdf01,0x90);guard=f.reu()
    f.call('se_overlay_call',11,0,error=0x11)
    assert f.m.read(result['symbols']['se_overlay_active'])==0 and f.read(result['symbols']['se_overlay_busy'],2)==b'\0\0'and f.reu()==guard
    safety.append('unnotifiedbindingcorruption directcopyrefusesexecution andclearsdestinationactive; oldRAMimagepreservationnotclaimedforthisoutofmanagedscopefault')
   finally:f.close()
  f=catalog.Fixture(probe,result['symbols'])
  try:
   image=f.image(11,0);f.imported(image);f.call('se_overlay_call',11,0);snapshot=f.read(result['symbols']['se_overlay_ids'],384)
   f.patch(f.handles()[0],50,image[36+50]^1);f.m.load(result['symbols']['se_overlay_ids'],snapshot)
   assert f.m.read(result['symbols']['image_slot'])&128
   f.m.load(0xa00,images['lifectrl'][36+0x800:36+0x900]);before=f.reu()
   for n,v in [('pc',0xa00),('sp',0x80),('p',0x24)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
   for steps in range(1000):
    if f.m.regs().pc==result['symbols']['se_doc_invalidate']:break
    f.m.lib.zeropage_peddle_step_instruction(f.m.handle)
   else:raise AssertionError('freshprelude didnot reach checkedcleanup')
   assert not any(x&128 for x in f.read(result['symbols']['image_slot'],64))and not any(f.read(result['symbols']['se_overlay_active'],2))and f.m.read(0xcbd5)==0
   assert f.reu()==before and f.read(0xc600,1024)==f.shim
   safety.append('actualnewC29freshprelude clearsresurrectedmemo/active/windowbeforefirstoverlaycall; all16MiB+shimunchanged')
  finally:f.close()
 finally:catalog.previous.tail.Machine=machine_class;catalog.previous.DIGEST=old_digest
 summary=dict(direct_warm=direct,actual_full_resident_safety=safety,status='private-full-link-passed',base=str(base),before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=result['sha256'],binding=result['resident_binding']['digest'],segments={k:segments[k]for k in ('COLD','CODE','CORE','RODATA','CRC_TABLE','ZEROPAGE','BSS')},cold_last=cold['end'],cold_bytes_before_F00=0xeff-cold['end'],core_free_before_crc=0x3eff-rodata['end'],lifecycle_asset_bytes={k:len(v)for k,v in images.items()},recipe=dict(objects=modules,required_other_changes=['Optional feature guards/defaultbytes preservation','C31stageguard image_slot AND1','freshprelude se_overlay_unverify beforefirstcall','allnewbindings/assets rebuild','flagaware hostcatalogselectors']),scope=__doc__)
 (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--direct',action='store_true');a=p.parse_args();run(a.fixture.resolve(),a.direct)

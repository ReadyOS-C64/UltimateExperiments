"""Ready-to-copy guarded managed-code candidate; private outputs only.

Off-mode emitted instructions/relocations are compared through actual full and
capsule links. Serialized ca65 debug file/line metadata is not a code ABI.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,difflib,hashlib,json,re,shlex,shutil,subprocess,sys,zipfile
import test_overlay_verification_candidate as memo
import test_overlay_verification_link as previous
ROOT=Path(__file__).resolve().parents[1]
BASE=previous.BASE
NAMES=('overlay/cache.s','reu/provider.s','reu/dma.s','iec/overlay_read.s','lifecycle/resume.s','history/dispatch.s','hot/dispatch.s','editor/startup.s')
FLAG='EDITOR_MANAGED_CODE'

def conditional(old,new,flag=FLAG):
 if not old:return f'.ifdef {flag}\n'+new+'.endif\n'
 if not new:return f'.ifndef {flag}\n'+old+'.endif\n'
 return f'.ifdef {flag}\n'+new+'.else\n'+old+'.endif\n'

def guard_diff(old,new,flag=FLAG):
 """Only used for directive-balanced provider/DMA changes."""
 a=old.splitlines(True);b=new.splitlines(True);out=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
  out.append(''.join(a[i:j]) if tag=='equal' else conditional(''.join(a[i:j]),''.join(b[k:l]),flag))
 return ''.join(out)

def guarded(root):
 originals={n:(root/'src'/n).read_text()for n in NAMES}
 memo.candidate(root);memo.direct_warm(root)
 transformed={n:(root/'src'/n).read_text()for n in NAMES}
 for n in ('reu/provider.s','reu/dma.s'):(root/'src'/n).write_text(guard_diff(originals[n],transformed[n]))
 a=originals['overlay/cache.s'];b=transformed['overlay/cache.s'];s=a
 # Whole scope replacements avoid changing the meaning of ca65 cheap labels.
 for start,end in [('se_overlay_call:\n','header_from_catalog:\n'),('request_stage:\n','    lda se_overlay_header+8\n    sta crc_remaining')]:
  i=s.index(start);j=s.index(end,i);ni=b.index(start);nj=b.index(end,ni)
  s=s[:i]+conditional(s[i:j],b[ni:nj])+s[j:]
 s=memo.replace(s,'.export se_overlay_init, se_overlay_import, se_overlay_call\n','.export se_overlay_init, se_overlay_import, se_overlay_call\n'+conditional('', '''; Managed backing is valid only under checked-write/provider notifications.
; Generic arbitrary-entry/strict-cache clients must leave this feature undefined.
.assert EDITOR_MANAGED_CODE=1,error,"managed-code flag must be1"
.if (EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY) = 0
.fatal "managed code requires editor fixed catalog"
.endif
.export se_overlay_unverify,se_overlay_managed_verification
se_overlay_managed_verification=1
'''))
 i=b.index('se_overlay_unverify:\n');j=b.index('asset_valid:\n',i)
 s=memo.replace(s,'asset_valid:\n',conditional('',b[i:j])+'asset_valid:\n')
 # Only import's slot load/store remains outside the guarded call function.
 s=memo.replace(s,'    lda image_slot,x\n    cmp se_overlay_header+5','    lda image_slot,x\n'+conditional('','    and #1\n')+'    cmp se_overlay_header+5')
 s=memo.replace(s,'    lda se_overlay_header+5\n    sta image_slot,x','    lda se_overlay_header+5\n'+conditional('','    ora #$80\n')+'    sta image_slot,x')
 (root/'src/overlay/cache.s').write_text(s)
 n='iec/overlay_read.s';s=originals[n];s=memo.replace(s,'    lda #<OVL_STAGE',conditional('','    lda #0\n    sta $CBD5 ;invalidate before first payload write, including partial reads\n')+'    lda #<OVL_STAGE');(root/'src'/n).write_text(s)
 n='lifecycle/resume.s';s=originals[n];s=memo.replace(s,'.import se_overlay_busy,se_overlay_active,se_overlay_frame,se_overlay_call\n','.import se_overlay_busy,se_overlay_active,se_overlay_frame,se_overlay_call\n'+conditional('','.import se_overlay_unverify\n'));s=memo.replace(s,' jsr se_doc_invalidate',conditional('',' jsr se_overlay_unverify ;disarm restored catalog before any execution\n')+' jsr se_doc_invalidate');(root/'src'/n).write_text(s)
 n='history/dispatch.s';s=originals[n];s=memo.replace(s,'se_history_cold:\n',conditional('','.segment "COLD"\n','EDITOR_COLD_DISPATCH')+'se_history_cold:\n');s=memo.replace(s,'se_history_call:\n',conditional('','.segment "CODE"\n','EDITOR_COLD_DISPATCH')+'se_history_call:\n');(root/'src'/n).write_text(s)
 n='hot/dispatch.s';s=originals[n];s=memo.replace(s,'se_hot_cold:\n',conditional('','.segment "COLD"\n','EDITOR_COLD_DISPATCH')+'se_hot_cold:\n');s=s.replace('    bcs return\n',conditional('    bcs return\n','    jcs return\n','EDITOR_COLD_DISPATCH'),1).replace('    beq okay\n',conditional('    beq okay\n','    jeq okay\n','EDITOR_COLD_DISPATCH'),1);s=memo.replace(s,'okay:\n',conditional('','    jmp okay\n.segment "CODE"\n','EDITOR_COLD_DISPATCH')+'okay:\n');(root/'src'/n).write_text(s)
 n='editor/startup.s';s=originals[n]
 s=memo.replace(s,'    jsr se_overlay_init\n    jcs failed','    jsr se_overlay_init\n    jcs failed\n'+conditional('','    sta $CF90 ;overlay_init success returnsA0\n    sta $CFE8\n'))
 old='    lda sample+$100,x\n    sta $8100,x\n    inx\n    bne @sample\n';new='    inx\n    bne @sample\n    ldx #0\n@sample_tail:\n    lda sample+$100,x\n    sta $8100,x\n    inx\n    cpx #<(sample_end-sample)\n    bcc @sample_tail\n';s=memo.replace(s,old,conditional(old,new))
 s=memo.replace(s,'.segment "RODATA"\nfailure_title:',conditional('.segment "RODATA"\n','.segment "COLD"\n')+'failure_title:')
 s=memo.replace(s,'failure_hint: .asciiz "Check disk and REU."\n',conditional('failure_hint: .asciiz "Check disk and REU."\n','failure_hint: .asciiz "Disk / REU?"\n'))
 s=memo.replace(s,'    .res 512-(sample_end-sample),0',conditional('    .res 512-(sample_end-sample),0\n','.assert (sample_end-sample)>256,error,"bounded sample copy requires a second page"\n.assert (sample_end-sample)<512,error,"bounded sample copy exceeds two pages"\n').rstrip('\n'))
 (root/'src'/n).write_text(s)
 # Future merges must fail rather than silently apply against other sources.
 return {n:hashlib.sha256(originals[n].encode()).hexdigest()for n in NAMES}

def command(args,cwd):return previous.command(args,cwd)

def object_contract(path):
 # ca65's debug file/line tables necessarily reflect the inserted guards. Compare
 # actual object import/export/segment contracts, then link the relocations.
 dump=subprocess.run(['od65','--dump-segments','--dump-imports','--dump-exports',str(path)],capture_output=True,text=True,check=True).stdout
 return '\n'.join(dump.splitlines()[1:])


def compile_modules(private,managed=False,cold=False):
 modules=[('overlay/cache.s','build/editor/overlay-cache.o',['FAST_EDITOR_CRC=1','EDITOR_HALF_CRC=1','EDITOR_CATALOG_TAIL=1','EDITOR_FIXED_ENTRY=1','OVL_LIMIT=64']),('reu/provider.s','build/editor-memory/provider.o',['SE_EDITOR_COLD_PROVIDER_INIT=1']),('reu/dma.s','build/reu/dma.o',[]),('hot/dispatch.s','build/editor/hot-dispatch.o',['EDITOR_FAST_HOT_FEED=1']),('history/dispatch.s','build/history/dispatch.o',[]),('editor/startup.s','build/editor/startup.o',[]),('iec/overlay_read.s','build/iec/overlay_read.o',[])]
 for source,obj,flags in modules:
  cc=['ca65','-g','-I','src','-o',obj,'-l',obj.removesuffix('.o')+'.lst']
  for f in flags+([FLAG+'=1']if managed else [])+(['EDITOR_COLD_DISPATCH=1']if cold and source in ('hot/dispatch.s','history/dispatch.s')else []):cc+=['-D',f]
  command(cc+['src/'+source],private)
 return modules

def lifecycle(out,private,managed):
 import test_lifecycle_editor as lc
 original=lc.ROOT;oldcmd=lc.command;lc.ROOT=private
 def cmd(*args):
  args=list(args)
  if managed and args[0]=='ca65':args[1:1]=['-D',FLAG+'=1']
  return oldcmd(*args)
 lc.command=cmd
 try:return lc.build(out,private)
 finally:lc.ROOT=original;lc.command=oldcmd

def header_checks(out,s):
 from overlays import wrap,HEADER
 m=memo.catalog.previous.tail.Machine();m.load(0x1000,(out/'probe.bin').read_bytes());count=0
 try:
  for length in [17,18,255,256,257,4095,4096]:
   for entry in [0,15,16,17,255,256,4080,4095,4096,65535]:
    image=bytearray(wrap(bytes(range(16))+bytes(4080),0,91,16,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes(range(16))))
    image[8:10]=length.to_bytes(2,'little');image[10:12]=entry.to_bytes(2,'little');image=memo.catalog.previous.reseal(image)
    m.load(s['se_overlay_header'],image[:HEADER]);r,_=m.call(s['se_overlay_validate'])
    good=16<=entry<length
    assert bool(r.p&1)!=good and(good or r.a==0x13),(length,entry,r.a,r.p)
    count+=1
  return count
 finally:m.close()

def generic_checks(out,original,private):
 cat=memo.catalog;oldroot=cat.ROOT;oldcommand=cat.command
 cases=[]
 try:
  for label,kw in [('generic-bitcrc',dict(fast=False)),('generic-fast',dict()),('tail24',dict(tail=True,capacity=24)),('fixed64-strict',dict(tail=True,fixed=True,capacity=64))]:
   cat.ROOT=original;before=cat.build(out/(label+'-before'),**kw)
   cat.ROOT=private;after=cat.build(out/(label+'-after'),**kw)
   a=(out/(label+'-before')/'probe.bin').read_bytes();b=(out/(label+'-after')/'probe.bin').read_bytes()
   assert a==b,(label,'disabled code changed')
   assert before==after,(label,'disabled symbol/segment change')
   contracts=[]
   for index in range(6):
    left=object_contract(out/(label+'-before')/(str(index)+'.o'));right=object_contract(out/(label+'-after')/(str(index)+'.o'))
    assert left==right,(label,index,'disabled object interface changed')
    contracts.append(hashlib.sha256(right.encode()).hexdigest())
   assert 'se_overlay_managed_verification'not in after and 'se_overlay_unverify'not in after
   memo.catalog.previous.OUT=out/'accelerator';memo.catalog.previous.DLL=memo.catalog.previous.accelerator()
   checked=header_checks(out/(label+'-after'),after) if not kw.get('fixed',False) else 0
   if label=='tail24':assert memo.catalog.previous.generic(out/(label+'-after'),after)==70
   cases.append(dict(profile=label,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),code=after['__CODE_SIZE__'],object_contract_sha256=contracts,actual_arbitrary_entry_header_checks=checked))
  # Managed flag is explicit and cannot be enabled on an arbitrary-entry cache.
  cat.ROOT=private
  def enabled(*args):
   args=list(args)
   if args[0]=='ca65':args[1:1]=['-D',FLAG+'=1']
   proc=subprocess.run(list(map(str,args)),cwd=private,capture_output=True,text=True)
   if proc.returncode:raise subprocess.CalledProcessError(proc.returncode,args,proc.stdout,proc.stderr)
  cat.command=enabled
  try:cat.build(out/'invalid-generic-managed',fast=False)
  except subprocess.CalledProcessError as exc:
   assert 'managed code requires editor fixed catalog'in exc.stderr
   (out/'invalid-config.txt').write_text(exc.stderr)
  else:raise AssertionError('managed arbitrary-entry cache was accepted')
 finally:cat.ROOT=oldroot;cat.command=oldcommand
 return cases

def run(base):
 direct=True
 out=ROOT/'build/overlay-managed-guarded'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
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
 original=out/'original';original.mkdir();shutil.copytree(private/'src',original/'src')
 source_hashes=guarded(private)
 # Original copied objects and independently assembled guard-disabled objects.
 resident_objects=['build/editor/overlay-cache.o','build/editor-memory/provider.o','build/reu/dma.o','build/editor/hot-dispatch.o','build/history/dispatch.o','build/editor/startup.o','build/iec/overlay_read.o']
 before_contracts={n:object_contract(private/n)for n in resident_objects}
 generic=generic_checks(out/'generic',original,private)
 compile_modules(private)
 for n in resident_objects:assert object_contract(private/n)==before_contracts[n],('disabled resident object interface changed',n)
 command(args,private);command(['python3','tools/bindings.py','--stem','editor'],private)
 command(['python3','tools/check_build.py','--stem','editor'],private)
 assert (private/'build/editor.prg').read_bytes()==old,'Disabled flags changed the actual complete resident'
 disabled=lifecycle(out/'lifecycle-disabled',private,False)
 for name,image in disabled.items():
  assert image==(base/'build/overlays'/(name+'.seo')).read_bytes(),('disabled lifecycle asset changed',name)
 modules=compile_modules(private,managed=True,cold=True)
 command(args,private);command(['python3','tools/bindings.py','--stem','editor'],private);checked=command(['python3','tools/check_build.py','--stem','editor'],private);(out/'checker.txt').write_text(checked)
 result=json.loads((private/'build/editor-report.json').read_text());segments={s['name']:s for s in result['segments']};cold=segments['COLD'];rodata=segments['RODATA'];assert cold['end']<0xf00 and rodata['end']<0x3f00
 images=lifecycle(out/'lifecycle',private,True)
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
  safety=catalog.full(probe,result['symbols'])+catalog.exhausted(probe,result['symbols'])+memo.extra(probe,result['symbols'])
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
 summary=dict(direct_warm=direct,actual_full_resident_safety=safety,status='guarded-private-full-link-passed',base=str(base),before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=result['sha256'],binding=result['resident_binding']['digest'],segments={k:segments[k]for k in ('COLD','CODE','CORE','RODATA','CRC_TABLE','ZEROPAGE','BSS')},cold_last=cold['end'],cold_bytes_before_F00=0xeff-cold['end'],core_free_before_crc=0x3eff-rodata['end'],lifecycle_asset_bytes={k:len(v)for k,v in images.items()},generic_disabled=generic,disabled_resident_sha256=hashlib.sha256(old).hexdigest(),source_baseline_sha256=source_hashes,managed_constant=result['symbols']['se_overlay_managed_verification'],recipe=dict(objects=modules,flags=dict(managed=FLAG+'=1',cold='EDITOR_COLD_DISPATCH=1'),required_other_changes=['R31stageguard image_slot AND1','allnewbindings/assets rebuild','flagaware hostcatalogselectors','parent preview-only GF_LOADS comparison removal']),scope=__doc__)
 # Save a reviewable exact guarded promotion diff and all source identities.
 diff=[]
 for name in NAMES:
  diff.extend(difflib.unified_diff((original/'src'/name).read_text().splitlines(True),(private/'src'/name).read_text().splitlines(True),fromfile='a/src/'+name,tofile='b/src/'+name))
 (out/'guarded-promotion.diff').write_text(''.join(diff))
 (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();run(a.fixture.resolve())

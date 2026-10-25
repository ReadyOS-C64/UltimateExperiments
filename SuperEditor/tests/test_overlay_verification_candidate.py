"""Private sizing/CPU experiment for managed-write overlay verification reuse.

Never edits production. Copies actual cache/provider/DMA, applies a candidate
in private sources, and keeps strict generic/source behavior untouched. Memoized
mode assumes no unnotified hardware/host REU corruption; checked owner2 writes
and ownership rebinding disarm it. Fresh lifecycle restore needs the separately
specified explicit invalidator call before execution (not integrated here).
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,zipfile,re
import test_overlay_catalog64 as catalog
ROOT=Path(__file__).resolve().parents[1]

def replace(text,old,new,count=1):
 assert text.count(old)==count,(old[:70],text.count(old),count)
 return text.replace(old,new)

def candidate(root):
 cache=root/'src/overlay/cache.s';s=cache.read_text()
 s=replace(s,'.export se_overlay_init, se_overlay_import, se_overlay_call','.export se_overlay_init, se_overlay_import, se_overlay_call, se_overlay_unverify')
 s=replace(s,'    lda image_slot,x\n    cmp ', '    lda image_slot,x\n    and #1\n    cmp ',2)
 s=replace(s,'    lda se_overlay_header+5\n    sta image_slot,x','    lda se_overlay_header+5\n    ora #$80\n    sta image_slot,x')
 # Keep unconditional strict import CRC. Only the runtime miss gets a memo arm.
 at=s.index('    ; Fetch to stage and verify before touching the previous executable slot.')
 end=s.index('    jsr request_stage\n    lda call_slot',at)
 part=s[at:end]
 part=part.replace('    bcs @return','    jcs @return')
 part=replace(part,'    jsr crc_stage','    ldx candidate\n    lda image_slot,x\n    bmi @memo\n    jsr crc_stage\n    jmp @verified_result\n@memo:\n    jsr binding_stage\n@verified_result:')
 part+='    ldx candidate\n    lda image_slot,x\n    ora #$80\n    sta image_slot,x\n'
 s=s[:at]+part+s[end:]
 # Binding is checked also on an already active RAM slot, before busy/stack or
 # executable changes. Existing fixed-entry setup becomes prefix-pointer setup.
 old='''@execute:
    ldx call_slot
    lda #1
    sta se_overlay_busy,x
    txa
    pha ; slot survives child calls and all overlay register clobbers
.if EDITOR_FIXED_ENTRY
    ; Every imported editor image was validated to enter just after its binding.
    ; No per-image executable pointer survives in the warm catalog.
    lda #OVL_BINDING_BYTES
    sta ovl_ptr
    ldx call_slot
    lda slot_high,x
    sta ovl_ptr+1
.else'''
 new='''@execute:
.if EDITOR_FIXED_ENTRY
    lda #0
    sta ovl_ptr
    ldx call_slot
    lda slot_high,x
    sta ovl_ptr+1
    jsr binding_at_pointer
    jcs @return
    lda #OVL_BINDING_BYTES
    sta ovl_ptr
.else'''
 s=replace(s,old,new)
 old='''.endif
    inc se_overlay_calls'''
 new='''.endif
    ldx call_slot
    lda #1
    sta se_overlay_busy,x
    txa
    pha ;slot survives all child operations
    inc se_overlay_calls'''
 s=replace(s,old,new)
 start=s.index('crc_stage:\n');end=s.index('    lda se_overlay_header+8\n    sta crc_remaining',start)
 s=s[:start]+'''binding_stage:
    lda #<OVL_STAGE
    sta ovl_ptr
    lda #>OVL_STAGE
    sta ovl_ptr+1
binding_at_pointer:
    ldy #OVL_BINDING_BYTES-1
@binding:
    lda (ovl_ptr),y
    cmp se_overlay_binding_digest,y
    bne @abi
    dey
    bpl @binding
    clc
    rts
@abi:
    lda #$11
    sec
    rts
crc_stage:
    jsr binding_stage
    bcc :+
    rts
:
'''+s[end:]
 # Preserve X/Y for provider bind/free; A/P are existing clobbers.
 s=replace(s,'asset_valid:\n','''se_overlay_unverify:
    txa
    pha
    ldx #OVL_LIMIT-1
@clear:
    lda image_slot,x
    and #1
    sta image_slot,x
    dex
    bpl @clear
    lda #0
    sta se_overlay_active
    sta se_overlay_active+1
    sta $CBD5 ;sharedfont/executable5000windowwitness
    pla
    tax
    rts
asset_valid:
''')
 cache.write_text(s)
 dma=root/'src/reu/dma.s';s=dma.read_text();s=replace(s,'.import se_reu_map, se_reu_logical_owner, se_reu_physical_owner','.import se_reu_map, se_reu_logical_owner, se_reu_physical_owner\n.import se_overlay_unverify')
 s=replace(s,'    sty dma_physical\n    php','''    sty dma_physical
    cmp #2
    bne :+
    ldy dma_direction
    bne :+
    jsr se_overlay_unverify
:
    php''');s=s.replace('    beq @handle','    jeq @handle')
 dma.write_text(s)
 provider=root/'src/reu/provider.s';s=provider.read_text();s=replace(s,'.import se_reu_banks','.import se_reu_banks\n.import se_overlay_unverify')
 s=replace(s,'    lda provider_owner\n    sta se_reu_logical_owner,x','''    lda provider_owner
    cmp #2
    bne :+
    jsr se_overlay_unverify
    lda provider_owner
:
    sta se_reu_logical_owner,x''')
 s=replace(s,'    cmp se_reu_physical_owner,y\n    bne provider_bad\n    lda #0','''    cmp se_reu_physical_owner,y
    bne provider_bad
    cmp #2
    bne :+
    jsr se_overlay_unverify
:
    lda #0''');s=s.replace('    bcc provider_bad','    jcc provider_bad',1).replace('    beq provider_bad','    jeq provider_bad',1)
 provider.write_text(s)

def direct_warm(root):
 p=root/'src/overlay/cache.s';text=p.read_text();start=text.index('    ; Fetch to stage and verify before touching the previous executable slot.');end=text.index('@execute:',start)
 text=text[:start]+'''    ; Managedverified backing may copydirectly; unverified keepsstaging+CRC.
    jsr header_from_catalog
    ldx candidate
    lda image_slot,x
    bmi @copy_slot
    jsr request_stage
    lda #1
    jsr se_reu_copy
    jcs @return
    jsr crc_stage
    jcs @return
    ldx candidate
    lda image_slot,x
    ora #$80
    sta image_slot,x
@copy_slot:
    jsr request_slot
    lda #1
    jsr se_reu_copy
    jcs @return
    ; SuccessfulDMAchangedthe destination; rejectanybadbindingwithnoactiveclaim.
    ldx call_slot
    lda #0
    sta se_overlay_active,x
    inc se_overlay_loads
    bne @execute
    inc se_overlay_loads+1
    jmp @execute
@hit:
    inc se_overlay_hits
    bne @execute
    inc se_overlay_hits+1
'''+text[end:]
 # Publishonlyaftertheactualdestinationbindingcheck. Repeatidempotentlyonhits.
 text=replace(text,'    lda #OVL_BINDING_BYTES\n    sta ovl_ptr\n.else','    lda #OVL_BINDING_BYTES\n    sta ovl_ptr\n    lda candidate\n    clc\n    adc #1\n    sta se_overlay_active,x\n.else')
 start=text.index('request_stage:\n');end=text.index('binding_stage:\n',start)
 text=text[:start]+'''request_stage:
    lda #0
    sta $CBD5
    lda #>OVL_STAGE
    bne request_common
request_slot:
    lda call_slot
    clc
    adc #$0A
    asl
    asl
    asl
    asl
request_common:
    sta se_reu_c64+1
    jsr asset_index
    lda se_overlay_asset,x
    sta se_reu_logical
    lda #0
    sta se_reu_c64
    sta se_reu_offset
    lda candidate
    asl
    asl
    asl
    asl
    sta se_reu_offset+1
    lda se_overlay_header+8
    sta se_reu_length
    lda se_overlay_header+9
    sta se_reu_length+1
    rts
'''+text[end:];p.write_text(text)

def extra(out,s):
 f=catalog.Fixture(out,s);cases=[]
 try:
  one=f.image(11,0);two=f.image(12,0);f.imported(one);f.imported(two)
  f.call('se_overlay_call',11,0);assert f.m.read(s['image_slot'])&128
  handle=f.handles()[0];bank=f.m.read(s['se_reu_map']+handle)
  # Corrupt via actual checked owner2 DMA while this exact image remains active.
  f.m.write(0xCBD5,41) #explicit executablewindow-witness seam
  f.patch(handle,50,one[36+50]^1)
  assert f.m.read(0xCBD5)==0
  assert not any(f.read(s['se_overlay_active'],2))and not any(x&128 for x in f.read(s['image_slot'],64))
  f.call('se_overlay_call',11,0,error=0x14);f.patch(handle,50,one[36+50]);f.call('se_overlay_call',11,0)
  cases.append('checkedowner2write disarms sameactivehit andall64memo bits; nextadmission strictCRC')
  # A legal free/rebind with identical owner and epoch must not inherit trust.
  f.call('se_reu_free',x=handle)
  assert not any(f.read(s['se_overlay_active'],2))and not any(x&128 for x in f.read(s['image_slot'],64))
  f.call('se_reu_bind',2,handle,bank);f.call('se_overlay_call',11,0)
  cases.append('checkedowner2free/rebind sameepoch clearsmemo/active andforcesrevalidation')
  # Binding is checked even if no reload was needed.
  f.m.write(0xA000,one[36]^1);f.call('se_overlay_call',11,0,error=0x11);f.m.write(0xA000,one[36]);f.call('se_overlay_call',11,0)
  cases.append('activeRAMhit checksresident-binding beforebusy/execute')
  # A warm snapshot can resurrect stale memo bits despite a checked mutation.
  snapshot=f.read(s['se_overlay_ids'],384);f.patch(handle,50,one[36+50]^1)
  f.m.load(s['se_overlay_ids'],snapshot);assert f.call('se_overlay_call',11,0)==11
  f.call('se_overlay_unverify');f.call('se_overlay_call',11,0,error=0x14);f.patch(handle,50,one[36+50]);f.call('se_overlay_call',11,0)
  cases.append('explicitsnapshotresurrection demonstratesmandatorypostrestoreunverify beforefirstexecution')
  # Demonstrate the narrower fault contract explicitly, without weakening a
  # strict test: an unnotified raw REU bitflip is invisible to the memo bit.
  f.call('se_overlay_call',12,0);offset=50
  assert f.m.read(s['image_slot'])&128
  for a,v in [(0xdf02,0),(0xdf03,0x70),(0xdf04,offset),(0xdf05,0),(0xdf06,bank),(0xdf07,1),(0xdf08,0),(0xdf09,0),(0xdf0a,0)]:f.m.write(a,v)
  f.m.write(0x7000,one[36+offset]^1);f.m.write(0xdf01,0x90)
  assert f.call('se_overlay_call',11,0)==11 #explicit unnotifiedfault isoutsidecertification
  f.call('se_overlay_unverify');f.call('se_overlay_call',11,0,error=0x14)
  f.patch(handle,offset,one[36+offset]);f.call('se_overlay_call',11,0)
  cases.append('rawhardware/hostmutation isnot certified bymanagedwrite memoization; strictdefaultrequiredforthatfaultmodel')
  return cases
 finally:f.close()

def profile(out,s):
 f=catalog.Fixture(out,s)
 try:
  f.imported(f.image(11,0));f.imported(f.image(12,0));results={}
  def measure(label):
   r=f.m.regs();before=(r.instructions,r.cycles,f.get('se_reu_dma_calls',2));f.call('se_overlay_call',11,0);r=f.m.regs()
   results[label]=dict(instructions=r.instructions-before[0],CPU_cycles_excluding_REU_stall=(r.cycles-before[1])or None,DMA_calls=f.get('se_reu_dma_calls',2)-before[2])
  measure('firstload');f.call('se_overlay_call',12,0);measure('reload');measure('activehit');return results
 finally:f.close()

def cold_fit(out):
 base=ROOT/'build/geos-preview-cache-product/20261025T101910272004Z/fixture'
 workspace=out/'cold-fit';workspace.mkdir();report=json.loads((base/'build/editor-report.json').read_text());symbols=report['symbols']
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and name.endswith(('.s','.inc')):
    p=workspace/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 defaults=workspace/'build/editor-settings/editor-defaults.bin';defaults.parent.mkdir(parents=True)
 prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');at=symbols['session_defaults']-load+2;defaults.write_bytes(prg[at:at+64])
 def segments(p):
  text=subprocess.run(['od65','--dump-segments',str(p)],capture_output=True,text=True,check=True).stdout
  return{n:int(size)for n,size in re.findall(r'Name:\s+"(\w+)".*?Size:\s+(\d+)',text,re.S)}
 result={}
 for tag,name in [('history','history/dispatch.s'),('hot','hot/dispatch.s'),('startup','editor/startup.s')]:
  text=(workspace/'src'/name).read_text();before=workspace/(tag+'-before.s');before.write_text(text)
  if tag=='history':text=text.replace('se_history_cold:\n','.segment "COLD"\nse_history_cold:\n').replace('se_history_call:\n','.segment "CODE"\nse_history_call:\n')
  elif tag=='hot':text=text.replace('se_hot_cold:\n','.segment "COLD"\nse_hot_cold:\n').replace('    bcs return\n','    jcs return\n',1).replace('    beq okay\n','    jeq okay\n',1).replace('okay:\n','    jmp okay\n.segment "CODE"\nokay:\n',1)
  else:
   text=replace(text,'    lda sample+$100,x\n    sta $8100,x\n    inx\n    bne @sample','    inx\n    bne @sample\n    ldx #0\n@tail:\n    lda sample+$100,x\n    sta $8100,x\n    inx\n    cpx #<(sample_end-sample)\n    bcc @tail')
   text=replace(text,'    .res 512-(sample_end-sample),0','')
   text=replace(text,'.segment "RODATA"\nfailure_title:','.segment "COLD"\nfailure_title:') # all46bytes before existing COLD section
   text=replace(text,'failure_hint: .asciiz "Check disk assets and REU capacity."','failure_hint: .asciiz "Check disk and REU."')
  after=workspace/(tag+'-after.s');after.write_text(text);values=[]
  for p in [before,after]:
   command=['ca65','-g','-I',workspace/'src','-o',p.with_suffix('.o'),p]
   if tag=='hot':command[1:1]=['-D','EDITOR_FAST_HOT_FEED=1']
   subprocess.run(list(map(str,command)),cwd=workspace,check=True);values.append(segments(p.with_suffix('.o')))
  result[tag]=dict(before=values[0],after=values[1],delta={k:values[1].get(k,0)-values[0].get(k,0)for k in set(values[0])|set(values[1])})
 cold=next(x for x in report['segments']if x['name']=='COLD');delta=sum(v['delta'].get('COLD',0)for v in result.values());core=sum(v['delta'].get('CODE',0)+v['delta'].get('RODATA',0)for v in result.values())
 return dict(objects=result,baseline_cold=cold,cold_delta=delta,projected_cold_end=cold['end']+delta,projected_with14Bfuture_names=cold['end']+delta+14,resident_reclaim=-core,scope='Private exact object-size proof from frozen101910 source. No production relink; hypothetical2newassets contribute14COLDbytes. Currentroot46coregap mustbe substituted separately.')

def main():
 out=ROOT/'build/overlay-verification-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 private=out/'candidate';(private/'src').mkdir(parents=True)
 for name in ['overlay/cache.s','overlay/format.inc','overlay/header.s','overlay/crc_fast.s','reu/provider.s','reu/dma.s']:
  p=private/'src'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'src'/name,p)
 before=catalog.build(out/'before',fixed=True,tail=True,capacity=64)
 candidate(private)
 original=catalog.ROOT;catalog.ROOT=private
 try:after=catalog.build(out/'after',fixed=True,tail=True,capacity=64)
 finally:catalog.ROOT=original
 catalog.previous.OUT=out/'accelerator'
 catalog.previous.DLL=catalog.previous.accelerator()
 cases=catalog.full(out/'after',after)+catalog.exhausted(out/'after',after)+extra(out/'after',after)
 # Object-level CODE and RODATA deltas, not a speculative resident fit claim.
 def segments(path):
  v=subprocess.run(['od65','--dump-segments',str(path)],capture_output=True,text=True,check=True).stdout
  import re
  return{n:int(size)for n,size in re.findall(r'Name:\s+"(\w+)".*?Size:\s+(\d+)',v,re.S)}
 deltas=[]
 for i,name in enumerate(['cache','header','provider','dma','crc','stub']):
  a=segments(out/'before'/f'{i}.o');b=segments(out/'after'/f'{i}.o');deltas.append(dict(module=name,before=a,after=b,code_delta=b.get('CODE',0)-a.get('CODE',0)))
 cold=cold_fit(out)
 result=dict(profiles=dict(before=profile(out/'before',before),candidate=profile(out/'after',after)),cold_fit=cold,status='passed-private-candidate',code_delta=after['__CODE_SIZE__']-before['__CODE_SIZE__'],BSS_delta=after['__BSS_SIZE__']-before['__BSS_SIZE__'],deltas=deltas,cases=cases,source_sha256={n:hashlib.sha256((ROOT/'src'/n).read_bytes()).hexdigest()for n in ['overlay/cache.s','reu/dma.s','reu/provider.s']},scope=__doc__)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()

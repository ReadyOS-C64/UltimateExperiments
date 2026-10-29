"""Focused warm/hit/corruption/FE/DMA fault gate for completeprivateR23cache."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,importlib.util
import test_geos_preview_glyph_cache as core
old=core.old;ROOT=core.ROOT

def run(out,base=core.BASE,build_script="build-cache.py"):
 frozen,identity=old.geos.freeze(out,base);old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names'];core.build_control(out/'control',frozen)
 spec=importlib.util.spec_from_file_location('cachebuild',core.D/build_script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);budget=m.build(out/'candidate',frozen)
 for ext in('bin','lbl'):shutil.copy2(out/'candidate'/('cache.'+ext),out/'candidate'/('r23.'+ext))
 dll=old.geos.grid.runner(out);a=core.Fixture(out,frozen,dll,out/'control');b=core.Fixture(out,frozen,dll,out/'candidate');pack=(out/'control/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)];e=next(x for x in entries if x[:4]==bytes((2,255,255,9)));off=int.from_bytes(e[8:11],'little');raw=pack[off:off+744];fallback=(frozen/'fonts/native8.bin').read_bytes();faults=[];cases=0;sumcontrol=sumcold=sumwarm=0
 try:
  h=b.get('se_gc_handle',1);ph=b.m.read(b.s['se_reu_map']+h);lo=ph*65536+0xeb69;hi=lo+4160;original=b.reu()
  def check(value,style,inverse,repeat=True):
   nonlocal cases,sumcontrol,sumcold,sumwarm
   ar,af,na=a.glyph(e,value,style,inverse);br,bf,nb=b.glyph(e,value,style,inverse);met,ink,cov=old.oracle(raw,fallback,value,0,style,inverse,(0,32,0,24));assert not(ar.p&1 or br.p&1)and af[:20]==bf[:20]and bf[14:20]==met and bf[20:56]==af[20:56]==ink[:36]
   assert bf[56:212]==b.last_before[0x8838:0x88d4]
   if repeat:
    cr,cf,nc=b.glyph(e,value,style,inverse);assert not cr.p&1 and cf[:20]==bf[:20]and cf[20:56]==bf[20:56];sumwarm+=nc
   cases+=1;sumcontrol+=na;sumcold+=nb
   return nb
  for value in range(256):
   for style in range(8):
    for inverse in range(2):check(value,style,inverse)
  key_totals=(sumcontrol,sumcold,sumwarm)
  print('KEYS',cases,'warm',sumwarm,'cold',sumcold,'control',sumcontrol,flush=True)
  def patch(offset,data):
   b.m.load(0x8080,data);b.put('se_reu_logical',h,1);b.put('se_reu_offset',offset,2);b.put('se_reu_length',len(data),2);b.put('se_reu_c64',0x8080,2);assert not b.call('se_reu_copy',0).p&1
  value=65;check(value,3,1);index=((b.m.read(0x880f)^(3<<4))&127)if build_script in ("build-stylehash.py","build-once.py")else(b.m.read(0x880f)&127)if build_script in ("build-screen.py","build-premeasure.py")else value&127;offset=0xeb69+64+index*32
  for at in range(32):
   for bit in range(8):
    check(value,3,1);current=b.reu()[ph*65536+offset:ph*65536+offset+32];patch(offset+at,bytes([current[at]^(1<<bit)]));used=check(value,3,1,False);assert used>3000;faults.append(dict(kind='record-bit',byte=at,bit=bit))
  for at in range(64):
   check(value,3,1);header=b.reu()[lo:lo+64];patch(0xeb69+at,bytes([header[at]^1]));used=check(value,3,1,False);assert used>10000;faults.append(dict(kind='header-byte',byte=at))
  for field,index,newvalue in [('se_gc_handle',0,0),('se_gc_epoch',0,None),('se_reu_logical_owner',h,77),('se_reu_physical_owner',ph,77),('se_reu_map',h,0)]:
   check(value,3,1);at=b.s[field]+index;oldvalue=b.m.read(at);b.m.write(at,(oldvalue^1)if newvalue is None else newvalue);before=b.reu();check(value,3,1,False);assert b.reu()==before,(field,'optionalcachefaultwroteREU');b.m.write(at,oldvalue);faults.append(dict(kind='FE-optional-miss',field=field))
  # Deliberately injected service failures, never presented as hardwarefaults.
  # Existing immutablefontwindow is valid, so realdecoder doesnotneedDMA.
  target=b.s['se_reu_copy'];oldentry=b.read(target,7);assert oldentry[:4]==bytes((0xc9,2,0x90,3))and oldentry[4]==0x4c
  for tag,init,write_only in [('read-error',False,False),('init-write-error',True,True),('put-write-error',False,True)]:
   check(value,3,1)
   if init:header=b.reu()[lo:lo+64];patch(0xeb69,bytes([header[0]^1]))
   if not init and write_only:
    record=b.reu()[ph*65536+offset:ph*65536+offset+32];patch(offset,bytes([record[0]^1]))
   before=b.reu()
   if write_only:
    hook=bytes((0xc9,0,0xf0,3,0x4c,(target+7)&255,(target+7)>>8,0xa9,2,0x38,0x60));b.m.load(0x8080,hook);b.m.load(target,bytes((0x4c,0x80,0x80)))
   else:b.m.load(target,bytes((0xa9,2,0x38,0x60)))
   try:check(value,3,1,False);assert b.reu()==before,(tag,'failuremutation')
   finally:b.m.load(target,oldentry)
   faults.append(dict(kind='injected-DMA-failure',phase=tag))
  now=b.reu();assert now[:lo]==original[:lo]and now[hi:]==original[hi:],'foreign16MiB'
  result=dict(status='passed',budget=budget,cases=cases,keys=4096,control_instructions=key_totals[0],cold_instructions=key_totals[1],warm_instructions=key_totals[2],warm_mean_perkey=key_totals[2]/4096,faults=faults,FEextent=[0xeb69,0xfba9],scope='RealFD+FE/CPlinkedR23, allBSWkeys cold/warm, CRC/key/header/FEguard failures + explicitlyinjectedDMA errors. Full64KiBRAM pernormalglyph; whole16MiB outside exactly4160ownedFE bytes. Privatecomponent notnative/integratededitor.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
 finally:a.close();b.close()
if __name__=='__main__':
 out=ROOT/'build/geos-preview-glyph-cache-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

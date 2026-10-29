"""Actual sealed R24 + resident typed-map/source-key read-only projection gate."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess,sys,shutil,hashlib,zipfile
from dataclasses import replace
from test_folds import projection
import test_fold_controller as resident
from overlays import wrap,HEADER
ROOT=resident.ROOT
DEFAULT=ROOT/'agentsworking/evidence/M7/20261025T053610658929Z-geos-preview-native'
F=0xCF00

def command(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True,capture_output=True)
def freeze(out,source):
 base=out/'fixture';(base/'build/overlays').mkdir(parents=True)
 source=Path(source);r=json.loads((source/'editor-report.json').read_text());identity=json.loads((source/'freeze.json').read_text());names=identity['catalog']
 for n in ['editor.prg','editor-report.json','editor.lbl','editor.map','editor-bindings.json']:shutil.copy2(source/n,base/'build'/n)
 for n in names:shutil.copy2(source/(n+'.seo'),base/'build/overlays'/(n+'.seo'))
 shutil.copy2(source/'product-sources.zip',base/'product-sources.zip');(base/'freeze.json').write_text(json.dumps(dict(names=names,prg_sha256=r['sha256'],binding=r['resident_binding']['digest']),indent=2)+'\n')
 return base,r,names

def build(out,base,r):
 out.mkdir();d=r['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 (out/'entry.s').write_text('''.setcpu "6502"
.include "editor-api.inc"
.include "render/geos/fold-query.inc"
.import se_f_owner
.segment "CODE"
OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 beq step
 cmp #2
 beq cancel
 lda #$B0
 sec
 rts
begin:jmp se_gfq_begin
step:jmp se_gfq_step
cancel:jmp se_gfq_cancel
busy:lda #$B2
 sec
 rts
''')
 objs=[]
 for n,p in [('entry',out/'entry.s'),('query',ROOT/'src/render/geos/fold-query.s')]:
  obj=out/(n+'.o');command('ca65','-g','-I',out,'-I','src','-o',obj,p);objs.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs)
 command('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
 (out/'r.cfg').write_text('MEMORY { R:file=%O,start=$A000,size=$1000; } SEGMENTS { CODE:load=R,type=ro; RODATA:load=R,type=ro; }')
 command('ld65','-C',out/'r.cfg','-o',out/'query.bin','-Ln',out/'query.lbl','-m',out/'query.map',*objs,out/'aliases.o')
 payload=(out/'query.bin').read_bytes();assert len(payload)<=4096
 s=r['symbols'];image=wrap(payload,0,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'query.seo').write_bytes(image)
 return payload,image

class Fixture(resident.Fixture):
 def __init__(self,out,payload,image):super().__init__(out);self.payload=payload;self.image=image;self.query_calls=0;self.query_peak=0
 def import_leaf(self):
  self.m.load(self.s['se_overlay_header'],self.image[:HEADER]);self.m.load(0x5000,self.image[HEADER:]);assert not self.call('se_overlay_import').p&1
 def invoke(self,op):
  self.put('se_overlay_frame',op,1);before=self.read(0,65536);canonical=self.canonical();leases=self.get('se_doc_read_locks',1)
  r,used=self.m.call(self.s['se_overlay_call'],a=24,x=0);self.total_instructions+=used
  self.query_calls+=1;self.query_peak=max(self.query_peak,used);after=self.read(0,65536);wanted=bytearray(before)
  pairs=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1)]
  allowed=[(self.s[n],self.s[n]+w) for n,w in pairs]+[(0x100,0x200),(F,F+48),(0x8080,0x80A0),(0xA000,0xA000+len(self.payload)),(0x5000,0x5000+len(self.payload)),(self.s['copy_direction'],self.s['copy_left']+2),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_overlay_header']+8,self.s['se_overlay_header']+10),(self.s['se_overlay_header']+12,self.s['se_overlay_header']+14),(0xDF00,0xDF0B)]
  if r.p&1:allowed += [(self.s['se_ef_valid'],self.s['se_ef_valid']+1),(self.s['se_ef_fold_rows'],self.s['se_ef_fold_rows']+3)]
  for lo,hi in allowed:wanted[lo:hi]=after[lo:hi]
  assert after==wanted,('fullRAM guard',op,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  assert self.canonical()==canonical and self.get('se_doc_read_locks',1)==leases
  return r
 def query(self,p,mode=0):
  self.m.load(F,p.to_bytes(3,'little')+bytes([mode]));before=self.reu();r=self.invoke(0);steps=0
  while not r.p&1 and r.a==1:r=self.invoke(1);steps+=1;assert steps<40000
  assert self.reu()==before
  return r,self.read(F+4,14),steps

def run(out,source,smoke=False):
 base,r,names=freeze(out,source);payload,image=build(out/'leaf',base,r)
 resident.cpu_editor.ROOT=resident.editor_fixture.ROOT=base;resident.cpu_editor.NAMES=resident.editor_fixture.NAMES=names
 f=Fixture(out,payload,image);cases=[]
 try:
  data=resident.native_text('# Main\rintro\r## Inner\rinside body\r# Tail\rend\r');f.source(data,banks=1);f.action(3);f.import_leaf();records=f.records();assert records
  f.put('se_f_owner',4,1);f.m.load(F,bytes(48));p=int.from_bytes(records[0][3:6],'little');end=int.from_bytes(records[0][6:9],'little');r,output,steps=f.query(p,1)
  assert not r.p&1 and r.a==0 and int.from_bytes(output[:3],'little')==end and output[3]==1 and output[5:14]==records[0][:9],(r.a,r.p,output.hex(),records[0].hex())
  cases.append(dict(tag='actualcollapsedouter-forward-query',query=p,result=end,steps=steps));print('FIRST R24 FOLD QUERY PASS: actual published typedmap, owner4, one-record STEP, source/phase/lease/16MiBREU exact',flush=True)
  faults=[];checks=1
  if not smoke:
   # Independent source parser supplies tree geometry; published state was
   # produced by the actual C19/C17/C18 builder and collapse-all operation.
   tree,_,_,err=resident.model.oracle(data);assert not err
   tree=[replace(t,flags=1) for t in tree]
   assert [tuple(int.from_bytes(raw[j:j+3],'little') for j in (0,3,6)) for raw in records]==[(t.start,t.hidden,t.end) for t in tree]
   points=sorted({0,len(data),*(max(0,min(len(data),p+d)) for t in tree for p in (t.start,t.hidden,t.end) for d in (-1,0,1))})
   for marked,a,b in [(0,0,0),(1,0,len(data)),(1,len(data),0),(1,7,34),(1,0,7),(1,34,len(data))]:
    f.put('se_f_owner',0,1);f.position(a);f.put('se_sel_mark',marked,1);f.put('se_sel_anchor',b);f.put('se_f_owner',4,1)
    for p in points:
     for mode in (0,1):
      r,output,steps=f.query(p,mode);want=projection(tree,p,mode,a,b if marked else a)
      assert not r.p&1 and r.a==0 and (int.from_bytes(output[:3],'little'),output[3],output[4])==want,(p,mode,a,b,marked,output.hex(),want)
      found=next((t for t in tree if t.flags&1 and t.hidden<=p<t.end),None)
      assert output[5:14]==(found.start.to_bytes(3,'little')+found.hidden.to_bytes(3,'little')+found.end.to_bytes(3,'little') if found else bytes(9))
      checks+=1
   cases.append(dict(tag='independent-preorder-nested-endpoints-forward-reverse-selection',checks=checks-1,positions=points))
   # Every other union owner is opaque, even with a poisoned private frame.
   for owner in (0,1,2,3,5,255):
    f.put('se_f_owner',owner,1);opaque=bytes((i*37+owner)&255 for i in range(128));f.m.load(F,opaque)
    for op in (0,1,2,255):
     r=f.invoke(op);assert r.p&1 and r.a==0xB2 and f.read(F,128)==opaque
   f.put('se_f_owner',4,1);f.m.load(F,bytes(48));faults.append('allwrongowners0/1/2/3/5/255 refuse before CF access for BEGIN/STEP/CANCEL/badop')
   # Map-unavailable path is identity, but canonical bounds remain checked.
   f.put('se_ef_valid',0,1)
   for p in (0,len(data)):
    r,o,n=f.query(p);assert not r.p&1 and r.a==0 and n==0 and int.from_bytes(o[:3],'little')==p and o[3:]==bytes(11)
   r,_,_=f.query(len(data)+1);assert r.p&1 and r.a==0xB0
   f.put('se_ef_valid',1,1);faults.append('no-map identity/EOF without DMA, out-of-source bounds refuse')
   # CANCEL preserves the immutable publication and another reader's lease.
   assert not f.call('se_doc_read_acquire').p&1;f.m.load(F,(len(data)-1).to_bytes(3,'little')+b'\0');assert f.invoke(0).a==1
   descriptor=f.read(f.s['se_ef_state'],114);r=f.invoke(0);assert r.p&1 and r.a==0xB2 and f.m.read(F+18)==1
   r=f.invoke(2);assert not r.p&1 and r.a==0 and f.m.read(F+18)==0 and f.read(f.s['se_ef_state'],114)==descriptor and f.get('se_doc_read_locks',1)==1
   assert not f.invoke(2).p&1;assert not f.call('se_doc_read_release').p&1
   faults.append('pendingBEGIN busy refusal and idempotentCANCEL preserve map/foreignsource lease')
   # Snapshot guards fail before any record DMA on changed descriptors/source.
   for name,width in [('se_ef_generation',2),('se_ef_count',2),('se_ef_token',5),('se_r_revision',4)]:
    f.put('se_sel_mark',0,1);f.m.load(F,(len(data)-1).to_bytes(3,'little')+b'\0');assert f.invoke(0).a==1
    at=f.s[name];old=f.read(at,width);f.m.write(at,old[0]^1);dma=f.read(f.s['se_reu_dma_calls'],2);r=f.invoke(1)
    assert r.p&1 and r.a==(0xB7 if name=='se_r_revision' else 0xB1) and f.read(f.s['se_reu_dma_calls'],2)==dma
    f.m.load(at,old);f.put('se_ef_valid',1,1)
   faults.append('bound map token/count/generation and actual fullsource revision changed fail before record DMA')
   for offset in (0,3,31,34,37,38,44):
    f.m.load(F,(len(data)-1).to_bytes(3,'little')+b'\0');assert f.invoke(0).a==1
    f.m.write(F+offset,f.m.read(F+offset)^1);r=f.invoke(1);assert r.p&1 and r.a==0xB1
   faults.append('query/mode/source-length/privatewitness/caret/selection changes fail closed')
   # Damaged map token and wrong typed object are genuine provider refusals.
   f.m.load(F,bytes(48));token=f.read(f.s['se_ef_token'],5)
   for byte in (0,1,2,3,4):
    f.m.load(f.s['se_ef_token'],token);f.m.write(f.s['se_ef_token']+byte,token[byte]^0x80)
    r,_,_=f.query(0);assert r.p&1 and r.a==0x31,(byte,r.a)
   f.m.load(f.s['se_ef_token'],f.read(f.s['se_doc_original'],5));r,_,_=f.query(0);assert r.p&1 and r.a==0xB0
   f.m.load(f.s['se_ef_token'],token)
   faults.append('all five token bytes and wrong actual object type rejected, no guessed REU access')
   def write_record(raw,index=0):
    f.m.load(f.s['se_object_id'],f.read(f.s['se_ef_token'],5));f.put('se_object_offset',index*32);f.put('se_object_length',32,2);f.put('se_object_c64',0x8080,2);f.m.load(0x8080,raw);assert not f.call('se_object_copy',0).p&1
   original=records[0]
   corrupt=[]
   for offset,value in [(0,int.from_bytes(original[3:6],'little')),(3,int.from_bytes(original[6:9],'little')),(6,len(data)+1),(12,0),(12,4),(13,4),(13,2),(11,16),(20,0),(20,7),(25,1)]:
    raw=bytearray(original);width=3 if offset in (0,3,6) else 1;raw[offset:offset+width]=value.to_bytes(width,'little');write_record(raw)
    r,_,_=f.query(7);assert r.p&1 and r.a==0xB0,(offset,value,r.a);corrupt.append([offset,value])
   write_record(original);faults.append(dict(tag='scanned record corruption cannot publish invalid jump',mutants=corrupt))
   for field in ('se_reu_logical_owner','se_reu_physical_owner'):
    logical=f.m.read(f.s['object_extents']+token[0]*16);slot=logical if field=='se_reu_logical_owner' else f.m.read(f.s['se_reu_map']+logical);old=f.m.read(f.s[field]+slot);f.m.write(f.s[field]+slot,0x77)
    r,_,_=f.query(7);assert r.p&1 and r.a==0x34;f.m.write(f.s[field]+slot,old)
   count=f.read(f.s['se_ef_count'],2)
   for n in (32768,32769,65535):
    f.put('se_ef_count',n,2);r,_,_=f.query(0);assert r.p&1 and r.a==0xB0
   f.m.load(f.s['se_ef_count'],count);faults.append('actual logical/physical map-owner mismatch and count/committed-size/capacity bounds refuse')
   # Explicit validated-map fixture seam: create/write a typed map through
   # actual object APIs, then run the actual R18 full-tree validator. The
   # anchors are synthetic schema inputs, not a claim of source parser output.
   def schema_map(source,folds,banks,noncontiguous=False,pending=False):
    f.put('se_f_owner',0,1);f.source(source,banks=2 if len(source)>65535 else 1)
    if pending:f.position(5);f.key(0xD1)
    reg,_=f.m.call(f.s['se_object_create'],a=0x46,x=banks);assert not reg.p&1;newtoken=f.read(f.s['se_object_id'],5)
    if noncontiguous:
     at=f.s['object_extents']+newtoken[0]*16+1;old=f.m.read(at);reg,_=f.m.call(f.s['se_reu_free'],x=old);assert not reg.p&1
     reg,_=f.m.call(f.s['se_reu_bind'],a=0x46,x=88,y=70);assert not reg.p&1;f.m.write(at,88)
    raw=b''.join(t.bytes() for t in folds)
    for at in range(0,len(raw),2048):
     part=raw[at:at+2048];f.m.load(0x8000,part);f.m.load(f.s['se_object_id'],newtoken);f.put('se_object_offset',at);f.put('se_object_length',len(part),2);f.put('se_object_c64',0x8000,2);assert not f.call('se_object_copy',0).p&1
    f.m.load(f.s['se_object_id'],newtoken);f.put('se_object_offset',len(raw));assert not f.call('se_object_resize').p&1
    assert not f.call('se_doc_invalidate').p&1;assert not f.call('se_ef_key_capture').p&1
    f.put('se_f_owner',3,1);f.put('se_i_ready',0,1);f.m.load(f.s['se_fold_token'],newtoken);f.put('se_fold_count',len(folds),2);f.put('se_fold_length',len(source)+int(pending));f.m.load(f.s['se_fold_epoch'],f.read(f.s['se_r_revision'],4));f.put('se_fold_busy',0,1)
    f.put('se_overlay_frame',6,1);reg,_=f.m.call(f.s['se_overlay_call'],a=18,x=0);assert not reg.p&1
    for _ in range(len(folds)+1):
     f.put('se_overlay_frame',7,1);reg,_=f.m.call(f.s['se_overlay_call'],a=18,x=0);assert not reg.p&1
    assert f.get('se_fold_valid',1)==1 and f.get('se_fold_busy',1)==0
    f.m.load(f.s['se_ef_token'],newtoken);f.put('se_ef_count',len(folds),2);f.put('se_ef_generation',1,2);f.put('se_ef_valid',1,1);f.import_leaf();f.put('se_f_owner',4,1);f.m.load(F,bytes(48));return newtoken
   from test_folds import Fold
   dense=[Fold(i*8,i*8+2,(i+1)*8,flags=1) for i in range(2200)];schema_map(b'A'*(2200*8),dense,2,True)
   for mode in (0,1):
    reg,o,n=f.query(dense[-1].hidden,mode);assert not reg.p&1 and n==2200 and int.from_bytes(o[:3],'little')==(dense[-1].start if mode==0 else dense[-1].end)
   checks+=2;cases.append(dict(tag='2200 fullyvalidated records beyond64KiB/noncontiguous logicalextent88 physical70',map_bytes=70400,steps=2200))
   far=[Fold(65530,65536,66001,flags=1)];schema_map(b'A'*66001,far,1)
   for p in (65529,65530,65535,65536,65537,66000,66001):
    for mode in (0,1):
     reg,o,n=f.query(p,mode);wanted=projection(far,p,mode,0,0);assert not reg.p&1 and (int.from_bytes(o[:3],'little'),o[3],o[4])==wanted;checks+=1
   cases.append(dict(tag='24bit canonical endpoints across65535/EOF',source_bytes=66001))
   # A pending gap is part of the full key. Moving its cursor leaves source
   # identity intact; a new query freezes the newly selected canonical caret.
   small=[Fold(0,10,101,flags=1)];schema_map(b'A'*100,small,1,pending=True)
   revision=f.get('se_r_revision',4);reu=f.reu()
   for op in (6,7):
    assert not f.call('se_hot_call',op).p&1;assert f.get('se_r_revision',4)==revision
    reg,o,n=f.query(20,1);assert not reg.p&1 and int.from_bytes(o[:3],'little')==101;checks+=1
   assert f.get('se_hot_pending',1)==1 and f.reu()==reu
   cases.append(dict(tag='actual pending insertion/LEFT-RIGHT gap motions keep sourcekey and read-only projection'))
  result=dict(status='passed',cases=cases,queries=checks,fault_groups=faults,peak_instructions=f.query_peak,payload_bytes=len(payload),state_bytes=48,record_bytes=32,new_BSS=0,new_ZP=0,scope='ActualsealedR24withfrozenresident sourcekey/object/DMA andpublishedmap; noGEOSpaint/nativeintegrationclaim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=DEFAULT);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-fold-query'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.source,a.smoke)

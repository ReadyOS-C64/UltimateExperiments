"""Private rootless persisted-INLINE consumer: actual baseline + C35 + C36.

No renderer/parent restore or registered-asset integration claim. All lookup
services are actual sealed workers; only baseline construction parses input.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_query as query
import test_cache_classify as classify
from test_cache_query_proof import hooks
from overlays import wrap,HEADER
command=query.command

def build_inline(out,base):
 out.mkdir();report=base/'build/editor-report.json';r=json.loads(report.read_text());s=r['symbols'];digest=r['resident_binding']['digest'];objs=[]
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 for name in ('entry','seed','query','source','records','core','page'):
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-D','BCQ_EDITOR_ACTIVE=1','-D','BCQ_SELECTOR_OWNS_OWNER=1','-o',obj,ROOT/'src/cache/inline'/(name+'.s'));objs.append(obj)
 seam={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85};(out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${v:04X}'for n,v in seam.items())+'\n');command('ca65','-o',out/'state.o',out/'state.s');objs.append(out/'state.o')
 command(sys.executable,'tools/module_bindings.py','--report',report,'--output',out/'aliases.s',*objs);command('ca65','-o',out/'aliases.o',out/'aliases.s');objs.append(out/'aliases.o')
 (out/'image.cfg').write_text('MEMORY { C:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }');command('ld65','-C',out/'image.cfg','-o',out/'image.bin','-Ln',out/'image.lbl','-m',out/'image.map',*objs)
 raw=(out/'image.bin').read_bytes();assert len(raw)<=4096
 image=wrap(raw,1,36,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'image.seo').write_bytes(image);return image

INLINE=r'''  from supermark_model import inline
  inline_cases=[]
  def output():return f.read(0x8300,161)+f.read(0x8f36,160)+f.read(0x8feb,1)+f.read(0x8fd6,21)
  def inlinecheck(data,q,count):
   rr,_,_,_=classify(q);assert rr.a==0
   f.m.write(G+4,count);f.m.load(G,q.to_bytes(3,'little'));sentinel=bytes([0xd7])*161
   f.m.load(0x8300,sentinel);f.m.load(0x8f36,sentinel[:160]);f.m.write(0x8feb,0xd7);f.m.load(0x8fd6,bytes([0xc7])*21)
   original=output();frame=f.read(G,192);canonical=f.canonical();reu=f.reu();old_active=f.get('se_doc_read_locks',1)
   rr=invoke(36,1,0);steps=0
   while not rr.p&1 and rr.a==1:
    now=output();assert now[:161]+now[171:]==original[:161]+original[171:] and f.m.read(G+24)==2,'prematurepublication'
    rr=invoke(36,1,1);steps+=1;assert steps<10000
   assert not rr.p&1 and rr.a==0,(q,count,rr.a,rr.p,steps)
   start=int.from_bytes(frame[9:12],'little');end=int.from_bytes(frame[12:15],'little');body=int.from_bytes(frame[15:18],'little');base=frame[18]
   styles=bytearray(161);roles=bytearray([base])*161;hidden=bytearray(21)
   for kind,style,width,a,b in inline(data[body:end],start=body,body_column=body-start if body>start else None):
    for i in range(count):
     pos=q+i
     if a<=pos<a+width or(kind==1 and b<=pos<b+width):hidden[i//8]|=128>>(i%8)
     if kind==1 and a+width<=pos<b:
      if style==4:styles[i]=128;roles[i]=4
      elif not styles[i]&128:styles[i]|=((style&2)>>1)|((style&1)<<1)
   expected=bytes(v&3 for v in styles[:count])+original[count:161]+bytes(roles[:min(count,160)])+original[161+min(count,160):321]+(bytes([roles[160]])if count==161 else original[321:322])+bytes(hidden)
   assert output()==expected,('inlineoracle',q,count,output().hex(),expected.hex())
   now=bytearray(f.read(G,192));now[21]=frame[21];now[24]=frame[24];assert bytes(now)==frame,'GSEMchanged'
   assert f.canonical()==canonical and f.reu()==reu and f.get('se_doc_read_locks',1)==old_active and f.read(0xc600,1024)==f.shim
   inline_cases.append({'query':q,'count':count,'steps':steps,'source_bytes':len(data)})
  for text in ['**bold *em* tail** @@code **literal**@@ £* escaped ££ unmatched *', '# Heading **strong** *em*', '- list ***both*** and @@x@@', 'Plain **Group** title', '*a* **b** ***c*** @@d@@']:
   data=baseline(sem.geos.native_text(text));end=data.find(13);end=len(data)if end<0 else end
   for q in sorted({0,min(1,end),min(8,end),max(0,end-7)}):inlinecheck(data,q,min(161,len(data)-q))
  for n in (0,1,7,8,31,32,33,127,128,160,161):
   data=baseline(sem.geos.native_text('**')+b'x'*170+sem.geos.native_text('** £* @@z@@'));inlinecheck(data,0,n)
  data=baseline(sem.geos.native_text('**')+b'x'*66000+sem.geos.native_text('**'));inlinecheck(data,65900,104)
  data=baseline(sem.geos.native_text('**x** ')*300);inlinecheck(data,1400,161)
  data=baseline(sem.geos.native_text('Body **bold**\rTail.'),True);inlinecheck(data,0,min(161,len(data)))
  result['inline_cases']=inline_cases

  inline_faults=[]
  data=baseline(sem.geos.native_text('**bold** *em* @@code@@ £* tail ')+b'x'*180);rr,_,_,_=classify(0);assert rr.a==0
  f.m.write(G+4,161);f.m.load(0x8300,bytes([0xd7])*161);f.m.load(0x8f36,bytes([0xd7])*160);f.m.write(0x8feb,0xd7);f.m.load(0x8fd6,bytes([0xc7])*21)
  saved=f.read(0,65536);saved_reu=f.reu();original=output()
  def restart():f.m.load(0,saved)
  def quiet():
   now=output();assert now[:161]+now[171:]==original[:161]+original[171:] and f.m.read(G+24)!=0 and not f.get('se_doc_read_locks',1)
  for owner in (0,1,2,3,5,255):
   for op in (0,1,2,255):
    restart();f.put('se_f_owner',owner,1);phase=f.read(F,576);stage=f.read(0x8880,512);semantic_frame=f.read(G,192);rr=invoke(36,1,op)
    assert rr.p&1 and rr.a==0xb2 and f.read(F,576)==phase and f.read(0x8880,512)==stage and f.read(G,192)==semantic_frame and output()==original
  inline_faults.append('sixforeignowners allentryops opaque')
  for field,value in [(4,162),(4,255),(18,14),(18,255)]:
   restart();f.m.write(G+field,value);phase=f.read(F,576);rr=invoke(36,1,0)
   assert rr.p&1 and rr.a==0xc0 and f.read(F,576)==phase and output()==original and not f.get('se_doc_read_locks',1)
  inline_faults.append('badcount/role beforephase/lease/output')
  for offset in range(85):
   restart();f.m.write(G+29+offset,f.m.read(G+29+offset)^1);rr=invoke(36,1,0)
   assert not rr.p&1 and rr.a==2;quiet()
  inline_faults.append('all85certbytefaults MISS2 beforesemanticpublication')
  for field in (0,4,9,12,15,18):
   restart();rr=invoke(36,1,0);assert not rr.p&1 and rr.a==1
   f.m.write(G+field,f.m.read(G+field)^1);rr=invoke(36,1,1)
   assert rr.p&1 and rr.a==0xc1;quiet()
  inline_faults.append('allfrozenquery/count/start/end/body/role inputs rejectbeforepublication')
  for boundary in ('READ','HEADER','PAYLOAD','EVENT'):
   restart();rr=invoke(36,1,0);assert rr.a==1 and not rr.p&1
   if boundary!='READ':
    for _ in range(100):
     rr=invoke(36,1,1);assert not rr.p&1 and rr.a==1
     if (boundary=='HEADER' and f.m.read(C+8)==8)or(boundary=='PAYLOAD'and f.m.read(C+8)==9)or(boundary=='EVENT'and f.m.read(F+4)==2):break
    else:raise AssertionError(('noboundary',boundary))
   transfer(0,transfer(0,length=1));assert not f.m.read(seam['se_bc_flags'])&32
   rr=invoke(36,1,1);assert rr.p&1 and rr.a==0xc1;quiet()
  inline_faults.append('actualcheckedtyped53write revokes READ/header/payload/heldEVENT nooutput/lease')
  restart();rr=invoke(36,1,0);f.put('se_r_revision',f.get('se_r_revision',4)+1,4);rr=invoke(36,1,1)
  assert rr.p&1 and rr.a in (0xb1,0xc1);quiet();inline_faults.append('midjobfullsource revision reject')
  restart();rr=invoke(36,1,0);idx=next(i for i in range(s['se_overlay_capacity'])if f.m.read(s['se_overlay_ids']+i)==14 and f.m.read(s['image_slot']+i)&1==0);f.m.write(s['se_overlay_ids']+idx,0);f.m.write(s['se_overlay_active'],0);rr=invoke(36,1,1)
  assert rr.p&1 and rr.a==0x17;quiet();inline_faults.append('missingR14 residentEND cleanup')
  restart();assert not f.call('se_doc_read_acquire').p&1;rr=invoke(36,1,0);assert rr.a==1 and f.get('se_doc_read_locks',1)==2
  rr=invoke(36,1,2);assert rr.a==0 and not rr.p&1 and f.get('se_doc_read_locks',1)==1
  rr=invoke(36,1,2);assert rr.a==0 and not rr.p&1 and f.get('se_doc_read_locks',1)==1;f.call('se_doc_read_release');inline_faults.append('idempotentCANCEL preservesforeignsourcelease')
  restart();root=transfer(128,length=128);crref=root[104:108];cr=transfer(crref[0]*4096+64+crref[1]*96,length=96);inl=cr[40];old=transfer(inl*4096+64,length=10);bad=bytearray(old);bad[9]=255;transfer(inl*4096+64,bad)
  rr,_,_,_=classify(0);assert rr.a==0;f.m.write(G+4,161);rr=invoke(36,1,0)
  for _ in range(100):
   if rr.p&1 or rr.a!=1:break
   rr=invoke(36,1,1)
  assert rr.p&1 and rr.a==0xc2 and not f.get('se_doc_read_locks',1) and f.m.read(G+24)!=0
  transfer(inl*4096+64,old);assert f.reu()==saved_reu;inline_faults.append('realINLpayloadCRC damage rejected afternewvalidCRclassification')

  import binascii
  page_offset=inl*4096;header=bytearray(transfer(page_offset,length=64));used=int.from_bytes(header[21:23],'little');assert used<=128
  payload=bytearray(transfer(page_offset+64,length=used));original_header=bytes(header);original_payload=bytes(payload)
  def seal_header(h,p):
   h[39:41]=binascii.crc_hqx(p,0xffff).to_bytes(2,'little');h[37:39]=binascii.crc_hqx(h[:3]+h[4:37]+h[39:],0xffff).to_bytes(2,'little')
  for field,value in [(0,255),(1,5),(2,0),(3,255),(8,255),(9,1)]:
   restart();bad=bytearray(original_payload);h=bytearray(original_header);bad[field]=value;seal_header(h,bad)
   transfer(page_offset+64,bad);transfer(page_offset,h);rr,_,_,_=classify(0);assert rr.a==0;f.m.write(G+4,161);rr=invoke(36,1,0)
   for _ in range(100):
    if rr.p&1 or rr.a!=1:break
    rr=invoke(36,1,1)
   assert rr.p&1 and rr.a==0xc2;quiet()
   transfer(page_offset+64,original_payload);transfer(page_offset,original_header);assert f.reu()==saved_reu
  for field,value in [(23,0),(24,1),(21,(original_header[21]+1)&255)]:
   restart();h=bytearray(original_header);h[field]=value;seal_header(h,original_payload);transfer(page_offset,h);rr,_,_,_=classify(0);assert rr.a==0;f.m.write(G+4,161);rr=invoke(36,1,0)
   for _ in range(100):
    if rr.p&1 or rr.a!=1:break
    rr=invoke(36,1,1)
   assert rr.p&1 and rr.a==0xc2;quiet();transfer(page_offset,original_header);assert f.reu()==saved_reu
  inline_faults.append('validCRC malformedevent kind/style/width/range/reserved and pageSLOTS/USED refuse')
  for text in (':::region **Group**\rbody\r:::end',':::basic\r10 PRINT "x"\r:::'):
   data=baseline(sem.geos.native_text(text));q=0 if text.startswith(':::region')else data.index(13)+1;rr,_,_,_=classify(q);assert rr.a==0;f.m.write(G+4,min(161,len(data)-q));rr=invoke(36,1,0)
   for _ in range(100):
    if rr.p&1 or rr.a!=1:break
    rr=invoke(36,1,1)
   assert not rr.p&1 and rr.a==2 and not f.get('se_doc_read_locks',1) and f.m.read(G+24)==2
  inline_faults.append('unsupportedregion/code kinds explicitMISS2 foractualC26fallback')
  result['inline_faults']=inline_faults
  result['wholeRAM_calls']=calls
  result['inline_bytes']=len(consumer)-36

'''

def run(out):
 text=(ROOT/'tests/test_cache_classify.py').read_text().replace("'BCQ_CLASSIFY=1'","'BCQ_CLASSIFY=1','-D','BCQ_PAGE_REUSE=1','-D','BCQ_FORWARD_SEED=1'")
 text=text.replace("image,seam=build(out/'classify',frozen);s.update(seam)","image,seam=build(out/'classify',frozen);s.update(seam);consumer=make_inline(out/'inline',frozen)")
 text=text.replace('for im in(writer,semantic,image):imp(im)','for im in(writer,semantic,image,consumer):imp(im)')
 text=text.replace("f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0", "f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0\n cap,dma=make_hooks(out/'hooks',frozen);f.m.load(0x900,cap);f.m.load(0x700,dma);f.m.load(s['se_reu_copy'],bytes([0x4c,0,7]))")
 text=text.replace('if ident==35:', 'if ident in(35,36):')
 text=text.replace("   assert wanted==after,", "   if ident==36:\n    for lo,hi in [(0x8880,0x8a00),(0x8300,0x83a1),(0x8f36,0x8fec)]:wanted[lo:hi]=after[lo:hi]\n   assert wanted==after,")
 text=text.replace('if i!=35','if i not in(35,36)')
 text=text.replace("f.m.read(seam['se_bc_flags'])==9","f.m.read(seam['se_bc_flags'])&~32==9").replace("f.m.read(seam['se_bc_flags'])==1","f.m.read(seam['se_bc_flags'])&~32==1")
 text=text.replace('return r,f.read(G+5,16),f.m.read(G+169),steps',"if not r.p&1 and r.a==0:\n   rr,_=f.fast_call(0x900);assert not rr.p&1\n  return r,f.read(G+5,16),f.m.read(G+169),steps")
 text=text.replace("  result={'status':'PASS'", "  result={'status':'PASS'")
 # Extra sourcecases runafteroriginalclassification/fault gate, not ashostseeded hits.
 text=text.replace("  (out/'result.json').write_text", INLINE+"\n  (out/'result.json').write_text") if "  (out/'result.json').write_text"in text else text
 # Resultwriter is compactonsameline, so injectbeforethatstatement.
 text=text.replace(";(out/'result.json').write_text", ";\n"+INLINE+"\n  (out/'result.json').write_text")
 (out/'generated-verifier.py').write_text(text)
 ns={'__file__':str(ROOT/'tests/test_cache_classify.py'),'__name__':'privateinline','make_inline':build_inline,'make_hooks':hooks};exec(compile(text,str(out/'generated-verifier.py'),'exec'),ns);ns['run'](out,classify.BASE,classify.PIPE)

if __name__=='__main__':
 out=ROOT/'build/cache-inline-rootless'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

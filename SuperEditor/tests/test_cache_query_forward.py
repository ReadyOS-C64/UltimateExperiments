"""Private viewport CR proof A/B: actualbaseline/query, no main source edits.

A private clone of the exact frozen DMA routine adds the proposed typed53-write
revocation, and a cold0900 test adapter executes the prospective C21 capture.
These are explicit executable test seams, not shipped resident modifications.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,re,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_classify as classify
import test_cache_query as query
command=query.command
SEAM={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85}

def hooks(out,base):
 out.mkdir();report=base/'build/editor-report.json';s=json.loads(report.read_text())['symbols']
 (out/'capture.s').write_text('.setcpu "6502"\n.macpack longbranch\n.import se_crc_init,se_crc_byte,se_crc_value\nBCQ_EDITOR_ACTIVE=1\nBCQ_PAGE_REUSE=1\nBCQ_PROOF_CAPTURE=1\n.segment "CODE"\n.include "cache/query/proof.inc"\n.export bcq_capture_page\n')
 with zipfile.ZipFile(base/'product-sources.zip')as z:original=z.read('src/reu/dma.s').decode()
 (out/'original-dma.s').write_text(original)
 declarations=original[original.index('.segment "BSS"'):original.index('.segment "CODE"')];names=re.findall(r'^(\w+):',declarations,re.M)
 dma=original.replace(declarations,'\n'.join('.import '+n for n in names)+'\n')
 dma=re.sub(r'^.export se_reu_copy,.*$', '.export se_reu_copy',dma,flags=re.M)
 dma=re.sub(r'^.export se_reu_dma_calls,.*$', '',dma,flags=re.M)
 dma=dma.replace('se_reu_copy:\n','''se_reu_copy:
    pha
    cmp #0
    bne revoke_done
    ldx se_reu_logical
    lda se_reu_logical_owner,x
    cmp #$53
    bne revoke_done
    lda $9FC2
    and #$DF
    sta $9FC2
revoke_done:
    pla
''',1)
 (out/'dma.s').write_text(dma)
 (out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${v:04X}'for n,v in SEAM.items())+'\n');command('ca65','-o',out/'state.o',out/'state.s')
 for tag,address,limit in [('capture',0x900,0x100),('dma',0x700,0x200)]:
  obj=out/(tag+'.o');command('ca65','-g','-I','src','-D','EDITOR_MANAGED_CODE=1','-o',obj,out/(tag+'.s'))
  command(sys.executable,'tools/module_bindings.py','--report',report,'--output',out/(tag+'-aliases.s'),obj,out/'state.o');command('ca65','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s'))
  (out/(tag+'.cfg')).write_text(f'MEMORY {{ C:file=%O,start=${address:04X},size=${limit:04X}; }} SEGMENTS {{ CODE:load=C,type=ro; RODATA:load=C,type=ro; }}');command('ld65','-C',out/(tag+'.cfg'),'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),obj,out/'state.o',out/(tag+'-aliases.o'))
 return (out/'capture.bin').read_bytes(),(out/'dma.bin').read_bytes()

def variant(out,forward):
 reuse=True
 src=ROOT/'tests/test_cache_classify.py';text=src.read_text()
 # This wrapper retains the canonical verifier/oracle and actualbaseline setup,
 # saving an exact generatedcopy rather than editing the shared test.
 if reuse:
  text=text.replace("'BCQ_CLASSIFY=1'","'BCQ_CLASSIFY=1','-D','BCQ_PAGE_REUSE=1','-D','BCQ_FORWARD_SEED=1'")
  text=text.replace("f.m.read(seam['se_bc_flags'])==9","f.m.read(seam['se_bc_flags'])&~32==9").replace("f.m.read(seam['se_bc_flags'])==1","f.m.read(seam['se_bc_flags'])&~32==1")
 text=text.replace("f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0",'''f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0;query_instructions=0;capture_instructions=0;measurements=[];seed_begins=0
 cap,dma=make_hooks(out/'hooks',frozen);f.m.load(0x900,cap);f.m.load(0x700,dma);f.m.load(s['se_reu_copy'],bytes([0x4c,0,7]))''')
 text=text.replace('nonlocal calls\n','nonlocal calls,query_instructions\n',1).replace('r=f.m.regs();calls+=1','r=f.m.regs();calls+=1;query_instructions+=n',1)
 text=text.replace('f.m.load(G,bytes(192));f.m.load(G,pos.to_bytes',"f.m.load(G,bytes(29));f.m.load(G+114,bytes(78));f.m.load(G,pos.to_bytes",1)
 text=text.replace('f.put(\'se_f_owner\',owner,1);',"nonlocal capture_instructions\n  start_instructions=query_instructions;start_capture=capture_instructions;start_seed=seed_begins\n  f.put('se_f_owner',owner,1);",1)
 text=text.replace('return r,f.read(G+5,16),f.m.read(G+169),steps', '''if USE_REUSE and not r.p&1 and r.a==0:
   before_capture=f.read(0,65536);rr,used=f.fast_call(0x900);assert not rr.p&1;capture_instructions+=used
   after_capture=f.read(0,65536);wanted=bytearray(before_capture)
   for lo,hi in [(G+29,G+114),(seam['se_bc_flags'],seam['se_bc_flags']+1),(s['se_crc_value'],s['se_crc_value']+2),(0x100,0x200)]:wanted[lo:hi]=after_capture[lo:hi]
   assert after_capture==wanted,'captureRAM'
  measurements.append({'position':pos,'steps':steps,'instructions':query_instructions-start_instructions,'capture_instructions':capture_instructions-start_capture,'seed_begins':seed_begins-start_seed,'flags':f.m.read(seam['se_bc_flags'])})
  return r,f.read(G+5,16),f.m.read(G+169),steps''')
 text=text.replace("  navigation=baseline(","  check('multipleCRpages',b'Line **x**\\r'*60,list(range(0,661,11)))\n  navigation=baseline(",1)
 # ExecuteC35seed andC37 as sequential actualouterC calls.
 text=text.replace("image,seam=build(out/'classify',frozen);s.update(seam)","image,seam=build(out/'classify',frozen);s.update(seam);fast=make_fast(out/'fast',frozen)")
 text=text.replace('for im in(writer,semantic,image):imp(im)','for im in(writer,semantic,image,fast):imp(im)')
 text=text.replace('nonlocal calls,query_instructions','nonlocal calls,query_instructions,seed_begins').replace('  f.put(\'se_overlay_frame\',op,1)',"  if ident==35 and op==0:seed_begins+=1\n  f.put('se_overlay_frame',op,1)")
 text=text.replace('if ident==35:', 'if ident in(35,37):').replace('(0x9136,0x9137)','(0x9135,0x9137)')
 text=text.replace("f.m.load(G,bytes(29));f.m.load(G+114,bytes(78));f.m.load(G,pos.to_bytes", "f.m.load(G,bytes(5));f.m.load(G+21,bytes(8));f.m.load(G+115,bytes(77));f.m.load(G,pos.to_bytes")
 text=text.replace("old=bytes(range(0xa0,0xb0));f.m.load(G+5,old)","old=f.read(G+5,16)")
 text=text.replace("r=invoke(35,1,0);steps=0", "ident=37 if FORWARD_MODE and f.m.read(seam['se_bc_flags'])&32 else 35;f.m.write(0x9135,ident);f.m.write(0x9136,0);r=invoke(ident,1,0);steps=0")
 text=text.replace('r=invoke(35,1,1);steps+=1;', 'ident=f.m.read(0x9135);r=invoke(ident,1,f.m.read(0x9136));steps+=1;')
 text=text.replace('if i!=35','if i not in(35,37)')
 # Prove the proposed real typedwrite hook: before each actualobject write,
 # bit32 may be present; after the call it MUST be gone (evenINLINEpages).
 text=text.replace("r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1", "r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1\n   if raw is not None:assert not f.m.read(seam['se_bc_flags'])&32")
 text=text.replace("  result={'status':'PASS'", "  if FORWARD_MODE:\n   multi_start=sum(c['queries']for c in cases[:5]);multi=measurements[multi_start:multi_start+61];assert sum(m['seed_begins']for m in multi)==2\n   baseline(sem.geos.native_text('First.\\rMiddle **b**\\rTail.'));rr,expected_middle,expected_hint,_=classify(8);assert rr.a==0\n   saved=f.read(0,65536);saved_reu=f.reu();extra=[]\n   def restart():\n    f.m.load(0,saved);f.m.write(0x9135,37);f.m.write(0x9136,0);f.m.load(G,(8).to_bytes(3,'little'));f.m.write(G+21,0);f.m.write(G+24,2)\n   for owner in (0,1,2,3,5,255):\n    for op in (0,1,2):\n     restart();f.put('se_f_owner',owner,1);phase=f.read(F,576);semantic=f.read(G,192);rr=invoke(37,1,op)\n     assert rr.p&1 and rr.a==0xb2 and f.read(F,576)==phase and f.read(G,192)==semantic\n   extra.append('C37sixforeignowners all3ops opaque')\n   for offset in range(85):\n    restart();at=G+29+offset;f.m.write(at,f.m.read(at)^1);old=f.read(G+5,16);rr=invoke(37,1,0)\n    assert not rr.p&1 and rr.a==1 and f.m.read(0x9135)==35 and not f.get('se_doc_read_locks',1) and f.read(G+5,16)==old\n   extra.append('C37all85certbytefaults handoff35 beforelease/output')\n   actualslot=saved[G+114]\n   for slot in range(256):\n    restart();f.m.write(G+114,slot);old=f.read(G+5,16);rr=invoke(37,1,0)\n    for _ in range(50):\n     if f.m.read(0x9135)==35 or rr.p&1 or rr.a!=1:break\n     rr=invoke(37,1,1)\n    assert not rr.p&1,(slot,rr.a)\n    if slot==actualslot:assert rr.a==0 and f.read(G+5,16)==expected_middle\n    else:assert rr.a==1 and f.m.read(0x9135)==35 and f.read(G+5,16)==old,('slot',slot,actualslot,rr.a)\n    assert not f.get('se_doc_read_locks',1)\n   extra.append('all256uncheckedslotvalues actualCRSTARTwitness or35handoff/nooutput')\n   for case in ('bit','backward','partial'):\n    restart();old=f.read(G+5,16)\n    if case=='bit':f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)\n    if case=='backward':f.m.load(G,(0).to_bytes(3,'little'))\n    if case=='partial':f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])|4,1)\n    rr=invoke(37,1,0);assert not rr.p&1 and rr.a==1 and f.m.read(0x9135)==35 and f.read(G+5,16)==old and not f.get('se_doc_read_locks',1)\n   extra.append('missingproof/backward/MUTATING safe35handoff')\n   for boundary in ('READ','READY'):\n    restart();old=f.read(G+5,16);rr=invoke(37,1,0);assert rr.a==1 and not rr.p&1 and f.get('se_doc_read_locks',1)==1\n    if boundary=='READY':rr=invoke(37,1,1);assert rr.a==1 and f.m.read(F+4)==1\n    transfer(0,transfer(0,length=1));assert not f.m.read(seam['se_bc_flags'])&32;rr=invoke(37,1,1)\n    assert rr.p&1 and rr.a==0xc1 and f.read(G+5,16)==old and not f.get('se_doc_read_locks',1)\n   extra.append('C37injob typedwriteguardrevocation READ/heldCR closesownlease beforepublication')\n   restart();f.put('se_f_owner',0,1);f.position(1);f.put('se_f_owner',4,1);old=f.read(G+5,16);rr=invoke(37,1,0)\n   assert not rr.p&1 and rr.a==2 and f.read(G+5,16)==old and not f.get('se_doc_read_locks',1) and f.m.read(G+24)==2\n   extra.append('C37actualpublicW_LOAD beforeBEGIN snapshotinapplicableMISS2')\n   restart();rr=invoke(37,1,0);assert rr.a==1 and f.get('se_doc_read_locks',1)==1;rr=invoke(37,1,2)\n   assert rr.a==0 and not rr.p&1 and not f.get('se_doc_read_locks',1) and not f.m.read(G+21) and not f.m.read(seam['se_bc_flags'])&8\n   extra.append('C37CANCEL releasesownsource/ACTIVE idempotent')\n   assert f.reu()==saved_reu\n   faults.extend(extra)\n"+"  result={'status':'PASS'")
 text=text.replace("'wholeRAM_calls':calls", "'query_instructions':query_instructions,'capture_instructions':capture_instructions,'measurements':measurements,'wholeRAM_calls':calls")
 (out/'generated-verifier.py').write_text(text)
 ns={'__file__':str(src),'__name__':'cache_proof_private','make_hooks':hooks,'USE_REUSE':reuse,'FORWARD_MODE':forward,'make_fast':build_fast};exec(compile(text,str(out/'generated-verifier.py'),'exec'),ns);ns['run'](out,classify.BASE,classify.PIPE)
 return json.loads((out/'result.json').read_text())

def build_fast(out,base):
 text=(ROOT/'tests/test_cache_classify.py').read_text()
 text=text.replace("('classify-entry','query','source','records')","('fast-entry','query','source','records')").replace("'BCQ_CLASSIFY=1'","'BCQ_CLASSIFY=1','-D','BCQ_PAGE_REUSE=1','-D','BCQ_FORWARD_SEED=1','-D','BCQ_FORWARD_QUERY=1'").replace("('core','open','page')","('core','page')").replace('wrap(raw,1,35','wrap(raw,1,37')
 ns={'__file__':str(ROOT/'tests/test_cache_classify.py'),'__name__':'privateforwardbuild'};exec(compile(text,str(out/'generated-build.py'),'exec'),ns)
 image,_=ns['build'](out,base);return image

if __name__=='__main__':
 out=ROOT/'build/cache-query-forward'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);rows={}
 for name,forward in [('page',False),('forward',True)]:
  folder=out/name;folder.mkdir();rows[name]=variant(folder,forward)
 result={'status':'PASS','scope':'Private actualproducer/writer/C35seed/C37frontendCPU A/B; no packaged claim','page':rows['page'],'forward':rows['forward']};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('FORWARD RESULT',result)

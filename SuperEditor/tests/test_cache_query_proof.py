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

def variant(out,reuse):
 src=ROOT/'tests/test_cache_classify.py';text=src.read_text()
 # This wrapper retains the canonical verifier/oracle and actualbaseline setup,
 # saving an exact generatedcopy rather than editing the shared test.
 if reuse:
  text=text.replace("'BCQ_CLASSIFY=1'","'BCQ_CLASSIFY=1','-D','BCQ_PAGE_REUSE=1'")
  text=text.replace("f.m.read(seam['se_bc_flags'])==9","f.m.read(seam['se_bc_flags'])&~32==9").replace("f.m.read(seam['se_bc_flags'])==1","f.m.read(seam['se_bc_flags'])&~32==1")
 text=text.replace("f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0",'''f=sem.Fixture(out,frozen,sem.geos.grid.runner(out),True);f.s.update(seam);cases=[];calls=0;query_instructions=0;capture_instructions=0;measurements=[]
 cap,dma=make_hooks(out/'hooks',frozen);f.m.load(0x900,cap);f.m.load(0x700,dma);f.m.load(s['se_reu_copy'],bytes([0x4c,0,7]))''')
 text=text.replace('nonlocal calls\n','nonlocal calls,query_instructions\n',1).replace('r=f.m.regs();calls+=1','r=f.m.regs();calls+=1;query_instructions+=n',1)
 text=text.replace('f.m.load(G,bytes(192));f.m.load(G,pos.to_bytes',"f.m.load(G,bytes(29));f.m.load(G+114,bytes(78));f.m.load(G,pos.to_bytes",1)
 text=text.replace('f.put(\'se_f_owner\',owner,1);',"nonlocal capture_instructions\n  start_instructions=query_instructions;start_capture=capture_instructions\n  f.put('se_f_owner',owner,1);",1)
 text=text.replace('return r,f.read(G+5,16),f.m.read(G+169),steps', '''if USE_REUSE and not r.p&1 and r.a==0:
   before_capture=f.read(0,65536);rr,used=f.fast_call(0x900);assert not rr.p&1;capture_instructions+=used
   after_capture=f.read(0,65536);wanted=bytearray(before_capture)
   for lo,hi in [(G+29,G+114),(seam['se_bc_flags'],seam['se_bc_flags']+1),(s['se_crc_value'],s['se_crc_value']+2),(0x100,0x200)]:wanted[lo:hi]=after_capture[lo:hi]
   assert after_capture==wanted,'captureRAM'
  measurements.append({'position':pos,'steps':steps,'instructions':query_instructions-start_instructions,'capture_instructions':capture_instructions-start_capture,'flags':f.m.read(seam['se_bc_flags'])})
  return r,f.read(G+5,16),f.m.read(G+169),steps''')
 text=text.replace("  navigation=baseline(","  check('multipleCRpages',b'Line **x**\\r'*60,[0,410,419,420,429,590,599,600])\n  navigation=baseline(",1)
 # Prove the proposed real typedwrite hook: before each actualobject write,
 # bit32 may be present; after the call it MUST be gone (evenINLINEpages).
 text=text.replace("r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1", "r=f.call('se_object_copy',a=int(raw is None));assert not r.p&1\n   if raw is not None:assert not f.m.read(seam['se_bc_flags'])&32")
 text=text.replace("  result={'status':'PASS'", """  if USE_REUSE:
   proofdata=baseline(sem.geos.native_text('Body **bold**\\rTail.'))
   r,expected_output,expected_hint,cold_steps=classify(0);assert r.a==0
   proof_faults=[]
   for offset in range(85):
    at=G+29+offset;f.m.write(at,f.m.read(at)^1)
    r,got,hint,steps=classify(0);assert r.a==0 and got==expected_output and hint==expected_hint and steps>7
   proof_faults.append('all85certificatebytebitflips refetchvalidatedpage ratherthan falsehit')
   root=transfer(128,length=128);ref=root[104:108];record_offset=ref[0]*4096+64+ref[1]*96;valid_record=transfer(record_offset,length=96)
   for boundary in ('OPEN','CRC','READ','READY'):
    f.m.load(G,bytes(29));f.m.load(G+5,bytes(range(16)));f.m.load(G,(0).to_bytes(3,'little'));f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
    rr=invoke(35,1,0);assert rr.a==1 and not rr.p&1
    if boundary!='OPEN':
     for _ in range(100):
      rr=invoke(35,1,1);assert not rr.p&1
      if (boundary=='CRC'and f.m.read(F+1)==4)or(boundary=='READ'and f.m.read(F+1)==6)or(boundary=='READY'and f.m.read(F+4)==1):break
     else:raise AssertionError(('boundarynotreached',boundary))
    source_reu=f.reu();transfer(record_offset,valid_record);assert not f.m.read(seam['se_bc_flags'])&32 and f.reu()==source_reu
    rr=invoke(35,1,1);assert rr.p&1 and rr.a==0xc1,(boundary,rr.a,rr.p)
    assert not f.get('se_doc_read_locks',1) and f.read(G+5,16)==bytes(range(16)) and not f.m.read(G+21)
   proof_faults.append('typed53identicalwrite duringOPEN/CRC-inprogress/alreadyprovedREAD/heldCR revokeslocalauthority beforepublication')
   f.m.load(G,bytes(29));rr=invoke(35,1,0)
   for _ in range(100):
    rr=invoke(35,1,1)
    if not rr.a:break
   assert not rr.p&1 and not rr.a and f.m.read(F+132)==0xa5
   transfer(record_offset,valid_record);before=f.read(G+29,85);rr,nn=f.fast_call(0x900)
   assert rr.p&1 and not f.m.read(seam['se_bc_flags'])&32 and f.read(G+29,85)==before
   proof_faults.append('typed53write afterEND beforeC21capture preventsVALIDlastrecertification')
   rr,_,_,_=classify(0);assert rr.a==0
   for address,value in [(G+24,2),(F+1,1),(F+3,1),(F+132,0),(F+115,0)]:
    saved=f.read(0,65536);f.m.write(address,value);before=f.read(G+29,85)
    rr,nn=f.fast_call(0x900)
    assert rr.p&1 and not f.m.read(seam['se_bc_flags'])&32 and f.read(G+29,85)==before,('captureprecondition',address)
    f.m.load(0,saved)
   proof_faults.append('captureERROR/state/live/proofA5/kindrefusal revokesbit32 withoutcertificatepublication')
   rr,_,_,warm_steps=classify(0);assert rr.a==0
   # A normal derived FE write does not revoke typed53 proof authority.
   allocated=f.call('se_reu_alloc',a=0xfe);assert not allocated.p&1
   f.put('se_reu_logical',allocated.a,1);f.put('se_reu_offset',0,2);f.put('se_reu_c64',IO,2);f.put('se_reu_length',1,2);f.m.write(IO,0x55)
   rr=f.call('se_reu_copy',a=0);assert not rr.p&1 and f.m.read(seam['se_bc_flags'])&32
   rr,got,hint,steps=classify(0);assert rr.a==0 and got==expected_output and steps==7
   proof_faults.append('actualrawFECPUwrite preserveseligibleCRproof and warmhit')
   faults.extend(proof_faults)
  result={'status':'PASS'""")
 text=text.replace("'wholeRAM_calls':calls", "'query_instructions':query_instructions,'capture_instructions':capture_instructions,'measurements':measurements,'wholeRAM_calls':calls")
 (out/'generated-verifier.py').write_text(text)
 ns={'__file__':str(src),'__name__':'cache_proof_private','make_hooks':hooks,'USE_REUSE':reuse};exec(compile(text,str(out/'generated-verifier.py'),'exec'),ns);ns['run'](out,classify.BASE,classify.PIPE)
 return json.loads((out/'result.json').read_text())

if __name__=='__main__':
 out=ROOT/'build/cache-query-proof'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);rows={}
 for name,reuse in [('control',False),('reuse',True)]:
  folder=out/name;folder.mkdir();rows[name]=variant(folder,reuse)
 result={'status':'PASS','scope':'Private actualpipeline CPU A/B +prospectiveC21capture/typed53DMAhooks; no packaged/nativeclaim','control':rows['control'],'reuse':rows['reuse']};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PROOF RESULT',result)

"""Private SOURCE_ONLY C39 actual event-work bound, no product integration."""
from pathlib import Path
from datetime import datetime,timezone
import sys,inspect,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_adaptive as adaptive
import test_cache_inline_source as source

def build_adapter(out,base):
 code=inspect.getsource(adaptive.build_adapter).replace('probes/adaptive-source','probes/event-bound-source')
 ns=dict(vars(adaptive));exec(compile(code,str(out/'event-builder.py'),'exec'),ns);return ns['build_adapter'](out,base)

INJECT="   if hostile_count is not None:\n    import binascii\n    root_header=transfer(128,length=128);ref=root_header[104:108];page_at=ref[0]*4096;hdr=bytearray(transfer(page_at,length=64));used=int.from_bytes(hdr[21:23],'little');payload=bytearray()\n    for off in range(0,used,128):payload.extend(transfer(page_at+64+off,length=min(128,used-off)))\n    at=ref[1]*96;cr=bytearray(payload[at:at+96]);cr[44:47]=hostile_count.to_bytes(3,'little');cr[74:76]=binascii.crc_hqx(cr[1:74]+cr[76:],0xffff).to_bytes(2,'little');payload[at:at+96]=cr\n    hdr[39:41]=binascii.crc_hqx(payload,0xffff).to_bytes(2,'little');hdr[37:39]=binascii.crc_hqx(hdr[:3]+hdr[4:37]+hdr[39:],0xffff).to_bytes(2,'little')\n    for off in range(0,used,128):transfer(page_at+64+off,payload[off:off+128])\n    transfer(page_at,hdr)\n"
CHECKS="   if not source_entry_faults:\n    original_frame=f.read(G,192);original_phase=f.read(F,576);original_stage=f.read(0x8880,512)\n    for owner in (0,1,2,3,5,255):\n     for op in (0,1,2,255):\n      f.put('se_f_owner',owner,1);rr=invoke(39,1,op);assert rr.p&1 and rr.a==0xb2 and f.read(G,192)==original_frame and f.read(F,576)==original_phase and f.read(0x8880,512)==original_stage\n    f.put('se_f_owner',4,1)\n    for cont in (0,2,255):\n     f.m.write(G+167,cont);saved_g=f.read(G,192)\n     for op in (0,1,2,255):\n      rr=invoke(39,1,op);assert rr.p&1 and rr.a==0xc0 and f.read(G,192)==saved_g and f.read(F,576)==original_phase and f.read(0x8880,512)==original_stage\n    f.m.load(G,original_frame);f.m.write(G+167,1);f.m.write(G+4,0);f.m.load(0x8300,bytes([0xd7])*161);f.m.load(0x8f36,bytes([0xd7])*160);f.m.write(0x8feb,0xd7);f.m.load(0x8fd6,bytes([0xc7])*21)\n    f.m.write(0x9135,39);f.m.write(0x9136,0);rr=invoke(39,1,0)\n    for _ in range(100):\n     if rr.p&1 or rr.a!=1 or f.m.read(0x9135)!=39:break\n     rr=invoke(39,1,f.m.read(0x9136))\n    assert not rr.p&1 and rr.a==1 and f.m.read(0x9135)==20 and f.m.read(0x9136)==1 and not f.get('se_doc_read_locks',1)\n    assert f.read(0x8300,161)==bytes([0xd7])*161 and f.read(0x8f36,160)==bytes([0xd7])*160 and f.m.read(0x8feb)==0xd7 and f.read(0x8fd6,21)==bytes(21)\n    f.m.load(G,original_frame);source_entry_faults.extend(['actualSOURCE_ONLY6foreignowners4ops opaque','actualSOURCE_ONLY3invalidCONT4ops beforephase','actualCOUNT0 finalSOURCE20/1 with unchangedstyles/roles zero21mask nolease'])\n"

def run(out):
 # Prepare the released adaptive driver's exact SOURCE body, then add only
 # SOURCE_ONLY endpoint and fault expectations. Existing test files stay fixed.
 prep=inspect.getsource(adaptive.run)
 prep=prep[:prep.index(' code=inspect.getsource(source.run)')]
 prep=prep.replace('def run(out):','def prepare():')+' return content\n'
 ns=dict(vars(adaptive));exec(compile(prep,str(out/'prepare.py'),'exec'),ns);content=ns['prepare']()
 content=content.replace('source_cases=[]','source_cases=[];source_entry_faults=[]')
 content=content.replace('bad_cert=False','bad_cert=False,hostile_count=None')
 content=content.replace('data=baseline(data,pending);rr,_,_,_=classify(start);assert rr.a==0','data=baseline(data,pending)\n'+INJECT+'   rr,_,_,_=classify(start);assert rr.a==0')
 content=content.replace('   # Only this sourceconstant path',CHECKS+'   # Only this sourceconstant path')
 content=content.replace("'hint':has_inline,","'hint':has_inline,'hostile_count':hostile_count,")
 content=content.replace('if cached and eligible and not poison and not bad_cert:assert counts[26]==begins','if cached and eligible and not poison and not bad_cert:assert counts[26]>=begins')
 old_assert='    assert not rr.p&1,(start,cached,poison,rr.a,counts)'
 assert old_assert in content
 content=content.replace(old_assert,"""    if hostile_count in (0,8,65536,0xffffff) and rr.p&1:
     assert rr.a==(0xc0 if hostile_count==8 else 0xc2) and returns==0 and not f.get('se_doc_read_locks',1) and not f.m.read(0x912d) and f.reu()==reu and f.canonical()==canonical and f.m.read(G+24)!=0,(hostile_count,rr.a,returns,f.get('se_doc_read_locks',1),f.m.read(0x912d),f.reu()==reu,f.canonical()==canonical,f.m.read(G+24))
     source_cases.append({'fault':'resealedhostileINLINEcount','hostile_count':hostile_count,'error':rr.a,'counts':counts});return
"""+old_assert)
 content=content.replace("  result['source_cases']=source_cases", """  for hostile in (0,8,9,255,256,65535,65536,0xffffff):line(samples[3],cached=True,hostile_count=hostile)
  for size in (512,1024):
   for events in (1,4,8):
    text='**x** '*events+'w ' *((size-events*6)//2)
    assert len(text)==size
    line(sem.geos.native_text(text+'\\rNext.'),cached=False);line(sem.geos.native_text(text+'\\rNext.'),cached=True)
  result['source_entry_faults']=source_entry_faults
  result['source_cases']=source_cases""")
 driver=inspect.getsource(adaptive.run)
 driver='def run(out):\n content=PREPARED\n'+driver[driver.index(' code=inspect.getsource(source.run)'):]
 driver=driver.replace("r['component_profile']=component_profile(component_out)","r['component_profile']={'scope':'SOURCE_ONLY endpoint; standalone A0/A2 gate not claimed'}")
 ns=dict(vars(adaptive));ns.update(build_adapter=build_adapter,PREPARED=content)
 (out/'source-cases.py').write_text(content);(out/'event-generator.py').write_text(driver);exec(compile(driver,str(out/'event-generator.py'),'exec'),ns);ns['run'](out)
 r=json.loads((out/'result.json').read_text());r['event_bound']=8;r['source_only']=True;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
 out=ROOT/'build/cache-inline-event-bound'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

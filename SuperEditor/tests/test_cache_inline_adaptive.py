"""Private C26 SOURCE-only adaptive routing; C20 bytes unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import sys,inspect,runpy,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_source as source


def build_adapter(out,base):
 code=inspect.getsource(source.component.build_inline)
 code=code.replace("ROOT/'src/cache/inline'/(name+'.s')", "ROOT/'src/cache/inline'/('probes/adaptive-source'if name=='entry'else('probes/source-adapter'if name in('seed','core','page')else''))/(name+'.s')")
 code=code.replace('wrap(raw,1,36','wrap(raw,1,39');ns=dict(vars(source.component));exec(compile(code,str(out/'generated-build.py'),'exec'),ns);return ns['build_inline'](out,base)

def source_images(out,base):
 out.mkdir();b=runpy.run_path(str(ROOT/'src/cache/inline/probes/adaptive-source/build.py'));candidate=b['build'](out/'inline',base)
 control=(base/'build/overlays/geosline.seo').read_bytes();return control,control,(base/'build/overlays/geosinln.seo').read_bytes(),candidate


def gate_contract(out,base):
 import json
 from peddle import Machine
 from test_cache_query import command
 out.mkdir();report=json.loads((base/'build/editor-report.json').read_text());sym=report['symbols']
 (out/'entry.s').write_text('.setcpu "6502"\n.include "render/geos/semantic.inc"\n.include "render/geos/source-line.inc"\n.import se_f_owner,se_overlay_frame,se_bc_flags,se_bc_count\nF=GSEM_FRAME\n.segment "CODE"\n.export entry\nentry:lda se_f_owner\ncmp #4\nbne busy\nlda se_overlay_frame\ncmp #5\nbeq source_legacy\ncmp #3\nbne bad\n.include "gate.inc"\nsource_legacy:lda #3\nclc\nrts\nbusy:lda #$B2\nsec\nrts\nbad:lda #$C0\nsec\nrts\n')
 command('ca65','-g','-I','src','-I','src/cache/inline/probes/adaptive-source','-o',out/'entry.o',out/'entry.s')
 (out/'state.s').write_text('.export se_bc_flags,se_bc_count\nse_bc_flags=$9FC2\nse_bc_count=$9FC5\n');command('ca65','-o',out/'state.o',out/'state.s')
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',out/'entry.o',out/'state.o');command('ca65','-o',out/'aliases.o',out/'aliases.s')
 (out/'image.cfg').write_text('MEMORY { C:file=%O,start=$0A00,size=$0200; } SEGMENTS { CODE:load=C,type=ro; }');command('ld65','-C',out/'image.cfg','-o',out/'image.bin',out/'entry.o',out/'state.o',out/'aliases.o')
 m=Machine();cases=[]
 def trial(body,end,want,**kw):
  # Host inputs test the read-only admission predicate only; no cache/source hit.
  m.load(0,bytes((i*73+29)&255 for i in range(65536)));m.load(0xa00,(out/'image.bin').read_bytes());m.write(sym['se_f_owner'],kw.get('owner',4));m.write(sym['se_overlay_frame'],kw.get('op',3));m.write(0x912c,kw.get('active',0));m.write(0x912d,kw.get('context',0));m.write(0x9fc2,kw.get('flags',33));m.write(0x9fc5,kw.get('queue',0));m.write(0x8b40+167,kw.get('continuation',1));m.write(0x8b40+21,kw.get('semantic_active',0));m.write(0x8b40+5,kw.get('kind',0));m.write(0x8b40+169,kw.get('inline',1));m.write(0x8b40+4,kw.get('count',160));m.write(0x8b40+18,kw.get('role',0));m.load(0x8b40+15,body.to_bytes(3,'little'));m.load(0x8b40+12,end.to_bytes(3,'little'))
  before=bytes(m.read(i)for i in range(65536));r,n=m.call(0xa00);after=bytes(m.read(i)for i in range(65536));allowed=bytearray(before);allowed[0x100:0x200]=after[0x100:0x200]
  if want==1:allowed[0x9135:0x9137]=bytes([39,0]);assert not r.p&1 and r.a==1
  elif want==3:assert not r.p&1 and r.a==3
  else:assert r.p&1 and r.a==want
  assert bytes(allowed)==after,('predicateRAM',body,end,kw)
  cases.append({'body':body,'end':end,'want':want,'input':kw,'instructions':n})
 try:
  for body,end in [(0,0),(0,511),(0,512),(0,65535),(0,65536),(0,0xffffff),(0xfff000,0xfff200),(0x10000,0xffff),(0xffff00,0xffffff),(0xfffe00,0xffffff),(0xfffdff,0xffffff)]:trial(body,end,1 if end>=body and end-body>=512 else 3)
  for field,values in {'flags':[0,1,2,3,4,5,8,9,32,35,37,41,255],'queue':[1,3,255],'active':[1,255],'context':[1,255],'continuation':[0,2,255],'semantic_active':[1,255],'kind':[4,5,6,7,255],'inline':[0],'count':[161,255],'role':[14,255]}.items():
   for value in values:trial(0,65536,3,**{field:value})
  for flags in [33,49]:trial(0,65536,1,flags=flags)
  trial(0,65536,1,count=0)
  for owner in [0,1,2,3,5,255]:
   for op in [3,5]:trial(0,65536,0xb2,owner=owner,op=op)
  for flags in [0,33,255]:trial(0,65536,3,op=5,flags=flags)
 finally:m.close()
 result={'status':'PASS','cases':cases,'scope':'Exact gate include, full64KiB read-only predicate/wrongowner/op5 bypass; endpoint legacy sentinel is explicit and proves no source semantics'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def component_profile(out):
 code=inspect.getsource(source.component.run)
 ns=dict(vars(source.component))
 def component_adapter(path,base):
  from overlays import wrap
  image=build_adapter(path,base);r=json.loads((base/'build/editor-report.json').read_text());sym=r['symbols'];return wrap(image[36:],1,36,api=(sym['se_overlay_call'],sym['se_overlay_frame']),binding_digest=bytes.fromhex(r['resident_binding']['digest']))
 ns['build_inline']=component_adapter
 (out/'component-generator.py').write_text(code);exec(compile(code,str(out/'component-generator.py'),'exec'),ns);ns['run'](out)
 return json.loads((out/'result.json').read_text())

def run(out):
 content=source.SOURCE
 content=content.replace('poison=False,change=False','poison=False,change=False,bad_cert=False')
 content=content.replace("f.assets['geosline']=source_candidate if cached else source_control", "f.assets['geosline']=source_control\n   f.assets['geosinln']=inline_candidate if cached else inline_control")
 content=content.replace("has_inline=f.m.read(G+169)", "has_inline=f.m.read(G+169);body_length=int.from_bytes(f.read(G+12,3),'little')-int.from_bytes(f.read(G+15,3),'little');eligible=bool(has_inline and body_length>=512)\n   if bad_cert:f.m.write(G+29,f.m.read(G+29)^1)")
 content=content.replace('if cached and not poison:assert f.read(0x45e6,0x800-0x5e6)==backups[-1]', 'if cached and backups:assert f.read(0x45e6,0x800-0x5e6)==backups[-1]')
 content=content.replace("if cached:assert (counts[39]>0)==bool(has_inline) and begins==returns", "if cached:assert (counts[39]>0)==bool(eligible and not poison)\n   if cached and eligible and not poison and not bad_cert:assert begins==returns")
 content=content.replace('if cached and not poison:assert counts[26]==0', 'if cached and eligible and not poison and not bad_cert:assert counts[26]==begins')
 content=content.replace('if poison:assert counts[26]>0','if poison or bad_cert:assert counts[26]>0')
 content=content.replace("'pending':pending,'counts'", "'pending':pending,'bad_cert':bad_cert,'body_length':body_length,'counts'")
 content=content.replace("line(samples[4],cached=True,change=True)", "line(samples[4],cached=True,change=True);line(samples[3],cached=True,poison=True);line(samples[3],cached=True,bad_cert=True)")
 content=content.replace("  result['source_cases']=source_cases", "  far_data=sem.geos.native_text('**')+b'x'*66000+sem.geos.native_text('**\\rNext.')\n  line(far_data,start=65900,cached=False);line(far_data,start=65900,cached=True)\n  dense=sem.geos.native_text('**x** ')*300\n  line(dense,start=1400,cached=False);line(dense,start=1400,cached=True)\n  result['source_cases']=source_cases")
 content=content.replace("Private actual C20 SOURCE continuation with sequential REQUEST/OP C39/C26 frontend", "Private unchanged C20 SOURCE continuation with adaptive C26 and sequential REQUEST/OP C39 frontend")
 code=inspect.getsource(source.run)
 code=code.replace("(0x8400,0x8480)","(0x8400,0x8800)")
 code=code.replace("('text_ptr',2),('screen_ptr',2)","('doc_root_ptr',2),('doc_piece_ptr',2),('se_doc_offset',7),('doc_cache_slot',30),('text_ptr',2),('screen_ptr',2)")
 code=code.replace("source_control,source_candidate=make_source", "source_control,source_candidate,inline_control,inline_candidate=make_source")
 ns=dict(vars(source));ns.update(SOURCE=content,build_adapter=build_adapter,source_images=source_images)
 (out/'adapter-generator.py').write_text(code);exec(compile(code,str(out/'adapter-generator.py'),'exec'),ns);ns['run'](out)
 r=json.loads((out/'result.json').read_text());r['gate_contract']=gate_contract(out/'gate-contract',source.component.classify.BASE);component_out=out/'component-profile';component_out.mkdir();r['component_profile']=component_profile(component_out);r['C20_unchanged']=True;r['adaptive_C26_bytes']=len((out/'source/inline/candidate/image.bin').read_bytes());(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
 out=ROOT/'build/cache-inline-adaptive'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)

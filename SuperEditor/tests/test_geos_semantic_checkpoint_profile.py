"""Actual root C24 query/read attribution on immutable combined48; no substitutions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as heading
geos=heading.geos;semantic=heading.semantic
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
F=0x8b40
class Fixture(heading.Fixture):
 def __init__(self,*a,**k):self.trace_enabled=False;self.queries=[];self.query=None;super().__init__(*a,**k)
 def call(self,n,a=0):
  sample=self.trace_enabled and n=='se_editor_service' and self.get('se_e_job',1)in(11,12)and self.get('se_f_owner',1)==4 and self.m.read(0x9135)==24
  if sample:
   query=int.from_bytes(self.read(F,3),'little');op=self.m.read(0x9136)
   if op==0:self.query=dict(query=query,source_bytes=self.get('se_v_length'),top=self.get('se_v_top'),docgen=self.get('se_doc_generation',2),revision=self.get('se_r_revision',4),job=self.get('se_e_job',1),instructions=0,services=0,READS=0,op=op)
   before=self.total_instructions
  r=super().call(n,a)
  if sample:
   assert self.query is not None
   self.query['instructions']+=self.total_instructions-before;self.query['services']+=1;self.query['READS']=int.from_bytes(self.read(F+164,3),'little')
   if self.m.read(0x9135)!=24 or not self.m.read(F+21):
    self.query.update(kind=self.m.read(F+5),start=int.from_bytes(self.read(F+9,3),'little'),end=int.from_bytes(self.read(F+12,3),'little'),body=int.from_bytes(self.read(F+15,3),'little'));self.queries.append(self.query);self.query=None
  return r

def run(out,base,only=None):
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};f=Fixture(out,frozen,dll,True);cases=[]
 try:
  for label,far in [('near',False),('far64k',True)]:
   pre=geos.native_text('prefix\r')*9400 if far else b''
   for op in ['body','CRsplit','CRjoin']:
    if only and label+'-'+op!=only:continue
    raw=pre+geos.native_text('# Heading words.\rFollowing row.\rTail.');at=len(pre)+(5 if op!='CRjoin'else 17)
    f.source(raw);f.command(99);f.position(at);f.render();oldtop=f.get('se_v_top');oldgen=f.get('se_doc_generation',2);oldrev=f.get('se_r_revision',4);oldgcc=f.read(0xcf90,47).hex();f.trace_enabled=True;f.queries=[];before=f.total_instructions
    key=geos.native_text('Q')[0]if op=='body'else 13 if op=='CRsplit'else 0x14
    data=raw[:at]+bytes([key])+raw[at:]if op!='CRjoin'else raw[:at-1]+raw[at:];f.key(key);afterinput=dict(top=f.get('se_v_top'),generation=f.get('se_doc_generation',2),revision=f.get('se_r_revision',4),GEC=f.read(0xcfe8,20).hex());f.render();f.trace_enabled=False
    assert f.merged()==data
    eb,ea,rows,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea
    assert not any(f.get(n,1)for n in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])and f.read(0xc600,1024)==f.shim
    entry=dict(oldtop=oldtop,oldgen=oldgen,oldrevision=oldrev,oldGCC=oldgcc,afterinput=afterinput,settledtop=f.get('se_v_top'),settledgen=f.get('se_doc_generation',2),tag=label+'-'+op,source_bytes=len(raw),edit_position=at,total_instructions=f.total_instructions-before,queries=f.queries,query_READS=sum(q['READS']for q in f.queries),query_instructions=sum(q['instructions']for q in f.queries));cases.append(entry);geos.png(eb,ea,out/(entry['tag']+'.png'));print('PASS',json.dumps({k:v for k,v in entry.items()if k!='queries'}|{'queries':len(entry['queries'])}),flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  result=dict(status='passed',identity=identity,cases=cases,scope='Actual public root/C6/C21/C24 service attribution. CPUinstructions include resident/overlay/R14 guard work during C24 services, not nativecycles. QueryREADS is actual C24 R14 counter, not inferred source length. No productchange.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--only');a=p.parse_args();out=ROOT/'build/geos-semantic-checkpoint-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.only)

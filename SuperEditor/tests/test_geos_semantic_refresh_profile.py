"""Private repeated publication profile; no new checkpoint authority is invented."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c
F=c.F

def run(out,base,smoke=False):
 spec=importlib.util.spec_from_file_location('consumer_build',c.D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 frozen,identity=c.geos.freeze(out,base);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);f.assets['geossema']=(out/'link/seed/geossema.seo').read_bytes();f.assets['geospage']=(out/'link/producer/geospage.seo').read_bytes();fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def records():
  cache,bank=f.raw_cache();result=[]
  for offset in(0x600,0x640):
   r=cache[offset:offset+64];result.append(dict(offset=offset,valid=r[3],version=r[1],anchor=int.from_bytes(r[4:7],'little'),revision=int.from_bytes(r[24:28],'little'),length=int.from_bytes(r[28:31],'little'),TOP=int.from_bytes(r[41:44],'little'),crc_ok=binascii.crc_hqx(r[:62],65535)==int.from_bytes(r[62:64],'little'),raw=r.hex()))
  return result
 try:
  for far in([False]if smoke else[False,True]):
   for row in([1]if smoke else[0,1,2]):
    pre=c.geos.native_text('prefix\r')*(9400 if far else 0);suffix=c.geos.native_text('# Heading words.\rSecond plain row.\rThird plain row.\rTail.');data=pre+suffix;top=len(pre);at=top+([5,len(suffix.split(b'\r')[0])+1+5,len(suffix.split(b'\r')[0])+1+len(suffix.split(b'\r')[1])+1+5][row]);f.source(data);f.command(99);f.position(top);f.render();f.position(at);f.render();assert f.get('se_v_top')==top,(far,row,top,f.get('se_v_top'))
    for serial,key in enumerate([c.geos.native_text('Q')[0],c.geos.native_text('R')[0],0x14,0x14,13]):
     before_records=records();at=f.get('se_hot_caret');data=(data[:at-1]+data[at:])if key==0x14 else(data[:at]+bytes([key])+data[at:]);f.key(key);canonical=f.canonical();catalog=f.catalog();before=f.reu();start=f.total_instructions;f.events=[];f.trace=True;f.render();f.trace=False;used=f.total_instructions-start;c.exact_pixels(f,data,fonts,'repeated');assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog and f.read(0xc600,1024)==f.shim;c.outside_cache(f,before,'repeated');assert not any(f.get(n,1)for n in['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])
     entry=dict(far=far,row=row,serial=serial,key=key,source_bytes=len(data),TOP=top,render_instructions=used,current_revision=f.get('se_r_revision',4),single_GEC_valid=f.m.read(0xcfe8),records_before=before_records,records_after=records(),queries=f.events,hit=any(e['op']==3 and e['proof']in(1,2)for e in f.events),max_READS=max([e['READS']for e in f.events]or [0]));cases.append(entry);print('PASS',{k:v for k,v in entry.items()if k not in['records_before','records_after','queries']},flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  result=dict(status='passed',identity=identity,budget=budget,cases=cases,scope='Measured actualpublicrepeated C6→C21/C24 consumer publications; strict original authority unchanged, allpixels/anchors/canonical/catalog/shim/full16MiB. CPUinstructions only.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=c.BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-semantic-refresh-profile'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve(),a.smoke);print('RESULT',r['status'],'cases',len(r['cases']))

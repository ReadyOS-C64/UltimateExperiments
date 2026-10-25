"""Recomputed-CRC invalidmetric records mustmiss, not publish cachedgeometry."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,binascii,importlib.util,shutil
import test_geos_preview_glyph_cache as c

def run(out,base,script='build-premeasure.py'):
 frozen,identity=c.old.geos.freeze(out,base);c.old.geos.grid.editor_fixture.ROOT=c.old.geos.grid.cpu_editor.ROOT=frozen;c.old.geos.grid.editor_fixture.NAMES=c.old.geos.grid.cpu_editor.NAMES=identity['names'];spec=importlib.util.spec_from_file_location('cachebuild',c.D/script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);budget=m.build(out/'leaf',frozen)
 for ext in('bin','lbl'):shutil.copy2(out/'leaf'/('cache.'+ext),out/'leaf'/('r23.'+ext))
 f=c.Fixture(out,frozen,c.old.geos.grid.runner(out),out/'leaf');pack=(out/'leaf/base/font-pack.bin').read_bytes();e=next(pack[32+i*16:48+i*16]for i in range(43)if pack[32+i*16:36+i*16]==bytes((2,255,255,9)));cases=[]
 try:
  h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h)
  for tag,field,value in [('screen',4,3),('width',5,12),('advance',6,15),('advance-relation',6,1),('height',7,8),('baseline',8,7)]:
   _,expected,_=f.glyph(e,65,3,1);index=((expected[15]^(3<<4))&127)if script in ('build-stylehash.py','build-once.py')else expected[15]&127;offset=0xeba9+index*32;record=bytearray(f.reu()[bank*65536+offset:bank*65536+offset+32]);record[field]=value;record[28:30]=binascii.crc_hqx(record[1:28],65535).to_bytes(2,'little');f.m.load(0x8080,record);f.put('se_reu_logical',h,1);f.put('se_reu_offset',offset,2);f.put('se_reu_length',32,2);f.put('se_reu_c64',0x8080,2);assert not f.call('se_reu_copy',0).p&1
   r,actual,instructions=f.glyph(e,65,3,1);assert not r.p&1 and actual[:56]==expected[:56]and instructions>3000,(tag,instructions);cases.append(dict(tag=tag,instructions=instructions))
  result=dict(status='passed',budget=budget,cases=cases,scope='ActualtypedFE/FD, forgedinvalidmetricrecords with recomputedCRC refusehit and regenerateexactgenuineglyph. No production/nativeclaim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
 finally:f.close()
if __name__=='__main__':
 out=c.ROOT/'build/geos-preview-glyph-cache-metrics'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve())

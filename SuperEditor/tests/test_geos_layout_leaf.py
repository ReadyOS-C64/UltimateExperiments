"""Actual sealed C20 source/line/bands leaf, private current-resident CPU proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys
import test_geos_source_line as source
import test_fold_retention as retention
import test_grid_modes as grid
import test_geos_bands as bands
import test_geos_line as line
from test_geos_glyphs import native
from overlays import wrap
ROOT=grid.ROOT;L=0x8D00;CONTROL=0x912C

def run(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def build(out,base):
 report=json.loads((base/'build/editor-report.json').read_text());d=report['resident_binding']['digest'];s=report['symbols']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for n in ['source-line','line','measure','assets','bands']:
  p=out/(n+'.o');run('ca65','-g','-I',out,'-I','src','-o',p,'src/render/geos/'+n+'.s');objs.append(p)
 aliases=out/'aliases.s';run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',aliases,*objs);run('ca65','-g','-I','src','-o',out/'aliases.o',aliases)
 run('ld65','-C','cfg/geos-editor-layout.cfg','-o',out/'geoslayout.bin','-Ln',out/'geoslayout.lbl','-m',out/'geoslayout.map',*objs,out/'aliases.o')
 import re
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'geoslayout.lbl').read_text())};payload=(out/'geoslayout.bin').read_bytes();assert len(payload)<=4096 and labels['entry']==0xB010 and labels['se_gb_frame']==L
 image=wrap(payload,1,20,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'geoslayout.seo').write_bytes(image)
 (out/'fit.json').write_text(json.dumps(dict(payload_bytes=len(payload),free=4096-len(payload),bands_bytes=labels['__GEOS_BANDS_SIZE__'],resident_sha256=report['sha256']),indent=2)+'\n');return image,report

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path);ap.add_argument('--build-only',action='store_true');a=ap.parse_args();out=ROOT/'build/geos-layout-leaf'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);base,identity=retention.freeze(out,a.fixture);image,report=build(out,base)
 if a.build_only:print((out/'fit.json').read_text());return
 grid.cpu_editor.ROOT=grid.editor_fixture.ROOT=base;grid.cpu_editor.NAMES=grid.editor_fixture.NAMES=identity['names'];dll=grid.runner(out);f=source.Fixture(out,base,dll,True);f.assets['geoslayout-private']=image;cases=[];widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();steps=hits=0
 parent=bytes((i*71+29)&255 for i in range(0x4C))
 def invoke(op):
  reg=f.invoke(op);assert f.read(0x9134,len(parent))==parent,'parent C21 controller clobbered';return reg
 try:
  for encoding,mode,data,start,pan,pending in [(0,0,b'Wide words and CASE\r',0,0,True),(1,0,b'A'*41+b'\r',0,0,False),(1,1,b'A'*90+b'\r',0,17,False),(0,0,b'x'*65540+b'\rHigh text\r',65541,0,False)]:
   f.source(data);merged=data
   if pending:f.position(1);f.key(ord('Q'));merged=data[:1]+b'Q'+data[1:]
   f.claim();f.m.load(0x9134,parent);f.p(1,encoding);f.p(0,mode);f.p(2,320,2);f.p(4,start,3);f.p(7,pan,3);canonical=f.canonical();reu=f.reu();reg=invoke(0);assert not reg.p&1 and reg.a==1
   before=f.read(L,1152)
   for op in [4,5,6]:reg=invoke(op);assert reg.p&1 and reg.a==0xB2 and f.read(L,1152)==before,'active source must reject bands without phase changes'
   for _ in range(len(merged)+100):
    reg=invoke(1);steps+=1;assert not reg.p&1
    if reg.a==0:break
    assert reg.a==1
   adv=[8 if encoding else widths[native(x)] for x in merged];want=line.oracle(merged,adv,start,320,mode,pan,start,0)
   for off,key in [(33,'reason'),(41,'end'),(44,'next'),(35,'x'),(47,'first')]:assert f.q(off,1 if off==33 else 3)==want[key]
   assert [f.q(176+i*2,2) for i in range(f.q(50,2)+1)]==want['maps']
   f.p(30,4,2);assert not invoke(3).p&1
   assert f.canonical()==canonical and f.reu()==reu and not f.get('se_doc_read_locks',1) and not f.m.read(CONTROL+1)
   f.release();cases.append(dict(source=True,encoding=encoding,mode=mode,length=len(merged),pending=pending))
  # Same imported C20 switches to pure authoritative geometry after END.
  f.source(b'geometry source\r');f.claim();f.m.load(0x9134,parent);canonical=f.canonical();reu=f.reu()
  for heights in [[],[9],[9,9],[9,8,9,8],[8]*22,[9]*22]:
   rows=bands.records(heights,0xFFF0);tops,wanted=bands.model(rows,1)
   f.m.load(L,bytes(286));f.p(0,len(rows));f.p(1,1);f.p(2,0xFFFFFF,3)
   raw=b''.join(b''.join(x.to_bytes(3,'little') for x in row[:3])+bytes([row[3]]) for row in rows);f.m.load(L+66,raw);immutable=f.read(L,5)+f.read(L+66,220);reg=invoke(4);assert not reg.p&1 and reg.a==1;packets=[]
   for _ in range(len(rows)+22):
    reg=invoke(5);steps+=1;assert not reg.p&1 and f.read(L,5)+f.read(L+66,220)==immutable
    if f.q(13,1):
     runs=[]
     for i in range(f.q(14,1)):
      idx,y,top,bottom=f.read(L+15+i*4,4);runs.append((idx,y-256 if y&128 else y,top,bottom))
     packets.append((f.q(43,1),runs))
   assert reg.a==0 and packets==wanted and f.q(6,1)
   for y in range(200):
    f.p(23,y);reg=invoke(6);assert not reg.p&1
    got=tuple(f.q(off,w) for off,w in [(24,1),(25,1),(26,1),(36,1),(27,3),(30,3),(33,3)]);assert got==bands.hit_model(rows,tops,y,0xFFFFFF);hits+=1
   assert f.canonical()==canonical and f.reu()==reu;cases.append(dict(bands_heights=heights,strips=len(packets)))
  # Context-valid guard is independent of ACTIVE; no hidden source-frame read.
  f.m.write(CONTROL+1,1);snapshot=f.read(L,1152)
  for op in [4,5,6]:reg=invoke(op);assert reg.p&1 and reg.a==0xB2 and f.read(L,1152)==snapshot
  f.m.write(CONTROL+1,0)
  for owner in [0,1,2,3,255]:
   f.put('se_f_owner',owner,1);snapshot=f.read(L,1152)
   for op in range(7):reg=invoke(op);assert reg.p&1 and reg.a==0xB2 and f.read(L,1152)==snapshot
  f.put('se_f_owner',4,1);f.release()
  # The combined leaf retains load-free cleanup after R14 admission failure.
  f.source(b'cancel source\r');f.claim();f.m.load(0x9134,parent);f.p(2,320,2);f.call('se_doc_read_acquire');assert not invoke(0).p&1;assert not invoke(2).p&1 and f.get('se_doc_read_locks',1)==1
  assert not invoke(0).p&1;idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==14 and f.m.read(f.s['image_slot']+i)==0);f.m.write(f.s['se_overlay_ids']+idx,0);reg=invoke(1);assert reg.p&1 and reg.a==0x17 and f.get('se_doc_read_locks',1)==1
  f.m.write(f.s['se_overlay_ids']+idx,14);f.call('se_doc_read_release');f.release();assert f.read(0xC600,1024)==f.shim
  result=dict(status='passed',identity=identity,payload_bytes=len(image)-36,bands_bytes=839,source_steps_and_geometry_steps=steps,vertical_hits=hits,parent_controller_bytes_preserved=76,new_BSS=0,new_ZP=0,full_REU_guard_bytes=16777216,cases=cases,scope='Actual sealed current-resident C20/R14 source-line and geometry leaf. Parent page-controller/product registration remains separate; no pixels/native/editableGEOS claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()

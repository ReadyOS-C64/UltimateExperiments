"""Private C24 packet preparation; exact original parser/lexer/anchor semantics."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_editor as geos
import test_geos_preview_editor as public
import test_geos_semantic_editor as literal
from test_geos_preview_cache_candidate import Fixture,profiled_runner
from test_geos_fold_editor import tree,TINY
from geos_preview_model import render,FontCatalog,with_chrome
from geos_fold_model import preview
from overlays import wrap
PREVIOUS=ROOT/'build/geos-preview-cache-product/20261025T101910272004Z/fixture'
PRIVATE=ROOT/'src/render/geos/preview-cold-candidate'

def command(*a):
 p=subprocess.run(list(map(str,a)),cwd=ROOT,capture_output=True,text=True)
 assert not p.returncode,(a,p.stdout,p.stderr)

def build(out,previous):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=list(identity['names'])
 inc=out/'includes';inc.mkdir()
 with zipfile.ZipFile(frozen/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and n.endswith('.inc'):
    p=inc/n[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  source=z.read('src/render/geos/semantic.s').decode();block=z.read('src/supermark/block.s');cfg=z.read('cfg/geos-editor-semantic.cfg')
 q=inc/'render/geos/preview-cold-candidate/prepare.inc';q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PRIVATE/'prepare.inc',q)
 candidate=source.replace(' lda F+GSEM_ACTIVE\n jeq state',' lda F+GSEM_ACTIVE\n cmp #2\n jeq gpc_step\n jeq state',1)
 # Original ACTIVE0 check must still be zero, not the CMP2 condition.
 candidate=candidate.replace(' jeq gpc_step\n jeq state',' jeq gpc_step\n lda F+GSEM_ACTIVE\n jeq state',1)
 candidate=candidate.replace('jmp se_gp_preview_complete','jmp gpc_complete')
 candidate+='\n.include "render/geos/preview-cold-candidate/prepare.inc"\n'
 report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];images={};sizes={}
 for name,text in [('control',source),('candidate',candidate)]:
  d=out/name;d.mkdir();(d/'semantic.s').write_text(text);(d/'block.s').write_bytes(block);(d/'leaf.cfg').write_bytes(cfg)
  digest=report['resident_binding']['digest'];(d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  for unit in ['semantic','block']:command('ca65','-g','-I',d,'-I',inc,'-o',d/(unit+'.o'),d/(unit+'.s'))
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',d/'bindings.s',d/'semantic.o',d/'block.o')
  command('ca65','-g','-o',d/'bindings.o',d/'bindings.s')
  command('ld65','-C',d/'leaf.cfg','-o',d/'semantic.bin','-m',d/'semantic.map','-Ln',d/'semantic.lbl',d/'semantic.o',d/'block.o',d/'bindings.o')
  raw=(d/'semantic.bin').read_bytes();sizes[name]=len(raw)
  if name=='control':assert raw==(frozen/'build/overlays/geossema.seo').read_bytes()[36:]
  images[name]=wrap(raw,1,24,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));print('LINK',name,len(raw),flush=True)
 return frozen,identity,s,images,sizes

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--previous',type=Path,default=PREVIOUS);a=p.parse_args()
 out=ROOT/'build/geos-preview-cold-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 frozen,identity,s,images,sizes=build(out,a.previous);print('BUILT',out,flush=True)
 if not a.run:return
 if not (frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
 fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes())
 sourcefonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 dll=profiled_runner(out,s);results=[];pairs={}
 cases=[('diverse',public.DIVERSE),('prefixes',geos.native_text('# One\r## Two\r### Three\r#### Four\r##### Five\r###### Six\r- bullet\r12. numbered\r')),('inline',geos.native_text('Prose **bold** *italic* ***both*** @@code@@.\r£*literal and **open\r')),('long-code',geos.native_text(':::basic\r10 PRINT "'+('ABcd'*60)+'":REM '+('tail '*40)+'\r:::\r')),('long-prose',geos.native_text('Start **'+('many plain words '*40)+'** END\r')),('empty',b''),('trailing-cr',b'Last\r'),('folded',TINY)]
 for label,data in cases:
  for variant,image in images.items():
   f=Fixture(out,frozen,dll,True)
   try:
    f.assets['geossema']=image;f.source(data,physical=256);f.command(99);f.render()
    lb,la,_,_=literal.expected(f,data,sourcefonts)
    assert f.read(0x6000,8000)==lb and f.read(0x4000,1000)==la,(label,variant,'ordinarysourceclient')
    if label=='folded':f.command(115);f.folds=[replace(q,flags=1)for q in tree(data)]
    before=f.canonical();catalog=f.catalog();reu=f.reu();f.command(102);start=f.total_instructions;loads=f.get('se_overlay_loads',2);dll.pc_zero();f.render()
    expected=(preview(data,f.read(s['se_editor_settings'],64),f.folds,catalog=fonts,top=f.get('se_v_top'))if f.folds else render(data,f.read(s['se_editor_settings'],64),catalog=fonts,top=f.get('se_v_top')))
    m,c,rect=geos.grid.logical_ui(f,data);eb,ea=with_chrome(expected.bitmap,expected.attrs,m,c,fonts.native)
    assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(label,variant,'pixels')
    assert f.read(0xcc07,3)==expected.bottom.to_bytes(3,'little')
    assert [int.from_bytes(f.read(s['se_v_rows']+3*i,3),'little')for i in range(len(expected.anchors))]==list(expected.anchors),(label,variant,'rawanchors')
    assert f.canonical()==before and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim and f.get('se_doc_read_locks',1)==0 and f.get('se_f_owner',1)==0
    public.guard_preview_reu(f,reu,f.reu(),label+'-'+variant)
    calls={str(i):dll.pc_calls(i)for i in (14,19,23,24,25,26,27)}
    assert calls['24']>0,'mustmeasurecoldproducer'
    result=dict(case=label,variant=variant,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,calls=calls,anchors=list(expected.anchors),bottom=expected.bottom,bitmap_sha256=hashlib.sha256(eb).hexdigest(),source_bytes=len(data));results.append(result);print('PASS',result,flush=True)
    comparable=(f.read(0x6000,8000),f.read(0x4000,1000),f.read(s['se_v_rows'],66),f.read(0xcc07,3))
    if variant=='control':pairs[label]=comparable
    else:assert comparable==pairs[label],(label,'A/Bcompletepixels/66anchors/bottom')
   except BaseException:
    (out/(label+'-'+variant+'-failure-ram.bin')).write_bytes(f.read(0,65536));raise
   finally:f.close()
 faults=[]
 for fault in ('STOP','missingC24','missingR14','revision','foreign-lease'):
  f=Fixture(out,frozen,dll,True)
  try:
   data=geos.native_text('# Header\r'+('Packet **data** '*15)+'\rLast\r')
   f.assets['geossema']=images['candidate'];f.source(data,physical=256);f.command(99);f.render();f.command(102)
   if fault=='foreign-lease':f.put('se_doc_read_locks',1,1)
   f.call('se_editor_render')
   for _ in range(25000):
    if f.get('se_f_owner',1)==4 and f.m.read(0x8b40+21)==2 and f.m.read(0x9135)==24:break
    f.call('se_editor_service')
   else:raise AssertionError(('packetphaseunreached',fault))
   assert f.get('se_doc_read_locks',1)==(2 if fault=='foreign-lease' else 1)
   before=f.canonical();reu=f.reu();catalog=f.catalog();phase=f.read(0xcc00,67)
   if fault in ('STOP','foreign-lease'):f.queued(3)
   elif fault.startswith('missing'):
    module=24 if fault=='missingC24' else 14;slot=1 if module==24 else 0
    ix=next(i for i in range(s['se_overlay_capacity'])if f.m.read(s['se_overlay_ids']+i)==module and f.m.read(s['image_slot']+i)==slot)
    f.m.write(s['se_overlay_ids']+ix,0);f.m.write(s['se_overlay_active']+slot,0);catalog=f.catalog()
   elif fault=='revision':f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   f.call('se_editor_service')
   assert f.get('se_e_job',1)==0 and f.get('se_f_owner',1)==0 and f.get('se_fs_owned',1)==0 and f.get('se_doc_read_locks',1)==int(fault=='foreign-lease'),(fault,f.debug())
   assert f.canonical()==before and f.reu()==reu and f.catalog()==catalog and f.read(0xc600,1024)==f.shim,(fault,'cancellationchangedsource/REU/catalog')
   faults.append(dict(fault=fault,error=f.get('se_e_error',1),foreign_read_lease_preserved=fault=='foreign-lease',whole_reu_bytes=16777216));print('FAULTPASS',faults[-1],flush=True)
  finally:f.close()
 verification=[Path(__file__),PRIVATE/'prepare.inc',ROOT/'tests/test_geos_preview_cache_candidate.py',ROOT/'tests/test_geos_editor.py',ROOT/'tests/test_grid_modes.py',ROOT/'tests/test_geos_preview_editor.py',ROOT/'tools/geos_preview_model.py',ROOT/'tools/geos_fold_model.py',ROOT/'tools/supermark_model.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py']
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in verification:z.write(p,p.relative_to(ROOT))
 (out/'result.json').write_text(json.dumps(dict(status='passed private C24 packet preparation',identity=identity,sizes=sizes,results=results,faults=faults,limits='Private validSEO C24 replacement; source/nav unchanged guard; no nativecycles/sharedbuild/productedits.'),indent=2)+'\n');print('DONE',out,flush=True)
if __name__=='__main__':main()

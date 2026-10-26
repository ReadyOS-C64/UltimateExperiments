"""Actual source-producer A/B raster substitution; independent pixels + exact FE spans."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
from dataclasses import replace
import test_geos_fold_editor as fold
from geos_fold_model import raster as fold_raster
import test_cache_observer as observer
import test_plain_geos as plain
import test_grid_editor_vice as diverse
import test_geos_raster_probe as candidate
ROOT=observer.ROOT

def run(out,base):
 link,src,s,ls,raw,image,modules=candidate.prepare(out,base,'candidate');g=observer.Gate(out/'gate',base);f=g.f;original=dict(f.assets);cases=[]
 fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
 def full():
  f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
 try:
  sources=[('251-markdown',plain.SOURCE,1,False),('422-markdown',diverse.fixture(),1,False),('422-full',diverse.fixture(),3,False),('styled',observer.geos.native_text('# Heading\rOrdinary ***bold italic*** and @@code@@.\r- List\r:::basic\r10 PRINT "MIX"\rREM tail\r:::\rEnd.'),3,False),('pending',observer.geos.native_text('Plain text and more.\rSecond line.'),3,True)]
  sources += [('selected',observer.geos.native_text('First ***bold*** plus @@code@@ and tail.\rSecond row.'),3,False),('fold-hidden',fold.TINY,3,False),('nested-fold',fold.NESTED,3,False),('nowrap-pan',observer.geos.native_text('***Wide mixed styled line*** '+('Wim. '*65)+'\r:::basic\r10 PRINT \"'+('wide '*12)+'\"\r:::\rtail.'),3,False)]
  for tag,data,caps,pending in sources:
   pair=[]
   for variant in ('control','candidate'):
    f.assets=dict(original)
    if variant=='candidate':f.assets['geosrow']=image
    f.source(data);f.typed(observer.geos.native_text('syntax full'if caps==3 else'syntax markdown'));f.command(99);f.render();source=data
    if pending:f.key(observer.Q);source=bytes([observer.Q])+data;assert f.get('se_hot_pending',1)
    folds=None
    if tag in ('fold-hidden','nested-fold'):
     f.command(115);f.render();folds=[replace(x,flags=1)for x in fold.tree(data)]
     if tag=='fold-hidden':
      f.position(folds[0].hidden-1);f.put('se_sel_anchor',folds[0].end);f.put('se_sel_mark',1,1);f.render()
    if tag=='selected':
     f.position(2);f.put('se_sel_anchor',len(data)-3);f.put('se_sel_mark',1,1);f.render()
    if tag=='nowrap-pan':
     f.command(77)
     for _ in range(3):f.command(75)
     f.render();assert f.get('se_l_mode',1)and f.get('se_l_pan')>0
    before=g.reu();stable=g.stable();start=f.total_instructions;full();used=f.total_instructions-start
    if folds is None:bits,attrs,rows=plain.expected(f,source,fonts,caps)
    else:
     bits,attrs,rows,_=fold_raster(source,fonts,folds,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')if f.get('se_sel_mark',1)else None)
     matrix,colors,popup=observer.geos.grid.logical_ui(f,source);bits,attrs=observer.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
    assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,variant,'independent pixels')
    assert f.merged()==source and stable==g.stable()and f.read(0xC600,1024)==f.shim
    assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
    _,bank=f.raw_cache();after=g.reu();wanted=bytearray(before)
    spans=[(0,64),(0x600,0x680),(0xB200,0xD568),(0xE568,0xEA88),(0xFC00,0xFDA0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
    for lo,hi in spans:wanted[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
    assert wanted==after,(tag,variant,'whole16MiB outside exact FE spans')
    observer.geos.png(bits,attrs,out/(tag+'-'+variant+'.png'));item=dict(tag=tag,variant=variant,instructions=used,bitmap_sha256=hashlib.sha256(bits).hexdigest(),attrs_sha256=hashlib.sha256(attrs).hexdigest());cases.append(item);pair.append(item);print('PASS',tag,variant,used,flush=True)
   assert pair[0]['bitmap_sha256']==pair[1]['bitmap_sha256']and pair[0]['attrs_sha256']==pair[1]['attrs_sha256']
  result=dict(status='PASS',cases=cases,payload=len(raw),candidate_sha256=hashlib.sha256(image).hexdigest(),scope='Actual public source/full-render producer packets; no native claim. Whole16MiB equality outside exact derived FE extents, independent bitmap/attrs, source/pending/history/clip/shim checked.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=candidate.BASE);a=p.parse_args();out=ROOT/'build/geos-raster-public-probe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)

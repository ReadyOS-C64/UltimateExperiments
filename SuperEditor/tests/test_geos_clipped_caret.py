"""Private real C22 clipped-caret proof; independent cell/pixel oracle unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,argparse,importlib.util,ctypes as C,hashlib,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as ob
import test_plain_geos as plain
from supermark_model import blocks
BASE=ROOT/'build/cache-editor-product/20261026T051042908519Z/fixture'

def run(out,base,smoke=False):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes());spec=importlib.util.spec_from_file_location('clippedbuild',ROOT/'src/render/geos/probes/clipped-caret/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seo,budget=b.build(out/'link',base)
 g=ob.Gate(out/'gate',base);f=g.f;fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)}
 original=f.assets['geospaint'];rows=[];traces=[];stage=None;reu_start=None;guards=0
 real_call=f.call
 # All 64 KiB are compared across actual C22 public service calls. These are
 # declared raster/loader/request scratch extents; canonical state is additionally
 # checked independently across the entire public render.
 writable=[(0,0x200),(0x4000,0x43e8),(0x5000,0x7f40),(0x8000,0x9180),(0x9c00,0xc600),(0xca00,0xcc00),(0xdf00,0xdf10)]
 def observe(name,a=0):
  nonlocal guards,reu_start
  active=name=='se_editor_service'and f.get('se_e_job',1)==11 and f.m.read(0x9135)==22
  if active:
   ram=f.read(0,65536)
   if reu_start is None:reu_start=g.reu()
  r=real_call(name,a)
  if active:
   after=f.read(0,65536);cursor=0
   for lo,hi in writable:
    assert after[cursor:lo]==ram[cursor:lo],('C22 undeclared RAM',stage,hex(cursor),hex(lo));cursor=hi
   assert after[cursor:]==ram[cursor:],('C22 undeclared RAMtail',stage,hex(cursor));guards+=1
   if f.m.read(0x9135)!=22 or f.get('se_e_error',1):
    assert g.reu()==reu_start,('C22 changed whole16MiB',stage);reu_start=None
  return r
 f.call=observe
 def render(tag,data,pan,at,anchor,candidate,caps=3,warm=False):
  nonlocal stage
  stage=tag;f.assets['geospaint']=seo if candidate else original
  if not warm:
   f.source(data);f.put('se_status',1,1);f.typed(ob.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(99);f.position(at);f.render()
   f.put('se_sel_mark',int(anchor is not None),1)
   if anchor is not None:f.put('se_sel_anchor',anchor)
   # Explicit caller inputs for odd pixel pan; derived outputs never seeded.
   f.put('se_l_mode',1,1);f.put('se_l_manual',1,1);f.put('se_l_pan',pan);f.put('se_v_top',0)
   f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
  canonical=f.canonical();queue=g.queue();before=g.reu();start=f.total_instructions
  f.render();cost=f.total_instructions-start
  actual=f.read(0x6000,8000)+f.read(0x4000,1000);bits,attrs,expected_rows=plain.expected(f,data,fonts,caps);expected=bits+attrs
  (out/(tag+'-actual.bin')).write_bytes(actual);(out/(tag+'-expected.bin')).write_bytes(expected);(out/(tag+'-source.bin')).write_bytes(data)
  ob.geos.png(actual[:8000],actual[8000:],out/(tag+'.png'))
  raw,bank=f.raw_cache();assert raw[:2]==bytes([1,len(expected_rows)])
  prefix=[]
  for i,row in enumerate(expected_rows):
   rec=raw[0x200+i*0x800:0x220+i*0x800];assert tuple(int.from_bytes(rec[o:o+3],'little')for o in(0,3,6))==(row.start,row.end,row.next)
   assert(rec[14],rec[15])==(row.height,row.top);prefix.append(rec.hex())
  assert f.canonical()==canonical, (tag,'canonical changed')
  assert g.queue()==queue,(tag,'observer changed',queue,g.queue())
  assert f.merged()==data and f.read(0xc600,1024)==f.shim,(tag,'source/shim')
  assert not any(f.get(n,1)for n in('se_e_error','se_e_job','se_f_owner','se_doc_read_locks'))
  if pan:assert f.m.read(0xcf90)==0,(tag,'R27 must keep its conservative nonzero-pan miss')
  after=g.reu();allowed=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]
  ev=blocks(data)
  for i,row in enumerate(expected_rows):
   lo=0x700+i*0x800;rec=after[bank*65536+lo:bank*65536+lo+64]
   if rec==before[bank*65536+lo:bank*65536+lo+64]:continue
   assert rec[:4]==b'C\x02\x40\x01' and rec[7:35]==raw[4:32] and binascii.crc_hqx(rec[:62],65535)==int.from_bytes(rec[62:64],'little')
   event=next((e for e in ev if e['start']==row.start),None)
   nxt=(event['end']+int(event['end']<len(data)and data[event['end']]==13))if event else len(data)
   assert int.from_bytes(rec[4:7],'little')==nxt;allowed.append((lo,lo+64))
  cursor=0
  for lo,hi in sorted((bank*65536+lo,bank*65536+hi)for lo,hi in allowed):
   assert after[cursor:lo]==before[cursor:lo],(tag,'outside declared FE',cursor,lo);cursor=max(cursor,hi)
  assert after[cursor:]==before[cursor:],(tag,'REU tail')
  diffs=[i for i,(x,y)in enumerate(zip(actual,expected))if x!=y]
  entry=dict(tag=tag,candidate=candidate,pan=pan,caret=at,anchor=anchor,caps=caps,instructions=cost,differences=diffs,seen=f.get('se_v_seen',1),row=f.get('se_v_caret_row',1),prefixes=prefix,header=raw[:64].hex());rows.append(entry);print('FRAME',tag,cost,'DIFF',len(diffs),flush=True)
  return diffs
 try:
  cases=[('A-pan1','Alpha ordinary text.\rMiddle line.\r',1,0,None),('A-pan5','Alpha text.\r',5,0,None),('A-hidden','Alpha text.\r',6,0,None),('A-visible','Alpha text.\r',0,0,None),('A-next','Alpha text.\r',1,1,None),('selection-union','Alpha text.\r',1,0,3),('selection-reverse','Alpha text.\r',1,3,0),('empty-CR','\rAfter',1,0,None),('empty-EOF','',1,0,None),('EOF-partial','A',7,1,None),('EOF-hidden','A',11,1,None),('native-code',':::basic\rPRINT "A"\r:::\r',1,9,None),('bold-partial','**Alpha** tail.\r','origin+1',2,None),('italic-partial','*Alpha* tail.\r','origin+1',1,None),('both-partial','***Alpha*** tail.\r','origin+1',3,None),('dot-partial','....tail.\r',1,0,None),('dot-hidden','....tail.\r',2,0,None),('right-partial','.'*160+'A\r',1,160,None),('right-hidden','.'*160+'A\r',0,160,None),('large-pan-hidden','Alpha text.\r',65537,0,None)]
  if smoke:cases=cases[:1]
  for tag,text,pan,at,anchor in cases:
   data=ob.geos.native_text(text)
   if pan=='origin+1':
    model=plain.sem.classify(data);begin=data.rfind(b'\r',0,at)+1
    pan=1+sum(8 if model.code[i] else fonts['bsw9-widths.bin'][ob.geos.native(data[i])]+(model.styles[i]&1)+(model.styles[i]&2)for i in range(begin,at))
   old=render(tag+'-original',data,pan,at,anchor,False)
   oldwarm=render(tag+'-original-warm',data,pan,at,anchor,False,warm=True)
   new=render(tag+'-candidate',data,pan,at,anchor,True)
   newwarm=render(tag+'-candidate-warm',data,pan,at,anchor,True,warm=True)
   assert not newwarm,(tag,'candidate warm independent mismatch',newwarm)
   assert not new,(tag,'candidate independent pixel mismatch',new)
   if tag=='A-pan1':assert old==list(range(640,648))+[960],('preserved original discrepancy',old)
  if not smoke:
   for tag,text,pan,at,anchor in [('plain-partial','Alpha text.\r',1,0,None),('plain-EOF','A',7,1,None),('plain-selection','Alpha text.\r',1,0,3)]:
    data=ob.geos.native_text(text)
    render(tag+'-original',data,pan,at,anchor,False,caps=0)
    assert not render(tag+'-candidate',data,pan,at,anchor,True,caps=0)
  # Wrong owners refuse before phase/pixels/REU, using actual capsule entry.
  owner_faults=[]
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1)
   for op in (0,1,2):
    f.put('se_overlay_frame',op,1);phase=f.read(0x8000,0x1180);pixels=f.read(0x4000,1000)+f.read(0x6000,8000);reu=g.reu();stable=f.canonical()
    r,n=f.fast_call(f.s['se_overlay_call'],a=22,x=1);assert r.p&1 and r.a==0xb2
    assert f.read(0x8000,0x1180)==phase and f.read(0x4000,1000)+f.read(0x6000,8000)==pixels and g.reu()==reu and f.canonical()==stable
    owner_faults.append((owner,op))
  f.put('se_f_owner',0,1)
  recovery=[]
  if not smoke:
   data=ob.geos.native_text('Alpha ordinary text.\rMiddle line.\r')
   for fault in ('queuedSTOP','missingR21'):
    assert not render(fault+'-setup',data,1,0,None,True)
    f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1)
    f.call('se_editor_render')
    for _ in range(25000):
     if f.get('se_e_job',1)==11 and f.m.read(0x9135)==22 and f.m.read(0x9136)==1 and f.m.read(0x8b43)==7:break
     f.call('se_editor_service')
    else:raise AssertionError('did not reach real C22/R21 draw boundary')
    before=g.reu();stable=f.canonical();q=g.queue()
    if fault=='queuedSTOP':
     tail=f.get('se_input_tail',1);f.queued(3);f.call('se_editor_service')
     assert f.get('se_input_tail',1)==((tail+1)&63) and not f.get('se_f_owner',1) and not f.get('se_e_job',1)
     assert g.reu()==before and f.canonical()==stable and g.queue()==q
     f.tick();f.settle()
    else:
     idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==21 and f.m.read(f.s['image_slot']+i)&1==0)
     a=f.s['se_overlay_ids']+idx;old=f.m.read(a);f.m.write(a,255);f.call('se_editor_service')
     assert f.get('se_e_error',1)==0x17 and not f.get('se_f_owner',1) and not f.get('se_e_job',1)
     assert g.reu()==before and f.canonical()==stable and g.queue()==q
     f.m.write(a,old);f.key(3)
    assert not render(fault+'-recovered',data,1,0,None,True,warm=True)
    recovery.append(fault)
  previews=[]
  if not smoke:
   import zipfile
   from test_geos_preview_editor import guard_preview_reu
   from geos_preview_model import FontCatalog,render as preview_model,with_chrome
   with zipfile.ZipFile(g.frozen/'product-sources.zip')as z:
    contract=z.read('src/render/geos/preview-glyph-cache.inc')
    for v in (b'PGC_VERSION=3',b'PGC_BASE=$EB69',b'PGC_END=$FBA9',b'PGC_BYTES=4160'):assert v in contract
   assert len(f.assets['geosfontrow'])-36==4095
   f.glyph_cache_span=(0xEB69,0xFBA9);catalog=FontCatalog(native=fonts['native8.bin'])
   data=ob.geos.native_text('**Alpha** *italic* and tail.\r:::basic\rPRINT 1\r:::\r')
   for use in (False,True):
    f.assets['geospaint']=seo if use else original;f.source(data);f.put('se_status',1,1);f.command(99);f.render();f.put('se_l_mode',1,1);f.put('se_l_manual',1,1);f.put('se_l_pan',1)
    stable=f.canonical();q=g.queue();before=g.reu();count=guards;start=f.total_instructions;f.command(102);f.render();cost=f.total_instructions-start
    assert f.get('se_r_presentation',1)==1 and f.get('se_e_ui',1)==4 and guards==count,'preview must not call C22'
    model=preview_model(data,f.read(f.s['se_editor_settings'],64),catalog=catalog,top=f.get('se_v_top'))
    matrix,colors,popup=ob.geos.grid.logical_ui(f,data);assert popup is None
    bits,attrs=with_chrome(model.bitmap,model.attrs,matrix,colors,fonts['native8.bin'])
    actual=f.read(0x6000,8000)+f.read(0x4000,1000);assert actual==bits+attrs
    assert f.canonical()==stable and g.queue()==q and f.merged()==data and f.read(0xc600,1024)==f.shim
    evidence=guard_preview_reu(f,before,g.reu(),'preview')
    tag='preview-'+('candidate'if use else'original');ob.geos.png(bits,attrs,out/(tag+'.png'));(out/(tag+'-actual.bin')).write_bytes(actual)
    previews.append(dict(tag=tag,instructions=cost,sha256=hashlib.sha256(actual).hexdigest(),REU=evidence,no_C22_calls=True))
   assert previews[0]['sha256']==previews[1]['sha256']
  result=dict(recovery=recovery,previews=previews,owner_faults=owner_faults,status='PASS-private-clipped-caret',fixture=g.identity,budget=budget,frames=rows,whole64KiB_C22_calls_guarded=guards,whole16MiB_C22_readonly=True,source_history_queue_shim=True,scope='Actual public source/mode/presentation/layout/render with only C22 capsule substitution. Pan/manual and selection/caret inputs explicit; no semantic/layout output seeds. Independent oracle unchanged. CPU only.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException as e:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure.json').write_text(json.dumps(dict(error=repr(e),stage=stage,frames=rows),indent=2)+'\n');raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-clipped-caret'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve(),a.smoke);print('RESULT',r['status'],len(r['frames']),r['budget'])

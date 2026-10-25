"""Private actual-R14 bounded packet sink fed from real public preview workers."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,sys,zipfile,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_editor as geos
import test_geos_preview_editor as public
from test_geos_preview_cache_candidate import Fixture,profiled_runner,command
from overlays import wrap
from geos_preview_model import render,FontCatalog,with_chrome,_inline
from supermark_model import blocks
PREVIOUS=ROOT/'build/geos-preview-cache-product/20261025T101910272004Z/fixture'
SINK=ROOT/'src/render/geos/preview-cold-candidate/packet/sink.s'

def build(out):
 frozen,identity=geos.freeze(out,PREVIOUS);inc=out/'includes';inc.mkdir()
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 with zipfile.ZipFile(frozen/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and n.endswith('.inc'):
    p=inc/n[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  sources={'entry':z.read('src/overlays/source-view.s').decode(),'context':z.read('src/fold/source-context.s').decode(),'read':z.read('src/fold/source-read.s').decode()};cfg=z.read('cfg/source-r.cfg')
 report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];seal=report['resident_binding']['digest'];images={};sizes={}
 for variant in ('control','candidate'):
  d=out/variant;d.mkdir();(d/'leaf.cfg').write_bytes(cfg)
  (d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  units=dict(sources)
  if variant=='candidate':
   units['entry']=units['entry'].replace('.import se_fs_begin,se_fs_guard,se_fs_read','.import se_fs_begin,se_fs_guard,se_fs_read,se_gpk_begin,se_gpk_step,se_gpk_cancel')
   units['entry']=units['entry'].replace('    lda #$B0','    cmp #3\n    beq packet_begin\n    cmp #4\n    beq packet_step\n    cmp #5\n    beq packet_cancel\n    lda #$B0')+'\npacket_begin:jmp se_gpk_begin\npacket_step:jmp se_gpk_step\npacket_cancel:jmp se_gpk_cancel\n'
   units['sink']=SINK.read_text()
  objects=[]
  for n,text in units.items():
   (d/(n+'.s')).write_text(text);obj=d/(n+'.o');command('ca65','-g','-I',d,'-I',inc,'-o',obj,d/(n+'.s'));objects.append(obj)
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',d/'bindings.s',*objects)
  command('ca65','-g','-o',d/'bindings.o',d/'bindings.s')
  command('ld65','-C',d/'leaf.cfg','-o',d/'source.bin','-m',d/'source.map','-Ln',d/'source.lbl',*objects,d/'bindings.o')
  raw=(d/'source.bin').read_bytes();sizes[variant]=len(raw)
  if variant=='control':assert raw==(frozen/'build/overlays/viewsource.seo').read_bytes()[36:]
  images[variant]=wrap(raw,0,14,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));print('LINK',variant,len(raw),flush=True)
 return frozen,identity,s,images,sizes

def wire_oracle(f,data):
 p=f.get('se_v_top');q=int.from_bytes(f.read(0xcc30,3),'little');count=f.m.read(0xcc0f)
 ev=next((e for e in blocks(data)if e['start']<=q<=e['end']),None)
 if ev is None:ev=dict(start=len(data),end=len(data),body=len(data),kind=1,language=0,level=0,marker=0)
 hidden,styles,roles=_inline(data,ev);base=2 if ev['kind']==2 else 1 if ev['kind']==3 else 4 if ev['kind']in(4,5,6) else 0
 source=data[q:q+count]+bytes(160-count)
 style=bytes(styles.get(i,0)for i in range(q,q+count))+bytes(160-count)
 role=bytes(roles.get(i,base)for i in range(q,q+count))+bytes(160-count)
 mask=bytearray(20)
 for i in range(count):
  if q+i in hidden:mask[i//8]|=128>>(i%8)
 # Metadata is independently checked against canonical event fields below;
 # profile bytes are caller settings input, never product glyph/layout output.
 prefix=bytes((ev['kind'],ev['language'],ev['level'],(ev['body']-ev['start']) if ev['body']-ev['start']<=255 else 0))+b''.join(ev[k].to_bytes(3,'little')for k in ('start','end','body'))+bytes((base,int(ev['kind']==2),8 if ev['kind']==5 else 9))
 anchor=f.read(0xcc01,3);profile=f.read(0xcc19,7);index=f.m.read(0xcc11);code=int(ev['kind']==5)
 header=prefix+q.to_bytes(3,'little')+bytes((count,))+anchor+profile+bytes((index,code|(128 if f.m.read(0xcc0d)==0 else 0)))
 assert len(header)==32
 payload=header+source+style+role+bytes(mask)
 return payload+binascii.crc_hqx(payload,0xffff).to_bytes(2,'little')

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args();out=ROOT/'build/geos-preview-packet-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 frozen,identity,s,images,sizes=build(out);print('BUILT',out,flush=True)
 if not a.run:return
 if not (frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
 fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes());dll=profiled_runner(out,s);results=[]
 f=Fixture(out,frozen,dll,True)
 try:
  for label,data in [('diverse',public.DIVERSE),('long-windows',geos.native_text('# Head\r**'+('Aa '*70)+'** end\r:::basic\r10 PRINT \"'+('ABcd'*60)+'\":REM tail\r:::\rLast\r'))]:
   packet_index=0
   f.assets['viewsource']=images['candidate'];f.source(data,physical=256);f.command(99);f.render();f.command(102);f.call('se_editor_render');seen=set()
   for _ in range(25000):
    if not f.get('se_e_job',1):break
    phase=f.m.read(0xcc00);q=int.from_bytes(f.read(0xcc30,3),'little');token=(q,phase)
    ready=f.m.read(0x9135)==27 and ((phase==3 and f.m.read(0x8e84)==0)or(phase==4 and f.m.read(0x8d3c)==0))
    if ready and token not in seen:
     seen.add(token);wire=wire_oracle(f,data);dest=0xb200+packet_index*534;packet_index+=1
     canonical=f.canonical();reu=f.reu();body=f.read(0x6000,8000);attrs=f.read(0x4000,1000);catalog=f.catalog();pp=f.read(0xcc00,67)
     f.m.load(0xcc50,bytes([0xA5])*17);f.m.write(0xcc50,0) #explicit caller phase initialization
     f.m.load(0xcc59,dest.to_bytes(2,'little'));dll.pc_zero();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
     f.put('se_overlay_frame',3,1);r,n=f.fast_call(s['se_overlay_call'],14,0);f.total_instructions+=n;used=[n];assert not r.p&1,('begin',r.a)
     steps=0
     while not f.m.read(0xcc5c):
      f.put('se_overlay_frame',4,1);r,n=f.fast_call(s['se_overlay_call'],14,0);f.total_instructions+=n;used.append(n);steps+=1;assert not r.p&1,('step',r.a)
      assert steps<=5
     bank,physical=f.raw_cache();assert bank[dest:dest+534]==wire,('wire',q,[(i,a,b)for i,(a,b)in enumerate(zip(bank[dest:dest+534],wire))if a!=b][:12])
     after=f.reu();b=physical*65536+dest;assert after[:b]==reu[:b]and after[b+534:]==reu[b+534:]
     assert f.canonical()==canonical and f.catalog()==catalog and f.read(0x6000,8000)==body and f.read(0x4000,1000)==attrs and f.read(0xcc00,67)==pp and f.read(0xc600,1024)==f.shim and f.get('se_doc_read_locks',1)==0
     result=dict(case=label,maximum_call_instructions=max(used),query=q,count=wire[19],steps=steps,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,destination=dest,packet_sha256=hashlib.sha256(wire).hexdigest());results.append(result);print('PACKET',result,flush=True)
    f.call('se_editor_service')
   else:raise AssertionError('rootdidnotfinish')
   expected=render(data,f.read(s['se_editor_settings'],64),catalog=fonts,top=f.get('se_v_top'));m,c,_=geos.grid.logical_ui(f,data);eb,ea=with_chrome(expected.bitmap,expected.attrs,m,c,fonts.native)
   assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea and f.merged()==data
 finally:f.close()
 (out/'result.json').write_text(json.dumps(dict(status='passed packet-sink feasibility only',identity=identity,sizes=sizes,packets=results,limits='No staged producer cursor/layout/consumer integration; no nativecycles/end-to-end gain. Actual public source/semantic/inline/lexer/font pipeline continued after each sink.'),indent=2)+'\n');print('DONE',out,flush=True)
if __name__=='__main__':main()

"""Actual coherent private publication hook, no host AUX calls/substitutions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,sys,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c
from redraw_model import Screen,verify_screen

def freeze_project(out,project):
 old,oldret,oldfile=c.geos.ROOT,c.geos.retention.ROOT,c.geos.__file__
 (project/'tests').mkdir(exist_ok=True)
 if Path(oldfile).resolve()!=(project/'tests/test_geos_editor.py').resolve():shutil.copy2(oldfile,project/'tests/test_geos_editor.py')
 try:
  c.geos.ROOT=c.geos.retention.ROOT=project;c.geos.__file__=str(project/'tests/test_geos_editor.py');return c.geos.freeze(out)
 finally:c.geos.ROOT,c.geos.retention.ROOT,c.geos.__file__=old,oldret,oldfile

def run(out,project,smoke=False):
 frozen,identity=freeze_project(out,project);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};frames=[];data=b''
 def profile():
  idx=next((i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==13 and f.m.read(f.s['image_slot']+i)&0x7f==1),-1);dll.gm_profile(f.s['se_overlay_active']+1,idx+1,0,0xb010,0xb011,0,0)
 def clean():assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in['se_e_error','se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks','se_e_draw_busy']),f.debug()
 def outside(before,tag):
  mode=f.get('se_mode',1)
  if mode==3:return c.outside_cache(f,before,tag)
  after=f.reu()
  if mode==0:assert after==before,(tag,'text40wholeREU');return
  cache,bank=f.raw_cache();start=bank*65536;cursor=0
  # Integrated SP2 owns precisely128 further bytes, not the rest of this bank.
  sp2=(start+0x1600,start+0x1680)
  if after[sp2[0]:sp2[1]]!=before[sp2[0]:sp2[1]]:
   cert=after[sp2[0]:sp2[1]]
   assert cert[:4]==b'SP\2\xa5'and binascii.crc_hqx(cert[:126],65535)==int.from_bytes(cert[126:],'little'),(tag,'SP2 record')
  for a,b in[(start,start+22*240),(start+0x1500,start+0x1680)]:assert after[cursor:a]==before[cursor:a],(tag,'narrowforeign',cursor,a);cursor=b
  assert after[cursor:]==before[cursor:],(tag,'narrowtail')
 def check(tag,refresh=None):
  canonical=f.canonical();catalog=f.catalog();before=f.reu();start=f.total_instructions;profile();f.events=[];f.trace=True;f.render();f.trace=False;used=f.total_instructions-start;calls=dll.gm_metric(0)
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data,(tag,'canonical/source/catalog');clean();outside(before,tag)
  if f.get('se_mode',1)==3:
   bits,attrs,rows=c.exact_pixels(f,data,fonts,tag);cache,_=f.raw_cache()
   if refresh is not None:assert calls==int(refresh),(tag,'actual-hookcalls',calls,refresh)
   if refresh:
    for offset in([0x600,0x640]if f.get('se_v_top')else[0x600]):
     r=cache[offset:offset+64];assert r[3]==1 and int.from_bytes(r[24:28],'little')==f.get('se_r_revision',4)and int.from_bytes(r[28:31],'little')==len(data),(tag,'fresh-pair',offset,r.hex())
  else:
   if f.get('se_st_request',1)==1:f.finish_style();f.render()
   wanted,anchors,seen,rect=c.geos.grid.expected(f,data)
   if f.get('se_mode',1):assert f.read(0x6000,8000)==wanted[0]and f.read(0x4000,1000)==wanted[1],(tag,'narrowpixels');bits,attrs=wanted
   else:
    verify_screen(f.read(0x4000,1000),f.read(0xd800,1000),Screen(*wanted,anchors,seen),tag=tag);bits=bytearray(8000);attrs=bytearray(1000)
    for i,(glyph,ink)in enumerate(zip(*wanted)):
     row,col=divmod(i,40);bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if glyph&128 else 0)for v in fonts['native8.bin'][(glyph&127)*8:(glyph&127)*8+8]);attrs[i]=(ink&15)*16+6
   actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(22))+(f.get('se_v_bottom'),);assert actual==anchors,(tag,'allanchors')
   assert f.canonical()==canonical and f.catalog()==catalog;outside(before,tag+'-style');clean()
  if bits is not None:c.geos.png(bits,attrs,out/(tag+'.png'))
  entry=dict(tag=tag,mode=f.get('se_mode',1),instructions=used,AUX_calls=calls,AUX_inclusive_instructions=dll.gm_metric(1),source_bytes=len(data),revision=f.get('se_r_revision',4),TOP=f.get('se_v_top'),queries=f.events);frames.append(entry);print('PASS',{k:v for k,v in entry.items()if k!='queries'},flush=True);(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def setup(far,row):
  nonlocal data
  pre=c.geos.native_text('prefix\r')*(9400 if far else 0);suffix=c.geos.native_text('# Heading words.\rSecond plain row.\rThird plain row.\rTail.');data=pre+suffix;top=len(pre);f.source(data);f.command(99);f.position(top);f.render();f.position(top+[5,22,40][row]);f.render();assert f.get('se_v_top')==top
 try:
  for far in([False]if smoke else[False,True]):
   for row in([1]if smoke else[0,1,2]):
    setup(far,row)
    for serial,key in enumerate([c.geos.native_text('Q')[0],c.geos.native_text('R')[0],0x14,0x14,13]):
     at=f.get('se_hot_caret');data=data[:at-1]+data[at:]if key==0x14 else data[:at]+bytes([key])+data[at:];f.key(key);check(('far'if far else'near')+'-row'+str(row)+'-'+str(serial),True)
    check(('far'if far else'near')+'-row'+str(row)+'-readonly',False)
  if not smoke:
   # Full mode routes and exactnative40/narrow/GEOS source/undo/redo/selection.
   original=c.geos.native_text('Simple words.\rNext row.\rTail.');f.source(original);data=original
   for mode in range(4):
    f.command(96+mode);f.position(5);check('mode'+str(mode)+'-initial')
    at=f.get('se_hot_caret');data=data[:at]+c.geos.native_text('Q')+data[at:];f.key(c.geos.native_text('Q')[0]);check('mode'+str(mode)+'-insert')
    f.command(16);data=original;check('mode'+str(mode)+'-undo');f.command(17);data=original[:5]+c.geos.native_text('Q')+original[5:];check('mode'+str(mode)+'-redo')
    f.position(5);f.command(68);f.command(1);f.command(1);check('mode'+str(mode)+'-reverse-selection')
    lo,hi=sorted((f.get('se_sel_anchor'),f.get('se_hot_caret')));clip=data[lo:hi];f.command(69);assert f.get('se_clip_length')==len(clip);f.command(50);f.position(len(data));f.command(71);data=data+clip;check('mode'+str(mode)+'-paste');f.command(16);data=data[:-len(clip)];check('mode'+str(mode)+'-paste-undo')
    # Restore the exact common document through actual Undo/commands rather
    # than a host source replacement between mode roundtrips.
    f.command(16);data=original;check('mode'+str(mode)+'-restored')
   # Missing optional refresh components cannot reject an already painted
   # actual localedit. Restore the catalog then actual Undo must still work.
   for missing,slot in[(13,1),(14,0)]:
    setup(False,2);at=f.get('se_hot_caret');data=data[:at]+c.geos.native_text('Q')+data[at:];f.key(c.geos.native_text('Q')[0]);idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==missing and f.m.read(f.s['image_slot']+i)&0x7f==slot);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0);check('optional-missing-'+str(missing));f.m.write(f.s['se_overlay_ids']+idx,missing);f.command(16);data=data[:at]+data[at+1:];check('optional-missing-'+str(missing)+'-undo')
   # An occasional lowbyte gate collision loads AUX, but the full sequence
   # guard rejects the stale event and never modifies checkpoint authority.
   setup(False,2);at=f.get('se_hot_caret');data=data[:at]+c.geos.native_text('Q')+data[at:];f.key(c.geos.native_text('Q')[0]);check('lowbyte-collision-initial',True);cache,_=f.raw_cache();pair=cache[0x600:0x680];canonical=f.canonical();profile()
   for i in range(256):f.render();assert f.canonical()==canonical and f.raw_cache()[0][0x600:0x680]==pair
   assert dll.gm_metric(0)==1,('lowbyte-collision-calls',dll.gm_metric(0));c.exact_pixels(f,data,fonts,'lowbyte-collision-final');clean()
   # Direct invalidmode seam must retain old no-overlay publication semantics.
   f.put('se_mode',4,1);before=f.reu();canonical=f.canonical();catalog=f.catalog();calls=f.get('se_overlay_calls',2);seq=f.get('se_e_draw_sequence',2);r=f.call('se_er_published');assert not r.p&1 and r.a==0 and f.get('se_overlay_calls',2)==calls and f.get('se_e_draw_sequence',2)==(seq+1)&65535 and f.reu()==before and f.canonical()==canonical and f.catalog()==catalog;f.put('se_mode',3,1)
  result=dict(status='passed',identity=identity,frames=frames,scope='Actualcoherentprivate resident/AUX/C21/C20 hook throughpublicrender; nohostAUXcalls/overlay substitutions. All4modes/source/history/selection/clipboard and exactpixels/anchors/catalog/shim/full16MiB declaredspans; invalidmode>=4 preservesnooverlay. CPUonly; matchingnativeBASICidlelog/absolute stack not yetcaptured.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-refresh-hook-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.project.resolve(),a.smoke);print('RESULT',r['status'],'frames',len(r['frames']))

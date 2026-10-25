"""Public-root incremental edit versus forced full producer and canonical oracle.

No candidate overlay substitutions. The comparison editor disarms only the
single-edit optimization certificate, so its actual full producer is a second
reference alongside the independent source/font pixel oracle.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,ctypes as C,zipfile
import test_geos_semantic_editor as semantic
geos=semantic.geos;ROOT=geos.ROOT
GEC=0xCFE8;FAST=0x9148;STATE=0x9149

def run(out,previous=None):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);g=geos.Fixture(out,frozen,dll,True)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 frames=[]
 with zipfile.ZipFile(frozen/'product-sources.zip')as z:
  contract=z.read('src/render/geos/edit-cache.inc');classes=b'GEX_CLASS=' in contract;heading_prefix=b'GEX_HEADING_CLASS=2' in contract;heading_body=b'GEX_HEADING_BODY_CLASS=4' in contract
 def whole_reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def setup(data,at):
  for x in(f,g):
   x.source(data);x.command(99)
   for _ in range(at):assert not x.call('se_hot_call',7).p&1
   x.render()
 def check(tag,incremental):
  canonical=f.canonical();before=f.total_instructions;g_before=g.total_instructions;reu=whole_reu()
  # A successful post-publication checkpoint refresh can leave R14 active.
  # Observe the actual renderer at publication, before that hook. Merely entering
  # R30/R31 is insufficient: a refused attempt must still count as a fallback.
  indices=[i+1 for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)in(30,31)and f.m.read(f.s['image_slot']+i)&0x7f==0]
  if indices:
   assert len(indices)==2
   published=f.s['se_er_published']
   dll.gm_profile(f.s['se_overlay_active'],*indices,published,0,published,0)
  f.render();direct_calls=dll.gm_metric(0)if indices else 0
  dll.gm_profile(0,0,0,0,0,0,0)
  g.m.write(GEC,0);g.render()
  direct=bool(direct_calls)
  assert (direct or f.m.read(FAST)==2) if incremental else (not direct and f.m.read(FAST)==0),(tag,'path',direct,f.m.read(FAST),f.read(STATE,47).hex())
  data=f.merged();assert data==g.merged() and f.canonical()==canonical
  eb,ea,_,_=semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==eb,(tag,'independent bitmap')
  assert f.read(0x4000,1000)==ea,(tag,'independent attributes')
  assert f.read(0x6000,8000)==g.read(0x6000,8000) and f.read(0x4000,1000)==g.read(0x4000,1000),(tag,'full producer')
  assert f.read(0xC600,1024)==f.shim
  actual=whole_reu();handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle);base=bank*65536
  assert handle and bank and f.m.read(f.s['se_reu_logical_owner']+handle)==0xFE and f.m.read(f.s['se_reu_physical_owner']+bank)==0xFE
  cursor=0
  for a,b in [(base,base+64),(base+0x200,base+0xE568)]:
   assert actual[cursor:a]==reu[cursor:a],(tag,'REU outside declared FE spans',cursor,a)
   cursor=b
  assert actual[cursor:]==reu[cursor:],(tag,'REU after FE transaction span')
  geos.png(eb,ea,out/(tag+'.png'))
  frames.append(dict(tag=tag,incremental=incremental,direct_typing=direct,direct_entry_calls=direct_calls,render_instructions=f.total_instructions-before,full_render_instructions=g.total_instructions-g_before,first_strip=f.m.read(STATE+5),end_strip=f.m.read(STATE+6),source_bytes=len(data)))
  print('PASS',frames[-1],flush=True)
 try:
  plain=geos.native_text('Ordinary text here.\rSecond source line.\rThird source line.\rLast.')
  for tag,at,command,byte in [('insert',5,None,geos.native_text('Q')[0]),('backspace',5,None,0x14),('forward-delete',5,4,None),('second-row',25,None,geos.native_text('j')[0]),('eof-row',len(plain)-2,None,geos.native_text('Q')[0])]:
   setup(plain,at)
   for x in(f,g):x.command(command)if command else x.key(byte)
   check(tag,True)
  widths=fonts['bsw9-widths.bin'];line=geos.native_text('Ordinary ')
  while sum(widths[geos.native(v)] for v in line)+widths[geos.native(geos.native_text('W')[0])]<=320:
   line+=geos.native_text('W')
  setup(line+geos.native_text('\rFollowing line.'),5)
  for x in(f,g):x.key(geos.native_text('W')[0])
  check('fallback-new-wrap',False)
  # Repeated publication must re-arm C6, while following cached rows' positions
  # and caret movement remain consistent after each insertion/deletion.
  setup(plain,5)
  for i in range(4):
   for x in(f,g):x.key(geos.native_text('i')[0]if i%2==0 else 0x14)
   check('repeat-'+str(i),True)
  mixed=geos.native_text('# Heading\rOrdinary prose here.\rPlain **bold** text.\r:::basic\r10 PRINT "Hi"\r:::\rTail.')
  for tag,at,byte in [('heading',4,81),('inline',mixed.index(b'**')+3,81),('basic',mixed.index(geos.native_text('PRINT'))+2,81),('linebreak',18,13),('prefix',0,81)]:
   setup(mixed,at)
   for x in(f,g):x.key(byte)
   eligible=(classes and tag in ('inline','basic'))or(heading_prefix and tag=='prefix')or(heading_body and tag=='heading')
   check(('dirty-'if eligible else'fallback-')+tag,eligible)
  result=dict(status='passed',identity=identity,frames=frames,pixels_checked=len(frames)*64000,attributes_checked=len(frames)*1000,scope='Actual packaged public root/C6/C21/R28/C22. Comparison editor only disarms GEC; independent canonical source/font oracle. CPU transport seams, no native timing claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);a=p.parse_args();out=ROOT/'build/geos-incremental-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)

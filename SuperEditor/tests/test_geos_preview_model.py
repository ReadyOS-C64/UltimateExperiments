"""Independent host preview oracle gate; never builds/runs editor products."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from geos_preview_model import FontCatalog,render,profiles,screen,with_chrome
from redraw_model import native_text
from fonts import png

OUT=ROOT/'build/geos-preview-model'


def encode(ps):
 b=bytearray(b'SEST'+bytes((1,64,8,7)))
 for p in ps:b+=bytes((p.origin,p.family&255,p.family>>8,p.point,p.foreground,p.background,p.styles))
 return bytes(b)


def main():
 OUT.mkdir(exist_ok=True);settings=(ROOT/'build/editor-settings/editor-defaults.bin').read_bytes();ps=profiles(settings);fonts=FontCatalog();cases=0
 def check(text,table=settings,**kw):
  nonlocal cases
  data=native_text(text) if isinstance(text,str) else bytes(text);before=data;r=render(data,table,catalog=fonts,**kw)
  assert data==before and len(r.bitmap)==8000 and len(r.attrs)==1000
  assert len(r.rows)<=22 and 0<=r.bottom<=len(data)
  assert r.anchors==tuple(row.start for row in r.rows)
  assert all(row.top%8==0 and row.height%8==0 and 16<=row.top<row.top+row.height<=192 for row in r.rows)
  assert list(r.anchors)==sorted(r.anchors) and all(0<=a<=len(data) for a in r.anchors)
  assert all(not any(r.bitmap[y*320:(y+1)*320]) for y in (0,1,24))
  cases+=1;return r
 empty=check(b'');assert empty.anchors==(0,) and empty.bottom==0 and not any(empty.bitmap)
 for level in range(1,7):
  r=check('#'*level+' Title');assert r.rows[0].profile==level and r.rows[0].glyph_sources[0]==level+1
  assert all(v==0x76 for v in r.attrs[80:120])
 for text,prefix in [('- bullet',2),('* bullet',2),('1. number',3),('  - indent',4),('123. number',5)]:
  a=check(text);b=check(text,keep_list_prefix=False);assert a.rows[0].glyph_sources[0]==0 and b.rows[0].glyph_sources[0]==prefix
 escaped=check('\\# literal');assert escaped.rows[0].profile==0 and escaped.rows[0].glyph_sources[0]==1
 hidden=check('**B** *I* ***BI*** @@C@@ \\*');at=hidden.rows[0].glyph_sources
 data=native_text('**B** *I* ***BI*** @@C@@ \\*');assert bytes(data[i] for i in at)==native_text('B I BI C *')
 unmatched=check('**open @@plain');assert unmatched.rows[0].glyph_sources==tuple(range(len(native_text('**open @@plain'))))
 region=check(':::REGION Name\rText\r:::END\r');assert region.anchors==(0,15,27) and region.rows[0].glyph_sources==tuple(range(10,14))
 title=check(':::REGION **Group**\rItem\r:::END\r');assert title.rows[0].glyph_sources==tuple(range(12,17))
 fence=check(':::BASIC\r10 PRINT 1\r:::\rTail');assert fence.anchors==(9,24) and fence.rows[0].profile==7
 # Native code exactly40chars fillsoneband;41st consumesanewcanonicalrow.
 r=check(':::BASIC\r'+'A'*81+'\r:::\r');assert r.anchors[:3]==(9,49,89)
 assert [x.height for x in r.rows[:3]]==[8,8,8]
 # Character wrapping isnotwordwrapping; canonicalsoftrowanchors are exact.
 a=check('W'*200);assert len(a.rows)>1 and all(row.start==a.rows[i-1].end for i,row in enumerate(a.rows) if i)
 exact=check(':::BASIC\r'+'A'*1000);assert len(exact.rows)==22 and exact.bottom==9+880
 longdata=native_text('Plain **bold** and @@code@@.\r')*3000
 big=check(longdata,top=65550);assert big.anchors[0]==65550
 # Firstinkpolicy: changinglaterglyphfgmustnotreplace firstclaiminsharedtile.
 custom=list(ps);custom[0]=replace(custom[0],foreground=2,background=0);custom[7]=replace(custom[7],foreground=5,background=7)
 r=check('i@@i@@',encode(custom));assert r.attrs[80]==0x20 and r.attrs[81]>>4 in (2,5)
 # Allgenuineface/size records; native fallback and allB/I/U combinations.
 selected=[key for key in fonts.faces if key[0]==1]
 for key in selected:
  for style in range(8):
   table=list(ps);table[0]=replace(table[0],origin=key[0],family=key[1],point=key[2],styles=style,foreground=(style+1)%16,background=style%16)
   r=check('Agjmpq W. **bold** *italic* @@CODE@@\r- List',encode(table))
   assert r.rows[0].baseline>=fonts.faces[key].baseline
 # RealmonospaceCommodore10 plusstyles: codeadvance stays8,height10->band16.
 table=list(ps);table[7]=replace(table[7],origin=1,family=26,point=10,styles=7)
 r=check(':::ASM\r'+'A'*41,encode(table));assert r.anchors==(7,47) and r.rows[0].height==16
 # Invalidsettings cannot silentlychooseanotherface/size.
 invalid=[]
 for offset,value in [(0,0),(4,2),(8,2),(12,16),(14,8)]:
  b=bytearray(settings);b[offset]=value;invalid.append(bytes(b))
 unavailable=list(ps);unavailable[0]=replace(unavailable[0],origin=1,family=2,point=24);invalid.append(encode(unavailable))
 for b in invalid:
  try:render(b'A',b,catalog=fonts)
  except ValueError:pass
  else:raise AssertionError('invalidsettingsaccepted')
 # Sharedchrome copiesexactnormal128glyphfont+explicitinverse,andonly3rows.
 r=check('Body');matrix=bytes([65])*1000;colors=bytes([7])*1000
 bits,attrs=with_chrome(r.bitmap,r.attrs,matrix,colors,fonts.native)
 assert bits[640:7680]==r.bitmap[640:7680] and attrs[80:960]==r.attrs[80:960]
 assert attrs[:80]==bytes([0x76])*80 and attrs[960:]==bytes([0x76])*40
 result=dict(status='passed',host_cases=cases,genuine_face_style_cases=len(selected)*8,malformed_settings=len(invalid),source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('tools/geos_preview_model.py','tests/test_geos_preview_model.py')},scope='Independenthostsource/font/settings/pixel/geometryoracle. Noactualeditor/nativegateclaim.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

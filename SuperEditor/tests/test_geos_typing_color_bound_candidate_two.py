"""Private actual6510 conditional ink-bound admission; canonical guard untouched."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys,shutil,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
from geos_packet import rows
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
F=0x8a00;GT=0x8a80;BP=0x8400;H=0x90ca

def load_builder():
 spec=importlib.util.spec_from_file_location('color_builder',ROOT/'src/render/geos/typing-color-bound-candidate/build-two.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def offset(y,c):return 0x6000+(y//8)*320+c*8+(y&7)
def scanlines(raw,top):return bytes(raw[offset(top+y,c)-0x6000]for y in range(9)for c in range(40))
def transformed(fonts,v,style):
 code=fold.geos.native(v);advance=fonts['bsw9-widths.bin'][code]+(style&1)+(style&2);ink=[]
 for y in range(9):
  word=int.from_bytes(fonts['bsw9.bin'][code*18+y*2:code*18+y*2+2],'big')
  if style&1:word|=word>>1
  if style&2:word>>=2 if y<3 else 1 if y<6 else 0
  ink+=word.to_bytes(2,'big')
 return advance,bytes(ink)

def run(out,base):
 frozen=out/'fixture';shutil.copytree(base,frozen);ls,payload,budget=load_builder().build(out/'component',frozen);fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;identity=json.loads((frozen/'freeze.json').read_text());fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names'];dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};cases=[];faults=[]
 def call(name):return f.fast_call(ls[name])
 def component():f.m.load(0xa000,payload)
 def ram_guard(before,kind):
  after=f.read(0,65536);wanted=bytearray(before);allowed=[(0x100,0x200)]
  for name in ['text_ptr','screen_ptr']:allowed.append((f.s[name],f.s[name]+2))
  if kind=='bound':allowed += [(F+5,F+40),(0x8580,0x8620),(0x8640,0x8784),(0x8100,0x8120),(0x8000,0x8340),(f.s['se_v_cache_count'],f.s['se_v_cache_count']+2),(0x9178,0x917e),(f.s['se_reu_c64'],f.s['dma_physical']+1),(f.s['doc_cache_slot'],f.s['doc_cache_slot']+1),(0xdf00,0xdf0b)]
  if kind=='shift':allowed += [(GT+28,GT+105),(BP,BP+360),(0x8580,0x85a8)]
  if kind=='publish':
   allowed += [(GT+29,GT+105),(0x8580,0x85a8)]
   top=f.m.read(GT+2)
   for y in range(9):
    for c in range(40):a=offset(top+y,c);allowed.append((a,a+1))
  for a,z in allowed:wanted[a:z]=after[a:z]
  assert after==wanted,(kind,'whole64KiBguard',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))

 def bounds_model(cache,top,row):
  result=[0,0];low=top&248
  for i,r in enumerate(rows(cache)):
   if not any(r['roles']):continue
   if i==row:return None
   for yy in range(r['top'],r['top']+r['height']):
    if low<=yy<low+16:result[(yy-low)//8]+=8
  return result
 def execute(tag,text,needle,at_delta,key=ord('X'),require=None,dirty=False):
  data=fold.geos.native_text(text);at=data.index(fold.geos.native_text(needle))+at_delta;f.source(data);f.command(99);f.position(at);f.render();oldbits=f.read(0x6000,8000);oldattrs=f.read(0x4000,1000);cache,bank=f.raw_cache();packets=rows(cache);row=next(i for i,r in enumerate(packets)if r['start']<=at<=r['end']);r=packets[row];top=r['top'];assert r['height']==9 and not r['prefix'][22]and not any(r['roles']);index=at-r['start'];x=r['x'][index];width=r['x'][-1];sty=semantic.classify(data).styles[at];op=int(key==0x14);position=at-1 if op else at
  if op:index-=1;x=r['x'][index];sty=semantic.classify(data).styles[position]
  adv,glyph=transformed(fonts,data[position]if op else key,sty);new=data[:position]+(data[position+1:]if op else bytes([key])+data[position:]);newwidth=width+(-adv if op else adv);first=x//8;last=(max(width,newwidth)-1)//8
  ci=position if op else position+1;ns=semantic.classify(new).styles;caretwidth=5 if ci==len(new)or new[ci]==13 else transformed(fonts,new[ci],ns[ci])[0]
  oldbase,_,_,_=semantic.body(data,fonts,caret=None);newbase,newattrs,_,_=semantic.body(new,fonts,caret=None);baseink=scanlines(oldbase,top);expectedbase=scanlines(newbase,top);f.key(key);assert f.merged()==new and not f.m.read(0x9149),'canonicalC6guardstillrefusesmixedneighbor';canonical=f.canonical();reu=f.reu();component();f.put('se_f_owner',4,1);f.m.load(H,cache[:64]);f.m.load(F,bytes([row,top,first,last,0x16])+bytes(19));f.m.load(GT,bytes([op,0,top,adv])+x.to_bytes(2,'little')+width.to_bytes(2,'little')+bytes([caretwidth,0x16])+glyph+bytes(77));
  if dirty:
   baseink=bytearray(baseink)
   for yy in range(9):
    for px in range(width,320):baseink[yy*40+px//8]|=128>>(px&7)
  f.m.load(BP,baseink)
  before=f.read(0x4000,0x4000);shift_ram=f.read(0,65536);regs,nshift=call('se_typing_patch');ram_guard(shift_ram,'shift');assert not regs.p&1 and f.read(0x4000,0x4000)==before,'provisionalshiftcannotwritebitmap/attrs';assert f.read(BP,360)==expectedbase,(tag,'actual6510shiftbase')
  snap=f.read(0,65536);regs,nbound=call('se_tcb_two_check');admit=regs.a==0 and not regs.p&1;ram_guard(snap,'bound');assert not regs.p&1,(tag,regs.a,regs.p);assert f.read(0x4000,0x4000)==before and f.reu()==reu and f.canonical()==canonical,'admissionreadonly'
  expectedbounds=bounds_model(cache,top,row)
  supported=all(not any(v not in (0,2)for v in q['roles'])for q in packets if q['top']<((top&248)+16)and q['top']+q['height']>(top&248))
  desired=supported and all(oldattrs[(top//8+b)*40+c]==newattrs[(top//8+b)*40+c]for b in range(2)for c in range(first,last+1))
  assert admit==desired,(tag,admit,desired)
  if require is not None:assert admit==require,(tag,admit,require,expectedbounds,first,last)
  if admit:
   publish_ram=f.read(0,65536);regs,npublish=call('se_tcb_publish');ram_guard(publish_ram,'publish');assert not regs.p&1
   expected,attrs,_,_=semantic.expected(f,new,fonts)
   # This isolatedprimitive updates bodypixels only. Preserveallthreechrome
   # rows byte-exact; statuspublication belongs to the future transaction.
   composite=oldbits[:640]+expected[640:7680]+oldbits[7680:]
   actual=f.read(0x6000,8000);assert actual==composite,(tag,'wholebitmap_with_unchanged_chrome')
   assert f.read(0x4000,1000)==attrs==oldattrs,(tag,'fullcolororacle')
   fold.geos.png(actual,attrs,out/(tag+'.png'))
  else:npublish=0;assert f.read(0x6000,8000)==oldbits and f.read(0x4000,1000)==oldattrs
  assert f.reu()==reu and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  candidate_bits=f.read(0x6000,8000);candidate_attrs=f.read(0x4000,1000)
  f.put('se_f_owner',0,1);f.m.write(f.s['se_overlay_active'],0);f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_gc_width',0,1);start=f.total_instructions;f.render();full_instructions=f.total_instructions-start
  fullbits,fullattrs,_,_=semantic.expected(f,new,fonts);assert f.read(0x6000,8000)==fullbits and f.read(0x4000,1000)==fullattrs
  if admit:assert candidate_bits[640:7680]==fullbits[640:7680]and candidate_attrs==fullattrs,(tag,'actualforcedfullbodyandcolors')
  if tag=='minority-LSN190':assert oldattrs[160]==0x16 and fullattrs[160]==0x36,'retainedknowncounterexample'
  assert f.canonical()==canonical and f.merged()==new
  item=dict(tag=tag,admitted=admit,actual_forced_full_instructions=full_instructions,bounds=expectedbounds,first=first,last=last,shift_instructions=nshift,bound_instructions=nbound,publish_instructions=npublish);cases.append(item);print('PASS',item,flush=True);f.put('se_f_owner',0,1);f.m.write(f.s['se_overlay_active'],0)
 try:
  execute('minority-LSN190','Intro.\rjjj\r- .\rTail.','jjj',2,0x14,False)
  # Searchdenseprefixes keeps source/font geometry real, never forgeinkvotes.
  for count in range(8,40):
   text='# Heading\r'+'M'*count+'\rTail.'
   try:execute('heading-dense-'+str(count),text,'M'*count,count//2,dirty=bool(count&1))
   except AssertionError as e:
    if 'canonicalC6guard' in str(e):continue
    raise

  for style,openmark in [(1,'**'),(2,'*'),(3,'***')]:
   text='# Heading\rAlpha '+openmark+'MMMMMMMMMMMM'+openmark+' tail.\rTail.'
   execute('styled-under-heading-'+str(style),text,'MMMMMMMMMMMM',4)
  for tag,line,needle,at,key in [('blank','          ','    ',2,ord('X')),('sparse','I I I I I I I I I','I I',2,ord('I')),('newtail','MMMMMMMM','MMMM',8,ord('M'))]:
   execute(tag,'# Heading\r'+line+'\rTail.',needle,at,key)
  for tag,line,word in [('natural','Plain row having ample room','having'),('pangram','A quick brown fox jumps over the lazy dog.','brown'),('alpha','Alpha interiorwords omega.','interiorwords')]:
   for key in [ord('X'),0x14]:execute(tag+('-insert'if key!=0x14 else'-back'),'# Heading\r'+line+'\rTail.',word,3,key)
  for count in [12,20,32]:execute('dense-back-'+str(count),'# Heading\r'+'M'*count+'\rTail.','M'*count,count//2,0x14)
  # Independent exact-election negatives and yellow-dominant admissions.
  for tag,line,delta,key,want in [('yellow-flips-white','jjj',1,ord('X'),False),('white-flips-yellow','jjjjj',2,0x14,False),('yellow-stable','jjj',2,0x14,True)]:
   execute(tag,'# .\r'+line+'\rTail.',line,delta,key,want)
  for marker in ['**','*','***']:
   execute('formatted-heading-'+str(len(marker)),'# '+marker+'Heading'+marker+'\rPlain row having ample room\rTail.','having',3,ord('X'))
  # RealtypedFE faults and maliciousrange inputs mustnotwriteVIC/source/REU.
  def write_fe(offset,data):
   f.m.load(0x8080,data);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',len(data),2);assert not f.call('se_reu_copy',0).p&1
  component();f.put('se_f_owner',4,1);cache,bank=f.raw_cache();target=1;slot=0x200+target*0x800;top=cache[slot+15];f.m.load(H,cache[:64]);f.m.load(F,bytes([target,top,0,8,0x16])+bytes(19));basebits,_,_,_=semantic.body(f.merged(),fonts,caret=None);f.m.load(BP,scanlines(basebits,top));r,_=call('se_tcb_two_check');assert r.a==0 and not r.p&1,'faultbaselineactualadmission'
  baseline=f.read(F,24);stored=cache
  def refuse(tag,mutate,restore=lambda:None,error=None):
   f.m.load(F,baseline);mutate();before=f.read(0,65536);reu=f.reu();canonical=f.canonical();r,n=call('se_tcb_two_check');after=f.read(0,65536)
   if error is None:assert r.a==2 and not r.p&1,(tag,r.a,r.p)
   else:assert r.a==error and r.p&1,(tag,r.a,r.p)
   assert after[0x4000:0x8000]==before[0x4000:0x8000]and f.reu()==reu and f.canonical()==canonical and after[0xc600:0xca00]==before[0xc600:0xca00],tag
   if f.get('se_f_owner',1)!=4:assert after[0x8000:0x9180]==before[0x8000:0x9180],tag
   restore();faults.append(dict(tag=tag,code=r.a,carry=bool(r.p&1),instructions=n))
  for field,value in [(0,22),(1,0),(1,184),(2,255),(3,40),(4,0x36)]:refuse('frame-'+str(field)+'-'+str(value),lambda field=field,value=value:f.m.write(F+field,value))
  for count in [0,23,255]:refuse('headercount-'+str(count),lambda count=count:f.m.write(H+1,count),lambda:f.m.write(H+1,stored[1]))
  for off,value in [(0,0),(2,0),(3,2),(35,1),(36,1),(37,1),(42,2),(46,1)]:
   refuse('header-field-'+str(off),lambda off=off,value=value:f.m.write(H+off,value),lambda off=off:f.m.write(H+off,stored[off]))
  for off,value in [(17,3),(17,4),(27,0),(24,1),(25,1),(9,255),(3,255),(518,1),(520,255)]:
   refuse('complete-geometry-'+str(off)+'-'+str(value),lambda off=off,value=value:write_fe(slot+off,bytes([value])),lambda off=off:write_fe(slot+off,stored[slot+off:slot+off+1]))
  for off in [194]:
   refuse('style-out-of-range-'+str(off),lambda off=off:write_fe(slot+off,bytes([4])),lambda off=off:write_fe(slot+off,stored[slot+off:slot+off+1]))
  for value in [0,2,0x80]:refuse('neighborflags-'+str(value),lambda value=value:write_fe(0x200+22,bytes([value])),lambda:write_fe(0x200+22,stored[0x200+22:0x200+23]))
  for off,value in [(14,8),(16,1)]:refuse('neighborkind-height-'+str(off),lambda off=off,value=value:write_fe(0x200+off,bytes([value])),lambda off=off:write_fe(0x200+off,stored[0x200+off:0x200+off+1]))
  refuse('native-unaligned-prefix',lambda:write_fe(0x200+14,bytes([8,17,1])),lambda:write_fe(0x200+14,stored[0x200+14:0x200+17]))
  refuse('following-row-overlap',lambda:write_fe(0x200+2*0x800+15,bytes([top+8])),lambda:write_fe(0x200+2*0x800+15,stored[0x200+2*0x800+15:0x200+2*0x800+16]))
  # Last rolebyte of the full161B publiccapacity is actually checked.
  oldroles=stored[slot+356:slot+356+161]
  write_fe(slot+12,(161).to_bytes(2,'little'));write_fe(slot+356,bytes(160)+bytes([2]));refuse('target161-lastcolored',lambda:None);write_fe(slot+356,bytes(160)+bytes([14]));refuse('target161-lastinvalid',lambda:None);write_fe(slot+12,stored[slot+12:slot+14]);write_fe(slot+356,oldroles)
  for count in [0,162,256,65535]:
   refuse('targetcount-'+str(count),lambda count=count:write_fe(slot+12,count.to_bytes(2,'little')),lambda:write_fe(slot+12,stored[slot+12:slot+14]))
  for off,value in [(14,0),(14,255),(15,248),(15,20),(16,1),(21,7),(22,2),(22,0x80)]:refuse('targetprefix-'+str(off)+'-'+str(value),lambda off=off,value=value:write_fe(slot+off,bytes([value])),lambda off=off:write_fe(slot+off,stored[slot+off:slot+off+1]))
  count=int.from_bytes(stored[slot+12:slot+14],'little')
  for index,value in [(0,2),(count-1,14)]:refuse('targetrole-'+str(index)+'-'+str(value),lambda index=index,value=value:write_fe(slot+356+index,bytes([value])),lambda index=index:write_fe(slot+356+index,stored[slot+356+index:slot+357+index]))
  for owner in [0,1,2,3,5,255]:refuse('foreignowner-'+str(owner),lambda owner=owner:f.put('se_f_owner',owner,1),lambda:f.put('se_f_owner',4,1),0xb2)
  handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle)
  for field,index in [('se_gc_epoch',0),('se_reu_logical_owner',handle),('se_reu_physical_owner',physical),('se_reu_map',handle)]:
   addr=f.s[field]+index;old=f.m.read(addr);refuse(field,lambda addr=addr:f.m.write(addr,0),lambda addr=addr,old=old:f.m.write(addr,old),0x18)

  result=dict(status='passed',identity=identity,budget=budget,cases=cases,faults=faults,scope='Exact two-color typedFE election + provisional actual6510 suffixshift and explicitpublish; this component retains production C6 unchanged. Separate runtime/public verifier owns integrated private pair proof.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geos-typing-two-color'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve())

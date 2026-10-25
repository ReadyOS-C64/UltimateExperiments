"""Actual sealed R21 GEOS row admission/rendering with independent strip oracle.

Private build only, current resident frozen first. No shared make/VICE. Row
borrows actual existing foreground pointers and owns no document/source lease.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_fold_controller as resident
import test_geos_row as model
from bindings import verify
from overlays import wrap,HEADER
F=0x8880;SIZE=704;PALETTE=0x8500
SOURCES=['render/geos/editor-row-entry','render/geos/row','render/geos/measure','render/geos/glyph','render/geos/assets']
def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out,base,row_source=None):
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];seal=verify(base/'build/editor.prg',base/'build/editor.lbl');d=seal['digest'];assert seal['resident_sha256']==report['sha256']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_f_owner\n.importzp text_ptr,screen_ptr\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objects=[]
 for name in SOURCES:
  p=out/(name.replace('/','-')+'.o');source=row_source if name=='render/geos/row' and row_source else ROOT/f'src/{name}.s';run('ca65','-g','-I',out,'-I','src','-o',p,source);objects.append(p)
 run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects)
 run('ca65','-g','-o',out/'aliases.o',out/'aliases.s');run('ld65','-C','cfg/geos-editor-row.cfg','-o',out/'geosrow.bin','-Ln',out/'geosrow.lbl','-m',out/'geosrow.map',*objects,out/'aliases.o')
 payload=(out/'geosrow.bin').read_bytes();ls={p[2].lstrip('.'):int(p[1],16) for line in (out/'geosrow.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
 assert ls['se_geos_packed']==0xabf3 and ls['se_geos_widths']==0xaedb, 'sealed font ABI moved'
 assert 16<len(payload)<=4096 and payload[:16]==bytes.fromhex(d) and ls['entry']==0xa010 and ls['se_gg_context']==s['text_ptr'] and ls['se_gg_pointer']==s['screen_ptr']
 aliases=json.loads((out/'aliases.json').read_text());assert aliases['imports']['text_ptr']==s['text_ptr'] and aliases['imports']['screen_ptr']==s['screen_ptr'] and aliases['imports']['se_petscii_screen']==s['se_petscii_screen']
 image=wrap(payload,0,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'geosrow.seo').write_bytes(image)
 measures={}
 for name,p in zip(SOURCES,objects):
  text=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);sizes={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)};assert all(sizes.get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE']);measures[name]=sizes
 (out/'build.json').write_text(json.dumps(dict(resident_sha256=report['sha256'],binding=d,slot=0,id=21,payload_bytes=len(payload),spare_bytes=4096-len(payload),entry=ls['entry'],packed_font=ls['se_geos_packed'],widths=ls['se_geos_widths'],source_native_fallback=0x4800,ZP_loans=[s['text_ptr'],s['screen_ptr']],new_BSS=0,new_ZP=0,segments=measures),indent=2)+'\n')
 return ls,payload,image

class Fixture(resident.Fixture):
 def __init__(self,out,ls,payload,image):
  super().__init__(out);self.ls=ls;self.payload=payload;self.image=image;self.font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();self.widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();self.native=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();self.native_addr=0x4800;self.row_calls=0;self.row_peak=0;self.import_image(image);self.m.load(0x4800,bytes([0xa7])*1024);self.m.load(0x4800,self.native);self.m.load(PALETTE,model.PALETTE)
 def import_image(self,image):
  for i in range(self.s['se_overlay_capacity']):
   if self.m.read(self.s['se_overlay_ids']+i)==image[6] and self.m.read(self.s['image_slot']+i)==image[5]:
    self.m.write(self.s['se_overlay_ids']+i,0);self.m.write(self.s['se_overlay_active']+image[5],0)
  self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);assert not self.call('se_overlay_import').p&1
 def setup(self,runs,row=0,clip=(0,320,0,8),reset=True):
  left,right,top,bottom=clip;frame=bytes([row,len(runs),int(reset),6])+b''.join(v.to_bytes(2,'little') for v in [0x8d00,self.ls['se_geos_packed'],self.ls['se_geos_widths'],self.native_addr,PALETTE,left,right])+bytes([top,bottom]);assert len(frame)==20
  self.m.load(F,frame+(bytes([0xa7])*(SIZE-20) if reset else b''));cursor=0x8d30;records=[]
  for index,(chars,styles,roles,flags,x,y) in enumerate(runs):
   n=len(chars);assert n<=128 and len(styles)==len(roles)==len(flags)==n;desc=bytearray([n,y&255])+x.to_bytes(2,'little');arrays=[]
   for value in [chars,styles,roles,flags]:arrays.append(cursor);self.m.load(cursor,bytes(value));desc+=cursor.to_bytes(2,'little');cursor+=len(value)
   at=cursor;self.m.load(at,b'\xa7'*(2*(n+1)));cursor+=2*(n+1);desc+=at.to_bytes(2,'little')+b'\xa7'*3;assert len(desc)==17;self.m.load(0x8d00+index*17,desc);records.append((at,n,arrays))
  assert cursor<=0x9180;return frame,records
 def cache_allowed(self):
  pairs=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2)]
  h=self.s['se_overlay_header']
  return [(self.s[n],self.s[n]+w) for n,w in pairs]+[(self.s['se_reu_c64'],self.s['dma_physical']+1),(h+8,h+10),(h+12,h+14),(0xdf00,0xdf0b)]
 def loader_expected(self,wanted,before,after,stage=None):
  wanted[0xa000:0xa000+len(self.payload)]=self.payload
  dma=self.s['se_reu_dma_calls'];loaded=int.from_bytes(after[dma:dma+2],'little')!=int.from_bytes(before[dma:dma+2],'little')
  if loaded:wanted[0x5000:0x5000+len(self.payload)]=self.payload if stage is None else stage
  for lo,hi in [*self.cache_allowed(),(0x100,0x200)]:wanted[lo:hi]=after[lo:hi]
 def invoke(self,op=0,ctx=F,owner=4):
  self.put('se_f_owner',owner,1);self.m.load(self.s['se_overlay_frame'],bytes([op,ctx&255,ctx>>8]));before=self.read(0,65536);canonical=self.canonical();leases=self.get('se_doc_read_locks',1)
  r,used=self.m.call(self.s['se_overlay_call'],a=21,x=0,limit=3_000_000);self.row_calls+=1;self.row_peak=max(self.row_peak,used);self.last_used=used;after=self.read(0,65536)
  assert self.canonical()==canonical and self.get('se_doc_read_locks',1)==leases and self.read(0xc600,1024)==self.shim
  assert self.read(0xa000,len(self.payload))==self.payload
  return r,before,after
 def check(self,runs,row=0,clip=(0,320,0,8),reset=True,hist=None):
  frame,records=self.setup(runs,row,clip,reset);r,before,after=self.invoke();wanted,weights,maps,dones=model.Fixture.oracle(self,runs,row,clip,before,hist)
  assert not r.p&1 and r.a==0,(row,clip,r.a,r.p)
  assert after[F:F+20]==frame and after[F+20]==1
  assert after[F+98:F+658]==bytes(v for tile in weights for v in tile),('histogram',row,clip)
  for index,(at,n,arrays) in enumerate(records):
   expected=b''.join(v.to_bytes(2,'little') for v in maps[index]);assert after[at:at+len(expected)]==expected;assert after[at+len(expected):at+2*(n+1)]==b'\xa7'*(2*(n+1)-len(expected));desc=0x8d00+index*17+14;assert after[desc:desc+3]==bytes([dones[index]])+maps[index][-1].to_bytes(2,'little');wanted[at:at+len(expected)]=expected;wanted[desc:desc+3]=after[desc:desc+3]
  wanted[F+20:F+SIZE]=after[F+20:F+SIZE];self.loader_expected(wanted,before,after)
  for lo,hi in [(self.s['text_ptr'],self.s['text_ptr']+2),(self.s['screen_ptr'],self.s['screen_ptr']+2)]:wanted[lo:hi]=after[lo:hi]
  assert after==wanted,('fullRAM/pixels/attributes/fonts/source/shim/phaseprefix/catalogtail',row,clip,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  return weights,maps,dones
 def refuse(self,error=0x90,op=0,ctx=F,owner=4,frame=False,partial=False,stage=None):
  r,before,after=self.invoke(op,ctx,owner);assert r.p&1 and r.a==error,(op,ctx,owner,error,r.a,r.p);wanted=bytearray(before);self.loader_expected(wanted,before,after,stage)
  if frame:
   wanted[F+20:F+SIZE]=after[F+20:F+SIZE]
   for n in ['text_ptr','screen_ptr']:at=self.s[n];wanted[at:at+2]=after[at:at+2]
  if partial:
   row=before[F];wanted[0x6000+row*320:0x6000+(row+1)*320]=after[0x6000+row*320:0x6000+(row+1)*320];wanted[0x4000+row*40:0x4000+(row+1)*40]=after[0x4000+row*40:0x4000+(row+1)*40];wanted[0x8d00+14:0x8d00+17]=after[0x8d00+14:0x8d00+17]
   at=int.from_bytes(before[0x8d00+12:0x8d00+14],'little');n=before[0x8d00];wanted[at:at+2*(n+1)]=after[at:at+2*(n+1)]
   assert after[F+20]==0
  assert after==wanted,('refusal touched frame/source/maps/font/lease/shim/neighbors',error,op,owner,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  return before,after

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--base',type=Path,default=ROOT/'agentsworking/evidence/M7/20261025T022319293214Z-geos-editor-poisoned-final-cpu/diverse/fixture');parser.add_argument('--row-source',type=Path);a=parser.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-row-leaf'/stamp;out.mkdir(parents=True)
 if a.base:
  base=out/'fixture';shutil.copytree(a.base,base);report=json.loads((base/'build/editor-report.json').read_text());names=json.loads((base/'freeze.json').read_text())['names']
 else:base,report,names=resident.freeze(out)
 resident.cpu_editor.ROOT=resident.editor_fixture.ROOT=base;resident.cpu_editor.NAMES=resident.editor_fixture.NAMES=names
 ls,payload,image=build(out,base,a.row_source);f=Fixture(out,ls,payload,image);cases=[];rows=0;invalid=0;profiles=[]
 shutil.copy2(a.row_source or ROOT/'src/render/geos/row.s',out/'row-source-used.s')
 def rec(chars,x=0,y=0,phase=0):return chars,bytes((i+phase)%4 for i in range(len(chars))),bytes((i+phase)%14 for i in range(len(chars))),bytes((i+phase)%8 for i in range(len(chars))),x,y
 try:
  reu=f.reu();f.check([rec(b'GEOS lower/UPPER gjpq',x=2,y=0)],row=2);rows+=1;cases.append('actualsealedR21catalogload/owner4/borrowedresidentpointers/native4800/firstindependentstrip')
  (out/'first-strip.json').write_text(json.dumps(dict(status='passed',payload_bytes=len(payload),row=2,bitmap_sha256=hashlib.sha256(f.read(0x6000+640,320)).hexdigest(),attrs_sha256=hashlib.sha256(f.read(0x4000+80,40)).hexdigest()))+'\n')
  # Warm-call profiles include validation, histogram clear, raster and final
  # attribute resolve. They exclude catalog cold loading; exact clear-path
  # deltas follow because the normal CODE/font addresses remain unchanged.
  sample=(b'Wim. gjpqy Mixed UPPER/lower',bytes([0])*26,bytes([0])*26,bytes([0])*26,0,0)
  sample=(sample[0],bytes(len(sample[0])),bytes(len(sample[0])),bytes(len(sample[0])),0,0)
  for tag,runs,clip in [('blank-full',[],(0,320,0,8)),('content-full',[sample],(0,320,0,8)),('blank-partial',[],(7,319,1,7)),('content-partial',[sample],(7,319,1,7))]:
   f.check(runs,row=2,clip=clip);rows+=1
   profiles.append(dict(tag=tag,instructions=f.last_used,bitmap=hashlib.sha256(f.read(0x6280,320)).hexdigest(),attributes=hashlib.sha256(f.read(0x4050,40)).hexdigest()))
  hist,_,_=f.check([sample],row=6);rows+=1
  f.check([rec(b'Append descenders',y=-8,phase=2)],row=6,reset=False,hist=hist);rows+=1
  profiles.append(dict(tag='append-no-clear',instructions=f.last_used,bitmap=hashlib.sha256(f.read(0x6000+6*320,320)).hexdigest(),attributes=hashlib.sha256(f.read(0x4000+6*40,40)).hexdigest()))
  cases.append('warmprofiles/full-and-partial-blank-content/append-histogram-preserved')
  if not a.smoke:
   # A true cold load may overwrite only the documented5000 staging span and
   # Rslot; a second warm paint must produce identical full output.
   f.put('se_overlay_active',0,1);f.m.load(0x5000,bytes([0x5a])*len(payload));f.check([rec(b'Cold / warm',phase=3)],row=0);rows+=1;cold=f.read(0x6000,320)+f.read(0x4000,40);f.check([rec(b'Cold / warm',phase=3)],row=0);rows+=1;assert f.read(0x6000,320)+f.read(0x4000,40)==cold
   for value in range(256):
    for style in range(4):
     chars=bytes([value])*8;f.check([(chars,bytes([style])*8,bytes([value%14])*8,bytes([value%8])*8,3,0)],row=value%25,clip=(5,37,0,8));rows+=1
   for row in range(25):
    for phase in range(8):f.check([rec(bytes((j*11+phase*19)&255 for j in range(80)),x=phase,y=(phase%8),phase=phase)],row=row);rows+=1
   upper=rec(b'gjpqy Lower/UPPER '+bytes([0xc1,0xc7,0xd9]),x=2,y=-8,phase=1);lower=rec(b'Next logical line',x=3,y=1,phase=2)
   f.check([upper,lower],row=5);rows+=1
   for clip in [(0,0,0,8),(320,320,0,8),(7,9,0,8),(0,320,3,5),(11,319,8,8),(19,301,1,7)]:f.check([rec(b'Wim.'*20,y=-3),rec(b'gjpq'*16,y=6,phase=1)],row=24,clip=clip);rows+=1
   f.check([],row=7);f.check([rec(b'')],row=8);rows+=2
   weights,_,_=f.check([rec(b'Wim.'*12)],row=10);rows+=1;f.check([rec(b'gjpq'*10,x=2,y=-8,phase=3)],row=10,reset=False,hist=weights);rows+=1
   dense=(b' '*80,bytes(80),bytes([2])*80,bytes([1])*80,0,0);weights,_,_=f.check([dense],row=6);rows+=1
   for _ in range(4):weights,_,_=f.check([dense],row=6,reset=False,hist=weights);rows+=1
   assert weights[0][2]==255
   cases.append('all256native-x4styles/all25strips/flags0..7/2runs/ninthrow/clips/maps/reset-append/saturatinginkvotes/cold-warmidentical')
   # Foreign counted leases are not owned or released by an immutable packet
   # renderer. Use actual resident acquire/release, not a fabricated count.
   for leases in [0,1,7]:
    for _ in range(leases):assert not f.call('se_doc_read_acquire').p&1
    f.check([rec(b'Lease-neutral native graphics '+bytes([0x5c,0x7f,0xa1,0xff]),phase=2)],row=12);rows+=1;assert f.get('se_doc_read_locks',1)==leases
    for _ in range(leases):assert not f.call('se_doc_read_release').p&1
   for owner in [0,1,2,3,5,255]:
    opaque=bytes((j*37+owner)&255 for j in range(1152));f.m.load(0x8d00,opaque);f.m.load(F,bytes((j*29+owner)&255 for j in range(SIZE)))
    for op in [0,1,255]:f.refuse(0xb2,op=op,ctx=0xc600,owner=owner);invalid+=1
   f.setup([rec(b'Frame stays opaque')]);before=f.read(F,SIZE);r,b,aft=f.invoke(1);assert not r.p&1 and r.a==0 and f.read(F,SIZE)==before;want=bytearray(b);f.loader_expected(want,b,aft);assert aft==want
   for op in [2,255]:f.refuse(op=op);invalid+=1
   f.refuse(ctx=0xc600);invalid+=1
   cases.append('owner4beforeANYframeaccess/wrongowner0-1-2-3-5-255/ADMITno-op/badop/badframe/sourceleases0-1-7opaque')
   mutations=[(0,25),(1,3),(2,2),(3,16),(18,9),(19,9),(15,2),(17,2),(5,0xc6),(7,0x60),(11,0xc6),(13,0xc6),('count',129),('origin',8),('origin',0xf7),('style',4),('role',14),('flag',8),('map',0x917f),('chars',0x8800)]
   for field,value in mutations:
    _,records=f.setup([rec(b'Valid')])
    if isinstance(field,int):f.m.write(F+field,value)
    elif field=='count':f.m.write(0x8d00,value)
    elif field=='origin':f.m.write(0x8d01,value)
    elif field in ['style','role','flag']:f.m.write(records[0][2][{'style':1,'role':2,'flag':3}[field]],value)
    else:f.m.load(0x8d00+{'map':12,'chars':4}[field],value.to_bytes(2,'little'))
    f.refuse(frame=True);invalid+=1
   f.setup([rec(b'Append')],reset=False);f.m.write(F+20,0);f.refuse(frame=True);invalid+=1
   f.setup([rec(b'Palette')]);f.m.write(PALETTE+2,16);f.refuse(frame=True);invalid+=1;f.m.load(PALETTE,model.PALETTE)
   # A bad supplied packed font refuses before the first pixel write. A later
   # bad glyph leaves only its declared unpublished strip/maps, VALID0.
   packed=(ROOT/'assets/fonts/generated/bsw9-original.bin').read_bytes();f.setup([rec(b'Valid')]);f.m.load(0x8200,packed);f.m.write(0x8200,packed[0]^1);f.m.load(F+6,(0x8200).to_bytes(2,'little'));f.refuse(0x94,frame=True);invalid+=1
   f.setup([(b' A',b'\0\0',b'\0\0',b'\0\0',0,0)]);bad=bytearray(packed);bad[8+65*2:8+65*2+2]=b'\xff\xff';f.m.load(0x8200,bad);f.m.load(F+6,(0x8200).to_bytes(2,'little'));f.refuse(0x94,frame=True,partial=True);invalid+=1
   cases.append('21scalar-range-style-role-flag-map-framefaults/profile94/lateglyph94-partialunpublished-neveroutsideownedstrip')
   # Real catalog failures before entry preserve frame, sources and foreign
   # leases. Damage asset bytes via checked resident DMA, restore afterwards.
   f.setup([rec(b'Admission')]);index=next(j for j in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+j)==21 and f.m.read(f.s['image_slot']+j)==0)
   f.m.write(f.s['se_overlay_ids']+index,0);f.refuse(0x17);invalid+=1;f.m.write(f.s['se_overlay_ids']+index,21)
   f.put('se_overlay_busy',1,1);f.refuse(0x19);assert f.get('se_overlay_busy',1)==1;invalid+=1;f.put('se_overlay_busy',0,1)
   epoch=f.get('se_reu_epoch',2);f.put('se_reu_epoch',epoch^1,2);f.refuse(0x18);invalid+=1;f.put('se_reu_epoch',epoch,2)
   logical=f.get('se_overlay_asset' if index<16 else 'se_overlay_asset_second',1);asset_offset=(index%16)*4096
   for offset,error in [(0,0x11),(len(payload)-1,0x14)]:
    bad=bytearray(payload);bad[offset]^=1;f.m.load(0x8000,bytes([bad[offset]]));f.put('se_reu_logical',logical,1);f.put('se_reu_offset',asset_offset+offset,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x8000,2);assert not f.call('se_reu_copy',0).p&1
    f.put('se_overlay_active',0,1);f.refuse(error,stage=bad);invalid+=1
    f.m.load(0x8000,bytes([payload[offset]]));f.put('se_reu_logical',logical,1);f.put('se_reu_offset',asset_offset+offset,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x8000,2);assert not f.call('se_reu_copy',0).p&1
   # Cold good retry after corruption must really reload the same sealed leaf.
   f.check([rec(b'After checked asset retry',phase=4)],row=23);rows+=1
   cases.append('actualcatalogmissing/busy/staleepoch/binding11/CRC14-beforeentry/checkedDMAassetrestore-andcoldretry')
  assert f.reu()==reu
  result=dict(status='passed',resident_sha256=report['sha256'],binding=json.loads((out/'build.json').read_text())['binding'],payload_bytes=len(payload),spare_bytes=4096-len(payload),rows=rows,pixels_checked=rows*2560,invalid_frames=invalid,row_calls=f.row_calls,peak_instructions=f.row_peak,new_BSS=0,new_ZP=0,borrowed_ZP=[f.s['text_ptr'],f.s['screen_ptr']],full_RAM_guard_bytes=65536,whole_REU_guard_bytes=16777216,shim_bytes=1024,catalog_tail_bytes=192,cases=cases,profiles=profiles,scope='ActualsealedR21 physical-strip renderer/currentresidentcatalog; independent pixels/attributes/maps oracle. No sourcelease ownership, native VIC, live editor mode or timing claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),cases=cases))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M7'/(stamp+'-geos-row-leaf');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 with zipfile.ZipFile(evidence/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in [*[f'src/{n}.s' for n in SOURCES],'cfg/geos-editor-row.cfg','src/render/geos/row.inc','src/render/geos/api.inc','src/render/geos/row-validate.s','src/render/geos/row-resolve.s','src/render/geos/row-fast.s','tests/test_geos_row_leaf.py','tests/test_geos_row.py']:z.write(ROOT/n,n)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()

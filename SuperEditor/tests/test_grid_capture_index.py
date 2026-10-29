"""Frozen packaged C33 capture/index lifetime regression; no capsule substitutions."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,random,re
import test_editor_file_integration as filemodel
from d81_image import D81Image
import test_cache_hotpath_profile as profile
import test_grid_editor_vice as diverse
observer=profile.observer
ROOT=observer.ROOT
BAD=ROOT/'build/cache-editor-product/20261026T180419392911Z/fixture'
FIXED=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'

def authenticate(base,expect_bad=False):
 identity=json.loads((base/'freeze.json').read_text());assert len(identity['names'])==59
 report=json.loads((base/'build/editor-report.json').read_text());digest=bytes.fromhex(report['resident_binding']['digest'])
 resident=(base/'build/editor.prg').read_bytes();disk=(base/'build/supereditor.d81').read_bytes();d81=D81Image(disk)
 assert hashlib.sha256(resident).hexdigest()==report['sha256']==identity['prg_sha256']
 assert d81.read(b'SUPEREDITOR',kind=2).data==resident
 for name in identity['names']:
  image=(base/f'build/overlays/{name}.seo').read_bytes()
  assert hashlib.sha256(image).hexdigest()==identity['assets'][name]
  assert d81.read(name.upper().encode(),kind=1).data==image and image[:4]==b'SEO2'
  assert image[20:36]==image[36:52]==digest and len(image)-36==int.from_bytes(image[8:10],'little')
  assert binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
 want='91a51068dbebaefc763379a5f6225a9cf0ddaabc098f6b219d2cd7a01eb31f2e'if expect_bad else'ab86a6aca6a054e7de24c48916856b1393438ef5846f693ff03493fce83d0fbb'
 assert identity['assets']['grid']==want,'only the explicitly bad/fixed packaged C33 is qualified'
 return dict(PRG=identity['prg_sha256'],binding=digest.hex(),D81=hashlib.sha256(disk).hexdigest(),C33=want,assets=59)

class FileFixture(filemodel.IntegratedFiles,observer.geos.Fixture):
 catalog=observer.geos.Fixture.catalog
 def __init__(self,*args):
  self.fs={};self.channels={};self.trace=[];self.inject={};self.selected_in=self.selected_out=None
  self.st=0;self.dos=b'00, OK,00,00\r';self.directory=b'';self.actions=[];self.opens=[];self.dos_commands=[];self.service_steps=0
  BaseFixture.__init__(self,*args)
 def key(self,byte,error=None,mods=0):return filemodel.IntegratedFiles.key(self,byte,error=error,mods=mods)

# Keep the original constructor explicit: Gate's temporary class selection only
# changes the modeled ROM boundary; actual product commands/capsules are intact.
BaseFixture=observer.geos.Fixture

def run(out,base,expect_bad=False,reverse=False,file_open=False,extended=False,far=False):
 out.mkdir(parents=True);seal=authenticate(base,expect_bad)
 saved=observer.geos.Fixture
 try:
  if file_open:observer.geos.Fixture=FileFixture
  g=observer.Gate(out,base)
 finally:observer.geos.Fixture=saved
 f=g.f;prefix=b'Prefix\r'*9400 if far else b'';data=prefix+diverse.fixture();steps=[];line2=9402 if far else 2
 def state(tag):
  v={n:f.get(n,w)for n,w in [('se_e_error',1),('se_e_job',1),('se_f_owner',1),('se_doc_read_locks',1),('se_i_ready',1),('se_i_count',1),('se_n_cache_count',1),('se_hot_caret',3),('se_v_top',3),('se_v_columns',1)]};v['tag']=tag;steps.append(v);(out/'progress.json').write_text(json.dumps(steps,indent=2)+'\n');return v
 def pixels(tag):
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,data)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
  assert f.merged()==data and f.catalog()==catalog and g.stable()==stable and f.read(0xc600,1024)==f.shim,(tag,'canonical/catalog/history/shim')
  assert not any(f.get(n,1)for n in ('se_n_owned','se_s_owned','se_v_nav_busy','se_hot_phase')), (tag,'no retained live phase/lease')
  observer.geos.png(bits,attrs,out/(tag+'.png'));state(tag)
 try:
  f.source(b'Original source.\r'if file_open else data,physical=256)
  if file_open:
   f.fs[b'DIVERSE']=data;f.start('f7','O');f.enter_name(b'DIVERSE',True);profile.drain(f)
   assert f.merged()==data and not f.get('se_e_error',1) and f.get('se_f_current_len',1)==7
   assert f.read(f.s['se_f_current_name'],7)==b'DIVERSE'
  f.typed(observer.geos.native_text('syntax plain'));catalog=f.catalog();stable=g.stable()
  for number,mode in enumerate((98,97)if reverse else(97,98)):
   before=g.audit_begin();f.command(mode);profile.drain(f);g.audit_end(before,'mode-'+str(mode));pixels('mode-'+str(mode))
   state('before-goto-'+str(mode))
   try:
    before=g.audit_begin();f.typed(observer.geos.native_text('goto '+str(line2)));profile.drain(f);g.audit_end(before,'goto-'+str(mode))
   except AssertionError:
    g.audit_end(before,'expected-failed-goto');state('failed-goto-'+str(mode));assert expect_bad and number==1 and f.get('se_e_error',1)==0x7b
    assert f.merged()==data and g.stable()==stable and f.catalog()==catalog and f.read(0xc600,1024)==f.shim
    (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(g.reu())
    result=dict(status='EXPECTED_BAD_FAILURE',error=0x7b,identity=g.identity,seal=seal,steps=steps,scope=__doc__,FileOpen=file_open)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('EXPECTED_BAD_FAILURE',mode,hex(0x7b),flush=True);return result
   assert f.get('se_hot_caret')==len(prefix)+diverse.fixture().index(b'\r')+1
   pixels('goto-'+str(mode))
   for _ in range(6):f.key(0x1d);profile.drain(f)
   expected=[len(prefix)+n for n in (37,36,65,36)]
   for action,key in [('right',0x1d),('left',0x9d),('down',0x11),('up',0x91)]:
    before=g.audit_begin();f.key(key);profile.drain(f);g.audit_end(before,str(mode)+'-'+action);assert f.get('se_hot_caret')==expected.pop(0),(mode,action,'canonical raw navigation');pixels(str(mode)+'-'+action)
  assert not expect_bad,'bad fixture did not reproduce'
  if extended:
   for line in ((9401,9403,9414,9420,9426,9402)if far else(1,3,14,20,26,2)):
    before=g.audit_begin();f.typed(observer.geos.native_text('goto '+str(line)));profile.drain(f);g.audit_end(before,'extended-goto-'+str(line))
    starts=[0]+[i+1 for i,b in enumerate(data)if b==13]
    assert f.get('se_hot_caret')==starts[line-1],(line,'canonical GOTO anchor')
    pixels('extended-goto-'+str(line))
  result=dict(status='PASS',identity=g.identity,seal=seal,steps=steps,scope=__doc__,FileOpen=file_open);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True);return result
 except BaseException:
  state('unexpected-failure');(out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(g.reu());raise
 finally:f.close()

def crc(out,base):
 """Internal arithmetic proof only, after real resident admission of exact C33."""
 out.mkdir(parents=True);seal=authenticate(base);g=observer.Gate(out,base);f=g.f
 try:
  image=(base/'build/overlays/grid.seo').read_bytes();payload=image[36:];pair=base/'build/overlays/grid.bin'
  assert pair.read_bytes()==payload
  labels={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(base/'build/overlays/grid.lbl').read_text())}
  f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
  assert not r.p&1 and f.read(0xb000,len(payload))==payload
  f.put('se_f_owner',4,1)
  for name,value in [('se_i_ready',1),('se_i_count',37),('se_n_cache_count',23)]:f.put(name,value,1)
  before=f.read(0,65536);reu=g.reu();r,n=f.fast_call(labels['capture_tables']);after=f.read(0,65536);wanted=bytearray(before)
  wanted[0x100:0x200]=after[0x100:0x200]
  words=[binascii.crc_hqx(bytes((i,)),0)for i in range(256)]
  wanted[0x8d00:0x8f00]=bytes(w&255 for w in words)+bytes(w>>8 for w in words)
  for name in ('se_i_ready','se_i_count','se_n_cache_count'):wanted[f.s[name]]=0
  assert after==wanted and g.reu()==reu,'only three authority bytes/table512/stack may change'
  rng=random.Random(3176);costs=[]
  for i in range(132):
   packet=bytes((i,))*240 if i<4 else bytes(rng.randrange(256)for _ in range(240));f.m.load(0x88c4,packet);f.m.write(0x89c0,0)
   before=f.read(0,65536);r,n=f.fast_call(labels['packet_crc']);after=f.read(0,65536);wanted=bytearray(before);wanted[0x100:0x200]=after[0x100:0x200]
   at=f.s['se_crc_value'];wanted[at:at+2]=binascii.crc_hqx(packet,65535).to_bytes(2,'little')
   assert after==wanted and g.reu()==reu and f.read(0xb000,len(payload))==payload,(i,'CRC wholeRAM/REU/code guard');costs.append(n)
  result=dict(status='PASS',identity=g.identity,seal=seal,table_words=256,packets=132,authority_bytes={k:f.s[k]for k in ('se_i_ready','se_i_count','se_n_cache_count')},changed_RAM_only='512B tables + these three authority bytes + call stack; packet kernel CRC+stack only',whole_REU_unchanged=True,instruction_min=min(costs),instruction_max=max(costs))
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('CRC_PASS',out,flush=True);return result
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BAD);p.add_argument('--expect-bad',action='store_true');p.add_argument('--reverse',action='store_true');p.add_argument('--file-open',action='store_true');p.add_argument('--extended',action='store_true');p.add_argument('--far',action='store_true');p.add_argument('--crc',action='store_true');a=p.parse_args();out=ROOT/'build/grid-capture-index'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);crc(out,a.fixture.resolve())if a.crc else run(out,a.fixture.resolve(),a.expect_bad,a.reverse,a.file_open,a.extended,a.far)

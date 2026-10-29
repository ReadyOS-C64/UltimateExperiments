"""Private compact-record feasibility, not an integrated/trusted FE glyph cache."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,subprocess,sys
import test_geos_catalog_byte_candidate as component
ROOT=component.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T112646631270Z/fixture'
SOURCE=ROOT/'src/render/geos/preview-glyph-cache-candidate/codec.s'


def run(out,base,smoke=False):
    leaf=out/'r23';symbols,size=component.build(leaf,base,False)
    report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols']
    codec=out/'codec';codec.mkdir()
    for cmd in [
      ['ca65','-g','-I',leaf/'includes','-o',codec/'codec.o',SOURCE],
      [sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',codec/'binding.s',codec/'codec.o'],
      ['ca65','-o',codec/'binding.o',codec/'binding.s']]:component.command(*cmd)
    (codec/'cfg').write_text('MEMORY{C:file=%O,start=$B000,size=$1000;}SEGMENTS{CODE:load=C,type=ro;}')
    component.command('ld65','-C',codec/'cfg','-o',codec/'codec.bin','-Ln',codec/'codec.lbl',codec/'codec.o',codec/'binding.o')
    cs=component.symbols(codec/'codec.lbl');code=(codec/'codec.bin').read_bytes()
    component.geos.grid.editor_fixture.ROOT=component.geos.grid.cpu_editor.ROOT=base
    names=json.loads((base/'freeze.json').read_text())['names']
    component.geos.grid.editor_fixture.NAMES=component.geos.grid.cpu_editor.NAMES=names
    (out/'runner').mkdir()
    dll=component.geos.grid.runner(out/'runner')
    f=component.Fixture(out/'machine',base,dll,leaf)
    pack=(leaf/'font-pack.bin').read_bytes();entry=pack[32+42*16:48+42*16]
    off=int.from_bytes(entry[8:11],'little');raw=pack[off:off+int.from_bytes(entry[11:13],'little')]
    assert entry[0]==2 and len(raw)==744
    baseline=f.reu();cases=[]
    try:
      f.m.load(0xb000,code)
      for value in ([0x41,0x47,0x20]if smoke else range(256)):
       for style in ([0,7]if smoke else range(8)):
        for inverse in (0,1):
         r,frame,cost=f.glyph(entry,value,style,inverse);assert not r.p&1
         metrics,ink,coverage=component.oracle(raw,(ROOT/'assets/fonts/generated/native8.bin').read_bytes(),value,0,style,inverse,(0,32,0,24))
         assert frame[14:20]==metrics and frame[20:56]==ink[:36]
         before=f.read(0,65536);r,packcost=f.fast_call(cs['glyph_pack']);assert not r.p&1,(value,style,inverse,'pack',r.a)
         record=f.read(0x8a00,32);expected=bytearray(32);expected[0]=0xa1;expected[1:4]=bytes((value,style,inverse));expected[4:9]=metrics[1:]
         expected[10:28]=b''.join(ink[y*4:y*4+2]for y in range(9));expected[28:30]=binascii.crc_hqx(expected[1:28],0xffff).to_bytes(2,'little')
         assert record==expected
         after=f.read(0,65536);want=bytearray(before)
         for a,b in [(0x100,0x200),(0x8a00,0x8a20),(s['se_crc_value'],s['se_crc_value']+2)]:want[a:b]=after[a:b]
         assert after==want,'pack fullRAM'
         f.m.load(0x880e,bytes([0xa7])*42);before=f.read(0,65536)
         r,hitcost=f.fast_call(cs['glyph_unpack']);assert not r.p&1,(value,style,inverse,'unpack',r.a)
         after=f.read(0,65536);want=bytearray(before)
         for a,b in [(0x100,0x200),(0x880e,0x8838),(s['se_crc_value'],s['se_crc_value']+2)]:want[a:b]=after[a:b]
         assert after==want,'unpack fullRAM'
         assert after[0x880e:0x8814]==metrics and after[0x8814:0x8838]==ink[:36]
         cases.append(dict(value=value,style=style,inverse=inverse,R23_instructions=cost,pack_instructions=packcost,unpack_instructions=hitcost))
      assert f.reu()==baseline,'any16MiBREUchanged'
      faults=0
      original=f.read(0x8a00,32)
      for at in range(32):
       for bit in range(8):
        bad=bytearray(original);bad[at]^=1<<bit;f.m.load(0x8a00,bad)
        r,_=f.fast_call(cs['glyph_unpack']);assert r.p&1 and r.a==0x94 and f.m.read(0x880e)==0,(at,bit,r.a)
        faults+=1
      f.m.load(0x8a00,original)
      for at in (0xcc00+33,0xcc00+35):
       old=f.m.read(at);f.m.write(at,4 if at==0xcc00+33 else 1)
       r,_=f.fast_call(cs['glyph_unpack']);assert r.p&1 and r.a==0x94,'fixed advance role/code is part of key'
       f.m.write(at,old);faults+=1
      for owner in (0,1,2,3,5,255):
       f.m.write(s['se_f_owner'],owner);before=f.read(0,65536)
       for label in ('glyph_pack','glyph_unpack'):
        r,_=f.fast_call(cs[label]);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
        assert r.p&1 and r.a==0xb2 and after==want
       faults+=2
      result=dict(status='PASS-codec-only',fixture=str(base),resident_sha256=report['sha256'],R23_bytes=size,R23_spare=4096-size,codec_bytes=len(code),record_bytes=32,records=128,header_budget=64,FE_tail_budget=5271,layout_bytes=4160,remaining_tail=1111,cases=cases,faults=faults,full16MiB_unchanged=True,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),scope='ActualR23 outputs and independentfontoracle, actual6510 pack/unpack+CRC; codec has NO FD/FE capability guard or cache lookup/DMA/header/lifetime state. Does not prove integratedspeed or safe cacheadmission. All43otherfontprofiles stayexistingfallback; thiscomponent handlesBSW9fullclipencoding0 only.')
      (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
      print('CODEC',len(code),'R23spare',4096-size,'cases',len(cases),flush=True)
      print('MEAN',sum(x['R23_instructions']for x in cases)/len(cases),sum(x['unpack_instructions']for x in cases)/len(cases),flush=True)
      return result
    finally:f.close()


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args()
 out=ROOT/'build/geos-preview-glyph-cache-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke)

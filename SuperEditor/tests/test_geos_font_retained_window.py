"""Private retained-window contract; counter simulation is NOT a warm-load test.

Reuse the released full actual6510 font test/oracle. Only preview's redundant
load-counter check and its one obsolete counter-only assertion change. Public
strict FETCH, real cold overlay staging, and all capability faults stay strict.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, inspect, json, shutil, subprocess, zipfile
import test_geos_font_fast as fast
ROOT=fast.ROOT
BASE=ROOT/'build/geos-preview-editor/20261025T110227640130Z/fixture'
OLD=ROOT/'agentsworking/evidence/M8/20261025T065206501755Z-preview-font-fast/sources.zip'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def prepare(out,base):
    project=out/'project';project.mkdir()
    with zipfile.ZipFile(base/'product-sources.zip') as z:
        for name in z.namelist():
            if name.startswith('src/') and not name.endswith('/'):
                p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
    shutil.copytree(ROOT/'tools',project/'tools',ignore=shutil.ignore_patterns('__pycache__'))
    (project/'build/geos-font-catalog').mkdir(parents=True)
    shutil.copy2(ROOT/'build/geos-font-catalog/font-pack.bin',project/'build/geos-font-catalog/font-pack.bin')
    source=project/'src/render/geos/font-store.s';before=source.read_text()
    (out/'font-store-original.s').write_text(before)
    old='    lda S+GF_LOADS,x\n    cmp se_overlay_loads,x\n    jne @refill\n'
    assert before.count(old)==1
    source.write_text(before.replace(old,''))
    # Released proof used the strict full-output glyph adapter. Restore that
    # exact archived adapter, rather than reinterpret current ink-only output.
    with zipfile.ZipFile(OLD) as z:
        wrapper=z.read('src/render/geos/preview-row-entry.s')
    (project/'src/render/geos/preview-row-entry.s').write_bytes(wrapper)
    namespace=dict(fast.__dict__,ROOT=project)
    exec(compile(inspect.getsource(fast.build),str(Path(__file__))+':build','exec'),namespace)
    return namespace['build'],dict(frozen_fixture=str(base),frozen_sources_sha256=sha((base/'product-sources.zip').read_bytes()),font_source_before_sha256=sha(before.encode()),font_source_after_sha256=sha(source.read_bytes()),released_strict_adapter_sha256=sha(wrapper),font_pack_sha256=sha((project/'build/geos-font-catalog/font-pack.bin').read_bytes()))


class WatchedFixture(fast.Fixture):
    def __init__(self,out,s):
        super().__init__(out,s)
        source=(out/'counted.cpp').read_text()
        marker='zeropage_peddle_step_instruction(m);'
        assert source.count(marker)==1
        extra='''static unsigned window_writes=0,armed_writes=0;
extern "C" unsigned fw_writes(){return window_writes;}
extern "C" unsigned fw_armed(){return armed_writes;}
'''
        check='''{auto r=zeropage_peddle_regs(m);auto p=r.pc;
if(zeropage_peddle_read(m,p)==0x8d&&zeropage_peddle_read(m,p+1)==1&&zeropage_peddle_read(m,p+2)==0xdf&&(r.a&0x91)==0x91){
unsigned address=zeropage_peddle_read(m,WINDOW_LO)+(zeropage_peddle_read(m,WINDOW_HI)<<8);
unsigned length=zeropage_peddle_read(m,LENGTH_LO)+(zeropage_peddle_read(m,LENGTH_HI)<<8);
if(address<0x6072&&address+length>0x5000){window_writes++;if(zeropage_peddle_read(m,0xcbd5))armed_writes++;}}}
'''.replace('WINDOW_LO',str(s['se_reu_c64'])).replace('WINDOW_HI',str(s['se_reu_c64']+1)).replace('LENGTH_LO',str(s['se_reu_length'])).replace('LENGTH_HI',str(s['se_reu_length']+1))
        source=extra+source.replace(marker,check+marker)
        (out/'watched.cpp').write_text(source)
        from peddle import VENDOR
        import sys
        ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('watched'+ext)
        subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(VENDOR),str(out/'watched.cpp'),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True,capture_output=True)
        lib=C.CDLL(str(path))
        for n in ('gf_run','gf_ram','gf_reu','gf_io','gf_info','gf_crc_watch','gf_crc_count'):
            old=getattr(self.r,n);getattr(lib,n).argtypes=old.argtypes;getattr(lib,n).restype=old.restype
        lib.fw_writes.restype=lib.fw_armed.restype=C.c_uint32;self.r=lib
        global LAST
        LAST=self
    def close(self):
        self.window_writes=self.r.fw_writes();self.armed_writes=self.r.fw_armed()
        assert self.armed_writes==0,(self.window_writes,self.armed_writes)
        super().close()


def run(out,base,smoke=False):
    builder,identity=prepare(out,base.resolve())
    source=inspect.getsource(fast.run)
    old="r,_,crc,dma=f.fetch();assert not r.p&1 and crc==length and dma\n        faults.append('changedloadwitness cannotshortcut strictrefill')"
    new="r,_,crc,dma=f.fetch();assert not r.p&1 and crc==dma==0 and f.read(0x5000,length)==raw\n        faults.append('MANUALcounter-onlychange retainsarmedfont; NOT actualwarmoverlayload evidence')"
    assert source.count(old)==1
    source=source.replace('for st in (0,1,2,7)','for st in range(8)')
    ns=dict(fast.__dict__,build=builder,Fixture=WatchedFixture)
    exec(compile(source.replace(old,new),str(Path(__file__))+':released-run','exec'),ns)
    result=ns['run'](out,smoke)
    # Default/non-preview object bytes are identical: the strict public entry
    # and its load-witness/fullCRC behavior have not changed at all.
    project=out/'project'
    default_ns=dict(fast.public.__dict__,ROOT=project)
    exec(compile(inspect.getsource(fast.public.build),str(Path(__file__))+':strict-build','exec'),default_ns)
    default_ns['build'](out/'strict-candidate')
    runtime=project/'src/render/geos/font-store.s';candidate=runtime.read_bytes()
    runtime.write_bytes((out/'font-store-original.s').read_bytes())
    try:default_ns['build'](out/'strict-control')
    finally:runtime.write_bytes(candidate)
    assert (out/'strict-candidate/fixture.bin').read_bytes()==(out/'strict-control/fixture.bin').read_bytes()
    strict_ns=dict(fast.public.__dict__,build=default_ns['build'])
    exec(compile(inspect.getsource(fast.public.run),str(Path(__file__))+':strict-run','exec'),strict_ns)
    strict_result=strict_ns['run'](out/'strict-suite',smoke)
    result['strict_default_byte_identity']=True
    result['strict_suite_result']=str(out/'strict-suite/result.json')
    result['strict_suite_fault_groups']=strict_result['fault_groups']
    writes,armed=LAST.window_writes,LAST.armed_writes
    assert writes>0
    # Native fallback bypasses the catalog, preserving the complete public
    # output contract rather than the production ink-only specialization.
    extra=out/'extra';symbols=builder(extra);f=WatchedFixture(extra,symbols)
    native_cases=0
    try:
        font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
        before=f.reu();shim=f.read(0xc600,1024)
        for value in (range(32,35) if smoke else range(256)):
            for style in range(8):
                for inverse in (0,1):
                    f.m.load(0xcc00+18,bytes((0,1,0,8,1,6,0)))
                    for at,v in ((34,value),(32,style),(65,inverse),(33,0),(35,0)):
                        f.m.write(0xcc00+at,v)
                    r,_,crc,dma=f.fetch('entry');assert not r.p&1 and crc==dma==0
                    frame=f.read(0x8800,240)
                    metrics,ink,coverage=fast.oracle(b'',font,value,0,style,inverse,(0,32,0,24),native_only=True)
                    assert frame[14:20]==metrics and frame[20:116]==ink and frame[116:212]==coverage,(value,style,inverse,'native-fallback')
                    native_cases+=1
        assert f.reu()==before and f.read(0xc600,1024)==shim
        # Actual cold font IEC BEGIN must disarm an old caller-owned window
        # before its first byte read/stage write. Properly release old FD
        # allocations first; no raw provider-map or source substitution.
        for h in f.read(0xcbc1,2):assert not f.call('se_reu_free',x=h).p&1
        f.m.load(0xcbc0,bytes(64));f.m.write(0xcbd5,0x81)
        pack=(ROOT/'build/geos-font-catalog/font-pack.bin').read_bytes();f.io(pack)
        window=f.read(0x5000,256);r=f.call('se_gf_import_begin',8)
        assert not r.p&1 and r.a==1 and f.m.read(0xcbd5)==0 and f.read(0x5000,256)==window and f.info()[7]==0
        steps=0
        while r.a==1:
            r=f.call('se_gf_import_step');assert not r.p&1
            steps+=1;assert steps<300
        assert f.info()[0]==len(pack) and f.info()[1:4]==[1,1,0] and not f.info()[6]
        for i,h in enumerate(f.read(0xcbc1,2)):
            physical=f.m.read(symbols['se_reu_map']+h);part=pack[i*65536:(i+1)*65536]
            assert f.reu()[physical*65536:physical*65536+len(part)]==part
        result['native_fallback_glyphs']=native_cases
        result['cold_IEC_import']=dict(steps=steps,bytes=len(pack),begin_disarms_before_first_CHRIN=True,rom_model_only=True)
    finally:f.close()
    result.update(retained_window_identity=identity,pre_DMA_window_writes=writes+f.window_writes,armed_before_window_DMA=armed+f.armed_writes,counter_test_scope='Manual16bit counter perturbation only; actual memo/direct warm loader integration is outside this private component proof.',native_or_warm_loader_claim=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('RETAINED PASS',json.dumps(dict(faces=len(result['faces']),glyphs=sum(x['glyphs']for x in result['faces']),window_writes=result['pre_DMA_window_writes'],armed_writes=result['armed_before_window_DMA'])),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args()
    out=ROOT/'build/geos-font-retained-window'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,a.fixture,a.smoke)

"""Managed type53 page-proof invalidation and failure-cleanup regression.

Uses explicit immutable before/current fixtures. Independently links each native
module byte-identically to its own resident, then compares both implementations
at the current ABI addresses. No shared build, production substitution or native
claim. Source/lease fixtures use actual editor/object/provider/R14 code; the C21
eligibility test is explicitly an extracted instruction unit.
"""
from pathlib import Path
from datetime import datetime, timezone
from zipfile import ZipFile
import argparse
import ctypes as C
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'tools')]
import test_grid_modes as grid
from peddle import Machine

BEFORE = ROOT/'build/cache-editor-product/20261026T001942640938Z/fixture'
FILES = ('src/reu/dma.s', 'src/render/geos/dispatch.s', 'src/render/geos/page.s')


def command(args):
    done = subprocess.run(list(map(str, args)), cwd=ROOT, text=True, capture_output=True)
    assert not done.returncode, (args, done.stdout, done.stderr)
    return done.stdout


def labels(path):
    return {name: int(address, 16) for address, name in
            re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)', path.read_text())}


def sizes(path):
    return {name: int(value) for name, value in re.findall(
        r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',
        command(['od65', '--dump-segments', path]), re.S)}


def fixture_report(fixture):
    report = json.loads((fixture/'build/editor-report.json').read_text())
    assert hashlib.sha256((fixture/'build/editor.prg').read_bytes()).hexdigest() == report['sha256']
    frozen = json.loads((fixture/'freeze.json').read_text())
    assert report['sha256'] == frozen['prg_sha256']
    for name, sha in frozen['assets'].items():
        assert hashlib.sha256((fixture/'build/overlays'/(name+'.seo')).read_bytes()).hexdigest() == sha
    return report


def build(out, fixture, before_fixture):
    reports = {name: fixture_report(path) for name, path in
               [('before', before_fixture), ('after', fixture)]}
    budgets = {}
    for variant, base in [('before', before_fixture), ('after', fixture)]:
        directory = out/variant
        with ZipFile(base/'product-sources.zip') as archive:
            for name in archive.namelist():
                if name.startswith('src/') and (name.endswith('.inc') or name in FILES):
                    target = directory/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
        for tag, name in [('dma', FILES[0]), ('dispatch', FILES[1])]:
            source = directory/name
            obj = source.with_suffix('.o')
            defines = ['-D', 'EDITOR_MANAGED_CODE=1'] if tag == 'dma' else []
            command(['ca65', '-g', *defines, '-I', directory/'src', '-o', obj, source])
            budgets[variant+':'+tag] = sizes(obj)
            assert sizes(obj)['ZEROPAGE'] == 0
            for profile, resident in [('native', base), ('common', fixture)]:
                report = reports[variant] if profile == 'native' else reports['after']
                symbols = report['symbols']
                linked = directory/(tag+'-native' if profile == 'native' else tag)
                linked.mkdir()
                command([sys.executable, ROOT/'tools/module_bindings.py', '--report',
                         resident/'build/editor-report.json', '--output', linked/'aliases.s', obj])
                command(['ca65', '-o', linked/'aliases.o', linked/'aliases.s'])
                address = symbols['se_reu_copy' if tag == 'dma' else 'se_geos_render']
                bss = f'B:file="",start=${symbols["se_reu_c64"]:04X},size=16;' if tag == 'dma' else ''
                segment = 'BSS:load=B,type=bss;' if tag == 'dma' else ''
                (linked/'image.cfg').write_text(f'MEMORY{{C:file=%O,start=${address:04X},size=$1000;{bss}}}SEGMENTS{{CODE:load=C,type=ro;{segment}}}')
                command(['ld65', '-C', linked/'image.cfg', '-o', linked/'image.bin',
                         '-Ln', linked/'image.lbl', obj, linked/'aliases.o'])
                if profile == 'native':
                    raw = (resident/'build/editor.prg').read_bytes()
                    load = int.from_bytes(raw[:2], 'little')
                    code = (linked/'image.bin').read_bytes()
                    assert code == raw[2+address-load:2+address-load+len(code)], (variant, tag, 'native CODE mismatch')
            if tag == 'dma':
                # Generic output is compared with the same current addresses;
                # object debug/source filenames need not be byte-identical.
                linked = directory/'generic'
                linked.mkdir()
                obj = linked/'dma.o'
                command(['ca65', '-I', directory/'src', '-o', obj, source])
                command([sys.executable, ROOT/'tools/module_bindings.py', '--report',
                         fixture/'build/editor-report.json', '--output', linked/'aliases.s', obj])
                command(['ca65', '-o', linked/'aliases.o', linked/'aliases.s'])
                symbols = reports['after']['symbols']
                (linked/'image.cfg').write_text(f'MEMORY{{C:file=%O,start=${symbols["se_reu_copy"]:04X},size=$1000;B:file="",start=${symbols["se_reu_c64"]:04X},size=16;}}SEGMENTS{{CODE:load=C,type=ro;BSS:load=B,type=bss;}}')
                command(['ld65', '-C', linked/'image.cfg', '-o', linked/'image.bin', obj, linked/'aliases.o'])
    assert (out/'before/generic/image.bin').read_bytes() == (out/'after/generic/image.bin').read_bytes(), 'generic CODE changed'
    assert 'BC_PAGE_PROOF' not in (out/'before'/FILES[0]).read_text()
    assert 'BC_PAGE_PROOF' in (out/'after'/FILES[0]).read_text()
    assert budgets['before:dma']['BSS'] == budgets['after:dma']['BSS'] == 16
    (out/'budget.json').write_text(json.dumps(budgets, indent=2)+'\n')
    return reports


def dma_proof(OUT, BASE):
 S=json.loads((BASE/'build/editor-report.json').read_text())['symbols']
 D=OUT/'proof';D.mkdir(exist_ok=True);dll=grid.runner(D);cpp=D/'runner.cpp';t=cpp.read_text();needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);';assert t.count(needle)==1
 extra=r'''
 static uint16_t proof_flags=0,proof_unverify=0;static unsigned proof_dma=0,proof_calls=0,proof_sp=255;static uint8_t proof_at_dma=0;
 extern "C" void pf_begin(uint16_t f,uint16_t u){proof_flags=f;proof_unverify=u;proof_dma=proof_calls=proof_at_dma=0;proof_sp=255;}
 extern "C" unsigned pf_get(unsigned i){return i==0?proof_dma:i==1?proof_calls:i==2?proof_at_dma:proof_sp;}
 static void pf_step(ZeroPagePeddle*m,uint16_t pc){if(!proof_flags)return;auto r=zeropage_peddle_regs(m);if(r.sp<proof_sp)proof_sp=r.sp;if(pc==proof_unverify)proof_calls++;if(zeropage_peddle_read(m,pc)==0x8d&&zeropage_peddle_read(m,pc+1)==1&&zeropage_peddle_read(m,pc+2)==0xdf){proof_dma++;proof_at_dma=zeropage_peddle_read(m,proof_flags);}}
 '''
 t=t.replace(needle,extra+needle+'pf_step(m,r.pc);');cpp.write_text(t)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(grid.VENDOR),str(cpp),str(ROOT/'build/libse_peddle.dylib'),'-o',str(D/'proof.dylib')],check=True)
 new=C.CDLL(str(D/'proof.dylib'))
 for n in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu'):
  a,b=getattr(dll,n),getattr(new,n);b.argtypes,b.restype=a.argtypes,a.restype
 new.pf_begin.argtypes=[C.c_uint16,C.c_uint16];new.pf_get.argtypes=[C.c_uint];new.pf_get.restype=C.c_uint
 names=json.load(open(BASE/'freeze.json'))['names'];grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=BASE;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=names
 f=grid.Fixture(D,BASE,new);f.source(b'Canonical source untouched.\rOther.');s=f.s
 # Real type53 allocation plus real provider-owned comparison classes.
 r,_=f.fast_call(s['se_object_create'],a=0x53,x=1);assert not r.p&1;token=f.read(s['se_object_id'],5);f.put('se_object_offset',65536);assert not f.call('se_object_resize').p&1
 handles={0x53:f.m.read(s['object_extents']+token[0]*16),2:f.get('se_overlay_asset',1)}
 for owner in (7,0xa5,0xfe):
  r,_=f.fast_call(s['se_reu_alloc'],a=owner);assert not r.p&1;handles[owner]=r.a
 # No physical identity assumption.
 assert all(f.m.read(s['se_reu_logical_owner']+h)==o for o,h in handles.items())
 raw=(BASE/'build/editor.prg').read_bytes();load=int.from_bytes(raw[:2],'little');images={v:(OUT/v/'dma/image.bin').read_bytes()for v in ('before','after')};base=s['se_reu_copy'];maxcode=max(map(len,images.values()))
 def allreu():
  b=C.create_string_buffer(16*1024*1024);new.gm_reu(f.m.handle,len(b),b);return b.raw
 def execute(variant,ram,direction,p):
  f.m.load(0,ram);f.m.load(base,images[variant]);new.pf_begin(s['se_bc_flags'],s['se_overlay_unverify'])
  for n,v in [('pc',base),('sp',0xfd),('p',p),('a',direction),('x',0x59),('y',0xa7)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
  f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);n=new.gm_run(f.m.handle,100000);assert n
  r=f.m.regs();out=f.read(0,65536);normalized=bytearray(out);normalized[0x100:0x200]=bytes(256);normalized[base:base+maxcode]=bytes(maxcode)
  return (r.a,r.x,r.y,r.p,r.sp),out,normalized,[new.pf_get(i)for i in range(4)]
 records=[];cases=0
 canonical=f.canonical();objects=f.read(s['object_owner'],184);provider=f.read(s['se_reu_map'],768)
 def case(owner,direction,p=0x24,flags=0xb5,invalid=None,whole=True):
  nonlocal cases
  f.m.load(load,raw[2:]);f.m.load(0x5000,bytes(range(16)));f.put('se_reu_logical',handles[owner],1);f.put('se_reu_c64',0x5000,2);f.put('se_reu_offset',0xf120,2);f.put('se_reu_length',16,2);f.put('se_bc_flags',flags,1);f.m.write(0xcc4d,0xa5);f.m.write(0xcbd5,0xa5)
  if invalid=='physical-owner':f.m.write(s['se_reu_physical_owner']+f.m.read(s['se_reu_map']+handles[owner]),0x77)
  elif invalid=='unowned-logical':f.put('se_reu_logical',next(i for i in range(1,256)if f.m.read(s['se_reu_logical_owner']+i)==0),1)
  elif invalid=='zero-length':f.put('se_reu_length',0,2)
  elif invalid=='cpu-low':f.put('se_reu_c64',0x3fff,2)
  elif invalid=='cpu-high':f.put('se_reu_c64',0xbfff,2)
  elif invalid=='bank-cross':f.put('se_reu_offset',0xffff,2)
  ram=f.read(0,65536);prior=allreu()if whole else None
  a=execute('before',ram,direction,p);ar=allreu()if whole else None;b=execute('after',ram,direction,p);br=allreu()if whole else None
  assert a[3][3]==b[3][3],('stack peak changed',a[3],b[3])
  assert a[0]==b[0],(owner,direction,invalid,'API registers',a[0],b[0])
  expected=flags&0xdf if owner==0x53 and direction==0 and invalid is None else flags
  a[2][s['se_bc_flags']]=expected
  assert a[2]==b[2],(owner,direction,invalid,'wholeRAM-differential',next((hex(i),x,y)for i,(x,y)in enumerate(zip(a[2],b[2]))if x!=y))
  assert b[1][s['se_bc_flags']]==expected
  valid=invalid is None and direction in (0,1)
  assert b[3][0]==int(valid),(owner,direction,invalid,b[3],b[0])
  if valid:assert b[3][2]==expected,('not revoked before DF01',b[3],expected)
  assert a[3][1]==b[3][1]==int(owner==2 and direction==0 and valid)
  if whole:
   assert br==ar
   want=bytearray(prior)
   if valid and direction==0:
    physical=f.m.read(s['se_reu_map']+handles[owner]);lo=physical*65536+0xf120;want[lo:lo+16]=bytes(range(16))
   assert br==want,(owner,direction,invalid,'16MiB span guard')
  assert f.read(0xc600,1024)==f.shim and f.canonical()==canonical
  # Fault injection only touches the selected ownership byte; source object
  # catalog stays exact, and the candidate never mutates mapping/ownership.
  assert f.read(s['object_owner'],184)==objects
  if invalid=='physical-owner':f.m.write(s['se_reu_physical_owner']+f.m.read(s['se_reu_map']+handles[owner]),owner)
  assert f.read(s['se_reu_map'],768)==provider
  cases+=1
  if whole:records.append(dict(owner=owner,direction=direction,P=p,flags=flags,invalid=invalid,after_flags=expected,hardware_DF01=b[3][0],unverify_calls=b[3][1]))
 try:
  for owner in handles:
   for direction in (0,1):
    for p in (0x20,0x24,0x64):case(owner,direction,p)
  for fault in ('physical-owner','unowned-logical','zero-length','cpu-low','cpu-high','bank-cross'):
   for direction in (0,1):case(0x53,direction,invalid=fault)
  for direction in (2,255):case(0x53,direction,invalid='direction')
  for flags in range(256):
   for direction in (0,1):case(0x53,direction,flags=flags,whole=False)
  result={'status':'passed','cases':cases,'whole16MiB_cases':len(records),'flags_domain':256,'source':str(BASE),'resident_sha256':json.load(open(BASE/'build/editor-report.json'))['sha256'],'before_CODE_byteidentical_to_actual_resident':True,'default_generic_CODE_byteidentical':True,'API':'A/X/Y/P/SP differential exact including IRQ I0/I1 and V0/V1','before_hardware_write':'BC_PAGE_PROOF observed cleared before STA DF01 for successful owner53 stash only','records':records}
  (OUT/'proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='records'},indent=2))
 finally:f.close()
 return result


def failure_proof(OUT, BASE):
 s=json.loads((BASE/'build/editor-report.json').read_text())['symbols']
 cmd=command
 # Exact changed C21 admission branch as a bounded instruction unit; the
 # independent predicate covers all flags including ACTIVE/MUTATING hazards.
 src=(OUT/'after/src/render/geos/page.s').read_text();body=src[src.index('begin:\n'):src.index('    lda GEC_VALID\n',src.index('begin:\n'))]
 syms=set(re.findall(r'\bse_\w+',body))
 head='.setcpu "6502"\n.macpack longbranch\n.include "cache/api.inc"\n.segment "CODE"\n'
 head+='\n'.join(n+'=$%04X'%s[n]for n in sorted(syms))+'\n'
 code=head+body+'    rts\nbusy: lda #$b2\nsec\nrts\nrequest: sta $9135\nstx $9136\nlda #1\nclc\nrts\n.export begin\n'
 (OUT/'schedule.s').write_text(code);cmd(['ca65','-g','-I',OUT/'after/src','-o',OUT/'schedule.o',OUT/'schedule.s']);(OUT/'schedule.cfg').write_text('MEMORY{C:file=%O,start=$3000,size=$1000;}SEGMENTS{CODE:load=C,type=ro;}');cmd(['ld65','-C',OUT/'schedule.cfg','-o',OUT/'schedule.bin',OUT/'schedule.o'])
 m=Machine();m.load(0x3000,(OUT/'schedule.bin').read_bytes());schedule_cases=0
 for owner in (0,1,4):
  for caps in (0,1,3,255):
   for flags in range(256):
    m.write(s['se_f_owner'],owner);m.write(s['se_render_caps'],caps);m.write(s['se_bc_flags'],flags)
    for name in ('se_i_ready','se_i_count','se_n_cache_count'):m.write(s[name],0xa5)
    m.write(0x9135,0xa5);m.write(0x9136,0xa5)
    r,n=m.call(0x3000)
    eligible=owner==0 and caps!=0 and flags&0x1f==2
    assert m.read(s['se_bc_flags'])==(18 if eligible else flags),(owner,caps,flags)
    assert (m.read(0x9135),m.read(0x9136))==((7,9)if eligible else(0xa5,0xa5))
    assert m.read(s['se_f_owner'])==(4 if owner==0 else owner)
    if owner:assert (r.a,r.p&1)==(0xb2,1)
    elif eligible:assert (r.a,r.p&1)==(1,0)
    for name in ('se_i_ready','se_i_count','se_n_cache_count'):assert m.read(s[name])==(0 if owner==0 else 0xa5)
    schedule_cases+=1
 m.close()
 D=OUT/'failures';D.mkdir(exist_ok=True);dll=grid.runner(D);names=json.load(open(BASE/'freeze.json'))['names'];grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=BASE;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=names
 f=grid.Fixture(D,BASE,dll);f.source(b'Actual lease source.\rNo mutation.');canonical=f.canonical()
 images={v:(OUT/v/'dispatch/image.bin').read_bytes()for v in ('before','after')};lbl={v:labels(OUT/v/'dispatch/image.lbl')for v in images};base=s['se_geos_render'];maxlen=max(map(len,images.values()))
 raw=(BASE/'build/editor.prg').read_bytes();load=int.from_bytes(raw[:2],'little');records=[]
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def check(tag,flags,owner=4,lease=None,stale=None):
  f.m.load(load,raw[2:]);f.put('se_f_owner',4,1);f.put('se_bc_flags',flags,1);f.m.write(0x912d,0);f.m.write(0x912c,0);f.m.load(0x8d00,bytes(576));f.m.load(s['se_fs_state'],bytes(86))
  if lease:
   f.put('se_overlay_frame',0,1);r,n=f.fast_call(s['se_overlay_call'],a=14,x=0);assert not r.p&1 and f.get('se_doc_read_locks',1)==1
   data=bytearray(f.read(s['se_fs_state'],86))
   if stale:data[27 if stale=='provider'else 33]^=1 #explicit captured-context fault, not current source mutation
   if lease=='cache':f.m.load(0x8d00+173,data)
   else:f.m.load(0x9040,data);f.m.write(0x912d,1)
  f.put('se_f_owner',owner,1);ram=f.read(0,65536);before=reu();values=[]
  for variant in ('before','after'):
   f.m.load(0,ram);f.m.load(base,images[variant]);r,n=f.fast_call(lbl[variant]['failed'],a=0x17)
   after=f.read(0,65536);normalized=bytearray(after);normalized[0x100:0x200]=bytes(256);normalized[base:base+maxlen]=bytes(maxlen)
   assert reu()==before and f.canonical()==canonical and f.read(0xc600,1024)==f.shim
   assert f.get('se_doc_read_locks',1)==int(bool(stale))
   values.append(((r.a,r.x,r.y,r.p,r.sp),normalized,f.get('se_bc_flags',1)))
  # Old unconditional stamp is intentionally removed for an unrelated error
  # after a fresh H_INIT. Attempted builds already have TRIED, while ACTIVE
  # cancellation supplies it even if a damaged caller omitted it.
  expected=(flags&~8)|16 if owner==4 and flags&8 else flags
  assert values[1][2]==expected,(tag,values)
  values[0][1][s['se_bc_flags']]=expected
  assert values[0][:2]==values[1][:2],(tag,'non-flag cleanup difference')
  records.append(dict(tag=tag,owner=owner,prior_flags=flags,old_flags=values[0][2],new_flags=expected,lease=lease,stale_capture=stale,readlocks_after=int(bool(stale))))
  if stale:f.put('se_doc_read_locks',0,1) #external test holder releases its protected foreign lock
 try:
  check('C7missing-after-C21-attempt',18)
  check('C34missing-before-BEGIN',18)
  check('C34local-error-already-cancelled',18)
  check('C34active-missing-owns-lease',26,lease='cache')
  check('C35active-missing-owns-lease',25,lease='cache')
  check('C35page-proof-active-missing',57,lease='cache')
  check('C35published-proof-error-before-source-BEGIN',49)
  check('cache-stale-provider-capture-refuses-foreign-lease',26,lease='cache',stale='provider')
  check('cache-stale-token-capture-refuses-foreign-lease',25,lease='cache',stale='tokens')
  check('active-cancel-stamps-even-if-caller-omitted',10,lease='cache')
  check('legacy-source-error-held-lease',18,lease='legacy')
  for owner in (0,1,3):check('unrelated-error-already-tried-owner'+str(owner),18,owner)
  for owner in (0,1,4):check('fresh-HINIT-unrelated-error-does-not-poison-owner'+str(owner),2,owner)
  result={'status':'passed','schedule_flag_cases':schedule_cases,'failed_cases':len(records),'source':str(BASE),'records':records,'scope':'Changed C21 eligibility instruction unit plus real resident failed/epoch-safe END paths with actual R14-acquired leases. No C34/C35 worker or native substitute claim.'};(OUT/'failure-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
 return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--before-fixture', type=Path, default=BEFORE)
    args = parser.parse_args()
    if not args.run:
        print('Prepared: --run --fixture CURRENT --before-fixture PREHOOK. Private CPU only.')
        return
    assert args.fixture, 'explicit immutable current fixture required'
    assert (ROOT/'build/libse_peddle.dylib').exists(), 'existing CPU runtime required'
    out = ROOT/'build/cache-proof-invalidation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    current, before = args.fixture.resolve(), args.before_fixture.resolve()
    reports = build(out, current, before)
    dma = dma_proof(out, current)
    failures = failure_proof(out, current)
    result = dict(status='passed', fixture=str(current), before_fixture=str(before),
                  before_sha256=reports['before']['sha256'], current_sha256=reports['after']['sha256'],
                  native_before_and_after_CODE_match_own_resident=True,
                  generic_off_CODE_identical=True,
                  DMA_cases=dma['cases'], whole16MiB_cases=dma['whole16MiB_cases'],
                  schedule_cases=failures['schedule_flag_cases'], failed_cases=failures['failed_cases'],
                  scope='Managed checked-write notification; full source/capability guards remain required. '
                        'No raw hardware corruption guarantee, complete query-consumer or native timing claim.')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('RESULT', json.dumps(result), flush=True)


if __name__ == '__main__':
    main()

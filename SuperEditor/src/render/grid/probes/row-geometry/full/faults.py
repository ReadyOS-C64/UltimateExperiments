"""Actual C6 mutation + C33/R24 boundary fault gates, bounded CPU pause seam."""
from pathlib import Path
import ctypes as C,hashlib,importlib.util,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_hotpath_profile as profile
observer=profile.observer
BASE_RUNNER=observer.runner

def runner(out):
 old=BASE_RUNNER(out);p=out/'runner.cpp';s=p.read_text();s+='''
extern "C" uint64_t rg_until(ZeroPagePeddle*m,uint16_t pc,uint16_t active,uint8_t tag,uint64_t max){auto before=zeropage_peddle_regs(m).instructions;
 for(uint64_t i=0;i<max;i++){auto r=zeropage_peddle_regs(m);if(r.pc==pc && zeropage_peddle_read(m,active)==tag)return r.instructions-before+1;if(r.pc==0x2ff)return 0;step(m);}return 0;}
''';p.write_text(s);ext='.dylib'if sys.platform=='darwin'else'.so';target=out/('pause'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(observer.geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(target)],check=True)
 dll=C.CDLL(str(target))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_end','fr_mask','fr_bad','fr_writes','pb_config','pb_begin','pb_end','pb_get','pb_fault_get','ob_ring','ob_ring_get'):
  a,b=getattr(old,name),getattr(dll,name);b.argtypes,b.restype=a.argtypes,a.restype
 dll.rg_until.argtypes=[C.c_void_p,C.c_uint16,C.c_uint16,C.c_uint8,C.c_uint64];dll.rg_until.restype=C.c_uint64;return dll

def run(out,base,labels):
 out.mkdir(parents=True);saved=observer.runner;observer.runner=runner
 try:g=observer.Gate(out,base)
 finally:observer.runner=saved
 f=g.f;symbols={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',labels.read_text())};tag=g.identity['names'].index('geosfold')+1;cases=[]
 r25={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(labels.parents[1]/'c33/geostail.lbl').read_text())}
 def start():
  f.put('se_overlay_frame',1,1)
  for n,v in [('pc',f.s['se_overlay_call']),('sp',0xfd),('p',0x24),('a',33),('x',1),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
  f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2)
 def restore(regs,stack):
  f.m.load(0x100,stack)
  for n in('pc','sp','p','a','x','y'):getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,getattr(regs,n))
 def fe_write(offset,raw):
  # Explicit fault transport only, preserving the suspended real CPU stack.
  regs=f.m.regs();stack=f.read(0x100,256);f.m.load(0x8880,raw)
  f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8880,2);f.put('se_reu_length',len(raw),2);assert not f.call('se_reu_copy',0).p&1;restore(regs,stack)
 def setup(width):
  data=b'A'*(width-1)+b'\rUntouched tail.\r';f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(5);profile.drain(f);f.key(observer.Q);return data[:5]+bytes([observer.Q])+data[5:]
 try:
  for width in(60,80):
   specs=[('boundary-source-revision','rg_boundary'),('prepare-source-token','rg_prepare'),('prepare-FE-map','rg_prepare'),('prepare-physicalFE','rg_prepare'),('prepare-live-mode','rg_prepare'),('prepare-header-phase', 'rg_prepare'),('prepare-packet-payload','rg_prepare'),('prepare-header-payload','rg_prepare'),('prepare-new-source-revision','rg_prepare'),('prepare-new-gap','rg_prepare'),('prepare-FEepoch','rg_prepare'),('prepare-foreignFE','rg_prepare'),('prepare-source-lease','rg_prepare'),('apply-plan-address','rg_apply'),('apply-direction','rg_apply'),('apply-lastrow','rg_apply'),('apply-new-source-revision','rg_apply'),('apply-packet-payload','rg_apply'),('late-packet-store-FE','rg_before_packet_store'),('late-header-store-FE','R25:store_header')]
   for name,point in specs:
    source=setup(width);start();assert g.dll.rg_until(f.m.handle,r25[point[4:]]if point.startswith('R25:')else symbols[point],f.s['se_overlay_active'],g.identity['names'].index('geostail')+1 if point.startswith('R25:')else tag,2000000),(name,'did not reachactualR24')
    _,bank=f.raw_cache();restore_bytes=[];restore_fe=[]
    if 'header-phase'in name:f.m.write(0x8a00+10,f.m.read(0x8a00+10)^1)
    elif 'packet-payload'in name:
     offset=240*2;raw=f.raw_cache()[0][offset:offset+1];fe_write(offset,bytes([raw[0]^1]));restore_fe.append((offset,raw))
    elif 'header-payload'in name:
     offset=0x1500+10;raw=f.raw_cache()[0][offset:offset+1];fe_write(offset,bytes([raw[0]^1]));restore_fe.append((offset,raw))
    else:
     if 'source-revision'in name:key,delta='se_r_revision',0
     elif 'new-gap'in name:key,delta='se_hot_left',0
     elif 'FEepoch'in name:key,delta='se_gc_epoch',0
     elif 'foreignFE'in name or name.startswith('late-'):key,delta='se_reu_logical_owner',f.get('se_gc_handle',1)
     elif 'source-lease'in name:key,delta='se_doc_read_locks',0
     elif 'source-token'in name:key,delta='se_doc_original',0
     elif 'FE-map'in name:key,delta='se_reu_map',f.get('se_gc_handle',1)
     elif 'physicalFE'in name:key,delta='se_reu_physical_owner',bank
     elif 'live-mode'in name:key,delta='se_mode',0
     else:key,delta=None,0
     a=f.s[key]+delta if key else(0x8d80+9 if'plan-address'in name else 0x8dff if'direction'in name else 0x8d80+91)
     v=f.m.read(a);restore_bytes.append((a,v));f.m.write(a,v^1)
    before_reu=g.reu();before_pixels=f.read(0x6000,8000)+f.read(0x4000,1000);sequence=f.get('se_e_draw_sequence',2);header=before_reu[bank*65536+0x1500:bank*65536+0x1600]
    n=g.dll.gm_run(f.m.handle,4000000);assert n and f.m.regs().a==2 and not f.m.regs().p&1,(width,name,'C33 optionalMISS',f.m.regs().a,f.m.regs().p)
    assert not f.get('se_f_owner',1)and f.get('se_e_draw_sequence',2)==sequence and g.reu()[bank*65536+0x1500:bank*65536+0x1600]==header,(name,'no partialpublication')
    assert g.reu()==before_reu,(name,'faultmustnotstashcache')
    assert f.read(0x6000,8000)+f.read(0x4000,1000)==before_pixels,(name,'faultcallitselfbeforeVICmutation')
    if point in('rg_apply','rg_before_packet_store'):assert f.read(f.s['se_gc_valid'],3)==bytes(3),(name,'priorR14paint must retaininvalidcache')
    for a,v in restore_bytes:f.m.write(a,v)
    for offset,raw in restore_fe:fe_write(offset,raw)
    if point.startswith('R25:'):
     before=g.reu();bits_before=f.read(0x6000,8000)+f.read(0x4000,1000);f.put('se_overlay_frame',1,1);r,n2=f.fast_call(f.s['se_overlay_call'],a=33,x=1);assert r.a==2 and not r.p&1 and g.reu()==before and bits_before==f.read(0x6000,8000)+f.read(0x4000,1000),'oldNCmustnotadmitafterlatecommitrefusal'
    # A real subsequent public fallback repairs pixels/header after late faults.
    f.put('se_e_redraw',1,1);profile.drain(f);assert f.merged()==source and not f.get('se_doc_read_locks',1)
    (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(name,'fallbackrepair')
    cases.append(dict(width=width,fault=name,point=point,instructions=int(n),no_partial_publication=True,repair=True));print('FAULT',width,name,flush=True)
  result=dict(status='PASS',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve())

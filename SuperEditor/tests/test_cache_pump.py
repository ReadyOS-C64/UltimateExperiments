"""Private real C34->R14/R33 automatic baseline pump, no product registration.

Retains the released writer's independent serialized-page/source/event oracle;
only its host per-output supervisor is replaced by the actual opcode pump.
Both private images are imported/admitted by the real sealed overlay loader.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as CT, hashlib, inspect, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'tools')]
import test_cache_arena as arena
import test_cache_semantic as semantic
from overlays import wrap, HEADER

F=0x8d00; C=F+387; IO=F+448


def build_pump(out, base):
    source=out.parent/'pump-source';source.mkdir()
    for name in ('worker.s','state.s','api.inc'):
        shutil.copy2(ROOT/'src/cache/semantic'/name,source/name)
    shutil.copy2(ROOT/'src/cache/editor/entry.s',source/'entry.s')
    old_d,old_command=semantic.D,semantic.command
    def command(args):
        args=list(args)
        if args[0]=='ca65' and Path(args[-1])==source/'worker.s':
            args[1:1]=['-D','BSC_SELECTOR_OWNS_OWNER=1','-D','BSC_AUTO_OWNS_CANCEL=1']
        return old_command(args)
    semantic.D,semantic.command=source,command
    try:
        linked,budget=ORIGINAL_BUILD(out,base)
        assert budget['total_bytes']<=4096,budget
        return linked,budget
    finally:semantic.D,semantic.command=old_d,old_command


def runner(out):
    old=ORIGINAL_RUNNER(out)
    path=out/'runner.cpp';text=path.read_text()
    needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
    assert text.count(needle)==1
    observer='''
static uint16_t pp_pc=0,pp_frame=0;static uint64_t pp_calls[512]={},pp_ops[8]={};
extern "C" void pp_begin(uint16_t p,uint16_t f){pp_pc=p;pp_frame=f;for(auto &v:pp_calls)v=0;for(auto &v:pp_ops)v=0;}
extern "C" uint64_t pp_get(unsigned id,unsigned slot){return pp_calls[id*2+slot];}
extern "C" uint64_t pp_op(unsigned op){return pp_ops[op];}
'''
    text=text.replace(needle,observer+needle+'if(pp_pc && r.pc==pp_pc && r.x<2){pp_calls[r.a*2+r.x]++;if(r.a==33 && r.x==0){auto o=zeropage_peddle_read(m,pp_frame);if(o<8)pp_ops[o]++;}}')
    path.write_text(text);ext='.dylib' if sys.platform=='darwin' else '.so';target=out/('pump-runner'+ext)
    subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared',
        '-fPIC','-I'+str(semantic.geos.grid.VENDOR),str(path),str(ROOT/('build/libse_peddle'+ext)),
        '-o',str(target)],check=True)
    dll=CT.CDLL(str(target))
    for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu'):
        a,b=getattr(old,name),getattr(dll,name);b.argtypes,b.restype=a.argtypes,a.restype
    dll.pp_begin.argtypes=[CT.c_uint16,CT.c_uint16];dll.pp_get.argtypes=[CT.c_uint,CT.c_uint];dll.pp_get.restype=CT.c_uint64
    dll.pp_op.argtypes=[CT.c_uint];dll.pp_op.restype=CT.c_uint64
    return dll


class PumpFixture(semantic.Fixture):
    def install(self,raw,linked):
        self.c=linked;self.pump_raw=raw;self.pump_trace=[]
        self.pump_generation=getattr(self,'pump_generation',0)+1
        if not hasattr(self,'all_pump_trace'):self.all_pump_trace=[]
        image=wrap(raw,1,34,api=(self.s['se_overlay_call'],self.s['se_overlay_frame']),
            binding_digest=bytes.fromhex(self.report['resident_binding']['digest']))
        self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:])
        assert not self.call('se_overlay_import').p&1

    def cc(self,name):
        op={'se_bsc_begin':0,'se_bsc_step':1,'se_bsc_cancel':2,'se_bsc_ack':3}.get(name,name)
        self.put('se_overlay_frame',op,1)
        ram=self.read(0,65536);canonical=self.canonical();catalog=self.catalog()
        protected=self.read(0x8800,128)+self.read(0x8c00,256)+self.read(0x9180,128)
        source_caps=b''.join(self.read(self.s[n],w)for n,w in
            [('object_owner',8),('object_gen_lo',8),('object_gen_hi',8),('object_banks',8),
             ('object_extents',128),('object_size_lo',8),('object_size_mid',8),('object_size_hi',8),
             ('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256)])
        counts=[int.from_bytes(self.read(F+i,3),'little')for i in (41,44)]
        self.dll.pp_begin(self.s['se_overlay_call'],self.s['se_overlay_frame'])
        r,n=self.fast_call(self.s['se_overlay_call'],a=34,x=1)
        self.total_instructions+=n;self.worker_peak=max(getattr(self,'worker_peak',0),n)
        calls=[(i,k,self.dll.pp_get(i,k))for i in range(256)for k in range(2)if self.dll.pp_get(i,k)]
        assert all(k==0 and i in (14,33)or k==1 and i==34 for i,k,_ in calls),calls
        assert self.dll.pp_get(33,0)<=1,('morethanoneR33request',calls)
        assert self.read(0xb000,len(self.pump_raw))==self.pump_raw,'C34 changed residency'
        active=self.m.read(self.s['se_overlay_active']+1)
        assert active and self.m.read(self.s['se_overlay_ids']+active-1)==34
        if op==1 and ram[self.s['se_f_owner']]==4 and not r.p&1:
            delta=[int.from_bytes(self.read(F+i,3),'little')-old for i,old in zip((41,44),counts)]
            assert sum(delta)<=32,('unboundedparserfeeds',delta)
            if ram[C+8]==10 and ram[F+82]:
                assert not self.dll.pp_get(33,0) and self.m.read(F+4)==self.m.read(F+82)==0
                assert not sum(delta),'ACK must not advance parser before append completed'
            if ram[C+8]==10 and not ram[F+82] and ram[F+4]:
                assert self.dll.pp_op(5)==1 and self.m.read(F+82)==1,'READY must be appended before ACK'
        after=self.read(0,65536);wanted=bytearray(ram)
        ranges=[(2,0x1a),(0x100,0x200),(0x5000,0x6000),(0x8000,0x8800),
            (F,F+576),(0x9a00,0x9d85),(0x9d85,0x9de5),(0x9e00,0x9fc6),
            (0xa000,0xc000),(0xc000,0xc600),(0xca00,0xcb80),(0xcbc0,0xcc00),(0xdf00,0xdf0b)]
        for a,b in ranges:wanted[a:b]=after[a:b]
        assert after==wanted,('wholeRAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b))
        assert self.canonical()==canonical and self.catalog()==catalog
        assert self.read(0x8800,128)+self.read(0x8c00,256)+self.read(0x9180,128)==protected
        assert self.read(0xc600,1024)==self.shim
        assert b''.join(self.read(self.s[n],w)for n,w in
            [('object_owner',8),('object_gen_lo',8),('object_gen_hi',8),('object_banks',8),
             ('object_extents',128),('object_size_lo',8),('object_size_mid',8),('object_size_hi',8),
             ('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256)])==source_caps
        self.pump_trace.append(dict(op=op,A=r.a,C=r.p&1,instructions=n,requests=calls,
            R33_operations=[(i,self.dll.pp_op(i))for i in range(8)if self.dll.pp_op(i)],
            ready=self.m.read(F+4),job=self.m.read(F+82),writer_phase=self.m.read(C+8),
            before_ready=ram[F+4],before_job=ram[F+82],before_writer_phase=ram[C+8],
            leases=self.get('se_doc_read_locks',1),flags=self.get('se_bc_flags',1)))
        self.all_pump_trace.append(dict(generation=self.pump_generation,**self.pump_trace[-1]))
        return r,n


def fault_gates(f,start,arena_bank,out):
    groups=[];data=semantic.geos.native_text('One **pair** and *em*.\rSecond line.\rTail.')
    def call(op,error=None):
        r,_=f.cc(op)
        assert bool(r.p&1)==(error is not None),(op,hex(r.a),error)
        if error is not None:assert r.a==error,(op,hex(r.a),hex(error))
        return r
    def advance(predicate,limit=20000):
        for _ in range(limit):
            if predicate():return
            r=call(1);assert r.a==1,('prematurecompletion',r.a)
        raise AssertionError('missing requested pump phase')
    def capture(token):
        _,physical,reu=arena_bank(token)
        return f.canonical(),reu,physical
    def unchanged(snapshot,arena_changes=False):
        canonical,before,physical=snapshot;after=f.reu()
        if arena_changes:
            lo=physical*65536;assert after[:lo]==before[:lo] and after[lo+65536:]==before[lo+65536:]
        else:assert after==before
        assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim
    def closed():
        assert not f.get('se_doc_read_locks',1)
        assert f.m.read(F+1)==f.m.read(F+3)==f.m.read(F+4)==f.m.read(C+8)==f.m.read(C+39)==0
        assert f.get('se_bc_flags',1)==18
    def remove(id_,slot):
        for index in range(f.s['se_overlay_capacity']):
            if f.m.read(f.s['se_overlay_ids']+index)==id_ and f.m.read(f.s['image_slot']+index)&1==slot:
                address=f.s['se_overlay_ids']+index;old=f.m.read(address);f.m.write(address,0)
                f.m.write(f.s['se_overlay_active']+slot,0);return address,old
        raise AssertionError(('missing fault image',id_,slot))

    # Admission is deliberately outside the pump. Idle CANCEL cannot consume
    # an opaque prospective phase merely because this caller holds owner4.
    token=start(data,begin_writer=False);f.m.load(F,bytes((i*37+19)&255 for i in range(576)))
    phase=f.read(F,576);snapshot=capture(token);assert call(2).a==0
    assert f.read(F,576)==phase and not f.pump_trace[-1]['R33_operations'];unchanged(snapshot)
    groups.append('inactive-CANCEL-opaque/noR33')
    token=start(data,begin_writer=False);f.m.write(F+5,0);phase=f.read(F,576);snapshot=capture(token)
    assert call(0).a==2 and f.read(F,576)==phase and not f.get('se_doc_read_locks',1)
    assert not f.pump_trace[-1]['R33_operations'];unchanged(snapshot);groups.append('Plain-BEGIN-miss2/noR33/lease')

    token=start(data);snapshot=capture(token);phase=f.read(F,576);locks=f.get('se_doc_read_locks',1)
    call(0,0xb2);assert f.read(F,576)==phase and f.get('se_doc_read_locks',1)==locks
    call(3,0x90);assert f.read(F,576)==phase and f.get('se_doc_read_locks',1)==locks
    unchanged(snapshot);call(2);closed();groups.append('competing-BEGIN-and-invalidopcode-preserve-runningjob')

    token=start(data)
    for owner in (0,1,2,3,5,255):
        f.put('se_f_owner',owner,1);phase=f.read(F,576);snapshot=capture(token)
        for op in (0,1,2,3,255):
            call(op,0xb2);assert f.read(F,576)==phase and not f.pump_trace[-1]['R33_operations']
        unchanged(snapshot)
    f.put('se_f_owner',4,1);call(2);closed();groups.append('sixforeignowners/fiveopcodes/fullphaseopaque')

    phases=[('writer-init',lambda:True),
        ('block',lambda:f.m.read(C+8)==10 and f.m.read(F+1)==1),
        ('BODY',lambda:f.m.read(C+8)==10 and f.m.read(F+1)==2),
        ('held-inline',lambda:f.m.read(F+4)==2 and not f.m.read(F+82)),
        ('held-CR',lambda:f.m.read(F+4)==1 and not f.m.read(F+82)),
        ('append-before-ACK',lambda:f.m.read(C+8)==10 and f.m.read(F+82)==1),
        ('writer-seal',lambda:f.m.read(F+82)==1 and f.m.read(C+8)!=10),
        ('root-before-VALID',lambda:f.m.read(C+8)==18)]
    for tag,predicate in phases:
        source=data if tag!='writer-seal' else semantic.geos.native_text('Body.\r'*60)
        token=start(source,lost=True,queued=True);advance(predicate);snapshot=capture(token)
        queue=f.read(f.s['se_bc_head'],3);ring=f.read(f.s['se_bc_ring'],96)
        assert call(2).a==0 and not f.pump_trace[-1]['R33_operations'];closed()
        assert call(2).a==0 and not f.pump_trace[-1]['R33_operations']
        call(1,0x90);closed();assert f.read(f.s['se_bc_head'],3)==queue and f.read(f.s['se_bc_ring'],96)==ring
        unchanged(snapshot);bank,_,_=arena_bank(token);assert bank[5]==1 and bank[31]==0 and bank[133]==0
    groups.append('eightphase-CANCEL/idempotent/closedSTEP90/noR33/queuepreserved')

    for tag,data_ in [('CR',b'A\r'*600),('INLINE',semantic.geos.native_text('**a** '*3600))]:
        token=start(data_);snapshot=capture(token)
        for _ in range(100000):
            r=call(1)
            if r.a==3:break
            assert r.a==1,(tag,r.a)
        else:raise AssertionError((tag,'noSTREAM'))
        closed();unchanged(snapshot,True);bank,_,_=arena_bank(token)
        assert bank[5]==1 and bank[31]==0 and bank[133]==0
        assert f.merged()==data_;call(1,0x90);closed()
    groups.append('actualCR/INLINEexhaustion-STREAM3-closeslease-afterwriter-clearsACTIVE')

    for stage in ('BEGIN','initial-step','APPEND','FINAL'):
        token=start(data,begin_writer=stage!='BEGIN')
        if stage=='APPEND':advance(lambda:f.m.read(F+4)!=0 and not f.m.read(F+82))
        if stage=='FINAL':advance(lambda:f.m.read(C+8)==10 and f.m.read(F+1)==0)
        address,old=remove(33,0);snapshot=capture(token)
        call(0 if stage=='BEGIN' else 1,0x17);closed();unchanged(snapshot)
        f.m.write(address,old)
    groups.append('missing-realR33-BEGIN/STEP/APPEND/FINAL-ownercleanupwithoutR33')
    for stage in ('BEGIN','scan'):
        token=start(data,begin_writer=stage!='BEGIN')
        if stage=='scan':advance(lambda:f.m.read(C+8)==10 and f.m.read(F+1)==1)
        address,old=remove(14,0);snapshot=capture(token);call(0 if stage=='BEGIN' else 1,0x17)
        if stage=='scan':closed()
        else:assert not f.get('se_doc_read_locks',1)and not f.m.read(F+3)
        unchanged(snapshot);f.m.write(address,old)
    groups.append('missing-realR14-BEGIN/scan-residentEND-only-ownedlease')

    for offset in [*range(8,21),*range(66,79),173+27+25,291+74]:
        token=start(data)
        if offset==291+74:advance(lambda:f.m.read(F+4)==1 and not f.m.read(F+82))
        old=f.m.read(F+offset);f.m.write(F+offset,old^1);snapshot=capture(token)
        r,_=f.cc(1);assert r.p&1,(offset,r.a);closed();unchanged(snapshot)
    for offset,value in [(0,0),(3,0),(3,2),(C-F+8,0),(C-F+8,255)]:
        token=start(data);f.m.write(F+offset,value);snapshot=capture(token)
        r,_=f.cc(1)
        if offset==3:
            # A producer-local live flag is read at the next producer slice.
            # R33 may finish bounded private directory staging first, under
            # its independent full59 source/arena guard. It cannot arm a root.
            for _ in range(100):
                if r.p&1:break
                assert r.a==1 and not f.get('se_bc_flags',1)&1
                r,_=f.cc(1)
        assert r.p&1,(offset,value,r.a);closed();unchanged(snapshot,offset==3)
    groups.append('26authority/snapshot/CRCRC/ABI/readerflag/phasefaults-closeactualownedlease')

    for name in ('se_reu_epoch','se_doc_epoch','se_doc_meta'):
        token=start(data);old=f.read(f.s[name],2 if name!='se_doc_meta' else 5)
        f.m.write(f.s[name],old[0]^1);f.put('se_doc_read_locks',7,1);snapshot=capture(token)
        phase=f.read(F,576)
        r,_=f.cc(1);assert r.p&1 and f.get('se_doc_read_locks',1)==7
        if name=='se_reu_epoch':
            # Real loader admission failed before C34 could execute. No
            # controller can clean itself after its own missing admission.
            # Preserve evidence; eventual resident dispatcher cleanup is a
            # separately required integration, not fabricated by this probe.
            assert r.a==0x18 and f.read(F,576)==phase,('outer-epoch',hex(r.a),f.pump_trace[-1],
                [(i,a,b)for i,(a,b)in enumerate(zip(phase,f.read(F,576)))if a!=b][:12])
            assert not f.pump_trace[-1]['R33_operations']
        else:assert not f.m.read(F+3)and not f.m.read(F+173+8)
        unchanged(snapshot)
        f.m.load(f.s[name],old);f.put('se_doc_read_locks',0,1)
    groups.append('changedepoch/graph-preserves-sevenforeignleases/outerprovider-admission-is-opaque-not-integrated-cleanup')

    token=start(data);phase=f.read(F,576);f.put('se_f_owner',0,1)
    f.put('se_e_key',semantic.geos.native_text('Z')[0],1);f.put('se_e_mods',0,1);f.call('se_editor_input')
    assert f.get('se_e_error',1)==f.get('se_e_job',1)==0
    wanted=f.merged();assert wanted!=data
    f.m.load(F,phase);f.put('se_f_owner',4,1);snapshot=capture(token)
    r,_=f.cc(1);assert r.p&1;closed();unchanged(snapshot);assert f.merged()==wanted
    groups.append('actualsuccessfulpendingedit-invalidatesoldjob-withoutlosingnewsource')
    return groups


ORIGINAL_BUILD=semantic.build
ORIGINAL_RUNNER=semantic.geos.grid.runner


def default_compatibility(out):
    results=[];old_d,old_command=semantic.D,semantic.command
    for tag,expected in [('generic','9807b8d16d5f9f03dee363bf82c8378547629da5ab05d2e329e26ec0ad0ae88b'),
                         ('selector','c9ca67b3ed2a71e29a76018a69905dae1e06b409ca110489a233d83b43e0123d')]:
        def command(args):
            args=list(args)
            if tag=='selector'and args[0]=='ca65'and Path(args[-1])==semantic.D/'worker.s':
                args[1:1]=['-D','BSC_SELECTOR_OWNS_OWNER=1']
            return old_command(args)
        semantic.command=command
        try:
            _,budget=ORIGINAL_BUILD(out/tag,semantic.BASE)
            assert budget['sha256']==expected,(tag,budget)
            results.append(dict(profile=tag,**budget))
        finally:semantic.D,semantic.command=old_d,old_command
    return results


def run(out,base,smoke=False):
    controls=default_compatibility(out)
    old_build,old_fixture=semantic.build,semantic.Fixture
    semantic.build,semantic.Fixture=build_pump,PumpFixture
    semantic.geos.grid.runner=runner
    text=inspect.getsource(arena.run_writer)
    text=text.replace('f=semantic.Fixture(out,frozen,dll,True);',
        'f=semantic.Fixture(out,frozen,dll,True);f.report=report;')
    text=text.replace("  f.install(raw_worker,linked);r,_=f.cc('se_bsc_begin');assert not r.p&1 and r.a==1\n  if begin_writer:wc(4);drain()",
        "  f.install(raw_worker,linked)\n  if begin_writer:\n   r,_=f.cc('se_bsc_begin');assert not r.p&1 and r.a==1")
    a=text.index('  while True:\n   r,_=f.cc(');b=text.index('  bank,_,after=arena_bank(token);root=bank[128:256]',a)
    text=text[:a]+'''  while True:
   ready=f.m.read(F+4)
   if ready and not f.m.read(F+82):
    if ready==1:records.append(f.read(IO,96))
    else:events.append((int.from_bytes(f.read(F+291+16,3),'little'),f.read(IO,10)))
   r,_=f.cc('se_bsc_step');assert not r.p&1,(tag,'automatic-pump',r.a);steps+=1;assert steps<100000
   if not f.m.read(seam['se_bc_flags'])&1:assert f.read(seam['se_bc_head'],3)==queue
   if r.a==0:break
   assert r.a==1,(tag,'unexpected stream',r.a)
  assert f.read(seam['se_bc_head'],3)==bytes(3) and f.read(seam['se_bc_ticket'],4)==observed and f.read(seam['se_bc_ring'],96)==queued_records
'''+text[b:]
    a=text.index('  # Existing semantic authority cannot')
    text=text[:a]+'''  faults=FAULTS(f,start,arena_bank,out)
  (out/'fault-trace.json').write_text(json.dumps(f.pump_trace,indent=2)+'\\n')
  (out/'all-pump-trace.json').write_text(json.dumps(f.all_pump_trace,indent=2)+'\\n')
  result=dict(status='passed',cases=cases,fault_groups=faults,pump_budget=semantic_budget,writer_bytes=len(raw),
   pump_calls=len(f.all_pump_trace),peak_instructions=max(e['instructions']for e in f.all_pump_trace),
   scope='Private actual C34/R33 admission and auto-pump; preopened EMPTY arena; independent serialized/root/source/event oracles retained. No editor registration/native claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print('RESULT',json.dumps(result),flush=True);return result
 except BaseException:
  (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
'''
    if smoke:
        for needle in ["  check('real-empty'", "  check('real-multi-page'", "  check('real-one-line-300-events'",
            "  check('real-far-body-over64KiB'", "  check('real-pending-merged'", "  check('real-LOST-explicit-rebuild'"]:
            text='\n'.join(line for line in text.split('\n')if not line.startswith(needle))
        text=text.replace('  faults=FAULTS(f,start,arena_bank,out)','  faults=[]')
    needle="  entry=dict(tag=tag,source_bytes=len(data),records=len(got)"
    assert text.count(needle)==1
    text=text.replace(needle,"""  finished=f.read(F,576);reu=f.reu();again,_=f.cc(1)
  assert again.p&1 and again.a==0x90 and f.get('se_bc_flags',1)==1
  assert f.read(F,576)==finished and f.reu()==reu and not f.pump_trace[-1]['R33_operations']
  (out/(tag+'-pump-trace.json')).write_text(json.dumps(f.pump_trace,indent=2)+'\\n')
"""+needle)
    (out/'actual-oracle-with-pump.py').write_text(text)
    ns=dict(arena.__dict__);ns['FAULTS']=fault_gates
    try:
        exec(compile(text,str(out/'actual-oracle-with-pump.py'),'exec'),ns)
        result=ns['run_writer'](out,base)
        result['default_profiles_byte_identical']=controls
        result['root_protocol_required']='Resident root must retain REQUEST34 and set OP9136=1 on A1. Old19fe component fixture does not implement or qualify this root service route.'
        result['outer_admission_cleanup_required']='Caller must clean saved86/owned phase via resident END if C34 itself cannot be admitted; provider-epoch gate here proves opaque failure/foreign leases preserved, not that missing root integration.'
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:
        semantic.build,semantic.Fixture=old_build,old_fixture
        semantic.geos.grid.runner=ORIGINAL_RUNNER


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=semantic.BASE);p.add_argument('--smoke',action='store_true')
    a=p.parse_args();out=ROOT/'build/cache-pump'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke)

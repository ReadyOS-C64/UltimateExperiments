"""Private C19 resource-only optional-cache retirement + canonical fold suite.

Only a sealed C19 image is replaced against the frozen052628 product. No
resident, allocator, source bytes, OBJECT_LIMIT or production files change.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,inspect,json,re,shutil,zipfile
import test_cache_visual_regressions as visual
import test_geos_fold_editor as fold
ROOT=visual.ROOT
D=ROOT/'src/cache/fold-pressure-probe'


class PressureAudit(visual.CurrentAudit):
    def audit_begin(self):
        super().audit_begin()
        self.pressure_state=self.read(self.s['se_bc_arena'],17)
        self.pressure_ring=self.read(self.s['se_bc_ring'],96)

    def audit_end(self,before,tag):
        if self.audit_arena_before is None or self.read(self.s['se_bc_arena'],5)!=bytes(5):
            return super().audit_end(before,tag)
        # C19 may retire the already authenticated optional arena, but cannot
        # change its ticket/incarnation/ring or any byte outside real46/FE DMA.
        assert before==self.audit_before
        writes=fold.retention.Fixture.audit_end(self,before,tag)
        assert self.arena() is None and self.dll.pb_arena_get()==0
        state=self.read(self.s['se_bc_arena'],17)
        assert state[:5]==bytes(5) and state[5:13]==self.pressure_state[5:13]
        assert state[13]==(self.pressure_state[13]&~33)|2
        assert state[14:]==self.pressure_state[14:] and self.read(self.s['se_bc_ring'],96)==self.pressure_ring
        old=bytes.fromhex(self.audit_arena_before[0]['token']);oid=old[0]
        assert self.m.read(self.s['object_owner']+oid) in (0,0x46)
        generation=self.m.read(self.s['object_gen_lo']+oid)+256*self.m.read(self.s['object_gen_hi']+oid)
        assert generation==int.from_bytes(old[1:3],'little')+1
        self.audit_records.append(dict(tag=tag,checked_dma_writes=writes,typed53_writes=0,
                                       retired_optional_arena=self.audit_arena_before[0],state_before=self.pressure_state.hex(),state_after=state.hex()))
        (self.audit_out/'dma-audits.json').write_text(json.dumps(self.audit_records,indent=2)+'\n')
        return writes


def build_fixture(out,base):
    spec=importlib.util.spec_from_file_location('pressure_builder',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
    image,budget=b.build(out/'link',base)
    frozen=out/'private-fixture';shutil.copytree(base,frozen);(frozen/'build/overlays/foldctl.seo').write_bytes(image)
    identity=json.load(open(frozen/'freeze.json'));identity['assets']['foldctl']=hashlib.sha256(image).hexdigest()
    identity['private_change']='OnlyC19 resource retry wrapper; originalresident and allotherSEOs byte-identical.'
    (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
    return frozen,budget


def faults(out,frozen,labels):
    out.mkdir();grid=fold.geos.grid;identity=json.load(open(frozen/'freeze.json'))
    grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen
    grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names']
    dll=visual.bypass.runner(out);f=fold.Fixture(out,frozen,dll,True);cases=[]
    ls={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',labels.read_text())}
    try:
        for action in ('ordinary-create','slot35','physical1','physical1-insufficient',
                       'ACTIVE','MUTATING','stale-generation','stale-epoch','foreign-type',
                       'logical-owner','physical-owner','mapped-foreign','foreign-phase','nonresource36'):
            f.source(fold.TINY);f.command(99);f.render()
            token=f.read(f.s['se_bc_arena'],5);assert token!=bytes(5) and f.get('se_bc_flags',1)&1
            oid=token[0];logical=f.m.read(f.s['object_extents']+oid*16);physical=f.m.read(f.s['se_reu_map']+logical)
            # Load the real sealed C19 without beginning a phase job.
            f.put('se_overlay_frame',255,1);r,_=f.fast_call(f.s['se_overlay_call'],a=19,x=1)
            assert r.p&1 and r.a==0xb0
            if action not in ('ordinary-create','physical1','physical1-insufficient','nonresource36'):
                while True:
                    r,_=f.fast_call(f.s['se_object_create'],a=0x7e,x=1)
                    if r.p&1:assert r.a==0x35;break
            if action.startswith('physical1'):
                for i in range(1,256):
                    if f.m.read(f.s['se_reu_physical_owner']+i)==0:f.m.write(f.s['se_reu_physical_owner']+i,0x7e)
                    if f.m.read(f.s['se_reu_logical_owner']+i)==0:f.m.write(f.s['se_reu_logical_owner']+i,0x7e)
            if action=='ACTIVE':f.put('se_bc_flags',f.get('se_bc_flags',1)|8,1)
            if action=='MUTATING':f.put('se_bc_flags',f.get('se_bc_flags',1)|4,1)
            if action=='stale-generation':f.m.write(f.s['se_bc_arena']+1,token[1]^1)
            if action=='stale-epoch':f.m.write(f.s['se_bc_arena']+3,token[3]^1)
            if action=='foreign-type':
                for address in (f.s['object_owner']+oid,f.s['se_reu_logical_owner']+logical,f.s['se_reu_physical_owner']+physical):f.m.write(address,0x7e)
            if action=='logical-owner':f.m.write(f.s['se_reu_logical_owner']+logical,0x7e)
            if action=='physical-owner':f.m.write(f.s['se_reu_physical_owner']+physical,0x7e)
            if action=='mapped-foreign':f.m.write(f.s['se_reu_map']+logical,0)
            owner=1 if action=='foreign-phase'else 3
            f.put('se_f_owner',owner,1)
            # Entire FILE/fold/style union is opaque to this micromodule.
            phase=bytes((i*29+41)&255 for i in range(1152));f.m.load(0x8d00,phase)
            banks=2 if action=='physical1-insufficient'else 0 if action=='nonresource36'else 1
            f.put('se_ec_banks',banks,1);phase=f.read(0x8d00,1152)
            canonical=f.canonical();before=f.read(0,65536);reu=f.reu();state=f.read(f.s['se_bc_arena'],17);ring=f.read(f.s['se_bc_ring'],96)
            r,n=f.fast_call(ls['ec_create_fold'],a=0x46,x=banks)
            success=action in ('ordinary-create','slot35','physical1')
            assert bool(r.p&1)!=success,(action,r.a,r.p)
            if not success:assert r.a==(1 if action=='physical1-insufficient'else 0x36 if action=='nonresource36'else 0x35),(action,r.a)
            evicted=action in ('slot35','physical1','physical1-insufficient')
            after=f.read(0,65536)
            if evicted:
                assert f.read(f.s['se_bc_arena'],5)==bytes(5)
                assert f.get('se_bc_flags',1)==(state[13]&~33)|2
                assert f.m.read(f.s['object_gen_lo']+oid)==token[1]+1
            else:
                assert f.read(f.s['se_bc_arena'],17)==state
                assert f.m.read(f.s['object_gen_lo']+oid)==token[1]
                if not success:
                    # No object/provider publication is permitted on refusal.
                    for name,count in [('object_owner',8),('object_banks',8),('object_gen_lo',8),('object_gen_hi',8),('object_size_lo',8),('object_size_mid',8),('object_size_hi',8),('object_extents',128),('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256)]:
                        a=f.s[name];assert after[a:a+count]==before[a:a+count],(action,name)
            created=f.read(f.s['se_object_id'],5)[0] if success else None
            for i in range(8):
                if i in (created,oid if evicted else None):continue
                for name in ('object_owner','object_banks','object_gen_lo','object_gen_hi','object_size_lo','object_size_mid','object_size_hi'):
                    assert after[f.s[name]+i]==before[f.s[name]+i],(action,'foreign object field',i,name)
                a=f.s['object_extents']+i*16;assert after[a:a+16]==before[a:a+16],(action,'foreign object extents',i)
            for name in ('se_reu_logical_owner','se_reu_physical_owner'):
                for i in range(256):
                    a=f.s[name]+i
                    if before[a]not in(0,0x53):assert after[a]==before[a],(action,'foreign provider ownership',name,i)
                    elif before[a]==0:assert after[a]in(0,0x46),(action,'new allocation owner',name,i)
            for i in range(256):
                if before[f.s['se_reu_logical_owner']+i]not in(0,0x53):
                    assert after[f.s['se_reu_map']+i]==before[f.s['se_reu_map']+i],(action,'foreign provider map',i)
            assert f.read(f.s['se_bc_ticket'],8)==state[5:13]
            assert f.read(f.s['se_bc_head'],3)==state[14:] and f.read(f.s['se_bc_ring'],96)==ring
            assert f.reu()==reu and f.read(0x8d00,1152)==phase
            assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim and f.get('se_f_owner',1)==owner
            allowed=set(range(0x100,0x200))
            for name,count in [('se_object_id',5),('se_bc_arena',5),('se_bc_flags',1),('object_owner',8),('object_banks',8),('object_gen_lo',8),('object_gen_hi',8),('object_size_lo',8),('object_size_mid',8),('object_size_hi',8),('object_extents',128),('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256)]:allowed.update(range(f.s[name],f.s[name]+count))
            for name in ('new_owner','new_banks','new_index','new_count','new_error','validate_index','validate_extent','validate_type','provider_owner'):allowed.add(f.s[name])
            assert all(a==b or i in allowed for i,(a,b)in enumerate(zip(before,after))),(action,'RAM outside allocator requests/catalog/provider/BCcap+flags/stack')
            item=dict(action=action,A=r.a,carry=r.p&1,instructions=n,evicted=evicted,before=state.hex(),after=f.read(f.s['se_bc_arena'],17).hex())
            cases.append(item);print('FAULT PASS',item,flush=True)
            (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
    finally:f.close()
    return cases


def run(out,base):
    out.mkdir(parents=True);frozen,budget=build_fixture(out,base)
    full=out/'full-fold';full.mkdir();records=[]
    for name in ('grid80','grid60'):shutil.copy2(frozen/'build/overlays'/(name+'.seo'),full/(name+'.seo'))
    class Fixture(PressureAudit,fold.Fixture):
        audit_out=full
        audit_records=records
    source=inspect.getsource(fold.run)
    needle='dll=retention.runner(out);f=Fixture';assert source.count(needle)==1
    source=source.replace(needle,'dll=current_runner(out);f=Fixture')
    needle="(out/'result.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result,indent=2))"
    assert source.count(needle)==1;source=source.replace(needle,needle+';return result')
    (full/'executed-verifier.py').write_text(source)
    ns=dict(fold.__dict__,Fixture=Fixture,current_runner=visual.bypass.runner)
    exec(compile(source,str(full/'executed-verifier.py'),'exec'),ns)
    r=ns['run'](full,frozen)
    r['current_transport_adapter']=dict(audits=records,scope=visual.__doc__)
    (full/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    assert len(r['frames'])==28
    retirements=[x for x in r['current_transport_adapter']['audits']if 'retired_optional_arena'in x]
    assert any(x['tag']=='cut-canonical-hidden-range'for x in retirements)
    fault_cases=faults(out/'faults',frozen,out/'link/image.lbl')
    result=dict(status='PASS',budget=budget,fold_frames=len(r['frames']),retirements=retirements,faults=fault_cases,scope=__doc__)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result,flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/cache-fold-pressure'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())

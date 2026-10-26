"""Native presentation11 on a frozen cache product; precise typed53+FE guard.

Reuses all independent presentation pixel/font/source/settings/timing assertions.
Only initial arena allocation changes are added to the existing FE allowance.
Every arena byte must remain unchanged from first ARMED Markdown onwards.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_presentation_vice as presentation
from test_presentation_vice import timing,preview,capacity,Captured,vice_plan,ROOT,expected_geos


def arena_scope(n, images):
    s=n.s; records={}; derived=set(); snapshots={}; first=None
    for item in n.measurements:
        ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes()
        assert len(images[ident])==16*1024*1024
        derived.update(bank for bank in range(256) if ram[s['se_reu_physical_owner']+bank]==0xFE)
        token=ram[s['se_bc_arena']:s['se_bc_arena']+5]
        owners=[i for i in range(8) if ram[s['object_owner']+i]==0x53]
        if token==bytes(5):
            assert not owners and not any(ram[s['se_reu_physical_owner']+b]==0x53 for b in range(256)),(ident,'unbound arena allocation')
            records[ident]=None;continue
        oid=token[0];assert oid<8 and owners==[oid]
        assert token[1:3]==bytes((ram[s['object_gen_lo']+oid],ram[s['object_gen_hi']+oid]))
        epoch=ram[s['se_object_epoch']:s['se_object_epoch']+2]
        assert token[3:5]==epoch==ram[s['se_reu_epoch']:s['se_reu_epoch']+2] and epoch!=bytes(2)
        banks=ram[s['object_banks']+oid];assert 1<=banks<=16
        logical=list(ram[s['object_extents']+oid*16:s['object_extents']+oid*16+banks])
        physical=[ram[s['se_reu_map']+b] for b in logical]
        assert len(set(logical))==len(set(physical))==banks and all(logical)
        assert all(ram[s['se_reu_logical_owner']+b]==0x53 for b in logical)
        assert all(ram[s['se_reu_physical_owner']+b]==0x53 for b in physical)
        assert sorted(physical)==[b for b in range(256) if ram[s['se_reu_physical_owner']+b]==0x53]
        size=sum(ram[s[k]+oid]<<(8*i) for i,k in enumerate(('object_size_lo','object_size_mid','object_size_hi')))
        assert 0<size<=banks*65536
        descriptor=dict(token=token.hex(),logical_banks=logical,physical_banks=physical,logical_size=size)
        payload=b''.join(images[ident][b*65536:(b+1)*65536] for b in physical)
        flags=ram[s['se_bc_flags']];assert flags in (1,17,33,49),(ident,'settled ARMED; optional REBUILD_TRIED and checked PAGE_PROOF retained',flags)
        assert item['id']=='markdown-geos' or first is not None,(ident,'unexpected first arena publication')
        if first is None:first=(ident,descriptor,payload)
        assert descriptor==first[1] and payload==first[2],(ident,'retained arena changed after first ARMED Markdown')
        records[ident]=descriptor;snapshots[ident]=hashlib.sha256(payload).hexdigest()
    assert first is not None
    firstid,descriptor,payload=first; assert not set(descriptor['physical_banks'])&derived
    before_id=n.measurements[0]['id'];before=images[before_id]
    old=b''.join(before[b*65536:(b+1)*65536] for b in descriptor['physical_banks'])
    changes=[i for i,(a,b) in enumerate(zip(old,payload)) if a!=b]
    runs=[]
    for i in changes:
        if runs and runs[-1][1]==i:runs[-1][1]=i+1
        else:runs.append([i,i+1])
    allocation=dict(**descriptor,first_armed=firstid,initial_changed_bytes=len(changes),initial_changed_relative_spans=runs,
        before_sha256=hashlib.sha256(old).hexdigest(),armed_sha256=hashlib.sha256(payload).hexdigest(),immutable_capture_sha256=snapshots)
    (n.out/'arena-allocation.json').write_text(json.dumps(allocation,indent=2)+'\n')
    return allocation,derived,records


def evaluate(n):
    original=timing.semantic.expected;original_catalog=timing.FontCatalog;original_render=timing.render;timing.semantic.expected=expected_geos
    preview_caps=iter(item['caps']for item in n.measurements if item['ui']==4)
    def preset_preview(*args,**kwargs):
        return original_render(*args,**kwargs,code_coloring=bool(next(preview_caps)&2))
    timing.render=preset_preview
    timing.FontCatalog=lambda path,native:preview.pack_catalog((n.e/'font-pack.bin').read_bytes(),native)
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original;timing.FontCatalog=original_catalog;timing.render=original_render
    s=n.s;images=timing.native.live.grid.reu_images(n.out/'run');stable=None;outside=None;intervals=0
    allocation, derived, arena_records = arena_scope(n, images)
    for item in n.measurements:
        ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);reu=images[ident]
        assert f.get('se_render_caps',1)==item['caps']
        assert not any(f.get(k,1)for k in ('se_hot_pending','se_h_dirty','se_sel_mark'))
        assert f.get('se_hot_caret')==0 and f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE'
        assert f.read(s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
        canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        if stable is None:stable=canonical
        assert stable==canonical,(ident,'source/history/clipboard preservation')
        masked=bytearray(reu)
        for bank in derived:
            assert ram[s['se_reu_physical_owner']+bank]in (0,0xFE),(ident,'derived bank foreign',bank)
            masked[bank*65536:(bank+1)*65536]=bytes(65536)
        for logical in allocation['logical_banks']:
            expected=0 if arena_records[ident] is None else 0x53
            assert ram[s['se_reu_logical_owner']+logical]==expected,(ident,'arena logical owner',logical)
        for bank in allocation['physical_banks']:
            expected=0 if arena_records[ident] is None else 0x53
            assert ram[s['se_reu_physical_owner']+bank]==expected,(ident,'arena physical owner',bank)
            masked[bank*65536:(bank+1)*65536]=bytes(65536)
        sha=hashlib.sha256(masked).hexdigest()
        if outside is None:outside=sha
        else:assert outside==sha,(ident,'whole16MiB outside checked FE+53');intervals+=1
        groups=item.get('cost_profile') # timing.evaluate creates its own result items
        measured=next(x for x in result['measurements']if x['id']==ident)
        calls={(x['slot'],x['id'])for x in measured['cost_profile']['groups']}
        if item['caps']==0 and item['ui']!=4:
            assert not calls&{(1,14),(1,15),(1,19),(1,24),(1,25),(1,26),(1,31),(0,31)},(ident,'Plain scheduled semantic worker',calls)
            assert f.get('se_st_request',1)==f.get('se_st_valid',1)==0
        if item['caps']==1:assert not calls&{(1,15),(1,25),(1,31),(0,31)},(ident,'Markdown scheduled lexical worker')
    assert (n.e/'working.d81').read_bytes()==(n.e/'initial-fixtures.d81').read_bytes()
    result.update(cache_arena_allocation=allocation, cache_scope='Actual initial baseline allocation and immutable retained arena; no lexer/inline cache-hit claim.', preset_source_checks='passed',whole16MiB_derived_only_intervals=intervals,presentation_scope='ActualPALsource/settings/explicit-previewcaptures, allVICpixels independently modeled. Typedpreset setup throughIRQ input; measure finalPlainRETURN through public-input seam. No physicalkeyboard claim. Overlayentry traces prove no semantic workerrequests in measuredPlain intervals; pureparser-zero acrossidle is CPUgate scope.')
    (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);p.add_argument('--freeze',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.verify:
        assert a.freeze;evaluate(presentation.scenario_loaded(a.freeze.resolve()));return
    if a.source:
        e=timing.freeze(a.source.resolve(),'pal');target=e.with_name(e.name.replace('display-timing-pal','cache-presentation-native'));e.rename(target);e=target
    else:assert a.freeze;e=a.freeze.resolve()
    shutil.copy2(e/'supereditor.d81',e/'working.d81');presentation.package(e)
    n=presentation.scenario(e);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests','tools'):
            for q in (ROOT/folder).glob('*.py'):z.write(q,q.relative_to(ROOT))
    print('PREPARED',e,'binary8100/text8200..8239','steps',len(n.steps),'screens',len(n.measurements),flush=True)
    if not a.run:return
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
    manifest=capacity.run_owned_plan(plan,n.out,timeout=1200);(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=evaluate(n);print('PASS',e,flush=True)
    for c in result['measurements']:print(json.dumps(dict(id=c['id'],settled_cycles=c['emulated_cycles'],loads=c['counter_deltas']['se_overlay_loads'])),flush=True)

if __name__=='__main__':main()

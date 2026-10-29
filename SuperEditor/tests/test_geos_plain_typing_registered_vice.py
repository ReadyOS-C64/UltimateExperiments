"""Current sealed60 Plain typing A/B: owned8500/text8600..8639, PAL.

Actual ROM File/Open and IRQ preset/cursor setup; measured keys use the existing
disclosed PC/SP/public-input stopwatch seam. No physical-key latency claim.
No product build, capsule substitution, hardware access or shared-test edits.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,socket,subprocess,zipfile
import test_presentation_vice as presentation
from test_presentation_vice import timing,preview,capacity,Captured,vice_plan,ROOT
from d81_image import D81Image
from closed_runtime_copy import run_with_closed_links

CONTROL=ROOT/'build/grid-cr-committed/20261026T214650663448Z/fixture'
CANDIDATE=ROOT/'build/geos-plain-registered/20261026T214754702606Z/fixture'
DATA=timing.native.live.grid.native_text('Ordinary short text here.\rSecond ordinary row.\rThird source row.\rLast.')
NAME=b'PLAINTEST'


def free_ports():
    for port in (8500,*range(8600,8640)):
        with socket.socket()as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',port))


def pair_identity(control,candidate):
    a,b=[json.loads((p/'freeze.json').read_text())for p in(control,candidate)]
    assert len(a['names'])==len(b['names'])==60 and a['names']==b['names']
    assert a['prg_sha256']==b['prg_sha256']
    changed=[n for n in a['names']if a['assets'][n]!=b['assets'][n]]
    assert set(changed)=={'gtype','type'},changed
    disks=[D81Image((p/'build/supereditor.d81').read_bytes())for p in(control,candidate)]
    assert {e.name for e in disks[0].entries()}=={e.name for e in disks[1].entries()}
    diff=[e.name.decode()for e in disks[0].entries()if disks[0].read(e.name).data!=disks[1].read(e.name).data]
    assert set(diff)=={'GTYPE','TYPE'},diff
    return dict(control=str(control),candidate=str(candidate),resident_sha256=a['prg_sha256'],catalog=60,changed_assets=changed)


class Plan(presentation.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=8500
        p['global_defaults']['monitor_port_span']=1
        assert not p['steps'][0]['params']['kill_stale']
        return p


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True
    n.boot();n.open('open_profile',NAME);n.typed('enter_geos','mode hires')
    for preset,caps in(('full',3),('plain',0)):
        n.typed('preset_'+preset,'syntax '+preset)
        n.memory('caps_'+preset,'se_render_caps',caps)
        n.typed('top_'+preset,'goto 1');n.send('column_'+preset,b'\x1d'*5)
        n.memory('before_'+preset,'se_hot_caret',5,3)
        data=DATA[:5]+timing.native.live.grid.native_text('Q')+DATA[5:]
        for action,key,wanted,caret in(('insert',timing.native.live.grid.native_text('Q')[0],data,6),('back',0x14,DATA,5)):
            tag=preset+'-'+action
            n.measure(tag,wanted,3,key=key,category=preset+'-local-'+action)
            n.measurements[-1].update(caps=caps,preset=preset,action=action)
            n.memory(tag+'_caret','se_hot_caret',caret,3)
            n.memory(tag+'_pending','se_hot_pending',1)
    return n


def freeze(source,label):
    e=timing.native.freeze(source)
    target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-plain-typing-'+label+'-native')
    shutil.move(e,target);e=target
    (e/'profile.bin').write_bytes(DATA)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'profile.bin'),NAME.decode().lower()+',s'],capture_output=True,text=True)
    (e/'profile-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(NAME,kind=1).data==DATA
    shutil.copy2(e/'working.d81',e/'profile-initial.d81')
    (e/'variant.json').write_text(json.dumps(dict(label=label,source_fixture=str(source),ports=dict(binary=8500,text=[8600,8639])),indent=2)+'\n')
    return e


def evaluate(n,label):
    original=timing.semantic.expected;catalog=timing.FontCatalog
    timing.semantic.expected=presentation.expected_geos
    timing.FontCatalog=lambda path,native:preview.pack_catalog((n.e/'font-pack.bin').read_bytes(),native)
    try:result=timing.evaluate(n)
    finally:timing.semantic.expected=original;timing.FontCatalog=catalog
    images=timing.native.live.grid.reu_images(n.out/'run');s=n.s;groups={};outside={};rows=[]
    pack=(n.e/'font-pack.bin').read_bytes()
    with zipfile.ZipFile(n.e/'product-sources.zip')as z:
        for name,terms in[
            ('src/render/geos/edit-cache.inc',(b'GEX_OLD_HEADER=$D528',b'GEX_TAIL_END=$E568')),
            ('src/render/geos/typing-font-cache.inc',(b'GTF_DATA=$E568',b'GTF_META=$EA68'))]:
            assert all(t in z.read(name)for t in terms)
    for item in result['measurements']:
        tag=item['id'];ram=(n.out/'captures'/(tag+'-ram.bin')).read_bytes()
        colors=(n.out/'captures'/(tag+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);reu=images[tag]
        assert len(reu)==16777216 and f.get('se_render_caps',1)==item['caps']
        assert f.read(s['se_editor_settings'],64)==(n.e/'editor-defaults.bin').read_bytes()
        assert f.get('se_mode',1)==3 and f.get('se_hot_pending',1)==1 and f.get('se_sel_mark',1)==0
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==NAME
        assert f.get('se_hot_caret')==(6 if item['action']=='insert'else 5)
        assert f.get('se_clip_busy',1)==0
        state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in[
            ('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),
            ('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        group=item['preset'];assert state==groups.setdefault(group,state),(tag,'pending edit changed committed source/history/clip')
        for i,handle in enumerate(f.read(s['se_gf_state']+1,2)):
            bank=ram[s['se_reu_map']+handle]
            assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfd
            raw=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(raw)]==raw
        handle=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+handle]
        assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
        assert [b for b in range(256)if ram[s['se_reu_physical_owner']+b]==0xfe]==[bank]
        masked=bytearray(reu)
        # Existing source GEOS header,22slots,edit transaction backup and GTF
        # normalfont table. No whole FEbank,semantic53 or foreign allowance.
        for lo,hi in((0,64),(0x200,0xea88)):masked[bank*65536+lo:bank*65536+hi]=bytes(hi-lo)
        digest=hashlib.sha256(masked).hexdigest();assert digest==outside.setdefault(group,digest),(tag,'whole16MiB outside exact source/GTF derived spans')
        calls={(v['slot'],v['id']):v for v in item['cost_profile']['groups']}
        if item['caps']==0:
            forbidden={(1,v)for v in(14,15,17,18,19,24,25,26,31,34,35,37,39,45,47,49)}|{(0,31),(0,36),(0,37)}
            assert not forbidden&calls.keys(),(tag,'Plain scheduled semantic/lexer worker',calls.keys())
            assert f.get('se_st_valid',1)==f.get('se_st_request',1)==0
        direct=(0,30)in calls and (1,21)not in calls and (1,20)not in calls
        assert direct==(label=='candidate'or item['caps']==3),(tag,'actual direct route',direct,calls.keys())
        rows.append(dict(id=tag,caps=item['caps'],direct=direct,first_publish_cycles=item['first_publish_cycles'],settled_cycles=item['emulated_cycles'],loads=item['counter_deltas']['se_overlay_loads'],calls=[list(k)for k in calls]))
    assert(n.e/'working.d81').read_bytes()==(n.e/'profile-initial.d81').read_bytes(),'read-only native D81 changed'
    result.update(variant=label,extra_guards='PASS: committed source/history/clip same within pending pair; settings/FDfontpack/all60capsules/shim/cold/64stack; whole16MiB exact outside authenticated FEheader64 +0200..EA87 source/GTF union. Semantic53 and all other banks exact.',route_checks=rows,parser_scope='Native overlay-entry absence in measured Plain work; zero actual parser/lexer entries additionally proved by paired CPU46+8. Not physical key latency.')
    (n.out/'plain-typing-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def loaded(e):
    n=presentation.scenario_loaded(e);n.__class__=Plan;return n


def execute(source,label):
    free_ports();e=freeze(source,label);n=scenario(e);p=n.plan()
    assert len({s['id']for s in p['steps']})==len(p['steps'])
    (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in('tests','tools'):
            for q in sorted((ROOT/folder).glob('*.py')):z.write(q,q.relative_to(ROOT))
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
    print('NATIVE',e,'binary8500/text8600..8639','steps',len(n.steps),'IRQbytes',n.keys,'screens',len(n.measurements),flush=True)
    manifest=run_with_closed_links(capacity.run_owned_plan,p,n.out,timeout=900)
    (n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=evaluate(n,label);free_ports();print('PASS',e,flush=True)
    return e,result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--control',type=Path,default=CONTROL);p.add_argument('--candidate',type=Path,default=CANDIDATE);p.add_argument('--verify',type=Path);p.add_argument('--variant',choices=['control','candidate']);a=p.parse_args()
    if a.verify:
        e=a.verify.resolve();label=json.loads((e/'variant.json').read_text())['label'];evaluate(loaded(e),label)
    elif a.run:
        identity=pair_identity(a.control.resolve(),a.candidate.resolve());out=ROOT/'build'/('geos-plain-registered-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));out.mkdir()
        records=[]
        for label,source in(('control',a.control),('candidate',a.candidate)):
            if a.variant and a.variant!=label:continue
            e,r=execute(source.resolve(),label);records.append(dict(variant=label,evidence=str(e),rows=r['route_checks']))
            (out/'result.json').write_text(json.dumps(dict(status='PASS'if len(records)==(1 if a.variant else 2)else'PARTIAL',identity=identity,records=records),indent=2)+'\n')
        print('RESULT',out,flush=True)
    else:print('Prepared; --run uses immutable60 pair and owned8500/text8600..8639. CPU matrix must pass before launch.')

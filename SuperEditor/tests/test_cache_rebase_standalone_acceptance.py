"""Prepared native62 standalone43 +F8five +View/Settings12 adapter.

Default/preparation is offline: no VICE, .NET, hardware, shared build or Git.
--run is an explicit future native action requiring parent-owned port assignment.
Every original source/pixel/raw-file/history/font/catalog/REU assertion remains.
"""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
import argparse,binascii,hashlib,inspect,json,os,shutil,socket,subprocess,tempfile,traceback,zipfile
import test_standalone_acceptance_vice as engine
import test_view_menu_vice as view
from d81_image import D81Image
from closed_runtime_copy import run_with_closed_links

ROOT=engine.ROOT
BASE=ROOT/'build/cache-rebase-cold62-prep/fixture'
PORT=8700
PHASES=('editing','restart','fold','f8','view')
EXPECTED_FRAMES={'editing':35,'restart':4,'fold':4,'f8':5,'view':12}
BASE_EVALUATE=engine.evaluate
BASE_SCENARIO=engine.scenario
BASE_PLAN=engine.Plan
VIEW_EVALUATE=view.evaluate


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def contracts(e):
    """Allow only source-owned extents from this exact frozen product."""
    digests={}
    with zipfile.ZipFile(e/'product-sources.zip')as z:
        required={
          'src/render/geos/edit-cache.inc':(b'GEX_OLD_HEADER=$D528',b'GEX_TAIL_END=$E568'),
          'src/render/geos/typing-font-cache.inc':(b'GTF_DATA=$E568',b'GTF_META=$EA68'),
          'src/render/geos/preview-cache.inc':(b'PPC_META_REU=$EA88',b'PPC_SIZE=225'),
          'src/render/geos/preview-glyph-cache.inc':(b'PGC_VERSION=3',b'PGC_BASE=$EB69',b'PGC_END=$FBA9',b'PGC_BYTES=4160'),
          'src/render/grid/cache.inc':(b'GRID_CACHE_ROWS=22',b'GRID_CACHE_PACKET=240'),
          'src/render/grid/caret/api.inc':(b'NC_REU=$1500',b'NC_SIZE=256',b'N_CAPS=253'),
          'src/render/grid/long-prose-candidate/prose2.inc':(b'SC_REU=$1600',b'SC_SIZE=128'),
          'src/editor/menu-data.inc':(b'E_SOURCE,E_SETTINGS',b'Preview / source (GEOS)',b'Preview settings...'),
        }
        for name,terms in required.items():
            raw=z.read(name);assert all(t in raw for t in terms),(name,'unrecognized live cache/UI contract')
            digests[name]=hashlib.sha256(raw).hexdigest()
    assert len((e/'geosfontrow.seo').read_bytes())-36==4095,'unknown PGC-enabled R23 revision'
    return digests


def validate(e):
    d=json.loads((e/'freeze.json').read_text());names=d['catalog'];report=json.loads((e/'editor-report.json').read_text());s=report['symbols']
    assert len(names)==len(set(names))==62 and names[-2:]==['parse','xform']
    assert sha(e/'editor.prg')==d['prg_sha256']==report['sha256']
    assert sha(e/'supereditor.d81')==d['disk_sha256']
    assert report['resident_binding']['digest']==d['resident_binding']
    assert s['se_presentation_default']==3 and s['se_overlay_managed_verification']==1
    disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
    slots=[]
    for name in names:
        p=e/(name+'.seo');raw=p.read_bytes();assert sha(p)==d['asset_sha256'][name]
        assert raw[20:36]==raw[36:52]==bytes.fromhex(d['resident_binding'])
        assert int.from_bytes(raw[8:10],'little')==len(raw)-36<=4096
        assert binascii.crc_hqx(raw[36:],65535)==int.from_bytes(raw[12:14],'little')
        assert disk.read(name.upper().encode(),kind=1).data==raw;slots.append(tuple(raw[5:7]))
    assert len(set(slots))==62 and slots[-2:]==[(1,41),(0,34)]
    assert sha(e/'font-pack.bin')==d['font_pack_sha256']
    assert disk.read(b'GEOSFONTS',kind=1).data==(e/'font-pack.bin').read_bytes()
    assert (e/'editor-defaults.bin').read_bytes()[:8]==b'SEST\x01\x40\x08\x07'
    assert sha(e/'product-sources.zip')==d['product_sources_sha256']
    contracts(e)
    return d


def freeze(base,out):
    """Native-shaped immutable inputs, copied working disk; no native process."""
    assert not out.exists();out.mkdir(parents=True)
    d=json.loads((base/'freeze.json').read_text());assert len(d['names'])==62
    for n in('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):
        os.link(base/'build'/n,out/n)
    for name in d['names']:os.link(base/f'build/overlays/{name}.seo',out/(name+'.seo'))
    for name in engine.live.geos.GEOS_FONTS+('native8.bin','chargen.bin'):os.link(base/'fonts'/name,out/name)
    os.link(base/'product-sources.zip',out/'product-sources.zip')
    disk=D81Image((out/'supereditor.d81').read_bytes());pack=disk.read(b'GEOSFONTS',kind=1).data;(out/'font-pack.bin').write_bytes(pack)
    report=json.loads((out/'editor-report.json').read_text());prg=(out/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');at=2+report['symbols']['session_defaults']-load
    (out/'editor-defaults.bin').write_bytes(prg[at:at+64])
    native=dict(prg_sha256=d['prg_sha256'],disk_sha256=d['disk_sha256'],resident_binding=report['resident_binding']['digest'],catalog=d['names'],asset_sha256=d['assets'],cpu_fixture=str(base.resolve()),font_pack_sha256=sha(out/'font-pack.bin'),product_sources_sha256=sha(out/'product-sources.zip'),source_parent_metadata=d.get('git_commit'),source_policy=d.get('source_policy','See original frozen source metadata'),input_freeze_sha256=sha(base/'freeze.json'))
    (out/'freeze.json').write_text(json.dumps(native,indent=2)+'\n');os.link(base/'freeze.json',out/'input-cpu-freeze.json')
    validate(out)
    shutil.copy2(out/'supereditor.d81',out/'working.d81');data=engine.live.grid.fixture();(out/'diverse.bin').write_bytes(data)
    if b'DIVERSE' not in {x.name for x in disk.entries()}:
        p=subprocess.run(['c1541','-attach',str(out/'working.d81'),'-write',str(out/'diverse.bin'),'diverse,s'],capture_output=True,text=True)
        (out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    work=D81Image((out/'working.d81').read_bytes());assert work.read(b'DIVERSE',kind=1).data==data
    assert {x.name for x in work.entries()}=={x.name for x in disk.entries()}|{b'DIVERSE'}
    for ent in disk.entries():assert work.read(ent.name).data==disk.read(ent.name).data
    shutil.copy2(out/'working.d81',out/'initial-fixtures.d81')
    return out


class Plan(BASE_PLAN):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1
        assert not p['global_defaults'].get('kill_stale',False)
        return p


class ViewPlan(view.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1
        assert not p['global_defaults'].get('kill_stale',False)
        return p


def evaluator_source():
    text=inspect.getsource(BASE_EVALUATE)
    old='[(0,64),(0x200,0xb200),(0xb200,0xd528)]'
    assert text.count(old)==1
    # Existing preview_spans adds EA88..EB69 and EB69..FBA9 from source.
    text=text.replace(old,'[(0,64),(0x200,0xb200),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88)]')
    needle="if narrow_witness and c['mode'] in (1,2):spans.append((0x1500,0x1600))"
    assert text.count(needle)==1
    text=text.replace(needle,needle+';spans.append((0x1600,0x1680))')
    needle="}[phase]+' IRQnativeevents"
    assert text.count(needle)==1
    text=text.replace(needle,"}.get(phase,'Freshownedcoldboot/reopen/IRQF8 cycle3→0→1→2→3.')+' IRQnativeevents")
    return text


@contextmanager
def adapted(e):
    validate(e);old=engine.evaluate;plan=engine.Plan
    source=evaluator_source();exec(compile(source,str(Path(__file__))+'::precise-FE-evaluator','exec'),vars(engine));engine.Plan=Plan
    try:yield source
    finally:engine.evaluate=old;engine.Plan=plan


def f8_scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),'f8');data=engine.live.grid.native_text('Q')+engine.live.grid.fixture();name=engine.NAMES[3]
    n.boot();n.open('f8_saved_open',name);n.switch('f8_start_geos',3);n.shot('f8-initial-geos',data,3,current=name,group='f8')
    for mode in(0,1,2,3):
        n.send('actual_F8_'+str(mode),b'\x8c');n.memory('F8_mode_'+str(mode),'se_mode',mode)
        n.shot('f8-mode-'+str(mode),data,mode,current=name,group='f8')
    # A cross-mode group must use the exact UNION of documented layouts, not
    # current-mode masking, and retain every53/source/font/unallocated byte.
    for c in n.cases:c['group']=None
    return n


def view_scenario(e):
    # Same real inputs/oracles as released12, without hardcoding ARMED|TRIED17:
    # current query may also hold PAGE_PROOF32. Evaluator still authenticates
    # flags/descriptor and requires the entire53 arena to remain immutable.
    source=inspect.getsource(view.scenario)
    old="n.memory('actual_baseline','se_bc_flags',17)";assert source.count(old)==1
    source=source.replace(old,"n.memory('actual_baseline_queue','se_bc_count',0)")
    closed="n.send('settings_close_'+str(mode),b'\\3')";assert source.count(closed)==1
    source=source.replace(closed,closed+"\n  if mode<3:\n   n.send('non_geos_preview_refusal_'+str(mode),b'\\x85VP',error=0x77)\n   n.memory('non_geos_source_policy_'+str(mode),'se_r_presentation',0)\n   n.memory('non_geos_source_ui_'+str(mode),'se_e_ui',0)\n   n.switch('non_geos_policy_recovery_'+str(mode),mode)")
    namespace=dict(vars(view));namespace['Plan']=ViewPlan;exec(compile(source,str(Path(__file__))+'::View12','exec'),namespace)
    return namespace['scenario'](e)


def scenario(e,phase):
    if phase=='f8':return f8_scenario(e)
    if phase=='view':return view_scenario(e)
    with adapted(e):return BASE_SCENARIO(e,phase)


def union_guard(e,phase):
    """F8 cross-view exact union; no analysis53 masking or free-bank waiver."""
    out=e/phase;s=json.loads((e/'editor-report.json').read_text())['symbols'];images=engine.live.grid.reu_images(out/'run');reference=None;binding=None;canonical=None
    for c in json.loads((out/'cases.json').read_text()):
        ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes();f=engine.Captured(s,ram,(out/'captures'/(c['id']+'-colors.bin')).read_bytes(),e);reu=images[c['id']]
        assert f.get('se_h_end',2)==0,'F8 fresh-process history'
        state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w)for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        assert canonical in(None,state),(c['id'],'F8 source/history/clipboard');canonical=state
        h=f.get('se_gc_handle',1);p=ram[s['se_reu_map']+h]
        assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xfe
        assert binding in(None,(h,p));binding=(h,p);masked=bytearray(reu)
        # Includes grid source packet/NC/SP2 and GEOS source/edit/font/preview
        # mutually exclusive layouts, preserving every gap and FBA9..FFFF.
        for a,b in((0,22*240),(0x1500,0x1680),(0,64),(0x200,0xb200),(0xb200,0xd528),(0xd528,0xe568),(0xe568,0xea88),(0xea88,0xeb69),(0xeb69,0xfba9)):
            masked[p*65536+a:p*65536+b]=bytes(b-a)
        digest=hashlib.sha256(masked).hexdigest();assert reference in(None,digest),(c['id'],'F8 whole16MiB outside exact FEunion');reference=digest
    return len(images)-1


def evaluate(e,phase):
    with adapted(e):
        if phase=='view':result=VIEW_EVALUATE(e)
        else:result=engine.evaluate(e,phase)
    if phase=='f8':
        result['whole16MiB_readonly_intervals']=union_guard(e,phase)
        assert(e/'working.d81').read_bytes()==(e/'f8-initial.d81').read_bytes(),'F8 read-only D81 changed'
    assert len(result['frames'])==EXPECTED_FRAMES[phase]
    result.update(adapter_sha256=sha(Path(__file__)),registered_assets=62,no_analysis53_mask=True,visual_review='pending')
    (e/('gallery'if phase=='view'else phase)/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def check_plan(n,phase):
    p=n.plan();ids=[s['id']for s in p['steps']];assert len(ids)==len(set(ids))
    assert len(n.cases)==EXPECTED_FRAMES[phase]
    assert p['global_defaults']['monitor_port_start']==PORT and p['global_defaults']['monitor_port_span']==1
    assert not p['global_defaults'].get('kill_stale',False) and not p['steps'][0]['params']['kill_stale']
    # Existing Plan.memory is a monitored assertion, never a write operation.
    assert all(x['type']!='monitor_write' for x in p['steps'])
    if phase=='f8':assert [c['mode']for c in n.cases]==[3,0,1,2,3]
    if phase=='restart':assert [c['current'].encode()for c in n.cases]==list(engine.NAMES)
    if phase in('editing','restart'):
        saved=engine.live.grid.native_text('Q')+engine.live.grid.fixture();assert len(saved)==423
    return p,dict(phase=phase,frames=len(n.cases),steps=len(n.steps),IRQ_bytes=n.keys,all_step_ids_unique=True,whole_REU_policy='No53mask; precise authenticatedFE spans only, actual46 derived-map handling unchanged')


def negative_controls(out,e):
    records=[]
    with tempfile.TemporaryDirectory(prefix='negative-',dir=out)as temp:
        target=Path(temp)
        def reset():
            for p in target.iterdir():p.unlink()
            for p in e.iterdir():
                if p.is_file():(target/p.name).symlink_to(p)
        def put(name,raw):
            p=target/name;p.unlink();p.write_bytes(raw)
        def changed_asset(raw):
            d=json.loads((target/'freeze.json').read_text());d['asset_sha256']['parse']=hashlib.sha256(raw).hexdigest();put('parse.seo',raw);put('freeze.json',json.dumps(d).encode())
        def mutated(tag,mode):
            reset()
            if mode in('payload','header','resealed','slot','coherent-slot'):
                raw=bytearray((e/'parse.seo').read_bytes())
                if mode=='header':raw[12]^=1
                elif mode in('slot','coherent-slot'):raw[5]=0
                else:raw[60]^=1
                if mode=='resealed':raw[12:14]=binascii.crc_hqx(raw[36:],65535).to_bytes(2,'little')
                changed_asset(raw)
                if mode=='coherent-slot':
                    disk=bytearray((e/'supereditor.d81').read_bytes());t,sector,_=D81Image(disk).read(b'PARSE',kind=1).sectors[0];disk[((t-1)*40+sector)*256+7]=0;put('supereditor.d81',disk)
                    d=json.loads((target/'freeze.json').read_text());d['disk_sha256']=hashlib.sha256(disk).hexdigest();put('freeze.json',json.dumps(d).encode())
                    assert D81Image(disk).read(b'PARSE',kind=1).data==raw
            elif mode=='count':
                d=json.loads((target/'freeze.json').read_text());d['catalog']=d['catalog'][:-2];put('freeze.json',json.dumps(d).encode())
            else:
                d=json.loads((target/'editor-report.json').read_text());d['symbols']['se_overlay_managed_verification']=0;put('editor-report.json',json.dumps(d).encode())
            try:validate(target)
            except AssertionError as error:
                guard=traceback.extract_tb(error.__traceback__)[-1].line
                if mode=='coherent-slot':assert 'slots[-2:]' in guard
                records.append(dict(test=tag,status='REJECTED',actual_guard=guard))
            else:raise AssertionError((tag,'invalid fixture admitted'))
        for tag,mode in [('payloadCRC','payload'),('headerCRC','header'),('D81_mismatch_after_reseal','resealed'),('slot_header_D81_mismatch','slot'),('coherent_C41_wrong_slot','coherent-slot'),('old60_cardinality','count'),('unsupported_catalog_policy','policy')]:mutated(tag,mode)
    validate(e)
    result=dict(status='PASS',valid_control='PASS',cases=records,no_app_or_emulator_execution=True)
    (out/'offline-negative-controls.json').write_text(json.dumps(result,indent=2)+'\n');return result


def prepare(base,out):
    out=out.resolve()
    e=freeze(base,out/'native')
    # View12 is a distinct cold read-only scenario, not a reused editing path.
    v=freeze(base,out/'view-native')
    records=[]
    for phase in PHASES:
        target=v if phase=='view'else e;n=scenario(target,phase);p,record=check_plan(n,phase)
        (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');records.append(record)
    (out/'adapted-evaluate.py').write_text(evaluator_source())
    negatives=negative_controls(out,e)
    receipt=dict(status='OFFLINE_PLAN_PASS_NOT_NATIVE',adapter_sha256=sha(Path(__file__)),oracle_sha256={str(p.relative_to(ROOT)):sha(p)for p in [Path(engine.__file__),Path(view.__file__),Path(engine.capacity.__file__)]},fixture=str(base.resolve()),product=validate(e),phases=records,total_planned_frames=sum(r['frames']for r in records),negative_controls=len(negatives['cases']),required_native_order=list(PHASES),saved_file_prerequisite='editing creates byte-exact FINAL40/FINAL60/FINAL80/FINALGEOS423B; restart/fold/f8 require these from that same working D81',native_ports_not_opened=True,limits='No native captures, VIC evaluation, actual saves/restart or lifecycle claim from plan generation. Future verification must pass all unchanged independent oracles and inspect every image.')
    (out/'prepare-result.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


def free_ports():
    for port in(PORT,*range(PORT+100,PORT+140)):
        with socket.socket()as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port))


def execute(e,phase):
    validate(e)
    if phase in('restart','fold','f8'):
        disk=D81Image((e/'working.d81').read_bytes());wanted=engine.live.grid.native_text('Q')+engine.live.grid.fixture()
        for name in engine.NAMES:assert disk.read(name,kind=1).data==wanted,'editing must complete first'
    if phase in('fold','f8'):shutil.copy2(e/'working.d81',e/(phase+'-initial.d81'))
    n=scenario(e,phase);p,record=check_plan(n,phase)
    (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
    with zipfile.ZipFile(e/(phase+'-verification-sources.zip'),'w',zipfile.ZIP_DEFLATED)as z:
        for folder in('tests','tools'):
            for source in sorted((ROOT/folder).glob('*.py')):z.write(source,source.relative_to(ROOT))
    # Native execution is available only under explicit --run; no shared build.
    project=engine.live.grid.synchronous_project(n.out);engine.vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    free_ports();manifest=run_with_closed_links(engine.capacity.run_owned_plan,p,n.out,timeout=1800);free_ports()
    (n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return evaluate(e,phase)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--output',type=Path);p.add_argument('--prepare',action='store_true');p.add_argument('--prepared',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');p.add_argument('--phase',choices=PHASES+('all',),default='all');p.add_argument('--monitor-port',type=int,default=8700);a=p.parse_args();PORT=a.monitor_port;assert 1024<=PORT<=65395
    assert sum((a.prepare,a.run,a.verify))<=1
    if a.prepare:
        out=a.output or ROOT/'build/cache-rebase-acceptance-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('PREPARE',out,flush=True);r=prepare(a.fixture.resolve(),out);print('OFFLINE_PASS',r['total_planned_frames'],flush=True)
    elif a.run or a.verify:
        assert a.prepared;out=a.prepared.resolve();receipt=json.loads((out/'prepare-result.json').read_text());assert receipt['status']=='OFFLINE_PLAN_PASS_NOT_NATIVE' and receipt['adapter_sha256']==sha(Path(__file__))
        for name,digest in receipt['oracle_sha256'].items():assert sha(ROOT/name)==digest,('acceptance oracle changed since preparation',name)
        results=[]
        for phase in(PHASES if a.phase=='all'else(a.phase,)):
            e=out/('view-native'if phase=='view'else'native');results.append(execute(e,phase)if a.run else evaluate(e,phase))
        (out/'native-result.json').write_text(json.dumps(dict(status='PASS',phases=results,visual_review='pending'),indent=2)+'\n')
    else:print(__doc__)

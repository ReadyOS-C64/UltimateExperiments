"""Prepared current62 five-view controlled standalone lifecycle qualification.

Host preparation is default; --run requires an already prepared immutable set.
Actual File/Open, COPY, IRQ typing/Undo/SaveAs/reopen; packaged C29/R26 and fresh
trusted descriptor/prelude, same live provider/REU, explicit PC/SP/IRQ seams.
No old-stack, ReadyOS, physical RESTORE, external IRQ handoff or hardware claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, binascii, hashlib, json, re, shutil, socket, subprocess, sys, threading, zipfile
import test_lifecycle_body_memo_vice as memo
import test_lifecycle_cache_current as cache
from test_geos_navigation_vice import object_bytes
from overlay_catalog_policy import catalog_identity, catalog_state
from d81_image import D81Image
from closed_runtime_copy import run_with_closed_links
from test_reu_capacity_vice import run_owned_plan
life = memo.current.lifecycle
ROOT = life.ROOT
BASE = ROOT/'build/rebase-refusal-canonical-working-v3/20261026T234113497948Z/fixture'
MODES = {'40': (0, False), '60': (1, False), '80': (2, False), 'literal': (3, False), 'preview': (3, True)}
LIFECYCLE_SOURCES = ('adapter.s','adapter.inc','resume.s','resume.inc','copy-entry.s','copy-entry.inc','preflight.s','preflight.inc')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def freeze(base, e):
    """Authenticate all actual62 packaged files; write only owned output."""
    e.mkdir(parents=True)
    ident = json.loads((base/'freeze.json').read_text()); names = ident['names']
    assert len(names) == len(set(names)) == 62 and names[-2:] == ['parse','xform']
    for name in ('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):
        shutil.copy2(base/'build'/name,e/name)
    prg = (e/'editor.prg').read_bytes(); disk = D81Image((e/'supereditor.d81').read_bytes())
    assert sha(e/'editor.prg') == ident['prg_sha256'] and sha(e/'supereditor.d81') == ident['disk_sha256']
    assert json.loads((e/'disk-manifest.json').read_text())['sha256'] == ident['disk_sha256']
    assert disk.read(b'SUPEREDITOR',kind=2).data == prg
    report = json.loads((e/'editor-report.json').read_text()); binding = report['resident_binding']['digest']
    assert report['symbols']['se_overlay_managed_verification'] == 1
    for name in names:
        image = (base/'build/overlays'/(name+'.seo')).read_bytes()
        assert sha(base/'build/overlays'/(name+'.seo')) == ident['assets'][name]
        assert image[20:36] == image[36:52] == bytes.fromhex(binding)
        assert disk.read(name.upper().encode(),kind=1).data == image
        assert len(image)-36 == int.from_bytes(image[8:10],'little')
        assert binascii.crc_hqx(image[36:],65535) == int.from_bytes(image[12:14],'little')
        (e/(name+'.seo')).write_bytes(image)
    for name in life.native.live.geos.GEOS_FONTS+('native8.bin','chargen.bin'):
        shutil.copy2(base/'fonts'/name,e/name)
    pack = disk.read(b'GEOSFONTS',kind=1).data; (e/'font-pack.bin').write_bytes(pack)
    at = report['symbols']['session_defaults']-int.from_bytes(prg[:2],'little')+2
    defaults = prg[at:at+64]; assert defaults[:8] == b'SEST\1\x40\10\7'
    (e/'editor-defaults.bin').write_bytes(defaults)
    shutil.copy2(base/'product-sources.zip',e/'product-sources.zip')
    frozen = dict(prg_sha256=ident['prg_sha256'],disk_sha256=ident['disk_sha256'],resident_binding=binding,
                  catalog=names,asset_sha256={n:sha(e/(n+'.seo')) for n in names},cpu_fixture=str(base),font_pack_sha256=hashlib.sha256(pack).hexdigest())
    (e/'freeze.json').write_text(json.dumps(frozen,indent=2)+'\n')
    shutil.copy2(e/'supereditor.d81',e/'working.d81')
    data = life.native.live.grid.fixture(); (e/'diverse.bin').write_bytes(data)
    p = subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True)
    (e/'package.log').write_text(p.stdout+p.stderr); assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data == data
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    return frozen


def source_project(base, out):
    """All assembler/config/binding inputs come from this exact frozen ZIP."""
    out.mkdir()
    with zipfile.ZipFile(base/'product-sources.zip') as z:
        for item in z.infolist():
            path = Path(item.filename)
            assert not path.is_absolute() and '..' not in path.parts
            if path.parts[0] not in ('src','cfg','tools') or item.is_dir(): continue
            target = out/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(z.read(item.filename))
    return out


def build_component(project, out, base):
    original_root, original_command = life.component.ROOT, life.component.command
    life.component.ROOT = project
    def flags(*args):
        args = list(args)
        if args[0] == 'ca65' and str(args[-1]).endswith(('/resume.s','/copy-entry.s')):
            args[1:1] = ['-D','EDITOR_MANAGED_CODE=1']
        return original_command(*args)
    # command's cwd resolves its module global ROOT at call time.
    life.component.command = flags
    try: images = life.component.build(out,base)
    finally: life.component.ROOT,life.component.command = original_root,original_command
    for name,image in images.items(): assert image == (base/'build/overlays'/(name+'.seo')).read_bytes(),('frozen source differs from packaged lifecycle',name)
    labels = {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',(out/'lifecopy.lbl').read_text())}
    return images, labels


class Plan(memo.BodyMemoPlan):
    binary_port = 8500
    def plan(self):
        p = super().plan(); p['global_defaults']['monitor_port_start'] = self.binary_port
        p['global_defaults']['monitor_port_span'] = 1
        p['plan_id'] = 'current62-lifecycle-'+self.e.name
        assert not p['global_defaults'].get('kill_stale',False)
        return p
    def open(self, ident, name):
        super().open(ident,name)
        if ident == 'open_diverse':
            # Real nonempty clipboard, not a token injected into saved state.
            self.send('lifecycle_mark5',b'\x89'); self.send('lifecycle_select5',b'\x1d'*5)
            self.send('lifecycle_copy5',b'\x0b'); self.memory('lifecycle_clip5','se_clip_length',5,3)
            self.send('lifecycle_unmark5',b'\3'); self.typed('lifecycle_top_after_copy','top')


def prepare(out, base, modes, binary):
    out.mkdir(parents=True)
    project = source_project(base,out/'frozen-project')
    images, labels = build_component(project,out/'component',base)
    config = dict(status='PREPARED_NOT_RUN',fixture=str(base),adapter_sha256=sha(__file__),modes=modes,
                  binary_port=binary,text_ports=[binary+100,binary+139],catalog=62,source_zip_sha256=sha(base/'product-sources.zip'),
                  source_aware_lifecycle=True,packaged_C29_R26_byte_identical=True,scope=__doc__)
    for name in modes:
        mode,preview = MODES[name]; e = out/name; freeze(base,e)
        shutil.copytree(out/'component',e/'component')
        (e/'copy-symbols.json').write_text(json.dumps(labels,indent=2)+'\n')
        life.Plan = Plan; Plan.binary_port = binary
        n = life.scenario(e,mode,preview); plan = n.plan()
        assert len({s['id'] for s in plan['steps']}) == len(plan['steps'])
        assert len(n.cases) == 6
        assert '"REUsize" "16384"' in (n.out/'resources.mon').read_text()
        (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
        (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
        (e/'adapter-config.json').write_text(json.dumps(dict(config,name=name,mode=mode,preview=preview),indent=2)+'\n')
        print('PREPARED',name,e,'steps',len(plan['steps']),flush=True)
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for directory in ('tests','tools'):
            for p in sorted((ROOT/directory).glob('*.py')): z.write(p,p.relative_to(ROOT))
    (out/'adapter.json').write_text(json.dumps(config,indent=2)+'\n')
    return out


def evaluate(e):
    """Original raw restoration/media/pixel evaluator, plus precise current proof."""
    e = Path(e); config = json.loads((e/'adapter-config.json').read_text())
    result = life.evaluate(e) # No edits or string-replacement of original assertions.
    s = json.loads((e/'editor-report.json').read_text())['symbols']; caps = e/'lifecycle/captures'
    images = life.native.live.grid.reu_images(e/'lifecycle/run')
    ram = lambda n:(caps/(n+'-ram.bin')).read_bytes()
    before = ram('pending-before'); prepared = ram('prepared'); resumed = ram('pending-resumed')
    assert all(len(images[n]) == 16777216 for n in ('pending-before','prepared','pending-resumed'))
    # The capture transaction already has an exact FC payload+header comparison
    # in life.evaluate. Strengthen its historical wholeFE resume allowance.
    h = resumed[s['se_gc_handle']]; spans=[]
    wanted = bytearray(images['prepared'])
    if h:
        p = resumed[s['se_reu_map']+h]
        assert p and resumed[s['se_reu_logical_owner']+h] == resumed[s['se_reu_physical_owner']+p] == 0xFE
        assert resumed[s['se_gc_epoch']:s['se_gc_epoch']+2] == resumed[s['se_reu_epoch']:s['se_reu_epoch']+2]
        spans = [(0,64),(0x200,0xEA88)]
        if config['preview']:
            # Exact source-declared preview metadata225 + PGC3 header/records4160.
            spans += [(0xEA88,0xEB69),(0xEB69,0xFBA9)]
        for a,b in spans: wanted[p*65536+a:p*65536+b] = images['pending-resumed'][p*65536+a:p*65536+b]
    assert images['pending-resumed'] == wanted, 'resume wrote outside precise typedFE/source/preview contracts'
    observer_at=s['se_bc_arena']; ring_at=s['se_bc_ring']; observer=before[observer_at:observer_at+17]; ring=before[ring_at:ring_at+96]
    for name in ('prepared','exact-restored','prelude-finished','memo-invalidated','pending-resumed'):
        memory=ram(name); assert memory[observer_at:observer_at+17] == observer,(name,'observer17')
        assert memory[ring_at:ring_at+96] == ring,(name,'observer96')
    assert observer[14]<3 and observer[15]<3 and observer[16]<=3 and not observer[13]&(4|8|32)
    events=[]
    for i in range(observer[16]):
        at=((observer[15]+i)%3)*32; event=ring[at:at+32]
        assert event[0] == 0xA5 and event[1] in (1,2,3)
        assert int.from_bytes(event[29:31],'little') == binascii.crc_hqx(event[1:29]+event[31:],65535)
        events.append(event.hex())
    arena = None
    if config['mode']==3:
        assert any(observer[:5]) and observer[13]&15==1 and observer[16]>=1,'actual GEOS baseline plus queued pending edit required'
    if any(observer[:5]):
        arena,payload = cache.cache_frame(s,before,images['pending-before'],e)
        assert payload[arena['root_offset']+31] in (1,5),'unsupported captured cache feature'
        arena['root_feature'] = payload[arena['root_offset']+31]
        for name in ('prepared','pending-resumed'):
            other,raw = cache.cache_frame(s,ram(name),images[name],e)
            other['root_feature'] = raw[other['root_offset']+31]
            assert other == arena and raw == payload,(name,'whole actual typed53 arena changed')
    # NonGEOS views may legitimately have no semantic object; do not invent one
    # or transplant the old literal-only ARMED-baseline premise to those modes.
    catalog=None; fonts=[]; pack=(e/'font-pack.bin').read_bytes(); settings=before[s['se_editor_settings']:s['se_editor_settings']+64]
    clip = life.native.live.grid.fixture()[:5]
    for name in ('pending-before','pending-resumed','typed-after','undo','saved','reopened'):
        memory=ram(name); image=images[name]; f=life.Captured(s,memory,b'',e)
        raw=memory[s['se_overlay_ids']:s['se_overlay_ids']+384]
        identity=catalog_identity(raw,s); catalog_state(raw,s)
        if catalog is None:catalog=identity
        assert identity == catalog
        assert memory[s['se_editor_settings']:s['se_editor_settings']+64] == settings
        token=memory[s['se_clip_token']:s['se_clip_token']+5]
        assert int.from_bytes(memory[s['se_clip_length']:s['se_clip_length']+3],'little')==5
        assert object_bytes(f,image,token,5) == clip,(name,'actual copied bytes')
        assert memory[s['se_gf_state']] == 0xA5
        handles=memory[s['se_gf_state']+1:s['se_gf_state']+3]; assert all(handles) and handles[0]!=handles[1]
        for i,handle in enumerate(handles):
            bank=memory[s['se_reu_map']+handle]
            assert bank and memory[s['se_reu_logical_owner']+handle] == memory[s['se_reu_physical_owner']+bank] == 0xFD
            chunk=pack[i*65536:(i+1)*65536]
            assert image[bank*65536:bank*65536+len(chunk)] == chunk,(name,'exact actual fontpack')
        fonts.append(dict(stage=name,handles=list(handles)))
    reopened=ram('reopened'); after_state=reopened[observer_at:observer_at+17]
    assert int.from_bytes(after_state[9:13],'little')>int.from_bytes(observer[9:13],'little'),'actual FileOpen new incarnation'
    assert after_state[16]==0 and not after_state[13]&(4|8|32),'reopened observer must be settled/empty'
    fresh_arena=None
    if arena:
        fresh_arena,_=cache.cache_frame(s,reopened,images['reopened'],e)
        assert fresh_arena['token']!=arena['token'] and fresh_arena['merged_length']==422
        assert fresh_arena['root_ticket']==int.from_bytes(after_state[5:9],'little')
    boundary=ram('memo-invalidated'); raw=boundary[s['se_overlay_ids']:s['se_overlay_ids']+384]
    assert not any(v for v in catalog_state(raw,s).verified if v is not None)
    assert boundary[s['se_overlay_active']:s['se_overlay_active']+2] == b'\0\0' and boundary[0xCBD5]==boundary[0xCC4D]==0
    assert catalog_identity(raw,s)==catalog
    entry=dict(mode=config['mode'],preview=config['preview'],evidence=str(e.relative_to(ROOT)),frames=len(result['frames']),native_pixels=result['native_pixels'])
    body=memo.verify_one(entry,Path(config['fixture']))['body_memo']
    result.update(status='PASS',actual_catalog_assets=62,observer17=observer.hex(),ring96=ring.hex(),queued_events=events,
                  actual_typed53=arena,reopened_actual_typed53=fresh_arena,fonts=fonts,nonempty_clipboard=clip.hex(),session_settings=settings.hex(),body_memo=body,
                  precise_resume_REU=dict(bytes=16777216,owner=0xFE,logical=h,relative_allowed_spans=spans,
                    whole53_source_history_catalog_fonts_FC_unchanged=True,changed_bytes=sum(a!=b for a,b in zip(images['prepared'],images['pending-resumed']))),
                  oracle_adaptations=['actual62 catalog; no fixed53 metadata','nonGEOS observer exact without fabricated semantic baseline','old wholeFE resume mask strengthened to source/GTF union plus exact preview metadata/PGC3 only'],
                  adapter_sha256=sha(__file__),visual_review='pending',scope=__doc__)
    (e/'current62-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def free_ports(binary):
    for port in (binary,*range(binary+100,binary+140)):
        with socket.socket() as sock: sock.bind(('127.0.0.1',port))


def execute(e, run=False):
    config=json.loads((e/'adapter-config.json').read_text());assert config['adapter_sha256']==sha(__file__)
    plan=json.loads((e/'lifecycle/plan.yaml').read_text());assert plan['global_defaults']['monitor_port_start']==config['binary_port']
    project=life.native.live.grid.synchronous_project(e/'lifecycle');life.vice_plan.PROJECT=project
    for label,command in [('dotnet-build',['dotnet','build',str(project),'--nologo']),('compile-only',['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(e/'lifecycle/plan.yaml')])]:
        p=subprocess.run(command,capture_output=True,text=True,timeout=120);(e/'lifecycle'/(label+'.log')).write_text(p.stdout+p.stderr);assert not p.returncode
    if not run:return
    free_ports(config['binary_port']);stop=threading.Event()
    def watch():
        while not stop.wait(.1):
            p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
            for line in p.stdout.splitlines():
                if '/x64sc 'in line and f'-binarymonitoraddress 127.0.0.1:{config["binary_port"]}'in line and str(e/'working.d81')in line:
                    fields=line.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(fields[0]),parent=int(fields[1]),command=fields[2]),indent=2)+'\n');return
    thread=threading.Thread(target=watch,daemon=True);thread.start()
    try:receipt=run_with_closed_links(run_owned_plan,plan,e/'lifecycle',timeout=2400)
    finally:stop.set();thread.join(timeout=3)
    (e/'owned-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    owned=json.loads((e/'owned-process.json').read_text());p=subprocess.run(['ps','-p',str(owned['PID']),'-o','command='],capture_output=True,text=True)
    assert str(e/'working.d81')not in p.stdout;free_ports(config['binary_port'])
    (e/'owned-closure.json').write_text(json.dumps(dict(PID=owned['PID'],exact_command_absent=True,owned_ports_released=True),indent=2)+'\n')
    return evaluate(e)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);p.add_argument('--prepared',type=Path);p.add_argument('--modes',choices=tuple(MODES),nargs='+',default=list(MODES));p.add_argument('--binary',type=int,default=8500);p.add_argument('--compile-only',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    if a.prepared:
        out=a.prepared.resolve();c=json.loads((out/'adapter.json').read_text());assert c['adapter_sha256']==sha(__file__)
    else:
        assert not a.run and not a.verify,'Prepare immutable plans before native execution.'
        out=(a.out or ROOT/'build/rebase-lifecycle-native-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
        assert len(set(a.modes))==len(a.modes);prepare(out,a.fixture.resolve(),a.modes,a.binary)
    c=json.loads((out/'adapter.json').read_text());results=[]
    for name in c['modes']:
        if a.verify:results.append(evaluate(out/name))
        elif a.run or a.compile_only:
            r=execute(out/name,a.run)
            if r:results.append(r)
    if results:(out/'result.json').write_text(json.dumps(dict(status='PASS',cases=results,frames=sum(len(r['frames'])for r in results),native_pixels=sum(r['native_pixels']for r in results),scope=__doc__,visual_review='pending'),indent=2)+'\n')
    print('PASS'if results else'PREPARED_NOT_RUN',out,flush=True)

if __name__=='__main__': main()

"""Prepared native warm-key A/B, committed62 vs sealed C32 byte shift.

Default is host-only preparation. --run is deliberately separate and uses only
an already prepared private pair. No canonical build, source/authority injection,
Ultimate access or physical keyboard latency claim. Public File/Open and IRQ
setup; measured keys use the existing PC/SP/public-input stopwatch seam.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, re, shutil, socket, subprocess, sys, threading, zipfile
import test_presentation_vice as presentation
from test_presentation_vice import timing, preview, capacity, Captured, vice_plan, ROOT
from test_cache_rebase_registered import metadata
from d81_image import D81Image
from closed_runtime_copy import run_with_closed_links
from png_pixels import read_png
from cache_job_build import editor_pair_index

CONTROL = ROOT / 'build/cache-rebase-committed/20261026T224637147761Z/fixture'
RELEASE = ROOT / 'src/render/geos/warm-shift-probe'
SOURCE_SHA = '2a2b64fd064fe8bc64d2f8223afed97699706872b057a1ccc8144bff22e97684'
DOCUMENTS = {
    'plain': (0, 'Ordinary words here.\rSecond source row.\rLast.', 5, b'WARMP'),
    'markdown': (1, 'Ordinary words here.\rSecond source row.\rLast.', 5, b'WARMM'),
    'full': (3, 'Ordinary words here.\rSecond source row.\rLast.', 5, b'WARMF'),
    'strong': (3, 'Ordinary **strong words** here.\rSecond source row.\rLast.', 14, b'WARMS'),
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def runtime_index(e,names,name):
    image=(e/(name+'.seo')).read_bytes()
    symbols=json.loads((e/'editor-report.json').read_text())['symbols']
    return editor_pair_index(image[5],image[6]) if 'catalog_index' in symbols else names.index(name)


def candidate_package(out, control):
    """Actual two-asset source rebuild and D81 package, outside shared build."""
    assert sha(RELEASE / 'wide.s') == SOURCE_SHA
    spec = importlib.util.spec_from_file_location('warm_native_rebuild', RELEASE / 'build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    target, budget = builder.build(out, control, 'after')
    old = json.loads((control / 'freeze.json').read_text())
    ident = json.loads((target / 'freeze.json').read_text())
    assert len(old['names']) == 62 and old['names'] == ident['names']
    assert old['prg_sha256'] == ident['prg_sha256']
    disk_path = target / 'build/supereditor.d81'
    before = D81Image(disk_path.read_bytes())
    commands = []
    for name in ('type', 'gtype'):
        image = target / 'build/overlays' / (name + '.seo')
        command = ['c1541', '-attach', str(disk_path), '-delete', name, '-write', str(image), name + ',s']
        commands.append(command)
        proc = subprocess.run(command, capture_output=True, text=True)
        (out / ('package-' + name + '.log')).write_text(proc.stdout + proc.stderr)
        assert not proc.returncode
    after = D81Image(disk_path.read_bytes())
    assert [(e.name, e.kind) for e in before.entries()] == [(e.name, e.kind) for e in after.entries()]
    changes = [e.name.decode() for e in before.entries()
               if before.read(e.name, kind=e.kind).data != after.read(e.name, kind=e.kind).data]
    assert set(changes) == {'TYPE', 'GTYPE'}, changes
    for name in ident['names']:
        image = (target / 'build/overlays' / (name + '.seo')).read_bytes()
        assert after.read(name.upper().encode(), kind=1).data == image
        if name not in ('type', 'gtype'):
            assert image == (control / 'build/overlays' / (name + '.seo')).read_bytes()
    assert after.read(b'SUPEREDITOR', kind=2).data == (control / 'build/editor.prg').read_bytes()
    assert after.read(b'GEOSFONTS', kind=1).data == before.read(b'GEOSFONTS', kind=1).data
    with zipfile.ZipFile(control / 'product-sources.zip') as z:
        sources = {i.filename: z.read(i.filename) for i in z.infolist()}
    path = 'src/render/geos/style-typing/wide.s'
    assert sources[path] == (RELEASE / 'wide-before.s').read_bytes()
    sources[path] = (RELEASE / 'wide.s').read_bytes()
    with zipfile.ZipFile(target / 'product-sources.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sources.items():
            z.writestr(name, data)
    ident['sources'] = dict(ident['sources'])
    ident['sources'][path] = SOURCE_SHA
    ident['disk_sha256'] = sha(disk_path)
    shutil.copy2(target/'build/disk-manifest.json',target/'build/input-disk-manifest.json')
    (target/'build/disk-manifest.json').write_text(json.dumps(dict(schema=1,disk=str(disk_path),bytes=disk_path.stat().st_size,sha256=ident['disk_sha256'],command=commands[0],additional_commands=commands[1:],input_manifest_sha256=sha(target/'build/input-disk-manifest.json'),scope='Private source-rebuilt TYPE/GTYPE replacement on copied input D81; other files exact.'),indent=2)+'\n')
    ident['private_variant']['packaging'] = 'Genuine private D81; exactly TYPE/GTYPE changed, all62 packaged payloads authenticated.'
    (target / 'freeze.json').write_text(json.dumps(ident, indent=2) + '\n')
    proof = dict(status='PASS',control=str(control),candidate=str(target),catalog=62,
                 actual_changed_disk_files=changes,budget=budget,source_sha256=SOURCE_SHA,
                 prg_sha256=ident['prg_sha256'],disk_sha256=ident['disk_sha256'],
                 assets=ident['assets'],scope='Normal frozen-source style-typing builder; C32/R30 only. No startup/catalog registration or runtime code injection.')
    (out / 'package-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    return target, proof


def native_freeze(source, e):
    """Same explicit immutable package checks as native.freeze; owned output."""
    e.mkdir(parents=True)
    identity = json.loads((source / 'freeze.json').read_text())
    assert len(identity['names']) == 62
    for name in ('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):
        shutil.copy2(source / 'build' / name, e / name)
    prg = (e / 'editor.prg').read_bytes()
    disk = D81Image((e / 'supereditor.d81').read_bytes())
    assert sha(e / 'editor.prg') == identity['prg_sha256']
    assert sha(e / 'supereditor.d81') == identity['disk_sha256']
    assert json.loads((e/'disk-manifest.json').read_text())['sha256'] == identity['disk_sha256']
    assert disk.read(b'SUPEREDITOR', kind=2).data == prg
    binding = json.loads((e / 'editor-report.json').read_text())['resident_binding']['digest']
    for name in identity['names']:
        image = (source / 'build/overlays' / (name + '.seo')).read_bytes()
        assert image[20:36] == image[36:52] == bytes.fromhex(binding)
        assert disk.read(name.upper().encode(), kind=1).data == image
        (e / (name + '.seo')).write_bytes(image)
    for name in timing.native.live.geos.GEOS_FONTS + ('native8.bin','chargen.bin'):
        shutil.copy2(source / 'fonts' / name, e / name)
    pack = disk.read(b'GEOSFONTS', kind=1).data
    (e / 'font-pack.bin').write_bytes(pack)
    report = json.loads((e / 'editor-report.json').read_text())
    at = report['symbols']['session_defaults'] - int.from_bytes(prg[:2], 'little') + 2
    defaults = prg[at:at+64]
    assert defaults[:8] == b'SEST\1\x40\10\7'
    (e / 'editor-defaults.bin').write_bytes(defaults)
    shutil.copy2(source / 'product-sources.zip', e / 'product-sources.zip')
    frozen = dict(prg_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],
                  resident_binding=binding,catalog=identity['names'],
                  asset_sha256={n:sha(e/(n+'.seo')) for n in identity['names']},
                  cpu_fixture=str(source),font_pack_sha256=hashlib.sha256(pack).hexdigest())
    (e / 'freeze.json').write_text(json.dumps(frozen, indent=2) + '\n')
    shutil.copy2(e / 'supereditor.d81', e / 'working.d81')
    return frozen


def trace_proof(e, source):
    names = json.loads((e / 'freeze.json').read_text())['catalog']
    targets = []
    for name in names:
        p = metadata(source, name)
        raw = p.with_suffix('.bin').read_bytes()
        image = (e / (name + '.seo')).read_bytes()
        assert raw == image[36:]
        symbols = {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)', p.with_suffix('.lbl').read_text())}
        wanted = [n for n in ('se_sm_init','se_sm_feed','se_si_init','se_si_feed','se_sl_init','se_sl_feed') if n in symbols]
        if name == 'gtype':
            wanted += ['se_gct_stage','prime']
        if name == 'type':
            wanted += ['se_gst_transaction','se_typing_patch','se_typing_color_patch']
        if not wanted:
            continue
        folder = e / 'trace-input' / name
        folder.mkdir(parents=True)
        for ext in ('.bin','.lbl','.map'):
            shutil.copy2(p.with_suffix(ext), folder / (name + ext))
        for symbol in wanted:
            pc = symbols[symbol]
            if name in ('type','clex'):
                staged_worker = 'gtype' if name == 'type' else 'code'
                namespace = 0x42 if name == 'type' else 0x41
                assert 0x5000 <= pc < 0x5000 + len(raw) - 32
                # Stage entry is reached only through the authenticated live R30
                # supervisor. Use the same two-term ownership predicate as its
                # entry; independently authenticate instruction bytes, enclosing
                # R30 payload interval and the complete final staged image.
                condition = f'(@cpu:${report_symbol(e,"se_overlay_active"):04x} == ${runtime_index(e,names,staged_worker)+1:02x}) && (@cpu:${report_symbol(e,"se_overlay_busy"):04x} == $01)'
            else:
                origin = 0xB000 if image[5] else 0xA000
                assert origin <= pc < origin + len(raw)
                condition = f'@cpu:${report_symbol(e,"se_overlay_active")+image[5]:04x} == ${runtime_index(e,names,name)+1:02x} && @cpu:${report_symbol(e,"se_overlay_busy")+image[5]:04x} == $01'
            targets.append(dict(asset=name,symbol=symbol,pc=pc,condition=condition,
                                payload_sha256=hashlib.sha256(raw).hexdigest()))
    (e / 'trace-proof.json').write_text(json.dumps(targets, indent=2) + '\n')
    return targets


def report_symbol(e, name):
    return json.loads((e / 'editor-report.json').read_text())['symbols'][name]


class Plan(presentation.Plan):
    def plan(self):
        p = super().plan()
        p['plan_id'] = 'geos-warm-shift-'+self.e.name+'-'+hashlib.sha256(str(self.e).encode()).hexdigest()[:10]
        p['global_defaults']['monitor_port_start'] = self.binary_port
        p['global_defaults']['monitor_port_span'] = 1
        p['global_defaults']['timeouts']['step_s'] = 120
        assert not p['global_defaults'].get('kill_stale', False)
        assert not p['steps'][0]['params']['kill_stale']
        return p

    def raw(self, ident, commands):
        if ident.endswith('_timed_coherent'):
            commands = list(commands)
            at = commands.index('stopwatch reset')
            commands[at:at] = [f'trace exec ${t["pc"]:04x} if {t["condition"]}' for t in self.trace_targets]
        return super().raw(ident, commands)


def scenario(e, config):
    standard, model = (1,0) if config['standard'] == 'pal' else (2,3)
    n = Plan(e, json.loads((e/'editor-report.json').read_text()), standard, model)
    n.binary_port = config['binary_port']
    n.trace_targets = json.loads((e/'trace-proof.json').read_text())
    parser_pcs = {t['pc'] for t in n.trace_targets if any(v in t['symbol'] for v in ('se_sm_','se_si_','se_sl_'))}
    other_pcs = {t['pc'] for t in n.trace_targets if not any(v in t['symbol'] for v in ('se_sm_','se_si_','se_sl_'))}
    for value in n.cost_points.values():
        other_pcs.update(value if isinstance(value,list) else [value])
    assert not parser_pcs & other_pcs,'ambiguous parser trace PC overlaps another trace category'
    n.cost_profile = True
    n.measurement_warp = not config['normal_speed']
    n.boot()
    for serial, name in enumerate(config['profiles']):
        caps, text, caret, filename = DOCUMENTS[name]
        source = timing.native.live.grid.native_text(text)
        n.typed(name+'-preset', 'syntax '+{0:'plain',1:'markdown',3:'full'}[caps])
        if serial:
            n.memory(name+'-previous-clean','se_hot_pending',0)
            n.memory(name+'-previous-history-clean','se_h_dirty',0)
        n.open(name+'-open', filename)
        n.typed(name+'-mode', 'mode hires')
        n.typed(name+'-top', 'top')
        n.send(name+'-column', b'\x1d'*caret)
        n.memory(name+'-initial-caret','se_hot_caret',caret,3)
        data = source
        actions = [(f'pair{i}-'+action,key) for i in range(config['pairs'])
                   for action,key in [('insert',timing.native.live.grid.native_text('Q')[0]),('back',0x14)]]
        actions += [(f'caret{i}-'+action,key) for i in range(2)
                    for action,key in [('right',0x1d),('left',0x9d)]]
        for tag, key in actions:
            if key == 0x14:
                data = data[:caret-1] + data[caret:]
                caret -= 1
            elif key == timing.native.live.grid.native_text('Q')[0]:
                data = data[:caret] + bytes([key]) + data[caret:]
                caret += 1
            else:
                caret += 1 if key == 0x1d else -1
            ident = name+'-'+tag
            n.measure(ident,data,3,key=key,category='first-pair' if tag.startswith('pair0') else 'steady-key')
            n.measurements[-1].update(profile=name,caps=caps,expected_caret=caret,
                                     action=tag,filename=filename.decode(),
                                     expected_transaction=not tag.startswith('caret'),expected_pending=int(not tag.startswith('caret')))
            n.memory(ident+'-check-caret','se_hot_caret',caret,3)
            n.memory(ident+'-check-caps','se_render_caps',caps)
            n.memory(ident+'-check-pending','se_hot_pending',int(not tag.startswith('caret')))
        assert data == source and caret == DOCUMENTS[name][2]
    return n


def prepare(out, control, profiles, pairs, binary, standard, normal_speed):
    out.mkdir(parents=True)
    candidate, proof = candidate_package(out/'candidate-package', control)
    config = dict(status='PREPARED_NOT_RUN',control=str(control),candidate=str(candidate),profiles=profiles,
                  pairs=pairs,binary_port=binary,text_ports=[binary+100,binary+139],
                  standard=standard,normal_speed=normal_speed,adapter_sha256=sha(__file__),
                  per_cohort_frames=len(profiles)*(2*pairs+4),
                  minimum_distinct_REU_bytes=2*len(profiles)*(2*pairs+4)*16777216,
                  resource_note='Native execute serializes cohorts and hardlinks ONLY closed successful output; actual REU captures still require the declared distinct bytes plus backing images/overhead.',
                  scope=__doc__)
    for cohort, source in [('control',control),('candidate',candidate)]:
        e = out/cohort
        native_freeze(source,e)
        trace_proof(e,source)
        logs = []
        for name in profiles:
            _,text,_,filename = DOCUMENTS[name]
            path = e/(filename.decode().lower()+'.seq')
            path.write_bytes(timing.native.live.grid.native_text(text))
            p = subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(path),filename.decode().lower()+',s'],capture_output=True,text=True)
            logs.append(p.stdout+p.stderr)
            assert not p.returncode
            assert D81Image((e/'working.d81').read_bytes()).read(filename,kind=1).data == path.read_bytes()
        (e/'documents-package.log').write_text('\n'.join(logs))
        shutil.copy2(e/'working.d81',e/'profile-initial.d81')
        n = scenario(e,config)
        plan = n.plan()
        assert len({s['id'] for s in plan['steps']}) == len(plan['steps'])
        assert len(n.measurements) == config['per_cohort_frames']
        (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
        (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
        (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
        (e/'adapter-config.json').write_text(json.dumps(dict(config,cohort=cohort),indent=2)+'\n')
        with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
            for folder in ('tests','tools'):
                for path in sorted((ROOT/folder).glob('*.py')):
                    z.write(path,path.relative_to(ROOT))
        print('PREPARED',cohort,e,'frames',len(n.measurements),'steps',len(plan['steps']),flush=True)
    (out/'adapter.json').write_text(json.dumps(config,indent=2)+'\n')
    return out


def free_ports(binary):
    for port in (binary,*range(binary+100,binary+140)):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',port))


def loaded(e):
    n = presentation.scenario_loaded(e)
    n.__class__ = Plan
    config = json.loads((e/'adapter-config.json').read_text())
    n.binary_port = config['binary_port']
    n.standard,n.model = (1,0) if config['standard'] == 'pal' else (2,3)
    n.trace_targets = json.loads((e/'trace-proof.json').read_text())
    n.measurement_warp = not config['normal_speed']
    return n


def evaluate(e):
    n = loaded(e)
    expected, catalog = timing.semantic.expected, timing.FontCatalog
    timing.semantic.expected = presentation.expected_geos
    timing.FontCatalog = lambda path,native:preview.pack_catalog((e/'font-pack.bin').read_bytes(),native)
    try:
        result = timing.evaluate(n)
    finally:
        timing.semantic.expected, timing.FontCatalog = expected, catalog
    config = json.loads((e/'adapter-config.json').read_text())
    assert len(result['measurements']) == config['per_cohort_frames']
    s = n.s
    images = timing.native.live.grid.reu_images(n.out/'run')
    groups, outside, records = {}, {}, []
    for item in result['measurements']:
        tag = item['id']
        ram = (n.out/'captures'/(tag+'-ram.bin')).read_bytes()
        before_ram = (n.out/'captures'/(tag+'-before-ram.bin')).read_bytes()
        f = Captured(s,ram,(n.out/'captures'/(tag+'-colors.bin')).read_bytes(),e)
        reu = images[tag]
        assert len(reu) == 16777216
        assert f.get('se_render_caps',1) == item['caps'] and f.get('se_hot_caret') == item['expected_caret']
        assert f.get('se_hot_pending',1) == item['expected_pending'] and not f.get('se_sel_mark',1)
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1)) == item['filename'].encode()
        assert f.read(s['se_editor_settings'],64) == (e/'editor-defaults.bin').read_bytes()
        state = f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],width) for k,width in [
            ('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),
            ('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),
            ('se_clip_token',5),('se_clip_length',3)])
        assert state == groups.setdefault(item['profile'],state),(tag,'pending canonical/history/clip changed')
        handle = f.get('se_gc_handle',1)
        bank = ram[s['se_reu_map']+handle]
        assert handle and bank and ram[s['se_reu_logical_owner']+handle] == ram[s['se_reu_physical_owner']+bank] == 0xfe
        assert [b for b in range(256) if ram[s['se_reu_physical_owner']+b] == 0xfe] == [bank]
        masked = bytearray(reu)
        for lo,hi in ((0,64),(0x200,0xea88)):
            masked[bank*65536+lo:bank*65536+hi] = bytes(hi-lo)
        digest = hashlib.sha256(masked).hexdigest()
        assert digest == outside.setdefault(item['profile'],digest),(tag,'whole16MiB outside source/GTF FE contract')
        # timing.evaluate authenticates every one of62 actual SEO payloads.
        # Also retain the exact physical FD font-bank content check.
        pack = (e/'font-pack.bin').read_bytes()
        for i,h in enumerate(f.read(s['se_gf_state']+1,2)):
            p = ram[s['se_reu_map']+h]
            assert h and p and ram[s['se_reu_logical_owner']+h] == ram[s['se_reu_physical_owner']+p] == 0xfd
            raw = pack[i*65536:(i+1)*65536]
            assert reu[p*65536:p*65536+len(raw)] == raw
        calls = {(v['slot'],v['id']) for v in item['cost_profile']['groups']}
        log = (n.out/('stopwatch-'+tag+'.log')).read_text(encoding='utf-8-sig')
        # Conditional tracepoints do not duplicate actual PCs within one slot
        # at the same time: group by physical PC so counts remain unambiguous.
        pcs = [int(v,16) for v in re.findall(r'(?m)^\.C:([0-9a-f]{4})\s',log,re.I)]
        trace_counts = {}
        for target in n.trace_targets:
            key = target['asset']+':'+target['symbol']
            trace_counts[key] = pcs.count(target['pc'])
        parser_keys = [k for k in trace_counts if any(x in k for x in (':se_sm_',':se_si_',':se_sl_'))]
        assert not any(trace_counts[k] for k in parser_keys),(tag,'actual parser init/feed trace',trace_counts)
        # A trace PC by itself cannot identify code in the shared5000 window.
        # Require exact frozen instruction bytes plus actual nested R30 call
        # timestamps. The supervisor validates the stage before its JSR5000.
        stage = (e/'type.seo').read_bytes()[68:]
        stage_lines = []
        intervals = [v for v in item['cost_profile']['overlay_intervals'] if (v['slot'],v['id']) == (0,30)]
        for target in n.trace_targets:
            if target['asset'] != 'type':
                continue
            for line in log.splitlines():
                match = re.match(r'\.C:([0-9a-f]{4})\s+((?:[0-9a-f]{2}\s+){1,3}).*?\s(\d+)\s*$',line,re.I)
                if not match or int(match[1],16) != target['pc']:
                    continue
                code = bytes.fromhex(match[2]); clock = int(match[3]); at = target['pc']-0x5000
                assert code == stage[at:at+len(code)],(tag,'frozen staged instruction',line)
                assert sum(v['payload'] <= clock < v['payload_end'] for v in intervals) == 1,(tag,'staged trace outside live R30',line)
                stage_lines.append(dict(symbol=target['symbol'],pc=target['pc'],clock=clock,opcode=code.hex()))
        transaction = trace_counts['type:se_gst_transaction']
        assert transaction == int(item['expected_transaction']),(tag,'actual staged transaction',transaction)
        if item['expected_transaction']:
            assert (0,30) in calls and (1,21) not in calls and ram[0x8ba0] == 2
            assert ram[0x5000:0x5000+len(stage)] == stage and ram[0xcbd5] == 0x42,(tag,'complete immutable executed stage and namespace')
            names=json.loads((e/'freeze.json').read_text())['catalog'];index=runtime_index(e,names,'type')
            backing = ram[s['se_overlay_asset']+(index>>4)]
            physical = ram[s['se_reu_map']+backing]
            epoch = ram[s['se_reu_epoch']:s['se_reu_epoch']+2]
            assert ram[0x5fe0:0x5fe5] == bytes([index,backing,physical])+epoch,(tag,'actual staged capability stamp')
        else:
            assert (0,27) in calls and (1,21) not in calls
        if item['caps'] == 0:
            forbidden={(1,k) for k in (14,15,17,18,19,24,25,26,31,34,35,37,39,45,47,49)}|{(0,31),(0,36),(0,37)}
            assert not calls & forbidden and f.get('se_st_request',1) == f.get('se_st_valid',1) == 0
        records.append(dict(id=tag,profile=item['profile'],action=item['action'],
                            first_publish_cycles=item['first_publish_cycles'],settled_cycles=item['emulated_cycles'],
                            counter_deltas=item['counter_deltas'],service_peak_cycles=item['service_peak_cycles'],
                            shared_window_before=before_ram[s['se_gf_state']+21],shared_window_after=ram[s['se_gf_state']+21],
                            trace_counts=trace_counts,staged_instruction_witnesses=stage_lines,pixels_sha256=hashlib.sha256(ram[0x6000:0x7f40]+ram[0x4000:0x43e8]).hexdigest(),
                            png_sha256=sha(n.out/('native-'+tag+'.png'))))
    assert (e/'working.d81').read_bytes() == (e/'profile-initial.d81').read_bytes()
    summary = dict(status='PASS',identity=result['identity'],records=records,native_pixels=result['native_pixels'],
                   scope='Original native evaluator retained: allVICpixels, canonical merged bytes, all62 payloads, normalized catalog, shim/lowerstack/cold-probe/IRQ resources. Extra exact pending source/history/clip/settings/FDfonts and whole16MiB outside FE[0,64)+[0200,EA88). No hardware/physical key latency claim.')
    (n.out/'warm-shift-result.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def compile_plan(e, run=False):
    n = loaded(e)
    config = json.loads((e/'adapter-config.json').read_text())
    plan = json.loads((n.out/'plan.yaml').read_text())
    assert len({s['id'] for s in plan['steps']}) == len(plan['steps'])
    assert plan['global_defaults']['monitor_port_start'] == config['binary_port']
    project = timing.native.live.grid.synchronous_project(n.out)
    vice_plan.PROJECT = project
    p = subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(p.stdout+p.stderr)
    assert not p.returncode
    if not run:
        p = subprocess.run(['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(n.out/'plan.yaml')],capture_output=True,text=True,timeout=120)
        (n.out/'compile-only.log').write_text(p.stdout+p.stderr)
        assert not p.returncode
        return None
    free_ports(config['binary_port'])
    stop = threading.Event()
    def observe():
        while not stop.wait(.1):
            p = subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
            for line in p.stdout.splitlines():
                if '/x64sc ' in line and f'-binarymonitoraddress 127.0.0.1:{config["binary_port"]}' in line and str(e/'working.d81') in line:
                    fields = line.strip().split(None,2)
                    (e/'owned-process.json').write_text(json.dumps(dict(PID=int(fields[0]),parent=int(fields[1]),command=fields[2],binary_port=config['binary_port'],text_ports=config['text_ports'],kill_stale=False,scope='Read-only ps; exact owned disk and binary port must both match.'),indent=2)+'\n')
                    return
    watcher = threading.Thread(target=observe,daemon=True)
    watcher.start()
    try:
        receipt = run_with_closed_links(capacity.run_owned_plan,plan,n.out,timeout=2400)
    finally:
        stop.set()
        watcher.join(timeout=3)
    (n.out/'owned-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert (e/'owned-process.json').exists(),'native PID witness absent; inspect launch args, no unowned process may be killed'
    owned = json.loads((e/'owned-process.json').read_text())
    process = subprocess.run(['ps','-p',str(owned['PID']),'-o','command='],capture_output=True,text=True)
    assert str(e/'working.d81') not in process.stdout,'owned process did not close'
    (e/'owned-closure.json').write_text(json.dumps(dict(PID=owned['PID'],exact_command_absent=True,close_vice=True),indent=2)+'\n')
    free_ports(config['binary_port'])
    return evaluate(e)


def compare(prepared):
    results = [json.loads((prepared/c/'timing/warm-shift-result.json').read_text()) for c in ('control','candidate')]
    rows = []
    for a,b in zip(results[0]['records'],results[1]['records']):
        assert a['id'] == b['id'] and a['pixels_sha256'] == b['pixels_sha256']
        # Expanded native RGB crop comparison is independent of PNG encoding.
        images = []
        for cohort in ('control','candidate'):
            e = prepared/cohort
            r = json.loads((e/'timing/result.json').read_text())
            w,h,rgb = read_png(e/'timing'/('native-'+a['id']+'.png'))
            x,y = r['native_viewport']
            images.append([rgb[(y+yy)*w+x+xx] for yy in range(200) for xx in range(320)])
        assert images[0] == images[1]
        rows.append(dict(id=a['id'],control_cycles=a['settled_cycles'],candidate_cycles=b['settled_cycles'],
                         first_publish_control=a['first_publish_cycles'],first_publish_candidate=b['first_publish_cycles'],
                         percent_saved=100*(a['settled_cycles']-b['settled_cycles'])/a['settled_cycles'],
                         control_counters=a['counter_deltas'],candidate_counters=b['counter_deltas']))
    assert len(rows) == len(results[0]['records']) == len(results[1]['records'])
    result = dict(status='PASS',comparisons=rows,scope='Native measured whole-operation cycles, first-publication separately; exact independent pixels then paired physical VIC RGB. Not inferred from CPU instructions.')
    (prepared/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control',type=Path,default=CONTROL)
    p.add_argument('--out',type=Path)
    p.add_argument('--prepared',type=Path)
    p.add_argument('--profiles',choices=tuple(DOCUMENTS),nargs='+',default=['plain','strong'])
    p.add_argument('--pairs',type=int,default=4)
    p.add_argument('--binary',type=int,default=8300)
    p.add_argument('--standard',choices=['pal','ntsc'],default='pal')
    p.add_argument('--normal-speed',action='store_true')
    p.add_argument('--compile-only',action='store_true')
    p.add_argument('--run',action='store_true')
    p.add_argument('--verify',action='store_true')
    p.add_argument('--cohort',choices=['control','candidate','both'],default='both')
    a = p.parse_args()
    if not a.prepared:
        assert not a.run and not a.verify,'Prepare first; execution requires explicit --prepared.'
        assert 4 <= a.pairs <= 5 and len(a.profiles) == len(set(a.profiles))
        out = (a.out or ROOT/'build/warm-shift-native-adapter'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
        prepare(out,a.control.resolve(),a.profiles,a.pairs,a.binary,a.standard,a.normal_speed)
    else:
        out = a.prepared.resolve()
        config = json.loads((out/'adapter.json').read_text())
        assert config['adapter_sha256'] == sha(__file__),'Use exact prepared adapter source for execution.'
    for cohort in (('control','candidate') if a.cohort == 'both' else (a.cohort,)):
        if a.verify:
            evaluate(out/cohort)
        elif a.run or a.compile_only:
            compile_plan(out/cohort,run=a.run)
    if (a.run or a.verify) and a.cohort == 'both':
        compare(out)
    print('READY' if not (a.run or a.verify) else 'PASS',out,flush=True)

if __name__ == '__main__':
    main()

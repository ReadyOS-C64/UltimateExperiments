"""Actual parser-entry counters for Plain/Markdown/Full source presentation.

No product build, CPU replacement, parser interception or native claim. The
read-only observer runs around the existing Peddle instruction step. Inputs use
actual editor command/input/render/idle paths. GEOS pixel/nav semantics and File
UI are independently qualified by their existing/parallel gates.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ctypes as C
import hashlib
import json
import re
import shutil
import subprocess
import sys

import test_geos_editor as geos
import test_geos_fold_editor as fold
import test_fold_retention as retention

ROOT = geos.ROOT
WORKERS = ('viewsource', 'styler', 'lexical', 'foldparse', 'foldfinish', 'foldctl',
           'geossema', 'geoslex', 'geosinln')
PRESETS = (('plain', 0), ('markdown', 1), ('full', 3))
SOURCE = geos.native_text(
    '# Heading **strong** and *emphasis*\r'
    'Ordinary interior prose with **bold** and @@code@@ plus a late close.\r'
    '- Bullet words\r:::basic\r10 PRINT "Hello":REM tail\r20 DATA 1,2,3\r:::\r'
    ':::asm\rstart: lda #$2A ; native comment\r .byte "ab",$FF\r:::\r'
    'Last prose line.\r')
INSERTED = geos.native_text('Q')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols(path):
    return {name: int(address, 16) for address, name in
            re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)', Path(path).read_text())}


def capture_labels(out, fixture):
    """Run only while parent promises a coherent build, or reuse saved pairs."""
    directory = out / 'entry-labels'
    manifest = out / 'entry-labels.json'
    if not directory.exists():
        directory.mkdir()
        paths = {name: ROOT / 'build/overlays' / name for name in WORKERS}
        # Optional new52 assets; historical fixtures retain their original targets.
        for name, asset in (('cachebuild', 'sema'), ('cachequery', 'inln'), ('cacheforward', 'page')):
            if (fixture / 'build/overlays' / (asset + '.seo')).exists():
                paths[name] = ROOT / 'build/cache-editor' / asset
        paths.update(stage31=ROOT / 'build/geos-prod/code-typing/stage',
                     stage32=ROOT / 'build/geos-prod/style-typing/stage')
        records = {}
        for name, source in paths.items():
            asset = {'stage31': 'clex', 'stage32': 'type', 'cachebuild': 'sema', 'cachequery': 'inln', 'cacheforward': 'page'}.get(name, name)
            raw = source.with_suffix('.bin').read_bytes()
            assert raw == (fixture / 'build/overlays' / (asset + '.seo')).read_bytes()[36:], (name, 'incoherent labels/binary')
            records[name] = dict(asset=asset, binary_sha256=hashlib.sha256(raw).hexdigest())
            for extension in ('.bin', '.lbl'):
                target = directory / (name + extension)
                shutil.copy2(source.with_suffix(extension), target)
                records[name][extension] = sha(target)
        manifest.write_text(json.dumps(records, indent=2) + '\n')
    records = json.loads(manifest.read_text())
    targets = []
    names = json.loads((fixture / 'freeze.json').read_text())['names']
    for name, record in records.items():
        for extension in ('.bin', '.lbl'):
            assert sha(directory / (name + extension)) == record[extension]
        raw = (directory / (name + '.bin')).read_bytes()
        assert raw == (fixture / 'build/overlays' / (record['asset'] + '.seo')).read_bytes()[36:]
        labels = symbols(directory / (name + '.lbl'))
        staged = name.startswith('stage')
        signature = raw[32:48] if staged else b'\0' * 16
        for function in ('entry', 'se_sm_init', 'se_sm_feed', 'se_sm_finish',
                         'se_si_init', 'se_si_feed', 'se_si_finish',
                         'se_sl_init', 'se_sl_feed', 'se_sl_finish'):
            if function not in labels:
                continue
            pc = labels[function]
            # The sealed container's B010 safe entry is not its staged body.
            if staged and function == 'entry':
                pc = 0x5000
            if staged:
                assert 0x5000 <= pc < 0x5000 + len(raw) - 32, (name, function, hex(pc))
            else:
                assert 0xB010 <= pc < 0xB000 + len(raw), (name, function, hex(pc))
            targets.append(dict(name=f'{name}:{function}', pc=pc,
                                kind=3 if staged else 2,
                                tag=0 if staged else names.index(record['asset']) + 1,
                                signature=signature.hex()))
    assert len(targets) <= 64
    assert any(t['name'] == 'viewsource:se_sm_feed' for t in targets)
    assert any(t['name'] == 'geosinln:se_si_feed' for t in targets)
    assert any(t['name'] == 'stage31:se_sl_feed' for t in targets)
    return targets


def runner(out):
    # Existing host CPU library is required; this lane must not rebuild a shared
    # runtime just because a vendor fingerprint changed concurrently.
    extension = '.dylib' if sys.platform == 'darwin' else '.so'
    assert (ROOT / ('build/libse_peddle' + extension)).exists()
    retention.runner(out)
    cpp = out / 'runner.cpp'
    source = cpp.read_text()
    needle = 'static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
    assert source.count(needle) == 1
    # New optional type53 baseline writes are authorized only for a counted
    # initial GEOS baseline. Existing typed46/FE and exact observed-DMA masks
    # remain unchanged; ordinary cached queries cannot write type53.
    source = source.replace('static uint8_t audit_mask',
        'static bool pb_allow_baseline=false;static uint32_t pb_arena_writes=0;\n'
        'extern "C" void pb_arena_begin(bool allow){pb_allow_baseline=allow;pb_arena_writes=0;}\n'
        'extern "C" uint32_t pb_arena_get(){return pb_arena_writes;}\nstatic uint8_t audit_mask')
    guard='(lo!=0x46 && lo!=0xfe)'
    assert source.count(guard)==1
    source=source.replace(guard,'(lo!=0x46 && lo!=0xfe && !(lo==0x53 && pb_allow_baseline))')
    source=source.replace('memset(audit_mask+uint32_t(bank)*65536+at,1,n);audit_writes++;',
        'if(lo==0x53)pb_arena_writes++;memset(audit_mask+uint32_t(bank)*65536+at,1,n);audit_writes++;')
    extra = r'''
static bool pb_on=false;static unsigned pb_n=0;static uint16_t pb_active,pb_pc[64];
static uint8_t pb_kind[64],pb_tag[64],pb_sig[64][16];static uint64_t pb_count[64];
static uint16_t pb_faults[64][6];static unsigned pb_fault_count=0;
extern "C" void pb_config(uint16_t active,unsigned n,const uint16_t*pc,const uint8_t*kind,const uint8_t*tag,const uint8_t*sig){pb_active=active;pb_n=n;memcpy(pb_pc,pc,n*2);memcpy(pb_kind,kind,n);memcpy(pb_tag,tag,n);memcpy(pb_sig,sig,n*16);}
extern "C" void pb_begin(){memset(pb_count,0,sizeof(pb_count));pb_fault_count=0;pb_on=true;}
extern "C" void pb_end(){pb_on=false;}
extern "C" uint64_t pb_get(unsigned n){return pb_count[n];}
extern "C" unsigned pb_fault_get(unsigned n,uint16_t*out){if(n>=pb_fault_count)return 0;memcpy(out,pb_faults[n],12);return 1;}
static void pb(ZeroPagePeddle*m,uint16_t pc){if(!pb_on)return;auto r=zeropage_peddle_regs(m);
 if(r.a==0xb0 && (r.p&1) && zeropage_peddle_read(m,pc)==0x60 && pb_fault_count<64){auto q=pb_faults[pb_fault_count++];q[0]=pc;q[1]=zeropage_peddle_read(m,pb_active);q[2]=zeropage_peddle_read(m,pb_active+1);q[3]=r.sp;q[4]=zeropage_peddle_read(m,0x100+uint8_t(r.sp+1))|(zeropage_peddle_read(m,0x100+uint8_t(r.sp+2))<<8);q[5]=zeropage_peddle_read(m,0x9134);}
 for(unsigned i=0;i<pb_n;i++){
 if(pc!=pb_pc[i])continue;
 if(pb_kind[i]==2 && zeropage_peddle_read(m,pb_active+1)!=pb_tag[i])continue;
 if(pb_kind[i]==3){bool same=true;for(unsigned j=0;j<16;j++)if(zeropage_peddle_read(m,0x5000+j)!=pb_sig[i][j]){same=false;break;}if(!same)continue;}
 pb_count[i]++;}}
'''
    source = source.replace(needle, extra + needle + 'pb(m,r.pc);')
    cpp.write_text(source)
    path = out / ('bypass-runner' + extension)
    subprocess.run(['clang++', '-std=c++20', '-O2',
                    '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC',
                    '-I' + str(geos.grid.VENDOR), str(cpp),
                    str(ROOT / ('build/libse_peddle' + extension)), '-o', str(path)], check=True)
    dll = C.CDLL(str(path))
    dll.gm_rom.argtypes = [C.c_void_p, C.c_void_p]
    dll.gm_rom_count.restype = C.c_uint64
    dll.gm_profile.argtypes = [C.c_uint16, C.c_uint8, C.c_uint8] + [C.c_uint16] * 4
    for name in ('gm_run', 'gm_idle'):
        getattr(dll, name).restype = C.c_uint64
    dll.gm_run.argtypes = [C.c_void_p, C.c_uint64]
    dll.gm_idle.argtypes = [C.c_void_p, C.c_uint16, C.c_uint64]
    dll.gm_read.argtypes = [C.c_void_p, C.c_uint16, C.c_uint32, C.c_void_p]
    dll.gm_reu.argtypes = [C.c_void_p, C.c_uint32, C.c_void_p]
    dll.fr_begin.argtypes = [C.c_uint16] * 7
    dll.fr_mask.argtypes = [C.c_void_p]
    dll.fr_bad.restype = dll.fr_writes.restype = C.c_uint32
    dll.pb_config.argtypes = [C.c_uint16, C.c_uint] + [C.c_void_p] * 4
    dll.pb_arena_begin.argtypes=[C.c_bool]
    dll.pb_arena_get.restype=C.c_uint32
    dll.pb_get.argtypes = [C.c_uint]
    dll.pb_get.restype = C.c_uint64
    dll.pb_fault_get.argtypes = [C.c_uint, C.c_void_p]
    dll.pb_fault_get.restype = C.c_uint
    return dll


def drain(f):
    f.render()
    for count in range(100000):
        quiet = not f.get('se_e_job', 1) and not f.get('se_e_redraw', 1)
        quiet &= f.get('se_f_owner', 1) == 0 and f.get('se_st_request', 1) != 1
        # STYLE_STATE/FS are phase aliases. Once owner0 is published, their
        # bytes are not style-busy/lease fields and must not gate quiescence.
        if quiet:
            assert not f.get('se_e_error', 1), f.debug()
            return count
        f.tick()
    raise AssertionError(('foreground did not quiesce', f.debug()))


def enforce(caps, counts, *, warm=False, allowed_plain=()):
    if caps == 0:
        bad = {k:v for k,v in counts.items() if v and k not in allowed_plain}
        assert not bad, ('Plain executed semantic/staged work', bad)
    elif caps == 1:
        bad = {k: v for k, v in counts.items() if v and
               (k.startswith(('lexical:', 'geoslex:', 'stage31:')) or ':se_sl_' in k)}
        assert not bad, ('Markdown executed language lexer', bad)
    if warm:
        assert not any(v for k, v in counts.items() if k.endswith(('_feed', '_finish'))), ('unchanged warm idle parsed source', counts)


def run(out, fixture, *, smoke=False, mode_only=None, fold_only=False):
    identity = json.loads((fixture / 'freeze.json').read_text())
    assert sha(fixture / 'build/editor.prg') == identity['prg_sha256']
    for name, expected in identity['assets'].items():
        assert sha(fixture / 'build/overlays' / (name + '.seo')) == expected
    targets = capture_labels(out, fixture)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = fixture
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = runner(out)
    f = fold.Fixture(out, fixture, dll, True)
    dll.pb_config(f.s['se_overlay_active'], len(targets),
                  (C.c_uint16 * len(targets))(*[t['pc'] for t in targets]),
                  (C.c_uint8 * len(targets))(*[t['kind'] for t in targets]),
                  (C.c_uint8 * len(targets))(*[t['tag'] for t in targets]),
                  (C.c_uint8 * (len(targets) * 16)).from_buffer_copy(b''.join(bytes.fromhex(t['signature']) for t in targets)))
    records = []
    (out / 'counter-targets.json').write_text(json.dumps(targets, indent=2) + '\n')

    def counted(tag, caps, operation, *, readonly=False, warm=False, allowed_plain=()):
        canonical, catalog = f.canonical(), f.catalog()
        before = f.reu() if readonly else None
        cache_before={n:f.get(n,w) for n,w in [('se_bc_flags',1),('se_bc_count',1)]} if 'se_bc_flags' in f.s else {}
        initial_baseline=(caps!=0 and f.get('se_mode',1)==3 and cache_before.get('se_bc_flags',0)&0x1f==2)
        dll.pb_arena_begin(initial_baseline)
        if readonly:
            f.audit_begin()
        dll.pb_begin()
        try:
            operation()
        except BaseException as error:
            trace = []
            for i in range(64):
                raw = (C.c_uint16 * 6)()
                if not dll.pb_fault_get(i, raw):
                    break
                trace.append(dict(pc=hex(raw[0]), rtag=raw[1], ctag=raw[2],
                                  sp=hex(raw[3]), caller=hex(raw[4] + 1), page_phase=raw[5]))
            (out / 'failed-counter-context.json').write_text(json.dumps(dict(
                tag=tag, error=str(error), trace=trace,
                counts={t['name']: int(dll.pb_get(i)) for i, t in enumerate(targets)},
                state={n:f.get(n,w) for n,w in [('se_mode',1),('se_render_caps',1),
                    ('se_e_job',1),('se_e_error',1),('se_f_owner',1),('se_hot_caret',3),
                    ('se_v_top',3)]}), indent=2) + '\n')
            raise
        finally:
            dll.pb_end()
            f.dll.fr_end()
        counts = {t['name']: int(dll.pb_get(i)) for i, t in enumerate(targets)}
        enforce(caps, counts, warm=warm, allowed_plain=allowed_plain)
        assert f.get('se_render_caps', 1) == caps
        assert f.catalog() == catalog and f.read(0xC600, 1024) == f.shim
        writes = f.audit_end(before, tag) if readonly else None
        arena_writes=int(dll.pb_arena_get())
        cache_after={n:f.get(n,w) for n,w in [('se_bc_flags',1),('se_bc_count',1)]} if cache_before else {}
        if arena_writes:
            assert initial_baseline and cache_after['se_bc_flags']&1 and cache_after['se_bc_count']==0,(tag,'unexpected type53 writes',cache_before,cache_after)
        if readonly:
            assert f.canonical() == canonical, (tag, 'canonical source/history/clipboard changed')
        assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_doc_read_locks', 'se_e_job'))
        assert f.m.read(0x912D) == 0, (tag, 'GEOS owned-source continuation remains live')
        row = dict(tag=tag, caps=caps, mode=f.get('se_mode', 1),
                   source_sha256=hashlib.sha256(f.merged()).hexdigest(), counts=counts,
                   derived_dma_writes=writes,typed53_dma_writes=arena_writes,cache_before=cache_before,cache_after=cache_after,
                   screen_sha256=hashlib.sha256(f.read(0x6000, 8000) + f.read(0x4000, 1000)).hexdigest())
        records.append(row)
        (out / 'progress.json').write_text(json.dumps(records, indent=2) + '\n')
        print('CASE', tag, {k: v for k, v in counts.items() if v}, flush=True)
        return counts

    try:
        assert f.get('se_render_caps', 1) == f.s['se_presentation_default']
        modes = () if fold_only else (mode_only,) if mode_only is not None else (0,) if smoke else range(4)
        for mode in modes:
            for preset, caps in PRESETS:
                f.source(SOURCE)
                f.put('se_status', 1, 1)  # fixture enables actual idle, not ROM/VIC simulation
                f.command((96, 97, 98, 99)[mode])
                f.typed(geos.native_text('syntax ' + preset))
                assert f.get('se_render_caps', 1) == caps, (preset, f.debug())
                # Explicit derived-cache invalidation requests a real cold
                # source render; no class/style/parser result is host-seeded.
                f.put('se_r_valid', 0, 1)
                f.put('se_l_valid', 0, 1)
                f.put('se_l_need_wrap', 1, 1)
                first = counted(f'{mode}-{preset}-cold-render', caps, lambda: drain(f), readonly=True)
                feeds = sum(v for k, v in first.items() if k.endswith(':se_sm_feed'))
                lex = sum(v for k, v in first.items() if k.endswith(':se_sl_feed'))
                if caps:
                    if mode==3 and 'cachequery:entry' in first and not feeds:
                        # Count actual C35 execution, never an unchanged FE-only
                        # repaint as a positive parser/cache control.
                        assert first['cachequery:entry']>0,(mode,preset,'missing positive cached-query control',first)
                        assert f.get('se_bc_flags',1)&0x0f==1 and f.get('se_bc_count',1)==0,(mode,preset,'query has no ARMED drained baseline')
                        assert first.get('geossema:se_sm_feed',0)==first.get('cachebuild:se_sm_feed',0)==0
                    else:
                        assert feeds > 0, (mode, preset, 'missing positive block-parser control')
                if caps == 3:
                    assert lex > 0, (mode, preset, 'missing positive lexer control')
                if mode==3 and caps and 'cachequery:entry' in first:
                    # A public wrap toggle invalidates page geometry while
                    # retaining the actual certified semantic baseline. This
                    # cannot pass on an unchanged FE repaint alone.
                    def cached_geometry():
                        f.command(73);drain(f)
                    cached=counted(f'{mode}-{preset}-cached-query-rebuild',caps,cached_geometry,readonly=True)
                    assert cached['cachequery:entry']>0,(preset,'no real C35 query')
                    assert f.get('se_bc_flags',1)&0x0f==1 and f.get('se_bc_count',1)==0
                    assert cached.get('geossema:se_sm_feed',0)==cached.get('cachebuild:se_sm_feed',0)==0,(preset,'cached rebuild parsed blocks',cached)
                    f.command(76);drain(f) #restore wrapped geometry for legacy cases
                counted(f'{mode}-{preset}-warm-idle', caps,
                        lambda: [f.tick() for _ in range(12)], readonly=True, warm=True)
                def typing():
                    f.key(INSERTED[0]);drain(f)
                counted(f'{mode}-{preset}-pending-typing', caps, typing)
                assert f.merged() == INSERTED + SOURCE
                def nav():
                    f.command(37);drain(f)
                    f.command(38);drain(f)
                    f.command(39);drain(f)
                counted(f'{mode}-{preset}-vertical-page', caps, nav)
                assert f.merged() == INSERTED + SOURCE
                f.command(16)  # actual undo; typing observer/history stays product code
                drain(f)
                assert f.merged() == SOURCE
        if not smoke and mode_only is None:
            # Real allocated fold object, parser-built metadata and edited-hint
            # retention. No synthetic map/token/flags or hidden-source seeding.
            from test_folds import action_model
            data = fold.TINY
            f.source(data);f.put('se_status', 1, 1);f.command(96)
            f.typed(geos.native_text('syntax full'));drain(f)
            def collapse():
                f.command(115);drain(f)
            collapse_counts = counted('fold-full-collapse-all', 3, collapse, readonly=True)
            assert collapse_counts['foldparse:se_sm_feed'] > 0
            tree, _ = action_model(fold.tree(data), 3, 0, 0, f.get('se_ef_motion', 4), 0)
            assert f.metadata() == b''.join(item.bytes() for item in tree)
            assert f.get('se_ef_fold_rows')
            stored = f.metadata()
            f.typed(geos.native_text('syntax plain'))
            counted('fold-plain-expanded', 0, lambda: drain(f), readonly=True)
            assert f.metadata() == stored and not f.get('se_ef_fold_rows')
            anchors = geos.grid.row_starts(data, f.get('se_v_top'), 40, False)
            actual = tuple(int.from_bytes(f.read(f.s['se_v_rows'] + i * 3, 3), 'little')
                           for i in range(22)) + (f.get('se_v_bottom'),)
            assert actual == anchors, ('Plain retained hidden source projection', actual, anchors)
            phase = f.read(0x8D00, 1152)
            counted('fold-plain-explicit-refusal', 0,
                    lambda: f.command(115, error=0xB0), readonly=True,  # current SF_BAD
                    allowed_plain=('foldctl:entry',))
            assert f.read(0x8D00, 1152) == phase and f.metadata() == stored
            position = data.index(geos.native_text('middle')) + 2
            def plain_edit():
                line = data[:position].count(b'\r') + 1
                column = position - (data.rfind(b'\r', 0, position) + 1)
                f.typed(geos.native_text(f'goto {line}'))
                for _ in range(column):
                    f.command(2)
                assert f.get('se_hot_caret') == position
                f.key(INSERTED[0]);drain(f)
            counted('fold-plain-pending-edit', 0, plain_edit)
            changed, expected_tree = retention.retained(tree, data, position, 0, INSERTED)
            assert f.merged() == changed and f.get('se_hot_pending', 1)
            assert f.metadata() == stored
            f.typed(geos.native_text('syntax full'))
            counted('fold-full-retained-rebuild', 3, lambda: drain(f), readonly=True)
            assert f.metadata() == b''.join(item.bytes() for item in expected_tree)
            assert f.merged() == changed and f.get('se_ef_fold_rows')
            assert all(item.flags & 1 for item in expected_tree)
        result = dict(status='passed', identity=identity, records=records,
                      scope='Actual linked source40/60/80/GEOS CPU commands, input, render and idle. Read-only instruction observer counts authenticated worker/parser entries; staged5000 signatures disambiguate font/stage aliases. ROM IEC/font and chargen-read seams are inherited fixture limitations. Plain/Markdown bypass and Full positive controls; independent source/history/clipboard/catalog/shim and exact observed typed16MiB readonly-render writes. Pixel/navigation semantics and native IRQ/VIC are separate gates. No product/shared assembler build.')
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        dll.pb_end()
        f.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--prepared', type=Path, help='existing output containing frozen entry-labels')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--mode', type=int, choices=range(4))
    parser.add_argument('--fold-only', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Prepared CPU counter gate. Use --run --prepared OUT --fixture IMMUTABLE [--smoke]; no shared build/native.')
        return
    assert args.fixture, 'parent-released immutable fixture is required'
    out = args.prepared or ROOT / 'build/presentation-bypass' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=True)
    print('RUN', out, flush=True)
    run(out, args.fixture.resolve(), smoke=args.smoke, mode_only=args.mode,
        fold_only=args.fold_only)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Source-build and execute actual-runtime FORMAT tests, without DOS media."""
from pathlib import Path
import sys, os
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.pycache_prefix = str(ROOT / 'build' / ('.absent-format-' + str(os.getpid())))
if sys.flags.optimize or Path(sys.pycache_prefix).exists():
    raise RuntimeError('Source-only unoptimized Python required')
import argparse, importlib.util, json, platform, re, shlex, subprocess, tempfile

def module(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
runtime = module('format_runtime', ROOT / 'build_support/runtime_media.py')
support = module('format_support', ROOT / 'build_support/native_media_tests.py')
digest, verify, copy, atomic = support.digest, support.verify, support.copy, support.atomic_json
OWNER = {'kind': 'dos64-floppy-format-tests', 'schema': 1}

def build(out):
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    if (out / 'OWNER.json').exists():
        if json.loads((out / 'OWNER.json').read_text()) != OWNER:
            raise RuntimeError('Different output owner')
    elif any(out.iterdir()):
        raise RuntimeError('Use an empty or owned output directory')
    else:
        atomic(out / 'OWNER.json', OWNER)
    locked = False; unlock_attempted = False; primary = None
    run = None; phase = 'lock'; commands = []
    record = {}; products = {}
    try:
        fd = os.open(out / 'LOCK', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd); locked = True
        run = Path(tempfile.mkdtemp(prefix='run-', dir=out))
        evidence = run / 'evidence'; evidence.mkdir()
        for name in ['floppy_format_tests.py', 'native_media_tests.py', 'runtime_media.py']:
            copy(ROOT / 'build_support' / name, evidence / name, record)
        phase = 'runtime'
        native = runtime.build(run / 'runtime', floppy_format=True)
        verify(native['source_inputs']); verify(native['native_products'])
        record.update(native['source_inputs']); record.update(native['native_products'])
        copy(run / 'runtime/RESULT.json', evidence / 'RUNTIME_RESULT.json', record)
        phase = 'model sources'
        inv = ROOT / 'build_support/native_media_sources.json'
        copy(inv, evidence / 'MODEL_INVENTORY.json', record)
        inventory = json.loads(inv.read_text())
        for source, wanted in inventory['model_baselines'].items():
            if digest(ROOT / source) != wanted:
                raise RuntimeError('Canonical model changed; review media overrides')
            record[str(ROOT / source)] = wanted
        for destination, source in inventory['test'].items():
            if destination.startswith(('model/', 'work/third_party/')):
                copy(ROOT / support.safe_relative(source), run / support.safe_relative(destination), record)
        pin = json.loads((run / 'work/third_party/peddle/UPSTREAM.json').read_text())
        for row in pin['files']:
            if digest(run / 'work/third_party/peddle' / row['path'])['sha256'] != row['sha256']:
                raise RuntimeError('Vendored Peddle changed')
        for source, destination in [('fixture.py', 'fixture.py'), ('test_runtime.py', 'test_runtime.py'),
                                    ('actual.zig', 'actual.zig'), ('build.zig', 'build-format.zig')]:
            copy(ROOT / 'tests/floppy_format' / source, run / destination, record)
        for name in ['dos64.prg', 'dos64.labels', 'dos64-overlay-package.json']:
            copy(Path(native['work']) / 'work/build' / name, run / 'work/build' / name, record)
        phase = 'tools'
        tools = support.tools(True)
        for path in [*tools.values(), Path(sys.executable).resolve()]: record[str(path)] = digest(path)
        env = support.command_environment(run, tools)
        def command(argv):
            args = list(map(str, argv)); commands.append({'argv': args, 'cwd': str(run)})
            atomic(evidence / 'COMMANDS.json', commands)
            with (evidence / 'commands.stdout').open('ab') as o, (evidence / 'commands.stderr').open('ab') as e:
                subprocess.run(args, cwd=run, env=env, stdin=subprocess.DEVNULL, stdout=o, stderr=e, check=True)
        # Pin Zig's installed source distribution and clang's actual SDK dependencies.
        command([tools['zig'], 'env', '--json'])
        raw_env = (evidence / 'commands.stdout').read_text()
        try:
            zig_env = json.loads(raw_env)
        except json.JSONDecodeError:
            # Zig 0.16 reports ZON; these two string fields retain JSON escaping.
            zig_env = {n: json.loads(re.search(r'\.' + n + r'\s*=\s*("(?:[^"\\]|\\.)*")', raw_env).group(1))
                       for n in ['lib_dir', 'zig_exe']}
        compiler = Path(zig_env['zig_exe']).resolve()
        record[str(compiler)] = digest(compiler)
        lib = Path(zig_env['lib_dir']).resolve()
        for path in sorted(lib.rglob('*')):
            if path.is_file(): record[str(path)] = digest(path)
        cpp = [Path('model/tests/floppy_export/bridge.cpp')] + [Path('work/third_party/peddle/Peddle') / n
            for n in ['Peddle.cpp', 'PeddleDebugger.cpp', 'PeddleDisassembler.cpp', 'StrWriter.cpp']]
        flags = ['-std=c++20', '-O2', '-Iwork/third_party/peddle/Peddle', '-Imodel/tests/host', '-Imodel/tests/floppy_export']
        phase = 'SDK dependencies'
        for i, source in enumerate(cpp):
            dep = evidence / ('model-%d.d' % i)
            command([tools['clang++'], *flags, '-M', '-MF', dep, source])
            for name in shlex.split(dep.read_text().replace('\\\n', '').split(':', 1)[1]):
                path = (run / name).resolve()
                if str(path) not in record:
                    copy(path, evidence / 'sdk' / path.relative_to(path.anchor), record)
        verify(record); atomic(evidence / 'INPUTS_BEFORE.json', record)
        phase = 'model compile'
        shared = ['-dynamiclib'] if platform.system() == 'Darwin' else ['-shared', '-fPIC']
        command([tools['clang++'], *flags, *shared, *cpp, '-o', 'model/format-peddle.dylib'])
        phase = 'Zig compile'
        command([tools['zig'], 'build', '--build-file', 'build-format.zig', 'compile', '--summary', 'all'])
        for path in [run / 'model/format-peddle.dylib', run / 'zig-out/bin/format-tests']:
            products[str(path)] = digest(path)
        atomic(evidence / 'PRODUCTS_BEFORE.json', products)
        phase = 'Python actual runtime'
        command([sys.executable, '-B', 'test_runtime.py'])
        result = json.loads((run / 'FORMAT_RUNTIME_RESULT.json').read_text())
        if result.get('passed') is not True or result.get('groups') != 12:
            raise RuntimeError('Expected twelve actual-runtime groups')
        phase = 'Zig actual runtime'
        command([run / 'zig-out/bin/format-tests'])
        if 'All 2 tests passed.' not in (evidence / 'commands.stderr').read_text():
            raise RuntimeError('Expected two directly executed Zig groups')
        phase = 'closure'; verify(record); verify(products)
        atomic(evidence / 'INPUTS_AFTER.json', record); atomic(evidence / 'PRODUCTS_AFTER.json', products)
        result = {'schema': 1, 'status': 'passed', 'scope': 'ACTUAL_RUNTIME_FORMAT_SYNTHETIC_NO_DOS_OR_HARDWARE_ACCEPTANCE',
                  'run': str(run), 'source_inputs': record, 'test_products': products, 'runtime_assets': native['assets'],
                  'groups': {'Python_actual_runtime': 12, 'direct_Zig': 2}, 'physical': False}
        atomic(run / 'RESULT.json', result)
        unlock_attempted = True
        (out / 'LOCK').unlink(); locked = False
        atomic(out / 'RESULT.json', result); return result
    except BaseException as ex:
        primary = ex
        failure = {'status': 'failed', 'phase': phase, 'error': type(ex).__name__ + ': ' + str(ex), 'run': str(run), 'prior_result_preserved': True}
        for p in ([run / 'FAILURE.json'] if run else []) + [out / 'LAST_FAILURE.json']:
            try: atomic(p, failure)
            except BaseException: pass
        raise
    finally:
        if locked and not unlock_attempted:
            try: (out / 'LOCK').unlink()
            except BaseException:
                if primary is None: raise

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT / 'build/floppy-format-tests')
    a = p.parse_args(); result = build(a.out)
    print(json.dumps({'status': result['status'], 'run': result['run'], 'groups': result['groups']}, indent=2))

"""Compact resident END: actual-CPU differential and full adapter regression.

Only private build/source-cleanup outputs are changed. The reference END and
frozen editor read_release are actual assembler, not Python substitutes.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, random, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from peddle import Machine

OUT = ROOT / 'build/source-cleanup'
FROZEN = ROOT / 'build/editor-file-integration/20261024T213441593038Z'
PRG_SHA = '2f6d1a76cb12424e03d2965e33853fb343032eead32797eca0a4b46fd9bf72ff'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_pair():
    OUT.mkdir(parents=True, exist_ok=True)
    report = json.loads((FROZEN / 'build/editor-report.json').read_text())
    symbols = report['symbols']
    # Caller context remains entirely private; the release target and document
    # fields are exact frozen resident addresses.
    imports = {n: symbols[n] for n in ['se_reu_epoch', 'se_doc_epoch',
        'se_doc_meta', 'se_doc_original', 'se_doc_append',
        'se_doc_read_locks', 'se_doc_read_release']}
    imports.update(se_fs_owned=0x8E08, se_fs_active=0x8E07,
                   se_fs_identity=0x8E1B)
    (OUT / 'externals.s').write_text('\n'.join(
        f'.export {n}\n{n} = ${v:04X}' for n, v in imports.items()) + '\n')
    source = (ROOT / 'src/fold/source-lease.s').read_text()
    (OUT / 'reference.s').write_text(source.replace('se_fs_end:',
                                                  'se_fs_end_reference:') +
                                    '\n.export se_fs_end_reference\n')
    (OUT / 'pair.cfg').write_text('''MEMORY {
 NEW:file="compact.bin",start=$1000,size=$0100,type=ro;
 OLD:file="reference.bin",start=$1100,size=$0100,type=ro;
}
SEGMENTS {
 CORE:load=NEW,type=ro,define=yes;
 FOLD_SOURCE_CLEANUP:load=OLD,type=ro,define=yes;
}
''')
    for name, source in [('compact', ROOT / 'src/style/source-cleanup.s'),
                         ('reference', OUT / 'reference.s'),
                         ('externals', OUT / 'externals.s')]:
        subprocess.run(['ca65', '-I', str(ROOT / 'src'), '-g', '-o',
                        str(OUT / (name + '.o')), str(source)], check=True)
    command = ['ld65', '-C', str(OUT / 'pair.cfg'), '-m', 'pair.map',
               '-Ln', 'pair.lbl', 'compact.o', 'reference.o', 'externals.o']
    subprocess.run(command, cwd=OUT, check=True)
    assert len((OUT / 'compact.bin').read_bytes()) == 54
    assert len((OUT / 'reference.bin').read_bytes()) == 105
    # Both token-contiguity assumptions must fail loudly at final link.
    text = (OUT / 'externals.s').read_text()
    for name in ['se_doc_original', 'se_doc_append']:
        bad = text.replace(f'{name} = ${imports[name]:04X}',
                           f'{name} = ${imports[name] + 1:04X}')
        (OUT / 'bad-externals.s').write_text(bad)
        subprocess.run(['ca65', '-o', str(OUT / 'bad-externals.o'),
                        str(OUT / 'bad-externals.s')], check=True)
        badcommand = [x if x != 'externals.o' else 'bad-externals.o'
                      for x in command]
        failure = subprocess.run(badcommand, cwd=OUT, capture_output=True,
                                 text=True)
        assert failure.returncode and 'token graph must be contiguous' in failure.stderr
        (OUT / (name + '-link-refusal.log')).write_text(failure.stderr)
    # Re-link good images after intentional failed links.
    subprocess.run(command, cwd=OUT, check=True)
    return imports


def differential(symbols):
    rng = random.Random(0x6502E0D)
    prg = (FROZEN / 'build/editor.prg').read_bytes()
    assert hashlib.sha256(prg).hexdigest() == PRG_SHA
    machine = Machine()
    machine.load(int.from_bytes(prg[:2], 'little'), prg[2:])
    machine.load(0x1000, (OUT / 'compact.bin').read_bytes())
    machine.load(0x1100, (OUT / 'reference.bin').read_bytes())
    spans = [(0x8E00, 128), (symbols['se_doc_meta'] - 4, 24),
             (symbols['se_doc_read_locks'] - 2, 5),
             (symbols['se_reu_epoch'], 2), (symbols['se_doc_epoch'], 2),
             (0xC600, 1024)]
    snapshot = lambda: [bytes(machine.read(a+i) for i in range(n))
                        for a, n in spans]
    restore = lambda data: [machine.load(a, b) for (a, _), b in zip(spans, data)]
    identity = symbols['se_fs_identity']
    owned = symbols['se_fs_owned']
    active = symbols['se_fs_active']
    locks = symbols['se_doc_read_locks']
    trials = []
    # Every checked identity byte can change independently on either side.
    for index in list(range(2)) + list(range(6, 21)):
        trials.extend([('identity', index), ('current', index)])
    trials.extend([('doc_epoch', 0), ('doc_epoch', 1)])
    # Captured doc epoch/gen/length/hot fields are intentionally irrelevant to
    # END: live provider/doc epochs and complete token graph own the lease.
    trials.extend(('ignored', i) for i in list(range(2, 6)) + list(range(21, 59)))
    trials += [('match', 0), ('unowned', 0), ('no_locks', 0)]
    trials += [('random', i) for i in range(4096)]
    released = 0
    for category, index in trials:
        machine.load(0x8E00, rng.randbytes(128))
        token = rng.randbytes(15)
        epoch = rng.randbytes(2)
        machine.load(identity, rng.randbytes(59))
        machine.load(identity, epoch)
        machine.load(identity + 6, token)
        machine.load(symbols['se_reu_epoch'], epoch)
        machine.load(symbols['se_doc_epoch'], epoch)
        machine.load(symbols['se_doc_meta'], token)
        machine.write(owned, rng.randrange(1, 256))
        machine.write(active, rng.randrange(256))
        machine.write(locks, rng.randrange(1, 256))
        mutate = lambda a: machine.write(a, machine.read(a) ^ rng.randrange(1, 256))
        if category == 'identity': mutate(identity + index)
        elif category == 'current':
            mutate(symbols['se_reu_epoch'] + index if index < 2
                   else symbols['se_doc_meta'] + index - 6)
        elif category == 'doc_epoch': mutate(symbols['se_doc_epoch'] + index)
        elif category == 'ignored': mutate(identity + index)
        elif category == 'unowned': machine.write(owned, 0)
        elif category == 'no_locks': machine.write(locks, 0)
        elif category == 'random':
            for _ in range(rng.randrange(6)):
                field = rng.choice([owned, active, locks,
                    symbols['se_reu_epoch'] + rng.randrange(2),
                    symbols['se_doc_epoch'] + rng.randrange(2),
                    symbols['se_doc_meta'] + rng.randrange(15),
                    identity + rng.randrange(59)])
                mutate(field)
        should_release = (machine.read(owned) != 0 and machine.read(locks) != 0
            and bytes(machine.read(identity+i) for i in range(2)) ==
                bytes(machine.read(symbols['se_reu_epoch']+i) for i in range(2)) ==
                bytes(machine.read(symbols['se_doc_epoch']+i) for i in range(2))
            and bytes(machine.read(identity+6+i) for i in range(15)) ==
                bytes(machine.read(symbols['se_doc_meta']+i) for i in range(15)))
        old_locks = machine.read(locks)
        before = snapshot()
        expected = [bytearray(x) for x in before]
        # Model permits exactly owned/active reset plus one owned decrement.
        for (base, width), values in zip(spans, expected):
            for address, value in [(owned, 0), (active, 0),
                                   (locks, old_locks - int(should_release))]:
                if base <= address < base + width: values[address-base] = value
        expected = list(map(bytes, expected))
        results = []
        for address in [0x1100, 0x1000]:
            restore(before)
            regs, _ = machine.call(address, a=0x81, x=0xE3, y=0x72)
            after = snapshot()
            assert regs.a == 0 and not regs.p & 1
            assert regs.y == 0x72, 'Y is preserved by both END implementations'
            assert after == expected, (category, index, address)
            # Repeated cancel must not decrement a second owned lease.
            regs, _ = machine.call(address)
            assert regs.a == 0 and not regs.p & 1 and snapshot() == after
            results.append(after)
        assert results[0] == results[1]
        released += int(should_release)
    machine.close()
    return dict(cases=len(trials), actual_owned_releases=released,
                idempotent_calls=len(trials)*2, link_refusals=2)


def adapter_regression():
    spec = importlib.util.spec_from_file_location('actual_source_adapter',
                                                ROOT / 'tests/test_fold_editor_source.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT / 'adapter'
    module.OUT.mkdir(exist_ok=True)
    cfg = (ROOT / 'src/fold/source-probe.cfg').read_text()
    cfg = cfg.replace('build/folds/editor-source/', 'build/source-cleanup/adapter/')
    cfg = cfg.replace('FOLD_SOURCE_CLEANUP:', 'CORE:')
    privatecfg = OUT / 'adapter.cfg'
    privatecfg.write_text(cfg)
    run = subprocess.run
    def redirected(command, *args, **kwargs):
        command = [str(x) for x in command]
        if command[0] == 'ca65' and command[-1] == str(ROOT / 'src/fold/source-lease.s'):
            command[-1] = str(ROOT / 'src/style/source-cleanup.s')
        if command[0] == 'ld65':
            command[command.index('-C')+1] = str(privatecfg)
        return run(command, *args, **kwargs)
    subprocess.run = redirected
    try:
        module.main()
    finally:
        subprocess.run = run
    result = json.loads((module.OUT / 'result.json').read_text())
    assert result['status'] == 'passed'
    return dict(result_file=str((module.OUT / 'result.json').relative_to(ROOT)),
                cases=len(result['cases']), builder_steps=result['builder_steps'],
                source_sha256=digest(ROOT / 'src/style/source-cleanup.s'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--differential-only', action='store_true')
    args = parser.parse_args()
    (OUT / 'result.json').unlink(missing_ok=True)
    symbols = compile_pair()
    result = dict(status='passed', compact_bytes=54, reference_bytes=105,
                  added_state_bytes=0, added_zero_page_bytes=0,
                  differential=differential(symbols), editor_prg_sha256=PRG_SHA)
    if not args.differential_only:
        result['actual_adapter_regression'] = adapter_regression()
    result['source_sha256'] = {str(p.relative_to(ROOT)):digest(p) for p in
        [ROOT / 'src/style/source-cleanup.s', Path(__file__)]}
    result['limits'] = ['Isolated actual-CPU test; no production placement or native/VIC claim.',
                        'X and arithmetic flags other than carry are scratch; A=0, carry clear.']
    (OUT / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()

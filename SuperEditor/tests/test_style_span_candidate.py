"""Private span-seeking C14: unchanged independent planner/lexer oracles.

No production source/build outputs are changed. Old and candidate modules run
the exact original guarded suites; additional grid tests use the public model.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import test_style_plan as base
import test_style_lexical as lexical
from supermark_model import blocks, inline, lex


def source_tree(out, baseline, candidate):
    project = out / ('candidate-source' if candidate else 'baseline-source')
    src = project / 'src'
    src.mkdir(parents=True)
    for p in (ROOT / 'src').iterdir():
        if p.name != 'style':
            (src / p.name).symlink_to(p, target_is_directory=p.is_dir())
    style = src / 'style'
    style.mkdir()
    for p in (ROOT / 'src/style').iterdir():
        if p.name != 'plan.s':
            (style / p.name).symlink_to(p, target_is_directory=p.is_dir())
    text = baseline.decode()
    if candidate:
        a, b = text.index('start_paint:\n'), text.index('\ninline_begin:\n')
        text = text[:a] + (ROOT / 'src/style/paint-span-candidate/paint.inc').read_text() + text[b:]
    (style / 'plan.s').write_text(text)
    (project / 'tests').symlink_to(ROOT / 'tests', target_is_directory=True)
    return project


def production(out, project, fixture):
    target = out / 'production'
    target.mkdir()
    run = lambda args: subprocess.run(list(map(str, args)), check=True)
    report = fixture / 'build/editor-report.json'
    run([sys.executable, ROOT / 'tools/overlay_api.py', '--report', report,
         '--output', target / 'style-api.inc', '--all-public'])
    run([sys.executable, ROOT / 'tools/overlay_api.py', '--report', report,
         '--output', target / 'editor-api.inc', '--all-public'])
    objs = []
    names = ['style/entry', 'style/plan', 'style/editor-control', 'style/reader-dispatch',
             'supermark/block', 'supermark/inline']
    for name in names:
        obj = target / (name.replace('/', '-') + '.o')
        args = ['ca65', '-g', '-I', project / 'src', '-I', target, '-o', obj]
        if name == 'style/plan':
            args += ['-D', 'SE_STYLE_LEXICAL=1', '-D', 'SE_STYLE_GRID=1']
        if name.startswith('supermark/'):
            args += ['-D', 'SE_SM_CODE_ONLY=1']
        run(args + [project / 'src' / (name + '.s')])
        objs.append(obj)
    run([sys.executable, ROOT / 'tools/module_bindings.py', '--report', report,
         '--output', target / 'bindings.s', '--require-export', 'se_style_auto', *objs])
    run(['ca65', '-o', target / 'bindings.o', target / 'bindings.s'])
    run(['ld65', '-C', ROOT / 'cfg/style-c.cfg', '-o', target / 'styler.bin',
         '-Ln', target / 'styler.lbl', '-m', target / 'styler.map', *objs, target / 'bindings.o'])
    size = (target / 'styler.bin').stat().st_size
    assert size <= 4096, size
    return size


def old_suites(out, baseline, project):
    result = {}
    for tag, path in [('baseline', baseline), ('candidate', project)]:
        base.ROOT = path
        base.OUT = out / tag / 'plan'
        base.main()
        lexical.ROOT = path
        lexical.OUT = out / tag / 'lexical'
        lexical.main()
        result[tag] = {'plan': json.loads((base.OUT / 'result.json').read_text()),
                       'lexical': json.loads((lexical.OUT / 'result.json').read_text())}
    base.ROOT = lexical.ROOT = ROOT
    return result


def grid_rows(data, width, nowrap, top=0):
    rows = [top]
    for _ in range(22):
        p = rows[-1]
        if nowrap:
            e = data.find(b'\r', p)
            p = len(data) if e < 0 else e + 1
        else:
            for _ in range(width):
                if p == len(data):
                    break
                c = data[p]
                p += 1
                if c == 13:
                    break
        rows.append(p)
    return rows


def grid_oracle(data, rows, width, nowrap, pan):
    styles = bytearray(len(data))
    palette = {7: 7, 8: 8, 9: 9, 10: 10, 11: 7, 12: 12, 13: 0}
    for e in blocks(data):
        k, a, b = e['kind'], e['start'], e['end']
        color = 0x82 if k == 2 else 4 if k == 5 else 10 if k in (4, 6, 7, 8) else 0
        styles[a:b] = bytes([color]) * (b-a)
        if k == 5:
            for start, end, role in lex(data[e['body']:b], e['language'], start=e['body']):
                styles[start:end] = bytes([palette[role]]) * (end-start)
        if k in (4, 5, 6):
            continue
        origin = e['body']
        for token, style, delim, start, end in inline(data[origin:b], origin, body_column=(origin-a) or None):
            if token != 1:
                continue
            for pos in range(start+delim, end):
                mask = (styles[pos] & 0xF0) | (style << 4)
                styles[pos] = mask | (4 if mask & 64 else [0, 1, 2, 3][(mask >> 4) & 3])
    return bytes(styles[pos] if pos < min(b, len(data)) and data[pos] != 13 else 0
                 for a, b in zip(rows, rows[1:]) for c in range(width)
                 for pos in [a + (pan if nowrap else 0) + c])


class GridFixture(lexical.Fixture):
    def __init__(self, *args):
        super().__init__(*args)
        self.instructions = 0
        # SE_STYLE_GRID adds exactly4 bytes to the original controller phase.
        # Protect everything after the actual linked controller/parser extent.
        end = self.s['__SM_STATE_RUN__'] + self.s['__SM_STATE_SIZE__']
        self.guard_ranges = [(a, b) for a, b in self.guard_ranges if a not in (0x4800, 0x8EDC)]
        self.guard_ranges.append((end, self.ram(end, 0x9180-end)))

    def call(self, *args):
        old = self.m.call
        def counted(*a, **k):
            r, count = old(*a, **k)
            self.instructions += count
            return r, count
        self.m.call = counted
        try:
            return super().call(*args)
        finally:
            self.m.call = old

    def seed_grid(self, data, width, nowrap, pan=0, top=0, chunk=128):
        super().seed(data, nowrap, pan, top=top, chunk=chunk)
        self.width, self.nowrap = width, nowrap
        self.rows = grid_rows(data, width, nowrap, top)
        self.m.load(self.s['se_st_rows'], b''.join(p.to_bytes(3, 'little') for p in self.rows))
        self.m.write(self.s['se_st_key']+32, {40: 0, 60: 2, 80: 4}[width] | nowrap)
        self.plan_address = 0x4400 if width == 40 else 0x4800
        spans = [(0x47E8, 0x818)] if width == 40 else [(0x4400, 880), (0x4800+width*22, 0x800-width*22)]
        self.plan_guards = []
        for a, n in spans:
            b = bytes((i*29+a) & 255 for i in range(n))
            self.m.load(a, b)
            self.plan_guards.append((a, b))

    def step(self):
        before = self.ram(self.plan_address, self.width*22)
        r = super().step()
        after = self.ram(self.plan_address, self.width*22)
        assert sum(a != b for a, b in zip(before, after)) <= 32
        return r

    def check_grid(self):
        assert not self.call('se_style_begin').p & 1
        self.finish()
        actual = self.ram(self.plan_address, self.width*22)
        wanted = grid_oracle(self.data, self.rows, self.width, self.nowrap, self.pan)
        assert actual == wanted, [(i, a, b) for i, (a, b) in enumerate(zip(actual, wanted)) if a != b][:12]
        assert self.reu(len(self.data)) == self.data
        for a, b in self.guard_ranges + self.plan_guards:
            assert self.ram(a, len(b)) == b, hex(a)


def grid_suite(out, baseline, project):
    original = lexical.objects
    original_run = lexical.run
    result = {}
    def objects(tag, sources):
        objs = []
        for name, flag in sources:
            obj = lexical.OUT / (tag+'-'+name.replace('/', '-')+'.o')
            args = ['ca65', '-g', '-I', lexical.OUT, '-I', lexical.ROOT/'src', '-o', obj]
            if flag:
                args += ['-D', flag+'=1']
            if name in ('style/state', 'style/plan', 'style/lexical-control'):
                args += ['-D', 'SE_STYLE_GRID=1']
            lexical.run(args + [lexical.ROOT/'src'/f'{name}.s'])
            objs.append(obj)
        return objs
    lexical.objects = objects
    def run(args, **kw):
        if args[0] == 'ld65':
            cfg = Path(args[args.index('-C')+1])
            if cfg.name in ('c14.cfg', 'c15.cfg'):
                text = cfg.read_text()
                at = text.rfind('}')
                cfg.write_text(text[:at] + ' RODATA:load=C,type=ro,optional=yes; ' + text[at:])
        return original_run(args, **kw)
    lexical.run = run
    try:
        for tag, path in [('baseline', baseline), ('candidate', project)]:
            lexical.ROOT, lexical.OUT = path, out/tag/'grid'
            rs, s, images, sizes = lexical.build()
            f = GridFixture(rs, s, images)
            cases = []
            try:
                texts = ['# Header\nplain *emphasis* **strong** ***both*** @@code@@\n'*3,
                         ':::basic\n10PRINT"CASE":GOTO10\n20REM DATA PRINT\n:::\n:::asm\nlabel: lda #$ff ; comment\n:::\n',
                         '\n'*24, 'x'*80+'\n# After\n**outer *inner* outer**\n']
                for width in (40, 60, 80):
                    for nowrap, pan in [(0, 0), (1, 0), (1, 7), (1, 1000), (1, 0xFFFFF0)]:
                        for i, text in enumerate(texts):
                            data = base.petscii(text)
                            start, steps = f.instructions, f.steps
                            f.seed_grid(data, width, nowrap, pan, chunk=7 if i & 1 else 128)
                            f.check_grid()
                            cases.append({'width': width, 'nowrap': nowrap, 'pan': pan, 'fixture': i,
                                          'instructions': f.instructions-start, 'steps': f.steps-steps})
                long = base.petscii('# Prefix\n*'+'a'*66000+'* end\n# Next\n')
                f.seed_grid(long, 80, 1, 65520, top=9)
                f.check_grid()
                result[tag] = {'cases': cases, 'cases_total': len(cases)+1, 'sizes': sizes,
                               'instructions_total': f.instructions, 'steps': f.steps}
            finally:
                f.close()
        for a, b in zip(result['baseline']['cases'], result['candidate']['cases']):
            assert (a['width'], a['nowrap'], a['pan'], a['fixture']) == (b['width'], b['nowrap'], b['pan'], b['fixture'])
    finally:
        lexical.objects, lexical.ROOT = original, ROOT
        lexical.run = original_run
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    args = p.parse_args()
    out = ROOT / 'build/style-span-candidate' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    with zipfile.ZipFile(args.fixture / 'product-sources.zip') as z:
        baseline_plan = z.read('src/style/plan.s')
        # The probe deliberately changes only the projection. Other planner,
        # parser and lease ABI inputs must still match the supplied baseline.
        for name in ['src/style/api.inc', 'src/style/state.s', 'src/style/lexical-control.s',
                     'src/supermark/block.s', 'src/supermark/inline.s', 'src/supermark/lexer.s']:
            assert z.read(name) == (ROOT / name).read_bytes(), name
    baseline = source_tree(out, baseline_plan, False)
    project = source_tree(out, baseline_plan, True)
    size = production(out, project, args.fixture.resolve())
    suites = old_suites(out, baseline, project)
    grids = grid_suite(out, baseline, project)
    result = {'status': 'passed-isolated-original-suites', 'production_bytes': size,
              'baseline_production_bytes': 3923, 'added_state_bytes': 0, 'added_ZP': 0,
              'suites': suites, 'grids': grids, 'scope': 'Actual planner/lexer code and independent oracles. Production binding/link budget only; public editor/native not yet qualified.'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS', out, 'production bytes', size, flush=True)


if __name__ == '__main__':
    main()

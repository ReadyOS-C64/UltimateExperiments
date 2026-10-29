"""Private C33op3 preparation through actual loader; resident route not installed."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, importlib.util, json, re, subprocess
import test_geos_heading_body_candidate as heading
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'src/render/grid/reveal-candidate'

def run(out, base):
    spec = importlib.util.spec_from_file_location('reveal_builder', D / 'build.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    image, _, budget = b.build(out / 'leaf', base)
    geos = heading.geos
    frozen, identity = geos.freeze(out, base)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    f = heading.Fixture(out, frozen, dll, True)
    f.assets['grid'] = image
    cases = []
    try:
        f.source(geos.native_text('One line.\rAnother line.'))
        f.position(5)
        for mode in range(4):
            f.put('se_mode', mode, 1)
            f.put('se_e_target', 0x123456)
            f.put('se_e_command', 0x9a, 1)
            before = f.canonical()
            reu = f.reu()
            f.m.write(f.s['se_overlay_frame'], 3)
            r, instructions = f.fast_call(f.s['se_overlay_call'], a=33, x=1)
            assert not r.p & 1 and r.a == int(mode == 3)
            assert f.get('se_e_target') == f.get('se_hot_caret') == 5
            assert f.get('se_e_command', 1) == 47
            assert f.canonical() == before and f.reu() == reu
            assert not f.get('se_f_owner', 1) and f.read(0xc600, 1024) == f.shim
            cases.append(dict(mode=mode, result=r.a, instructions=instructions))
        for owner in [1, 2, 3, 4, 255]:
            f.put('se_f_owner', owner, 1)
            before = f.canonical()
            target = f.get('se_e_target')
            command = f.get('se_e_command', 1)
            reu = f.reu()
            f.m.write(f.s['se_overlay_frame'], 3)
            r, _ = f.fast_call(f.s['se_overlay_call'], a=33, x=1)
            assert r.p & 1 and r.a == 0xb2
            assert f.get('se_f_owner', 1) == owner
            assert f.get('se_e_target') == target and f.get('se_e_command', 1) == command
            assert f.canonical() == before and f.reu() == reu
        sizes = {}
        for tag, source in [('control', ROOT/'src/editor/commands.s'), ('candidate', D/'commands.s')]:
            obj = out / (tag+'.o')
            subprocess.run(['ca65','-g','-I',ROOT/'src','-I',ROOT/'build','-o',obj,source],check=True)
            text = subprocess.check_output(['od65','--dump-segments',obj],text=True)
            sizes[tag] = {n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)}
        assert sizes['control'] == sizes['candidate'], sizes
        result = dict(status='passed', cases=cases, foreign_owners=5, whole_REU_guard_bytes=16777216,
                      budget=budget, resident_segment_sizes=sizes, scope=__doc__)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('PASS',result,flush=True)
    finally:
        f.close()

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/grid-reveal-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN',out,flush=True);run(out,a.fixture.resolve())

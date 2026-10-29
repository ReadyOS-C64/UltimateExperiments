"""Actual selector differential: released worker, compact generic, owner profile.

Builds only private outputs. The unsafe-to-call-direct selector profile is
entered exclusively through the unchanged owner-checking opcode dispatcher.
The existing full semantic matrix/oracles are reused without modifying them.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'tools')]
import test_cache_semantic as original

RELEASE = ROOT / 'build/cache-semantic/20261025T230506994396Z/release.json'
FILES = ['api.inc', 'state.s', 'entry.s', 'worker.s']


def run(out, fixture, release, smoke=False):
    manifest = json.loads(release.read_text())
    archive = Path(manifest['source_archive'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['source_archive_sha256']
    baseline = {}
    with zipfile.ZipFile(archive) as z:
        for name in FILES:
            path = 'src/cache/semantic/' + name
            baseline[name] = z.read(path)
            assert hashlib.sha256(baseline[name]).hexdigest() == manifest['source_sha256'][path]
    # This proof holds entry/state/API fixed; future auto-pump dispatch is a
    # separate parent-owned integration, not silently included in this test.
    for name in FILES[:-1]:
        assert (ROOT / 'src/cache/semantic' / name).read_bytes() == baseline[name], name
    current = (ROOT / 'src/cache/semantic/worker.s').read_bytes()
    saved = original.D, original.command, original.Fixture
    results = []
    transcripts = []
    try:
        for tag, worker, selector in [('baseline', baseline['worker.s'], False),
                                      ('generic', current, False),
                                      ('selector', current, True)]:
            variant = out / tag
            variant.mkdir()
            source = variant / 'source'
            source.mkdir()
            for name in FILES:
                (source / name).write_bytes(worker if name == 'worker.s' else baseline[name])
            original.D = source
            raw_command = saved[1]

            def command(args):
                args = list(args)
                if selector and args[0] == 'ca65' and Path(args[-1]) == source / 'worker.s':
                    args[1:1] = ['-D', 'BSC_SELECTOR_OWNS_OWNER=1']
                return raw_command(args)

            original.command = command
            transcript = []
            direct_checks = []

            class Observed(saved[2]):
                def cc(self, name):
                    result, instructions = super().cc(name)
                    if not selector and self.get('se_f_owner', 1) != 4:
                        # Generic exports retain their independent owner guard.
                        # The selector-only profile is NEVER entered this way.
                        ram, reu = self.read(0, 65536), self.reu()
                        direct, _ = self.fast_call(self.c[name])
                        now = self.read(0, 65536)
                        assert direct.a == 0xb2 and direct.p & 1
                        assert now[:0x100] == ram[:0x100] and now[0x200:] == ram[0x200:]
                        assert self.reu() == reu
                        direct_checks.append((name, self.get('se_f_owner', 1)))
                    # No register-value identity is promised beyond A/C.
                    # Hash every actual caller-owned frame byte after every
                    # opcode invocation, including held output and all faults.
                    transcript.append((name, result.a, result.p & 1,
                        hashlib.sha256(self.read(original.F, 576)).hexdigest(),
                        self.get('se_doc_read_locks', 1), self.get('se_f_owner', 1)))
                    return result, instructions

            original.Fixture = Observed
            print('VARIANT', tag, flush=True)
            result = original.run(variant, fixture, smoke)
            if tag == 'baseline':
                assert result['budget']['total_bytes'] == 4082
                assert result['budget']['sha256'] == manifest['raw_sha256']
            if selector:
                assert result['budget']['total_bytes'] <= 3996, result['budget']
            (variant / 'transcript.json').write_text(json.dumps(transcript) + '\n')
            if transcripts:
                assert transcript == transcripts[0], next(
                    ((i, a, b) for i, (a, b) in enumerate(zip(transcripts[0], transcript)) if a != b),
                    ('callcount', len(transcripts[0]), len(transcript)))
            transcripts.append(transcript)
            results.append(dict(profile=tag, bytes=result['budget']['total_bytes'],
                sha256=result['budget']['sha256'], cases=len(result['cases']),
                faults=len(result['fault_groups']), calls=len(transcript),
                instructions=sum(c['instructions'] for c in result['cases']),
                direct_generic_owner_checks=len(direct_checks),
                frame_transcript_sha256=hashlib.sha256(json.dumps(transcript).encode()).hexdigest()))
        summary = dict(status='passed', variants=results,
            spare_bytes=4096-results[-1]['bytes'],
            scope='Unchanged actual opcode selector; all frame outputs/A/C/counts/lease/owner '
                  'identical to released4082 worker, original wholeRAM/16MiB/source/capability '
                  'oracles retained. No auto-pump/editor/arena-writer integration or native claim.')
        (out / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
        print('RESULT', json.dumps(summary), flush=True)
        return summary
    finally:
        original.D, original.command, original.Fixture = saved


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, default=original.BASE)
    p.add_argument('--release', type=Path, default=RELEASE)
    p.add_argument('--smoke', action='store_true')
    a = p.parse_args()
    out = ROOT / 'build/cache-semantic-selector' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, a.fixture.resolve(), a.release.resolve(), a.smoke)

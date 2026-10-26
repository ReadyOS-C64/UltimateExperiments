"""Current typed-cache transport adapter for the legacy visual regressions.

All legacy source, independent pixel/attribute, row-map, fold and history
assertions remain intact. Only their obsolete FE-only REU allowance is replaced
with the released checked-DMA observer plus an authenticated first type53
allocation and immutable subsequent arena snapshots. No product substitutions.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, inspect, json, shutil, zipfile
import test_geos_semantic_editor as semantic
import test_geos_fold_editor as fold
import test_presentation_bypass as bypass
from test_lifecycle_cache_current import cache_frame

ROOT = semantic.ROOT


class CurrentAudit:
    def reu(self):
        buf = C.create_string_buffer(16 * 1024 * 1024)
        self.dll.gm_reu(self.m.handle, len(buf), buf)
        return buf.raw

    def arena(self, memory=None, reu=None):
        memory = self.read(0, 65536) if memory is None else memory
        reu = self.reu() if reu is None else reu
        s = self.s
        token = memory[s['se_bc_arena']:s['se_bc_arena'] + 5]
        ids = [i for i in range(8) if memory[s['object_owner'] + i] == 0x53]
        if token == bytes(5):
            assert not ids and not any(memory[s['se_reu_physical_owner'] + b] == 0x53 for b in range(256))
            return None
        ident = token[0]
        assert ident < 8 and ids == [ident]
        assert token[1:3] == bytes((memory[s['object_gen_lo'] + ident], memory[s['object_gen_hi'] + ident]))
        epoch = memory[s['se_object_epoch']:s['se_object_epoch'] + 2]
        assert token[3:5] == epoch == memory[s['se_reu_epoch']:s['se_reu_epoch'] + 2] and epoch != bytes(2)
        banks = memory[s['object_banks'] + ident]
        assert 1 <= banks <= 16
        logical = list(memory[s['object_extents'] + ident * 16:s['object_extents'] + ident * 16 + banks])
        physical = [memory[s['se_reu_map'] + b] for b in logical]
        assert len(set(logical)) == len(set(physical)) == banks and all(logical) and all(physical)
        assert all(memory[s['se_reu_logical_owner'] + b] == 0x53 for b in logical)
        assert all(memory[s['se_reu_physical_owner'] + b] == 0x53 for b in physical)
        assert sorted(physical) == [b for b in range(256) if memory[s['se_reu_physical_owner'] + b] == 0x53]
        proof, payload = cache_frame(s, memory, reu, self.audit_out)
        assert proof['bytes'] == banks * 65536
        return proof, payload, physical

    def audit_begin(self):
        self.audit_before = self.reu()
        self.audit_arena_before = self.arena(reu=self.audit_before)
        self.audit_baseline = (self.audit_arena_before is None and self.get('se_render_caps', 1) != 0
                               and self.get('se_mode', 1) == 3 and self.get('se_bc_flags', 1) & 31 == 2)
        self.dll.pb_arena_begin(self.audit_baseline)
        names = ('se_reu_copy', 'se_reu_logical', 'se_reu_offset', 'se_reu_length',
                 'se_reu_map', 'se_reu_logical_owner', 'se_reu_physical_owner')
        self.dll.fr_begin(*(self.s[n] for n in names))

    def audit_end(self, before, tag):
        assert before == self.audit_before, (tag, 'audit snapshot mismatch')
        writes = fold.retention.Fixture.audit_end(self, before, tag)
        current = self.arena()
        arena_writes = int(self.dll.pb_arena_get())
        if self.audit_arena_before is not None:
            assert current == self.audit_arena_before, (tag, 'existing complete type53 arena changed')
            assert arena_writes == 0, (tag, 'write to immutable arena')
        elif current is not None:
            assert self.audit_baseline and arena_writes, (tag, 'unexpected allocation')
            assert self.get('se_bc_flags', 1) & 15 == 1 and self.get('se_bc_count', 1) == 0
            assert current[0]['merged_length'] == len(self.merged()) and current[0]['records'] > 0
            # Every newly changed arena byte is independently covered by the
            # exact observer mask from an actual checked owner53 DMA request.
            mask = C.create_string_buffer(len(before)); self.dll.fr_mask(mask)
            after = self.reu()
            for bank in current[2]:
                lo = bank * 65536; hi = lo + 65536
                assert all(a == b or m for a, b, m in zip(before[lo:hi], after[lo:hi], mask.raw[lo:hi]))
        else:
            assert arena_writes == 0
        self.audit_records.append(dict(tag=tag,checked_dma_writes=writes,typed53_writes=arena_writes,
                                       first_allocation=self.audit_arena_before is None and current is not None,
                                       arena=None if current is None else current[0]))
        (self.audit_out/'dma-audits.json').write_text(json.dumps(self.audit_records,indent=2)+'\n')
        return writes


def run(out, fixture, suite):
    out.mkdir(parents=True)
    with zipfile.ZipFile(out/'current-verifiers.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in (Path(__file__), Path(semantic.__file__), Path(fold.__file__), Path(bypass.__file__),
                     ROOT/'tests/test_fold_retention.py', ROOT/'tests/test_lifecycle_cache_current.py'):
            z.write(path,path.relative_to(ROOT))
    # The existing raw captured-state root validator also constructs the
    # native font view from these exact sealed leaves; no execution uses them.
    for name in ('grid80', 'grid60'):
        shutil.copy2(fixture/'build/overlays'/(name+'.seo'), out/(name+'.seo'))
    records = []
    parent = semantic.geos.Fixture if suite == 'inline' else fold.Fixture
    class Fixture(CurrentAudit, parent):
        audit_out = out
        audit_records = records
    runner = bypass.runner
    if suite == 'inline':
        source = inspect.getsource(semantic.run)
        needle = '        f.render()\n'
        assert source.count(needle) == 1
        source = source.replace(needle, '        f.audit_begin()\n' + needle)
        start = source.index('        after=f.reu();start=bank*65536;cursor=0\n')
        end = source.index('        assert f.read(0xC600', start)
        source = source[:start] + '        f.audit_end(reu,tag)\n' + source[end:]
        assert source.count('dll=geos.grid.runner(out)') == 1
        source = source.replace('dll=geos.grid.runner(out)', 'dll=current_runner(out)')
        saved_fixture = semantic.geos.Fixture
        semantic.geos.Fixture = Fixture
        ns = dict(semantic.__dict__, current_runner=runner)
        try:
            (out/'executed-adapter.py').write_text(source)
            exec(compile(source, str(Path(__file__)) + ':inline-current-DMA', 'exec'), ns)
            result = ns['run'](out, fixture, inline_case=True)
        finally:
            semantic.geos.Fixture = saved_fixture
    else:
        source = inspect.getsource(fold.run)
        needle = 'dll=retention.runner(out);f=Fixture'
        assert source.count(needle) == 1
        source = source.replace(needle, 'dll=current_runner(out);f=Fixture')
        ns = dict(fold.__dict__, Fixture=Fixture, current_runner=runner)
        (out/'executed-adapter.py').write_text(source)
        exec(compile(source, str(Path(__file__)) + ':fold-current-DMA', 'exec'), ns)
        result = ns['run'](out, fixture)
    (out/'executed-adapter.py').write_text(source)
    result['current_transport_adapter'] = dict(
        scope=__doc__, audits=records, frames=len(result['frames']),
        legacy_assertions='Unchanged except obsolete REU ownership allowance; no output normalization or product replacement.',
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--suite',choices=('inline','fold'),required=True); a=p.parse_args()
    out=ROOT/'build/cache-visual-regressions'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite)
    print('RUN',out,flush=True)
    r=run(out,a.fixture.resolve(),a.suite)
    print('PASS',a.suite,'frames',len(r['frames']),flush=True)

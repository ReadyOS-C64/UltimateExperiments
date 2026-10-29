"""Private C35→C37/3→C35 continuation for committed source geometry changes.

The real current R14 lease remains exact after admission. No pending edit,
observer-ticket rebase, renderer/root routing or native integration is claimed.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, sys
import test_cache_query_forward as forward
import test_cache_query as query
import test_cache_classify as classify

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT/'src/cache/query/probes/committed'
original_command = query.command


def command(*args):
    args = list(args)
    if str(args[0]) == 'ca65' and 'BCQ_CLASSIFY=1' in args:
        path = Path(args[-1])
        if path.name in ('query.s', 'fast-entry.s'):
            args[-1] = PRIVATE/path.name
        args[1:1] = ['-D', 'BCQ_COMMITTED_IDENTITY=1']
    return original_command(*args)


EXTRA = '''
   extra=[]
   # Reopen C35 after actual public window loading, not an old C37 proof.
   data=baseline(sem.geos.native_text('Body **bold**\\rTail.'))
   f.put('se_f_owner',0,1);f.position(1);f.put('se_f_owner',4,1)
   f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
   stable_content=f.read(0,65536);content_reu=f.reu()
   r,got,hint,steps=classify(1)
   assert r.a==0 and got==expected(data,1)[0] and hint==expected(data,1)[1]
   assert f.read(G+29,59)==f.read(s['se_fs_identity'],59)
   assert not f.get('se_doc_read_locks',1)
   extra.append('C35actualW_LOAD committedidentity admitted current59 published')
   # Every canonical source-prefix byte is essential, even with valid geometry.
   for offset in range(29):
    f.m.load(0,stable_content)
    f.m.load(G,bytes(192));f.m.load(G,(1).to_bytes(3,'little'))
    r=invoke(35,1,0)
    for _ in range(200):
     if f.m.read(0x9135)==37 and f.m.read(0x9136)==3:break
     r=invoke(35,1,1)
     assert not r.p&1 and r.a==1
    else:raise AssertionError('no committed continuation')
    before_output=f.read(G+5,16)
    f.m.write(F+32+offset,f.m.read(F+32+offset)^1)
    r=invoke(37,1,3)
    assert not r.p&1 and r.a==2 and f.read(G+5,16)==before_output
    assert not f.get('se_doc_read_locks',1) and not f.m.read(G+21)
   extra.append('all29canonicalprefixfaults reject beforepublication and release ownlease')
   # A pending baseline cannot masquerade as a committed-only representation.
   data=baseline(sem.geos.native_text('Body **bold**\\rTail.'),True)
   f.put('se_f_owner',0,1);f.command(2);f.put('se_f_owner',4,1)
   f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
   r,got,hint,steps=classify(1)
   assert r.a==2 and not f.get('se_doc_read_locks',1)
   extra.append('pendingbaseline geometry mismatch stays optionalMISS2')
   data=baseline(b'A'*66000+sem.geos.native_text('\\r# Far\\rTail.'))
   f.put('se_f_owner',0,1);f.position(65999);f.put('se_f_owner',4,1)
   f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
   mark=len(routes);r,got,hint,steps=classify(65999)
   assert r.a==0 and got==expected(data,65999)[0]
   assert [37,3] in routes[mark:] and [35,1] in routes[mark:]
   assert f.read(G+29,59)==f.read(s['se_fs_identity'],59)
   cases.append({'tag':'actualW_LOADover64KiB','queries':1,'source_bytes':len(data)})
   extra.append('actual>64KiBwindowload retains classifications via35→37/3→35')
   data=baseline(sem.geos.native_text('Body **bold**\\rTail.'))
   f.put('se_f_owner',0,1);f.position(1);f.put('se_f_owner',4,1)
   f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1)
   f.m.load(G,bytes(192));f.m.load(G,(1).to_bytes(3,'little'))
   r=invoke(35,1,0)
   for _ in range(200):
    if f.m.read(0x9135)==37 and f.m.read(0x9136)==3:break
    r=invoke(35,1,1);assert not r.p&1 and r.a==1
   else:raise AssertionError('no committed continuation for faults')
   live=f.read(0,65536);live_reu=f.reu();old=f.read(G+5,16)
   for owner in (0,1,2,3,5,255):
    f.m.load(0,live);f.put('se_f_owner',owner,1)
    before=f.read(F,576)+f.read(G,192);r=invoke(37,1,3)
    assert r.p&1 and r.a==0xb2 and before==f.read(F,576)+f.read(G,192)
    assert f.get('se_doc_read_locks',1)==1
   extra.append('op3sixforeignowners opaque liveownedlease retained')
   for field in ('se_bc_count','se_r_revision','se_bc_ticket','se_bc_incarnation'):
    f.m.load(0,live);f.put(field,f.get(field,1)^1,1)
    r=invoke(37,1,3)
    assert r.p&1 and f.read(G+5,16)==old and not f.get('se_doc_read_locks',1)
    assert not f.m.read(G+21) and not f.m.read(seam['se_bc_flags'])&8
   extra.append('op3queue/source/ticket/incarnation changes error and closeownlease')
   f.m.load(0,live);r=invoke(35,1,2)
   assert not r.p&1 and r.a==0 and not f.get('se_doc_read_locks',1)
   assert not f.m.read(G+21) and not f.m.read(seam['se_bc_flags'])&8
   assert f.reu()==live_reu
   extra.append('C35CANCEL atcrosscapsuleboundary releasesexactownlease')
   assert f.read(0xc600,1024)==f.shim
   faults.extend(extra)
'''


def run(out, base):
    # Rebuild only the standalone baseline/writer qualification in this output.
    # All loaded resident code and packaged assets come from the frozen product.
    prep = out/'baseline'
    prep.mkdir()
    # Component transport seam: omit only the four packaged cache workers
    # that this test imports through the real checked loader. Keep resident,
    # provider, reader and every other asset exact. No catalog bytes are poked.
    parent = classify.sem.Fixture
    class Fixture(parent):
        def source(self, *args, **kwargs):
            assets = self.assets
            self.assets = {n: v for n, v in assets.items()
                           if n not in ('fold', 'sema', 'inln', 'page')}
            try:
                return super().source(*args, **kwargs)
            finally:
                self.assets = assets
    classify.sem.Fixture = Fixture
    arena_source = Path(query.arena.__file__).read_text()
    old = "index=len(identity['names'])"
    assert arena_source.count(old) == 1
    arena_source = arena_source.replace(old, old+'-4')
    (out/'generated-arena.py').write_text(arena_source)
    arena_ns = {'__file__': query.arena.__file__, '__name__': 'committed_arena'}
    exec(compile(arena_source, str(out/'generated-arena.py'), 'exec'), arena_ns)
    arena_ns['run_writer'](prep, base)
    classify.BASE = prep/'fixture'
    classify.PIPE = prep
    # The historical verifier pins hashes from an older resident binding.
    # Recompute both unmodified canonical profiles for this exact fixture.
    expected = []
    for active in (False, True):
        image, _, _ = query.build(out/('canonical-active' if active else 'canonical'),
                                  classify.BASE, active)
        expected.append(hashlib.sha256(image[36:]).hexdigest())
    query.command = forward.command = command
    source = (ROOT/'tests/test_cache_query_forward.py').read_text()
    hashes = ('9233b2e7b77ec4a04b17f4c6c4e4dcf32c8197c31d6dc0f9bc56b59a8f61d0c0',
              '38621b45225378a3e5dab7e1c6ce7b0894dbdb0080cbce1e700b3d826319c920')
    suffix = ''.join(f'.replace({old!r},{new!r})' for old, new in zip(hashes, expected))
    source = source.replace('.read_text()', '.read_text()'+suffix)
    needle = " (out/'generated-verifier.py').write_text(text)"
    addition = '''
 text=text.replace("assert r.a==2 and not f.get('se_doc_read_locks',1) and f.read(seam['se_bc_arena'],5)==oldtoken", "assert r.a==0 and not f.get('se_doc_read_locks',1) and f.read(seam['se_bc_arena'],5)==oldtoken")
 text=text.replace("r,got,hint,steps=classify(1);assert r.a==0 and", "f.put('se_bc_flags',f.m.read(seam['se_bc_flags'])&~32,1);r,got,hint,steps=classify(1);assert r.a==0 and")
 text=text.replace("'actualpublicW_LOADgeometryinapplicableMISS'", "'actualpublicW_LOADcommittedidentity'" )
 text=text.replace("phase=f.read(F,576);semantic=f.read(G,192)", "phase=f.read(F,576);semantic_snapshot=f.read(G,192)")
 text=text.replace("f.read(G,192)==semantic\\n", "f.read(G,192)==semantic_snapshot\\n")
 text=text.replace("seed_begins=0", "seed_begins=0;routes=[]",1)
 text=text.replace("  if ident==35 and op==0:", "  routes.append([ident,op])\\n  if ident==35 and op==0:",1)
 text=text.replace("  result={'status':'PASS'", COMMITTED_EXTRA+"  result={'status':'PASS'")
'''
    assert source.count(needle) == 1
    source = source.replace(needle, addition+needle)
    (out/'generated-forward.py').write_text(source)
    ns = {'__file__': str(ROOT/'tests/test_cache_query_forward.py'),
          '__name__': 'private_committed', 'COMMITTED_EXTRA': EXTRA}
    exec(compile(source, str(out/'generated-forward.py'), 'exec'), ns)
    ns['command'] = command
    variant = out/'candidate'
    variant.mkdir()
    result = ns['variant'](variant, True)
    result['scope'] = __doc__
    result['private_sources'] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in PRIVATE.glob('*.s')}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('COMMITTED PASS', result['private_sources'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    out = ROOT/'build/cache-committed-identity'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    try:
        run(out, args.fixture.resolve())
    except Exception:
        # Subprocess diagnostics from ca65/ld65 are otherwise hidden by helper.
        import traceback
        traceback.print_exc()
        error = sys.exc_info()[1]
        if getattr(error, 'stderr', None):
            print(error.stderr, flush=True)
        raise

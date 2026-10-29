# Content-aware cache jobs and owned D81 freshness candidate

Private proof only. No canonical source, shared build, Git or hardware changes.
`ensure.py` is ready to copy unchanged to the clearer production name
`tools/cache_job_build.py`; its project/base/output roots are explicit CLI inputs.
The program does not use its own directory to find application sources.

## Proposed production Make changes

Keep every original resident/source/probe/font/asset prerequisite. Add these phony
force prerequisites so the cheap content check executes even if Make3.81 sees all
integer timestamps as equal. Replace the **existing** recipes, rather than adding
a second recipe for the same D81 target:

```make
.PHONY: cache-jobs-force cache-package-force
cache-jobs-force:
cache-package-force:

build/cache-editor/jobs.stamp: cache-jobs-force build/editor.prg build/editor.lbl build/editor-report.json $(CACHE_JOB_INPUTS) tools/cache_job_build.py
	$(PYTHON) tools/cache_job_build.py --project "$(CURDIR)" --base "$(CURDIR)" --out build/cache-editor --publish build/overlays

build/overlays/fold.seo build/overlays/sema.seo build/overlays/inln.seo build/overlays/page.seo build/overlays/line.seo: build/cache-editor/jobs.stamp
	cmp -s build/cache-editor/$(@F) $@ || cp build/cache-editor/$(@F) $@

# Add this prerequisite to all the existing D81 prerequisites. Replace the
# original `tools/package.py` recipe with the following combined guard.
build/supereditor.d81: cache-package-force
	$(PYTHON) tools/cache_job_build.py --project "$(CURDIR)" --base "$(CURDIR)" --out build/cache-editor --publish build/overlays --package --c1541 "$(C1541)"
```

Remove the old unconditional `touch jobs.stamp`. The helper manages its content
stamp, leaving it untouched on a true no-op. `--publish` repairs all five actual
published files by byte comparison inside the check, so correctness does not
rely on Make noticing a timestamp change. The conditional `cmp/cp` rule also
preserves file mtimes if Make invokes it. The D81 check independently hashes
packaging inputs and its output; it never relies on propagation of a changed
stamp/SEO timestamp. The repeated job check in the D81 recipe is cheap and proves
that packaging cannot use a stale five-image family.

This does not replace upstream resident compilation. The actual PRG/report/labels
must represent the requested build configuration. The proof replays two genuine
sealed54 ABIs A/B/A; B is not claimed to be a Plain preset. It reproduces the same
coarse-clock failure observed during Full/Plain/Full without fabricating a preset.

## Cache input/output identity

Every invocation verifies the normalized complete PRG+link-label binding, report
SHA/digest and each report symbol against the actual link labels. The input key
includes all three actual resident files; conservative direct production source
siblings under cache/{editor,arena,query,semantic,inline}; actual recursive textual
`.include`/`.incbin` closure; the actual SuperMark block/inline sources/API;
module_bindings.py/bindings.py/overlays.py; this guard's bytes; and ca65/ld65/od65
version strings. Current closure is51 files, including `src/cache/api.inc`, which
the original Make wildcard list omitted. Generated editor-api/state data derives
from the verified resident, not from an earlier output cache. Nested private probe
namespaces are not included. Unresolved includes refuse rather than being ignored.

On a dirty/missing/invalid family the actual `src/cache/editor/build.py` assembles
all five capsules in a new temporary directory. No cached code is substituted.
Inputs are rechecked before publication. Each family must pass exact SEO2 type,
slot/ID, resident API, header/payload CRC, length, header/body binding and budget
identity. Manifest hashes cover all five SEO/bin/lbl/map files plus budget and
state/API inputs. Files are replaced only if bytes differ, and the family proof
is published last. Missing/corrupt outputs rebuild; a missing stamp or damaged
published copy repairs without recompiling correct job outputs. Input changes
mid-build preserve the previous family/proof. Concurrent guard invocations fail
on a lock; a crashed stale lock requires explicit review. Ordinary repository
build/freeze operations must remain serialized; this is not a claim of an atomic
cross-file snapshot for uncontrolled concurrent external writers.

## Packaging identity

`--package` validates every editor name from the actual literal `NAMES` declarations
in tools/cpu_editor.py against the current resident seal/API/header and payload
CRC. It also fingerprints the actual packager/dependent host code, reports/labels,
and every input member named by the real disk manifest. If a manifest/proof is
missing or invalid, or any input/output bytes differ, it invokes the unchanged real
tools/package.py and c1541. The resulting disk is independently walked through
D81Image and **every** PRG/SEQ member is compared with its actual source file.
The disk proof is published last and includes the manifest and complete D81 SHA.
The six intentionally malformed probe fixtures are regenerated by the real
packager and compared byte-exact, not silently treated as valid editor capsules.
A c1541/validation failure restores the previous disk and manifest; no new proof
is published. Only this project's owned build D81 is handled.

A no-op invokes no assembler/linker/od65 build operation and no c1541, and rewrites
no product output, copy, stamp, manifest or D81. Transient locks and Python bytecode
caches are not product outputs. Compiler version checks are read-only subprocesses.

## Executable proof

```
python3 tests/test_cache_job_rebuild.py
```

Terminal run `build/cache-job-rebuild/20261026T082259701182Z` passes12 cache cases
and8 packaging cases, plus actual invalid-report, mid-build-change, foreign54 and
c1541-failure refusals. Source/inputs are immutable fixtures:

- A: `build/cache-editor-product/20261026T051042908519Z/fixture`,
  PRG a2578487.../binding f50620a2..., disk774437a337e1... .
- B: `build/cache-editor-product/20261026T035310363807Z/fixture`,
  PRG91de02aa.../binding eaccc1c6..., disk c6706a5aaf8c... .

The test extracts the real packager's input files from immutable D81 bytes. Its
minimal generic probe report contains only four fields decoded from authentic
RONE header bytes, used by package.py for its intentional malformed fixtures.
Every regenerated member and both complete A/B/A D81 hashes equal the immutable
media. Both initial and final five source-built SEO families equal the fixtures
byte-for-byte; all54 editor headers are checked, and all79 disk members are read.

Legacy equal-time rules leave all five SEOs stale in both ABI directions and leave
an actual D81 stale even after its five cache inputs were repaired. The proposed
forced content checks repair both stages despite equal integer timestamps. External
exec wrappers prove zero build-tool calls and zero c1541 calls on no-ops, and exact
all-product mtime snapshots prove zero output rewrites. A separate direct no-op
with normal tool lookup took0.153s; instrumented dirty five-job builds took about
3.1s. These are host wall times, not C64 performance measurements.

No application runtime or emulator/hardware behavior is claimed by this host test.
The independently qualified clipped-caret and mapped INLINE releases stay immutable.

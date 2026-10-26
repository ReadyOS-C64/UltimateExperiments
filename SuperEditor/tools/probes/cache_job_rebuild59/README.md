# Private content guard extension for the registered59 cohort

This is a separate release. The sealed54 guard under `cache_job_rebuild` stays
unchanged. No canonical/shared build, Git, native or hardware operation belongs
to this proof. `ensure.py` can replace the proposed production
`tools/cache_job_build.py` verbatim; explicit project/base roots remain mandatory.

## Exact production integration

Use one forced master transaction for both five-capsule builders. Do not leave
`build/lexical/jobs.stamp` running its independent Python builder or unconditional
touch, because that would bypass the combined transaction and coarse-clock proof.
Keep every existing source/resident/asset/font/probe prerequisite. Replace existing
recipes (do not add conflicting second recipes) using this structure:

```make
.PHONY: cache-jobs-force cache-package-force
cache-jobs-force:
cache-package-force:
CACHE_JOB_GUARD = $(PYTHON) tools/cache_job_build.py --project "$(CURDIR)" --base "$(CURDIR)" --out build/cache-editor --lexical-out build/lexical --publish build/overlays

build/cache-editor/jobs.stamp: cache-jobs-force build/editor.prg build/editor.lbl build/editor-report.json $(CACHE_JOB_INPUTS) $(wildcard src/cache/lexical/*) src/supermark/lexer.s tools/cache_job_build.py
	$(CACHE_JOB_GUARD)

# Retain lexical prerequisites if desired, but replace its builder/touch recipe.
build/lexical/jobs.stamp: build/cache-editor/jobs.stamp
	@test -f $@

build/overlays/fold.seo build/overlays/sema.seo build/overlays/inln.seo build/overlays/page.seo build/overlays/line.seo: build/cache-editor/jobs.stamp
	cmp -s build/cache-editor/$(@F) $@ || cp build/cache-editor/$(@F) $@
build/overlays/edit.seo build/overlays/tail.seo build/overlays/lex.seo build/overlays/ical.seo build/overlays/ctrl.seo: build/cache-editor/jobs.stamp
	cmp -s build/lexical/$(@F) $@ || cp build/lexical/$(@F) $@

# Add the phony prerequisite alongside all original D81 prerequisites; replace
# its old package.py recipe with the following content check.
build/supereditor.d81: cache-package-force
	$(CACHE_JOB_GUARD) --package --c1541 "$(C1541)"
```

Both stamp files contain the combined content signature, and both stay untouched
on a no-op. `--publish` fixes actual file bytes inside the guard; correctness never
relies on Make3.81 seeing changed timestamps. The D81 forced content check remains
necessary even when all ten input capsules have been repaired in the same second.

The lexical output path is explicit. A registered lexical catalog with a missing
`--lexical-out` refuses before building/publishing; it cannot return a five-only
success. Base-only54 usage without the registered names remains available.

## Complete family/type/closure rules

| Family/builder | Output | SEO slot/ID |
|---|---|---|
| src/cache/editor/build.py | build/cache-editor | fold R33; sema C34; inln C35; page C37; line C39 |
| src/cache/lexical/build.py | build/lexical | edit C45; tail R36; lex R37; ical C47; ctrl C49 |

All ten SEO/bin/lbl/map artifacts, both budget/API files and base state.s are
covered by one schema2 manifest in build/cache-editor/content.json. Fresh builds
of both families occur in temporary directories. The manifest and files are not
replaced until **both** builders and identity/CRC checks succeed. The original
base budget still requires its actual resident SHA. The separate lexical budget
schema has binding, slot/id/size/raw SHA but no state.s/resident-SHA field: those
actual fields are checked as emitted; no missing metadata is pretended. The guard's
verified complete resident input identity independently covers both families.

The source closure additionally includes every direct lexical .s/.inc/.py,
SuperMark lexer.s and their real recursive includes. Current closure is64 files,
including the compact C35 arena opener and actual lexical builder/handoff APIs.
Generated source/API state remains derived from the sealed current PRG/labels/
report. All header/body bindings, resident APIs, entry16, slots/IDs, lengths,
header/payload CRCs, budget sizes and available raw hashes are checked. No cached
capsule substitutes for a required fresh dirty source build. Compiler/linker
version strings and guard source bytes remain part of the signature.

The packaging catalog is read from actual NAMES declarations, with no fixed54
cardinality. All59 current editor capsules must authenticate to the actual resident
before packaging. The real package.py/c1541 result is independently read through
D81Image and every one of84 actual member files is byte-compared. Prior disk/manifest
rollback, post-build input checks, lock behavior and exact no-op publication rules
from the sealed54 proposal remain. This does not replace upstream resident builds
or claim atomic snapshots against uncontrolled concurrent external writers.

## Executable proof and exact scope

```
python3 tests/test_cache_job_rebuild59.py
```

Input is the immutable qualified promotion project
`build/cache-lexical-registration/candidate-59b/project`; the verifier copies it
before any operation. It genuinely compiles startup/report defaults Full3→Plain0
→Full3, then performs reference full capsule rebinds. Controlled equal-integer-time
replays put the actual preceding cache output family beside the new real resident.
Legacy stamp rules leave all ten stale; the combined guard recompiles and compares
against the independent actual reference rebuild. No runtime source result,
semantic/cache record, binding or preset is fabricated.

Terminal `build/cache-job-rebuild59/20261026T180918462964Z` passes11 cases:
initial, no-op, both equal-time preset transitions, restored no-op, lexical include
change/restore, missing/corrupt lexical artifact, cheap published lexical repair,
and recovery from an actual second-family builder failure. That failure preserves
both entire old output families, published assets and manifest. Omitted lexical
family is separately refused. Source builders are restored byte-exact.

Full resident93832107be6bca207087516304249b5de8b567143528ddcc132befdba64dd76b,
binding7abb2d3f53543b3dfd5c297c6760a5f6, and all59 original source-built capsule bytes
return exactly after the real Plain build (binding2906a6b86a7001e67d535f54633d8059).
Each dirty family transaction executes60ca65/10ld65/135od65 calls. Each unchanged
check executes zero build operations, copies and c1541 calls and preserves every
product mtime. A comment-only lexical include change rebuilds the source family
but correctly avoids repackaging byte-identical D81 content. Only real packaged
content changes run c1541. Raw artifacts are never adopted from mismatched sources.

This is host build/packaging qualification, not a new app/native/lifecycle claim.
Root's separately promoted C33/C22/source cohort may change input hashes; the
same verified resident/source transaction then rebuilds against that exact input.

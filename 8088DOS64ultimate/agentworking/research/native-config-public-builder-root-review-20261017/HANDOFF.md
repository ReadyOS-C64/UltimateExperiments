# Public-layout CONFIG relocation + all-file diagnostic graph

This is a source-only public-layout integration, not another complete installer,
DOS, physical-device or Turbo acceptance run. Public sources were not edited.
`PUBLIC_COPY_MAP.json` lists exactly 42 proposed source writes with committed
baseline and successor identities. It does not replace Makefile, src/, native
runtime/cold builders, existing DOS images, or any prebuilt model library.

The combined CONFIG code is the sealed 066062 component. The SETUP code is the
sealed 150415 component (312bb8a7 frozen source window). Their native behaviors
and complete UI cases retain those original scopes. This wrapper compiled both
from source and composed their actual products with the already qualified c7
cold eight-assets. The candidate package assembly is not a newly executed
SETUP→DOS run.

## Actual checks

* Combined CONFIG reproduces 5c91bb74 PRG /104a35fd labels, 44,382 bytes;
  its public-layout test path passes 9 actual native groups plus 2 directly
  executed Zig assertions using a freshly compiled Peddle model.
* Relocation-only variant passes 5 actual native groups plus 2 direct Zig.
  It is 6d34dd9c/1feacf3a because the combined component has corrected captions;
  no claim that it reproduces the older 54632dea caption ancestor.
* SETUP reproduces c6adeaee PRG, FAT12c77438 and PUBae37560b from source.
* Default flags preserve CONFIG3deb/50fd and SETUPe710/4d404 PRG/labels;
  SETUP FAT35a3/PUBafae also remain exact. Maps contain real source/debug and
  empty default-OFF object differences; they are deliberately not claimed exact.
* 8 source/profile host controls and 23 actual-asset candidate packaging controls
  pass under before/after source/product closure. Clean default tooling discovery
  collects334, no optional CONFIG tests, no failed imports, no subprocesses.
* Native-only CONFIG succeeds with nonexistent optional Zig/clang settings.
  Native builds require Python, cc65/ca65/ld65 and none.lib; tests add clang/Peddle
  and Zig. No DOS images are part of this source package or required for these
  focused tests. Default config/config-tests paths remain opt-in and unchanged.

`RESULT.json`, `COMPILER_AND_NATIVE_TEST_RECEIPTS.json`, `DEFAULT_COMPARISON.json`
and the immutable run receipts are authoritative. INPUTS_BEFORE/AFTER plus
INPUT_COPIES bind executed source/tools/products. Older preliminary receipts
are retained; do not substitute their live original pointers for final closure.

## Proposed public commands after exact promotion

```
python3 -B build_support/config_generation.py --out build/config-relocation \
  --bundle-result build/cold-start/RESULT.json --start20k --cold-inventory \
  --mnu56k --startup-diagnostics --all-file-diagnostics --relocation
make config-relocation-tests \
  DOS64_CONFIG_ARGS='--out build/config-relocation-tests --bundle-result build/cold-start/RESULT.json --start20k --cold-inventory --mnu56k'
python3 -B build_support/setup_installer.py --out build/setup-all-errors \
  --bundle-result build/cold-start/RESULT.json --start20k --cold-inventory \
  --mnu56k --startup-diagnostics --file-diagnostics --all-file-diagnostics
make v1-candidate DOS64_V1_CANDIDATE_ARGS=--runtime-media
```

The last command is production orchestration supported by the shared existing
runtime/cold source graph. Here the four component invocation flags were
host-tested, and actual existing c7 cold plus newly compiled SETUP/CONFIG were
assembled/validated. The full runtime/cold compiler pipeline was not repeated in
this partial source derivative. Root must regenerate the final matched runtime
cohort after promotion; changing included source inventories can change its tag.
The legacy nine-file candidate branch still omits both new optional profiles.
The runtime-media branch now requires checked SETUP terminal lifetime assertions
and CONFIG all-file+relocation receipts before assembling its twelve files.

## User-facing behavior and limits

Return opens, Delete goes to parent, F1 selects current folder, F3/F5 page,
and left/right scroll long paths. A moved installation needs explicit Y at the
displayed old/current-home prompt; Return does not confirm. Only component-boundary
case-insensitive descendants of the old home are rebased; external paths remain
exact. There is no old-path fallback. Canonical nonroot homes are required; new
launch home is2..117 bytes, media paths<=127. Original CFG/START/INI/media stay
unchanged. Use the generated new START; a moved original START still contains
its saved old home. Shared image files remain shared. File/path/op first errors,
unknown closure and verified permanent fallback retain the component contracts.

SETUP all-file diagnostics are enabled only with existing startup/file flags.
CONFIG relocation and all-file diagnostics are numeric default-OFF. Neither
changes D64C/D64R/START ABI or allocates new REU space. The combined CONFIG map
has MAIN32 bytes free; HIGH8175 endingFFEE; phase code ends8B94 before state8BB0;
state endsAFF2; permanent state endsBFC5 before fallbackBFC8..BFFE. Root's next
CPU trap/runtime cohort and hardware acceptance remain separate.

## Retained first failures / staging corrections

* Initial archive cwd invocation failed before staging; corrected owned cwd.
* Initial default discovery lacked imported font source fixtures; captured its
  single failed import, then staged exact committed font sources. No utility
  tests or device actions ran.
* First candidate host run had one old error-message regex after deliberately
  strengthening the profile rejection. Source policy already refused correctly;
  only the expected host caption was corrected, then23 tests passed.
* Initial staging aliased the app codec onto two unused generic utility copies.
  The incorrect bytes are retained and both generic files restored exactly to
  the committed baseline. No executed native/source ledger consumed those
  extra copies, and neither appears in the42-file promotion map.
* The earlier `closed-default` omits the existing startup diagnostic flag and
  produces7e2cce2b; it is a different explicit profile, not a failed3deb compare.

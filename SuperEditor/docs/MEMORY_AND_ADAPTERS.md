# Memory and standalone adapters

## Current 62-image runtime

The current linked package has62 registered images and four REU code banks.
Its resident is215bd082/bindingc10bc2. The experimental63rd image was retired
from the production build; its exact unqualified sources remain in6a280d8. The ReadyOS reservation is the entire
untouched `$C600–$C9FF` range. Current resource sizes are:

| Resource | Linked bytes |
| --- | ---: |
| Zero page |24|
| BSS |1534|
| COLD |1737, ending `$0ED5` inclusive;42 bytes before `$0F00`|
| C7 menu/control |4001|
| C21 page coordinator |4096|
| R21 polling logical-row rasterizer |4095|
| C22 row painter |4089|
| R22 popup/settings |4086|
| R30 local typing |3662|
| C32 typing stage |3856, raw3824;240 bytes before the stage stamp|
| C41 rebase |4068|
| R34 transform |4095|

The scheduler update5349d45 preserves62 images and reduces resident code one
byte. The R21/C22 replacement removes per-strip row preparation, retains the
same fonts, and adds no resident/REU allocation or registered image. Its combined
payload is34 bytes larger; the polling helper reuses the fixed image tail. All other
60 images are unchanged from the scheduler control. Actual62 CFG analysis still
computes68 relative bytes for foreground plus one IRQ/NMI, subject to the
declared ROM/frame contracts. This is not an exhaustive physical NMI guarantee.

C21 completes source/layout before paint. During C22/R21 paint, these existing
phase loans are exclusive:

| Inclusive range | Paint owner |
| --- | --- |
| `$4400–$47DD` | Complete161-glyph packet, x map and palette |
| `$8880–$8B3F` | Glyph frame and upper-band histogram |
| `$8B40–$8BFF` | C22 state and selection witness |
| `$8D00–$8F2F` | Lower-band histogram; reused only after invalidation for native cells |
| `$9040–$9081` | Row descriptor and continuation in inactive source snapshot |

Both source lease/context flags must be zero before paint; zero flags alone do
not authorize painting while a suspended C20 continuation exists. C21's actual
build-before-paint sequencing supplies that proof. No source prefetch or parser
may run while the row continuation is live. IRQ writes only input state; normal
input cancels source paint before another phase. Every C22 STEP still checks
source/provider/header/selection. R21 validates arrays at packet admission,
then checks its scalar/frame/cursor/stage bounds and reconstructs output
addresses on continuation. Internal IRQ-ring/NMI polls continue within the same
verified invocation when no input waits; they do not introduce another source
trust boundary or allocate state. C20's next BEGIN revokes its old certificates before reusing
the loaned bytes. Native-row transitions revoke row continuation first.

The GEOS edit transaction uses one 842-byte following-row shadow at FE
`$D568–$D8B1`. It is valid only while the foreground C21/R28 transaction is
live. The former backup tail `$D8B2–$E567` is unowned and must remain exact;
font storage still begins at `$E568`. Resume and every transaction exit revoke
the phase/validity fields, so stale shadow bytes never become durable state.

Paged Help retains C7/R22. The retired paint supervisor and shadow overlap stay
outside production. See the [optimization replacement plan](OPTIMIZATION_PLAN.md).
The [capacity and tested limits](CAPACITY.md) distinguish the bounded1MiB source
engine proof, finite quotas, lower-memory configurations and D81 free space.

The following sections preserve earlier checkpoint descriptions. Their scoped
sizes and historical wording do not supersede this current linked map.

The current build registers62 editor overlays in the existing64-entry catalogue
and four checked REU code banks. R29 ROW and C41 PARSE/R34 XFORM reuse existing
filename suffixes. The packed catalog leaves COLD ending`$0ED5`, with42 bytes
before`$0F00`. BSS remains1,534 bytes and zero page24. The entire ReadyOS
reservation`$C600–$C9FF` remains untouched. C7 is3930bytes, C21 is4096, C41 is4068
and R34 is4095. The rebase batch quota borrows BC_FRAME+79; its source reader is
at+173 and live SuperMark state starts at+94. Up to four typed R34 microsteps
share one synchronous source/observer guard, renewed after every yield. Final
journal/root VALID-last publication retains its nonyielding boundary. No resident
warm state, bank, object, BSS or zero page was added. See the
[checked rebase contract](../src/cache/edit-rebase-integration/README.md).

C33 remains4,096 bytes and expands512 bytes of CRC lookup data only during its
checked, non-yielding CAPTURE operation. The expansion borrows `$8D00–$8EFF`,
which aliases retained sparse line-index storage. It clears `se_i_ready`,
`se_i_count` and `se_n_cache_count` before the first write. Owner4 alone is not
proof that cached index data is disposable. Pending redraw/drawbusy refusal
happens before borrowing this area. A native60→80/GOTO regression exposed the
missing invalidation; both directions and source positions above64KiB now pass.
R25 stays4,057 bytes. C22's partially visible caret fix reduces it to4,056.
The combined foreground stack bound remains68 bytes including one IRQ/NMI.

Both five-capsule cache families now share a content-aware build transaction.
Actual resident/source/include/tool identities and all ten outputs are checked;
changed content reaches the real D81 even with second-resolution Make clocks.
A no-op preserves output bytes and mtimes. `make editor disk` runs these checks.
The following paragraphs retain their named earlier checkpoint scopes.

The previous grid update changes only C33/R25/R14 relative to checkpoint69720da.
It adds no resident, BSS, zero-page, allocation or catalogue entry. C33 remains
4,096 bytes, R25 is4,057 and R14 is4,095. NC byte253 stores the exact parsing
preset inside the existing256-byte CRC-covered header. Raw editing preserves
SP2 and semantic descriptors. See [grid qualification](GRID_RAW_EDITING.md) for
native costs, the physical-row correction and remaining capture overhead.

The C19 fold allocator is 1,469 bytes (+99) and reclaims optional
checked type53 analysis only after genuine resource exhaustion, then retries
once. It borrows no fold phase bytes, BSS or zero page. Owner 3, full capability
and extent checks, and no ACTIVE/MUTATING job are required. It preserves cache
TRIED/ticket/incarnation/ring; C12 file retirement remains byte-identical.
Checkpoint `69720da` changes only C19 versus `4c25480`; all 54 assets are present.
All 28 fold and five editor scenarios, the 68-byte stack bound and three
native Copy/Cut/Undo frames pass.

R21 remains 4,094 bytes and uses one transient byte `$8B3B` inside its existing
704-byte glyph frame for the precomputed vertical intersection. Font addresses
`$ABF3`/`$AEDB` and compositor tail address `$AF5B` stay fixed; font bytes are
identical. Tail jump operands may relocate with code, so a fixed tail address
is not a claim that all tail bytes are unchanged. No new allocation is added.

The current 54-asset build packs each startup filename into a low address byte
and one byte containing its high address nibble and length. Assembly/link checks
require names below `$1000`, lengths1–15 and at most64 entries. The original raw
DOS names, order, aliases and 325-byte tutorial stay byte-identical.

This recovers47 cold bytes: COLD ends at `$0EC5`, leaving58 bytes before the
REU-probe save area at `$0F00`. BSS remains1,534 bytes and zero page24; the
entire `$C600–$C9FF` reservation remains untouched. Warm addresses stay fixed;
warm code changes only the initial JSR operand for the relocated cold REU
probe and its ABI seal. This is available headroom, not registration of the
private lexical/edit-cache modules. The catalog still contains54 assets.

The emitted-table audit checks every filename against the frozen three-table
build and the exact file in the new D81. Fresh native startup imports all54,
all11 presentation images remain identical, navigation56 and stack68 pass,
and controlled same-process lifecycle6 restores48,152 bytes and reopens422.
No new allocation or bank is introduced.

Historical parsing-preset update: one session capability byte is linked into ordinary
BSS, which ends at `$C5FD` (1,534 bytes; two spare). Code/constants end `$3EFD`
and cold startup ends `$0EFC`; `$C600–$C9FF` remains untouched. The SES64 font
table is unchanged. Plain exposes expanded source through `se_ef_visible`
without discarding the stored fold map. The internal raw context kind9 is a
layout input, never a claimed SuperMark parser result. Preview metadata's
previously reserved byte3 now carries the preset and is covered by its CRC.

The following checkpoint notes describe the preceding Full-render baseline.
D81dbc4ecf968ab, resident2d87e75e,
bindingbc032951a4ff040b1cd687f8eb175884. Core/RODATA3EF9 (6bytes free),
cold0EFE (1free), BSS1533/ZP24,48assets/threebanks, C600..C9FF untouched.
C144089/R144095/C334096/R254095/C204096/C213741/R194028/R283749.
No new resident/BSS/ZP storage, overlay asset, REU object or bank was added.

R19op7 publishes actual C24 outgoing carry in precisely22x64B of existing FE
row padding [0700+i0800,0740+i0800). R28 authenticates sourcekey/CRC/TOP/NEXT
and all six carry bytes before suffix reuse; page and record validity publish
last. Live ABI3 row contents, parser checkpoints, SP2 and font caches retain
separate extents. R14op7 requires owner4 before its strict shift frame; owner2
producer uses latch89C3, C14-only dispatcher leaves C15 unchanged. Production
builds regenerate the actual linked C24/C14/R14/R25/native witnesses.

SP2 uses exactly128 FEbytes1600..167F, previously unused, for actual C14
logical-paragraph authority. Owner2 producer and owner4 C33 consumer are mode-
bound and CRC/source/epoch/anchor checked. C33 authenticates actual linked
C14/R14/R25 sizes/CRCs and managed publisher/font verification. Code lives in
src/render/grid/paragraph; generated witnesses come from current linked images,
not historical probe outputs. Source READ0..2 is retained; optional3..5 provide
paragraph BEGIN/EVENT/FINISH. C33 retains revealop3, caret/typing and planner.

C20 style/role certificate owns4400..458B and its bounded window adds6bytes
458C..4591. Remaining84-byte ledger suffix,525-byte continuation and13-byte tail
stay reserved/guarded. R21 uses two more ephemeral bytes inside its existing704B
caller frame, no frame growth; fontABF3/widthAEDB/tailAF5B remain fixed. Its new
indirect shift table is byte-checked only in the R21 stack graph.

Incoming parser records remain FE0600/0640. AUXop6 refreshes actual published
keys under complete old/new-source and nonwrapping16-bit sequence guards;
C21 preserves an unobserved predecessor until a valid refresh or checked miss.
The resident route consumes22B; four fixed copies save28B, leaving6 free.
Actual48/sevenhelper stack77/minSPB2 and forced66-output rebuild pass. Final
combined lifecycle/media/pressure qualification remains pending. No ReadyOS
application or UltimateDOS integration is claimed.

Earlier exact-build details follow with their original scopes.

Current qualified hardening build: D81 `6f975a6d74b4`, residentb33cc41e,
48assets/three assetbanks, BSS1533/ZP24/core3EFF/cold0EFE. ReservedC600..C9FF
unchanged. C33/R25=4096/3586, R21=4094, C21=3597, C22=4070,
C25=4049,C26=3327,R28=4095. No new allocation/state/bank. C26operation4
accepts exactly161 with split finalrole at8FEB and hiddenbit160 at8FEA;
legacyoperations0/3 retain160limit. C22 budgets up to8 prep/nativecells perSTEP
and yields before/after R21. Actualall48/sevenhelper stack77/minSPB2 and
forced65-output rebuild pass. Exactevidence is in the current hardening manifest.

Earlier checkpoint details follow and retain their original scope.

# Memory, overlays and future adapters

The standalone editor owns its RAM and logical REU allocations. It is not a
ReadyOS application and does not use UltimateDOS yet. These boundaries are
part of the implementation contract, not evidence of an installed OS adapter.

## Current48 incremental rendering

Resident `b33cc41e`, binding `1ecddb41a1977cec0b84d415d6ab6595`,
D81 `57be0ca4350b`:48 images in three asset banks. BSS1533 and zero page24
are unchanged; `$C600–$C9FF` remains reserved. Cold ends `$0EFE`, core/RODATA
ends `$3EFF`, with the CRC table still at `$3F00`. There is no spare core byte.

C33/grid is3914 bytes. It retains a256-byte authenticated source/font/row
witness at offset `$1500` of the existing owned FE allocation. Geometry,
source/pending revision, style/folds, selection, actual packet CRCs, provider
and publication sequence must match. Up to two caret/selection cells per row
are XORed using their four/five-pixel masks; colors remain unchanged because
caret/selection is excluded from ink voting. Unsupported changes fall back.
Operation2 contains only the pure fold/layout decision; its return cannot
nest another C overlay or borrow the File phase. The source40 common path
stays resident. GRID reuses GRIDEDIT's filename prefix at startup.

C6/window=4091, R30/gtype=3651, C32/type=3772 (3740 raw bytes at `$5000`),
R28/geosdelta=4095, C14/styler=4047. R21/geosrow=4086 and C22/geospaint=4085. R30 adds a seventh fixed helper JMP at
`$A032`; the original six `$A020..$A02F` vectors retain their addresses.
The exact white/yellow shared-tile election uses temporary scratch only,
within the existing synchronous owner4 phase. A dry caret-free transform must
prove the existing color winner before FE/VIC publication; unknown roles or
changed winners fall back. The direct pixel primitive retains strict guards.

C6 publishes certificate VALID2, and both new worker entries require2. The old
producer/consumer used1. This explicit discriminator makes mixed generations
refuse before publication; resident seals alone cannot distinguish changed
assets built for the same resident. C32 still requires the exact stage CRC and
namespace42 witness at `$5FE0`; C31 retains namespace41.

R28 class4 permits alphanumeric INSERT/BACK inside an unchanged complete
heading prefix, including CR/EOF append; its real rebuilt row must preserve
geometry before tail reuse. New wrap, structural edits and uncertain cases
fall back. No new BSS, zero page, object or REU bank is added by these changes.
Current stack analysis reassembles both staged borrowers, all seven helpers
and all48 assets; forced rebuild reproduces65 existing outputs exactly.
Native all-mode PAL/NTSC64 and targeted CPU checks pass. Lifecycle/media/
capacity release evidence is tracked separately in the current checkpoint.

The current R28 keeps the64B old-header witness at D528..D567 and one
same-transaction 842B following-row shadow at D568..D8B1. D8B2..E567 has no
readers or writers and remains exact through successful edits, refusal and
failure/recovery. Early wrap is only an optional refusal before staging, never
a new positive admission.
C22's largest gathered packet is388B and ends below the actual FS state8EE0;
its scatter order consumes overlapping style inputs before role writes. The
R21 fixed font/tail addresses ABF3/AEDB/AF5B remain unchanged. None of these
changes add a lifecycle state, allocation, bank, object or same-slot nesting.

## Historical47 local-style increment

Resident `4e64d113`, binding `bcec17ed8107a9013db3e0ba87e7e3c6`, current D81
`ed098bf5c005`:47 images still use three asset banks,1533 BSS bytes and24 zero-page
bytes. C6 is4084 bytes; R30 is2073. C32 is3553 bytes, with3521 raw executable
bytes at `$5000` and a five-byte witness at `$5FE0`. It uses namespace42; code
C31 remains namespace41. All legitimate font/stage writers revoke that window.

C32 handles 8–11 pixel suffix deletion as one byte plus 0–3 residual bit
shifts. Its 149-byte increase adds no state, bank, object, BSS or zero page.
R27 is4053 bytes; C16 is4096. Chrome rows0/1/24 use a checked 40-cell row
operation; popup rectangles retain the cell operation. Three existing UI
scratch bytes are reused within the original 88-byte phase allocation.

C14 is4047 bytes after bounded row-intersection source-color projection
(previous3923). It reuses the existing controller fields, with no new state.
The pure planner, actual root/missing-asset/ownership tests, native A/B and
current PAL+NTSC64 pixel gates pass. The full combined stack stays77/minB2.

R21 is4086 bytes with fixed font addressesABF3/AEDB and byte compositor tailAF5B.
C27 is4095; R23 cached-ink is4095. Managed preview-body stateCC4D adds no BSS/ZP;
resident grows six bytes and R26 grows eight. Core ends3EFD (two bytes spare);
cold ends0EFD. All checked CPU→REU writes and fresh prelude revokeCC4D.
The optional glyph cache uses preciselyFE[EB69,FBA9),4160 bytes, no new bank.
Its ABI3 header binds the actualFE/FD graph, resident seal and generated BSW9CRC;
recordCRC/key/metrics precede publication. C27 transport and R23 glyph scratch
share8A00 only in disjoint synchronous phases.

R30 fixes six helper JMPs at `$A020,$A023,$A026,$A029,$A02C,$A02F`. C32 links to
those helpers and the current resident seal; no resident router bytes or new
phase storage were needed. The `TYPE` startup filename aliases the suffix of
`GTYPE`, adding only three cold-table bytes. Cold code ends `$0EFD`; core/CRC and
ReadyOS reserved ranges retain the managed46 geometry below. The staged stack
verifier independently reassembles both executable borrowers and resolves their
calls in the owning overlay context.

## Historical managed46 build

Resident `bdef9dd0`, D81 `b3813f5d4fae`, binding
`b91eb05ce60de246071ec54efe90d7c3`: all46 slots fit three asset banks.
BSS remains1533 bytes, zero page24 bytes. Cold code ends `$0EFA`; resident
constants end `$3EF7`, leaving eight bytes before the unchanged256-byte CRC
lookup table at `$3F00`. Startup-only history/hot initialization and46 bytes of
cold strings moved into disposable startup storage. The357-byte sample is
copied with bounded256+101-byte loops; unused sample padding was removed.
The ReadyOS `$C600–$C9FF` reservation remains intact.

`EDITOR_MANAGED_CODE=1` applies only to editor-specific cache/provider/DMA/IEC/
startup/resume objects. Generic objects retain their original behavior.
A published catalog entry uses slot-byte bit7 as its verification memo and bit0
as slot identity; other bits are invalid. Import and first load validate the
binding and full payload CRC. Verified warm copies use one direct DMA into the
execution slot, leaving `$5000` unchanged. All entries, including active hits,
check the resident binding. A checked owner2 write/free/rebind or fresh resume
clears every memo bit, both active tags and `$CBD5` before further execution.
IEC payload writes also clear `$CBD5` before their first store, including failed
partial reads. No claim is made for arbitrary unnotified host/raw REU mutation.

The unverified load path still stages and checks before replacing an executable.
A verified direct load that discovers a bad binding refuses execution and leaves
its active tag clear; it does not promise to retain the old slot bytes.

C21 row prefix bytes30/31 publish the actual language and its complement.
R31 authenticates a complete native8 row, obtains the typed C31 asset directly,
checks binding/rawCRC and executes its pure lexer/native painter at `$5000`.
C31 links to run at `$5000` and load at `$B020`; it is a data capsule, not a
same-slot nested call. Corrected BASIC raw code occupies3314 bytes through
`$5CF1`. Its five-byte capability stamp is `$5FE0–$5FE4`, guarded against overlap.
`GF_VALID=$41` and `GF_FACE=$FF` distinguish code from cached font data.

C6 is4030 bytes after certifying every glyph role intersecting the changed
physical tile bands. R30 remains4091 bytes. No new persistent state is required.
The preview font fast path uses the checked sticky window capability rather than
an overlay-load counter; public strict font fetch retains full CRC verification.

The full stack proof resolves all1022 actual staged instructions:52 foreground
bytes plus16 IRQ/one-NMI bytes. Matching native BASIC SYS idle SP `$F6` adds nine
existing BASIC bytes, giving77 bytes total and minimum SP `$B2`. Fresh trusted
resume needs68 bytes. This bound is scoped to the pinned ROM/vector contracts,
not arbitrary ROMs or repeated NMI storms. Evidence:
`agentsworking/evidence/M8/20261025T113435781210Z-managed-stack-absolute`.

The following tables preserve earlier build-specific audits. Their resident
identities and bounds are historical. In the FE table, the current editor uses
`$D568–$D8B1` as its transaction shadow and keeps `$D8B2–$E567` dead; the older
build described below reserved the complete 4 KiB range.

## Historical44-asset delta

Current packaged cache build: PRG`e9c82775d0c6b9c1c124bd401a20ec312c8bb0ccbf7b200a2743020f8053fc25`,
D81`3d1a2b7eb63b387e9f963a8a8d23caa0757cb2bf52f8aff0d86728b2e4257c60`.
BSS1533bytes/ZP24bytes, cold end`$0EFE`, five aligned corebytes free.
C6=3897/R30=4091/C30=3399/C21=3521/R28=3768/C27=4044bytes.
The frozen41-image table below remains historical.

Direct plain typing reuses the47-byte retired R28 phase`$9149–$9177` for its
sealed certificate. Phase ownership makes these exclusive. The original20-byte
edit witness remains`$CFE8–$CFFB`. No resident state or ReadyOS shim space was
added. The existing typed FE logical allocation now contains:

| FE offsets | Meaning |
| --- | --- |
|`$0000–$B1FF`|Literal row packets/cache data |
|`$B200–$D527`|Literal caret-free8000-byte bitmap and1000-byte attributes |
|`$D528–$D567`|R28 old-header witness,64bytes |
|`$D568–$D8B1`|Current 842-byte following-row transaction shadow |
|`$D8B2–$E567`|Retired backup tail; unowned and exact,3254bytes |
|`$E568–$EA67`|128normal glyphs plus widths,1280bytes |
|`$EA68–$EA87`|32-byte normal-font READY witness |
|`$EA88–$EB68`|225-byte preview witness and all66anchor bytes |

Preview reuses the body-base area in a different packed layout:7040bitmap bytes
at`$B200–$CD7F`,880attributes at`$CD80–$D0EF`. These interpretations are mutually
exclusive. Preview clears literal publication validity; returning to editable
GEOS rebuilds the literal base. Preview lookup verifies the full bodyCRC before
its two live displayDMAs, without yielding between finalcheck andcopy. Cache
writes touch only the current bounded R28 shadow and never the dead tail or
normal glyphs. An optional cache failure cannot
reject an already rendered page. Source/settings/fold/font/provider identities
are checked on bounded continuations. Strict overlay admission remains intact.

The final44-image stack analysis resolves112foreground/module/helper graphs,
including pinned KERNAL901227-03 device8/9 IEC paths, actual emitted IRQcode and
one NMI overlap. Maximum is51bytes below root idleSP plus16interrupt bytes.
Observed natural BASIC SYS idleSP`$F6` yields minimum`$B3`, including nine existing
BASIC bytes. Fresh trusted resume starts a new stack and yields minimum`$BC`.
This is a scoped static bound, not arbitrary-ROM or repeated-NMI coverage. The
older foreground-only experiment below retains its narrower original scope.

Actual one-bank-document workloads on1MiB/2MiB REUs reach15privatebanks and all
eight objectslots during stagedOpen while retaining snapshot/clipboard/folds/
history. Transient owner writes are included. Pressure-allocation tests exercise
COPY refusal and failed secondOpen reservation rollback, then continue editing.
These measured workloads are not a universal maximum-capacity guarantee.

Two build identities matter here. The stack experiment below uses the accepted
39-asset `071324` fixture (PRG `054bfd4b…3652c`, binding
`6e15b659db9afead2209aff70fb5b6c4`). The linker audit uses the newer 41-asset
candidate, PRG `d1d2a8b0787c001f7f82b8e0c29a689e0137c8dc03704181f79527814663653e`,
binding `abc457b9d13808aedc7c1c5eac8d4625`. Adding lifecycle images does not
promote the older native gallery into native 41-asset or hardware proof.

## Historical42-asset delta

The later incremental build uses PRG`e0c9007124f0031037266ec8f29156a67e5a7a1af55c2443910946958766cab9`
and binding`112e1bd5ae2fe3c91844005e28538ef4`. The following detailed table remains
the frozen41-asset audit; these are the measured changes:42catalog entries,
cold end`$0EEE`, six bytes of aligned core slack, C22=4017, R28=3689, R21=4086 and R23=3820bytes (latest byte-decoder increment). ResidentBSS1533 andZP24 are unchanged.

The exact single-edit witness occupies`$CFE8–$CFFB`. R28's47-byte caller phase
is`$9149–$9177`; it is exclusive with other foreground owners. The existing
FE bank retains fixed2KiB ABI3 slots (842 live bytes each) through`$B1FF`, caret-free bitmap/attributes at
`$B200–$D527`, then oldheader/oldrow/newrow transaction backups at
`$D528–$E567`. The bank tail from`$E568` remains untouched by the current public build; a private verified glyph-cache candidate uses E568..EA87 and is not yet wired. No extra REU bank
or resident storage was added for incremental edits. ABI3 derives literal canonical affinities as FIRST+index; the legacy LEFT/RIGHT
array offsets are non-live. Following-row rebasing updates prefixes only.
A page is unpublished
until rebuilt-row geometry and rebased positions pass checks.

## CPU RAM

Addresses and occupied sizes below come from the frozen 41-asset linker report.
Aliased phase segments are alternatives, not additive allocations.

| Range | Use and measured allocation |
| --- | --- |
| `$0002–$0019` |24 bytes of editor zero page; linker capacity ends `$001B` |
| `$0100–$01FF` |6510 hardware stack; no document/overlay storage |
| `$0801–$0EEA` |Cold bootstrap and initialization code; discarded after startup |
| `$1000–$3FFF` |Resident entry/code/constants; CRC table `$3F00–$3FFF` |
| `$4000–$43E7` |1000 bitmap attributes; source40 uses the text matrix here |
| `$4400–$476F` |880-byte source40 semantic plan |
| `$4770–$47E7` |120-byte style checkpoint; remaining linker reservation ends `$47FF` |
| `$4800–$4FFF` |Native font copy, or inactive font space reused by narrow style plans |
| `$5000–$5FFF` |Overlay staging; verify before replacing an executable slot |
| `$6000–$7F3F` |8000-byte bitmap; color RAM remains separate at `$D800` |
| `$8000–$8BFF` |Operation-specific transfer/render scratch; not a general free heap |
| `$8C00–$8CD9` |218-byte view state |
| `$8CDA–$8CFE` |37-byte style descriptor; last VIEW byte remains unused |
| `$8D00–$917F` |1152-byte phase union: index, FILE, style, fold or GEOS work; owner guarded |
| `$9180–$91FB` |124-byte navigation state |
| `$9200–$99FF` |2048-byte pending text gap |
| `$9A00–$9D84` |901 occupied bytes of document state; capacity 1024 |
| `$9E00–$9FB4` |437 occupied bytes of checked object metadata; capacity 512 |
| `$A000–$AFFF` |4096-byte R executable slot |
| `$B000–$BFFF` |4096-byte C executable slot |
| `$C000–$C5FD` |1534-byte resident BSS; 2 bytes remain before `$C600` |
| **`$C600–$C9FF`** |**ReadyOS's reserved 1 KiB: no editor fill, BSS, loaders or DMA** |
| `$CA00–$CB7F` |64-entry overlay catalog, 384 bytes |
| `$CB80–$CBBF` |64-byte session settings table |
| `$CBC0–$CBFF` |64-byte font-store state |
| `$CC00–$CFFF` |1024-byte preview/caret-cache workspace |

VIEWSTATE occupies `$8C00–$8CD9` inclusive; the descriptor starts `$8CDA`.
The code/core/constants end at `$3EFD`, leaving 2 bytes before the aligned CRC
table. This alignment slack is not a general allocation pool. BSS, VIEW and
individual overlays must each respect their own limits.

The full warm CPU payload is two disjoint extents: `$1000–$C5FF` (`$B600`
bytes), then `$CA00–$CFFF` (`$0600` bytes). Editor ZP `$0002–$0019` adds 24 bytes:
`$BC18` bytes total. The stack, vectors, CIA/VIC registers, color RAM and CPU
port are not included in those extents. The reserved ReadyOS gap must never
be bridged by a contiguous copy.

## Overlay calls and measured sizes

SEO2 images contain a 36-byte checked header followed by at most 4096 payload
bytes, including a 16-byte resident-binding signature. The resident loader
validates slot, ID, size, entry, binding and CRC before executable replacement.
A cached image is a checked logical REU allocation, not a persistent RAM pointer.
A call supplies the resident frame; modules must not retain pointers into
another evictable image.

R-slot 0 is `$A000`, C-slot 1 is `$B000`. Same-slot nesting is rejected. C→R
nesting is allowed; calling C from an active R is rejected. A root scheduler
therefore sequences C workers instead of nesting them. IRQ/NMI handlers are
resident and do not load overlays or DMA document state.

The audited 41-image candidate uses 41 of 64 catalog entries. Full slots are
R16 and R17 (4096 bytes); C16 is 4095, leaving one byte. R1 is 4070, C22 is 4065,
R21 is 4047 and C23 is 4030. The new lifecycle controller C29 is 2304 bytes
(including its fixed template), R26 copier 1783. These sizes include binding,
entry and data; they are not estimates of executable instructions alone.
The complete per-image hashes are [archived with the audit](../build/editor-stack/20261025T075401300951Z/current41-map/overlay-sizes.json).

| Image | Slot/module ID | Payload bytes | Bytes to 4096 |
| --- | --- | ---: | ---: |
|`eedit`|C4|3456|640|
|`eplay`|C5|2118|1978|
|`window`|C6|2543|1553|
|`text40`|R1|4070|26|
|`menu40`|C7|2491|1605|
|`engine`|R2|3516|580|
|`navigate`|C8|3804|292|
|`search`|C9|974|3122|
|`block`|C10|3872|224|
|`layout`|C11|3738|358|
|`fileio`|C12|3965|131|
|`aux`|C13|2272|1824|
|`styler`|C14|3923|173|
|`viewsource`|R14|2331|1765|
|`lexical`|C15|3664|432|
|`gridedit`|C16|4095|1|
|`grid80`|R16|4096|0|
|`grid60`|R17|4096|0|
|`foldparse`|C17|3297|799|
|`foldfinish`|C18|3230|866|
|`foldcore`|R18|3015|1081|
|`foldctl`|C19|1343|2753|
|`rangeio`|R19|2817|1279|
|`foldxform`|R20|2987|1109|
|`geosline`|C20|3461|635|
|`geospage`|C21|3402|694|
|`geosrow`|R21|4047|49|
|`geospaint`|C22|4065|31|
|`geosnav`|C23|4030|66|
|`geossema`|C24|2268|1828|
|`geoslex`|C25|3872|224|
|`geosinln`|C26|3160|936|
|`popups`|R22|3793|303|
|`geospreview`|C27|2273|1823|
|`geosfontrow`|R23|3373|723|
|`geosfontin`|C28|791|3305|
|`geosfold`|R24|1541|2555|
|`geostail`|R25|246|3850|
|`geoscaret`|R27|3933|163|
|`lifectrl`|C29|2304|1792|
|`lifecopy`|R26|1783|2313|


## REU provider, document limits and DMA

The standalone provider probes capacity, then maintains logical→physical maps,
typed ownership and an epoch. Bank 0 is reserved by this provider; it is not an
application scratch shortcut. Objects carry ID, generation and provider epoch,
and split checked transfers at logical-bank boundaries. Never substitute an
object ID, logical handle or file number for a physical REU bank.

The ordinary `se_reu_copy` buffer must fit wholly in `$4000–$BFFF`, have a
nonzero exact 16-bit length and stay in one 64 KiB REU bank. It validates the full
request before writing REU registers and briefly masks IRQ around the DMA.
The one-byte presence probe and lifecycle copier have separate narrow contracts;
their special handling does not widen the general DMA API. Document readers
have stricter phase/buffer rules as well: a physically legal address does not
establish ownership of VIEW, NAV or another live phase.

The engine allocates metadata plus separate original and append objects. Its
source quota derives from the original object's admitted bank count. Pending
insertions and their eventual append interval are checked before mutation;
full-capacity refusal must preserve the pending edit, caret, selection and
usable Undo history. Capacity is not the same as free physical REU space.

Actual historical full-feature cold-boot/edit/save evidence exists at 1 MiB and
2 MiB; the full font configuration refuses 512 KiB and missing REU. The native
64KiB boundary gate verifies a one-bank quota, early refusal, replacement,
Undo/Redo and byte-exact 65536-byte SaveAs/reopen. These are tested configurations,
not a promise that every document/history/clipboard combination fits 1 MiB.
The standalone gallery uses 16 MiB. Allocation counts at checkpoints are not
transient high-water measurements.

## Observed foreground stack

The immutable 39-asset run passed 128 seeded rounds and 183 canonical/integrity
checks, including all four modes, insertion/deletion, Undo/Redo, clipboard,
fold/preview churn and source offsets above 64 KiB. It sampled **2,593,027,928
instructions across 101,364 foreground calls**. No observed push wrapped SP.

The deepest sample was **SP=`$DE`: 33 bytes used from `$FF`, including the two
synthetic caller bytes**. The remaining stack address range is 223 bytes
(`$0100–$01DE`); this is numerical headroom at an observed sample, not a proven
native reserve. It occurred while public RIGHT (command 2) drained job 2 in GEOS:
`se_editor_service`, with C4 `eedit` and R2 `engine` loaded. The actual deepest
instruction was JSR at `$21BE` (`se_object_validate`) to `$21A0`
(`object_service_valid`). Catalog indexes were 1 and 6 respectively; indexes
are not module IDs.

[Full stack samples and identity](../build/editor-stack/20261025T075401300951Z/stack-result.json),
[original soak result](../build/editor-stack/20261025T075401300951Z/result.json),
[calibration](../build/editor-stack/20261025T075401300951Z/calibration.json),
and [41-asset linker audit](../build/editor-stack/20261025T075401300951Z/current41-map/editor-report.json)
are separate records. The stack workload's final source SHA256 was
`2d9f24a314b12c703974431563ce307087c0ace83f67678ed7fc55159207117c`.
No pixel or emulated-cycle claim is derived from this instruction experiment.

The CPU harness starts each callable service at SP=`$FD`, with two synthetic
return bytes in `$01FE/$01FF`; reported usage from `$FF` includes those two
bytes. It executes real editor instructions, including checked overlay loads,
and records SP before and after every instruction. It neither patches editor
code nor substitutes a host source/history implementation. Explicit fixture
source/font imports and ROM IEC seams are excluded from the measurement.

The seven-instruction calibration reaches SP=`$F9`: the two caller bytes,
one nested JSR, PHA and PHP require exactly six bytes. This catches a probe
which samples only entry/exit and misses the deepest push.

This is **observed foreground depth**, not a static worst-case bound. CPU
interrupts are masked in this experiment. The separate native PAL/NTSC timing
gate compares `$0100–$013F` before/after real IRQ-driven operations; that proves
those 64 bytes stayed unchanged in those samples. It does not identify the
lowest transient SP or establish a universal 192-byte native bound.

The resident IRQ handler calls KERNAL UDTIM (`$FFEA`) and SCNKEY (`$FF9F`), then
returns through `$EA81`. Its comment/ABI expects the KERNAL dispatcher to have
stacked A/X/Y; each handler JSR itself pushes another two bytes, while ROM
helper nesting is outside this CPU probe. The NMI handler adds exactly three
software pushes and no JSR; the 6510 interrupt entry adds three hardware bytes.
Those local facts do not bound upstream ROM entry, NMI interrupting an IRQ,
repeated NMI edges, or IEC OPEN/CHRIN/CHROUT/status/error paths. This historical probe alone claims no audited
combined IRQ/NMI/ROM maximum. Its original follow-up requirement was
verified ROM-revision call-depth analysis or instruction-level native tracing
covering those paths, not subtraction of a guessed interrupt allowance.

## Lifecycle and future OS integration

The current47 standalone adapter has native four-mode capture/restore and
continued editing/SaveAs/reopen evidence, including affected preview-cache
revocation tests. Its versioned C29/R26 contract remains the one described
below; the current checkpoint identifies all exact build scopes. This is a
controlled standalone adapter, not a ReadyOS application switch.

The original 41-image candidate contains a standalone, same-process C29/R26 adapter.
Its current contract uses an FC-typed logical snapshot allocation, a versioned
header, resident binding, provider/source witnesses and a fresh trusted low-RAM
thunk. Capture and verification steps process at most 256 payload bytes or one
provider table. The final trusted thunk restores the complete fixed extents
and transfers control; that final commit is not a 256-byte step. Restore
verifies before publishing and resumes at a fresh editor event loop, never at
a saved C/R-slot PC or saved CPU stack. Its exact-extent copy is deliberately
separate from general DMA.

The fresh control region includes bounce `$0700`, binding/descriptor `$0800`,
restore thunk `$0900` and resume prelude `$0A00`; these are cold-only facilities,
not new warm allocations. The current primitive assumes its live provider and
backing REU remain owned and its known interrupt hooks are not externally
raced. Actual standalone scramble/resume tests belong to that adapter's own
identity/evidence. This document's 39-image stack/native gates do not establish
41-image lifecycle, power-loss recovery, OS switching or hardware readiness.

ReadyOS currently snapshots `$1000–$C5FF`; its existing shim alone does not
preserve `$CA00–$CFFF`, editor ZP, color RAM, vectors or hardware state. A future
adapter must explicitly preserve the second extent, coordinate provider-owned
allocations/epochs, reinstall runtime hooks and refresh display/input state at
an OS safe point. It must replace the standalone allocator/probe, not rerun
cold provider initialization over live mappings. The editor remains excluded
from `$C600–$C9FF`. No ReadyOS registration or C8xx calls are implemented here.

UltimateDOS belongs behind the existing bounded open/read/write/status/directory
transport seam. Keep filename/device binding, acknowledgement, staging,
verification and atomic source publication in the editor coordinator. Replacing
IEC transport must not flatten canonical source, bypass ownership checks or
convert PETSCII data into host text. D81/KERNAL transport remains the current
standalone implementation.

# Native START / main handoff ABI 1

Implementation contract, not yet a working launcher or hardware acceptance.
The main consumer is implemented and model-tested in runtime `cea57480`:
`make test-loader-handoff` checks validation/adoption and real Peddle NMI
delivery; `make test-loader-dos` boots genuine DOS through VER and DIR /P.
Its default required flag is zero for legacy startup. The generated standalone
START entry, user interface and physical handoff remain pending.
All integers below are little endian. CRC32 is reflected EDB88320, initial
FFFFFFFF, final XOR FFFFFFFF, identical to the durable CFG codec.

START loads complete raw A at REU100000 and optional B at180000. Each must be
exactly05A000 bytes, closed, and CRC-verified against durable CFG before handoff.
The complete main PRG, including its two-byte0801 load header, stages at3E0000.
Its length is at mostB801; the payload must fit0801..BFFF. START validates the
unmodified release CRC before changing only D64N, D64H and the required flag.
These ranges must be distinct, contained in the checked PRG and match their
disabled template signatures. All file handles are closed/transport quiet.

The fixed REU anchor at3FF000 contains a32-byte D64R header and the exact576-byte
D64C CFG at3FF020. Header fields:

|Offset|Bytes|Value|
|---|---|---|
|0|4|ASCII D64R|
|4|1|Version1|
|5|1|ReadyA5, published last|
|6|2|Header length32|
|8|4|CRC of CFG bytes0..571, equal its stored CRC572..575|
|12|4|CRC of the patched complete staged main PRG; diagnostic binding|
|16|4|Verified A CRC, equal CFG528..531|
|20|4|Verified B CRC, equal CFG532..535; zero when absent|
|24|2|UCI base, DF1C / DE1C / DFFC only|
|26|1|Floppy target1|
|27|1|Hard-drive target2|
|28|4|CRC of header bytes0..27 with ready=A5|

Do not CRC the576-byte codeword to bind CFG identity: appending its own CRC
gives a fixed CRC residue. Bind bytes0..571 and check the stored CRC separately.

Write body first, then header with ready0, then readyA5. Any failure/cancel must
leave ready0; final success is the only publication. Main's serialized
`dos64_loader_required` defaults0. START patchesA5. Values other than0/A5 fail.
For A5, cold startup validates both CRCs, all CFG semantics and cross-field
bindings before adopting any media, then consumes ready (writes0). Missing,
consumed or malformed required handoffs fail; no silent legacy fallback.
Legacy0 startup is unchanged. The main-PRG CRC is recorded context, not a claim
that the main consumer independently verified its own live mutated image.

The cold consumer initializes D64N/D64H from validated CFG before their existing
checks. A's target is1; C's target2, bootDL0, importfloppy flag1, configured
readonly/profile/path. Use32 HD cache slots (existing reserved1MiB), not old2.
Convert configured REU bytes to conservative whole MiB by floor, minimum4;
no caller may round capacity upward. Main only uses baseline fixed arenas.
After disk/FILES/import initialization and before legacy import starts, check
the CFG body again against captured CRC, CRC every byte of preloaded A/B, and
adopt through PREPARE/COMMIT. First A PREPARE must return100000 and B180000;
refuse any mismatch. Pass captured readonly and CRC as binding. No partial
consumer failure boots a partially adopted configuration. Preloaded success
skips legacy import and enters the existing post-import BIOS/HD startup path.

Cold code may occupy4000..43FF before font4400; if measured code exceeds this,
report it and propose another explicit lifetime/layout. Never silently overlap
fonts, device code, packaged overlays or resident state. Header/CFG scratch may
use C100..C35F and image-CRC bounce C400..C4FF before UCI ownership; phase2 must
prove disjoint use of FILES/UCI state. Revalidate RAM ownership after linking.

START owns RAM/I/O with IRQs disabled, D=0, and CIA sources masked/acked. Its
fixed RTI at5882 and RAM NMI vector5882 are installed before first mapping35.
All START code/state exclude5000..5FFF. ABI1 incoming main NMI must be5882 and
byte40. Thus the whole payload DMA never invalidates the installed handler or
changes its vector. The0200 trampoline resets SP, programs DF02..DF0A, submits
REU3E0002->0801 for checked payload count, requires bounded EOB/no error, then
JSR checked native_start; carry failure enters checked idle, else JMP native_loop.
No C software-stack frame survives this jump. Actual NMI delivery tests and
physical qualification are required; a host ordering assertion is insufficient.

The64-byte D64L release descriptor is separate DOS64.REL, generated from exact
unmodified main PRG and labels. Fields: magic0 D64L, version4=1, capabilities5=1,
length6=64; PRG size8/4, PRG CRC12/4, load16/2=0801, payload18/2;
start20/2, loop22/2, idle24/2, NMI26/2=5882; D64N fileoffset28/4,
D64H fileoffset32/4, requiredflag fileoffset36/4; staging40/4=3E0000,
anchor44/4=3FF000; CFGbytes48/2=576, handoffbytes50/1=32, NMIopcode51=40;
D64Nbytes52/2=142, D64Hbytes54/2=140; reserved56..59 zero;
descriptorCRC60/4 covers0..59. Bounds, nonoverlap and template signatures are
mandatory before any patch. This descriptor binds a release; it is not a
cryptographic signature or authorization to open arbitrary external files.

Generated START stores canonical absolute home in initialized serialized data,
not BSS, and reads DOS64.CFG / DOS64.REL / DOS64.PRG there. It uses the CFG's
explicit A/B/C paths. No mounted D81, guessed current directory, firmware REST,
guest DOS copying, bundled DOS image or preallocated HD template is required.

Current components: public `make setup-release-tests` runs four actual Zig/Peddle descriptor groups and four host-tool groups. Private staging controller faa30 and main cold consumer ce482 have separate native proofs; their composition, runnable START, setup UI and physical acceptance remain pending. Physical bulk32K c5 is accepted with complete recovery; it does not accept this launcher.

## Standalone launcher build

`make start` produces `build/start/START.PRG`, a disabled template with persistent ownerFF/homeFF. `make start-tests` rebuilds a fresh test cohort and runs46 actual6510 groups, including genuine DOS from locally supplied reference images. The build requires cc65/ca65/ld65 and none.lib; model tests also require clang++. DOS64_CC65/CA65/LD65 and DOS64_CC65_LIB may select the toolchain. Neither target contacts the Ultimate.

The launcher uses its native SYS2061 entry, explicit startup CLOSE1/CLOSE2 through the same FILES/UCI engine, coherent CIA elapsed time and Run/Stop cleanup. Its complete18,432-byte PRG loads0801..4FFE, leaving one byte below5000. CRC tables areC900..CCFF, software stackCD00..CFFF and the final112-byte trampoline occupies0200..026F. Default codec flags retain the original maker/decoder bytes; START opts into fast CRC and decoder-only compilation.

Configured A/B model boot verifies the complete main payload and delivers NMIs through both the platform RTI and main5882 before genuine DOS VER/DIR. C backing-file transfer and real Ultimate acceptance remain separate. Native SETUP must validate a release-bound template descriptor before patching persistent home/base/owner and must fully verify the written launcher; the host patch in the tests is not an installer.

## Native SETUP template patching

`make start-template` additionally creates the64-byte `build/start/START.REL` D64S descriptor; `make start-template-tests` checks the host generator against the actual launcher. This descriptor binds the disabled START template and is distinct from D64L `DOS64.REL`, which binds the emulator. The native UI-phase helper `tools/setup/start_template.c` validates received size, descriptor/template CRCs, initialized DATA/control defaults and canonical home/base before streaming a copy that changes only the131-byte persistent control. It adds no resident START bytes.

The caller supplies buffered readonly source and fresh output callbacks. Native completion is byte-copy acceptance only: flush, WRITE/CLOSE, reopen, fullCRC/EOF and finalCLOSE must finish before the installer publishes START or CFG. Discard partial outputs. Actual helper/error/CRC0 and patched START-entry tests are recorded in `agentworking/evidence/native-start-template-root-20261016.json`; full installer integration remains pending.

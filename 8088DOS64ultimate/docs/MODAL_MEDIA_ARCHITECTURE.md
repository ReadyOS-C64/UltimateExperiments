# V1 native disk controls: measured integration checkpoint

This is the current implementation boundary, not a released menu. The default
emulator remains `666089b5`; the optional selected Save As profile is `46fa2e54`.
Neither currently provides the complete interactive disk workflow. V1 acceptance
remains defined by [V1_ENDPOINT.md](V1_ENDPOINT.md).

## Components actually executed

The native C frontend displays independent A/B status and collects Save, Save As,
Insert, Eject, Write Protect, Resume and Finish intentions. Dirty media gets
Save/Discard/Cancel choices. Its private ticket and pending intention, rather
than the public display/event buffers, determine which reply it will consume.
The backend must still validate and perform every operation.

The frontend executes as real cc65/6510 code under Peddle with physical CIA1
matrix input. Fifteen component groups cover keys, modifiers, cancellation,
both dirty-drive decisions, stale/forged observations, bounded path editing,
and all 255 nonzero filename bytes. Ambiguous glyphs are shown as `%XX`; event
paths retain their original bytes. No FILES, REU or clock initializer is enabled
in those isolated frontend tests.

A separate assembly broker admits only an already coherent paused guest, after
cold ownership has been released, with all 32 cache frames unpinned and the
transport, overlays and C context quiescent. It flushes dirty guest memory,
invalidates cache tags and all published map entries, and sets cache limit zero
before any menu/worker can replace cache RAM. It retains exact FILES, HD and
HD-BIOS snapshots and checks them again before releasing memory.

Eight actual broker groups cover all 32 dirty frames, guest refills after
release, both C targets with a warm cache, 22 rejected admissions, 208 altered
context bytes/fields, clock failure/defer, repeated sessions and write guards.
Two additional composition groups execute the actual C frontend through this
broker: 48 frontend calls across three machines, real CIA selection/path/cancel
input, Resume, and a deliberately failed Save As intention. Whole 4 MiB REU,
C handle/position, and timer-control writes remain unchanged. These are model
component tests, not a successful end-user save or physical screen acceptance.

## Actual linked ownership

| Range | Current private component | Measured use |
| --- | --- | --- |
| `7000..76FF` | Broker instructions and private snapshots | 1,101 bytes through `744C` in the terminal-error successor |
| `7700..77FF` | Broker state | 221 bytes through `77DC` |
| `7800..7C98` | Frontend state | 1,177 bytes |
| `8000..9CFC` | Frontend code, constants and initialized data | 7,421 bytes; PRG is 7,423 bytes |
| `80..99` | Frontend zero page | 26 bytes |
| `B800..BFFF` | Declared frontend software-stack region | Observed lowest write `BFE6`; compare-buffer overlap is guarded |

The broker exchanges the frontend's reserved high zero-page range `80..DF`
around C calls. The current normal native map uses `20..43`, so these ranges
do not currently alias; the explicit exchange also establishes which context
may call resident assembly. The hardware stack is shared normally. No C frame,
software-stack pointer into a worker, or worker instruction may survive phase
replacement.

The broker selects 40-column native text with the lower/upper ROM charset
(`D018=16`) and preserves observable VIC/CIA2 bank settings. It does not call
standalone `ps_init`, reset CIA timers, read ICR/TOD, or replace NMI handlers.
An incoherent clock sample defers; a real ownership/control failure blocks
Resume. The caller must continue sampling the existing elapsed clock while
the guest is paused.

The current broker is linked against the **unit** image's labels. A final asset
must be relinked against its matched runtime and checked by the release loader.
These private files are not installable release assets.

## Remaining integration

The resident native code is nearly full: MAIN has one byte, DEVICE has 16,
HDBIOS has ten, and the selected SAVER has four. Consequently the menu and
configuration logic run in explicitly borrowed RAM, rather than being added
to those resident segments.

A proposed immutable asset area is `3DA000..3DFFFF`, the 24 KiB gap after the
third complete floppy arena. Two KiB broker, eight KiB frontend, and two six KiB
worker phases consume 22 KiB before container/alignment overhead. This is a
budget, not a linked release or implemented loader. Runtime work can use the
separate, cold-released `3E0000..3EFFFF` staging area. Both remain inside 4 MiB;
the unbacked upper REU is not used.

The loader/hotkey still needs implementation. One possible fit reuses the input
overlay to request a coherent pause and load only the broker into retired bitmap
RAM. It must return to the resident wrapper and release the overlay lease before
entering the broker. The broker must return to resident code before a full paused
guest redraw reclaims its bitmap and cache RAM. Restore VIC settings **and redraw
guest pixels, matrix and colors before RUN**; restoring registers alone is not
enough after the frontend has used color RAM.

Selected Save As/output CRC already has a portable 27-group public test graph.
Its present completion restores cache limit 32/stage 5, which is incompatible
with a live modal owner. A modal worker must retain cache limit zero/stage 8 and
return with known C context before the controller can switch phases. A verified
file or CRC alone never grants CLEAN or a new backing path.

Durable binding/configuration is being implemented separately: create a new
verified image and candidate CFG, persist an exact old/new CFG journal, then
use no-replace renames and reopen verification. START must recognize a pending
journal before trusting normal CFG. Collisions, mixed states and uncertain
closure retain artifacts and cannot look like Save success. This is the current
implementation direction; journal recovery, normal Save, Insert/Swap, Finish,
matched asset installation and physical acceptance are not complete.

Evidence: [public Save As graph](../agentworking/evidence/native-media-public-root-20261017.json),
[broker component](../agentworking/evidence/native-media-broker-component-root-20261017.json).
The composition and frontend source/product identities are retained in the
project-local `agentworking/scratch/live-media-composition-root-20261017` and
`live-media-panel-display-successor-20261017` cohorts.

The private terminal-error successor adds six ROOT-replayed actual native controls. Owned/cache0 presentation can show a terminal stage E1 error; backend polling, release and Resume remain stage8-only. The controller must call `mu_block` with the first failure and never reinitialize a failed session. Public observations cannot clear the private block or pending ticket. [Terminal-error evidence](../agentworking/evidence/native-media-terminal-fault-root-20261017.json).

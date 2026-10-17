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
| `7000..76FF` | Broker instructions and private snapshots | 1,612 bytes through `764B` in the hotkey/runtime successor |
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

Broker assets now have separately linked unit and runtime roles; their cold_open aliases differ. Cold START verifies the role-specific whole-file CRC as well as the common cohort header. The complete Save As controller below currently proves the unit role; its final cold container/runtime/menu combination remains to be coupled. These private files are not installable release assets.

## Full Save As controller checkpoint

The private controller now performs one complete Save As operation in one actual native entry: acquire the old configuration, save and verify the selected image, build the new configuration/journal, publish the durable transaction, bind the live configuration/launch records, then mark the selected disk clean. It loads each matching worker itself from REU and validates its CRC; every worker frame returns before replacement. The test host does not swap phases or manufacture completed worker facts.

Seven actual Peddle groups pass: B in arena38 with C target1, A in arena18 with C target2, four corrupt phase assets, and an existing output-file collision. They check the full image/configuration, original files, C state and position, caller high zero page/flags and complete4MiB guards. A reproduced postcommit failure originally denied Resume only in its result buffer while native release still succeeded. The fix leaves native stageE1 whenever private commit/closure/clock rules deny Resume; actual release rejection is now tested. Restored C does not clear a terminal error.

Controller code/data/BSS uses8000..8FE3, preserving CUI state7800..7C98. Its separate software stack is9E00..9FFF and nested PLAN/BIND workers useBFFF. The first24KiB asset source gap remains3DA000..3DFFFF; the private40KiB cold loader also maps retired installer storage3F0000..3F3FFF for controller/BIND. The third complete floppy is preserved. The cold loader proof and worker-controller proof are separate: the current worker fixture has blank broker/UI slots and is not the final cold container.

The next step connects the frontend's private intent/ticket through a resident load/return/reload bridge, couples actual runtime-role assets to START/main, and completes normal Save, Insert/Eject, write protection, Finish and explicit startup-journal recovery. Existing startup validation blocks pending journals before normal configuration acquisition; recovery mutations and their user controls remain private work. SETUP preflight/package updates and final physical installer/media/Turbo/restart/human acceptance remain required. No speed improvement blocks V1.

[Full controller evidence](../agentworking/evidence/native-media-action-controller-root-20261017.json), [cold40KiB loader](../agentworking/evidence/native-start-40k-root-20261017.json), [startup journal gate](../agentworking/evidence/native-start-journal-root-20261017.json).

Evidence: [public Save As graph](../agentworking/evidence/native-media-public-root-20261017.json),
[broker component](../agentworking/evidence/native-media-broker-component-root-20261017.json).
The composition and frontend source/product identities are retained in the
project-local `agentworking/scratch/live-media-composition-root-20261017` and
`live-media-panel-display-successor-20261017` cohorts.

The private terminal-error successor adds six ROOT-replayed actual native controls. Owned/cache0 presentation can show a terminal stage E1 error; backend polling, release and Resume remain stage8-only. The controller must call `mu_block` with the first failure and never reinitialize a failed session. Public observations cannot clear the private block or pending ticket. [Terminal-error evidence](../agentworking/evidence/native-media-terminal-fault-root-20261017.json).

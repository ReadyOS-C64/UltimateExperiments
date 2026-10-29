# Auxiliary command operations

ID13 in the command slot shares rare control and modal-paint work without adding
another persistent frame. Every entry returns to resident before a different
command overlay is loaded. Operation IDs are in `api.inc`.

| Operation | Ownership and result |
| --- | --- |
|1 layout context | Pure no-wrap comparison of source/view identities, generation, revision and bounds; A0 ready/A1 rebuild, carry clear. Does not access LINEINDEX/FILESTATE. |
|2 file emergency | Independent of C12. Close only owned channels, validate epoch, restore uncommitted OPEN or finish acknowledged H_INIT publication, release only owned candidates/lease; retain exact DOS capabilities and recovery owner. |
|3 index publication | The original sparse-index prefix trimming algorithm, called once after a known publication. |
|4 recovery keys | F6 help remains available; STOP closes only a safe frame without retained DOS capabilities. K explicitly keeps recovery files and closes a source-safe frame without DOS writes. |
|5 file popup | Stateless ReadyOS-style filename/list/confirmation/help/recovery painting using the phase-owned FILESTATE frame. |

`se_index_changed` remains resident. It invokes operation3 at a root safe point;
if admission fails after publication, it conservatively invalidates the derived
index rather than leave stale checkpoints trusted. No source or history change
is rolled back merely because this acceleration helper is unavailable.

C12 admission errors while a file command owns the union invoke operation2.
The resident preserves the original admission error and consumes `committed2`
before showing recovery, so an acknowledged new-document publication cannot be
paired with the old hot window. If AUX is also unavailable, the resident closes
known owned LFNs5/7 and retains the frame/owner/candidates/leases. It cannot infer
a safe rollback from two unavailable command images.

The extra catalog entry and all workspaces stay in the existing memory/REU
contracts; `$C600-$C9FF` remains untouched. Current build measurements and exact
evidence identities belong to `agentsworking/STATUS.md`, not this API description.

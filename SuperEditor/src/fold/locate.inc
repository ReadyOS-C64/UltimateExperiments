.ifndef SE_FOLD_LOCATE_API
SE_FOLD_LOCATE_API=1
.include "fold/api.inc"
SF_LOCATE=4
.global se_fold_locate_begin,se_fold_locate_step,se_fold_locate_cancel
; Read-only target locator. Requires trusted, exclusively caller-owned tree.
; BEGIN inputs query24 andmode0any/1expandedonly/2collapsedonly, unchanged until
; done/cancel. Target16 publishes only on success;FFFF means no visible target.
; Innermost eligible summary<=query<end wins. Collapsed hidden ancestor blocks
; all descendants: choose that ancestor ifeligible, otherwise returnFFFF.
; STEP authenticates tick/read and transfers atmostone32-byte record. Cancelling
; this job preservesvalid+target; foreignbusyjob is rejected, nevercancelled.
; Scratch aliases: next3=query snapshot,action=mode snapshot,last2=candidate.
; No allocation/BSS/ZP or metadata/source writes. SameD=0,A/X/Y/P clobbers/errors
; as foundation. Read/identity failure revokesvalid via se_fold_fail.
.endif

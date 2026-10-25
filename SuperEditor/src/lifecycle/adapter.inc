.ifndef SE_LIFECYCLE_ADAPTER
SE_LIFECYCLE_ADAPTER=1
.include "lifecycle/copy-entry.inc"
LC_CONTROLLER_ID=29
LC_COPY_ID=26
LC_BEGIN=0
LC_STEP=1
LC_CANCEL=2
LC_HARDWARE=5
; C29 BEGIN validates quiescence and source, allocates/reuses one FC bank,
; captures59B source+caret+selection witnesses, then starts R26.
; STEP revalidates source/input before one bounded R26 unit. It never flushes.
; Caller installs trusted binding0800 +fresh resume0A00 before BEGIN.
; Resume uses freshly trusted R26 (never an unverified/scrambled oldloader).
; Same-process/live-provider/backing-REU immutability contract applies.
LC_E_CHANGED=$DF
.endif

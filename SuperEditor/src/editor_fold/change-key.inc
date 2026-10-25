.ifndef SE_EF_CHANGE_KEY_INC
SE_EF_CHANGE_KEY_INC=1
; Pure, operation-sized caller frame. No resident allocation, ZP, source reader,
; DMA or live-service imports. Caller supplies already validated full28B keys
; captured under exclusive editor ownership. This is an evidence checker, not
; authentication of arbitrary caller-written RAM.
EFC_OLD=0
EFC_CURRENT=28
EFC_HOT_ORIGINAL=56
EFC_HOT_APPEND=61
EFC_HOT_GENERATION=66
EFC_HOT_EPOCH=68
EFC_READY=70
EFC_PENDING=71
EFC_PHASE=72
EFC_FAULT=73
EFC_BASE=74
EFC_OLD_LENGTH=77
EFC_LENGTH=79
EFC_LEFT=81
EFC_RIGHT=83
EFC_PREFIX=85
EFC_SUFFIX=87
EFC_DOC_LENGTH=89
EFC_BUSY=92
EFC_KIND=93 ;1hotpublication,2block,3undo,4redo
EFC_REQUEST=94 ;authoritative position/delete/insert, three24-bit fields
EFC_BEFORE_TICKET=103 ;32-bit caller-observed successful publication serial
EFC_AFTER_TICKET=107
EFC_AUTH=111 ;$A5 only after provenance requirements below are satisfied
EFC_RESULT=112 ;position/delete/insert; published only on success
EFC_SCRATCH=121 ;six bytes
EFC_VALID=127
EFC_FRAME_SIZE=128
EFC_CHANGED=$B7
EFC_RANGE=$B8
EFC_PROVENANCE=$B9
; PENDING requires OLD captured after flush (no pending bytes), CURRENT from
; actual merged view; same committed graph/generation and nonwrapping newer
; render revision. A single current gap represents every edit since OLD.
; PUBLICATION requires caller observed precisely one successful source commit,
; captured REQUEST at publication, retained OLD before it, and CURRENT after
; pending cleanup. AFTER_TICKET=BEFORE_TICKET+1, nonwrapping; no inferred witness
; from stale se_doc_edit_* or generation alone. Current product has NO such
; persistent ticket. An integration must add the seam or synchronously consume
; every actual publication. History group undo can contain multiple commits:
; observe/check one event per committed record, not one event per keypress.
; Both reject epoch/token changes and numeric wraps, busy/transient source,
; malformed shapes or length arithmetic. Cclear/A0 success, Cset error above.
; Failures clear VALID, preserve RESULT and all input bytes. A/X/Y clobbered.
.import se_ef_change_frame
.ifndef SE_EF_CHANGE_IMPLEMENTATION
.import se_ef_change_pending,se_ef_change_publication
.endif
.endif

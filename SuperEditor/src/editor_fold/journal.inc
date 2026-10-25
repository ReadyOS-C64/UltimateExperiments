.ifndef SE_EF_JOURNAL_INC
SE_EF_JOURNAL_INC=1
EJ_ARMED=1
EJ_DIRTY=2
EJ_FAILED=$80
EJ_LIMIT=112
EJ_LOCAL=2
EJ_COMMIT=3
EJ_FLUSH=4
EJ_BASELINE=5
EJ_READLOG=6
; Operation-sized R19 service, no R calls/phase workspace/ZP. LOCAL consumes
; authoritative pre-mutation hot_caret/delete(0/1); COMMIT consumes actual
; successful se_doc_edit tuple after source publication. FLUSH advances the
; committed-generation witness but never logs already visible edits twice.
; BASELINE requires a fresh valid merged-view fullsource key and resets count.
; Ticket is monotonic32-bit per appended edit, never reset by BASELINE; wrap
; disarms. READLOG fetches exactly count*9 at $8000 (zero count = no DMA).
; Tail is the last1024 bytes of the validated type46 fold object; fold count
; must be <=banks*2048-32. Object logical size already spans full capacity.
; Guard/write failures set STATUS80, preserve count/ticket/witness, return
; genuine Cset/Aerror; root observer wrapper MUST suppress failure for editing.
; INPUT/REQUEST and $8000..$83FF are foreground scratch. Does not touch phases,
; release leases, mutate canonical bytes, free/resize objects, or call R18.
; BASELINE arms; successful first append switches to DIRTY; repeated append
; allowed while DIRTY. No operation is legal while disarmed/FAILED except a
; fresh BASELINE. Caller serializes source publication and observer callbacks.
.ifndef SE_EF_JOURNAL_IMPLEMENTATION
.import se_ej_local,se_ej_commit,se_ej_flush,se_ej_baseline,se_ej_readlog
.endif
.import se_ej_position,se_ej_delete,se_ej_insert,se_ej_count,se_ej_status,se_ej_ticket
.import se_ej_generation,se_ej_length
.endif

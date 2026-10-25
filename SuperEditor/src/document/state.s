.setcpu "6502"
.include "document/api.inc"
.segment "BSS"
se_doc_epoch: .res 2
.segment "DOCSTATE"
; Root entry: leaf slot,record count,byte count24,newline count24.
; Newline FFFFFF means not indexed yet; it is never used for byte seeks.
se_doc_roots: .res DOC_ROOTS*8
.assert se_doc_roots = $9A00, lderror, "root table moved"
se_doc_next_roots: .res DOC_ROOTS*8
se_doc_ready: .res 1
se_doc_generation: .res 2
se_doc_length: .res 3
se_doc_root_count: .res 1
; Object tokens5 bytes, source offsets/lengths24 bits, no screen pointers.
se_doc_meta: .res 5
se_doc_original: .res 5
se_doc_append: .res 5
; Foreground caller request; read leaves it unchanged.
se_doc_source_length: .res 3
se_doc_offset: .res 3
se_doc_count: .res 2
se_doc_c64: .res 2
se_doc_busy: .res 1 ;0 idle,1 feeding,2 building; suspend forbidden while nonzero
se_doc_read_locks: .res 1
se_snapshot_busy: .res 1 ;0 idle,1 full capture,2 selected-range capture

; Shared persistent layout; engine CODE imports this resident frame.
.ifdef ENGINE_CODE
.globalzp emit_ptr
.global se_doc_emit
.global pending
.global emit_root_count
.global emit_total
.global emit_records
.global emit_leaf_sum
.global emit_used
.global emit_slot
.global emit_mask
.global emit_scan
.global emit_end
.else
.segment "ZEROPAGE"
emit_ptr: .res 2
.segment "DOCSTATE"
se_doc_emit: .res 16
pending: .res 16
emit_root_count: .res 1
emit_total: .res 3
emit_records: .res 1
emit_leaf_sum: .res 3
emit_used: .res 8
emit_slot: .res 1
emit_mask: .res 1
emit_scan: .res 1
emit_end: .res 3
.ifdef ENGINE_STATE_ONLY
.exportzp se_engine_emit_emit_ptr
se_engine_emit_emit_ptr = emit_ptr
.export se_engine_emit_se_doc_emit
se_engine_emit_se_doc_emit = se_doc_emit
.export se_engine_emit_pending
se_engine_emit_pending = pending
.export se_engine_emit_emit_root_count
se_engine_emit_emit_root_count = emit_root_count
.export se_engine_emit_emit_total
se_engine_emit_emit_total = emit_total
.export se_engine_emit_emit_records
se_engine_emit_emit_records = emit_records
.export se_engine_emit_emit_leaf_sum
se_engine_emit_emit_leaf_sum = emit_leaf_sum
.export se_engine_emit_emit_used
se_engine_emit_emit_used = emit_used
.export se_engine_emit_emit_slot
se_engine_emit_emit_slot = emit_slot
.export se_engine_emit_emit_mask
se_engine_emit_emit_mask = emit_mask
.export se_engine_emit_emit_scan
se_engine_emit_emit_scan = emit_scan
.export se_engine_emit_emit_end
se_engine_emit_emit_end = emit_end
.endif
.endif

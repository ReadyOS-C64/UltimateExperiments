; Shared persistent layout; engine CODE imports this resident frame.
.ifdef ENGINE_CODE
.global se_doc_edit_position
.global se_doc_edit_delete
.global se_doc_edit_insert
.global tx_position
.global tx_end
.global tx_insert
.global tx_new_length
.global tx_append_start
.global tx_append_end
.global tx_left
.global tx_write
.global tx_inserted
.global tx_old_pos
.global tx_piece_end
.global tx_ref_mode
.global tx_local_mode
.global se_doc_reused_roots
.global feed_amount
.global feed_end
.else
.segment "DOCSTATE"
se_doc_edit_position: .res 3
se_doc_edit_delete: .res 3
se_doc_edit_insert: .res 3
tx_position: .res 3
tx_end: .res 3
tx_insert: .res 3
tx_new_length: .res 3
tx_append_start: .res 3
tx_append_end: .res 3
tx_left: .res 3
tx_write: .res 3
tx_inserted: .res 1
tx_old_pos: .res 3
tx_piece_end: .res 3
tx_ref_mode: .res 1
tx_local_mode: .res 1
se_doc_reused_roots: .res 1
feed_amount: .res 3
feed_end: .res 2
.ifdef ENGINE_STATE_ONLY
.export se_engine_splice_se_doc_edit_position
se_engine_splice_se_doc_edit_position = se_doc_edit_position
.export se_engine_splice_se_doc_edit_delete
se_engine_splice_se_doc_edit_delete = se_doc_edit_delete
.export se_engine_splice_se_doc_edit_insert
se_engine_splice_se_doc_edit_insert = se_doc_edit_insert
.export se_engine_splice_tx_position
se_engine_splice_tx_position = tx_position
.export se_engine_splice_tx_end
se_engine_splice_tx_end = tx_end
.export se_engine_splice_tx_insert
se_engine_splice_tx_insert = tx_insert
.export se_engine_splice_tx_new_length
se_engine_splice_tx_new_length = tx_new_length
.export se_engine_splice_tx_append_start
se_engine_splice_tx_append_start = tx_append_start
.export se_engine_splice_tx_append_end
se_engine_splice_tx_append_end = tx_append_end
.export se_engine_splice_tx_left
se_engine_splice_tx_left = tx_left
.export se_engine_splice_tx_write
se_engine_splice_tx_write = tx_write
.export se_engine_splice_tx_inserted
se_engine_splice_tx_inserted = tx_inserted
.export se_engine_splice_tx_old_pos
se_engine_splice_tx_old_pos = tx_old_pos
.export se_engine_splice_tx_piece_end
se_engine_splice_tx_piece_end = tx_piece_end
.export se_engine_splice_tx_ref_mode
se_engine_splice_tx_ref_mode = tx_ref_mode
.export se_engine_splice_tx_local_mode
se_engine_splice_tx_local_mode = tx_local_mode
.export se_engine_splice_se_doc_reused_roots
se_engine_splice_se_doc_reused_roots = se_doc_reused_roots
.export se_engine_splice_feed_amount
se_engine_splice_feed_amount = feed_amount
.export se_engine_splice_feed_end
se_engine_splice_feed_end = feed_end
.endif
.endif

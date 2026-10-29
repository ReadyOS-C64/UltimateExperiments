; Paged piece table:32 roots,64 records/leaf,16 bytes/record,64 COW leaf slots.
DOC_LEAF = $8400
DOC_BUILD = $8800
DOC_ROOTS = 32
.global se_doc_init, se_doc_adopt_original, se_doc_read, se_doc_validate, se_doc_invalidate
.global se_doc_epoch, se_doc_ready, se_doc_generation, se_doc_length, se_doc_root_count
.global se_doc_roots, se_doc_next_roots, se_doc_meta, se_doc_original, se_doc_append
.global se_doc_source_length, se_doc_offset, se_doc_count, se_doc_c64
.global se_doc_leaf_load, se_doc_walk_reset, se_doc_walk_next, se_doc_walk_piece
.global se_doc_splice_begin, se_doc_splice_feed, se_doc_splice_step, se_doc_splice_cancel
.global se_doc_read_acquire, se_doc_read_release, se_doc_read_locks
.global se_doc_busy, se_doc_edit_position, se_doc_edit_delete, se_doc_edit_insert
.macro DOC_TOKEN source
    ldy #4
:
    lda source,y
    sta se_object_id,y
    dey
    bpl :-
.endmacro

.global se_doc_piece_validate
.global se_snapshot_begin, se_snapshot_step, se_snapshot_cancel, se_snapshot_busy
.global se_snapshot_token, se_snapshot_offset, se_snapshot_pieces, se_snapshot_length, se_snapshot_bytes
.global se_replay_begin, se_replay_step, se_replay_cancel
.global se_replay_token, se_replay_offset, se_replay_pieces, se_replay_length

.global se_doc_splice_refs_begin, se_doc_refs_token, se_doc_refs_offset, se_doc_refs_pieces

.global se_doc_splice_local_begin, se_doc_splice_local_refs_begin
.global se_doc_reused_roots

.global se_doc_read_some, se_doc_read_done

.global se_range_begin, se_range_step, se_range_cancel
.global se_range_token, se_range_offset, se_range_position, se_range_length
.global se_range_pieces, se_range_bytes

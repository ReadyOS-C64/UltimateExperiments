; Persistent selected-range frame: identical resident DOCSTATE order.
.ifdef ENGINE_CODE
.global se_range_token
.global se_range_offset
.global se_range_position
.global se_range_length
.global se_range_pieces
.global se_range_bytes
.global range_token
.global range_out
.global range_pos
.global range_start
.global range_end
.global range_piece_end
.global range_delta
.global range_fragment
.global range_goal
.global range_written
.global range_epoch
.global range_generation
.global range_root_end
.global range_packet
.global range_budget
.global range_done
.global range_error
.global range_store_end
.else
.segment "DOCSTATE"
se_range_token: .res 5
se_range_offset: .res 3
se_range_position: .res 3
se_range_length: .res 3
se_range_pieces: .res 2
se_range_bytes: .res 2
range_token: .res 5
range_out: .res 3
range_pos: .res 3
range_start: .res 3
range_end: .res 3
range_piece_end: .res 3
range_delta: .res 3
range_fragment: .res 3
range_goal: .res 3
range_written: .res 3
range_epoch: .res 2
range_generation: .res 2
range_root_end: .res 3
range_packet: .res 1
range_budget: .res 1
range_done: .res 1
range_error: .res 1
range_store_end: .res 3
.ifdef ENGINE_STATE_ONLY
.export se_engine_range_se_range_token
se_engine_range_se_range_token = se_range_token
.export se_engine_range_se_range_offset
se_engine_range_se_range_offset = se_range_offset
.export se_engine_range_se_range_position
se_engine_range_se_range_position = se_range_position
.export se_engine_range_se_range_length
se_engine_range_se_range_length = se_range_length
.export se_engine_range_se_range_pieces
se_engine_range_se_range_pieces = se_range_pieces
.export se_engine_range_se_range_bytes
se_engine_range_se_range_bytes = se_range_bytes
.export se_engine_range_range_token
se_engine_range_range_token = range_token
.export se_engine_range_range_out
se_engine_range_range_out = range_out
.export se_engine_range_range_pos
se_engine_range_range_pos = range_pos
.export se_engine_range_range_start
se_engine_range_range_start = range_start
.export se_engine_range_range_end
se_engine_range_range_end = range_end
.export se_engine_range_range_piece_end
se_engine_range_range_piece_end = range_piece_end
.export se_engine_range_range_delta
se_engine_range_range_delta = range_delta
.export se_engine_range_range_fragment
se_engine_range_range_fragment = range_fragment
.export se_engine_range_range_goal
se_engine_range_range_goal = range_goal
.export se_engine_range_range_written
se_engine_range_range_written = range_written
.export se_engine_range_range_epoch
se_engine_range_range_epoch = range_epoch
.export se_engine_range_range_generation
se_engine_range_range_generation = range_generation
.export se_engine_range_range_root_end
se_engine_range_range_root_end = range_root_end
.export se_engine_range_range_packet
se_engine_range_range_packet = range_packet
.export se_engine_range_range_budget
se_engine_range_range_budget = range_budget
.export se_engine_range_range_done
se_engine_range_range_done = range_done
.export se_engine_range_range_error
se_engine_range_range_error = range_error
.export se_engine_range_range_store_end
se_engine_range_range_store_end = range_store_end
.endif
.endif

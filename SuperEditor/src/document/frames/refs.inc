; Shared persistent layout; engine CODE imports this resident frame.
.ifdef ENGINE_CODE
.global se_doc_refs_token
.global se_doc_refs_offset
.global se_doc_refs_pieces
.global refs_token
.global refs_origin
.global refs_count
.global refs_pos
.global refs_left
.global refs_sum
.global refs_end
.global refs_bytes
.global refs_packet_pieces
.global refs_packet_offset
.global refs_budget
.global refs_old_piece
.global doc_refs_active
.else
.segment "DOCSTATE"
se_doc_refs_token: .res 5
se_doc_refs_offset: .res 3
se_doc_refs_pieces: .res 2
refs_token: .res 5
refs_origin: .res 3
refs_count: .res 2
refs_pos: .res 3
refs_left: .res 2
refs_sum: .res 3
refs_end: .res 3
refs_bytes: .res 2
refs_packet_pieces: .res 1
refs_packet_offset: .res 1
refs_budget: .res 1
refs_old_piece: .res 16
doc_refs_active: .res 1
.ifdef ENGINE_STATE_ONLY
.export se_engine_refs_se_doc_refs_token
se_engine_refs_se_doc_refs_token = se_doc_refs_token
.export se_engine_refs_se_doc_refs_offset
se_engine_refs_se_doc_refs_offset = se_doc_refs_offset
.export se_engine_refs_se_doc_refs_pieces
se_engine_refs_se_doc_refs_pieces = se_doc_refs_pieces
.export se_engine_refs_refs_token
se_engine_refs_refs_token = refs_token
.export se_engine_refs_refs_origin
se_engine_refs_refs_origin = refs_origin
.export se_engine_refs_refs_count
se_engine_refs_refs_count = refs_count
.export se_engine_refs_refs_pos
se_engine_refs_refs_pos = refs_pos
.export se_engine_refs_refs_left
se_engine_refs_refs_left = refs_left
.export se_engine_refs_refs_sum
se_engine_refs_refs_sum = refs_sum
.export se_engine_refs_refs_end
se_engine_refs_refs_end = refs_end
.export se_engine_refs_refs_bytes
se_engine_refs_refs_bytes = refs_bytes
.export se_engine_refs_refs_packet_pieces
se_engine_refs_refs_packet_pieces = refs_packet_pieces
.export se_engine_refs_refs_packet_offset
se_engine_refs_refs_packet_offset = refs_packet_offset
.export se_engine_refs_refs_budget
se_engine_refs_refs_budget = refs_budget
.export se_engine_refs_refs_old_piece
se_engine_refs_refs_old_piece = refs_old_piece
.export se_engine_refs_doc_refs_active
se_engine_refs_doc_refs_active = doc_refs_active
.endif
.endif

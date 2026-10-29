; Shared persistent layout; engine CODE imports this resident frame.
.ifdef ENGINE_CODE
.global build_budget
.global fragment_delta
.global fragment_length
.global ref_resume
.else
.segment "DOCSTATE"
build_budget: .res 1
fragment_delta: .res 3
fragment_length: .res 3
ref_resume: .res 1
.ifdef ENGINE_STATE_ONLY
.export se_engine_splice_build_build_budget
se_engine_splice_build_build_budget = build_budget
.export se_engine_splice_build_fragment_delta
se_engine_splice_build_fragment_delta = fragment_delta
.export se_engine_splice_build_fragment_length
se_engine_splice_build_fragment_length = fragment_length
.export se_engine_splice_build_ref_resume
se_engine_splice_build_ref_resume = ref_resume
.endif
.endif

; Shared persistent layout; engine CODE imports this resident frame.
.ifdef ENGINE_CODE
.global local_end
.global local_root
.else
.segment "DOCSTATE"
local_end: .res 3
local_root: .res 1
.ifdef ENGINE_STATE_ONLY
.export se_engine_local_local_end
se_engine_local_local_end = local_end
.export se_engine_local_local_root
se_engine_local_local_root = local_root
.endif
.endif

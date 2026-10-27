.ifndef SE_STYLE_API
SE_STYLE_API=1
STYLE_ID=14
ST_BEGIN=0
ST_STEP=1
ST_CANCEL=2
ST_VERSION=1
ST_PENDING=2
ST_STALE=$B8
ST_BUSY=$B9
ST_ARGUMENT=$BA
STYLE_PLAN=$4400
STYLE_CELLS=880
STYLE_ROWS=22
STYLE_KEY_BYTES=33
; descriptor: meta/original/append tokens15, generation2, revision4,
; merged length3, top3, pan3, provider epoch2, layout mode1.
; Production grid byte32: (se_mode*2)|nowrap; legacy isolated planner:0/1.
ST_KEY_LENGTH=21
ST_KEY_TOP=24
ST_KEY_PAN=27
ST_KEY_EPOCH=30
ST_KEY_MODE=32
STYLE_DESC_BYTES=37
.global se_style_begin,se_style_step,se_style_cancel
.global se_st_key,se_st_rows,se_st_busy,se_st_error,se_st_state,se_st_state_size
.global se_st_descriptor,se_st_generation,se_st_valid,se_st_request
.global se_st_cache_generation,se_st_cache_valid
.global se_st_cp_valid,se_st_cp_rows,se_st_cp_anchor,se_st_cp_count
.endif

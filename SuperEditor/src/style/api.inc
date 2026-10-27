.ifndef SE_STYLE_API
SE_STYLE_API=1
STYLE_ID=14
ST_BEGIN=0
ST_STEP=1
ST_CANCEL=2
ST_VERSION=1
ST_PENDING=2
ST_RETRY=$7D
ST_STALE=$B8
ST_BUSY=$B9
ST_ARGUMENT=$BA
STYLE_PLAN=$4400
STYLE_CELLS=880
STYLE_ROWS=22
STYLE_CARRY_BYTES=5
STYLE_CARRY_TABLE_BYTES=STYLE_ROWS*STYLE_CARRY_BYTES
STYLE_CARRY_FENCE_MASK=$0F
STYLE_CARRY_LANGUAGE_MASK=$30
STYLE_CARRY_LANGUAGE_SHIFT=4
STYLE_CARRY_START=$80
; Persistent styled-row handoff in the fixed $4770 checkpoint window.
; Writers store the body/checksum first and phase last; consumers authenticate
; CHECK = $A7 xor PHASE xor every byte from START through DOC_EPOCH+1.
; Phase values are 0 invalid, $A5 admitted, and $5A ready for C33.
ST_TX_PHASE=0
ST_TX_CHECK=1
ST_TX_START=2
ST_TX_END=5
ST_TX_ROW_MODE=8
ST_TX_COUNT_KIND=9
ST_TX_SEQUENCE=10
ST_TX_REVISION=12
ST_TX_DOC_GENERATION=16
ST_TX_DOC_EPOCH=18
ST_TX_BYTES=20
ST_TX_ROW_MASK=$1F
ST_TX_MODE_MASK=$E0
ST_TX_DELETE=$20
ST_TX_COUNT_MASK=$1F
ST_TX_CHECK_SEED=$A7
ST_TX_INVALID=0
ST_TX_ADMITTED=$A5
ST_TX_READY=$5A
ST_TX_WAIT=$7E
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
.global se_st_cp_valid,se_st_cp_rows,se_st_cp_anchor,se_st_cp_count,se_st_cp_crc
.global se_st_tx
.endif

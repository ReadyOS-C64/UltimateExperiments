; Existing parser layouts, aliased only after a completed block's carry/ranges
; have been retained. No persistent state or new ZP allocation.
.include "cache/semantic/api.inc"
.segment "BSC_PARSER"
.export se_sm_state,se_sm_state_size,sm_begin,sm_end
se_sm_state:
sm_begin:
.export se_sm_pos,se_sm_ready,se_sm_kind,se_sm_start,se_sm_end,se_sm_body
.export se_sm_level,se_sm_language,se_sm_fence,se_sm_regions,se_sm_marker,se_sm_end_state
.export sm_line,sm_length,sm_used,sm_prefix,sm_colons,sm_index,sm_word,sm_word_len
.export sm_byte,sm_list_state,sm_indent,sm_list_body,sm_region_overflow
se_sm_pos:.res 3
se_sm_ready:.res 1
se_sm_kind:.res 1
se_sm_start:.res 3
se_sm_end:.res 3
se_sm_body:.res 3
se_sm_level:.res 1
se_sm_language:.res 1
se_sm_fence:.res 1
se_sm_regions:.res 1
se_sm_marker:.res 1
se_sm_end_state:.res 1
sm_line:.res 3
sm_length:.res 3
sm_used:.res 1
sm_prefix:.res 32
sm_colons:.res 1
sm_index:.res 1
sm_word:.res 8
sm_word_len:.res 1
sm_byte:.res 1
sm_list_state:.res 1
sm_indent:.res 1
sm_list_body:.res 3
sm_region_overflow:.res 3
sm_end:
se_sm_state_size=sm_end-sm_begin
.assert se_sm_state_size=79,error,"block parser layout changed"
.assert se_sm_state=BSC_PARSER,lderror,"semantic parser frame moved"
.macro ALIAS symbol,offset
 .export symbol
 symbol=se_sm_state+offset
.endmacro
ALIAS se_si_state,0
se_si_state_size=68
.export se_si_state_size
ALIAS si_begin,0
ALIAS si_end,68
ALIAS se_si_pos,0
ALIAS se_si_ready,3
ALIAS se_si_kind,4
ALIAS se_si_style,5
ALIAS se_si_width,6
ALIAS se_si_open,7
ALIAS se_si_close,10
ALIAS se_si_depth,13
ALIAS si_stack,14
ALIAS si_run,46
ALIAS si_run_len,47
ALIAS si_run_pos,48
ALIAS si_code,51
ALIAS si_code_pos,52
ALIAS si_pound,55
ALIAS si_pound_context,56
ALIAS si_escape,57
ALIAS si_escape_count,58
ALIAS si_pound_pos,59
ALIAS si_leading,62
ALIAS si_indent,63
ALIAS si_column,64
ALIAS si_byte,67

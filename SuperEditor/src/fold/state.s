.setcpu "6502"
.include "fold/api.inc"
.segment "FOLD_STATE"
se_fold_state:
se_fold_token: .res 5
se_fold_count: .res 2
se_fold_length: .res 3
se_fold_epoch: .res 4
se_fold_stamp: .res 4
se_fold_bound_token:.res 5
se_fold_bound_count:.res 2
se_fold_bound_length:.res 3
se_fold_valid: .res 1
se_fold_busy: .res 1
se_fold_error: .res 1
se_fold_job: .res 1
se_fold_index: .res 2
se_fold_caret: .res 3
se_fold_motion: .res 4
se_fold_select_a: .res 3
se_fold_select_b: .res 3
se_fold_query: .res 3
se_fold_mode: .res 1
se_fold_result: .res 3
se_fold_hidden: .res 1
se_fold_selected: .res 1
se_fold_target: .res 2
se_fold_action: .res 1
se_fold_next: .res 3
se_fold_last: .res 3
se_fold_depth: .res 1
se_fold_temp: .res 3
se_fold_stack_end: .res 48
se_fold_stack_hidden: .res 48
se_fold_stack_index: .res 32
se_fold_state_size=*-se_fold_state
.segment "FOLD_BUFFER"
se_fold_record: .res SF_RECORD_SIZE

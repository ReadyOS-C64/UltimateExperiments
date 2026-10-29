.setcpu "6502"
.export se_f_preflight_phase,se_f_preflight_result,se_f_preflight_track,se_f_preflight_sector,se_f_preflight_link,se_f_preflight_remaining,se_f_preflight_index,se_f_preflight_entry,se_f_preflight_value,se_f_preflight_error,se_f_preflight_length,se_f_preflight_blocks
.export se_f_preflight_kind
.segment "FILESTATE"
se_f_preflight_phase: .res 1 ;0idle,1header,2directory,3firstfileblock
se_f_preflight_result: .res 1 ;0nonempty,1empty; meaningful only afterA0 completion
se_f_preflight_track: .res 1
se_f_preflight_sector: .res 1
se_f_preflight_link: .res 2
se_f_preflight_remaining: .res 1
se_f_preflight_index: .res 1
se_f_preflight_entry: .res 1
se_f_preflight_value: .res 1
se_f_preflight_error: .res 1
se_f_preflight_length: .res 3
se_f_preflight_blocks: .res 2
se_f_preflight_kind: .res 1 ;0closed-SEQ chain,1any non-DEL candidate occupancy

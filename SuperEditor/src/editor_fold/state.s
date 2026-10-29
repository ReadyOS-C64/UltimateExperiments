.setcpu "6502"
SE_EDITOR_FOLD_IMPLEMENTATION=1
.include "editor_fold/api.inc"
.export se_ef_state,se_ef_token,se_ef_count,se_ef_key,se_ef_valid,se_ef_motion
.export se_ef_capacity_banks,se_ef_generation,se_ef_active,se_ef_operation
.export se_ef_paint_ends,se_ef_fold_rows,se_ef_state_end
.segment "BSS"
; Phase-independent, readable while FileUI owner1 owns $8D00..$917F.
se_ef_state:
se_ef_token: .res 5
se_ef_count: .res 2
se_ef_key: .res EF_KEY_SIZE
se_ef_valid: .res 1
se_ef_motion: .res 4
se_ef_capacity_banks: .res 1
se_ef_generation: .res 2
se_ef_active: .res 1
se_ef_operation: .res 1
.assert *-se_ef_state=EF_DESCRIPTOR_SIZE,error,"fold descriptor must be45B"
; Canonical row starts/bottom stay in existing VIEW. Each paint end is normal
; next anchor, or collapsed opener's HIDDEN boundary. Coordinator publishes.
se_ef_paint_ends: .res 66
se_ef_fold_rows: .res 3
se_ef_state_end:
.assert se_ef_state_end-se_ef_state=EF_STATE_SIZE,error,"fold state must be114B"

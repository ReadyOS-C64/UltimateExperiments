.setcpu "6502"
; Explicit aliases into the phase union, not BSS allocations. Link this object
; resident for emergency/dispatch and independently intoC19. Owner3 gates all
; accesses; C17/18foundation/state ends at8FD6. File/style/index use sameunion.
.export se_ec_state,se_ec_phase,se_ec_action,se_ec_candidate,se_ec_allocated
.export se_ec_result,se_ec_carry,se_ec_error,se_ec_banks,se_ec_reuse,se_ec_moved
.export se_ec_state_end
se_ec_state=$8FD6
se_ec_phase=se_ec_state
se_ec_action=se_ec_state+1
se_ec_candidate=se_ec_state+2
se_ec_allocated=se_ec_state+7
se_ec_result=se_ec_state+8
se_ec_carry=se_ec_state+9
se_ec_error=se_ec_state+10
se_ec_banks=se_ec_state+11
se_ec_reuse=se_ec_state+12
se_ec_moved=se_ec_state+13
se_ec_state_end=se_ec_state+14
.assert se_ec_state_end <= $9180,error,"fold controller escapesphaseunion"

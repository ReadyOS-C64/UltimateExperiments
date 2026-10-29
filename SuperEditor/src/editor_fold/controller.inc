.ifndef SE_EDITOR_FOLD_CONTROLLER
SE_EDITOR_FOLD_CONTROLLER=1
.include "editor_fold/api.inc"
EF_CONTROL_ID=19
EF_BEGIN=0
EF_STEP=1
EF_CANCEL=2
; BEGIN frame+1: toggle0,collapse1,expand2,collapseall3,expandall4,reveal5.
; Root owns job10. C19 returnsA1pending/A0done,Cseterror. A pending request
; active17/18 +operation0/1 is executed by root sequentially AFTER C19returns,
; never nested. Root stores returnedA in se_ec_result, carryboolean in
; se_ec_carry, resetsactive19; nextC19STEPconsumesit. Cancel calls C19op2.
; Successfuldone writes existingse_e_target (actualactioncaret or initialcaret).
; Root consumes that target before anotherphaseclaim and uses existingreload;
; controlledcollapse/restore must not increment ordinarymotionserial.
; Phase aliases8FD6..8FE3, no additive residentBSS. Only owner3 may inspectthem.
EC_BUILD=1
EC_LOCATE=2
EC_ACTION=3
.global se_ec_state,se_ec_phase,se_ec_action,se_ec_candidate,se_ec_allocated
.global se_ec_result,se_ec_carry,se_ec_error,se_ec_banks,se_ec_reuse,se_ec_moved
.global se_ec_state_end
.ifndef EF_CONTROLLER_IMPLEMENTATION
.global se_ef_begin,se_ef_step,se_ef_cancel,se_ef_emergency
.endif
.endif

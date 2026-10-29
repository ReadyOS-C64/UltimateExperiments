.setcpu "6502"
.include "fold/source.inc"
.segment "FOLD_SOURCE_STATE"
se_fs_state:
se_fs_offset:.res 3
se_fs_count:.res 1
se_fs_buffer:.res 2
se_fs_done:.res 1
se_fs_active:.res 1
se_fs_owned:.res 1
se_fs_error:.res 1
se_fs_length:.res 3
se_fs_revision:.res 4
se_fs_hot_end:.res 3
se_fs_temp:.res 3
se_fs_output:.res 2
se_fs_phys:.res 2
se_fs_identity:.res 59
se_fs_identity_size=59
se_fs_state_size=*-se_fs_state

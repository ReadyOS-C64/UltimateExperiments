.setcpu "6502"
.import dos64_files_state_start,dos64_files_state_end,dos64_files_handle
.export _bc_files := dos64_files_state_start
.assert dos64_files_state_end-dos64_files_state_start=25,lderror,"FILES snapshot ABI changed"
.assert dos64_files_handle-dos64_files_state_start=15,lderror,"FILES handle snapshot offset changed"

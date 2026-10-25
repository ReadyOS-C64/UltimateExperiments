.setcpu "6502"
.export se_fd_confirm,se_fd_list_count,se_fd_list_index,se_fd_list_names
.export se_fd_list_lengths,se_fd_page,se_fd_list_error,se_fd_resume
.export se_fd_open_name,se_fd_open_len,se_fd_open_device,se_fd_task,se_fd_skip
.export se_fd_index,se_fd_command
.segment "FILESTATE"
se_fd_confirm: .res 1
se_fd_list_count: .res 1
se_fd_list_index: .res 1
se_fd_list_names: .res 128
se_fd_list_lengths: .res 8
se_fd_page: .res 2
se_fd_list_error: .res 1
se_fd_resume: .res 1
se_fd_open_name: .res 16
se_fd_open_len: .res 1
se_fd_open_device: .res 1
se_fd_task: .res 1 ;0modal/operation,1directory-open,2directory-next,3directory-close
se_fd_skip: .res 2
se_fd_index: .res 1
se_fd_command: .res 1

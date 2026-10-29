.setcpu "6502"
.export se_io_device, se_io_name, se_io_name_len, se_io_other, se_io_other_len
.export se_io_raw_status, se_io_dos_code, se_io_status_text, se_io_mode
.export se_io_count, se_io_done, se_io_eof, se_io_owned_temp, se_io_owned_backup
.export se_io_dir_name, se_io_dir_len, se_io_dir_blocks, se_io_dir_flags
.export fio_error, fio_value, fio_index, fio_command, fio_command_len
.export fio_line, fio_line_len
.export se_io_temp_name, se_io_temp_len, se_io_backup_name, se_io_backup_len
.export se_io_wrote
.ifdef SE_FILE_UNION
.segment "FILESTATE"
.else
.segment "BSS"
.endif
se_io_device: .res 1
se_io_name: .res 16
se_io_name_len: .res 1
se_io_other: .res 16
se_io_other_len: .res 1
se_io_raw_status: .res 1
se_io_dos_code: .res 1
se_io_status_text: .res 40 ; DOS response, CR omitted; length below
se_io_mode: .res 1 ; 0 idle,1 read,2 write,3 directory
se_io_count: .res 1 ; requested bytes 1..255;0 means256
se_io_done: .res 2 ; transferred bytes, including final EOI byte
se_io_eof: .res 1
se_io_wrote: .res 1
; These are capabilities, not arbitrary filename matching. Command module
; creates them after a successful create/rename, and consumes on scratch/rename.
se_io_owned_temp: .res 1
se_io_owned_backup: .res 1
se_io_temp_name: .res 16
se_io_temp_len: .res 1
se_io_backup_name: .res 16
se_io_backup_len: .res 1
se_io_dir_name: .res 16
se_io_dir_len: .res 1
se_io_dir_blocks: .res 2
se_io_dir_flags: .res 1 ; bit0 splat,bit1 locked
fio_error: .res 1
fio_value: .res 1
fio_index: .res 1
fio_command: .res 38 ; R0:dest=source, or0:name,S,W
fio_command_len: .res 1
fio_line: .res 82 ; directory listing BASIC line, bounded
fio_line_len: .res 1

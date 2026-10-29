.ifndef SE_FILEIO_API
SE_FILEIO_API = 1
; Foreground, non-reentrant IEC provider; every entry clobbers A/X/Y/P.
; No IRQ, NMI, overlay loader or second filesystem consumer may enter concurrently.
; Carry clear/A=0 success. Errors below preserve raw READST and DOS status.
FIO_ARGUMENT = $90
FIO_BUSY = $91
FIO_IO = $92
FIO_DOS = $93
FIO_FORMAT = $94
FIO_LIMIT = $95
FIO_OWNERSHIP = $96
FIO_STATE = $97
FIO_EMPTY = $98 ; unproven zero-byte SEQ close is refused; discard owned temp
FIO_BUFFER = $8000
FIO_DATA_LFN = 5
FIO_COMMAND_LFN = 6
.global se_io_device, se_io_name, se_io_name_len, se_io_other, se_io_other_len
.global se_io_raw_status, se_io_dos_code, se_io_status_text, se_io_mode
.global se_io_count, se_io_done, se_io_eof, se_io_owned_temp, se_io_owned_backup
.global se_io_init, se_io_validate, se_io_open_read, se_io_create_write
.global se_io_read_chunk, se_io_write_chunk, se_io_close, se_io_abort
.global se_io_status, se_io_rename, se_io_scratch_owned
.global se_io_create_temp, se_io_make_backup
.global se_io_temp_name, se_io_temp_len, se_io_backup_name, se_io_backup_len
.global se_io_wrote
.global se_io_directory_open, se_io_directory_next
.global se_io_dir_name, se_io_dir_len, se_io_dir_blocks, se_io_dir_flags
.endif

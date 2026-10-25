; Diagnostic snapshot ABI1. Caller owns128 bytes in8800–8BFF until cancel/done.
DIAG_BYTES=128
D_BEGIN=1
D_STEP=2
D_CANCEL=3
D_STATE=$78
D_CHANGED=$79
D_BUFFER=$7A
D_SHAPE=$7B
.global se_diag_begin,se_diag_step,se_diag_cancel
.global se_diag_call
.global se_diag_buffer,se_diag_cursor,se_diag_active,se_diag_owned,se_diag_epoch
.global se_diag_output,se_diag_crc,se_diag_pos,se_diag_length,se_diag_hot_end
.global se_diag_temp,se_diag_count,se_diag_error,se_diag_frame_start,se_diag_frame_end
; Snapshot offsets. Multibyte integers little endian; positions24-bit.
DS_ABI=4
DS_SIZE=5
DS_STATUS=6 ;1 scanning,2 complete,3 cancelled,4 failed;CRC valid only2
DS_HASH_TYPE=7 ;1 CRC16/CCITT-FALSE:poly1021/initFFFF/refin0/refout0/xorout0
DS_LENGTH=8
DS_GENERATION=11
DS_CURSOR=13 ;caller-supplied visible caret frozen at BEGIN
DS_PENDING=16
DS_DIRTY=17 ;history dirty OR pending
DS_HISTORY_DIRTY=18
DS_HOT_READY=19
DS_EPOCH=20
DS_CRC=22
DS_SCANNED=24
DS_ERROR=27
DS_LOADS=28 ;telemetry frozen at BEGIN, modulo16bit
DS_HITS=30
DS_CALLS=32
DS_MAP=34 ;three live256-byte arrays;valid only for DS_EPOCH
DS_LOGICAL_OWNERS=36
DS_PHYSICAL_OWNERS=38
DS_ALLOCATED=40 ;logical owner1..254,includes control
DS_FREE=42 ;physical owner0,excludes unavailable255
DS_BANKS=44
DS_RETIRED=46
DS_HOT_PHASE=47
DS_ORIGINAL=48
DS_APPEND=53
DS_META=58
DS_COMMITTED_LENGTH=63
DS_HOT_BASE=66
DS_HOT_OLD_LENGTH=69
DS_HOT_LENGTH=71
DS_HOT_LEFT=73
DS_HOT_RIGHT=75
DS_HOT_GENERATION=77
DS_HOT_ORIGINAL=79
DS_HOT_APPEND=84
DS_REVISION=89
DS_READ_LOCKS=93 ;at BEGIN,includes this diagnostic's lease

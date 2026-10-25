; RAM edit window ABI1. Logical positions are24-bit; gap offsets16-bit.
HOT_FIRST=$9200
HOT_END=$9A00
HOT_BYTES=2048
HOT_ID=6
W_LOAD=1
W_STEP=2
W_INSERT=3
W_BACK=4
W_DELETE=5
W_LEFT=6
W_RIGHT=7
W_FLUSH=8
W_CANCEL=9
W_CLOSE=10
W_PREPARE=$80
W_PACKET=$81
W_COMMIT=$82
.global se_hot_cold,se_hot_call
.global se_hot_ready,se_hot_phase,se_hot_pending,se_hot_fault,se_hot_owned
.global se_hot_original,se_hot_append,se_hot_generation,se_hot_epoch
.global se_hot_position,se_hot_base,se_hot_caret,se_hot_before,se_hot_group,se_hot_byte
.global se_hot_old_length,se_hot_length,se_hot_left,se_hot_right
.global se_hot_prefix,se_hot_suffix,se_hot_loaded,se_hot_target,se_hot_feed,se_hot_feed_left
.global se_hot_tmp,se_hot_count,se_hot_delete,se_hot_command
.globalzp se_hot_ptr,se_hot_packet

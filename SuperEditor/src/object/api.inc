; Internal object service linkage. Tokens: ID + generation16 + provider epoch16.
OBJECT_LIMIT = 8
OBJECT_EXTENTS = 16
.global se_object_init, se_object_create, se_object_release, se_object_resize
.global se_object_copy, object_service_valid, se_object_validate
.global se_object_id, se_object_generation, se_object_token_epoch
.global se_object_offset, se_object_length, se_object_c64, se_object_epoch
.global object_owner, object_gen_lo, object_gen_hi, object_size_lo, object_size_mid, object_size_hi
.global object_banks, object_extents

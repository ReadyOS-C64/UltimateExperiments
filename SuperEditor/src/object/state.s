.setcpu "6502"
.include "object/api.inc"
.segment "BSS"
; Cleared by cold entry. Remains valid only for this provider epoch.
se_object_epoch: .res 2
.segment "OBJECTS"
; Dedicated protected working set at9E00; never a DMA client buffer.
object_owner: .res OBJECT_LIMIT
object_gen_lo: .res OBJECT_LIMIT
object_gen_hi: .res OBJECT_LIMIT
object_size_lo: .res OBJECT_LIMIT
object_size_mid: .res OBJECT_LIMIT
object_size_hi: .res OBJECT_LIMIT
object_banks: .res OBJECT_LIMIT
object_extents: .res OBJECT_LIMIT*OBJECT_EXTENTS
; Public foreground request. Copy/resize/release leave the token unchanged.
se_object_id: .res 1
se_object_generation: .res 2
se_object_token_epoch: .res 2
se_object_offset: .res 3
se_object_length: .res 2
se_object_c64: .res 2

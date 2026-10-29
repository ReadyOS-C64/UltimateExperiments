; SEO2 sidecar, byte-order little endian. Fixed link addresses, relocatable REU.
OVL_HEADER = 36
OVL_BINDING_BYTES = 16
.ifndef OVL_LIMIT
OVL_LIMIT = 15
.endif
.ifndef EDITOR_CATALOG_TAIL
EDITOR_CATALOG_TAIL = 0
.endif
.ifndef EDITOR_FIXED_ENTRY
EDITOR_FIXED_ENTRY = 0
.endif
.assert OVL_LIMIT > 0,error,"overlay catalog must have entries"
.if EDITOR_CATALOG_TAIL
.if EDITOR_FIXED_ENTRY
.assert OVL_LIMIT <= 64,error,"fixed-entry catalog exceeds four logical asset banks"
.else
.assert OVL_LIMIT <= 24,error,"tail catalog exceeds its192-byte workspace"
.endif
.else
.assert OVL_LIMIT <= 16,error,"overlay catalog exceeds its logical 64KiB asset bank"
.endif
; Staging remains a full4KiB non-executable bounce. The editor catalog lives
; separately atCA00..CB7F; runtime CRC must not clobber either executable slot.
OVL_STAGE = $5000
OVL_OWNER = 2
; header: magic[4], ABI, slot, ID, reserved, length[2], entry[2], CRC16[2],
; headerCRC16[2], resident call address[2], resident frame address[2], complete resident binding digest[16]

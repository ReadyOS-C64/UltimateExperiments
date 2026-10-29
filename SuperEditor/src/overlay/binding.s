.setcpu "6502"
.export se_overlay_binding_digest
.segment "RODATA"
; Fixed-size post-link seal. tools/bindings.py hashes the complete normalized
; PRG plus link symbols, then stamps these bytes without moving any address.
se_overlay_binding_digest: .res 16,0

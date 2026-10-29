; Private replacement of retired R33. One source-matched bounded current-BODY presentation plan.
; No persistent CR/root/index. C20/C26 caller supplies freshly checked GS_FS59.
.include "render/geos/semantic.inc"
.include "render/geos/source-line.inc"
.include "render/geos/source-certificate.inc"
.include "render/geos/inline.inc"
.import se_bc_ring,se_bc_arena,se_f_owner,se_render_caps,se_r_presentation
.import se_crc_init,se_crc_byte,se_crc_value
VP=se_bc_ring
VP_VALID=VP
VP_KEY=VP+1                  ;59B reserved; first29 are logical source identity
VP_ORIGIN=VP+60              ;canonical24 current inline window start
VP_LIMIT=VP+63               ;exclusive canonical bound (<=4096 entries)
VP_BODY=VP+66
VP_END=VP+69
VP_BASE=VP+72
VP_CAPS=VP+73
VP_BLOCK=VP+74
VP_INDEX=VP+75
VP_OUTPUT=VP+76
VP_COUNT=VP+77
VP_BITS=VP+78
VP_DELTA=VP+79               ;3B current source delta
VP_STOP=VP+82                ;3B clipped event end delta
VP_MODE=VP+85
VP_AMOUNT=VP+86
VP_IO=$8880                  ;34B dead R21 context while C20/C26 owns phase
VP_START=VP+88               ;canonical logical start, exact C24 context
VP_FRAME=VP+87               ;1B original opcode
.assert 91<=96,error,"viewport plan exceeds retired ring"
; Packed entries: style0..1, role2..5, hidden6, exclusive code7.
;128 records of32 entries+CRC16 =4352 bytes, in one actually allocated type53.

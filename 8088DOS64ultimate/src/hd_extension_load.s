.setcpu "6502"
.macpack longbranch
.import __HDBIOS_SIZE__,hdb_startup,dos64_cold_open
.export hdb_load_extension,hdb_extension_ready
.segment "NATIVESTATE"
hdb_extension_ready: .byte 0
.segment "COLDINIT"
hdb_load_extension:
 lda dos64_cold_open
 cmp #$a5
 bne hdb_load_fail
 lda $01
 and #7
 cmp #5
 bne hdb_load_fail
 lda #$a0
 sta copy_source+2
 sta verify_source+2
 lda #$f0
 sta copy_target+2
 sta verify_target+2
 ldy #14
 ldx #0
copy_source:
 lda $a000,x
copy_target:
 sta $f000,x
 inx
 bne copy_source
 inc copy_source+2
 inc copy_target+2
 dey
 bne copy_source
 ldy #14
verify_source:
 lda $a000,x
verify_target:
 cmp $f000,x
 bne hdb_load_fail
 inx
 bne verify_source
 inc verify_source+2
 inc verify_target+2
 dey
 bne verify_source
 jsr hdb_startup
 lda #$a5
 sta hdb_extension_ready
 clc
 rts
hdb_load_fail:
 sec
 rts
.assert __HDBIOS_SIZE__ <= $e00,lderror,"HD shadow exceeds exclusive allocation"

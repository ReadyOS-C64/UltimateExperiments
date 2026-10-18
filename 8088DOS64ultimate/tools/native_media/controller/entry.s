.setcpu "6502"
.macpack longbranch
.include "native.inc"
.importzp sp
.import zerobss,_ac_body,_ac_request
.export _ac_entry,ac_entry,ac_active,ac_native_high,ac_ledger
ac_native_high=$9d80
ac_ledger=$7f00
.export _ac_ledger:=ac_ledger
.segment "LOADADDR"
.word $8000
.segment "DATA"
ac_active:.byte 0
.segment "CODE"
_ac_entry:
ac_entry:
 php
 sei
 cld
 lda ac_active
 jne rejected
 lda $00
 and #7
 cmp #7
 jne rejected
 lda $01
 and #7
 cmp #5
 jne rejected
 lda modal_owned
 cmp #$a5
 jne rejected
 lda modal_context
 cmp #1
 jne rejected
 lda dos64_native_diag
 cmp #8
 jne rejected
 lda dos64_cache_limit
 ora dos64_cold_open
 ora sav_borrowed
 ora sav_context_pending
 ora dos64_overlay_busy
 ora hdb_active
 ora hd_uncertain
 jne rejected
 lda _ac_request
 cmp #$a5
 jne rejected
 lda _ac_request+1
 cmp #2
 jcs rejected
 lda _ac_request+2
 ora _ac_request+3
 jeq rejected
 lda #1
 sta ac_active
 ldx #95
: lda $80,x
 sta ac_native_high,x
 lda #0
 sta $80,x
 dex
 bpl :-
 lda #$ff
 sta sp
 lda #$9f
 sta sp+1
 jsr zerobss
 jsr _ac_body
 pha
 ldx #95
: lda ac_native_high,x
 sta $80,x
 dex
 bpl :-
 lda #0
 sta ac_active
 pla
 ldx #0
 plp
 rts
rejected:
 lda #0
 ldx #0
 plp
 rts

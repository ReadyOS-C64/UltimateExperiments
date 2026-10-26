.setcpu "6502"
.macpack longbranch
.include "cache/query/api.inc"
.include "cache/arena/api.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.import bq_pending,bq_corrupt,bq_fail,bq_done
.import payload_offset
.export read_record
.macro CP source,target,count
 ldy #count-1
:
 lda source,y
 sta target,y
 dey
 bpl :-
.endmacro
; Unsigned compare24, C/Z reflects high-to-low comparison. A/X dead.
.macro CMP24 source,target
 ldx #2
:
 lda source,x
 cmp target,x
 bne :+
 dex
 bpl :-
 lda #0
:
.endmacro
.macro ADD24 source,offset,target
 clc
 lda source
 adc offset
 sta target
 lda source+1
 adc offset+1
 sta target+1
 lda source+2
 adc offset+2
 sta target+2
 jcs bq_corrupt
.endmacro
.segment "CODE"
read_record:
 jsr payload_offset
 jcs bq_fail
.ifndef BCQ_CLASSIFY
 lda BQ_CLASS
 cmp #2
 jeq event
.endif
 CP BC_IO,BQ_CR,96
 lda BQ_CR
 cmp #1
 jne bq_corrupt
 lda BQ_CR+1
 cmp #1
 jne bq_corrupt
 jsr se_crc_init
 ldy #1
@crc:cpy #74
 bne :+
 ldy #76
:
 lda BQ_CR,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @crc
 lda se_crc_value
 cmp BQ_CR+74
 jne bq_corrupt
 lda se_crc_value+1
 cmp BQ_CR+75
 jne bq_corrupt
 lda BQ_CR+2
 and #$F0
 jne bq_corrupt              ; no lexical certificate in firstbaseline
 lda BQ_CR+3
 cmp #9
 bcc @ordinary_kind
 cmp #$FF
 jne bq_corrupt
 lda BQ_CR+2
 cmp #10
 jne bq_corrupt
 jmp @kind
@ordinary_kind:
 lda BQ_CR+2
 and #8
 jne bq_corrupt
@kind:
 lda BQ_CR+69
 cmp #3
 jcs bq_corrupt
 lda BQ_CR+3
 cmp #2
 bne @level_ok
 lda BQ_CR+70
 jeq bq_corrupt
 cmp #7
 jcs bq_corrupt
@level_ok:
.ifndef BCQ_PAGE_REUSE
 lda BQ_CR+3
 cmp #4
 bcs @no_inline
 lda BQ_CR+2
 and #4
 jeq bq_corrupt
 jmp @inline_flag
@no_inline:
 lda BQ_CR+2
 and #4
 jne bq_corrupt
 lda BQ_CR+44
 ora BQ_CR+45
 ora BQ_CR+46
 jne bq_corrupt
@inline_flag:
.endif
 ; ABI/proof/source ticket and all reserved bytes are semantic authority.
 lda BQ_CR+58
 cmp #1
 jne bq_corrupt
 lda BQ_CR+63
 cmp #1
 jne bq_corrupt
 lda BQ_CR+65
 cmp #1
 jne bq_corrupt
 lda BQ_CR+67
 cmp #1
 jne bq_corrupt
 lda BQ_CR+64
 ora BQ_CR+66
 ora BQ_CR+68
 ora BQ_CR+92
 ora BQ_CR+93
 ora BQ_CR+94
 ora BQ_CR+95
 jne bq_corrupt
 ldy #3
@ticket:lda BQ_CR+12,y
 cmp BQ_AUTH+5,y
 jne bq_corrupt
 lda BQ_CR+59,y
 cmp BQ_AUTH+5,y
 jne bq_corrupt
 dey
 bpl @ticket
 CMP24 BQ_CR+16,BQ_EXPECT
 jne bq_corrupt
 CMP24 BQ_CR+22,BQ_CR+19
 jcc @body_ok
 jne bq_corrupt
@body_ok:
 ADD24 BQ_CR+16,BQ_CR+19,BQ_END
 CMP24 BQ_END,BQ_LENGTH
 jcc @range_ok
 jne bq_corrupt
@range_ok:
 ADD24 BQ_CR+16,BQ_CR+25,BQ_NEXT
 ; NEXT is END+1 forCR, END forEOF. Exactly one ofCR/EOF is required.
 lda BQ_CR+2
 and #3
 cmp #1
 beq @cr
 cmp #2
 jne bq_corrupt
 CMP24 BQ_NEXT,BQ_END
 jne bq_corrupt
 CMP24 BQ_END,BQ_LENGTH
 jne bq_corrupt
 jmp @membership
@cr:
 inc BQ_END
 bne :+
 inc BQ_END+1
 bne :+
 inc BQ_END+2
:
 CMP24 BQ_NEXT,BQ_END
 jne bq_corrupt
 CMP24 BQ_NEXT,BQ_LENGTH
 jcc @restore_end
 jne bq_corrupt
@restore_end:
 lda BQ_END
 bne @dec_low
 lda BQ_END+1
 bne @dec_mid
 dec BQ_END+2
@dec_mid:dec BQ_END+1
@dec_low:dec BQ_END
@membership:
 ; EOF must be the last rootreference, CR must not be last. This bounds
 ; cycles/count mismatches without certifying unvisited unrelated records.
 lda BQ_REMAIN
 cmp #1
 bne @not_last
 lda BQ_REMAIN+1
 bne @not_last
 ldy #3
@last:lda BQ_REF,y
 cmp BQ_LAST,y
 jne bq_corrupt
 dey
 bpl @last
 lda BQ_CR+2
 and #2
 jeq bq_corrupt
 jmp @member
@not_last:
 lda BQ_CR+2
 and #1
 jeq bq_corrupt
@member:
 CMP24 BQ_POSITION,BQ_END
 jcc @found
 jeq @found
 ; Fullyparsed baseline is contiguous, monotonic, bounded byrootrecordcount.
 lda BQ_REMAIN
 bne :+
 dec BQ_REMAIN+1
:dec BQ_REMAIN
 lda BQ_REMAIN
 ora BQ_REMAIN+1
 jeq bq_corrupt
 CP BQ_NEXT,BQ_EXPECT,3
 jsr advance
 jcs bq_fail
 lda #BQ_PAGE
 sta BQ_STATE
 jmp bq_pending
@found:
.ifndef BCQ_PAGE_REUSE
 CP BQ_REF,BQ_RECORD_REF,4
 CP BQ_CR+44,BQ_EVENTS,3
 lda BQ_EVENTS+2
 jne bq_corrupt
 CP BQ_CR+40,BQ_REF,4
 lda BQ_EVENTS
 ora BQ_EVENTS+1
 beq @empty
 lda BQ_CR+2
 and #4
 jeq bq_corrupt
 lda BQ_REF
 and BQ_REF+1
 and BQ_REF+2
 and BQ_REF+3
 cmp #$FF
 jeq bq_corrupt
 jmp @output
@empty:
 lda BQ_REF
 and BQ_REF+1
 and BQ_REF+2
 and BQ_REF+3
 cmp #$FF
 jne bq_corrupt
@output:
 CP BQ_CR,BC_IO,96
.endif
 lda #1
 sta BQ_READY
 jmp bq_pending
; Nextreference can onlyadvance: initialbaselinewriterallocatesmonotonicpages.
advance:
 inc BQ_REF+1
 lda BQ_REF+1
 cmp BQ_SLOTS
 bcc @ok
 lda BQ_PAGE_NEXT
 cmp BQ_REF
 jcc bq_corrupt
 jeq bq_corrupt
 CP BQ_PAGE_NEXT,BQ_REF,4
@ok:clc
 rts
.ifndef BCQ_CLASSIFY
event:
 lda BC_IO+9
 jne bq_corrupt
 lda BC_IO
 cmp #1
 beq @pair
 cmp #2
 jne bq_corrupt
 lda BC_IO+1
 jne bq_corrupt
 lda BC_IO+2
 cmp #1
 jne bq_corrupt
 lda #1
 bne @after_style
@pair:
 lda BC_IO+1
 cmp #1
 jcc bq_corrupt
 cmp #5
 jcs bq_corrupt
 cmp #4
 bne @ordinary
 lda BC_IO+2
 cmp #2
 jne bq_corrupt
 jmp @after_style
@ordinary:
 lda BC_IO+2
 cmp BC_IO+1
 jne bq_corrupt
@after_style:
 ; Relative events start atBODY orlater, then open+width<=close and
 ; close+width<=END. ConfirmedESCAPE hasclose=open+1 exactly.
 CMP24 BC_IO+3,BQ_CR+22
 jcc bq_corrupt
 lda BC_IO+2
 clc
 adc BC_IO+3
 sta BQ_TEMP
 lda BC_IO+4
 adc #0
 sta BQ_TEMP+1
 lda BC_IO+5
 adc #0
 sta BQ_TEMP+2
 jcs bq_corrupt
 CMP24 BQ_TEMP,BC_IO+6
 jcs @equal
 lda BC_IO
 cmp #2
 jeq bq_corrupt
 jmp @right
@equal:jne bq_corrupt
@right:
 lda BC_IO+2
 clc
 adc BC_IO+6
 sta BQ_TEMP
 lda BC_IO+7
 adc #0
 sta BQ_TEMP+1
 lda BC_IO+8
 adc #0
 sta BQ_TEMP+2
 jcs bq_corrupt
 CMP24 BQ_TEMP,BQ_CR+19
 jcc @valid
 jne bq_corrupt
@valid:
 lda #2
 sta BQ_READY
 jmp bq_pending
.endif
.export advance

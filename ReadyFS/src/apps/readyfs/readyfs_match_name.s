; Matcher-side copy of the physically proven UltimateDOS access-name
; normalizer used by the recursive controller. Both entry points are
; __fastcall__: AX points at a NUL-terminated relative stem.

        .export _readyfs_match_decode_name
        .export _readyfs_match_strip_type
        .export _readyfs_match_strip_annotation
        .importzp ptr1, ptr2, tmp1, tmp2

        .segment "OVERLAY1"

rfm_nibble:
        cmp #$41
        bcc @digit
        and #$DF
        sec
        sbc #$37
        rts
@digit:
        sec
        sbc #$30
        rts

rfm_inc_read:
        inc ptr1
        bne :+
        inc ptr1+1
:       rts

rfm_inc_write:
        inc ptr2
        bne :+
        inc ptr2+1
:       rts

_readyfs_match_decode_name:
        sta ptr1
        stx ptr1+1
        sta ptr2
        stx ptr2+1
@next:
        ldy #$00
        lda (ptr1),y
        beq @decode_done
        cmp #$5B
        beq @open_hex
@copy:
        sta (ptr2),y
        jsr rfm_inc_read
        jsr rfm_inc_write
        jmp @next
@open_hex:
        jsr rfm_inc_read
@hex_pair:
        ldy #$00
        lda (ptr1),y
        cmp #$5D
        beq @close_hex
        jsr rfm_nibble
        asl a
        asl a
        asl a
        asl a
        sta tmp1
        jsr rfm_inc_read
        ldy #$00
        lda (ptr1),y
        jsr rfm_nibble
        ora tmp1
        sta (ptr2),y
        jsr rfm_inc_read
        jsr rfm_inc_write
        jmp @hex_pair
@close_hex:
        jsr rfm_inc_read
        jmp @next
@decode_done:
        sta (ptr2),y
        rts

rfm_lower:
        ora #$20
        rts

_readyfs_match_strip_type:
        sta ptr1
        stx ptr1+1
        ldy #$00
@find_end:
        lda (ptr1),y
        beq @have_end
        iny
        bne @find_end
@early_done:
        rts
@have_end:
        cpy #$04
        bcc @early_done
        sty tmp1
        tya
        sec
        sbc #$04
        tay
        lda (ptr1),y
        cmp #$2E
        bne @early_done
        iny
        lda (ptr1),y
        jsr rfm_lower
        sta tmp2
        iny
        lda (ptr1),y
        jsr rfm_lower
        tax
        iny
        lda (ptr1),y
        jsr rfm_lower
        cmp #$71
        bne @try_prg
        cpx #$65
        bne @early_done
        lda tmp2
        cmp #$73
        beq @valid_type
        bne @early_done
@try_prg:
        cmp #$67
        bne @try_usr
        cpx #$72
        bne @early_done
        lda tmp2
        cmp #$70
        beq @valid_type
        bne @early_done
@try_usr:
        cmp #$72
        bne @try_rel
        cpx #$73
        bne @early_done
        lda tmp2
        cmp #$75
        beq @valid_type
        bne @early_done
@try_rel:
        cmp #$6C
        bne @early_done
        cpx #$65
        bne @early_done
        lda tmp2
        cmp #$72
        bne @early_done
@valid_type:
        ldy tmp1
        dey
        lda (ptr1),y
        jsr rfm_lower
        sta tmp2
        ldy tmp1
        tya
        sec
        sbc #$04
        tay
        lda #$00
        sta (ptr1),y
        lda tmp1
        cmp #$08
        bcc @strip_done
        sec
        sbc #$08
        tay
        lda (ptr1),y
        cmp #$2E
        bne @strip_done
        ldx #$03
@compare_ext:
        iny
        lda (ptr1),y
        jsr rfm_lower
        sta tmp2
        tya
        clc
        adc #$04
        tay
        lda (ptr1),y
        jsr rfm_lower
        cmp tmp2
        bne @strip_done
        tya
        sec
        sbc #$04
        tay
        dex
        bne @compare_ext
        ldy tmp1
        tya
        sec
        sbc #$08
        tay
        lda #$00
        sta (ptr1),y
@strip_done:
        rts

; AX = decoded host spelling. Remove only UltimateDOS' final C64 type
; annotation, retaining a same-named host extension (for example
; `sfa.seq.SEQ` becomes `sfa.seq`).
_readyfs_match_strip_annotation:
        sta ptr1
        stx ptr1+1
        ldy #$00
@ann_find_end:
        lda (ptr1),y
        beq @ann_have_end
        iny
        bne @ann_find_end
@ann_done:
        rts
@ann_have_end:
        cpy #$04
        bcc @ann_done
        tya
        sec
        sbc #$04
        tay
        lda (ptr1),y
        cmp #$2E
        bne @ann_done
        iny
        lda (ptr1),y
        jsr rfm_lower
        sta tmp1
        iny
        lda (ptr1),y
        jsr rfm_lower
        sta tmp2
        iny
        lda (ptr1),y
        jsr rfm_lower
        cmp #$71
        bne @ann_prg
        lda tmp2
        cmp #$65
        bne @ann_done
        lda tmp1
        cmp #$73
        beq @ann_strip
        bne @ann_done
@ann_prg:
        cmp #$67
        bne @ann_usr
        lda tmp2
        cmp #$72
        bne @ann_done
        lda tmp1
        cmp #$70
        beq @ann_strip
        bne @ann_done
@ann_usr:
        cmp #$72
        bne @ann_rel
        lda tmp2
        cmp #$73
        bne @ann_done
        lda tmp1
        cmp #$75
        beq @ann_strip
        bne @ann_done
@ann_rel:
        cmp #$6C
        bne @ann_done
        lda tmp2
        cmp #$65
        bne @ann_done
        lda tmp1
        cmp #$72
        bne @ann_done
@ann_strip:
        dey
        dey
        dey
        lda #$00
        sta (ptr1),y
        rts

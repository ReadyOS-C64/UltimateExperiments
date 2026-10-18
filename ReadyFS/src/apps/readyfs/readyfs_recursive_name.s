; Compact UltimateDOS READ_DIR access-spelling conversion for recursive
; copies to C64-style IEC targets. Both entry points are __fastcall__: AX is
; a NUL-terminated path suffix. The source access spelling is kept elsewhere;
; these routines only shorten the destination buffer in place.

        .export _readyfs_recursive_decode_name
        .export _readyfs_recursive_strip_type
        .importzp ptr1, ptr2, tmp1, tmp2

        .segment "OVERLAY11"

; Convert one ASCII hex digit in A to a nibble. UltimateDOS generated the
; bracket field, so every input digit is valid.
rfn_nibble:
        cmp #$41
        bcc @digit
        and #$DF
        sec
        sbc #$37                    ; 'A' - 10
        rts
@digit:
        sec
        sbc #$30
        rts

rfn_inc_read:
        inc ptr1
        bne :+
        inc ptr1+1
:       rts

rfn_inc_write:
        inc ptr2
        bne :+
        inc ptr2+1
:       rts

_readyfs_recursive_decode_name:
        sta ptr1
        stx ptr1+1
        sta ptr2
        stx ptr2+1
@next:
        ldy #$00
        lda (ptr1),y
        beq @decode_done
        cmp #$5B                    ; '['
        beq @open_hex
@copy:
        sta (ptr2),y
        jsr rfn_inc_read
        jsr rfn_inc_write
        jmp @next
@open_hex:
        jsr rfn_inc_read
@hex_pair:
        ldy #$00
        lda (ptr1),y
        cmp #$5D                    ; ']'
        beq @close_hex
        jsr rfn_nibble
        asl a
        asl a
        asl a
        asl a
        sta tmp1
        jsr rfn_inc_read
        ldy #$00
        lda (ptr1),y
        jsr rfn_nibble
        ora tmp1
        sta (ptr2),y
        jsr rfn_inc_read
        jsr rfn_inc_write
        jmp @hex_pair
@close_hex:
        jsr rfn_inc_read
        jmp @next
@decode_done:
        sta (ptr2),y
        rts

; Return a lower-case ASCII byte in A. Digits/punctuation are not passed.
rfn_lower:
        ora #$20
        rts

; AX = decoded destination suffix. Strip the UltimateDOS type annotation;
; if the host's final extension is the same type, strip that too so
; SoftwareIEC can add its normal host extension from the C64 file type.
_readyfs_recursive_strip_type:
        sta ptr1
        stx ptr1+1
        ldy #$00
@find_end:
        lda (ptr1),y
        beq @have_end
        iny
        bne @find_end               ; ReadyFS paths are at most 255 bytes
@early_done:
        rts
@have_end:
        cpy #$04
        bcc @early_done
        sty tmp1                    ; original end index
        tya
        sec
        sbc #$04
        tay
        lda (ptr1),y
        cmp #$2E                    ; '.'
        bne @early_done
        iny
        lda (ptr1),y
        jsr rfn_lower
        sta tmp2
        iny
        lda (ptr1),y
        jsr rfn_lower
        tax
        iny
        lda (ptr1),y
        jsr rfn_lower
        ; Admit only SEQ, PRG, USR, and REL annotations.
        cmp #$71                    ; q
        bne @try_prg
        cpx #$65                    ; e
        bne @early_done
        lda tmp2
        cmp #$73                    ; s
        beq @valid_type
        bne @early_done
@try_prg:
        cmp #$67                    ; g
        bne @try_usr
        cpx #$72                    ; r
        bne @early_done
        lda tmp2
        cmp #$70                    ; p
        beq @valid_type
        bne @early_done
@try_usr:
        cmp #$72                    ; r
        bne @try_rel
        cpx #$73                    ; s
        bne @early_done
        lda tmp2
        cmp #$75                    ; u
        beq @valid_type
        bne @early_done
@try_rel:
        cmp #$6C                    ; l
        bne @early_done
        cpx #$65                    ; e
        bne @early_done
        lda tmp2
        cmp #$72                    ; r
        bne @early_done
@valid_type:
        ldy tmp1
        dey
        lda (ptr1),y                ; final type char
        jsr rfn_lower
        sta tmp2
        ldy tmp1
        tya
        sec
        sbc #$04
        tay
        lda #$00
        sta (ptr1),y                ; remove annotation
        lda tmp1
        cmp #$08
        bcc @strip_done
        sec
        sbc #$08
        tay
        lda (ptr1),y
        cmp #$2E
        bne @strip_done
        ; Compare the preceding extension against the annotation's three
        ; letters, case-insensitively, from right to left.
        ldx #$03
@compare_ext:
        iny
        lda (ptr1),y
        jsr rfn_lower
        sta tmp2
        tya
        clc
        adc #$04
        tay
        lda (ptr1),y
        jsr rfn_lower
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

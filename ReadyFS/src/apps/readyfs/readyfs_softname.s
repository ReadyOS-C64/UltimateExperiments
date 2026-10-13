; Compact SoftwareIEC-only PETSCII normalization in resident code.
; __fastcall__ input: AX = NUL-terminated canonical path. ReadyFS path buffers
; are always at most 255 bytes plus NUL, so Y cannot wrap before the terminator.

        .export _readyfs_softname_normalize
        .export _readyfs_same_word
        .importzp ptr1, ptr2, tmp1
        .import popax

        .segment "CODE"

_readyfs_softname_normalize:
        sta ptr1
        stx ptr1+1
        ldy #$00
@next: lda (ptr1),y
        beq @done
        cmp #$A4
        bne @keep
        lda #$5F
        sta (ptr1),y
@keep: iny
        bne @next
@done: rts

; unsigned char __fastcall__ readyfs_same_word(const char *left,
;                                               const char *right)
; The right pointer arrives in AX; pop the left pointer.  Fold PETSCII bit 7
; and ASCII case without loading an overlay while an IEC channel is active.
; Numeric ASCII limits are deliberate: the c64 assembler character map maps
; character literals to PETSCII, which would disable folding after AND $7F.
_readyfs_same_word:
        sta ptr2
        stx ptr2+1
        jsr popax
        sta ptr1
        stx ptr1+1
        ldy #$00
@word: lda (ptr1),y
        and #$7F
        cmp #$41
        bcc @left
        cmp #$5B
        bcs @left
        ora #$20
@left: sta tmp1
        lda (ptr2),y
        and #$7F
        cmp #$41
        bcc @right
        cmp #$5B
        bcs @right
        ora #$20
@right:
        cmp tmp1
        bne @no
        ora tmp1
        beq @yes
        iny
        bne @word
@no:   lda #$00
        rts
@yes:  lda #$01
        rts

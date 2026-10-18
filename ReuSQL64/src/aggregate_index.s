; Bounded explicit-index iterator for aggregate rescans.
;
; cc65 spends substantial sidecar space addressing the iterator and row-ID
; pointers on its software stack. Aggregate callers publish those two stable
; work-RAM pointers here, and this helper validates one leaf at a time before
; returning the next physical row identity. No state is shared between nested
; rescans beyond the caller-owned three-byte iterator.

        .import _g_rsql_meta_page0
        .import _rsql_page_checksum
        .import _rsql_reu_page_address
        .import _rsql_reu_read
        .import pusheax, pushax
        .importzp ptr1, ptr2

        .export _g_aggregate_index_scan
        .export _g_aggregate_index_row
        .export _rsql_aggregate_index_next

RSQL_OK                  = 0
RSQL_ERR_CORRUPT_STORAGE = 4
RSQL_ERR_NOT_FOUND       = 10
RSQL_STORAGE_VERSION     = 4

LEAF_CAPACITY  = 5
LEAF_NEXT      = 6
LEAF_COUNT     = 10
LEAF_KEY_WIDTH = 11
LEAF_DATA      = 12
CHECKSUM       = 255
KEY_MAX        = 96

        .segment "BSS"

_g_aggregate_index_scan: .res 2
_g_aggregate_index_row:  .res 2
index_width:              .res 1
index_entry_width:        .res 1
index_offset:             .res 1

.segment "OVERLAY1"

_rsql_aggregate_index_next:
        lda _g_aggregate_index_scan
        sta ptr2
        lda _g_aggregate_index_scan+1
        sta ptr2+1
        jmp next_leaf

return_ok:
        lda #RSQL_OK
        ldx #$00
        rts

return_corrupt:
        lda #RSQL_ERR_CORRUPT_STORAGE
        ldx #$00
        rts

return_not_found:
        lda #RSQL_ERR_NOT_FOUND
        ldx #$00
        rts

next_leaf:
        ; A leaf page of $FFFF terminates this independent iterator.
        ldy #$00
        lda (ptr2),y
        iny
        and (ptr2),y
        cmp #$FF
        beq return_not_found

read_leaf:
        ldy #$00
        lda (ptr2),y
        pha
        iny
        lda (ptr2),y
        tax
        pla
        jsr _rsql_reu_page_address
        jsr pusheax
        lda #<(_g_rsql_meta_page0)
        ldx #>(_g_rsql_meta_page0)
        jsr pushax
        lda #$00
        ldx #$01
        jsr _rsql_reu_read
        cmp #RSQL_OK
        beq validate_leaf
        ldx #$00
        rts

validate_leaf:
        ; ca65 source bytes use the C64 target character set.
        lda _g_rsql_meta_page0
        cmp #$D2                    ; R
        bne return_corrupt
        lda _g_rsql_meta_page0+1
        cmp #$C9                    ; I
        bne return_corrupt
        lda _g_rsql_meta_page0+2
        cmp #$CC                    ; L
        bne return_corrupt
        lda _g_rsql_meta_page0+3
        cmp #$C6                    ; F
        bne return_corrupt
        lda _g_rsql_meta_page0+4
        cmp #RSQL_STORAGE_VERSION
        bne return_corrupt
        lda #<(_g_rsql_meta_page0)
        ldx #>(_g_rsql_meta_page0)
        jsr _rsql_page_checksum
        cmp _g_rsql_meta_page0+CHECKSUM
        bne return_corrupt

        ; All cc65 calls may use the compiler pointer registers as scratch.
        ; Reload the caller-owned iterator after the final resident helper.
        lda _g_aggregate_index_scan
        sta ptr2
        lda _g_aggregate_index_scan+1
        sta ptr2+1

        lda _g_rsql_meta_page0+LEAF_KEY_WIDTH
        beq return_corrupt
        cmp #(KEY_MAX+1)
        bcs return_corrupt
        sta index_width
        clc
        adc #$03
        sta index_entry_width

        lda _g_rsql_meta_page0+LEAF_CAPACITY
        cmp _g_rsql_meta_page0+LEAF_COUNT
        bcs :+
        jmp return_corrupt
:

        ldy #$02
        lda (ptr2),y
        cmp _g_rsql_meta_page0+LEAF_COUNT
        bcc have_entry

        lda _g_rsql_meta_page0+LEAF_NEXT
        ldy #$00
        sta (ptr2),y
        lda _g_rsql_meta_page0+LEAF_NEXT+1
        iny
        sta (ptr2),y
        lda #$00
        iny
        sta (ptr2),y
        jmp next_leaf

have_entry:
        tax
        lda #LEAF_DATA
        sta index_offset
multiply_entry:
        cpx #$00
        beq validate_entry
        clc
        lda index_offset
        adc index_entry_width
        bcs entry_corrupt
        sta index_offset
        dex
        bne multiply_entry

validate_entry:
        ; offset + key width + row ID must end no later than byte 254.
        clc
        lda index_offset
        adc index_entry_width
        bcs entry_corrupt

        ; The three row-ID bytes begin immediately after the key.
        ; ptr1 is loaded only after the checksum call because the checksum
        ; implementation uses ptr1 as scratch. ptr2 deliberately retains the
        ; caller-owned scan pointer across all resident helper calls.
        lda _g_aggregate_index_row
        sta ptr1
        lda _g_aggregate_index_row+1
        sta ptr1+1
        clc
        lda index_offset
        adc index_width
        tay
        lda _g_rsql_meta_page0,y
        pha
        iny
        lda _g_rsql_meta_page0,y
        pha
        iny
        lda _g_rsql_meta_page0,y
        ldy #$02
        sta (ptr1),y
        pla
        dey
        sta (ptr1),y
        pla
        dey
        sta (ptr1),y

        ldy #$02
        lda (ptr2),y
        clc
        adc #$01
        sta (ptr2),y
        jmp return_ok

entry_corrupt:
        jmp return_corrupt

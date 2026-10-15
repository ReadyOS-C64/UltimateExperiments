        .import _g_rsql_meta_page0, _g_rsql_meta_page1
        .import _g_rsql_scalar_compare_part
        .import _g_rsql_scalar_compare_offset
        .import _g_rsql_scalar_compare_page_start
        .import _g_rsql_scalar_compare_right
        .import _g_rsql_scalar_compare_value
        .import _rsql_reu_page_address, _rsql_reu_read
        .import pushax, pusheax
        .importzp ptr1, ptr2

        .export _rsql_scalar_compare_part_byte

PART_KIND       = 0
PART_DATA       = 1
PART_FIRST      = 3
PART_NEXT       = 5
PART_START      = 7
PART_PAGE_START = 11
PART_PAGE_USED  = 13

PAGE_NEXT       = 6
PAGE_USED       = 8
PAGE_DATA       = 10

RSQL_OK         = 0
RSQL_CORRUPT    = 4

        .segment "OVERLAY3"

_rsql_scalar_compare_part_byte:
        ; Convert the result-relative byte offset to the part-relative source
        ; offset once.  Every caller walks offsets in ascending order.
        lda _g_rsql_scalar_compare_part
        sta ptr1
        lda _g_rsql_scalar_compare_part+1
        sta ptr1+1
        ldy #PART_START
        clc
        lda _g_rsql_scalar_compare_offset
        adc (ptr1),y
        sta _g_rsql_scalar_compare_offset
        iny
        lda _g_rsql_scalar_compare_offset+1
        adc (ptr1),y
        sta _g_rsql_scalar_compare_offset+1

        ldy #PART_KIND
        lda (ptr1),y
        bne text_part

        ldy #PART_DATA
        lda (ptr1),y
        clc
        adc _g_rsql_scalar_compare_offset
        sta ptr2
        iny
        lda (ptr1),y
        adc _g_rsql_scalar_compare_offset+1
        sta ptr2+1
        ldy #0
        lda (ptr2),y
        jmp store_value

text_part:
        ; Each operand owns one metadata page buffer, so its current page may
        ; remain cached while comparisons alternate left and right bytes.
        jsr select_text_state

        ldy #PART_PAGE_USED
        lda (ptr1),y
        iny
        ora (ptr1),y
        beq fresh_page

        ; Cached offsets are monotonic. Use the current page while the source
        ; offset is strictly below page_start + used.
        ldy #PART_PAGE_START
        lda (ptr1),y
        sta _g_rsql_scalar_compare_page_start
        iny
        lda (ptr1),y
        sta _g_rsql_scalar_compare_page_start+1
        jsr offset_in_cached_page
        bcc continue_page
        jmp cached_byte

continue_page:
        jsr advance_page_start
        jmp read_page

fresh_page:
        ldy #PART_FIRST
        lda (ptr1),y
        ldy #PART_NEXT
        sta (ptr1),y
        ldy #PART_FIRST+1
        lda (ptr1),y
        ldy #PART_NEXT+1
        sta (ptr1),y
        lda #0
        sta _g_rsql_scalar_compare_page_start
        sta _g_rsql_scalar_compare_page_start+1

read_page:
        lda _g_rsql_scalar_compare_part
        sta ptr1
        lda _g_rsql_scalar_compare_part+1
        sta ptr1+1
        ldy #PART_NEXT
        lda (ptr1),y
        pha
        iny
        lda (ptr1),y
        tax
        pla
        cpx #$FF
        bne have_page
        cmp #$FF
        bne have_page
        jmp corrupt
have_page:
        jsr _rsql_reu_page_address
        jsr pusheax
        lda ptr2
        ldx ptr2+1
        jsr pushax
        lda #0
        ldx #1
        jsr _rsql_reu_read
        cmp #RSQL_OK
        beq :+
        ldx #0
        rts
:

        ; Reload volatile zero-page pointers after the C calls.
        jsr select_text_state

        ldy #3
validate_magic:
        lda (ptr2),y
        cmp blob_magic,y
        bne corrupt
        dey
        bpl validate_magic

        ldy #PAGE_USED+1
        lda (ptr2),y
        bne corrupt
        dey
        lda (ptr2),y
        beq corrupt
        cmp #247
        bcs corrupt
        ldy #PART_PAGE_USED
        sta (ptr1),y
        iny
        lda #0
        sta (ptr1),y
        ldy #PAGE_NEXT
        lda (ptr2),y
        ldy #PART_NEXT
        sta (ptr1),y
        ldy #PAGE_NEXT+1
        lda (ptr2),y
        ldy #PART_NEXT+1
        sta (ptr1),y
        ldy #PART_PAGE_START
        lda _g_rsql_scalar_compare_page_start
        sta (ptr1),y
        iny
        lda _g_rsql_scalar_compare_page_start+1
        sta (ptr1),y

        jsr offset_in_cached_page
        bcs cached_byte
advance_loaded:
        jsr advance_page_start
        jmp read_page

cached_byte:
        sec
        lda _g_rsql_scalar_compare_offset
        sbc _g_rsql_scalar_compare_page_start
        clc
        adc #PAGE_DATA
        tay
        lda (ptr2),y
store_value:
        pha
        lda _g_rsql_scalar_compare_value
        sta ptr1
        lda _g_rsql_scalar_compare_value+1
        sta ptr1+1
        pla
        ldy #0
        sta (ptr1),y
        lda #RSQL_OK
        ldx #0
        rts

corrupt:
        lda #RSQL_CORRUPT
        ldx #0
        rts

; Restore the descriptor pointer and select the operand's private REU page
; buffer.  Both ptr1 and ptr2 are volatile across the C REU calls.
select_text_state:
        lda _g_rsql_scalar_compare_part
        sta ptr1
        lda _g_rsql_scalar_compare_part+1
        sta ptr1+1
        lda _g_rsql_scalar_compare_right
        beq select_left
        lda #<_g_rsql_meta_page1
        ldx #>_g_rsql_meta_page1
        bne select_store
select_left:
        lda #<_g_rsql_meta_page0
        ldx #>_g_rsql_meta_page0
select_store:
        sta ptr2
        stx ptr2+1
        rts

; Return carry set exactly when offset < page_start + page_used.  Equal means
; that the next payload page owns the requested byte.
offset_in_cached_page:
        ldy #PART_PAGE_USED
        clc
        lda _g_rsql_scalar_compare_page_start
        adc (ptr1),y
        pha
        iny
        lda _g_rsql_scalar_compare_page_start+1
        adc (ptr1),y
        cmp _g_rsql_scalar_compare_offset+1
        bcc offset_not_cached
        bne offset_cached_high
        pla
        cmp _g_rsql_scalar_compare_offset
        beq offset_not_cached_popped
        bcc offset_not_cached_popped
        sec
        rts
offset_cached_high:
        pla
        sec
        rts
offset_not_cached:
        pla
offset_not_cached_popped:
        clc
        rts

advance_page_start:
        ldy #PART_PAGE_USED
        clc
        lda _g_rsql_scalar_compare_page_start
        adc (ptr1),y
        sta _g_rsql_scalar_compare_page_start
        iny
        lda _g_rsql_scalar_compare_page_start+1
        adc (ptr1),y
        sta _g_rsql_scalar_compare_page_start+1
        rts

blob_magic:
        .byte $D2, $C2, $CC, $C2     ; PETSCII "RBLB"

.include "host_input.inc"
.ifndef DOS64_MODAL_MENU
DOS64_MODAL_MENU=0
.endif
.if DOS64_MODAL_MENU
.import dos64_modal_input,dos64_modal_pending,dos64_modal_edge
.endif
.macpack longbranch
.import dos64_keyboard_enqueue, dos64_keyboard_key, dos64_keyboard_status
.import dos64_mem_read, dos64_mem_write
.importzp dos64_address, dos64_mem_value
.export dos64_host_input_init, dos64_host_input_poll
.export dos64_host_input_claim, dos64_host_input_ready, dos64_host_input_status
.export dos64_host_input_pending, dos64_host_input_matrix
.export dos64_host_input_state_start, dos64_host_input_state_end

.segment "DEVICESTATE"
dos64_host_input_state_start:
dos64_host_input_claim: .res 1
dos64_host_input_ready: .res 1
dos64_host_input_status: .res 1
dos64_host_input_pending: .res 1
pending_word: .res 2
pending_row: .res 1
pending_bit: .res 1
dos64_host_input_matrix: .res 8
seen: .res 8
saved_ports: .res 4
row: .res 1
key_bit: .res 1
index: .res 1
modifiers: .res 1
char: .res 1
scan: .res 1
; Pound is a deferred printable key and the F9/F10 layer switch. States:
; 0 released, 1 printable deferred, 2 layer consumed, 3 printable committed.
fn_state: .res 1
fn_word: .res 2
dos64_host_input_state_end:

.macro enter
    php
    sei
    cld
    pha
    txa
    pha
    tya
    pha
    lda $00
    pha
    lda $01
    pha
    lda $00
    ora #7
    sta $00
    lda $01
    and #$F8
    ora #5
    sta $01
.endmacro
.macro leave carry
    pla
    sta $01
    pla
    sta $00
    pla
    tay
    pla
    tax
    pla
    plp
    .if carry
        sec
    .else
        clc
    .endif
    rts
.endmacro

.segment "INPUTCODE"
dos64_host_input_init:
    enter
    lda #0
    sta dos64_host_input_ready
    sta dos64_host_input_status
    lda dos64_host_input_claim
    cmp #HI_OWNED
    jne owner_error
    lda #0
    sta dos64_host_input_pending
    sta fn_state
.if DOS64_MODAL_MENU
    sta dos64_modal_pending
    sta dos64_modal_edge
.endif
    ldx #7
@clear:
    sta seen,x
    sta dos64_host_input_matrix,x
    dex
    bpl @clear
    lda #1
    sta dos64_host_input_ready
    jmp done

dos64_host_input_poll:
    enter
    lda #0
    sta dos64_host_input_status
    lda dos64_host_input_claim
    cmp #HI_OWNED
    jne owner_error
    lda dos64_host_input_ready
    jeq unready_error
    ldx #3
@save:
    lda $DC00,x
    sta saved_ports,x
    dex
    bpl @save
    lda #0
    sta $DC03
    lda #$FF
    sta $DC01
    sta $DC02
    lda #$FE
    ldx #0
@scan:
    sta $DC00
    pha
    lda $DC01
    eor #$FF
    sta dos64_host_input_matrix,x
    pla
    sec
    rol
    inx
    cpx #8
    bne @scan
    ; Put both ports in input before restoring observed output values/DDRs.
    lda #0
    sta $DC02
    sta $DC03
    lda saved_ports
    sta $DC00
    lda saved_ports+1
    sta $DC01
    lda saved_ports+2
    sta $DC02
    lda saved_ports+3
    sta $DC03
    ; A diodeless matrix cannot distinguish rectangles from phantom keys.
    ldx #0
@ghost_row:
    stx row
    inx
@ghost_other:
    cpx #8
    beq @next_row
    lda dos64_host_input_matrix,x
    ldy row
    and dos64_host_input_matrix,y
    sta key_bit
    sec
    sbc #1
    and key_bit
    jne ghost_error
    inx
    bne @ghost_other
@next_row:
    ldx row
    inx
    cpx #7
    bne @ghost_row
.if DOS64_MODAL_MENU
    jsr dos64_modal_input
    bcc @modal_normal
    cmp #0
    jeq done
    jmp queue_error
@modal_normal:
.endif
    lda #0
    sta modifiers
    lda dos64_host_input_matrix+1
    and #$80
    beq @right
    lda #2
    sta modifiers
@right:
    lda dos64_host_input_matrix+6
    and #$10
    beq @ctrl
    inc modifiers
@ctrl:
    lda dos64_host_input_matrix+7
    and #4
    beq @alt
    lda modifiers
    ora #4
    sta modifiers
@alt:
    lda dos64_host_input_matrix+7
    and #$20
    beq @bda
    lda modifiers
    ora #8
    sta modifiers
@bda:
    lda #$17
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    jsr dos64_mem_read
    jcs cache_error
    and #$F0
    ora modifiers
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs cache_error
    ldx #7
@released:
    lda seen,x
    and dos64_host_input_matrix,x
    sta seen,x
    dex
    bpl @released
    lda dos64_host_input_pending
    beq @new_keys
    jsr enqueue_pending
    jcs queue_error
@new_keys:
    jsr prepare_fn
    jcs queue_error
    lda #0
    sta row
    sta index
@row:
    lda #1
    sta key_bit
@key:
    ldx row
    lda dos64_host_input_matrix,x
    and key_bit
    jeq @advance
    lda seen,x
    and key_bit
    jne @advance
    ldx index
    cpx #48
    jeq @mark
    lda scans,x
    jeq @mark
    sta scan
    lda normal,x
    sta char
    lda fn_state
    cmp #2
    bne @shift
    cpx #6
    beq @f9
    cpx #3
    bne @shift
    lda #$44
    bne @fn_scan
@f9:
    lda #$43
@fn_scan:
    sta scan
    jmp @control
@shift:
    lda modifiers
    and #3
    beq @control
    lda shifted,x
    sta char
    ; Extended key shifted variants and function pairs.
    cpx #0
    bne @cursor_lr
    lda #$53
    bne @changed_scan
@cursor_lr:
    cpx #2
    bne @cursor_ud
    lda #$4B
    bne @changed_scan
@cursor_ud:
    cpx #7
    bne @home
    lda #$48
    bne @changed_scan
@home:
    cpx #51
    bne @function
    lda #$4F
    bne @changed_scan
@function:
    cpx #3
    bcc @control
    cpx #7
    bcs @control
    inc scan
    bne @control
@changed_scan:
    sta scan
@control:
    ; XT BIOS function words use distinct Ctrl/Alt scan codes. Physical
    ; Shift selects F2/F4/F6/F8; on the pound layer it means Shift-F9/F10.
    lda scan
    cmp #$3B
    bcc @ordinary_control
    cmp #$45
    bcs @ordinary_control
@function_control:
    lda modifiers
    and #8
    beq @function_ctrl
    lda scan
    clc
    adc #$2D
    bne @function_scan
@function_ctrl:
    lda modifiers
    and #4
    beq @function_shift
    lda scan
    clc
    adc #$23
    bne @function_scan
@function_shift:
    lda fn_state
    cmp #2
    bne @ordinary_control
    cpx #6
    beq @layer_shift
    cpx #3
    bne @ordinary_control
@layer_shift:
    lda modifiers
    and #3
    beq @ordinary_control
    lda scan
    clc
    adc #$19
@function_scan:
    sta scan
@ordinary_control:
    lda modifiers
    and #8
    beq @ctrl_char
    lda #0
    sta char
    beq @publish
@ctrl_char:
    lda modifiers
    and #4
    beq @publish
    lda char
    cmp #'a'
    bcc @upper
    cmp #'z'+1
    bcs @upper
    and #$DF
@upper:
    cmp #'@'
    bcc @publish
    cmp #'_'+1
    bcs @publish
    and #$1F
    sta char
@publish:
    lda char
    sta pending_word
    lda scan
    sta pending_word+1
    lda row
    sta pending_row
    lda key_bit
    sta pending_bit
    lda #1
    sta dos64_host_input_pending
    jsr enqueue_pending
    jcs queue_error
    jmp @advance
@mark:
    ldx row
    lda seen,x
    ora key_bit
    sta seen,x
@advance:
    inc index
    asl key_bit
    jne @key
    inc row
    lda row
    cmp #8
    jne @row
done:
    leave 0
owner_error:
    lda #HI_ERR_OWNER
    bne fail
unready_error:
    lda #HI_ERR_UNREADY
    bne fail
ghost_error:
    lda #HI_ERR_GHOST
    bne fail
cache_error:
    lda #HI_ERR_CACHE
    bne fail
queue_error:
    lda #HI_ERR_QUEUE
fail:
    sta dos64_host_input_status
    leave 1

enqueue_pending:
    lda pending_word
    sta dos64_keyboard_key
    lda pending_word+1
    sta dos64_keyboard_key+1
    jsr dos64_keyboard_enqueue
    bcs @return
    ldx pending_row
    ; A released pending key must not suppress its next fresh press. If
    ; held at commitment, consume it to avoid retrying the accepted word.
    lda pending_bit
    and dos64_host_input_matrix,x
    ora seen,x
    sta seen,x
    lda #0
    sta dos64_host_input_pending
@return:
    rts

prepare_fn:
    lda dos64_host_input_matrix+6
    and #1
    bne @held
    lda fn_state
    pha
    lda #0
    sta fn_state
    pla
    cmp #1
    beq publish_fn
@ok:
    clc
    rts
@held:
    lda fn_state
    bne @new_chord
    ; A pending printable pound accepted while held consumed this press.
    ; It cannot re-arm either deferred text or the layer until release.
    lda seen+6
    and #1
    bne @ok
    lda #1
    sta fn_state
    lda #$2B
    sta fn_word+1
    lda #$5C
    sta fn_word
    lda modifiers
    and #3
    beq @print_ctrl
    lda #$7C
    sta fn_word
@print_ctrl:
    lda modifiers
    and #4
    beq @print_alt
    lda #$1C
    sta fn_word
@print_alt:
    lda modifiers
    and #8
    beq @new_chord
    lda #0
    sta fn_word
@new_chord:
    lda fn_state
    cmp #3
    beq @ok
    lda seen
    eor #$FF
    and dos64_host_input_matrix
    and #$48
    beq @ordinary
    lda #2
    sta fn_state
    bne @ok
@ordinary:
    lda fn_state
    cmp #1
    bne @ok
    ldx #7
@edge:
    lda seen,x
    eor #$FF
    and dos64_host_input_matrix,x
    and fn_printable_mask,x
    bne @flush
    dex
    bpl @edge
    bmi @ok
@flush:
    lda #3
    sta fn_state
publish_fn:
    lda fn_word
    sta pending_word
    lda fn_word+1
    sta pending_word+1
    lda #6
    sta pending_row
    lda #1
    sta pending_bit
    sta dos64_host_input_pending
    jmp enqueue_pending
fn_printable_mask:
.byte $FF,$7F,$FF,$FF,$FF,$FF,$EE,$DB

; Matrix indices are PRA-selected column*8 + PRB row, matching Commodore's
; original KERNAL keyboard tables. ASCII legends plus selected printable
; alternatives for C64 graphic legends determine ASCII;
; resulting word's high byte is the corresponding XT set-1 scan code.
normal:
.byte 8,13,0,0,0,0,0,0
.byte '3','w','a','4','z','s','e',0
.byte '5','r','d','6','c','f','t','x'
.byte '7','y','g','8','b','h','u','v'
.byte '9','i','j','0','m','k','o','n'
.byte '+','p','l','-','.',':','@',','
.byte $5C,'*',';',0,0,'=','^','/'
.byte '1',9,0,'2',' ',0,'q',27
shifted:
.byte 0,13,0,0,0,0,0,0
.byte '#','W','A','$','Z','S','E',0
.byte '%','R','D','&','C','F','T','X'
.byte $27,'Y','G','(','B','H','U','V'
.byte ')','I','J','0','M','K','O','N'
.byte '+','P','L','_','>','[','`','<'
.byte '|','*',']',0,0,'=','~','?'
.byte '!',0,0,$22,' ',0,'Q',27
scans:
.byte $0E,$1C,$4D,$41,$3B,$3D,$3F,$50
.byte $04,$11,$1E,$05,$2C,$1F,$12,0
.byte $06,$13,$20,$07,$2E,$21,$14,$2D
.byte $08,$15,$22,$09,$30,$23,$16,$2F
.byte $0A,$17,$24,$0B,$32,$25,$18,$31
.byte $0D,$19,$26,$0C,$34,$27,$03,$33
.byte $2B,$09,$27,$47,0,$0D,$07,$35
.byte $02,$0F,0,$03,$39,0,$10,$01

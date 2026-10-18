        .import pushax
        .importzp ptr1, ptr2
        .import _cputs, _readyfs_reu_session_fetch
        .import _args
        .export _readyfs_content_format

; Packed ReadyFsDriveUiCall offsets.  This sidecar only validates and composes
; the command.  The resident ReadyIRC-style controller owns synchronization,
; command-channel I/O, status draining, and final completion.
RF_D_ARGC       = 1
RF_D_PENDING    = 2
RF_D_DEVICE     = 3
RF_D_IO_OK      = 4
RF_D_HANDLED    = 9
RF_D_ARGS       = 10
RF_D_SOURCE     = 14
RF_D_OUTPUT     = 18
RF_D_OUTCAP     = 20

        .segment "OVERLAY9"

callptr:        .res 2
argtab:         .res 2
argptr:         .res 2
labelptr:       .res 2
idptr:          .res 2
profile:        .res 4
unit:           .res 1
ten:            .res 1

; ca65's C64 character map turns lowercase source letters into the unshifted
; PETSCII uppercase bytes produced by the keyboard and cc65 C literals.
opt_label:      .byte "--label",0
opt_id:         .byte "--id",0
opt_disposable: .byte "--disposable",0
opt_yes:        .byte "--yes",0
msg_reject:     .byte "format rejected",13,10,0
msg_unprobed:   .byte "unprobed",13,10,0
msg_denied:     .byte "profile denied",13,10,0
msg_confirmed:  .byte "format confirmed",13,10,0

; Y is a byte offset in the char** table.
load_arg:
        lda argtab
        sta ptr1
        lda argtab+1
        sta ptr1+1
        lda (ptr1),y
        sta argptr
        iny
        lda (ptr1),y
        sta argptr+1
        rts

; A/X names an uppercase literal; compare exactly while accepting PETSCII
; upper/lower case in the parsed argument.  Return zero on mismatch.
same_arg:
        sta ptr2
        stx ptr2+1
        lda argptr
        sta ptr1
        lda argptr+1
        sta ptr1+1
        ldy #0
@loop: lda (ptr1),y
        and #$7f
        cmp (ptr2),y
        bne @no
        lda (ptr2),y
        beq @yes
        iny
        bne @loop
@no:   lda #0
        rts
@yes:  lda #1
        rts

return_message:
        jsr _cputs
return_ok:
        lda #1
        ldx #0
        rts

reject:
        lda #<msg_reject
        ldx #>msg_reject
        jmp return_message

_readyfs_content_format:
        sta callptr
        stx callptr+1
        sta ptr1
        stx ptr1+1
        ldy #RF_D_HANDLED
        lda #1
        sta (ptr1),y
        ldy #RF_D_PENDING
        lda #0
        sta (ptr1),y

        ; Re-validate a canonical flat IEC root, 8:/ through 30:/.
        ldy #RF_D_SOURCE
        lda (ptr1),y
        tax
        iny
        lda (ptr1),y
        sta ptr1+1
        stx ptr1
        ora ptr1
        beq @root_bad
        ldy #0
        lda (ptr1),y
        cmp #'0'
        bcc @root_bad
        cmp #'9'+1
        bcs @root_bad
        sec
        sbc #'0'
        sta unit
        iny
        lda (ptr1),y
        cmp #':'
        beq @colon
        cmp #'0'
        bcc @root_bad
        cmp #'9'+1
        bcs @root_bad
        sec
        sbc #'0'
        pha
        lda unit
        asl a
        sta ten
        asl a
        asl a
        clc
        adc ten
        sta unit
        pla
        clc
        adc unit
        sta unit
        iny
        lda (ptr1),y
        cmp #':'
        bne @root_bad
@colon: iny
        lda (ptr1),y
        beq @root_ok
        cmp #'/'
        bne @root_bad
        iny
        lda (ptr1),y
        bne @root_bad
@root_ok:
        lda unit
        cmp #8
        bcc @root_bad
        cmp #31
        bcs @root_bad
        jmp @profile
@root_bad:
        jmp reject

        ; A profile must have been freshly probed; unknown and SoftIEC are
        ; refused because neither has a proven IEC media-format contract.
@profile:
        lda callptr
        sta ptr1
        lda callptr+1
        sta ptr1+1
        lda unit
        ldy #RF_D_DEVICE
        sta (ptr1),y
        sec
        sbc #8
        asl a
        asl a
        clc
        adc #$88
        ldx #$08
        jsr pushax
        lda #<profile
        ldx #>profile
        jsr pushax
        lda #4
        ldx #0
        jsr _readyfs_reu_session_fetch
        beq @unprobed
        lda profile
        cmp #$52
        bne @unprobed
        lda profile+1
        cmp unit
        bne @unprobed
        lda profile+2
        beq @denied
        cmp #6
        beq @denied
        jmp @syntax
@unprobed:
        lda #<msg_unprobed
        ldx #>msg_unprobed
        jmp return_message
@denied:
        lda #<msg_denied
        ldx #>msg_denied
        jmp return_message

        ; Exact, order-stable destructive syntax:
        ; FORMAT N: --LABEL NAME --ID ID --DISPOSABLE --YES
@syntax:
        lda callptr
        sta ptr1
        lda callptr+1
        sta ptr1+1
        ldy #RF_D_ARGC
        lda (ptr1),y
        cmp #8
        bne @args_bad
        lda #<_args
        sta argtab
        lda #>_args
        sta argtab+1

        ldy #4
        jsr load_arg
        lda #<opt_label
        ldx #>opt_label
        jsr same_arg
        beq @args_bad
        ldy #6
        jsr load_arg
        lda argptr
        sta labelptr
        lda argptr+1
        sta labelptr+1
        ldy #8
        jsr load_arg
        lda #<opt_id
        ldx #>opt_id
        jsr same_arg
        beq @args_bad
        ldy #10
        jsr load_arg
        lda argptr
        sta idptr
        lda argptr+1
        sta idptr+1
        ldy #12
        jsr load_arg
        lda #<opt_disposable
        ldx #>opt_disposable
        jsr same_arg
        beq @args_bad
        ldy #14
        jsr load_arg
        lda #<opt_yes
        ldx #>opt_yes
        jsr same_arg
        beq @args_bad
        jmp @capacity
@args_bad:
        jmp reject

        ; Capacity 22 covers N: + 16-byte label + comma + two-byte ID + NUL.
@capacity:
        lda callptr
        sta ptr1
        lda callptr+1
        sta ptr1+1
        ldy #RF_D_OUTPUT
        lda (ptr1),y
        sta ptr2
        iny
        lda (ptr1),y
        sta ptr2+1
        ora ptr2
        beq @cap_bad
        ldy #RF_D_OUTCAP+1
        lda (ptr1),y
        bne @capacity_ok
        dey
        lda (ptr1),y
        cmp #22
        bcc @cap_bad
        bcs @build
@cap_bad:
        jmp reject
@capacity_ok:
@build:
        ldy #0
        lda #'n'
        sta (ptr2),y
        iny
        lda #':'
        sta (ptr2),y
        clc
        lda ptr2
        adc #2
        sta ptr2
        bcc :+
        inc ptr2+1
:
        ; Validate and copy a 1..16 byte label without commas.
        lda labelptr
        sta ptr1
        lda labelptr+1
        sta ptr1+1
        ldy #0
        lda (ptr1),y
        beq @name_bad
@label:cmp #','
        beq @name_bad
        sta (ptr2),y
        iny
        cpy #17
        beq @name_bad
        lda (ptr1),y
        bne @label
        lda #','
        sta (ptr2),y
        iny
        sty ten
        ; ID is exactly two non-comma bytes.
        lda idptr
        sta ptr1
        lda idptr+1
        sta ptr1+1
        ldy #0
        lda (ptr1),y
        beq @bad_id
        cmp #','
        beq @bad_id
        sta argptr
        iny
        lda (ptr1),y
        beq @bad_id
        cmp #','
        beq @bad_id
        sta argptr+1
        iny
        lda (ptr1),y
        bne @bad_id
        ldy ten
        lda argptr
        sta (ptr2),y
        iny
        lda argptr+1
        sta (ptr2),y
        iny
        lda #0
        sta (ptr2),y

        lda #<msg_confirmed
        ldx #>msg_confirmed
        jsr _cputs
        lda callptr
        sta ptr1
        lda callptr+1
        sta ptr1+1
        ldy #RF_D_IO_OK
        lda #0
        sta (ptr1),y
        ldy #RF_D_PENDING
        lda #1
        sta (ptr1),y
        jmp return_ok

@bad_id:
@name_bad:
        jmp reject

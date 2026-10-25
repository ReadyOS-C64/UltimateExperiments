; Shared by command modules, no overlay-private persistent frame.
; Input header at8000; checks schema/context/count-derived size/header CRC.
.proc h_header_crc
    jsr se_crc_init
    ldy #0
loop:
    lda $8000,y
    jsr se_crc_byte
    iny
    cpy #58
    bne :+
    ldy #60
:
    cpy #64
    bcc loop
    rts
.endproc
.proc h_header_check
    ldx #3
magic:
    lda $8000,x
    cmp h_magic,x
    jne bad
    dex
    bpl magic
    lda $8004
    cmp #H_RECORD_ABI
    jne bad
    lda $8005
    and #$FE
    jne bad
    lda $802D
    beq no_group
    lda $8005
    cmp #1
    jne bad
    lda $801D
    ora $801E
    ora $801F
    jne bad
    lda $8020
    ora $8021
    ora $8022
    jeq bad
    jmp grouped
no_group:
    lda $8005
    jne bad
grouped:
    ldx #4
context:
    lda $8010,x
    cmp se_h_original,x
    jne bad
    lda $8015,x
    cmp se_h_append,x
    jne bad
    dex
    bpl context
    lda $8008
    ora $8009
    ora $800A
    ora $800B
    jeq bad
    lda $800C
    ora $800D
    ora $800E
    ora $800F
    jeq bad
    ldx #3
nodes:
    lda $8008,x
    cmp $800C,x
    bne different
    dex
    bpl nodes
    jmp bad
different:
    ldx #9
reserved:
    lda $802E,x
    jne bad
    dex
    bpl reserved
    lda $803C
    ora $803D
    ora $803E
    ora $803F
    jne bad
    lda $8024
    cmp #8
    bcc removed
    jne bad
    lda $8023
    jne bad
removed:
    lda $8026
    jne bad
    lda $8025
    cmp #2
    jcs bad
    lda $8023
    ora $8024
    beq empty_removed
    lda $801D
    ora $801E
    ora $801F
    jeq bad
    jmp inserted
empty_removed:
    lda $801D
    ora $801E
    ora $801F
    jne bad
inserted:
    lda $8025
    beq empty_inserted
    lda $8020
    ora $8021
    ora $8022
    jeq bad
    jmp length
empty_inserted:
    lda $8020
    ora $8021
    ora $8022
    jne bad
    lda $8023
    ora $8024
    jeq bad ; no-op edits have no history record
length:
    clc
    lda $8023
    adc $8025
    sta se_h_tmp
    lda $8024
    adc #0
    sta se_h_tmp+1
    pha
    lda se_h_tmp
    pha
    .repeat 3
        asl se_h_tmp
        rol se_h_tmp+1
    .endrepeat
    pla
    clc
    adc se_h_tmp
    sta se_h_tmp
    pla
    adc se_h_tmp+1
    sta se_h_tmp+1
    clc
    lda se_h_tmp
    adc #66
    sta se_h_tmp
    lda se_h_tmp+1
    adc #0
    sta se_h_tmp+1
    cmp $8007
    jne bad
    lda se_h_tmp
    cmp $8006
    jne bad
    jsr h_header_crc
    lda se_crc_value
    cmp $803A
    bne bad
    lda se_crc_value+1
    cmp $803B
    bne bad
    lda #0
    clc
    rts
bad:
    lda #$62
    sec
    rts
.endproc
.ifdef H_HEADER_WRITER
.proc h_header_save
    ldx #63
copy:
    lda se_h_record,x
    sta $8000,x
    dex
    bpl copy
    jsr h_header_crc
    lda se_crc_value
    sta se_h_record+58
    sta $803A
    lda se_crc_value+1
    sta se_h_record+59
    sta $803B
    lda #0
    sta se_h_io_pos
    sta se_h_io_pos+2
    sta se_h_io_count+1
    lda #$B0
    sta se_h_io_pos+1
    lda #64
    sta se_h_io_count
    lda #0
    jmp se_h_io
.endproc
.endif
; CRC state persists in resident frame, not the shared overlay CRC scratch.
.proc h_crc_packet
    lda se_h_crc
    sta se_crc_value
    lda se_h_crc+1
    sta se_crc_value+1
    ldy #0
loop:
    lda $8000,y
    jsr se_crc_byte
    iny
    cpy se_h_io_count
    bcc loop
    lda se_crc_value
    sta se_h_crc
    lda se_crc_value+1
    sta se_h_crc+1
    rts
.endproc
.proc h_crc_request
    lda #128
    ldx se_h_crc_left+1
    bne count
    cmp se_h_crc_left
    bcc count
    lda se_h_crc_left
count:
    sta se_h_io_count
    lda #0
    sta se_h_io_count+1
    COPY24 se_h_crc_pos,se_h_io_pos
    lda #1
    jsr se_h_io
    jcs done
    jsr h_crc_packet
    clc
    lda se_h_crc_pos
    adc se_h_io_count
    sta se_h_crc_pos
    lda se_h_crc_pos+1
    adc #0
    sta se_h_crc_pos+1
    bcc :+
    inc se_h_crc_pos+2
:
    sec
    lda se_h_crc_left
    sbc se_h_io_count
    sta se_h_crc_left
    lda se_h_crc_left+1
    sbc #0
    sta se_h_crc_left+1
    lda se_h_crc_left
    ora se_h_crc_left+1
    beq complete
    lda #1
    clc
    rts
complete:
    lda #0
    clc
 done:
    rts
.endproc
.proc h_copy_packet
    lda se_h_io_left
    sta se_h_io_count
    lda se_h_io_left+1
    sta se_h_io_count+1
    cmp #4
    bcc copy
    lda #4
    sta se_h_io_count+1
    lda #0
    sta se_h_io_count
copy:
    lda #1
    jsr se_h_io
    jcs done
    COPY24 se_h_io_pos,se_h_tmp
    COPY24 se_h_io_dest,se_h_io_pos
    lda #0
    jsr se_h_io
    jcs done
    COPY24 se_h_tmp,se_h_io_pos
    clc
    lda se_h_io_pos
    adc se_h_io_count
    sta se_h_io_pos
    lda se_h_io_pos+1
    adc se_h_io_count+1
    sta se_h_io_pos+1
    bcc :+
    inc se_h_io_pos+2
:
    clc
    lda se_h_io_dest
    adc se_h_io_count
    sta se_h_io_dest
    lda se_h_io_dest+1
    adc se_h_io_count+1
    sta se_h_io_dest+1
    bcc :+
    inc se_h_io_dest+2
:
    sec
    lda se_h_io_left
    sbc se_h_io_count
    sta se_h_io_left
    lda se_h_io_left+1
    sbc se_h_io_count+1
    sta se_h_io_left+1
    lda se_h_io_left
    ora se_h_io_left+1
    beq complete
    lda #1
    clc
    rts
complete:
    lda #0
    clc
 done:
    rts
.endproc
.segment "RODATA"
h_magic: .byte $53,$45,$48,$31
.segment "CODE"

; Deliberately isolated direct-REU callback fixture. Production binds the fold
; lane's checked editor-source adapter; this fixture is not that integration.
.setcpu "6502"
.macpack longbranch
.export se_fs_begin,se_fs_guard,se_fs_read,se_fs_end
.export se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.export fixture_epoch,fixture_stamp,fixture_owned,fixture_leases,fixture_chunk
.export fixture_reads,fixture_ends,fixture_fail,fixture_begin_fail
.segment "FIXTURE_STATE"
se_fs_offset:.res 3
se_fs_count:.res 1
se_fs_buffer:.res 2
se_fs_done:.res 1
se_fs_length:.res 3
fixture_epoch:.res 2
fixture_stamp:.res 2
fixture_owned:.res 1
fixture_leases:.res 1
fixture_chunk:.res 1
fixture_reads:.res 2
fixture_ends:.res 2
fixture_fail:.res 1
fixture_begin_fail:.res 1
.segment "CODE"
se_fs_begin:
    lda fixture_begin_fail
    bne error
    lda fixture_owned
    bne busy
    inc fixture_owned
    inc fixture_leases
    lda fixture_epoch
    sta fixture_stamp
    lda fixture_epoch+1
    sta fixture_stamp+1
    lda #0
    clc
    rts
se_fs_guard:
    lda fixture_fail
    bne error
    lda fixture_epoch
    cmp fixture_stamp
    bne stale
    lda fixture_epoch+1
    cmp fixture_stamp+1
    bne stale
    lda #0
    clc
    rts
busy:lda #$B9
    bne error
stale:lda #$B8
error:sec
    rts
se_fs_end:
    lda fixture_owned
    beq done
    lda #0
    sta fixture_owned
    inc fixture_ends
    bne :+
    inc fixture_ends+1
:   lda fixture_epoch
    cmp fixture_stamp
    bne done
    lda fixture_epoch+1
    cmp fixture_stamp+1
    bne done
    dec fixture_leases
done:lda #0
    clc
    rts
se_fs_read:
    jsr se_fs_guard
    bcs error
    inc fixture_reads
    bne :+
    inc fixture_reads+1
:   sec
    lda se_fs_length
    sbc se_fs_offset
    sta se_fs_done
    lda se_fs_length+1
    sbc se_fs_offset+1
    tax
    lda se_fs_length+2
    sbc se_fs_offset+2
    bcc argument
    ora #0
    bne @count
    cpx #0
    bne @count
    lda se_fs_done
    cmp se_fs_count
    bcc @chunk
@count:
    lda se_fs_count
    sta se_fs_done
@chunk:
    lda fixture_chunk
    beq :+
    cmp se_fs_done
    bcs :+
    sta se_fs_done
:   lda se_fs_done
    beq done
    lda se_fs_buffer
    sta $DF02
    lda se_fs_buffer+1
    sta $DF03
    lda se_fs_offset
    sta $DF04
    lda se_fs_offset+1
    sta $DF05
    lda se_fs_offset+2
    sta $DF06
    lda se_fs_done
    sta $DF07
    lda #0
    sta $DF08
    sta $DF0A
    lda #$91
    sta $DF01
    jmp done
argument:lda #$BA
    sec
    rts

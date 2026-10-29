.setcpu "6502"
.include "style/api.inc"
.include "editor_file/api.inc"
.include "fold/source.inc"
.include "render/presentation.inc"
.import se_overlay_call,se_overlay_frame
.import st_lex_phase
.export se_style_idle,se_style_input,se_style_release
.segment "CODE"
se_style_idle:
    lda se_render_caps
    beq done ;raw editing never schedules a semantic/lexical overlay
    lda #3 ;ST_AUTO; idle controller schedules one bounded planner slice
    sta se_overlay_frame
    lda #STYLE_ID
    ldx se_f_owner
    cpx #2
    bne invoke
    ldx st_lex_phase
    beq invoke
    lda #15 ;C15 lexical pass; root switches C images between idle slices
invoke:
    ldx #1
    jsr se_overlay_call
    bcc done
    jsr se_style_release
    lda #$80
    sta se_st_request ;hold failed admission for the descriptor's exact context
    rts
se_style_input:
se_style_release:
    lda #0
    sta se_st_tx+ST_TX_PHASE ;any foreground input retires ADMITTED/READY work
    lda se_f_owner
    cmp #2
    bne done ;never inspect a stale index/file union as source-provider state
    jsr se_fs_end
    ; END guarantees A0/Cclear, including epoch/graph replacement cleanup.
    sta se_st_busy
    sta se_st_valid
    sta se_st_request
    sta se_st_cp_valid       ;a cancelled builder never publishes partial carry
    sta se_f_owner
    sta st_lex_phase
done:
    rts

.setcpu "6502"
.import reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_direction, reu_banks
.import embedding_row, embedding_result
.importzp embedding_rows, embedding_index
.import matrix_project, matrix_dots
.importzp matrix_rows, dot_columns
.import vector_norm, vector_pack, vector_add, vector_count, vector_relu
.importzp vector_source, vector_dest, vector_gains
.ifdef GROUP4_EXPERIMENT
    .macpack longbranch
    .import group4_prepare, group4_ready, matrix_project_group4
.endif
.ifdef GROUP8_EXPERIMENT
    .import group8_prepare, matrix_project_group8
    .import mul8_unsigned
    .importzp mul_rhs, mul_result
.endif
.export model_open, model_open_at, model_bank, model_embed, model_project, model_norm, layer_front
.export token_id, token_pos, model_context, layer_id, residual, normalized, query, key, value
.export layer_tail, attention, hidden, projected

TILE_HEADER = 64
MATRICES = 26
GAIN_BASE = 379267
IMAGE_SIZE = GAIN_BASE + 9 * 192
BASE_CONTEXT = 128
EMBED_ROW_BYTES = 99
CONTEXT_AT = 52
.ifdef GROUP8_EXPERIMENT
    .exportzp IMAGE_END_LO, IMAGE_END_MID, IMAGE_END_HI
IMAGE_END_LO = <IMAGE_SIZE
IMAGE_END_MID = >IMAGE_SIZE
IMAGE_END_HI = ^IMAGE_SIZE
.endif

.segment "BSS"
model_ready:      .res 1
model_bank:       .res 1
directory:        .res MATRICES * 8
projection_left:  .res 2
projection_bytes: .res 1
first_matrix:     .res 1
token_id:         .res 1
token_pos:        .res 1
model_context:    .res 1
layer_id:         .res 1
residual:         .res 384
normalized:       .res 384
query:            .res 384
key:              .res 384
value:            .res 384
attention:        .res 384
hidden:           .res 1024
projected:        .res 384
.ifdef GROUP4_EXPERIMENT
group4_model:     .res 1
group4_projection: .res 1
.endif

.segment "ZEROPAGE"
output:           .res 2

.segment "RODATA"
header:
    .byte "T64M", 1, 96, 4, 4
    .word 256, MATRICES
    .dword IMAGE_SIZE, GAIN_BASE
    .byte $4b,$60,$32,$37,$07,$0a,$d9,$08,$44,$33,$53,$7b,$f8,$d6,$c7,$47
    .byte $0d,$0f,$c5,$83,$e6,$a4,$f1,$f0,$3c,$00,$cd,$17,$26,$4e,$70,$95
header_end:

; The canonical v1 directory is contiguous and sorted. Verify exact
; offsets and dimensions before any target matrix accesses.
expected_directory:
    .dword 4096
    .word 97,96
    .dword 4096+97*99
    .word 128,96
.repeat 4, L
    LayerBase .set 4096+225*99+L*(4*96*99+256*99+96*259)
    .repeat 4, M
        .dword LayerBase+M*96*99
        .word 96,96
    .endrepeat
    .dword LayerBase+4*96*99
    .word 256,96
    .dword LayerBase+4*96*99+256*99
    .word 96,256
.endrepeat
.ifdef GROUP4_EXPERIMENT
.ifdef GROUP8_EXPERIMENT
group8_matrix:
    .byte 0, 0
    .repeat 4
        .byte 2, 2, 2, 1, 2, 0
    .endrepeat
.endif
packed_matrix:
    .byte 0, 0                         ; tied embeddings and positions
    .repeat 4
        .byte 1, 1, 1, 1, 1, 0        ; Q/K/V/O/F1, with sparse F2 kept raw
    .endrepeat
.endif

.segment "CODE"
.macro POINTER dst, address
    lda #<(address)
    sta dst
    lda #>(address)
    sta dst+1
.endmacro

.proc read_tile
    POINTER reu_ram, REU_TILE
    lda #1
    sta reu_direction
    jmp reu_transfer
.endproc

; Admit fixed geometry and directory offsets. Layouts 1-3 also pin the
; upstream identity. Layout 4 supplies its own identity and context size.
; The caller must authenticate the payload before use.
model_open:
    lda #0
.proc model_open_at
    ; A is the high byte of an aligned catalog slot: $00, $10, or $20.
    cmp #0
    beq slot
    cmp #$10
    beq slot
    cmp #$20
    beq slot
    sec
    rts
slot:
    sta model_bank
    sta reu_addr+2
    lda #0
    sta model_ready
    sta logits_ready
    sta token_pos
    sta model_context
    sta reu_addr
    sta reu_addr+1
.ifdef GROUP4_EXPERIMENT
    sta group4_model
    sta group4_ready
.endif
    lda reu_banks
    cmp #2                 ; owned cache begins in region 1
    bcc failure
    cmp #33
    bcs failure
    POINTER reu_size, TILE_HEADER+MATRICES*8
    jsr read_tile
    bcs failure
.ifdef GROUP4_EXPERIMENT
    lda REU_TILE+4
    cmp #2
.ifdef GROUP8_EXPERIMENT
    beq packed
    cmp #3
    beq packed
    cmp #4
packed:
.endif
    bne :+
    sta group4_model
:
.endif
    ldx #header_end-header-1
check_header:
.ifdef GROUP4_EXPERIMENT
    cpx #4
    bne :+
    lda group4_model
    bne header_byte_ok
:
.ifdef GROUP8_EXPERIMENT
    lda group4_model
    cmp #4
    bne compare_header
    ; Layout 4 checks its image length separately and carries a model-specific SHA.
    cpx #20
    bcs header_byte_ok
    cpx #16
    bcs compare_header
    cpx #12
    bcs header_byte_ok
compare_header:
.endif
.endif
    lda REU_TILE,x
    cmp header,x
    bne failure
.ifdef GROUP4_EXPERIMENT
header_byte_ok:
.endif
    dex
    bpl check_header
    ldx #0
check_directory:
    lda REU_TILE+TILE_HEADER,x
    cmp expected_directory,x
    bne failure
    sta directory,x
    inx
    cpx #MATRICES*8
    bne check_directory
    lda #BASE_CONTEXT
.ifdef GROUP8_EXPERIMENT
    ldx group4_model
    cpx #4
    bne context_ready
    jsr extended_context
    bcs failure
context_ready:
.endif
    sta model_context
    lda #1
    sta model_ready
    clc
    rts
failure:
    sec
    rts
.endproc

.ifdef GROUP8_EXPERIMENT
; The first 128 positions and all other tensors keep their original offsets.
; Additional position rows follow the gain vectors in the same tile format.
.proc extended_context
    lda REU_TILE+CONTEXT_AT
    sec
    sbc #BASE_CONTEXT
    bcc fail
    ldy #EMBED_ROW_BYTES
    sty mul_rhs
    jsr mul8_unsigned
    clc
    adc #<IMAGE_SIZE
    tax
    lda mul_result+1
    adc #>IMAGE_SIZE
    tay
    lda #^IMAGE_SIZE
    adc #0
    cmp REU_TILE+14
    bne fail
    cpy REU_TILE+13
    bne fail
    cpx REU_TILE+12
    bne fail
    lda REU_TILE+15
    bne fail
    lda REU_TILE+CONTEXT_AT
    clc
    rts
fail:
    sec
    rts
.endproc
.endif

.proc matrix_address
    ldx model_ready
    beq failure
    cmp #MATRICES
    bcs failure
    asl
    asl
    asl
    tax
    .repeat 2, I
        lda directory+I,x
        sta reu_addr+I
    .endrepeat
    lda directory+2,x
    clc
    adc model_bank
    sta reu_addr+2
    clc
    rts
failure:
    sec
    rts
.endproc

; A selects a canonical directory index. The caller already ran
; vector_pack with the matrix's column count. Emit rows at vector_dest.
.proc model_project
    jsr matrix_address
.ifdef GROUP4_EXPERIMENT
    jcs fail
    lda directory+6,x
    cmp dot_columns
    jne fail
.else
    bcs fail
    lda directory+6,x
    cmp dot_columns
    bne fail
.endif
.ifdef GROUP4_EXPERIMENT
    lda #0
    sta group4_projection
    lda group4_model
    beq layout_ready
    txa
    lsr
    lsr
    lsr
    tay
    lda packed_matrix,y
.ifdef GROUP8_EXPERIMENT
    beq layout_ready
    lda group4_model
    cmp #3
    bcc group_four
    lda group8_matrix,y
    bne select_kernel
group_four:
    lda #1
select_kernel:
    sta group4_projection
    cmp group4_ready
    beq layout_ready
    txa
    pha
    lda group4_projection
    cmp #2
    bne prepare_four
    jsr group8_prepare
    jmp restore_directory
prepare_four:
    jsr group4_prepare
restore_directory:
    pla
    tax
    jcs fail
.else
    beq layout_ready
    lda group4_ready
    bne packed
    txa
    pha
    jsr group4_prepare
    pla
    tax
    bcs fail
packed:
    inc group4_projection
.endif
layout_ready:
.endif
    lda directory+4,x
    sta projection_left
    lda directory+5,x
    sta projection_left+1
    lda vector_dest
    sta output
    lda vector_dest+1
    sta output+1
tile:
    lda projection_left+1
    bne full_tile
    lda projection_left
    cmp #16
    bcc selected
full_tile:
    lda #16
selected:
    sta matrix_rows
    asl
    asl
    sta projection_bytes
.ifdef GROUP4_EXPERIMENT
    lda group4_projection
    beq raw_tile
.ifdef GROUP8_EXPERIMENT
    cmp #2
    bne four_tile
    jsr matrix_project_group8
    jmp projection_status
four_tile:
.endif
    jsr matrix_project_group4
    jmp projection_status
raw_tile:
.endif
    jsr matrix_project
.ifdef GROUP4_EXPERIMENT
projection_status:
.endif
    bcs done
    ldy #0
copy:
    lda matrix_dots,y
    sta (output),y
    iny
    cpy projection_bytes
    bne copy
    clc
    tya
    adc output
    sta output
    bcc :+
    inc output+1
:
    sec
    lda projection_left
    sbc matrix_rows
    sta projection_left
    lda projection_left+1
    sbc #0
    sta projection_left+1
    ora projection_left
    bne tile
    clc
done:
    rts
fail:
    sec
    rts
.endproc

; Sum the token and position rows directly in target RAM.
.proc model_embed
    lda token_id
    cmp #97
    bcs failure
    sta embedding_index
    lda token_pos
    cmp model_context
    bcc valid
failure:
    rts
valid:
    lda #0
    jsr matrix_address
    bcs done
    lda #97
    sta embedding_rows
    jsr embedding_row
    bcs done
    ldx #0
copy:
    lda embedding_result,x
    sta residual,x
    cpx #128
    bcs :+
    lda embedding_result+256,x
    sta residual+256,x
:
    inx
    bne copy
    lda token_pos
    cmp #BASE_CONTEXT
    bcc base_position
    sbc #BASE_CONTEXT
    sta embedding_index
    lda model_context
    sec
    sbc #BASE_CONTEXT
    sta embedding_rows
    POINTER reu_addr, IMAGE_SIZE
    lda #^IMAGE_SIZE
    clc
    adc model_bank
    sta reu_addr+2
    jmp read_position
base_position:
    lda #1
    jsr matrix_address
    bcs done
    lda #BASE_CONTEXT
    sta embedding_rows
    lda token_pos
    sta embedding_index
read_position:
    jsr embedding_row
    bcs done
    POINTER vector_source, embedding_result
    POINTER vector_dest, residual
    lda #96
    sta vector_count
    jsr vector_add
    clc
done:
    rts
.endproc

; A selects gain vector 2*layer (+1 for FFN), or 8 for final norm.
; The CPU's DMA tile holds the gains during the normalization.
.proc model_norm
    ldx model_ready
    beq failure
    cmp #9
    bcs failure
    tax
    lda #<GAIN_BASE
    sta reu_addr
    lda #>GAIN_BASE
    sta reu_addr+1
    lda #^GAIN_BASE
    clc
    adc model_bank
    sta reu_addr+2
    cpx #0
    beq load
offset:
    clc
    lda reu_addr
    adc #192
    sta reu_addr
    bcc :+
    inc reu_addr+1
    bne :+
    inc reu_addr+2
:
    dex
    bne offset
load:
    POINTER reu_size, 192
    jsr read_tile
    bcs done
    POINTER vector_gains, REU_TILE
    lda #96
    sta vector_count
    jmp vector_norm
failure:
    sec
done:
    rts
.endproc

; Check layer_id and return its Q directory index in A.
.proc layer_matrix_index
    lda layer_id
    cmp #4
    bcs done
    asl
    tax
    asl
    sta first_matrix
    txa
    clc
    adc first_matrix
    adc #2
    clc
done:
    rts
.endproc

; Normalize the current residual and project Q/K/V for the selected
; layer. The single packed vector is reused for all three matrices.
.proc layer_front
    jsr layer_matrix_index
    bcs done
    sta first_matrix
    POINTER vector_source, residual
    POINTER vector_dest, normalized
    lda layer_id
    asl
    jsr model_norm
    bcs done
    POINTER vector_source, normalized
    jsr vector_pack

    POINTER vector_dest, query
    lda first_matrix
    jsr model_project
    bcs done
    POINTER vector_dest, key
    inc first_matrix
    lda first_matrix
    jsr model_project
    bcs done
    POINTER vector_dest, value
    inc first_matrix
    lda first_matrix
    jmp model_project
done:
    rts
.endproc

; Project attention through O, add its residual, and run the complete
; feed-forward path. The causal attention kernel supplies attention[].
.proc layer_tail
    jsr layer_matrix_index
    bcc start
    rts
start:
    adc #3
    sta first_matrix
    POINTER vector_source, attention
    lda #96
    sta vector_count
    jsr vector_pack
    POINTER vector_dest, projected
    lda first_matrix
    jsr model_project
    bcs done
    jsr add_projection

    POINTER vector_source, residual
    POINTER vector_dest, normalized
    lda layer_id
    asl
    ora #1
    jsr model_norm
    bcs done
    POINTER vector_source, normalized
    jsr vector_pack

    POINTER vector_dest, hidden
    inc first_matrix
    lda first_matrix
    jsr model_project
    bcs done
    lda #0
    sta vector_count
    jsr vector_relu
    POINTER vector_source, hidden
    jsr vector_pack

    POINTER vector_dest, projected
    inc first_matrix
    lda first_matrix
    jsr model_project
    bcs done
    jsr add_projection
    clc
done:
    rts
.endproc

.proc add_projection
    POINTER vector_source, projected
    POINTER vector_dest, residual
    lda #96
    sta vector_count
    jmp vector_add
.endproc

.import cache_store, cache_attention
.export model_first_token, model_reset, model_ingest, model_choose, logits

.segment "BSS"
logits: .res 97*4
want_logits: .res 1
logits_ready: .res 1
best_token: .res 1
best_score: .res 4
candidate:  .res 1

.segment "CODE"
; Cache records at and beyond the reset position are invalid until written.
.proc model_reset
    lda #0
    sta token_pos
    sta logits_ready
    rts
.endproc

; Convenience entry for a single-token test. Input token_id, position zero.
.proc model_first_token
    jsr model_reset
    lda token_id
    ldx #1
    jmp model_ingest
.endproc

; A is the input token. X=0 does prefill only, X=1 calculates logits.
; Carry reports failure. Only advance the causal position on success.
.proc model_ingest
    ldy #0
    sty logits_ready
    cmp #97
    bcs failure
    cpx #2
    bcs failure
    sta token_id
    stx want_logits
    sty layer_id
    jsr model_embed
    bcs done
layer:
    jsr layer_front
    bcs done
    jsr cache_store
    bcs done
    jsr cache_attention
    bcs done
    jsr layer_tail
    bcs done
    inc layer_id
    lda layer_id
    cmp #4
    bcc layer
    lda want_logits
    beq advance
    POINTER vector_source, residual
    POINTER vector_dest, normalized
    lda #8
    jsr model_norm
    bcs done
    POINTER vector_source, normalized
    jsr vector_pack
    POINTER vector_dest, logits
    lda #0
    jsr model_project
    bcs done
    inc logits_ready
advance:
    inc token_pos
    clc
done:
    rts
failure:
    sec
    rts
.endproc

; Return the lowest token ID attaining the maximum signed logit.
; Carry set until a successful ingest requested logits.
.proc model_choose
    lda logits_ready
    bne ready
    sec
    rts
ready:
    lda #0
    sta best_token
    sta candidate
    POINTER output, logits
    ldy #0
    .repeat 4, I
        lda (output),y
        sta best_score+I
        iny
    .endrepeat
    lda best_score+3
    eor #$80
    sta best_score+3
advance:
    inc candidate
    lda candidate
    cmp #97
    beq done
    clc
    lda output
    adc #4
    sta output
    bcc :+
    inc output+1
:
    ldy #3
    lda (output),y
    eor #$80
    cmp best_score+3
    bcc advance
    bne replace
lower_bytes:
    dey
    bmi advance
    lda (output),y
    cmp best_score,y
    bcc advance
    beq lower_bytes
replace:
    lda candidate
    sta best_token
    ldy #0
    .repeat 4, I
        lda (output),y
        sta best_score+I
        iny
    .endrepeat
    lda best_score+3
    eor #$80
    sta best_score+3
    jmp advance
done:
    lda best_token
    clc
    rts
.endproc

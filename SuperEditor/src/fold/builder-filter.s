.setcpu "6502"
.macpack longbranch
.include "fold/builder.inc"
.segment "FOLD_BUILD_FILTER"
; D093: exact explicit/fence intervals win. Only crossed heading projections
; are omitted; parser/style semantics and every canonical byte are unchanged.
se_fb_filter_step:
    lda se_fb_scan
    cmp se_fb_raw_count
    jne @read
    lda se_fb_scan+1
    cmp se_fb_raw_count+1
    jne @read
    lda #0
    sta se_fb_scan
    sta se_fb_scan+1
    sta se_fb_depth
    lda #FB_COMPACT
    sta se_fb_phase
    clc
    rts
@read:
    SF_COPY se_fb_scan,se_fold_index,2
    jsr se_fold_read
    jcs se_fb_fail
    SF_COPY se_fold_record+SF_SUMMARY,se_fb_start,3
    SF_COPY se_fold_record+SF_END,se_fb_end,3
    lda se_fold_record+SF_KIND
    sta se_fb_kind
    ; Remove expired heading intervals and explicit scopes from active stacks.
@pop_h:
    lda se_fb_heads
    jeq @pop_e
    sec
    sbc #1
    asl
    clc
    adc se_fb_heads
    sec
    sbc #1
    tax
    lda FB_H_END,x
    sta se_fold_temp
    lda FB_H_END+1,x
    sta se_fold_temp+1
    lda FB_H_END+2,x
    sta se_fold_temp+2
    SF_LT se_fb_start,se_fold_temp,@pop_e
    dec se_fb_heads
    jmp @pop_h
@pop_e:
    lda se_fb_regions
    jeq @kind
    sec
    sbc #1
    asl
    clc
    adc se_fb_regions
    sec
    sbc #1
    tax
    lda FB_E_END,x
    sta se_fold_temp
    lda FB_E_END+1,x
    sta se_fold_temp+1
    lda FB_E_END+2,x
    sta se_fold_temp+2
    SF_LT se_fb_start,se_fold_temp,@kind
    dec se_fb_regions
    jmp @pop_e
@kind:
    lda se_fb_kind
    cmp #SF_HEADING
    jne @explicit
    ; A heading with no bytes after its opener is not a fold.
    SF_GE se_fold_record+SF_HIDDEN,se_fb_end,@empty
    lda #0
    sta se_fb_slot
    lda se_fb_regions
    jeq @push_h
    sec
    sbc #1
    asl
    clc
    adc se_fb_regions
    sec
    sbc #1
    tax
    lda FB_E_END,x
    sta se_fold_temp
    lda FB_E_END+1,x
    sta se_fold_temp+1
    lda FB_E_END+2,x
    sta se_fold_temp+2
    SF_GE se_fold_temp,se_fb_end,@push_h
    ; Heading begins within explicit interval and ends outside it.
    lda #$80
    sta se_fold_record+SF_FLAGS
    jsr se_fold_write
    jcs se_fb_fail
    jsr omitted
    lda #1
    sta se_fb_slot
@push_h:
    ldx se_fb_heads
    cpx #6
    jcs @depth
    lda se_fb_slot
    sta FB_H_OMIT,x
    txa
    asl
    tax
    lda se_fb_scan
    sta FB_H_INDEX,x
    lda se_fb_scan+1
    sta FB_H_INDEX+1,x
    txa
    clc
    adc se_fb_heads
    tax
    lda se_fb_end
    sta FB_H_END,x
    lda se_fb_end+1
    sta FB_H_END+1,x
    lda se_fb_end+2
    sta FB_H_END+2,x
    inc se_fb_heads
    jmp next_filter
@empty:
    lda #$80
    sta se_fold_record+SF_FLAGS
    jsr se_fold_write
    jcs se_fb_fail
    inc se_fb_empty
    bne :+
    inc se_fb_empty+1
:   jmp next_filter
@explicit:
    ; Explicit intervals may nest or be disjoint, never cross each other.
    lda se_fb_regions
    jeq @mark
    SF_LT se_fold_temp,se_fb_end,@bad
@mark:
    lda #0
    sta se_fb_slot
    lda #FB_MARK
    sta se_fb_phase
    clc
    rts
@depth:
    lda #FB_DEPTH
    jmp se_fb_fail
@bad:
    lda #SF_BAD
    jmp se_fb_fail

se_fb_mark_step:
    ldx se_fb_slot
    cpx se_fb_heads
    jcs @push_e
    lda FB_H_OMIT,x
    jne @next
    txa
    asl
    clc
    adc se_fb_slot
    tax
    lda FB_H_END,x
    sta se_fold_temp
    lda FB_H_END+1,x
    sta se_fold_temp+1
    lda FB_H_END+2,x
    sta se_fold_temp+2
    SF_GE se_fold_temp,se_fb_end,@next
    ; Explicit interval begins inside heading and ends outside it.
    lda se_fb_slot
    asl
    tax
    lda FB_H_INDEX,x
    sta se_fold_index
    lda FB_H_INDEX+1,x
    sta se_fold_index+1
    jsr se_fold_read
    jcs se_fb_fail
    lda #$80
    sta se_fold_record+SF_FLAGS
    jsr se_fold_write
    jcs se_fb_fail
    ldx se_fb_slot
    lda #1
    sta FB_H_OMIT,x
    jsr omitted
@next:
    inc se_fb_slot
    clc
    rts
@push_e:
    lda se_fb_regions
    cmp #16
    jcs @depth
    asl
    clc
    adc se_fb_regions
    tax
    lda se_fb_end
    sta FB_E_END,x
    lda se_fb_end+1
    sta FB_E_END+1,x
    lda se_fb_end+2
    sta FB_E_END+2,x
    inc se_fb_regions
    jmp next_filter
@depth:
    lda #FB_DEPTH
    jmp se_fb_fail
omitted:
    inc se_fb_omitted
    bne :+
    inc se_fb_omitted+1
:   rts
next_filter:
    inc se_fb_scan
    bne :+
    inc se_fb_scan+1
:   lda #FB_FILTER
    sta se_fb_phase
    clc
    rts

se_fb_compact_step:
    lda se_fb_scan
    cmp se_fb_raw_count
    jne @read
    lda se_fb_scan+1
    cmp se_fb_raw_count+1
    jne @read
    jmp se_fb_finish_build
@read:
    SF_COPY se_fb_scan,se_fold_index,2
    jsr se_fold_read
    jcs se_fb_fail
    lda se_fold_record+SF_FLAGS
    jne @next
@pop:
    lda se_fb_depth
    jeq @root
    sec
    sbc #1
    asl
    clc
    adc se_fb_depth
    sec
    sbc #1
    tax
    lda se_fold_stack_end,x
    sta se_fold_temp
    lda se_fold_stack_end+1,x
    sta se_fold_temp+1
    lda se_fold_stack_end+2,x
    sta se_fold_temp+2
    SF_LT se_fold_record+SF_SUMMARY,se_fold_temp,@child
    dec se_fb_depth
    jmp @pop
@root:
    lda #$FF
    sta se_fold_record+SF_PARENT
    sta se_fold_record+SF_PARENT+1
    jne @push
@child:
    lda se_fb_depth
    sec
    sbc #1
    asl
    tax
    lda se_fold_stack_index,x
    sta se_fold_record+SF_PARENT
    lda se_fold_stack_index+1,x
    sta se_fold_record+SF_PARENT+1
@push:
    lda se_fb_depth
    cmp #16
    jcs @depth
    sta se_fold_record+SF_DEPTH
    asl
    tax
    lda se_fb_count
    sta se_fold_stack_index,x
    lda se_fb_count+1
    sta se_fold_stack_index+1,x
    txa
    clc
    adc se_fb_depth
    tax
    lda se_fold_record+SF_END
    sta se_fold_stack_end,x
    lda se_fold_record+SF_END+1
    sta se_fold_stack_end+1,x
    lda se_fold_record+SF_END+2
    sta se_fold_stack_end+2,x
    SF_COPY se_fb_count,se_fold_index,2
    jsr se_fold_write
    jcs se_fb_fail
    inc se_fb_depth
    inc se_fb_count
    jne @next
    inc se_fb_count+1
@next:
    inc se_fb_scan
    bne :+
    inc se_fb_scan+1
:   clc
    rts
@depth:
    lda #FB_DEPTH
    jmp se_fb_fail

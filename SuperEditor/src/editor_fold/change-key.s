.setcpu "6502"
.macpack longbranch
SE_EF_CHANGE_IMPLEMENTATION=1
.include "editor_fold/change-key.inc"
.export se_ef_change_pending,se_ef_change_publication
F=se_ef_change_frame
S=F+EFC_SCRATCH
R=F+EFC_RESULT
.macro EQ left,right,size
 ldx #size-1
:
 lda left,x
 cmp right,x
 jne changed
 dex
 bpl :-
.endmacro
.macro COPY from,to,size
 ldx #size-1
:
 lda from,x
 sta to,x
 dex
 bpl :-
.endmacro
.segment "FOLD_CHANGE"
; Common full graph/epoch and idle state gate. External capture validates the
; actual token objects; no rawbank or derived renderer damage enters this ABI.
common:
 lda #0
 sta F+EFC_VALID
 lda F+EFC_AUTH
 cmp #$A5
 jne provenance
 lda F+EFC_BUSY
 jne changed
 EQ F+EFC_OLD,F+EFC_CURRENT,15
 EQ F+EFC_OLD+24,F+EFC_CURRENT+24,4
 clc
 rts
se_ef_change_pending:
 jsr common
 jcs return
 lda F+EFC_READY
 cmp #1
 jne changed
 lda F+EFC_PENDING
 cmp #1
 jne changed
 lda F+EFC_PHASE
 ora F+EFC_FAULT
 jne changed
 EQ F+EFC_OLD+15,F+EFC_CURRENT+15,2
 EQ F+EFC_HOT_ORIGINAL,F+EFC_OLD+5,10
 EQ F+EFC_HOT_GENERATION,F+EFC_OLD+15,2
 ; hot_epoch is object/provider service epoch, captured with validated keys.
 EQ F+EFC_HOT_EPOCH,F+EFC_OLD+24,2
 EQ F+EFC_DOC_LENGTH,F+EFC_OLD+21,3
 ; Strictly newer32-bit revision; equality and wrap both refuse retention.
 ldx #3
@revision:
 lda F+EFC_CURRENT+17,x
 cmp F+EFC_OLD+17,x
 bne @different
 dex
 bpl @revision
 jmp changed
@different:
 jcc changed
 ; Bounds: old/currentwindow <=2048, left<=right<=2048.
 ldx #EFC_OLD_LENGTH
 jsr bound2048
 jcs range
 ldx #EFC_LENGTH
 jsr bound2048
 jcs range
 ldx #EFC_RIGHT
 jsr bound2048
 jcs range
 lda F+EFC_LEFT+1
 cmp F+EFC_RIGHT+1
 jcc @gap
 jne range
 lda F+EFC_LEFT
 cmp F+EFC_RIGHT
 jcc @gap
 jne range
@gap:
 ; Current length must exactly match physical gap shape.
 sec
 lda F+EFC_LEFT
 sbc F+EFC_RIGHT
 sta S
 lda F+EFC_LEFT+1
 sbc F+EFC_RIGHT+1
 clc
 adc #8
 cmp F+EFC_LENGTH+1
 jne range
 lda S
 cmp F+EFC_LENGTH
 jne range
 ; Stable edges must fit both old and current windows.
 clc
 lda F+EFC_PREFIX
 adc F+EFC_SUFFIX
 sta S
 lda F+EFC_PREFIX+1
 adc F+EFC_SUFFIX+1
 sta S+1
 jcs range
 lda S+1
 cmp F+EFC_OLD_LENGTH+1
 jcc @newedges
 jne range
 lda S
 cmp F+EFC_OLD_LENGTH
 jcc @newedges
 jne range
@newedges:
 lda S+1
 cmp F+EFC_LENGTH+1
 jcc @tuple
 jne range
 lda S
 cmp F+EFC_LENGTH
 jcc @tuple
 jne range
@tuple:
 ; Candidate tuple is staged in REQUEST? No: all inputs immutable. Use output
 ; only after shape arithmetic has been proven, retaining failure atomicity.
 ; First check base+oldwindow <= committed source.
 clc
 lda F+EFC_BASE
 adc F+EFC_OLD_LENGTH
 sta S+2
 lda F+EFC_BASE+1
 adc F+EFC_OLD_LENGTH+1
 sta S+3
 lda F+EFC_BASE+2
 adc #0
 sta S+4
 jcs range
 ldx #2
@within:
 lda S+2,x
 cmp F+EFC_DOC_LENGTH,x
 jcc @merged
 jne range
 dex
 bpl @within
@merged:
 ; visiblelength = committedlength-oldwindow+newwindow
 sec
 lda F+EFC_DOC_LENGTH
 sbc F+EFC_OLD_LENGTH
 sta S+2
 lda F+EFC_DOC_LENGTH+1
 sbc F+EFC_OLD_LENGTH+1
 sta S+3
 lda F+EFC_DOC_LENGTH+2
 sbc #0
 sta S+4
 jcc range
 clc
 lda S+2
 adc F+EFC_LENGTH
 sta S+2
 lda S+3
 adc F+EFC_LENGTH+1
 sta S+3
 lda S+4
 adc #0
 sta S+4
 jcs range
 EQ S+2,F+EFC_CURRENT+21,3
 ; All possible failures are past. Publish exact conservative replacement.
 clc
 lda F+EFC_BASE
 adc F+EFC_PREFIX
 sta R
 lda F+EFC_BASE+1
 adc F+EFC_PREFIX+1
 sta R+1
 lda F+EFC_BASE+2
 adc #0
 sta R+2
 sec
 lda F+EFC_OLD_LENGTH
 sbc S
 sta R+3
 lda F+EFC_OLD_LENGTH+1
 sbc S+1
 sta R+4
 sec
 lda F+EFC_LENGTH
 sbc S
 sta R+6
 lda F+EFC_LENGTH+1
 sbc S+1
 sta R+7
 lda #0
 sta R+5
 sta R+8
 jmp success
bound2048:
 lda F+1,x
 cmp #8
 bcc @ok
 bne @bad
 lda F,x
 beq @ok
@bad:
 sec
 rts
@ok:
 clc
 rts

se_ef_change_publication:
 jsr common
 jcs return
 lda F+EFC_KIND
 jeq provenance
 cmp #5
 jcs provenance
 lda F+EFC_PENDING
 ora F+EFC_PHASE
 ora F+EFC_FAULT
 jne changed
 ; Ticket and committed generation each advance exactly once, no wrap.
 clc
 .repeat 4,I
 lda F+EFC_BEFORE_TICKET+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta S+I
 .endrepeat
 jcs provenance
 ldx #3
@ticket_match:
 lda S,x
 cmp F+EFC_AFTER_TICKET,x
 jne provenance
 dex
 bpl @ticket_match
 clc
 lda F+EFC_OLD+15
 adc #1
 sta S
 lda F+EFC_OLD+16
 adc #0
 sta S+1
 jcs changed
 EQ S,F+EFC_CURRENT+15,2
 ; Request position+delete must fit OLD length.
 clc
 .repeat 3,I
 lda F+EFC_REQUEST+I
 adc F+EFC_REQUEST+3+I
 sta S+I
 .endrepeat
 jcs range
 ldx #2
@requestbound:
 lda S,x
 cmp F+EFC_OLD+21,x
 jcc @newlength
 jne range
 dex
 bpl @requestbound
@newlength:
 sec
 .repeat 3,I
 lda F+EFC_OLD+21+I
 sbc F+EFC_REQUEST+3+I
 sta S+I
 .endrepeat
 jcc range
 clc
 .repeat 3,I
 lda S+I
 adc F+EFC_REQUEST+6+I
 sta S+I
 .endrepeat
 jcs range
 EQ S,F+EFC_CURRENT+21,3
 EQ F+EFC_DOC_LENGTH,F+EFC_CURRENT+21,3
 COPY F+EFC_REQUEST,R,9
success:
 lda #1
 sta F+EFC_VALID
 lda #0
 clc
return:
 rts
changed:
 lda #EFC_CHANGED
 sec
 rts
range:
 lda #EFC_RANGE
 sec
 rts
provenance:
 lda #EFC_PROVENANCE
 sec
 rts

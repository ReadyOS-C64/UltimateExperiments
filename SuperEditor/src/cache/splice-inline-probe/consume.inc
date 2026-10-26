; Called only after full mapped classification and query_final succeeded.
; The actual mapped CR is held with its base-ticket+relative INLINE references.
inline_begin:
 lda S_ORIGIN
 jne inline_miss ;dirty CR is never interpreted as unchanged INLINE authority
 lda S_CR+3
 cmp #4
 jcs inline_miss
 lda S_CR+2
 and #4
 jeq inline_miss
 lda S_CR+46
 jne inline_miss ;bounded initial event count16, preserves larger fallback
 .ifdef I_SPARSE_INLINE
 lda S_CR+45
 jne inline_miss
 lda S_CR+44
 cmp #9
 jcs inline_miss
 .endif
 CP S_CR+44,I_COUNT,3
 CP S_CR+40,I_REF,4
 lda I_COUNT
 ora I_COUNT+1
 beq @empty
 lda I_REF
 and I_REF+1
 and I_REF+2
 and I_REF+3
 cmp #$FF
 jeq corrupt
 jmp @ranges
@empty:
 lda I_REF
 and I_REF+1
 and I_REF+2
 and I_REF+3
 cmp #$FF
 jne corrupt
@ranges:
 EQ S_CR+16,SQ_FRAME+GSEM_START,3
 EQ S_END,SQ_FRAME+GSEM_END,3
 clc
 .repeat 3,I
 lda S_CR+16+I
 adc S_CR+22+I
 sta I_POS+I
 .endrepeat
 jcs failed_stale
 EQ I_POS,SQ_FRAME+GSEM_BODY,3
 sec
 .repeat 3,I
 lda SQ_FRAME+GSEM_QUERY+I
 sbc S_CR+16+I
 sta I_REL+I
 .endrepeat
 jcc failed_stale
 clc
 lda SQ_FRAME+GSEM_QUERY
 adc SQ_FRAME+GSEM_COUNT
 sta I_POS
 lda SQ_FRAME+GSEM_QUERY+1
 adc #0
 sta I_POS+1
 lda SQ_FRAME+GSEM_QUERY+2
 adc #0
 sta I_POS+2
 jcs failed_stale
 C24 S_READER+10,I_POS
 jcc failed_stale
 ; Only now clobber inactive root/manifest staging, after final proof.
 lda #0
 ldx #160
@styles:sta IS,x
 dex
 cpx #$FF
 bne @styles
 ldx #20
@hide:sta IH,x
 dex
 bpl @hide
 ldx #18
@inputs:lda SQ_FRAME,x
 sta IP,x
 dex
 bpl @inputs
 ; IO aliases the first ten old output roles; preserve all of them until END.
 ldx #9
@old:lda $9030,x
 sta IR,x
 dex
 bpl @old
 ldx SQ_FRAME+GSEM_COUNT
 beq @done_roles
 dex
 lda SQ_FRAME+GSEM_ROLE
@roles:sta IR,x
 dex
 cpx #$FF
 bne @roles
@done_roles:
 lda I_COUNT
 ora I_COUNT+1
 jeq inline_finish
 jmp inline_page
inline_page:
 lda I_REF
 sta BCA_PAGE
 lda #2
 sta BCA_KIND
 CP I_REF+2,BCA_GENERATION,2
 lda #9
 jsr helper
 jcs failed
 lda #9
 sta S_STATE
 jmp pending
inline_step:
 lda S_ABI
 cmp #S_PROOF
 jne failed_stale
 ldx #18
@inputs:lda SQ_FRAME,x
 cmp IP,x
 jne failed_stale
 dex
 bpl @inputs
 CP BC_IO,S_PACKET,10
 jsr guard
 jcs failed
 CP S_PACKET,BC_IO,10
 lda S_STATE
 cmp #9
 beq @page
 cmp #10
 beq inline_read
 cmp #11
 jeq inline_paint
 jmp failed_stale
@page:
 lda #10
 jsr helper
 jcs failed
 cmp #0
 jne pending
 lda #10
 sta S_STATE
 jmp pending
inline_read:
 lda I_REF+1
 cmp I_SLOTS
 jcs failed_corrupt
 ; Certified page payload offset = page*4096+64+slot*10.
 lda I_REF
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 lda I_REF
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 lda #64
 sta BCA_OFFSET
 ldx I_REF+1
 beq @offset
@times:clc
 lda BCA_OFFSET
 adc #10
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:dex
 bne @times
@offset:
 lda #10
 sta BCA_LENGTH
 lda #3
 jsr helper
 jcs failed
 ; Exact old event schema, with relative bounds against the authenticated CR.
 lda BC_IO+9
 jne failed_corrupt
 lda BC_IO
 cmp #1
 beq @pair
 cmp #2
 jne failed_corrupt
 lda BC_IO+1
 jne failed_corrupt
 lda BC_IO+2
 cmp #1
 jne failed_corrupt
 jmp @bounds
@pair:
 lda BC_IO+1
 cmp #1
 jcc failed_corrupt
 cmp #5
 jcs failed_corrupt
 cmp #4
 bne @normal
 lda BC_IO+2
 cmp #2
 jne failed_corrupt
 jmp @bounds
@normal:
 cmp BC_IO+2
 jne failed_corrupt
@bounds:
 C24 BC_IO+3,S_CR+22
 jcc failed_corrupt
 clc
 lda BC_IO+3
 adc BC_IO+2
 sta I_FROM
 lda BC_IO+4
 adc #0
 sta I_FROM+1
 lda BC_IO+5
 adc #0
 sta I_FROM+2
 jcs failed_corrupt
 C24 I_FROM,BC_IO+6
 bcc @space
 jne failed_corrupt
 jmp @close
@space:
 lda BC_IO
 cmp #2
 jeq failed_corrupt
@close:
 clc
 lda BC_IO+6
 adc BC_IO+2
 sta I_TO
 lda BC_IO+7
 adc #0
 sta I_TO+1
 lda BC_IO+8
 adc #0
 sta I_TO+2
 jcs failed_corrupt
 C24 I_TO,S_CR+19
 bcc @checked
 jne failed_corrupt
@checked:
 ; Events are not sorted by source offset (nested pairs close first).
 ; Skip only this disjoint event, never the remaining authenticated stream.
 C24 I_TO,I_REL
 jcc inline_ack
 jeq inline_ack
 clc
 lda I_REL
 adc IP+GSEM_COUNT
 sta S_QUERY
 lda I_REL+1
 adc #0
 sta S_QUERY+1
 lda I_REL+2
 adc #0
 sta S_QUERY+2
 jcs failed_corrupt
 C24 BC_IO+3,S_QUERY
 jcs inline_ack
 CP I_REL,I_POS,3
 lda #0
 sta I_INDEX
 C24 BC_IO+3,I_REL
 bcc @origin
 CP BC_IO+3,I_POS,3
 sec
 lda I_POS
 sbc I_REL
 sta I_INDEX
@origin:
 lda BC_IO+1
 cmp #4
 bne @style
 lda #$80
 bne @save
@style:
 lsr
 and #1
 sta I_STYLE
 lda BC_IO+1
 and #1
 asl
 ora I_STYLE
@save:sta I_STYLE
 lda #11
 sta S_STATE
inline_paint:
 lda #32
 sta I_BUDGET
@cell:
 C24 I_POS,I_TO
 jcs inline_ack
 lda I_INDEX
 cmp IP+GSEM_COUNT
 jeq inline_ack
 C24 I_POS,BC_IO+3
 bcc @next
 C24 I_POS,I_FROM
 bcc @hidden
 lda BC_IO
 cmp #2
 beq @next
 C24 I_POS,BC_IO+6
 bcc @ink
 C24 I_POS,I_TO
 bcs @next
@hidden:
 lda I_INDEX
 and #7
 tay
 lda I_INDEX
 lsr
 lsr
 lsr
 tax
 lda inline_bits,y
 ora IH,x
 sta IH,x
 jmp @next
@ink:
 ldx I_INDEX
 lda I_STYLE
 bmi @code
 lda IS,x
 bmi @next
 ora I_STYLE
 sta IS,x
 jmp @next
@code:
 sta IS,x
 lda #4
 sta IR,x
@next:
 inc I_INDEX
 INC24 I_POS
 dec I_BUDGET
 jne @cell
 jmp pending
inline_ack:
 ; Source guard must run only after held IO is drained. Next entry may R14.
 lda I_COUNT
 bne :+
 dec I_COUNT+1
:dec I_COUNT
 lda I_COUNT
 ora I_COUNT+1
 jeq inline_finish
 inc I_REF+1
 lda I_REF+1
 cmp I_SLOTS
 bcc @same
 lda I_NEXT
 cmp I_REF
 jcc failed_corrupt
 jeq failed_corrupt
 CP I_NEXT,I_REF,4
 jmp inline_page
@same:
 lda #10
 sta S_STATE
 jmp pending
inline_finish:
 ; End lease before publication: no further source call may refill IO/roles.
 jsr guard
 jcs failed
 jsr release
 ldx #0
@out:
 cpx IP+GSEM_COUNT
 beq @mask
 lda IS,x
 and #3
 sta GI_OUTPUT_STYLES,x
 lda IR,x
 cpx #160
 beq @last
 sta GI_OUTPUT_ROLES,x
 jmp @next
@last:sta GI_OUTPUT_ROLE_LAST
@next:inx
 bne @out
@mask:
 ldx #9
@oldroles:lda IR,x
 sta GI_OUTPUT_ROLES,x
 dex
 bpl @oldroles
 ldx #20
@bits:lda IH,x
 sta GI_OUTPUT_HIDDEN,x
 dex
 bpl @bits
 lda #0
 sta SQ_FRAME+GSEM_ERROR
 sta GI_ACTIVE
 sta SQ_FRAME+GSEM_ACTIVE
 lda I_RETURN
 sta $9135
 lda #1
 sta $9136
 lda #1
 clc
 rts
inline_miss:
 jsr release
 lda #26
 sta $9135
 lda I_RETURN
 cmp #20
 bne @normal
 lda #5 ;real SOURCE fallback, never delegates again
 bne @op
@normal:
 lda SQ_FRAME+GSEM_COUNT
 cmp #161
 beq @wide
 lda #0
 beq @op
@wide:lda #4
@op:sta $9136
 lda #1
 clc
 rts
inline_bits:.byte $80,$40,$20,$10,$08,$04,$02,$01

inline_argument:lda #$C0
 sec
 rts

; R24 read-only folded-source projection; persistent warm scratch, no allocation.
.ifndef SE_GEOS_FOLD_QUERY
SE_GEOS_FOLD_QUERY=1
GFQ_ID=24
GFQ_BEGIN=0
GFQ_STEP=1
GFQ_CANCEL=2
GFQ_STATE=$CF00
GFQ_QUERY=GFQ_STATE           ;3B canonical input, inclusive source EOF allowed
GFQ_MODE=GFQ_STATE+3          ;0 normalize hidden->summary,1 forward hidden->end
GFQ_RESULT=GFQ_STATE+4        ;3B success only
GFQ_HIDDEN=GFQ_STATE+7
GFQ_SELECTED=GFQ_STATE+8      ;canonical marked range intersects matched hidden body
GFQ_SUMMARY=GFQ_STATE+9       ;matched record, zero if visible
GFQ_BODY=GFQ_STATE+12
GFQ_END=GFQ_STATE+15
GFQ_ACTIVE=GFQ_STATE+18
GFQ_ERROR=GFQ_STATE+19
GFQ_INDEX=GFQ_STATE+20        ;2B private, one record max per STEP
GFQ_TOKEN=GFQ_STATE+22        ;5B bound published map token
GFQ_COUNT=GFQ_STATE+27        ;2B
GFQ_GENERATION=GFQ_STATE+29   ;2B fold mutation/publication serial
GFQ_LENGTH=GFQ_STATE+31      ;3B canonical merged source length
GFQ_BOUND_QUERY=GFQ_STATE+34 ;3B inputs remain immutable across pending STEPs
GFQ_BOUND_MODE=GFQ_STATE+37
GFQ_SELECT_A=GFQ_STATE+38    ;3B hot caret, frozen and checked each STEP
GFQ_SELECT_B=GFQ_STATE+41    ;3B anchor if marked, otherwise caret
GFQ_MARK=GFQ_STATE+44
GFQ_LAST=GFQ_STATE+45        ;3B previous preorder summary, checked on scanned prefix
GFQ_SIZE=48
GFQ_RECORD=$8080            ;32B checked object DMA bounce; source8000..807F safe
.assert GFQ_STATE+GFQ_SIZE<=$CF80,error,"GEOS fold query scratch overflow"
; Entry FIRST gates owner4, before ANY CF/frame access; wrong owner=B2, opaque.
; BEGIN/STEP return A1 pending or A0 done/CLC; Cset preserves primary error.
; BEGIN with ef_valid0 returns checked identity immediately (no map access).
; BEGIN freezes query/mode/map token/count/generation and current selection.
; Caller sets ACTIVE0 on owner4 acquisition (or CANCEL), never mid-query.
; Map requires published ef_valid1 + exact current canonical key. Published map
; bytes are immutable and already fully tree-validated by builder publication.
; This query authenticates typed object/all extents/committed size each slice;
; each read also checks anchors/kind/flags/level/reserved and scanned ordering.
; It does not revalidate unseen tree ancestry or acquire/release source leases.
; First enclosing collapsed preorder record wins (outer collapse). Hidden body
; is [BODY,END); QUERY==END remains visible. Selection is nonempty canonical
; overlap; endpoints never change. A visible result equals original QUERY.
; Output RESULT/HIDDEN/SELECTED/SUMMARY/BODY/END publish only on success.
; No BSS/ZP, source/map writes, C calls, index/GL/semantic/FS/header clobbers.
; Clobbers resident view/object/DMA request scratch and8080..809F only.
.ifndef GFQ_IMPLEMENTATION
.global se_gfq_begin,se_gfq_step,se_gfq_cancel
.endif
.endif

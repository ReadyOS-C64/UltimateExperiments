; C20-only continuation bridge. Owner4 has invalidated the inactive source-grid
; plan; its1024 bytes4400..47FF hold the current-output certificate and the
; live GL core/map,59B source identity and native packet32. Measure outputs are
; scratch; the14 immutable glyph inputs are retained for the next measure call.
; End the old lease before leaving C20: STOP during C26 has just one real lease.
inline_request:
    lda #0
    sta se_st_request
    sta se_st_cp_valid
    lda L+GL_MAP_COUNT+1
    jne argument
    lda L+GL_MAP_COUNT
    cmp #INLINE_SOURCE_CAPACITY
    jcs argument
    ldx #INLINE_CORE_SIZE-1
@save_core:
    lda L,x
    sta INLINE_LINE,x
    dex
    bpl @save_core
    ldx #0
@save_map_page:
    lda L+GL_MAP,x
    sta INLINE_MAP,x
    inx
    bne @save_map_page
    ldx #INLINE_MAP_SIZE-257
@save_map_tail:
    lda L+GL_MAP+$100,x
    sta INLINE_MAP+$100,x
    dex
    bpl @save_map_tail
    ldx #INLINE_IDENTITY_SIZE-1
@save_fs:
    lda GS_FS+27,x
    sta INLINE_FS,x
    dex
    bpl @save_fs
    ldx #31
@save_packet:
    lda GS_PACKET,x
    sta INLINE_PACKET,x
    dex
    bpl @save_packet
    jsr cleanup
    ldx #2
@query:
    lda L+GL_SCAN,x
    sta GSEM_FRAME+GSEM_QUERY,x
    dex
    bpl @query
    lda L+GL_PACKET_COUNT
    sta GSEM_FRAME+GSEM_COUNT
    lda #1
    sta INLINE_CONT
    lda #26
    sta $9135
    lda #3 ;SOURCE_BEGIN: completion hands root back to C20/STEP
    sta $9136
    lda #0
    ldx #85
@clear_fs:
    sta se_fs_state,x
    dex
    bpl @clear_fs
    lda #GS_PENDING
    clc
    rts
inline_resume:
    ; Restore GL, then acquire a fresh reader. Every frozen source identity
    ; byte must match the old lease before consuming its retained native data.
    ldx #INLINE_CORE_SIZE-1
@restore_core:
    lda INLINE_LINE,x
    sta L,x
    dex
    bpl @restore_core
    ldx #0
@restore_map_page:
    lda INLINE_MAP,x
    sta L+GL_MAP,x
    inx
    bne @restore_map_page
    ldx #INLINE_MAP_SIZE-257
@restore_map_tail:
    lda INLINE_MAP+$100,x
    sta L+GL_MAP+$100,x
    dex
    bpl @restore_map_tail
    ldx #31
@restore_packet:
    lda INLINE_PACKET,x
    sta GS_PACKET,x
    lda $8300,x
    sta GS_STYLES,x
    dex
    bpl @restore_packet
    ; The packed packet temporarily spans the inactive style checkpoint byte.
    ; It is dead after this copy; clear the checkpoint before parent code runs.
    lda #0
    sta se_st_cp_valid
    jsr save_overlap
    lda #0
    sta INLINE_CONT
    ldx #85
@fresh_fs:
    sta se_fs_state,x
    dex
    bpl @fresh_fs
    jsr reader_invoke
    jcs fail
    lda #1
    sta GS_ACTIVE
    sta GS_CONTEXT_VALID
    ldx #58
@identity:
    lda GS_FS+27,x
    cmp INLINE_FS,x
    bne @changed
    dex
    bpl @identity
    jsr style_remember
    lda L+GL_PACKET_COUNT
    jmp feed_line
@changed:
    lda #GL_CHANGED
    jmp fail

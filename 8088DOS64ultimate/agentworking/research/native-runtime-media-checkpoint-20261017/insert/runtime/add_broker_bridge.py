from pathlib import Path
P=Path(__file__).resolve().parent
for name in ['broker','broker-runtime']:
 p=P/name/'broker.s';s=p.read_text();s=s.replace('.include "symbols.inc"','.include "symbols.inc"\n.include "bridge_products.inc"')
 s=s.replace('.export modal_entry','.export modal_entry,modal_view_refresh,modal_verify,verify_expected,ui_ready')
 # Refactor the exact existing view builder; the accepted CFG begins3FF020.
 a=s.index(' lda #0\n ldx #0\n@view:');b=s.index(' jsr modal_display_on',a);view=s[a:b]
 view=view.replace(' lda #1\n sta _mu_view+258',' lda dos64_native_diag\n cmp #8\n bne :+\n lda #1\n sta _mu_view+258\n:')
 view+=' clc\n rts\n';s=s[:a]+' jsr modal_view_refresh\n jcs modal_entry_failed\n'+s[b:]
 # Before retiring guest bitmap, load and verify bridge using trusted broker CRC.
 a=s.index(' ldx #16\n jsr entry_dma');s=s[:a]+''' ldx #40
 jsr entry_dma
 jcs modal_entry_failed
 ldx #3
: lda bridge_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs modal_entry_failed
 jsr $6003
'''+s[a:]
 # Validated take() has returned and UI high context has been restored.
 key=' cmp #6                         ; Resume is the first connected operation\n beq @resume\n';assert key in s
 s=s.replace(key,key+''' cmp #2
 bne @unavailable
 jsr $6000
 jcs modal_entry_failed
 jmp modal_wait
@unavailable:
''')
 s=s.replace('ENTRY_DMA _mu_view+1,$3ff088,128,1','ENTRY_DMA _mu_view+1,$3ff0a8,128,1').replace('ENTRY_DMA _mu_view+130,$3ff108,128,1','ENTRY_DMA _mu_view+130,$3ff128,128,1')
 s+='''
modal_view_refresh:
'''+view+'''
; Pure CPU CRC of the just-completed fixed request. The exact expected value
; comes from source-bound products; preserve native high ZP around all reads.
modal_verify:
 ENTER
 lda $80
 sta verify_saved
 lda $81
 sta verify_saved+1
 ldx #1
: lda dos64_reu_request,x
 sta $80,x
 lda dos64_reu_request+5,x
 sta verify_count,x
 dex
 bpl :-
 lda #$ff
 ldx #3
: sta verify_crc,x
 dex
 bpl :-
@next:
 lda verify_count
 ora verify_count+1
 beq @done
 ldy #0
 lda ($80),y
 eor verify_crc
 sta verify_crc
 ldx #8
@bit:
 lsr verify_crc+3
 ror verify_crc+2
 ror verify_crc+1
 ror verify_crc
 bcc @skip
 lda verify_crc
 eor #$20
 sta verify_crc
 lda verify_crc+1
 eor #$83
 sta verify_crc+1
 lda verify_crc+2
 eor #$b8
 sta verify_crc+2
 lda verify_crc+3
 eor #$ed
 sta verify_crc+3
@skip:
 dex
 bne @bit
 inc $80
 bne :+
 inc $81
: lda verify_count
 bne :+
 dec verify_count+1
: dec verify_count
 jmp @next
@done:
 ldx #3
: lda verify_crc,x
 eor #$ff
 cmp verify_expected,x
 bne @bad
 dex
 bpl :-
 lda verify_saved
 sta $80
 lda verify_saved+1
 sta $81
 RETURN 0
@bad:
 lda verify_saved
 sta $80
 lda verify_saved+1
 sta $81
 RETURN 1
bridge_crc:.dword BRIDGE_CRC
.segment "STATE"
verify_crc:.res 4
verify_expected:.res 4
verify_saved:.res 2
verify_count:.res 2
'''
 # entry_requests has five8B records; append new bridge record immediately.
 key=' ENTRY_DMA _mu_view+130,$3ff128,128,1\n';assert key in s;s=s.replace(key,key+' ENTRY_DMA $6000,$3df300,BRIDGE_BYTES,1\n');p.write_text(s)
 # Placeholder is fixed-size DATA, resolves mutual aliases before final bytes.
 (P/name/'bridge_products.inc').write_text('BRIDGE_BYTES=1\nBRIDGE_CRC=0\n')

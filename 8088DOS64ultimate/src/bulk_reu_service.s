; DEVELOPMENT RECOVERY ONLY: never linked into the DOS runtime.
; Exclusive machine/REU/CIA2/NMI takeover. Host publishes body/staging while
; paused, then GO last, and resumes. One command per expected 16-bit sequence.
; $6000: magic DRS1; +4 state ($11 ready,$47 GO,$33 busy,$a5 done,$e1 fail);
; +5 error; +6 direction (1 snapshot,0 restore); +7 sequence LE; +9 ack LE;
; +11 REU address24 LE; +14 length16 LE; +16 inverse sequence; +18 REU error;
; +19 REU status. Host never writes acknowledgement. All commands stage at
; $8000. Allowed count1..$4000, bank-contained REU span within [0,$400000).
; Ack changes once per accepted expected sequence, including a failed command.
; Bad magic/sequence does not consume ack. Duplicate GO cannot repeat DMA.
.include "reu.inc"
.macpack longbranch
.import dos64_reu_request, dos64_reu_transfer
.export dos64_bulk_reu_entry, dos64_bulk_reu_idle, dos64_bulk_reu_poll
.export dos64_bulk_reu_mailbox := $6000
.segment "LOADADDR"
 .word $0801
.segment "BASIC"
 .word $080b,10
 .byte $9e
 .asciiz "2061"
 .word 0
.segment "BSS"
bulk_expected: .res 2
bulk_end: .res 3
.segment "CODE"
dos64_bulk_reu_entry:
 sei
 cld
 ldx #$ff
 txs
 lda #$2f
 sta $00
 lda #$37
 sta $01                          ; KERNAL stays visible during vector install
 lda #<bulk_nmi
 sta $fffa
 lda #>bulk_nmi
 sta $fffb
 lda #$7f
 sta $dd0d                         ; exclusive CIA2, disable all NMI sources
 lda $dd0d                        ; acknowledge already-pending CIA2 sources
 lda #$35
 sta $01                          ; expose the now-complete owned RAM NMI vector
 lda #0
 ldx #31
@clear:
 sta $6000,x
 dex
 bpl @clear
 ldx #3
@magic:
 lda bulk_magic,x
 sta $6000,x
 dex
 bpl @magic
 lda #$11
 sta $6004                        ; READY published last
dos64_bulk_reu_idle:
 jsr dos64_bulk_reu_poll
 jmp dos64_bulk_reu_idle
bulk_nmi:
 rti

dos64_bulk_reu_poll:
 lda $6004
 cmp #$47
 beq @go
 rts
@go:
 lda #$33
 sta $6004                        ; claim command before inspecting descriptor
 lda #0
 sta $6005
 sta $6012
 sta $6013
 ldx #3
@checkmagic:
 lda $6000,x
 cmp bulk_magic,x
 jne @magicbad
 dex
 bpl @checkmagic
 clc
 lda $6009
 adc #1
 sta bulk_expected
 lda $600a
 adc #0
 sta bulk_expected+1
 cmp $6008
 jne @seqbad
 lda bulk_expected
 cmp $6007
 jne @seqbad
 ; Sequence is accepted now. Ack publication is deferred until completion.
 lda $6007
 eor $6010
 cmp #$ff
 jne @guardbad
 lda $6008
 eor $6011
 cmp #$ff
 jne @guardbad
 lda $6006
 cmp #2
 jcs @directionbad
 sta dos64_reu_request+R_DIRECTION
 lda $600e
 sta dos64_reu_request+R_LENGTH
 lda $600f
 sta dos64_reu_request+R_LENGTH+1
 cmp #$40
 bcc @lengthlow
 jne @lengthbad
 lda $600e
 jne @lengthbad
@lengthlow:
 lda $600e
 ora $600f
 jeq @lengthbad
 lda $600d
 cmp #$40
 jcs @addressbad
 sta dos64_reu_request+R_REU+2
 lda $600c
 sta dos64_reu_request+R_REU+1
 lda $600b
 sta dos64_reu_request+R_REU
 clc
 adc $600e
 sta bulk_end
 lda $600c
 adc $600f
 sta bulk_end+1
 lda $600d
 adc #0
 sta bulk_end+2
 cmp #$40
 bcc @span
 jne @addressbad
 lda bulk_end
 ora bulk_end+1
 jne @addressbad
@span:
 ; REU primitive also rejects non-exact bank seams before DMA is triggered.
 lda #0
 sta dos64_reu_request+R_HOST
 lda #$80
 sta dos64_reu_request+R_HOST+1
 jsr dos64_reu_transfer
 lda dos64_reu_request+R_ERROR
 sta $6012
 lda dos64_reu_request+R_STATUS
 sta $6013
 jcs @dmabad
 lda #0
 jmp bulk_finish
@magicbad:
 lda #1
 bne bulk_reject
@seqbad:
 lda #2
 bne bulk_reject
@guardbad:
 lda #3
 bne bulk_finish
@directionbad:
 lda #4
 bne bulk_finish
@lengthbad:
 lda #5
 bne bulk_finish
@addressbad:
 lda #6
 bne bulk_finish
@dmabad:
 lda #7
bulk_finish:
 sta $6005
 lda bulk_expected
 sta $6009
 lda bulk_expected+1
 sta $600a
 lda $6005
 beq @done
 lda #$e1
 bne @publish
@done:
 lda #$a5
@publish:
 sta $6004                        ; DONE/FAIL published after ack and data
 rts
bulk_reject:
 sta $6005
 lda #$e1
 sta $6004
 rts
.segment "RODATA"
bulk_magic: .byte "DRS1"

.ifndef SE_GEOS_LINE_API
SE_GEOS_LINE_API=1
.ifndef GEOS_LINE_FRAME
GEOS_LINE_FRAME=$8D00
.endif
GL_MODE=0                  ;0 proportional wrap,1 logical line/no-wrap
GL_ENCODING=1              ;0 native/style via actual measure,1 supplied advance
GL_WIDTH=2                 ;viewport pixels1..320
GL_START=4                 ;canonical24-bit initial source position
GL_PAN=7                   ;24-bit no-wrap horizontal origin
GL_CARET=10                ;canonical source caret to observe while streaming
GL_FONT=13
GL_WIDTHS=15
GL_NATIVE=17
GL_PACKET=20               ;immutable native source byte packet
GL_STYLES=22               ;style0..3, only measured encoding
GL_ADVANCES=24              ;positive advance1..255, supplied encoding
GL_PACKET_AT=26            ;must equal returned scan anchor before STEP
GL_PACKET_COUNT=29         ;0..32, at most32 consumed per STEP
GL_HIT_X=30                ;unsigned viewport x, clamped to width
GL_STATE=32                ;1 streaming,2 complete visible/logical line
GL_REASON=33
GL_USED=34
GL_X=35                    ;untrimmed24-bit logical width scanned
GL_SCAN=38                 ;next accepted canonical source anchor
GL_END=41                  ;published line-end boundary, excludes CR
GL_NEXT=44                 ;next line anchor;may rewind scanned word suffix
GL_MAP_FIRST=47            ;canonical source associated with boundary0
GL_MAP_COUNT=50            ;word,0..320 generic cells;rendered<=161 VISIBLE glyphs
GL_CARET_X=52               ;logical24-bit x at requested source boundary
GL_CARET_VALID=55
GL_HIT_SOURCE=56            ;canonical nearest boundary
GL_HIT_BOUNDARY=59          ;word index0..map_count
GL_BREAK_COUNT=61
GL_BREAK_SOURCE=63
GL_BREAK_X=66
GL_BREAK_VALID=69
GL_MAP_CLOSED=70
GL_MAP_STARTED=71
GL_RIGHT=72                ;pan+width,checked24-bit
GL_PENDING_X=75
GL_REWIND=78                ;1 NEXT is before SCAN;caller refetches from NEXT
GL_PRIVATE=79
GL_RASTER_X=92             ;signed16 first intersecting glyph origin, not clamped map0
GL_HIDDEN=94               ;rendered flag only: pointer to MSB-first <=32bit packet mask
GL_RENDER_ANCHORS=$4400     ;162 canonical24-bit RIGHT boundaries/glyph anchors
GL_RENDER_CAPACITY=161      ;max intersecting glyphs + one final boundary
GL_RENDER_LEFT0=$47F3       ;LEFT0 before first glyph's preceding hidden run
GL_RENDER_EDGE=$47F6        ;previous visible glyph+1, independent of hidden run
GL_RENDER_BREAK_EDGE=$47F9  ;saved word-break edge for canonical rewind
GL_GLYPH=96                ;77-byte existing measure frame
GL_MAP=176                 ;321 little-endian viewport x words,clipped0..width
GL_SIZE=832
GL_CR=1
GL_EOF=2
GL_FULL=3
GL_WORD=4
GL_HARD=5
GL_OVERWIDE=6
.global se_geos_line_begin,se_geos_line_step,se_geos_line_finish,se_geos_line_hit
GL_ARGUMENT=$90
GL_CHANGED=$74
GL_STATE_ERROR=$70
GL_RANGE=$7B
; SE_EDITOR_GEOS_RENDERED changes geometry only. GL_HIDDEN=0 is literal input;
; otherwise caller supplies ceil(PACKET_COUNT/8) readable mask bytes, MSB first.
; Hidden bytes consume canonical SCAN/USED at unchanged X, including caret
; observation, but no glyph/map/space break. CR always remains a line boundary.
; RIGHT(k<count)=actual glyph source, RIGHT(count)=canonical boundary after
; mapped edge's hidden suffix. LEFT(k>0)=RIGHT(k-1)+1; LEFT0 is explicit above.
; HIT chooses nearest x boundary (right on midpoint), returns actual RIGHT(k).
; Caller exclusively loans ledger4400..45E5/witness47F3..47FB during geometry.
; No-wrap closing freezes RIGHT after the next visible glyph, so later offscreen
; hidden text cannot move viewport anchors. Full wrap delays publication through
; hidden suffix only. Word rewind restores final RIGHT=BREAK_SOURCE.
.assert GL_RENDER_ANCHORS+(GL_RENDER_CAPACITY+1)*3=$45E6,error,"rendered ledger extent"
.assert GL_RENDER_BREAK_EDGE+3=$47FC,error,"rendered witness extent"
.assert GEOS_LINE_FRAME >= $8D00 .and GEOS_LINE_FRAME+GL_SIZE <= $9180,error,"GEOS line frame outside caller phase"
.endif

.ifndef SE_GEOS_INLINE_ABI
SE_GEOS_INLINE_ABI=1
GI_ID=26
GI_BEGIN=0
GI_STEP=1
GI_CANCEL=2
GI_BEGIN_WIDE=4             ;exact161 query; append-role ABI requires matching C21
GI_SOURCE_BEGIN=3           ;finish requests C20/STEP1 and returnsA1 after END
GI_PARSER=$8D00             ;68B unchanged actual SuperMark inline state
GI_STYLES=$8D44             ;160B private; bit7=exclusive proven inline code
GI_ROLES=$8DE4              ;160B private semantic roles
GI_CONTROL=$8E84            ;92B private below real reader8EE0
GI_ACTIVE=GI_CONTROL
GI_PHASE=GI_CONTROL+1       ;1initialize,2scan,3paint event,4styles,5hiddenmask
GI_COUNT=GI_CONTROL+2
GI_BASE=GI_CONTROL+3
GI_QUERY=GI_CONTROL+4       ;24-bit canonical visible-window origin
GI_BODY=GI_CONTROL+7
GI_END=GI_CONTROL+10
GI_START=GI_CONTROL+13
GI_VISIBLE_END=GI_CONTROL+16
GI_LENGTH=GI_CONTROL+19
GI_INDEX=GI_CONTROL+22
GI_USED=GI_CONTROL+23
GI_BUDGET=GI_CONTROL+24
GI_READS=GI_CONTROL+25      ;0/1 source reads during current STEP
GI_FINISHED=GI_CONTROL+26
GI_BYTE=GI_CONTROL+27
GI_FROM=GI_CONTROL+28
GI_TO=GI_CONTROL+31
GI_TEMP=GI_CONTROL+34
GI_PAINT=GI_CONTROL+37
GI_STOP=GI_CONTROL+38
GI_STYLE=GI_CONTROL+39
GI_ERROR=GI_CONTROL+40
GI_RESERVED=GI_CONTROL+41
GI_SOURCE_RETURN=GI_CONTROL+42
GI_HIDDEN=GI_CONTROL+43     ;20B private MSB-first canonical-window bitset
GI_HIDE_POS=GI_CONTROL+63   ;24-bit bounded event delimiter cursor
GI_HIDE_LEFT=GI_CONTROL+66  ;event width1..3; no source/output allocation
GI_OUTPUT_STYLES=$8300
GI_OUTPUT_ROLES=$8F36       ;160B after FS, safe across parent cache/DOC guards
GI_OUTPUT_HIDDEN=$8FD6      ;20B: QUERY+i -> byte i/8, bit$80>>(i&7)
GI_HIDDEN_BYTES=21
GI_LAST_HIDDEN=GI_CONTROL+67
GI_LAST_STYLE=GI_CONTROL+68
GI_LAST_ROLE=GI_CONTROL+69
GI_OUTPUT_ROLE_LAST=GI_OUTPUT_HIDDEN+GI_HIDDEN_BYTES ;8FEB, separate161strole
GI_STATE_END=$8EE0
; Owner4 only. Read-only entireGSEM8B40..8BFF and visible packet8200..829F.
; Inputs GSEM QUERY0/count4/START9/END12/BODY15/baseROLE18. QUERY may precede
; BODY or packet may extend pastEND, so bytes outside BODY..END keep base.
; Validate QUERY>=START, BODY<=END<=sourceLEN, QUERY+COUNT<=sourceLEN.
; Actual parser scans the complete BODY..END, never a truncated display packet.
; Closed PAIR interior OPEN+WIDTH..CLOSE only: SMstrong2->GGbold1,
; SMemphasis1->GGitalic2. Nested pairs OR; inline-code is exclusive role4/style0.
; Hidden mask marks only matched PAIR opener/closer widths and confirmed ESCAPE
; pound introducer. Escaped character remains visible; unmatched markers stay
; literal. Actual parser code exclusivity applies. Styles/roles are unchanged.
; All21 mask bytes are published; bits at/after COUNT are zero. Old0/3 max160.
; WIDE4 accepts exactly161; styles stay contiguous8300..83A0, first160 roles
; stay8F36..8FD5, roleindex160 publishes separately atGI_OUTPUT_ROLE_LAST.
; Existing control/arrays and first20hidden bytes preserve their addresses.
; A1pending/A0complete/Cseterror. Each STEP <=32 feeds or32 initialize/paint/
; publish cells and <=one32B R14 READ. Source lease/snapshot uses existing
; GSFS9040/flags912C/D; resident cleanup remains safe if C26 is unavailable.
; Pending root request9135=26/op9136=1; all other parent bytes preserved.
; Lease END precedes publication. Each output slice compares full59B source
; identity plus three resident metadata-only typed token checks; no DOC reads
; publication sees no DOC scratch writes. Outputs countbytes only. Caller consumes
; only successful completion, discards partial derived outputs on cancellation/error.
; Hidden mask is advisory derived output, not a source mutation. No
; glyph/raster writes, resident BSS/ZP, REU writes or persistent objects.
; SOURCE_BEGIN3 uses identical input/work but completion writesREQUEST20/OP1
; and returnsA1 with no lease/context/active flag, allowing C20 to restore GL.
.assert GI_STYLES-GI_PARSER=68,error,"inline parser placement changed"
.assert GI_ROLES-GI_STYLES=160,error,"inline style extent changed"
.assert GI_CONTROL-GI_ROLES=160,error,"inline role extent changed"
.assert GI_LAST_ROLE<GI_STATE_END,error,"inline private context overlaps reader"
.assert GI_OUTPUT_ROLES+160=GI_OUTPUT_HIDDEN,error,"inline hidden mask placement"
.assert GI_OUTPUT_HIDDEN+GI_HIDDEN_BYTES<=$9040,error,"inline hidden mask overlaps saved source"
.endif

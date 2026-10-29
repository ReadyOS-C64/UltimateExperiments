.ifndef SE_GEOS_SEMANTIC_ABI
SE_GEOS_SEMANTIC_ABI=1
GSEM_ID=24
GSEM_BEGIN=0
GSEM_STEP=1
GSEM_CANCEL=2
GSEM_FRAME=$8B40
GSEM_QUERY=0                ;input canonical24-bit anchor, including EOF
GSEM_LANGUAGE=3             ;reserved caller lexical language
GSEM_COUNT=4                ;reserved visiblepacket count0..160
GSEM_KIND=5                 ;actual SuperMark block kind0..8
GSEM_LANG=6                 ;actual language0plain/1BASIC/2ASM
GSEM_LEVEL=7
GSEM_MARKER=8               ;advisory prefixlength; BODY-START is authoritative
GSEM_START=9                ;canonical24-bit logical line start
GSEM_END=12                 ;canonical24-bit end excluding CR
GSEM_BODY=15                ;canonical24-bit body after literal prefix
GSEM_ROLE=18                ;ReadyOS semantic palette role, not VIC color
GSEM_REVERSE=19             ;heading base inverse; selection/caret union later
GSEM_HEIGHT=20              ;8 for code body,9 for prose/literal fence markers
GSEM_ACTIVE=21
GSEM_INDEX=22
GSEM_USED=23
GSEM_ERROR=24
GSEM_LENGTH=25              ;private frozen visible source length24
GSEM_CP_VALID=28            ;parent MUST clear on fresh page/nav claim and paint
GSEM_CP_MODE=29
GSEM_CP_KEY=30              ;28B full canonical source key
GSEM_CP_NEXT=58             ;24-bit parser position after classified CR/EOF
GSEM_CP_STATE=61            ;79B actual parser state, survives intervening C20
GSEM_CP_EVENT=140           ;16B last successful output5..20
GSEM_CP_QUERY=156           ;24-bit last query; backwards requests restart0
GSEM_READS=164              ;24-bit actual R14 READ count for this query
GSEM_INLINE=169             ;nonzero requests inline interpretation
; C24 detects '*'/'@'; cached readers may skip only a proved empty result.
GSEM_FRAME_END=$8C00
GSEM_BLOCK_STATE=$8D00      ;79B pure actual block parser state
GSEM_PENDING=1
; Owner4 required before all frame/phase accesses. BEGIN acquires a counted
; R14 snapshot lease and starts actual block parsing from canonical0. STEP
; performs <=one32B source READ/<=32 feed calls, preserving page controller
;9134..9177 except root scheduling REQUEST9135/OP9136. A1pending/A0done/Cseterr.
; Output5..20 is published only on success. QUERY/input fields are immutable.
; No prefix hiding: START/BODY/END are canonical source offsets. Softwrapped
; anchors inherit the complete CR-delimited logical line's classification.
; Real FS8EE0 is copied to GS savedcontext9040 after every R14 call; GS flags
;912C/912D let resident se_geos_cancel end only this own lease if C24 is absent.
; CANCEL ends the lease idempotently, retains parent owner4 and its controller.
;8100prefix/8200source/8300roles are untouched. Packet90EC..910B is private.
; Explicit VALID0 starts from0. Valid forward queries restore a full-keyed79B
; parser checkpoint; queries in its last exact logical event need zero READs.
; Backwards/key/mode changes restart0. No lease crosses a C20 call. C22's8B40
; paint frame overwrites this certificate: parent must invalidate it explicitly.
.assert GSEM_CP_EVENT-GSEM_CP_STATE=79,error,"semantic checkpoint state size"
.assert GSEM_FRAME+GSEM_READS+3<=GSEM_FRAME_END,error,"semantic frame overflow"
.endif

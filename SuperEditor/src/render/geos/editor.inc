.ifndef SE_GEOS_EDITOR_ABI
SE_GEOS_EDITOR_ABI=1
GP_LAYOUT_ID=20
GP_PAGE_ID=21
GP_ROW_ID=21
GP_PAINT_ID=22
GP_NAV_ID=23
GP_SEMANTIC_ID=24
GP_SEMLEX_ID=25
GP_INLINE_ID=26
GP_CACHE_OWNER=$FE
GP_CACHE_WIDTH=$FF
GP_MAX_LINES=22
GP_MAX_GLYPHS=161
GP_HEADER=$8500
GP_HEADER_SIZE=64
GP_CACHE_VERSION=3
GPH_VALID=0
GPH_COUNT=1
GPH_MAGIC=2
GPH_VERSION=3
GPH_KEY=4                    ;28B canonical graph/gen/revision/mergedlength/epochs
GPH_TOP=32                   ;3 canonical viewport anchor
GPH_PAN=35                   ;3 pixel horizontal pan
GPH_BOTTOM=38                ;3 canonical exclusive page anchor
GPH_SEEN=41
GPH_CARET_ROW=42
GPH_CARET_X=43               ;2 viewport pixel caret
GPH_FOLD_VALID=46
GPH_FOLD_GENERATION=47 ;word
GPH_CARET_VISIBLE=45         ;horizontal visibility, independent of SEEN member
GP_SLOT_BASE=$0200
GP_SLOT_SIZE=$0800
GPR_START=0
GPR_END=3
GPR_NEXT=6
GPR_FIRST=9                  ;canonical first visible source cell
GPR_COUNT=12                 ;word,0..161 visible glyphs, excludingCR
GPR_HEIGHT=14                ;8 native code,9 BSW
GPR_TOP=15                   ;physical pixelY16..191
GPR_KIND=16                  ;0BSW,1native8
GPR_REASON=17                ;GL_CR/EOF/FULL/WORD/HARD/OVERWIDE
GPR_CARET_VALID=18
GPR_CARET_X=19               ;word viewport pixelX
GPR_BACKGROUND=21
GPR_FLAGS=22
GPR_INLINE=23               ;logical event contains possible '*'/'@' syntax
GPR_RASTER_X=24             ;signed16 first real glyph origin; maps remain clamped
GPR_MEMBER=26               ;caret belongs to this logical row, even if panned off
GPR_TAIL_VALID=27           ;virtualCR/EOF space intersects horizontal viewport
GPR_TAIL_X=28               ;signed16 virtualspace origin;0 when ineligible
GPR_PREFIX=32
GPR_CHARS=32                 ;161 native bytes
GPR_STYLES=194               ;161 bold/italic0..3
GPR_ROLES=356                ;161 palette roles0..13
GPR_X=518                    ;162 little-endian16-bit x boundaries
GPR_LEFT=842                 ;legacy ABI2 offset; non-live in ABI3
GPR_RIGHT=1328               ;legacy ABI2 offset; non-live in ABI3
GPR_USED=842                 ;prefix/characters/styles/roles/X; FIRST+index affinities
GP_RECORD=$8100              ;32B foreground row-prefix staging
GP_SOURCE=$8200              ;160B foreground native packet during page build
GP_ROLES=$8300
GP_CANONICAL=$8400           ;<=64*3B read staging for paint selection/caret
; Shared checked logical-bank transfer request. Caller sets offset/host/length;
; routines refresh resident DMA request; source read cache8000 may be clobbered.
GP_IO_OFFSET=$9178           ;2 within ownedFEbank
GP_IO_POINTER=$917A          ;2 C64 buffer
GP_IO_LENGTH=$917C           ;2 nonzero
; Page controller private state9134..9177 survivesC20/paint jobs. C22 private
; paint state8B40..8BFF survivesR21frame8880..8B3F. C20/bands phasealiases are
; exclusive; onlyowner4 may read them. No additive resident state orZP.
GP_CONTROL=$9134
; Current sealed R21 layout. Entry source's code/table sizes are fixed by
; link assertions in production Make; these pointers are dereferenced ONLY
; after invoking R21, never after replacing its slot.
GP_ROW_FONT=$ABF3
GP_ROW_WIDTHS=$AEDB
GP_NATIVE_FONT=$4800
; Shared cache.s is linked into each C21/C22 consumer, never called across C.
; OPEN allocates/revalidates existinglogicalFEbank and writes freshvalid0header.
; GUARD validates owner4, logical/physicalFEownership/epoch, fullsourcekey/top/pan;
; fetches64B header to8500. It permitsvalid0 whileC21builds; C22requiresvalid1.
; READ/WRITE useGP_IO fields, validateFEownership/epoch; A0/Cclear or realerror.
; SLOT A=row0..21 ->GP_IO_OFFSET=0200+row*0800; noDMA.
.ifndef GP_CACHE_IMPLEMENTATION
.import se_gp_cache_open,se_gp_cache_guard,se_gp_cache_read,se_gp_cache_write,se_gp_cache_slot
.endif
.assert GPR_USED<=GP_SLOT_SIZE,error,"GEOS row slot overflow"
.assert GP_SLOT_BASE+GP_MAX_LINES*GP_SLOT_SIZE<=$10000,error,"GEOS page bank overflow"
.endif

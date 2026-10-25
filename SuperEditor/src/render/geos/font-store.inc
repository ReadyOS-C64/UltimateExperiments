.ifndef SE_GEOS_FONT_STORE_ABI
SE_GEOS_FONT_STORE_ABI=1
GF_OWNER=$FD
GF_READY_VALUE=$A5
GF_DATA_LFN=7
GF_BUFFER=$5000
GF_STATE_SIZE=64
GF_READY=0
GF_HANDLE0=1
GF_HANDLE1=2
GF_EPOCH=3
GF_BUSY=5
GF_ERROR=6
GF_RAW_STATUS=7
GF_OWNED=8
GF_POSITION=9             ;3B import progress / runtime saved raw offset
GF_DONE=12                ;2B import chunkcount / runtime destination pointer
GF_CRC=14                 ;2B cold running CRC, restored between overlay calls
GF_ORIGIN=16              ;query nativeGFCnamespace1file/2system
GF_FAMILY=17              ;query16bit GEOSfamily; systemBSW=$FFFF
GF_POINT=19               ;query actual native point identifier
GF_FACE=20
GF_VALID=21
GF_STRICT_VALID=1
GF_PREVIEW_VALID=$81       ;strictly verified, preview-owned window still intact
GF_LOADS=22               ;overlay loadcount witness, never sole hit-integrity proof
GF_LENGTH=24
GF_BASELINE=26
GF_HEIGHT=27
GF_STRIDE=28
GF_GLYPHS=30
GF_FIRST=31
GF_MAX_WIDTH=32
GF_MONO=33
GF_OFFSET=34              ;3B current rawdata IO cursor
GF_IO_LENGTH=37           ;2B remaining data transfer
GF_ENTRY=39               ;16B copied GFC1 index record
GF_TEMP=55                ;9B private, device/byte/index/CRC-loop scratch
; After PREVIEW_FETCH only, these9 bytes freeze the verified capability graph.
; A strict FETCH/import may freely overwrite them and therefore disarms reuse.
GF_FAST_HANDLES=GF_TEMP    ;2logicalFDhandles
GF_FAST_MAP=GF_TEMP+2      ;2physicalbindings
GF_FAST_EPOCH=GF_TEMP+4    ;2provider epoch
GF_FAST_FACE=GF_TEMP+6
GF_FAST_LENGTH=GF_TEMP+7   ;2B checkedrawlength
GF_ARGUMENT=$90
GF_BUSY_ERROR=$91
GF_IO_ERROR=$92
GF_FORMAT=$94
GF_LIMIT=$95
GF_STALE=$18
GF_NOT_FOUND=$17
.global se_gf_state,se_gf_fetch,se_gf_fetch_preview,se_gf_import_begin,se_gf_import_step,se_gf_import_cancel
.global se_gf_font_pointer
; Descriptor is64CPU-onlybytesCBC0..CBFF (root FONT_STORE_STATE segment).
; Root COLD must zero it before firstBEGIN; never erase a live descriptor.
; BEGIN A=device8/9, STEP/CANCEL: A1pending/A0done/Csetprimaryerror.
; Cold importer owns only LFN7; requires no other open channels, FDtwo rawbanks,
; exact immutableGFC1 bytes/trustedCRC. Errors close ownchannel and release only
; sameepoch/FDownedhandles. No source/overlayobject allocation or CA-DMA.
; FETCH inputs ORIGIN/FAMILY/POINT, outputs5000 contiguous rawfont and metrics.
; BuiltinBSW maps namespace2/familyFFFF/point9; native is caller bypass.
; FETCH restores no pixels: up4210B5000..6071 overwrites114B topbitmapchrome.
; Caller must repaintchrome AFTER fontuse on success/error, never use rawfont
; after chromepaint. Native4800, source4000..47FF, hot9200, A000/B000 preserved.
; Fetch hit checks fullfaceCRC even if loadtag matches, preventing16bitwrap or
; stagealias falsehit. No new BSS/ZP; borrowforeground text_ptr/screen_ptr.
; Phase/state/query must not be used concurrently by other consumers.
;
; PREVIEW_FETCH is an explicitly narrower operation, enabled only when linked
; with SE_GEOS_PREVIEW_FAST=1; otherwise it aliases the strict public FETCH.
; Requires owner4. It may omitCRC only after a strict verify in the same
; preview-owned window lifetime, with matching fullfacekey/FDcapabilities/
; length/loadwitness. It republishes derivedmetrics from the verified rawheader.
; All overlay staging MUST clear GF_VALID BEFORE any5000write, including failed
; admission; this sticky invalidation makes loadcounter wrap irrelevant. C27
; BEGIN clears GF_VALID; every other window borrower/owner lifetime must too.
; Public FETCH always checks CRC and returns GF_VALID1; preview returns81.
.endif

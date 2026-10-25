.ifndef SE_GEOS_CATALOG_GLYPH
SE_GEOS_CATALOG_GLYPH=1
.globalzp se_gg_context,se_gg_pointer
.global se_geos_catalog_measure,se_geos_catalog_glyph
; X/Y caller frame pointer. All fields are RAM; input0..13 immutable.
; CPU font/native spans and entire frame must lie1000..C5FF, not overlap.
CG_FONT=0                 ;ptr to exact native packed font;ptr0+len0 native-only
CG_LENGTH=2               ;word,202..4210
CG_NATIVE=4               ;explicit valid native128x8 font pointer
CG_VALUE=6
CG_ENCODING=7             ;0 PETSCII,1 rawscreen/inversebit7,2 GEOSASCII32..127
                         ;BSWalso128;mode2 SCREENoutputisrawASCII,noinversebit
CG_STYLE=8                ;bold1,italic2,underline4
CG_FLAGS=9                ;inverse1; union with rawscreeninverse
CG_LEFT=10                ;halfopen localclip0..32; invertedclip is empty
CG_RIGHT=11
CG_TOP=12                 ;halfopen0..24
CG_BOTTOM=13
CG_VALID=14               ;0 invalid,1 measured,2 rasterized
CG_SCREEN=15
CG_WIDTH=16               ;native advance0..24; graphicsfallback8
CG_ADVANCE=17             ;width+bold1+italic2 <=27;native-onlyfixed8
CG_HEIGHT=18              ;checked1..24 actualnative raster height
CG_BASELINE=19
CG_INK=20                 ;24rows×4B bigendian,leftaligned; beyondheightzero
CG_COVERAGE=116           ;same192bits format, clipped advance masks
CG_SCRATCH=212            ;28private bytes; outputs/scratch unspecified onerror
CG_SIZE=240
CG_BOLD=1
CG_ITALIC=2
CG_UNDERLINE=4
CG_ARGUMENT=$90
CG_FORMAT=$94
; Italic rightshift2 if3*row<height,1 if3*row<2*height,else0.
; Underline row=baseline+1, whole styled advance, within native height.
; Inversion afterstyles XORs cell coverage once. Fallback graphics are top-
; aligned native8, blank afterrow7/truncated if selectedfontheight<8.
; Native-only mode fontptr0/length0 is8px mono,height8/baseline6; B/I clipped
; into that8px advance. Native-onlyencoding2 rejects. Otherzero-pointer/
; length combinations reject. Width0 safelyemits emptyink/advance exceptB/I
; stilladd1/2; caller alwaysconsumescanonicalbyteevenifadvance0.
; No BSS/ZP allocation. Borrows existing4B GG pointers, A/X/Y clobbered.
.endif

.ifndef DOS64_RENDER_GRAPHICS_INC
DOS64_RENDER_GRAPHICS_INC = 1
; One synchronous scanline, exclusive overlay owner, 0..199. Outputs below
; describe the committed palette for the presenter; this API never sets VIC.
RG_LINE = 0
RG_DONE = 1               ; fully committed native bitmap bytes, 0..40
RG_STATUS = 2
RG_ERROR = 3
RG_BACKGROUND = 4         ; C64 D021 value (caller publishes separately)
RG_MULTICOLOR = 5         ; 1: modes4/5, 0: mode6
RG_SIZE = 6
RG_OK = 1
RG_FAILED = 2
RG_ERR_ARGUMENT = 1
RG_ERR_CACHE = 2
.endif

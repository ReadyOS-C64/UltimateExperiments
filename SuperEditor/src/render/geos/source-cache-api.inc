; Optional cached SOURCE routing; disabled C26 keeps its original byte stream.
.ifndef SE_EDITOR_CACHED_INLINE_SOURCE_ABI
SE_EDITOR_CACHED_INLINE_SOURCE_ABI=1
.ifdef SE_EDITOR_CACHED_INLINE_SOURCE
GI_SOURCE_FALLBACK=5 ;explicit legacy SOURCE, bypasses adaptive delegation
.endif
.endif

# ASM exact whole-word lookup (private)

`asm-exact.patch` adds optional macro parameterwhole and a5B length check only for indexed `sl_asm_table`. Existing indexed BASIC token-prefix behavior and unindexed directives remain unchanged. The pure lexer previously accepted any ASM mnemonic prefix as a complete word: LDAQ emitted keyword over all4bytes. The independent existing oracle correctly emits ordinarycode.

Tests: `python3 tests/test_asm_word_candidate.py` PASS2034cases (1449ASM/directive/native/high24-bit variants;585BASIC exact old/new/oracle cases), full64KiBRAMguard eachcase, no state/ZP growth. Pure image2845→2850.

`python3 tests/test_asm_word_editor_candidate.py` PASS5 actual root GEOS frames using baseline183509: ldaQ/ldxQ/sta0/adcQ plus actual pending lda→ldaQ. Baseline C25 reassembles byte-identically to packaged image. Only C25 is replaced; original resident/C23/C31 untouched. Explicit derived-cache invalidation forces the full public C25 path. Baseline fourattributes76 differ from independentE6; candidate fixes them while allbitmap pixels remain identical. Canonical/history/shim and foreign16MiB exact. ActualC25 payload4044→4049. This is not a C23/cache defect.

Evidence: M8/20261025T190618735702Z-asm-wholeword-candidate. Parent promotion must rebuild all lexer consumers and regenerate C31 staged length/CRC/catalog witnesses normally; do not substitute this private C25 alone as final product acceptance. No canonical source/Make/build/native changes here.

# Retained first failures

Native defects rejected before final acceptance:

* CONFIG fit7 put file_error CODE before SYS entry: actual BASIC37 first wrong PC B013. Final builder appends it after the real entry, and asserts SYS entry/JMP/bank guard.
* CONFIG fit8 tried the B000 load-only fallback after zeroBSS. It is retired. Final late fallback is permanent BFC8, cold-copied/readback before zeroBSS.
* CONFIG fit10 used phase-local RM DMA, which accepts at most512 bytes, for the larger renderer. Final loader is resident, bounded direct REU hardware.
* CONFIG fit11 assumed RM fast CRC tables were initialized. Bootstrap uses its private bitwise CRC instead. Final payload certification uses its trusted raw checksum; whole HIGH CRC is rebound afterward.
* SETUP rejected link/zero-page mismatches and1/3-byte overflows before execution. Final linked hard bounds pass; no weakened checks or stack borrowing.

Fixture/tool reporting errors, all old files/logs retained:

* Untyped ctypes NMI argument caused a host crash; corrected prototype.
* Early500K CPU budgets did not cover native CRC work; increased bounded fixture budgets.
* A host getter call changed PC to0300 before trying to resume SYS; removed it from keyboard flow.
* An early source-path diagnostic inspected root state5 before its next loop had executed the renderer. Its zero fd_closed and blank screen were not a native unknown-closure defect. Final check waits actual fd_park and observes captured knownclosed1.
* Screen-code expectations for lowercase/brackets were corrected to actual native glyph encoding.
* First CONFIG publication driver queued keys while asynchronous directories were loading; UI properly dropped them. Final driver waits directory/UI readiness and proves private coordinator enters RM/CP before long completion.
* First numeric0 CONFIG replay omitted the normal postlink HIGH CRC patch. Final replay applies the same exact normal calculation and is byte-identical.
* First final SETUP builder queried a segment run label not exported by cfg. Linker define=yes for ZP/CRC_TABLES supplies metadata; final native bytes stay c6ad.

No false passing result was relabeled. Historical failures remain separate from closed-native acceptance.

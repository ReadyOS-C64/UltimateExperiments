# Private trusted bootstrap diagnostics

Parent: sealed726c0f0e cold56 installer. No public, hardware, cold asset format or emulator runtime changes. Nine portable paths are listed in PORTABLE_SOURCE.json. Both producers opt in with `--startup-diagnostics`; ASM flag DOS64_BOOT_DIAGNOSTICS defaults numerically off.

Enabled SETUP22a956b1 (43003 bytes), CONFIGb35e103a (43233 bytes). Undefined/default0 reproduces parent SETUP01316a17 and CONFIG215e3988; separate explicit numeric0 source builds match. Actual SYS/Peddle eight focused groups pass; CLOSURE.json records four build source/product closures. No new Zig or physical claim.

SETUP first copies/readbacks a188-byte trusted diagnostic to C843..C8FE, after FILES state and before C900 tables, then installs HIGH/AUX. Failure of the diagnostic copy itself stays at the original trusted resident park; it never executes partial code and cannot promise a screen when that RAM copy fails. Later cold install/source-CRC/startup-CLOSE failures can show the program filename, hex error, CLOSED:Y only from captured actual startup/context proof, otherwise CLOSED:?, and RESTART,RELOAD. This path performs no further file operation or retry. It uses trusted ps_init text mode and bounded screen/color writes. Initial serialized strip is retired by normal UI-cache preparation.

CONFIG224-byte strip is serialized at B000..B0DF, aliases initial BSS, runs only on failed HIGH CRC/copy before zerobss. Success zeroes and retires it. It calls no unverified HIGH/C code. Its direct bounded text mode setup and screen/color writes are independently guarded. Linked assertions and producer checks bind exact LOAD/RUN/source/end/zeroing lifetime.

SETUP lower6000 bound remains full; HIGH endsFFF2, AUX endsC7E8; DIAG endsC8FE. CONFIG lower DATA ends5FF9, HIGH remainsFFB3. No permanent buffer growth. Both terminal loops ignore STOP/Return and cannot revive unknown ownership.

Retained actual first failure: the original incomplete-DIAG-copy fallback incorrectly executed the serialized source linked for RUN and BRKed. FIRST_DIAG_COPY_COUNTER.json and assessment retain it; the repaired trusted park is directly tested. Host parent-map/label/sentinel mistakes remain retained and qualified. Resource audit verifies63 inherited cc65 assembler resources against immutable parent pins after execution; it does not pretend to be a new pre-execution attestation. Both source-built Peddle models separately retain1010 SDK/source pins each.

Scope limitation: later external FAT/PUB/INO missing/corrupt/short file-specific operation/status panes remain OPEN. These screens identify SETUP.PRG or CONFIG.PRG; they do not invent a failed external filename. Arbitrary corrupted trusted bootstrap code, unavailable diagnostic RAM, final current-runtime cold56 bundle and physical execution are not covered.

Focused replay: `python3 -B test_boot.py` uses the sealed source-built observer model and the actual producer receipts, executes SYS plus synthetic firmware/CIA inputs, and asserts full memory write ranges/no retired/unverified PC execution. `python3 -B test_explicit_zero.py` rebuilds explicit0 profiles. All historical failed artifacts are retained.

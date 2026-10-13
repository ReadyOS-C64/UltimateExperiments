# ReadyFS 60-Case Evidence Report

Status: **58 proven**, **2 partial**, **0 missing**.

Latest UI inventory: **33/33 suites**, **382 assertions**.

| Case | Status | Requirement | Evidence | Remaining proof |
|---:|---|---|---|---|
| 1 | PROVEN | Boot banner, standalone identity, and REU status. | `vice_auto_20260815_174951` | — |
| 2 | PROVEN | Help opens and lists canonical endpoints. | `vice_auto_20260815_174951` | — |
| 3 | PROVEN | Unknown command reports an error and returns to prompt. | `vice_auto_20260815_190200` | — |
| 4 | PROVEN | Empty command is harmless. | `vice_auto_20260815_190200` | — |
| 5 | PROVEN | 255-byte logical line reaches the parser without overflow. | `vice_auto_20260816_161744`, `vice_auto_20260817_002517` | — |
| 6 | PROVEN | Horizontal editor scroll follows the cursor. | `vice_auto_20260816_161744`, `vice_auto_20260817_002517` | — |
| 7 | PROVEN | Left/right insertion edits the middle of a command. | `vice_auto_20260815_194939`, `vice_auto_20260817_002517` | — |
| 8 | PROVEN | Insert/overwrite toggle changes replacement behavior. | `vice_auto_20260815_194939`, `vice_auto_20260817_002517` | — |
| 9 | PROVEN | Delete and Home/End behavior. | `vice_auto_20260815_194939`, `vice_auto_20260817_002517` | — |
| 10 | PROVEN | Up/Down recalls and edits command history. | `vice_auto_20260815_194939`, `vice_auto_20260817_002517` | — |
| 11 | PROVEN | Page Up/Page Down and C= fallback traverse scrollback. | `vice_auto_20260815_223302`, `vice_auto_20260816_141948`, `vice_auto_20260817_001605` | — |
| 12 | PROVEN | Quoted arguments, spaces, and malformed quote diagnostics. | `vice_auto_20260815_190200` | — |
| 13 | PROVEN | IEC endpoints accept 8 and 30 and reject 7 and 31. | `vice_auto_20260815_190200` | — |
| 14 | PROVEN | Ultimate root and USB1/SD-card absolute paths. | `vice_auto_20260815_190200` | — |
| 15 | PROVEN | SoftIEC partition 0 and 255 boundaries. | `vice_auto_20260815_190200` | — |
| 16 | PROVEN | Tape endpoint capability query. | `vice_auto_20260815_190200` | — |
| 17 | PROVEN | Alias create/list/use/remove. | `vice_auto_20260815_190200` | — |
| 18 | PROVEN | Alias expansion cannot escape its root in automation mode. | `vice_auto_20260815_190200` | — |
| 19 | PROVEN | `!` distinguishes image host and internal names. | `softwrite-noftp-metadata-lowercase5-20260817-2004` | — |
| 20 | PROVEN | Invalid image boundaries are rejected before I/O. | `vice_auto_20260815_190200` | — |
| 21 | PROVEN | `*` and `?` component matching. | `vice_auto_20260815_205402` | — |
| 22 | PROVEN | `**` recursive matching. | `vice_auto_20260815_205402` | — |
| 23 | PROVEN | `--include`/`--exclude` full-relative-stem filtering. | `vice_auto_20260816_150616` | — |
| 24 | PROVEN | Native-pattern mode stays distinct from shell matching. | `vice_auto_20260816_160722`, `vice_auto_20260816_165721`, `vice_auto_20260816_171906` | — |
| 25 | PROVEN | `probe uci` absent path in VICE. | `vice_auto_20260816_161342` | — |
| 26 | PROVEN | `probe udos` identify on C64U. | `speed-matrix-20260815-200638`, `ui-readonly-20260815-185313` | — |
| 27 | PROVEN | `probe softiec` active and module-not-loaded outcomes. | `speed-matrix-20260815-200638`, `ui-readonly-20260815-185313` | — |
| 28 | PROVEN | `drives scan` covers IEC 8–30 and returns to the prompt. | `vice_auto_20260816_145814` | — |
| 29 | PROVEN | IEC D64 directory and blocks free. | `vice_auto_20260816_142523` | — |
| 30 | PROVEN | IEC D71 16-bit blocks free. | `vice_auto_20260816_142523` | — |
| 31 | PROVEN | IEC D81 directory over 30 entries. | `vice_auto_20260816_141948` | — |
| 32 | PROVEN | UltimateDOS host directory over 30 entries. | `speed-matrix-20260815-200638`, `ui-readonly-20260815-185313` | — |
| 33 | PROVEN | `stat` reports type, raw/display name, exact/estimated size units. | `softwrite-noftp-metadata-lowercase5-20260817-2004` | — |
| 34 | PROVEN | `volume`/`free` distinguish host, image, and C64 block units. | `softwrite-noftp-metadata-lowercase5-20260817-2004` | — |
| 35 | PROVEN | `new` creates an empty SEQ file. | `vice_auto_20260815_192229` | — |
| 36 | PROVEN | `write --line` creates expected bytes. | `vice_auto_20260815_192229` | — |
| 37 | PROVEN | `append --line` preserves old bytes and adds new bytes. | `vice_auto_20260815_195522`, `vice_auto_20260816_191625` | — |
| 38 | PROVEN | Same-backend staged copy and verification. | `vice_auto_20260816_143116`, `vice_auto_20260815_194550`, `vice_auto_20260816_191556` | — |
| 39 | PROVEN | IEC-to-IEC cross-device copy. | `vice_auto_20260816_140348`, `vice_auto_20260816_160831`, `vice_auto_20260817_002532`, `vice_auto_20260817_002551` | — |
| 40 | PROVEN | IEC-to-UltimateDOS copy. | `cross-owned-20260817-iec-udos-roundtrip-k` | — |
| 41 | PROVEN | UltimateDOS-to-IEC PRG copy preserves bytes/type. | `cross-owned-20260817-iec-udos-roundtrip-k` | — |
| 42 | PROVEN | UltimateDOS-to-SoftIEC copy. | `softwrite-noftp-20260817-ident-close2-prod`, `softiec-owned-20260817-nested-parent-prod-full`, `softwrite-noftp-20260817-treeverify-final` | — |
| 43 | PROVEN | Recursive UltimateDOS-to-SoftIEC tree. | `rr5-final3`, `rr5-verify` | — |
| 44 | PROVEN | Move deletes source only after verified copy. | `vice_auto_20260816_143116`, `vice_auto_20260815_194550`, `vice_auto_20260816_191556` | — |
| 45 | PROVEN | Replacement rollback preserves old destination on failure. | `vice_auto_20260817_002634` | — |
| 46 | PROVEN | Delete prompt defaults to no. | `vice_auto_20260815_192229` | — |
| 47 | PROVEN | Recursive delete summary and `--yes` behavior. | `vice_auto_20260816_144213` | — |
| 48 | PROVEN | REL cross-backend copy rejects with an explicit capability error. | `vice_auto_20260816_143000`, `vice_auto_20260816_171852` | — |
| 49 | PROVEN | Delete dry-run reports zero writes/deletes/mounts. | `vice_auto_20260815_192229` | — |
| 50 | PROVEN | Copy dry-run enumerates sources/destination/conflicts without writes. | `vice_auto_20260816_143116`, `vice_auto_20260815_194550`, `vice_auto_20260816_191556` | — |
| 51 | PROVEN | Move dry-run leaves source and destination unchanged. | `vice_auto_20260816_143116`, `vice_auto_20260815_194550`, `vice_auto_20260816_191556` | — |
| 52 | PROVEN | Recursive dry-run applies filters and leaves trees unchanged. | `softwrite-noftp-whatif-filter-casefold-180400` | — |
| 53 | PROVEN | Ultimate image mount/dismount on disposable image. | `softwrite-noftp-media-145816` | — |
| 54 | PROVEN | Ultimate disk swap command. | `softwrite-noftp-media-145816` | — |
| 55 | PARTIAL | SoftIEC partition map/unmap under owned root. | `softiec-owned-20260815-215734`, `softiec-owned-20260815-215809`, `softwrite-noftp-20260817-155612`, `softwrite-noftp-20260817-160912` | firmware 3.14 target $05 has no $20/$21 handlers; requires future firmware/device exposing them, then marker-gated successful map/unmap and exact restoration |
| 56 | PARTIAL | SD2IEC-compatible image mount/root/unmount sequence. | `vice_auto_20260816_160730`, `readyfs_cmdpath_test`, `vice_auto_20260817_230948` | real SD2IEC hardware success for the already emulated compatible-profile path; VICE now proves cached SD2IEC P1/F1/I1 admission plus translated directory/tree/mkdir/image dispatch, clean action completion, explicit non-SD2IEC device failures, and byte-identical fixture preservation |
| 57 | PROVEN | Batch `onerror stop` and `continue` behavior. | `vice_auto_20260816_140348`, `vice_auto_20260816_160831`, `vice_auto_20260817_002532`, `vice_auto_20260817_002551` | — |
| 58 | PROVEN | Batch expected-result journal and report conversion. | `vice_auto_20260816_140348`, `vice_auto_20260816_160831`, `vice_auto_20260817_002532`, `vice_auto_20260817_002551` | — |
| 59 | PROVEN | UCI transport recovery followed by a successful identify at 1/16/64 MHz. | `readyfs_uci_test`, `speed-matrix-20260817-uci-recover-only` | — |
| 60 | PROVEN | Configuration restoration and owned-root preservation after forced suite failure. | `softwrite-noftp-forced-restore-put-16-183320` | — |

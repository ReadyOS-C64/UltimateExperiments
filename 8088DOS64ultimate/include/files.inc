.ifndef DOS64_FILES_INC
DOS64_FILES_INC = 1
; Native Ultimate DOS v3.14 bounded single-file layer over exclusive UCI.
; init is startup-only; caller separately initializes UCI, keeps its ownership,
; base/timeouts immutable while busy, and supplies files_now monotonic ticks.
; start/poll preserve A/X/Y/P except C. C=1 rejects calls, asynchronous result
; is files_state/error. poll always propagates now to UCI; no poll-count time.
; target 1 or 2, op firmware IDs below. target cannot change while open/unknown.
; Caller prepares OPEN path at uci_command+3, CD path at +2, WRITE bytes at +4.
; path_len includes NUL, 2..252, no embedded NUL; modes READ=1, WRITE=2,
; READ|WRITE=3, CREATE_NEW|WRITE=6 or CREATE_NEW|READ|WRITE=7.
; No create-always/truncate support in this layer.
; count READ/WRITE 1..512; seek is 32-bit LE absolute, never REU-truncated.
; Requests/buffers immutable while BUSY. One reply block only; unexpected MORE
; aborts with protocol error. Response queues/lengths/raw wire bytes retained
; in UCI buffers until next start. Status error never becomes file success.
; READ expects empty status (firmware contract), actual count=reply length;
; short read is DONE + short=1. v3.14 read error branch omits *status assignment:
; empty-status read success cannot establish error-free media; verify image.
; WRITE firmware discards actual count: DONE means status accepted, count_known
; remains 0 and uncertain=1. CLOSE discards fclose result too. Neither proves
; persistence. Retain uncertainty until higher layer reopen/content verifies.
; handle=0 closed,1 open,2 uncertain. Unknown handles only permit CLOSE.
; Exact firmware 19-byte 84,NO FILE TO CLOSE leaves CLOSED but reports failure.
; FILECODE must be writable, unbanked, outside A000-BFFF/E000-FFFF.
FILES_IDLE=0
FILES_BUSY=1
FILES_DONE=2
FILES_FAILED=3
FILES_ERR_INPUT=1
FILES_ERR_TRANSPORT=2
FILES_ERR_STATUS=3
FILES_ERR_PROTOCOL=4
FILES_IDENTIFY=$01
FILES_OPEN=$02
FILES_CLOSE=$03
FILES_READ=$04
FILES_WRITE=$05
FILES_SEEK=$06
FILES_CD=$11
.endif

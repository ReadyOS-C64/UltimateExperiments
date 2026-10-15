; Initial HD backend: one exact 512-byte sector per request, lba16 little endian.
; Profile=0 exact2MiB4096sectors128/2/16; profile=1 exact20MiB40960sectors640/4/16.
; Cache32KiB extents, slots1..32; identity is exclusive until a fresh init.
; init only when no operation/uncertainty and backing FILE freshly opened known.
; Caller explicitly initializes hd_state/hd_uncertain at exclusive startup; BSS
; is not assumed zero on hardware. Config profile/slots/readonly adopted by init.
; Original images use readonly=1. Caller serializes one image/FILE target; any
; file/media switch requires close/reopen/init, which invalidates all tags.
; The first request seeks exact length-1 and reads2: one byte plus EOF required.
; prepare/advance are bounded HD-overlay calls and NEVER call FILE wrappers.
; request=1 asks resident orchestration to run configured files_start/poll;
; then call advance once FILE DONE/FAILED. request immutable until then.
; Publishing a request clears prior FILE completion/count-known; an early
; advance cannot use the previous result. No concurrent FILE/UCI consumers.
; Requests support exactly one sector; BIOS multi-sector spans must be checked
; before a resident loop of these operations. Other counts reject before IO.
; Public HD APIs require the native RAM+IO map and preserve P except C, clobber
; A/X/Y; resident wrappers must own the C900 lease until the call returns.
; DONE read publishes exactly512 bytes in uci_data until next request.
; WRITE desired sector supplied in uci_command+4 before prepare; recovery
; staging350000..3501FF remains authoritative through failure/retry.
; Writes invalidate matchingextent, seek/write/seek/readback compare all512.
; observed agreement is NOT persistence, reopen verification or powerfail safety.
; Failed writes forbid init/new requests until retry succeeds; caller may need
; FILE close/reopen recovery for unknown handles first. Retry uses retained
; original LBA/data and ignores changed public request fields. Read failures
; can be retried with prepare because no guest data was accepted as written.
; CHS helper uses CH/CL/DH encoded IBM fields and rejects all invalid sectors.
HD_IDLE=0
HD_WAIT=1
HD_DONE=2
HD_FAILED=3
HD_ERR_INPUT=1
HD_ERR_FILE=2
HD_ERR_SHORT=3
HD_ERR_DMA=4
HD_ERR_VERIFY=5
HD_ERR_LENGTH=6

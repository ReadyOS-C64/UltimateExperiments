.ifndef DOS64_KEYBOARD_INC
DOS64_KEYBOARD_INC = 1
KB_OK = 0
KB_FULL = 1
KB_BAD_STATE = 2
KB_UNSUPPORTED = 3
KB_CACHE = 4
KB_START = $1E
KB_END = $3E
; service consumes guest AH00/01/02; enqueue consumes keyboard_key word.
; C=0 handled (including AH00 waiting=1); C=1 status FULL/BAD_STATE/
; UNSUPPORTED/CACHE. host_error=1 only CACHE. key input is unchanged.
; Guest registers except service AX, and guest FLAGS, remain unchanged.
; Native A/X/Y and memory-bus scratch clobbered; native P except C preserved.
; No initialization routine is required: each call resets output descriptors.
;
; flags_mask/value are LOW bytes, flags_mask_high/value_high HIGH bytes.
; Apply (saved_FLAGS & ~mask_word) | value_word on a successfully handled
; service only. AH01 mask0BD5 yields CMP(head,tail) arithmetic flags,
; TF=0 and IF=1; other services mask0 preserve their caller's IRET flags.
; AH01 reads AX even when head==tail. AH02 returns AH=0, AL=mutable0417.
; AH00 empty waiting leaves AX/head unchanged; caller owns bounded yielding
; and callback retry, with the ordinary guest interrupt frame still intact.
;
; Fixed original-sized ring041E..043D (16 slots,15 usable), head041A,
; tail041C. Even in-range pointers and high bytes zero are required.
; Relocating the ring via later XT BUFFER_START/END0480/0482 is unsupported.
; No native C64 keyboard polling, scan translation, PIC IRQ or AT functions.
.endif

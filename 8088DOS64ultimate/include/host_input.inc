.ifndef DOS64_HOST_INPUT_INC
DOS64_HOST_INPUT_INC=1
HI_OWNED=$A5
HI_OK=0
HI_ERR_OWNER=1
HI_ERR_UNREADY=2
HI_ERR_GHOST=3
HI_ERR_CACHE=4
HI_ERR_QUEUE=5
; Caller exclusively owns CIA1 keyboard ports, has disabled KERNAL scanning
; and CIA1 timer output on PB6/PB7, and owns/blocks NMI/RESTORE handling.
; init requires claim=A5. poll scans once, coherently updates BDA0417 low
; nibble, and feeds dos64_keyboard_enqueue. No IRQ1, typematic, time-based
; debounce or Ctrl-Alt-Del reset. Caller owns cadence; transitions sampled
; between polls cannot be recovered. One word per observed held-key edge.
; Pound (matrix48) is a deferred backslash/pipe key. Hold it before or
; together with physical F5/F7 for F9/F10; Ctrl and Commodore/Alt combine
; normally and either Shift means Shift-F9/F10. The layer consumes pound
; without a guest prefix. Pound alone publishes on release; an ordinary
; new key commits pound first and disables the layer until pound release.
; An already accepted F5/F7 is not reinterpreted by later pound.
; Function modifier priority is Alt, Ctrl, Shift. Shift selects the
; physical F1/F3/F5/F7 pairs F2/F4/F6/F8, while layer Shift stays a modifier.
; Full queue retains exactly one translated word until acceptance, even if
; released. Acceptance marks only a physically held key as seen; accepting
; a released pending key cannot suppress its next fresh press. No secondary
; edge history is retained while blocked: a release/repress before pending
; acceptance coalesces with that word if the key is held at acceptance.
; This also consumes a repressed deferred pound: it cannot re-arm printable
; text or Fn until a subsequent observed release and fresh pound press.
; Other brief presses while blocked are not guaranteed capture.
; C=1/status QUEUE includes FULL/BAD_STATE/CACHE in keyboard_status. Retry
; pending without reinitializing. accepted words are never retried.
; C64 shift keys -> XT shift bits; CTRL -> CTRL; Commodore -> Alt. Shift-lock
; is left-shift hardware, not CapsLock. High BDA modifier/toggle bits survive
; but do not alter this translation; no Caps/Num/Scroll toggle input is exposed.
; Any two scan rows sharing >=2 low columns are conservatively rejected as
; ambiguous ghost rectangles. Joysticks must be disconnected/released.
; PRA/PRB pin snapshots and DDRs restored; hidden input latch bits cannot be
; read and are overwritten. No CIA timers/ICR/TOD accesses. No NMI safety.
; Native A/X/Y and P except C preserved; 6510 DDR and observable bank bits
; restored. Non-reentrant, INPUTCODE must stay loaded throughout poll/init.
.endif

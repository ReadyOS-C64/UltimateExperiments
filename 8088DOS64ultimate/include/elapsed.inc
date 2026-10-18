.ifndef DOS64_ELAPSED_INC
DOS64_ELAPSED_INC = 1
; Elapsed deadline units are exactly 4096 raw CIA phi2 ticks (counter >> 12).
; They are not milliseconds or turbo CPU clocks. PAL frequency is established
; separately; scheduler/transport durations remain expressed in these units.
; The low 16 bits wrap modulo 65536. Durations must be 1..32767 and polling
; gaps <32768 units, as required by UCI/files/import signed deadline arithmetic.
; Caller already owns/initializes host_clock and its CIA2/NMI policy.
; poll preserves native P except C, clobbers A, and preserves X/Y and banking.
; C=1 leaves elapsed_now unchanged; inspect host_clock_status for the reason.
; Not reentrant or NMI-safe; all consumers share the exclusive native owner.
DOS64_ELAPSED_SHIFT = 12
.endif

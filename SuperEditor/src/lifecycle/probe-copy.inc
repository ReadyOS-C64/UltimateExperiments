; PRIVATE exact-copy proof, not the editor lifecycle ABI or a ReadyOS adapter.
; Caller owns ALL cold scratch below, has quiesced IRQ AND NMI, and keeps the
; descriptor/provider/REU immutable until return (or the fresh entry transfer).
; Entry requires I=1,D=0, CPU DDR low3=7, CPU port low3=5 (RAM+I/O).
; No allocation/free. FC is reserved only for this private snapshot capability.
.ifndef SE_LCP_INC
SE_LCP_INC=1
LCP_OWNER=$FC
LCP_DESCRIPTOR=$0800
LCP_LOGICAL=LCP_DESCRIPTOR
LCP_PHYSICAL=LCP_DESCRIPTOR+1
LCP_EPOCH=LCP_DESCRIPTOR+2
LCP_BUILD=LCP_DESCRIPTOR+4       ; 16 exact binding bytes
LCP_ENTRY=LCP_DESCRIPTOR+20      ; caller safe entry in $1000..$3FFF
; descriptor22..31 MUST zero; descriptor is not itself captured.
LCP_WORK=$0820                  ; 64 bytes, disposable
LCP_HEADER=$0880                ; 64-byte readback/build scratch
LCP_BOUNCE=$0700                ; 256 bytes, disposable
LCP_THUNK=$0900                 ; freshly copied executable, <=256 bytes
LCP_PAYLOAD=$BC18
LCP_HEADER_REU=$BC20
LCP_E_BAD=$D0
LCP_E_CAP=$D1
LCP_E_HEADER=$D2
LCP_E_CRC=$D3
LCP_E_PROVIDER=$D4
; CAPTURE: A0/Cclear after header publication; Cset/Aerror otherwise.
; RESTORE: validates everything before warm writes; Cset/Aerror on refusal.
; Success never returns: copies fresh thunk, SP=$FF, A0/Cclear -> JMP ENTRY.
; Clobbers A/X/Y/P, stack, listed cold scratch, REU registers. No ZP scratch.
; Exact CPU extents: $1000..$C5FF,$CA00..$CFFF,$0002..$0019.
; REU offsets: 0,$B600,$BC00; header $BC20..$BC5F. All other REU stays exact.
.endif

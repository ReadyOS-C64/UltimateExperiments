; Callable lifecycle component ABI. Trusted caller owns COLD0700..0DFF.
; No saved stack/overlay continuation. CPU DDRlow3=7/portlow3=6,I1,D0.
.ifndef SE_LIFECYCLE_COPY_ENTRY
SE_LIFECYCLE_COPY_ENTRY=1
LC_BUILD=$0800                  ;expected binding16, populated by trusted caller
LC_HANDLE=$0810
LC_PHYSICAL=$0811
LC_EPOCH=$0812                  ;word
LC_WORK=$0820
LC_PHASE=LC_WORK                ;0idle,1capture,2verifycapture,3verifyrestore,4restoreprovider,5captureprovider
LC_PAGE=LC_WORK+1               ;0..188;page188 is saved ZP24
LC_CRC=LC_WORK+2                ;word
LC_SAVECRC=LC_WORK+4            ;word
LC_AMOUNT=LC_WORK+6             ;0=256,24tail
LC_TABLE=LC_WORK+7
LC_ERROR=LC_WORK+8
LC_CPU=LC_WORK+9                ;word
LC_REU=LC_WORK+11               ;word
LC_CMD=LC_WORK+13
LC_HEADER=$0880                 ;64B
LC_BOUNCE=$0700                 ;256B
LC_THUNK=$0900
LC_RESUME=$0A00
LC_RESUME_TEMPLATE=$B800        ;sealed C29fixed load/run template
LC_DRIVER=$0AE0                ;fresh callableBEGIN/STEP/CANCEL trampoline
LC_RESUME_END=$0B00
LC_WITNESS=$0D00                ;59B source identity
LC_CARET=$0D3B                  ;3
LC_SELECTION=$0D3E             ;mark+anchor3
LC_HEADER_REU=$BC20
LC_PAYLOAD=$BC18
LC_OWNER=$FC
LC_E_STATE=$DA
LC_E_CAP=$DB
LC_E_HEADER=$DC
LC_E_CRC=$DD
LC_E_PROVIDER=$DE
; R26 BEGIN_CAPTURE0,STEP1,BEGIN_RESTORE2,CANCEL3.
; A1/Cclear pending,A0/Cclear committed;Cset/Aerror.
; Final restore STEP transfers fresh0900 ->0A00 (no return).
; Every STEP <=256B payload DMA/CRC, or one256B provider table.
.endif

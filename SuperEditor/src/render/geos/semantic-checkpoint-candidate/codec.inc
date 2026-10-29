.ifndef SE_GEOS_CHECKPOINT_CODEC
SE_GEOS_CHECKPOINT_CODEC=1
.include "render/geos/semantic.inc"
.include "render/geos/edit-certificate.inc"
GSC_RECORD=$9000 ;64B temporary; GS saved sourcecontext9040 is untouched
GSC_BYTES=64
GSC_ANCHOR=4 ;3 canonical incoming logical-line START
GSC_KEY=7 ;28B actual caller-guarded merged-source identity
GSC_CARRY=35 ;fence/language/regions/overflow24
GSC_CRC=62 ;CCITT of bytes0..61, including valid1
GSC_CURRENT=GSEM_FRAME+GSEM_CP_KEY ;28B current guarded source snapshot
GSC_INCOMING=GSEM_FRAME+170 ;9B actual START3+fence/language/regions/overflow3
GSC_PROOF=GSEM_FRAME+180 ;0miss/1exact/2single-GEC prefix proof
GSC_TRY=GSEM_FRAME+181 ;private BEGIN path discriminator
GSC_CAPTURED=GSEM_FRAME+182 ;actual target incoming9 are initialized
GSC_ALLOW_EDIT=GSEM_FRAME+179 ;provisional C21BEGIN GEC_VALID snapshot, not authorityalone
GSC_TEMP=GSEM_FRAME+184 ;4B temporary; fullframe remains below8C00
GSC_SLOT_OFFSET=$0400 ;reserved proposal only, no transport in purecodec
.assert GSC_TEMP+4<=$8C00,error,"checkpoint scratch exceeds ownedframe"
; Caller must acquire/guard actual R14 source and populate CURRENT before call.
; ENCODE immediately before target CR/EOF classification; captures actual
; sm_line and six persistent carrybytes, not the partial prefix/list scratch.
; RESTORE A1 trusted incoming state/A0miss, Cclear. Owner!=4 ->B2/Cset before
; dereferencing frame. Miss does not change parser, record or canonicalsource.
; Only exactkey or explicitly authorized one-GEC prefix-preserving edits work.
; Transport/FEcapability/VALID-last remain the eventual caller's obligation.
.endif

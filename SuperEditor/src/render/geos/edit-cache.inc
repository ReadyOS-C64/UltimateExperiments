; R28 pure derived-page transaction. Caller is C21 owner4, no source lease live.
.ifndef SE_GEOS_EDIT_CACHE
SE_GEOS_EDIT_CACHE=1
.include "render/geos/editor.inc"
GEX_ID=28
GEX_ADMIT=0
GEX_VERIFYROW=1
GEX_REBASE=2
GEX_CANCEL=3
GEX_STATE=GP_CONTROL+21
GEX_PHASE=GEX_STATE
GEX_ROW=GEX_STATE+1
GEX_PAGE_COUNT=GEX_STATE+2
GEX_TOP=GEX_STATE+3
GEX_HEIGHT=GEX_STATE+4
GEX_FIRST_STRIP=GEX_STATE+5
GEX_END_STRIP=GEX_STATE+6 ;exclusive
GEX_OLD_START=GEX_STATE+7 ;3
GEX_OLD_END=GEX_STATE+10 ;3
GEX_OLD_NEXT=GEX_STATE+13 ;3
GEX_OLD_BOTTOM=GEX_STATE+16 ;3
GEX_OLD_LENGTH=GEX_STATE+19 ;3
GEX_NEW_LENGTH=GEX_STATE+22 ;3
GEX_OP=GEX_STATE+25
GEX_SCAN_ROW=GEX_STATE+26
GEX_PAIR=GEX_STATE+27
GEX_BOUNDARIES=GEX_STATE+29
GEX_CHUNK=GEX_STATE+30
GEX_BASE=GEX_STATE+31 ;2
GEX_HOST=GEX_STATE+33 ;2
GEX_OFFSET=GEX_STATE+35 ;2
GEX_COPY_LEFT=GEX_STATE+37 ;2
GEX_COPY_TARGET=GEX_STATE+39 ;2
GEX_TEMP=GEX_STATE+42 ;3
GEX_AUX=GEX_STATE+45 ;oldreason
GEX_CLASS=GEX_STATE+46 ;0 plain,1 semantic,2 heading→prose,3 prose→heading,4 headingbody
GEX_HEADING_CLASS=2 ;singlealpha INSERT at complete oldheading START
GEX_HEADING_BACK_CLASS=3 ;BACK of leadingalpha before1..6hash+space only
GEX_HEADING_BODY_CLASS=4 ;alnum INSERT/BACK after unchanged complete hash+space prefix
GEX_END=GEX_STATE+47
GEX_OLD_HEADER=$D528 ;64B
GEX_CONVERGENT_LINE=1
GEX_EARLY_WRAP=0 ;optional strict overflow refusal before any header/row staging
GEX_ROW_BACKUPS=0 ;old/new row copies had no consumers; addresses stay reserved
GEX_OLD_ROW=$D568 ;2048B reserved, unused
GEX_NEW_ROW=$DD68 ;2048B reserved, unused
GEX_TAIL_END=$E568
GEX_BUFFER=$9000 ;192B, sourcecontext must be inactive
GEX_HEADER=$9080 ;64B duringADMIT, upperpart of192Bbuffer
.assert GEX_END=GP_IO_OFFSET,error,"edit phase mustend before checkedDMArequest"
.assert GEX_TAIL_END<=$10000,error,"edit backups exceed ownedFEbank"
; ADMIT A1accepted/A2miss. Outputs oldgeometry +dirtyrange; headerVALID0/current
; key and64B oldheader witness publishedbeforeaccepted (not on earlyrefusal).
; VERIFY reads the rebuilt row atROW,
; requires sameCR/EOF geometry +delta boundaries; A1verified.
; REBASE max32LEFT/RIGHT boundarypairs/call; A1pending/A0atomicVALID1publication.
; CANCEL A0, keeps/setsVALID0 ifsame ownedtransaction stillexists.
; Cset propagates realprovider/source/argumenterrors. Foreignowner refusesB2
; before phase access. Rejections consume GEC and invalidateGCC, never source.
; Dirty rowbuilder must retain pageCOUNT/TOP andpreserve this47B. Onlyplain,
; literal, unselected, unfolded, unpanned completeCR/EOF rows areeligible.
; No newBSS/ZP. GEX_BUFFER isphase-only: GS_ACTIVE/GS_CONTEXT_VALID mustbe0.
.endif

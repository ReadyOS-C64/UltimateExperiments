.include "render/geos/editor.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/typing/certificate.inc"
GTT_LOCAL=$8BA0             ;47B capturedcertificate, owner4
GTT_ROW=GTT_LOCAL+1
GTT_PREFIX=GTT_LOCAL+2
GTT_X=GTT_LOCAL+34
GTT_WIDTH=GTT_LOCAL+36
GTT_INDEX=GTT_LOCAL+38
GTT_ADVANCE=GTT_LOCAL+39
GTT_REVISION=GTT_LOCAL+40
GTT_CONTROL=$8BCF           ;49B until8BFF
GTT_PHASE=GTT_CONTROL
GTT_SLOT=GTT_CONTROL+1      ;word
GTT_TEMP=GTT_CONTROL+3      ;4B arithmetic/sourcecurrenttag
GTT_SCAN=GTT_CONTROL+7
GTT_ERROR=GTT_CONTROL+8
GTT_PACKET=$8D00            ;842B ABI3 livepacket, through9049
GTT_WIDTHS=$904A            ;128B trusted font widths
GTT_HEADER=$90CA            ;64B oldheader backup
GTT_META=$910A              ;32B fontcachemetadata
.assert GTT_LOCAL+47=GTT_CONTROL,error,"typing localcertificate overlap"
.assert GTT_META+32<=$912C,error,"typing metadatacannot touchGSflags"

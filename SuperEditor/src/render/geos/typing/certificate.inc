.ifndef SE_TYPING_CERTIFICATE
SE_TYPING_CERTIFICATE=1
; Retired phase certificate. C6 writes onlyafterclaimingowner4 from0.
; Foreignowners areopaque. R30 mustchecksum/copy thenindependentlyvalidate.
.ifndef GTC_PACKET_VERSION
GTC_PACKET_VERSION=3
.endif
GTC=$9149
GTC_VALID=GTC ;0 retired,2 current; old all-white producer/consumer used1
GTC_ROW=GTC+1
GTC_PREFIX=GTC+2             ;32B exact oldrowprefix
GTC_X=GTC+34                ;2 editpixelX
GTC_WIDTH=GTC+36            ;2 old rowpixelwidth
GTC_INDEX=GTC+38            ;byte canonical editindex
GTC_ADVANCE=GTC+39          ;oldglyph advance,0 forinsertatend
GTC_REVISION=GTC+40         ;4 old revision, duplicate GEC
GTC_RESERVED=GTC+44 ;CRC-covered0 strict white /1 exact two-color election
GTC_CRC=GTC+45              ;CRC16 bytes1..44, VALID publishedlast
GTC_END=GTC+47
.assert GTC_END=$9178,error,"certificate mustend before GP_IO"
.endif

.export _sm_modal_spec,_sm_modal_header
.segment "DATA"
_sm_modal_spec:
.byte "D64M",1,16
.word 32768
.dword 1014406398
.dword $3da000
_sm_modal_header:
.incbin "modal-header.bin"

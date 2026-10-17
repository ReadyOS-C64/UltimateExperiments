.setcpu "6502"
.import _nf_io_address,_nf_io_buffer,_nf_io_length,_nf_io_direction,_nf_io_status
.import dos64_reu_request,dos64_reu_transfer
.export _nf_dma
.segment "CODE"
_nf_dma:
 lda _nf_io_buffer
 sta dos64_reu_request
 lda _nf_io_buffer+1
 sta dos64_reu_request+1
 lda _nf_io_address
 sta dos64_reu_request+2
 lda _nf_io_address+1
 sta dos64_reu_request+3
 lda _nf_io_address+2
 sta dos64_reu_request+4
 lda _nf_io_length
 sta dos64_reu_request+5
 lda _nf_io_length+1
 sta dos64_reu_request+6
 lda _nf_io_direction
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 lda dos64_reu_request+9
 sta _nf_io_status
 rts

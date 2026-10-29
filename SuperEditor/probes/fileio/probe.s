.setcpu "6502"
.include "fileio/api.inc"
.export fileio_probe_entry
.segment "CODE"
fileio_probe_entry:
    jmp se_io_init

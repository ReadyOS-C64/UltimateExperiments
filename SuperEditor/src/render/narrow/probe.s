; Isolated CPU linker fixture: these are aliases, not new resident allocation.
.setcpu "6502"
.exportzp se_nr_context,se_nr_pointer
se_nr_context=$F0
se_nr_pointer=$F2

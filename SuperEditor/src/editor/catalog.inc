; Cold startup names only. Two bytes per item, no warm-state allocation.
; The high address byte occupies bits4..7; DOS filename length occupies0..3.
; Keep raw filename bytes/aliases in startup.s and encode their linked address.
.macro COLD_FILE name, length
 .assert length>0 .and length<16,error,"cold filename length exceeds nibble"
 .assert name<$1000,lderror,"cold filename escaped four-bit address page"
 .byte <name,((>name)<<4)|length
.endmacro
file_catalog:
 COLD_FILE file0,5
 COLD_FILE file1,5
 COLD_FILE file2,6
 COLD_FILE file3,6
 COLD_FILE file4,6
 COLD_FILE file5,6
 COLD_FILE file6,8
 COLD_FILE file7,6
 COLD_FILE file8,5
 COLD_FILE file9,6
 COLD_FILE file10,6
 COLD_FILE file11,3
 COLD_FILE file12,6
 COLD_FILE file13,10
 COLD_FILE file14,7
 COLD_FILE file15,8
 COLD_FILE file16,6
 COLD_FILE file17,6
 COLD_FILE file18,9
 COLD_FILE file19,10
 COLD_FILE file20,8
 COLD_FILE file21,7
 COLD_FILE file22,7
 COLD_FILE file23,9
 COLD_FILE file24,8
 COLD_FILE file25,8
 COLD_FILE file26,7
 COLD_FILE file27,9
 COLD_FILE file28,7
 COLD_FILE file29,8
 COLD_FILE file30,7
 COLD_FILE file31,8
 COLD_FILE file32,6
 COLD_FILE file33,11
 COLD_FILE file34,11
 COLD_FILE file35,10
 COLD_FILE file36,8
 COLD_FILE file37,8
 COLD_FILE file38,9
 COLD_FILE file39,8
 COLD_FILE file40,8
 COLD_FILE file41,9
 COLD_FILE file42,5
 COLD_FILE file43,5
 COLD_FILE file44,4
 COLD_FILE file45,4
 COLD_FILE file46,4
 COLD_FILE file47,4
 COLD_FILE file48,7
 COLD_FILE file49,4
 COLD_FILE file50,4
 COLD_FILE file51,4
 COLD_FILE file52,4
 COLD_FILE file53,4
 COLD_FILE file54,4
 COLD_FILE file55,4
 COLD_FILE file56,3
 COLD_FILE file57,4
 COLD_FILE file58,4
file_catalog_end:
COLD_FILE_COUNT=(file_catalog_end-file_catalog)/2
.assert COLD_FILE_COUNT<=64,error,"cold catalogue exceeds fixed overlay capacity"
.delmacro COLD_FILE

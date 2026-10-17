.setcpu "6502"
.export _so_asset_header,_so_ui_bytes,_so_fat_bytes,_so_asset_bytes
.export _so_ui_crc,_so_ui_full_crc,_so_fat_crc
.export _so_publish_header,_so_publish_bytes,_so_publish_asset_bytes
.export _so_publish_crc,_so_publish_full_crc
.segment "RODATA"
.include "build/overlay_metadata.inc"

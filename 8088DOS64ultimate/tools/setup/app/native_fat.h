#ifndef DOS64_NATIVE_FAT_H
#define DOS64_NATIVE_FAT_H
/* cc65 target: unsigned char8, unsigned int16, unsigned long32. */
typedef unsigned char nf_u8;
typedef unsigned int nf_u16;
typedef unsigned long nf_u32;
#define NF_OK 0
#define NF_E_INPUT 1
#define NF_E_IO 2
#define NF_E_FULL 3
#define NF_E_NAME 4
#define NF_E_SOURCE 5
#define NF_E_CANCEL 6
#define NF_E_STATE 7
#define NF_MAX_FILES 512
#define NF_MAX_DIRS 64
#define NF_META 0x300000UL
/* Integration supplies REU transfer functions. Return exact count or short;
 * no filesystem calls, DOS API, guest memory, or implicit owner changes. */
extern nf_u16 nf_store_read(nf_u32 address, void* bytes, nf_u16 length);
extern nf_u16 nf_store_write(nf_u32 address, const void* bytes, nf_u16 length);
extern nf_u8 nf_cancelled(void);
/* Fresh C profiles0=2MiB FAT12,1=20MiB FAT16; blankB2=360KiB FAT12. */
extern nf_u8 nf_error,nf_profile,nf_pending,nf_finished,nf_reu_mib; /*0(default4),4,8,16 beforeinit; snapshotted */
extern nf_u16 nf_file_count,nf_dir_count;
extern nf_u32 nf_total_bytes,nf_output_offset,nf_zero_run_size;
extern nf_u8 nf_sector[512];
nf_u8 nf_init(nf_u8 profile);
/* Private producer receipt: public progress cannot authorize reset/borrow.
 * Active init refuses nonfatally; first producer failure is session-terminal.
 * inactive=unplanned/consumed, consumed=all planned bytes actually acknowledged. */
nf_u8 nf_inactive(void);
nf_u8 nf_consumed(void);
/* source360KiB FAT12 images already in REU, three disjoint slots; validated
 * before copying any file. source id0..2. Full source originals unchanged. */
nf_u8 nf_source(nf_u8 id,nf_u32 base,nf_u32 size);
/* Absolute uppercase short path e.g DOS/DISK1/COMMAND.COM. Native metadata
 * supplies source_file's root index (not byte offset) and originalattrs/time. */
nf_u8 nf_put_source(const char* path,nf_u8 source_id,nf_u16 root_index,nf_u8 replace);
/* Generated/user loose bytes already in REU; exact source range/attrs. */
nf_u8 nf_put_memory(const char* path,nf_u32 address,nf_u32 size,nf_u8 attr,nf_u8 replace);
/* Allocate all chains/directories, seal plan, then emit ascending512B sectors.
 * next leaves its buffer/offset immutable until exact ack. ack(error/short)
 * latches first failure and never advances. Stream acceptance is not physical
 * durability; coordinator retains each REU slab until file close/readback. */
nf_u8 nf_import_dos(void); /* archive all originals + first-source convenience */
nf_u8 nf_plan(void);
nf_u8 nf_next(void);
nf_u8 nf_ack(nf_u16 actual,nf_u8 io_error);
/* Optional all-zero range begins at immutable pendingoffset; positive512aligned
 * accepted<=zero_run_size can skip repeated sector memset/DMA. Sink must really
 * write verified zeros; count is producer acceptance, not durability. */
nf_u8 nf_ack_zero(nf_u32 actual,nf_u8 io_error);
/* Clone validated user's boot floppy to a disjoint owned REU region, preserving
 * boot sector/system root placement/all other files; replace owned startuptext.
 * Success means complete REU image, not file persistence or guest boot proof. */
nf_u8 nf_derive_a(nf_u8 source_id,nf_u32 destination,
 nf_u32 auto_address,nf_u16 auto_size,nf_u32 config_address,nf_u16 config_size);
/* Optional readonly existing raw data-C source. Exact bounded callback; no
 * writes to source. Register/import before adding files; nf_put_* replace=1
 * explicitly replaces a selected imported file, while replace=0 rejects it.
 * Replans allocations into NEW output; does not preserve raw free/deleted
 * sectors, cluster placement, bootstrap bytes or source bootability. */
extern nf_u16 nf_disk_read(nf_u32 offset,void* bytes,nf_u16 length);
nf_u8 nf_import_existing(nf_u32 raw_bytes);
#endif

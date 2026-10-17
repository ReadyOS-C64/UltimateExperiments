#ifndef DOS64_FAT_PREPARE_H
#define DOS64_FAT_PREPARE_H
#include "native_fat.h"
#define FP_VALID 0x80u
/* FAT-phase primitives; dispatcher must hold authentic FAT ticket for whole
 * call, own REU/engine/IRQ+stacks, and keep all three source images immutable.
 * Caller must require private SI idle/completed and knownclosed output before
 * ANY prepare/reset/sector borrow; NF consumed alone is not SI durability.
 * A/B require both file contexts knownclosed. ExistingC permits only owned
 * readonly source0+INFO, output1 knownclosed, quiet single engine.
 * No UI calls/pointers/state. No phase BSS initialization assumed.
 * Read selection before existing-C OPEN; retain returned scalar privately.
 * Return 80..83=valid|profile0/1|(existing<<1), 0=failed checked capsule read.
 * Flags are caller input, never substitute for dispatcher capability. */
nf_u8 fp_selection(void);
/* 0 success, NF error otherwise. C is UNPLANNED for generated extras/explicit
 * per-file replacement. Existing-C mode imports readonly logical tree only;
 * collision/merge policy belongs to coordinator, no silent DOS overwrite. */
nf_u8 fp_prepare_c(nf_u8 flags);
nf_u8 fp_prepare_b(nf_u8 flags); /* planned blank360KiB */
/* External text is supplied at3DA000/3DC000, <=8192 each, disjoint originals.
 * Derives A at200000 preserving boot/system placement; no persistence claim. */
nf_u8 fp_prepare_a(nf_u8 flags,nf_u16 auto_size,nf_u16 config_size);
#endif

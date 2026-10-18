#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct Dos64Machine Dos64Machine;
void dos64_native_display_enable(struct Dos64Machine *);
void dos64_native_display_seed(struct Dos64Machine *,const uint8_t *);
uint8_t dos64_native_display_reg(struct Dos64Machine *,uint8_t);
uint32_t dos64_native_display_reads(struct Dos64Machine *,uint8_t);
uint32_t dos64_native_display_writes(struct Dos64Machine *,uint8_t);
typedef struct Dos64Regs {
    uint16_t pc;
    uint8_t sp, a, x, y, p;
    uint64_t cycles, instructions;
} Dos64Regs;
typedef enum Dos64RunStatus {
    DOS64_RUN_RETURNED = 0,
    DOS64_RUN_MODEL_FAULT = 1,
    DOS64_RUN_STACK_IMBALANCE = 2,
    DOS64_RUN_CYCLE_BUDGET = 3,
    DOS64_RUN_UNEXPECTED_BRK = 4
} Dos64RunStatus;
typedef struct Dos64RunResult {
    Dos64Regs regs;
    Dos64RunStatus status;
    uint8_t stack_high_water;
} Dos64RunResult;
Dos64Machine *dos64_create(void);
void dos64_destroy(Dos64Machine *);
void dos64_poke(Dos64Machine *, uint16_t, uint8_t);
uint8_t dos64_peek(const Dos64Machine *, uint16_t);
void dos64_load(Dos64Machine *, uint16_t, const uint8_t *, size_t);
void dos64_set_regs(Dos64Machine *, Dos64Regs);
Dos64Regs dos64_get_regs(const Dos64Machine *);
void dos64_step(Dos64Machine *);
/* Execute real Peddle instructions up to the return sentinel or a failure.
 * The budget is relative to the current clock and checked between instructions.
 * No CPU/device state or write tracking is reset by this operation. */
Dos64RunResult dos64_run(Dos64Machine *, uint16_t sentinel, uint64_t cycle_budget);
void dos64_clear_writes(Dos64Machine *);
uint8_t dos64_was_written(const Dos64Machine *, uint16_t);
uint8_t dos64_model_fault(const Dos64Machine *);
void dos64_enable_reu(Dos64Machine *);
uint8_t dos64_enable_reu_sized(Dos64Machine *, uint32_t size_kib);
void dos64_reu_poke(Dos64Machine *, uint32_t, uint8_t);
uint8_t dos64_reu_peek(const Dos64Machine *, uint32_t);
uint8_t dos64_bus_read(Dos64Machine *, uint16_t);
void dos64_bus_write(Dos64Machine *, uint16_t, uint8_t);
uint64_t dos64_dma_bytes(const Dos64Machine *);
uint64_t dos64_dma_transfers(const Dos64Machine *);
/* Adversarial model only: incomplete DMA reports DONE to test readback. */
void dos64_reu_silent_after(Dos64Machine *,uint64_t,uint32_t);
void dos64_reu_fail_after(Dos64Machine *, uint64_t skip, uint32_t prefix_bytes);
uint8_t dos64_reu_read(const Dos64Machine *, uint32_t address, uint8_t *out, size_t length);
uint32_t dos64_reu_compare(const Dos64Machine *, uint32_t address, const uint8_t *expected, size_t length);
/* UCI is disabled until explicitly enabled. delay schedules mock firmware
 * events by modeled register observations, never native elapsed-time ticks.
 * counter:0 PUSH,1 ACCEPT,2 ABORT,3 CLR_ERR,4 data reads,5 status reads,
 * 6 current captured command bytes. Remaining helpers require enabled UCI. */
void dos64_uci_model_enable(void *, uint16_t base, uint32_t delay, uint8_t id);
void dos64_uci_model_block(void *, const uint8_t *, size_t, const uint8_t *, size_t);
void dos64_uci_model_stuck(void *, uint8_t);
void dos64_uci_model_error(void *);
void dos64_uci_model_stale(void *, uint8_t);
uint64_t dos64_uci_model_count(void *, uint8_t);
uint8_t dos64_uci_model_command(void *, uint16_t);
/* Optional read-only whole-floppy source fixture; requires explicit UCI model
 * enable first. Source length0..368641, fixed fixture raw path disk.img and
 * READ target1; never writes source, target RAM or REU. Ordinary UCI remains
 * scripted and strict until this separate enable. See image_import_model.h. */
void import_model_source(void *, const uint8_t *, size_t);
void import_model_faults(void *, int command, int corrupt, int short_offset, int close);
uint32_t import_model_commands(void *);
uint32_t import_model_position(void *);
uint8_t import_model_open(void *);
/* CIA clock is disabled until explicitly enabled. Advances/scripts are actual
 * model PHI2 inputs, never derived from Peddle CPU clocks or turbo settings.
 * Other helpers require an enabled model. */
uint8_t native_runtime_nmi_checked(struct Dos64Machine *);
void native_runtime_require_nmi_order(struct Dos64Machine *,uint16_t);
/* Explicit test-only edge at an instruction boundary; runs real Peddle NMI. */
void dos64_nmi_at_pc(struct Dos64Machine *,uint16_t);
uint32_t dos64_nmi_delivered(struct Dos64Machine *);
void native_runtime_control_enable(struct Dos64Machine *);
void dos64_cia_clock_enable(struct Dos64Machine *);
void dos64_cia_clock_seed(struct Dos64Machine *, uint16_t a, uint16_t b);
void dos64_cia_clock_advance(struct Dos64Machine *, uint32_t ticks);
void dos64_cia_clock_step(struct Dos64Machine *, uint32_t per_read);
void dos64_cia_clock_script(struct Dos64Machine *, const uint32_t *, size_t);
uint32_t dos64_cia_clock_low_snapshot(const struct Dos64Machine *);
uint32_t dos64_cia_clock_reads(const struct Dos64Machine *, uint8_t reg);
uint32_t dos64_cia_clock_writes(const struct Dos64Machine *, uint8_t reg);
uint16_t dos64_cia_clock_count(const struct Dos64Machine *, uint8_t timer);
uint16_t dos64_cia_clock_latch(const struct Dos64Machine *, uint8_t timer);
void dos64_cia_clock_icr_seed(struct Dos64Machine *, uint8_t mask, uint8_t pending);
uint8_t dos64_cia_clock_mask(const struct Dos64Machine *);
uint8_t dos64_cia_clock_pending(const struct Dos64Machine *);
/* Standalone clock-probe fixture ONLY. Explicit raster-read scripts advance
 * CIA inputs; this is not physical VIC timing or CPU-clock-derived time.
 * Disabled by default; mode0 advances,1 freezes low,2 freezes high,3 tears.
 * lines1..512,ticks0..65536,repeats1..65535. Invalid scripts fault explicitly. */
void dos64_clock_probe_model_enable(Dos64Machine *, uint16_t lines,
                                   uint32_t ticks_per_line, uint32_t repeats,
                                   uint8_t mode);
uint64_t dos64_clock_probe_model_reads(const Dos64Machine *);
#ifdef __cplusplus
}
#endif

#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct Dos64Machine Dos64Machine;
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
void dos64_reu_fail_after(Dos64Machine *, uint64_t skip, uint32_t prefix_bytes);
uint8_t dos64_reu_read(const Dos64Machine *, uint32_t address, uint8_t *out, size_t length);
uint32_t dos64_reu_compare(const Dos64Machine *, uint32_t address, const uint8_t *expected, size_t length);
#ifdef __cplusplus
}
#endif

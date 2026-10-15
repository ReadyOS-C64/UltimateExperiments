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
Dos64Machine *dos64_create(void);
void dos64_destroy(Dos64Machine *);
void dos64_poke(Dos64Machine *, uint16_t, uint8_t);
uint8_t dos64_peek(const Dos64Machine *, uint16_t);
void dos64_load(Dos64Machine *, uint16_t, const uint8_t *, size_t);
void dos64_set_regs(Dos64Machine *, Dos64Regs);
Dos64Regs dos64_get_regs(const Dos64Machine *);
void dos64_step(Dos64Machine *);
void dos64_clear_writes(Dos64Machine *);
uint8_t dos64_was_written(const Dos64Machine *, uint16_t);
uint8_t dos64_model_fault(const Dos64Machine *);
#ifdef __cplusplus
}
#endif

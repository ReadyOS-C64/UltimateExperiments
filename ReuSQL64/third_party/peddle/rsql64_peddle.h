#ifndef RSQL64_PEDDLE_H
#define RSQL64_PEDDLE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct Rsql64Peddle Rsql64Peddle;

typedef struct Rsql64PeddleRegs {
    uint16_t pc;
    uint16_t pc0;
    uint8_t sp;
    uint8_t a;
    uint8_t x;
    uint8_t y;
    uint8_t p;
    uint64_t cycles;
    uint64_t instructions;
} Rsql64PeddleRegs;

Rsql64Peddle *rsql64_peddle_create(uint32_t reu_size_kib);
void rsql64_peddle_destroy(Rsql64Peddle *machine);
void rsql64_peddle_reset(Rsql64Peddle *machine);
void rsql64_peddle_clear_memory(Rsql64Peddle *machine);
void rsql64_peddle_load(Rsql64Peddle *machine, uint16_t address, const uint8_t *bytes, size_t len);
uint8_t rsql64_peddle_read(const Rsql64Peddle *machine, uint16_t address);
void rsql64_peddle_write(Rsql64Peddle *machine, uint16_t address, uint8_t value);
uint8_t rsql64_peddle_read_reu(const Rsql64Peddle *machine, uint32_t address);
void rsql64_peddle_write_reu(Rsql64Peddle *machine, uint32_t address, uint8_t value);
size_t rsql64_peddle_load_reu(Rsql64Peddle *machine, uint32_t address, const uint8_t *bytes, size_t len);
size_t rsql64_peddle_copy_reu(const Rsql64Peddle *machine, uint32_t address, uint8_t *bytes, size_t len);
uint32_t rsql64_peddle_reu_size(const Rsql64Peddle *machine);
void rsql64_peddle_set_pc(Rsql64Peddle *machine, uint16_t pc);
void rsql64_peddle_set_sp(Rsql64Peddle *machine, uint8_t sp);
void rsql64_peddle_set_a(Rsql64Peddle *machine, uint8_t value);
void rsql64_peddle_set_x(Rsql64Peddle *machine, uint8_t value);
void rsql64_peddle_set_y(Rsql64Peddle *machine, uint8_t value);
void rsql64_peddle_set_p(Rsql64Peddle *machine, uint8_t value);
void rsql64_peddle_step_instruction(Rsql64Peddle *machine);
Rsql64PeddleRegs rsql64_peddle_regs(const Rsql64Peddle *machine);

#ifdef __cplusplus
}
#endif

#endif

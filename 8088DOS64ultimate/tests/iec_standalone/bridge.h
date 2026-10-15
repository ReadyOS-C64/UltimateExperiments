#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct IecMachine IecMachine;
typedef struct IecRun { uint64_t cycles,instructions,kernal_calls,reads; uint32_t dma_count,dma_bytes; uint16_t pc; uint8_t sp,fault,status; } IecRun;
IecMachine *iec_create(const uint8_t *prg,size_t prg_len,const uint8_t *source,size_t source_len,uint8_t fault);
void iec_destroy(IecMachine *);
IecRun iec_run(IecMachine *,uint16_t entry,uint16_t stop,uint64_t budget);
const uint8_t *iec_ram(IecMachine *);
const uint8_t *iec_reu(IecMachine *);
void iec_poke(IecMachine *,uint16_t,uint8_t);
#ifdef __cplusplus
}
#endif

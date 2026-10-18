#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void hd_trace_enable(void*,uint16_t,uint16_t,uint16_t,uint16_t);
void hd_trace_phase(void*,uint8_t);
uint8_t hd_trace_valid(void*);
uint32_t hd_trace_requests(void*);
uint32_t hd_trace_field(void*,uint32_t,uint8_t);
uint8_t hd_trace_data(void*,uint32_t,uint32_t);
uint32_t hd_trace_writes(void*);
uint32_t hd_trace_write_field(void*,uint32_t,uint8_t);
uint8_t hd_trace_write_data(void*,uint32_t,uint32_t);
uint8_t hd_model_copy_source(void*,uint8_t*,size_t);
#ifdef __cplusplus
}
#endif

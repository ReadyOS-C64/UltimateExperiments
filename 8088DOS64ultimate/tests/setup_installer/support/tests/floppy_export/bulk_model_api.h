#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void bulk_model_enable(void*);
void bulk_model_faults(void*,int,int,int,int,int);
uint32_t bulk_model_commands(void*);
uint8_t bulk_model_command(void*,uint32_t,uint32_t);
uint32_t bulk_model_size(void*,const char*);
uint8_t bulk_model_open(void*,uint8_t);
uint8_t bulk_model_read(void*,const char*,uint8_t*,uint32_t);
void bulk_model_seed(void*,const char*,const uint8_t*,uint32_t);
void bulk_reu_seed(void*,uint32_t,const uint8_t*,uint32_t);
#ifdef __cplusplus
}
#endif

#pragma once
#include "peddle_bridge.h"
#ifdef __cplusplus
extern "C" {
#endif
void dir_model_enable(void*);
void dir_model_path(void*,const char*);
void dir_model_row(void*,const char*,uint8_t,const uint8_t*,uint32_t);
void dir_model_fault(void*,int,int,int);
uint32_t dir_model_commands(void*);
uint32_t dir_model_cmd_size(void*,uint32_t);
uint8_t dir_model_cmd_byte(void*,uint32_t,uint32_t);
void bulk_model_enable(void*);
void bulk_model_seed(void*,const char*,const uint8_t*,uint32_t);
#ifdef __cplusplus
}
#endif

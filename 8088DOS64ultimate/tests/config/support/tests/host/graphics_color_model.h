#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct Dos64Machine;
void dos64_graphics_color_enable(struct Dos64Machine *);
uint8_t dos64_graphics_color_peek(struct Dos64Machine *,uint16_t);
#ifdef __cplusplus
}
#endif

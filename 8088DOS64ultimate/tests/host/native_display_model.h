#pragma once
#include <stdint.h>
#ifdef __cplusplus
#include <array>
// Explicit functional register readback only. No raster/DMA/scanout model.
// CIA2 bank pins are separate from the elapsed-clock timer model; no access
// to CIA timers, ICR, TOD or CIA1 is implemented or silently accepted.
struct NativeDisplayModel {
 std::array<uint8_t,8> regs{};
 std::array<uint32_t,8> reads{},writes{};
 bool fault=false;
 static int index(uint16_t a) {
  constexpr uint16_t addresses[]={0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdd00,0xdd02};
  for(int i=0;i<8;++i)if(a==addresses[i])return i;return -1;
 }
 static bool owns(uint16_t a){return index(a)>=0;}
 uint8_t read(uint16_t a){int i=index(a);if(i<0){fault=true;return 0;}++reads[i];
  if(i==1)return regs[i]|0xc0;if(i==2)return regs[i]|1;if(i==4||i==5)return regs[i]|0xf0;return regs[i];}
 void write(uint16_t a,uint8_t v){int i=index(a);if(i<0){fault=true;return;}++writes[i];regs[i]=v;}
};
extern "C" {
#endif
struct Dos64Machine;
void dos64_native_display_enable(struct Dos64Machine *);
void dos64_native_display_seed(struct Dos64Machine *,const uint8_t *);
uint8_t dos64_native_display_reg(struct Dos64Machine *,uint8_t);
uint32_t dos64_native_display_reads(struct Dos64Machine *,uint8_t);
uint32_t dos64_native_display_writes(struct Dos64Machine *,uint8_t);
#ifdef __cplusplus
}
#endif

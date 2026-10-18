#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
#include <array>
// Independent switch-network model. Low outputs/joysticks propagate through
// pressed switches until a fixed point; there are no per-key isolation diodes.
// Only CIA1 ports/DDRs implemented. Timers/ICR/TOD accesses are test faults.
struct HostInputModel {
    std::array<uint8_t,4> regs{0xff,0xff,0,0};
    std::array<uint8_t,8> keys{};
    std::array<uint32_t,16> reads{},writes{};
    uint8_t joy_a=0,joy_b=0;
    bool fault=false;
    uint16_t lowPins() const {
        uint8_t a=(uint8_t(~regs[0])&regs[2])|joy_a;
        uint8_t b=(uint8_t(~regs[1])&regs[3])|joy_b;
        for(unsigned pass=0;pass<16;++pass) {
            uint8_t old_a=a,old_b=b;
            for(unsigned i=0;i<8;++i) {
                if(a&(1u<<i)) b|=keys[i];
                if(b&keys[i]) a|=uint8_t(1u<<i);
            }
            if(a==old_a&&b==old_b) break;
        }
        return a|(uint16_t(b)<<8);
    }
    uint8_t read(uint8_t reg) {
        ++reads[reg];
        if(reg<2) return uint8_t(~(lowPins()>>(reg*8)));
        if(reg<4) return regs[reg];
        fault=true;return 0;
    }
    void write(uint8_t reg,uint8_t value) {
        ++writes[reg];
        if(reg<4) regs[reg]=value;else fault=true;
    }
};
extern "C" {
#endif
struct Dos64Machine;
void dos64_host_input_model_enable(struct Dos64Machine *);
void dos64_host_input_model_keys(struct Dos64Machine *, const uint8_t *);
void dos64_host_input_model_seed(struct Dos64Machine *, const uint8_t *);
uint8_t dos64_host_input_model_reg(struct Dos64Machine *, uint8_t);
uint32_t dos64_host_input_model_reads(struct Dos64Machine *, uint8_t);
uint32_t dos64_host_input_model_writes(struct Dos64Machine *, uint8_t);
#ifdef __cplusplus
}
#endif

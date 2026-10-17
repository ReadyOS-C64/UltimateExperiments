#pragma once
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
#include <array>
#include <vector>
// Functional subset for host_clock.s only. Phi2 advances are explicit test
// inputs, NEVER inferred from Peddle clocks/instruction counts. Not a complete
// cycle-exact 6526. One-tick A->B propagation models the dangerous reload race.
struct CiaClockModel {
    std::array<uint16_t,2> count{0xffff,0xffff}, latch{0xffff,0xffff};
    std::array<uint8_t,2> control{0,0}, startup{0,0};
    std::array<uint32_t,16> reads{}, writes{};
    std::vector<uint32_t> script;
    size_t script_index=0;
    uint32_t read_step=0, last_low_snapshot=0xffffffff;
    uint8_t mask=0, pending=0;
    bool cascade_pending=false, unsupported=false;
    void advance(uint32_t n) {
        while(n--) {
            const bool old_event=cascade_pending; cascade_pending=false;
            for(int t=1;t>=0;--t) {
                if(!(control[t]&1)) continue;
                if(startup[t]) {--startup[t]; continue;}
                bool pulse=t==0 ? !(control[0]&0x20) : ((control[1]&0x60)==0 ? true : ((control[1]&0x60)==0x40 && old_event));
                if(!pulse) continue;
                if(count[t]) --count[t];
                else {
                    count[t]=latch[t]; pending|=uint8_t(1u<<t);
                    if(t==0) cascade_pending=true;
                    if(control[t]&8) control[t]&=0xfe;
                }
            }
        }
    }
    uint8_t read(uint8_t reg) {
        ++reads[reg]; advance(script_index<script.size()?script[script_index++]:read_step);
        if(reg>=4&&reg<=7) {
            if(reg==4) last_low_snapshot=(uint32_t(count[1])<<16)|count[0];
            return uint8_t(count[(reg-4)/2]>>((reg&1)*8));
        }
        if(reg==14||reg==15) return control[reg-14]&0xef;
        if(reg==13) {uint8_t r=pending|((pending&mask)?0x80:0); pending=0; return r;}
        unsupported=true; return 0;
    }
    void write(uint8_t reg,uint8_t value) {
        ++writes[reg];
        if(reg>=4&&reg<=7) {
            unsigned t=(reg-4)/2;
            if(!(reg&1)) latch[t]=(latch[t]&0xff00)|value;
            else {latch[t]=(latch[t]&0xff)|(uint16_t(value)<<8); if(!(control[t]&1)) count[t]=latch[t];}
            return;
        }
        if(reg==14||reg==15) {
            unsigned t=reg-14; bool starting=!(control[t]&1)&&(value&1);
            control[t]=value&0xef;
            if(value&0x10) {count[t]=latch[t]; startup[t]=1;}
            if(starting) startup[t]=2;
            return;
        }
        if(reg==13) {if(value&0x80) mask|=value&0x1f;else mask&=~(value&0x1f);return;}
        unsupported=true;
    }
};
extern "C" {
#endif
struct Dos64Machine;
void dos64_cia_clock_enable(struct Dos64Machine *);
void dos64_cia_clock_seed(struct Dos64Machine *, uint16_t a, uint16_t b);
void dos64_cia_clock_advance(struct Dos64Machine *, uint32_t ticks);
void dos64_cia_clock_step(struct Dos64Machine *, uint32_t per_read);
void dos64_cia_clock_script(struct Dos64Machine *, const uint32_t *, size_t);
uint32_t dos64_cia_clock_low_snapshot(const struct Dos64Machine *);
uint32_t dos64_cia_clock_reads(const struct Dos64Machine *, uint8_t reg);
uint32_t dos64_cia_clock_writes(const struct Dos64Machine *, uint8_t reg);
uint16_t dos64_cia_clock_count(const struct Dos64Machine *, uint8_t timer);
uint16_t dos64_cia_clock_latch(const struct Dos64Machine *, uint8_t timer);
void dos64_cia_clock_icr_seed(struct Dos64Machine *, uint8_t mask, uint8_t pending);
uint8_t dos64_cia_clock_mask(const struct Dos64Machine *);
uint8_t dos64_cia_clock_pending(const struct Dos64Machine *);
#ifdef __cplusplus
}
#endif

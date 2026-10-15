#pragma once
// Functional register model of the used FPGA protocol only, not timing/IRQ/DMA.
// Primary source pins: GideonZ/1541ultimate v3.14
// 830665cd9b41bc34b868f5c1a1179c5baa4989af, and master
// 125da1fec3e3b50d31f6409ec217d80693ed674d
// fpga/io/command_interface/vhdl_source/command_protocol.vhd and
// software/io/command_interface/command_intf.cc. DATA_ACC updates FPGA state
// synchronously; firmware publication/handshake clear/abort are scheduled.
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void dos64_uci_model_enable(void *, uint16_t base, uint32_t delay, uint8_t id);
void dos64_uci_model_block(void *, const uint8_t *, size_t, const uint8_t *, size_t);
void dos64_uci_model_stuck(void *, uint8_t);
void dos64_uci_model_error(void *);
void dos64_uci_model_stale(void *, uint8_t);
uint64_t dos64_uci_model_count(void *, uint8_t);
uint8_t dos64_uci_model_command(void *, uint16_t);
#ifdef __cplusplus
}
#include <array>
#include <vector>
#include <cstdint>
#include <algorithm>
struct UciModel {
    struct Block { std::vector<uint8_t> data, status; };
    uint16_t base = 0xdf1c;
    uint8_t id = 0xc9, state = 0, handshake = 0;
    bool error = false, fault = false, stuck = false;
    uint32_t delay = 3, pending = 0, accept_clear = 0;
    uint8_t event = 0;
    size_t block = 0, dp = 0, sp = 0, cp = 0;
    uint64_t pushes = 0, accepts = 0, aborts = 0, clears = 0, data_reads = 0, stat_reads = 0;
    std::vector<uint8_t> command;
    std::vector<Block> blocks;
    bool owns(uint16_t a) const { return a >= base && a < base+4; }
    void publish() {
        if (block >= blocks.size()) { fault = true; return; }
        state = block+1 < blocks.size() ? 0x30 : 0x20;
        dp = sp = 0;
    }
    void advance() {
        if (stuck) return;
        if (accept_clear && --accept_clear == 0) handshake &= ~2;
        if (!event) return;
        if (pending && --pending) return;
        uint8_t e = event; event = 0;
        if (e == 1) { handshake &= ~1; cp = 0; publish(); }
        if (e == 2) { ++block; publish(); accept_clear = delay ? delay : 1; }
        if (e == 3) { state = handshake = 0; command.clear(); dp = sp = cp = 0; }
    }
    uint8_t status() const {
        uint8_t v = state | handshake | (error ? 8 : 0);
        if ((state & 0x20) && !(handshake & 4) && block < blocks.size()) {
            if (dp < blocks[block].data.size()) v |= 0x80;
            if (sp < (blocks[block].status.size() & 255)) v |= 0x40;
        }
        return v;
    }
    uint8_t read(uint16_t address) {
        advance();
        switch (address-base) {
        case 0: return status();
        case 1: return id;
        case 2:
            if (!(status() & 0x80)) { fault = true; return 0; }
            ++data_reads; { auto v=blocks[block].data[dp]; if(dp<895)++dp; return v; }
        case 3:
            if (!(status() & 0x40)) { fault = true; return 0; }
            ++stat_reads; {auto v=blocks[block].status[sp]; if(sp<255)++sp; return v; }
        }
        fault = true; return 0;
    }
    void write(uint16_t address, uint8_t value) {
        advance();
        if (address == base+1) {
            if (state) { fault = true; return; }
            if(command.size()<=cp)command.resize(cp+1); command[cp]=value; if(cp<895)++cp; return;
        }
        if (address != base || (value & 0xf0)) { fault = true; return; }
        if (value & 8) { ++clears; error = false; }
        if (value & 1) {
            ++pushes;
            if (state) error = true;
            else { state = 0x10; handshake |= 1; block = 0; event = 1; pending = delay; }
        }
        if ((value & 2) && (state & 0x20)) {
            ++accepts;
            handshake = (handshake & ~2) | ((state & 0x10) ? 2 : 0);
            state &= ~0x20;
            if (state) { event = 2; pending = delay; }
            else { command.clear(); dp = sp = cp = 0; }
        }
        if (value & 4) { ++aborts; handshake |= 4; event = 3; pending = delay; }
    }
};

#endif

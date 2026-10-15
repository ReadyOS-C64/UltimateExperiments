#pragma once
#include <array>
#include <vector>
#include <cstdint>

// Functional subset used by dos64_reu_transfer. No bus-stall timing, IRQ,
// deferred FF00 trigger, compare or swap behavior is claimed.
class ReuModel {
public:
    std::vector<uint8_t> bytes;
    std::array<uint8_t,11> regs{0x10,0x10,0,0,0,0,0,0xff,0xff,0x1f,0x3f};
    std::array<uint8_t,7> reload{};
    uint64_t dma_bytes = 0;
    uint64_t transfers = 0;
    bool unsupported = false;
    explicit ReuModel(uint32_t size_kib = 4096) : bytes(size_kib*1024u) {}

    uint8_t read(unsigned index) {
        const auto value = regs[index];
        if (index == 0) regs[0] &= 0x1f;
        return value;
    }
    void write(unsigned index, uint8_t value,
               std::array<uint8_t,65536> &ram,
               std::array<uint8_t,65536> &written) {
        if (index == 0) return;
        regs[index] = value;
        if (index >= 2 && index <= 8) reload[index-2] = value;
        if (index == 9) {
            regs[9] |= 0x1f;
            if (value & 0xe0) unsupported = true;
        }
        if (index == 10) regs[10] |= 0x3f;
        if (index != 1 || !(value & 0x80)) return;
        const auto mode = value & 3;
        if (!(value & 0x10) || mode > 1 || (regs[9] & 0xe0)) {
            unsupported = true;
            return;
        }
        uint16_t host = regs[2] | (uint16_t(regs[3])<<8);
        uint32_t far = regs[4] | (uint32_t(regs[5])<<8) | (uint32_t(regs[6])<<16);
        const unsigned count = (regs[7] | (unsigned(regs[8])<<8)) ?
                               (regs[7] | (unsigned(regs[8])<<8)) : 65536;
        for (unsigned index = 0; index < count; ++index) {
            const auto physical = far & (bytes.size()-1);
            if (mode == 0) bytes[physical] = ram[host];
            else { ram[host] = bytes[physical]; written[host] = 1; }
            if (!(regs[10] & 0x80)) ++host;
            if (!(regs[10] & 0x40)) {
                // Expanded REC bank latch does not carry across bit 19.
                far = (far & 0xf80000) | ((far+1) & 0x07ffff);
            }
        }
        dma_bytes += count;
        ++transfers;
        if (value & 0x20) {
            for (unsigned index = 0; index < 7; ++index) regs[index+2] = reload[index];
        } else {
            regs[2] = uint8_t(host); regs[3] = uint8_t(host>>8);
            regs[4] = uint8_t(far); regs[5] = uint8_t(far>>8); regs[6] = uint8_t(far>>16);
            regs[7] = 1; regs[8] = 0; // REC post-completion count, not zero
        }
        regs[0] |= 0x40;
        regs[1] = (value & 0x7f) | 0x10;
    }
};

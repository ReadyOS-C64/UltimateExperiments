// CPU and functional REU embedding. No disk, VIC or turbo timing model.
#include "Peddle.h"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
constexpr unsigned ram_size = 65536;
constexpr unsigned reu_size = 16 * 1024 * 1024;
constexpr unsigned reu_counter = 512 * 1024 - 1;
constexpr unsigned reu_base = 0xdf00;
constexpr uint16_t return_pc = 0x0200;
constexpr uint8_t caller_sp = 0xfd;
constexpr uint8_t stack_floor = 0xc0;
constexpr unsigned dma_tile_start = 0x8000;
constexpr unsigned dma_tile_end = 0xa000;
constexpr unsigned cache_start = 0x080000;
constexpr unsigned cache_end = 0x0a0000;

enum RunFailure { none, timeout, invalid_reu_io, cpu_write, stack, cpu_dma, reu_dma };

bool within(unsigned address, unsigned size, unsigned first, unsigned end) {
    return address >= first && address < end && size <= end - address;
}

class Machine : public peddle::Peddle {
public:
    std::array<uint8_t, ram_size> ram{};
    std::vector<uint8_t> reu = std::vector<uint8_t>(reu_size);
    unsigned reu_capacity = reu_size;
    std::array<uint8_t, 11> io{0x10, 0x10, 0, 0, 0, 0, 0, 0xff, 0xff, 0x1f, 0x3f};
    std::array<uint8_t, 8> keyboard{};
    bool keyboard_enabled = false;
    bool group4_workspace = false;
    bool group8_dma = false;
    std::vector<uint64_t> cycle_profile;
    uint64_t dma_calls = 0;
    uint64_t dma_bytes = 0;
    RunFailure failure = none;
    unsigned failed_address = 0;
    unsigned model_length = 0;

    Machine() {
        ram.fill(0xa5);
        keyboard.fill(0xff);
        setModel(peddle::MOS_6510);
        reset();
    }

    int run(uint16_t pc, uint64_t limit, uint64_t *stats, uint8_t accumulator,
            uint8_t x, unsigned guard_model_length) {
        reg.pc = reg.pc0 = pc;
        reg.sp = caller_sp;
        reg.a = accumulator;
        reg.x = x;
        ram[0x1fe] = (return_pc - 1) & 0xff;
        ram[0x1ff] = (return_pc - 1) >> 8;
        next = peddle::fetch;
        setP(0x24);
        const auto start = clock;
        const auto start_calls = dma_calls;
        const auto start_bytes = dma_bytes;
        failure = none;
        failed_address = 0;
        model_length = guard_model_length;
        uint8_t lowest_stack = caller_sp;
        uint64_t instructions = 0;
        const bool profiling = !cycle_profile.empty();
        while (reg.pc != return_pc && instructions < limit && failure == none) {
            const auto instruction_pc = reg.pc;
            const auto instruction_start = clock;
            do {
                execute();
                ++clock;
            } while (next != peddle::fetch);
            if (profiling) cycle_profile[instruction_pc] += clock - instruction_start;
            ++instructions;
            if (model_length) {
                lowest_stack = std::min(lowest_stack, reg.sp);
                if (failure == none && (reg.sp < stack_floor ||
                    (reg.pc == return_pc ? reg.sp != 0xff : reg.sp > caller_sp))) {
                    failure = stack;
                    failed_address = 0x100 + reg.sp;
                }
            }
        }
        stats[0] = instructions;
        stats[1] = clock - start;
        stats[2] = dma_calls - start_calls;
        stats[3] = dma_bytes - start_bytes;
        stats[4] = getP();
        stats[5] = reg.pc;
        stats[6] = reg.a;
        stats[7] = 0xff - lowest_stack;
        stats[8] = failed_address;
        model_length = 0;
        return failure ? failure : (reg.pc == return_pc ? none : timeout);
    }
private:
    uint8_t read(uint16_t address) override {
        if (keyboard_enabled && address == 0xdc01) {
            uint8_t rows = 0xff;
            const auto low_outputs = ram[0xdc02] & ~ram[0xdc00];
            for (unsigned col = 0; col < keyboard.size(); ++col) {
                if (low_outputs & (1 << col)) rows &= keyboard[col];
            }
            return rows;
        }
        if (address < reu_base || address >= reu_base + io.size())
            return ram[address];
        const auto index = address - reu_base;
        const auto value = io[index];
        if (index == 0) io[0] &= 0x1f;
        return value;
    }
    uint8_t readDasm(uint16_t address) const override { return ram[address]; }

    void write(uint16_t address, uint8_t value) override {
        if (model_length && !((group4_workspace && (within(address, 1, 0x60, 0x76) ||
                                                     within(address, 1, 0xc000, 0xcc00))) ||
                              within(address, 1, 0x80, 0xf0) ||
                              within(address, 1, 0x100 + stack_floor, 0x200) ||
                              within(address, 1, 0x5000, dma_tile_end) ||
                              within(address, 1, reu_base + 1, reu_base + io.size()))) {
            failure = cpu_write;
            failed_address = address;
            return;
        }
        if (address < reu_base || address >= reu_base + io.size()) {
            ram[address] = value;
            return;
        }
        const auto index = address - reu_base;
        if (index == 0) return;
        io[index] = value;
        if (index == 1 && (value & 0x80)) dma(value);
    }

    void dma(uint8_t command) {
        if ((command != 0x90 && command != 0x91) || (io[9] & 0xe0) || (io[10] & 0xc0)) {
            failure = invalid_reu_io;
            failed_address = reu_base + 1;
            return;
        }
        unsigned cpu = io[2] | unsigned(io[3]) << 8;
        unsigned far = io[4] | unsigned(io[5]) << 8 | unsigned(io[6]) << 16;
        const unsigned length = io[7] | unsigned(io[8]) << 8;
        const unsigned count = length ? length : ram_size;
        if (model_length) {
            const bool model_read = (command & 1) && within(far, count, 0, model_length);
            const bool group8_read = group8_dma && model_read && within(cpu, count, 0xc400, 0xcb00);
            if (!within(cpu, count, dma_tile_start, dma_tile_end) && !group8_read) {
                failure = cpu_dma;
                failed_address = cpu;
                return;
            }
            const unsigned bank = far & ~reu_counter;
            const bool crosses_bank = count > bank + reu_counter + 1 - far;
            if (crosses_bank || !(model_read || within(far, count, cache_start, cache_end))) {
                failure = reu_dma;
                failed_address = far;
                return;
            }
        }
        // The address counter does not carry out of a 512 KiB region.
        const unsigned high = far & ~reu_counter;
        unsigned remaining = count;
        while (remaining) {
            const unsigned physical = far & (reu_capacity - 1);
            const unsigned chunk = std::min({remaining, ram_size - cpu,
                                              reu_counter + 1 - (far & reu_counter),
                                              reu_capacity - physical});
            if (command & 1) std::memcpy(ram.data() + cpu, reu.data() + physical, chunk);
            else std::memcpy(reu.data() + physical, ram.data() + cpu, chunk);
            cpu = (cpu + chunk) & 0xffff;
            far = high | ((far + chunk) & reu_counter);
            remaining -= chunk;
        }
        io[2] = cpu;
        io[3] = cpu >> 8;
        io[4] = far;
        io[5] = far >> 8;
        io[6] = far >> 16;
        io[7] = 1;
        io[8] = 0;
        io[0] |= 0x40;
        io[1] &= 0x7f;
        ++dma_calls;
        dma_bytes += count;
    }
};
}

extern "C" {
Machine *tiny_new() { return new Machine; }
void tiny_free(Machine *m) { delete m; }
uint8_t *tiny_ram(Machine *m) { return m->ram.data(); }
uint8_t *tiny_reu(Machine *m) { return m->reu.data(); }
void tiny_set_reu_capacity(Machine *m, unsigned capacity) { m->reu_capacity = capacity; }
void tiny_enable_group4_workspace(Machine *m) { m->group4_workspace = true; }
void tiny_enable_group8_dma(Machine *m) { m->group8_dma = true; }
uint8_t *tiny_keyboard(Machine *m) {
    m->keyboard_enabled = true;
    return m->keyboard.data();
}
uint64_t *tiny_enable_cycle_profile(Machine *m) {
    m->cycle_profile.assign(ram_size, 0);
    return m->cycle_profile.data();
}
int tiny_run(Machine *m, uint16_t pc, uint64_t limit, uint64_t *stats,
             uint8_t accumulator, uint8_t x, unsigned guard_model_length) {
    return m->run(pc, limit, stats, accumulator, x, guard_model_length);
}
}

#include "peddle_bridge.h"
#include "Peddle.h"
#include "reu_model.h"
#include <array>
#include <algorithm>
#include <cstring>
#include <memory>

class Machine : public peddle::Peddle {
public:
    std::array<uint8_t, 65536> ram{};
    std::array<uint8_t, 65536> written{};
    std::array<uint8_t, 4096> io{};
    uint64_t instructions = 0;
    bool unsupported = false;
    std::unique_ptr<ReuModel> reu;
    Machine() {
        setModel(peddle::MOS_6510); reset(); reg.sp = 0xff;
        reg.pport.direction = 0x2f; reg.pport.data = 0x35;
    }
    void setRegs(Dos64Regs r) {
        reg.pc = r.pc; reg.pc0 = r.pc; next = peddle::fetch;
        reg.sp = r.sp; reg.a = r.a; reg.x = r.x; reg.y = r.y; setP(r.p);
    }
    void step() {
        // Peddle's embedding application owns clock advancement. Its
        // executeInstruction() does not increment clock. Step microcycles here
        // so budgets, delayed interrupt inputs and timing assertions are real.
        for (unsigned cycle = 0; cycle < 32; ++cycle) {
            execute(); ++clock;
            if (inFetchPhase()) { ++instructions; return; }
        }
        unsupported = true; // jam/unsupported CPU path must never hang a test
    }
    void poke(uint16_t a, uint8_t v) {
        if (a == 0) writePortDir(v);
        else if (a == 1) writePort(v);
        else ram[a] = v;
    }
    uint8_t peek(uint16_t a) const {
        if (a == 0) return reg.pport.direction;
        if (a == 1) return reg.pport.data;
        if (a == 0xd020) return io[0x20];
        return ram[a];
    }
    uint8_t busRead(uint16_t a) { return read(a); }
    void busWrite(uint16_t a, uint8_t v) { write(a,v); }
protected:
    uint8_t externalPortBits() const override { return 0xff; }
    void writePort(uint8_t v) override {
        peddle::Peddle::writePort(v); ram[1] = v; written[1] = 1;
    }
    void writePortDir(uint8_t v) override {
        peddle::Peddle::writePortDir(v); ram[0] = v; written[0] = 1;
    }
    // Banking subset: BASIC/KERNAL/character ROM return recognizable sentinels,
    // not executable ROMs. It catches data hidden by a wrong $00/$01 mapping.
    peddle::u8 read(peddle::u16 a) override {
        const auto port = readPort();
        if (a >= 0xa000 && a <= 0xbfff && (port & 3) == 3) return 0xba;
        if (a >= 0xe000 && (port & 2)) return 0xea;
        if (a >= 0xd000 && a <= 0xdfff && (port & 3)) {
            if (!(port & 4)) return 0xcc;
            if (a >= 0xdf00 && a <= 0xdf0a && reu) return reu->read(a-0xdf00);
            if (a != 0xd020) unsupported = true;
            return io[a-0xd000];
        }
        return ram[a];
    }
    void write(peddle::u16 a, peddle::u8 v) override {
        const auto port = readPort();
        written[a] = 1;
        if (a >= 0xd000 && a <= 0xdfff && (port & 3) && (port & 4)) {
            if (a >= 0xdf00 && a <= 0xdf0a && reu) {
                reu->write(a-0xdf00, v, ram, written); return;
            }
            if (a != 0xd020) unsupported = true;
            io[a-0xd000] = v;
            return;
        }
        ram[a] = v;
    }
    peddle::u8 readDasm(peddle::u16 a) const override { return ram[a]; }
};
struct Dos64Machine { Machine cpu; };
Dos64Machine *dos64_create() { return new Dos64Machine; }
void dos64_destroy(Dos64Machine *m) { delete m; }
void dos64_poke(Dos64Machine *m, uint16_t a, uint8_t v) { m->cpu.poke(a, v); }
uint8_t dos64_peek(const Dos64Machine *m, uint16_t a) { return m->cpu.peek(a); }
void dos64_load(Dos64Machine *m, uint16_t a, const uint8_t *p, size_t n) {
    n = std::min(n, static_cast<size_t>(65536u-a));
    std::memcpy(m->cpu.ram.data()+a, p, n);
}
void dos64_set_regs(Dos64Machine *m, Dos64Regs r) { m->cpu.setRegs(r); }
Dos64Regs dos64_get_regs(const Dos64Machine *m) {
    const auto &c = m->cpu;
    return { c.reg.pc, c.reg.sp, c.reg.a, c.reg.x, c.reg.y, c.getP(),
             static_cast<uint64_t>(c.clock), c.instructions };
}
void dos64_step(Dos64Machine *m) { m->cpu.step(); }
void dos64_clear_writes(Dos64Machine *m) { m->cpu.written.fill(0); }
uint8_t dos64_was_written(const Dos64Machine *m, uint16_t a) { return m->cpu.written[a]; }
uint8_t dos64_model_fault(const Dos64Machine *m) { return m->cpu.unsupported || (m->cpu.reu && m->cpu.reu->unsupported); }
void dos64_enable_reu(Dos64Machine *m) { m->cpu.reu = std::make_unique<ReuModel>(); }
uint8_t dos64_enable_reu_sized(Dos64Machine *m, uint32_t size_kib) {
    if (size_kib != 4096 && size_kib != 8192 && size_kib != 16384) return 0;
    m->cpu.reu = std::make_unique<ReuModel>(size_kib); return 1;
}
void dos64_reu_poke(Dos64Machine *m, uint32_t a, uint8_t v) { m->cpu.reu->bytes.at(a) = v; }
uint8_t dos64_reu_peek(const Dos64Machine *m, uint32_t a) { return m->cpu.reu->bytes.at(a); }
uint8_t dos64_bus_read(Dos64Machine *m, uint16_t a) { return m->cpu.busRead(a); }
void dos64_bus_write(Dos64Machine *m, uint16_t a, uint8_t v) { m->cpu.busWrite(a,v); }
uint64_t dos64_dma_bytes(const Dos64Machine *m) { return m->cpu.reu ? m->cpu.reu->dma_bytes : 0; }
uint64_t dos64_dma_transfers(const Dos64Machine *m) { return m->cpu.reu ? m->cpu.reu->transfers : 0; }
void dos64_reu_fail_after(Dos64Machine *m, uint64_t skip, uint32_t prefix_bytes) {
    m->cpu.reu->fault_armed = true;
    m->cpu.reu->fault_skip = skip;
    m->cpu.reu->fault_prefix = prefix_bytes;
}

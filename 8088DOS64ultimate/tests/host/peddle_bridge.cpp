#include "peddle_bridge.h"
#include "Peddle.h"
#include <array>
#include <algorithm>
#include <cstring>

class Machine : public peddle::Peddle {
public:
    std::array<uint8_t, 65536> ram{};
    std::array<uint8_t, 65536> written{};
    uint64_t instructions = 0;
    bool unsupported = false;
    Machine() { setModel(peddle::MOS_6510); reset(); reg.sp = 0xff; }
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
        return ram[a];
    }
protected:
    void writePort(uint8_t v) override {
        peddle::Peddle::writePort(v); ram[1] = v; written[1] = 1;
    }
    void writePortDir(uint8_t v) override {
        peddle::Peddle::writePortDir(v); ram[0] = v; written[0] = 1;
    }
    // Foundation bus: ordinary RAM and border register only. REU/UCI access is
    // explicitly unsupported until its register contract is implemented.
    peddle::u8 read(peddle::u16 a) override {
        if (a >= 0xdf00 && a <= 0xdf1f) unsupported = true;
        return ram[a];
    }
    void write(peddle::u16 a, peddle::u8 v) override {
        if (a >= 0xdf00 && a <= 0xdf1f) unsupported = true;
        ram[a] = v; written[a] = 1;
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
uint8_t dos64_model_fault(const Dos64Machine *m) { return m->cpu.unsupported; }

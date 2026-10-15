#include "rsql64_peddle.h"

#include "Peddle.h"

#include <algorithm>
#include <cstring>
#include <vector>

static constexpr uint16_t ReuRegisterBase = 0xdf00;
static constexpr uint16_t ReuRegisterLast = 0xdf0a;

class Rsql64PeddleMachine : public peddle::Peddle {
public:
    uint8_t memory[65536];
    std::vector<uint8_t> reu;
    uint8_t reu_regs[11];
    uint8_t reu_status;
    uint64_t instructions;

    explicit Rsql64PeddleMachine(uint32_t reu_size_kib)
        : reu(static_cast<size_t>(reu_size_kib) * 1024u)
    {
        setModel(peddle::MOS_6510);
        clearMemory();
        resetCpu();
    }

    void clearMemory()
    {
        std::memset(memory, 0, sizeof(memory));
        std::fill(reu.begin(), reu.end(), 0);
        resetReuRegisters();
    }

    void resetReuRegisters()
    {
        std::memset(reu_regs, 0, sizeof(reu_regs));
        reu_status = 0x10;
        reu_regs[0] = reu_status;
        reu_regs[1] = 0x10;
        reu_regs[6] = 0xf8;
        reu_regs[7] = 0xff;
        reu_regs[8] = 0xff;
        reu_regs[9] = 0x1f;
        reu_regs[10] = 0x3f;
    }

    void resetCpu()
    {
        reset();
        reg.sp = 0xff;
        instructions = 0;
        resetReuRegisters();
    }

    void setPc(uint16_t pc)
    {
        reg.pc = pc;
        reg.pc0 = pc;
        next = peddle::fetch;
    }

    void stepInstruction()
    {
        executeInstruction();
        instructions += 1;
    }

    uint8_t readMemory(uint16_t address) const
    {
        if (address >= ReuRegisterBase && address <= ReuRegisterLast) {
            return reu_regs[address - ReuRegisterBase];
        }
        return memory[address];
    }

    void writeMemory(uint16_t address, uint8_t value)
    {
        if (address >= ReuRegisterBase && address <= ReuRegisterLast) {
            writeReuRegister(address, value);
        } else {
            memory[address] = value;
        }
    }

protected:
    peddle::u8 read(peddle::u16 address) override
    {
        if (address >= ReuRegisterBase && address <= ReuRegisterLast) {
            return readReuRegister(address);
        }
        return memory[address];
    }

    void write(peddle::u16 address, peddle::u8 value) override
    {
        writeMemory(address, value);
    }

    peddle::u8 readDasm(peddle::u16 address) const override
    {
        return readMemory(address);
    }

private:
    uint8_t readReuRegister(uint16_t address)
    {
        const auto index = static_cast<size_t>(address - ReuRegisterBase);
        if (index == 0) {
            const uint8_t value = reu_status;
            reu_status &= static_cast<uint8_t>(~0xe0);
            reu_regs[0] = reu_status;
            return value;
        }
        return reu_regs[index];
    }

    void writeReuRegister(uint16_t address, uint8_t value)
    {
        const auto index = static_cast<size_t>(address - ReuRegisterBase);
        reu_regs[index] = value;
        memory[address] = value;
        if (index == 1 && (value & 0x80) != 0) executeReuCommand(value);
    }

    void executeReuCommand(uint8_t command)
    {
        const uint8_t transfer_type = command & 0x03;
        uint16_t c64_address = static_cast<uint16_t>(reu_regs[2] |
            (static_cast<uint16_t>(reu_regs[3]) << 8));
        uint32_t reu_address = static_cast<uint32_t>(reu_regs[4]) |
            (static_cast<uint32_t>(reu_regs[5]) << 8) |
            (static_cast<uint32_t>(reu_regs[6]) << 16);
        uint32_t length = static_cast<uint32_t>(reu_regs[7]) |
            (static_cast<uint32_t>(reu_regs[8]) << 8);
        if (length == 0) length = 65536;
        const bool fix_c64 = (reu_regs[10] & 0x80) != 0;
        const bool fix_reu = (reu_regs[10] & 0x40) != 0;
        bool verify_fault = false;

        for (uint32_t i = 0; i < length; ++i) {
            const uint16_t caddr = fix_c64 ? c64_address
                                           : static_cast<uint16_t>(c64_address + i);
            const uint32_t raw_raddr = fix_reu ? reu_address : reu_address + i;
            const size_t raddr = reu.empty() ? 0u
                                             : static_cast<size_t>(raw_raddr % reu.size());
            switch (transfer_type) {
                case 0:
                    reu[raddr] = memory[caddr];
                    break;
                case 1:
                    memory[caddr] = reu[raddr];
                    break;
                case 2: {
                    const uint8_t temp = memory[caddr];
                    memory[caddr] = reu[raddr];
                    reu[raddr] = temp;
                    break;
                }
                case 3:
                    if (memory[caddr] != reu[raddr]) {
                        verify_fault = true;
                        i = length;
                    }
                    break;
            }
        }
        reu_status = static_cast<uint8_t>(0x50 | (verify_fault ? 0x20 : 0x00));
        reu_regs[0] = reu_status;
    }
};

struct Rsql64Peddle {
    explicit Rsql64Peddle(uint32_t size_kib) : machine(size_kib) {}
    Rsql64PeddleMachine machine;
};

Rsql64Peddle *rsql64_peddle_create(uint32_t reu_size_kib)
{
    if (reu_size_kib < 512u || reu_size_kib > 16384u) return nullptr;
    return new Rsql64Peddle(reu_size_kib);
}

void rsql64_peddle_destroy(Rsql64Peddle *machine) { delete machine; }
void rsql64_peddle_reset(Rsql64Peddle *machine) { machine->machine.resetCpu(); }
void rsql64_peddle_clear_memory(Rsql64Peddle *machine) { machine->machine.clearMemory(); }

void rsql64_peddle_load(Rsql64Peddle *machine, uint16_t address,
                        const uint8_t *bytes, size_t length)
{
    if (length > 65536u - address) length = 65536u - address;
    std::memcpy(&machine->machine.memory[address], bytes, length);
}

uint8_t rsql64_peddle_read(const Rsql64Peddle *machine, uint16_t address)
{
    return machine->machine.readMemory(address);
}

void rsql64_peddle_write(Rsql64Peddle *machine, uint16_t address, uint8_t value)
{
    machine->machine.writeMemory(address, value);
}

uint8_t rsql64_peddle_read_reu(const Rsql64Peddle *machine, uint32_t address)
{
    if (machine->machine.reu.empty()) return 0;
    return machine->machine.reu[address % machine->machine.reu.size()];
}

void rsql64_peddle_write_reu(Rsql64Peddle *machine, uint32_t address, uint8_t value)
{
    if (!machine->machine.reu.empty()) {
        machine->machine.reu[address % machine->machine.reu.size()] = value;
    }
}

size_t rsql64_peddle_load_reu(Rsql64Peddle *machine, uint32_t address,
                              const uint8_t *bytes, size_t length)
{
    if (address >= machine->machine.reu.size()) return 0;
    length = std::min(length, machine->machine.reu.size() - address);
    std::memcpy(&machine->machine.reu[address], bytes, length);
    return length;
}

size_t rsql64_peddle_copy_reu(const Rsql64Peddle *machine, uint32_t address,
                              uint8_t *bytes, size_t length)
{
    if (address >= machine->machine.reu.size()) return 0;
    length = std::min(length, machine->machine.reu.size() - address);
    std::memcpy(bytes, &machine->machine.reu[address], length);
    return length;
}

uint32_t rsql64_peddle_reu_size(const Rsql64Peddle *machine)
{
    return static_cast<uint32_t>(machine->machine.reu.size());
}

void rsql64_peddle_set_pc(Rsql64Peddle *machine, uint16_t pc) { machine->machine.setPc(pc); }
void rsql64_peddle_set_sp(Rsql64Peddle *machine, uint8_t sp) { machine->machine.reg.sp = sp; }
void rsql64_peddle_set_a(Rsql64Peddle *machine, uint8_t value) { machine->machine.reg.a = value; }
void rsql64_peddle_set_x(Rsql64Peddle *machine, uint8_t value) { machine->machine.reg.x = value; }
void rsql64_peddle_set_y(Rsql64Peddle *machine, uint8_t value) { machine->machine.reg.y = value; }
void rsql64_peddle_set_p(Rsql64Peddle *machine, uint8_t value) { machine->machine.setP(value); }
void rsql64_peddle_step_instruction(Rsql64Peddle *machine) { machine->machine.stepInstruction(); }

Rsql64PeddleRegs rsql64_peddle_regs(const Rsql64Peddle *machine)
{
    Rsql64PeddleRegs out = {};
    out.pc = machine->machine.reg.pc;
    out.pc0 = machine->machine.reg.pc0;
    out.sp = machine->machine.reg.sp;
    out.a = machine->machine.reg.a;
    out.x = machine->machine.reg.x;
    out.y = machine->machine.reg.y;
    out.p = machine->machine.getP();
    out.cycles = machine->machine.clock;
    out.instructions = machine->machine.instructions;
    return out;
}

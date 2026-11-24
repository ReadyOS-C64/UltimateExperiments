// Functional diagnostic for the native command state machine. No disk,
// turbo or hardware timing claims. The CPU executing it is Peddle.
#include "Peddle.h"
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace {
class Fixture final : public peddle::Peddle {
public:
    std::array<uint8_t, 65536> ram{};
    unsigned mode = 0;
    unsigned model_bytes = 0;
    unsigned slot = 0;
    unsigned transactions = 0;
    bool opened = false;
    bool loaded = false;
    bool closed = false;
    bool protocol_error = false;

    Fixture() {
        setModel(peddle::MOS_6510);
        reset();
    }

    bool call(uint16_t pc, unsigned limit) {
        reg.pc = reg.pc0 = pc;
        reg.sp = 0xfd;
        ram[0x1fe] = 0xff;
        ram[0x1ff] = 0x01;
        next = peddle::fetch;
        setP(0x24);
        while (reg.pc != 0x0200 && limit-- != 0) {
            do {
                execute();
                ++clock;
            } while (next != peddle::fetch);
        }
        if (reg.pc != 0x0200) protocol_error = true;
        return getP() & 1;
    }

private:
    enum Phase {idle, pushing, busy, data, accepted};
    Phase phase = idle;
    unsigned polls = 0;
    bool more = false;
    bool pending_more = false;
    std::vector<uint8_t> command;
    std::vector<uint8_t> reply;
    std::string response_status;
    unsigned used_data = 0;
    unsigned used_status = 0;

    void respond() {
        reply.clear();
        response_status = "00,OK";
        used_data = used_status = 0;
        const auto op = command.size() >= 2 ? command[1] : 0;
        ++transactions;
        if (command.empty() || command[0] != 2) {
            protocol_error = true;
        } else if (op == 2) {
            const std::string path(command.begin() + 3, command.end());
            if (command[2] != 1 || !path.starts_with("/USB1/TINY64-") ||
                    !path.ends_with(slot ? "/C64PROGINFO.BIN" : "/MODEL.BIN")) protocol_error = true;
            opened = true;
        } else if (op == 7 && opened) {
            unsigned actual = mode == 1 ? model_bytes - 1 : model_bytes;
            for (unsigned i = 0; i < 4; ++i) reply.push_back(actual >> (i * 8));
            reply.push_back(0x42);
            more = true;  // force a second asynchronous block on file-info
        } else if (op == 0x21 && opened && command.size() == 10) {
            for (unsigned i = 0; i < 4; ++i) {
                if (command[i + 2] != (slot && i == 2 ? 0x10 : 0) ||
                    command[i + 6] != uint8_t(model_bytes >> (i * 8))) protocol_error = true;
            }
            loaded = true;
            if (mode == 2) response_status = "02,REQUEST TRUNCATED";
        } else if (op == 3 && opened && command.size() == 2) {
            closed = true;
            opened = false;
        } else {
            protocol_error = true;
        }
        phase = data;
        command.clear();
    }

    uint8_t state() {
        if (phase == pushing && polls++ >= 5) {
            phase = busy;
            polls = 0;
        }
        if (phase == busy && polls++ >= 5) respond();
        if (phase == accepted && polls++ >= 4) {
            if (!pending_more) {
                phase = idle;
            } else {
                // Return final data directly to test accepted-bit handling.
                more = false;
                pending_more = false;
                reply = {7, 9};
                used_data = used_status = 0;
                response_status = "00,OK";
                phase = data;
            }
        }
        switch (phase) {
        case idle: return 0;
        case pushing: return 1;
        case busy: return 0x10;
        case accepted: return (pending_more ? 0x30 : 0x20) | 2;
        case data:
            return (more ? 0x30 : 0x20)
                | (used_data < reply.size() ? 0x80 : 0)
                | (!more && used_status < response_status.size() ? 0x40 : 0);
        }
        return 0;
    }

    uint8_t read(uint16_t address) override {
        if (address >= 0xdd04 && address <= 0xdd07) {
            uint32_t sample = ~(0x2200u + uint32_t(clock / (mode == 3 ? 48 : 64)));
            return sample >> (8 * (address - 0xdd04));
        }
        switch (address) {
        case 0xdf1c: return state();
        case 0xdf1d: return 0xc9;
        case 0xdf1e: return used_data < reply.size() ? reply[used_data++] : 0;
        case 0xdf1f: return used_status < response_status.size() ? response_status[used_status++] : 0;
        default: return ram[address];
        }
    }

    void write(uint16_t address, uint8_t value) override {
        switch (address) {
        case 0xdf1d:
            if (phase != idle) protocol_error = true;
            command.push_back(value);
            break;
        case 0xdf1c:
            if (value & 4) {
                phase = idle;
                command.clear();
            }
            if (value & 1) {
                if (phase != idle) protocol_error = true;
                polls = 0;
                phase = pushing;
            }
            if (value & 2) {
                if (phase != data || used_data != reply.size() ||
                    (!more && used_status != response_status.size())) protocol_error = true;
                pending_more = more;
                polls = 0;
                phase = accepted;
            }
            break;
        default: ram[address] = value;
        }
    }
};
}

extern "C" int test_uci(const uint8_t *image, unsigned bytes, uint16_t start_clock,
                        uint16_t loader, uint16_t dos_stage, uint16_t dos_status,
                        uint16_t requested_model, unsigned slot, unsigned expected,
                        unsigned mode, uint8_t *result) {
    if (bytes > 0x2000) return 1;
    Fixture fixture;
    fixture.mode = mode;
    fixture.slot = slot;
    fixture.model_bytes = expected;
    std::memcpy(fixture.ram.data() + 0xa000, image, bytes);
    if (requested_model) fixture.ram[requested_model] = slot;
    fixture.call(start_clock, 500);
    result[0] = fixture.call(loader, 500000);
    result[1] = fixture.ram[dos_stage];
    result[2] = fixture.ram[dos_status];
    result[3] = fixture.ram[dos_status + 1];
    result[4] = fixture.transactions;
    result[5] = fixture.loaded;
    result[6] = fixture.closed;
    return fixture.protocol_error;
}

extern "C" int test_turbo(const uint8_t *image, unsigned bytes, uint16_t start_clock,
                          uint16_t start_turbo, uint16_t restore_turbo, uint16_t sample,
                          unsigned mode, uint32_t *result) {
    if (bytes > 0x2000) return 1;
    Fixture fixture;
    fixture.mode = mode;
    fixture.ram[0xd031] = mode == 4 ? 0xff : 1;
    std::memcpy(fixture.ram.data() + 0xa000, image, bytes);
    fixture.call(start_clock, 500);
    result[0] = fixture.call(start_turbo, 200000);
    result[1] = fixture.ram[0xd031];
    result[2] = 0;
    for (unsigned i = 0; i < 4; ++i) result[2] |= uint32_t(fixture.ram[sample + i]) << (8 * i);
    fixture.call(restore_turbo, 500);
    result[3] = fixture.ram[0xd031];
    return fixture.protocol_error;
}

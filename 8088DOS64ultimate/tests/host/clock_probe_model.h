#pragma once
#include <stdint.h>
#ifdef __cplusplus
#include "cia_clock_model.h"
// Scripted bus fixture ONLY: each selected D011/D012/D011 sample advances the
// raster and CIA by explicit inputs. It has no connection to Peddle CPU clocks,
// actual turbo speed, VIC DMA, or physical emulation. Hardware/VICE acceptance
// remains separate. modes: 0 advancing, 1 frozen low, 2 frozen high, 3 torn.
struct ClockProbeModel {
    uint16_t lines = 312, raster = 0;
    uint32_t ticks_per_line = 63, repeats = 1, sample_calls = 0;
    uint64_t d011_reads = 0;
    uint8_t mode = 0;
    bool owns(uint16_t a) const { return a == 0xd011 || a == 0xd012; }
    uint8_t read(uint16_t a, CiaClockModel *cia) {
        if(a == 0xd012) return uint8_t(raster);
        const bool first = !(d011_reads++ & 1);
        if(mode == 3) return first ? 0 : 0x80;
        if(first && mode == 0 && ++sample_calls >= repeats) {
            sample_calls = 0;
            raster = uint16_t((raster + 1) % lines);
            if(cia) cia->advance(ticks_per_line);
        }
        if(mode == 1) return 0;
        if(mode == 2) return 0x80;
        return raster & 0x100 ? 0x80 : 0;
    }
};
extern "C" {
#endif
struct Dos64Machine;
void dos64_clock_probe_model_enable(struct Dos64Machine *, uint16_t lines,
                                   uint32_t ticks_per_line, uint32_t repeats,
                                   uint8_t mode);
uint64_t dos64_clock_probe_model_reads(const struct Dos64Machine *);
#ifdef __cplusplus
}
#endif

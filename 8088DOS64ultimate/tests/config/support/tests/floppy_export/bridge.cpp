#include "peddle_bridge.h"
#include "file_model.h"
#include "bulk_model.h"
#include "directory_model.h"
#include "Peddle.h"
#include "reu_model.h"
#include "uci_model.h"
#include "image_import_model.h"
#include "hd_file_model.h"
#include "hd_trace.h"
#include "cia_clock_model.h"
#include "clock_probe_model.h"
#include "host_input_model.h"
#include "native_display_model.h"
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
    bool graphics_color_ram = false;
    std::unique_ptr<ReuModel> reu;
    // Explicitly enabled per fixture; ordinary machines still reject UCI I/O.
    std::unique_ptr<UciModel> uci;
    std::unique_ptr<FloppyExportModel> floppy_export;
    std::unique_ptr<BulkModel> bulk_model;
    uint16_t fw_error_write=0;uint32_t fw_stop_events=0;
    uint16_t fw_crc_start=0,fw_crc_end=0;uint32_t fw_crc_bad=65536;
    std::unique_ptr<DirectoryModel> directory_model;
    // Explicit read-only filesystem source fixture; disabled in ordinary UCI.
    std::unique_ptr<ImageImportModel> image_import;
    std::unique_ptr<HdFileModel> hd_file;
    struct HdRequest {std::array<uint16_t,14> regs;uint16_t ret_ip,ret_cs,ret_flags;uint8_t profile,phase;std::vector<uint8_t> data;};
    std::vector<HdRequest> hd_requests;
    uint16_t hd_trace_pc=0,hd_trace_guest=0,hd_trace_active=0,hd_trace_profile=0;
    uint8_t hd_trace_phase_id=0;bool hd_trace_good=true;
    uint8_t hd_guest_byte(uint32_t physical){
      physical&=0xfffff;const uint16_t page=physical>>9;const uint8_t frame=ram[0xe100+page];
      if(frame==0xff)return reu->bytes[physical];
      if(frame>=32 || !(ram[0xe940+frame]&1) || (uint16_t(ram[0xe900+frame])|(uint16_t(ram[0xe920+frame])<<8))!=page){hd_trace_good=false;return 0;}
      return ram[0x8000+512*frame+(physical&511)];
    }
    void observe_hd(){
      if(!hd_trace_pc||reg.pc!=hd_trace_pc||ram[hd_trace_active]||!reu)return;
      HdRequest q{};for(unsigned i=0;i<14;++i)q.regs[i]=uint16_t(ram[hd_trace_guest+2*i])|(uint16_t(ram[hd_trace_guest+2*i+1])<<8);
      const uint8_t op=q.regs[0]>>8;if(op<2||op>4)return;
      q.profile=ram[hd_trace_profile];q.phase=hd_trace_phase_id;
      auto sw=[&](unsigned delta){const uint16_t off=q.regs[4]+delta;uint32_t a=(uint32_t(q.regs[10])*16+off)&0xfffff;return uint16_t(hd_guest_byte(a))|(uint16_t(hd_guest_byte(a+1))<<8);};
      q.ret_ip=sw(0);q.ret_cs=sw(2);q.ret_flags=sw(4);
      if(op==3){uint32_t begin=(uint32_t(q.regs[8])*16+q.regs[3])&0xfffff;for(unsigned i=0;i<(q.regs[0]&255)*512;++i)q.data.push_back(hd_guest_byte(begin+i));}
      hd_requests.push_back(q);
    }
    // Explicitly enabled per fixture; its PHI2 advances are independent of CPU.
    std::unique_ptr<CiaClockModel> cia_clock;
    bool native_runtime_control=false;
    bool native_runtime_nmi_order=false, native_runtime_nmi_checked=false;
    uint16_t native_runtime_nmi_vector=0;
    // Isolated calibration fixture only; default machines still reject VIC.
    std::unique_ptr<ClockProbeModel> clock_probe;
    std::unique_ptr<HostInputModel> host_input;
    std::unique_ptr<NativeDisplayModel> native_display;
    Machine() {
        setModel(peddle::MOS_6510); reset(); reg.sp = 0xff;
        reg.pport.direction = 0x2f; reg.pport.data = 0x35;
    }
    void setRegs(Dos64Regs r) {
        reg.pc = r.pc; reg.pc0 = r.pc; next = peddle::fetch;
        reg.sp = r.sp; reg.a = r.a; reg.x = r.x; reg.y = r.y; setP(r.p);
    }
    void step() {
        observe_hd();
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
        if(native_runtime_nmi_order && (v&7)==5){
          if((uint16_t(ram[0xfffa])|(uint16_t(ram[0xfffb])<<8))!=native_runtime_nmi_vector || !cia_clock || cia_clock->mask || cia_clock->pending) unsupported=true;
          native_runtime_nmi_order=false;native_runtime_nmi_checked=true;
        }
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
            if (native_runtime_control && (a==0xdc0d || a==0xdc0e || a==0xdc0f)) return io[a-0xd000];
            if (native_runtime_control && (a==0xd019 || a==0xd01a)) return io[a-0xd000];
            if (graphics_color_ram && a>=0xd800 && a<=0xdbff) return io[a-0xd000];
            if (native_display && native_display->owns(a)) return native_display->read(a);
            if (a>=0xdc00 && a<=0xdc0f && host_input) return host_input->read(a-0xdc00);
            if (clock_probe && clock_probe->owns(a)) return clock_probe->read(a, cia_clock.get());
            if (uci && uci->owns(a)) return uci->read(a);
            if (a >= 0xdf00 && a <= 0xdf0a && reu) return reu->read(a-0xdf00);
            if (a >= 0xdd00 && a <= 0xdd0f && cia_clock) return cia_clock->read(a-0xdd00);
            if (a != 0xd020) unsupported = true;
            return io[a-0xd000];
        }
        return ram[a];
    }
    void write(peddle::u16 a, peddle::u8 v) override {
        const auto port = readPort();
        // Test-only later physical key edge, triggered by actual native error
        // publication after the private SI leaf has already been observed.
        if(fw_error_write && a==fw_error_write && v && host_input && !fw_stop_events){host_input->keys[7]|=0x80;++fw_stop_events;}
        if(fw_crc_start && a>=0xc900 && a<0xcd00 && !(reg.pc0>=fw_crc_start && reg.pc0<fw_crc_end) && fw_crc_bad==65536)fw_crc_bad=a;
        written[a] = 1;
        if (a >= 0xd000 && a <= 0xdfff && (port & 3) && (port & 4)) {
            if (native_runtime_control && (a==0xdc0d || a==0xdc0e || a==0xdc0f)) {io[a-0xd000] = (a==0xdc0d ? 0 : v);return;}
            if (native_runtime_control && (a==0xd019 || a==0xd01a)) {if(a==0xd019)io[0x19]&=~v;else io[0x1a]=v;return;}
            if (graphics_color_ram && a>=0xd800 && a<=0xdbff) {io[a-0xd000]=v&15;return;}
            if (native_display && native_display->owns(a)) {native_display->write(a,v);return;}
            if (a>=0xdc00 && a<=0xdc0f && host_input) {host_input->write(a-0xdc00,v);return;}
            if (uci && uci->owns(a)) {
                if(directory_model&&directory_model->owns(*uci,a,v)){
                  if(bulk_model&&(bulk_model->handles[1].open||bulk_model->handles[2].open)){uci->fault=true;return;}
                  if(!directory_model->prepare(*uci))return;
                }else if (bulk_model && !bulk_model->prepare(*uci,reu.get(),a,v)) return;
                if (floppy_export && !floppy_export->prepare(*uci, a, v)) return;
                if (image_import && !image_import->prepare(*uci, a, v)) return;
                if(hd_file){hd_file->owner=hd_requests.empty()?0xffffffff:uint32_t(hd_requests.size()-1);hd_file->phase=hd_trace_phase_id;if(!hd_file->prepare(*uci,a,v))return;}
                uci->write(a, v); return;
            }
            if (a >= 0xdd00 && a <= 0xdd0f && cia_clock) {
                cia_clock->write(a-0xdd00, v); return;
            }
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
Dos64RunResult dos64_run(Dos64Machine *m, uint16_t sentinel, uint64_t cycle_budget) {
    auto &cpu = m->cpu;
    const auto start = static_cast<uint64_t>(cpu.clock);
    Dos64RunResult result{};
    while (true) {
        result.regs = dos64_get_regs(m);
        result.stack_high_water = std::max(result.stack_high_water,
                                          static_cast<uint8_t>(255-cpu.reg.sp));
        // Preserve Fixture.call's failure precedence, including checking model
        // faults at a return address before accepting completion. peek is the
        // existing raw-RAM BRK guard, not an extra modeled bus access.
        if (dos64_model_fault(m)) result.status = DOS64_RUN_MODEL_FAULT;
        else if (cpu.reg.pc == sentinel) {
            result.status = cpu.reg.sp == 0xff ? DOS64_RUN_RETURNED : DOS64_RUN_STACK_IMBALANCE;
        }
        else if (result.regs.cycles-start >= cycle_budget) result.status = DOS64_RUN_CYCLE_BUDGET;
        else if (cpu.peek(cpu.reg.pc) == 0) result.status = DOS64_RUN_UNEXPECTED_BRK;
        else { cpu.step(); continue; }
        return result;
    }
}
void dos64_clear_writes(Dos64Machine *m) { m->cpu.written.fill(0); }
uint8_t dos64_was_written(const Dos64Machine *m, uint16_t a) { return m->cpu.written[a]; }
uint8_t dos64_model_fault(const Dos64Machine *m) {
    return m->cpu.unsupported || (m->cpu.native_display && m->cpu.native_display->fault) || (m->cpu.reu && m->cpu.reu->unsupported) ||
           (m->cpu.uci && m->cpu.uci->fault) ||
           (m->cpu.cia_clock && m->cpu.cia_clock->unsupported) || (m->cpu.host_input && m->cpu.host_input->fault);
}
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
uint8_t dos64_reu_read(const Dos64Machine *m, uint32_t address, uint8_t *out, size_t length) {
    if (!m->cpu.reu || address > m->cpu.reu->bytes.size() || length > m->cpu.reu->bytes.size()-address) return 0;
    std::copy_n(m->cpu.reu->bytes.data()+address, length, out); return 1;
}
uint32_t dos64_reu_compare(const Dos64Machine *m, uint32_t address, const uint8_t *expected, size_t length) {
    if (!m->cpu.reu || address > m->cpu.reu->bytes.size() || length > m->cpu.reu->bytes.size()-address) return 0xfffffffe;
    const auto actual = m->cpu.reu->bytes.data()+address;
    if (std::memcmp(actual,expected,length)==0) return 0xffffffff;
    for (size_t index=0; index<length; ++index) if (actual[index]!=expected[index]) return uint32_t(index);
    return 0xfffffffe;
}

void dos64_uci_model_enable(void *p, uint16_t base, uint32_t delay, uint8_t id) {
    auto &m = static_cast<Dos64Machine *>(p)->cpu;
    m.image_import.reset();
    m.uci = std::make_unique<UciModel>();
    m.uci->base = base; m.uci->delay = delay; m.uci->id = id;
}
void dos64_uci_model_block(void *p, const uint8_t *data, size_t length,
                           const uint8_t *status, size_t status_length) {
    auto &u = *static_cast<Dos64Machine *>(p)->cpu.uci;
    if (length > 896 || status_length > 256) { u.fault = true; return; }
    UciModel::Block b;
    if (length) b.data.assign(data, data + length);
    if (status_length) b.status.assign(status, status + status_length);
    u.blocks.push_back(b);
}
void dos64_uci_model_stuck(void *p, uint8_t stuck) {
    static_cast<Dos64Machine *>(p)->cpu.uci->stuck = stuck;
}
void dos64_uci_model_error(void *p) {
    static_cast<Dos64Machine *>(p)->cpu.uci->error = true;
}
void dos64_uci_model_stale(void *p, uint8_t state) {
    auto &u = *static_cast<Dos64Machine *>(p)->cpu.uci;
    if (state & 0x20) u.publish();
    u.state = state;
}
uint64_t dos64_uci_model_count(void *p, uint8_t counter) {
    const auto &u = *static_cast<Dos64Machine *>(p)->cpu.uci;
    switch (counter) {
        case 0: return u.pushes;
        case 1: return u.accepts;
        case 2: return u.aborts;
        case 3: return u.clears;
        case 4: return u.data_reads;
        case 5: return u.stat_reads;
        case 6: return u.command.size();
        default: return 0;
    }
}
uint8_t dos64_uci_model_command(void *p, uint16_t position) {
    return static_cast<Dos64Machine *>(p)->cpu.uci->command.at(position);
}

void dos64_cia_clock_enable(Dos64Machine *m) {
    m->cpu.cia_clock = std::make_unique<CiaClockModel>();
}
void dos64_cia_clock_seed(Dos64Machine *m, uint16_t a, uint16_t b) {
    auto &c = *m->cpu.cia_clock;
    c.count = {a, b}; c.startup = {0, 0}; c.cascade_pending = false;
}
void dos64_cia_clock_advance(Dos64Machine *m, uint32_t ticks) {
    m->cpu.cia_clock->advance(ticks);
}
void dos64_cia_clock_step(Dos64Machine *m, uint32_t per_read) {
    m->cpu.cia_clock->read_step = per_read;
}
void dos64_cia_clock_script(Dos64Machine *m, const uint32_t *p, size_t n) {
    auto &c = *m->cpu.cia_clock;
    c.script.assign(p, p + n); c.script_index = 0;
}
uint32_t dos64_cia_clock_low_snapshot(const Dos64Machine *m) {
    return m->cpu.cia_clock->last_low_snapshot;
}
uint32_t dos64_cia_clock_reads(const Dos64Machine *m, uint8_t reg) {
    return m->cpu.cia_clock->reads[reg];
}
uint32_t dos64_cia_clock_writes(const Dos64Machine *m, uint8_t reg) {
    return m->cpu.cia_clock->writes[reg];
}
uint16_t dos64_cia_clock_count(const Dos64Machine *m, uint8_t timer) {
    return m->cpu.cia_clock->count[timer];
}
uint16_t dos64_cia_clock_latch(const Dos64Machine *m, uint8_t timer) {
    return m->cpu.cia_clock->latch[timer];
}
void dos64_cia_clock_icr_seed(Dos64Machine *m, uint8_t mask, uint8_t pending) {
    auto &c = *m->cpu.cia_clock;
    c.mask = mask; c.pending = pending;
}
uint8_t dos64_cia_clock_mask(const Dos64Machine *m) {
    return m->cpu.cia_clock->mask;
}
uint8_t dos64_cia_clock_pending(const Dos64Machine *m) {
    return m->cpu.cia_clock->pending;
}

void dos64_clock_probe_model_enable(Dos64Machine *m, uint16_t lines,
                                    uint32_t ticks, uint32_t repeats, uint8_t mode) {
    // Invalid fixture scripts fail explicitly rather than divide by zero or
    // impose an unbounded host-side tick loop. No ordinary fixture enables it.
    if (!lines || lines > 512 || ticks > 65536 || !repeats || repeats > 65535 || mode > 3) {
        m->cpu.unsupported = true; return;
    }
    m->cpu.clock_probe = std::make_unique<ClockProbeModel>();
    auto &p = *m->cpu.clock_probe;
    p.lines = lines; p.ticks_per_line = ticks; p.repeats = repeats; p.mode = mode;
}
uint64_t dos64_clock_probe_model_reads(const Dos64Machine *m) {
    return m->cpu.clock_probe ? m->cpu.clock_probe->d011_reads : 0;
}

// Import source fixture is enabled separately from the FPGA protocol model.
extern "C" {
void import_model_source(void *p,const uint8_t *s,size_t n) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 if (!m.uci || (!s && n) || n>368641) {m.unsupported=true;return;}
 m.image_import=std::make_unique<ImageImportModel>();
 auto &source=*m.image_import;
 if(n) source.source.assign(s,s+n);
 source.path={'d','i','s','k','.','i','m','g'};
}
void import_model_faults(void *p,int command,int corrupt,int short_offset,int close) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 if(!m.image_import) {m.unsupported=true;return;}
 auto &source=*m.image_import;
 source.fail_command=command;source.corrupt_at=corrupt;
 source.short_at=short_offset;source.bad_close=close;
}
uint32_t import_model_commands(void *p) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 return m.image_import ? m.image_import->history.size() : 0;
}
uint32_t import_model_position(void *p) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 return m.image_import ? m.image_import->position : 0;
}
uint8_t import_model_open(void *p) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 return m.image_import ? m.image_import->opened : 0;
}
}

void dos64_host_input_model_enable(Dos64Machine *m) {m->cpu.host_input=std::make_unique<HostInputModel>();}
void dos64_host_input_model_keys(Dos64Machine *m,const uint8_t *p) {std::copy_n(p,8,m->cpu.host_input->keys.data());}
void dos64_host_input_model_seed(Dos64Machine *m,const uint8_t *p) {std::copy_n(p,4,m->cpu.host_input->regs.data());}
uint8_t dos64_host_input_model_reg(Dos64Machine *m,uint8_t r) {return m->cpu.host_input->regs[r];}
uint32_t dos64_host_input_model_reads(Dos64Machine *m,uint8_t r) {return m->cpu.host_input->reads[r];}
uint32_t dos64_host_input_model_writes(Dos64Machine *m,uint8_t r) {return m->cpu.host_input->writes[r];}

void dos64_native_display_enable(Dos64Machine *m){m->cpu.native_display=std::make_unique<NativeDisplayModel>();}
void dos64_native_display_seed(Dos64Machine *m,const uint8_t *p){std::copy_n(p,8,m->cpu.native_display->regs.data());m->cpu.native_display->reads.fill(0);m->cpu.native_display->writes.fill(0);}
uint8_t dos64_native_display_reg(Dos64Machine *m,uint8_t r){return r<8?m->cpu.native_display->regs[r]:0;}
uint32_t dos64_native_display_reads(Dos64Machine *m,uint8_t r){return r<8?m->cpu.native_display->reads[r]:0;}
uint32_t dos64_native_display_writes(Dos64Machine *m,uint8_t r){return r<8?m->cpu.native_display->writes[r]:0;}

extern "C" void native_runtime_control_enable(Dos64Machine *m){m->cpu.native_runtime_control=true;}

extern "C" void native_runtime_require_nmi_order(Dos64Machine *m,uint16_t vector){m->cpu.native_runtime_nmi_order=true;m->cpu.native_runtime_nmi_vector=vector;}
extern "C" uint8_t native_runtime_nmi_checked(Dos64Machine *m){return m->cpu.native_runtime_nmi_checked;}

extern "C" void dos64_graphics_color_enable(Dos64Machine *m){m->cpu.graphics_color_ram=true;}
extern "C" uint8_t dos64_graphics_color_peek(Dos64Machine *m,uint16_t a){return m->cpu.io[a-0xd000];}

extern "C" {
void hd_model_source(void *p,const uint8_t *s,size_t n){auto &m=static_cast<Dos64Machine*>(p)->cpu;if(!m.uci||n>20971521){m.unsupported=true;return;}m.image_import.reset();m.hd_file=std::make_unique<HdFileModel>();m.hd_file->source.assign(s,s+n);}
void hd_model_faults(void *p,int command,int short_offset,int partial_write){auto &m=static_cast<Dos64Machine*>(p)->cpu;if(!m.hd_file){m.unsupported=true;return;}m.hd_file->fail_command=command;m.hd_file->short_offset=short_offset;m.hd_file->partial_write=partial_write;}
uint32_t hd_model_commands(void *p){auto &m=static_cast<Dos64Machine*>(p)->cpu;return m.hd_file?m.hd_file->history.size():0;}
uint8_t hd_model_byte(void *p,uint32_t a){auto &m=static_cast<Dos64Machine*>(p)->cpu;return m.hd_file&&a<m.hd_file->source.size()?m.hd_file->source[a]:0;}
uint32_t hd_model_reads_at(void *p,uint32_t a){auto &m=static_cast<Dos64Machine*>(p)->cpu;uint32_t pos=0,n=0;if(!m.hd_file)return 0;for(auto &c:m.hd_file->history){if(c[1]==6)pos=uint32_t(c[2])|(uint32_t(c[3])<<8)|(uint32_t(c[4])<<16)|(uint32_t(c[5])<<24);if(c[1]==4){if(pos==a)++n;pos+=c[2]+256*c[3];}}return n;}
}

extern "C" {
void hd_model_floppy(void *p,const uint8_t *s,size_t n){auto &m=static_cast<Dos64Machine*>(p)->cpu;if(!m.hd_file||n>368640){m.unsupported=true;return;}m.hd_file->floppy.assign(s,s+n);}
void hd_model_path(void *p,const uint8_t *s,size_t n){auto &m=static_cast<Dos64Machine*>(p)->cpu;if(!m.hd_file||n>127){m.unsupported=true;return;}m.hd_file->hd_path.assign(s,s+n);}
uint8_t hd_model_handle_open(void *p){auto &m=static_cast<Dos64Machine*>(p)->cpu;return m.hd_file&&m.hd_file->opened;}
uint32_t hd_model_count_op(void *p,uint8_t op){auto &m=static_cast<Dos64Machine*>(p)->cpu;uint32_t n=0;if(m.hd_file)for(auto &c:m.hd_file->history)if(c.size()>1&&c[1]==op)++n;return n;}
}

extern "C" {
void hd_trace_enable(void *p,uint16_t pc,uint16_t guest,uint16_t active,uint16_t profile){auto &m=static_cast<Dos64Machine*>(p)->cpu;m.hd_trace_pc=pc;m.hd_trace_guest=guest;m.hd_trace_active=active;m.hd_trace_profile=profile;}
void hd_trace_phase(void *p,uint8_t phase){static_cast<Dos64Machine*>(p)->cpu.hd_trace_phase_id=phase;}
uint8_t hd_trace_valid(void *p){return static_cast<Dos64Machine*>(p)->cpu.hd_trace_good;}
uint32_t hd_trace_requests(void *p){return static_cast<Dos64Machine*>(p)->cpu.hd_requests.size();}
uint32_t hd_trace_field(void *p,uint32_t n,uint8_t field){auto &q=static_cast<Dos64Machine*>(p)->cpu.hd_requests.at(n);if(field<14)return q.regs[field];switch(field){case 14:return q.ret_ip;case 15:return q.ret_cs;case 16:return q.ret_flags;case 17:return q.profile;case 18:return q.phase;case 19:return q.data.size();}return 0;}
uint8_t hd_trace_data(void *p,uint32_t n,uint32_t off){return static_cast<Dos64Machine*>(p)->cpu.hd_requests.at(n).data.at(off);}
uint32_t hd_trace_writes(void *p){auto &m=static_cast<Dos64Machine*>(p)->cpu;return m.hd_file?m.hd_file->writes.size():0;}
uint32_t hd_trace_write_field(void *p,uint32_t n,uint8_t field){auto &q=static_cast<Dos64Machine*>(p)->cpu.hd_file->writes.at(n);switch(field){case 0:return q.offset;case 1:return q.owner;case 2:return q.phase;case 3:return q.data.size();}return 0;}
uint8_t hd_trace_write_data(void *p,uint32_t n,uint32_t off){return static_cast<Dos64Machine*>(p)->cpu.hd_file->writes.at(n).data.at(off);}
uint8_t hd_model_copy_source(void *p,uint8_t *out,size_t n){auto &m=static_cast<Dos64Machine*>(p)->cpu;if(!m.hd_file||m.hd_file->source.size()!=n)return 0;std::copy_n(m.hd_file->source.data(),n,out);return 1;}
}

void export_model_enable(void *p,int existing) {
 auto &m=static_cast<Dos64Machine*>(p)->cpu;
 m.image_import.reset();m.hd_file.reset();
 m.floppy_export=std::make_unique<FloppyExportModel>();
 m.floppy_export->exists=existing;
 if(existing)m.floppy_export->output.assign(97,0x6b);
}
void export_model_faults(void *p,int command,int partial,int corrupt,int short_at,int extra,int close) {
 auto &m=*static_cast<Dos64Machine*>(p)->cpu.floppy_export;
 m.fail_command=command;m.partial_command=partial;m.corrupt_offset=corrupt;m.short_offset=short_at;m.extra=extra;m.bad_cleanup=close;
}
uint32_t export_model_size(void *p){return static_cast<Dos64Machine*>(p)->cpu.floppy_export->output.size();}
uint8_t export_model_byte(void *p,uint32_t i){return static_cast<Dos64Machine*>(p)->cpu.floppy_export->output.at(i);}
uint32_t export_model_count(void *p,uint8_t op){uint32_t n=0;for(auto &c:static_cast<Dos64Machine*>(p)->cpu.floppy_export->history)if(!op||c[1]==op)++n;return n;}
uint8_t export_model_open(void *p){return static_cast<Dos64Machine*>(p)->cpu.floppy_export->opened;}

void export_model_info(void *p,int64_t size,int fault) {
 auto &m=*static_cast<Dos64Machine*>(p)->cpu.floppy_export;
 m.info_size=size;m.info_fault=fault;
}

void export_model_dma_alias(void *p,int enabled){static_cast<Dos64Machine*>(p)->cpu.floppy_export->aligned_dma_alias=enabled;}
uint32_t export_model_alias_hits(void *p){return static_cast<Dos64Machine*>(p)->cpu.floppy_export->alias_hits;}
uint32_t export_model_write_size(void *p,uint32_t index){for(auto &c:static_cast<Dos64Machine*>(p)->cpu.floppy_export->history)if(c[1]==5){if(!index--)return c[2]+256*c[3];}return 0;}

extern "C" {
void bulk_model_enable(void *p){auto &m=static_cast<Dos64Machine*>(p)->cpu;m.floppy_export.reset();m.image_import.reset();m.hd_file.reset();m.bulk_model=std::make_unique<BulkModel>();}
void bulk_model_faults(void*p,int f,int s,int r,int k,int c){auto &m=*static_cast<Dos64Machine*>(p)->cpu.bulk_model;m.fail_at=f;m.short_at=s;m.reply_at=r;m.reply_fault=k;m.corrupt_at=c;}
uint32_t bulk_model_commands(void*p){return static_cast<Dos64Machine*>(p)->cpu.bulk_model->history.size();}
uint8_t bulk_model_command(void*p,uint32_t n,uint32_t i){auto &c=static_cast<Dos64Machine*>(p)->cpu.bulk_model->history.at(n);return i<c.size()?c[i]:0;}
uint32_t bulk_model_size(void*p,const char*n){auto &m=*static_cast<Dos64Machine*>(p)->cpu.bulk_model;auto it=m.files.find(n);return it==m.files.end()?0xffffffff:it->second.size();}
uint8_t bulk_model_open(void*p,uint8_t t){return static_cast<Dos64Machine*>(p)->cpu.bulk_model->handles[t].open;}
uint8_t bulk_model_read(void*p,const char*n,uint8_t*out,uint32_t len){auto &m=*static_cast<Dos64Machine*>(p)->cpu.bulk_model;auto it=m.files.find(n);if(it==m.files.end()||it->second.size()!=len)return 0;std::copy_n(it->second.data(),len,out);return 1;}
void bulk_model_seed(void*p,const char*n,const uint8_t*b,uint32_t len){auto &m=*static_cast<Dos64Machine*>(p)->cpu.bulk_model;m.files[n]=std::vector<uint8_t>(b,b+len);}
void bulk_reu_seed(void*p,uint32_t a,const uint8_t*b,uint32_t len){auto &r=*static_cast<Dos64Machine*>(p)->cpu.reu;if(a>r.bytes.size()||len>r.bytes.size()-a){r.unsupported=true;return;}std::copy_n(b,len,r.bytes.begin()+a);}
}

void dir_model_enable(void*p){static_cast<Dos64Machine*>(p)->cpu.directory_model=std::make_unique<DirectoryModel>();}
void dir_model_path(void*p,const char*name){static_cast<Dos64Machine*>(p)->cpu.directory_model->dirs[name]={};}
void dir_model_row(void*p,const char*path,uint8_t attr,const uint8_t*name,uint32_t length){static_cast<Dos64Machine*>(p)->cpu.directory_model->dirs[path].push_back({attr,std::vector<uint8_t>(name,name+length)});}
void dir_model_fault(void*p,int op,int at,int kind){auto&d=*static_cast<Dos64Machine*>(p)->cpu.directory_model;d.fault_op=op;d.fault_index=at;d.fault_kind=kind;}
uint32_t dir_model_commands(void*p){return static_cast<Dos64Machine*>(p)->cpu.directory_model->history.size();}
uint32_t dir_model_cmd_size(void*p,uint32_t i){return static_cast<Dos64Machine*>(p)->cpu.directory_model->history.at(i).size();}
uint8_t dir_model_cmd_byte(void*p,uint32_t i,uint32_t j){return static_cast<Dos64Machine*>(p)->cpu.directory_model->history.at(i).at(j);}

extern "C" uint32_t browser_bad_write(void*p,const uint8_t*allowed){const auto&m=static_cast<Dos64Machine*>(p)->cpu;for(uint32_t a=0;a<65536;++a)if(m.written[a]&&!allowed[a])return a;return 65536;}

extern "C" uint16_t browser_bank(void*p){auto&m=static_cast<Dos64Machine*>(p)->cpu;return uint16_t(m.reg.pport.direction)|(uint16_t(m.readPort())<<8);}

extern "C" uint16_t setup_soft_stack_min(void*p){auto&m=static_cast<Dos64Machine*>(p)->cpu;for(uint32_t a=0xcd00;a<0xd000;++a)if(m.written[a])return uint16_t(a);return 0xd000;}

extern "C" uint16_t setup_crc_table_write(void*p){auto&m=static_cast<Dos64Machine*>(p)->cpu;for(uint32_t a=0xc900;a<0xcd00;++a)if(m.written[a])return uint16_t(a);return 0xcd00;}

extern "C" void bulk_model_seed_open(void*p,uint8_t t,const char*name,uint8_t mode,uint32_t pos){auto&b=*static_cast<Dos64Machine*>(p)->cpu.bulk_model;if(t<1||t>2||!b.files.contains(name)){static_cast<Dos64Machine*>(p)->cpu.unsupported=true;return;}b.handles[t]={true,mode,pos,name};}

extern "C" void fw_stop_after_error_write(Dos64Machine*m,uint16_t address){m->cpu.fw_error_write=address;}
extern "C" uint32_t fw_stop_event_count(Dos64Machine*m){return m->cpu.fw_stop_events;}

extern "C" void fw_crc_write_guard(Dos64Machine*m,uint16_t start,uint16_t end){m->cpu.fw_crc_start=start;m->cpu.fw_crc_end=end;m->cpu.fw_crc_bad=65536;}
extern "C" uint32_t fw_crc_bad_write(Dos64Machine*m){return m->cpu.fw_crc_bad;}

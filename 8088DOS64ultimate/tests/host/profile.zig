//! Opt-in evidence from the linked 6510 interpreter, never a host CPU substitute.
const std = @import("std");
const host = @import("machine.zig");
const c = host.c;
const Fixture = host.Fixture;
const allocator = std.testing.allocator;
const ram_size = 1024 * 1024;
const seed: u32 = 0x80886510;
const call_budget: u64 = 100_000;
const aggregate_budget: u64 = 150_000_000;
const call_limit = 32_768;
const names = [_][]const u8{ "ax", "cx", "dx", "bx", "sp", "bp", "si", "di", "es", "cs", "ss", "ds", "ip", "flags" };
const initial_regs = [14]u16{ 0, 0, 0, 0, 0x8000, 0, 0, 0, 0x4000, 0, 0x3000, 0x2000, 0x100, 0xf002 };
const Kind = enum { register_loop, dirty_memory, stack_calls, rep_256, rep_20k, multiply_divide };
const Workload = struct {
    name: []const u8,
    kind: Kind,
    code: [64]u8 = @splat(0),
    code_len: usize = 0,
    expected: [14]u16 = initial_regs,
    guest_instructions: u64,
    working_set_bytes: usize,
    guest_bytes_copied: usize = 0,
    fn program(self: *const Workload) []const u8 {
        return self.code[0..self.code_len];
    }
};
const Counters = struct {
    host_cpu_cycles: u64 = 0,
    native_peddle_instructions: u64 = 0,
    dma_operations: u64 = 0,
    dma_bytes: u64 = 0,
    fn snapshot(f: *Fixture) Counters {
        const r = c.dos64_get_regs(f.machine);
        return .{ .host_cpu_cycles = r.cycles, .native_peddle_instructions = r.instructions, .dma_operations = c.dos64_dma_transfers(f.machine), .dma_bytes = c.dos64_dma_bytes(f.machine) };
    }
    fn delta(after: Counters, before: Counters) Counters {
        return .{ .host_cpu_cycles = after.host_cpu_cycles - before.host_cpu_cycles, .native_peddle_instructions = after.native_peddle_instructions - before.native_peddle_instructions, .dma_operations = after.dma_operations - before.dma_operations, .dma_bytes = after.dma_bytes - before.dma_bytes };
    }
    fn add(self: *Counters, other: Counters) void {
        self.host_cpu_cycles += other.host_cpu_cycles;
        self.native_peddle_instructions += other.native_peddle_instructions;
        self.dma_operations += other.dma_operations;
        self.dma_bytes += other.dma_bytes;
    }
};
const Sample = struct {
    workload: []const u8,
    cache_state: []const u8,
    cache_frames: u8,
    working_set_bytes: usize,
    guest_bytes_copied: usize,
    host_cpu_cycles_per_copied_byte: ?f64,
    guest_program_hex: []const u8,
    completed_guest_instructions: u64,
    scheduling_calls: u64,
    counters: Counters,
    host_cpu_cycles_per_guest_instruction: f64,
    native_instructions_per_guest_instruction: f64,
    dma_operations_per_guest_instruction: f64,
    dma_bytes_per_guest_instruction: f64,
    validation_flush_counters: Counters,
    final_registers: [14]u16,
    final_cpu_status: u8,
    full_1mib_ram_matches: bool,
    final_ram_sha256: [64]u8,
};
const Identity = struct { path: []const u8, sha256: [64]u8 };

fn setWord(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address + 1, @truncate(value >> 8));
}
fn digest(bytes: []const u8) [64]u8 {
    var hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(bytes, &hash, .{});
    return std.fmt.bytesToHex(hash, .lower);
}
fn identify(path: []const u8) !Identity {
    const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, allocator, .limited(16 * 1024 * 1024));
    defer allocator.free(bytes);
    return .{ .path = path, .sha256 = digest(bytes) };
}
fn putCode(w: *Workload, code: []const u8) void {
    @memcpy(w.code[0..code.len], code);
    w.code_len = code.len;
    w.expected[12] = 0x100 + @as(u16, @intCast(code.len));
    w.expected[13] = 0xf046; // Final equal CMP fixes all defined arithmetic flags.
}
fn workload(kind: Kind, expected_ram: []const u8) Workload {
    var w = Workload{ .name = @tagName(kind), .kind = kind, .guest_instructions = 0, .working_set_bytes = 512 };
    switch (kind) {
        .register_loop => {
            // ADD wraps once, exercising ADC with CF=1. JNE is both taken
            // and not taken (AX=260 on the first iteration).
            putCode(&w, &.{ 0xb8, 1, 0, 0xbb, 3, 1, 0xb9, 0, 1, 0x01, 0xd8, 0x15, 0, 0, 0x3d, 4, 1, 0x75, 1, 0x90, 0xe2, 0xf3, 0x3d, 2, 3, 0xf4 });
            w.expected[0] = 770;
            w.expected[3] = 259;
            w.guest_instructions = 1286;
        },
        .dirty_memory => {
            // Copy 512 words through ordinary ModR/M loads/stores, dirty pages.
            putCode(&w, &.{ 0xb9, 0, 2, 0xbe, 0, 0, 0xbf, 0, 0x40, 0x8b, 4, 0x89, 5, 0x83, 0xc6, 2, 0x83, 0xc7, 2, 0xe2, 0xf4, 0x3d, 0, 0, 0xf4 });
            const last = std.mem.readInt(u16, expected_ram[0x203fe..][0..2], .little);
            std.mem.writeInt(u16, w.code[22..24], last, .little);
            w.expected[0] = last;
            w.expected[6] = 1024;
            w.expected[7] = 0x4400;
            w.guest_instructions = 2565;
            w.working_set_bytes = 2560;
            w.guest_bytes_copied = 1024;
        },
        .stack_calls => {
            // Repeated guest CALL -> PUSH/ADD/POP/RET, preserving BX/SP.
            putCode(&w, &.{ 0xb9, 0x80, 0, 0xb8, 0, 0, 0xbb, 1, 0, 0xe8, 6, 0, 0xe2, 0xfb, 0x3d, 0x80, 0, 0xf4, 0x53, 0x01, 0xd8, 0x5b, 0xc3 });
            w.expected[0] = 128;
            w.expected[3] = 1;
            w.expected[12] = 0x112;
            w.guest_instructions = 773;
            w.working_set_bytes = 1024;
        },
        .rep_256, .rep_20k => {
            const count: u16 = if (kind == .rep_256) 256 else 20 * 1024;
            putCode(&w, &.{ 0xb9, 0, 0, 0xbe, 0, 0, 0xbf, 0, 0, 0xfc, 0xf3, 0xa4, 0xb8, 0, 0, 0x3d, 0, 0, 0xf4 });
            for ([_]usize{ 1, 13, 16 }) |offset| std.mem.writeInt(u16, w.code[offset..][0..2], count, .little);
            w.expected[0] = count;
            w.expected[6] = count;
            w.expected[7] = count;
            w.guest_instructions = 8;
            w.working_set_bytes = 512 + 2 * @as(usize, count);
            w.guest_bytes_copied = count;
        },
        .multiply_divide => {
            // Repeated unsigned full-word product/division, exact quotient.
            putCode(&w, &.{ 0xb9, 0x80, 0, 0xb8, 0x34, 0x12, 0xbb, 7, 0, 0xf7, 0xe3, 0xf7, 0xf3, 0x05, 1, 0, 0xe2, 0xf7, 0x3d, 0xb4, 0x12, 0xf4 });
            w.expected[0] = 0x12b4;
            w.expected[3] = 7;
            w.guest_instructions = 517;
        },
    }
    return w;
}
fn goldenRam(w: *const Workload, expected: []u8) void {
    switch (w.kind) {
        .dirty_memory => @memcpy(expected[0x24000..0x24400], expected[0x20000..0x20400]),
        .rep_256, .rep_20k => {
            const count: usize = if (w.kind == .rep_256) 256 else 20 * 1024;
            @memcpy(expected[0x40000..][0..count], expected[0x20000..][0..count]);
        },
        .stack_calls => {
            std.mem.writeInt(u16, expected[0x37ffe..][0..2], 0x10c, .little);
            std.mem.writeInt(u16, expected[0x37ffc..][0..2], 1, .little);
        },
        else => {},
    }
}
fn resetGuest(f: *Fixture) !void {
    _ = try f.call("dos64_cpu_init", 10_000);
    const g = try f.symbol("dos64_guest");
    for (initial_regs, 0..) |value, index| setWord(f, g + @as(u16, @intCast(2 * index)), value);
}
fn measure(f: *Fixture, w: *const Workload, phase: []const u8, expected_ram: []const u8) !Sample {
    try resetGuest(f); // Initialization is outside the measured interval.
    const before = Counters.snapshot(f);
    const completed = try f.symbol("dos64_cpu_instructions");
    const status = try f.symbol("dos64_cpu_status");
    var calls: u64 = 0;
    while (f.peek(status) == 0) {
        const now = Counters.snapshot(f);
        if (calls >= call_limit or now.host_cpu_cycles - before.host_cpu_cycles >= aggregate_budget) return error.ProfileAggregateBudget;
        // Fixture.call/bridge retain the monotonic clock. The synthetic caller
        // installs a return address; these costs start at entry, include RTS,
        // and exclude a caller JSR's six CPU cycles.
        const r = f.call("dos64_cpu_step", call_budget) catch |err| {
            std.debug.print("Profile execution failure {s} {s} call={d} cycles={d} ip={x}: {s}\n", .{ w.name, phase, calls, Counters.snapshot(f).host_cpu_cycles - before.host_cpu_cycles, f.word((try f.symbol("dos64_guest")) + 24), @errorName(err) });
            return err;
        };
        calls += 1;
        if ((r.p & 1) != 0) {
            std.debug.print("Profile CPU fault: {s} {s} status={d} ip={x}\n", .{ w.name, phase, f.peek(status), f.word((try f.symbol("dos64_guest")) + 24) });
            return error.ProfileCpuFault;
        }
    }
    const measured = Counters.delta(Counters.snapshot(f), before);
    try std.testing.expectEqual(@as(u8, 1), f.peek(status));
    const completed_count = @as(u64, f.word(completed)) | (@as(u64, f.word(completed + 2)) << 16);
    try std.testing.expectEqual(w.guest_instructions, completed_count);
    const expected_calls = switch (w.kind) {
        .rep_256 => w.guest_instructions - 1 + 256 / 16,
        .rep_20k => w.guest_instructions - 1 + (20 * 1024) / 16,
        else => w.guest_instructions,
    };
    try std.testing.expectEqual(expected_calls, calls);
    try std.testing.expect(measured.host_cpu_cycles <= aggregate_budget);
    var actual: [14]u16 = undefined;
    const g = try f.symbol("dos64_guest");
    for (names, 0..) |name, i| {
        actual[i] = f.word(g + @as(u16, @intCast(2 * i)));
        if (actual[i] != w.expected[i]) {
            std.debug.print("Profile first register divergence {s} {s} {s}: expected={x} actual={x}\n", .{ w.name, phase, name, w.expected[i], actual[i] });
            return error.ProfileRegisterMismatch;
        }
    }
    const before_flush = Counters.snapshot(f);
    const flushed = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), flushed.p & 1);
    const flush_cost = Counters.delta(Counters.snapshot(f), before_flush);
    const difference = c.dos64_reu_compare(f.machine, 0, expected_ram.ptr, expected_ram.len);
    if (difference != 0xffffffff) {
        if (difference >= expected_ram.len) return error.ProfileComparisonBounds;
        std.debug.print("Profile first RAM divergence {s} {s} at {x}: expected={x} actual={x}\n", .{ w.name, phase, difference, expected_ram[difference], c.dos64_reu_peek(f.machine, difference) });
        return error.ProfileRamMismatch;
    }
    const denominator: f64 = @floatFromInt(w.guest_instructions);
    return .{
        .workload = w.name,
        .cache_state = phase,
        .cache_frames = 32,
        .working_set_bytes = w.working_set_bytes,
        .guest_bytes_copied = w.guest_bytes_copied,
        .host_cpu_cycles_per_copied_byte = if (w.guest_bytes_copied == 0) null else @as(f64, @floatFromInt(measured.host_cpu_cycles)) / @as(f64, @floatFromInt(w.guest_bytes_copied)),
        .guest_program_hex = try allocator.dupe(u8, std.fmt.bytesToHex(w.code, .lower)[0 .. w.code_len * 2]),
        .completed_guest_instructions = w.guest_instructions,
        .scheduling_calls = calls,
        .counters = measured,
        .host_cpu_cycles_per_guest_instruction = @as(f64, @floatFromInt(measured.host_cpu_cycles)) / denominator,
        .native_instructions_per_guest_instruction = @as(f64, @floatFromInt(measured.native_peddle_instructions)) / denominator,
        .dma_operations_per_guest_instruction = @as(f64, @floatFromInt(measured.dma_operations)) / denominator,
        .dma_bytes_per_guest_instruction = @as(f64, @floatFromInt(measured.dma_bytes)) / denominator,
        .validation_flush_counters = flush_cost,
        .final_registers = actual,
        .final_cpu_status = f.peek(status),
        .full_1mib_ram_matches = true,
        .final_ram_sha256 = digest(expected_ram),
    };
}

test "profile real linked CPU workloads with exact registers and complete RAM oracles" {
    // Identify runtime, linker inputs and the host measurement/model machinery.
    const paths = [_][]const u8{
        "build/dos64-tests.prg",                      "build/dos64-tests.labels",                   "build.zig",                                  "Makefile",                                        "cfg/dos64.cfg",
        "src/boot.s",                                 "src/cpu_state.s",                            "src/reu.s",                                  "src/address.s",                                   "src/memory.s",
        "src/cpu.s",                                  "src/alu.s",                                  "src/operands.s",                             "src/stack.s",                                     "src/strings.s",
        "src/shifts.s",                               "src/control.s",                              "src/math.s",                                 "src/indirect.s",                                  "src/range.s",
        "src/range_probe.s", "src/range_snapshot.s",                          "src/disk.s",                                 "src/bios.s",                                 "src/reu_probe.s",                                 "src/cache_probe.s",
        "src/reu_snapshot.s",                         "include/abi.inc",                            "include/reu.inc",                            "include/memory.inc",                              "include/parity.inc",
        "include/range.inc",                          "include/disk.inc",                           "include/bios.inc",                           "tests/fixtures/foundation.s",                     "tests/host/profile.zig",
        "tests/host/machine.zig",                     "tests/host/peddle_bridge.h",                 "tests/host/peddle_bridge.cpp",               "tests/host/reu_model.h",                          "third_party/peddle/UPSTREAM.json",
        "third_party/peddle/Peddle/Peddle.h",         "third_party/peddle/Peddle/PeddleConfig.h",   "third_party/peddle/Peddle/PeddleDebugger.h", "third_party/peddle/Peddle/PeddleDebuggerTypes.h", "third_party/peddle/Peddle/PeddleDisassembler.h",
        "third_party/peddle/Peddle/PeddleExec_cpp.h", "third_party/peddle/Peddle/PeddleInit_cpp.h", "third_party/peddle/Peddle/PeddleMacros.h",   "third_party/peddle/Peddle/PeddleMemory_cpp.h",    "third_party/peddle/Peddle/PeddleTypes.h",
        "third_party/peddle/Peddle/PeddleUtils.h",    "third_party/peddle/Peddle/StrWriter.h",      "third_party/peddle/Peddle/Peddle.cpp",       "third_party/peddle/Peddle/PeddleDebugger.cpp",    "third_party/peddle/Peddle/PeddleDisassembler.cpp",
        "third_party/peddle/Peddle/StrWriter.cpp",
    };
    var identities: [paths.len]Identity = undefined;
    var combined = std.crypto.hash.sha2.Sha256.init(.{});
    for (paths, 0..) |path, i| {
        identities[i] = try identify(path);
        combined.update(path);
        combined.update(&.{0});
        combined.update(&identities[i].sha256);
        combined.update(&.{0});
    }
    var combined_hash: [32]u8 = undefined;
    combined.final(&combined_hash);
    var samples: [12]Sample = undefined;
    var count: usize = 0;
    defer for (samples[0..count]) |sample| allocator.free(sample.guest_program_hex);
    const expected = try allocator.alloc(u8, ram_size);
    defer allocator.free(expected);
    var totals: Counters = .{};
    var guest_total: u64 = 0;
    var scheduling_total: u64 = 0;
    for (std.enums.values(Kind)) |kind| {
        var f = try Fixture.init();
        defer f.deinit();
        try std.testing.expectEqual(@as(u8, 1), c.dos64_enable_reu_sized(f.machine, 4096));
        f.poke(try f.symbol("dos64_cache_limit"), 32);
        _ = try f.call("dos64_cache_init", 50_000);
        f.poke(try f.symbol("dos64_memory_mode"), 1);
        var rng: u32 = seed;
        for (expected, 0..) |*byte, address| {
            rng ^= rng << 13;
            rng ^= rng >> 17;
            rng ^= rng << 5;
            byte.* = @truncate(rng);
            c.dos64_reu_poke(f.machine, @intCast(address), byte.*);
        }
        const w = workload(kind, expected);
        @memcpy(expected[0x100..][0..w.code_len], w.program());
        for (w.program(), 0..) |byte, offset| c.dos64_reu_poke(f.machine, @intCast(0x100 + offset), byte);
        // The expected RAM is independently constructed from seed/input and
        // workload semantics; no observed output supplies an expected byte.
        goldenRam(&w, expected);
        for ([_][]const u8{ "cold_empty_cache", "warm_after_same_workload_and_validation_flush" }) |phase| {
            samples[count] = try measure(&f, &w, phase, expected);
            totals.add(samples[count].counters);
            guest_total += samples[count].completed_guest_instructions;
            scheduling_total += samples[count].scheduling_calls;
            count += 1;
        }
    }
    const report = .{
        .schema_version = 1,
        .measurement = "Actual linked 6510 CPU entry through RTS; monotonic Peddle counter deltas",
        .exclusions = [_][]const u8{ "Synthetic host caller JSR (6 CPU cycles per scheduling call)", "REU DMA stall/transfer elapsed time", "VIC contention, hardware timers, rendering, UCI/IEC waits", "Guest 8088 cycle timing, XT ratio and physical C64U elapsed time" },
        .source_identity_algorithm = "SHA256 of ordered path + NUL + lowercase file SHA256 + NUL",
        .source_identity_sha256 = std.fmt.bytesToHex(combined_hash, .lower),
        .file_identities = identities,
        .configuration = .{ .host_cpu = "MOS6510 via pinned Peddle", .initial_6510_port_direction = 0x2f, .initial_6510_port_data = 0x35, .host_call_initial_status = 0x24, .dma_model = "Functional synchronous copy; no DMA stall clocks", .guest_cpu = "functional original 8088", .reu_kib = 4096, .guest_ram_bytes = ram_size, .memory_mode = "ALL_RAM", .page_bytes = 512, .cache_frames = 32, .cache_bytes = 16384, .zig_mode = "Debug", .zig_version = @import("builtin").zig_version_string, .bridge_flags = "-std=c++20 -O2 -Wno-unused-parameter -Wno-unused-variable", .ram_seed = seed, .seed_algorithm = "xorshift32: left13,right17,left5; low byte per address", .per_call_cycle_budget = call_budget, .per_sample_aggregate_cycle_budget = aggregate_budget, .per_sample_scheduling_call_limit = call_limit, .rep_iterations_per_scheduling_call_max = 16, .warm_policy = "Reuse same fixture/cache after previous workload and unmeasured coherent validation flush; Guest CPU registers/instruction counter reset outside measurement; monotonic host counters are retained and cache is not cleared. Above-cache workloads remain capacity limited." },
        .register_order = names,
        .initial_guest_registers = initial_regs,
        .samples = samples,
        .totals = .{ .completed_guest_instructions = guest_total, .scheduling_calls = scheduling_total, .counters = totals, .host_cpu_cycles_per_guest_instruction = @as(f64, @floatFromInt(totals.host_cpu_cycles)) / @as(f64, @floatFromInt(guest_total)), .native_instructions_per_guest_instruction = @as(f64, @floatFromInt(totals.native_peddle_instructions)) / @as(f64, @floatFromInt(guest_total)), .dma_operations_per_guest_instruction = @as(f64, @floatFromInt(totals.dma_operations)) / @as(f64, @floatFromInt(guest_total)), .dma_bytes_per_guest_instruction = @as(f64, @floatFromInt(totals.dma_bytes)) / @as(f64, @floatFromInt(guest_total)), .averages_are_instruction_weighted = true },
        .all_final_state_checks_passed = true,
        .physical_timing_calibrated = false,
    };
    const json = try std.json.Stringify.valueAlloc(allocator, report, .{ .whitespace = .indent_2 });
    defer allocator.free(json);
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/cpu-profile.json", .data = json });
    std.debug.print("Verified {d} CPU profile samples; {d} guest instructions; {d} host CPU cycles; build/cpu-profile.json\n", .{ count, guest_total, totals.host_cpu_cycles });
}

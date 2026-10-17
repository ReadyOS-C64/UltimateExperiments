const std = @import("std");
const h = @import("machine.zig");
const F = h.Fixture;
const c = h.c;
var snapshot_max: u64 = 0;
var tick_max: u64 = 0;
var import_poll_max: u64 = 0;
var start_max: u64 = 0;
const im = @cImport({
    @cInclude("image_import_model.h");
    @cInclude("host_input_model.h");
});
fn p(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn diag(f: *F, off: u16) !u8 {
    return f.peek((try f.symbol("dos64_native_diag")) + off);
}
fn put(f: *F, off: u16, v: u8) !void {
    f.poke((try f.symbol("dos64_native_diag")) + off, v);
}
fn call(f: *F, n: []const u8, budget: u64, carry: u8) !void {
    const command = try diag(f, 3);
    const before = c.dos64_get_regs(f.machine).cycles;
    const r = try f.call(n, budget);
    const cycles = r.cycles - before;
    if (std.mem.eql(u8, n, "dos64_native_tick")) {
        if (command == 2) snapshot_max = @max(snapshot_max, cycles) else tick_max = @max(tick_max, cycles);
    }
    if (std.mem.eql(u8, n, "dos64_native_cold_poll")) import_poll_max = @max(import_poll_max, cycles);
    if (std.mem.eql(u8, n, "dos64_native_start")) start_max = @max(start_max, cycles);
    try std.testing.expectEqual(carry, r.p & 1);
}
fn setup() !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    c.dos64_cia_clock_enable(f.machine);
    c.dos64_cia_clock_step(f.machine, 1);
    c.dos64_native_display_enable(f.machine);
    im.dos64_host_input_model_enable(@ptrCast(f.machine));
    c.native_runtime_control_enable(f.machine);
    return f;
}
fn config(f: *F) !void {
    const a = try f.symbol("dos64_native_config");
    f.poke(a + 4, 0xa5);
    f.poke(a + 7, 9);
    for ("disk.img\x00", 0..) |b, i| f.poke(a + 14 + @as(u16, @intCast(i)), b);
}
fn request(f: *F, cmd: u8) !void {
    try put(f, 3, cmd);
    try call(f, "dos64_native_tick", 3000000, 0);
    try std.testing.expectEqual(@as(u8, 0), try diag(f, 3));
    try std.testing.expectEqual(@as(u8, 0xa5), try diag(f, 4));
}
fn guest32(f: *F) !u32 {
    const a = try f.symbol("dos64_cpu_instructions");
    return @as(u32, f.word(a)) | (@as(u32, f.word(a + 2)) << 16);
}
fn ready(f: *F) !void {
    try call(f, "dos64_overlay_init", 10000, 0);
    try p(f, "dos64_overlay_reu_mib", 4);
    try call(f, "dos64_overlay_bootstrap", 300_000, 0);
    try call(f, "dos64_cpu_init", 10000, 0);
    try p(f, "dos64_cache_limit", 32);
    try call(f, "dos64_cache_init", 50000, 0);
    try call(f, "dos64_disk_init", 10000, 0);
    try call(f, "dos64_bios_init", 40000000, 0);
    try p(f, "dos64_host_clock_claim", 0xa5);
    try call(f, "dos64_host_clock_init", 10000, 0);
    c.dos64_cia_clock_seed(f.machine, 0xf000, 0xffff);
    try p(f, "dos64_host_input_claim", 0xa5);
    try call(f, "dos64_overlay_input_init", 50000, 0);
    try call(f,"dos64_elapsed_poll",10000,0);
    try call(f,"dos64_native_timer_init",100000,0);
    try call(f, "dos64_cold_release", 10000, 0);
    try call(f, "dos64_overlay_text_setup", 10000, 0);
    const d = try f.symbol("dos64_native_diag");
    for (0..19) |i| f.poke(d + @as(u16, @intCast(i)), 0);
    try put(f, 0, 4);
}
test "native disabled config rejects before device takeover and reload-only reentry is inert" {
    var f = try setup();
    defer f.deinit();
    try call(&f, "dos64_native_start", 10000, 1);
    try std.testing.expectEqual(@as(u8, 0xe1), try diag(&f, 0));
    try std.testing.expectEqual(@as(u8, 1), try diag(&f, 1));
    try std.testing.expectEqual(@as(u32, 0), c.dos64_cia_clock_writes(f.machine, 13));
    const g = try f.symbol("dos64_guest");
    f.poke(g, 0x6d);
    try config(&f);
    try call(&f, "dos64_native_start", 10000, 1);
    try std.testing.expectEqual(@as(u8, 0x6d), f.peek(g));
    try p(&f, "dos64_cold_open", 0);
    for (0x7000..0x8000) |a| f.poke(@intCast(a), 0);
    try call(&f, "dos64_native_start", 10000, 1);
    try call(&f, "dos64_native_cold_poll", 10000, 1);
    try std.testing.expectEqual(@as(u8, 0x6d), f.peek(g));
}
test "native initial stopped clock fails bounded before overlays cache CPU mutate" {
    var f = try setup();
    defer f.deinit();
    try config(&f);
    c.dos64_cia_clock_step(f.machine, 0);
    const g = try f.symbol("dos64_guest");
    f.poke(g, 0x6d);
    try call(&f, "dos64_native_start", 1000000, 1);
    try std.testing.expectEqual(@as(u8, 3), try diag(&f, 1));
    try std.testing.expectEqual(@as(u8, 4), try diag(&f, 2));
    try std.testing.expectEqual(@as(u8, 0x6d), f.peek(g));
}
test "native runtime bounded actual CPU keys coherent pause read validation and post-display guards" {
    var f = try setup();
    defer f.deinit();
    try ready(&f);
    for (0x7000..0x8000) |a| f.poke(@intCast(a), 0);
    const g = try f.symbol("dos64_guest");
    f.poke(g + 18, 0);
    f.poke(g + 19, 0);
    f.poke(g + 24, 0);
    f.poke(g + 25, 0x10);
    for (0..100) |i| c.dos64_reu_poke(f.machine, 0x1000 + @as(u32, @intCast(i)), 0x90);
    c.dos64_cia_clock_step(f.machine, 0);
    c.dos64_cia_clock_seed(f.machine, 0xf000, 0xffff);
    try call(&f,"dos64_native_timer_resume",100000,0);
    try call(&f, "dos64_native_tick", 200000, 0);
    try std.testing.expectEqual(@as(u32, 16), try guest32(&f));
    try put(&f, 5, 0x61);
    try put(&f, 6, 0x1e);
    try request(&f, 1);
    try std.testing.expectEqual(@as(u32, 32), try guest32(&f));
    try request(&f, 2);
    const count = try guest32(&f);
    try call(&f, "dos64_native_tick", 10000, 0);
    try std.testing.expectEqual(count, try guest32(&f));
    try std.testing.expectEqual(@as(u8, 5), try diag(&f, 0));
    for (0xff00..0x10200) |i| c.dos64_reu_poke(f.machine, @intCast(i), @truncate((i * 37) ^ (i >> 8)));
    for ([_]struct { far: u32, count: u16, ok: bool }{ .{ .far = 0xfffff, .count = 1, .ok = true }, .{ .far = 0xff800, .count = 2048, .ok = true }, .{ .far = 0xfffff, .count = 2, .ok = false }, .{ .far = 0, .count = 0, .ok = false }, .{ .far = 0, .count = 2049, .ok = false }, .{ .far = 0x100000, .count = 1, .ok = false }, .{ .far = 0xffffff, .count = 1, .ok = false }, .{ .far = 0xfffffe, .count = 2, .ok = false }, .{ .far = 0xff80, .count = 512, .ok = false }, .{ .far = 0xff80, .count = 128, .ok = true }, .{ .far = 0x10000, .count = 384, .ok = true } }) |v| {
        try put(&f, 14, @truncate(v.far));
        try put(&f, 15, @truncate(v.far >> 8));
        try put(&f, 16, @truncate(v.far >> 16));
        try put(&f, 17, @truncate(v.count));
        try put(&f, 18, @truncate(v.count >> 8));
        try put(&f, 3, 4);
        try call(&f, "dos64_native_tick", 100000, 0);
        try std.testing.expectEqual(@as(u8, if (v.ok) 0xa5 else 0xe1), try diag(&f, 4));
        if (v.ok) for (0..v.count) |i| try std.testing.expectEqual(c.dos64_reu_peek(f.machine, v.far + @as(u32, @intCast(i))), f.peek(@intCast(0xc100 + i)));
    }
    try request(&f, 3);
    try std.testing.expectEqual(@as(u8, 4), try diag(&f, 0));
    try std.testing.expectEqual(count + 16, try guest32(&f));
    try call(&f, "dos64_native_start", 10000, 1);
    try call(&f, "dos64_native_cold_poll", 10000, 1);
    c.dos64_cia_clock_seed(f.machine, 0xffff, 0xffff);
    try call(&f, "dos64_native_tick", 10000, 0);
    try std.testing.expectEqual(count + 16, try guest32(&f));
    try p(&f, "dos64_host_clock_claim", 0);
    try call(&f, "dos64_native_tick", 10000, 1);
    try std.testing.expectEqual(@as(u8, 3), try diag(&f, 1));
}
test "patched actual native entry imports exact original disk then real BIOS release and bounded guest reset execution" {
    const path = "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img";
    const data = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, std.testing.allocator, .limited(368641));
    defer std.testing.allocator.free(data);
    var f = try setup();
    defer f.deinit();
    try config(&f);
    im.import_model_source(f.machine, data.ptr, data.len);
    c.dos64_cia_clock_icr_seed(f.machine, 0x1f, 0x1f);
    c.native_runtime_require_nmi_order(f.machine, try f.symbol("dos64_native_nmi"));
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, try f.symbol("dos64_native_loop"), 1000000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(@as(u8, 1), c.native_runtime_nmi_checked(f.machine));
    try std.testing.expectEqual(@as(u8, 2), try diag(&f, 0));
    for (0..150000) |_| {
        if (try diag(&f, 0) != 2) break;
        try call(&f, "dos64_native_cold_poll", 40000000, 0);
    }
    try std.testing.expectEqual(@as(u8, 4), try diag(&f, 0));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_cold_open")));
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek(try f.symbol("dos64_bios_ready")));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_disk_loaded")));
    try std.testing.expectEqual(@as(u32, 723), im.import_model_commands(f.machine));
    try std.testing.expectEqual(@as(u8, 0), im.import_model_open(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x100000, data.ptr, data.len));
    c.dos64_cia_clock_step(f.machine, 0);
    c.dos64_cia_clock_seed(f.machine, 0xf000, 0xffff);
    try call(&f,"dos64_native_timer_resume",100000,0);
    try call(&f, "dos64_native_tick", 3000000, 0);
    try std.testing.expectEqual(@as(u32, 16), try guest32(&f));
    try request(&f, 2);
    for (0..512) |i| try std.testing.expectEqual(data[i], c.dos64_reu_peek(f.machine, 0x7c00 + @as(u32, @intCast(i))));
    for (0..data.len) |i| try std.testing.expectEqual(data[i], c.dos64_reu_peek(f.machine, 0x100000 + @as(u32, @intCast(i))));
}
test "native malformed cold config never accesses CIA nor commits startup overlays" {
    const Case = struct { offset: u16, value: u8 };
    for ([_]Case{ .{ .offset = 0, .value = 0 }, .{ .offset = 5, .value = 3 }, .{ .offset = 5, .value = 17 }, .{ .offset = 6, .value = 0 }, .{ .offset = 6, .value = 3 }, .{ .offset = 7, .value = 1 }, .{ .offset = 7, .value = 129 }, .{ .offset = 8, .value = 0 }, .{ .offset = 9, .value = 0xdc }, .{ .offset = 14, .value = 0 }, .{ .offset = 22, .value = 65 } }) |v| {
        var f = try setup();
        defer f.deinit();
        try config(&f);
        f.poke((try f.symbol("dos64_native_config")) + v.offset, v.value);
        try call(&f, "dos64_native_start", 10000, 1);
        try std.testing.expectEqual(@as(u8, 1), try diag(&f, 1));
        try std.testing.expectEqual(@as(u32, 0), c.dos64_cia_clock_writes(f.machine, 13));
        try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    }
}
test "native import short and elapsed deadline fail unpublished without cold release" {
    for ([_]bool{ false, true }) |timeout| {
        var f = try setup();
        defer f.deinit();
        try config(&f);
        const data = [_]u8{0x42} ** 512;
        im.import_model_source(f.machine, &data, data.len);
        try call(&f, "dos64_native_start", 1000000, 0);
        if (timeout) {
            try p(&f, "dos64_import_timeout", 1);

            f.poke((try f.symbol("dos64_import_timeout")) + 1, 0);
        }
        for (0..10000) |i| {
            if (try diag(&f, 0) != 2) break;
            if (timeout) {
                const t: u32 = ((@as(u32, @intCast(i + 2)) * 16) << 12) | 0x100;
                c.dos64_cia_clock_seed(f.machine, @truncate(~t), @truncate(~(t >> 16)));
            }
            _ = try f.call("dos64_native_cold_poll", 100000);
        }
        try std.testing.expectEqual(@as(u8, 0xe1), try diag(&f, 0));
        try std.testing.expectEqual(@as(u8, 4), try diag(&f, 1));
        try std.testing.expectEqual(@as(u8, if (timeout) 7 else 3), try diag(&f, 2));
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_disk_loaded")));
        try std.testing.expectEqual(@as(u8, 0xa5), f.peek(try f.symbol("dos64_cold_open")));
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_native_text_state")));
    }
}
test "second native SYS after bitmap takeover rejects before stack or cache mutation" {
    var f = try setup();
    defer f.deinit();
    try ready(&f);
    for (0x7000..0x8000) |a| f.poke(@intCast(a), 0);
    c.dos64_clear_writes(f.machine);
    // Entry branches directly to its resident idle; stopped by PC without a call.
    const entry = try f.symbol("dos64_native_entry");
    const idle = try f.symbol("dos64_native_idle");
    c.dos64_set_regs(f.machine, .{ .pc = entry, .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, idle, 1000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    for (0..65536) |a| try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, @intCast(a)));
}

test "disabled native entry remains safe KERNAL-visible idle with truthful RAM diagnostic" {
    var f = try setup();
    defer f.deinit();
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, try f.symbol("dos64_native_idle"), 10000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(@as(u8, 7), f.peek(1) & 7);
    try std.testing.expectEqual(@as(u8, 0xe1), try diag(&f, 0));
    try std.testing.expectEqual(@as(u8, 1), try diag(&f, 1));
    try std.testing.expectEqual(@as(u32, 0), c.dos64_cia_clock_writes(f.machine, 13));
    std.debug.print("native-runtime CPU clocks: snapshot25rows={d}/3000000, tick={d}/3000000, coldPollWithBios={d}/40000000, coldStart={d}/1000000\n", .{ snapshot_max, tick_max, import_poll_max, start_max });
}

test "native scheduler normalizes all 256 elapsed blink phases to renderer booleans" {
    var f = try setup();
    defer f.deinit();
    try ready(&f);
    const g = try f.symbol("dos64_guest");
    f.poke(g + 18, 0);
    f.poke(g + 19, 0);
    f.poke(g + 24, 0);
    f.poke(g + 25, 0x10);
    for (0..4096) |i| c.dos64_reu_poke(f.machine, 0x1000 + @as(u32, @intCast(i)), 0x90);
    c.dos64_cia_clock_step(f.machine, 0);
    for (0..256) |phase| {
        // Keep away from the timer reload exclusion while covering every
        // scheduler phase, including both sides of the bit7 transition.
        const raw = (@as(u32, @intCast(phase)) << 12) | 256;
        const counter = ~raw;
        c.dos64_cia_clock_seed(f.machine, @truncate(counter), @truncate(counter >> 16));
        try call(&f,"dos64_native_timer_resume",100000,0);
        const prior: u16 = @as(u16, @intCast(phase)) -% 4;
        try put(&f, 10, @truncate(prior));
        try put(&f, 11, @truncate(prior >> 8));
        try call(&f, "dos64_native_tick", 3_000_000, 0);
        try std.testing.expectEqual(@as(u8, 4), try diag(&f, 0));
        try std.testing.expectEqual(@as(u8, @intCast(phase / 128)), f.peek((try f.symbol("dos64_render_text_request")) + 1));
        try std.testing.expectEqual(@as(u32, @intCast((phase + 1) * 16)), try guest32(&f));
    }
}

// Use the real runtime cold helper, with a return sentinel outside its code.
// The unit image can retire its cold window, so this fixture loads runtime bytes.
fn initialClockCall(f: *F, name: []const u8, carry: u8) !void {
    f.poke(0x1ff, 2);
    f.poke(0x1fe, 0xff);
    c.dos64_clear_writes(f.machine);
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol(name), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, 0x0300, 2_000_000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(carry, r.regs.p & 1);
    try std.testing.expectEqual(@as(u8, 0x82), r.regs.x);
    try std.testing.expectEqual(@as(u8, 0x93), r.regs.y);
    try std.testing.expectEqual(@as(u8, 4), r.regs.p & 0x0c);
    try std.testing.expectEqual(@as(u8, 7), f.peek(0) & 7);
    try std.testing.expectEqual(@as(u8, 5), f.peek(1) & 7);
    if (std.mem.eql(u8, name, "n_fresh_initial_clock")) {
        const low = try f.symbol("dos64_host_clock_claim");
        const high = (try f.symbol("dos64_elapsed_now")) + 2;
        const attempts = try f.symbol("n_attempts");
        for (0..65536) |i| {
            const address: u16 = @intCast(i);
            if (c.dos64_was_written(f.machine, address) == 0) continue;
            try std.testing.expect(address == 0 or address == 1 or address == attempts or
                (address >= 0x100 and address < 0x200) or (address >= low and address < high));
        }
    }
}
fn initialClockFixture() !F {
    var f = try F.initPaths("build/dos64.prg", "build/dos64.labels");
    errdefer f.deinit();
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    c.dos64_cia_clock_enable(f.machine);
    c.native_runtime_control_enable(f.machine);
    c.dos64_cia_clock_step(f.machine, 0);
    try p(&f, "dos64_host_clock_claim", 0xa5);
    try initialClockCall(&f, "dos64_host_clock_init", 0);
    const now = try f.symbol("dos64_elapsed_now");
    f.poke(now, 0xef);
    f.poke(now + 1, 0xbe);
    const ticks = try f.symbol("dos64_host_clock_ticks");
    for ([_]u8{ 0x11, 0x22, 0x33, 0x44 }, 0..) |v, i| f.poke(ticks + @as(u16, @intCast(i)), v);
    return f;
}
fn initialClockUnpublished(f: *F) !void {
    try std.testing.expectEqual(@as(u16, 0xbeef), f.word(try f.symbol("dos64_elapsed_now")));
    const ticks = try f.symbol("dos64_host_clock_ticks");
    for ([_]u8{ 0x11, 0x22, 0x33, 0x44 }, 0..) |v, i| try std.testing.expectEqual(v, f.peek(ticks + @as(u16, @intCast(i))));
}
test "initial FILE clock refresh replaces the stale published epoch" {
    var f = try initialClockFixture();
    defer f.deinit();
    c.dos64_cia_clock_seed(f.machine, 0xefff, 0xfffd);
    try initialClockCall(&f, "n_fresh_initial_clock", 0);
    try std.testing.expectEqual(@as(u16, 33), f.word(try f.symbol("dos64_elapsed_now")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_host_clock_status")));
}
test "initial clock sample refusal stops after exactly 256 attempts without publication" {
    var f = try initialClockFixture();
    defer f.deinit();
    c.dos64_cia_clock_seed(f.machine, 0xffff, 0xffff);
    const before = c.dos64_cia_clock_reads(f.machine, 5);
    try initialClockCall(&f, "n_fresh_initial_clock", 1);
    try std.testing.expectEqual(@as(u32, 256 * 8), c.dos64_cia_clock_reads(f.machine, 5) - before);
    try std.testing.expectEqual(@as(u8, 4), f.peek(try f.symbol("dos64_host_clock_status")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("n_attempts")));
    try initialClockUnpublished(&f);
}
test "initial clock owner refusal touches no CIA registers or published time" {
    var f = try initialClockFixture();
    defer f.deinit();
    try p(&f, "dos64_host_clock_claim", 0);
    var before: [16]u32 = undefined;
    for (&before, 0..) |*v, i| v.* = c.dos64_cia_clock_reads(f.machine, @intCast(i));
    try initialClockCall(&f, "n_fresh_initial_clock", 1);
    for (before, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_cia_clock_reads(f.machine, @intCast(i)));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_host_clock_status")));
    try initialClockUnpublished(&f);
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
var maximum_poll_cycles: u64 = 0;
const model = @cImport({
    @cInclude("host_input_model.h");
});
fn byte(f: *Fixture, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn keys(f: *Fixture, indices: []const u8) void {
    var m = [_]u8{0} ** 8;
    for (indices) |i| {
        m[i / 8] |= @as(u8, 1) << @as(u3, @intCast(i % 8));
    }
    model.dos64_host_input_model_keys(@ptrCast(f.machine), &m);
}
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    model.dos64_host_input_model_enable(@ptrCast(f.machine));
    try bootstrap(&f);
    f.poke(try f.symbol("dos64_cache_limit"), 1);
    _ = try f.call("dos64_cache_init", 50_000);
    c.dos64_reu_poke(f.machine, 0x41a, 0x1e);
    c.dos64_reu_poke(f.machine, 0x41c, 0x1e);
    f.poke(try f.symbol("dos64_host_input_claim"), 0xa5);
    _ = try f.call("dos64_overlay_input_init", 50_000);
    return f;
}
fn poll(f: *Fixture, expected: u8) !void {
    const before = c.dos64_get_regs(f.machine).cycles;
    const port = f.peek(1);
    const ddr = f.peek(0);
    const direct = ddr != 0x2f or (port & 7) != 5;
    if (direct) {
        f.poke(0, 0x2f);
        f.poke(1, 0x35);
        f.poke(try f.symbol("dos64_overlay_requested"), 3);
        _ = try f.call("dos64_overlay_acquire", 50_000);
        f.poke(0, ddr);
        f.poke(1, port);
    }
    const r = try f.call(if (direct) "dos64_host_input_poll" else "dos64_overlay_input_poll", 150_000);
    maximum_poll_cycles = @max(maximum_poll_cycles, r.cycles - before);
    try std.testing.expectEqual(expected, r.p & 1);
    if (direct) {
        try std.testing.expectEqual(@as(u8, 0x71), r.a);
        try std.testing.expectEqual(@as(u8, 0x82), r.x);
        try std.testing.expectEqual(@as(u8, 0x93), r.y);
    }
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    if (direct) {
        f.poke(0, 0x2f);
        f.poke(1, 0x35);
        _ = try f.call("dos64_overlay_release", 10_000);
        f.poke(0, ddr);
        f.poke(1, port);
    }
}
fn write(f: *Fixture, a: u32, v: u8) !void {
    const p = try f.symbol("dos64_address");
    f.poke(p, @truncate(a));
    f.poke(p + 1, @truncate(a >> 8));
    f.poke(p + 2, @truncate(a >> 16));
    f.poke(try f.symbol("dos64_mem_value"), v);
    const r = try f.call("dos64_mem_write", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn read(f: *Fixture, a: u32) !u8 {
    const p = try f.symbol("dos64_address");
    f.poke(p, @truncate(a));
    f.poke(p + 1, @truncate(a >> 8));
    f.poke(p + 2, @truncate(a >> 16));
    const r = try f.call("dos64_mem_read", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}
fn pop(f: *Fixture) !?u16 {
    const g = try f.symbol("dos64_guest");
    f.poke(g + 1, 0);
    const r = try f.call("dos64_keyboard_service", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    if (try byte(f, "dos64_keyboard_waiting") != 0) return null;
    return f.word(g);
}
fn empty(f: *Fixture) !void {
    try std.testing.expectEqual(@as(?u16, null), try pop(f));
}
// Independently specified C64 legends -> XT BIOS words, in hardware matrix
// order. Modifier switches emit no word; all64 positions are exercised.
const plain = [_]u16{
    0x0e08, 0x1c0d, 0x4d00, 0x4100, 0x3b00, 0x3d00, 0x3f00, 0x5000,
    0x0433, 0x1177, 0x1e61, 0x0534, 0x2c7a, 0x1f73, 0x1265, 0,
    0x0635, 0x1372, 0x2064, 0x0736, 0x2e63, 0x2166, 0x1474, 0x2d78,
    0x0837, 0x1579, 0x2267, 0x0938, 0x3062, 0x2368, 0x1675, 0x2f76,
    0x0a39, 0x1769, 0x246a, 0x0b30, 0x326d, 0x256b, 0x186f, 0x316e,
    0x0d2b, 0x1970, 0x266c, 0x0c2d, 0x342e, 0x273a, 0x0340, 0x332c,
    0x2b5c, 0x092a, 0x273b, 0x4700, 0,      0x0d3d, 0x075e, 0x352f,
    0x0231, 0x0f09, 0,      0x0332, 0x3920, 0,      0x1071, 0x011b,
};
const shifted = [_]u16{
    0x5300, 0x1c0d, 0x4b00, 0x4200, 0x3c00, 0x3e00, 0x4000, 0x4800,
    0x0423, 0x1157, 0x1e41, 0x0524, 0x2c5a, 0x1f53, 0x1245, 0,
    0x0625, 0x1352, 0x2044, 0x0726, 0x2e43, 0x2146, 0x1454, 0x2d58,
    0x0827, 0x1559, 0x2247, 0x0928, 0x3042, 0x2348, 0x1655, 0x2f56,
    0x0a29, 0x1749, 0x244a, 0x0b30, 0x324d, 0x254b, 0x184f, 0x314e,
    0x0d2b, 0x1950, 0x264c, 0x0c5f, 0x343e, 0x275b, 0x0360, 0x333c,
    0x2b7c, 0x092a, 0x275d, 0x4f00, 0,      0x0d3d, 0x077e, 0x353f,
    0x0221, 0x0f00, 0,      0x0322, 0x3920, 0,      0x1051, 0x011b,
};
test "native input owns CIA scan only after claim and initialization" {
    var f = try Fixture.init();
    defer f.deinit();
    model.dos64_host_input_model_enable(@ptrCast(f.machine));
    try bootstrap(&f);
    try poll(&f, 1);
    try std.testing.expectEqual(@as(u8, 1), try byte(&f, "dos64_host_input_status"));
    f.poke(try f.symbol("dos64_host_input_claim"), 0xa5);
    try poll(&f, 1);
    try std.testing.expectEqual(@as(u8, 2), try byte(&f, "dos64_host_input_status"));
    for (0..16) |i| {
        try std.testing.expectEqual(@as(u32, 0), model.dos64_host_input_model_reads(@ptrCast(f.machine), @intCast(i)));
        try std.testing.expectEqual(@as(u32, 0), model.dos64_host_input_model_writes(@ptrCast(f.machine), @intCast(i)));
    }
}
test "native input scans all64 physical keys with held edges release and exact XT translations" {
    var f = try init();
    defer f.deinit();
    for (plain, 0..) |word, i| {
        keys(&f, &.{@intCast(i)});
        try poll(&f, 0);
        const actual = try pop(&f);
        try std.testing.expectEqual(if (word == 0) @as(?u16, null) else word, actual);
        try poll(&f, 0);
        try empty(&f);
        keys(&f, &.{});
        try poll(&f, 0);
        try empty(&f);
    }
}
test "native input SHIFT legends cursors delete home and function pairs cover every position" {
    var f = try init();
    defer f.deinit();
    for (shifted, 0..) |word, i| {
        if (i == 15 or i == 52 or i == 58 or i == 61) continue;
        keys(&f, &.{ 15, @intCast(i) });
        try poll(&f, 0);
        try std.testing.expectEqual(@as(?u16, word), try pop(&f));
        try poll(&f, 0);
        try empty(&f);
        keys(&f, &.{});
        try poll(&f, 0);
    }
}
test "native input modifiers update dirty BDA flags and CTRL and Commodore Alt affect accepted words" {
    var f = try init();
    defer f.deinit();
    for (0..16) |m| {
        try write(&f, 0x417, 0xf0);
        var inds: [5]u8 = undefined;
        var n: usize = 1;
        inds[0] = 20;
        for ([_]u8{ 52, 15, 58, 61 }, 0..) |i, b| {
            if ((m & (@as(usize, 1) << @intCast(b))) != 0) {
                inds[n] = i;
                n += 1;
            }
        }
        keys(&f, inds[0..n]);
        try poll(&f, 0);
        try std.testing.expectEqual(@as(u8, @intCast(0xf0 | m)), try read(&f, 0x417));
        const low: u16 = if (m & 8 != 0) 0 else if (m & 4 != 0) 3 else if (m & 3 != 0) 'C' else 'c';
        try std.testing.expectEqual(@as(?u16, 0x2e00 | low), try pop(&f));
        keys(&f, &.{});
        try poll(&f, 0);
        try std.testing.expectEqual(@as(u8, 0xf0), try read(&f, 0x417));
    }
}
test "native input pending full-ring word survives release and modifier changes without duplicates" {
    var f = try init();
    defer f.deinit();
    const key = try f.symbol("dos64_keyboard_key");
    for (0..15) |i| {
        f.poke(key, @intCast(i));
        f.poke(key + 1, 0xaa);
        _ = try f.call("dos64_keyboard_enqueue", 100_000);
    }
    keys(&f, &.{ 15, 10 });
    try poll(&f, 1);
    try std.testing.expectEqual(@as(u8, 1), try byte(&f, "dos64_host_input_pending"));
    try std.testing.expectEqual(@as(u8, 1), try byte(&f, "dos64_keyboard_status"));
    keys(&f, &.{});
    try poll(&f, 1);
    try std.testing.expectEqual(@as(?u16, 0xaa00), try pop(&f));
    try poll(&f, 0);
    for (1..15) |i| try std.testing.expectEqual(@as(?u16, @intCast(0xaa00 + i)), try pop(&f));
    try std.testing.expectEqual(@as(?u16, 0x1e41), try pop(&f));
    try empty(&f);
    try poll(&f, 0);
    try empty(&f);
    keys(&f, &.{10});
    try poll(&f, 0);
    try std.testing.expectEqual(@as(?u16, 0x1e61), try pop(&f));
    try poll(&f, 0);
    try empty(&f);
}
test "native input switch-network ghost rectangle is rejected before BDA or FIFO updates" {
    var f = try init();
    defer f.deinit();
    try write(&f, 0x417, 0xb0);
    keys(&f, &.{ 8, 9, 16 });
    try poll(&f, 1);
    try std.testing.expectEqual(@as(u8, 3), try byte(&f, "dos64_host_input_status"));
    try std.testing.expectEqual(@as(u8, 0xb0), try read(&f, 0x417));
    try empty(&f);
    keys(&f, &.{ 8, 9 });
    try poll(&f, 0);
    try std.testing.expectEqual(@as(?u16, 0x0433), try pop(&f));
    try std.testing.expectEqual(@as(?u16, 0x1177), try pop(&f));
    try empty(&f);
}
test "native input failed coherent load and invalid queue retry without accepting duplicate edges" {
    for ([_]bool{ false, true }) |bad_ring| {
        var f = try init();
        defer f.deinit();
        keys(&f, &.{10});
        if (bad_ring) {
            try write(&f, 0x41a, 0x1f);
        } else {
            c.dos64_reu_fail_after(f.machine, 0, 17);
        }
        try poll(&f, 1);
        try std.testing.expectEqual(@as(u8, if (bad_ring) 5 else 4), try byte(&f, "dos64_host_input_status"));
        if (bad_ring) {
            try std.testing.expectEqual(@as(u8, 1), try byte(&f, "dos64_host_input_pending"));
            try write(&f, 0x41a, 0x1e);
        }
        try poll(&f, 0);
        try std.testing.expectEqual(@as(?u16, 0x1e61), try pop(&f));
        try poll(&f, 0);
        try empty(&f);
    }
}
test "native input restores CIA port outputs DDRs banking and ABI while never touching other CIA registers" {
    var f = try init();
    defer f.deinit();
    for (0..256) |v| {
        const seed = [_]u8{ 0xff, 0xff, @intCast(v), @truncate(v * 53) };
        model.dos64_host_input_model_seed(@ptrCast(f.machine), &seed);
        f.poke(0, @intCast(v));
        f.poke(1, @truncate(v * 37));
        const ddr = f.peek(0);
        const port = f.peek(1);
        f.initial_status = @intCast(v);
        keys(&f, &.{});
        try poll(&f, 0);
        try std.testing.expectEqual(ddr, f.peek(0));
        try std.testing.expectEqual(port & ddr, f.peek(1) & ddr);
        for (seed, 0..) |x, i| try std.testing.expectEqual(x, model.dos64_host_input_model_reg(@ptrCast(f.machine), @intCast(i)));
    }
    for (4..16) |i| {
        try std.testing.expectEqual(@as(u32, 0), model.dos64_host_input_model_reads(@ptrCast(f.machine), @intCast(i)));
        try std.testing.expectEqual(@as(u32, 0), model.dos64_host_input_model_writes(@ptrCast(f.machine), @intCast(i)));
    }
}
test "native input matrix matches every two-switch chord and rejects every three-corner rectangle" {
    var f = try init();
    defer f.deinit();
    const m = try f.symbol("dos64_host_input_matrix");
    for (0..64) |a| for (a + 1..64) |b| {
        keys(&f, &.{ @intCast(a), @intCast(b) });
        try poll(&f, 0);
        for (0..8) |r| {
            var want: u8 = 0;
            if (a / 8 == r) want |= @as(u8, 1) << @as(u3, @intCast(a % 8));
            if (b / 8 == r) want |= @as(u8, 1) << @as(u3, @intCast(b % 8));
            try std.testing.expectEqual(want, f.peek(m + @as(u16, @intCast(r))));
        }
        while (try pop(&f) != null) {}
        keys(&f, &.{});
        try poll(&f, 0);
    };
    for (0..8) |r0| for (r0 + 1..8) |r1| for (0..8) |c0| for (c0 + 1..8) |c1| {
        keys(&f, &.{ @intCast(r0 * 8 + c0), @intCast(r0 * 8 + c1), @intCast(r1 * 8 + c0) });
        try poll(&f, 1);
        try std.testing.expectEqual(@as(u8, 3), try byte(&f, "dos64_host_input_status"));
        try empty(&f);
    };
}
test "native input bounded writes leave overlay code and memory guards unchanged" {
    var f = try init();
    defer f.deinit();
    const lo = try f.symbol("dos64_host_input_state_start");
    const hi = try f.symbol("dos64_host_input_state_end");
    const guards = [_]u16{ 0x1f, 0x80, 0xe9ff, hi, 0x8200, 0xbfff, 0xc000, 0xefff };
    for (guards, 0..) |a, i| f.poke(a, @truncate(0x31 + i));
    var code: [1792]u8 = undefined;
    for (&code, 0..) |*v, i| v.* = f.peek(0xc900 + @as(u16, @intCast(i)));
    keys(&f, &.{10});
    try poll(&f, 0);
    for (guards, 0..) |a, i| try std.testing.expectEqual(@as(u8, @truncate(0x31 + i)), f.peek(a));
    for (code, 0..) |v, i| try std.testing.expectEqual(v, f.peek(0xc900 + @as(u16, @intCast(i))));
    const k_lo = try f.symbol("dos64_keyboard_state_start");
    const k_hi = try f.symbol("dos64_keyboard_state_end");
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        try std.testing.expect(a <= 1 or (a >= 0x20 and a < 0x30) or (a >= 0x100 and a < 0x200) or (a >= 0xe000 and a < 0xe0de) or (a >= 0xe100 and a < 0xe9c0) or (a >= lo and a < hi) or (a >= try f.symbol("dos64_overlay_ready") and a <= try f.symbol("dos64_overlay_reu_mib")) or (a >= k_lo and a < k_hi) or (a >= 0x8000 and a < 0x8200) or (a >= 0xdc00 and a < 0xdc04) or (a >= 0xdf00 and a <= 0xdf0a));
    }
}

test "native input maximal disjoint matrix stars enqueue all14 edges once in matrix order" {
    var f = try init();
    defer f.deinit();
    const indices = [_]u8{ 1, 2, 3, 4, 5, 6, 7, 8, 16, 24, 32, 40, 48, 56 };
    keys(&f, &indices);
    try poll(&f, 0);
    for (indices) |i| try std.testing.expectEqual(@as(?u16, plain[i]), try pop(&f));
    try empty(&f);
    try poll(&f, 0);
    try empty(&f);
    const metrics = try std.fmt.allocPrint(std.testing.allocator, "{{\"maximum_observed_poll_cpu_cycles\":{d},\"dma_stalls_modeled\":false}}\n", .{maximum_poll_cycles});
    defer std.testing.allocator.free(metrics);
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/input-metrics.json", .data = metrics });
}

fn bootstrap(f: *Fixture) !void {
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 100_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"), 4);
    const boot = try f.call("dos64_overlay_bootstrap", 100_000);
    try std.testing.expectEqual(@as(u8, 0), boot.p & 1);
}

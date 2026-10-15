const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn word(f: *Fixture, name: []const u8, v: u16) !void {
    const a = try f.symbol(name);
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 2);
    _ = try f.call("dos64_cache_init", 50_000);
    return f;
}
fn run(f: *Fixture, vector: u8, dx: u16, ax: u16, carry: u8, fatal: u8) !void {
    const g = try f.symbol("dos64_guest");
    for (0..28) |i| f.poke(g + @as(u16, @intCast(i)), @truncate(i * 7 + 3));
    f.poke(g, @truncate(ax));
    f.poke(g + 1, @truncate(ax >> 8));
    f.poke(g + 4, @truncate(dx));
    f.poke(g + 5, @truncate(dx >> 8));
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    f.poke(try f.symbol("dos64_aux_bios_vector"), vector);
    f.poke(try f.symbol("dos64_aux_bios_host_error"), 0xa5);
    const r = try f.call("dos64_aux_bios_service", 100_000);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    try std.testing.expectEqual(fatal, f.peek(try f.symbol("dos64_aux_bios_host_error")));
    for (before, 0..) |v, i| try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
    try std.testing.expectEqual(vector, f.peek(try f.symbol("dos64_aux_bios_vector")));
}
fn base(vector: u8, dx: u16) u32 {
    const offset: u16 = (dx *% 2) +% @as(u16, if (vector == 0x17) 8 else 0);
    return 0x400 + @as(u32, offset);
}
fn fresh(f: *Fixture) !void {
    _ = try f.call("dos64_cache_init", 50_000);
}
fn store(f: *Fixture, at: u32, v: u8) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(at));
    f.poke(a + 1, @truncate(at >> 8));
    f.poke(a + 2, @truncate(at >> 16));
    f.poke(try f.symbol("dos64_mem_value"), v);
    const r = try f.call("dos64_mem_write", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
test "absent original XT serial and printer preserve all registers for every AH before dispatch" {
    var f = try init();
    defer f.deinit();
    for ([_]u8{ 0x14, 0x17 }) |vector| for (0..4) |dx| for (0..256) |ah| {
        try run(&f, vector, @intCast(dx), @as(u16, @intCast(ah << 8)) | 0xa3, 0, 0);
    };
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x400));
}
test "actual DOS startup COM4 initialization is no-op rather than invented timeout" {
    var f = try init();
    defer f.deinit();
    try run(&f, 0x14, 3, 0x00a3, 0, 0);
}
test "native caller status preserved for handled unsupported and host failure paths" {
    for ([_]u8{ 0x20, 0x2e, 0xe8, 0xef }) |p| {
        var f = try init();
        defer f.deinit();
        f.initial_status = p;
        try run(&f, 0x14, 0, 0xffff, 0, 0);
        try run(&f, 0x13, 0, 0x00a3, 1, 0);
        try fresh(&f);
        c.dos64_reu_fail_after(f.machine, 0, 0);
        try run(&f, 0x14, 0, 0x00a3, 1, 1);
    }
}
test "nonzero BDA base explicitly unsupported without changing AX including high byte only" {
    for ([_]u8{ 0x14, 0x17 }) |vector| for ([_]u16{ 0, 1, 2, 3, 0x7fff, 0x8000, 0x8001, 0xffff }) |dx| for (0..2) |byte| {
        var f = try init();
        defer f.deinit();
        c.dos64_reu_poke(f.machine, base(vector, dx) + @as(u32, @intCast(byte)), 0x80);
        try run(&f, vector, dx, 0xffa3, 1, 0);
    };
}
test "original unchecked DX word index wraps and printer table addition also wraps" {
    for ([_]u8{ 0x14, 0x17 }) |vector| {
        var f = try init();
        defer f.deinit();
        // 8000h aliases device0, not a rejected out-of-range device number.
        c.dos64_reu_poke(f.machine, base(vector, 0), 1);
        try run(&f, vector, 0x8000, 0x33a3, 1, 0);
        c.dos64_reu_poke(f.machine, base(vector, 0), 0);
        try fresh(&f);
        try run(&f, vector, 0x8000, 0x33a3, 0, 0);
        // DX=FFFFh gives FFFEh (serial) or0006h (printer) after 16-bit add.
        c.dos64_reu_poke(f.machine, base(vector, 0xffff), 1);
        try fresh(&f);
        try run(&f, vector, 0xffff, 0x33a3, 1, 0);
    }
}
test "BDA base reads see coherent dirty guest updates before REU flush" {
    for ([_]u8{ 0x14, 0x17 }) |vector| {
        var f = try init();
        defer f.deinit();
        try run(&f, vector, 3, 0x00a3, 0, 0);
        try store(&f, base(vector, 3) + 1, 3);
        try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, base(vector, 3) + 1));
        try run(&f, vector, 3, 0x00a3, 1, 0);
        try store(&f, base(vector, 3) + 1, 0);
        try run(&f, vector, 3, 0x00a3, 0, 0);
    }
}
test "cache failure distinguishes fatal unavailable BDA from absent device and can retry" {
    for ([_]u8{ 0x14, 0x17 }) |vector| {
        var f = try init();
        defer f.deinit();
        c.dos64_reu_fail_after(f.machine, 0, 17);
        try run(&f, vector, 0, 0x00a3, 1, 1);
        try run(&f, vector, 0, 0x00a3, 0, 0);
    }
    var f = try init();
    defer f.deinit();
    // For printer180h, timeout5F8h and base708h occupy separate cache pages.
    c.dos64_reu_fail_after(f.machine, 1, 11);
    try run(&f, 0x17, 0x180, 0x02a3, 1, 1);
    try run(&f, 0x17, 0x180, 0x02a3, 0, 0);
}
test "unknown vectors reject before any BDA DMA and clear prior host error" {
    var f = try init();
    defer f.deinit();
    c.dos64_reu_fail_after(f.machine, 0, 0);
    for ([_]u8{ 0, 0x10, 0x13, 0x15, 0x16, 0x18, 0xff }) |vector| try run(&f, vector, 0xffff, 0x00a3, 1, 0);
    // Failure remains armed: an actual supported-vector read now fails.
    try run(&f, 0x14, 0, 0x00a3, 1, 1);
}

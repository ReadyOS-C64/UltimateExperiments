const std = @import("std");
const host = @import("machine.zig");
const c = host.c;
const F = host.Fixture;
fn put(f: *F, name: []const u8, value: u8) !void {
    f.poke(try f.symbol(name), value);
}
fn get(f: *F, name: []const u8) !u8 {
    return f.peek(try f.symbol(name));
}
fn entry(f: *F) !void {
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0x57, .a = 0, .x = 0, .y = 0, .p = 0x28, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, try f.symbol("dos64_idle"), 50_000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(@as(u8, 0xff), r.regs.sp);
    try std.testing.expectEqual(@as(u8, 0), r.regs.p & 8);
    try std.testing.expectEqual(@as(u8, 0x25), f.peek(1) & 0x2f);
}
fn blob() ![]u8 {
    return std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests-overlay-startup.bin", std.testing.allocator, .limited(6145));
}

test "native entry commits both real overlays before publishing ready" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    const bytes = try blob();
    defer std.testing.allocator.free(bytes);
    c.dos64_reu_poke(f.machine, 0x33ffff, 0x83);
    c.dos64_reu_poke(f.machine, 0x341800, 0x29);
    try entry(&f);
    try f.expectStatus(1);
    try std.testing.expectEqual(@as(u8, 0xa5), try get(&f, "dos64_overlay_ready"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_overlay_reu_mib"));
    try std.testing.expectEqual(@as(u8, 5), f.peek(0xd020));
    try std.testing.expectEqual(@as(u64, 3), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, bytes.ptr, bytes.len));
    try std.testing.expectEqual(@as(u8, 0x83), c.dos64_reu_peek(f.machine, 0x33ffff));
    try std.testing.expectEqual(@as(u8, 0x29), c.dos64_reu_peek(f.machine, 0x341800));
    for (bytes, 0..) |v, i| try std.testing.expectEqual(v, f.peek((if (i < 4096) @as(u16, 0x6000) else @as(u16, 0x7000)) + @as(u16, @intCast(i))));
}

test "native entry malformed overlay header reports failure before either REU write" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    const saved = f.peek(0x6805);
    f.poke(0x6805, saved ^ 0xff);
    try entry(&f);
    try f.expectStatus(0xe1);
    try std.testing.expectEqual(@as(u8, 4), f.peek((try f.symbol("dos64_mailbox")) + 4));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_ready"));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u8, 2), f.peek(0xd020));
    f.poke(0x6805, saved);
    try entry(&f);
    try f.expectStatus(1);
}

test "native entry partial bootstrap never claims ready and cold retry repairs exact assets" {
    const bytes = try blob();
    defer std.testing.allocator.free(bytes);
    for (0..3) |skip| for ([_]u32{ 0, 1, 17, 2047, 2048 }) |prefix| {
        var f = try F.init();
        defer f.deinit();
        c.dos64_enable_reu(f.machine);
        c.dos64_reu_fail_after(f.machine, skip, prefix);
        try entry(&f);
        try f.expectStatus(0xe1);
        try std.testing.expectEqual(@as(u8, 5), f.peek((try f.symbol("dos64_mailbox")) + 4));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_ready"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
        try std.testing.expectEqual(@as(u8, 2), f.peek(0xd020));
        for (bytes, 0..) |v, i| try std.testing.expectEqual(v, f.peek((if (i < 4096) @as(u16, 0x6000) else @as(u16, 0x7000)) + @as(u16, @intCast(i))));
        try entry(&f);
        try f.expectStatus(1);
        try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, bytes.ptr, bytes.len));
    };
}

test "loaded FILE direct ABI retains register flag and mapping coverage under overlay lock" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    try put(&f, "dos64_overlay_reu_mib", 4);
    _ = try f.call("dos64_overlay_bootstrap", 10_000);
    try put(&f, "dos64_overlay_requested", 1);
    _ = try f.call("dos64_overlay_acquire", 10_000);
    for ([_]u8{ 0, 7, 0x2f, 0xff }) |ddr| for ([_]u8{ 0x30, 0x35, 0x37 }) |port| {
        f.poke(0, ddr);
        f.poke(1, port);
        f.initial_status = 0xef;
        const r = try f.call("dos64_files_init", 100_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0xce), r.p & 0xce);
        try std.testing.expectEqual(@as(u8, 0x71), r.a);
        try std.testing.expectEqual(@as(u8, 0x82), r.x);
        try std.testing.expectEqual(@as(u8, 0x93), r.y);
        try std.testing.expectEqual(ddr, f.peek(0));
        try std.testing.expectEqual(port & ddr, f.peek(1) & ddr);
    };
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    _ = try f.call("dos64_overlay_release", 10_000);
}

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
fn nativeModel(f: *F) !void {
    c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    c.dos64_cia_clock_enable(f.machine);
    c.dos64_cia_clock_step(f.machine, 1);
    c.native_runtime_control_enable(f.machine);
    const config = try f.symbol("dos64_native_config");
    f.poke(config + 4, 0xa5);
    f.poke(config + 7, 9);
    for ("disk.img\x00", 0..) |v, i| f.poke(config + 14 + @as(u16, @intCast(i)), v);
}
fn entry(f: *F, success: bool) !void {
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0x57, .a = 0, .x = 0, .y = 0, .p = 0x28, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, try f.symbol(if (success) "dos64_native_loop" else "dos64_native_idle"), 1000000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(@as(u8, 0xff), r.regs.sp);
    try std.testing.expectEqual(@as(u8, 0), r.regs.p & 8);
    try std.testing.expectEqual(@as(u8, 5), f.peek(1) & 7);
}
fn diagnostic(f: *F, stage: u8, error_code: u8, detail: u8) !void {
    const d = try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(stage, f.peek(d));
    try std.testing.expectEqual(error_code, f.peek(d + 1));
    try std.testing.expectEqual(detail, f.peek(d + 2));
}
fn blob() ![]u8 {
    return std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests-overlay-startup.bin", std.testing.allocator, .limited(10241));
}

test "configured native entry commits all real overlays before starting read-only import" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    try nativeModel(&f);
    const bytes = try blob();
    defer std.testing.allocator.free(bytes);
    c.dos64_reu_poke(f.machine, 0x33ffff, 0x83);
    c.dos64_reu_poke(f.machine, 0x342800, 0x29);
    try entry(&f, true);
    try diagnostic(&f, 2, 0, 0);
    try std.testing.expectEqual(@as(u8, 0xa5), try get(&f, "dos64_overlay_ready"));
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_overlay_reu_mib"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_disk_loaded"));
    try std.testing.expectEqual(@as(u64, 7), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, bytes.ptr, bytes.len));
    try std.testing.expectEqual(@as(u8, 0x83), c.dos64_reu_peek(f.machine, 0x33ffff));
    try std.testing.expectEqual(@as(u8, 0x29), c.dos64_reu_peek(f.machine, 0x342800));
}

test "configured native malformed overlay header fails before REU writes and SYS cannot reset evidence" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    try nativeModel(&f);
    const saved = f.peek(0x6805);
    f.poke(0x6805, saved ^ 0xff);
    try entry(&f, false);
    try diagnostic(&f, 0xe1, 2, 4);
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_ready"));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    f.poke(0x6805, saved);
    const r = try f.call("dos64_native_start", 10000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try diagnostic(&f, 0xe1, 2, 4);
    // Explicit cold bootstrap repair remains independently legal; this does
    // not restart the high-level owner or pretend an active file is closed.
    _ = try f.call("dos64_overlay_bootstrap", 10000);
    try std.testing.expectEqual(@as(u8, 0xa5), try get(&f, "dos64_overlay_ready"));
}

test "configured native partial bootstrap stays unpublished and explicit cold repair restores exact assets" {
    const bytes = try blob();
    defer std.testing.allocator.free(bytes);
    for (0..5) |skip| for ([_]u32{ 0, 1, 17, 2047, 2048 }) |prefix| {
        var f = try F.init();
        defer f.deinit();
        c.dos64_enable_reu(f.machine);
        try nativeModel(&f);
        c.dos64_reu_fail_after(f.machine, skip, prefix);
        try entry(&f, false);
        try diagnostic(&f, 0xe1, 2, 5);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_ready"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
        _ = try f.call("dos64_overlay_bootstrap", 10000);
        try std.testing.expectEqual(@as(u8, 0xa5), try get(&f, "dos64_overlay_ready"));
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

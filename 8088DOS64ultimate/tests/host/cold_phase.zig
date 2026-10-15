const std = @import("std");
const host = @import("machine.zig");
const c = host.c;
const F = host.Fixture;
const model = @cImport({
    @cInclude("host_input_model.h");
});
fn put(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn byte(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn call(f: *F, n: []const u8, carry: u8, budget: u64) !void {
    const r = try f.call(n, budget);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
}
fn init() !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    try call(&f, "dos64_overlay_init", 0, 50_000);
    try put(&f, "dos64_overlay_reu_mib", 4);
    try call(&f, "dos64_overlay_bootstrap", 0, 50_000);
    return f;
}
test "cold release requires bootstrap BIOS readiness and no live overlay owner" {
    var f = try F.init();
    defer f.deinit();
    try std.testing.expectEqual(@as(u8, 0xa5), try byte(&f, "dos64_cold_open"));
    try call(&f, "dos64_cold_release", 1, 1000);
    try std.testing.expectEqual(@as(u8, 0xa5), try byte(&f, "dos64_cold_open"));
    try put(&f, "dos64_overlay_ready", 0xa5);
    try call(&f, "dos64_cold_release", 1, 1000);
    try put(&f, "dos64_bios_ready", 0xa5);
    try put(&f, "dos64_overlay_busy", 1);
    try call(&f, "dos64_cold_release", 1, 1000);
    try put(&f, "dos64_overlay_busy", 0);
    try put(&f, "dos64_import_state", 1);
    try call(&f, "dos64_cold_release", 1, 1000);
    try put(&f, "dos64_import_state", 0);
    try call(&f, "dos64_cold_release", 0, 1000);
    try std.testing.expectEqual(@as(u8, 0), try byte(&f, "dos64_cold_open"));
}
test "released cold RAM traps cannot be entered by BIOS importer or overlay reinitialization" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_cache_limit", 32);
    try call(&f, "dos64_cache_init", 0, 50_000);
    try call(&f, "dos64_bios_init", 0, 40_000_000);
    try call(&f, "dos64_cold_release", 0, 1000);
    for (0x7000..0x8000) |a| f.poke(@intCast(a), 0); // BRK traps replace every cold code/state/data byte.
    for ([_][]const u8{ "dos64_bios_init", "dos64_import_init", "dos64_import_start", "dos64_import_poll", "dos64_overlay_init" }) |name| {
        try call(&f, name, 1, 1000);
        try std.testing.expectEqual(@as(u8, 0), try byte(&f, "dos64_cold_open"));
        for (0x7000..0x8000) |a| {
            try std.testing.expectEqual(@as(u8, 0), f.peek(@intCast(a)));
            try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, @intCast(a)));
        }
    }
    try std.testing.expectEqual(@as(u8, 2), try byte(&f, "dos64_bios_host_error"));
    try std.testing.expectEqual(@as(u8, 1), try byte(&f, "dos64_cold_error"));
    try call(&f, "dos64_cold_release", 0, 1000);
    try call(&f, "dos64_overlay_bootstrap", 0, 1000);
    try std.testing.expectEqual(@as(u8, 0xa5), try byte(&f, "dos64_overlay_ready"));
    // Resident BIOS gates remain callable after all init code/data is destroyed.
    const g = try f.symbol("dos64_guest");
    f.poke(g, 0);
    f.poke(g + 1, 0);
    f.poke(g + 18, 0);
    f.poke(g + 19, 0xf0);
    f.poke(g + 24, 0x90);
    f.poke(g + 25, 1);
    try call(&f, "dos64_cpu_step", 0, 2_000_000);
    try std.testing.expectEqual(@as(u16, 0x192), f.word(g + 24));
    // A second SYS entry must never reopen the initialized resident guard.
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, try f.symbol("dos64_native_idle"), 50_000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(@as(u8, 0), try byte(&f, "dos64_cold_open"));
}
test "released first four cache frames cannot alter committed INPUT code asset" {
    var f = try init();
    defer f.deinit();
    const allocator = std.testing.allocator;
    const blob = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests-overlay-startup.bin", allocator, .limited(10241));
    defer allocator.free(blob);
    for (0x8000..0x8800) |a| f.poke(@intCast(a), 0xee);
    try put(&f, "dos64_overlay_requested", 3);
    try call(&f, "dos64_overlay_acquire", 0, 50_000);
    for (blob[4096 + 16 .. 4096 + 16 + 882], 0..) |v, i| try std.testing.expectEqual(v, f.peek(0xc900 + @as(u16, @intCast(i))));
    try call(&f, "dos64_overlay_release", 0, 1000);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, blob.ptr, blob.len));
}
test "INPUT locked wrappers survive FILE and TEXT replacements with exact native queue word" {
    var f = try init();
    defer f.deinit();
    model.dos64_host_input_model_enable(@ptrCast(f.machine));
    try put(&f, "dos64_cache_limit", 1);
    try call(&f, "dos64_cache_init", 0, 50_000);
    c.dos64_reu_poke(f.machine, 0x41a, 0x1e);
    c.dos64_reu_poke(f.machine, 0x41c, 0x1e);
    try put(&f, "dos64_host_input_claim", 0xa5);
    try call(&f, "dos64_overlay_input_init", 0, 50_000);
    var keys: [8]u8 = @splat(0);
    keys[1] = 4;
    model.dos64_host_input_model_keys(@ptrCast(f.machine), &keys);
    for ([_]u8{ 1, 2, 1, 2 }) |id| {
        try put(&f, "dos64_overlay_requested", id);
        try call(&f, "dos64_overlay_acquire", 0, 50_000);
        try call(&f, "dos64_overlay_release", 0, 1000);
    }
    try call(&f, "dos64_overlay_input_poll", 0, 150_000);
    try std.testing.expectEqual(@as(u8, 3), try byte(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(@as(u8, 0), try byte(&f, "dos64_overlay_busy"));
    const g = try f.symbol("dos64_guest");
    f.poke(g + 1, 0);
    try call(&f, "dos64_keyboard_service", 0, 100_000);
    try std.testing.expectEqual(@as(u16, 0x1e61), f.word(g));
}

test "BIOS cold initialization cannot consume uncommitted INPUT cache-source bytes" {
    var f = try F.init();
    defer f.deinit();
    var bytes: [2048]u8 = undefined;
    for (&bytes, 0..) |*v, i| v.* = f.peek(0x8000 + @as(u16, @intCast(i)));
    try call(&f, "dos64_bios_init", 1, 1000);
    try std.testing.expectEqual(@as(u8, 3), try byte(&f, "dos64_bios_host_error"));
    for (bytes, 0..) |v, i| try std.testing.expectEqual(v, f.peek(0x8000 + @as(u16, @intCast(i))));
}

const std = @import("std");
const host = @import("machine.zig");
const F = host.Fixture;
var maximum_poll_cycles: u64 = 0;
const c = @cImport({
    @cInclude("image_import_model.h");
    @cInclude("peddle_bridge.h");
});
fn p(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn g(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn w(f: *F, n: []const u8, v: u16) !void {
    const a = try f.symbol(n);
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn crc32(data: []const u8) u32 {
    var v: u32 = 0xffffffff;
    for (data) |b| {
        v ^= b;
        for (0..8) |_| {
            const low = v & 1;
            v >>= 1;
            if (low != 0) v ^= 0xedb88320;
        }
    }
    return ~v;
}
fn call(f: *F, n: []const u8, carry: u8) !void {
    const d = f.peek(0);
    const port = f.peek(1);
    const before = host.c.dos64_get_regs(f.machine).cycles;
    const r = try f.call(n, 100_000);
    if (std.mem.eql(u8, n, "dos64_import_poll")) maximum_poll_cycles = @max(maximum_poll_cycles, r.cycles - before);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    try std.testing.expectEqual(d, f.peek(0));
    try std.testing.expectEqual(port & d, f.peek(1) & d);
}
fn setup(data: []const u8) !F {
    var f = try F.init();
    errdefer f.deinit();
    host.c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    try p(&f, "dos64_overlay_reu_mib", 4);
    _ = try f.call("dos64_overlay_bootstrap", 10_000);
    c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    c.import_model_source(f.machine, data.ptr, data.len);
    _ = try f.call("dos64_uci_init", 10_000);
    _ = try f.call("dos64_overlay_files_init", 10_000);
    try call(&f, "dos64_import_init", 0);
    try w(&f, "dos64_uci_timeout", 500);
    try w(&f, "dos64_uci_recovery_timeout", 100);
    try w(&f, "dos64_import_timeout", 30000);
    try p(&f, "dos64_files_path_len", 9);
    const a = (try f.symbol("dos64_uci_command")) + 3;
    for ("disk.img\x00", 0..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    const crc = crc32(data);
    const dest = try f.symbol("dos64_import_expected_crc");
    for (0..4) |i| f.poke(dest + @as(u16, @intCast(i)), @truncate(crc >> @as(u5, @intCast(8 * i))));
    for (0..4 * 1024 * 1024) |i| host.c.dos64_reu_poke(f.machine, @intCast(i), 0xa5);
    // Install actual packaged assets after filling the independent REU oracle.
    _ = try f.call("dos64_overlay_init", 10_000);
    try p(&f, "dos64_overlay_reu_mib", 4);
    _ = try f.call("dos64_overlay_bootstrap", 10_000);
    for (try f.symbol("dos64_import_code_end")..0x8000) |i| f.poke(@intCast(i), 0xa6);
    return f;
}
fn run(f: *F, start: u16, step: u16) !void {
    var now = start;
    try w(f, "dos64_import_now", now);
    try call(f, "dos64_import_start", 0);
    for (0..150000) |i| {
        if (try g(f, "dos64_import_state") != 1) return;
        if (i % 10 == 0) now +%= step;
        try w(f, "dos64_import_now", now);
        try call(f, "dos64_import_poll", 0);
        if (try g(f, "dos64_import_state") == 1) try std.testing.expectEqual(@as(u8, 0), try g(f, "dos64_disk_loaded"));
    }
    return error.PollBudget;
}
fn seeded() [368640]u8 {
    var d: [368640]u8 = undefined;
    var seed: u32 = 0x808864;
    for (&d) |*b| {
        seed = seed *% 1664525 +% 1013904223;
        b.* = @truncate(seed >> 16);
    }
    return d;
}
fn guards(f: *F) !void {
    const a = std.testing.allocator;
    const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.prg", a, .limited(65538));
    defer a.free(prg);
    const load = std.mem.readInt(u16, prg[0..2], .little);
    for (try f.symbol("dos64_import_code_start")..try f.symbol("dos64_import_state_start")) |i| try std.testing.expectEqual(prg[2 + i - load], f.peek(@intCast(i)));
    for (try f.symbol("dos64_import_code_end")..0x8000) |i| try std.testing.expectEqual(@as(u8, 0xa6), f.peek(@intCast(i)));
    for (0..4096) |i| try std.testing.expectEqual(f.peek(@intCast(0x6000 + i)), host.c.dos64_reu_peek(f.machine, @intCast(0x340000 + i)));
    try std.testing.expectEqual(@as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, 0x0fffff));
    try std.testing.expectEqual(@as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, 0x15a000));
}
fn failed(f: *F, e: u8) !void {
    try guards(f);
    try std.testing.expectEqual(@as(u8, 3), try g(f, "dos64_import_state"));
    try std.testing.expectEqual(e, try g(f, "dos64_import_error"));
    try std.testing.expectEqual(@as(u8, 0), try g(f, "dos64_disk_loaded"));
}
test "import exact whole360K image CRC native wrappers all REU guards and monotonic wrap" {
    const data = seeded();
    var f = try setup(&data);
    defer f.deinit();
    f.initial_status = 0xef;
    try run(&f, 65000, 1);
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_import_state"));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
    try std.testing.expectEqual(@as(u16, 720), f.word(try f.symbol("dos64_import_sectors")));
    try guards(&f);
    try std.testing.expectEqual(@as(u32, 723), c.import_model_commands(f.machine));
    try std.testing.expectEqual(@as(u32, 368640), c.import_model_position(f.machine));
    try std.testing.expectEqual(@as(u8, 0), c.import_model_open(f.machine));
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
    try std.testing.expectEqual(@as(u32, 0xffffffff), host.c.dos64_reu_compare(f.machine, 0x100000, &data, data.len));
    for (0..4 * 1024 * 1024) |i| {
        if (i >= 0x100000 and i < 0x15a000) continue;
        if (i >= 0x340000 and i < 0x341000) {
            try std.testing.expectEqual(f.peek(@intCast(0x6000 + i - 0x340000)), host.c.dos64_reu_peek(f.machine, @intCast(i)));
            continue;
        }
        try std.testing.expectEqual(@as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, @intCast(i)));
    }
}
test "import rejects closed ownership violation busy reentry zero invalid deadline" {
    const data = seeded();
    var f = try setup(&data);
    defer f.deinit();
    try p(&f, "dos64_disk_loaded", 1);
    try p(&f, "dos64_files_handle", 2);
    try call(&f, "dos64_import_start", 1);
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
    try p(&f, "dos64_files_handle", 0);
    for ([_]u16{ 0, 0x8000, 0xffff }) |t| {
        try w(&f, "dos64_import_timeout", t);
        try call(&f, "dos64_import_start", 1);
    }
    try w(&f, "dos64_import_timeout", 30000);
    try call(&f, "dos64_import_start", 0);
    try call(&f, "dos64_import_start", 1);
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_import_state"));
}
test "import short extra stale corruption CRC and failed close never publish" {
    const data = seeded();
    const Case = struct { len: usize = 368640, corrupt: i32 = -1, short: i32 = -1, close: i32 = 0, err: u8 };
    var large: [368641]u8 = undefined;
    @memcpy(large[0..data.len], &data);
    large[data.len] = 0x5a;
    for ([_]Case{ .{ .len = 0, .err = 3 }, .{ .len = 511, .err = 3 }, .{ .len = 368639, .err = 3 }, .{ .len = 368641, .err = 4 }, .{ .corrupt = 0, .err = 5 }, .{ .corrupt = 368639, .err = 5 }, .{ .short = 512, .err = 3 }, .{ .close = 1, .err = 8 } }) |t| {
        var f = try setup(large[0..t.len]);
        defer f.deinit();
        c.import_model_faults(f.machine, -1, t.corrupt, t.short, t.close);
        try run(&f, 0, 1);
        try failed(&f, t.err);
        if (t.close != 0) {
            try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_import_cleanup_error"));
            try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_handle"));
        } else try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
    }
}
test "import read transport status failure and partial REU DMA remain unpublished" {
    const data = seeded();
    {
        var f = try setup(&data);
        defer f.deinit();
        c.import_model_faults(f.machine, 1, -1, -1, 0);
        try run(&f, 0, 1);
        try failed(&f, 2);
        // Firmware no-file CLOSE establishes closed ownership while retaining
        // the failed cleanup status, so import still cannot publish.
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
        try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_import_cleanup_error"));
    }
    {
        var f = try setup(&data);
        defer f.deinit();
        c.import_model_faults(f.machine, 3, -1, -1, 0);
        try run(&f, 0, 1);
        try failed(&f, 2);
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
    }
    for ([_]u32{ 0, 17, 512 }) |prefix| {
        var f = try setup(&data);
        defer f.deinit();
        // First file acquire performs header + payload DMA, then image transfer.
        host.c.dos64_reu_fail_after(f.machine, 2, prefix);
        try run(&f, 0, 1);
        try failed(&f, 6);
        try std.testing.expectEqual(@as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, 0x0fffff));
        try std.testing.expectEqual(@as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, 0x15a000));
        for (0..512) |i| try std.testing.expectEqual(if (i < prefix) data[i] else @as(u8, 0xa5), host.c.dos64_reu_peek(f.machine, @intCast(0x100000 + i)));
    }
}
test "import elapsed deadline at wrap aborts and separately recovers no pollcount time" {
    const data = seeded();
    var f = try setup(&data);
    defer f.deinit();
    try w(&f, "dos64_import_now", 65530);
    try w(&f, "dos64_import_timeout", 10);
    try call(&f, "dos64_import_start", 0);
    for (0..30) |_| try call(&f, "dos64_import_poll", 0);
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_import_error"));
    try w(&f, "dos64_import_now", 4);
    for (0..1000) |i| {
        if (try g(&f, "dos64_import_state") != 1) break;
        try w(&f, "dos64_import_now", @truncate(4 + i / 10));
        try call(&f, "dos64_import_poll", 0);
    }
    try failed(&f, 7);
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
}
test "import supplied untouched DOS33 disk1 independent pinned manifest CRC and SHA" {
    const path = "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img";
    const a = std.testing.allocator;
    const data = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, a, .limited(368641));
    defer a.free(data);
    try std.testing.expectEqual(@as(usize, 368640), data.len);
    var before: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(data, &before, .{});
    const pinned = [_]u8{ 0xbc, 0xa9, 0x89, 0x92, 0xb4, 0x76, 0xdf, 0xee, 0x95, 0x66, 0x7b, 0x1e, 0xdc, 0x9a, 0x71, 0xc2, 0x55, 0x85, 0x8e, 0x58, 0x8c, 0x03, 0xed, 0xec, 0xe0, 0x4a, 0xd7, 0x23, 0x7c, 0xa6, 0xff, 0xdb };
    try std.testing.expectEqualSlices(u8, &pinned, &before);
    var f = try setup(data);
    defer f.deinit();
    // Fixed manifest from independent Python zlib, not target or mock CRC.
    const expected = [_]u8{ 0x37, 0x0a, 0x77, 0x30 };
    const e = try f.symbol("dos64_import_expected_crc");
    for (expected, 0..) |b, i| f.poke(e + @as(u16, @intCast(i)), b);
    try std.testing.expectEqual(@as(u32, 0x30770a37), crc32(data));
    try run(&f, 1234, 1);
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_import_state"));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
    try guards(&f);
    try std.testing.expectEqual(@as(u32, 723), c.import_model_commands(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), host.c.dos64_reu_compare(f.machine, 0x100000, data.ptr, data.len));
    const after = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, a, .limited(368641));
    defer a.free(after);
    var after_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(after, &after_hash, .{});
    try std.testing.expectEqualSlices(u8, &pinned, &after_hash);
    try std.testing.expectEqualSlices(u8, data, after);
}
test "import elapsed transport recovery failure retains unknown handle and unpublished media" {
    const data = seeded();
    var f = try setup(&data);
    defer f.deinit();
    c.dos64_uci_model_stuck(f.machine, 1);
    try w(&f, "dos64_import_now", 65530);
    try w(&f, "dos64_import_timeout", 10);
    try call(&f, "dos64_import_start", 0);
    for (0..20) |_| try call(&f, "dos64_import_poll", 0);
    try w(&f, "dos64_import_now", 4);
    try call(&f, "dos64_import_poll", 0);
    for (0..1000) |i| {
        if (try g(&f, "dos64_import_state") != 1) break;
        try w(&f, "dos64_import_now", @truncate(4 + i));
        try call(&f, "dos64_import_poll", 0);
    }
    try failed(&f, 7);
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_import_cleanup_error"));
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_handle"));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_uci_recovery_failed"));
    try std.testing.expectEqual(@as(u64, 1), c.dos64_uci_model_count(f.machine, 2));
    std.debug.print("image import maximum observed per-poll native cycles={d}; full-image CRC bytes bounded16/call\n", .{maximum_poll_cycles});
}

test "import filesystem model defaults off and ordinary scripted UCI remains strict" {
    {
        var f = try F.init();
        defer f.deinit();
        try std.testing.expectEqual(@as(u32, 0), c.import_model_commands(f.machine));
        _ = host.c.dos64_bus_read(f.machine, 0xdf1c);
        try std.testing.expectEqual(@as(u8, 1), host.c.dos64_model_fault(f.machine));
    }
    {
        var f = try F.init();
        defer f.deinit();
        c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
        c.dos64_uci_model_block(f.machine, "X", 1, "00,OK", 5);
        // Arbitrary command retains caller-scripted response. The optional
        // filesystem source would reject these bytes if accidentally enabled.
        host.c.dos64_bus_write(f.machine, 0xdf1d, 99);
        host.c.dos64_bus_write(f.machine, 0xdf1d, 255);
        host.c.dos64_bus_write(f.machine, 0xdf1c, 1);
        for (0..20) |_| _ = host.c.dos64_bus_read(f.machine, 0xdf1c);
        try std.testing.expectEqual(@as(u8, 'X'), host.c.dos64_bus_read(f.machine, 0xdf1e));
        try std.testing.expectEqual(@as(u32, 0), c.import_model_commands(f.machine));
        try std.testing.expectEqual(@as(u8, 0), host.c.dos64_model_fault(f.machine));
        _ = host.c.dos64_bus_read(f.machine, 0xdd04);
        try std.testing.expectEqual(@as(u8, 1), host.c.dos64_model_fault(f.machine));
    }
}

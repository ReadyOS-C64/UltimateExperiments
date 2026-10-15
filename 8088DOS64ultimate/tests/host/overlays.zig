const std = @import("std");
const host = @import("machine.zig");
const F = host.Fixture;
const c = host.c;
const uci = @cImport({
    @cInclude("uci_model.h");
});
const allocator = std.testing.allocator;

fn put(f: *F, name: []const u8, value: u8) !void {
    f.poke(try f.symbol(name), value);
}
fn get(f: *F, name: []const u8) !u8 {
    return f.peek(try f.symbol(name));
}
fn call(f: *F, name: []const u8, carry: u8) !c.Dos64Regs {
    const port = f.peek(1);
    const ddr = f.peek(0);
    const r = try f.call(name, 2_000_000);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    try std.testing.expectEqual(ddr, f.peek(0));
    try std.testing.expectEqual(port & ddr, f.peek(1) & ddr);
    return r;
}
fn setup(boot: bool) !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    _ = try call(&f, "dos64_overlay_init", 0);
    try put(&f, "dos64_overlay_reu_mib", 4);
    if (boot) _ = try call(&f, "dos64_overlay_bootstrap", 0);
    return f;
}
fn assets() ![]u8 {
    return std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests-overlay-startup.bin", allocator, .limited(10241));
}
fn release(f: *F) !void {
    _ = try call(f, "dos64_overlay_release", 0);
}
fn acquire(f: *F, identity: u8, carry: u8) !void {
    try put(f, "dos64_overlay_requested", identity);
    _ = try call(f, "dos64_overlay_acquire", carry);
}
fn state(f: *F, ready: u8, current: u8, busy: u8, err: u8) !void {
    try std.testing.expectEqual(ready, try get(f, "dos64_overlay_ready"));
    try std.testing.expectEqual(current, try get(f, "dos64_overlay_current"));
    try std.testing.expectEqual(busy, try get(f, "dos64_overlay_busy"));
    try std.testing.expectEqual(err, try get(f, "dos64_overlay_error"));
}
fn native(f: *F, start: u16, expected: []const u8) !void {
    for (expected, 0..) |v, i| try std.testing.expectEqual(v, f.peek(start + @as(u16, @intCast(i))));
}
fn seedGuard(f: *F) void {
    f.poke(0xbfff, 0xa1);
    f.poke(0xc010, 0xa2);
    for (0xc8f0..0xc900) |a| f.poke(@intCast(a), 0xb3);
    for (0xd000..0xd010) |a| f.poke(@intCast(a), 0xc4);
    for (0xc900..0xd000) |a| f.poke(@intCast(a), 0x97);
}
fn guard(f: *F) !void {
    try std.testing.expectEqual(@as(u8, 0xa1), f.peek(0xbfff));
    try std.testing.expectEqual(@as(u8, 0xa2), f.peek(0xc010));
    for (0xc8f0..0xc900) |a| try std.testing.expectEqual(@as(u8, 0xb3), f.peek(@intCast(a)));
    for (0xd000..0xd010) |a| try std.testing.expectEqual(@as(u8, 0xc4), f.peek(@intCast(a)));
}

test "overlays bootstrap exact whole 4 MiB REU oracle and startup phase ownership" {
    var f = try setup(false);
    defer f.deinit();
    const blob = try assets();
    defer allocator.free(blob);
    const expected = try allocator.alloc(u8, 4 * 1024 * 1024);
    defer allocator.free(expected);
    @memset(expected, 0);
    expected[0x33ffff] = 0x39;
    expected[0x342800] = 0x73;
    c.dos64_reu_poke(f.machine, 0x33ffff, 0x39);
    c.dos64_reu_poke(f.machine, 0x342800, 0x73);
    @memcpy(expected[0x340000..0x342800], blob);
    _ = try call(&f, "dos64_overlay_bootstrap", 0);
    try state(&f, 0xa5, 0, 0, 0);
    try std.testing.expectEqual(@as(u64, 5), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u64, 10240), c.dos64_dma_bytes(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0, expected.ptr, expected.len));
    try native(&f, 0x6000, blob[0..4096]);
    try native(&f, 0x8000, blob[4096..]);
    // The released startup region is now owned by the bitmap; bootstrap must
    // neither read it nor overwrite immutable assets on subsequent calls.
    for (0x6000..0x7000) |a| f.poke(@intCast(a), 0xee);
    _ = try call(&f, "dos64_overlay_bootstrap", 0);
    try std.testing.expectEqual(@as(u64, 5), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0, expected.ptr, expected.len));
}

test "overlays exact replacement image and immutable source guards across switches" {
    var f = try setup(true);
    defer f.deinit();
    const blob = try assets();
    defer allocator.free(blob);
    seedGuard(&f);
    const full_reu = try allocator.alloc(u8, 4 * 1024 * 1024);
    defer allocator.free(full_reu);
    @memset(full_reu, 0);
    @memcpy(full_reu[0x340000..0x342800], blob);
    var old: [1792]u8 = @splat(0x97);
    var transfers: u64 = 5;
    for ([_]u8{ 1, 2, 1, 2, 2, 1 }) |id| {
        const base: usize = @as(usize, id - 1) * 2048;
        const size = std.mem.readInt(u16, blob[base + 6 ..][0..2], .little);
        const before = try get(&f, "dos64_overlay_current");
        try acquire(&f, id, 0);
        if (before != id) transfers += 2;
        @memcpy(old[0..size], blob[base + 16 ..][0..size]);
        try native(&f, 0xc900, &old);
        try state(&f, 0xa5, id, 1, 0);
        try release(&f);
        try guard(&f);
        try std.testing.expectEqual(transfers, c.dos64_dma_transfers(f.machine));
        try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0, full_reu.ptr, full_reu.len));
    }
}

test "overlays reject every malformed startup header byte before either copy" {
    for (0..48) |index| {
        var f = try setup(false);
        defer f.deinit();
        const a: u16 = if (index < 32) 0x6000 + @as(u16, @intCast(index / 16 * 2048 + index % 16)) else 0x8000 + @as(u16, @intCast(index % 16));
        f.poke(a, f.peek(a) ^ 0xff);
        _ = try call(&f, "dos64_overlay_bootstrap", 1);
        try state(&f, 0, 0, 0, 4);
        try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    }
}

test "overlays replacement checks all REU header bytes and rejects wrong slot identity" {
    for ([_]u8{ 1, 2 }) |id| {
        for (0..16) |index| {
            var f = try setup(true);
            defer f.deinit();
            seedGuard(&f);
            const a: u32 = 0x340000 + @as(u32, id - 1) * 2048 + @as(u32, @intCast(index));
            c.dos64_reu_poke(f.machine, a, c.dos64_reu_peek(f.machine, a) ^ 0xff);
            try acquire(&f, id, 1);
            try state(&f, 0xa5, 0, 0, 4);
            try std.testing.expectEqual(@as(u64, 6), c.dos64_dma_transfers(f.machine));
            for (0xc900..0xd000) |n| try std.testing.expectEqual(@as(u8, 0x97), f.peek(@intCast(n)));
            try guard(&f);
        }
    }
    var f = try setup(true);
    defer f.deinit();
    const blob = try assets();
    defer allocator.free(blob);
    for (blob[0..2048], 0..) |v, i| c.dos64_reu_poke(f.machine, 0x340800 + @as(u32, @intCast(i)), v);
    try acquire(&f, 2, 1);
    try state(&f, 0xa5, 0, 0, 4);
}

test "overlays partial bootstrap DMA never publishes ready and full retry repairs both slots" {
    const blob = try assets();
    defer allocator.free(blob);
    for (0..5) |skip| {
        for ([_]u32{ 0, 1, 17, 2047, 2048 }) |prefix| {
            var f = try setup(false);
            defer f.deinit();
            c.dos64_reu_fail_after(f.machine, skip, prefix);
            _ = try call(&f, "dos64_overlay_bootstrap", 1);
            try state(&f, 0, 0, 0, 5);
            try acquire(&f, 1, 1);
            try state(&f, 0, 0, 0, 2);
            _ = try call(&f, "dos64_overlay_bootstrap", 0);
            try state(&f, 0xa5, 0, 0, 0);
            try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, blob.ptr, blob.len));
        }
    }
}

test "overlays partial header or code DMA invalidates current and wrapper requires full retry" {
    const blob = try assets();
    defer allocator.free(blob);
    for ([_]u8{ 1, 2 }) |id| {
        for (0..2) |skip| {
            for ([_]u32{ 0, 1, 17, 800 }) |prefix| {
                var f = try setup(true);
                defer f.deinit();
                try acquire(&f, 3 - id, 0);
                try release(&f);
                seedGuard(&f);
                c.dos64_reu_fail_after(f.machine, skip, prefix);
                try acquire(&f, id, 1);
                try state(&f, 0xa5, 0, 0, 5);
                try guard(&f);
                try acquire(&f, id, 0);
                try state(&f, 0xa5, id, 1, 0);
                const base: usize = @as(usize, id - 1) * 2048;
                const size = std.mem.readInt(u16, blob[base + 6 ..][0..2], .little);
                try native(&f, 0xc900, blob[base + 16 ..][0..size]);
                try release(&f);
                try guard(&f);
            }
        }
    }
}

test "overlays capacity identity unready and busy guards preserve ownership without DMA" {
    for ([_]u8{ 0, 1, 2, 3, 17, 255 }) |capacity| {
        var f = try setup(false);
        defer f.deinit();
        try put(&f, "dos64_overlay_reu_mib", capacity);
        _ = try call(&f, "dos64_overlay_bootstrap", 1);
        try state(&f, 0, 0, 0, 6);
        try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    }
    for ([_]u8{ 4, 8, 16 }) |capacity| {
        var f = try setup(false);
        defer f.deinit();
        try put(&f, "dos64_overlay_reu_mib", capacity);
        _ = try call(&f, "dos64_overlay_bootstrap", 0);
        try state(&f, 0xa5, 0, 0, 0);
    }
    var f = try setup(true);
    defer f.deinit();
    for ([_]u8{ 0, 6, 255 }) |id| {
        try acquire(&f, id, 1);
        try state(&f, 0xa5, 0, 0, 3);
    }
    try acquire(&f, 1, 0);
    const before = c.dos64_dma_transfers(f.machine);
    for ([_][]const u8{ "dos64_overlay_acquire", "dos64_overlay_bootstrap", "dos64_overlay_files_init", "dos64_overlay_files_start", "dos64_overlay_files_poll", "dos64_overlay_render_text_row" }) |entry| {
        _ = try call(&f, entry, 1);
        try state(&f, 0xa5, 1, 1, 1);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_requested"));
        try std.testing.expectEqual(before, c.dos64_dma_transfers(f.machine));
    }
    try release(&f);
}

fn releaseCold(f:*F)!void {
    try put(f,"dos64_cache_limit",32);
    _=try call(f,"dos64_cache_init",0);
    // Real BIOS initialization is cold code; flush before fixture cache reset.
    const r=try f.call("dos64_bios_init",40_000_000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
    _=try call(f,"dos64_cache_flush",0);
    _=try call(f,"dos64_cold_release",0);
}
fn geometry(f: *F) void {
    for ([_]struct { a: u32, v: u8 }{ .{ .a = 0x449, .v = 3 }, .{ .a = 0x44a, .v = 80 }, .{ .a = 0x44b, .v = 0 }, .{ .a = 0x44c, .v = 0 }, .{ .a = 0x44d, .v = 16 }, .{ .a = 0x44e, .v = 0 }, .{ .a = 0x44f, .v = 0 }, .{ .a = 0x462, .v = 0 } }) |x| c.dos64_reu_poke(f.machine, x.a, x.v);
    for (0..1024) |i| f.poke(0x4400 + @as(u16,@intCast(i)),0xff);
    for (0..2048) |i| f.poke(0x4800 + @as(u16, @intCast(i)), 0xff);
    for (0..160) |i| c.dos64_reu_poke(f.machine, 0xb8000 + @as(u32, @intCast(i)), if (i % 2 == 0) 65 else 7);
    for (0x6000..0x8000) |a| f.poke(@intCast(a), 0);
}
fn render(f: *F) !void {
    const file_start = try f.symbol("dos64_files_state_start");
    const file_end = try f.symbol("dos64_files_state_end");
    var saved: [64]u8 = undefined;
    const size: usize = file_end - file_start;
    try std.testing.expect(size <= saved.len);
    for (0..size) |i| saved[i] = f.peek(file_start + @as(u16, @intCast(i)));
    const r = try f.symbol("dos64_render_text_request");
    f.poke(r, 0);
    f.poke(r + 1, 1);
    _ = try call(f, "dos64_overlay_render_text_row", 0);
    try std.testing.expectEqual(@as(u8, 40), f.peek(r + 2));
    for (0x6000..0x6140) |a| try std.testing.expectEqual(@as(u8, 0xff), f.peek(@intCast(a)));
    try state(f, 0xa5, 2, 0, 0);
    try native(f, file_start, saved[0..size]);
}

test "overlays real file transaction survives rendering switch between asynchronous native polls" {
    var f = try setup(true);
    defer f.deinit();
    try releaseCold(&f);
    try put(&f, "dos64_cache_limit", 1);
    _ = try call(&f, "dos64_cache_init", 0);
    geometry(&f);
    uci.dos64_uci_model_enable(f.machine, 0xdf1c, 7, 0xc9);
    _ = try call(&f, "dos64_uci_init", 0);
    _ = try call(&f, "dos64_overlay_files_init", 0);
    try put(&f, "dos64_files_op", 1);
    const d = "ULTIMATE-II DOS V1.2";
    const s = "00,OK";
    uci.dos64_uci_model_block(f.machine, d.ptr, d.len, s.ptr, s.len);
    _ = try call(&f, "dos64_overlay_files_start", 0);
    var polls: usize = 0;
    var seen = false;
    for (0..500) |n| {
        if (try get(&f, "dos64_files_state") != 1) break;
        if (try get(&f, "dos64_uci_state") == 3) {
            try std.testing.expectEqual(@as(u8, 1), uci.dos64_uci_model_command(f.machine, 0));
            try std.testing.expectEqual(@as(u8, 1), uci.dos64_uci_model_command(f.machine, 1));
            seen = true;
        }
        try render(&f);
        const now = try f.symbol("dos64_files_now");
        f.poke(now, @truncate(n + 1));
        f.poke(now + 1, @truncate((n + 1) >> 8));
        _ = try call(&f, "dos64_overlay_files_poll", 0);
        try state(&f, 0xa5, 1, 0, 0);
        polls += 1;
    }
    try std.testing.expect(polls > 5);
    try std.testing.expectEqual(@as(u8, 2), try get(&f, "dos64_files_state"));
    const data = try f.symbol("dos64_uci_data");
    try native(&f, data, d);
    try std.testing.expect(seen);
    try std.testing.expectEqual(@as(u64, 1), uci.dos64_uci_model_count(f.machine, 0));
    try std.testing.expectEqual(@as(u64, 1), uci.dos64_uci_model_count(f.machine, 1));
    try render(&f);
}

test "overlays wrapper failure never executes invalid target and native flags survive" {
    var f = try setup(true);
    defer f.deinit();
    const state_start = try f.symbol("dos64_files_state_start");
    const state_end = try f.symbol("dos64_files_state_end");
    for (state_start..state_end) |a| f.poke(@intCast(a), 0x93);
    for ([_]u8{ 0x20, 0xef, 0x24, 0x29 }) |flags| {
        f.initial_status = flags;
        c.dos64_reu_fail_after(f.machine, 1, 17);
        _ = try call(&f, "dos64_overlay_files_init", 1);
        try state(&f, 0xa5, 0, 0, 5);
        for (state_start..state_end) |a| try std.testing.expectEqual(@as(u8, 0x93), f.peek(@intCast(a)));
    }
    _ = try call(&f, "dos64_overlay_files_init", 0);
    try state(&f, 0xa5, 1, 0, 0);
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_files_state"));
}

test "overlays reject direct replacement with native return inside execution window" {
    for ([_]u16{ 0xc900, 0xc9fe, 0xcfff }) |return_address| {
        var f = try setup(true);
        defer f.deinit();
        try put(&f, "dos64_overlay_requested", 1);
        f.poke(0x1ff, @intCast(return_address >> 8));
        f.poke(0x1fe, @truncate(return_address));
        const stop = return_address + 1;
        c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_overlay_acquire"), .sp = 0xfd, .a = 0, .x = 0, .y = 0, .p = 0x2c, .cycles = 0, .instructions = 0 });
        const r = c.dos64_run(f.machine, stop, 100_000);
        try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
        try std.testing.expectEqual(@as(u8, 1), r.regs.p & 1);
        try std.testing.expectEqual(@as(u8, 0x0c), r.regs.p & 0xce);
        try state(&f, 0xa5, 0, 0, 7);
        try std.testing.expectEqual(@as(u64, 5), c.dos64_dma_transfers(f.machine));
    }
}

test "overlays preserve wrapped target carry and measure verified native manager costs" {
    var f = try setup(false);
    defer f.deinit();
    var before = c.dos64_get_regs(f.machine).cycles;
    const boot = try call(&f, "dos64_overlay_bootstrap", 0);
    const bootstrap_cycles = boot.cycles - before;
    before = c.dos64_get_regs(f.machine).cycles;
    try acquire(&f, 1, 0);
    const file_cycles = c.dos64_get_regs(f.machine).cycles - before;
    try release(&f);
    before = c.dos64_get_regs(f.machine).cycles;
    try acquire(&f, 1, 0);
    const hit_cycles = c.dos64_get_regs(f.machine).cycles - before;
    try release(&f);
    before = c.dos64_get_regs(f.machine).cycles;
    try acquire(&f, 2, 0);
    const text_cycles = c.dos64_get_regs(f.machine).cycles - before;
    try release(&f);
    try releaseCold(&f);
    // Invalid row is a real target failure, distinct from manager failure.
    const r = try f.symbol("dos64_render_text_request");
    f.poke(r, 25);
    f.poke(r + 1, 1);
    _ = try call(&f, "dos64_overlay_render_text_row", 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(r + 4));
    try state(&f, 0xa5, 2, 0, 0);
    std.debug.print("Overlay manager native cycles: bootstrap={d}, file load={d}, text load={d}, same-image hit={d}; excludes DMA stalls and physical elapsed\n", .{ bootstrap_cycles, file_cycles, text_cycles, hit_cycles });
}

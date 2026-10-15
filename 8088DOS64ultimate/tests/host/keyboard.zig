const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn nativeWord(f: *Fixture, a: u16, v: u16) void {
    f.poke(a, @truncate(v));
    f.poke(a +% 1, @truncate(v >> 8));
}
fn address(f: *Fixture, a: u32) !void {
    const p = try f.symbol("dos64_address");
    f.poke(p, @truncate(a));
    f.poke(p + 1, @truncate(a >> 8));
    f.poke(p + 2, @truncate(a >> 16));
}
fn write(f: *Fixture, a: u32, v: u8) !void {
    try address(f, a);
    f.poke(try f.symbol("dos64_mem_value"), v);
    const r = try f.call("dos64_mem_write", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn read(f: *Fixture, a: u32) !u8 {
    try address(f, a);
    const r = try f.call("dos64_mem_read", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}
fn word(f: *Fixture, a: u32, v: u16) !void {
    try write(f, a, @truncate(v));
    try write(f, a + 1, @truncate(v >> 8));
}
fn getWord(f: *Fixture, a: u32) !u16 {
    return @as(u16, try read(f, a)) | (@as(u16, try read(f, a + 1)) << 8);
}
fn symbolByte(f: *Fixture, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn descriptor(f: *Fixture, n: []const u8) !u16 {
    const a = try f.symbol(n);
    const high = try std.fmt.allocPrint(std.testing.allocator, "{s}_high", .{n});
    defer std.testing.allocator.free(high);
    return @as(u16, f.peek(a)) | (@as(u16, f.peek(try f.symbol(high))) << 8);
}
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 1);
    _ = try f.call("dos64_cache_init", 50_000);
    c.dos64_reu_poke(f.machine, 0x41a, 0x1e);
    c.dos64_reu_poke(f.machine, 0x41c, 0x1e);
    const g = try f.symbol("dos64_guest");
    for (0..28) |i| f.poke(g + @as(u16, @intCast(i)), @truncate(i * 13 + 5));
    return f;
}
fn invoke(f: *Fixture, is_enqueue: bool, expected: u8) !void {
    const g = try f.symbol("dos64_guest");
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    const r = try f.call(if (is_enqueue) "dos64_keyboard_enqueue" else "dos64_keyboard_service", 100_000);
    try std.testing.expectEqual(expected, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    for (before, 0..) |v, i| if (is_enqueue or i >= 2) {
        try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
    };
    try std.testing.expectEqual(@as(u8, 0), try symbolByte(f, "dos64_keyboard_host_error"));
}
fn service(f: *Fixture, ax: u16, expected: u8) !void {
    nativeWord(f, try f.symbol("dos64_guest"), ax);
    try invoke(f, false, expected);
}
fn enqueue(f: *Fixture, key: u16, expected: u8) !void {
    nativeWord(f, try f.symbol("dos64_keyboard_key"), key);
    try invoke(f, true, expected);
    try std.testing.expectEqual(key, f.word(try f.symbol("dos64_keyboard_key")));
}
fn cmpFlags(a: u16, b: u16) u16 {
    const d = a -% b;
    var flags: u16 = 0x200;
    if (a < b) flags |= 1;
    if (@popCount(@as(u8, @truncate(d))) % 2 == 0) flags |= 4;
    if (((a ^ b ^ d) & 0x10) != 0) flags |= 0x10;
    if (d == 0) flags |= 0x40;
    if ((d & 0x8000) != 0) flags |= 0x80;
    if ((((a ^ b) & (a ^ d)) & 0x8000) != 0) flags |= 0x800;
    return flags;
}

test "XT keyboard empty read yields without inventing input and unsupported functions are explicit" {
    var f = try init();
    defer f.deinit();
    f.initial_status = 0xef;
    try service(&f, 0x005a, 0);
    try std.testing.expectEqual(@as(u16, 0x005a), f.word(try f.symbol("dos64_guest")));
    try std.testing.expectEqual(@as(u8, 1), try symbolByte(&f, "dos64_keyboard_waiting"));
    try std.testing.expectEqual(@as(u16, 0), try descriptor(&f, "dos64_keyboard_flags_mask"));
    try std.testing.expectEqual(@as(u16, 0x1e), try getWord(&f, 0x41a));
    for ([_]u16{ 0x0301, 0x1002, 0x1103, 0xff04 }) |ax| {
        try service(&f, ax, 1);
        try std.testing.expectEqual(ax, f.word(try f.symbol("dos64_guest")));
        try std.testing.expectEqual(@as(u8, 3), try symbolByte(&f, "dos64_keyboard_status"));
        try std.testing.expectEqual(@as(u8, 0), try symbolByte(&f, "dos64_keyboard_waiting"));
    }
}

test "XT keyboard15-entry FIFO full rejection wraps head and tail repeatedly and preserves all neighboring BDA" {
    var f = try init();
    defer f.deinit();
    for (0x400..0x600) |a| if (a < 0x41a or a >= 0x43e) {
        try write(&f, @intCast(a), @truncate(a * 7));
    };
    var counter: u16 = 0;
    for (0..8) |_| {
        for (0..15) |i| try enqueue(&f, counter + @as(u16, @intCast(i)), 0);
        try enqueue(&f, 0xffff, 1);
        try std.testing.expectEqual(@as(u8, 1), try symbolByte(&f, "dos64_keyboard_status"));
        for (0..15) |i| {
            try service(&f, 0x0100, 0);
            try std.testing.expectEqual(counter + @as(u16, @intCast(i)), f.word(try f.symbol("dos64_guest")));
            try std.testing.expectEqual(@as(u8, 0), try symbolByte(&f, "dos64_keyboard_waiting"));
            try service(&f, 0x0000, 0);
            try std.testing.expectEqual(counter + @as(u16, @intCast(i)), f.word(try f.symbol("dos64_guest")));
            try std.testing.expectEqual(@as(u16, 0), try descriptor(&f, "dos64_keyboard_flags_mask"));
        }
        counter += 15;
        try service(&f, 0x0055, 0);
        try std.testing.expectEqual(@as(u8, 1), try symbolByte(&f, "dos64_keyboard_waiting"));
    }
    for (0x400..0x600) |a| if (a < 0x41a or a >= 0x43e) {
        try std.testing.expectEqual(@as(u8, @truncate(a * 7)), try read(&f, @intCast(a)));
    };
}

test "original XT AH01 always loads head word including empty ring and exports exact CMP RET2 flags" {
    var f = try init();
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    for (0..16) |hi| for (0..16) |ti| {
        const head: u16 = @intCast(0x1e + hi * 2);
        const tail: u16 = @intCast(0x1e + ti * 2);
        try word(&f, 0x41a, head);
        try word(&f, 0x41c, tail);
        try word(&f, 0x400 + @as(u32, head), 0x5a00 | head);
        nativeWord(&f, g + 26, 0xffff);
        try service(&f, 0x0100, 0);
        try std.testing.expectEqual(@as(u16, 0x5a00) | head, f.word(g));
        try std.testing.expectEqual(head, try getWord(&f, 0x41a));
        try std.testing.expectEqual(tail, try getWord(&f, 0x41c));
        const mask = try descriptor(&f, "dos64_keyboard_flags_mask");
        const value = try descriptor(&f, "dos64_keyboard_flags_value");
        try std.testing.expectEqual(@as(u16, 0xbd5), mask);
        try std.testing.expectEqual(cmpFlags(head, tail), value);
        try std.testing.expectEqual(@as(u16, 0xffff), f.word(g + 26));
        try std.testing.expectEqual((@as(u16, 0xffff) & ~mask) | cmpFlags(head, tail), (@as(u16, 0xffff) & ~mask) | value);
    };
}

test "original XT AH02 returns all mutable shift bytes with AH zero and caller flags untouched" {
    var f = try init();
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    for (0..256) |v| {
        try write(&f, 0x417, @intCast(v));
        try service(&f, 0x02c3, 0);
        try std.testing.expectEqual(@as(u16, @intCast(v)), f.word(g));
        try std.testing.expectEqual(@as(u16, 0), try descriptor(&f, "dos64_keyboard_flags_mask"));
    }
    // This operation is independent of ring pointers.
    try word(&f, 0x41a, 0xffff);
    try service(&f, 0x0200, 0);
}

test "keyboard malformed odd out of bounds and high byte pointers fail before AX or queue mutation" {
    var f = try init();
    defer f.deinit();
    for ([_]u16{ 0, 0x1c, 0x1f, 0x3d, 0x3e, 0x100, 0x11e, 0xffff }) |bad| for ([_]u32{ 0x41a, 0x41c }) |at| {
        try word(&f, 0x41a, 0x1e);
        try word(&f, 0x41c, 0x20);
        try word(&f, at, bad);
        for ([_]u16{ 0x005a, 0x015a }) |ax| {
            try service(&f, ax, 1);
            try std.testing.expectEqual(ax, f.word(try f.symbol("dos64_guest")));
            try std.testing.expectEqual(@as(u8, 2), try symbolByte(&f, "dos64_keyboard_status"));
            try std.testing.expectEqual(@as(u16, 0), try descriptor(&f, "dos64_keyboard_flags_mask"));
        }
        try enqueue(&f, 0x1e61, 1);
        try std.testing.expectEqual(@as(u8, 2), try symbolByte(&f, "dos64_keyboard_status"));
        try std.testing.expectEqual(bad, try getWord(&f, at));
    };
}

test "keyboard observes dirty BDA with one cache frame and publishes ring changes coherently" {
    var f = try init();
    defer f.deinit();
    try word(&f, 0x41a, 0x3c);
    try word(&f, 0x41c, 0x1e);
    try word(&f, 0x43c, 0x4800);
    try std.testing.expectEqual(@as(u8, 0x1e), c.dos64_reu_peek(f.machine, 0x41a));
    try service(&f, 0x0100, 0);
    try std.testing.expectEqual(@as(u16, 0x4800), f.word(try f.symbol("dos64_guest")));
    try service(&f, 0x0000, 0);
    try std.testing.expectEqual(@as(u16, 0x1e), try getWord(&f, 0x41a));
    try enqueue(&f, 0x1e61, 0);
    try std.testing.expectEqual(@as(u16, 0x20), try getWord(&f, 0x41c));
    _ = try read(&f, 0x600); // force dirty BDA eviction
    try std.testing.expectEqual(@as(u8, 0x20), c.dos64_reu_peek(f.machine, 0x41c));
    try service(&f, 0x0000, 0);
    try std.testing.expectEqual(@as(u16, 0x1e61), f.word(try f.symbol("dos64_guest")));
}

test "keyboard partial REU load and dirty eviction failures remain terminal cache errors with retry authority" {
    for ([_]bool{ false, true }) |dirty| {
        var f = try init();
        defer f.deinit();
        const g = try f.symbol("dos64_guest");
        if (dirty) try write(&f, 0x800, 0xa7);
        c.dos64_reu_fail_after(f.machine, 0, 17);
        nativeWord(&f, g, 0x0155);
        const r = try f.call("dos64_keyboard_service", 100_000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 1), try symbolByte(&f, "dos64_keyboard_host_error"));
        try std.testing.expectEqual(@as(u8, 4), try symbolByte(&f, "dos64_keyboard_status"));
        try std.testing.expectEqual(@as(u16, 0x0155), f.word(g));
        try std.testing.expectEqual(@as(u16, 0), try descriptor(&f, "dos64_keyboard_flags_mask"));
        try std.testing.expectEqual(@as(u8, 0x1e), c.dos64_reu_peek(f.machine, 0x41a));
        try enqueue(&f, 0x1e61, 0);
        try service(&f, 0x0000, 0);
        try std.testing.expectEqual(@as(u16, 0x1e61), f.word(g));
        if (dirty) {
            try std.testing.expectEqual(@as(u8, 0xa7), try read(&f, 0x800));
        }
    }
}

test "keyboard callback preserves all native status combinations and bounds every observed native write" {
    var f = try init();
    defer f.deinit();
    const lo = try f.symbol("dos64_keyboard_state_start");
    const hi = try f.symbol("dos64_keyboard_state_end");
    const guards = [_]u16{ 0x1f, 0xe0, lo - 1, hi, 0x8200, 0xbfff, 0xc000, 0xefff };
    for (guards, 0..) |a, i| f.poke(a, @truncate(0x5a + i));
    const banking = f.peek(1);
    for (0..256) |p| {
        f.initial_status = @intCast(p);
        try service(&f, 0x0255, 0);
        try std.testing.expectEqual(banking & 0x2f, f.peek(1) & 0x2f);
        for (guards, 0..) |a, i| try std.testing.expectEqual(@as(u8, @truncate(0x5a + i)), f.peek(a));
    }
    // Reinitialize cold cache so this call records the REU DMA setup as well.
    _ = try f.call("dos64_cache_init", 50_000);
    try service(&f, 0x0100, 0);
    const guest = try f.symbol("dos64_guest");
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        try std.testing.expect(a <= 1 or (a >= 0x20 and a < 0xe0) or (a >= 0x100 and a < 0x200) or (a >= guest and a < 0xe100) or (a >= 0xe100 and a < 0xe900) or (a >= 0xe900 and a < 0xe9c0) or (a >= lo and a < hi) or (a >= 0x8000 and a < 0x8200) or (a >= 0xdf00 and a <= 0xdf0a));
    }
}

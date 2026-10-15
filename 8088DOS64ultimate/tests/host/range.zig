const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn word(f: *Fixture, a: u16, v: u16) void {
    f.poke(a, @truncate(v));
    f.poke(a +% 1, @truncate(v >> 8));
}
fn far(f: *Fixture, a: u16, v: u32) void {
    for (0..3) |i| f.poke(a + @as(u16, @intCast(i)), @truncate(v >> @as(u5, @intCast(i * 8))));
}
fn getFar(f: *Fixture, a: u16) u32 {
    return @as(u32, f.peek(a)) | (@as(u32, f.peek(a + 1)) << 8) | (@as(u32, f.peek(a + 2)) << 16);
}
fn init(frames: u8, mode: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), mode);
    return f;
}
fn request(f: *Fixture, guest: u32, reu: u32, length: u16, direction: u8) !u16 {
    const r = try f.symbol("dos64_range_request");
    far(f, r, guest);
    far(f, r + 3, reu);
    word(f, r + 6, length);
    f.poke(r + 8, direction);
    f.poke(r + 9, 0xbb);
    f.poke(r + 10, 0xcc);
    word(f, r + 11, 0xdddd);
    return r;
}
fn copy(f: *Fixture) !host.c.Dos64Regs {
    return f.call("dos64_range_copy", 80_000_000);
}
fn writeGuest(f: *Fixture, address: u32, value: u8) !void {
    far(f, try f.symbol("dos64_address"), address);
    f.poke(try f.symbol("dos64_mem_value"), value);
    const r = try f.call("dos64_mem_write", 20_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn readGuest(f: *Fixture, address: u32) !u8 {
    far(f, try f.symbol("dos64_address"), address);
    const r = try f.call("dos64_mem_read", 20_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}
fn assertProgress(f: *Fixture, r: u16, guest: u32, reu: u32, remaining: u16, done: u16, status: u8, err: u8) !void {
    try std.testing.expectEqual(guest, getFar(f, r));
    try std.testing.expectEqual(reu, getFar(f, r + 3));
    try std.testing.expectEqual(remaining, f.word(r + 6));
    try std.testing.expectEqual(done, f.word(r + 11));
    try std.testing.expectEqual(status, f.peek(r + 9));
    try std.testing.expectEqual(err, f.peek(r + 10));
}

test "coherent range import export preserve dirty ownership guards and REU bank seams" {
    for ([_]u8{ 1, 2 }) |frames| {
        var f = try init(frames, 1);
        defer f.deinit();
        for (0x3e00..0x4600) |a| c.dos64_reu_poke(f.machine, @intCast(a), 0x5a);
        for (0..549) |i| c.dos64_reu_poke(f.machine, 0x17ff80 + @as(u32, @intCast(i)), @truncate(i * 13 + 7));
        try writeGuest(&f, 0x3f10, 0xc3); // outside destination, already dirty
        f.poke(0xbfff, 0x29);
        f.poke(0xc100, 0x83);
        f.poke(0xcfff, 0xb7);
        f.initial_status = 0xed;
        const r = try request(&f, 0x3fef, 0x17ff80, 549, 0);
        var result = try copy(&f);
        try std.testing.expectEqual(@as(u8, 0), result.p & 1);
        try std.testing.expectEqual(@as(u8, 0xec), result.p & 0xef);
        try assertProgress(&f, r, 0x4214, 0x1801a5, 0, 549, 1, 0);
        for (0..549) |i| try std.testing.expectEqual(@as(u8, @truncate(i * 13 + 7)), try readGuest(&f, 0x3fef + @as(u32, @intCast(i))));
        try std.testing.expectEqual(@as(u8, 0xc3), try readGuest(&f, 0x3f10));
        try std.testing.expectEqual(@as(u8, 0x5a), try readGuest(&f, 0x3fee));
        try std.testing.expectEqual(@as(u8, 0x5a), try readGuest(&f, 0x4214));
        try writeGuest(&f, 0x3ff4, 0xd7); // export must see authoritative dirty data
        c.dos64_reu_poke(f.machine, 0x2fff7f, 0x69);
        c.dos64_reu_poke(f.machine, 0x3001a5, 0x96);
        _ = try request(&f, 0x3fef, 0x2fff80, 549, 1);
        result = try copy(&f);
        try std.testing.expectEqual(@as(u8, 0), result.p & 1);
        try assertProgress(&f, r, 0x4214, 0x3001a5, 0, 549, 1, 0);
        for (0..549) |i| try std.testing.expectEqual(@as(u8, if (i == 5) 0xd7 else @truncate(i * 13 + 7)), c.dos64_reu_peek(f.machine, 0x2fff80 + @as(u32, @intCast(i))));
        try std.testing.expectEqual(@as(u8, 0x69), c.dos64_reu_peek(f.machine, 0x2fff7f));
        try std.testing.expectEqual(@as(u8, 0x96), c.dos64_reu_peek(f.machine, 0x3001a5));
        try std.testing.expectEqual(@as(u8, 0x29), f.peek(0xbfff));
        try std.testing.expectEqual(@as(u8, 0x83), f.peek(0xc100));
        try std.testing.expectEqual(@as(u8, 0xb7), f.peek(0xcfff));
    }
}

test "range guest physical wrap is linear and 65535 byte extent remains bounded" {
    var f = try init(2, 1);
    defer f.deinit();
    const r = try request(&f, 0xffff0, 0x3f0001, 65535, 0);
    for (0..65535) |i| c.dos64_reu_poke(f.machine, 0x3f0001 + @as(u32, @intCast(i)), @truncate((i * 29) ^ 0xb5));
    const result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try assertProgress(&f, r, 0x0ffef, 0x400000, 0, 65535, 1, 0);
    for ([_]u32{ 0, 1, 15, 16, 255, 256, 32768, 65534 }) |i| try std.testing.expectEqual(@as(u8, @truncate((i * 29) ^ 0xb5)), try readGuest(&f, (0xffff0 + i) & 0xfffff));
}

test "range uses PC bus policy for ROM holes and CGA rather than guest backing DMA" {
    var f = try init(2, 0);
    defer f.deinit();
    c.dos64_reu_poke(f.machine, 0x100000, 0x34);
    c.dos64_reu_poke(f.machine, 0xa0000, 0x77);
    _ = try request(&f, 0xa0000, 0x100000, 1, 0);
    var result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0xff), try readGuest(&f, 0xa0000));
    try std.testing.expectEqual(@as(u8, 0x77), c.dos64_reu_peek(f.machine, 0xa0000));
    _ = try request(&f, 0xa0000, 0x100001, 1, 1);
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0xff), c.dos64_reu_peek(f.machine, 0x100001));
    c.dos64_reu_poke(f.machine, 0xf0000, 0x78);
    _ = try request(&f, 0xf0000, 0x100002, 1, 1);
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0x78), c.dos64_reu_peek(f.machine, 0x100002));
    _ = try request(&f, 0xf0000, 0x100000, 1, 0);
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0x78), try readGuest(&f, 0xf0000));
    _ = try request(&f, 0xb8000, 0x100000, 1, 0);
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0x34), try readGuest(&f, 0xb8000));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_video_dirty")));
}

test "range validates input and disjoint REU extent before touching data including empty" {
    const cases = [_]struct { guest: u32 = 0, reu: u32 = 0x100000, length: u16 = 0, dir: u8 = 0, err: u8 = 0 }{
        .{},                           .{ .guest = 0xfffff, .reu = 0x3fffff }, .{ .guest = 0x100000, .err = 1 }, .{ .dir = 2, .err = 1 },
        .{ .reu = 0xfffff, .err = 2 }, .{ .reu = 0x400000, .err = 2 },         .{ .reu = 0xffffff, .err = 2 },   .{ .reu = 0x3fffff, .length = 2, .err = 2 },
    };
    for (cases) |t| {
        var f = try init(1, 1);
        defer f.deinit();
        const r = try request(&f, t.guest, t.reu, t.length, t.dir);
        const result = try copy(&f);
        try std.testing.expectEqual(@as(u8, if (t.err == 0) 0 else 1), result.p & 1);
        try assertProgress(&f, r, t.guest, t.reu, t.length, 0, if (t.err == 0) 1 else 2, t.err);
        try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    }
}

test "range import error reports only bytes committed and retry imports remaining" {
    var f = try init(1, 1);
    defer f.deinit();
    for (0..4) |i| c.dos64_reu_poke(f.machine, 0x100000 + @as(u32, @intCast(i)), @as(u8, @intCast(i)) + 0x30);
    const r = try request(&f, 0x1ff, 0x100000, 4, 0);
    // Range staging load, first guest page load, dirty victim write-back, then
    // fail loading next guest page: byte0 is committed, byte1 is not.
    c.dos64_reu_fail_after(f.machine, 3, 16);
    var result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 1), result.p & 1);
    try assertProgress(&f, r, 0x200, 0x100001, 3, 1, 2, 3);
    try std.testing.expectEqual(@as(u8, 0x30), c.dos64_reu_peek(f.machine, 0x1ff));
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try assertProgress(&f, r, 0x203, 0x100004, 0, 3, 1, 0);
    for (0..4) |i| try std.testing.expectEqual(@as(u8, @intCast(i)) + 0x30, try readGuest(&f, 0x1ff + @as(u32, @intCast(i))));
}

test "range DMA failures never publish uncertain current chunk progress" {
    for ([_]u8{ 0, 1 }) |direction| {
        var f = try init(1, 1);
        defer f.deinit();
        for (0..300) |i| {
            c.dos64_reu_poke(f.machine, 0x100000 + @as(u32, @intCast(i)), 0x68);
            c.dos64_reu_poke(f.machine, 0x2000 + @as(u32, @intCast(i)), 0x97);
        }
        const r = try request(&f, 0x2000, 0x100000, 300, direction);
        // Export gathers one cold guest page before DMA; import fails at its
        // staging DMA immediately. Prefixbytesmodeldemonstratesuncertainty.
        c.dos64_reu_fail_after(f.machine, if (direction == 0) 0 else 1, 16);
        const result = try copy(&f);
        try std.testing.expectEqual(@as(u8, 1), result.p & 1);
        try assertProgress(&f, r, 0x2000, 0x100000, 300, 0, 2, 4);
        if (direction == 1) {
            try std.testing.expectEqual(@as(u8, 0x97), c.dos64_reu_peek(f.machine, 0x100000));
            try std.testing.expectEqual(@as(u8, 0x68), c.dos64_reu_peek(f.machine, 0x100010));
        }
        try std.testing.expectEqual(@as(u8, 0x97), try readGuest(&f, 0x2000));
    }
}

test "range export advances only complete chunks and retries uncertain tail" {
    var f = try init(1, 1);
    defer f.deinit();
    for (0..300) |i| {
        c.dos64_reu_poke(f.machine, 0x100000 + @as(u32, @intCast(i)), 0x68);
        c.dos64_reu_poke(f.machine, 0x2000 + @as(u32, @intCast(i)), 0x97);
    }
    const r = try request(&f, 0x2000, 0x100000, 300, 1);
    // One source-page load, first chunk DMA, then partial second chunk DMA.
    c.dos64_reu_fail_after(f.machine, 2, 16);
    var result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 1), result.p & 1);
    try assertProgress(&f, r, 0x2100, 0x100100, 44, 256, 2, 4);
    try std.testing.expectEqual(@as(u8, 0x97), c.dos64_reu_peek(f.machine, 0x10010f));
    try std.testing.expectEqual(@as(u8, 0x68), c.dos64_reu_peek(f.machine, 0x100110));
    result = try copy(&f);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try assertProgress(&f, r, 0x212c, 0x10012c, 0, 44, 1, 0);
    for (0..300) |i| try std.testing.expectEqual(@as(u8, 0x97), c.dos64_reu_peek(f.machine, 0x100000 + @as(u32, @intCast(i))));
    var gather = try init(1, 1);
    defer gather.deinit();
    _ = try request(&gather, 0x1ff, 0x100000, 4, 1);
    c.dos64_reu_fail_after(gather.machine, 1, 16);
    result = try copy(&gather);
    try std.testing.expectEqual(@as(u8, 1), result.p & 1);
    try assertProgress(&gather, try gather.symbol("dos64_range_request"), 0x1ff, 0x100000, 4, 0, 2, 3);
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(gather.machine, 0x100000));
}

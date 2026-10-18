const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn pattern(index: usize, edited: bool) u8 {
    const base = @as(u8, @truncate(index)) ^ @as(u8, @intCast(index / 256)) ^ 0xa7;
    return base ^ (if (edited and index % 256 == 0) @as(u8, 0x5a) else 0);
}
fn outputMatches(f: *Fixture, wrong: bool) !void {
    for (0..1536) |i| {
        const expected = pattern(i, true) ^ (if (wrong and i == 1280) @as(u8, 1) else 0);
        if (f.peek(0x6000 + @as(u16, @intCast(i))) != expected) return error.OutputMismatch;
    }
}
fn canaries(f: *Fixture) void {
    for ([_]u32{0x34feff, 0x350500, 0x35feff, 0x360500}) |a| c.dos64_reu_poke(f.machine, a, 0x39);
    for (0..256) |i| {
        c.dos64_reu_poke(f.machine, 0x7fc00 + @as(u32, @intCast(i)), 0x77);
        c.dos64_reu_poke(f.machine, 0x80300 + @as(u32, @intCast(i)), 0x66);
    }
    f.poke(0x5fff, 0xe7);
    f.poke(0x6600, 0xd2);
    f.poke(0xc100, 0xbc);
}
fn checkCanaries(f: *Fixture) !void {
    for ([_]u32{0x34feff, 0x350500, 0x35feff, 0x360500}) |a| try std.testing.expectEqual(@as(u8, 0x39), c.dos64_reu_peek(f.machine, a));
    for (0..256) |i| {
        try std.testing.expectEqual(@as(u8, 0x77), c.dos64_reu_peek(f.machine, 0x7fc00 + @as(u32, @intCast(i))));
        try std.testing.expectEqual(@as(u8, 0x66), c.dos64_reu_peek(f.machine, 0x80300 + @as(u32, @intCast(i))));
    }
    try std.testing.expectEqual(@as(u8, 0xe7), f.peek(0x5fff));
    try std.testing.expectEqual(@as(u8, 0xd2), f.peek(0x6600));
    try std.testing.expectEqual(@as(u8, 0xbc), f.peek(0xc100));
}
fn readGuest(f: *Fixture, physical: u32) !u8 {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(physical));
    f.poke(a + 1, @truncate(physical >> 8));
    f.poke(a + 2, @truncate(physical >> 16));
    const r = try f.call("dos64_mem_read", 5000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}

test "shared range probe verifies source dirty guest export and host readback across both seams" {
    var f = try Fixture.init();
    defer f.deinit();
    // Baseline capacity, deliberately narrower than the VICE harness's 16 MiB.
    try std.testing.expectEqual(@as(u8, 1), c.dos64_enable_reu_sized(f.machine, 4096));
    canaries(&f);
    _ = try f.call("dos64_range_probe", 5_000_000);
    try f.expectStatus(0xa5);
    try std.testing.expectEqual(@as(u8, 0), f.peek((try f.symbol("dos64_mailbox")) + 4));
    try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_cache_limit")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_memory_mode")));
    const request = try f.symbol("dos64_range_request");
    try std.testing.expectEqual(@as(u16, 1536), f.word(request + 11));
    try std.testing.expectEqual(@as(u8, 1), f.peek(request + 9));
    try outputMatches(&f, false);
    for (0..1536) |i| {
        try std.testing.expectEqual(pattern(i, false), c.dos64_reu_peek(f.machine, 0x34ff00 + @as(u32, @intCast(i))));
        try std.testing.expectEqual(pattern(i, true), c.dos64_reu_peek(f.machine, 0x35ff00 + @as(u32, @intCast(i))));
    }
    // Complete dirty backing and independently reread the final guest bytes.
    const flush = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), flush.p & 1);
    for (0..1536) |i| try std.testing.expectEqual(pattern(i, true), c.dos64_reu_peek(f.machine, 0x7fd00 + @as(u32, @intCast(i))));
    try checkCanaries(&f);
    try std.testing.expect(f.stack_high_water <= 40);
}

test "range probe output oracle catches wrong expectations and corruption despite pass mailbox" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_range_probe", 5_000_000);
    try f.expectStatus(0xa5);
    try outputMatches(&f, false);
    try std.testing.expectError(error.OutputMismatch, outputMatches(&f, true));
    f.poke(0x6500, f.peek(0x6500) ^ 0x5a); // stale last-page byte
    try f.expectStatus(0xa5);
    try std.testing.expectError(error.OutputMismatch, outputMatches(&f, false));
}

test "range probe reports partial DMA failures without exporting uncommitted bytes" {
    const Case = struct { after: u32, stage: u8, done: u16 };
    for ([_]Case{ .{ .after = 0, .stage = 1, .done = 0 }, .{ .after = 6, .stage = 2, .done = 0 }, .{ .after = 8, .stage = 2, .done = 256 } }) |case| {
        var f = try Fixture.init();
        defer f.deinit();
        c.dos64_enable_reu(f.machine);
        canaries(&f);
        for (0..1536) |i| {
            f.poke(0x6000 + @as(u16, @intCast(i)), 0xec);
            c.dos64_reu_poke(f.machine, 0x35ff00 + @as(u32, @intCast(i)), 0x2c);
        }
        c.dos64_reu_fail_after(f.machine, case.after, 17);
        _ = try f.call("dos64_range_probe", 5_000_000);
        try f.expectStatus(0xe1);
        try std.testing.expectEqual(case.stage, f.peek((try f.symbol("dos64_mailbox")) + 4));
        if (case.stage == 2) {
            const request = try f.symbol("dos64_range_request");
            try std.testing.expectEqual(case.done, f.word(request + 11));
            try std.testing.expectEqual(@as(u8, 4), f.peek(request + 10));
            for (0..case.done) |i| try std.testing.expectEqual(pattern(i, false), try readGuest(&f, 0x7fd00 + @as(u32, @intCast(i))));
        }
        for (0..1536) |i| {
            try std.testing.expectEqual(@as(u8, 0xec), f.peek(0x6000 + @as(u16, @intCast(i))));
            try std.testing.expectEqual(@as(u8, 0x2c), c.dos64_reu_peek(f.machine, 0x35ff00 + @as(u32, @intCast(i))));
        }
        try checkCanaries(&f);
    }
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const day: u32 = 0x1800b0;

fn word(f: *Fixture, name: []const u8, v: u16) !void {
    const a = try f.symbol(name);
    f.poke(a, @truncate(v)); f.poke(a + 1, @truncate(v >> 8));
}
fn init(ticks: u32, flag: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 1);
    _ = try f.call("dos64_cache_init", 50_000);
    for (0..4) |i| c.dos64_reu_poke(f.machine, 0x46c + @as(u32, @intCast(i)), @truncate(ticks >> @as(u5, @intCast(i * 8))));
    c.dos64_reu_poke(f.machine, 0x470, flag);
    c.dos64_reu_poke(f.machine, 0x46b, 0x5a);
    c.dos64_reu_poke(f.machine, 0x471, 0xa5);
    return f;
}
fn guest(f: *Fixture, ax: u16, ticks: u32) ![28]u8 {
    const g = try f.symbol("dos64_guest");
    for (0..28) |i| f.poke(g + @as(u16, @intCast(i)), @truncate(i * 13 + 7));
    f.poke(g, @truncate(ax)); f.poke(g + 1, @truncate(ax >> 8));
    f.poke(g + 2, @truncate(ticks >> 16)); f.poke(g + 3, @truncate(ticks >> 24));
    f.poke(g + 4, @truncate(ticks)); f.poke(g + 5, @truncate(ticks >> 8));
    var result: [28]u8 = undefined;
    for (&result, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    return result;
}
fn expectGuest(f: *Fixture, expected: [28]u8) !void {
    const g = try f.symbol("dos64_guest");
    for (expected, 0..) |v, i| try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
}
fn call(f: *Fixture, entry: []const u8, failure: bool) !void {
    f.poke(try f.symbol("dos64_clock_host_error"), 0xa5);
    const r = try f.call(entry, 100_000);
    try std.testing.expectEqual(@as(u8, @intFromBool(failure)), r.p & 1);
    try std.testing.expectEqual(@as(u8, @intFromBool(failure)), f.peek(try f.symbol("dos64_clock_host_error")));
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn expectBda(f: *Fixture, ticks: u32, flag: u8) !void {
    try flush(f);
    for (0..4) |i| try std.testing.expectEqual(@as(u8, @truncate(ticks >> @as(u5, @intCast(i * 8)))), c.dos64_reu_peek(f.machine, 0x46c + @as(u32, @intCast(i))));
    try std.testing.expectEqual(flag, c.dos64_reu_peek(f.machine, 0x470));
    try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x46b));
    try std.testing.expectEqual(@as(u8, 0xa5), c.dos64_reu_peek(f.machine, 0x471));
}
fn write(f: *Fixture, address: u32, value: u8) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address)); f.poke(a + 1, @truncate(address >> 8)); f.poke(a + 2, @truncate(address >> 16));
    f.poke(try f.symbol("dos64_mem_value"), value);
    const r = try f.call("dos64_mem_write", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}

test "XT clock all256 functions retain original AH decrement and saved guest FLAGS" {
    var f = try init(0x12345678, 0xa7);
    defer f.deinit();
    for (0..256) |ah| {
        var expected = try guest(&f, (@as(u16, @intCast(ah)) << 8) | 0xc9, 0x12345678);
        if (ah == 0) { expected[0] = 0xa7; } else { expected[1] -= 1; }
        try call(&f, "dos64_clock_service", false);
        try expectGuest(&f, expected);
    }
    try expectBda(&f, 0x12345678, 0);
}
test "XT AH00 returns full midnight byte exactly once and coherent high low words" {
    for ([_]u8{ 0, 1, 2, 0x80, 0xff }) |flag| {
        var f = try init(0xfedcba98, flag);
        defer f.deinit();
        var expected = try guest(&f, 0x00c9, 0xfedcba98);
        expected[0] = flag;
        try call(&f, "dos64_clock_service", false);
        try expectGuest(&f, expected);
        try std.testing.expectEqual(flag, c.dos64_reu_peek(f.machine, 0x470)); // dirty cache authoritative
        expected[0] = 0;
        try call(&f, "dos64_clock_service", false);
        try expectGuest(&f, expected);
        try expectBda(&f, 0xfedcba98, 0);
    }
}
test "XT AH01 accepts unnormalized times including high words and preserves AL CX DX" {
    for ([_]u32{ 0, day - 1, day, day + 1, 0x12345678, 0x80000000, 0xffffffff }) |ticks| {
        var f = try init(0, 0xff);
        defer f.deinit();
        var expected = try guest(&f, 0x01c9, ticks);
        expected[1] = 0;
        try call(&f, "dos64_clock_service", false);
        try expectGuest(&f, expected);
        try expectBda(&f, ticks, 0);
    }
}
test "XT unsupported RTC AH02 probe is handled unchanged except AH and performs no DMA" {
    var f = try init(0x76543210, 0xff);
    defer f.deinit();
    c.dos64_reu_fail_after(f.machine, 0, 17);
    for (2..256) |ah| {
        var expected = try guest(&f, (@as(u16, @intCast(ah)) << 8) | 0xc9, 0);
        expected[1] -= 1;
        try call(&f, "dos64_clock_service", false);
        try expectGuest(&f, expected);
    }
    const expected = try guest(&f, 0x00c9, 0);
    try call(&f, "dos64_clock_service", true); // no-op calls left fault armed
    try expectGuest(&f, expected);
}
test "clock advance wide arithmetic oracle covers exact midnight and invalid set wrap" {
    for ([_]u32{ 0, 0xffff, day - 257, day - 1, day, day + 1, 0xffffff00, 0xffffffff }) |start| {
        for ([_]u16{ 1, 255, 256, 257, 65535 }) |count| {
            var f = try init(start, 0xa7);
            defer f.deinit();
            const before = try guest(&f, 0x9712, 0x12345678);
            try word(&f, "dos64_clock_count", count);
            var remaining = count;
            while (remaining != 0) {
                const consumed: u16 = @min(remaining, 256);
                try call(&f, "dos64_clock_advance", false);
                remaining -= consumed;
                try std.testing.expectEqual(consumed, f.word(try f.symbol("dos64_clock_done")));
                try std.testing.expectEqual(remaining, f.word(try f.symbol("dos64_clock_count")));
                try expectGuest(&f, before);
            }
            // Distance on the entire32-bit ring models original equality;
            // values already above day must travel around32-bit wrap first.
            const until_day: u64 = (@as(u64, day) + 0x1_0000_0000 - start) % 0x1_0000_0000;
            const rolls = until_day != 0 and until_day <= count;
            const expected: u32 = if (rolls) @intCast(@as(u64, count) - until_day) else start +% @as(u32, count);
            try expectBda(&f, expected, if (rolls) 1 else 0xa7);
        }
    }
}
test "zero advance is bounded no-op with no cache access and clears stale status progress" {
    var f = try init(day - 1, 0xff);
    defer f.deinit();
    c.dos64_reu_fail_after(f.machine, 0, 0);
    try word(&f, "dos64_clock_count", 0);
    try word(&f, "dos64_clock_done", 0xffff);
    const expected = try guest(&f, 0x00c9, 0);
    try call(&f, "dos64_clock_advance", false);
    try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_clock_done")));
    try expectGuest(&f, expected);
    try call(&f, "dos64_clock_service", true);
}
test "clock cache acquisition failures leave guest BDA progress authoritative and retry" {
    for ([_][]const u8{ "dos64_clock_service", "dos64_clock_advance" }) |entry| {
        for ([_]u8{ 0, 1 }) |ah| {
            var f = try init(day - 1, 0xa7);
            defer f.deinit();
            const expected = try guest(&f, @as(u16, ah) << 8 | 0xc9, 0xfedcba98);
            try word(&f, "dos64_clock_count", 257);
            c.dos64_reu_fail_after(f.machine, 0, 17);
            try call(&f, entry, true);
            try expectGuest(&f, expected);
            try std.testing.expectEqual(@as(u16, 257), f.word(try f.symbol("dos64_clock_count")));
            if (std.mem.eql(u8, entry, "dos64_clock_advance")) try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_clock_done")));
            try call(&f, entry, false);
            const final_ticks: u32 = if (std.mem.eql(u8, entry, "dos64_clock_advance")) 255 else if (ah == 1) 0xfedcba98 else day - 1;
            try expectBda(&f, final_ticks, if (std.mem.eql(u8, entry, "dos64_clock_advance")) 1 else 0);
        }
    }
}
test "dirty BDA one-frame eviction faults preserve completed ticks and retry exactly once" {
    var f = try init(0, 0xa7);
    defer f.deinit();
    // A dirty guest update is the clock authority before any REU flush.
    try write(&f, 0x46c, 0xaf); try write(&f, 0x46d, 0); try write(&f, 0x46e, 0x18);
    try word(&f, "dos64_clock_count", 257);
    try call(&f, "dos64_clock_advance", false);
    try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_clock_count")));
    // Arm writeback failure while resolving a different guest page.
    c.dos64_reu_fail_after(f.machine, 0, 17);
    const a = try f.symbol("dos64_address");
    f.poke(a, 0); f.poke(a + 1, 8); f.poke(a + 2, 0);
    const failed = try f.call("dos64_mem_read", 50_000);
    try std.testing.expectEqual(@as(u8, 1), failed.p & 1);
    try call(&f, "dos64_clock_advance", false);
    try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_clock_count")));
    try expectBda(&f, 256, 1);
}
test "native caller flags preserved on service tick no-op and fatal paths" {
    for ([_]u8{ 0x20, 0x2e, 0xe8, 0xef }) |p| {
        var f = try init(day - 1, 0xff);
        defer f.deinit();
        f.initial_status = p;
        _ = try guest(&f, 0x02c9, 0);
        try call(&f, "dos64_clock_service", false);
        try word(&f, "dos64_clock_count", 256);
        c.dos64_reu_fail_after(f.machine, 0, 0);
        try call(&f, "dos64_clock_advance", true);
        try call(&f, "dos64_clock_advance", false);
        _ = try guest(&f, 0x00c9, 255);
        try call(&f, "dos64_clock_service", false);
        try expectBda(&f, 255, 0);
    }
}
test "same-page clock commits need one DMA and preserve complete BDA and state guards" {
    for ([_]u8{ 0, 1, 2 }) |kind| {
        var f = try init(day - 1, 0x80);
        defer f.deinit();
        const lo = try f.symbol("dos64_clock_state_start");
        const hi = try f.symbol("dos64_clock_state_end");
        f.poke(lo - 1, 0x69); f.poke(hi, 0x96);
        var expected: [512]u8 = undefined;
        for (&expected, 0..) |*v, i| {
            const address: u32 = 0x400 + @as(u32, @intCast(i));
            v.* = if (address >= 0x46c and address <= 0x470) c.dos64_reu_peek(f.machine, address) else @truncate(i * 29 + 3);
            c.dos64_reu_poke(f.machine, address, v.*);
        }
        _ = try guest(&f, @as(u16, if (kind == 1) 1 else 0) << 8 | 0xc9, 0x12345678);
        try word(&f, "dos64_clock_count", 256);
        // Exactly one DMA may acquire BDA. All later writes use that frame.
        c.dos64_reu_fail_after(f.machine, 1, 17);
        try call(&f, if (kind == 2) "dos64_clock_advance" else "dos64_clock_service", false);
        try std.testing.expectEqual(@as(u8, 0x69), f.peek(lo - 1));
        try std.testing.expectEqual(@as(u8, 0x96), f.peek(hi));
        const ticks: u32 = if (kind == 0) day - 1 else if (kind == 1) 0x12345678 else 255;
        for (0..4) |i| expected[0x6c + i] = @truncate(ticks >> @as(u5, @intCast(i * 8)));
        expected[0x70] = if (kind == 2) 1 else 0;
        // Fault still armed after the coherent commit; failed writeback must
        // preserve the entire dirty frame, then a full retry flush succeeds.
        const failed = try f.call("dos64_cache_flush", 100_000);
        try std.testing.expectEqual(@as(u8, 1), failed.p & 1);
        try flush(&f);
        for (expected, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_reu_peek(f.machine, 0x400 + @as(u32, @intCast(i))));
    }
}

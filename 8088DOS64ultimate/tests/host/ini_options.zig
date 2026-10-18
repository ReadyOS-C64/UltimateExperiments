const std = @import("std");
const h = @import("machine.zig");
const F = h.Fixture;
const c = h.c;
fn crc(b: []const u8) u32 {
    var v: u32 = 0xffffffff;
    for (b) |x| {
        v ^= x;
        for (0..8) |_| {
            const low = v & 1;
            v >>= 1;
            if (low != 0) v ^= 0xedb88320;
        }
    }
    return ~v;
}
fn put(b: []u8, at: usize, v: u32) void {
    std.mem.writeInt(u32, b[at..][0..4], v, .little);
}
fn record(columns: u8, identity: u32, main: u32) [32]u8 {
    var b: [32]u8 = @splat(0);
    @memcpy(b[0..4], "D64O");
    b[4] = 1;
    b[5] = 0xa5;
    b[6] = 32;
    put(&b, 8, identity);
    put(&b, 12, main);
    b[16] = columns;
    put(&b, 28, crc(b[0..28]));
    return b;
}
fn init(identity: u32, main: u32) !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    f.poke(try f.symbol("dos64_loader_required"), 0xa5);
    f.poke(try f.symbol("dos64_options_required"), 0xa5);
    var bind: [8]u8 = undefined;
    put(&bind, 0, identity);
    put(&bind, 4, main);
    for (bind, 0..) |v, i| f.poke(0xc108 + @as(u16, @intCast(i)), v);
    return f;
}
fn seed(f: *F, b: []const u8) void {
    for (b, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x3ff500 + @as(u32, @intCast(i)), v);
}
fn check(f: *F, carry: u8, mode: u8) !void {
    const r = try f.call("dos64_options_validate", 100_000);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(mode, f.peek(try f.symbol("dos64_bios_initial_mode")));
    const ranges = [_][2]u16{ .{ 0, 2 }, .{ 0x100, 0x100 }, .{ try f.symbol("dos64_segment"), 7 }, .{ try f.symbol("reu_host_end"), 4 }, .{ try f.symbol("dos64_reu_request"), 10 }, .{ try f.symbol("dos64_reu_first_status"), 1 }, .{ 0x4000, 4 }, .{ 0xc400, 32 }, .{ try f.symbol("dos64_bios_initial_mode"), 1 }, .{ 0xdf00, 11 } };
    for (0..65536) |i| {
        const at: @TypeOf(r.pc) = @intCast(i);
        if (c.dos64_was_written(f.machine, at) == 0) continue;
        var owned = false;
        for (ranges) |a| {
            if (at >= a[0] and @as(u32, at) < @as(u32, a[0]) + a[1]) {
                owned = true;
                break;
            }
        }
        try std.testing.expect(owned);
    }
}
test "options realconsumer accepts40/80 and zeroCFGidentity then consumes once" {
    for ([_]u8{ 40, 80 }) |columns| for ([_]u32{ 0, 0x2144df1c }) |identity| {
        var f = try init(identity, 0x8711c155);
        defer f.deinit();
        seed(&f, &record(columns, identity, 0x8711c155));
        try check(&f, 0, if (columns == 40) 1 else 3);
        try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x3ff505));
        try check(&f, 1, 3);
    };
}
test "legacy optionszero ignores staleREU and restores default without DMA" {
    var f = try init(0, 0);
    defer f.deinit();
    seed(&f, &record(40, 0, 0));
    f.poke(try f.symbol("dos64_options_required"), 0);
    f.poke(try f.symbol("dos64_loader_required"), 0);
    f.poke(try f.symbol("dos64_bios_initial_mode"), 1);
    try check(&f, 0, 3);
    try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u8, 0xa5), c.dos64_reu_peek(f.machine, 0x3ff505));
}
test "options rejects malformedrequired and missingcurrentD64R authority before DMA" {
    var f = try init(0, 0);
    defer f.deinit();
    for ([_]u8{ 1, 0xff }) |flag| {
        f.poke(try f.symbol("dos64_options_required"), flag);
        try check(&f, 1, 3);
    }
    f.poke(try f.symbol("dos64_options_required"), 0xa5);
    f.poke(try f.symbol("dos64_loader_required"), 0);
    try check(&f, 1, 3);
    try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
}
test "options everyrecordbyte corruption and resignedbadfields cannot publish" {
    for (0..32) |offset| {
        var f = try init(17, 29);
        defer f.deinit();
        var b = record(40, 17, 29);
        b[offset] ^= 1;
        seed(&f, &b);
        try check(&f, 1, 3);
    }
    for ([_]usize{ 4, 5, 6, 7, 8, 12, 16, 17, 27 }) |offset| {
        var f = try init(17, 29);
        defer f.deinit();
        var b = record(40, 17, 29);
        b[offset] ^= 1;
        put(&b, 28, crc(b[0..28]));
        seed(&f, &b);
        try check(&f, 1, 3);
    }
}
test "options staleCPU scratch cannot authorize suppressedorpartial FETCH" {
    for ([_]u32{ 0, 4, 16, 31 }) |prefix| {
        var f = try init(17, 29);
        defer f.deinit();
        const stale = record(40, 17, 29);
        for (stale, 0..) |v, i| f.poke(0xc400 + @as(u16, @intCast(i)), v);
        seed(&f, &record(80, 18, 29));
        c.dos64_reu_silent_after(f.machine, 0, prefix);
        try check(&f, 1, 3);
    }
}
test "options consumption suppression fails independentreadback and preserves default" {
    for ([_]u64{ 1, 2 }) |skip| {
        var f = try init(17, 29);
        defer f.deinit();
        seed(&f, &record(40, 17, 29));
        c.dos64_reu_silent_after(f.machine, skip, 0);
        try check(&f, 1, 3);
    }
}

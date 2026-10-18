const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn word(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address +% 1, @truncate(value >> 8));
}
fn reg(f: *Fixture, index: u16, value: u16) !void {
    word(f, (try f.symbol("dos64_guest")) + index * 2, value);
}
fn get(f: *Fixture, index: u16) !u16 {
    return f.word((try f.symbol("dos64_guest")) + index * 2);
}
fn physical(segment: u16, offset: u16) u32 {
    return (@as(u32, segment) * 16 + offset) & 0xfffff;
}
fn bytes(f: *Fixture, segment: u16, offset: u16, data: []const u8) void {
    for (data, 0..) |value, i| c.dos64_reu_poke(f.machine, physical(segment, offset +% @as(u16, @intCast(i))), value);
}
fn init(op: u8, wide: bool, repeat: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 32);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    _ = try f.call("dos64_cpu_init", 10_000);
    // BX/BL operand, IVT0 to 0000:0400, owned stack at 2000:0800.
    const opcode: u8 = if (wide) 0xf7 else 0xf6;
    if (repeat != 0) bytes(&f, 0x1000, 0x100, &.{ repeat, opcode, 0xc3 | (op << 3), 0x55, 0xaa }) else bytes(&f, 0x1000, 0x100, &.{ opcode, 0xc3 | (op << 3), 0x55, 0xaa });
    bytes(&f, 0, 0, &.{ 0, 4, 0, 0 });
    return f;
}
fn execute(f: *Fixture, ax: u16, dx: u16, operand: u16, flags: u16) !void {
    try reg(f, 0, ax);
    try reg(f, 2, dx);
    try reg(f, 3, operand);
    try reg(f, 4, 0x800);
    try reg(f, 10, 0x2000);
    try reg(f, 9, 0x1000);
    try reg(f, 12, 0x100);
    try reg(f, 13, flags);
    word(f, try f.symbol("dos64_cpu_instructions"), 0);
    const r = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn memoryWord(f: *Fixture, seg: u16, off: u16) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, physical(seg, off))) | (@as(u16, c.dos64_reu_peek(f.machine, physical(seg, off +% 1))) << 8);
}
fn compareFlags(a: u16, b: u16, wide: bool, initial: u16) u16 {
    const mask: u32 = if (wide) 0xffff else 0xff;
    const sign: u32 = if (wide) 0x8000 else 0x80;
    const lhs: u32 = @as(u32, a) & mask;
    const rhs: u32 = @as(u32, b) & mask;
    const r = (lhs -% rhs) & mask;
    var flags = initial & ~@as(u16, 0x8d5);
    if (lhs < rhs) flags |= 1;
    if ((@popCount(@as(u8, @truncate(r))) & 1) == 0) flags |= 4;
    if (((lhs ^ rhs ^ r) & 0x10) != 0) flags |= 0x10;
    if (r == 0) flags |= 0x40;
    if ((r & sign) != 0) flags |= 0x80;
    if (((lhs ^ rhs) & (lhs ^ r) & sign) != 0) flags |= 0x800;
    return flags;
}
fn signed(value: u16, wide: bool) i64 {
    return if (wide) @as(i16, @bitCast(value)) else @as(i8, @bitCast(@as(u8, @truncate(value))));
}
fn seedNext(seed: *u32) u16 {
    seed.* = seed.* *% 1664525 +% 1013904223;
    return @truncate(seed.* >> 8);
}

test "math NOT NEG all bytes and seeded words preserve unrelated state and flags" {
    for ([_]u8{ 2, 3 }) |op| for ([_]bool{ false, true }) |wide| {
        var f = try init(op, wide, 0);
        defer f.deinit();
        var seed: u32 = 0x8088c64;
        for (0..512) |i| {
            const input: u16 = if (i < 256) @intCast(i) else seedNext(&seed);
            try execute(&f, 0x1234, 0x5678, input, 0xfed7);
            const value: u16 = if (op == 2) ~input else 0 -% input;
            const expected: u16 = if (wide) value else (input & 0xff00) | (value & 0xff);
            try std.testing.expectEqual(expected, try get(&f, 3));
            try std.testing.expectEqual(@as(u16, 0x1234), try get(&f, 0));
            try std.testing.expectEqual(@as(u16, 0x5678), try get(&f, 2));
            try std.testing.expectEqual(if (op == 2) @as(u16, 0xfed7) else compareFlags(0, input, wide, 0xfed7), try get(&f, 13));
        }
    };
}

test "MUL IMUL match independent double width integer oracle including REP products" {
    for ([_]u8{ 4, 5 }) |op| for ([_]bool{ false, true }) |wide| for ([_]u8{ 0, 0xf2, 0xf3 }) |repeat| {
        var f = try init(op, wide, repeat);
        defer f.deinit();
        var seed: u32 = 0xc648088;
        for (0..192) |i| {
            const edge = [_]u16{ 0, 1, 0x7f, 0x80, 0xff, 0x7fff, 0x8000, 0xffff };
            const a = if (i < 64) edge[i / 8] else seedNext(&seed);
            const b = if (i < 64) edge[i % 8] else seedNext(&seed);
            var product: i64 = if (op == 5) signed(a, wide) * signed(b, wide) else @as(i64, if (wide) a else a & 0xff) * @as(i64, if (wide) b else b & 0xff);
            if (repeat != 0) product = -product;
            const raw: u32 = @truncate(@as(u64, @bitCast(product)));
            try execute(&f, a, 0x5678, b, 0xfed7);
            try std.testing.expectEqual(@as(u16, @truncate(raw)), try get(&f, 0));
            try std.testing.expectEqual(if (wide) @as(u16, @truncate(raw >> 16)) else @as(u16, 0x5678), try get(&f, 2));
            const minimum: i64 = if (wide) -32768 else -128;
            const maximum: i64 = if (wide) 32767 else 127;
            const overflow = if (op == 5) product < minimum or product > maximum else if (wide) (raw >> 16) != 0 else ((raw >> 8) & 0xff) != 0;
            const flags = try get(&f, 13);
            try std.testing.expectEqual(@as(u16, if (overflow) 0x801 else 0), flags & 0x801);
            try std.testing.expectEqual(@as(u16, 0xf600), flags & 0xf700);
            try std.testing.expectEqual(@as(u16, 0x1000), try get(&f, 9));
        }
    };
}

test "DIV IDIV quotient remainder and original overflow route through guest INT0" {
    for ([_]u8{ 6, 7 }) |op| for ([_]bool{ false, true }) |wide| for ([_]u8{ 0, 0xf2, 0xf3 }) |repeat| {
        var f = try init(op, wide, repeat);
        defer f.deinit();
        var seed: u32 = 0xd108088;
        for (0..192) |i| {
            const dividends = [_]u32{ 0, 1, 127, 128, 255, 256, 32767, 32768, 65535, 65536, 0x7fffffff, 0x80000000, 0xffffffff, 0xffff8000, 0x0000ff80, 0xffffff80 };
            const divisors = [_]u16{ 0, 1, 2, 0xffff, 0x8000, 0xff, 0x80, 0x7fff };
            const raw: u32 = if (i < 128) dividends[i / 8] else (@as(u32, seedNext(&seed)) << 16) | seedNext(&seed);
            const divisor: u16 = if (i < 128) divisors[i % 8] else seedNext(&seed);
            const dividend: i64 = if (op == 7) (if (wide) @as(i32, @bitCast(raw)) else @as(i16, @bitCast(@as(u16, @truncate(raw))))) else (if (wide) @as(i64, raw) else @as(i64, raw & 0xffff));
            const d: i64 = if (op == 7) signed(divisor, wide) else if (wide) @as(i64, divisor) else @as(i64, divisor & 0xff);
            var quotient: i64 = if (d != 0) @divTrunc(dividend, d) else 0;
            const remainder: i64 = if (d != 0) @rem(dividend, d) else 0;
            const limit: i64 = if (wide) (if (op == 7) 32767 else 65535) else (if (op == 7) 127 else 255);
            const fault = d == 0 or (if (op == 7) quotient < -limit or quotient > limit else quotient > limit);
            if (op == 7 and repeat != 0) quotient = -quotient;
            const ax: u16 = @truncate(raw);
            const dx: u16 = @truncate(raw >> 16);
            try execute(&f, ax, dx, divisor, 0xfed7);
            if (fault) {
                try std.testing.expectEqual(@as(u16, 0), try get(&f, 9));
                try std.testing.expectEqual(@as(u16, 0x400), try get(&f, 12));
                try std.testing.expectEqual(@as(u16, 0x7fa), try get(&f, 4));
                try std.testing.expectEqual(ax, try get(&f, 0));
                try std.testing.expectEqual(dx, try get(&f, 2));
                try flush(&f);
                try std.testing.expectEqual(@as(u16, if (repeat != 0) 0x103 else 0x102), memoryWord(&f, 0x2000, 0x7fa));
                try std.testing.expectEqual(@as(u16, 0x1000), memoryWord(&f, 0x2000, 0x7fc));
            } else {
                const q: u16 = @truncate(@as(u64, @bitCast(quotient)));
                const r: u16 = @truncate(@as(u64, @bitCast(remainder)));
                try std.testing.expectEqual(if (wide) q else (q & 0xff) | ((r & 0xff) << 8), try get(&f, 0));
                try std.testing.expectEqual(if (wide) r else dx, try get(&f, 2));
                try std.testing.expectEqual(@as(u16, 0x1000), try get(&f, 9));
                try std.testing.expectEqual(@as(u16, 0x800), try get(&f, 4));
            }
        }
    };
}

test "group TEST alias byte and word use immediate without writing operand" {
    for ([_]u8{ 0, 1 }) |op| for ([_]bool{ false, true }) |wide| {
        var f = try init(op, wide, 0);
        defer f.deinit();
        try execute(&f, 0x1234, 0x5678, 0x0355, 0xfed7);
        try std.testing.expectEqual(@as(u16, 0x0355), try get(&f, 3));
        const result: u16 = 0x0355 & (if (wide) @as(u16, 0xaa55) else @as(u16, 0x55));
        var expected: u16 = 0xf602;
        if ((@popCount(@as(u8, @truncate(result))) & 1) == 0) expected |= 4;
        if (result == 0) expected |= 0x40;
        if ((result & (if (wide) @as(u16, 0x8000) else @as(u16, 0x80))) != 0) expected |= 0x80;
        try std.testing.expectEqual(expected, try get(&f, 13));
        try std.testing.expectEqual(@as(u16, if (wide) 0x104 else 0x103), try get(&f, 12));
    };
}

test "NEG high byte register and wrapped memory operands execute actual writeback" {
    var high = try init(3, false, 0);
    defer high.deinit();
    bytes(&high, 0x1000, 0x100, &.{ 0xf6, 0xdf }); // NEG BH
    try execute(&high, 0x1234, 0x5678, 0x80ab, 0xf002);
    try std.testing.expectEqual(@as(u16, 0x80ab), try get(&high, 3));
    try std.testing.expectEqual(compareFlags(0, 0x80, false, 0xf002), try get(&high, 13));
    var memory = try init(3, true, 0);
    defer memory.deinit();
    bytes(&memory, 0x1000, 0x100, &.{ 0xf7, 0x1e, 0xff, 0xff }); // NEG word DS:FFFF
    try reg(&memory, 11, 0x1234);
    bytes(&memory, 0x1234, 0xffff, &.{ 1, 0x80 });
    try execute(&memory, 0x1234, 0x5678, 0, 0xf002);
    try flush(&memory);
    try std.testing.expectEqual(@as(u16, 0x7fff), memoryWord(&memory, 0x1234, 0xffff));
    try std.testing.expectEqual(compareFlags(0, 0x8001, true, 0xf002), try get(&memory, 13));
}

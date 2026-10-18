// Target: original8088, not later x86 adjustment pseudocode. Primary hardware
// source: SingleStepTests/8088 pin aea84484abc79d09639d855b7b0ab32bc9e4dbeb,
// v2/{27,2F,37,3F,D4,D5,D6,D7}.json.gz and v2/metadata.json. Parent corpus
// importer owns durable fixture integration; isolated source execution evidence
// is retained under agentworking/scratch/adjust/. Undefined flag bits are
// explicitly retained by this implementation except the hardware-observed
// AAM0 error state. REP tests are microcode-derived, not hardware-corpus claims.
const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn word(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address +% 1, @truncate(value >> 8));
}
fn reg(f: *Fixture, index: u16, value: u16) !void { word(f, (try f.symbol("dos64_guest")) + index * 2, value); }
fn get(f: *Fixture, index: u16) !u16 { return f.word((try f.symbol("dos64_guest")) + index * 2); }
fn physical(seg: u16, off: u16) u32 { return (@as(u32, seg) * 16 + off) & 0xfffff; }
fn bytes(f: *Fixture, seg: u16, off: u16, data: []const u8) void {
    for (data, 0..) |value, i| c.dos64_reu_poke(f.machine, physical(seg, off +% @as(u16, @intCast(i))), value);
}
fn init(op: u8, base: u8, prefix: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 2);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    _ = try f.call("dos64_cpu_init", 10_000);
    if (prefix == 0) bytes(&f, 0x1000, 0x100, &.{ op, base }) else bytes(&f, 0x1000, 0x100, &.{ prefix, op, base });
    return f;
}
fn execute(f: *Fixture, ax: u16, flags: u16) !void {
    try reg(f, 0, ax);
    try reg(f, 9, 0x1000);
    try reg(f, 12, 0x100);
    try reg(f, 13, flags);
    const before = f.word(try f.symbol("dos64_cpu_instructions"));
    const r = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xfe, r.p & 0xfe);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_cpu_status")));
    try std.testing.expectEqual(before +% 1, f.word(try f.symbol("dos64_cpu_instructions")));
}
fn szp(al: u8) u16 {
    return (if ((@popCount(al) & 1) == 0) @as(u16, 4) else 0) |
        (if (al == 0) @as(u16, 0x40) else 0) | (al & 0x80);
}
const Answer = struct { ax: u16, flags: u16 };
fn decimal(op: u8, ax: u16, flags: u16) Answer {
    const old: u8 = @truncate(ax);
    const low_adjust = (old & 15) >= 10 or (flags & 16) != 0;
    // Independent correction-factor oracle for original8088 silicon, verified
    // against all10,000 pinned SST rows per opcode. Incoming AF changes the
    // high-digit threshold; DAS low-nibble borrow alone never sets CF.
    const high_adjust = (flags & 1) != 0 or old > (if ((flags & 16) != 0) @as(u8, 0x9f) else 0x99);
    const correction: u8 = (if (low_adjust) @as(u8, 6) else 0) + (if (high_adjust) @as(u8, 0x60) else 0);
    const result: u8 = if (op == 0x27) old +% correction else old -% correction;
    return .{ .ax = (ax & 0xff00) | result, .flags = (flags & ~@as(u16, 0xd5)) | szp(result) |
        (if (low_adjust) @as(u16, 16) else 0) | (if (high_adjust) @as(u16, 1) else 0) };
}

test "8088 DAA DAS exhaust AL and AF CF including AF-sensitive 9A..9F and DAS borrow" {
    for ([_]u8{ 0x27, 0x2f }) |op| {
        var f = try init(op, 0, 0);
        defer f.deinit();
        for (0..256) |al| for (0..4) |bits| {
            const flags: u16 = 0xfeca | @as(u16, @intCast(bits & 1)) | @as(u16, @intCast((bits & 2) << 3));
            const ax: u16 = 0x9b00 | @as(u16, @intCast(al));
            try execute(&f, ax, flags);
            const expected = decimal(op, ax, flags);
            try std.testing.expectEqual(expected.ax, try get(&f, 0));
            try std.testing.expectEqual(expected.flags, try get(&f, 13));
            try std.testing.expectEqual(@as(u16, 0x101), try get(&f, 12));
        };
    }
}

test "8088 AAA AAS independent AL and AH byte corrections and every low input" {
    for ([_]u8{ 0x37, 0x3f }) |op| {
        var f = try init(op, 0, 0);
        defer f.deinit();
        for ([_]u16{ 0, 1, 0x7f, 0x80, 0xff }) |ah| for (0..256) |al| for (0..2) |af| {
            const ax: u16 = (ah << 8) | @as(u16, @intCast(al));
            const flags: u16 = 0xfecf | @as(u16, @intCast(af << 4));
            const correction = (al & 15) > 9 or af != 0;
            const lo: u8 = @intCast(al);
            const result: u8 = if (!correction) lo else if (op == 0x37) lo +% 6 else lo -% 6;
            const high: u16 = if (!correction) ah else if (op == 0x37) (ah +% 1) & 255 else (ah -% 1) & 255;
            try execute(&f, ax, flags);
            try std.testing.expectEqual((high << 8) | (result & 15), try get(&f, 0));
            try std.testing.expectEqual((flags & ~@as(u16, 0x11)) | (if (correction) @as(u16, 0x11) else 0), try get(&f, 13));
        };
    }
}

test "AAM all byte dividends and bases including nondecimal quotient remainder" {
    // Exhaust both dimensions without changing backing memory beneath a live
    // cache: every base gets its own fixture and immutable code bytes.
    for (1..256) |base| {
        var f = try init(0xd4, @intCast(base), 0);
        defer f.deinit();
        for (0..256) |al| {
            try execute(&f, 0x8b00 | @as(u16, @intCast(al)), 0xfed7);
            const result: u16 = @intCast(((al / base) << 8) | (al % base));
            try std.testing.expectEqual(result, try get(&f, 0));
            try std.testing.expectEqual((@as(u16, 0xfed7) & ~@as(u16, 0xc4)) | szp(@truncate(result)), try get(&f, 13));
            try std.testing.expectEqual(@as(u16, 0x102), try get(&f, 12));
        }
    }
}

test "AAD all bases and seeded full AX modulo arithmetic including base zero" {
    var seed: u32 = 0x8088aad;
    for (0..256) |base| {
        var f = try init(0xd5, @intCast(base), 0);
        defer f.deinit();
        for (0..32) |i| {
            seed = seed *% 1664525 +% 1013904223;
            const edges = [_]u16{ 0, 1, 0xff, 0x100, 0x7fff, 0x8000, 0xff00, 0xffff };
            const ax = if (i < edges.len) edges[i] else @as(u16, @truncate(seed >> 8));
            const result: u8 = @truncate((@as(u32, ax >> 8) * @as(u32, @intCast(base))) + (ax & 255));
            try execute(&f, ax, 0xfed7);
            try std.testing.expectEqual(@as(u16, result), try get(&f, 0));
            try std.testing.expectEqual((@as(u16, 0xfed7) & ~@as(u16, 0xc4)) | szp(result), try get(&f, 13));
        }
    }
}

test "AAM zero enters original divide-error frame with following IP and unchanged AX" {
    for ([_]u8{ 0, 0xf2, 0xf3 }) |prefix| {
        var f = try init(0xd4, 0, prefix);
        defer f.deinit();
        bytes(&f, 0, 0, &.{ 0x34, 0x12, 0x78, 0x56 });
        try reg(&f, 4, 0x800);
        try reg(&f, 10, 0x2000);
        try execute(&f, 0xcafe, 0xfed7);
        try std.testing.expectEqual(@as(u16, 0xcafe), try get(&f, 0));
        try std.testing.expectEqual(@as(u16, 0x5678), try get(&f, 9));
        try std.testing.expectEqual(@as(u16, 0x1234), try get(&f, 12));
        try std.testing.expectEqual(@as(u16, 0x7fa), try get(&f, 4));
        try std.testing.expectEqual(@as(u16, 0xf446), try get(&f, 13));
        _ = try f.call("dos64_cache_flush", 100_000);
        const lo = c.dos64_reu_peek(f.machine, 0x207fa);
        const hi = c.dos64_reu_peek(f.machine, 0x207fb);
        try std.testing.expectEqual(@as(u16, if (prefix == 0) 0x102 else 0x103), @as(u16, lo) | (@as(u16, hi) << 8));
        try std.testing.expectEqual(@as(u8, 0x46), c.dos64_reu_peek(f.machine, 0x207fe));
        try std.testing.expectEqual(@as(u8, 0xf6), c.dos64_reu_peek(f.machine, 0x207ff));
    }
}

test "REP AAM AAD ignores repeat without negating the result and SALC preserves flags" {
    // REP behavior is microcode-derived, not directly covered by the pinned
    // SST sources for these opcodes. Control registers and CX remain unchanged.
    for ([_]u8{ 0xf2, 0xf3 }) |prefix| for ([_]u8{ 0xd4, 0xd5, 0xd6 }) |op| {
        var f = try init(op, 10, prefix);
        defer f.deinit();
        try reg(&f, 1, 0x1984);
        try execute(&f, 0x0563, 0xfed7);
        try std.testing.expectEqual(@as(u16, if (op == 0xd4) 0x0909 else if (op == 0xd5) 149 else 0x05ff), try get(&f, 0));
        try std.testing.expectEqual(@as(u16, 0x1984), try get(&f, 1));
        if (op == 0xd6) try std.testing.expectEqual(@as(u16, 0xfed7), try get(&f, 13));
    };
    var f = try init(0xd6, 0, 0);
    defer f.deinit();
    for (0..256) |flags_low| {
        const flags = 0xfe00 | @as(u16, @intCast(flags_low));
        try execute(&f, 0xab42, flags);
        try std.testing.expectEqual(@as(u16, if ((flags & 1) != 0) 0xabff else 0xab00), try get(&f, 0));
        try std.testing.expectEqual(flags, try get(&f, 13));
    }
}

test "XLAT segment overrides offset wrap physical wrap and memory holes" {
    for ([_]u8{ 0, 0x26, 0x2e, 0x36, 0x3e }) |prefix| {
        var f = try init(0xd7, 0, prefix);
        defer f.deinit();
        try reg(&f, 3, 0xfff0);
        try reg(&f, 8, 0x2000);
        try reg(&f, 10, 0x3000);
        try reg(&f, 11, 0xffff);
        const seg: u16 = switch (prefix) { 0x26 => 0x2000, 0x2e => 0x1000, 0x36 => 0x3000, else => 0xffff };
        c.dos64_reu_poke(f.machine, physical(seg, 0x20), 0xa7);
        try execute(&f, 0x5830, 0xfed7);
        try std.testing.expectEqual(@as(u16, 0x58a7), try get(&f, 0));
        try std.testing.expectEqual(@as(u16, 0xfed7), try get(&f, 13));
    }
    var f = try init(0xd7, 0, 0);
    defer f.deinit();
    try reg(&f, 11, 0xa000);
    f.poke(try f.symbol("dos64_memory_mode"), 0);
    try execute(&f, 0x5800, 0xfed7);
    try std.testing.expectEqual(@as(u16, 0x58ff), try get(&f, 0));
}

test "XLAT reads dirty coherent source and preserves every unrelated guest register" {
    var f = try init(0xd7, 0, 0);
    defer f.deinit();
    for (1..12) |i| {
        if (i == 9) continue;
        try reg(&f, @intCast(i), @intCast(0x1300 + i * 0x111));
    }
    try reg(&f, 3, 0x1fe);
    try reg(&f, 11, 0x2000);
    const seg = try f.symbol("dos64_segment");
    const off = try f.symbol("dos64_offset");
    word(&f, seg, 0x2000);
    word(&f, off, 0x21e);
    _ = try f.call("dos64_physical", 1000);
    f.poke(try f.symbol("dos64_mem_value"), 0xc9);
    const wr = try f.call("dos64_mem_write", 50_000);
    try std.testing.expectEqual(@as(u8, 0), wr.p & 1);
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x2021e));
    var previous: [12]u16 = undefined;
    for (0..12) |i| previous[i] = try get(&f, @intCast(i));
    try execute(&f, 0x6720, 0xfed7);
    try std.testing.expectEqual(@as(u16, 0x67c9), try get(&f, 0));
    for (1..12) |i| {
        if (i == 9) continue;
        try std.testing.expectEqual(previous[i], try get(&f, @intCast(i)));
    }
    try std.testing.expectEqual(@as(u16, 0xfed7), try get(&f, 13));
}

test "XLAT operand DMA error and AAM immediate DMA error preserve AX and roll back IP" {
    {
        var f = try init(0xd7, 0, 0);
        defer f.deinit();
        try reg(&f, 0, 0xab20);
        try reg(&f, 3, 0);
        try reg(&f, 11, 0x2000);
        try reg(&f, 9, 0x1000);
        try reg(&f, 12, 0x100);
        c.dos64_reu_fail_after(f.machine, 1, 17);
        const r = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 3), f.peek(try f.symbol("dos64_cpu_status")));
        try std.testing.expectEqual(@as(u16, 0xab20), try get(&f, 0));
        try std.testing.expectEqual(@as(u16, 0x100), try get(&f, 12));
    }
    {
        var f = try init(0xd4, 10, 0);
        defer f.deinit();
        bytes(&f, 0x1000, 0x1ff, &.{ 0xd4, 10 });
        try reg(&f, 0, 0xab20);
        try reg(&f, 9, 0x1000);
        try reg(&f, 12, 0x1ff);
        c.dos64_reu_fail_after(f.machine, 1, 17);
        const r = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 3), f.peek(try f.symbol("dos64_cpu_status")));
        try std.testing.expectEqual(@as(u16, 0xab20), try get(&f, 0));
        try std.testing.expectEqual(@as(u16, 0x1ff), try get(&f, 12));
    }
}


test "adjust instructions restore host decimal and interrupt flags through CPU completion" {
    for ([_]u8{ 0x24, 0x2c, 0xa4, 0xac }) |native_flags| for ([_]u8{ 0x27, 0x2f, 0x37, 0x3f, 0xd4, 0xd5, 0xd6, 0xd7 }) |op| {
        var f = try init(op, 10, 0);
        defer f.deinit();
        f.initial_status = native_flags;
        try reg(&f, 3, 0);
        try reg(&f, 11, 0x2000);
        c.dos64_reu_poke(f.machine, 0x20063, 0x29);
        try execute(&f, 0x0563, 0xfed7);
    };
}

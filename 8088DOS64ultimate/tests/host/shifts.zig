const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
fn word(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address + 1, @truncate(value >> 8));
}
fn init(frames: u8, bytes: []const u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    _ = try f.call("dos64_cpu_init", 10_000);
    word(&f, (try f.symbol("dos64_guest")) + 18, 0);
    for (bytes, 0..) |value, i| c.dos64_reu_poke(f.machine, 0x100 + @as(u32, @intCast(i)), value);
    return f;
}
fn step(f: *Fixture) !void {
    const result = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
}
fn rotate(value: u32, bits: u5, count: u8, left: bool) u32 {
    const n: u5 = @intCast(count % bits);
    const mask = (@as(u32, 1) << bits) - 1;
    if (n == 0) return value;
    return (if (left) (value << n) | (value >> (bits - n)) else (value >> n) | (value << (bits - n))) & mask;
}

// Closed-form integer/ring oracle, separate from the target's repeated-bit
// implementation. Original 8088 counts are not masked to five bits.
fn oracle(op: u8, width: u8, value: u16, count: u8, initial: u16) struct { value: u16, flags: u16, mask: u16 } {
    if (count == 0) return .{ .value = value, .flags = initial, .mask = 0xffff };
    const bits: u5 = if (width == 0) 8 else 16;
    const mask = (@as(u32, 1) << bits) - 1;
    const sign = @as(u32, 1) << (bits - 1);
    const old: u32 = @as(u32, value) & mask;
    var result: u32 = 0;
    var carry: u32 = 0;
    var overflow: u32 = 0;
    switch (op) {
        0, 1 => {
            result = rotate(old, bits, count, op == 0);
            carry = if (op == 0) result & 1 else (result >> (bits - 1)) & 1;
        },
        2, 3 => {
            const ring = old | (@as(u32, initial & 1) << bits);
            const rotated = rotate(ring, bits + 1, count, op == 2);
            result = rotated & mask;
            carry = (rotated >> bits) & 1;
        },
        4 => {
            result = if (count >= bits) 0 else (old << @as(u5, @intCast(count))) & mask;
            carry = if (count > bits) 0 else (old >> @as(u5, @intCast(bits - count))) & 1;
        },
        5 => {
            result = if (count >= bits) 0 else old >> @as(u5, @intCast(count));
            carry = if (count > bits) 0 else (old >> @as(u5, @intCast(count - 1))) & 1;
            overflow = if (count == 1 and (old & sign) != 0) 1 else 0;
        },
        6 => result = mask,
        7 => {
            const negative = (old & sign) != 0;
            carry = if (count >= bits) @intFromBool(negative) else (old >> @as(u5, @intCast(count - 1))) & 1;
            result = if (count >= bits) (if (negative) mask else 0) else (old >> @as(u5, @intCast(count))) | (if (negative) mask ^ (mask >> @as(u5, @intCast(count))) else 0);
        },
        else => unreachable,
    }
    if (op == 0 or op == 2 or op == 4) overflow = ((result >> (bits - 1)) & 1) ^ carry;
    if (op == 1 or op == 3) overflow = ((result >> (bits - 1)) ^ (result >> (bits - 2))) & 1;
    var flags = (initial & ~@as(u16, 0x0801)) | @as(u16, @intCast(carry | overflow << 11));
    if (op >= 4) {
        flags &= ~@as(u16, 0x00d4);
        if (@popCount(@as(u8, @truncate(result))) % 2 == 0) flags |= 4;
        if (result == 0) flags |= 0x40;
        if ((result & sign) != 0) flags |= 0x80;
    }
    return .{ .value = @intCast(result), .flags = flags, .mask = if (op == 6) 0xf72a else if (op >= 4) 0xffef else 0xffff };
}

test "assembled original 8088 rotate and shift counts match independent ring oracle" {
    const counts = [_]u8{ 0, 1, 8, 9, 16, 17, 31, 32, 255 };
    const edges = [_]u16{ 0, 1, 0x0081, 0x80ff, 0x8001, 0xffff };
    for (0..2) |wide| for (0..8) |operation| {
        const width: u8 = @intCast(wide);
        const op: u8 = @intCast(operation);
        var f = try init(2, &.{ 0xd2 + width, 0xc0 + 8 * op });
        defer f.deinit();
        f.initial_status = 0x28;
        const guest = try f.symbol("dos64_guest");
        for (counts) |count| for (edges) |edge| for (0..2) |cf| {
            const initial: u16 = 0xfad6 | @as(u16, @intCast(cf));
            const value: u16 = if (width == 0) edge & 255 else edge;
            const expected = oracle(op, width, value, count, initial);
            word(&f, guest, if (width == 0) 0xa500 | value else value);
            word(&f, guest + 2, 0x5a00 | @as(u16, count));
            word(&f, guest + 24, 0x100);
            word(&f, guest + 26, initial);
            try step(&f);
            const actual: u16 = if (width == 0) f.word(guest) & 255 else f.word(guest);
            if (actual != expected.value or f.word(guest + 26) & expected.mask != expected.flags & expected.mask) {
                std.debug.print("Shift mismatch op={d} width={d} count={d} value={x} cf={d} result={x}/{x} flags={x}/{x}\n", .{ op, width, count, value, cf, actual, expected.value, f.word(guest + 26), expected.flags });
                return error.ShiftMismatch;
            }
            if (width == 0) try std.testing.expectEqual(@as(u8, 0xa5), f.peek(guest + 1));
            try std.testing.expectEqual(@as(u16, 0x5a00 | @as(u16, count)), f.word(guest + 2));
            try std.testing.expectEqual(@as(u16, 0x102), f.word(guest + 24));
            try std.testing.expectEqual(@as(u8, 8), f.last_regs.?.p & 0x0c);
        };
    };
}

test "one-bit opcodes select high byte and word registers without CL dependency" {
    for (0..2) |wide| for (0..8) |operation| {
        const width: u8 = @intCast(wide);
        const op: u8 = @intCast(operation);
        const reg: u8 = if (width == 0) 4 else 3; // AH or BX.
        var f = try init(1, &.{ 0xd0 + width, 0xc0 + 8 * op + reg });
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest, 0x81a5);
        word(&f, guest + 6, 0x8001);
        word(&f, guest + 2, 0); // D0/D1 must still shift when CL is zero.
        word(&f, guest + 24, 0x100);
        word(&f, guest + 26, 0xfad7);
        const expected = oracle(op, width, if (width == 0) 0x81 else 0x8001, 1, 0xfad7);
        try step(&f);
        try std.testing.expectEqual(expected.value, if (width == 0) @as(u16, f.peek(guest + 1)) else f.word(guest + 6));
        try std.testing.expectEqual(expected.flags & expected.mask, f.word(guest + 26) & expected.mask);
        if (width == 0) try std.testing.expectEqual(@as(u8, 0xa5), f.peek(guest));
    };
}

test "memory shifts preserve zero count and survive eviction and 16-bit word wrapping" {
    for ([_]u8{ 0, 1, 32, 255 }) |count| {
        var f = try init(1, &.{ 0xd3, 0x26, 0xff, 0xff }); // SHL word DS:FFFF,CL.
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest + 22, 0x1000);
        word(&f, guest + 24, 0x100);
        word(&f, guest + 2, count);
        word(&f, guest + 26, 0xfad7);
        c.dos64_reu_poke(f.machine, 0x1ffff, 1);
        c.dos64_reu_poke(f.machine, 0x10000, 0x80);
        c.dos64_reu_poke(f.machine, 0x20000, 0x5a);
        const expected = oracle(4, 1, 0x8001, count, 0xfad7);
        const epoch = try f.symbol("dos64_write_epoch");
        const before = f.word(epoch);
        try step(&f);
        if (count == 0) try std.testing.expectEqual(before, f.word(epoch));
        _ = try f.call("dos64_cache_flush", 100_000);
        try std.testing.expectEqual(@as(u8, @truncate(expected.value)), c.dos64_reu_peek(f.machine, 0x1ffff));
        try std.testing.expectEqual(@as(u8, @truncate(expected.value >> 8)), c.dos64_reu_peek(f.machine, 0x10000));
        try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x20000));
        try std.testing.expectEqual(expected.flags & expected.mask, f.word(guest + 26) & expected.mask);
    }
}

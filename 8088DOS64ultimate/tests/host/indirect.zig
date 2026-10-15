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
    const guest = try f.symbol("dos64_guest");
    word(&f, guest + 18, 0);
    word(&f, guest + 24, 0x100);
    word(&f, guest + 26, 0xfad7);
    for (bytes, 0..) |value, i| c.dos64_reu_poke(f.machine, 0x100 + @as(u32, @intCast(i)), value);
    return f;
}
fn step(f: *Fixture) !void {
    const result = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
}
fn backingWord(f: *Fixture, address: u32) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, address)) | (@as(u16, c.dos64_reu_peek(f.machine, address + 1)) << 8);
}

test "CBW and CWD sign extension preserves all flags and unrelated registers" {
    var f = try init(1, &.{ 0x98, 0x99 });
    defer f.deinit();
    const guest = try f.symbol("dos64_guest");
    f.initial_status = 0x28;
    for (0..256) |low| {
        word(&f, guest, 0x5a00 | @as(u16, @intCast(low)));
        word(&f, guest + 4, 0x1234);
        word(&f, guest + 24, 0x100);
        try step(&f);
        try std.testing.expectEqual(@as(u16, @intCast(low)) | (if (low >= 128) @as(u16, 0xff00) else 0), f.word(guest));
        try std.testing.expectEqual(@as(u16, 0x1234), f.word(guest + 4));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
        try step(&f);
        try std.testing.expectEqual(if (low >= 128) @as(u16, 0xffff) else 0, f.word(guest + 4));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
        try std.testing.expectEqual(@as(u8, 8), f.last_regs.?.p & 0x0c);
    }
    // AX and AL have opposite signs: CWD must test bit15, not bit7.
    for ([_]u16{ 0x0080, 0x7fff, 0x8001, 0xff7f }) |value| {
        word(&f, guest, value);
        word(&f, guest + 4, 0xa55a);
        word(&f, guest + 24, 0x101);
        try step(&f);
        try std.testing.expectEqual(if (value & 0x8000 != 0) @as(u16, 0xffff) else 0, f.word(guest + 4));
        try std.testing.expectEqual(value, f.word(guest));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
    }
}

test "INC DEC r/m preserve carry and match independent edge flag oracle" {
    const values = [_]u16{ 0, 1, 0x000f, 0x0010, 0x007f, 0x0080, 0x00ff, 0x7fff, 0x8000, 0xffff };
    for (0..2) |wide| for (0..2) |decrement| {
        const width: u8 = @intCast(wide);
        var f = try init(1, &.{ 0xfe + width, 0xc0 + @as(u8, @intCast(decrement * 8)) });
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        const mask: u16 = if (width == 0) 0xff else 0xffff;
        const sign: u16 = if (width == 0) 0x80 else 0x8000;
        for (values) |input| for (0..2) |carry| {
            const old = input & mask;
            const expected = (if (decrement == 1) old -% 1 else old +% 1) & mask;
            var flags: u16 = 0xf202 | @as(u16, @intCast(carry));
            if (@popCount(@as(u8, @truncate(expected))) % 2 == 0) flags |= 4;
            if (expected == 0) flags |= 0x40;
            if ((expected & sign) != 0) flags |= 0x80;
            if (if (decrement == 1) old & 15 == 0 else old & 15 == 15) flags |= 0x10;
            if (old == (if (decrement == 1) sign else sign - 1)) flags |= 0x800;
            word(&f, guest, if (width == 0) 0xa500 | old else old);
            word(&f, guest + 24, 0x100);
            word(&f, guest + 26, 0xf202 | @as(u16, @intCast(carry)));
            try step(&f);
            try std.testing.expectEqual(expected, f.word(guest) & mask);
            try std.testing.expectEqual(flags, f.word(guest + 26));
            if (width == 0) try std.testing.expectEqual(@as(u8, 0xa5), f.peek(guest + 1));
        };
    };
}

test "XCHG covers every byte and word register pair including aliases" {
    const offsets = [_]u16{ 0, 2, 4, 6, 1, 3, 5, 7 };
    for (0..2) |wide| {
        const width: u8 = @intCast(wide);
        var f = try init(1, &.{ 0x86 + width, 0xc0 });
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        for (0..8) |reg| for (0..8) |rm| {
            var expected: [16]u8 = undefined;
            for (&expected, 0..) |*value, i| value.* = @intCast(0x20 + i);
            const left: usize = if (width == 0) offsets[reg] else reg * 2;
            const right: usize = if (width == 0) offsets[rm] else rm * 2;
            const before = expected;
            for (0..@as(usize, width + 1)) |i| {
                expected[left + i] = before[right + i];
                expected[right + i] = before[left + i];
            }
            for (before, 0..) |value, i| f.poke(guest + @as(u16, @intCast(i)), value);
            c.dos64_reu_poke(f.machine, 0x101, 0xc0 + @as(u8, @intCast(reg * 8 + rm)));
            _ = try f.call("dos64_cache_init", 50_000);
            word(&f, guest + 24, 0x100);
            try step(&f);
            for (expected, 0..) |value, i| try std.testing.expectEqual(value, f.peek(guest + @as(u16, @intCast(i))));
            try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
        };
    }
}

test "XCHG writes memory using original base register before replacing it" {
    var f = try init(1, &.{ 0x87, 0x1f }); // XCHG [BX],BX.
    defer f.deinit();
    const guest = try f.symbol("dos64_guest");
    word(&f, guest + 6, 0x0400);
    word(&f, guest + 22, 0x1000);
    c.dos64_reu_poke(f.machine, 0x10400, 0xef);
    c.dos64_reu_poke(f.machine, 0x10401, 0xbe);
    c.dos64_reu_poke(f.machine, 0x1beef, 0x5a);
    try step(&f);
    _ = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u16, 0xbeef), f.word(guest + 6));
    try std.testing.expectEqual(@as(u16, 0x0400), backingWord(&f, 0x10400));
    try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x1beef));
    try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
}

test "TEST accumulator immediate updates only defined AND flags" {
    for (0..2) |wide| {
        const width: u8 = @intCast(wide);
        var f = try init(1, if (width == 0) &.{ 0xa8, 0x81 } else &.{ 0xa9, 0x01, 0x80 });
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        for ([_]u16{ 0, 1, 0x0080, 0x0081, 0x8000, 0x8001, 0xffff }) |value| {
            const result = value & (if (width == 0) @as(u16, 0x81) else 0x8001);
            var flags: u16 = 0xf202;
            if (@popCount(@as(u8, @truncate(result))) % 2 == 0) flags |= 4;
            if (result == 0) flags |= 0x40;
            if (result & (if (width == 0) @as(u16, 0x80) else 0x8000) != 0) flags |= 0x80;
            word(&f, guest, value);
            word(&f, guest + 24, 0x100);
            word(&f, guest + 26, 0xfaD7);
            try step(&f);
            try std.testing.expectEqual(value, f.word(guest));
            try std.testing.expectEqual(flags, f.word(guest + 26) & 0xffef);
            try std.testing.expectEqual(0x102 + @as(u16, width), f.word(guest + 24));
        }
    }
}

test "indirect PUSH SP alias uses decremented SP and POP SP overwrites its increment" {
    for ([_]u8{ 0xf4, 0xfc }) |modrm| {
        var f = try init(1, &.{ 0xff, modrm, 0x8f, 0xc4 }); // FF /6 or /7 PUSH SP; POP SP.
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest + 8, 0);
        word(&f, guest + 20, 0x1000);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xfffe), f.word(guest + 8));
        _ = try f.call("dos64_cache_flush", 100_000);
        try std.testing.expectEqual(@as(u16, 0xfffe), backingWord(&f, 0x1fffe));
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xfffe), f.word(guest + 8));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
    }
}

test "indirect near CALL captures memory target before overlapping return push" {
    var f = try init(1, &.{ 0xff, 0x16, 0, 2 }); // CALL word DS:0200.
    defer f.deinit();
    const guest = try f.symbol("dos64_guest");
    word(&f, guest + 8, 0x202);
    word(&f, guest + 20, 0x1000);
    word(&f, guest + 22, 0x1000);
    c.dos64_reu_poke(f.machine, 0x10200, 0x10);
    c.dos64_reu_poke(f.machine, 0x10201, 0x32);
    c.dos64_reu_poke(f.machine, 0x3210, 0xc3);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x3210), f.word(guest + 24));
    try std.testing.expectEqual(@as(u16, 0x200), f.word(guest + 8));
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x104), f.word(guest + 24));
    try std.testing.expectEqual(@as(u16, 0x202), f.word(guest + 8));
    try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
}

test "near indirect register CALL captures original SP and JMP leaves stack unchanged" {
    for ([_]u8{ 0xd4, 0xe4 }) |modrm| {
        var f = try init(1, &.{ 0xff, modrm }); // CALL SP or JMP SP.
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest + 8, 0x200);
        word(&f, guest + 20, 0x1000);
        c.dos64_reu_poke(f.machine, 0x200, 0xc3);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x200), f.word(guest + 24));
        try std.testing.expectEqual(@as(u16, if (modrm == 0xd4) 0x1fe else 0x200), f.word(guest + 8));
        if (modrm == 0xd4) {
            try step(&f);
            try std.testing.expectEqual(@as(u16, 0x102), f.word(guest + 24));
            try std.testing.expectEqual(@as(u16, 0x200), f.word(guest + 8));
        }
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
    }
}

test "POP memory retains decoded SS address across stack read and eviction" {
    var f = try init(1, &.{ 0x8f, 0x46, 0 }); // POP word SS:[BP+0].
    defer f.deinit();
    const guest = try f.symbol("dos64_guest");
    word(&f, guest + 8, 0x200);
    word(&f, guest + 10, 0xffff);
    word(&f, guest + 20, 0x1000);
    c.dos64_reu_poke(f.machine, 0x10200, 0x34);
    c.dos64_reu_poke(f.machine, 0x10201, 0x12);
    c.dos64_reu_poke(f.machine, 0x20000, 0x5a);
    try step(&f);
    _ = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0x34), c.dos64_reu_peek(f.machine, 0x1ffff));
    try std.testing.expectEqual(@as(u8, 0x12), c.dos64_reu_peek(f.machine, 0x10000));
    try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x20000));
    try std.testing.expectEqual(@as(u16, 0x202), f.word(guest + 8));
    try std.testing.expectEqual(@as(u16, 0xffff), f.word(guest + 10));
    try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
}

test "far indirect pointers wrap and are read before overlapping call stack writes" {
    for ([_]u8{ 0x1e, 0x2e }) |modrm| {
        var f = try init(1, &.{ 0xff, modrm, 0xff, 0xff });
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest + 8, 2);
        word(&f, guest + 20, 0x1000);
        word(&f, guest + 22, 0x1000);
        c.dos64_reu_poke(f.machine, 0x1ffff, 0xef);
        c.dos64_reu_poke(f.machine, 0x10000, 0xbe);
        c.dos64_reu_poke(f.machine, 0x10001, 0x45);
        c.dos64_reu_poke(f.machine, 0x10002, 0x23);
        c.dos64_reu_poke(f.machine, 0x20000, 0x5a);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xbeef), f.word(guest + 24));
        try std.testing.expectEqual(@as(u16, 0x2345), f.word(guest + 18));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
        _ = try f.call("dos64_cache_flush", 100_000);
        if (modrm == 0x1e) {
            try std.testing.expectEqual(@as(u16, 0xfffe), f.word(guest + 8));
            try std.testing.expectEqual(@as(u16, 0x104), backingWord(&f, 0x1fffe));
            try std.testing.expectEqual(@as(u16, 0), backingWord(&f, 0x10000));
        } else try std.testing.expectEqual(@as(u16, 2), f.word(guest + 8));
        try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x20000));
    }
}

test "undefined far register and unaudited byte control forms diagnose explicitly" {
    for ([_][2]u8{ .{ 0xff, 0xd8 }, .{ 0xff, 0xe8 }, .{ 0xfe, 0xd0 }, .{ 0x8f, 0xc8 } }) |bytes| {
        var f = try init(1, &bytes);
        defer f.deinit();
        const guest = try f.symbol("dos64_guest");
        word(&f, guest + 8, 0x200);
        const result = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 1), result.p & 1);
        try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_cpu_status")));
        try std.testing.expectEqual(@as(u16, 0x100), f.word(guest + 24));
        try std.testing.expectEqual(@as(u16, 0x200), f.word(guest + 8));
        try std.testing.expectEqual(@as(u16, 0xfad7), f.word(guest + 26));
    }
}

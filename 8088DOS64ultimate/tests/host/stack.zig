const trace=@import("trap_fixture.zig");
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
fn init(frames: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    _ = try f.call("dos64_cpu_init", 10_000);
    return f;
}
fn bytes(f: *Fixture, segment: u16, offset: u16, code: []const u8) void {
    for (code, 0..) |value, i| {
        const a = (@as(u32, segment) * 16 + (offset +% @as(u16, @intCast(i)))) & 0xfffff;
        c.dos64_reu_poke(f.machine, a, value);
    }
}
fn program(f: *Fixture, cs: u16, ip: u16, code: []const u8) !void {
    try reg(f, 9, cs);
    try reg(f, 12, ip);
    bytes(f, cs, ip, code);
}
fn step(f: *Fixture) !void {
    const r = try f.call("dos64_cpu_step", 100_000);
    if ((r.p & 1) != 0) {
        std.debug.print("Stack execution fault status={d}, opcode={x}, IP={x}\n", .{ f.peek(try f.symbol("dos64_cpu_status")), f.peek(try f.symbol("dos64_cpu_opcode")), try get(f, 12) });
        return error.StackExecutionFault;
    }
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn reuWord(f: *Fixture, segment: u16, offset: u16) u16 {
    const lo = (@as(u32, segment) * 16 + offset) & 0xfffff;
    const hi = (@as(u32, segment) * 16 + (offset +% 1)) & 0xfffff;
    return @as(u16, c.dos64_reu_peek(f.machine, lo)) | (@as(u16, c.dos64_reu_peek(f.machine, hi)) << 8);
}

test "assembly stack primitives preserve host flags and wrap guest SS SP per byte" {
    var f = try init(1);
    defer f.deinit();
    try reg(&f, 10, 0x1234);
    try reg(&f, 4, 1);
    word(&f, try f.symbol("dos64_cpu_value"), 0xbeef);
    f.initial_status = 0xed;
    var r = try f.call("dos64_stack_push", 30_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u8, 0xec), r.p & 0xef);
    try std.testing.expectEqual(@as(u16, 0xffff), try get(&f, 4));
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0xbeef), reuWord(&f, 0x1234, 0xffff));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x22340));
    word(&f, try f.symbol("dos64_cpu_value"), 0);
    r = try f.call("dos64_stack_pop", 30_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u8, 0xec), r.p & 0xef);
    try std.testing.expectEqual(@as(u16, 0xbeef), f.word(try f.symbol("dos64_cpu_value")));
    try std.testing.expectEqual(@as(u16, 1), try get(&f, 4));
    try std.testing.expectEqual(@as(u16, 0x1234), try get(&f, 10));
    // DMA restores the output bits; input latch bits may reflect the saved
    // electrical read (pull-ups), as on the existing REU contract.
    try std.testing.expectEqual(@as(u8, 0x2f), f.peek(0));
    try std.testing.expectEqual(@as(u8, 0x35 & 0x2f), f.peek(1) & 0x2f);
}

test "all register PUSH POP execute with original 8088 PUSH SP and POP SP order" {
    for (0..8) |i| {
        var f = try init(2);
        defer f.deinit();
        const index: u16 = @intCast(i);
        try reg(&f, 10, 0x2000);
        try reg(&f, 4, 0x800);
        if (i != 4) try reg(&f, index, 0xa011 + index);
        try reg(&f, 13, 0xfad7);
        try program(&f, 0x1000, 0x100, &.{ @as(u8, 0x50) + @as(u8, @intCast(i)), @as(u8, 0x58) + @as(u8, @intCast(i)) });
        try step(&f);
        try flush(&f);
        const expected: u16 = if (i == 4) 0x7fe else 0xa011 + index;
        try std.testing.expectEqual(@as(u16, 0x7fe), try get(&f, 4));
        try std.testing.expectEqual(expected, reuWord(&f, 0x2000, 0x7fe));
        if (i != 4) try reg(&f, index, 0);
        try step(&f);
        try std.testing.expectEqual(expected, try get(&f, index));
        try std.testing.expectEqual(@as(u16, if (i == 4) 0x7fe else 0x800), try get(&f, 4));
        try std.testing.expectEqual(@as(u16, 0xfad7), try get(&f, 13));
    }
}

test "segment stack instructions use SS and repaired NMOS POP segment inhibits next instruction" {
    const pushes = [_]u8{ 0x06, 0x0e, 0x16, 0x1e };
    for (pushes, 0..) |opcode, i| {
        var f = try init(2);
        defer f.deinit();
        for (8..12) |n| try reg(&f, @intCast(n), 0x2100 + @as(u16, @intCast(n)));
        try reg(&f, 4, 0x400);
        try program(&f, 0x2109, 0x100, &.{ 0x3e, opcode });
        const expected = try get(&f, 8 + @as(u16, @intCast(i)));
        try step(&f);
        try flush(&f);
        try std.testing.expectEqual(expected, reuWord(&f, 0x210a, 0x3fe));
    }
    for ([_]u8{ 0x07, 0x17, 0x1f }) |opcode| {
        var f = try init(2);
        defer f.deinit();
        try reg(&f, 10, 0x3000);
        try reg(&f, 4, 0x200);
        bytes(&f, 0x3000, 0x200, &.{ 0x67, 0x45 });
        try program(&f, 0x1000, 0x100, &.{ opcode, 0x90 });
        try step(&f);
        const index: u16 = if (opcode == 7) 8 else if (opcode == 0x17) 10 else 11;
        try std.testing.expectEqual(@as(u16, 0x4567), try get(&f, index));
        try std.testing.expectEqual(@as(u16, 0x202), try get(&f, 4));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_irq_shadow")));
        try step(&f);
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_cpu_irq_shadow")));
    }
}

test "SAHF LAHF exhaust low byte preserving high flags and AL" {
    var f = try init(2);
    defer f.deinit();
    try trace.install(&f);try reg(&f,10,0x2000);try reg(&f,4,0x800);
    try program(&f, 0x1000, 0x100, &.{ 0x9e, 0x9f });
    for (0..256) |n| {
        try reg(&f, 12, 0x100);
        try reg(&f, 0, (@as(u16, @intCast(n)) << 8) | 0x37);
        try reg(&f, 13, 0xfb02);
        try step(&f);
        const expected: u16 = (@as(u16, @intCast(n)) & 0xd5) | 2;
        try std.testing.expectEqual(@as(u16, 0xfb00) | expected, try get(&f, 13));
        try trace.enterAndReturn(&f);
        try reg(&f, 0, 0x0037);
        try step(&f);
        try std.testing.expectEqual((expected << 8) | 0x37, try get(&f, 0));
        try trace.enterAndReturn(&f);
    }
}

test "PUSHF POPF normalize original 8088 reserved bits and IF transition shadow" {
    for ([_]u16{ 0, 0xffff, 0x0300, 0x0fd5, 0xf002 }) |value| {
        var f = try init(2);
        defer f.deinit();
        try reg(&f, 10, 0x2000);
        try reg(&f, 4, 0x500);
        try reg(&f, 13, 0xf002);
        bytes(&f, 0x2000, 0x500, &.{ @truncate(value), @truncate(value >> 8) });
        try program(&f, 0x1000, 0x100, &.{ 0x9d, 0x9c, 0x90 });
        try step(&f);
        const expected = (value & 0x0fd5) | 0xf002;
        try std.testing.expectEqual(expected, try get(&f, 13));
        try std.testing.expectEqual(@as(u8, if ((value & 0x200) != 0) 1 else 0), f.peek(try f.symbol("dos64_cpu_irq_shadow")));
        try step(&f);
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_cpu_irq_shadow")));
        try std.testing.expectEqual(@as(u16, 0x500), try get(&f, 4));
        try flush(&f);
        try std.testing.expectEqual(expected, reuWord(&f, 0x2000, 0x500));
    }
}

test "near CALL RET and RET immediate execute guest return and wrap displacement" {
    for ([_]bool{ false, true }) |cleanup| {
        var f = try init(2);
        defer f.deinit();
        try reg(&f, 10, 0x2000);
        try reg(&f, 4, 0x600);
        try program(&f, 0x1000, 0x100, &.{ 0xe8, 5, 0, 0xf4, 0x90, 0x90, 0x90, 0x90, 0xb8, 0x34, 0x12, if (cleanup) 0xc2 else 0xc3, 6, 0 });
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x108), try get(&f, 12));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x103), reuWord(&f, 0x2000, 0x5fe));
        try step(&f);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x103), try get(&f, 12));
        try std.testing.expectEqual(@as(u16, if (cleanup) 0x606 else 0x600), try get(&f, 4));
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x1234), try get(&f, 0));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
    }
    var f = try init(2);
    defer f.deinit();
    try reg(&f, 4, 0);
    try program(&f, 0x1000, 0xffff, &.{ 0xe8, 0xfc, 0xff });
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0xfffe), try get(&f, 12));
    try std.testing.expectEqual(@as(u16, 0xfffe), try get(&f, 4));
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 2), reuWord(&f, 0, 0xfffe));
}

test "far CALL RETF return CS IP in correct stack order and cleanup wraps SP" {
    for ([_]bool{ false, true }) |cleanup| {
        var f = try init(2);
        defer f.deinit();
        try reg(&f, 10, 0x2000);
        try reg(&f, 4, 2);
        try program(&f, 0x1234, 0x100, &.{ 0x9a, 0x00, 0x02, 0x21, 0x43, 0xf4 });
        bytes(&f, 0x4321, 0x200, &.{ 0xb8, 0x78, 0x56, if (cleanup) 0xca else 0xcb, 6, 0 });
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x4321), try get(&f, 9));
        try std.testing.expectEqual(@as(u16, 0x200), try get(&f, 12));
        try std.testing.expectEqual(@as(u16, 0xfffe), try get(&f, 4));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x105), reuWord(&f, 0x2000, 0xfffe));
        try std.testing.expectEqual(@as(u16, 0x1234), reuWord(&f, 0x2000, 0));
        try step(&f);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x1234), try get(&f, 9));
        try std.testing.expectEqual(@as(u16, 0x105), try get(&f, 12));
        try std.testing.expectEqual(@as(u16, if (cleanup) 8 else 2), try get(&f, 4));
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x5678), try get(&f, 0));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
    }
}

test "stack memory failure leaves documented partial write and no false pop advance" {
    var push = try init(1);
    defer push.deinit();
    try reg(&push, 10, 0x1234);
    try reg(&push, 4, 1);
    word(&push, try push.symbol("dos64_cpu_value"), 0x7654);
    // Lower byte load succeeds; the independently addressed high byte load fails.
    c.dos64_reu_fail_after(push.machine, 1, 16);
    var r = try push.call("dos64_stack_push", 30_000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u16, 0xffff), try get(&push, 4));
    // The low byte remains owned by the dirty cache despite the failed eviction.
    try flush(&push);
    try std.testing.expectEqual(@as(u8, 0x54), c.dos64_reu_peek(push.machine, 0x2233f));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(push.machine, 0x12340));
    var pop = try init(1);
    defer pop.deinit();
    try reg(&pop, 10, 0x1234);
    try reg(&pop, 4, 0xffff);
    bytes(&pop, 0x1234, 0xffff, &.{ 0x54, 0x76 });
    c.dos64_reu_fail_after(pop.machine, 1, 16);
    r = try pop.call("dos64_stack_pop", 30_000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u16, 0xffff), try get(&pop, 4));
}

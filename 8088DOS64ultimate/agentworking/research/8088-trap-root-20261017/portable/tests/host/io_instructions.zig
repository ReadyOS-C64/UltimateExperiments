const trace=@import("trap_fixture.zig");
const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn word(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address +% 1, @truncate(value >> 8));
}
fn initialize(program: []const u8, ax: u16, dx: u16) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), 2);
    _ = try f.call("dos64_cache_init", 50_000);
    _ = try f.call("dos64_cpu_init", 5_000);
    _ = try f.call("dos64_io_init", 5_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    const g = try f.symbol("dos64_guest");
    for (0..14) |i| word(&f, g + @as(u16, @intCast(i * 2)), @truncate(0x1234 + i * 0x111));
    word(&f, g, ax);
    word(&f, g + 4, dx);
    word(&f, g + 18, 0);
    word(&f, g + 24, 0x200);
    word(&f, g + 26, 0xfdd7);
    for (program, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x200 + @as(u32, @intCast(i)), v);
    return f;
}

test "all eight IN OUT forms execute PIC cycles and preserve guest flags and unrelated registers" {
    const Row = struct { opcode: u8, port: u16, ax: u16, expected_ax: u16, imr: u8, expected_imr: u8, read: bool };
    const rows = [_]Row{
        .{ .opcode = 0xe4, .port = 0x21, .ax = 0x7700, .expected_ax = 0x77a5, .imr = 0xa5, .expected_imr = 0xa5, .read = true },
        .{ .opcode = 0xe5, .port = 0x20, .ax = 0x7700, .expected_ax = 0xa53c, .imr = 0xa5, .expected_imr = 0xa5, .read = true },
        .{ .opcode = 0xe6, .port = 0x21, .ax = 0x77a5, .expected_ax = 0x77a5, .imr = 0xfc, .expected_imr = 0xa5, .read = false },
        .{ .opcode = 0xe7, .port = 0x20, .ax = 0xa50b, .expected_ax = 0xa50b, .imr = 0xfc, .expected_imr = 0xa5, .read = false },
        .{ .opcode = 0xec, .port = 0x21, .ax = 0x7700, .expected_ax = 0x77a5, .imr = 0xa5, .expected_imr = 0xa5, .read = true },
        .{ .opcode = 0xed, .port = 0x20, .ax = 0x7700, .expected_ax = 0xa53c, .imr = 0xa5, .expected_imr = 0xa5, .read = true },
        .{ .opcode = 0xee, .port = 0x21, .ax = 0x77a5, .expected_ax = 0x77a5, .imr = 0xfc, .expected_imr = 0xa5, .read = false },
        .{ .opcode = 0xef, .port = 0x20, .ax = 0xa50b, .expected_ax = 0xa50b, .imr = 0xfc, .expected_imr = 0xa5, .read = false },
    };
    for (rows) |row| {
        const program = [_]u8{ row.opcode, @truncate(row.port) };
        var f = try initialize(&program, row.ax, row.port);
        defer f.deinit();
        f.poke(try f.symbol("dos64_pic_imr"), row.imr);
        f.poke(try f.symbol("dos64_pic_irr"), 0x3c);
        const g = try f.symbol("dos64_guest");
        var before: [14]u16 = undefined;
        for (&before, 0..) |*v, i| v.* = f.word(g + @as(u16, @intCast(i * 2)));
        const result = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 0), result.p & 1);
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_cpu_status")));
        for (before, 0..) |v, i| {
            const expected = if (i == 0) row.expected_ax else if (i == 12) @as(u16, if (row.opcode < 0xe8) 0x202 else 0x201) else v;
            try std.testing.expectEqual(expected, f.word(g + @as(u16, @intCast(i * 2))));
        }
        try std.testing.expectEqual(row.expected_imr, f.peek(try f.symbol("dos64_pic_imr")));
        try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
        if (!row.read and row.port == 0x20) try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_pic_read_isr")));
    }
}

test "unsupported port and width rewind the instruction without partial PIC or AX effects" {
    const rows = [_]struct { opcode: u8, port: u16 }{
        .{ .opcode = 0xe5, .port = 0x21 }, .{ .opcode = 0xe7, .port = 0x21 },
        .{ .opcode = 0xed, .port = 0xffff }, .{ .opcode = 0xef, .port = 0x120 },
        .{ .opcode = 0xe6, .port = 0xf1 }, .{ .opcode = 0xe4, .port = 0x62 },
    };
    for (rows) |row| {
        const program = [_]u8{ row.opcode, @truncate(row.port) };
        var f = try initialize(&program, 0xa50b, row.port);
        defer f.deinit();
        const g = try f.symbol("dos64_guest");
        const result = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 1), result.p & 1);
        try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_cpu_status")));
        try std.testing.expectEqual(@as(u16, 0x200), f.word(g + 24));
        try std.testing.expectEqual(@as(u16, 0xa50b), f.word(g));
        try std.testing.expectEqual(@as(u16, 0xfdd7), f.word(g + 26));
        try std.testing.expectEqual(@as(u8, 0xfc), f.peek(try f.symbol("dos64_pic_imr")));
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_pic_read_isr")));
        try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_cpu_instructions")));
    }
}

test "immediate I O wraps IP and prefixes do not invent repeated bus cycles" {
    var f = try initialize(&.{ 0xf3, 0xf0, 0xe6, 0x21 }, 0x77a5, 0x20);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    try trace.install(&f);
    _ = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u16, 0x204), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek(try f.symbol("dos64_pic_imr")));
    try trace.enterAndReturn(&f);
    c.dos64_reu_poke(f.machine, 0xffff, 0xe6);
    c.dos64_reu_poke(f.machine, 0, 0x21);
    word(&f, g + 24, 0xffff);
    word(&f, g, 0x7766);
    _ = try f.call("dos64_cpu_step", 100_000);
    try std.testing.expectEqual(@as(u16, 1), f.word(g + 24));
    try std.testing.expectEqual(@as(u8, 0x66), f.peek(try f.symbol("dos64_pic_imr")));
}


test "8088 byte IO reaches XT PPI fixed PIT and absent game adapter with unchanged guest flags" {
    const rows=[_]struct{opcode:u8,port:u16,ax:u16,expected:u16}{
        .{.opcode=0xe4,.port=0x61,.ax=0xa500,.expected=0xa548},
        .{.opcode=0xec,.port=0x61,.ax=0xa500,.expected=0xa548},
        .{.opcode=0xe6,.port=0x61,.ax=0xa54b,.expected=0xa54b},
        .{.opcode=0xee,.port=0x61,.ax=0xa54b,.expected=0xa54b},
        .{.opcode=0xe6,.port=0x40,.ax=0xa500,.expected=0xa500},
        .{.opcode=0xee,.port=0x40,.ax=0xa500,.expected=0xa500},
        .{.opcode=0xec,.port=0x201,.ax=0xa500,.expected=0xa5ff},
    };
    for(rows)|row| {
        var f=try initialize(&.{row.opcode,@truncate(row.port)},row.ax,row.port);defer f.deinit();
        const g=try f.symbol("dos64_guest");const before= f.word(g+26);
        const result=try f.call("dos64_cpu_step",100_000);
        try std.testing.expectEqual(@as(u8,0),result.p&1);
        try std.testing.expectEqual(row.expected,f.word(g));
        try std.testing.expectEqual(before,f.word(g+26));
        try std.testing.expectEqual(@as(u16,if(row.opcode<0xe8)0x202 else 0x201),f.word(g+24));
        try std.testing.expectEqual(@as(u8,0xfc),f.peek(try f.symbol("dos64_pic_imr")));
        if(row.port==0x40)try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_pit_write_phase")));
        if(row.port==0x61 and (row.opcode==0xe6 or row.opcode==0xee))try std.testing.expectEqual(@as(u8,0x4b),f.peek(try f.symbol("dos64_ppi_port_b")));
    }
}

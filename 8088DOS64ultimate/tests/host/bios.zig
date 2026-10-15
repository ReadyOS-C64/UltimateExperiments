const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const allocator = std.testing.allocator;

fn word(f: *Fixture, a: u16, v: u16) void {
    f.poke(a, @truncate(v));
    f.poke(a +% 1, @truncate(v >> 8));
}
fn reg(f: *Fixture, index: u16, v: u16) !void {
    word(f, (try f.symbol("dos64_guest")) + index * 2, v);
}
fn init(initialize_bios: bool) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    try bootstrap(&f);
    f.poke(try f.symbol("dos64_cache_limit"), 32);
    _ = try f.call("dos64_cache_init", 50_000);
    _ = try f.call("dos64_cpu_init", 10_000);
    _ = try f.call("dos64_disk_init", 10_000);
    if (initialize_bios) try biosInit(&f);
    return f;
}
fn biosInit(f: *Fixture) !void {
    const r = try f.call("dos64_bios_init", 40_000_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek(try f.symbol("dos64_bios_ready")));
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 200_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn step(f: *Fixture) !void {
    const r = try f.call("dos64_cpu_step", 2_000_000);
    if ((r.p & 1) != 0) {
        std.debug.print("BIOS CPU fault status={d} CS:IP={x}:{x}\n", .{ f.peek(try f.symbol("dos64_cpu_status")), f.word((try f.symbol("dos64_guest")) + 18), f.word((try f.symbol("dos64_guest")) + 24) });
        return error.BiosCpuFault;
    }
}
fn code(f: *Fixture, at: u32, bytes: []const u8) void {
    for (bytes, 0..) |v, i| c.dos64_reu_poke(f.machine, at + @as(u32, @intCast(i)), v);
}
fn coherentCode(f: *Fixture, at: u16, bytes: []const u8) !void {
    const address = try f.symbol("dos64_address");
    for (bytes, 0..) |value, index| {
        word(f, address, at + @as(u16, @intCast(index)));
        f.poke(address + 2, 0);
        f.poke(try f.symbol("dos64_mem_value"), value);
        const r = try f.call("dos64_mem_write", 50_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    }
}
fn port(f: *Fixture, p: u8) !c.Dos64Regs {
    const sentinel = try f.symbol("fixture_return");
    word(f, 0x1fe, sentinel -% 1);
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_bios_port"), .sp = 0xfd, .a = p, .x = 0x82, .y = 0x93, .p = 0x2c, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.machine, sentinel, 200_000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    return r.regs;
}
fn disk1(f: *Fixture) ![]u8 {
    const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img", allocator, .limited(400 * 1024));
    errdefer allocator.free(bytes);
    try std.testing.expectEqual(@as(usize, 360 * 1024), bytes.len);
    code(f, 0x100000, bytes);
    f.poke(try f.symbol("dos64_disk_loaded"), 1);
    return bytes;
}

test "owned synthetic BIOS initializes exact ROM IVT BDA and preserves conventional RAM and disk configuration" {
    var f = try init(false);
    defer f.deinit();
    c.dos64_reu_poke(f.machine, 0x500, 0xab);
    c.dos64_reu_poke(f.machine, 0x9ffff, 0xcd);
    f.poke(try f.symbol("dos64_disk_loaded"), 1);
    f.initial_status = 0x2c;
    try biosInit(&f);
    try std.testing.expectEqual(@as(u8, 0x2c), f.last_regs.?.p & 0x2c);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_memory_mode")));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_disk_loaded")));
    try std.testing.expectEqual(@as(u16, 720), f.word(try f.symbol("dos64_disk_sectors")));
    try flush(&f);
    const low = try allocator.alloc(u8, 0x500);
    defer allocator.free(low);
    @memset(low, 0);
    for ([_][2]u16{ .{ 0x44, 0x20 }, .{ 0x45, 1 }, .{ 0x47, 0xf0 }, .{ 0x48, 0x30 }, .{ 0x49, 1 }, .{ 0x4b, 0xf0 }, .{ 0x4d, 1 }, .{ 0x4f, 0xf0 }, .{ 0x64, 0x10 }, .{ 0x65, 1 }, .{ 0x67, 0xf0 }, .{ 0x79, 3 }, .{ 0x7b, 0xf0 }, .{ 0x410, 0x21 }, .{ 0x413, 0x80 }, .{ 0x414, 2 }, .{ 0x41a, 0x1e }, .{ 0x41c, 0x1e }, .{ 0x449, 3 }, .{ 0x44a, 80 }, .{ 0x44d, 0x10 }, .{ 0x460, 7 }, .{ 0x461, 6 }, .{ 0x463, 0xd4 }, .{ 0x464, 3 }, .{ 0x465, 0x29 } }) |p| low[p[0]] = @intCast(p[1]);
    low[0x20]=0xa0;low[0x21]=1;low[0x23]=0xf0;
    low[0x70]=0xc0;low[0x71]=1;low[0x73]=0xf0;
    low[0x54] = 0x40;
    low[0x55] = 1;
    low[0x57] = 0xf0;
    for ([_][2]u16{ .{ 0x40, 0x50 }, .{ 0x41, 1 }, .{ 0x43, 0xf0 }, .{ 0x50, 0x60 }, .{ 0x51, 1 }, .{ 0x53, 0xf0 }, .{ 0x5c, 0x70 }, .{ 0x5d, 1 }, .{ 0x5f, 0xf0 }, .{ 0x466, 0x30 } }) |p| low[p[0]] = @intCast(p[1]);
    for ([_][2]u16{ .{ 0x58, 0x80 }, .{ 0x59, 1 }, .{ 0x5b, 0xf0 }, .{ 0x68, 0x90 }, .{ 0x69, 1 }, .{ 0x6b, 0xf0 }, .{ 0x480, 0x1e }, .{ 0x482, 0x3e } }) |p| low[p[0]] = @intCast(p[1]);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0, low.ptr, low.len));
    const rom = try allocator.alloc(u8, 65536);
    defer allocator.free(rom);
    @memset(rom, 0xff);
    @memcpy(rom[0x100..0x103], &[_]u8{ 0xe6, 0xf1, 0xcf });
    @memcpy(rom[0x110..0x113], &[_]u8{ 0xe6, 0xf2, 0xf4 });
    @memcpy(rom[0x120..0x12a], &[_]u8{ 0x1e, 0x31, 0xc0, 0x8e, 0xd8, 0xa1, 0x10, 0x04, 0x1f, 0xcf });
    @memcpy(rom[0x130..0x13a], &[_]u8{ 0x1e, 0x31, 0xc0, 0x8e, 0xd8, 0xa1, 0x13, 0x04, 0x1f, 0xcf });
    @memcpy(rom[0x140..0x14b], &[_]u8{ 0x55, 0x89, 0xe5, 0x83, 0x4e, 6, 1, 0xb4, 0x86, 0x5d, 0xcf });
    @memcpy(rom[0x150..0x153], &[_]u8{ 0xe6, 0xf3, 0xcf });
    @memcpy(rom[0x160..0x163], &[_]u8{ 0xe6, 0xf4, 0xcf });
    @memcpy(rom[0x170..0x173], &[_]u8{ 0xe6, 0xf5, 0xcf });
    @memcpy(rom[0x180..0x183], &[_]u8{ 0xe6, 0xf6, 0xcf });
    @memcpy(rom[0x190..0x193], &[_]u8{ 0xe6, 0xf7, 0xcf });
    @memcpy(rom[0x1a0..0x1ad], &[_]u8{0xfb,0x50,0xe6,0xf8,0xcd,0x1c,0xb0,0x20,0xe6,0x20,0x58,0xcf,0xff});
    rom[0x1c0]=0xcf;
    @memcpy(rom[0x300..0x30b], &[_]u8{ 0xcf, 2, 0x25, 2, 9, 0x2a, 0xff, 0x50, 0xf6, 0x19, 4 });
    @memcpy(rom[0xfff0..0xfffe], &[_]u8{ 0xea, 0x10, 1, 0, 0xf0, '1', '0', '/', '1', '5', '/', '2', '6', 0xff });
    rom[0xfffe] = 0xfe;
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0xf0000, rom.ptr, rom.len));
    try std.testing.expectEqual(@as(u8, 0xab), c.dos64_reu_peek(f.machine, 0x500));
    try std.testing.expectEqual(@as(u8, 0xcd), c.dos64_reu_peek(f.machine, 0x9ffff));
    const screen = try allocator.alloc(u8, 0x4000);
    defer allocator.free(screen);
    for (screen, 0..) |*v, i| v.* = if (i % 2 == 0) 0x20 else 7;
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0xb8000, screen.ptr, screen.len));
    // Guest stores through the normal PC bus cannot alter the owned ROM.
    word(&f, try f.symbol("dos64_segment"), 0xf000);
    word(&f, try f.symbol("dos64_offset"), 0x100);
    word(&f, try f.symbol("dos64_cpu_value"), 0x1234);
    _ = try f.call("dos64_cpu_word_write", 10_000);
    try flush(&f);
    try std.testing.expectEqual(@as(u8, 0xe6), c.dos64_reu_peek(f.machine, 0xf0100));
    try std.testing.expectEqual(@as(u8, 0xf1), c.dos64_reu_peek(f.machine, 0xf0101));
}

test "BIOS initialization restores caller memory mode and refuses publication after partial cache failure" {
    var f = try init(false);
    defer f.deinit();
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    c.dos64_reu_fail_after(f.machine, 2, 16);
    const r = try f.call("dos64_bios_init", 40_000_000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_memory_mode")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_bios_ready")));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_bios_host_error")));
}

test "INT10 query and absent INT14 INT17 use owned gates and normal IRET frames" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    const rows = [_]struct { vector: u8, ax: u16, gate: u16, expected: u16, expected_bx:u16=0xbeef }{
        .{ .vector = 0x10, .ax = 0x0f00, .gate = 0x150, .expected = 0x5003, .expected_bx=0x00ef },
        .{ .vector=0x10,.ax=0x1b00,.gate=0x150,.expected=0x1b00 },
        .{ .vector=0x10,.ax=0x10a7,.gate=0x150,.expected=0x10a7 },
        .{ .vector=0x10,.ax=0xff5a,.gate=0x150,.expected=0xff5a },
        .{ .vector = 0x14, .ax = 0x00a3, .gate = 0x160, .expected = 0x00a3 },
        .{ .vector = 0x17, .ax = 0xffa3, .gate = 0x170, .expected = 0xffa3 },
    };
    for (rows, 0..) |row, i| {
        const at: u16 = 0x200 + @as(u16, @intCast(i * 8));
        for ([_]u8{ 0xcd, row.vector, 0xf4 }, 0..) |value, index| {
            const address = try f.symbol("dos64_address");
            word(&f, address, at + @as(u16, @intCast(index)));
            f.poke(address + 2, 0);
            f.poke(try f.symbol("dos64_mem_value"), value);
            const write = try f.call("dos64_mem_write", 50_000);
            try std.testing.expectEqual(@as(u8, 0), write.p & 1);
        }
        try reg(&f, 9, 0);
        try reg(&f, 12, at);
        try reg(&f, 4, 0x1000);
        try reg(&f, 10, 0x2000);
        try reg(&f, 13, 0xf603);
        try reg(&f, 0, row.ax);
        try reg(&f, 2, 3);
        try reg(&f, 3, 0xbeef);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xf000), f.word(g + 18));
        try std.testing.expectEqual(row.gate, f.word(g + 24));
        try step(&f);
        try step(&f);
        try std.testing.expectEqual(row.expected, f.word(g));
        try std.testing.expectEqual(row.expected_bx, f.word(g + 6));
        try std.testing.expectEqual(@as(u16, 3), f.word(g + 4));
        try std.testing.expectEqual(@as(u16, 0x1000), f.word(g + 8));
        try std.testing.expectEqual(@as(u16, 0xf603), f.word(g + 26));
        try std.testing.expectEqual(at + 2, f.word(g + 24));
    }
}

test "video and auxiliary callback whitelists reject wrong gates and propagate cache failure" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    for ([_][2]u16{ .{ 0x102, 0xf3 }, .{ 0x152, 0xf4 }, .{ 0x162, 0xf5 }, .{ 0x172, 0xf3 } }) |item| {
        try reg(&f, 9, 0xf000);
        try reg(&f, 12, item[0]);
        try reg(&f, 0, 0x0f00);
        const r = try port(&f, @intCast(item[1]));
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_bios_host_error")));
        try std.testing.expectEqual(@as(u16, 0x0f00), f.word(g));
    }
    // Segment alias of F0150 is admitted and queries dirty coherent BDA.
    try reg(&f, 9, 0xf001);
    try reg(&f, 12, 0x142);
    var r = try port(&f, 0xf3);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u16, 0x5003), f.word(g));
    try flush(&f);
    f.poke(try f.symbol("dos64_cache_limit"), 1);
    _ = try f.call("dos64_cache_init", 50_000);
    c.dos64_reu_fail_after(f.machine, 0, 8);
    try reg(&f, 9, 0xf000);
    try reg(&f, 12, 0x152);
    try reg(&f, 0, 0x0f00);
    r = try port(&f, 0xf3);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_bios_host_error")));
}

test "INT1A RTC probe follows original XT AH decrement and restores caller flags" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    try coherentCode(&f, 0x200, &.{ 0xcd, 0x1a, 0xf4 });
    try reg(&f, 9, 0);
    try reg(&f, 12, 0x200);
    try reg(&f, 10, 0x2000);
    try reg(&f, 4, 0x1000);
    try reg(&f, 0, 0x02c9);
    try reg(&f, 1, 0x1234);
    try reg(&f, 2, 0x5678);
    try reg(&f, 13, 0xf703);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x190), f.word(g + 24));
    try step(&f);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x01c9), f.word(g));
    try std.testing.expectEqual(@as(u16, 0x1234), f.word(g + 2));
    try std.testing.expectEqual(@as(u16, 0x5678), f.word(g + 4));
    try std.testing.expectEqual(@as(u16, 0xf703), f.word(g + 26));
    try std.testing.expectEqual(@as(u16, 0x202), f.word(g + 24));
}

test "INT16 empty read yields in its owned gate then consumes an enqueued key without stack drift" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    try coherentCode(&f, 0x200, &.{ 0xcd, 0x16, 0xf4 });
    try reg(&f, 9, 0);
    try reg(&f, 12, 0x200);
    try reg(&f, 10, 0x2000);
    try reg(&f, 4, 0x1000);
    try reg(&f, 0, 0x00a7);
    try reg(&f, 13, 0xf403);
    try step(&f);
    for (0..32) |_| {
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x180), f.word(g + 24));
        try std.testing.expectEqual(@as(u16, 0x0ffa), f.word(g + 8));
        try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_yield")));
        try std.testing.expectEqual(@as(u16, 0x00a7), f.word(g));
        try std.testing.expectEqual(@as(u16, 0x200), f.word(g + 26) & 0x200);
    }
    word(&f, try f.symbol("dos64_keyboard_key"), 0x1e61);
    const queued = try f.call("dos64_keyboard_enqueue", 100_000);
    try std.testing.expectEqual(@as(u8, 0), queued.p & 1);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x182), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 0x1e61), f.word(g));
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x202), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 0x1000), f.word(g + 8));
    try std.testing.expectEqual(@as(u16, 0xf403), f.word(g + 26));
    try std.testing.expectEqual(@as(u16, 3), f.word(try f.symbol("dos64_cpu_instructions")));
}

test "INT16 peek patches original CMP TF IF return flags and leaves the key queued" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    word(&f, try f.symbol("dos64_keyboard_key"), 0x3062);
    _ = try f.call("dos64_keyboard_enqueue", 100_000);
    try coherentCode(&f, 0x200, &.{ 0xcd, 0x16, 0xf4 });
    try reg(&f, 9, 0);
    try reg(&f, 12, 0x200);
    try reg(&f, 10, 0x2000);
    try reg(&f, 4, 0x1000);
    try reg(&f, 0, 0x0100);
    try reg(&f, 13, 0xfdd7);
    try step(&f);
    try step(&f);
    try step(&f);
    // CMP 001Eh,0020h = FFFEh: CF/SF set; PF/AF/ZF/OF clear; STI IF1, TF0.
    try std.testing.expectEqual(@as(u16, (0xfdd7 & ~@as(u16, 0x0bd5)) | 0x0281), f.word(g + 26));
    try std.testing.expectEqual(@as(u16, 0x3062), f.word(g));
    try flush(&f);
    try std.testing.expectEqual(@as(u8, 0x1e), c.dos64_reu_peek(f.machine, 0x41a));
    try std.testing.expectEqual(@as(u8, 0x20), c.dos64_reu_peek(f.machine, 0x41c));
}

test "BIOS private ports whitelist physical owned opcodes including aliases and reject arbitrary guest instructions" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    try reg(&f, 4, 0x1000);
    try reg(&f, 13, 0xf203);
    for ([_][3]u16{ .{ 0, 0x102, 0xf1 }, .{ 0xf000, 0x102, 0xf2 }, .{ 0xf000, 0x112, 0xf1 }, .{ 0xf000, 0x103, 0xf1 }, .{ 0xf000, 0x102, 0x71 } }) |item| {
        try reg(&f, 9, item[0]);
        try reg(&f, 12, item[1]);
        try reg(&f, 0, 0);
        const r = try port(&f, @intCast(item[2]));
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_bios_host_error")));
        try std.testing.expectEqual(@as(u16, 0), f.word(g));
    }
    // F001:00F0 aliases the admitted physical F0100 opcode.
    try reg(&f, 9, 0xf001);
    try reg(&f, 12, 0xf2);
    var r = try port(&f, 0xf1);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    // FFFF:0110 wraps to physical 00100, and must not gain privilege.
    try reg(&f, 9, 0xffff);
    try reg(&f, 12, 0x112);
    r = try port(&f, 0xf1);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    f.poke(try f.symbol("dos64_bios_ready"), 0);
    try reg(&f, 9, 0xf000);
    try reg(&f, 12, 0x102);
    r = try port(&f, 0xf1);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
}

test "INT13 normal ROM IRET patches only saved carry and preserves other guest registers on success and error" {
    for ([_]u16{ 0, 0xff00 }) |ax| {
        var f = try init(true);
        defer f.deinit();
        const g = try f.symbol("dos64_guest");
        code(&f, 0x200, &.{ 0xcd, 0x13, 0xf4 });
        try reg(&f, 9, 0);
        try reg(&f, 12, 0x200);
        try reg(&f, 4, 2);
        try reg(&f, 10, 0x2000);
        try reg(&f, 13, 0xf603);
        try reg(&f, 0, ax);
        for ([_]u16{ 1, 3, 5, 6, 7, 8, 11 }) |i| try reg(&f, i, 0x1234 + i);
        const before: [28]u8 = blk: {
            var v: [28]u8 = undefined;
            for (&v, 0..) |*b, i| b.* = f.peek(g + @as(u16, @intCast(i)));
            break :blk v;
        };
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x100), f.word(g + 24));
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x102), f.word(g + 24));
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x202), f.word(g + 24));
        try std.testing.expectEqual(@as(u16, 2), f.word(g + 8));
        try std.testing.expectEqual(if (ax == 0) @as(u16, 0xf602) else @as(u16, 0xf603), f.word(g + 26));
        try std.testing.expectEqual(if (ax == 0) @as(u16, 0) else @as(u16, 0x0100), f.word(g));
        for ([_]u16{ 1, 2, 3, 5, 6, 7, 8, 10, 11 }) |i| try std.testing.expectEqual(std.mem.readInt(u16, before[i * 2 ..][0..2], .little), f.word(g + i * 2));
    }
}

test "PUSHF CALL FAR BIOS disk chain returns through ordinary IRET and cache failures remain terminal" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    code(&f, 0x200, &.{ 0x9c, 0x9a, 0, 1, 0, 0xf0, 0xf4 });
    try reg(&f, 9, 0);
    try reg(&f, 12, 0x200);
    try reg(&f, 4, 0x1000);
    try reg(&f, 13, 0xf203);
    try reg(&f, 0, 0);
    for (0..4) |_| try step(&f);
    try std.testing.expectEqual(@as(u16, 0x206), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 0x1000), f.word(g + 8));
    try std.testing.expectEqual(@as(u16, 0xf202), f.word(g + 26));
    try reg(&f, 9, 0xf000);
    try reg(&f, 12, 0x102);
    try reg(&f, 10, 0x7000);
    try reg(&f, 4, 0x1234);
    c.dos64_reu_fail_after(f.machine, 0, 16);
    const r = try port(&f, 0xf1);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_bios_host_error")));
}

test "real guest reset reaches BIOS bootstrap and loads original disk sector exactly at 0000 7C00" {
    var f = try init(true);
    defer f.deinit();
    const bytes = try disk1(&f);
    defer allocator.free(bytes);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x110), f.word((try f.symbol("dos64_guest")) + 24));
    try step(&f);
    const g = try f.symbol("dos64_guest");
    for ([_]u16{ 8, 9, 10, 11 }) |i| try std.testing.expectEqual(@as(u16, 0), f.word(g + i * 2));
    try std.testing.expectEqual(@as(u16, 0x7c00), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 0x7c00), f.word(g + 8));
    try std.testing.expectEqual(@as(u16, 0xf202), f.word(g + 26));
    try std.testing.expectEqual(@as(u8, 0), f.peek(g + 4));
    try flush(&f);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x7c00, bytes.ptr, 512));
    // Execute the unchanged sector through its reset and first real root read.
    var reached = false;
    for (0..1024) |_| {
        if (f.word(g + 18) == 0 and f.word(g + 24) == 0x7d75) {
            reached = true;
            break;
        }
        try step(&f);
    }
    try std.testing.expect(reached);
    try std.testing.expectEqual(@as(u16, 1), f.word(g));
    try flush(&f);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x500, bytes[5 * 512 ..].ptr, 512));
}

test "failed real reset bootstrap retains ROM halt path and exports disk status" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    try step(&f);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0xf000), f.word(g + 18));
    try std.testing.expectEqual(@as(u16, 0x112), f.word(g + 24));
    try std.testing.expectEqual(@as(u8, 0x80), f.peek(try f.symbol("dos64_bios_boot_status")));
    try std.testing.expectEqual(@as(u16, 0x8000), f.word(g));
    try step(&f);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
}

test "BIOS gate forwards guest disk cache faults as terminal host failures" {
    var f = try init(true);
    defer f.deinit();
    f.poke(try f.symbol("dos64_disk_loaded"), 1);
    try reg(&f, 9, 0xf000);
    try reg(&f, 12, 0x102);
    try reg(&f, 0, 0x0201);
    try reg(&f, 1, 1);
    try reg(&f, 8, 0x7000);
    try reg(&f, 3, 0);
    try reg(&f, 4, 0x1000);
    // First DMA reads owned disk staging; the next load of guest destination
    // fails. This is a cache authority failure, rather than a guest disk error.
    c.dos64_reu_fail_after(f.machine, 1, 16);
    const r = try port(&f, 0xf1);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_disk_host_error")));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_bios_host_error")));
}

test "ordinary INT11 and INT12 ROM handlers query mutable dirty BDA and preserve DS saved flags and stack" {
    var f = try init(true);
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    code(&f, 0x200, &.{ 0xcd, 0x11, 0xcd, 0x12, 0xcd, 0x11, 0xcd, 0x12, 0xf4 });
    try reg(&f, 9, 0);
    try reg(&f, 12, 0x200);
    try reg(&f, 4, 0x1000);
    try reg(&f, 10, 0x1000);
    try reg(&f, 11, 0x3456);
    try reg(&f, 13, 0xfbd7);
    for ([_]u16{ 1, 2, 3, 5, 6, 7, 8 }) |i| try reg(&f, i, 0x8765 + i);
    for ([_]u16{ 0x21, 0x280, 0x41, 0x260 }, 0..) |expected, query| {
        if (query == 2) {
            // Coherent CPU writes remain dirty: the native BIOS initializer's
            // defaults must not replace these guest-visible BDA authorities.
            const equipment_backing = c.dos64_reu_peek(f.machine, 0x410);
            const memory_backing = c.dos64_reu_peek(f.machine, 0x413);
            word(&f, try f.symbol("dos64_segment"), 0);
            word(&f, try f.symbol("dos64_offset"), 0x410);
            word(&f, try f.symbol("dos64_cpu_value"), 0x41);
            var r = try f.call("dos64_cpu_word_write", 10_000);
            try std.testing.expectEqual(@as(u8, 0), r.p & 1);
            word(&f, try f.symbol("dos64_offset"), 0x413);
            word(&f, try f.symbol("dos64_cpu_value"), 0x260);
            r = try f.call("dos64_cpu_word_write", 10_000);
            try std.testing.expectEqual(@as(u8, 0), r.p & 1);
            try std.testing.expectEqual(equipment_backing, c.dos64_reu_peek(f.machine, 0x410));
            try std.testing.expectEqual(memory_backing, c.dos64_reu_peek(f.machine, 0x413));
            try std.testing.expect(equipment_backing != 0x41 and memory_backing != 0x60);
        }
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xf000), f.word(g + 18));
        try std.testing.expectEqual(if (query % 2 == 0) @as(u16, 0x120) else @as(u16, 0x130), f.word(g + 24));
        for (0..6) |_| try step(&f);
        try std.testing.expectEqual(expected, f.word(g));
        try std.testing.expectEqual(@as(u16, 0x3456), f.word(g + 22));
        try std.testing.expectEqual(@as(u16, 0xfbd7), f.word(g + 26));
        try std.testing.expectEqual(@as(u16, 0x1000), f.word(g + 8));
        try std.testing.expectEqual(@as(u16, 0), f.word(g + 18));
        try std.testing.expectEqual(@as(u16, 0x202) + @as(u16, @intCast(query)) * 2, f.word(g + 24));
        for ([_]u16{ 1, 2, 3, 5, 6, 7, 8 }) |i| try std.testing.expectEqual(@as(u16, 0x8765) + i, f.word(g + i * 2));
    }
}

test "original XT INT15 configuration request returns unsupported AH86 CF1 through guest frame and IRET" {
    for ([_]u16{ 0xfad6, 0xfad7 }) |flags| {
        var f = try init(true);
        defer f.deinit();
        const g = try f.symbol("dos64_guest");
        code(&f, 0x200, &.{ 0xcd, 0x15, 0x72, 2, 0xb0, 0, 0xf4 });
        for ([_]u16{ 1, 2, 3, 5, 6, 7, 8 }) |i| try reg(&f, i, 0x1100 + i);
        try reg(&f, 0, 0xc05a);
        try reg(&f, 4, 0x200);
        try reg(&f, 9, 0);
        try reg(&f, 10, 0x2345);
        try reg(&f, 11, 0x3456);
        try reg(&f, 12, 0x200);
        try reg(&f, 13, flags);
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0xf000), f.word(g + 18));
        try std.testing.expectEqual(@as(u16, 0x140), f.word(g + 24));
        for (0..6) |_| try step(&f);
        try std.testing.expectEqual(@as(u16, 0x865a), f.word(g));
        try std.testing.expectEqual(flags | 1, f.word(g + 26));
        try std.testing.expectEqual(@as(u16, 0x200), f.word(g + 8));
        try std.testing.expectEqual(@as(u16, 0), f.word(g + 18));
        try std.testing.expectEqual(@as(u16, 0x2345), f.word(g + 20));
        try std.testing.expectEqual(@as(u16, 0x3456), f.word(g + 22));
        try std.testing.expectEqual(@as(u16, 0x202), f.word(g + 24));
        for ([_]u16{ 1, 2, 3, 5, 6, 7, 8 }) |i| try std.testing.expectEqual(@as(u16, 0x1100) + i, f.word(g + i * 2));
        try flush(&f);
        const frame = [_]u8{ 0x05, 0x11, 0x02, 0x02, 0, 0, @truncate(flags | 1), @truncate(flags >> 8) };
        try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x23450 + 0x1f8, &frame, frame.len));
        // The real kernel follows this request with JC; unsupported must take
        // that branch without publishing an ES:BX configuration pointer.
        try step(&f);
        try std.testing.expectEqual(@as(u16, 0x206), f.word(g + 24));
        try step(&f);
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
        try std.testing.expectEqual(@as(u16, 0x865a), f.word(g));
    }
}

fn bootstrap(f: *Fixture) !void {
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 100_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"), 4);
    const boot = try f.call("dos64_overlay_bootstrap", 300_000);
    try std.testing.expectEqual(@as(u8, 0), boot.p & 1);
}

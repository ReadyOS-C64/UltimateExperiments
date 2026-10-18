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
fn physical(segment: u16, offset: u16) u32 {
    return (@as(u32, segment) * 16 + offset) & 0xfffff;
}
fn bytes(f: *Fixture, segment: u16, offset: u16, data: []const u8) void {
    for (data, 0..) |value, i| c.dos64_reu_poke(f.machine, physical(segment, offset +% @as(u16, @intCast(i))), value);
}
fn seedWord(f: *Fixture, segment: u16, offset: u16, value: u16) void {
    bytes(f, segment, offset, &.{ @truncate(value), @truncate(value >> 8) });
}
fn backingWord(f: *Fixture, segment: u16, offset: u16) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, physical(segment, offset))) | (@as(u16, c.dos64_reu_peek(f.machine, physical(segment, offset +% 1))) << 8);
}
fn program(f: *Fixture, code: []const u8) !void {
    try reg(f, 9, 0x1000);
    try reg(f, 12, 0x100);
    bytes(f, 0x1000, 0x100, code);
}
fn step(f: *Fixture) !void {
    const r = try f.call("dos64_cpu_step", 250_000);
    if ((r.p & 1) != 0) {
        std.debug.print("String fault status={d} opcode={x} CX={x} IP={x}\n", .{ f.peek(try f.symbol("dos64_cpu_status")), f.peek(try f.symbol("dos64_cpu_opcode")), try get(f, 1), try get(f, 12) });
        return error.StringExecutionFault;
    }
    try std.testing.expectEqual(f.initial_status & 0xee, r.p & 0xef);
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 100_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn complete(f: *Fixture) !usize {
    for (0..4097) |i| {
        try step(f);
        if (f.word(try f.symbol("dos64_cpu_instructions")) != 0) return i + 1;
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_yield")));
    }
    return error.UnboundedStringInstruction;
}
fn compareFlags(lhs: u16, rhs: u16, wide: bool, initial: u16) u16 {
    const mask: u32 = if (wide) 0xffff else 0xff;
    const sign: u32 = if (wide) 0x8000 else 0x80;
    const a: u32 = @as(u32, lhs) & mask;
    const b: u32 = @as(u32, rhs) & mask;
    const result = (a -% b) & mask;
    var flags = initial & ~@as(u16, 0x8d5);
    if (a < b) flags |= 1;
    if ((@popCount(@as(u8, @truncate(result))) & 1) == 0) flags |= 4;
    if (((a ^ b ^ result) & 0x10) != 0) flags |= 0x10;
    if (result == 0) flags |= 0x40;
    if ((result & sign) != 0) flags |= 0x80;
    if (((a ^ b) & (a ^ result) & sign) != 0) flags |= 0x800;
    return flags;
}

test "all non-REP MOVS STOS LODS widths honor DF and pointer wrapping with CX zero" {
    for ([_]u8{ 0xa4, 0xa5, 0xaa, 0xab, 0xac, 0xad }) |opcode| {
        for ([_]bool{ false, true }) |backward| {
            var f = try init(1);
            defer f.deinit();
            try reg(&f, 11, 0x1234);
            try reg(&f, 8, 0x5678);
            try reg(&f, 6, 0xffff);
            try reg(&f, 7, 0xffff);
            try reg(&f, 1, 0);
            try reg(&f, 0, 0xa15c);
            const flags: u16 = if (backward) 0xfed7 else 0xfad7;
            try reg(&f, 13, flags);
            seedWord(&f, 0x1234, 0xffff, 0x8732);
            seedWord(&f, 0x5678, 0xffff, 0xbbaa);
            try program(&f, &.{opcode});
            try step(&f);
            const delta: u16 = 1 + (opcode & 1);
            const next: u16 = if (backward) 0xffff -% delta else 0xffff +% delta;
            const kind = opcode & 0xfe;
            try std.testing.expectEqual(@as(u16, if (kind == 0xaa) 0xffff else next), try get(&f, 6));
            try std.testing.expectEqual(@as(u16, if (kind == 0xac) 0xffff else next), try get(&f, 7));
            try std.testing.expectEqual(@as(u16, 0), try get(&f, 1));
            try std.testing.expectEqual(flags, try get(&f, 13));
            try flush(&f);
            const wide = (opcode & 1) != 0;
            const expected_ax: u16 = if (kind == 0xac) (if (wide) 0x8732 else 0xa132) else 0xa15c;
            try std.testing.expectEqual(expected_ax, try get(&f, 0));
            const expected_memory: u16 = if (kind == 0xa4) (if (wide) 0x8732 else 0xbb32) else if (kind == 0xaa) (if (wide) 0xa15c else 0xbb5c) else 0xbbaa;
            try std.testing.expectEqual(expected_memory, backingWord(&f, 0x5678, 0xffff));
            try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
        }
    }
}

test "CMPS SCAS set independent comparison flags in both widths and directions" {
    const pairs = [_][2]u16{ .{ 0, 0 }, .{ 0, 1 }, .{ 0x80, 1 }, .{ 0x8000, 1 }, .{ 0x7fff, 0xffff }, .{ 0xffff, 0 } };
    for ([_]u8{ 0xa6, 0xa7, 0xae, 0xaf }) |opcode| {
        for (pairs) |pair| {
            for ([_]bool{ false, true }) |backward| {
                var f = try init(1);
                defer f.deinit();
                try reg(&f, 11, 0x1234);
                try reg(&f, 8, 0x5678);
                try reg(&f, 6, 0xffff);
                try reg(&f, 7, 0xffff);
                try reg(&f, 0, pair[0]);
                try reg(&f, 1, 0x7788);
                const flags: u16 = if (backward) 0xfed7 else 0xfad7;
                try reg(&f, 13, flags);
                seedWord(&f, 0x1234, 0xffff, pair[0]);
                seedWord(&f, 0x5678, 0xffff, pair[1]);
                try program(&f, &.{opcode});
                try step(&f);
                const wide = (opcode & 1) != 0;
                const delta: u16 = if (wide) 2 else 1;
                const next: u16 = if (backward) 0xffff -% delta else 0xffff +% delta;
                try std.testing.expectEqual(@as(u16, if (opcode < 0xaa) next else 0xffff), try get(&f, 6));
                try std.testing.expectEqual(next, try get(&f, 7));
                try std.testing.expectEqual(compareFlags(pair[0], pair[1], wide, flags), try get(&f, 13));
                try std.testing.expectEqual(@as(u16, 0x7788), try get(&f, 1));
                try std.testing.expectEqual(pair[0], try get(&f, 0));
                try flush(&f);
                try std.testing.expectEqual(pair[0], backingWord(&f, 0x1234, 0xffff));
                try std.testing.expectEqual(pair[1], backingWord(&f, 0x5678, 0xffff));
            }
        }
    }
}

test "REP CX zero performs no data access or flag and pointer changes for all strings" {
    for ([_]u8{ 0xa4, 0xa5, 0xa6, 0xa7, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf }) |opcode| {
        for ([_]u8{ 0xf2, 0xf3 }) |repeat| {
            var f = try init(1);
            defer f.deinit();
            try reg(&f, 11, 0x1234);
            try reg(&f, 8, 0x5678);
            try reg(&f, 6, 0xffff);
            try reg(&f, 7, 0xffff);
            try reg(&f, 0, 0x7856);
            try reg(&f, 1, 0);
            try reg(&f, 13, 0xfad7);
            try program(&f, &.{ repeat, opcode });
            // Instruction page load is permitted; any source/destination DMA
            // would become a terminal synthetic failure and fail this test.
            c.dos64_reu_fail_after(f.machine, 1, 0);
            try step(&f);
            try std.testing.expectEqual(@as(u64, 1), c.dos64_dma_transfers(f.machine));
            try std.testing.expectEqual(@as(u16, 0xffff), try get(&f, 6));
            try std.testing.expectEqual(@as(u16, 0xffff), try get(&f, 7));
            try std.testing.expectEqual(@as(u16, 0x7856), try get(&f, 0));
            try std.testing.expectEqual(@as(u16, 0xfad7), try get(&f, 13));
            try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
            try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_string_pending")));
        }
    }
}

test "REP MOVS bounded continuation preserves long prefixes override and instruction count" {
    var f = try init(1);
    defer f.deinit();
    f.initial_status = 0xed;
    var code = [_]u8{0x2e} ** 69;
    code[65] = 0xf3;
    code[66] = 0x36;
    code[67] = 0xa4;
    code[68] = 0xf4;
    try reg(&f, 10, 0x2000);
    try reg(&f, 11, 0x4000);
    try reg(&f, 8, 0x3000);
    try reg(&f, 6, 0xfff0);
    try reg(&f, 7, 0x1ff);
    try reg(&f, 1, 33);
    try reg(&f, 13, 0xfad7);
    var source: [33]u8 = undefined;
    for (&source, 0..) |*value, i| value.* = @truncate(i * 17 + 3);
    bytes(&f, 0x2000, 0xfff0, &source);
    try program(&f, &code);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 33), try get(&f, 1));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_pending")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_string_pending")));
    for ([_]u16{ 17, 1 }) |remaining| {
        try step(&f);
        try std.testing.expectEqual(remaining, try get(&f, 1));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_string_pending")));
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_yield")));
        try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_cpu_instructions")));
        try std.testing.expectEqual(@as(u16, 0x144), try get(&f, 12));
    }
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0), try get(&f, 1));
    try std.testing.expectEqual(@as(u16, 0x11), try get(&f, 6));
    try std.testing.expectEqual(@as(u16, 0x220), try get(&f, 7));
    try std.testing.expectEqual(@as(u16, 0xfad7), try get(&f, 13));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_string_pending")));
    try std.testing.expectEqual(@as(u16, 1), f.word(try f.symbol("dos64_cpu_instructions")));
    try flush(&f);
    for (source, 0..) |value, i| try std.testing.expectEqual(value, c.dos64_reu_peek(f.machine, physical(0x3000, 0x1ff + @as(u16, @intCast(i)))));
    try step(&f);
    try std.testing.expectEqual(@as(u16, 2), f.word(try f.symbol("dos64_cpu_instructions")));
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
}

test "REP LODS and STOS repeat for both prefixes with fixed ES destination" {
    for ([_]u8{ 0xaa, 0xab, 0xac, 0xad }) |opcode| {
        for ([_]u8{ 0xf2, 0xf3 }) |repeat| {
            var f = try init(1);
            defer f.deinit();
            try reg(&f, 8, 0x3000);
            try reg(&f, 10, 0x2000);
            try reg(&f, 11, 0x4000);
            try reg(&f, 0, 0x9876);
            // Cross CX low-byte borrow and 16-bit SI/DI offset boundaries.
            try reg(&f, 1, 257);
            try reg(&f, 6, 0x100);
            try reg(&f, 7, 0x200);
            try reg(&f, 13, 0xfed7);
            const delta: u16 = 1 + (opcode & 1);
            for (0..257) |n| seedWord(&f, 0x2000, 0x100 -% (@as(u16, @intCast(n)) * delta), 0x6543);
            try program(&f, &.{ 0x3e, repeat, 0x36, opcode });
            try std.testing.expectEqual(@as(usize, 17), try complete(&f));
            try std.testing.expectEqual(@as(u16, 0), try get(&f, 1));
            try std.testing.expectEqual(@as(u16, 0xfed7), try get(&f, 13));
            if (opcode < 0xac) {
                try std.testing.expectEqual(@as(u16, 0x100), try get(&f, 6));
                try std.testing.expectEqual(@as(u16, 0x200 -% (257 * delta)), try get(&f, 7));
                try flush(&f);
                for (0..257) |n| {
                    const offset = 0x200 -% (@as(u16, @intCast(n)) * delta);
                    const actual = backingWord(&f, 0x3000, offset);
                    if (delta == 2) try std.testing.expectEqual(@as(u16, 0x9876), actual) else try std.testing.expectEqual(@as(u8, 0x76), @as(u8, @truncate(actual)));
                }
                try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, physical(0x2000, 0x200)));
            } else {
                try std.testing.expectEqual(@as(u16, 0x100 -% (257 * delta)), try get(&f, 6));
                try std.testing.expectEqual(@as(u16, 0x200), try get(&f, 7));
                try std.testing.expectEqual(@as(u16, if (delta == 2) 0x6543 else 0x9843), try get(&f, 0));
            }
        }
    }
}

test "REPE REPNE CMPS SCAS stop after comparison including after a continuation" {
    for ([_]u8{ 0xa6, 0xa7, 0xae, 0xaf }) |opcode| {
        for ([_]u8{ 0xf2, 0xf3 }) |repeat| {
            var f = try init(2);
            defer f.deinit();
            try reg(&f, 11, 0x2000);
            try reg(&f, 8, 0x3000);
            try reg(&f, 0, 0x1234);
            try reg(&f, 1, 30);
            try reg(&f, 6, 0x100);
            try reg(&f, 7, 0x200);
            // Initial ZF deliberately requests stopping, but cannot prevent
            // the first comparison; 18 iterations end on the inverted result.
            try reg(&f, 13, if (repeat == 0xf3) 0xf002 else 0xf042);
            const delta: u16 = 1 + (opcode & 1);
            for (0..30) |n| {
                const different = if (repeat == 0xf3) n == 17 else n != 17;
                seedWord(&f, 0x2000, 0x100 + @as(u16, @intCast(n)) * delta, 0x1234);
                seedWord(&f, 0x3000, 0x200 + @as(u16, @intCast(n)) * delta, if (different) 0x1235 else 0x1234);
            }
            try program(&f, &.{ repeat, opcode });
            try std.testing.expectEqual(@as(usize, 2), try complete(&f));
            try std.testing.expectEqual(@as(u16, 12), try get(&f, 1));
            try std.testing.expectEqual(@as(u16, 0x200 + 18 * delta), try get(&f, 7));
            try std.testing.expectEqual(@as(u16, if (opcode < 0xaa) 0x100 + 18 * delta else 0x100), try get(&f, 6));
            const rhs: u16 = if (repeat == 0xf3) 0x1235 else 0x1234;
            try std.testing.expectEqual(compareFlags(0x1234, rhs, delta == 2, 0xf002), try get(&f, 13));
        }
    }
}

test "overlapping REP MOVS is sequential and can overwrite its own decoded opcode" {
    // A forward overlapping byte copy propagates the first byte rather than
    // behaving like a host memmove. Native cache writes remain authoritative.
    var overlap = try init(1);
    defer overlap.deinit();
    try reg(&overlap, 11, 0x2000);
    try reg(&overlap, 8, 0x2000);
    try reg(&overlap, 6, 0x100);
    try reg(&overlap, 7, 0x101);
    try reg(&overlap, 1, 33);
    bytes(&overlap, 0x2000, 0x100, &.{ 0x5a, 1, 2, 3 });
    try program(&overlap, &.{ 0xf3, 0xa4 });
    try std.testing.expectEqual(@as(usize, 3), try complete(&overlap));
    try flush(&overlap);
    for (0..34) |i| try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(overlap.machine, physical(0x2000, 0x100 + @as(u16, @intCast(i)))));
    var self = try init(1);
    defer self.deinit();
    try reg(&self, 11, 0x2000);
    try reg(&self, 8, 0x1000);
    try reg(&self, 6, 0);
    try reg(&self, 7, 0x100);
    try reg(&self, 1, 33);
    var replacement = [_]u8{0x90} ** 34;
    replacement[33] = 0xf4;
    bytes(&self, 0x2000, 0, &replacement);
    try program(&self, &.{ 0xf3, 0xa4 });
    try std.testing.expectEqual(@as(usize, 3), try complete(&self));
    try std.testing.expectEqual(@as(u16, 0x102), try get(&self, 12));
    try flush(&self);
    for (0..33) |i| try std.testing.expectEqual(@as(u8, 0x90), c.dos64_reu_peek(self.machine, physical(0x1000, 0x100 + @as(u16, @intCast(i)))));
    try step(&self);
    try std.testing.expectEqual(@as(u16, 0x103), try get(&self, 12));
    try std.testing.expectEqual(@as(u16, 2), self.word(try self.symbol("dos64_cpu_instructions")));
}

test "REP data failure latches terminal error and preserves last complete iteration" {
    var f = try init(1);
    defer f.deinit();
    try reg(&f, 11, 0x2000);
    try reg(&f, 8, 0x3000);
    try reg(&f, 1, 2);
    try reg(&f, 6, 0);
    try reg(&f, 7, 0);
    bytes(&f, 0x2000, 0, &.{ 0x34, 0x56 });
    try program(&f, &.{ 0xf3, 0xa4 });
    // Code load, source load, destination load, destination write-back, then
    // fail reloading the source for iteration two (partial 16-byte DMA).
    c.dos64_reu_fail_after(f.machine, 4, 16);
    const r = try f.call("dos64_cpu_step", 250_000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 3), f.peek(try f.symbol("dos64_cpu_status")));
    try std.testing.expectEqual(@as(u16, 1), try get(&f, 1));
    try std.testing.expectEqual(@as(u16, 1), try get(&f, 6));
    try std.testing.expectEqual(@as(u16, 1), try get(&f, 7));
    try std.testing.expectEqual(@as(u16, 0x100), try get(&f, 12));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_string_pending")));
    try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_cpu_instructions")));
    try std.testing.expectEqual(@as(u8, 0x34), c.dos64_reu_peek(f.machine, 0x30000));
    const next = try f.call("dos64_cpu_step", 1000);
    try std.testing.expectEqual(@as(u8, 1), next.p & 1);
}

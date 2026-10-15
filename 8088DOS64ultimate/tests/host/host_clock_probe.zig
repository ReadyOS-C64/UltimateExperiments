// Opt-in scripted VIC bus fixture: actual unmodified standalone PRG runs in
// Peddle. This is a control-flow/record/budget test, NOT clock-domain physics.
// The dedicated bridge must include clock_probe_model.h (ordinary shared
// bridge deliberately rejects VIC I/O). Build paths can be replaced in a
// private scratch copy for isolated work; standard artifacts live in build/.
const std = @import("std");
const c = @cImport({ @cInclude("peddle_bridge.h"); });
extern fn dos64_cia_clock_enable(*c.Dos64Machine) void;
extern fn dos64_cia_clock_reads(*const c.Dos64Machine, u8) u32;
extern fn dos64_cia_clock_writes(*const c.Dos64Machine, u8) u32;
extern fn dos64_cia_clock_mask(*const c.Dos64Machine) u8;
extern fn dos64_cia_clock_icr_seed(*c.Dos64Machine, u8, u8) void;
extern fn dos64_clock_probe_model_enable(*c.Dos64Machine, u16, u32, u32, u8) void;
extern fn dos64_clock_probe_model_reads(*const c.Dos64Machine) u64;
const allocator = std.testing.allocator;

const Fixture = struct {
    machine: *c.Dos64Machine,
    labels: []u8,
    fn init(lines: u16, ticks: u32, repeats: u32, mode: u8) !Fixture {
        const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,
            "build/dos64-clock-probe.prg", allocator, .limited(65538));
        defer allocator.free(prg);
        if (prg.len < 3 or std.mem.readInt(u16, prg[0..2], .little) != 0x801)
            return error.InvalidPrg;
        const machine = c.dos64_create() orelse return error.CreateMachine;
        errdefer c.dos64_destroy(machine);
        c.dos64_load(machine, 0x801, prg[2..].ptr, prg.len - 2);
        dos64_cia_clock_enable(machine);
        dos64_cia_clock_icr_seed(machine, 0x1f, 0x10);
        dos64_clock_probe_model_enable(machine, lines, ticks, repeats, mode);
        const labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,
            "build/dos64-clock-probe.labels", allocator, .limited(65536));
        return .{ .machine = machine, .labels = labels };
    }
    fn deinit(self: *Fixture) void {
        allocator.free(self.labels);
        c.dos64_destroy(self.machine);
    }
    fn symbol(self: *const Fixture, name: []const u8) !u16 {
        var lines = std.mem.splitScalar(u8, self.labels, '\n');
        while (lines.next()) |line| {
            var bits = std.mem.tokenizeAny(u8, line, " \t\r");
            if (!std.mem.eql(u8, bits.next() orelse continue, "al")) continue;
            const raw_address = bits.next() orelse continue;
            const raw = bits.next() orelse continue;
            if (std.mem.eql(u8, raw[1..], name))
                return std.fmt.parseInt(u16, raw_address, 16);
        }
        return error.MissingSymbol;
    }
    fn run(self: *Fixture, budget: u64) !void {
        c.dos64_set_regs(self.machine, .{ .pc = try self.symbol("dos64_entry"),
            .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24,
            .cycles = 0, .instructions = 0 });
        const r = c.dos64_run(self.machine, try self.symbol("dos64_idle"), budget);
        try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
        try std.testing.expectEqual(@as(u8, 0xff), r.regs.sp);
        try std.testing.expectEqual(@as(u8, 0), c.dos64_model_fault(self.machine));
    }
    fn byte(self: *const Fixture, offset: u16) u8 {
        return c.dos64_peek(self.machine, 0x6000 + offset);
    }
    fn word(self: *const Fixture, offset: u16) u16 {
        return @as(u16, self.byte(offset)) | (@as(u16, self.byte(offset+1)) << 8);
    }
    fn long(self: *const Fixture, offset: u16) u32 {
        return @as(u32, self.word(offset)) | (@as(u32, self.word(offset+2)) << 16);
    }
};

test "clock calibration actual assembly publishes 100 frame modulo delta and full PAL height" {
    var f = try Fixture.init(312, 63, 1, 0);
    defer f.deinit();
    try f.run(10_000_000);
    try std.testing.expectEqualSlices(u8, "DCK1", &.{ f.byte(0), f.byte(1), f.byte(2), f.byte(3) });
    try std.testing.expectEqual(@as(u8, 0xa5), f.byte(5));
    try std.testing.expectEqual(@as(u8, 0), f.byte(6));
    try std.testing.expectEqual(@as(u8, 1), f.byte(7));
    try std.testing.expectEqual(@as(u16, 100), f.word(8));
    try std.testing.expectEqual(@as(u16, 311), f.word(12));
    try std.testing.expectEqual(@as(u32, 1_965_600), f.long(22));
    try std.testing.expectEqual(f.long(18) -% f.long(14), f.long(22));
    try std.testing.expect(f.word(32) < 16 and f.word(34) < 16);
    try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_reads(f.machine, 13));
    try std.testing.expectEqual(@as(u32, 1), dos64_cia_clock_writes(f.machine, 13));
    try std.testing.expectEqual(@as(u8, 0x1c), dos64_cia_clock_mask(f.machine));
    try std.testing.expectEqual(@as(u8, 0x40), c.dos64_bus_read(f.machine, 0xdd0f) & 0x60);
    // Every native write is limited to the declared probe takeover/envelope.
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        if (a <= 1 or (a >= 0x100 and a <= 0x1ff)) continue;
        if (a >= 0x6000 and a < 0x6028) continue;
        if (a >= 0xe000 and a < 0xe008) continue;
        if (a >= 0xea00 and a < 0xea13) continue;
        if (a == 0xfffa or a == 0xfffb or a == 0xd020) continue;
        if (a >= 0xdd04 and a <= 0xdd07) continue;
        if (a == 0xdd0d or a == 0xdd0e or a == 0xdd0f) continue;
        std.debug.print("Unexpected calibration write {x:0>4}\n", .{a});
        return error.UnexpectedProbeWrite;
    }

}

test "clock probe watchdog resets each raster phase beyond 65535 total polls" {
    var f = try Fixture.init(312, 63, 8, 0);
    defer f.deinit();
    try f.run(45_000_000);
    try std.testing.expectEqual(@as(u8, 0xa5), f.byte(5));
    try std.testing.expect(dos64_clock_probe_model_reads(f.machine) > 2*65535);
    try std.testing.expectEqual(@as(u32, 1_965_600), f.long(22));
}

test "frozen low high and torn VIC terminate with native diagnostic" {
    for ([_]u8{ 1, 2, 3 }) |mode| {
        var f = try Fixture.init(312, 63, 1, mode);
        defer f.deinit();
        try f.run(20_000_000);
        try std.testing.expectEqual(@as(u8, 0xe1), f.byte(5));
        try std.testing.expectEqual(@as(u8, 2), f.byte(6));
        try std.testing.expectEqual(@as(u16, 0), f.word(8));
        try std.testing.expectEqual(@as(u8, 2), c.dos64_peek(f.machine,
            (try f.symbol("dos64_mailbox"))+4));
    }
}

test "unsupported video profile retains measurements but does not claim PAL" {
    var f = try Fixture.init(263, 65, 1, 0);
    defer f.deinit();
    try f.run(10_000_000);
    try std.testing.expectEqual(@as(u8, 0xe1), f.byte(5));
    try std.testing.expectEqual(@as(u8, 4), f.byte(6));
    try std.testing.expectEqual(@as(u8, 0), f.byte(7));
    try std.testing.expectEqual(@as(u16, 262), f.word(12));
    try std.testing.expectEqual(@as(u32, 1_709_500), f.long(22));
}

test "frozen CIA reload rejection is bounded and cannot forge calibration success" {
    var f = try Fixture.init(312, 0, 1, 0);
    defer f.deinit();
    try f.run(10_000_000);
    try std.testing.expectEqual(@as(u8, 0xe1), f.byte(5));
    try std.testing.expectEqual(@as(u8, 3), f.byte(6));
    try std.testing.expectEqual(@as(u8, 0xfe), f.byte(28));
    try std.testing.expectEqual(@as(u16, 16), f.word(26));
    try std.testing.expectEqual(@as(u16, 0), f.word(8));
}

test "VIC scripting is disabled by default and rejects malformed fixture inputs" {
    {
        const machine = c.dos64_create() orelse return error.CreateMachine;
        defer c.dos64_destroy(machine);
        _ = c.dos64_bus_read(machine, 0xd011);
        try std.testing.expectEqual(@as(u8, 1), c.dos64_model_fault(machine));
        try std.testing.expectEqual(@as(u64, 0), dos64_clock_probe_model_reads(machine));
    }
    for ([_][4]u32{
        .{ 0, 63, 1, 0 }, .{ 513, 63, 1, 0 }, .{ 312, 65537, 1, 0 },
        .{ 312, 63, 0, 0 }, .{ 312, 63, 65536, 0 }, .{ 312, 63, 1, 4 },
    }) |bad| {
        const machine = c.dos64_create() orelse return error.CreateMachine;
        defer c.dos64_destroy(machine);
        dos64_clock_probe_model_enable(machine, @intCast(bad[0]), bad[1], bad[2], @intCast(bad[3]));
        try std.testing.expectEqual(@as(u8, 1), c.dos64_model_fault(machine));
    }
}

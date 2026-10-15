const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
// C ABI supplied by the optional CIA clock extension in the Peddle bridge.
extern fn dos64_cia_clock_enable(*c.Dos64Machine) void;
extern fn dos64_cia_clock_seed(*c.Dos64Machine, u16, u16) void;
extern fn dos64_cia_clock_advance(*c.Dos64Machine, u32) void;
extern fn dos64_cia_clock_step(*c.Dos64Machine, u32) void;
extern fn dos64_cia_clock_script(*c.Dos64Machine, [*]const u32, usize) void;
extern fn dos64_cia_clock_low_snapshot(*const c.Dos64Machine) u32;
extern fn dos64_cia_clock_reads(*const c.Dos64Machine, u8) u32;
extern fn dos64_cia_clock_writes(*const c.Dos64Machine, u8) u32;
extern fn dos64_cia_clock_count(*const c.Dos64Machine, u8) u16;
extern fn dos64_cia_clock_latch(*const c.Dos64Machine, u8) u16;
extern fn dos64_cia_clock_icr_seed(*c.Dos64Machine, u8, u8) void;
extern fn dos64_cia_clock_mask(*const c.Dos64Machine) u8;
extern fn dos64_cia_clock_pending(*const c.Dos64Machine) u8;
fn value(f: *Fixture) !u32 {
    const p = try f.symbol("dos64_host_clock_ticks");
    var n: u32 = 0;
    for (0..4) |i| n |= @as(u32, f.peek(p + @as(u16, @intCast(i)))) << @as(u5, @intCast(i * 8));
    return n;
}
fn start(f: *Fixture) !void {
    dos64_cia_clock_enable(f.machine);
    f.poke(try f.symbol("dos64_host_clock_claim"), 0xa5);
    const r = try f.call("dos64_host_clock_init", 2000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn read(f: *Fixture) !u32 {
    const r = try f.call("dos64_host_clock_read", 5000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_host_clock_status")));
    const result = try value(f);
    try std.testing.expectEqual(~dos64_cia_clock_low_snapshot(f.machine), result);
    return result;
}
fn untouched(f: *Fixture) !void {
    for ([_]u8{ 0, 1, 2, 3, 8, 9, 10, 11, 12, 13 }) |reg| {
        try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_reads(f.machine, reg));
        try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_writes(f.machine, reg));
    }
}
test "clock requires explicit ownership and readiness before touching CIA" {
    var f = try Fixture.init();
    defer f.deinit();
    dos64_cia_clock_enable(f.machine);
    for ([_][]const u8{ "dos64_host_clock_init", "dos64_host_clock_read" }) |entry| {
        const r = try f.call(entry, 2000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_host_clock_status")));
    }
    f.poke(try f.symbol("dos64_host_clock_claim"), 0xa5);
    const r = try f.call("dos64_host_clock_read", 2000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_host_clock_status")));
    for (0..16) |reg| {
        try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_reads(f.machine, @intCast(reg)));
        try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_writes(f.machine, @intCast(reg)));
    }
}
test "clock programs stopped latches and cascade without consuming NMI state" {
    var f = try Fixture.init();
    defer f.deinit();
    dos64_cia_clock_enable(f.machine);
    c.dos64_bus_write(f.machine, 0xdd0e, 0xc8);
    c.dos64_bus_write(f.machine, 0xdd0f, 0x88);
    dos64_cia_clock_icr_seed(f.machine, 0x14, 0x16);
    f.poke(try f.symbol("dos64_host_clock_claim"), 0xa5);
    _ = try f.call("dos64_host_clock_init", 2000);
    try std.testing.expectEqual(@as(u8, 0x81), c.dos64_bus_read(f.machine, 0xdd0e));
    try std.testing.expectEqual(@as(u8, 0xc1), c.dos64_bus_read(f.machine, 0xdd0f));
    for (0..2) |timer| {
        try std.testing.expectEqual(@as(u16, 0xffff), dos64_cia_clock_latch(f.machine, @intCast(timer)));
        try std.testing.expectEqual(@as(u16, 0xffff), dos64_cia_clock_count(f.machine, @intCast(timer)));
    }
    try std.testing.expectEqual(@as(u8, 0x14), dos64_cia_clock_mask(f.machine));
    try std.testing.expectEqual(@as(u8, 0x16), dos64_cia_clock_pending(f.machine));
    try untouched(&f);
}
test "clock returns coherent raw counter with independent phi2 advance" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    dos64_cia_clock_seed(f.machine, 0x3456, 0x1234);
    try std.testing.expectEqual(@as(u32, 0xedcb_cba9), try read(&f));
    const a = try read(&f);
    dos64_cia_clock_advance(f.machine, 12345);
    const b = try read(&f);
    try std.testing.expectEqual(@as(u32, 12345), b -% a);
    try untouched(&f);
}
test "clock retries every low byte seam and preserves sampled instant" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    dos64_cia_clock_step(f.machine, 1);
    for (1..255) |hi| {
        dos64_cia_clock_seed(f.machine, (@as(u16, @intCast(hi)) << 8) | 7, 0x5678);
        _ = try read(&f);
    }
    try untouched(&f);
}
test "clock bounded reload rejection handles delayed cascade and later resumes" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    dos64_cia_clock_seed(f.machine, 0x1234, 0x1200);
    const old = try read(&f);
    dos64_cia_clock_seed(f.machine, 4, 0x1200);
    dos64_cia_clock_step(f.machine, 1);
    const before = dos64_cia_clock_reads(f.machine, 7);
    const r = try f.call("dos64_host_clock_read", 5000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 4), f.peek(try f.symbol("dos64_host_clock_status")));
    try std.testing.expectEqual(old, try value(&f));
    try std.testing.expect(dos64_cia_clock_reads(f.machine, 7) - before <= 32);
    try std.testing.expectEqual(@as(u16, 0x11ff), dos64_cia_clock_count(f.machine, 1));
    dos64_cia_clock_advance(f.machine, 300);
    _ = try read(&f);
}
test "clock handles full 32-bit wrap and rejects B high-low read seam" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    dos64_cia_clock_seed(f.machine, 0x0123, 0);
    const before = try read(&f);
    dos64_cia_clock_advance(f.machine, 0x300);
    const after = try read(&f);
    try std.testing.expect(after < before);
    try std.testing.expectEqual(@as(u32, 0x300), after -% before);
    dos64_cia_clock_seed(f.machine, 0, 0x1200);
    const script = [_]u32{ 0, 0, 0, 2 };
    dos64_cia_clock_script(f.machine, &script, script.len);
    const r = try f.call("dos64_host_clock_read", 5000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(after, try value(&f));
    dos64_cia_clock_advance(f.machine, 300);
    _ = try read(&f);
}
test "clock detects timer ownership damage without replacing last good publication" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    dos64_cia_clock_seed(f.machine, 0x1234, 0xabcd);
    const old = try read(&f);
    for ([_]u8{ 0, 0x21, 9, 3, 0x41 }) |bad| {
        c.dos64_bus_write(f.machine, 0xdd0e, bad);
        const r = try f.call("dos64_host_clock_read", 2000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 3), f.peek(try f.symbol("dos64_host_clock_status")));
        try std.testing.expectEqual(old, try value(&f));
    }
    c.dos64_bus_write(f.machine, 0xdd0e, 1);
    for ([_]u8{ 0, 1, 0x61, 0x49, 0x43 }) |bad| {
        c.dos64_bus_write(f.machine, 0xdd0f, bad);
        const r = try f.call("dos64_host_clock_read", 2000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(old, try value(&f));
    }
    f.poke(try f.symbol("dos64_host_clock_claim"), 0);
    const r = try f.call("dos64_host_clock_read", 2000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_host_clock_status")));
}
test "clock preserves registers flags and observable banking for all DDR modes" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    for ([_]u8{ 0, 7, 0x2f, 0xff }) |ddr| for (0..8) |bits| for ([_]u8{ 0x20, 0x24, 0x28, 0xec }) |p| {
        f.poke(0, ddr);
        f.poke(1, 0x30 | @as(u8, @intCast(bits)));
        f.initial_status = p;
        dos64_cia_clock_seed(f.machine, 0x2345, 0x6789);
        const original_port = c.dos64_bus_read(f.machine, 1);
        const r = try f.call("dos64_host_clock_read", 5000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(p & 0xfe, r.p & 0xfe);
        try std.testing.expectEqual(@as(u8, 0x71), r.a);
        try std.testing.expectEqual(@as(u8, 0x82), r.x);
        try std.testing.expectEqual(@as(u8, 0x93), r.y);
        try std.testing.expectEqual(ddr, f.peek(0));
        // Input-configured latch bits are not readable on a 6510. Preserve
        // all DDR/output bits; pullups then preserve the effective mapping.
        try std.testing.expectEqual(original_port & ddr, c.dos64_bus_read(f.machine, 1) & ddr);
    };
}
test "clock only writes its state stack mapping and explicitly owned timer registers" {
    var f = try Fixture.init();
    defer f.deinit();
    try start(&f);
    const first = try f.symbol("dos64_host_clock_claim");
    const last = (try f.symbol("dos64_host_clock_ticks")) + 9;
    for ([_][]const u8{ "dos64_host_clock_init", "dos64_host_clock_read" }) |entry| {
        dos64_cia_clock_seed(f.machine, 0x1234, 0x5678);
        _ = try f.call(entry, 5000);
        for (0..65536) |i| {
            const a: u16 = @intCast(i);
            if (c.dos64_was_written(f.machine, a) == 0) continue;
            if (a <= 1 or (a >= 0x100 and a <= 0x1ff)) continue;
            if (a >= first and a < last) continue;
            if (std.mem.eql(u8, entry, "dos64_host_clock_init") and
                (a == 0xdd04 or a == 0xdd05 or a == 0xdd06 or a == 0xdd07 or a == 0xdd0e or a == 0xdd0f)) continue;
            std.debug.print("Unexpected clock write {x:0>4}\n", .{a});
            return error.UnexpectedClockWrite;
        }
        try untouched(&f);
    }
}

test "clock model exposes stopped latch force load start and ICR semantics independently" {
    var f = try Fixture.init();
    defer f.deinit();
    dos64_cia_clock_enable(f.machine);
    c.dos64_bus_write(f.machine, 0xdd04, 2);
    c.dos64_bus_write(f.machine, 0xdd05, 0);
    try std.testing.expectEqual(@as(u16, 2), dos64_cia_clock_count(f.machine, 0));
    c.dos64_bus_write(f.machine, 0xdd0e, 1);
    dos64_cia_clock_advance(f.machine, 3);
    try std.testing.expectEqual(@as(u16, 1), dos64_cia_clock_count(f.machine, 0));
    c.dos64_bus_write(f.machine, 0xdd04, 9);
    c.dos64_bus_write(f.machine, 0xdd05, 0);
    try std.testing.expectEqual(@as(u16, 1), dos64_cia_clock_count(f.machine, 0));
    c.dos64_bus_write(f.machine, 0xdd0e, 0x11);
    try std.testing.expectEqual(@as(u16, 9), dos64_cia_clock_count(f.machine, 0));
    try std.testing.expectEqual(@as(u8, 1), c.dos64_bus_read(f.machine, 0xdd0e));
    c.dos64_bus_write(f.machine, 0xdd0d, 0x81);
    dos64_cia_clock_advance(f.machine, 20);
    try std.testing.expectEqual(@as(u8, 0x81), c.dos64_bus_read(f.machine, 0xdd0d));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_bus_read(f.machine, 0xdd0d));
    c.dos64_bus_write(f.machine, 0xdd0d, 1);
    try std.testing.expectEqual(@as(u8, 0), dos64_cia_clock_mask(f.machine));
}

test "CIA model is optional and obeys ordinary 6510 I/O banking" {
    {
        var f = try Fixture.init();
        defer f.deinit();
        _ = c.dos64_bus_read(f.machine, 0xdd04);
        try std.testing.expectEqual(@as(u8, 1), c.dos64_model_fault(f.machine));
    }
    var f = try Fixture.init();
    defer f.deinit();
    dos64_cia_clock_enable(f.machine);
    f.poke(0xdd04, 0x5a);
    f.poke(1, 0x30);
    try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_bus_read(f.machine, 0xdd04));
    f.poke(1, 0x33);
    try std.testing.expectEqual(@as(u8, 0xcc), c.dos64_bus_read(f.machine, 0xdd04));
    try std.testing.expectEqual(@as(u32, 0), dos64_cia_clock_reads(f.machine, 4));
    f.poke(1, 0x35);
    try std.testing.expectEqual(@as(u8, 0xff), c.dos64_bus_read(f.machine, 0xdd04));
    try std.testing.expectEqual(@as(u32, 1), dos64_cia_clock_reads(f.machine, 4));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_model_fault(f.machine));
}

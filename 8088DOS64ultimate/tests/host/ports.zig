const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn put(f: *Fixture, name: []const u8, value: u8) !void {
    f.poke(try f.symbol(name), value);
}
fn get(f: *Fixture, name: []const u8) !u8 {
    return f.peek(try f.symbol(name));
}
fn word(f: *Fixture, name: []const u8, value: u16) !void {
    const a = try f.symbol(name);
    f.poke(a, @truncate(value));
    f.poke(a + 1, @truncate(value >> 8));
}
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    const r = try f.call("dos64_io_init", 10_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return f;
}
fn cycle(f: *Fixture, port: u16, value: u16, width: u8, read: bool, carry: u8) !u16 {
    try word(f, "dos64_io_port", port);
    try word(f, "dos64_io_value", value);
    try put(f, "dos64_io_width", width);
    // Every tested command also checks complete guest state and host status.
    const g = try f.symbol("dos64_guest");
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| {
        v.* = @truncate(i * 13 + 7);
        f.poke(g + @as(u16, @intCast(i)), v.*);
    }
    const r = try f.call(if (read) "dos64_io_read" else "dos64_io_write", 10_000);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce); // N,V,D,I,Z; B is stack-only.
    for (before, 0..) |v, i| try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
    try std.testing.expectEqual(port, f.word(try f.symbol("dos64_io_port")));
    try std.testing.expectEqual(width, try get(f, "dos64_io_width"));
    const actual = f.word(try f.symbol("dos64_io_value"));
    if (!read or carry != 0) try std.testing.expectEqual(value, actual);
    // The only native writes permitted are the bounded state plus host stack.
    const lo = try f.symbol("dos64_io_state_start");
    const hi = try f.symbol("dos64_io_state_end");
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        try std.testing.expect((a >= 0x100 and a < 0x200) or (a >= lo and a < hi));
    }
    return actual;
}
fn out(f: *Fixture, port: u16, value: u8) !void {
    _ = try cycle(f, port, value, 0, false, 0);
}
fn expectState(f: *Fixture, name: []const u8, value: u8) !void {
    try std.testing.expectEqual(value, try get(f, name));
}

test "PIC original XT BIOS defaults and native initialization ABI" {
    var f = try init();
    defer f.deinit();
    const lo = try f.symbol("dos64_io_state_start");
    const hi = try f.symbol("dos64_io_state_end");
    const guest = try f.symbol("dos64_guest");
    for (lo..hi) |a| f.poke(@intCast(a), 0xa7);
    for (0..28) |i| f.poke(guest + @as(u16, @intCast(i)), @truncate(i * 7));
    f.poke(lo - 1, 0x3c);
    f.poke(hi, 0xc3);
    const initialized = try f.call("dos64_io_init", 10_000);
    try std.testing.expectEqual(@as(u8, 0), initialized.p & 1);
    try std.testing.expectEqual(@as(u8, 0x3c), f.peek(lo - 1));
    try std.testing.expectEqual(@as(u8, 0xc3), f.peek(hi));
    for (0..28) |i| try std.testing.expectEqual(@as(u8, @truncate(i * 7)), f.peek(guest + @as(u16, @intCast(i))));
    try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_io_port")));
    try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_io_value")));
    try expectState(&f, "dos64_io_width", 0);
    try expectState(&f, "dos64_pic_imr", 0xfc);
    try expectState(&f, "dos64_pic_base", 8);
    try expectState(&f, "dos64_pic_icw1", 0x13);
    try expectState(&f, "dos64_pic_icw4", 9);
    for ([_][]const u8{ "dos64_pic_irr", "dos64_pic_isr", "dos64_pic_phase", "dos64_pic_read_isr", "dos64_pic_special_mask", "dos64_pic_rotate_auto" }) |n| try expectState(&f, n, 0);
    try expectState(&f, "dos64_pic_priority", 7);
    try std.testing.expect((try f.symbol("dos64_io_state_start")) >= 0xea00 and (try f.symbol("dos64_io_state_end")) <= 0xef00);
    for ([_]u8{ 0x20, 0x2e, 0xe8, 0xef }) |p| {
        f.initial_status = p;
        _ = try cycle(&f, 0x21, 0x5500, 0, true, 0);
        const r = try f.call("dos64_io_init", 10_000);
        try std.testing.expectEqual(p & 0xce, r.p & 0xce);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    }
}

test "PIC all four ICW sequence lengths route data and reset transient command state" {
    for ([_]u8{ 0x10, 0x11, 0x12, 0x13 }) |icw1| {
        var f = try init();
        defer f.deinit();
        try put(&f, "dos64_pic_irr", 0xaa);
        try put(&f, "dos64_pic_isr", 0xff);
        try out(&f, 0x20, 0x6b);
        try out(&f, 0x20, 0xc3);
        try out(&f, 0x20, 0x80);
        try out(&f, 0x20, icw1);
        for ([_][]const u8{ "dos64_pic_imr", "dos64_pic_irr", "dos64_pic_isr", "dos64_pic_read_isr", "dos64_pic_special_mask", "dos64_pic_rotate_auto", "dos64_pic_icw4" }) |n| try expectState(&f, n, 0);
        try expectState(&f, "dos64_pic_phase", 2);
        try expectState(&f, "dos64_pic_priority", 7);
        try out(&f, 0x21, 0x2f);
        try expectState(&f, "dos64_pic_base", 0x28);
        try expectState(&f, "dos64_pic_icw2", 0x2f);
        if (icw1 & 2 == 0) {
            try expectState(&f, "dos64_pic_phase", 3);
            try out(&f, 0x21, 0x40);
            try expectState(&f, "dos64_pic_icw3", 0x40);
        }
        if (icw1 & 1 != 0) {
            try expectState(&f, "dos64_pic_phase", 4);
            try out(&f, 0x21, 0xfb);
            try expectState(&f, "dos64_pic_icw4", 0x1b);
        }
        try expectState(&f, "dos64_pic_phase", 0);
        try out(&f, 0x21, 0xa6);
        try expectState(&f, "dos64_pic_imr", 0xa6);
    }
    // ICW1 restarts an incomplete sequence on the command address.
    var f = try init();
    defer f.deinit();
    try out(&f, 0x20, 0x11);
    try out(&f, 0x21, 0x20);
    try out(&f, 0x20, 0x13);
    try out(&f, 0x21, 0x08);
    try out(&f, 0x21, 0x09);
    try expectState(&f, "dos64_pic_phase", 0);
}

test "PIC masks IRR ISR read selection persists and RR0 leaves selection unchanged" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_pic_irr", 0xa5);
    try put(&f, "dos64_pic_isr", 0x5a);
    for (0..256) |mask| {
        try out(&f, 0x21, @intCast(mask));
        try std.testing.expectEqual(@as(u16, 0x7700) | @as(u16, @intCast(mask)), try cycle(&f, 0x21, 0x7700, 0, true, 0));
    }
    try std.testing.expectEqual(@as(u16, 0x66a5), try cycle(&f, 0x20, 0x6600, 0, true, 0));
    try out(&f, 0x20, 0x0b);
    for (0..2) |_| try std.testing.expectEqual(@as(u16, 0x665a), try cycle(&f, 0x20, 0x6600, 0, true, 0));
    try out(&f, 0x20, 0x08);
    try out(&f, 0x20, 0x09);
    try std.testing.expectEqual(@as(u16, 0x665a), try cycle(&f, 0x20, 0x6600, 0, true, 0));
    try out(&f, 0x20, 0x0a);
    try std.testing.expectEqual(@as(u16, 0x66a5), try cycle(&f, 0x20, 0x6600, 0, true, 0));
    try expectState(&f, "dos64_pic_irr", 0xa5);
    try expectState(&f, "dos64_pic_isr", 0x5a);
}

test "PIC nonspecific EOI uses rotating priority and specific EOI only named ISR" {
    var f = try init();
    defer f.deinit();
    // Independent oracle: first set bit cyclically after configured bottom IRQ.
    for (0..8) |bottom| for (0..256) |bits| {
        try out(&f, 0x20, 0xc0 | @as(u8, @intCast(bottom)));
        try put(&f, "dos64_pic_isr", @intCast(bits));
        var expected: u8 = @intCast(bits);
        for (1..9) |distance| {
            const irq: u3 = @intCast((bottom + distance) % 8);
            const bit = @as(u8, 1) << irq;
            if (expected & bit != 0) {
                expected &= ~bit;
                break;
            }
        }
        try out(&f, 0x20, 0x20);
        try expectState(&f, "dos64_pic_isr", expected);
        try expectState(&f, "dos64_pic_priority", @intCast(bottom));
    };
    for (0..8) |irq| {
        try put(&f, "dos64_pic_isr", 0xff);
        try out(&f, 0x20, 0x60 | @as(u8, @intCast(irq)));
        try expectState(&f, "dos64_pic_isr", ~(@as(u8, 1) << @as(u3, @intCast(irq))));
    }
    try out(&f, 0x20, 0xc7);
    try put(&f, "dos64_pic_isr", 0x88);
    try out(&f, 0x20, 0xa0);
    try expectState(&f, "dos64_pic_isr", 0x80);
    try expectState(&f, "dos64_pic_priority", 3);
    try out(&f, 0x20, 0xe7);
    try expectState(&f, "dos64_pic_isr", 0);
    try expectState(&f, "dos64_pic_priority", 7);
    try out(&f, 0x20, 0xc2);
    try out(&f, 0x20, 0xa0);
    try expectState(&f, "dos64_pic_priority", 2);
    try out(&f, 0x20, 0x80);
    try expectState(&f, "dos64_pic_rotate_auto", 1);
    try out(&f, 0x20, 0x40);
    try expectState(&f, "dos64_pic_rotate_auto", 1);
    try out(&f, 0x20, 0);
    try expectState(&f, "dos64_pic_rotate_auto", 0);
}

test "PIC special mask mode excludes masked ISR from nonspecific EOI only" {
    var f = try init();
    defer f.deinit();
    try out(&f, 0x21, 1);
    try put(&f, "dos64_pic_isr", 3);
    try out(&f, 0x20, 0x68);
    try out(&f, 0x20, 0x20);
    try expectState(&f, "dos64_pic_isr", 1);
    try out(&f, 0x20, 0x28);
    try expectState(&f, "dos64_pic_special_mask", 1); // ESMM0 ignores SMM
    try out(&f, 0x20, 0x60);
    try expectState(&f, "dos64_pic_isr", 0); //specific still clears masked bit
    try put(&f, "dos64_pic_isr", 3);
    try out(&f, 0x20, 0x48);
    try out(&f, 0x20, 0x20);
    try expectState(&f, "dos64_pic_isr", 2);
}

test "PIC word cycles preserve descriptors and preflight unsupported widths and boundary ports" {
    var f = try init();
    defer f.deinit();
    _ = try cycle(&f, 0x20, 0x0813, 1, false, 0);
    try expectState(&f, "dos64_pic_base", 8);
    try expectState(&f, "dos64_pic_phase", 4);
    try out(&f, 0x21, 9);
    try out(&f, 0x21, 0xa6);
    try put(&f, "dos64_pic_irr", 0x35);
    try std.testing.expectEqual(@as(u16, 0xa635), try cycle(&f, 0x20, 0x8888, 1, true, 0));
    for ([_]u16{ 0, 0x1f, 0x21, 0x22, 0x61, 0xa0, 0x120, 0xfffe, 0xffff }) |port| {
        const imr = try get(&f, "dos64_pic_imr");
        const phase = try get(&f, "dos64_pic_phase");
        // A failed word at21 must not replace IMR on its first byte.
        _ = try cycle(&f, port, 0x3311, 1, false, 1);
        _ = try cycle(&f, port, 0x7766, 1, true, 1);
        try expectState(&f, "dos64_pic_imr", imr);
        try expectState(&f, "dos64_pic_phase", phase);
        if (port != 0x21 and port != 0x61) {
            _ = try cycle(&f, port, 0x3311, 0, false, 1);
            _ = try cycle(&f, port, 0x7766, 0, true, 1);
        }
    }
    for ([_]u8{ 2, 255 }) |width| {
        _ = try cycle(&f, 0x20, 0x1313, width, false, 1);
        _ = try cycle(&f, 0x20, 0xabcd, width, true, 1);
    }
    // Unsupported poll must not silently change selection or acknowledge IRR.
    _ = try cycle(&f, 0x20, 0x6f, 0, false, 1);
    _ = try cycle(&f, 0x20, 0x426f, 1, false, 1);
    try expectState(&f, "dos64_pic_read_isr", 0);
    try expectState(&f, "dos64_pic_special_mask", 0);
    try expectState(&f, "dos64_pic_irr", 0x35);
    try expectState(&f, "dos64_pic_imr", 0xa6);
}

test "DOS shared IRQ global rearm accepts only documented absent-board byte broadcasts" {
    var f=try init(); defer f.deinit();
    for(0x2f2..0x2f8) |port_number| {
        for(0..256) |value| {
            _=try cycle(&f,@intCast(port_number),@intCast(value),0,false,0);
            try expectState(&f,"dos64_pic_imr",0xfc);
            try expectState(&f,"dos64_pic_irr",0);
            try expectState(&f,"dos64_pic_isr",0);
        }
        _=try cycle(&f,@intCast(port_number),0xff,0,true,1);
        _=try cycle(&f,@intCast(port_number),0xffff,1,false,1);
    }
    for([_]u16{0x2f1,0x2f8,0x1f2,0x3f2}) |port_number| _=try cycle(&f,port_number,0xff,0,false,1);
}


test "XT8255 port B readback all mode0 output latch bits and no adjacent word side effects" {
    var f=try init();defer f.deinit();
    try expectState(&f,"dos64_ppi_port_b",0x48);
    for(0..256)|n| {
        try out(&f,0x61,@intCast(n));
        try std.testing.expectEqual(@as(u16,0xa500|@as(u16,@intCast(n))),try cycle(&f,0x61,0xa5ff,0,true,0));
        for([_]u16{0x60,0x61,0x62,0x63,0x161})|port| {
            _=try cycle(&f,port,0x7234,1,true,1);
            _=try cycle(&f,port,0x7234,1,false,1);
        }
        try expectState(&f,"dos64_ppi_port_b",@intCast(n));
        try expectState(&f,"dos64_pic_imr",0xfc);
    }
}


test "fixed BIOS PIT accepts only same divisor zero lohi rewrites preserving all timer IRQ state" {
    var f=try init();defer f.deinit();
    const a=try f.symbol("dos64_pit_state_start");const z=try f.symbol("dos64_pit_state_end");
    for(a..z)|i|f.poke(@intCast(i),@truncate(i*17+3));
    const irr=try f.symbol("dos64_pic_irr");f.poke(irr,0x91);
    for(0..8)|n| {
        try out(&f,0x40,0);
        try expectState(&f,"dos64_pit_write_phase",@intCast((n+1)&1));
        for(a..z)|i|try std.testing.expectEqual(@as(u8,@truncate(i*17+3)),f.peek(@intCast(i)));
        try expectState(&f,"dos64_pic_irr",0x91);
        _=try cycle(&f,0x40,0,0,true,1);
        _=try cycle(&f,0x40,0,1,false,1);
        _=try cycle(&f,0x40,0,1,true,1);
        _=try cycle(&f,0x140,0,0,false,1);
        for(1..256)|value|_=try cycle(&f,0x40,@intCast(value),0,false,1);
        try expectState(&f,"dos64_pit_write_phase",@intCast((n+1)&1));
        for([_]u16{0x41,0x42,0x43})|port| { for(0..256)|value| { _=try cycle(&f,port,@intCast(value),0,false,1); } }
    }
}


test "absent XT game adapter byte input is pulled high without pretending joystick hardware" {
    var f=try init();defer f.deinit();
    try std.testing.expectEqual(@as(u16,0x92ff),try cycle(&f,0x201,0x9217,0,true,0));
    _=try cycle(&f,0x201,0x1234,1,true,1);
    _=try cycle(&f,0x201,0x1234,0,false,1);
    _=try cycle(&f,0x201,0x1234,1,false,1);
    for([_]u16{0x200,0x202,0x301,0x1201})|port|_=try cycle(&f,port,0x1234,0,true,1);
}

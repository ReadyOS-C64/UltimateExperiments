const std = @import("std");
const o = @import("machine_irq_pit.zig");
const r = @import("machine_reference.zig");
const c = o.c;
const Pair = struct {
    a: o.Fixture,
    b: r.Fixture,
    fn init() !Pair {
        var a = try o.Fixture.init();
        errdefer a.deinit();
        var b = try r.Fixture.init();
        errdefer b.deinit();
        var pair: Pair = .{ .a = a, .b = b };
        inline for (.{ "dos64_cpu_init", "dos64_io_init" }) |n| {
            _ = try invoke(&pair.a, n);
            _ = try invoke(&pair.b, n);
        }
        try set(&pair.a, "dos64_cache_limit", 32);
        try set(&pair.b, "dos64_cache_limit", 32);
        _ = try invoke(&pair.a, "dos64_cache_init");
        _ = try invoke(&pair.b, "dos64_cache_init");
        return pair;
    }
    fn deinit(p: *Pair) void {
        p.a.deinit();
        p.b.deinit();
    }
    fn put(p: *Pair, n: []const u8, v: u64, len: usize) !void {
        try wide(&p.a, n, v, len);
        try wide(&p.b, n, v, len);
    }
    fn call(p: *Pair, n: []const u8) !void {
        const x = try invoke(&p.a, n);
        const y = try invoke(&p.b, n);
        try std.testing.expectEqual(y.p & 0xcf, x.p & 0xcf);
    }
    fn check(p: *Pair, ram: bool) !void {
        inline for (.{ "dos64_pit_now", "dos64_pit_last", "dos64_pit_fraction", "dos64_pit_phase", "dos64_pit_edges", "dos64_pit_total", "dos64_pit_ready", "dos64_pit_error", "dos64_pit_poll_error", "dos64_pit_poll_enabled" }, .{ 4, 4, 3, 2, 2, 4, 1, 1, 1, 1 }) |name, len| try compareField(&p.a, &p.b, name, len);
        inline for (.{ "dos64_guest", "dos64_cpu_status", "dos64_cpu_instructions", "dos64_cpu_yield", "dos64_cpu_pending", "dos64_cpu_irq_shadow", "dos64_string_pending", "dos64_irq_line", "dos64_irq_selected", "dos64_irq_result", "dos64_irq_callback_enabled", "dos64_elapsed_now", "dos64_host_clock_ticks" }, .{ 28, 1, 4, 1, 1, 1, 1, 1, 1, 1, 1, 2, 4 }) |name, len| try compareField(&p.a, &p.b, name, len);
        const a = try p.a.symbol("dos64_io_state_start");
        const b = try p.b.symbol("dos64_io_state_start");
        const len = try p.a.symbol("dos64_io_state_end") - a;
        for (0..len) |i| try std.testing.expectEqual(p.b.peek(b + @as(u16, @intCast(i))), p.a.peek(a + @as(u16, @intCast(i))));
        if (ram) {
            try p.call("dos64_cache_flush");
            const bytes = try std.testing.allocator.alloc(u8, 1024 * 1024);
            defer std.testing.allocator.free(bytes);
            try std.testing.expectEqual(@as(u8, 1), c.dos64_reu_read(p.a.machine, 0, bytes.ptr, bytes.len));
            try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(p.b.machine, 0, bytes.ptr, bytes.len));
        }
    }
};
fn invoke(f: anytype, n: []const u8) !o.c.Dos64Regs {
    return try f.call(n, 1000000);
}
fn set(f: anytype, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn wide(f: anytype, n: []const u8, v: u64, len: usize) !void {
    const at = try f.symbol(n);
    for (0..len) |i| f.poke(at + @as(u16, @intCast(i)), @truncate(v >> @as(u6, @intCast(8 * i))));
}
fn get(f: anytype, n: []const u8, len: usize) !u64 {
    var v: u64 = 0;
    const at = try f.symbol(n);
    for (0..len) |i| v |= @as(u64, f.peek(at + @as(u16, @intCast(i)))) << @as(u6, @intCast(8 * i));
    return v;
}
fn compareField(a: anytype, b: anytype, n: []const u8, len: usize) !void {
    const x = try a.symbol(n);
    const y = try b.symbol(n);
    for (0..len) |i| {
        const va = a.peek(x + @as(u16, @intCast(i)));
        const vb = b.peek(y + @as(u16, @intCast(i)));
        if (va != vb) std.debug.print("STATE_MISMATCH {s}[{d}] optimized={x} reference={x}\n", .{ n, i, va, vb });
        try std.testing.expectEqual(vb, va);
    }
}
fn rand(seed: *u32) u32 {
    seed.* = seed.* *% 1664525 +% 1013904223;
    return seed.*;
}
fn threshold(phase: u64, fraction: u64) u64 {
    return ((65536 - phase) * 451572 - fraction + 546874) / 546875;
}

test "inverse threshold exact for seeded arbitrary phase fraction and both sides of first next edge" {
    var p = try Pair.init();
    defer p.deinit();
    var seed: u32 = 0x08088253;
    for (0..1024) |_| {
        var raw = rand(&seed);
        try p.put("dos64_pit_now", raw, 4);
        try p.call("dos64_pit_init");
        const phase = rand(&seed) & 65535;
        const fraction = rand(&seed) % 451572;
        try p.put("dos64_pit_phase", phase, 2);
        try p.put("dos64_pit_fraction", fraction, 3);
        try p.put("dos64_pit_total", 0xffffffff, 4);
        try p.call("dos64_pit_rebase");
        const distance = threshold(phase, fraction);
        try std.testing.expectEqual(distance, try get(&p.a, "dos64_pit_until", 2));
        raw +%= @intCast(distance - 1);
        try p.put("dos64_pit_now", raw, 4);
        try p.call("dos64_pit_advance");
        try p.check(false);
        try std.testing.expectEqual(@as(u64, 1), try get(&p.a, "dos64_pit_until", 2));
        raw +%= 1;
        try p.put("dos64_pit_now", raw, 4);
        try p.call("dos64_pit_advance");
        try p.check(false);
        try std.testing.expectEqual(@as(u64, 1), try get(&p.a, "dos64_pit_edges", 2));
        try std.testing.expectEqual(@as(u64, 0), try get(&p.a, "dos64_pit_total", 4));
        try std.testing.expectEqual(threshold(try get(&p.a, "dos64_pit_phase", 2), try get(&p.a, "dos64_pit_fraction", 3)), try get(&p.a, "dos64_pit_until", 2));
    }
    try p.check(true);
}
test "seeded fine and coarse cadence retains complete public time PIC CPU and guest memory across wraps gaps rebase" {
    var p = try Pair.init();
    defer p.deinit();
    var seed: u32 = 0x65020888;
    var raw: u32 = 0xffff8000;
    try p.put("dos64_pit_now", raw, 4);
    try p.call("dos64_pit_init");
    for (0..4096) |i| {
        const pick = rand(&seed);
        const delta: u32 = switch (i % 8) {
            0 => 0,
            1 => 1,
            2 => pick & 31,
            3 => pick & 255,
            4 => pick & 65535,
            5 => 985248,
            6 => 0x07fff000,
            else => pick & 4095,
        };
        raw +%= delta;
        try p.put("dos64_pit_now", raw, 4);
        try p.call("dos64_pit_advance");
        try p.check(i % 128 == 0);
        try std.testing.expectEqual(threshold(try get(&p.a, "dos64_pit_phase", 2), try get(&p.a, "dos64_pit_fraction", 3)), try get(&p.a, "dos64_pit_until", 2));
        if (i % 127 == 0) {
            const epoch = raw;
            const rejected: u32 = epoch +% 0x08000000;
            try p.put("dos64_pit_now", rejected, 4);
            try p.call("dos64_pit_advance");
            try p.check(false);
            try p.put("dos64_pit_now", epoch +% 1, 4);
            try p.call("dos64_pit_advance");
            try p.check(false);
            raw = rejected;
            try p.put("dos64_pit_now", raw, 4);
            try p.call("dos64_pit_rebase");
            try p.check(false);
        }
    }
    try p.check(true);
}
fn cia(f: anytype, raw: u32) !void {
    c.dos64_cia_clock_enable(f.machine);
    try set(f, "dos64_host_clock_claim", 0xa5);
    _ = try invoke(f, "dos64_host_clock_init");
    seedCia(f, raw);
    _ = try invoke(f, "dos64_elapsed_poll");
    _ = try invoke(f, "dos64_native_timer_init");
}
fn seedCia(f: anytype, raw: u32) void {
    c.dos64_cia_clock_seed(f.machine, ~@as(u16, @truncate(raw)), ~@as(u16, @truncate(raw >> 16)));
}
fn guestWrite(f: anytype, at: u32, v: u8) !void {
    try wide(f, "dos64_address", at, 3);
    try set(f, "dos64_mem_value", v);
    const x = try invoke(f, "dos64_mem_write");
    try std.testing.expectEqual(@as(u8, 0), x.p & 1);
}
fn wordGuest(f: anytype, off: u16, v: u16) !void {
    const at = try f.symbol("dos64_guest") + off;
    f.poke(at, @truncate(v));
    f.poke(at + 1, @truncate(v >> 8));
}
fn install(f: anytype) !void {
    try wordGuest(f, 18, 0x100);
    try wordGuest(f, 24, 0x200);
    try wordGuest(f, 20, 0x2000);
    try wordGuest(f, 8, 0x1000);
    try wordGuest(f, 26, 0xf202);
    try set(f, "dos64_pic_imr", 0);
    for ([_]u8{ 0, 3, 0, 4 }, 0..) |v, i| try guestWrite(f, 0x20 + @as(u32, @intCast(i)), v);
    for (@embedFile("guest_timer.bin"), 0..) |v, i| try guestWrite(f, 0x4300 + @as(u32, @intCast(i)), v);
    for ([_]u8{ 0, 6, 0, 4 }, 0..) |v, i| try guestWrite(f, 0x70 + @as(u32, @intCast(i)), v);
    for ([_]u8{ 0x2e, 0xff, 0x06, 0, 5, 0xcf }, 0..) |v, i| try guestWrite(f, 0x4600 + @as(u32, @intCast(i)), v);
    // STI when IF already1, MOV ES shadow, REP MOVSB final element, HLT loop.
    const code = [_]u8{ 0xfb, 0x8e, 0xc0, 0xf3, 0xa4, 0xf4, 0xeb, 0xfd };
    for (code, 0..) |v, i| try guestWrite(f, 0x1200 + @as(u32, @intCast(i)), v);
    try wordGuest(f, 0, 0x3000);
    try wordGuest(f, 2, 3);
    try wordGuest(f, 12, 0x100);
    try wordGuest(f, 14, 0x200);
    try wordGuest(f, 22, 0x4000);
    for (0..3) |i| try guestWrite(f, 0x40100 + @as(u32, @intCast(i)), @intCast(0xa0 + i));
    try cia(f, 1024);
}
test "optimized and frozen real CPU delivery chains match over physical cadence with masked IRQ EOI HLT and REP" {
    var p = try Pair.init();
    defer p.deinit();
    try install(&p.a);
    try install(&p.b);
    var seed: u32 = 0x0888cafe;
    var raw: u32 = 1024;
    for (0..1024) |i| {
        raw +%= switch (i % 5) {
            0 => 0,
            1 => 1,
            2 => rand(&seed) & 63,
            3 => 54116,
            else => rand(&seed) & 1023,
        };
        if (i % 47 == 0) try p.put("dos64_pic_imr", 1, 1) else if (i % 47 == 3) try p.put("dos64_pic_imr", 0, 1);
        seedCia(&p.a, raw);
        seedCia(&p.b, raw);
        try p.call("dos64_native_timer_step");
        try p.check(i % 32 == 0);
    }
    try p.check(true);
}
test "optimized real CIA transient control gap resume and elapsed-wrap outputs match frozen reference" {
    var p = try Pair.init();
    defer p.deinit();
    try cia(&p.a, 0x0fffff00);
    try cia(&p.b, 0x0fffff00);
    for ([_]u32{ 0x0fffff01, 0x10000100, 0, 0x10000400, 0x18000401 }) |raw| {
        seedCia(&p.a, raw);
        seedCia(&p.b, raw);
        try p.call("dos64_pit_poll");
        try p.check(false);
    }
    try p.put("dos64_pit_now", 0xfffff000, 4);
    try p.call("dos64_pit_rebase");
    try p.put("dos64_cpu_status", 0, 1);
    for ([_]u32{ 0xfffff001, 0x00000400, 0x00000401 }) |raw| {
        seedCia(&p.a, raw);
        seedCia(&p.b, raw);
        try p.call("dos64_pit_poll");
        try p.check(false);
    }
    seedCia(&p.a, 0xc0000400);
    seedCia(&p.b, 0xc0000400);
    try p.call("dos64_native_timer_resume");
    try p.check(false);
    c.dos64_bus_write(p.a.machine, 0xdd0e, 0);
    c.dos64_bus_write(p.b.machine, 0xdd0e, 0);
    try p.call("dos64_pit_poll");
    try p.check(true);
}
fn sampledElement(f: anytype, raw: u32) !void {
    const sentinel = try f.symbol("fixture_return");
    const ret = sentinel -% 1;
    f.poke(0x1ff, @truncate(ret >> 8));
    f.poke(0x1fe, @truncate(ret));
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_cpu_step"), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
    const start = c.dos64_get_regs(f.machine).cycles;
    const boundary = try f.symbol("string_iteration_complete");
    var hit = false;
    while (c.dos64_get_regs(f.machine).cycles - start < 1000000) {
        const regs = c.dos64_get_regs(f.machine);
        if (regs.pc == sentinel) {
            try std.testing.expect(hit);
            try std.testing.expectEqual(@as(u8, 0xff), regs.sp);
            try std.testing.expectEqual(@as(u8, 0), regs.p & 1);
            return;
        }
        if (!hit and regs.pc == boundary) {
            seedCia(f, raw);
            hit = true;
        }
        c.dos64_step(f.machine);
    }
    return error.ElementSamplingBudget;
}
test "optimized threshold and frozen converter agree when a real CIA edge arrives inside final REP element" {
    const cases = [_]struct { prefix: u8, opcode: u8, equal: bool, samples: bool }{
        .{ .prefix = 0xf3, .opcode = 0xa4, .equal = true, .samples = true },
        .{ .prefix = 0xf3, .opcode = 0xa6, .equal = true, .samples = true },
        .{ .prefix = 0xf3, .opcode = 0xa6, .equal = false, .samples = false },
        .{ .prefix = 0xf2, .opcode = 0xa6, .equal = true, .samples = false },
        .{ .prefix = 0xf2, .opcode = 0xa6, .equal = false, .samples = true },
    };
    for (cases) |case| {
        var p = try Pair.init();
        defer p.deinit();
        try install(&p.a);
        try install(&p.b);
        inline for (.{ &p.a, &p.b }) |f| {
            try wordGuest(f, 16, 0x3000);
            try wordGuest(f, 2, 1);
            try guestWrite(f, 0x1200, case.prefix);
            try guestWrite(f, 0x1201, case.opcode);
            try guestWrite(f, 0x1202, 0xf4);
            try guestWrite(f, 0x30200, if (case.equal) 0xa0 else 0x5f);
            try sampledElement(f, 1024 + 54116);
        }
        try p.check(true);
        try std.testing.expectEqual(@as(u64, @intFromBool(case.samples)), try get(&p.a, "dos64_irq_result", 1));
        try std.testing.expectEqual(@as(u64, 0), try get(&p.a, "dos64_guest", 4) >> 16); // CX0
        try std.testing.expectEqual(@as(u64, if (case.samples) 1024 + 54116 else 1024), try get(&p.a, "dos64_pit_last", 4));
        if (case.samples) {
            // Run guest clock chain and re-fetched zero-count REP to retirement. Every
            // subsequent raw observation is fixed; neither backend repeats an element.
            for (0..24) |_| {
                try p.call("dos64_native_timer_step");
                try p.check(false);
            }
            try p.check(true);
        }
    }
}
test "all16 binary rational table entries agree with independent wide integer division" {
    var f = try o.Fixture.init();
    defer f.deinit();
    for (0..16) |i| {
        const scaled = (@as(u64, 1) << @as(u6, @intCast(i))) * 546875;
        const index: u16 = @intCast(i);
        // Lease the actual image before reading its linked table bytes.
        try set(&f, "dos64_overlay_requested", 4);
        _ = try invoke(&f, "dos64_overlay_acquire");
        const q = @as(u64, f.peek(try f.symbol("pit_qlo") + index)) | (@as(u64, f.peek(try f.symbol("pit_qhi") + index)) << 8);
        const rem = @as(u64, f.peek(try f.symbol("pit_rlo") + index)) | (@as(u64, f.peek(try f.symbol("pit_rmid") + index)) << 8) | (@as(u64, f.peek(try f.symbol("pit_rhi") + index)) << 16);
        try std.testing.expectEqual(scaled / 451572, q);
        try std.testing.expectEqual(scaled % 451572, rem);
        _ = try invoke(&f, "dos64_overlay_release");
    }
}
test "direct rebase and fast advance preserve every native flag including incoming decimal mode" {
    var p = try Pair.init();
    defer p.deinit();
    try p.put("dos64_pit_now", 1024, 4);
    try p.call("dos64_pit_init");
    for ([_]u8{ 0, 1, 8, 9, 0xff, 0x24, 0xc9, 0x7f }) |flags| {
        p.a.initial_status = flags;
        p.b.initial_status = flags;
        try p.put("dos64_pit_phase", 65534, 2);
        try p.put("dos64_pit_fraction", 451571, 3);
        try p.call("dos64_pit_rebase");
        try p.check(false);
        try std.testing.expectEqual(@as(u64, 1), try get(&p.a, "dos64_pit_until", 2));
        try p.put("dos64_pit_phase", 1200, 2);
        try p.put("dos64_pit_fraction", 400000, 3);
        try p.call("dos64_pit_rebase");
        try std.testing.expectEqual(threshold(1200, 400000), try get(&p.a, "dos64_pit_until", 2));
        const raw: u32 = @intCast(try get(&p.a, "dos64_pit_now", 4));
        try p.put("dos64_pit_now", raw +% 17, 4);
        try p.call("dos64_pit_advance");
        try p.check(false);
    }
}

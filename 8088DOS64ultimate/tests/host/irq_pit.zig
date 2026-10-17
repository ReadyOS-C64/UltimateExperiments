const std = @import("std");
const host = @import("machine_irq_pit.zig");
const Fixture = host.Fixture;
const c = host.c;
const g_ax = 0;
const g_cx = 2;
const g_sp = 8;
const g_si = 12;
const g_di = 14;
const g_es = 16;
const g_cs = 18;
const g_ss = 20;
const g_ds = 22;
const g_ip = 24;
const g_flags = 26;
fn put(f: *Fixture, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn get(f: *Fixture, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn gw(f: *Fixture, off: u16, v: u16) !void {
    const a = try f.symbol("dos64_guest") + off;
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn gr(f: *Fixture, off: u16) !u16 {
    return f.word(try f.symbol("dos64_guest") + off);
}
fn guestSnapshot(f: *Fixture) ![28]u8 {
    var a: [28]u8 = undefined;
    const g = try f.symbol("dos64_guest");
    for (&a, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    return a;
}
fn rw(f: *Fixture, a: u32, v: u16) void {
    c.dos64_reu_poke(f.machine, a, @truncate(v));
    c.dos64_reu_poke(f.machine, a + 1, @truncate(v >> 8));
}
fn readWord(f: *Fixture, a: u32) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, a)) | (@as(u16, c.dos64_reu_peek(f.machine, a + 1)) << 8);
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 100000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn write(f: *Fixture, a: u32, v: u8) !void {
    const p = try f.symbol("dos64_address");
    for (0..3) |i| f.poke(p + @as(u16, @intCast(i)), @truncate(a >> @as(u5, @intCast(i * 8))));
    try put(f, "dos64_mem_value", v);
    const r = try f.call("dos64_mem_write", 100000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    try put(&f, "dos64_cache_limit", 1);
    _ = try f.call("dos64_cache_init", 100000);
    _ = try f.call("dos64_cpu_init", 100000);
    _ = try f.call("dos64_io_init", 100000);
    const g = try f.symbol("dos64_guest");
    for (0..28) |i| f.poke(g + @as(u16, @intCast(i)), 0);
    try gw(&f, g_flags, 0xF202);
    try gw(&f, g_cs, 0x0100);
    try gw(&f, g_ip, 0x0200);
    try gw(&f, g_ss, 0x2000);
    try gw(&f, g_sp, 0x1000);
    try put(&f, "dos64_pic_imr", 0);
    try put(&f, "dos64_irq_callback_enabled", 0);
    rw(&f, 0x20, 0x0300);
    rw(&f, 0x22, 0x0400);
    c.dos64_reu_poke(f.machine, 0x4300, 0xcf);
    // Retained guest-memory failure oracles arm after the overlay is resident;
    // separate new tests inject acquisition failures before logical INTA.
    const warm = try f.call("dos64_irq_select", 100000);
    try std.testing.expectEqual(@as(u8, 0), warm.p & 1);
    return f;
}
fn pulse(f: *Fixture, irq: u8) !void {
    try put(f, "dos64_irq_line", irq);
    const r = try f.call("dos64_irq_pulse", 10000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn attempt(f: *Fixture, want: u8) !void {
    const r = try f.call("dos64_irq_try", 100000);
    try std.testing.expectEqual(@as(u8, if (want >= 2) 1 else 0), r.p & 1);
    try std.testing.expectEqual(want, try get(f, "dos64_irq_result"));
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
}
fn step(f: *Fixture) !void {
    const r = try f.call("dos64_cpu_step", 1000000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn io(f: *Fixture, v: u8) !void {
    const p = try f.symbol("dos64_io_port");
    f.poke(p, 0x20);
    f.poke(p + 1, 0);
    try put(f, "dos64_io_width", 0);
    try put(f, "dos64_io_value", v);
    const r = try f.call("dos64_io_write", 10000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn oracle(irr: u8, imr: u8, isr: u8, priority: u8, special: bool) u8 {
    const blockers = isr & (if (special) ~imr else @as(u8, 0xff));
    const requests = irr & ~imr;
    for (0..8) |rank| {
        const line: u3 = @truncate(@as(usize, priority) + 1 + rank);
        const bit = @as(u8, 1) << line;
        if (blockers & bit != 0) return 0xff;
        if (requests & bit != 0) return line;
    }
    return 0xff;
}
test "PIC edge pulse latches while masked and IFclear, coalesces, rejects invalid descriptor" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_pic_imr", 0xff);
    try gw(&f, g_flags, 0xf002);
    for (0..8) |i| {
        try pulse(&f, @intCast(i));
        try pulse(&f, @intCast(i));
        try std.testing.expectEqual(@as(u8, @truncate((@as(u16, 1) << @as(u4, @intCast(i + 1))) - 1)), try get(&f, "dos64_pic_irr"));
    }
    try attempt(&f, 0);
    for (8..256) |i| {
        try put(&f, "dos64_irq_line", @intCast(i));
        const r = try f.call("dos64_irq_pulse", 10000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0xff), try get(&f, "dos64_pic_irr"));
    }
}
test "PIC priority selection independent oracle 32768 combinations leaves controller unchanged" {
    var f = try init();
    defer f.deinit();
    const masks = [_]u8{ 0, 1, 0x80, 0x55, 0xaa, 0xfe, 0x7f, 0xff };
    var count: usize = 0;
    for (0..256) |irr| for (masks, 0..) |imr, mi| for (0..8) |pri| for (0..2) |special| {
        const isr: u8 = @truncate(irr * 37 + mi * 29 + pri * 73);
        try put(&f, "dos64_pic_irr", @intCast(irr));
        try put(&f, "dos64_pic_imr", imr);
        try put(&f, "dos64_pic_isr", isr);
        try put(&f, "dos64_pic_priority", @intCast(pri));
        try put(&f, "dos64_pic_special_mask", @intCast(special));
        const r = try f.call("dos64_irq_select", 10000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(oracle(@intCast(irr), imr, isr, @intCast(pri), special != 0), try get(&f, "dos64_irq_selected"));
        try std.testing.expectEqual(@as(u8, @intCast(irr)), try get(&f, "dos64_pic_irr"));
        try std.testing.expectEqual(isr, try get(&f, "dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8, @intCast(pri)), try get(&f, "dos64_pic_priority"));
        count += 1;
    };
    try std.testing.expectEqual(@as(usize, 32768), count);
}
test "all eight IRQ vectors original FLAGS frame count preserved and native status restored" {
    for (0..8) |line| for ([_]u8{ 0x20, 0x2e, 0xe8, 0xef }) |status| {
        var f = try init();
        defer f.deinit();
        f.initial_status = status;
        try gw(&f, g_flags, 0x0fff);
        try gw(&f, g_ax, 0x9a57);
        const before = try guestSnapshot(&f);
        const v: u32 = (@as(u32, @intCast(line)) + 0x28) * 4;
        try put(&f, "dos64_pic_base", 0x28);
        rw(&f, v, 0x5678);
        rw(&f, v + 2, 0x1234);
        try pulse(&f, @intCast(line));
        try attempt(&f, 1);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x5678), try gr(&f, g_ip));
        try std.testing.expectEqual(@as(u16, 0x1234), try gr(&f, g_cs));
        try std.testing.expectEqual(@as(u16, 0xffd7), readWord(&f, 0x20ffe));
        try std.testing.expectEqual(@as(u16, 0x0100), readWord(&f, 0x20ffc));
        try std.testing.expectEqual(@as(u16, 0x0200), readWord(&f, 0x20ffa));
        try std.testing.expectEqual(@as(u16, 0x0cff), try gr(&f, g_flags));
        try std.testing.expectEqual(@as(u8, 1) << @as(u3, @intCast(line)), try get(&f, "dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
        const after = try guestSnapshot(&f);
        for (0..24) |i| if (i < g_sp or i >= g_sp + 2) {
            if (i < g_cs or i >= g_cs + 2) try std.testing.expectEqual(before[i], after[i]);
        };
        const count = try f.symbol("dos64_cpu_instructions");
        try std.testing.expectEqual(@as(u16, 0), f.word(count));
        try std.testing.expectEqual(@as(u16, 0), f.word(count + 2));
    };
}
test "IVT read before aliasing stack writes and offset wrap are actual assembly behavior" {
    var f = try init();
    defer f.deinit();
    try gw(&f, g_ss, 0);
    try gw(&f, g_sp, 0x26);
    try pulse(&f, 0);
    try attempt(&f, 1);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x300), try gr(&f, g_ip));
    try std.testing.expectEqual(@as(u16, 0x400), try gr(&f, g_cs));
    try std.testing.expectEqual(@as(u16, 0x200), readWord(&f, 0x20));
    try std.testing.expectEqual(@as(u16, 0x100), readWord(&f, 0x22));
    var w = try init();
    defer w.deinit();
    try gw(&w, g_sp, 4);
    try pulse(&w, 0);
    try attempt(&w, 1);
    try flush(&w);
    try std.testing.expectEqual(@as(u16, 0xfffe), try gr(&w, g_sp));
    try std.testing.expectEqual(@as(u16, 0x200), readWord(&w, 0x2fffe));
    try std.testing.expectEqual(@as(u16, 0x100), readWord(&w, 0x20000));
}
test "nested priority blocks same lower IRQ and EOI admits pending request" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_pic_irr", 0x14);
    rw(&f, 0x28, 0x300);
    rw(&f, 0x2a, 0x400);
    try attempt(&f, 1);
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_pic_isr"));
    try gw(&f, g_flags, 0xf202);
    try attempt(&f, 0);
    try pulse(&f, 1);
    rw(&f, 0x24, 0x300);
    rw(&f, 0x26, 0x400);
    try attempt(&f, 1);
    try std.testing.expectEqual(@as(u8, 6), try get(&f, "dos64_pic_isr"));
    try io(&f, 0x20);
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_pic_isr"));
    try gw(&f, g_flags, 0xf202);
    try attempt(&f, 0);
    try io(&f, 0x62);
    try attempt(&f, 1);
    try std.testing.expectEqual(@as(u8, 16), try get(&f, "dos64_pic_isr"));
}
test "AEOI rotation changes lowest priority only when enabled unsupported modes have no effects" {
    for (0..8) |line| for (0..2) |rotate| {
        var f = try init();
        defer f.deinit();
        try put(&f, "dos64_pic_icw4", 3);
        try put(&f, "dos64_pic_rotate_auto", @intCast(rotate));
        try pulse(&f, @intCast(line));
        try attempt(&f, 1);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8, if (rotate == 1) @intCast(line) else 7), try get(&f, "dos64_pic_priority"));
    };
    const modes = [_][3]u8{ .{ 0x11, 9, 0 }, .{ 0x1b, 9, 0 }, .{ 0x13, 8, 0 }, .{ 0x13, 0x11, 0 }, .{ 0x13, 0x0b, 0 }, .{ 0x13, 9, 2 } };
    for (modes) |mode| {
        var f = try init();
        defer f.deinit();
        try put(&f, "dos64_pic_icw1", mode[0]);
        try put(&f, "dos64_pic_icw4", mode[1]);
        try put(&f, "dos64_pic_phase", mode[2]);
        try pulse(&f, 0);
        const before = try guestSnapshot(&f);
        try attempt(&f, 3);
        try std.testing.expectEqualSlices(u8, &before, &try guestSnapshot(&f));
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_irr"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
    }
}
test "STI MOVSS POPSS shadow blocks one complete next instruction and HLT wakes" {
    const programs = [_][]const u8{ &.{ 0xfb, 0x90, 0xf4 }, &.{ 0x8e, 0xd0, 0x90, 0xf4 }, &.{ 0x17, 0x90, 0xf4 } };
    for (programs, 0..) |code, i| {
        var f = try init();
        defer f.deinit();
        for (code, 0..) |v, j| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(j)), v);
        if (i == 0) try gw(&f, g_flags, 0xf002);
        if (i == 1) try gw(&f, g_ax, 0x2000);
        if (i == 2) rw(&f, 0x21000, 0x2000);
        try step(&f);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_irq_shadow"));
        try pulse(&f, 0);
        try attempt(&f, 0);
        try step(&f);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_cpu_irq_shadow"));
        try attempt(&f, 1);
    }
    var h = try init();
    defer h.deinit();
    c.dos64_reu_poke(h.machine, 0x1200, 0xf4);
    try step(&h);
    try std.testing.expectEqual(@as(u8, 1), try get(&h, "dos64_cpu_status"));
    try gw(&h, g_flags, 0xf002);
    try pulse(&h, 0);
    try attempt(&h, 0);
    try std.testing.expectEqual(@as(u8, 1), try get(&h, "dos64_cpu_status"));
    try gw(&h, g_flags, 0xf202);
    try attempt(&h, 1);
    try std.testing.expectEqual(@as(u8, 0), try get(&h, "dos64_cpu_status"));
    try flush(&h);
    try std.testing.expectEqual(@as(u16, 0x201), readWord(&h, 0x20ffa));
}
test "prefix-only yield cannot acknowledge IRQ and last prefix is REP interrupt restart" {
    var f = try init();
    defer f.deinit();
    for (0..64) |j| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(j)), 0x3e);
    c.dos64_reu_poke(f.machine, 0x1240, 0x90);
    try step(&f);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_pending"));
    try pulse(&f, 0);
    try attempt(&f, 0);
    try step(&f);
    try attempt(&f, 1);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x241), readWord(&f, 0x20ffa));
}
fn repInit(code: []const u8, count: u16) !Fixture {
    var f = try init();
    errdefer f.deinit();
    try gw(&f, g_ds, 0x3000);
    try gw(&f, g_es, 0x4000);
    try gw(&f, g_si, 0x100);
    try gw(&f, g_di, 0x200);
    try gw(&f, g_cx, count);
    for (code, 0..) |v, j| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(j)), v);
    for (0..40) |j| {
        c.dos64_reu_poke(f.machine, 0x30100 + @as(u32, @intCast(j)), @truncate(0x20 + j));
        c.dos64_reu_poke(f.machine, 0x40100 + @as(u32, @intCast(j)), @truncate(0xa0 + j));
    }
    return f;
}
test "REP accepts after first iteration shadow expires and IRET completes exactly once" {
    var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 33);
    defer f.deinit();
    try put(&f, "dos64_cpu_irq_shadow", 1);
    try pulse(&f, 0);
    try attempt(&f, 0);
    try put(&f,"dos64_irq_callback_enabled",1);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 32), try gr(&f, g_cx));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_cpu_irq_shadow"));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_irq_result"));
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x200), readWord(&f, 0x20ffa));
    try io(&f, 0x20);
    try step(&f); // actual guest IRET
    for (0..32) |_| try step(&f);
    try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
    try std.testing.expectEqual(@as(u16, 0x121), try gr(&f, g_si));
    try std.testing.expectEqual(@as(u16, 0x221), try gr(&f, g_di));
    try flush(&f);
    for (0..33) |j| try std.testing.expectEqual(@as(u8, @truncate(0x20 + j)), c.dos64_reu_peek(f.machine, 0x40200 + @as(u32, @intCast(j))));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x40221));
}
test "original8088 multiple prefix loss is explicit for override REP and REP override orders" {
    for (0..2) |order| {
        const code: []const u8 = if (order == 0) &.{ 0x26, 0xf3, 0xa4, 0xf4 } else &.{ 0xf3, 0x26, 0xa4, 0xf4 };
        var f = try repInit(code, 5);
        defer f.deinit();
        try put(&f,"dos64_irq_callback_enabled",1);
        try pulse(&f,0);
        try step(&f);
        try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_irq_result"));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x201), readWord(&f, 0x20ffa));
        try io(&f, 0x20);
        try step(&f);
        if (order == 0) {
            for (0..4) |_| {
                try step(&f);
            }
        } else {
            try step(&f);
        }
        try flush(&f);
        try std.testing.expectEqual(@as(u8, 0xa0), c.dos64_reu_peek(f.machine, 0x40200));
        if (order == 0) {
            try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
            for (1..5) |j| try std.testing.expectEqual(@as(u8, @truncate(0x20 + j)), c.dos64_reu_peek(f.machine, 0x40200 + @as(u32, @intCast(j))));
        } else {
            try std.testing.expectEqual(@as(u16, 4), try gr(&f, g_cx));
            try std.testing.expectEqual(@as(u8, 0xa1), c.dos64_reu_peek(f.machine, 0x40201));
            try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x40202));
        }
    }
}
test "dirty mutable IVT is authoritative and failed DMA is terminal after acknowledge without duplicate" {
    var f = try init();
    defer f.deinit();
    try write(&f, 0x20, 0x45);
    try write(&f, 0x21, 0x23);
    try write(&f, 0x22, 0x78);
    try write(&f, 0x23, 0x56);
    try pulse(&f, 0);
    try attempt(&f, 1);
    try std.testing.expectEqual(@as(u16, 0x2345), try gr(&f, g_ip));
    try std.testing.expectEqual(@as(u16, 0x5678), try gr(&f, g_cs));
    for (0..5) |fail_after| {
        var w = try init();
        defer w.deinit();
        c.dos64_reu_fail_after(w.machine, @intCast(fail_after), 17);
        try pulse(&w, 0);
        const r = try w.call("dos64_irq_try", 100000);
        if (r.p & 1 == 0) {
            try std.testing.expectEqual(@as(u8, 1), try get(&w, "dos64_irq_result"));
            continue;
        }
        try std.testing.expectEqual(@as(u8, 2), try get(&w, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u8, 3), try get(&w, "dos64_cpu_status"));
        try std.testing.expectEqual(@as(u8, 0), try get(&w, "dos64_pic_irr"));
        try std.testing.expectEqual(@as(u8, 1), try get(&w, "dos64_pic_isr"));
        const snapshot = try guestSnapshot(&w);
        try attempt(&w, 0);
        try std.testing.expectEqualSlices(u8, &snapshot, &try guestSnapshot(&w));
    }
}
test "IRQ during REP re-fetches mutable instruction bytes instead of retained decode" {
    var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 4);
    defer f.deinit();
    try put(&f,"dos64_irq_callback_enabled",1);
    try pulse(&f,0);
    try step(&f);
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_irq_result"));
    // Handler changes MOVSB to STOSB through coherent guest memory.
    try write(&f, 0x1201, 0xaa);
    try gw(&f, g_ax, 0x765a);
    try io(&f, 0x20);
    try step(&f);
    for (0..3) |_| try step(&f);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x101), try gr(&f, g_si));
    try std.testing.expectEqual(@as(u16, 0x204), try gr(&f, g_di));
    try std.testing.expectEqual(@as(u8, 0x20), c.dos64_reu_peek(f.machine, 0x40200));
    for (1..4) |i| try std.testing.expectEqual(@as(u8, 0x5a), c.dos64_reu_peek(f.machine, 0x40200 + @as(u32, @intCast(i))));
}
test "REP word copies in both DF directions preserve each element around an IRQ" {
    for ([_]u16{ 0xf202, 0xf602 }) |flags| {
        var f = try repInit(&.{ 0xf3, 0xa5, 0xf4 }, 5);
        defer f.deinit();
        try gw(&f, g_flags, flags);
        if (flags & 0x400 != 0) {
            try gw(&f, g_si, 0x108);
            try gw(&f, g_di, 0x208);
        }
        try put(&f,"dos64_irq_callback_enabled",1);
        try pulse(&f,0);
        try step(&f);
        try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_irq_result"));
        try io(&f, 0x20);
        try step(&f);
        for (0..3) |_| try step(&f);
        try flush(&f);
        for (0..10) |i| try std.testing.expectEqual(@as(u8, @truncate(0x20 + i)), c.dos64_reu_peek(f.machine, 0x40200 + @as(u32, @intCast(i))));
        try std.testing.expectEqual(@as(u16, if (flags & 0x400 == 0) 0x10a else 0xfe), try gr(&f, g_si));
        try std.testing.expectEqual(@as(u16, if (flags & 0x400 == 0) 0x20a else 0x1fe), try gr(&f, g_di));
        try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
    }
}
test "REPE and REPNE compare termination stops restart and saves last completed FLAGS" {
    for ([_]u8{ 0xf2, 0xf3 }) |rep| {
        var f = try repInit(&.{ rep, 0xa6, 0xf4 }, 6);
        defer f.deinit();
        // First three comparisons continue, fourth terminates.
        for (0..6) |i| c.dos64_reu_poke(f.machine, 0x40200 + @as(u32, @intCast(i)), @truncate(0x20 + i + @as(usize, if ((rep == 0xf2 and i < 3) or (rep == 0xf3 and i >= 3)) 1 else 0)));
        try put(&f,"dos64_irq_callback_enabled",1);
        try pulse(&f,0);
        try step(&f);
        try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_irq_result"));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x200), readWord(&f, 0x20ffa));
        const saved_flags = readWord(&f, 0x20ffe);
        try std.testing.expectEqual(@as(u16, if (rep == 0xf3) 0x40 else 0), saved_flags & 0x40);
        try io(&f, 0x20);
        try step(&f); // IRET
        try step(&f); // remaining comparisons terminate before HLT
        try std.testing.expectEqual(@as(u16, 2), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u16, 0x104), try gr(&f, g_si));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_string_pending"));
        try pulse(&f, 0);
        try attempt(&f, 1);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x202), readWord(&f, 0x20ffa));
    }
}
test "representative frame changes only six guest bytes with cache and native state guards" {
    var f = try init();
    defer f.deinit();
    const low = try f.symbol("dos64_irq_state_start");
    const high = try f.symbol("dos64_irq_state_end");
    f.poke(low - 1, 0x69);
    f.poke(high, 0x96);
    var expected: [640 * 1024]u8 = undefined;
    for (&expected, 0..) |*v, i| v.* = c.dos64_reu_peek(f.machine, @intCast(i));
    const values = [_]u8{ 0, 2, 0, 1, 2, 0xf2 }; // IP0200,CS0100,FLAGSF202
    @memcpy(expected[0x20ffa..0x21000], &values);
    try pulse(&f, 0);
    try attempt(&f, 1);
    try flush(&f);
    for (expected, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_reu_peek(f.machine, @intCast(i)));
    try std.testing.expectEqual(@as(u8, 0x69), f.peek(low - 1));
    try std.testing.expectEqual(@as(u8, 0x96), f.peek(high));
}
test "bounded helper native cycle samples and acknowledgement failure stages" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_irq_line", 0);
    var before = c.dos64_get_regs(f.machine).cycles;
    var r = try f.call("dos64_irq_pulse", 100000);
    const pulse_cycles = r.cycles - before;
    try gw(&f, g_flags, 0xf002);
    before = c.dos64_get_regs(f.machine).cycles;
    r = try f.call("dos64_irq_try", 100000);
    const disabled_cycles = r.cycles - before;
    try gw(&f, g_flags, 0xf202);
    before = c.dos64_get_regs(f.machine).cycles;
    r = try f.call("dos64_irq_select", 100000);
    const select_cycles = r.cycles - before;
    before = c.dos64_get_regs(f.machine).cycles;
    r = try f.call("dos64_irq_try", 100000);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_irq_result"));
    std.debug.print("IRQ_METRICS pulse={d} disabled={d} select0={d} cold_frame1={d} CPUcycles\n", .{ pulse_cycles, disabled_cycles, select_cycles, r.cycles - before });
    for (0..5) |fail_after| {
        var w = try init();
        defer w.deinit();
        c.dos64_reu_fail_after(w.machine, @intCast(fail_after), 17);
        try pulse(&w, 0);
        before = c.dos64_get_regs(w.machine).cycles;
        r = try w.call("dos64_irq_try", 100000);
        std.debug.print("IRQ_FAILURE_STAGE after={d} carry={d} result={d} status={d} sp={x} cycles={d}\n", .{ fail_after, r.p & 1, try get(&w, "dos64_irq_result"), try get(&w, "dos64_cpu_status"), try gr(&w, g_sp), r.cycles - before });
    }
}
fn runUntil(f: *Fixture, ip: u16) !void {
    for (0..100) |_| {
        if (try gr(f, g_cs) == 0x100 and try gr(f, g_ip) == ip) return;
        try step(f);
    }
    return error.GuestTimerBudget;
}
test "guest INT08 updates BDA once calls mutable INT1C then EOI and replacement INT08 owns behavior" {
    const timer = @embedFile("guest_timer.bin");
    for ([_]u32{ 0, 0xffff, 0x1800af, 0xffffffff }) |start| {
        var f = try init();
        defer f.deinit();
        try gw(&f, g_ax, 0xa571);
        try gw(&f, g_ds, 0x7654);
        for (timer, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4300 + @as(u32, @intCast(i)), v);
        // Mutable hook code counts calls in CS-relative data, then actual IRET.
        const hook1 = [_]u8{ 0x2e, 0xff, 0x06, 0x00, 0x05, 0xcf };
        const hook2 = [_]u8{ 0x2e, 0xff, 0x06, 0x02, 0x05, 0xcf };
        const replace8 = [_]u8{ 0x2e, 0xff, 0x06, 0x04, 0x05, 0x50, 0xb0, 0x20, 0xe6, 0x20, 0x58, 0xcf };
        for (hook1, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4400 + @as(u32, @intCast(i)), v);
        for (hook2, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4420 + @as(u32, @intCast(i)), v);
        for (replace8, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4600 + @as(u32, @intCast(i)), v);
        for (0..3) |i| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(i)), 0x90);
        rw(&f, 0x70, 0x400);
        rw(&f, 0x72, 0x400);
        rw(&f, 0x46c, @truncate(start));
        rw(&f, 0x46e, @truncate(start >> 16));
        try pulse(&f, 0);
        try attempt(&f, 1);
        try runUntil(&f, 0x200);
        try flush(&f);
        const expected: u32 = if (start == 0x1800af) 0 else start +% 1;
        try std.testing.expectEqual(@as(u16, @truncate(expected)), readWord(&f, 0x46c));
        try std.testing.expectEqual(@as(u16, @truncate(expected >> 16)), readWord(&f, 0x46e));
        try std.testing.expectEqual(@as(u8, if (start == 0x1800af) 1 else 0), c.dos64_reu_peek(f.machine, 0x470));
        try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4500));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
        try std.testing.expectEqual(@as(u16, 0xa571), try gr(&f, g_ax));
        try std.testing.expectEqual(@as(u16, 0x7654), try gr(&f, g_ds));
        try step(&f); // next guest NOP completes IRET's original IF transition shadow
        try write(&f, 0x70, 0x20);
        try write(&f, 0x71, 0x04);
        try pulse(&f, 0);
        try attempt(&f, 1);
        try runUntil(&f, 0x201);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4500));
        try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4502));
        const second = expected +% 1;
        try std.testing.expectEqual(@as(u16, @truncate(second)), readWord(&f, 0x46c));
        try std.testing.expectEqual(@as(u16, @truncate(second >> 16)), readWord(&f, 0x46e));
        try step(&f);
        try write(&f, 0x20, 0x00);
        try write(&f, 0x21, 0x06);
        try pulse(&f, 0);
        try attempt(&f, 1);
        try runUntil(&f, 0x202);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4504));
        try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4502));
        // Replacing INT08 suppresses the default BDA service entirely.
        try std.testing.expectEqual(@as(u16, @truncate(second)), readWord(&f, 0x46c));
        try std.testing.expectEqual(@as(u16, @truncate(second >> 16)), readWord(&f, 0x46e));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
    }
}
// Inject an external request after the native string element commits, before
// its interrupt/end checks. This is controlled instruction stepping of the
// actual6510 core, not an x86 host implementation or timing model.
fn stepInjectAt(f: *Fixture, entry: []const u8, irq_mask: u8) !void {
    return stepInjectWithFailure(f, entry, irq_mask, null);
}
fn stepInjectWithFailure(f: *Fixture, entry: []const u8, irq_mask: u8, fail_after: ?u64) !void {
    const sentinel = try f.symbol("fixture_return");
    const ret = sentinel -% 1;
    f.poke(0x1ff, @truncate(ret >> 8));
    f.poke(0x1fe, @truncate(ret));
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_cpu_step"), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = f.initial_status, .cycles = 0, .instructions = 0 });
    const start = c.dos64_get_regs(f.machine).cycles;
    const inject_pc = try f.symbol(entry);
    var injected = false;
    while (c.dos64_get_regs(f.machine).cycles - start < 1000000) {
        const regs = c.dos64_get_regs(f.machine);
        if (regs.pc == sentinel) {
            try std.testing.expect(injected);
            try std.testing.expectEqual(@as(u8, 0xff), regs.sp);
            try std.testing.expectEqual(@as(u8, 0), c.dos64_model_fault(f.machine));
            return;
        }
        if (regs.pc == inject_pc and !injected) {
            try put(f, "dos64_pic_irr", try get(f, "dos64_pic_irr") | irq_mask);
            if (fail_after) |n| c.dos64_reu_fail_after(f.machine, n, 17);
            injected = true;
        }
        c.dos64_step(f.machine);
    }
    return error.NativeInjectionBudget;
}
test "in-core REP callback samples final element before CXzero for all ten string opcodes" {
    for ([_]u8{ 0xa4, 0xa5, 0xa6, 0xa7, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf }) |opcode| {
        var f = try repInit(&.{ 0xf3, opcode, 0xf4 }, 1);
        defer f.deinit();
        try put(&f, "dos64_irq_callback_enabled", 1);
        try gw(&f, g_ax, 0x2120);
        if (opcode & 0xfe == 0xa6 or opcode & 0xfe == 0xae) {
            c.dos64_reu_poke(f.machine, 0x40200, 0x20);
            c.dos64_reu_poke(f.machine, 0x40201, 0x21);
        }
        try stepInjectAt(&f, "string_iteration_complete", 1);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u16, 0x300), try gr(&f, g_ip));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_string_pending"));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x200), readWord(&f, 0x20ffa));
        const count = try f.symbol("dos64_cpu_instructions");
        try std.testing.expectEqual(@as(u16, 0), f.word(count));
        const si = try gr(&f, g_si);
        const di = try gr(&f, g_di);
        const ax = try gr(&f, g_ax);
        // Real IRET followed by re-fetched REP with CX=0 copies/compares none.
        try io(&f, 0x20);
        try step(&f);
        try step(&f);
        try std.testing.expectEqual(si, try gr(&f, g_si));
        try std.testing.expectEqual(di, try gr(&f, g_di));
        try std.testing.expectEqual(ax, try gr(&f, g_ax));
        try std.testing.expectEqual(@as(u16, 0x202), try gr(&f, g_ip));
        try std.testing.expectEqual(@as(u16, 2), f.word(count));
    }
}
test "compare condition termination precedes INTR sampling for REPE REPNE byte and word" {
    for ([_]u8{ 0xa6, 0xa7, 0xae, 0xaf }) |opcode| {
        for ([_]u8{ 0xf2, 0xf3 }) |rep| {
            for ([_]u16{ 1, 2 }) |count| {
                var f = try repInit(&.{ rep, opcode, 0xf4 }, count);
                defer f.deinit();
                try put(&f, "dos64_irq_callback_enabled", 1);
                try gw(&f, g_ax, 0x2120);
                // REPE stops on inequality; REPNE stops on equality.
                c.dos64_reu_poke(f.machine, 0x40200, if (rep == 0xf3) 0x21 else 0x20);
                c.dos64_reu_poke(f.machine, 0x40201, 0x21);
                try stepInjectAt(&f, "string_iteration_complete", 1);
                try std.testing.expectEqual(@as(u16, count - 1), try gr(&f, g_cx));
                try std.testing.expectEqual(@as(u16, 0x202), try gr(&f, g_ip));
                try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_string_pending"));
                try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_irr"));
                try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
                try attempt(&f, 1);
                try flush(&f);
                try std.testing.expectEqual(@as(u16, 0x202), readWord(&f, 0x20ffa));
                try std.testing.expectEqual(@as(u16, if (rep == 0xf2) 0x40 else 0), readWord(&f, 0x20ffe) & 0x40);
            }
        }
    }
}
test "masked IFclear or nestedblocked final REP element retires normally without rewinding" {
    for (0..3) |condition| {
        var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 1);
        defer f.deinit();
        try put(&f, "dos64_irq_callback_enabled", 1);
        if (condition == 0) try put(&f, "dos64_pic_imr", 1);
        if (condition == 1) try gw(&f, g_flags, 0xf002);
        if (condition == 2) try put(&f, "dos64_pic_isr", 1);
        try stepInjectAt(&f, "string_iteration_complete", 1);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u16, 0x202), try gr(&f, g_ip));
        try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_irr"));
    }
}
test "STI0to1 defers then repeated STI with IF1 does not extend its shadow" {
    var f = try init();
    defer f.deinit();
    try gw(&f, g_flags, 0xf002);
    c.dos64_reu_poke(f.machine, 0x1200, 0xfb);
    c.dos64_reu_poke(f.machine, 0x1201, 0xfb);
    c.dos64_reu_poke(f.machine, 0x1202, 0x90);
    try step(&f);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_irq_shadow"));
    try pulse(&f, 0);
    try attempt(&f, 0);
    try step(&f);
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_cpu_irq_shadow"));
    try attempt(&f, 1);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x202), readWord(&f, 0x20ffa));
    var w = try init();
    defer w.deinit();
    c.dos64_reu_poke(w.machine, 0x1200, 0xfb);
    try step(&w);
    try std.testing.expectEqual(@as(u8, 0), try get(&w, "dos64_cpu_irq_shadow"));
    try pulse(&w, 0);
    try attempt(&w, 1);
    try flush(&w);
    try std.testing.expectEqual(@as(u16, 0x201), readWord(&w, 0x20ffa));
}
test "previous STI MOVSS POPSS shadow expires at first REP element before callback acceptance" {
    const leads = [_][]const u8{ &.{0xfb}, &.{ 0x8e, 0xd0 }, &.{0x17} };
    for (leads, 0..) |lead, kind| {
        var f = try repInit(&.{0x90}, 2);
        defer f.deinit();
        try put(&f, "dos64_irq_callback_enabled", 1);
        for (lead, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(i)), v);
        c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(lead.len)), 0xf3);
        c.dos64_reu_poke(f.machine, 0x1201 + @as(u32, @intCast(lead.len)), 0xa4);
        if (kind == 0) try gw(&f, g_flags, 0xf002);
        if (kind == 1) try gw(&f, g_ax, 0x2000);
        if (kind == 2) rw(&f, 0x21000, 0x2000);
        try step(&f);
        try pulse(&f, 0);
        try attempt(&f, 0);
        try step(&f);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u16, 1), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u16, 0x101), try gr(&f, g_si));
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x200 + @as(u16, @intCast(lead.len))), readWord(&f, if (kind == 2) 0x20ffc else 0x20ffa));
    }
}
test "repaired NMOS8088 MOV ES CS SS DS and POP ES SS DS all inhibit next instruction" {
    for ([_]u8{ 0xc0, 0xc8, 0xd0, 0xd8 }) |modrm| {
        var f = try init();
        defer f.deinit();
        const segment = (@as(u16, modrm >> 3) & 3) * 2 + 16;
        const value: u16 = if (segment == g_cs) 0x100 else 0x2000;
        try gw(&f, g_ax, value);
        c.dos64_reu_poke(f.machine, 0x1200, 0x8e);
        c.dos64_reu_poke(f.machine, 0x1201, modrm);
        c.dos64_reu_poke(f.machine, 0x1202, 0x90);
        try step(&f);
        try std.testing.expectEqual(value, try gr(&f, segment));
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_irq_shadow"));
        try pulse(&f, 0);
        try attempt(&f, 0);
        try step(&f);
        try attempt(&f, 1);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x203), readWord(&f, 0x20ffa));
    }
    for ([_]u8{ 0x07, 0x17, 0x1f }) |opcode| {
        var f = try init();
        defer f.deinit();
        c.dos64_reu_poke(f.machine, 0x1200, opcode);
        c.dos64_reu_poke(f.machine, 0x1201, 0x90);
        rw(&f, 0x21000, 0x2000);
        try step(&f);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_irq_shadow"));
        try pulse(&f, 0);
        try attempt(&f, 0);
        try step(&f);
        try attempt(&f, 1);
        try flush(&f);
        try std.testing.expectEqual(@as(u16, 0x202), readWord(&f, 0x20ffc));
    }
}
test "PUSH segments MOV from segments general POP LDS LES never gain a segment load shadow" {
    const programs = [_][]const u8{ &.{0x06}, &.{0x0e}, &.{0x16}, &.{0x1e}, &.{0x58}, &.{ 0x8c, 0xc0 }, &.{ 0x8c, 0xc8 }, &.{ 0x8c, 0xd0 }, &.{ 0x8c, 0xd8 }, &.{ 0xc4, 0x06, 0x00, 0x04 }, &.{ 0xc5, 0x06, 0x00, 0x04 } };
    for (programs) |program| {
        var f = try init();
        defer f.deinit();
        for (program, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(i)), v);
        rw(&f, 0x400, 0xabcd);
        rw(&f, 0x402, 0x3000);
        try step(&f);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_cpu_irq_shadow"));
        try pulse(&f, 0);
        try attempt(&f, 1);
        try std.testing.expectEqual(@as(u16, 0x300), try gr(&f, g_ip));
    }
}
test "chained MOV and POP segment shadows extend through final load then one following instruction" {
    var f = try init();
    defer f.deinit();
    const code = [_]u8{ 0x8e, 0xc0, 0x8e, 0xd8, 0x07, 0x90 };
    for (code, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(i)), v);
    try gw(&f, g_ax, 0x3000);
    rw(&f, 0x21000, 0x4000);
    try step(&f);
    try pulse(&f, 0);
    try attempt(&f, 0);
    try step(&f);
    try attempt(&f, 0);
    try step(&f);
    try attempt(&f, 0);
    try step(&f);
    try attempt(&f, 1);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x206), readWord(&f, 0x20ffc));
}
test "in-core IRQ DMA failure preserves completed REP element and latches terminal ownership" {
    for ([_]u64{ 0, 1, 2 }) |after| {
        var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 1);
        defer f.deinit();
        try put(&f, "dos64_irq_callback_enabled", 1);
        // Failure armed only after the element writes, at the source microcode
        // sample boundary. No earlier instruction/cache work consumes it.
        try stepInjectWithFailure(&f, "string_iteration_complete", 1, after);
        try std.testing.expectEqual(@as(u8, 2), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_cpu_status"));
        try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u16, 0x101), try gr(&f, g_si));
        try std.testing.expectEqual(@as(u16, 0x201), try gr(&f, g_di));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_isr"));
        const before = try guestSnapshot(&f);
        const result = try f.call("dos64_cpu_step", 10000);
        try std.testing.expectEqual(@as(u8, 1), result.p & 1);
        try attempt(&f, 0);
        try std.testing.expectEqualSlices(u8, &before, &try guestSnapshot(&f));
        try flush(&f);
        try std.testing.expectEqual(@as(u8, 0x20), c.dos64_reu_peek(f.machine, 0x40200));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x40201));
    }
}
fn putWide(f: *Fixture, name: []const u8, n: u64, bytes: usize) !void {
    const a = try f.symbol(name);
    for (0..bytes) |i| f.poke(a + @as(u16, @intCast(i)), @truncate(n >> @as(u6, @intCast(i * 8))));
}
fn getWide(f: *Fixture, name: []const u8, bytes: usize) !u64 {
    const a = try f.symbol(name);
    var n: u64 = 0;
    for (0..bytes) |i| n |= @as(u64, f.peek(a + @as(u16, @intCast(i)))) << @as(u6, @intCast(i * 8));
    return n;
}
fn pitInit(f: *Fixture, epoch: u32) !void {
    try putWide(f, "dos64_pit_now", epoch, 4);
    const r = try f.call("dos64_pit_init", 10000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
var pit_max_observed: u64 = 0;
fn pitAdvance(f: *Fixture, now: u32, failed: bool) !u64 {
    try putWide(f, "dos64_pit_now", now, 4);
    const start = c.dos64_get_regs(f.machine).cycles;
    const r = try f.call("dos64_pit_advance", 100000);
    try std.testing.expectEqual(@as(u8, @intFromBool(failed)), r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    const measured = r.cycles - start;
    pit_max_observed = @max(pit_max_observed, measured);
    return measured;
}
const PitOracle = struct {
    fraction: u64 = 0,
    phase: u64 = 0,
    total: u64 = 0,
    fn advance(self: *PitOracle, delta: u32) u64 {
        const scaled = @as(u64, delta) * 546875 + self.fraction;
        const cycles = scaled / 451572;
        self.fraction = scaled % 451572;
        const combined = self.phase + cycles;
        const edges = combined / 65536;
        self.phase = combined % 65536;
        self.total = (self.total + edges) & 0xffffffff;
        return edges;
    }
    fn expect(self: PitOracle, f: *Fixture, edges: u64) !void {
        try std.testing.expectEqual(self.fraction, try getWide(f, "dos64_pit_fraction", 3));
        try std.testing.expectEqual(self.phase, try getWide(f, "dos64_pit_phase", 2));
        try std.testing.expectEqual(self.total, try getWide(f, "dos64_pit_total", 4));
        try std.testing.expectEqual(edges, try getWide(f, "dos64_pit_edges", 2));
    }
};
fn ciaInitAt(f: *Fixture, raw: u32) !void {
    c.dos64_cia_clock_enable(f.machine);
    try put(f, "dos64_host_clock_claim", 0xa5);
    const r = try f.call("dos64_host_clock_init", 10000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    ciaSeed(f, raw);
}
fn ciaSeed(f: *Fixture, raw: u32) void {
    c.dos64_cia_clock_seed(f.machine, ~@as(u16, @truncate(raw)), ~@as(u16, @truncate(raw >> 16)));
}
fn stepCIAAtElement(f: *Fixture, delta: u32) !void {
    const sentinel = try f.symbol("fixture_return");
    const ret = sentinel -% 1;
    f.poke(0x1ff, @truncate(ret >> 8));
    f.poke(0x1fe, @truncate(ret));
    c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_cpu_step"), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = f.initial_status, .cycles = 0, .instructions = 0 });
    const start = c.dos64_get_regs(f.machine).cycles;
    const sample = try f.symbol("string_iteration_complete");
    var advanced = false;
    while (c.dos64_get_regs(f.machine).cycles - start < 1000000) {
        const r = c.dos64_get_regs(f.machine);
        if (r.pc == sentinel) {
            try std.testing.expect(advanced);
            try std.testing.expectEqual(@as(u8, 0xff), r.sp);
            try std.testing.expectEqual(@as(u8, 0), c.dos64_model_fault(f.machine));
            return;
        }
        if (r.pc == sample and !advanced) {
            c.dos64_cia_clock_advance(f.machine, delta);
            advanced = true;
        }
        c.dos64_step(f.machine);
    }
    return error.NativeCIAPollBudget;
}
fn installTimer(f: *Fixture, start: u32) !void {
    const timer = @embedFile("guest_timer.bin");
    for (timer, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4300 + @as(u32, @intCast(i)), v);
    const hook = [_]u8{ 0x2e, 0xff, 0x06, 0x00, 0x05, 0xcf };
    for (hook, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4400 + @as(u32, @intCast(i)), v);
    rw(f, 0x70, 0x400);
    rw(f, 0x72, 0x400);
    rw(f, 0x46c, @truncate(start));
    rw(f, 0x46e, @truncate(start >> 16));
    for (0..4) |i| c.dos64_reu_poke(f.machine, 0x1200 + @as(u32, @intCast(i)), 0x90);
}
test "PIT rational conversion wide oracle 512 deterministic varied deltas and modulo host epochs" {
    var f = try init();
    defer f.deinit();
    var now: u32 = 0xffff1234;
    try pitInit(&f, now);
    var pit_oracle: PitOracle = .{};
    var seed: u32 = 0x08088253;
    const cases = [_]u32{ 0, 1, 2, 255, 256, 4095, 4096, 54115, 54116, 65535, 65536, 985248, 451571, 451572, 0x07fff000 };
    for (0..512) |i| {
        seed = seed *% 1664525 +% 1013904223;
        const delta: u32 = if (i < cases.len) cases[i] else seed % 0x07fff001;
        now +%= delta;
        const edges = pit_oracle.advance(delta);
        _ = try pitAdvance(&f, now, false);
        try pit_oracle.expect(&f, edges);
        try std.testing.expectEqual(@as(u64, now), try getWide(&f, "dos64_pit_last", 4));
        try std.testing.expectEqual(@as(u8, if (edges > 0) 1 else 0), try get(&f, "dos64_pic_irr"));
        try put(&f, "dos64_pic_irr", 0);
    }
}
test "PIT fragmentation preserves exact rational remainder phase and total across one PAL second" {
    var whole = try init();
    defer whole.deinit();
    var split = try init();
    defer split.deinit();
    try pitInit(&whole, 17);
    try pitInit(&split, 17);
    _ = try pitAdvance(&whole, 985248 + 17, false);
    var now: u32 = 17;
    var remaining: u32 = 985248;
    var seed: u32 = 0x8253;
    while (remaining > 0) {
        seed = seed *% 1103515245 +% 12345;
        const delta = @min(remaining, (seed % 8192) + 1);
        remaining -= delta;
        now += delta;
        _ = try pitAdvance(&split, now, false);
    }
    for ([_][]const u8{ "dos64_pit_fraction", "dos64_pit_phase", "dos64_pit_total" }, [_]usize{ 3, 2, 4 }) |name, bytes| try std.testing.expectEqual(try getWide(&whole, name, bytes), try getWide(&split, name, bytes));
    try std.testing.expectEqual(@as(u64, 18), try getWide(&whole, "dos64_pit_total", 4));
    try std.testing.expectEqual(@as(u64, 13533), try getWide(&whole, "dos64_pit_phase", 2));
    try std.testing.expectEqual(@as(u64, 369468), try getWide(&whole, "dos64_pit_fraction", 3));
}
test "PIT invalid gaps and reversed time latch explicit pause and rebase keeps oscillator phase" {
    for ([_]u32{ 0x07fff001, 0x08000000, 0x80000000, 0xffffffff }) |delta| {
        var f = try init();
        defer f.deinit();
        try pitInit(&f, 0x1234);
        _ = try pitAdvance(&f, 0x2345, false);
        const fraction = try getWide(&f, "dos64_pit_fraction", 3);
        const phase = try getWide(&f, "dos64_pit_phase", 2);
        const total = try getWide(&f, "dos64_pit_total", 4);
        try put(&f, "dos64_pic_irr", 0);
        const rejected: u32 = 0x2345 +% delta;
        _ = try pitAdvance(&f, rejected, true);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pit_error"));
        try std.testing.expectEqual(@as(u64, 0x2345), try getWide(&f, "dos64_pit_last", 4));
        try std.testing.expectEqual(fraction, try getWide(&f, "dos64_pit_fraction", 3));
        try std.testing.expectEqual(phase, try getWide(&f, "dos64_pit_phase", 2));
        try std.testing.expectEqual(total, try getWide(&f, "dos64_pit_total", 4));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
        _ = try pitAdvance(&f, 0x2346, true);
        try putWide(&f, "dos64_pit_now", rejected, 4);
        const r = try f.call("dos64_pit_rebase", 10000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(phase, try getWide(&f, "dos64_pit_phase", 2));
        var pit_oracle: PitOracle = .{ .fraction = fraction, .phase = phase, .total = total };
        const edges = pit_oracle.advance(1);
        _ = try pitAdvance(&f, rejected +% 1, false);
        try pit_oracle.expect(&f, edges);
    }
}
test "PIT native time bookkeeping never changes guest RAM or registers and bounds every call" {
    var f = try init();
    defer f.deinit();
    try pitInit(&f, 0);
    const before = try guestSnapshot(&f);
    const lo = try f.symbol("dos64_pit_state_start");
    const hi = try f.symbol("dos64_pit_state_end");
    f.poke(lo - 1, 0x69);
    f.poke(hi, 0x96);
    var memory: [640 * 1024]u8 = undefined;
    for (&memory, 0..) |*v, i| v.* = c.dos64_reu_peek(f.machine, @intCast(i));
    var max_cycles: u64 = 0;
    for ([_]u32{ 0, 1, 54116, 985248, 0x07fff000 }) |now| {
        try pitInit(&f, 0);
        const cycles = try pitAdvance(&f, now, false);
        max_cycles = @max(max_cycles, cycles);
        std.debug.print("PIT_SAMPLE delta={d} cycles={d}\n", .{ now, cycles });
        try std.testing.expectEqualSlices(u8, &before, &try guestSnapshot(&f));
    }
    for (memory, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_reu_peek(f.machine, @intCast(i)));
    try std.testing.expectEqual(@as(u8, 0x69), f.peek(lo - 1));
    try std.testing.expectEqual(@as(u8, 0x96), f.peek(hi));
    std.debug.print("PIT_MAX_SAMPLE_CPU_CYCLES {d}; ALL_OBSERVED {d}\n", .{ max_cycles, pit_max_observed });
}
test "PIT IRQ0 wakes HLT and midnight advances only through guest INT08 INT1C EOI IRET" {
    var f = try init();
    defer f.deinit();
    try installTimer(&f, 0x1800af);
    c.dos64_reu_poke(f.machine, 0x1200, 0xf4);
    try step(&f);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_status"));
    try pitInit(&f, 0);
    _ = try pitAdvance(&f, 54116, false);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_cpu_status"));
    try std.testing.expectEqual(@as(u16, 0xaf), readWord(&f, 0x46c));
    try attempt(&f, 1);
    try runUntil(&f, 0x201);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0), readWord(&f, 0x46c));
    try std.testing.expectEqual(@as(u16, 0), readWord(&f, 0x46e));
    try std.testing.expectEqual(@as(u8, 1), c.dos64_reu_peek(f.machine, 0x470));
    try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4500));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
}
test "PIT masked and in-service elapsed periods coalesce as PIC edges without BIOS catchup" {
    var f = try init();
    defer f.deinit();
    try installTimer(&f, 0);
    try pitInit(&f, 0);
    try put(&f, "dos64_pic_imr", 1);
    _ = try pitAdvance(&f, 985248, false);
    try std.testing.expectEqual(@as(u64, 18), try getWide(&f, "dos64_pit_edges", 2));
    try attempt(&f, 0);
    try std.testing.expectEqual(@as(u16, 0), readWord(&f, 0x46c));
    try put(&f, "dos64_pic_imr", 0);
    try attempt(&f, 1);
    // A second wall-clock second passes with IRQ0 in service. Its pending IRR0
    // survives, but there is still only one new pending interrupt.
    _ = try pitAdvance(&f, 1970496, false);
    try attempt(&f, 0);
    try runUntil(&f, 0x200);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x46c));
    try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4500));
    try step(&f);
    try attempt(&f, 1);
    try runUntil(&f, 0x201);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 2), readWord(&f, 0x46c));
    try std.testing.expectEqual(@as(u16, 2), readWord(&f, 0x4500));
    try std.testing.expectEqual(@as(u64, 36), try getWide(&f, "dos64_pit_total", 4));
}
test "PIT follows replaced INT08 vector and never repairs guest custom EOI or time behavior" {
    var f = try init();
    defer f.deinit();
    try installTimer(&f, 0x12345678);
    const custom = [_]u8{ 0x2e, 0xff, 0x06, 0x04, 0x05, 0xcf };
    for (custom, 0..) |v, i| c.dos64_reu_poke(f.machine, 0x4600 + @as(u32, @intCast(i)), v);
    try write(&f, 0x20, 0);
    try write(&f, 0x21, 6);
    try pitInit(&f, 0);
    _ = try pitAdvance(&f, 54116, false);
    try attempt(&f, 1);
    try runUntil(&f, 0x200);
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 1), readWord(&f, 0x4504));
    try std.testing.expectEqual(@as(u16, 0x5678), readWord(&f, 0x46c));
    try std.testing.expectEqual(@as(u16, 0x1234), readWord(&f, 0x46e));
    try std.testing.expectEqual(@as(u16, 0), readWord(&f, 0x4500));
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_isr"));
}
test "actual elapsed raw publication wraps its16bit view while PIT retains subunit and32bit epochs" {
    for ([_][2]u32{ .{ 0x0fffff00, 0x10000100 }, .{ 0xfffffe00, 0x00000400 } }) |pair| {
        var f = try init();
        defer f.deinit();
        try ciaInitAt(&f, pair[0]);
        try pitInit(&f, pair[0]);
        c.dos64_cia_clock_advance(f.machine, pair[1] -% pair[0]);
        const r = try f.call("dos64_pit_poll", 100000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        var pit_oracle: PitOracle = .{};
        const edges = pit_oracle.advance(pair[1] -% pair[0]);
        try pit_oracle.expect(&f, edges);
        try std.testing.expectEqual(@as(u64, (pair[1] >> 12) & 0xffff), try getWide(&f, "dos64_elapsed_now", 2));
        try std.testing.expectEqual(@as(u64, pair[1]), try getWide(&f, "dos64_pit_last", 4));
    }
}
test "CIA advances during final REP element and real polling produces restartable IRQ0" {
    var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 1);
    defer f.deinit();
    try ciaInitAt(&f, 1024);
    try pitInit(&f, 1024);
    try put(&f, "dos64_irq_callback_enabled", 1);
    try put(&f, "dos64_pit_poll_enabled", 1);
    try stepCIAAtElement(&f, 54116);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_irq_result"));
    try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
    try std.testing.expectEqual(@as(u64, 1), try getWide(&f, "dos64_pit_edges", 2));
    try flush(&f);
    try std.testing.expectEqual(@as(u16, 0x200), readWord(&f, 0x20ffa));
    try io(&f, 0x20);
    try step(&f);
    try step(&f);
    try std.testing.expectEqual(@as(u16, 0x101), try gr(&f, g_si));
    try std.testing.expectEqual(@as(u16, 0x201), try gr(&f, g_di));
}
test "CIA transient sample preserves PIT epoch and fatal control stops at completed REP boundary" {
    for (0..2) |fatal| {
        var f = try repInit(&.{ 0xf3, 0xa4, 0xf4 }, 1);
        defer f.deinit();
        try ciaInitAt(&f, 1024);
        try pitInit(&f, 1024);
        try put(&f, "dos64_irq_callback_enabled", 1);
        try put(&f, "dos64_pit_poll_enabled", 1);
        if (fatal == 1) c.dos64_bus_write(f.machine, 0xdd0e, 0) else ciaSeed(&f, 8);
        const r = try f.call("dos64_cpu_step", 1000000);
        try std.testing.expectEqual(@as(u8, @intCast(fatal)), r.p & 1);
        try std.testing.expectEqual(@as(u64, 1024), try getWide(&f, "dos64_pit_last", 4));
        try std.testing.expectEqual(@as(u16, 0), try gr(&f, g_cx));
        try std.testing.expectEqual(@as(u16, 0x101), try gr(&f, g_si));
        try std.testing.expectEqual(@as(u16, 0x201), try gr(&f, g_di));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8, if (fatal == 1) 3 else 0), try get(&f, "dos64_cpu_status"));
        try std.testing.expectEqual(@as(u8, if (fatal == 1) 4 else 0), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u8, if (fatal == 1) 3 else 4), try get(&f, "dos64_pit_poll_error"));
    }
}
test "fixed BIOS PIT rejects unmodeled access while silent speaker data leaves IRQ0 exact" {
    var f = try init();
    defer f.deinit();
    try pitInit(&f, 12345);
    for ([_]u16{ 0x40, 0x41, 0x42, 0x43 }) |port| {
        for ([_]u8{ 0, 1 }) |width| {
            try putWide(&f, "dos64_io_port", port, 2);
            try put(&f, "dos64_io_width", width);
            try putWide(&f, "dos64_io_value", 0x0036, 2);
            for ([_][]const u8{ "dos64_io_read", "dos64_io_write" }) |entry| {
                const r = try f.call(entry, 10000);
                const supported = port == 0x42 and width == 0 and std.mem.eql(u8, entry, "dos64_io_write");
                try std.testing.expectEqual(@as(u8, if (supported) 0 else 1), r.p & 1);
                try std.testing.expectEqual(@as(u64, 12345), try getWide(&f, "dos64_pit_last", 4));
                try std.testing.expectEqual(@as(u64, 0), try getWide(&f, "dos64_pit_phase", 2));
                try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
            }
        }
    }
}
test "actual CIA long pause and unready PIT report separate tagged terminal poll failures" {
    for (0..2) |gap| {
        var f = try init();
        defer f.deinit();
        try ciaInitAt(&f, 1024);
        if (gap == 1) {
            try pitInit(&f, 1024);
            c.dos64_cia_clock_advance(f.machine, 0x07fff001);
        }
        const r = try f.call("dos64_pit_poll", 100000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, if (gap == 1) 0x81 else 0x82), try get(&f, "dos64_pit_poll_error"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_host_clock_status"));
        try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_cpu_status"));
        try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_irq_result"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_pic_irr"));
        if (gap == 1) try std.testing.expectEqual(@as(u64, 1024), try getWide(&f, "dos64_pit_last", 4));
    }
}

fn nativeBios() !Fixture {
    var f = try init();
    errdefer f.deinit();
    try put(&f, "dos64_cache_limit", 32);
    _ = try f.call("dos64_cache_init", 100000);
    const r = try f.call("dos64_bios_init", 40000000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try gw(&f, g_cs, 0x100);
    try gw(&f, g_ip, 0x200);
    try gw(&f, g_ss, 0x2000);
    try gw(&f, g_sp, 0x1000);
    try gw(&f, g_ax, 0xb951);
    try gw(&f, g_ds, 0x3467);
    try gw(&f, g_flags, 0xf202);
    try ciaInitAt(&f, 1024);
    try std.testing.expectEqual(@as(u8, 0), (try f.call("dos64_elapsed_poll", 100000)).p & 1);
    try std.testing.expectEqual(@as(u8, 0), (try f.call("dos64_native_timer_init", 100000)).p & 1);
    return f;
}
fn nativeCall(f: *Fixture, n: []const u8, carry: u8) !void {
    const r = try f.call(n, 1000000);
    try std.testing.expectEqual(carry, r.p & 1);
}
fn nativeStage(f: *Fixture, stage: u8, command: u8) !void {
    const d = try f.symbol("dos64_native_diag");
    f.poke(d, stage);
    f.poke(d + 3, command);
}
fn noPresentationDue(f: *Fixture, raw: u32) !void {
    const d = try f.symbol("dos64_native_diag");
    f.poke(d + 9, 0);
    f.poke(d + 10, @truncate(raw >> 12));
    f.poke(d + 11, @truncate(raw >> 20));
}
test "resident disabled callback clears stale delivery without overlay or device activity" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_irq_result", 1);
    try put(&f, "dos64_overlay_current", 0);
    try put(&f, "dos64_overlay_busy", 1);
    const dma = c.dos64_dma_transfers(f.machine);
    const guest = try guestSnapshot(&f);
    for ([_]u8{ 0, 0xff, 0x24, 0xc9 }) |flags| {
        f.initial_status = flags;
        const r = try f.call("dos64_native_timer_repeat", 10000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(flags & 0xce, r.p & 0xce);
    }
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_irq_result"));
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_busy"));
    try std.testing.expectEqual(dma, c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqualSlices(u8, &guest, &try guestSnapshot(&f));
}
test "native BIOS INT08 alone updates midnight and mutable INT1C then guest EOI restores AX DS FLAGS" {
    for ([_]u32{ 0xffff, 0x1800af }) |start| {
        var f = try nativeBios();
        defer f.deinit();
        try write(&f, 0x46c, @truncate(start));
        try write(&f, 0x46d, @truncate(start >> 8));
        try write(&f, 0x46e, @truncate(start >> 16));
        try write(&f, 0x46f, @truncate(start >> 24));
        for ([_]u8{ 0, 6, 0, 4 }, 0..) |v, i| try write(&f, 0x70 + @as(u32,@intCast(i)), v);
        for ([_]u8{ 0x2e, 0xff, 0x06, 0, 5, 0xcf },0..) |v,i| try write(&f,0x4600+@as(u32,@intCast(i)),v);
        ciaSeed(&f, 1024 + 54116);
        try nativeCall(&f, "dos64_native_timer_repeat", 0);
        try std.testing.expectEqual(@as(u16, 0x1a0), try gr(&f, g_ip));
        try flush(&f);
        try std.testing.expectEqual(@as(u16,@truncate(start)),readWord(&f,0x46c));
        try runUntil(&f, 0x200);
        try flush(&f);
        const expected: u32 = if (start == 0x1800af) 0 else start + 1;
        try std.testing.expectEqual(@as(u16,@truncate(expected)),readWord(&f,0x46c));
        try std.testing.expectEqual(@as(u16,@truncate(expected >> 16)),readWord(&f,0x46e));
        try std.testing.expectEqual(@as(u8,@intFromBool(start==0x1800af)),c.dos64_reu_peek(f.machine,0x470));
        try std.testing.expectEqual(@as(u16,1),readWord(&f,0x4500));
        try std.testing.expectEqual(@as(u16,0xb951),try gr(&f,g_ax));
        try std.testing.expectEqual(@as(u16,0x3467),try gr(&f,g_ds));
        try std.testing.expectEqual(@as(u16,0xf202),try gr(&f,g_flags));
        try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_busy"));
    }
}
test "native bounded loop polls physical timer wakes HLT and custom INT08 suppresses default clock" {
    var f = try nativeBios();
    defer f.deinit();
    try write(&f,0x1200,0xf4);
    try step(&f);
    // Custom handler: INC CS:[0504] / IRET; intentionally no default chain/EOI.
    for ([_]u8{ 0x2e,0xff,0x06,4,5,0xcf },0..) |v,i| try write(&f,0x4600+@as(u32,@intCast(i)),v);
    for ([_]u8{0,6,0,4},0..) |v,i| try write(&f,0x20+@as(u32,@intCast(i)),v);
    try write(&f,0x1201,0xf4);
    const raw:u32=1024+985248;
    ciaSeed(&f,raw);
    try noPresentationDue(&f,raw);
    try nativeStage(&f,4,0);
    try nativeCall(&f,"dos64_native_tick",0);
    try flush(&f);
    try std.testing.expectEqual(@as(u16,1),readWord(&f,0x4504));
    try std.testing.expectEqual(@as(u16,0),readWord(&f,0x46c));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_pic_isr"));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_cpu_status"));
    try std.testing.expectEqual(@as(u64,18),try getWide(&f,"dos64_pit_total",4));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8,4),try get(&f,"dos64_overlay_current"));
}
test "native resume explicitly rebases long paused interval retaining phase pending IRQ and ISR" {
    var f=try nativeBios(); defer f.deinit();
    try write(&f,0x1200,0xf4);
    _=try pitAdvance(&f,2048,false);
    const phase=try getWide(&f,"dos64_pit_phase",2);
    const fraction=try getWide(&f,"dos64_pit_fraction",3);
    try put(&f,"dos64_pic_irr",1);
    try put(&f,"dos64_pic_isr",1);
    try nativeStage(&f,5,3);
    const raw:u32=0x10000400;
    ciaSeed(&f,raw);
    try noPresentationDue(&f,raw);
    try nativeCall(&f,"dos64_native_tick",0);
    try std.testing.expectEqual(@as(u64,raw),try getWide(&f,"dos64_pit_last",4));
    try std.testing.expectEqual(phase,try getWide(&f,"dos64_pit_phase",2));
    try std.testing.expectEqual(fraction,try getWide(&f,"dos64_pit_fraction",3));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_pic_irr"));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_pic_isr"));
    const d=try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(@as(u8,4),f.peek(d));
    try std.testing.expectEqual(@as(u8,0xa5),f.peek(d+4));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_pit_error"));
}
test "native unannounced long pause is terminal without BDA catchup" {
    var f=try nativeBios(); defer f.deinit();
    try write(&f,0x1200,0xf4);
    const raw:u32=0x08000400;
    ciaSeed(&f,raw);
    try noPresentationDue(&f,raw);
    try nativeStage(&f,4,0);
    try nativeCall(&f,"dos64_native_tick",1);
    const d=try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(@as(u8,0xe1),f.peek(d));
    try std.testing.expectEqual(@as(u8,10),f.peek(d+1));
    try std.testing.expectEqual(@as(u8,4),f.peek(d+2));
    try std.testing.expectEqual(@as(u8,0x81),try get(&f,"dos64_pit_poll_error"));
    try std.testing.expectEqual(@as(u8,3),try get(&f,"dos64_cpu_status"));
    try flush(&f);
    try std.testing.expectEqual(@as(u16,0),readWord(&f,0x46c));
}
test "native REP lease acquisition failure retains completed element and never acknowledges pending IRQ" {
    for ([_]u8{0,1,2}) |failure| {
        var f=try repInit(&.{0xf3,0xa4,0xf4},1); defer f.deinit();
        try put(&f,"dos64_irq_callback_enabled",1);
        try put(&f,"dos64_pic_irr",1);
        // Eject the previously warmed PIT with a real INPUT lease, then arm
        // either header or payload DMA failure at the completed REP boundary.
        if (failure != 0) {
            try put(&f,"dos64_overlay_requested",3);
            try nativeCall(&f,"dos64_overlay_acquire",0);
            try nativeCall(&f,"dos64_overlay_release",0);
        } else try put(&f,"dos64_overlay_busy",1);
        try stepInjectWithFailure(&f,"string_iteration_complete",1,if(failure==0) null else @as(u64,failure-1));
        try std.testing.expectEqual(@as(u8,1),c.dos64_get_regs(f.machine).p&1);
        try std.testing.expectEqual(@as(u16,0),try gr(&f,g_cx));
        try std.testing.expectEqual(@as(u16,0x101),try gr(&f,g_si));
        try std.testing.expectEqual(@as(u16,0x201),try gr(&f,g_di));
        try std.testing.expectEqual(@as(u8,5),try get(&f,"dos64_irq_result"));
        try std.testing.expectEqual(@as(u8,3),try get(&f,"dos64_cpu_status"));
        try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_pic_irr"));
        try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_pic_isr"));
        try std.testing.expectEqual(@as(u8,@intFromBool(failure==0)),try get(&f,"dos64_overlay_busy"));
        if (failure!=0) try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_current"));
        const snap=try guestSnapshot(&f);
        try nativeCall(&f,"dos64_cpu_step",1);
        try std.testing.expectEqualSlices(u8,&snap,&try guestSnapshot(&f));
    }
}
test "disabled resident callback preserves REP progress after stale delivered result" {
    var f=try repInit(&.{0xf3,0xa4,0xf4},33);defer f.deinit();
    try put(&f,"dos64_irq_result",1);
    try step(&f);
    try std.testing.expectEqual(@as(u16,17),try gr(&f,g_cx));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_string_pending"));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_irq_result"));
    try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));
}
test "native resume transient physical sample retains pending command paused stage and oscillator epoch" {
    var f=try nativeBios();defer f.deinit();
    const last=try getWide(&f,"dos64_pit_last",4);
    const phase=try getWide(&f,"dos64_pit_phase",2);
    ciaSeed(&f,0); // first256ticks are deliberately rejected by coherent reader
    try nativeStage(&f,5,3);
    try nativeCall(&f,"dos64_native_tick",0);
    const d=try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(@as(u8,5),f.peek(d));
    try std.testing.expectEqual(@as(u8,3),f.peek(d+3));
    try std.testing.expectEqual(@as(u8,0),f.peek(d+4));
    try std.testing.expectEqual(last,try getWide(&f,"dos64_pit_last",4));
    try std.testing.expectEqual(phase,try getWide(&f,"dos64_pit_phase",2));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_busy"));
}
test "native resume lease fault fails paused runtime without publishing running state or clearing pending PIC" {
    var f=try nativeBios();defer f.deinit();
    try put(&f,"dos64_overlay_requested",3);
    try nativeCall(&f,"dos64_overlay_acquire",0);
    try nativeCall(&f,"dos64_overlay_release",0);
    const last=try getWide(&f,"dos64_pit_last",4);
    try put(&f,"dos64_pic_irr",1);
    try nativeStage(&f,5,3);
    ciaSeed(&f,0x08000400);
    c.dos64_reu_fail_after(f.machine,1,17);
    try nativeCall(&f,"dos64_native_tick",1); // terminal failure remains carry-set
    const d=try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(@as(u8,0xe1),f.peek(d));
    try std.testing.expectEqual(@as(u8,10),f.peek(d+1));
    try std.testing.expectEqual(@as(u8,0xe1),f.peek(d+4));
    try std.testing.expectEqual(last,try getWide(&f,"dos64_pit_last",4));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_pic_irr"));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_current"));
}
test "integrated native polling overhead separates warm NOP noedge duepulse and accepted frame" {
    const scenarios=[_]struct{delta:u32,accept:bool,label:[]const u8}{
      .{.delta=0,.accept=true,.label="same-raw-noedge-IFset"},
      .{.delta=1,.accept=true,.label="one-phi2-noedge-IFset"},
      .{.delta=100,.accept=true,.label="100-phi2-noedge-IFset"},
      .{.delta=32767,.accept=true,.label="many-bits-noedge-IFset"},
      .{.delta=54115,.accept=true,.label="one-before-edge-IFset"},
      .{.delta=54116,.accept=false,.label="due-edge-IFclear"},
      .{.delta=54116,.accept=true,.label="due-edge-frame"},
    };
    for(scenarios)|scenario|{
        var callback_cycles:u64=0;var step_cycles:u64=0;var nop_cycles:u64=0;
        for([_]bool{false,true})|include_step|{
            var f=try init();defer f.deinit();
            c.dos64_reu_poke(f.machine,0x1200,0x90);
            try gw(&f,g_flags,0xf002);
            try step(&f); // warm instruction page and fast fetch independently
            try gw(&f,g_ip,0x200);
            var before=c.dos64_get_regs(f.machine).cycles;
            try step(&f);
            nop_cycles=c.dos64_get_regs(f.machine).cycles-before;
            try gw(&f,g_ip,0x200);
            try gw(&f,g_flags,if(scenario.accept) 0xf202 else 0xf002);
            try ciaInitAt(&f,1024);
            try nativeCall(&f,"dos64_elapsed_poll",0);
            try nativeCall(&f,"dos64_native_timer_init",0);
            ciaSeed(&f,1024+scenario.delta);
            before=c.dos64_get_regs(f.machine).cycles;
            try nativeCall(&f,if(include_step) "dos64_native_timer_step" else "dos64_native_timer_repeat",0);
            const cycles=c.dos64_get_regs(f.machine).cycles-before;
            if(include_step)step_cycles=cycles else callback_cycles=cycles;
            try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_busy"));
        }
        std.debug.print("INTEGRATED_TIMER label={s} rawdelta={d} warmNOP={d} callback={d} nativeStep={d} CPUcycles\n",.{scenario.label,scenario.delta,nop_cycles,callback_cycles,step_cycles});
    }
}

test "empty or fully masked IRR still validates every PIC programming byte before returning none" {
    var f = try init();
    defer f.deinit();
    for ([_][2]u8{ .{ 0, 0 }, .{ 255, 255 } }) |requests| {
        try put(&f, "dos64_pic_irr", requests[0]);
        try put(&f, "dos64_pic_imr", requests[1]);
        inline for (.{ "dos64_pic_icw1", "dos64_pic_icw4", "dos64_pic_phase" }, .{ @as(u8, 0x13), @as(u8, 9), @as(u8, 0) }) |name, normal| {
            for (0..256) |raw| {
                const value: u8 = @intCast(raw);
                try put(&f, name, value);
                const valid = if (std.mem.eql(u8, name, "dos64_pic_icw1"))
                    value & 0x1b == 0x13
                else if (std.mem.eql(u8, name, "dos64_pic_icw4"))
                    value & 0x11 == 1 and !(value & 2 != 0 and value & 0x0c == 8)
                else
                    value == 0;
                const r = try f.call("dos64_irq_select", 10000);
                try std.testing.expectEqual(@as(u8, if (valid) 0 else 1), r.p & 1);
                try std.testing.expectEqual(@as(u8, 255), try get(&f, "dos64_irq_selected"));
                try std.testing.expectEqual(requests[0], try get(&f, "dos64_pic_irr"));
                try std.testing.expectEqual(requests[1], try get(&f, "dos64_pic_imr"));
                try std.testing.expectEqual(value, try get(&f, name));
            }
            try put(&f, name, normal);
        }
    }
}

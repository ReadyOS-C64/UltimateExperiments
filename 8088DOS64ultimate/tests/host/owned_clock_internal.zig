const std = @import("std");
const host = @import("machine_irq_pit.zig");
const F = host.Fixture;
const c = host.c;
fn setup() !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_cia_clock_enable(f.machine);
    f.poke(try f.symbol("dos64_host_clock_claim"), 0xa5);
    try std.testing.expectEqual(@as(u8, 0), (try f.call("dos64_host_clock_init", 10000)).p & 1);
    return f;
}
fn seed(f: *F, raw: u32) void {
    c.dos64_cia_clock_seed(f.machine, @truncate(~raw), @truncate(~(raw >> 16)));
}
fn value(f: *F, name: []const u8, length: u16) !u32 {
    const address = try f.symbol(name);
    var v: u32 = 0;
    for (0..length) |i| v |= @as(u32, f.peek(address + @as(u16, @intCast(i)))) << @as(u5, @intCast(i * 8));
    return v;
}
test "owned elapsed gateway keeps exact raw and elapsed publications and coherent CIA read counts" {
    var f = try setup();
    defer f.deinit();
    var state: u32 = 0x808864;
    const expected = [_]u32{ 0, 0, 0, 0, 1, 2, 2, 4, 0, 0, 0, 0, 0, 0, 1, 1 };
    for (0..2048) |i| {
        state = state *% 1664525 +% 1013904223;
        const raw = state | 0x100; // Outside the expressly excluded A-highFF reload window.
        seed(&f, raw);
        f.initial_status = @truncate(i);
        var before: [16]u32 = undefined;
        for (&before, 0..) |*v, reg| v.* = c.dos64_cia_clock_reads(f.machine, @intCast(reg));
        const original_port = f.peek(1);
        const r = try f.call("dos64_elapsed_poll_owned", 10000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
        try std.testing.expectEqual(raw, try value(&f, "dos64_host_clock_ticks", 4));
        try std.testing.expectEqual(@as(u32, @as(u16, @truncate(raw >> 12))), try value(&f, "dos64_elapsed_now", 2));
        for (before, expected, 0..) |old, wanted, reg| try std.testing.expectEqual(wanted, c.dos64_cia_clock_reads(f.machine, @intCast(reg)) - old);
        try std.testing.expectEqual(@as(u8, 0x2f), f.peek(0));
        try std.testing.expectEqual(original_port, f.peek(1));
        try std.testing.expectEqual(@as(u8, 5), f.peek(1) & 7);
        try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, 0));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, 1));
    }
}
test "owned elapsed gateway retains both old publications on owner readiness control and reload errors" {
    var f = try setup();
    defer f.deinit();
    seed(&f, 0x31415926);
    _ = try f.call("dos64_elapsed_poll_owned", 10000);
    const old_raw = try value(&f, "dos64_host_clock_ticks", 4);
    const old_elapsed = try value(&f, "dos64_elapsed_now", 2);
    for ([_]u8{ 1, 2, 3, 4 }) |expected| {
        f.poke(try f.symbol("dos64_host_clock_claim"), if (expected == 1) 0 else 0xa5);
        f.poke(try f.symbol("dos64_host_clock_ready"), if (expected == 2) 0 else 1);
        c.dos64_bus_write(f.machine, 0xdd0e, if (expected == 3) 9 else 1);
        seed(&f, if (expected == 4) 0 else 0x12345100);
        f.initial_status = 0xef;
        const r = try f.call("dos64_elapsed_poll_owned", 10000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0xce), r.p & 0xce);
        try std.testing.expectEqual(@as(u32, expected), try value(&f, "dos64_host_clock_status", 1));
        try std.testing.expectEqual(old_raw, try value(&f, "dos64_host_clock_ticks", 4));
        try std.testing.expectEqual(old_elapsed, try value(&f, "dos64_elapsed_now", 2));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, 0));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_was_written(f.machine, 1));
    }
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const model = @cImport({
    @cInclude("uci_model.h");
});
fn put(f: *Fixture, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn get(f: *Fixture, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn word(f: *Fixture, n: []const u8, v: u16) !void {
    const a = try f.symbol(n);
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn readWord(f: *Fixture, n: []const u8) !u16 {
    return f.word(try f.symbol(n));
}
fn invoke(f: *Fixture, n: []const u8, carry: u8) !void {
    const port = f.peek(1);
    const direction = f.peek(0);
    const r = try f.call(n, 50_000);
    try std.testing.expectEqual(carry, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    try std.testing.expectEqual(@as(u8, 0x71), r.a);
    try std.testing.expectEqual(@as(u8, 0x82), r.x);
    try std.testing.expectEqual(@as(u8, 0x93), r.y);
    try std.testing.expectEqual(port & direction, f.peek(1) & direction);
    try std.testing.expectEqual(direction, f.peek(0));
}
fn setup(base: u16, delay: u32, id: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    model.dos64_uci_model_enable(f.machine, base, delay, id);
    try invoke(&f, "dos64_uci_init", 0);
    try word(&f, "dos64_uci_base", base);
    try word(&f, "dos64_uci_timeout", 5000);
    try word(&f, "dos64_uci_command_len", 2);
    const p = try f.symbol("dos64_uci_command");
    f.poke(p, 1);
    f.poke(p + 1, 1);
    const end = try f.symbol("dos64_uci_buffer_end");
    f.poke(p - 1, 0xa5);
    f.poke(end, 0x5a);
    return f;
}
fn block(f: *Fixture, data: []const u8, status: []const u8) void {
    model.dos64_uci_model_block(f.machine, data.ptr, data.len, status.ptr, status.len);
}
fn tick(f: *Fixture, now: *u16) !void {
    now.* +%= 1;
    try word(f, "dos64_uci_now", now.*);
    try invoke(f, "dos64_uci_poll", 0);
}
fn until(f: *Fixture, now: *u16, state: u8) !void {
    for (0..2000) |_| {
        if (try get(f, "dos64_uci_state") == state) return;
        try tick(f, now);
    }
    std.debug.print("UCI state={d}, error={d}, wanted={d}\n", .{ try get(f, "dos64_uci_state"), try get(f, "dos64_uci_error"), state });
    return error.StateBudget;
}
fn guard(f: *Fixture) !void {
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek((try f.symbol("dos64_uci_buffer_start")) - 1));
    try std.testing.expectEqual(@as(u8, 0x5a), f.peek(try f.symbol("dos64_uci_buffer_end")));
}

test "UCI bounded command upload, full response and status queues preserve ABI and mapping" {
    for ([_]u16{ 0xdf1c, 0xde1c, 0xdffc }) |base| {
        var f = try setup(base, 7, 0xc9);
        defer f.deinit();
        f.initial_status = 0xef;
        f.poke(1, 0x30);
        var cmd: [895]u8 = undefined;
        var data: [895]u8 = undefined;
        var stat: [255]u8 = undefined;
        for (&cmd, 0..) |*b, i| b.* = @truncate(i * 23 + 1);
        for (&data, 0..) |*b, i| b.* = @truncate(i * 37 + 19);
        for (&stat, 0..) |*b, i| b.* = @truncate(i * 71 + 5);
        const p = try f.symbol("dos64_uci_command");
        for (cmd, 0..) |b, i| f.poke(p + @as(u16, @intCast(i)), b);
        try word(&f, "dos64_uci_command_len", 895);
        block(&f, &data, &stat);
        try invoke(&f, "dos64_uci_start", 0);
        var now: u16 = 0;
        var last: u64 = 0;
        while (try get(&f, "dos64_uci_state") != 3) {
            try tick(&f, &now);
            const n = model.dos64_uci_model_count(f.machine, 6);
            try std.testing.expect(n - last <= 16);
            last = n;
        }
        try std.testing.expectEqual(@as(u64, 895), last);
        for (cmd, 0..) |b, i| try std.testing.expectEqual(b, model.dos64_uci_model_command(f.machine, @intCast(i)));
        try until(&f, &now, 5);
        try std.testing.expectEqual(@as(u16, 895), try readWord(&f, "dos64_uci_data_len"));
        try std.testing.expectEqual(@as(u16, 255), try readWord(&f, "dos64_uci_status_len"));
        for (data, 0..) |b, i| try std.testing.expectEqual(b, f.peek((try f.symbol("dos64_uci_data")) + @as(u16, @intCast(i))));
        for (stat, 0..) |b, i| try std.testing.expectEqual(b, f.peek((try f.symbol("dos64_uci_status")) + @as(u16, @intCast(i))));
        try invoke(&f, "dos64_uci_accept", 0);
        try until(&f, &now, 9);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_uci_error"));
        try std.testing.expectEqual(@as(u64, 895), model.dos64_uci_model_count(f.machine, 4));
        try std.testing.expectEqual(@as(u64, 255), model.dos64_uci_model_count(f.machine, 5));
        try guard(&f);
    }
}

test "UCI MORE streaming holds each block until consumer accepts and handles missed BUSY" {
    for ([_]u32{ 0, 1, 30, 300 }) |delay| {
        var f = try setup(0xdf1c, delay, 0x49);
        defer f.deinit();
        block(&f, "first", "00,OK");
        block(&f, "second", "01,opaque");
        block(&f, "", "00,OK");
        try invoke(&f, "dos64_uci_start", 0);
        var now: u16 = 0;
        for ([_][]const u8{ "first", "second", "" }, 0..) |expected, i| {
            try until(&f, &now, 5);
            try std.testing.expectEqual(@as(u16, @intCast(expected.len)), try readWord(&f, "dos64_uci_data_len"));
            for (expected, 0..) |b, j| try std.testing.expectEqual(b, f.peek((try f.symbol("dos64_uci_data")) + @as(u16, @intCast(j))));
            const reads = model.dos64_uci_model_count(f.machine, 4);
            for (0..8) |_| try tick(&f, &now);
            try std.testing.expectEqual(reads, model.dos64_uci_model_count(f.machine, 4));
            try std.testing.expectEqual(@as(u64, i), model.dos64_uci_model_count(f.machine, 1));
            try invoke(&f, "dos64_uci_accept", 0);
        }
        try until(&f, &now, 9);
        try std.testing.expectEqual(@as(u16, 3), try readWord(&f, "dos64_uci_blocks"));
        try std.testing.expectEqual(@as(u16, 11), try readWord(&f, "dos64_uci_data_seen"));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_uci_flags"));
        try guard(&f);
    }
}

test "UCI capacity truncation drains both queues without crossing buffers" {
    for ([_]u16{ 0, 1, 255, 256 }) |cap| {
        var f = try setup(0xdf1c, 2, 0xc9);
        defer f.deinit();
        try word(&f, "dos64_uci_data_capacity", cap);
        try word(&f, "dos64_uci_status_capacity", cap);
        var data: [895]u8 = @splat(0x61);
        var status: [255]u8 = @splat(0x32);
        block(&f, &data, &status);
        const d = try f.symbol("dos64_uci_data");
        const s = try f.symbol("dos64_uci_status");
        for (0..896) |i| f.poke(d + @as(u16, @intCast(i)), 0xa7);
        for (0..256) |i| f.poke(s + @as(u16, @intCast(i)), 0xb8);
        try invoke(&f, "dos64_uci_start", 0);
        var now: u16 = 0;
        try until(&f, &now, 5);
        for (0..896) |i| try std.testing.expectEqual(@as(u8, if (i < cap and i < 895) 0x61 else 0xa7), f.peek(d + @as(u16, @intCast(i))));
        for (0..256) |i| try std.testing.expectEqual(@as(u8, if (i < cap and i < 255) 0x32 else 0xb8), f.peek(s + @as(u16, @intCast(i))));
        try std.testing.expectEqual(@as(u8, if (cap >= 255) 1 else 3), try get(&f, "dos64_uci_flags"));
        try invoke(&f, "dos64_uci_accept", 0);
        try until(&f, &now, 9);
        try guard(&f);
    }
}

test "UCI rejects invalid lengths capacities bases and tick durations before PUSH" {
    const Case = struct { n: []const u8, v: u16 };
    for ([_]Case{ .{ .n = "dos64_uci_command_len", .v = 0 }, .{ .n = "dos64_uci_command_len", .v = 896 }, .{ .n = "dos64_uci_data_capacity", .v = 897 }, .{ .n = "dos64_uci_status_capacity", .v = 257 }, .{ .n = "dos64_uci_base", .v = 0xdefc }, .{ .n = "dos64_uci_base", .v = 0x4000 }, .{ .n = "dos64_uci_timeout", .v = 0 }, .{ .n = "dos64_uci_timeout", .v = 0x8000 }, .{ .n = "dos64_uci_recovery_timeout", .v = 0 }, .{ .n = "dos64_uci_recovery_timeout", .v = 0xffff } }) |case| {
        var f = try setup(0xdf1c, 1, 0xc9);
        defer f.deinit();
        try word(&f, case.n, case.v);
        try invoke(&f, "dos64_uci_start", 1);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_uci_error"));
        try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(f.machine, 0));
    }
    var f = try setup(0xdf1c, 1, 0xff);
    defer f.deinit();
    try invoke(&f, "dos64_uci_start", 1);
    try std.testing.expectEqual(@as(u8, 2), try get(&f, "dos64_uci_error"));
}

test "UCI elapsed deadline wraps, expires exactly, and stuck recovery is explicit" {
    var f = try setup(0xdf1c, 200, 0xc9);
    defer f.deinit();
    block(&f, "late", "00,OK");
    try word(&f, "dos64_uci_now", 0xfffc);
    try word(&f, "dos64_uci_timeout", 8);
    try word(&f, "dos64_uci_recovery_timeout", 4);
    model.dos64_uci_model_stuck(f.machine, 1);
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0xfffc;
    for (0..7) |_| try tick(&f, &now);
    try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_uci_state"));
    try tick(&f, &now);
    try std.testing.expectEqual(@as(u8, 8), try get(&f, "dos64_uci_state"));
    for (0..3) |_| try tick(&f, &now);
    try std.testing.expectEqual(@as(u8, 8), try get(&f, "dos64_uci_state"));
    try tick(&f, &now);
    try std.testing.expectEqual(@as(u8, 10), try get(&f, "dos64_uci_state"));
    try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_uci_recovery_failed"));
    try std.testing.expectEqual(@as(u64, 1), model.dos64_uci_model_count(f.machine, 2));
    try invoke(&f, "dos64_uci_start", 1);
}

test "UCI cancellation aborts once, verifies quiet, then permits a new command" {
    var f = try setup(0xdf1c, 20, 0xc9);
    defer f.deinit();
    block(&f, "aborted", "00,OK");
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    try until(&f, &now, 3);
    try invoke(&f, "dos64_uci_start", 1);
    try invoke(&f, "dos64_uci_abort", 0);
    try invoke(&f, "dos64_uci_abort", 1);
    try until(&f, &now, 10);
    try std.testing.expectEqual(@as(u8, 5), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_uci_recovery_failed"));
    try std.testing.expectEqual(@as(u64, 1), model.dos64_uci_model_count(f.machine, 2));
    try invoke(&f, "dos64_uci_start", 0);
    try until(&f, &now, 5);
    try invoke(&f, "dos64_uci_accept", 0);
    try until(&f, &now, 9);
}

test "UCI protocol error is cleared during bounded abort recovery" {
    var f = try setup(0xdf1c, 5, 0xc9);
    defer f.deinit();
    block(&f, "abc", "00,OK");
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    try until(&f, &now, 3);
    model.dos64_uci_model_error(f.machine);
    try tick(&f, &now);
    try until(&f, &now, 10);
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u64, 1), model.dos64_uci_model_count(f.machine, 2));
    try std.testing.expectEqual(@as(u64, 1), model.dos64_uci_model_count(f.machine, 3));
}

test "UCI preexisting response is aborted safely and never reported as this command" {
    for ([_]u8{ 0x10, 0x20, 0x30 }) |state| {
        var f = try setup(0xdf1c, 3, 0xc9);
        defer f.deinit();
        block(&f, "stale", "00,OK");
        block(&f, "more", "00,OK");
        model.dos64_uci_model_stale(f.machine, state);
        try invoke(&f, "dos64_uci_start", 0);
        var now: u16 = 0;
        try until(&f, &now, 10);
        try std.testing.expectEqual(@as(u8, 6), try get(&f, "dos64_uci_error"));
        try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(f.machine, 0));
        try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(f.machine, 4));
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_uci_recovery_failed"));
    }
}

test "UCI backpressure deadline counts caller time and no poll-count timing" {
    var f = try setup(0xdf1c, 1, 0xc9);
    defer f.deinit();
    block(&f, "data", "00,OK");
    try word(&f, "dos64_uci_timeout", 100);
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    try until(&f, &now, 5);
    for (0..1000) |_| try invoke(&f, "dos64_uci_poll", 0);
    try std.testing.expectEqual(@as(u8, 5), try get(&f, "dos64_uci_state"));
    now = 100;
    try word(&f, "dos64_uci_now", now);
    try invoke(&f, "dos64_uci_accept", 0);
    try until(&f, &now, 10);
    try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_uci_error"));
}

test "UCI actual FPGA queue boundary detects saturated response and 8-bit status length" {
    var f = try setup(0xdf1c, 2, 0xc9);
    defer f.deinit();
    var data: [896]u8 = @splat(0x6d);
    block(&f, &data, "00,OK");
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    try until(&f, &now, 10);
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u64, 896), model.dos64_uci_model_count(f.machine, 4));
    try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(f.machine, 1));
    try guard(&f);
    var g = try setup(0xdf1c, 2, 0xc9);
    defer g.deinit();
    var status: [256]u8 = @splat(0x73);
    block(&g, "", &status);
    try invoke(&g, "dos64_uci_start", 0);
    now = 0;
    try until(&g, &now, 5);
    // Hardware publishes only low8 status-length bits, so256 appears empty.
    // Target command builders must never request/assume such a status size.
    try std.testing.expectEqual(@as(u16, 0), try readWord(&g, "dos64_uci_status_len"));
    try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(g.machine, 5));
    try invoke(&g, "dos64_uci_accept", 0);
    try until(&g, &now, 9);
}

test "UCI 24-bit aggregate counts cross 64 KiB with independent block bounds" {
    var f = try setup(0xdf1c, 0, 0xc9);
    defer f.deinit();
    var data: [895]u8 = undefined;
    for (&data, 0..) |*b, i| b.* = @truncate(i * 17 + 3);
    for (0..80) |_| block(&f, &data, "00,OK");
    try word(&f, "dos64_uci_timeout", 10000);
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    for (0..80) |_| {
        try until(&f, &now, 5);
        try std.testing.expectEqual(@as(u16, 895), try readWord(&f, "dos64_uci_data_len"));
        try invoke(&f, "dos64_uci_accept", 0);
    }
    try until(&f, &now, 9);
    const p = try f.symbol("dos64_uci_data_seen");
    const actual = @as(u32, f.peek(p)) | (@as(u32, f.peek(p + 1)) << 8) | (@as(u32, f.peek(p + 2)) << 16);
    try std.testing.expectEqual(@as(u32, 71600), actual);
    try std.testing.expectEqual(@as(u16, 80), try readWord(&f, "dos64_uci_blocks"));
    try guard(&f);
}

test "UCI aggregate overflow aborts rather than silently wrapping" {
    for ([_][]const u8{ "dos64_uci_data_seen", "dos64_uci_status_seen" }) |name| {
        var f = try setup(0xdf1c, 1, 0xc9);
        defer f.deinit();
        var bytes: [50]u8 = @splat(0x41);
        if (std.mem.eql(u8, name, "dos64_uci_data_seen")) block(&f, &bytes, "") else block(&f, "", &bytes);
        try invoke(&f, "dos64_uci_start", 0);
        var now: u16 = 0;
        try until(&f, &now, 4);
        const p = try f.symbol(name);
        for (0..3) |i| f.poke(p + @as(u16, @intCast(i)), 0xff);
        try until(&f, &now, 10);
        try std.testing.expectEqual(@as(u8, 7), try get(&f, "dos64_uci_error"));
        try std.testing.expectEqual(@as(u64, 1), model.dos64_uci_model_count(f.machine, 2));
        try guard(&f);
    }
}

test "UCI temporarily forces banking outputs and restores arbitrary DDR mappings" {
    for ([_]u8{ 0, 0x2f, 0xff }) |direction| {
        for ([_]u8{ 0x30, 0x35, 0x37 }) |port| {
            var f = try setup(0xdf1c, 0, 0xc9);
            defer f.deinit();
            f.poke(0, direction);
            f.poke(1, port);
            block(&f, "mapping", "00,OK");
            try invoke(&f, "dos64_uci_start", 0);
            var now: u16 = 0;
            try until(&f, &now, 5);
            try invoke(&f, "dos64_uci_accept", 0);
            try until(&f, &now, 9);
            try guard(&f);
        }
    }
}

test "UCI no-reply commands are rejected and init does not erase owned buffers" {
    var f = try setup(0xdf1c, 0, 0xc9);
    defer f.deinit();
    const b = try f.symbol("dos64_uci_buffer_start");
    const e = try f.symbol("dos64_uci_buffer_end");
    for (b..e) |a| f.poke(@intCast(a), @truncate(a * 19 + 7));
    try invoke(&f, "dos64_uci_init", 0);
    for (b..e) |a| try std.testing.expectEqual(@as(u8, @truncate(a * 19 + 7)), f.peek(@intCast(a)));
    try std.testing.expectEqual(@as(u16, 0), try readWord(&f, "dos64_uci_command_len"));
    try word(&f, "dos64_uci_command_len", 2);
    f.poke(b, 0x81);
    try invoke(&f, "dos64_uci_start", 1);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u64, 0), model.dos64_uci_model_count(f.machine, 0));
}

test "UCI source and response storage remain bounded and unrelated native RAM is untouched" {
    var f = try setup(0xdf1c, 2, 0xc9);
    defer f.deinit();
    block(&f, "ownership", "00,OK");
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    const lo = try f.symbol("dos64_uci_state_start");
    const hi = try f.symbol("dos64_uci_state_end");
    const b = try f.symbol("dos64_uci_buffer_start");
    const e = try f.symbol("dos64_uci_buffer_end");
    const code_lo = try f.symbol("dos64_uci_code_start");
    const code_hi = try f.symbol("dos64_uci_code_end");
    for (0..50) |_| {
        try tick(&f, &now);
        for (0..65536) |i| {
            const a: u16 = @intCast(i);
            if (host.c.dos64_was_written(f.machine, a) == 0) continue;
            // Self-modifying register/buffer operands are owned code writes.
            // The linker labels keep this valid when UCI moves to DEVICECODE.
            try std.testing.expect(a <= 1 or (a >= 0x100 and a < 0x200) or (a >= code_lo and a < code_hi) or (a >= lo and a < hi) or (a >= b and a < e) or (a >= 0xdf1c and a <= 0xdf1f));
        }
        if (try get(&f, "dos64_uci_state") == 5) break;
    }
    try std.testing.expectEqual(@as(u8, 5), try get(&f, "dos64_uci_state"));
    try std.testing.expectEqual(@as(u8, 1), f.peek(b));
    try std.testing.expectEqual(@as(u8, 1), f.peek(b + 1));
    try invoke(&f, "dos64_uci_accept", 0);
    try until(&f, &now, 9);
    try guard(&f);
}

test "UCI unexpected idle after PUSH is never completion and timeout can recover" {
    var f = try setup(0xdf1c, 20, 0xc9);
    defer f.deinit();
    block(&f, "late", "00,OK");
    try word(&f, "dos64_uci_timeout", 12);
    try invoke(&f, "dos64_uci_start", 0);
    var now: u16 = 0;
    try until(&f, &now, 3);
    model.dos64_uci_model_stuck(f.machine, 1);
    model.dos64_uci_model_stale(f.machine, 0);
    while (now < 11) {
        try tick(&f, &now);
        try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_uci_state"));
    }
    try tick(&f, &now);
    try std.testing.expectEqual(@as(u8, 8), try get(&f, "dos64_uci_state"));
    model.dos64_uci_model_stuck(f.machine, 0);
    try until(&f, &now, 10);
    try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_uci_error"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_uci_recovery_failed"));
}

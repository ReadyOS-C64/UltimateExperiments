const std = @import("std");
const host = @import("machine.zig");
const F = host.Fixture;
const m = @cImport({
    @cInclude("uci_model.h");
});
fn p(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn g(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn w(f: *F, n: []const u8, v: u16) !void {
    const a = try f.symbol(n);
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn call(f: *F, n: []const u8, c: u8) !void {
    const port = f.peek(1);
    const direction = f.peek(0);
    const wrapper = if (std.mem.eql(u8, n, "dos64_files_init")) "dos64_overlay_files_init" else if (std.mem.eql(u8, n, "dos64_files_start")) "dos64_overlay_files_start" else if (std.mem.eql(u8, n, "dos64_files_poll")) "dos64_overlay_files_poll" else n;
    const r = try f.call(wrapper, 100_000);
    try std.testing.expectEqual(port & direction, f.peek(1) & direction);
    try std.testing.expectEqual(direction, f.peek(0));
    try std.testing.expectEqual(c, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    if (std.mem.eql(u8, wrapper, n)) {
        try std.testing.expectEqual(@as(u8, 0x71), r.a);
        try std.testing.expectEqual(@as(u8, 0x82), r.x);
        try std.testing.expectEqual(@as(u8, 0x93), r.y);
    } else {
        try std.testing.expectEqual(@as(u8, 0), try g(f, "dos64_overlay_busy"));
        try std.testing.expectEqual(@as(u8, 1), try g(f, "dos64_overlay_current"));
    }
}
fn setup() !F {
    var f = try F.init();
    errdefer f.deinit();
    host.c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    try p(&f, "dos64_overlay_reu_mib", 4);
    _ = try f.call("dos64_overlay_bootstrap", 10_000);
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 7, 0xc9);
    try call(&f, "dos64_uci_init", 0);
    try call(&f, "dos64_files_init", 0);
    try w(&f, "dos64_uci_timeout", 4000);
    f.poke((try f.symbol("dos64_uci_command")) - 1, 0xa5);
    return f;
}
fn reply(f: *F, d: []const u8, s: []const u8) void {
    m.dos64_uci_model_block(f.machine, d.ptr, d.len, s.ptr, s.len);
}
fn tick(f: *F, now: *u16) !void {
    now.* +%= 1;
    try w(f, "dos64_files_now", now.*);
    try call(f, "dos64_files_poll", 0);
}
fn path(f: *F, op: u8, s: []const u8) !void {
    try p(f, "dos64_files_op", op);
    try p(f, "dos64_files_path_len", @intCast(s.len + 1));
    const a = (try f.symbol("dos64_uci_command")) + @as(u16, if (op == 2) 3 else 2);
    for (s, 0..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    f.poke(a + @as(u16, @intCast(s.len)), 0);
}
fn run(f: *F, cmd: []const u8, d: []const u8, s: []const u8) !void {
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 7, 0xc9);
    reply(f, d, s);
    try call(f, "dos64_files_start", 0);
    var now = f.word(try f.symbol("dos64_files_now"));
    var seen = false;
    for (0..4000) |_| {
        if (try g(f, "dos64_uci_state") == 3 and !seen) {
            for (cmd, 0..) |b, i| try std.testing.expectEqual(b, m.dos64_uci_model_command(f.machine, @intCast(i)));
            seen = true;
        }
        if (try g(f, "dos64_files_state") != 1) break;
        try tick(f, &now);
    }
    try std.testing.expect(seen);
    try std.testing.expect(try g(f, "dos64_files_state") != 1);
    try std.testing.expectEqual(now, f.word(try f.symbol("dos64_uci_now")));
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek((try f.symbol("dos64_uci_command")) - 1));
    try std.testing.expectEqual(@as(u8, 0xad), f.peek(try f.symbol("dos64_uci_buffer_end")));
}
fn open(f: *F) !void {
    try path(f, 2, "disk.img");
    try p(f, "dos64_files_mode", 1);
    try run(f, &.{ 1, 2, 1, 'd', 'i', 's', 'k', '.', 'i', 'm', 'g', 0 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 1), try g(f, "dos64_files_handle"));
}

test "files pinned identify path open seek read close exact commands and response bytes" {
    var f = try setup();
    defer f.deinit();
    f.initial_status = 0xef;
    try p(&f, "dos64_files_op", 1);
    try run(&f, &.{ 1, 1 }, "ULTIMATE-II DOS V1.2", "00,OK");
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
    try path(&f, 0x11, "/usb1");
    try run(&f, &.{ 1, 0x11, '/', 'u', 's', 'b', '1', 0 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 6), try g(&f, "dos64_files_path_len"));
    try open(&f);
    try p(&f, "dos64_files_op", 6);
    const a = try f.symbol("dos64_files_offset");
    for ([_]u8{ 0x78, 0x56, 0x34, 0x12 }, 0..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    try run(&f, &.{ 1, 6, 0x78, 0x56, 0x34, 0x12 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
    try p(&f, "dos64_files_op", 4);
    try w(&f, "dos64_files_count", 5);
    const data = [_]u8{ 0, 0x1a, 0xff, 0x41, 0x80 };
    try run(&f, &.{ 1, 4, 5, 0 }, &data, "");
    try std.testing.expectEqual(@as(u16, 5), f.word(try f.symbol("dos64_files_actual")));
    for (data, 0..) |b, i| try std.testing.expectEqual(b, f.peek((try f.symbol("dos64_uci_data")) + @as(u16, @intCast(i))));
    try p(&f, "dos64_files_op", 3);
    try run(&f, &.{ 1, 3 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
}

test "files short reads EOF and 512 bytes retain actual count" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    var d: [512]u8 = undefined;
    for (&d, 0..) |*b, i| b.* = @truncate(i * 37);
    for ([_]usize{ 0, 1, 255, 256, 511, 512 }) |n| {
        try p(&f, "dos64_files_op", 4);
        try w(&f, "dos64_files_count", 512);
        try run(&f, &.{ 1, 4, 0, 2 }, d[0..n], "");
        try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
        try std.testing.expectEqual(@as(u16, @intCast(n)), f.word(try f.symbol("dos64_files_actual")));
        try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_files_count_known"));
        try std.testing.expectEqual(@as(u8, if (n < 512) 1 else 0), try g(&f, "dos64_files_short"));
    }
}

test "files WRITE has unknown count despite OK and CLOSE cannot prove persistence" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    try p(&f, "dos64_files_op", 5);
    try w(&f, "dos64_files_count", 512);
    var cmd: [516]u8 = undefined;
    cmd[0..4].* = .{ 1, 5, 0, 2 };
    for (cmd[4..], 0..) |*b, i| b.* = @truncate(i * 19 + 7);
    const a = try f.symbol("dos64_uci_command");
    for (cmd[4..], 4..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    try run(&f, &cmd, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_count_known"));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_files_uncertain"));
    try p(&f, "dos64_files_op", 3);
    try run(&f, &.{ 1, 3 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_files_uncertain"));
}

test "files rejects stale reordered invalid requests without PUSH" {
    var f = try setup();
    defer f.deinit();
    for ([_]u8{ 3, 4, 5, 6, 7, 0, 0x81 }) |op| {
        try p(&f, "dos64_files_op", op);
        try call(&f, "dos64_files_start", 1);
    }
    try path(&f, 2, "disk.img");
    for ([_]u8{ 0, 4, 5, 8, 0xff }) |mode| {
        try p(&f, "dos64_files_mode", mode);
        try call(&f, "dos64_files_start", 1);
    }
    try std.testing.expectEqual(@as(u64, 0), m.dos64_uci_model_count(f.machine, 0));
    try open(&f);
    for ([_]u16{ 0, 513, 895, 65535 }) |n| {
        try p(&f, "dos64_files_op", 4);
        try w(&f, "dos64_files_count", n);
        try call(&f, "dos64_files_start", 1);
    }
    try p(&f, "dos64_files_target", 2);
    try p(&f, "dos64_files_op", 3);
    try call(&f, "dos64_files_start", 1);
    try p(&f, "dos64_files_target", 1);
    try p(&f, "dos64_files_op", 1);
    try call(&f, "dos64_files_start", 1);
    try path(&f, 2, "other.img");
    try p(&f, "dos64_files_mode", 1);
    try call(&f, "dos64_files_start", 1);
}

test "files status errors malformed response and oversized count cannot report success" {
    const Case = struct { d: []const u8, s: []const u8, e: u8 };
    for ([_]Case{ .{ .d = "", .s = "85,NO FILE OPEN", .e = 3 }, .{ .d = "X", .s = "00,OK", .e = 4 }, .{ .d = "", .s = "00,OK\x00", .e = 3 }, .{ .d = "", .s = "00,WRONG", .e = 3 } }) |c| {
        var f = try setup();
        defer f.deinit();
        try path(&f, 2, "disk.img");
        try p(&f, "dos64_files_mode", 1);
        try run(&f, &.{ 1, 2, 1, 'd', 'i', 's', 'k', '.', 'i', 'm', 'g', 0 }, c.d, c.s);
        try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_state"));
        try std.testing.expectEqual(c.e, try g(&f, "dos64_files_error"));
        try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_handle"));
        try std.testing.expectEqual(@as(u16, @intCast(c.s.len)), f.word(try f.symbol("dos64_uci_status_len")));
        try p(&f, "dos64_files_op", 3);
        try run(&f, &.{ 1, 3 }, "", "00,OK");
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
    }
    var f = try setup();
    defer f.deinit();
    try open(&f);
    try p(&f, "dos64_files_op", 4);
    try w(&f, "dos64_files_count", 1);
    try run(&f, &.{ 1, 4, 1, 0 }, "AB", "");
    try std.testing.expectEqual(@as(u8, 4), try g(&f, "dos64_files_error"));
    try run(&f, &.{ 1, 4, 1, 0 }, "A", "00,OK");
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_error"));
}

test "files unexpected MORE aborts without replacing first retained response" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    reply(&f, "first", "");
    reply(&f, "second", "");
    try p(&f, "dos64_files_op", 4);
    try w(&f, "dos64_files_count", 512);
    try call(&f, "dos64_files_start", 0);
    var now: u16 = 0;
    for (0..4000) |_| {
        if (try g(&f, "dos64_files_state") != 1) break;
        try tick(&f, &now);
    }
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 4), try g(&f, "dos64_files_error"));
    try std.testing.expectEqual(@as(u64, 0), m.dos64_uci_model_count(f.machine, 1));
    try std.testing.expectEqual(@as(u64, 1), m.dos64_uci_model_count(f.machine, 2));
    try std.testing.expectEqual(@as(u8, 'f'), f.peek(try f.symbol("dos64_uci_data")));
}

test "files elapsed timeout wraps and failed recovery requires caller reset" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 10000, 0xc9);
    reply(&f, "", "");
    try w(&f, "dos64_uci_timeout", 10);
    try w(&f, "dos64_files_now", 65530);
    try p(&f, "dos64_files_op", 4);
    try w(&f, "dos64_files_count", 1);
    try call(&f, "dos64_files_start", 0);
    var now: u16 = 65530;
    try tick(&f, &now);
    try tick(&f, &now);
    try w(&f, "dos64_files_now", 20);
    try call(&f, "dos64_files_poll", 0);
    try std.testing.expectEqual(@as(u8, 8), try g(&f, "dos64_uci_state"));
    try w(&f, "dos64_files_now", 100);
    try call(&f, "dos64_files_poll", 0);
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_error"));
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_transport_error"));
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_handle"));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_uci_recovery_failed"));
    try p(&f, "dos64_files_op", 3);
    try call(&f, "dos64_files_start", 1);
}

test "files closed firmware handle can recover after failed OPEN without false CLOSE success" {
    var f = try setup();
    defer f.deinit();
    try path(&f, 2, "disk.img");
    try p(&f, "dos64_files_mode", 1);
    try run(&f, &.{ 1, 2, 1, 'd', 'i', 's', 'k', '.', 'i', 'm', 'g', 0 }, "", "82,FILE NOT FOUND");
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_handle"));
    try p(&f, "dos64_files_op", 3);
    try run(&f, &.{ 1, 3 }, "", "84,NO FILE TO CLOSE");
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_files_handle"));
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_error"));
    try open(&f);
}

test "files active transaction rejects another start and does not replace command bytes" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 20, 0xc9);
    reply(&f, "x", "");
    try p(&f, "dos64_files_op", 4);
    try w(&f, "dos64_files_count", 1);
    try call(&f, "dos64_files_start", 0);
    const a = try f.symbol("dos64_uci_command");
    var before: [4]u8 = undefined;
    for (&before, 0..) |*b, i| b.* = f.peek(a + @as(u16, @intCast(i)));
    try call(&f, "dos64_files_start", 1);
    for (before, 0..) |b, i| try std.testing.expectEqual(b, f.peek(a + @as(u16, @intCast(i))));
    var now = f.word(try f.symbol("dos64_files_now"));
    for (0..4000) |_| {
        if (try g(&f, "dos64_files_state") != 1) break;
        try tick(&f, &now);
    }
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u64, 1), m.dos64_uci_model_count(f.machine, 0));
}

test "files exact path boundaries target two and input terminators validate before PUSH" {
    var f = try setup();
    defer f.deinit();
    try p(&f, "dos64_files_target", 2);
    try p(&f, "dos64_files_op", 2);
    try p(&f, "dos64_files_mode", 6);
    const a = try f.symbol("dos64_uci_command");
    var cmd: [255]u8 = @splat('A');
    cmd[0] = 2;
    cmd[1] = 2;
    cmd[2] = 6;
    cmd[254] = 0;
    for (cmd[3..], 3..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    try p(&f, "dos64_files_path_len", 252);
    try run(&f, &cmd, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_files_handle"));
    try p(&f, "dos64_files_op", 3);
    try run(&f, &.{ 2, 3 }, "", "00,OK");
    for ([_]u8{ 0, 1, 253, 255 }) |n| {
        try p(&f, "dos64_files_op", 2);
        try p(&f, "dos64_files_path_len", n);
        try call(&f, "dos64_files_start", 1);
    }
    try path(&f, 2, "abc");
    f.poke(a + 4, 0);
    try call(&f, "dos64_files_start", 1);
    try path(&f, 2, "abc");
    f.poke(a + 6, 'x');
    try call(&f, "dos64_files_start", 1);
}

test "files stale published reply cannot become a new operation result" {
    var f = try setup();
    defer f.deinit();
    reply(&f, "ULTIMATE-II DOS V1.2", "00,OK");
    m.dos64_uci_model_stale(f.machine, 0x20);
    try p(&f, "dos64_files_op", 1);
    try call(&f, "dos64_files_start", 0);
    var now: u16 = 0;
    for (0..4000) |_| {
        if (try g(&f, "dos64_files_state") != 1) break;
        try tick(&f, &now);
    }
    try std.testing.expectEqual(@as(u8, 3), try g(&f, "dos64_files_state"));
    try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_error"));
    try std.testing.expectEqual(@as(u8, 6), try g(&f, "dos64_files_transport_error"));
    try std.testing.expectEqual(@as(u64, 0), m.dos64_uci_model_count(f.machine, 0));
    try std.testing.expectEqual(@as(u64, 1), m.dos64_uci_model_count(f.machine, 2));
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_uci_recovery_failed"));
}

test "files scripted independent backing bytes survive seek and chunked binary reads" {
    var f = try setup();
    defer f.deinit();
    try open(&f);
    // This host array is the fake backing file, not an implementation of files.s.
    // The script validates each native wire request and supplies firmware replies.
    var backing: [1037]u8 = undefined;
    for (&backing, 0..) |*b, i| b.* = @truncate(i * 71 + 0x1a);
    var restored: [1037]u8 = undefined;
    const offset = try f.symbol("dos64_files_offset");
    const data = try f.symbol("dos64_uci_data");
    var pos: usize = 0;
    while (pos < backing.len) {
        const n = @min(512, backing.len - pos);
        try p(&f, "dos64_files_op", 6);
        f.poke(offset, @truncate(pos));
        f.poke(offset + 1, @truncate(pos >> 8));
        f.poke(offset + 2, 0);
        f.poke(offset + 3, 0);
        try run(&f, &.{ 1, 6, @truncate(pos), @truncate(pos >> 8), 0, 0 }, "", "00,OK");
        try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
        try p(&f, "dos64_files_op", 4);
        try w(&f, "dos64_files_count", @intCast(n));
        try run(&f, &.{ 1, 4, @truncate(n), @truncate(n >> 8) }, backing[pos..][0..n], "");
        try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
        const got = f.word(try f.symbol("dos64_files_actual"));
        try std.testing.expectEqual(@as(u16, @intCast(n)), got);
        for (0..got) |i| restored[pos + i] = f.peek(data + @as(u16, @intCast(i)));
        pos += got;
    }
    try std.testing.expectEqualSlices(u8, &backing, &restored);
}

test "files accepts pinned read write and create-new access masks only" {
    for ([_]u8{ 1, 2, 3, 6, 7 }) |mode| {
        var f = try setup();
        defer f.deinit();
        try path(&f, 2, "disk.img");
        try p(&f, "dos64_files_mode", mode);
        try run(&f, &.{ 1, 2, mode, 'd', 'i', 's', 'k', '.', 'i', 'm', 'g', 0 }, "", "00,OK");
        try std.testing.expectEqual(@as(u8, 2), try g(&f, "dos64_files_state"));
        try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_files_handle"));
    }
}

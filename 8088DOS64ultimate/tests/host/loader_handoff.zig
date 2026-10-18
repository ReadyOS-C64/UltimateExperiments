const std = @import("std");
const h = @import("machine.zig");
const F = h.Fixture;
const c = h.c;
const A = std.testing.allocator;
fn crc(b: []const u8) u32 {
    var v: u32 = 0xffffffff;
    for (b) |x| {
        v ^= x;
        for (0..8) |_| {
            const low = v & 1;
            v >>= 1;
            if (low != 0) v ^= 0xedb88320;
        }
    }
    return ~v;
}
fn d(b: []u8, at: usize, v: u32) void {
    std.mem.writeInt(u32, b[at..][0..4], v, .little);
}
fn path(b: []u8, at: usize, s: []const u8) void {
    @memset(b[at..][0..128], 0);
    @memcpy(b[at..][0..s.len], s);
}
fn cfg(ac: u32, bc: u32, present: u8, ro: u8, capacity: u32) [576]u8 {
    var b: [576]u8 = @splat(0);
    @memcpy(b[0..4], "D64C");
    b[4] = 1;
    b[5] = 0x40;
    b[6] = 2;
    path(&b, 8, "/sd/My DOS home");
    path(&b, 136, "/sd/My DOS home/A.IMG");
    if (present & 2 != 0) path(&b, 264, "/usb1/Working/B.IMG");
    if (present & 4 != 0) path(&b, 392, "/usb1/Working/C.IMG");
    b[524] = ro;
    b[525] = present;
    d(&b, 528, ac);
    d(&b, 532, bc);
    b[536] = 1;
    d(&b, 538, capacity);
    sign(&b);
    return b;
}
fn sign(b: *[576]u8) void {
    d(b, 572, crc(b[0..572]));
}
fn header(b: *const [576]u8) [32]u8 {
    var x: [32]u8 = @splat(0);
    @memcpy(x[0..4], "D64R");
    x[4] = 1;
    x[5] = 0xa5;
    x[6] = 32;
    @memcpy(x[8..12], b[572..576]);
    d(&x, 12, 0x12345678);
    @memcpy(x[16..24], b[528..536]);
    x[24] = 0x1c;
    x[25] = 0xdf;
    x[26] = 1;
    x[27] = 2;
    d(&x, 28, crc(x[0..28]));
    return x;
}
fn seed(f: *F, at: u32, b: []const u8) void {
    for (b, 0..) |v, i| c.dos64_reu_poke(f.machine, at + @as(u32, @intCast(i)), v);
}
fn record(f: *F, b: *const [576]u8) void {
    seed(f, 0x3ff000, &header(b));
    seed(f, 0x3ff020, b);
}
fn p(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn g(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn call(f: *F, n: []const u8, budget: u64, carry: u8) !void {
    const r = try f.call(n, budget);
    try std.testing.expectEqual(carry, r.p & 1);
}
fn init() !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    f.poke(0xfffa, 0x82);
    f.poke(0xfffb, 0x58);
    try p(&f, "dos64_loader_required", 0xa5);
    return f;
}
fn prepare(f: *F) !void {
    try call(f, "dos64_overlay_init", 10000, 0);
    try p(f, "dos64_overlay_reu_mib", 4);
    try call(f, "dos64_overlay_bootstrap", 1000000, 0);
    try call(f, "dos64_disk_init", 10000, 0);
    c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    try call(f, "dos64_uci_init", 10000, 0);
    try call(f, "dos64_overlay_files_init", 100000, 0);
    try call(f, "dos64_import_init", 10000, 0);
    try call(f, "dos64_loader_install", 100000, 0);
}
fn image(tag: u8) ![]u8 {
    const b = try A.alloc(u8, 368640);
    for (b, 0..) |*v, i| v.* = tag ^ @as(u8, @truncate(i * 13));
    for ([_]usize{ 11, 12, 19, 20, 21, 24, 25, 26, 27, 14, 15, 16 }, [_]u8{ 0, 2, 0xd0, 2, 0xfd, 9, 0, 2, 0, 1, 0, 2 }) |o, v| b[o] = v;
    return b;
}
fn check(f: *F, b: *const [576]u8, carry: u8) !void {
    record(f, b);
    try call(f, "dos64_loader_validate", 1000000, carry);
}
fn validationWrites(f: *F) !void {
    const ranges = [_][2]u16{
        .{ 0, 2 },                            .{ 0x100, 0x100 },                          .{ try f.symbol("dos64_segment"), 7 },
        .{ try f.symbol("reu_host_end"), 4 }, .{ try f.symbol("dos64_reu_request"), 10 }, .{ try f.symbol("dos64_reu_first_status"), 1 },
        .{ 0x4000, 17 },                      .{ 0xc100, 608 },                           .{ try f.symbol("dos64_native_config"), 142 },
        .{ try f.symbol("hdc_config"), 140 }, .{ 0xdf00, 11 },
    };
    for (0..65536) |i| {
        const at: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, at) == 0) continue;
        var owned = false;
        for (ranges) |range| {
            if (at >= range[0] and @as(u32, at) < @as(u32, range[0]) + range[1]) {
                owned = true;
                break;
            }
        }
        if (!owned) std.debug.print("loader validation write escaped ${x:0>4}\n", .{at});
        try std.testing.expect(owned);
    }
}

test "loader actual legacy zero and malformed required flag preserve configs and REU" {
    var f = try init();
    defer f.deinit();
    try p(&f, "dos64_loader_required", 0);
    const n = try f.symbol("dos64_native_config");
    f.poke(n + 4, 0x23);
    try call(&f, "dos64_loader_validate", 10000, 0);
    try std.testing.expectEqual(@as(u8, 0x23), f.peek(n + 4));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_dma_transfers(f.machine));
    for ([_]u8{ 1, 0xff }) |v| {
        try p(&f, "dos64_loader_required", v);
        try call(&f, "dos64_loader_validate", 10000, 1);
    }
    try p(&f, "dos64_loader_required", 0xa5);
    try call(&f, "dos64_loader_validate", 1000000, 1);
}
test "loader validates capacity floors paths readonly and32HDslots then consumes ready" {
    for ([_]u32{ 0x400000, 0x410000, 0x5f0000, 0xff0000, 0x1000000 }) |capacity| {
        var f = try init();
        defer f.deinit();
        var b = cfg(0x1234, 0x5678, 7, 5, capacity);
        b[522] = 1;
        sign(&b);
        try check(&f, &b, 0);
        try validationWrites(&f);
        const n = try f.symbol("dos64_native_config");
        const hd = try f.symbol("hdc_config");
        try std.testing.expectEqual(@as(u8, @intCast(capacity >> 20)), f.peek(n + 5));
        try std.testing.expectEqual(@as(u8, 32), f.peek(hd + 10));
        try std.testing.expectEqual(@as(u8, 2), f.peek(hd + 9));
        try std.testing.expectEqual(@as(u8, 0), f.peek(hd + 8));
        try std.testing.expectEqual(@as(u8, 1), f.peek(hd + 7));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x3ff005));
        try call(&f, "dos64_loader_validate", 1000000, 1);
    }
}
test "loader every header and CFG single-byte corruption is rejected" {
    const b = cfg(0, 0, 1, 0, 0x400000);
    for (0..608) |index| {
        var f = try init();
        defer f.deinit();
        record(&f, &b);
        const at = 0x3ff000 + @as(u32, @intCast(index));
        c.dos64_reu_poke(f.machine, at, c.dos64_reu_peek(f.machine, at) ^ 1);
        try call(&f, "dos64_loader_validate", 1000000, 1);
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_disk_loaded"));
    }
}
test "loader correctly resigned semantic malformed records rejected" {
    const cases = [_][2]usize{ .{ 0, 88 }, .{ 4, 2 }, .{ 5, 0x41 }, .{ 6, 3 }, .{ 7, 1 }, .{ 525, 0 }, .{ 525, 9 }, .{ 524, 8 }, .{ 524, 2 }, .{ 526, 1 }, .{ 527, 1 }, .{ 520, 1 }, .{ 521, 1 }, .{ 522, 1 }, .{ 523, 1 }, .{ 536, 0 }, .{ 537, 1 }, .{ 538, 1 }, .{ 539, 1 }, .{ 540, 0x3f }, .{ 541, 2 }, .{ 542, 1 }, .{ 571, 1 }, .{ 532, 1 }, .{ 135, 1 }, .{ 263, 1 }, .{ 264, 47 }, .{ 391, 1 }, .{ 392, 47 }, .{ 519, 1 } };
    for (cases) |entry| {
        var f = try init();
        defer f.deinit();
        var b = cfg(0, 0, 1, 0, 0x400000);
        b[entry[0]] = @intCast(entry[1]);
        sign(&b);
        record(&f, &b);
        const r = try f.call("dos64_loader_validate", 1000000);
        if (r.p & 1 != 1) std.debug.print("semantic accepted offset{d} value{x}\n", .{ entry[0], entry[1] });
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    }
    for ([_][]const u8{ "relative", "/sd//A", "/sd/./A", "/sd/../A", "/sd/A.", "/sd/A ", "/sd/A\\B", "/sd/A:B", "/sd/A\x7fB", "/sd/A\x80B", "/" }) |name| {
        var f = try init();
        defer f.deinit();
        var b = cfg(0, 0, 1, 0, 0x400000);
        path(&b, 136, name);
        sign(&b);
        try check(&f, &b, 1);
    }
}
test "loader header cross fields UCI targets NMI and CFGcodeword binding" {
    for (0..8) |which| {
        var f = try init();
        defer f.deinit();
        var b = cfg(0, 0, 1, 0, 0x400000);
        record(&f, &b);
        var x = header(&b);
        switch (which) {
            0 => x[16] ^= 1,
            1 => x[20] ^= 1,
            2 => x[24] = 0x1d,
            3 => x[25] = 0xdc,
            4 => x[26] = 2,
            5 => x[27] = 1,
            6 => {
                b[8 + 4] = 'X';
                sign(&b);
                seed(&f, 0x3ff020, &b);
            },
            7 => f.poke(0xfffa, 0x83),
            else => unreachable,
        }
        d(&x, 28, crc(x[0..28]));
        seed(&f, 0x3ff000, &x);
        try call(&f, "dos64_loader_validate", 1000000, 1);
    }
}
test "loader helper exact REU readback before execution and alloriginal FILE bytes retained" {
    for ([_]usize{ 0, 17, 255, 256, 306 }) |offset| {
        var f = try init();
        defer f.deinit();
        const b = cfg(0, 0, 1, 0, 0x400000);
        try check(&f, &b, 0);
        try call(&f, "dos64_overlay_init", 10000, 0);
        try p(&f, "dos64_overlay_reu_mib", 4);
        try call(&f, "dos64_overlay_bootstrap", 1000000, 0);
        const at = 0x3405c8 + @as(u32, @intCast(offset));
        c.dos64_reu_poke(f.machine, at, c.dos64_reu_peek(f.machine, at) ^ 1);
        try call(&f, "dos64_loader_install", 100000, 1);
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_disk_loaded"));
    }
}
test "loader adopts full independent A and B readonly generation and CRC bindings" {
    var f = try init();
    defer f.deinit();
    const a = try image(0x23);
    defer A.free(a);
    const b = try image(0xa7);
    defer A.free(b);
    const config = cfg(crc(a), crc(b), 3, 1, 0x400000);
    seed(&f, 0x100000, a);
    seed(&f, 0x180000, b);
    try check(&f, &config, 0);
    try prepare(&f);
    try call(&f, "dos64_loader_adopt", 500000000, 0);
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
    const desc = try f.symbol("dos64_disk_b_descriptor");
    try std.testing.expectEqual(@as(u8, 1), f.peek(desc + 9));
    const ro = try f.symbol("dos64_disk_readonly");
    try std.testing.expectEqual(@as(u8, 1), f.peek(ro));
    try std.testing.expectEqual(@as(u8, 0), f.peek(ro + 1));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x100000, a.ptr, a.len));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x180000, b.ptr, b.len));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_uci_model_count(f.machine, 0));
}
test "loader phase2 changed CFG CRC image tail and geometry cannot publish" {
    const a = try image(0x23);
    defer A.free(a);
    for (0..3) |kind| {
        var f = try init();
        defer f.deinit();
        const b = cfg(crc(a), 0, 1, 0, 0x400000);
        seed(&f, 0x100000, a);
        try check(&f, &b, 0);
        try prepare(&f);
        switch (kind) {
            0 => c.dos64_reu_poke(f.machine, 0x3ff020 + 8, 0),
            1 => c.dos64_reu_poke(f.machine, 0x159fff, c.dos64_reu_peek(f.machine, 0x159fff) ^ 1),
            2 => {
                var bad = cfg(crc(a), 0, 1, 0, 0x400000);
                bad[9] ^= 1;
                sign(&bad);
                seed(&f, 0x3ff020, &bad);
            },
            else => unreachable,
        }
        try call(&f, "dos64_loader_adopt", 500000000, 1);
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_disk_loaded"));
    }
}
test "loader actual NMI delivery preserves phase1 and preloaded startup without legacy IO" {
    var f = try init();
    defer f.deinit();
    const a = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img", A, .limited(368641));
    defer A.free(a);
    const b = cfg(crc(a), 0, 1, 0, 0x400000);
    record(&f, &b);
    seed(&f, 0x100000, a);
    c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
    c.dos64_cia_clock_enable(f.machine);
    c.dos64_cia_clock_step(f.machine, 1);
    c.dos64_native_display_enable(f.machine);
    c.native_runtime_control_enable(f.machine);
    c.dos64_nmi_at_pc(f.machine, try f.symbol("dos64_reu_transfer"));
    try call(&f, "dos64_native_start", 500000000, 0);
    try std.testing.expectEqual(@as(u32, 1), c.dos64_nmi_delivered(f.machine));
    try std.testing.expectEqual(@as(u8, 4), f.peek(try f.symbol("dos64_native_diag")));
    try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_uci_model_count(f.machine, 0));
    try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_cold_open"));
}
test "loader helper NMI full A B startup and B failure never boots partial configuration" {
    const a = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img", A, .limited(368641));
    defer A.free(a);
    const b = try image(0x95);
    defer A.free(b);
    for ([_]bool{ false, true }) |bad| {
        var f = try init();
        defer f.deinit();
        const config = cfg(crc(a), crc(b), 3, 3, 0x400000);
        record(&f, &config);
        seed(&f, 0x100000, a);
        seed(&f, 0x180000, b);
        if (bad) c.dos64_reu_poke(f.machine, 0x1d9fff, c.dos64_reu_peek(f.machine, 0x1d9fff) ^ 1);
        c.dos64_uci_model_enable(f.machine, 0xdf1c, 3, 0xc9);
        c.dos64_cia_clock_enable(f.machine);
        c.dos64_cia_clock_step(f.machine, 1);
        c.dos64_native_display_enable(f.machine);
        c.native_runtime_control_enable(f.machine);
        c.dos64_nmi_at_pc(f.machine, try f.symbol("dos64_loader_adopt"));
        try call(&f, "dos64_native_start", 500000000, if (bad) 1 else 0);
        try std.testing.expectEqual(@as(u32, 1), c.dos64_nmi_delivered(f.machine));
        try std.testing.expectEqual(@as(u8, if (bad) 0xe1 else 4), f.peek(try f.symbol("dos64_native_diag")));
        try std.testing.expectEqual(@as(u8, 1), try g(&f, "dos64_disk_loaded"));
        try std.testing.expectEqual(@as(u8, if (bad) 0 else 1), f.peek((try f.symbol("dos64_disk_b_descriptor")) + 9));
        if (bad) {
            try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_bios_ready"));
            try std.testing.expectEqual(@as(u16, 0), f.word(try f.symbol("dos64_cpu_instructions")));
        }
        try std.testing.expectEqual(@as(u64, 0), c.dos64_uci_model_count(f.machine, 0));
    }
}
test "loader actual geometry rejection and REU page failure publish no A" {
    for ([_]bool{ false, true }) |dma| {
        var f = try init();
        defer f.deinit();
        const a = try image(0x29);
        defer A.free(a);
        if (!dma) a[24] = 8;
        const b = cfg(crc(a), 0, 1, 0, 0x400000);
        seed(&f, 0x100000, a);
        try check(&f, &b, 0);
        try prepare(&f);
        if (dma) c.dos64_reu_fail_after(f.machine, 256, 17);
        try call(&f, "dos64_loader_adopt", 500000000, 1);
        try std.testing.expectEqual(@as(u8, 0), try g(&f, "dos64_disk_loaded"));
    }
    for ([_]u32{ 0, 17, 607 }) |prefix| {
        var f = try init();
        defer f.deinit();
        const b = cfg(0, 0, 1, 0, 0x400000);
        record(&f, &b);
        c.dos64_reu_fail_after(f.machine, 0, prefix);
        try call(&f, "dos64_loader_validate", 1000000, 1);
        try std.testing.expectEqual(@as(u8, 0xa5), c.dos64_reu_peek(f.machine, 0x3ff005));
    }
}

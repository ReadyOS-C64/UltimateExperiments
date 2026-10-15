const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const palette = [_]u8{ 0, 6, 5, 3, 2, 4, 9, 15, 12, 14, 13, 3, 10, 4, 7, 1 };
fn random(state: *u32) u8 {
    state.* = state.* *% 1664525 +% 1013904223;
    return @truncate(state.* >> 19);
}
fn init(frames: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"), 4);
    _ = try f.call("dos64_overlay_bootstrap", 10_000);
    // Acquire the renderer once before injecting range/cache DMA failures, so
    // those injections continue to target the original coherent reads.
    f.poke(try f.symbol("dos64_overlay_requested"), 2);
    _ = try f.call("dos64_overlay_acquire", 10_000);
    _ = try f.call("dos64_overlay_release", 10_000);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    f.initial_status = 0xec;
    const guest = try f.symbol("dos64_guest");
    for (0..28) |i| f.poke(guest + @as(u16, @intCast(i)), @as(u8, @intCast(i)) *% 19 +% 0xa7);
    return f;
}
fn backingWord(f: *Fixture, at: u32, value: u16) void {
    c.dos64_reu_poke(f.machine, at, @truncate(value));
    c.dos64_reu_poke(f.machine, at + 1, @truncate(value >> 8));
}
fn geometry(f: *Fixture, mode: u8, page: u8) !void {
    const columns: u16 = if (mode < 2) 40 else 80;
    const stride: u16 = if (columns == 40) 2048 else 4096;
    c.dos64_reu_poke(f.machine, 0x449, mode);
    backingWord(f, 0x44a, columns);
    backingWord(f, 0x44c, stride);
    backingWord(f, 0x44e, stride * page);
    c.dos64_reu_poke(f.machine, 0x462, page);
    // Only read-only frames exist while changing this raw fixture backing.
    _ = try f.call("dos64_cache_init", 50_000);
}
fn busWrite(f: *Fixture, address: u32, value: u8) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address));
    f.poke(a + 1, @truncate(address >> 8));
    f.poke(a + 2, @truncate(address >> 16));
    f.poke(try f.symbol("dos64_mem_value"), value);
    const r = try f.call("dos64_mem_write", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn render(f: *Fixture, row: u8, blink: u8, done: u8, error_code: u8) !void {
    const request = try f.symbol("dos64_render_text_request");
    f.poke(request, row);
    f.poke(request + 1, blink);
    for (2..5) |i| f.poke(request + @as(u16, @intCast(i)), 0xd7);
    const guest = try f.symbol("dos64_guest");
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| v.* = f.peek(guest + @as(u16, @intCast(i)));
    const port = f.peek(1);
    const ddr = f.peek(0);
    // Resident wrappers require the documented RAM+I/O mapping. For the
    // underlying renderer's separate banking ABI oracle, acquire while mapped,
    // restore the tested mapping, call the real target under the held lock,
    // then release from the resident mapping. Normal calls use the wrapper.
    const direct = ddr != 0x2f or port != 0x35;
    if (direct) {
        f.poke(0, 0x2f);
        f.poke(1, 0x35);
        f.poke(try f.symbol("dos64_overlay_requested"), 2);
        const acquired = try f.call("dos64_overlay_acquire", 10_000);
        try std.testing.expectEqual(@as(u8, 0), acquired.p & 1);
        f.poke(0, ddr);
        f.poke(1, port);
    }
    const r = try f.call(if (direct) "dos64_render_text_row" else "dos64_overlay_render_text_row", 2_000_000);
    if ((r.p & 1) != (if (error_code == 0) @as(u8, 0) else 1)) std.debug.print("Render status divergence row={d} blink={d} done={d} status={d} error={d}\n", .{ row, blink, f.peek(request + 2), f.peek(request + 3), f.peek(request + 4) });
    try std.testing.expectEqual(if (error_code == 0) @as(u8, 0) else 1, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    try std.testing.expectEqual(ddr, f.peek(0));
    // Latent latch bits configured as inputs are not readable on a 6510.
    try std.testing.expectEqual(port & ddr, f.peek(1) & ddr);
    try std.testing.expectEqual(done, f.peek(request + 2));
    try std.testing.expectEqual(if (error_code == 0) @as(u8, 1) else 2, f.peek(request + 3));
    try std.testing.expectEqual(error_code, f.peek(request + 4));
    if (direct) {
        f.poke(0, 0x2f);
        f.poke(1, 0x35);
        _ = try f.call("dos64_overlay_release", 10_000);
        f.poke(0, ddr);
        f.poke(1, port);
    }
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_overlay_busy")));
    for (before, 0..) |v, i| try std.testing.expectEqual(v, f.peek(guest + @as(u16, @intCast(i))));
}
fn half(byte: u8) u8 {
    var result: u8 = 0;
    for (0..4) |x| {
        const shift: u3 = @intCast(6 - x * 2);
        if (((byte >> shift) & 3) != 0) result |= @as(u8, 1) << @as(u3, @intCast(3 - x));
    }
    return result;
}
const Screen = struct {
    font: [2048]u8,
    vram: [16384]u8,
    bitmap: [8000]u8 = @splat(0xa7),
    matrix: [1000]u8 = @splat(0x5c),
    resident_first: u8,
    fn seed(f: *Fixture, seed_value: u32) Screen {
        var s = Screen{ .font = undefined, .vram = undefined, .resident_first = f.peek(0x5000) };
        var state = seed_value;
        for (&s.font, 0..) |*v, i| {
            v.* = random(&state);
            f.poke(0x4800 + @as(u16, @intCast(i)), v.*);
        }
        for (&s.vram, 0..) |*v, i| {
            v.* = random(&state);
            c.dos64_reu_poke(f.machine, 0xb8000 + @as(u32, @intCast(i)), v.*);
        }
        s.clear(f);
        return s;
    }
    fn clear(s: *Screen, f: *Fixture) void {
        @memset(&s.bitmap, 0xa7);
        @memset(&s.matrix, 0x5c);
        for (0x4000..0x4800) |a| f.poke(@intCast(a), 0x5c);
        for (0x6000..0x8000) |a| f.poke(@intCast(a), 0xa7);
        f.poke(0x3fff, 0x39);
        // 5000 is live resident DEVICECODE in the combined link; never corrupt it.
        f.poke(0x5fff, 0x76);
    }
    fn row(s: *Screen, mode: u8, page: u8, row_number: u8, blink: bool, cells: u8) void {
        const cols: usize = if (mode < 2) 40 else 80;
        const stride: usize = if (cols == 40) 2048 else 4096;
        for (0..cells) |cell| {
            const offset = @as(usize, page) * stride + @as(usize, row_number) * cols * 2 + cell * (if (cols == 40) @as(usize, 2) else 4);
            const left_char = s.vram[offset];
            const left_attr = s.vram[offset + 1];
            s.matrix[@as(usize, row_number) * 40 + cell] = (palette[left_attr & 15] << 4) | palette[(left_attr >> 4) & 7];
            for (0..8) |line| {
                const left = if (!blink and left_attr & 0x80 != 0) @as(u8, 0) else s.font[@as(usize, left_char) * 8 + line];
                var pixels = left;
                if (cols == 80) {
                    const right = if (!blink and s.vram[offset + 3] & 0x80 != 0) @as(u8, 0) else s.font[@as(usize, s.vram[offset + 2]) * 8 + line];
                    pixels = half(left) * 16 + half(right);
                }
                s.bitmap[@as(usize, row_number) * 320 + cell * 8 + line] = pixels;
            }
        }
    }
    fn compare(s: *const Screen, f: *Fixture) !void {
        for (s.bitmap, 0..) |v, i| {
            const actual = f.peek(0x6000 + @as(u16, @intCast(i)));
            if (v != actual) std.debug.print("Text bitmap divergence offset {x}, expected {x}, actual {x}\n", .{ i, v, actual });
            try std.testing.expectEqual(v, actual);
        }
        for (s.matrix, 0..) |v, i| try std.testing.expectEqual(v, f.peek(0x4000 + @as(u16, @intCast(i))));
        for (s.font, 0..) |v, i| try std.testing.expectEqual(v, f.peek(0x4800 + @as(u16, @intCast(i))));
        for (0x43e8..0x4800) |a| try std.testing.expectEqual(@as(u8, 0x5c), f.peek(@intCast(a)));
        for (0x7f40..0x8000) |a| try std.testing.expectEqual(@as(u8, 0xa7), f.peek(@intCast(a)));
        try std.testing.expectEqual(@as(u8, 0x39), f.peek(0x3fff));
        try std.testing.expectEqual(s.resident_first, f.peek(0x5000));

        try std.testing.expectEqual(@as(u8, 0x76), f.peek(0x5fff));
    }
    fn guestUnchanged(s: *const Screen, f: *Fixture) !void {
        const r = try f.call("dos64_cache_flush", 1_000_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0xb8000, &s.vram, s.vram.len));
    }
};

test "text renderer every mode page and row matches full independent bitmap matrix font and guard oracle" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0x65108088);
    var max_cycles: [4]u64 = @splat(0);
    for (0..4) |mode| {
        const pages: usize = if (mode < 2) 8 else 4;
        for (0..pages) |page| {
            try geometry(&f, @intCast(mode), @intCast(page));
            s.clear(&f);
            for (0..25) |row| {
                const blink: u8 = @intCast((row + page + mode) % 2);
                const before_cycles = c.dos64_get_regs(f.machine).cycles;
                try render(&f, @intCast(row), blink, 40, 0);
                max_cycles[mode] = @max(max_cycles[mode], c.dos64_get_regs(f.machine).cycles - before_cycles);
                s.row(@intCast(mode), @intCast(page), @intCast(row), blink == 1, 40);
                try s.compare(&f);
            }
            try s.guestUnchanged(&f);
        }
    }
    std.debug.print("Text renderer 600 rows: max native cycles modes 0..3={any}; excludes REU stalls/physical elapsed\n", .{max_cycles});
}

test "text renderer rejects inconsistent geometry invalid pages rows and blink without output" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0xaabbccdd);
    const mutations = [_]struct { address: u32, value: u8 }{
        .{ .address = 0x449, .value = 4 },  .{ .address = 0x449, .value = 255 },
        .{ .address = 0x44a, .value = 80 }, .{ .address = 0x44b, .value = 1 },
        .{ .address = 0x44c, .value = 1 },  .{ .address = 0x44d, .value = 16 },
        .{ .address = 0x44e, .value = 1 },  .{ .address = 0x44f, .value = 8 },
        .{ .address = 0x462, .value = 8 },
    };
    for (mutations) |mutation| {
        try geometry(&f, 0, 0);
        c.dos64_reu_poke(f.machine, mutation.address, mutation.value);
        try render(&f, 0, 1, 0, 1);
        try s.compare(&f);
    }
    try geometry(&f, 3, 0);
    c.dos64_reu_poke(f.machine, 0x462, 4);
    try render(&f, 0, 1, 0, 1);
    try geometry(&f, 3, 0);
    try render(&f, 25, 1, 0, 1);
    try render(&f, 255, 1, 0, 1);
    try render(&f, 0, 2, 0, 1);
    try s.compare(&f);
    try s.guestUnchanged(&f);
}

test "text renderer sees dirty one-frame VRAM and restores bank outputs DDR and native flags" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0x80ff0088);
    try geometry(&f, 3, 3);
    const start: usize = 3 * 4096 + 24 * 160;
    s.vram[start + 158] ^= 0xff;
    s.vram[start + 159] = 0x87;
    try busWrite(&f, 0xb8000 + @as(u32, @intCast(start + 158)), s.vram[start + 158]);
    try busWrite(&f, 0xb8000 + @as(u32, @intCast(start + 159)), s.vram[start + 159]);
    try std.testing.expect(s.vram[start + 159] != c.dos64_reu_peek(f.machine, 0xb8000 + @as(u32, @intCast(start + 159))));
    for ([_]u8{ 0x00, 0x07, 0x2f, 0xff }) |ddr| {
        for ([_]u8{ 0x30, 0x35, 0x37 }) |port| {
            f.initial_status = switch (port) {
                0x30 => 0x22,
                0x35 => 0xec,
                else => 0xeb,
            };
            f.poke(0, ddr);
            f.poke(1, port);
            try render(&f, 24, 0, 40, 0);
            s.row(3, 3, 24, false, 40);
            try s.compare(&f);
        }
    }
    f.poke(0, 0x2f);
    f.poke(1, 0x35);
    try s.guestUnchanged(&f);
}

test "text renderer reports exact committed cells on cache failure and whole row retry" {
    // 80-col row 3 starts byte 480, so 8 host cells precede the page seam.
    for (0..3) |skip| {
        var f = try init(1);
        defer f.deinit();
        var s = Screen.seed(&f, 0x12345678);
        try geometry(&f, 3, 0);
        c.dos64_reu_fail_after(f.machine, @intCast(skip), 17);
        const done: u8 = if (skip == 2) 8 else 0;
        try render(&f, 3, 1, done, 2);
        s.row(3, 0, 3, true, done);
        try s.compare(&f);
        try render(&f, 3, 1, 40, 0);
        s.row(3, 0, 3, true, 40);
        try s.compare(&f);
        try s.guestUnchanged(&f);
    }
}

test "text renderer independent blink halves and all RGBI palette entries" {
    var f = try init(2);
    defer f.deinit();
    var s = Screen.seed(&f, 0);
    @memset(&s.font, 0xff);
    for (s.font, 0..) |v, i| f.poke(0x4800 + @as(u16, @intCast(i)), v);
    for (0..40) |cell| {
        const at = cell * 4;
        s.vram[at] = @intCast(cell);
        s.vram[at + 1] = @as(u8, @intCast((cell % 8) * 16 + cell % 16)) | (if (cell % 2 == 0) @as(u8, 0x80) else 0);
        s.vram[at + 2] = @intCast(255 - cell);
        s.vram[at + 3] = if (cell % 3 == 0) 0x80 else 0;
        for (0..4) |i| c.dos64_reu_poke(f.machine, 0xb8000 + @as(u32, @intCast(at + i)), s.vram[at + i]);
    }
    try geometry(&f, 3, 0);
    for ([_]u8{ 0, 1, 0 }) |phase| {
        try render(&f, 0, phase, 40, 0);
        s.row(3, 0, 0, phase == 1, 40);
        try s.compare(&f);
    }
    try s.guestUnchanged(&f);
}

test "text renderer reads dirty BDA geometry and leaves coherent guest state untouched" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0xabcdef01);
    try geometry(&f, 0, 0);
    // All changes remain authoritative in the single dirty BDA frame.
    const updates = [_]struct { at: u32, value: u8 }{
        .{ .at = 0x449, .value = 3 },  .{ .at = 0x44a, .value = 80 },
        .{ .at = 0x44d, .value = 16 }, .{ .at = 0x44f, .value = 0x30 },
        .{ .at = 0x462, .value = 3 },
    };
    for (updates) |update| try busWrite(&f, update.at, update.value);
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x449));
    try render(&f, 17, 1, 40, 0);
    s.row(3, 3, 17, true, 40);
    try s.compare(&f);
    try s.guestUnchanged(&f);
    for (updates) |update| try std.testing.expectEqual(update.value, c.dos64_reu_peek(f.machine, update.at));
}

test "text renderer dirty VRAM write-back failure preserves authority and succeeds on retry" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0x11223344);
    try geometry(&f, 0, 0);
    s.vram[0] ^= 0xff;
    try busWrite(&f, 0xb8000, s.vram[0]);
    // BDA read must evict the dirty VRAM frame; inject a partial write-back.
    c.dos64_reu_fail_after(f.machine, 0, 17);
    try render(&f, 0, 1, 0, 2);
    try s.compare(&f);
    try render(&f, 0, 1, 40, 0);
    s.row(0, 0, 0, true, 40);
    try s.compare(&f);
    try s.guestUnchanged(&f);
}

test "text renderer all 256 text attributes retain left palette and blink policy" {
    var f = try init(1);
    defer f.deinit();
    var s = Screen.seed(&f, 0x13572468);
    for (0..256) |attribute| {
        s.vram[attribute * 2] = @intCast(attribute);
        s.vram[attribute * 2 + 1] = @intCast(attribute);
        c.dos64_reu_poke(f.machine, 0xb8000 + @as(u32, @intCast(attribute * 2)), @intCast(attribute));
        c.dos64_reu_poke(f.machine, 0xb8001 + @as(u32, @intCast(attribute * 2)), @intCast(attribute));
    }
    try geometry(&f, 0, 0);
    for ([_]u8{ 0, 1 }) |phase| {
        for (0..7) |row_number| {
            try render(&f, @intCast(row_number), phase, 40, 0);
            s.row(0, 0, @intCast(row_number), phase == 1, 40);
            try s.compare(&f);
        }
    }
    try s.guestUnchanged(&f);
}

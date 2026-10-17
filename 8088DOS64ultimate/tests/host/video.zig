const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const allocator = std.testing.allocator;

fn word(f: *Fixture, a: u16, v: u16) void {
    f.poke(a, @truncate(v));
    f.poke(a +% 1, @truncate(v >> 8));
}
fn reg(f: *Fixture, index: u16, value: u16) !void {
    word(f, (try f.symbol("dos64_guest")) + index * 2, value);
}
fn init(frames: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"),4);
    const boot = try f.call("dos64_overlay_bootstrap",300_000);
    try std.testing.expectEqual(@as(u8,0),boot.p&1);
    try std.testing.expectEqual(@as(u8,0xa5),f.peek(try f.symbol("hdb_extension_ready")));
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    _ = try f.call("dos64_cpu_init", 10_000);
    const g = try f.symbol("dos64_guest");
    for (0..14) |i| word(&f, g + @as(u16, @intCast(i)) * 2, 0xa700 + @as(u16, @intCast(i)));
    word(&f, g + 26, 0xfbd7);
    f.initial_status = 0xec;
    return f;
}
fn guest(f: *Fixture) ![28]u8 {
    var bytes: [28]u8 = undefined;
    const g = try f.symbol("dos64_guest");
    for (&bytes, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    return bytes;
}
fn invoke(f: *Fixture, ax: u16, bx: u16, cx: u16, dx: u16, outputs: []const u8, handled: bool) !void {
    try reg(f, 0, ax);
    try reg(f, 3, bx);
    try reg(f, 1, cx);
    try reg(f, 2, dx);
    const before = try guest(f);
    const result = try f.call("dos64_video_service", 30_000_000);
    try std.testing.expectEqual(if (handled) @as(u8, 0) else @as(u8, 1), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0xec), result.p & 0xec);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_video_host_error")));
    const after = try guest(f);
    for (before, after, 0..) |a, b, i| {
        if (std.mem.indexOfScalar(u8, outputs, @intCast(i)) != null) continue;
        if (a != b) std.debug.print("Video changed unrelated guest byte {d}: {x}->{x}, AX={x}\n", .{ i, a, b, ax });
        try std.testing.expectEqual(a, b);
    }
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 1_000_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
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
fn busRead(f: *Fixture, address: u32) !u8 {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address));
    f.poke(a + 1, @truncate(address >> 8));
    f.poke(a + 2, @truncate(address >> 16));
    const r = try f.call("dos64_mem_read", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}
fn backingWord(f: *Fixture, a: u32) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, a)) | (@as(u16, c.dos64_reu_peek(f.machine, a + 1)) << 8);
}
fn mode(f: *Fixture, value: u8) !void {
    try invoke(f, value, 0x1234, 0x5678, 0x9abc, &.{}, true);
}
fn cursor(f: *Fixture, page: u8, row: u8, col: u8) !void {
    try invoke(f, 0x0200, @as(u16, page) << 8, 0x7788, (@as(u16, row) << 8) | col, &.{}, true);
}
fn expectBytes(f: *Fixture, address: u32, expected: []const u8) !void {
    const first = c.dos64_reu_compare(f.machine, address, expected.ptr, expected.len);
    if (first != 0xffffffff) {
        std.debug.print("Video first divergence physical {x}: expected {x}, actual {x}\n", .{ address + first, expected[first], c.dos64_reu_peek(f.machine, address + first) });
        return error.VideoMemoryMismatch;
    }
}

// Independent logical screen oracle: cells are addressed by page/row/column.
// Scroll reads a snapshot, so overlap correctness does not depend on traversal.
const Screen = struct {
    bytes: [16384]u8,
    cols: u8,
    stride: usize,
    pages: u8,
    row: [8]u8 = @splat(0),
    col: [8]u8 = @splat(0),
    fn init(cols: u8) Screen {
        var s = Screen{ .bytes = undefined, .cols = cols, .stride = if (cols == 40) 2048 else 4096, .pages = if (cols == 40) 8 else 4 };
        for (&s.bytes, 0..) |*v, i| v.* = if (i % 2 == 0) 0x20 else 7;
        return s;
    }
    fn index(s: *const Screen, page: u8, row: u8, col: u8) usize {
        return @as(usize, page) * s.stride + (@as(usize, row) * s.cols + col) * 2;
    }
    fn scroll(s: *Screen, page: u8, top: u8, left: u8, bottom: u8, right: u8, lines: u8, attr: u8, down: bool) void {
        const before = s.bytes;
        const height: u16 = @as(u16, bottom) - top + 1;
        var row: u16 = top;
        while (row <= bottom) : (row += 1) {
            var col: u16 = left;
            while (col <= right) : (col += 1) {
                const dst = s.index(page, @intCast(row), @intCast(col));
                const src: i32 = @as(i32, row) + (if (down) -@as(i32, lines) else @as(i32, lines));
                if (lines == 0 or lines >= height or src < top or src > bottom) {
                    s.bytes[dst] = 0x20;
                    s.bytes[dst + 1] = attr;
                } else {
                    const at = s.index(page, @intCast(src), @intCast(col));
                    s.bytes[dst] = before[at];
                    s.bytes[dst + 1] = before[at + 1];
                }
            }
        }
    }
    fn tty(s: *Screen, page: u8, char: u8) void {
        if (char == 7) return;
        const at = s.index(page, s.row[page], s.col[page]);
        switch (char) {
            8 => {
                if (s.col[page] != 0) s.col[page] -= 1;
            },
            13 => s.col[page] = 0,
            10 => s.row[page] += 1,
            else => {
                s.bytes[at] = char;
                s.col[page] += 1;
                if (s.col[page] == s.cols) {
                    s.col[page] = 0;
                    s.row[page] += 1;
                }
            },
        }
        if (s.row[page] == 25) {
            const attr = s.bytes[s.index(page, 24, s.col[page]) + 1];
            s.scroll(page, 0, 0, 24, s.cols - 1, 1, attr, false);
            s.row[page] = 24;
        }
    }
    fn compare(s: *const Screen, f: *Fixture) !void {
        try flush(f);
        try expectBytes(f, 0xb8000, &s.bytes);
    }
};
fn seedScreen(f: *Fixture, s: *Screen) !void {
    // Initialize via the authoritative bus, forcing dirty page evictions.
    for (&s.bytes, 0..) |*v, i| {
        v.* = @truncate((i * 37 + i / 83 + 9) ^ (i >> 4));
        try busWrite(f, 0xb8000 + @as(u32, @intCast(i)), v.*);
    }
}

// Fixed seed and arithmetic keep this fixture independent of Zig RNG changes.
fn random(state: *u32) u32 {
    state.* = state.* *% 1664525 +% 1013904223;
    return state.*;
}

test "video modes 0 through 6 clear every CGA byte and establish exact BDA with one and two cache frames" {
    for ([_]u8{ 1, 2 }) |frames| {
        var f = try init(frames);
        defer f.deinit();
        c.dos64_reu_poke(f.machine, 0xb7fff, 0xa7);
        c.dos64_reu_poke(f.machine, 0xbc000, 0x5c);
        for (0..7) |m| {
            // Dirty tails must be replaced by the mode clear, not resurrected.
            try busWrite(&f, 0xbbfff, 0xfe);
            try busWrite(&f, 0xb8000, 0xed);
            try mode(&f, @intCast(m));
            try flush(&f);
            var expected: [16384]u8 = undefined;
            for (&expected, 0..) |*v, i| v.* = if (m >= 4) 0 else if (i % 2 == 0) 0x20 else 7;
            try expectBytes(&f, 0xb8000, &expected);
            const cols: u16 = if (m == 2 or m == 3 or m == 6) 80 else 40;
            try std.testing.expectEqual(@as(u8, @intCast(m)), c.dos64_reu_peek(f.machine, 0x449));
            try std.testing.expectEqual(cols, backingWord(&f, 0x44a));
            try std.testing.expectEqual(if (m >= 4) @as(u16, 0x4000) else if (cols == 40) @as(u16, 0x800) else @as(u16, 0x1000), backingWord(&f, 0x44c));
            try std.testing.expectEqual(@as(u16, 0), backingWord(&f, 0x44e));
            for (0..8) |page| try std.testing.expectEqual(@as(u16, 0), backingWord(&f, 0x450 + @as(u32, @intCast(page)) * 2));
            try std.testing.expectEqual(@as(u16, 0x0607), backingWord(&f, 0x460));
            try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x462));
            try std.testing.expectEqual(@as(u16, 0x3d4), backingWord(&f, 0x463));
            try std.testing.expectEqual(if (m == 6) @as(u8, 0x3f) else @as(u8, 0x30), c.dos64_reu_peek(f.machine, 0x466));
            try std.testing.expectEqual(@as(u8, 0xa7), c.dos64_reu_peek(f.machine, 0xb7fff));
            try std.testing.expectEqual(@as(u8, 0x5c), c.dos64_reu_peek(f.machine, 0xbc000));
        }
    }
}

test "video AH0F queries mutable dirty BDA and preserves BL other guest registers and all flags" {
    var f = try init(2);
    defer f.deinit();
    try mode(&f, 3);
    try flush(&f);
    try busWrite(&f, 0x449, 5);
    try busWrite(&f, 0x44a, 33);
    try busWrite(&f, 0x462, 6);
    try std.testing.expectEqual(@as(u8, 3), c.dos64_reu_peek(f.machine, 0x449));
    try invoke(&f, 0x0f99, 0xaa55, 0x9876, 0x5432, &.{ 0, 1, 7 }, true);
    const g = try f.symbol("dos64_guest");
    try std.testing.expectEqual(@as(u16, 0x2105), f.word(g));
    try std.testing.expectEqual(@as(u16, 0x0655), f.word(g + 6));
}

test "video cursor shape positions and active page cover every text column and all 40 and 80 column pages" {
    for ([_]u8{ 0, 1, 2, 3 }) |m| {
        var f = try init(1);
        defer f.deinit();
        try mode(&f, m);
        const cols: u8 = if (m < 2) 40 else 80;
        const pages: u8 = if (m < 2) 8 else 4;
        try invoke(&f, 0x0100, 0xabcd, 0x2007, 0x5678, &.{}, true);
        for (0..pages) |p| {
            const page: u8 = @intCast(p);
            for (0..cols) |co| {
                const col: u8 = @intCast(co);
                const row: u8 = @intCast((co * 7 + p) % 25);
                try cursor(&f, page, row, col);
                try invoke(&f, 0x0300, @as(u16, page) << 8, 0, 0, &.{ 2, 3, 4, 5 }, true);
                const g = try f.symbol("dos64_guest");
                try std.testing.expectEqual(@as(u16, 0x2007), f.word(g + 2));
                try std.testing.expectEqual((@as(u16, row) << 8) | col, f.word(g + 4));
            }
            try invoke(&f, 0x0500 | @as(u16, page), 0, 0, 0, &.{}, true);
            try invoke(&f, 0x0f00, 0x005e, 0, 0, &.{ 0, 1, 7 }, true);
            try std.testing.expectEqual(page, f.peek((try f.symbol("dos64_guest")) + 7));
            try flush(&f);
            try std.testing.expectEqual(@as(u16, page) * (if (cols == 40) @as(u16, 2048) else @as(u16, 4096)), backingWord(&f, 0x44e));
        }
        for ([_][2]u8{ .{ 25, 0 }, .{ 0, cols }, .{ 255, 255 } }) |pos| try invoke(&f, 0x0200, 0, 0, (@as(u16, pos[0]) << 8) | pos[1], &.{}, false);
        try invoke(&f, 0x0200, @as(u16, pages) << 8, 0, 0, &.{}, false);
        try invoke(&f, 0x0300, @as(u16, pages) << 8, 0, 0, &.{}, false);
        try invoke(&f, 0x0500 | @as(u16, pages), 0, 0, 0, &.{}, false);
    }
}

test "video text writes retain exact CP437 attributes cursor and linear repetitions across page padding and CGA end" {
    for ([_]u8{ 1, 3 }) |m| {
        var f = try init(2);
        defer f.deinit();
        try mode(&f, m);
        var s = Screen.init(if (m == 1) 40 else 80);
        try seedScreen(&f, &s);
        for (0..s.pages) |p| {
            const page: u8 = @intCast(p);
            for (0..256) |ch| {
                const row: u8 = @intCast((ch / s.cols) % 25);
                const col: u8 = @intCast(ch % s.cols);
                try cursor(&f, page, row, col);
                const at = s.index(page, row, col);
                const attribute: u8 = @truncate(ch * 17 + p);
                try invoke(&f, 0x0900 | @as(u16, @intCast(ch)), (@as(u16, page) << 8) | attribute, 1, 0, &.{}, true);
                s.bytes[at] = @intCast(ch);
                s.bytes[at + 1] = attribute;
                try invoke(&f, 0x0800, @as(u16, page) << 8, 0, 0, &.{ 0, 1 }, true);
                try std.testing.expectEqual((@as(u16, attribute) << 8) | @as(u16, @intCast(ch)), f.word(try f.symbol("dos64_guest")));
                try invoke(&f, 0x0a00 | @as(u16, @intCast(255 - ch)), @as(u16, page) << 8, 1, 0, &.{}, true);
                s.bytes[at] = @intCast(255 - ch);
            }
            try cursor(&f, page, 24, s.cols - 1);
            const at = s.index(page, 24, s.cols - 1);
            // The original BIOS repeat operation is linear, not cursor motion;
            // it crosses text page padding. The bus ignores bytes past BBFFF.
            const count: usize = 40;
            try invoke(&f, 0x09b3, (@as(u16, page) << 8) | 0xe9, count, 0, &.{}, true);
            for (0..count) |i| if (at + i * 2 + 1 < s.bytes.len) {
                s.bytes[at + i * 2] = 0xb3;
                s.bytes[at + i * 2 + 1] = 0xe9;
            };
            try invoke(&f, 0x0900, @as(u16, page) << 8, 0, 0, &.{}, true);
            try invoke(&f, 0x0a00, @as(u16, page) << 8, 0, 0, &.{}, true);
            try invoke(&f, 0x0300, @as(u16, page) << 8, 0, 0, &.{ 2, 3, 4, 5 }, true);
            try std.testing.expectEqual((@as(u16, 24) << 8) | (s.cols - 1), f.word((try f.symbol("dos64_guest")) + 4));
        }
        // Exercise the high byte of CX and long sequential address carries.
        try cursor(&f, 0, 0, 0);
        try invoke(&f, 0x09c4, 0x00f1, 0x0201, 0, &.{}, true);
        for (0..0x201) |i| {
            s.bytes[i * 2] = 0xc4;
            s.bytes[i * 2 + 1] = 0xf1;
        }
        try invoke(&f, 0x0a9d, 0, 0x0101, 0, &.{}, true);
        for (0..0x101) |i| s.bytes[i * 2] = 0x9d;
        c.dos64_reu_poke(f.machine, 0xbc000, 0x91);
        try cursor(&f, s.pages - 1, 24, s.cols - 1);
        try invoke(&f, 0x0a7f, @as(u16, s.pages - 1) << 8, 96, 0, &.{}, true);
        var at = s.index(s.pages - 1, 24, s.cols - 1);
        while (at < s.bytes.len) : (at += 2) s.bytes[at] = 0x7f;
        try s.compare(&f);
        try std.testing.expectEqual(@as(u8, 0x91), c.dos64_reu_peek(f.machine, 0xbc000));
        // Repetitions use a wrapping 16-bit B800:DI, including CX > 32768.
        // The intervening PC bus hole receives no backing writes.
        try invoke(&f, 0x0941, (@as(u16, s.pages - 1) << 8) | 0x32, 0x8001, 0, &.{}, true);
        for (&s.bytes, 0..) |*v, i| v.* = if (i % 2 == 0) 0x41 else 0x32;
        try s.compare(&f);
        try std.testing.expectEqual(@as(u8, 0x91), c.dos64_reu_peek(f.machine, 0xbc000));
    }
}

test "video window scroll matches a snapshot oracle for overlap clipping counts active pages and exact attributes" {
    var seed: u32 = 0x10c6a033;
    for ([_]u8{ 1, 2 }) |frames| {
        for ([_]u8{ 1, 3 }) |m| {
            var f = try init(frames);
            defer f.deinit();
            try mode(&f, m);
            var s = Screen.init(if (m == 1) 40 else 80);
            try seedScreen(&f, &s);
            for (0..s.pages) |p| {
                const page: u8 = @intCast(p);
                try invoke(&f, 0x0500 | @as(u16, page), 0, 0, 0, &.{}, true);
                for (0..16) |case| {
                    const top: u8 = @intCast(random(&seed) % 25);
                    const bottom: u8 = top + @as(u8, @intCast(random(&seed) % (25 - @as(u32, top))));
                    const left: u8 = @intCast(random(&seed) % s.cols);
                    const right: u8 = left + @as(u8, @intCast(random(&seed) % (s.cols - @as(u32, left))));
                    const attr: u8 = @truncate(random(&seed));
                    const lines: u8 = switch (case % 4) {
                        0 => 0,
                        1 => 1,
                        2 => bottom - top + 1,
                        else => 255,
                    };
                    const down = case % 2 == 0;
                    try invoke(&f, (if (down) @as(u16, 0x0700) else @as(u16, 0x0600)) | lines, @as(u16, attr) << 8, (@as(u16, top) << 8) | left, (@as(u16, bottom) << 8) | right, &.{}, true);
                    s.scroll(page, top, left, bottom, right, lines, attr, down);
                    try s.compare(&f);
                }
            }
            // Guaranteed multi-line overlap in both directions and full width.
            for ([_]bool{ false, true }) |down| {
                try invoke(&f, (if (down) @as(u16, 0x0700) else @as(u16, 0x0600)) | 3, 0x0000, 0, (@as(u16, 24) << 8) | (s.cols - 1), &.{}, true);
                s.scroll(s.pages - 1, 0, 0, 24, s.cols - 1, 3, 0, down);
                try s.compare(&f);
            }
        }
    }
}

test "video teletype handles carriage return linefeed backspace bell wrap and bottom scroll on every page" {
    for ([_]u8{ 1, 3 }) |m| {
        var f = try init(1);
        defer f.deinit();
        try mode(&f, m);
        var s = Screen.init(if (m == 1) 40 else 80);
        try seedScreen(&f, &s);
        for (0..s.pages) |p| {
            const page: u8 = @intCast(p);
            s.row[page] = 23;
            s.col[page] = s.cols - 2;
            try cursor(&f, page, s.row[page], s.col[page]);
            try invoke(&f, 0x0500 | @as(u16, page), 0, 0, 0, &.{}, true);
            const stream = [_]u8{ 'A', 'B', 'C', 8, 'X', 13, 8, 7, 10, 10, 10, 0, 0xdb, 255, 13, 10 };
            for (stream) |ch| {
                try invoke(&f, 0x0e00 | @as(u16, ch), (@as(u16, (page + 1) % s.pages) << 8) | 0xfe, 0x3245, 0x9876, &.{}, true);
                s.tty(page, ch);
                try invoke(&f, 0x0300, @as(u16, page) << 8, 0, 0, &.{ 2, 3, 4, 5 }, true);
                try std.testing.expectEqual((@as(u16, s.row[page]) << 8) | s.col[page], f.word((try f.symbol("dos64_guest")) + 4));
                try s.compare(&f);
            }
            // Put a glyph at the bottom-right corner: wrap must scroll once.
            s.row[page] = 24;
            s.col[page] = s.cols - 1;
            try cursor(&f, page, 24, s.cols - 1);
            try invoke(&f, 0x0e5a, @as(u16, page) << 8, 0, 0, &.{}, true);
            s.tty(page, 'Z');
            try s.compare(&f);
        }
    }
}

fn pixelIndex(x: u16, y: u16, bits: u3) usize {
    return @as(usize, y % 2) * 8192 + @as(usize, y / 2) * 80 + @as(usize, x) * bits / 8;
}
fn pixel(s: *[16384]u8, x: u16, y: u16, bits: u3, value: u8) u8 {
    const at = pixelIndex(x, y, bits);
    const shift: u3 = @intCast(8 - @as(u16, bits) - (x % (8 / @as(u16, bits))) * bits);
    const mask: u8 = if (bits == 1) 1 else 3;
    const previous: u8 = (s[at] >> shift) & mask;
    const next = if (value & 0x80 != 0) previous ^ (value & mask) else value & mask;
    s[at] = (s[at] & ~(mask << shift)) | (next << shift);
    return next;
}

test "video CGA pixel read write and XOR match an independent oracle at every x odd even and bank edges" {
    var seed: u32 = 0xc6a41064;
    for ([_]u8{ 1, 2 }) |frames| {
        for ([_]u8{ 4, 5, 6 }) |m| {
            var f = try init(frames);
            defer f.deinit();
            try mode(&f, m);
            var expected: [16384]u8 = @splat(0);
            const bits: u3 = if (m == 6) 1 else 2;
            const width: u16 = if (m == 6) 640 else 320;
            for ([_]u16{ 0, 1, 198, 199 }) |y| {
                for (0..width) |xx| {
                    const x: u16 = @intCast(xx);
                    const color: u8 = @truncate(random(&seed));
                    const want = pixel(&expected, x, y, bits, color);
                    try invoke(&f, 0x0c00 | @as(u16, color), 0xabcd, x, y, &.{}, true);
                    try invoke(&f, 0x0d00, 0xabcd, x, y, &.{0}, true);
                    try std.testing.expectEqual(want, f.peek(try f.symbol("dos64_guest")));
                }
            }
            for (0..512) |_| {
                const x: u16 = @intCast(random(&seed) % width);
                const y: u16 = @intCast(random(&seed) % 200);
                const color: u8 = @truncate(random(&seed));
                const want = pixel(&expected, x, y, bits, color);
                try invoke(&f, 0x0c00 | @as(u16, color), 0, x, y, &.{}, true);
                try invoke(&f, 0x0d00, 0, x, y, &.{0}, true);
                try std.testing.expectEqual(want, f.peek(try f.symbol("dos64_guest")));
            }
            // XOR twice restores every color and does not disturb neighbors.
            for (0..8) |i| {
                const x: u16 = @intCast(width - 8 + i);
                const y: u16 = 199;
                try invoke(&f, 0x0c83, 0, x, y, &.{}, true);
                try invoke(&f, 0x0c83, 0, x, y, &.{}, true);
            }
            try flush(&f);
            try expectBytes(&f, 0xb8000, &expected);
            for ([_][2]u16{ .{ width, 0 }, .{ 0, 200 }, .{ 0xffff, 199 }, .{ 639, 0xffff } }) |xy| {
                try invoke(&f, 0x0c83, 0, xy[0], xy[1], &.{}, false);
                try invoke(&f, 0x0d00, 0, xy[0], xy[1], &.{}, false);
            }
            try flush(&f);
            try expectBytes(&f, 0xb8000, &expected);
        }
    }
}

test "video rejects unknown modes services graphics glyphs and malformed windows before changing guest memory" {
    var f = try init(1);
    defer f.deinit();
    try mode(&f, 3);
    var s = Screen.init(80);
    try seedScreen(&f, &s);
    for ([_]u16{ 7, 0x80, 0x83, 0xff, 0x0400, 0x0c01, 0x0d00 }) |ax| try invoke(&f, ax, 0, 0, 0, &.{}, false);
    for ([_][2]u16{ .{ 0x1900, 0x1800 }, .{ 0x000a, 0x1809 }, .{ 0, 0x1a00 }, .{ 0, 0x1850 }, .{ 0xffff, 0xffff } }) |window| {
        try invoke(&f, 0x0601, 0x7700, window[0], window[1], &.{}, false);
        try invoke(&f, 0x0700, 0x7700, window[0], window[1], &.{}, false);
    }
    try s.compare(&f);
    for ([_]u8{ 4, 5, 6 }) |m| {
        try mode(&f, m);
        for ([_]u16{ 0x0800, 0x0941, 0x0a41, 0x0e41, 0x0601, 0x0701 }) |ax| try invoke(&f, ax, 0, 1, 0, &.{}, false);
        try invoke(&f, 0x0501, 0, 0, 0, &.{}, false);
        try invoke(&f, 0x0200, 0x0100, 0, 0, &.{}, false);
        try flush(&f);
        const blank: [16384]u8 = @splat(0);
        try expectBytes(&f, 0xb8000, &blank);
    }
}

test "video cache failures at deep mode and pixel helpers unwind host stack preserve flags and report fatal" {
    for ([_]u32{ 0, 1, 2, 33 }) |after| {
        var f = try init(1);
        defer f.deinit();
        try reg(&f, 0, 3);
        c.dos64_reu_fail_after(f.machine, after, 16);
        const r = try f.call("dos64_video_service", 30_000_000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 0xec), r.p & 0xec);
        try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_video_host_error")));
        try std.testing.expect(f.stack_high_water <= 32);
    }
    var f = try init(1);
    defer f.deinit();
    try mode(&f, 6);
    // AH0D loads BDA, then a different VRAM page: fail inside v_vram_read.
    try reg(&f, 0, 0x0d00);
    try reg(&f, 1, 639);
    try reg(&f, 2, 199);
    c.dos64_reu_fail_after(f.machine, 1, 16);
    const r = try f.call("dos64_video_service", 100_000);
    try std.testing.expectEqual(@as(u8, 1), r.p & 1);
    try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_video_host_error")));
    try std.testing.expectEqual(@as(u8, 0xec), r.p & 0xec);
    _ = try busRead(&f, 0x449); // failure injection is one-shot, authority retries
    try invoke(&f, 0xff00, 0, 0, 0, &.{}, true); // XT ignored function clears old host fatal
}

fn expectNativeWriteBounds(f: *Fixture) !void {
    for (0..65536) |index| {
        const a: u16 = @intCast(index);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        if (a <= 1 or (a >= 0x20 and a < 0xe0) or (a >= 0x100 and a < 0x200)) continue;
        if (a >= 0x8000 and a < 0xc000) continue; // coherent cache frames
        if (a >= 0xe000 and a < 0xe0ff) continue; // existing memory/CPU state
        if (a >= 0xe100 and a < 0xe9c0) continue; // page map and frame metadata
        if (a >= 0xea00 and a < 0xeb00) continue; // declared DEVICESTATE bank
        if (a >= 0xdf01 and a <= 0xdf0a) continue; // owned REU DMA registers
        std.debug.print("Video wrote outside native ownership at {x}\n", .{a});
        return error.VideoForbiddenHostWrite;
    }
}

test "video operations leave native executable staging unused control and guest VRAM envelope guards intact" {
    var f = try init(1);
    defer f.deinit();
    c.dos64_reu_poke(f.machine, 0xb7fff, 0xa7);
    c.dos64_reu_poke(f.machine, 0xbc000, 0x5c);
    try mode(&f, 3);
    try expectNativeWriteBounds(&f);
    try cursor(&f, 3, 24, 79);
    try expectNativeWriteBounds(&f);
    try invoke(&f, 0x0503, 0, 0, 0, &.{}, true);
    try expectNativeWriteBounds(&f);
    try invoke(&f, 0x0e41, 0, 0, 0, &.{}, true);
    try expectNativeWriteBounds(&f);
    try invoke(&f, 0x0703, 0xc300, 0, 0x184f, &.{}, true);
    try expectNativeWriteBounds(&f);
    try mode(&f, 6);
    try expectNativeWriteBounds(&f);
    try invoke(&f, 0x0c81, 0, 639, 199, &.{}, true);
    try expectNativeWriteBounds(&f);
    try invoke(&f, 0x0d00, 0, 639, 199, &.{0}, true);
    try expectNativeWriteBounds(&f);
    try flush(&f);
    try std.testing.expectEqual(@as(u8, 0xa7), c.dos64_reu_peek(f.machine, 0xb7fff));
    try std.testing.expectEqual(@as(u8, 0x5c), c.dos64_reu_peek(f.machine, 0xbc000));
    try std.testing.expect(f.stack_high_water <= 32);
}


test "XT palette background and selection preserve other bits guest registers and adjacent memory" {
    var f = try init(1); defer f.deinit();
    try mode(&f, 3);
    try busWrite(&f, 0x465, 0x5a); try busWrite(&f, 0x467, 0xa5);
    for ([_]u8{0, 1, 0x1f, 0x20, 0x3f, 0x80, 0xff}) |prior| {
        for ([_]u8{0, 1, 2, 0xff}) |id| {
            for ([_]u8{0, 1, 2, 0x10, 0x1f, 0x20, 0x80, 0xff}) |value| {
                try busWrite(&f,0x466,prior);
                try invoke(&f,0x0b01,(@as(u16,id)<<8)|value,0x1234,0x5678,&.{},true);
                const expected: u8 = if(id==0) (prior&0xe0)|(value&0x1f) else (prior&0xdf)|((value&1)<<5);
                try std.testing.expectEqual(expected,try busRead(&f,0x466));
                try std.testing.expectEqual(@as(u8,0x5a),try busRead(&f,0x465));
                try std.testing.expectEqual(@as(u8,0xa5),try busRead(&f,0x467));
            }
        }
    }
    try flush(&f);
    try std.testing.expectEqual(@as(u8,0x20),try busRead(&f,0xb8000));
    try std.testing.expectEqual(@as(u8,7),try busRead(&f,0xb8001));
}


test "XT palette cold BDA cache failure unwinds host stack without changing guest" {
    var f=try init(1); defer f.deinit();
    try reg(&f,0,0x0b01); try reg(&f,3,0x0000);
    const before=try guest(&f);
    c.dos64_reu_fail_after(f.machine,0,16);
    const r=try f.call("dos64_video_service",100_000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,0xec),r.p&0xec);
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_video_host_error")));
    try std.testing.expectEqualSlices(u8,&before,&try guest(&f));
    try std.testing.expect(f.stack_high_water<=32);
}

test "video XT row25 clears26rows and scrolls both directions without clipping legitimate nextpage spill" {
    for ([_]u8{ 1, 32 }) |frames| {
        for ([_]u8{ 1, 3 }) |m| {
            var f = try init(frames);
            defer f.deinit();
            try mode(&f, m);
            var s = Screen.init(if (m == 1) 40 else 80);
            try seedScreen(&f, &s);
            c.dos64_reu_poke(f.machine, 0xb7fff, 0xa7);
            c.dos64_reu_poke(f.machine, 0xbc000, 0x5c);
            for ([_]bool{ false, true }) |down| {
                for ([_]u8{ 0, 1, 3, 26, 255 }) |lines| {
                    try invoke(&f, (if (down) @as(u16, 0x0700) else @as(u16, 0x0600)) | lines, 0x1400, 0, 0x1900 | @as(u16, s.cols - 1), &.{}, true);
                    s.scroll(0, 0, 0, 25, s.cols - 1, lines, 0x14, down);
                    try s.compare(&f);
                    try std.testing.expectEqual(@as(u8, 0xa7), c.dos64_reu_peek(f.machine, 0xb7fff));
                    try std.testing.expectEqual(@as(u8, 0x5c), c.dos64_reu_peek(f.machine, 0xbc000));
                }
            }
            // Full aperture oracle includes nextpage32/64bytes and proves
            // all later bytes remain their original pattern.
            const touched = 26 * @as(usize, s.cols) * 2;
            try std.testing.expect(touched > s.stride);
        }
    }
}

test "video XT row25 validates lastpage end exactly and refuses first byte beyond CGA before anywrite" {
    for ([_]u8{ 1, 32 }) |frames| {
        for ([_]u8{ 1, 3 }) |m| {
            var f = try init(frames);
            defer f.deinit();
            try mode(&f, m);
            var s = Screen.init(if (m == 1) 40 else 80);
            try seedScreen(&f, &s);
            const page = s.pages - 1;
            try invoke(&f, 0x0500 | @as(u16, page), 0, 0, 0, &.{}, true);
            const right: u8 = if (m == 1) 23 else 47;
            for ([_]bool{ false, true }) |down| {
                try invoke(&f, if (down) 0x0700 else 0x0600, 0x3c00, 0x1900, 0x1900 | @as(u16, right), &.{}, true);
                s.scroll(page, 25, 0, 25, right, 0, 0x3c, down);
                try s.compare(&f);
                try invoke(&f, if (down) 0x0701 else 0x0601, 0x6e00, 0, 0x1900 | @as(u16, right + 1), &.{}, false);
                try s.compare(&f);
                try invoke(&f, if (down) 0x0700 else 0x0600, 0x6e00, 0, 0x1900 | @as(u16, s.cols - 1), &.{}, false);
                try s.compare(&f);
            }
            // Component deliberately remains bounded to rows0..25.
            try invoke(&f, 0x0600, 0x7700, 0, 0x1a00, &.{}, false);
            try s.compare(&f);
            try invoke(&f, 0x0700, 0x7700, 0x1900, 0x1800, &.{}, false);
            try s.compare(&f);
        }
    }
}

test "video XT row25 cache-one-frame and32frame implementations agree on patterned copied rows and full guestFLAGS" {
    for ([_]u8{ 1, 32 }) |frames| {
        for ([_]u8{ 1, 3 }) |m| {
            var f = try init(frames);
            defer f.deinit();
            try mode(&f, m);
            var s = Screen.init(if (m == 1) 40 else 80);
            try seedScreen(&f, &s);
            for ([_]u8{ 1, 3, 25 }) |lines| {
                for ([_]bool{ false, true }) |down| {
                    // Each copycase starts patterned, not a prior clear.
                    try seedScreen(&f, &s);
                    try invoke(&f, (if (down) @as(u16, 0x0700) else @as(u16, 0x0600)) | lines, 0x7f00, 0x0102, 0x1900 | @as(u16, s.cols - 3), &.{}, true);
                    s.scroll(0, 1, 2, 25, s.cols - 3, lines, 0x7f, down);
                    try s.compare(&f);
                }
            }
        }
    }
}

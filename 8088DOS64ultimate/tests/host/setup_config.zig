const std = @import("std");
const m = @import("machine.zig");
const N = 576;
const P = 128;
const home = 8;
const drive_a = 136;
const drive_b = 264;
const drive_c = 392;
const checksum = 572;

fn put(f: *m.Fixture, name: []const u8, bytes: []const u8) !void {
    const addr = try f.symbol(name);
    for (bytes, 0..) |v, i| f.poke(addr + @as(u16, @intCast(i)), v);
}
fn get(f: *m.Fixture, name: []const u8, bytes: []u8) !void {
    const addr = try f.symbol(name);
    for (bytes, 0..) |*v, i| v.* = f.peek(addr + @as(u16, @intCast(i)));
}
fn init(f: *m.Fixture) !void { _ = try f.call("_codec_init", 1_000_000); }
fn fixture() !m.Fixture { return m.Fixture.initPaths("build/setup-config.prg", "build/setup-config.labels"); }
fn run(f: *m.Fixture, name: []const u8, ok: bool) !void {
    const r = try f.call(name, 12_000_000);
    try std.testing.expectEqual(@as(u8, if (ok) 1 else 0), r.a);
    try std.testing.expectEqual(@as(u16, 0xc000), f.word(try f.symbol("sp")));
    // C's private hardware/software stacks are separate; both must stay bounded.
    try std.testing.expect(f.stack_high_water < 120);
    const bs = try f.symbol("__BSS_RUN__");
    const be = bs + try f.symbol("__BSS_SIZE__");
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (m.c.dos64_was_written(f.machine, a) == 0) continue;
        if (a >= 2 and a < 0x1c) continue;
        if (a >= 0x100 and a < 0x200) continue;
        if (a >= 0xbf00 and a < 0xc000) continue;
        if (a >= bs and a < be) continue;
        std.debug.print("Forbidden native write {x}\n", .{a});
        return error.ForbiddenWrite;
    }
}
fn path(p: []u8, s: []const u8) void { @memset(p, 0); @memcpy(p[0..s.len], s); }
fn source() [N]u8 {
    var v = [_]u8{0} ** N;
    path(v[home..][0..P], "/usb1/DOS 64");
    path(v[drive_a..][0..P], "/usb1/DOS 64/A.IMG");
    path(v[drive_b..][0..P], "/usb1/DOS 64/B.IMG");
    path(v[drive_c..][0..P], "/usb1/DOS 64/C.IMG");
    v[522] = 1; v[524] = 2; v[525] = 7;
    @memcpy(v[528..536], &[_]u8{0x12,0x34,0x56,0x78,0xfe,0xdc,0xba,0x98});
    v[536] = 1; v[540] = 0x40;
    return v;
}
fn sign(v: *[N]u8) void {
    std.mem.writeInt(u32, v[checksum..][0..4], std.hash.Crc32.hash(v[0..checksum]), .little);
}
fn expected(v: [N]u8) [N]u8 {
    var out = v;
    @memcpy(out[0..8], &[_]u8{0x44,0x36,0x34,0x43,1,0x40,2,0});
    out[526] = 0; out[527] = 0;
    @memset(out[542..checksum], 0);
    sign(&out);
    return out;
}
fn unchangedFailure(f: *m.Fixture, input: [N]u8, function: []const u8, err: ?u8) !void {
    const sentinel = [_]u8{0xa9} ** N;
    try put(f, "_d64_cfg_input", &input);
    try put(f, "_d64_cfg_output", &sentinel);
    try run(f, function, false);
    var out: [N]u8 = undefined;
    try get(f, "_d64_cfg_output", &out);
    try std.testing.expectEqualSlices(u8, &sentinel, &out);
    try get(f, "_d64_cfg_input", &out);
    try std.testing.expectEqualSlices(u8, &input, &out);
    if (err) |e| try std.testing.expectEqual(e, f.peek(try f.symbol("_d64_cfg_error")));
}

test "native config creation matches independent CRC32 and canonical serialization" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    var input = source(); input[0] = 0x99; input[527] = 0xab; input[550] = 0xcc;
    try put(&f, "_d64_cfg_input", &input);
    try run(&f, "_d64_config_make", true);
    var actual: [N]u8 = undefined;
    try get(&f, "_d64_cfg_output", &actual);
    try std.testing.expectEqualSlices(u8, &expected(input), &actual);
    try get(&f, "_d64_cfg_input", &actual);
    try std.testing.expectEqualSlices(u8, &input, &actual);
    const valid = expected(input);
    try put(&f, "_d64_cfg_input", &valid);
    try run(&f, "_d64_config_validate", true);
    try get(&f, "_d64_cfg_output", &actual);
    try std.testing.expectEqualSlices(u8, &valid, &actual);
}
test "native validator rejects one bit changed at every record byte atomically" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    const valid = expected(source());
    for (0..N) |i| {
        var broken = valid; broken[i] ^= 1;
        try unchangedFailure(&f, broken, "_d64_config_validate", null);
    }
}
test "native correctly signed malformed fields are rejected and absent drives canonical" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    const offsets = [_]usize{0,4,5,6,7,526,527,542,571,536,537,520,521,523,524,525};
    for (offsets) |i| {
        var invalid = expected(source()); invalid[i] = 0xff; sign(&invalid);
        try unchangedFailure(&f, invalid, "_d64_config_validate", null);
    }
    const bad_paths = [_][]const u8{"", "/", "relative", "/usb1/../x", "/usb1/./x", "/usb1//x", "/usb1/x/", "/usb1/a\\b", "/usb1/a:b", "/usb1/\x80"};
    for ([_]usize{drive_a,drive_b,drive_c}) |offset| {
        for (bad_paths) |s| {
            var invalid = expected(source()); path(invalid[offset..][0..P], s); sign(&invalid);
            try unchangedFailure(&f, invalid, "_d64_config_validate", 3);
        }
        var invalid = expected(source()); invalid[offset+127] = 'X'; sign(&invalid);
        try unchangedFailure(&f, invalid, "_d64_config_validate", 3);
    }
    var one = source(); one[524] = 0; one[525] = 1; one[522] = 0;
    @memset(one[drive_b..drive_c+P], 0); @memset(one[532..536], 0);
    path(one[home..][0..P], "/");
    try put(&f, "_d64_cfg_input", &one); try run(&f, "_d64_config_make", true);
    var actual: [N]u8 = undefined; try get(&f, "_d64_cfg_output", &actual);
    try std.testing.expectEqualSlices(u8, &expected(one), &actual);
    var invalid = one; invalid[drive_b] = '/'; try unchangedFailure(&f, invalid, "_d64_config_make", 3);
    invalid = one; invalid[532] = 1; try unchangedFailure(&f, invalid, "_d64_config_make", 4);
    invalid = one; invalid[524] = 2; try unchangedFailure(&f, invalid, "_d64_config_make", 4);
    invalid = one; invalid[522] = 1; try unchangedFailure(&f, invalid, "_d64_config_make", 5);
}
test "native explicit REU capacity accepts larger profiles and rejects invalid bounds" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    for ([_]u32{0x400000,0x800000,0xc00000,0x1000000}) |capacity| {
        var input = source();
        std.mem.writeInt(u32, input[538..542], capacity, .little);
        try put(&f, "_d64_cfg_input", &input); try run(&f, "_d64_config_make", true);
        const valid = expected(input); try put(&f, "_d64_cfg_input", &valid);
        try run(&f, "_d64_config_validate", true);
        var actual: [N]u8 = undefined; try get(&f, "_d64_cfg_output", &actual);
        try std.testing.expectEqualSlices(u8, &valid, &actual);
    }
    for ([_]u32{0,0x3f0000,0x3fffff,0x400001,0x1000001,0x1010000,0xffffffff}) |capacity| {
        var input = source(); std.mem.writeInt(u32, input[538..542], capacity, .little);
        try unchangedFailure(&f, input, "_d64_config_make", 6);
        const signed = expected(input);
        try unchangedFailure(&f, signed, "_d64_config_validate", 6);
    }
}
fn pathCall(f: *m.Fixture, base: []const u8, relative: []const u8, function: []const u8, result: ?[]const u8) !void {
    var a: [P]u8 = undefined; path(&a, base);
    var b: [P]u8 = undefined; path(&b, relative);
    const sentinel = [_]u8{0xe7} ** P;
    try put(f, "_d64_path_source", &a); try put(f, "_d64_path_relative", &b);
    try put(f, "_d64_path_output", &sentinel);
    try run(f, function, result != null);
    var actual: [P]u8 = undefined; try get(f, "_d64_path_output", &actual);
    if (result) |s| { var want: [P]u8 = undefined; path(&want, s); try std.testing.expectEqualSlices(u8, &want, &actual); }
    else try std.testing.expectEqualSlices(u8, &sentinel, &actual);
    try get(f, "_d64_path_source", &actual); try std.testing.expectEqualSlices(u8, &a, &actual);
    try get(f, "_d64_path_relative", &actual); try std.testing.expectEqualSlices(u8, &b, &actual);
}
test "native folder navigation joins absolute paths with exact bounds and no partial writes" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    try pathCall(&f, "/", "A.IMG", "_d64_path_join", "/A.IMG");
    try pathCall(&f, "/usb1/DOS 64", "disks/A.IMG", "_d64_path_join", "/usb1/DOS 64/disks/A.IMG");
    try pathCall(&f, "/usb1/DOS 64", "", "_d64_path_parent", "/usb1");
    try pathCall(&f, "/usb1", "", "_d64_path_parent", "/");
    try pathCall(&f, "/", "", "_d64_path_parent", "/");
    for ([_][]const u8{"", "/x", "../x", "a/./b", "a//b", "a/", "a:b", "a\\b", "\x1f", "\x80"}) |s|
        try pathCall(&f, "/usb1", s, "_d64_path_join", null);
    var long = [_]u8{'a'} ** 126;
    var want = [_]u8{'a'} ** 127; want[0] = '/';
    try pathCall(&f, "/", &long, "_d64_path_join", &want);
    try pathCall(&f, "/x", &long, "_d64_path_join", null);
    long[0] = '/'; try pathCall(&f, &long, "", "_d64_path_parent", "/");
    var unterminated = [_]u8{'a'} ** P;
    try put(&f, "_d64_path_source", &unterminated);
    const sentinel = [_]u8{0xe7} ** P; try put(&f, "_d64_path_output", &sentinel);
    try run(&f, "_d64_path_parent", false);
    var actual: [P]u8 = undefined; try get(&f, "_d64_path_output", &actual);
    try std.testing.expectEqualSlices(u8, &sentinel, &actual);
}
test "native FatFs canonical paths retain internal spaces and reject normalized aliases" {
    var f = try fixture(); defer f.deinit(); try init(&f);
    try pathCall(&f, "/usb1/DOS 64", "MS-DOS Version 3.3 (Microsoft) (1988) - 1 of 3.img", "_d64_path_join",
        "/usb1/DOS 64/MS-DOS Version 3.3 (Microsoft) (1988) - 1 of 3.img");
    try pathCall(&f, "/sd/ My DOS", "A..B.IMG", "_d64_path_join", "/sd/ My DOS/A..B.IMG");
    for ([_][]const u8{"a.", "a ", ".. ", ". ", "dir./A.IMG", "dir /A.IMG", "a\"b", "a*b", "a<b", "a>b", "a?b", "a|b"}) |bad| {
        try pathCall(&f, "/usb1", bad, "_d64_path_join", null);
        var absolute: [P]u8 = [_]u8{0} ** P;
        @memcpy(absolute[0..6], "/usb1/"); @memcpy(absolute[6..][0..bad.len], bad);
        for ([_]usize{home,drive_a,drive_b,drive_c}) |offset| {
            var invalid = source(); @memcpy(invalid[offset..][0..P], &absolute);
            try unchangedFailure(&f, invalid, "_d64_config_make", 3);
            const signed = expected(invalid);
            try unchangedFailure(&f, signed, "_d64_config_validate", 3);
        }
        try pathCall(&f, absolute[0..6+bad.len], "A.IMG", "_d64_path_join", null);
        try pathCall(&f, absolute[0..6+bad.len], "", "_d64_path_parent", null);
    }
}

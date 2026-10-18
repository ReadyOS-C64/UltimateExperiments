const std = @import("std");
const a = std.testing.allocator;
const Manifest = struct { schema_version: u32, kind: []const u8, complete: bool, original_images_unchanged: bool, source_system_files_identical: bool, inspection: struct { bytes: usize, sha256: []const u8, fat_copies_equal: bool, bpb: struct { bytes_per_sector: u16, heads: u8, sectors_per_track: u8 } }, raw_image: struct { path: []const u8, bytes: usize, sha256: []const u8 }, geometry: struct { cylinders: u16, heads: u8, sectors_per_track: u8, bytes_per_sector: u16 }, cross16: ?struct { guest_write_close_reopen_read_compare_eof_close: bool, host_compared_all_generated_bytes: bool } = null };
fn manifestPath(profile: u8) ![]const u8 {
    return (if (profile == 0) @import("hd_options").small_manifest else @import("hd_options").large_manifest) orelse error.MissingExplicitHDManifest;
}
fn hash(bytes: []const u8) [64]u8 {
    var d: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(bytes, &d, .{});
    return std.fmt.bytesToHex(d, .lower);
}
fn parse(path: []const u8) !std.json.Parsed(Manifest) {
    const raw = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, a, .limited(4 * 1024 * 1024));
    defer a.free(raw);
    const parsed = try std.json.parseFromSlice(Manifest, a, raw, .{ .ignore_unknown_fields = true, .allocate = .alloc_always });
    std.debug.print("HD fixture manifest {s} SHA256={s}\n", .{ path, hash(raw) });
    return parsed;
}
pub fn image(profile: u8) ![]u8 {
    return checkedImage(try manifestPath(profile), profile);
}
fn checkedImage(path: []const u8, profile: u8) ![]u8 {
    const parsed = try parse(path);
    defer parsed.deinit();
    const m = parsed.value;
    const length: usize = if (profile == 0) 2 * 1024 * 1024 else 20 * 1024 * 1024;
    if (m.schema_version != 1 or !std.mem.eql(u8, m.kind, "dos64-genuine-dos-hd-fixture") or !m.original_images_unchanged or !m.source_system_files_identical or !m.inspection.fat_copies_equal or m.inspection.bytes != length or !std.mem.eql(u8, m.inspection.sha256, m.raw_image.sha256) or m.inspection.bpb.bytes_per_sector != 512 or m.inspection.bpb.heads != m.geometry.heads or m.inspection.bpb.sectors_per_track != 16 or !m.complete or m.raw_image.bytes != length or m.geometry.cylinders != (if (profile == 0) @as(u16, 128) else @as(u16, 640)) or m.geometry.heads != (if (profile == 0) @as(u8, 2) else @as(u8, 4)) or m.geometry.sectors_per_track != 16 or m.geometry.bytes_per_sector != 512) return error.InvalidHDManifest;
    if (m.cross16) |cross| {
        if (!cross.guest_write_close_reopen_read_compare_eof_close or !cross.host_compared_all_generated_bytes) return error.InvalidCross16Manifest;
    }
    const backing = if (std.fs.path.isAbsolute(m.raw_image.path)) try a.dupe(u8, m.raw_image.path) else try std.fs.path.join(a, &.{ std.fs.path.dirname(path) orelse ".", m.raw_image.path });
    defer a.free(backing);
    const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, backing, a, .limited(length + 1));
    errdefer a.free(bytes);
    if (bytes.len != length or !std.mem.eql(u8, &hash(bytes), m.raw_image.sha256)) return error.HDImageIdentityMismatch;
    std.debug.print("HD source {s} bytes={d} SHA256={s}\n", .{ backing, bytes.len, hash(bytes) });
    return bytes;
}
pub fn hasCross16(profile: u8) !bool {
    const parsed = try parse(try manifestPath(profile));
    defer parsed.deinit();
    return parsed.value.cross16 != null;
}

test "explicit HD manifest consumer checks readiness source flags geometry inspection and image hash" {
    const bytes = try a.alloc(u8, 2 * 1024 * 1024);
    defer a.free(bytes);
    for (bytes, 0..) |*v, i| v.* = @truncate(i * 31);
    const digest = hash(bytes);
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/hd-fixture-consumer.raw", .data = bytes });
    const good = Manifest{ .schema_version = 1, .kind = "dos64-genuine-dos-hd-fixture", .complete = true, .original_images_unchanged = true, .source_system_files_identical = true, .inspection = .{ .bytes = bytes.len, .sha256 = &digest, .fat_copies_equal = true, .bpb = .{ .bytes_per_sector = 512, .heads = 2, .sectors_per_track = 16 } }, .raw_image = .{ .path = "hd-fixture-consumer.raw", .bytes = bytes.len, .sha256 = &digest }, .geometry = .{ .cylinders = 128, .heads = 2, .sectors_per_track = 16, .bytes_per_sector = 512 } };
    for (0..12) |i| {
        var m = good;
        switch (i) {
            0 => {},
            1 => m.complete = false,
            2 => m.original_images_unchanged = false,
            3 => m.source_system_files_identical = false,
            4 => m.geometry.cylinders = 129,
            5 => m.geometry.heads = 4,
            6 => m.geometry.bytes_per_sector = 1024,
            7 => m.inspection.fat_copies_equal = false,
            8 => m.inspection.bytes -= 1,
            9 => m.inspection.sha256 = "wrong",
            10 => m.raw_image.sha256 = "wrong",
            11 => m.cross16 = .{ .guest_write_close_reopen_read_compare_eof_close = false, .host_compared_all_generated_bytes = true },
            else => unreachable,
        }
        const json = try std.json.Stringify.valueAlloc(a, m, .{});
        defer a.free(json);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/hd-fixture-consumer.json", .data = json });
        if (i == 0) {
            const actual = try checkedImage("build/hd-fixture-consumer.json", 0);
            defer a.free(actual);
            try std.testing.expectEqualSlices(u8, bytes, actual);
        } else try std.testing.expectError(if (i == 11) error.InvalidCross16Manifest else error.InvalidHDManifest, checkedImage("build/hd-fixture-consumer.json", 0));
    }
    const json = try std.json.Stringify.valueAlloc(a, good, .{});
    defer a.free(json);
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/hd-fixture-consumer.json", .data = json });
    bytes[100] ^= 1;
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/hd-fixture-consumer.raw", .data = bytes });
    try std.testing.expectError(error.HDImageIdentityMismatch, checkedImage("build/hd-fixture-consumer.json", 0));
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

const Envelope = struct { far: u32, host: u16, len: usize };
const envelopes = [_]Envelope{
    .{ .far = 0x07fc00, .host = 0x6000, .len = 2048 },
    .{ .far = 0x34ff00, .host = 0x6800, .len = 1536 },
    .{ .far = 0x35ff00, .host = 0x6e00, .len = 1536 },
};
fn pattern(arena: usize, index: usize) u8 {
    // Nonzero distinct arena patterns avoid zero-filled accidental success.
    return @intCast((index * 37 + arena * 61 + 11) % 255 + 1);
}
fn seed(f: *Fixture) void {
    for (envelopes, 0..) |e, arena| {
        for (0..e.len) |i| c.dos64_reu_poke(f.machine, e.far + @as(u32, @intCast(i)), pattern(arena, i));
        c.dos64_reu_poke(f.machine, e.far - 1, @intCast(0xa1 + arena));
        c.dos64_reu_poke(f.machine, e.far + @as(u32, @intCast(e.len)), @intCast(0xb1 + arena));
    }
    f.poke(0x5fff, 0xc3);
    f.poke(0x7400, 0xd4);
}
fn expectGuards(f: *Fixture) !void {
    for (envelopes, 0..) |e, arena| {
        try std.testing.expectEqual(@as(u8, @intCast(0xa1 + arena)), c.dos64_reu_peek(f.machine, e.far - 1));
        try std.testing.expectEqual(@as(u8, @intCast(0xb1 + arena)), c.dos64_reu_peek(f.machine, e.far + @as(u32, @intCast(e.len))));
    }
    try std.testing.expectEqual(@as(u8, 0xc3), f.peek(0x5fff));
    try std.testing.expectEqual(@as(u8, 0xd4), f.peek(0x7400));
}

test "range recovery helpers preserve all three nonzero envelopes and neighboring bytes" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    seed(&f);
    const backup = try f.call("dos64_range_backup", 10000);
    try std.testing.expectEqual(@as(u8, 0), backup.p & 1);
    try f.expectStatus(0xa5);
    for (envelopes, 0..) |e, arena| {
        for (0..e.len) |i| {
            try std.testing.expectEqual(pattern(arena, i), f.peek(e.host + @as(u16, @intCast(i))));
            try std.testing.expectEqual(pattern(arena, i), c.dos64_reu_peek(f.machine, e.far + @as(u32, @intCast(i))));
            c.dos64_reu_poke(f.machine, e.far + @as(u32, @intCast(i)), 0x55);
        }
    }
    try expectGuards(&f);
    const restored = try f.call("dos64_range_restore", 10000);
    try std.testing.expectEqual(@as(u8, 0), restored.p & 1);
    try f.expectStatus(0xa5);
    try std.testing.expectEqual(@as(u8, 0), f.peek((try f.symbol("dos64_mailbox")) + 4));
    for (envelopes, 0..) |e, arena| {
        for (0..e.len) |i| try std.testing.expectEqual(pattern(arena, i), c.dos64_reu_peek(f.machine, e.far + @as(u32, @intCast(i))));
    }
    try expectGuards(&f);
    try std.testing.expectEqual(@as(u64, 12), c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u64, 10240), c.dos64_dma_bytes(f.machine));
}

test "range recovery reports each incomplete chunk and a full retry recovers partial restore" {
    for ([_][]const u8{ "dos64_range_backup", "dos64_range_restore" }) |entry| {
        for (0..6) |chunk| {
            var f = try Fixture.init();
            defer f.deinit();
            c.dos64_enable_reu(f.machine);
            seed(&f);
            // Backup first supplies genuine payload even for restoration failures.
            _ = try f.call("dos64_range_backup", 10000);
            for (envelopes) |e| {
                for (0..e.len) |i| c.dos64_reu_poke(f.machine, e.far + @as(u32, @intCast(i)), 0x55);
            }
            c.dos64_reu_fail_after(f.machine, @intCast(chunk), 17);
            const regs = try f.call(entry, 10000);
            try std.testing.expectEqual(@as(u8, 1), regs.p & 1);
            try f.expectStatus(0xe1);
            try std.testing.expectEqual(@as(u8, @intCast(chunk + 1)), f.peek((try f.symbol("dos64_mailbox")) + 4));
            try expectGuards(&f);
            if (std.mem.eql(u8, entry, "dos64_range_restore")) {
                _ = try f.call("dos64_range_restore", 10000);
                try f.expectStatus(0xa5);
                for (envelopes, 0..) |e, arena| {
                    for (0..e.len) |i| try std.testing.expectEqual(pattern(arena, i), c.dos64_reu_peek(f.machine, e.far + @as(u32, @intCast(i))));
                }
                try expectGuards(&f);
            }
        }
    }
}

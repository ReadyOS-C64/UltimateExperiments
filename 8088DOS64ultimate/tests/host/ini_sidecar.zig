const std = @import("std");
const host = @import("machine.zig");
const F = host.Fixture;
const c = host.c;
test "unit sidecar loads exact linked251 bytes and executes both original helpers" {
    var f = try F.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    try std.testing.expectEqual(@as(u16, 0xef00), try f.symbol("__UNITEXTRA_RUN__"));
    try std.testing.expectEqual(@as(u16, 251), try f.symbol("__UNITEXTRA_SIZE__"));
    try std.testing.expectEqual(@as(u16, 0xef00), try f.symbol("dos64_reu_probe"));
    try std.testing.expectEqual(@as(u16, 0xef9e), try f.symbol("dos64_reu_backup"));
    const port = f.peek(1);
    _ = try f.call("dos64_reu_probe", 200_000);
    try f.expectStatus(0xa5);
    try std.testing.expectEqual(port & 0x2f, f.peek(1) & 0x2f);
    for (0..4096) |i| try std.testing.expectEqual(@as(u8, @truncate(i)) ^ 0xa7, f.peek(0x6000 + @as(u16, @intCast(i))));
    for (0..2048) |i| c.dos64_reu_poke(f.machine, 0x7fc00 + @as(u32, @intCast(i)), @truncate(i * 19 + 3));
    _ = try f.call("dos64_reu_backup", 200_000);
    try f.expectStatus(0xa5);
    for (0..2048) |i| {
        try std.testing.expectEqual(@as(u8, @truncate(i * 19 + 3)), f.peek(0x6000 + @as(u16, @intCast(i))));
        f.poke(0x6000 + @as(u16, @intCast(i)), @truncate(i * 13 + 7));
    }
    _ = try f.call("dos64_reu_restore", 200_000);
    try f.expectStatus(0xa5);
    for (0..2048) |i| try std.testing.expectEqual(@as(u8, @truncate(i * 13 + 7)), c.dos64_reu_peek(f.machine, 0x7fc00 + @as(u32, @intCast(i))));
    try std.testing.expectEqual(port & 0x2f, f.peek(1) & 0x2f);
}
test "unit sidecar refuses hiddenROM or hiddenIO before native registers and stack" {
    var f = try F.init();
    defer f.deinit();
    for ([_]u8{ 0x37, 0x34, 0x30 }) |port| {
        f.poke(1, port);
        const before = f.peek(0x1fe);
        try std.testing.expectError(error.UnitFixtureBank, f.call("dos64_reu_probe", 200_000));
        try std.testing.expectEqual(before, f.peek(0x1fe));
    }
    f.poke(1, 0x35);
    f.poke(0, 0x2d);
    try std.testing.expectError(error.UnitFixtureBank, f.call("dos64_reu_backup", 200_000));
}
test "unit sidecar refuses retired cold ownership before executing snapshot or probe" {
    var f = try F.init();
    defer f.deinit();
    const names = [_][]const u8{ "dos64_cold_open", "dos64_overlay_ready", "dos64_native_started" };
    const values = [_]u8{ 0, 0xa5, 0xa5 };
    for (names, values) |name, value| {
        const at = try f.symbol(name);
        const old = f.peek(at);
        f.poke(at, value);
        for ([_][]const u8{ "dos64_reu_probe", "dos64_reu_backup", "dos64_reu_restore" }) |entry| try std.testing.expectError(error.DiscardedUnitFixture, f.call(entry, 200_000));
        f.poke(at, old);
    }
}
test "unit sidecar readonly guard catches actual6510 store even when byte restored" {
    var f = try F.init();
    defer f.deinit();
    const address = @as(u16, 0xef00);
    const old = f.peek(address);
    const program = [_]u8{ 0xa9, old, 0x8d, 0x00, 0xef, 0x60 };
    c.dos64_load(f.machine, 0x6000, &program, program.len);
    try f.symbols.put(std.testing.allocator, "sidecar_test_store", 0x6000);
    try std.testing.expectError(error.UnitFixtureCodeWrite, f.call("sidecar_test_store", 100));
}

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

test "unit tail exact207 bytes executes original foundation and cache probe without touching upper guards" {
    var f=try F.init();defer f.deinit();
    try std.testing.expectEqual(@as(u16,0xff00),try f.symbol("__UNITTAIL_RUN__"));
    try std.testing.expectEqual(@as(u16,207),try f.symbol("__UNITTAIL_SIZE__"));
    try std.testing.expectEqual(@as(u16,0xff00),try f.symbol("fixture_pass"));
    try std.testing.expectEqual(@as(u16,0xff23),try f.symbol("dos64_cache_probe"));
    var upper:[49]u8=undefined;
    for(&upper,0..) |*v,i|v.*=f.peek(0xffcf+@as(u16,@intCast(i)));
    const pass=try f.call("fixture_pass",10000);try f.expectStatus(0xa5);
    try std.testing.expectEqual(@as(u8,0x93),pass.y);
    c.dos64_enable_reu(f.machine);
    _=try f.call("dos64_cache_probe",3_000_000);try f.expectStatus(0xa5);
    for(0..1536) |i|try std.testing.expectEqual(@as(u8,@truncate(i))^@as(u8,@intCast(i>>8))^0xa7,f.peek(0x6000+@as(u16,@intCast(i))));
    for(upper,0..) |v,i|try std.testing.expectEqual(v,f.peek(0xffcf+@as(u16,@intCast(i))));
}
test "unit tail wrong mapping refuses before hardware stack and native registers" {
    var f=try F.init();defer f.deinit();
    for([_]u8{0x37,0x34,0x30}) |port| {
        f.poke(1,port);const before=c.dos64_get_regs(f.machine);const stack=f.peek(0x1fe);
        try std.testing.expectError(error.UnitFixtureBank,f.call("fixture_pass",100));
        try std.testing.expectEqualDeep(before,c.dos64_get_regs(f.machine));try std.testing.expectEqual(stack,f.peek(0x1fe));
    }
    f.poke(1,0x35);f.poke(0,0x2d);
    try std.testing.expectError(error.UnitFixtureBank,f.call("dos64_cache_probe",100));
}
test "unit tail retired cold ownership refuses all original entries without target execution" {
    var f=try F.init();defer f.deinit();
    const names=[_][]const u8{"dos64_cold_open","dos64_overlay_ready","dos64_native_started"};
    const values=[_]u8{0,0xa5,0xa5};
    for(names,values) |name,value| {
        const at=try f.symbol(name);const old=f.peek(at);f.poke(at,value);const before=c.dos64_get_regs(f.machine);
        for([_][]const u8{"fixture_pass","fixture_fail","fixture_runaway","fixture_unbalanced","fixture_bad_write","fixture_timed","fixture_unimplemented_reu","dos64_cache_probe"}) |entry| {
            try std.testing.expectError(error.DiscardedUnitFixture,f.call(entry,100));try std.testing.expectEqualDeep(before,c.dos64_get_regs(f.machine));
        }
        f.poke(at,old);
    }
}
test "unit tail guard catches samebyte write and changedcode before later calls" {
    var f=try F.init();defer f.deinit();const old=f.peek(0xff00);
    const program=[_]u8{0xa9,old,0x8d,0x00,0xff,0x60};c.dos64_load(f.machine,0x6000,&program,program.len);
    try f.symbols.put(std.testing.allocator,"tail_test_store",0x6000);
    try std.testing.expectError(error.UnitFixtureCodeWrite,f.call("tail_test_store",100));
    f.poke(0xff00,old^1);const before=c.dos64_get_regs(f.machine);
    try std.testing.expectError(error.UnitFixtureCodeWrite,f.call("fixture_timed",100));try std.testing.expectEqualDeep(before,c.dos64_get_regs(f.machine));
}
test "unit tail unloaded fallback fixtures reject helpers before hardware context mutation" {
    inline for (.{@import("machine_future.zig"),@import("machine_irq_pit.zig")}) |late| {
        var f=try late.Fixture.init();defer f.deinit();
        const before=late.c.dos64_get_regs(f.machine);const stack=f.peek(0x1fe);
        for([_][]const u8{"fixture_pass","fixture_timed","dos64_cache_probe","dos64_reu_probe"}) |entry| {
            try std.testing.expectError(error.DiscardedUnitFixture,f.call(entry,100));
            try std.testing.expectEqualDeep(before,late.c.dos64_get_regs(f.machine));try std.testing.expectEqual(stack,f.peek(0x1fe));
        }
    }
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;

test "assembly reset initializes original CPU state and preserves host ABI" {
    var f = try Fixture.init();
    defer f.deinit();
    const guest = try f.symbol("dos64_guest");
    for (0..28) |index| f.poke(guest+@as(u16, @intCast(index)), 0xa7);
    f.poke(1, 0x35);
    const regs = try f.call("fixture_pass", 10_000);
    try std.testing.expectEqual(@as(u16, 0xffff), f.word(guest+18));
    try std.testing.expectEqual(@as(u16, 0xf002), f.word(guest+26));
    for (0..13) |index| {
        if (index == 9) continue;
        try std.testing.expectEqual(@as(u16, 0), f.word(guest+@as(u16, @intCast(index*2))));
    }
    try std.testing.expectEqual(@as(u8, 0x93), regs.y);
    try std.testing.expectEqual(@as(u8, 0x35), f.peek(1));
    try f.expectStatus(0xa5);
    try f.verifyWrites();
    try std.testing.expectEqual(@as(u8, 4), f.stack_high_water);
    try std.testing.expect(regs.cycles > 100);
}

test "wrong expected behavior is detected by the Zig harness" {
    var f = try Fixture.init();
    defer f.deinit();
    _ = try f.call("fixture_pass", 10_000);
    try std.testing.expectError(error.StatusMismatch, f.expectStatus(0xe1));
}

test "target-reported failure is observable" {
    var f = try Fixture.init();
    defer f.deinit();
    _ = try f.call("fixture_fail", 100);
    try std.testing.expectError(error.StatusMismatch, f.expectStatus(0xa5));
    try f.expectStatus(0xe1);
}

test "runaway actual assembly stops at the CPU cycle budget" {
    var f = try Fixture.init();
    defer f.deinit();
    try std.testing.expectError(error.CycleBudget, f.call("fixture_runaway", 100));
    try std.testing.expectEqual(try f.symbol("fixture_runaway"), f.last_regs.?.pc);
    try std.testing.expect(f.last_regs.?.cycles >= 100);
}

test "unbalanced host stack fails even when the completion address is reached" {
    var f = try Fixture.init();
    defer f.deinit();
    try std.testing.expectError(error.StackImbalance, f.call("fixture_unbalanced", 100));
}

test "write guards catch a target write into the reserved display matrix" {
    var f = try Fixture.init();
    defer f.deinit();
    _ = try f.call("fixture_bad_write", 100);
    try std.testing.expectError(error.ForbiddenWrite, f.verifyWrites());
    try std.testing.expectEqual(@as(u8, 0x42), f.peek(0x4000));
}

test "raw unit payload is byte-identical to the linked PRG payload" {
    const allocator = std.testing.allocator;
    const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.prg", allocator, .limited(65538));
    defer allocator.free(prg);
    const raw = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.bin", allocator, .limited(65536));
    defer allocator.free(raw);
    try std.testing.expectEqualSlices(u8, prg[2..], raw);
}

test "Peddle bridge counts all two LDA and six RTS microcycles" {
    var f = try Fixture.init();
    defer f.deinit();
    const before = host.c.dos64_get_regs(f.machine).cycles;
    const after = try f.call("fixture_timed", 100);
    try std.testing.expectEqual(@as(u64, 8), after.cycles-before);
    try std.testing.expectEqual(@as(u64, 2), after.instructions);
    try std.testing.expectEqual(@as(u8, 7), after.a);
}

test "unsupported REU access is rejected rather than treated as ordinary RAM" {
    var f = try Fixture.init();
    defer f.deinit();
    try std.testing.expectError(error.UnsupportedDevice, f.call("fixture_unimplemented_reu", 100));
}

test "actual disabled PRG entry safely reports config failure with KERNAL visible" {
    var f = try Fixture.init();
    defer f.deinit();
    const g = try f.symbol("dos64_guest");
    f.poke(g, 0x6d);
    const idle = try f.symbol("dos64_native_idle");
    host.c.dos64_set_regs(f.machine, .{ .pc = try f.symbol("dos64_entry"), .sp = 0x57, .a = 0, .x = 0, .y = 0, .p = 0x28, .cycles = 0, .instructions = 0 });
    const r = host.c.dos64_run(f.machine, idle, 10000);
    try std.testing.expectEqual(@as(c_uint, host.c.DOS64_RUN_RETURNED), r.status);
    const d = try f.symbol("dos64_native_diag");
    try std.testing.expectEqual(@as(u8, 0xe1), f.peek(d));
    try std.testing.expectEqual(@as(u8, 1), f.peek(d + 1));
    try std.testing.expectEqual(@as(u8, 0x6d), f.peek(g));
    try std.testing.expectEqual(@as(u8, 0x2f), f.peek(0));
    try std.testing.expectEqual(@as(u8, 7), f.peek(1) & 7);
    try std.testing.expectEqual(@as(u8, 0xff), r.regs.sp);
    try std.testing.expectEqual(@as(u8, 0), r.regs.p & 8);
}


test { _ = @import("reu.zig"); }
test { _ = @import("memory.zig"); }
test { _ = @import("range_probe.zig"); }
test { _ = @import("range_snapshot.zig"); }
test { _ = @import("overlay_integration.zig"); }
test { _ = @import("native_runtime_integration.zig"); }
test { _ = @import("native_text_integration.zig"); }

test "unit cold fixtures reject after real release before target stack or register writes" {
    var f = try Fixture.init(); defer f.deinit();
    f.poke(try f.symbol("dos64_overlay_ready"), 0xa5);
    f.poke(try f.symbol("dos64_bios_ready"), 0xa5);
    f.poke(try f.symbol("dos64_import_state"), 0);
    f.poke(try f.symbol("dos64_overlay_busy"), 0);
    const r = try f.call("dos64_cold_release", 1000);
    try std.testing.expectEqual(@as(u8,0),r.p & 1);
    const start = try f.symbol("__UNITCOLD_RUN__");
    const size = try f.symbol("__UNITCOLD_SIZE__");
    try std.testing.expectEqual((try f.symbol("__COLDRODATA_RUN__")) + (try f.symbol("__COLDRODATA_SIZE__")),start);
    try std.testing.expectEqual(@as(u16,517),size);
    try std.testing.expectEqual(@as(u16,975),size+(try f.symbol("__UNITEXTRA_SIZE__"))+(try f.symbol("__UNITTAIL_SIZE__")));
    for (0..size) |i| f.poke(start+@as(u16,@intCast(i)),0);
    const before = host.c.dos64_get_regs(f.machine);
    for ([_][]const u8{ "fixture_pass", "fixture_fail", "fixture_runaway", "fixture_unbalanced", "fixture_bad_write", "fixture_timed", "fixture_unimplemented_reu", "dos64_reu_probe", "dos64_cache_probe", "dos64_reu_backup", "dos64_reu_restore", "dos64_range_probe", "dos64_range_backup", "dos64_range_restore" }) |entry| {
        try std.testing.expectError(error.DiscardedUnitFixture,f.call(entry,1000));
        try std.testing.expectEqualDeep(before,host.c.dos64_get_regs(f.machine));
    }
    try std.testing.expect((try f.symbol("fixture_return")) < 0x4000);
    _ = try f.call("dos64_cpu_reset",1000);
    try std.testing.expectEqual(@as(u16,0xffff),f.word((try f.symbol("dos64_guest"))+18));
}

test "unit fixture ownership ends before bootstrap or any native startup attempt" {
 for([_][]const u8{ "dos64_overlay_ready", "n_started" })|owner| {
  var f=try Fixture.init();defer f.deinit();
  f.poke(try f.symbol(owner),1);
  const before=host.c.dos64_get_regs(f.machine);
  try std.testing.expectError(error.DiscardedUnitFixture,f.call("dos64_range_backup",1000));
  try std.testing.expectEqualDeep(before,host.c.dos64_get_regs(f.machine));
 }
}

const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
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
    try std.testing.expectEqual(@as(u16,975),size);
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

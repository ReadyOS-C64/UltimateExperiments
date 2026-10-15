const std = @import("std");
const host = @import("machine.zig");
const c = host.c;
const F = host.Fixture;
fn invoke(f: *F, ah: u8, al: u8, status: u8) !void {
    const g = try f.symbol("dos64_guest");
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| {
        v.* = @truncate(i * 41 + @as(usize, ah) + al);
        f.poke(g + @as(u16, @intCast(i)), v.*);
    }
    before[0] = al;
    before[1] = ah;
    f.poke(g, al);
    f.poke(g + 1, ah);
    f.poke(try f.symbol("dos64_video_host_error"), 0xa7);
    f.initial_status = status;
    const result = try f.call("dos64_video_service", 1000);
    try std.testing.expectEqual(@as(u8, 0), result.p & 1);
    try std.testing.expectEqual(status & 0xce, result.p & 0xce);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_video_host_error")));
    for (before, 0..) |v, i| try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
    // REU/CIA/VIC models remain disabled. An accidental BDA/VRAM/device call
    // fails explicitly, rather than reading permissive model defaults.
    try std.testing.expectEqual(@as(u8, 0), c.dos64_model_fault(f.machine));
    for (0..65536) |i| {
        if (c.dos64_was_written(f.machine, @intCast(i)) == 0) continue;
        if (i >= 0x100 and i < 0x200) continue;
        if (i == try f.symbol("v_sp") or i == try f.symbol("dos64_video_host_error")) continue;
        std.debug.print("XT ignored video function wrote host {x}\n", .{i});
        return error.XtNoOpWrite;
    }
}
test "original XT out of range INT10 functions preserve guest registers flags memory and absent device models" {
    var f = try F.init();
    defer f.deinit();
    for (0x10..256) |ah| for ([_]u8{ 0, 1, 0x7f, 0xff }) |al| try invoke(&f, @intCast(ah), al, @truncate(ah ^ al));
}
test "MODE video state probe AH1B preserves every AL and native arithmetic status combination" {
    var f = try F.init();
    defer f.deinit();
    for (0..256) |v| try invoke(&f, 0x1b, @intCast(v), @intCast(v));
}

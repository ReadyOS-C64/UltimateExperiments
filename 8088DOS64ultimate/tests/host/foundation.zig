const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
test { _ = @import("reu.zig"); }
test { _ = @import("memory.zig"); }
test { _ = @import("cpu.zig"); }
test { _ = @import("escape.zig"); }
test { _ = @import("cga_crtc.zig"); }
test { _ = @import("alu.zig"); }
test { _ = @import("stack.zig"); }

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

test { _ = @import("operands.zig"); }

test { _ = @import("runner.zig"); }

test { _ = @import("interrupts.zig"); }
test { _ = @import("shifts.zig"); }
test { _ = @import("strings.zig"); }

test { _ = @import("math.zig"); }
test { _ = @import("indirect.zig"); }

test { _ = @import("range.zig"); }
test { _ = @import("disk.zig"); }
test { _ = @import("bios.zig"); }
test { _ = @import("range_probe.zig"); }
test { _ = @import("dos_boot.zig"); }
test { _ = @import("range_snapshot.zig"); }

test { _ = @import("fetch.zig"); }

test { _ = @import("ports.zig"); }
test { _ = @import("io_instructions.zig"); }

test { _ = @import("video.zig"); }
test { _ = @import("adjust.zig"); }
test { _ = @import("aux_bios.zig"); }

test { _ = @import("clock.zig"); }
test { _ = @import("keyboard.zig"); }
test { _ = @import("uci.zig"); }
test { _ = @import("host_clock.zig"); }

test { _ = @import("files.zig"); }
test { _ = @import("render_text.zig"); }
test { _ = @import("overlays.zig"); }
test { _ = @import("overlay_startup.zig"); }

test { _ = @import("host_input.zig"); }
test { _ = @import("cold_phase.zig"); }

test { _ = @import("native_text_display.zig"); }
test { _ = @import("elapsed.zig"); }

test { _ = @import("irq_pit.zig"); }
test { _ = @import("native_timer_startup.zig"); }
test { _ = @import("future_layout.zig"); }
test { _ = @import("native_cga.zig"); }
test { _ = @import("unit_cold_lifetime.zig"); }

comptime { _ = @import("video_xt_compat.zig"); }

test { _ = @import("video_spans.zig"); }

test { _ = @import("owned_clock_internal.zig"); }

test { _ = @import("cga_status.zig"); }

test { _ = @import("cga_cursor.zig"); }

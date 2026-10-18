const std = @import("std");
const host = @import("machine.zig");
const c = host.c;

// Retain the former bridge loop here as a regression reference. Both paths
// execute the same native instructions in separate real Peddle machines.
fn oldRun(machine: *c.Dos64Machine, sentinel: u16, budget: u64) c.Dos64RunResult {
    const start = c.dos64_get_regs(machine).cycles;
    var result: c.Dos64RunResult = std.mem.zeroes(c.Dos64RunResult);
    while (true) {
        result.regs = c.dos64_get_regs(machine);
        result.stack_high_water = @max(result.stack_high_water, 255 - result.regs.sp);
        if (c.dos64_model_fault(machine) != 0) result.status = c.DOS64_RUN_MODEL_FAULT else if (result.regs.pc == sentinel) {
            result.status = if (result.regs.sp == 0xff) c.DOS64_RUN_RETURNED else c.DOS64_RUN_STACK_IMBALANCE;
        } else if (result.regs.cycles - start >= budget) result.status = c.DOS64_RUN_CYCLE_BUDGET else if (c.dos64_peek(machine, result.regs.pc) == 0) result.status = c.DOS64_RUN_UNEXPECTED_BRK else {
            c.dos64_step(machine);
            continue;
        }
        return result;
    }
}

fn seed(machine: *c.Dos64Machine, program: []const u8) void {
    c.dos64_load(machine, 0x6000, program.ptr, program.len);
    c.dos64_poke(machine, 0x1ff, 0x60);
    c.dos64_poke(machine, 0x1fe, 0xff);
    c.dos64_clear_writes(machine);
    c.dos64_set_regs(machine, .{ .pc = 0x6000, .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
}

test "batched runner preserves bounded stepping, failure precedence and bus writes" {
    const success = [_]u8{ 0xa9, 0x42, 0x48, 0xa2, 3, 0xca, 0xd0, 0xfd, 0x68, 0x60 };
    const cases = [_]struct { program: []const u8, budget: u64, status: c.Dos64RunStatus }{
        .{ .program = &success, .budget = 100, .status = c.DOS64_RUN_RETURNED },
        .{ .program = &success, .budget = 7, .status = c.DOS64_RUN_CYCLE_BUDGET },
        .{ .program = &.{0}, .budget = 100, .status = c.DOS64_RUN_UNEXPECTED_BRK },
        .{ .program = &.{ 0x68, 0x4c, 0, 0x61 }, .budget = 100, .status = c.DOS64_RUN_STACK_IMBALANCE },
        .{ .program = &.{ 0xad, 0, 0xdf, 0x60 }, .budget = 100, .status = c.DOS64_RUN_MODEL_FAULT },
        .{ .program = &.{ 0xa9, 0x99, 0x8d, 0, 0x40, 0x60 }, .budget = 100, .status = c.DOS64_RUN_RETURNED },
        // Peddle returns from this undocumented opcode to the following BRK;
        // preserve the adapter's observed behavior without claiming jam timing.
        .{ .program = &.{0x02}, .budget = 100, .status = c.DOS64_RUN_UNEXPECTED_BRK },
    };
    for (cases) |case| {
        const old = c.dos64_create() orelse return error.CreateMachine;
        defer c.dos64_destroy(old);
        const batch = c.dos64_create() orelse return error.CreateMachine;
        defer c.dos64_destroy(batch);
        seed(old, case.program);
        seed(batch, case.program);
        const expected = oldRun(old, 0x6100, case.budget);
        const actual = c.dos64_run(batch, 0x6100, case.budget);
        try std.testing.expectEqual(case.status, actual.status);
        try std.testing.expectEqualDeep(expected, actual);
        for (0..65536) |index| {
            const address: u16 = @intCast(index);
            try std.testing.expectEqual(c.dos64_peek(old, address), c.dos64_peek(batch, address));
            try std.testing.expectEqual(c.dos64_was_written(old, address), c.dos64_was_written(batch, address));
        }
    }
}

test "batched return wins over zero budget and a preexisting model fault wins over return" {
    const machine = c.dos64_create() orelse return error.CreateMachine;
    defer c.dos64_destroy(machine);
    c.dos64_set_regs(machine, .{ .pc = 0x6100, .sp = 0xff, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    var result = c.dos64_run(machine, 0x6100, 0);
    try std.testing.expectEqual(@as(c.Dos64RunStatus, c.DOS64_RUN_RETURNED), result.status);
    try std.testing.expectEqual(@as(u8, 0), result.stack_high_water);
    _ = c.dos64_bus_read(machine, 0xdf00);
    result = c.dos64_run(machine, 0x6100, 0);
    try std.testing.expectEqual(@as(c.Dos64RunStatus, c.DOS64_RUN_MODEL_FAULT), result.status);
    try std.testing.expectEqual(@as(u64, 0), result.regs.instructions);
}

test "Fixture keeps cached symbols and cumulative stack high water with batched execution" {
    var f = try host.Fixture.init();
    defer f.deinit();
    const timed = try f.symbol("fixture_timed");
    try std.testing.expectEqual(timed, try f.symbol("fixture_timed"));
    const pass = try f.call("fixture_pass", 10_000);
    try std.testing.expectEqual(@as(u8, 4), f.stack_high_water);
    const after = try f.call("fixture_timed", 100);
    try std.testing.expectEqual(@as(u64, 8), after.cycles - pass.cycles);
    try std.testing.expectEqual(@as(u8, 4), f.stack_high_water);
    try std.testing.expectEqualDeep(after, f.last_regs.?);
}

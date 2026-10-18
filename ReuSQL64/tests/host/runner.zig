const std = @import("std");

const c = @cImport({
    @cInclude("rsql64_peddle.h");
});

const KernalChrout: u16 = 0xffd2;
const KernalGetin: u16 = 0xffe4;
const KernalReadst: u16 = 0xffb7;
const KernalSetlfs: u16 = 0xffba;
const KernalSetnam: u16 = 0xffbd;
const KernalOpen: u16 = 0xffc0;
const KernalClose: u16 = 0xffc3;
const KernalCkout: u16 = 0xffc9;
const KernalClrchn: u16 = 0xffcc;
const BasicFin: u16 = 0xbcf3;
const BasicMovfm: u16 = 0xbba2;
const BasicFadd: u16 = 0xb867;
const BasicFdiv: u16 = 0xbb0f;
const BasicMovmf: u16 = 0xbbd4;
const BasicFloatActive: u16 = 0xcfef;
const BorderColor: u16 = 0xd020;
const Sentinel: u16 = 0xcff0;
const ReuSizeSelector: u16 = 0xcff1;
const OverlayPreloadedMask: u16 = 0xcff2;
const CheckpointControl: u16 = 0xcfff;
const BenchmarkControl: u16 = 0xcfff;
const ShellCommands =
    "CREATE TYPE STATE AS ENUM8(NEW=1,DONE=2)\r" ++
    "CREATE TABLE T(ID I16,NAME CHAR(8),NOTE TEXT NULL,STATUS STATE)\r" ++
    "INSERT INTO T VALUES(-2,'BETA','LONG NOTE',STATE.DONE)\r" ++
    "SELECT ID,NAME,NOTE,STATUS FROM T\r" ++
    ".TABLES\r.SCHEMA T\r.TYPES\r.MEMBERS STATE\r.CHECKPOINT\r.QUIT\r";

pub fn main(init: std.process.Init) !void {
    const allocator = init.gpa;
    const io = init.io;
    var it = std.process.Args.Iterator.init(init.minimal.args);
    defer it.deinit();
    var args: std.ArrayList([]const u8) = .empty;
    defer args.deinit(allocator);
    while (it.next()) |arg| try args.append(allocator, arg);
    const extended = args.items.len >= 101 and
        !std.mem.startsWith(u8, args.items[91], "--");
    const checkpoint_extended = args.items.len >= 111 and extended and
        !std.mem.startsWith(u8, args.items[101], "--");
    const shell_extended = args.items.len >= 121 and checkpoint_extended and
        !std.mem.startsWith(u8, args.items[111], "--");
    const flag_index: usize = if (shell_extended) 121 else if (checkpoint_extended) 111 else if (extended) 101 else 91;
    const has_flag = args.items.len > flag_index;
    const result_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--result-only");
    const ctas_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--ctas-only");
    const varupdate_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--varupdate-only");
    const variable_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--variable-only");
    const aggregate_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--aggregate-only");
    const fixedagg_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--fixedagg-only");
    const join_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--join-only");
    const checkpoint_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--checkpoint-only");
    const shell_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--shell-only");
    const benchmark_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--benchmark-only");
    const pipeline_benchmark_only = has_flag and
        std.mem.eql(u8, args.items[flag_index], "--pipeline-benchmark-only");
    if (args.items.len != 91 and !(args.items.len == 101 and extended) and
        !(args.items.len == 111 and checkpoint_extended) and
        !(args.items.len == 121 and shell_extended) and
        !result_only and !ctas_only and
        !varupdate_only and !variable_only and !aggregate_only and
        !fixedagg_only and !join_only and !checkpoint_only and !shell_only and
        !benchmark_only and !pipeline_benchmark_only)
    {
        return error.ExpectedClientsAndOverlayPaths;
    }

    const storage_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[1], allocator, .limited(1024 * 1024));
    defer allocator.free(storage_bytes);
    const query_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[2], allocator, .limited(1024 * 1024));
    defer allocator.free(query_bytes);
    const aggregate_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[3], allocator, .limited(1024 * 1024));
    defer allocator.free(aggregate_bytes);
    const variable_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[4], allocator, .limited(1024 * 1024));
    defer allocator.free(variable_bytes);
    const varupdate_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[5], allocator, .limited(1024 * 1024));
    defer allocator.free(varupdate_bytes);
    const join_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[6], allocator, .limited(1024 * 1024));
    defer allocator.free(join_bytes);
    const joinagg_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[7], allocator, .limited(1024 * 1024));
    defer allocator.free(joinagg_bytes);
    const result_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[8], allocator, .limited(1024 * 1024));
    defer allocator.free(result_bytes);
    const ctas_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[9], allocator, .limited(1024 * 1024));
    defer allocator.free(ctas_bytes);
    var fixedagg_bytes: ?[]u8 = null;
    if (extended) {
        fixedagg_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[91], allocator, .limited(1024 * 1024));
    }
    defer if (fixedagg_bytes) |bytes| allocator.free(bytes);
    var checkpoint_bytes: ?[]u8 = null;
    if (checkpoint_extended) {
        checkpoint_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[101], allocator, .limited(1024 * 1024));
    }
    defer if (checkpoint_bytes) |bytes| allocator.free(bytes);
    var shell_bytes: ?[]u8 = null;
    if (shell_extended) {
        shell_bytes = try std.Io.Dir.cwd().readFileAlloc(io, args.items[111], allocator, .limited(1024 * 1024));
    }
    defer if (shell_bytes) |bytes| allocator.free(bytes);
    var storage_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        storage_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 10], allocator, .limited(64 * 1024));
    }
    defer for (storage_overlays) |overlay| allocator.free(overlay);
    var query_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        query_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 19], allocator, .limited(64 * 1024));
    }
    defer for (query_overlays) |overlay| allocator.free(overlay);
    var aggregate_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        aggregate_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 28], allocator, .limited(64 * 1024));
    }
    defer for (aggregate_overlays) |overlay| allocator.free(overlay);
    var variable_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        variable_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 37], allocator, .limited(64 * 1024));
    }
    defer for (variable_overlays) |overlay| allocator.free(overlay);
    var varupdate_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        varupdate_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 46], allocator, .limited(64 * 1024));
    }
    defer for (varupdate_overlays) |overlay| allocator.free(overlay);
    var join_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        join_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 55], allocator, .limited(64 * 1024));
    }
    defer for (join_overlays) |overlay| allocator.free(overlay);
    var joinagg_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        joinagg_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 64], allocator, .limited(64 * 1024));
    }
    defer for (joinagg_overlays) |overlay| allocator.free(overlay);
    var result_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        result_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 73], allocator, .limited(64 * 1024));
    }
    defer for (result_overlays) |overlay| allocator.free(overlay);
    var ctas_overlays: [9][]u8 = undefined;
    for (0..9) |index| {
        ctas_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 82], allocator, .limited(64 * 1024));
    }
    defer for (ctas_overlays) |overlay| allocator.free(overlay);
    var fixedagg_overlays: [9][]u8 = undefined;
    if (extended) {
        for (0..9) |index| {
            fixedagg_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 92], allocator, .limited(64 * 1024));
        }
    }
    defer {
        if (extended) {
            for (fixedagg_overlays) |overlay| allocator.free(overlay);
        }
    }
    var checkpoint_overlays: [9][]u8 = undefined;
    if (checkpoint_extended) {
        for (0..9) |index| {
            checkpoint_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 102], allocator, .limited(64 * 1024));
        }
    }
    defer {
        if (checkpoint_extended) {
            for (checkpoint_overlays) |overlay| allocator.free(overlay);
        }
    }
    var shell_overlays: [9][]u8 = undefined;
    if (shell_extended) {
        for (0..9) |index| {
            shell_overlays[index] = try std.Io.Dir.cwd().readFileAlloc(io, args.items[index + 112], allocator, .limited(64 * 1024));
        }
    }
    defer {
        if (shell_extended) {
            for (shell_overlays) |overlay| allocator.free(overlay);
        }
    }
    if (storage_bytes.len < 3 or query_bytes.len < 3 or
        aggregate_bytes.len < 3 or variable_bytes.len < 3 or
        varupdate_bytes.len < 3 or join_bytes.len < 3 or
        joinagg_bytes.len < 3 or result_bytes.len < 3 or
        ctas_bytes.len < 3 or
        (fixedagg_bytes != null and fixedagg_bytes.?.len < 3) or
        (checkpoint_bytes != null and checkpoint_bytes.?.len < 3) or
        (shell_bytes != null and shell_bytes.?.len < 3))
    {
        return error.InvalidPrg;
    }
    const storage_load_address = @as(u16, storage_bytes[0]) | (@as(u16, storage_bytes[1]) << 8);
    const query_load_address = @as(u16, query_bytes[0]) | (@as(u16, query_bytes[1]) << 8);
    const aggregate_load_address = @as(u16, aggregate_bytes[0]) | (@as(u16, aggregate_bytes[1]) << 8);
    const variable_load_address = @as(u16, variable_bytes[0]) | (@as(u16, variable_bytes[1]) << 8);
    const varupdate_load_address = @as(u16, varupdate_bytes[0]) | (@as(u16, varupdate_bytes[1]) << 8);
    const join_load_address = @as(u16, join_bytes[0]) | (@as(u16, join_bytes[1]) << 8);
    const joinagg_load_address = @as(u16, joinagg_bytes[0]) | (@as(u16, joinagg_bytes[1]) << 8);
    const result_load_address = @as(u16, result_bytes[0]) | (@as(u16, result_bytes[1]) << 8);
    const ctas_load_address = @as(u16, ctas_bytes[0]) | (@as(u16, ctas_bytes[1]) << 8);
    const fixedagg_load_address = if (fixedagg_bytes) |bytes|
        @as(u16, bytes[0]) | (@as(u16, bytes[1]) << 8)
    else
        0;
    const checkpoint_load_address = if (checkpoint_bytes) |bytes|
        @as(u16, bytes[0]) | (@as(u16, bytes[1]) << 8)
    else
        0;
    const shell_load_address = if (shell_bytes) |bytes|
        @as(u16, bytes[0]) | (@as(u16, bytes[1]) << 8)
    else
        0;

    if (shell_only) {
        const bytes = shell_bytes orelse return error.ShellClientRequired;
        try runCase(allocator, io, "shell", shell_load_address, bytes[2..], shell_overlays, 512, 0);
        try runCase(allocator, io, "shell", shell_load_address, bytes[2..], shell_overlays, 16384, 5);
        var shell_stdout_buffer: [256]u8 = undefined;
        var shell_stdout = std.Io.File.stdout().writer(io, &shell_stdout_buffer);
        defer shell_stdout.interface.flush() catch {};
        try shell_stdout.interface.print("Peddle target interactive shell regression passed at 512KB and 16MB\n", .{});
        return;
    }

    if (benchmark_only) {
        try runCase(allocator, io, "benchmark", join_load_address, join_bytes[2..], join_overlays, 512, 0);
        var benchmark_stdout_buffer: [256]u8 = undefined;
        var benchmark_stdout = std.Io.File.stdout().writer(io, &benchmark_stdout_buffer);
        defer benchmark_stdout.interface.flush() catch {};
        try benchmark_stdout.interface.print("Peddle real-world benchmark regression passed at 512KB\n", .{});
        return;
    }

    if (pipeline_benchmark_only) {
        try runCase(allocator, io, "pipeline-benchmark", join_load_address, join_bytes[2..], join_overlays, 512, 0);
        var pipeline_stdout_buffer: [256]u8 = undefined;
        var pipeline_stdout = std.Io.File.stdout().writer(io, &pipeline_stdout_buffer);
        defer pipeline_stdout.interface.flush() catch {};
        try pipeline_stdout.interface.print("Peddle staged TEMP-table benchmark passed at 512KB\n", .{});
        return;
    }

    if (checkpoint_only) {
        const bytes = checkpoint_bytes orelse return error.CheckpointClientRequired;
        try runCase(allocator, io, "checkpoint", checkpoint_load_address, bytes[2..], checkpoint_overlays, 512, 0);
        try runCase(allocator, io, "checkpoint", checkpoint_load_address, bytes[2..], checkpoint_overlays, 16384, 5);
        var checkpoint_stdout_buffer: [256]u8 = undefined;
        var checkpoint_stdout = std.Io.File.stdout().writer(io, &checkpoint_stdout_buffer);
        defer checkpoint_stdout.interface.flush() catch {};
        try checkpoint_stdout.interface.print("Peddle target whole-REU checkpoint/restore regression passed at 512KB and 16MB\n", .{});
        return;
    }

    if (result_only) {
        try runCase(allocator, io, "result", result_load_address, result_bytes[2..], result_overlays, 512, 0);
        try runCase(allocator, io, "result", result_load_address, result_bytes[2..], result_overlays, 16384, 5);
        var result_stdout_buffer: [256]u8 = undefined;
        var result_stdout = std.Io.File.stdout().writer(io, &result_stdout_buffer);
        defer result_stdout.interface.flush() catch {};
        try result_stdout.interface.print("Peddle target result-shaping regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (ctas_only) {
        try runCase(allocator, io, "ctas", ctas_load_address, ctas_bytes[2..], ctas_overlays, 512, 0);
        try runCase(allocator, io, "ctas", ctas_load_address, ctas_bytes[2..], ctas_overlays, 16384, 5);
        var ctas_stdout_buffer: [256]u8 = undefined;
        var ctas_stdout = std.Io.File.stdout().writer(io, &ctas_stdout_buffer);
        defer ctas_stdout.interface.flush() catch {};
        try ctas_stdout.interface.print("Peddle target CTAS/lifecycle regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (varupdate_only) {
        try runCase(allocator, io, "varupdate", varupdate_load_address, varupdate_bytes[2..], varupdate_overlays, 512, 0);
        try runCase(allocator, io, "varupdate", varupdate_load_address, varupdate_bytes[2..], varupdate_overlays, 16384, 5);
        var varupdate_stdout_buffer: [256]u8 = undefined;
        var varupdate_stdout = std.Io.File.stdout().writer(io, &varupdate_stdout_buffer);
        defer varupdate_stdout.interface.flush() catch {};
        try varupdate_stdout.interface.print("Peddle target variable-update/schema-drop regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (variable_only) {
        try runCase(allocator, io, "variable", variable_load_address, variable_bytes[2..], variable_overlays, 512, 0);
        try runCase(allocator, io, "variable", variable_load_address, variable_bytes[2..], variable_overlays, 16384, 5);
        var variable_stdout_buffer: [256]u8 = undefined;
        var variable_stdout = std.Io.File.stdout().writer(io, &variable_stdout_buffer);
        defer variable_stdout.interface.flush() catch {};
        try variable_stdout.interface.print("Peddle target variable-value regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (aggregate_only) {
        try runCase(allocator, io, "aggregate", aggregate_load_address, aggregate_bytes[2..], aggregate_overlays, 512, 0);
        try runCase(allocator, io, "aggregate", aggregate_load_address, aggregate_bytes[2..], aggregate_overlays, 16384, 5);
        if (fixedagg_bytes) |bytes| {
            try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 512, 0);
            try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 16384, 5);
        }
        var aggregate_stdout_buffer: [256]u8 = undefined;
        var aggregate_stdout = std.Io.File.stdout().writer(io, &aggregate_stdout_buffer);
        defer aggregate_stdout.interface.flush() catch {};
        try aggregate_stdout.interface.print("Peddle target integer/FLOAT/FIXED8_8 aggregate regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (fixedagg_only) {
        const bytes = fixedagg_bytes orelse return error.FixedAggregateClientRequired;
        try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 512, 0);
        try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 16384, 5);
        var fixed_stdout_buffer: [256]u8 = undefined;
        var fixed_stdout = std.Io.File.stdout().writer(io, &fixed_stdout_buffer);
        defer fixed_stdout.interface.flush() catch {};
        try fixed_stdout.interface.print("Peddle target FIXED8_8 aggregate regression passed at 512KB and 16MB\n", .{});
        return;
    }
    if (join_only) {
        try runCase(allocator, io, "join", join_load_address, join_bytes[2..], join_overlays, 512, 0);
        try runCase(allocator, io, "join", join_load_address, join_bytes[2..], join_overlays, 16384, 5);
        var join_stdout_buffer: [256]u8 = undefined;
        var join_stdout = std.Io.File.stdout().writer(io, &join_stdout_buffer);
        defer join_stdout.interface.flush() catch {};
        try join_stdout.interface.print("Peddle target join/subquery regression passed at 512KB and 16MB\n", .{});
        return;
    }

    try runCase(allocator, io, "storage", storage_load_address, storage_bytes[2..], storage_overlays, 512, 0);
    try runCase(allocator, io, "storage", storage_load_address, storage_bytes[2..], storage_overlays, 16384, 5);
    try runCase(allocator, io, "query", query_load_address, query_bytes[2..], query_overlays, 512, 0);
    try runCase(allocator, io, "query", query_load_address, query_bytes[2..], query_overlays, 16384, 5);
    try runCase(allocator, io, "aggregate", aggregate_load_address, aggregate_bytes[2..], aggregate_overlays, 512, 0);
    try runCase(allocator, io, "aggregate", aggregate_load_address, aggregate_bytes[2..], aggregate_overlays, 16384, 5);
    try runCase(allocator, io, "variable", variable_load_address, variable_bytes[2..], variable_overlays, 512, 0);
    try runCase(allocator, io, "variable", variable_load_address, variable_bytes[2..], variable_overlays, 16384, 5);
    try runCase(allocator, io, "varupdate", varupdate_load_address, varupdate_bytes[2..], varupdate_overlays, 512, 0);
    try runCase(allocator, io, "varupdate", varupdate_load_address, varupdate_bytes[2..], varupdate_overlays, 16384, 5);
    try runCase(allocator, io, "join", join_load_address, join_bytes[2..], join_overlays, 512, 0);
    try runCase(allocator, io, "join", join_load_address, join_bytes[2..], join_overlays, 16384, 5);
    try runCase(allocator, io, "joinagg", joinagg_load_address, joinagg_bytes[2..], joinagg_overlays, 512, 0);
    try runCase(allocator, io, "joinagg", joinagg_load_address, joinagg_bytes[2..], joinagg_overlays, 16384, 5);
    try runCase(allocator, io, "result", result_load_address, result_bytes[2..], result_overlays, 512, 0);
    try runCase(allocator, io, "result", result_load_address, result_bytes[2..], result_overlays, 16384, 5);
    try runCase(allocator, io, "ctas", ctas_load_address, ctas_bytes[2..], ctas_overlays, 512, 0);
    try runCase(allocator, io, "ctas", ctas_load_address, ctas_bytes[2..], ctas_overlays, 16384, 5);
    if (fixedagg_bytes) |bytes| {
        try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 512, 0);
        try runCase(allocator, io, "fixedagg", fixedagg_load_address, bytes[2..], fixedagg_overlays, 16384, 5);
    }
    if (checkpoint_bytes) |bytes| {
        try runCase(allocator, io, "checkpoint", checkpoint_load_address, bytes[2..], checkpoint_overlays, 512, 0);
        try runCase(allocator, io, "checkpoint", checkpoint_load_address, bytes[2..], checkpoint_overlays, 16384, 5);
    }
    if (shell_bytes) |bytes| {
        try runCase(allocator, io, "shell", shell_load_address, bytes[2..], shell_overlays, 512, 0);
        try runCase(allocator, io, "shell", shell_load_address, bytes[2..], shell_overlays, 16384, 5);
    }

    var stdout_buffer: [1024]u8 = undefined;
    var stdout = std.Io.File.stdout().writer(io, &stdout_buffer);
    defer stdout.interface.flush() catch {};
    try stdout.interface.print("Peddle target storage/query/integer-FLOAT-FIXED8_8 aggregate/variable/varupdate/join/join-aggregate/subquery/result-shaping/CTAS/checkpoint/shell regression passed at 512KB and 16MB\n", .{});
}

fn runCase(allocator: std.mem.Allocator, io: std.Io, lane: []const u8, load_address: u16, payload: []const u8, overlays: [9][]u8, reu_size_kib: u32, selector: u8) !void {
    const machine = c.rsql64_peddle_create(reu_size_kib) orelse return error.EmulatorCreateFailed;
    defer c.rsql64_peddle_destroy(machine);
    if (c.rsql64_peddle_reu_size(machine) != reu_size_kib * 1024) {
        return error.ReuSizeMismatch;
    }
    const image_probe = [_]u8{ 0x52, 0x53, 0x51, 0x4c };
    var image_copy: [4]u8 = undefined;
    if (c.rsql64_peddle_load_reu(machine, 0x0120, &image_probe, image_probe.len) != image_probe.len) {
        return error.ReuImageLoadFailed;
    }
    if (c.rsql64_peddle_copy_reu(machine, 0x0120, &image_copy, image_copy.len) != image_copy.len or
        !std.mem.eql(u8, &image_probe, &image_copy))
    {
        return error.ReuImageCopyFailed;
    }
    c.rsql64_peddle_clear_memory(machine);
    c.rsql64_peddle_load(machine, load_address, payload.ptr, payload.len);
    const overlay_base = reu_size_kib * 1024 - 139264;
    for (overlays[0..7], 0..) |overlay, slot| {
        if (overlay.len != 17410 or overlay[0] != 0x00 or overlay[1] != 0x7c) {
            return error.InvalidOverlaySidecar;
        }
        const loaded = c.rsql64_peddle_load_reu(
            machine,
            overlay_base + @as(u32, @intCast(slot)) * 17408,
            overlay[2..].ptr,
            17408,
        );
        if (loaded != 17408) return error.OverlayPreloadFailed;
    }
    const admin_overlay = overlays[7];
    if (admin_overlay.len != 17410 or admin_overlay[0] != 0x00 or
        admin_overlay[1] != 0x7c)
    {
        return error.InvalidAdminSidecar;
    }
    if (c.rsql64_peddle_load_reu(machine, 34 * 256, admin_overlay[2..].ptr, 17408) != 17408) {
        return error.AdminPreloadFailed;
    }
    const wide_overlay = overlays[8];
    if (wide_overlay.len != 17410 or wide_overlay[0] != 0x00 or
        wide_overlay[1] != 0x7c)
    {
        return error.InvalidWideSidecar;
    }
    if (c.rsql64_peddle_load_reu(machine, overlay_base + 7 * 17408, wide_overlay[2..].ptr, 17408) != 17408) {
        return error.WidePreloadFailed;
    }
    c.rsql64_peddle_reset(machine);
    c.rsql64_peddle_set_sp(machine, 0xff);
    c.rsql64_peddle_write(machine, 0x0001, 0x37);
    c.rsql64_peddle_write(machine, ReuSizeSelector, selector);
    c.rsql64_peddle_write(machine, OverlayPreloadedMask, 0xff);
    c.rsql64_peddle_set_pc(machine, 0x080d);

    var output: std.ArrayList(u8) = .empty;
    defer output.deinit(allocator);
    var checkpoint_image: ?[]u8 = null;
    defer if (checkpoint_image) |bytes| allocator.free(bytes);
    var checkpoint_stage: u8 = 0;
    var shell_input_index: usize = 0;
    var basic_fac: f64 = 0.0;
    var budget: usize = if (std.mem.eql(u8, lane, "storage"))
        192_000_000
    else if (std.mem.eql(u8, lane, "aggregate"))
        128_000_000
    else if (std.mem.eql(u8, lane, "fixedagg"))
        128_000_000
    else if (std.mem.eql(u8, lane, "varupdate"))
        128_000_000
    else if (std.mem.eql(u8, lane, "variable"))
        48_000_000
    else if (std.mem.eql(u8, lane, "join"))
        96_000_000
    else if (std.mem.eql(u8, lane, "joinagg"))
        256_000_000
    else if (std.mem.eql(u8, lane, "result"))
        64_000_000
    else if (std.mem.eql(u8, lane, "ctas"))
        96_000_000
    else if (std.mem.eql(u8, lane, "query"))
        48_000_000
    else if (std.mem.eql(u8, lane, "checkpoint"))
        48_000_000
    else if (std.mem.eql(u8, lane, "shell"))
        96_000_000
    else if (std.mem.eql(u8, lane, "benchmark") or
        std.mem.eql(u8, lane, "pipeline-benchmark"))
        2_000_000_000
    else
        24_000_000;
    var trace = [_]u16{0} ** 64;
    var trace_index: usize = 0;
    var summary_start_cycles: ?u64 = null;
    var summary_start_instructions: ?u64 = null;
    var summary_cycles: ?u64 = null;
    var summary_instructions: ?u64 = null;
    var eligible_start_cycles: ?u64 = null;
    var eligible_start_instructions: ?u64 = null;
    var eligible_cycles: ?u64 = null;
    var eligible_instructions: ?u64 = null;
    while (budget > 0) : (budget -= 1) {
        const regs = c.rsql64_peddle_regs(machine);
        const pc: u16 = @intCast(regs.pc);
        trace[trace_index] = pc;
        trace_index = (trace_index + 1) % trace.len;
        if (std.mem.eql(u8, lane, "benchmark") or
            std.mem.eql(u8, lane, "pipeline-benchmark"))
        {
            const stage = c.rsql64_peddle_read(machine, 0xcff3);
            if (stage == 0xb1 and summary_start_cycles == null) {
                summary_start_cycles = regs.cycles;
                summary_start_instructions = regs.instructions;
            } else if (stage == 0xb2 and summary_cycles == null) {
                summary_cycles = regs.cycles - summary_start_cycles.?;
                summary_instructions = regs.instructions -
                    summary_start_instructions.?;
                c.rsql64_peddle_write(machine, BenchmarkControl, 1);
            } else if (stage == 0xc1 and eligible_start_cycles == null) {
                eligible_start_cycles = regs.cycles;
                eligible_start_instructions = regs.instructions;
            } else if (stage == 0xc2 and eligible_cycles == null) {
                eligible_cycles = regs.cycles - eligible_start_cycles.?;
                eligible_instructions = regs.instructions -
                    eligible_start_instructions.?;
                c.rsql64_peddle_write(machine, BenchmarkControl, 2);
            }
        }
        if (std.mem.eql(u8, lane, "checkpoint")) {
            const sentinel = c.rsql64_peddle_read(machine, Sentinel);
            if (sentinel == 0xc1 and checkpoint_stage == 0) {
                const image = try allocator.alloc(u8, reu_size_kib * 1024);
                if (c.rsql64_peddle_copy_reu(machine, 0, image.ptr, image.len) != image.len) {
                    return error.ReuCheckpointCopyFailed;
                }
                checkpoint_image = image;
                checkpoint_stage = 1;
                c.rsql64_peddle_write(machine, CheckpointControl, 1);
            } else if (sentinel == 0xc2 and checkpoint_stage == 1) {
                const image = checkpoint_image orelse
                    return error.ReuCheckpointImageMissing;
                if (c.rsql64_peddle_load_reu(machine, 0, image.ptr, image.len) != image.len) {
                    return error.ReuCheckpointLoadFailed;
                }
                checkpoint_stage = 2;
                // Exclude cc65 startup's CHROUT charset switch; bytes emitted
                // after restore belong to the export adapter under test.
                output.clearRetainingCapacity();
                c.rsql64_peddle_write(machine, CheckpointControl, 2);
            }
        }
        if (c.rsql64_peddle_read(machine, Sentinel) == 0xa5 and
            c.rsql64_peddle_read(machine, BorderColor) == 5)
        {
            break;
        }
        if (c.rsql64_peddle_read(machine, BorderColor) == 2) {
            std.debug.print("{s}/{d}KiB regression failed at stage=${x:0>2}, detail=${x:0>2}, diag=${x:0>2}/${x:0>2}, sentinel=${x:0>2}, pc=${x:0>4}, sp=${x:0>2}, csp=${x:0>2}{x:0>2}\n", .{ lane, reu_size_kib, c.rsql64_peddle_read(machine, 0xcff3), c.rsql64_peddle_read(machine, 0xcff4), c.rsql64_peddle_read(machine, 0xcff5), c.rsql64_peddle_read(machine, 0xcff6), c.rsql64_peddle_read(machine, Sentinel), pc, regs.sp, c.rsql64_peddle_read(machine, 0x0003), c.rsql64_peddle_read(machine, 0x0002) });
            var fail_stack: [8]u8 = undefined;
            for (0..fail_stack.len) |stack_index| {
                fail_stack[stack_index] = c.rsql64_peddle_read(machine, 0x01f8 + @as(u16, @intCast(stack_index)));
            }
            std.debug.print("failure hardware stack $01f8-$01ff: {any}\n", .{fail_stack});
            std.debug.print("failure pc trace next={d}: {any}\n", .{ trace_index, trace });
            return error.TargetRegressionFailed;
        }
        if (try handleBasicFloat(machine, pc, regs, &basic_fac)) {
            returnFromSubroutine(machine, regs.sp);
            continue;
        }
        if (isKernalStub(pc)) {
            if (pc == KernalChrout) try output.append(allocator, @intCast(regs.a));
            if (pc == KernalReadst) c.rsql64_peddle_set_a(machine, 0);
            if (pc == KernalGetin) {
                c.rsql64_peddle_set_a(machine, shellInputByte(&shell_input_index));
            }
            c.rsql64_peddle_set_p(machine, @intCast(regs.p & ~@as(u8, 1)));
            returnFromSubroutine(machine, regs.sp);
            continue;
        }
        const opcode = c.rsql64_peddle_read(machine, pc);
        if (opcode == 0x00) {
            var stack: [16]u8 = undefined;
            for (0..stack.len) |stack_index| {
                stack[stack_index] = c.rsql64_peddle_read(machine, 0x01f0 + @as(u16, @intCast(stack_index)));
            }
            std.debug.print("{s}/{d}KiB BRK at ${x:0>4}, sp=${x:0>2}, a=${x:0>2}, x=${x:0>2}, y=${x:0>2}, sentinel=${x:0>2}, border=${x:0>2}, output={s}\n", .{
                lane,
                reu_size_kib,
                pc,
                regs.sp,
                regs.a,
                regs.x,
                regs.y,
                c.rsql64_peddle_read(machine, Sentinel),
                c.rsql64_peddle_read(machine, BorderColor),
                output.items,
            });
            std.debug.print("hardware stack $01f0-$01ff: {any}\n", .{stack});
            std.debug.print("pc trace next={d}: {any}\n", .{ trace_index, trace });
            std.debug.print("cc65 software sp=${x:0>2}{x:0>2}\n", .{
                c.rsql64_peddle_read(machine, 0x0003),
                c.rsql64_peddle_read(machine, 0x0002),
            });
            return error.BrkEncountered;
        }
        if (opcode == 0x20) {
            const target_addr = pc +% 1;
            const target = @as(u16, c.rsql64_peddle_read(machine, target_addr)) |
                (@as(u16, c.rsql64_peddle_read(machine, target_addr +% 1)) << 8);
            if (target == KernalChrout) {
                try output.append(allocator, @intCast(regs.a));
                c.rsql64_peddle_set_pc(machine, pc +% 3);
                continue;
            }
            if (target == KernalReadst) {
                c.rsql64_peddle_set_a(machine, 0);
                c.rsql64_peddle_set_p(machine, @intCast(regs.p & ~@as(u8, 1)));
                c.rsql64_peddle_set_pc(machine, pc +% 3);
                continue;
            }
            if (target == KernalGetin) {
                c.rsql64_peddle_set_a(machine, shellInputByte(&shell_input_index));
                c.rsql64_peddle_set_pc(machine, pc +% 3);
                continue;
            }
            if (target == KernalSetlfs or target == KernalSetnam or
                target == KernalOpen or target == KernalClose or
                target == KernalCkout or target == KernalClrchn)
            {
                c.rsql64_peddle_set_p(machine, @intCast(regs.p & ~@as(u8, 1)));
                c.rsql64_peddle_set_pc(machine, pc +% 3);
                continue;
            }
        }
        c.rsql64_peddle_step_instruction(machine);
    } else {
        const regs = c.rsql64_peddle_regs(machine);
        var stack: [16]u8 = undefined;
        for (0..stack.len) |stack_index| {
            stack[stack_index] = c.rsql64_peddle_read(machine, 0x01f0 + @as(u16, @intCast(stack_index)));
        }
        std.debug.print("{s}/{d}KiB instruction budget exhausted at ${x:0>4}, sp=${x:0>2}, sentinel=${x:0>2}, border=${x:0>2}, diag={x:0>2}/{x:0>2}/{x:0>2}/{x:0>2}, output={s}\n", .{
            lane,
            reu_size_kib,
            @as(u16, @intCast(regs.pc)),
            regs.sp,
            c.rsql64_peddle_read(machine, Sentinel),
            c.rsql64_peddle_read(machine, BorderColor),
            c.rsql64_peddle_read(machine, 0xcff3),
            c.rsql64_peddle_read(machine, 0xcff4),
            c.rsql64_peddle_read(machine, 0xcff5),
            c.rsql64_peddle_read(machine, 0xcff6),
            output.items,
        });
        std.debug.print("hardware stack $01f0-$01ff: {any}\n", .{stack});
        std.debug.print("cc65 software sp=${x:0>2}{x:0>2}\n", .{
            c.rsql64_peddle_read(machine, 0x0003),
            c.rsql64_peddle_read(machine, 0x0002),
        });
        return error.InstructionBudgetExceeded;
    }

    if (c.rsql64_peddle_read(machine, Sentinel) != 0xa5) return error.FoundationSentinelMissing;
    if (c.rsql64_peddle_read(machine, BorderColor) != 5) return error.FoundationBorderWrong;
    if (std.mem.eql(u8, lane, "benchmark")) {
        if (summary_cycles == null or summary_instructions == null or
            eligible_cycles == null or eligible_instructions == null)
        {
            return error.BenchmarkTimingMissing;
        }
        std.debug.print("Peddle benchmark/512KiB sales-summary: {d} cycles, {d} instructions\n" ++
            "Peddle benchmark/512KiB eligible-sales: {d} cycles, {d} instructions\n", .{ summary_cycles.?, summary_instructions.?, eligible_cycles.?, eligible_instructions.? });
    }
    if (std.mem.eql(u8, lane, "pipeline-benchmark")) {
        if (summary_cycles == null or summary_instructions == null or
            eligible_cycles == null or eligible_instructions == null)
        {
            return error.BenchmarkTimingMissing;
        }
        std.debug.print("Peddle pipeline/512KiB full materialized pipeline: {d} cycles, {d} instructions\n" ++
            "Peddle pipeline/512KiB final grouped query: {d} cycles, {d} instructions\n", .{ summary_cycles.?, summary_instructions.?, eligible_cycles.?, eligible_instructions.? });
    }
    if (std.mem.eql(u8, lane, "checkpoint")) {
        const expected_export = [_]u8{
            'R',  'S',  'Q',  'X',  1,    3,
            0x52, 3,    0,    2,    0,    1,
            0,    9,    0,    5,    0,    0xc1,
            0xcc, 0xd0, 0xc8, 0xc1, 11,   0,
            1,    0,    1,    0x52, 3,    0,
            2,    0,    2,    0,    9,    0,
            4,    0,    0xc2, 0xc5, 0xd4, 0xc1,
            11,   0,    1,    0,    2,    0xff,
            2,    0,    0,    0,
        };
        if (!std.mem.eql(u8, output.items, &expected_export)) {
            std.debug.print("checkpoint/{d}KiB D81 export mismatch: {any}\n", .{
                reu_size_kib, output.items,
            });
            return error.ExportFramingMismatch;
        }
    }
    if (std.mem.eql(u8, lane, "shell")) {
        const expected = [_][]const u8{
            "REUSQL64 SHELL 0.1\r",
            "-2, BETA    , LONG NOTE, 2\r",
            "TABLE T ROWS=1 COLUMNS=4",
            "COLUMN NOTE TEXT NULL",
            "TYPE STATE ENUM8 MEMBERS=2",
            "MEMBER DONE=2",
            "CHECKPOINT READY\r",
            "BYE\r",
        };
        for (expected) |needle| {
            if (std.mem.indexOf(u8, output.items, needle) == null) {
                std.debug.print("shell/{d}KiB missing output '{s}': {any}\n", .{
                    reu_size_kib, needle, output.items,
                });
                return error.ShellOutputMismatch;
            }
        }
    }
    const software_sp = @as(u16, c.rsql64_peddle_read(machine, 0x0002)) |
        (@as(u16, c.rsql64_peddle_read(machine, 0x0003)) << 8);
    if (software_sp < 0x7800 or software_sp > 0x7c00) {
        std.debug.print("{s}/{d}KiB cc65 software stack outside $7800-$7C00: ${x:0>4}\n", .{
            lane, reu_size_kib, software_sp,
        });
        return error.SoftwareStackOutOfRange;
    }
    _ = io;
}

fn readBasicFloat(machine: *c.Rsql64Peddle, address: u16) f64 {
    const exponent = c.rsql64_peddle_read(machine, address);
    if (exponent == 0) return 0.0;
    const first = c.rsql64_peddle_read(machine, address +% 1);
    const fraction = (@as(u32, first & 0x7f) << 24) |
        (@as(u32, c.rsql64_peddle_read(machine, address +% 2)) << 16) |
        (@as(u32, c.rsql64_peddle_read(machine, address +% 3)) << 8) |
        @as(u32, c.rsql64_peddle_read(machine, address +% 4));
    var value = 1.0 + @as(f64, @floatFromInt(fraction)) / 2147483648.0;
    var power: i32 = @as(i32, exponent) - 129;
    while (power > 0) : (power -= 1) value *= 2.0;
    while (power < 0) : (power += 1) value /= 2.0;
    return if ((first & 0x80) != 0) -value else value;
}

fn writeBasicFloat(machine: *c.Rsql64Peddle, address: u16, input: f64) void {
    if (input == 0.0) {
        for (0..5) |index| {
            c.rsql64_peddle_write(machine, address +% @as(u16, @intCast(index)), 0);
        }
        return;
    }
    const negative = input < 0.0;
    var normalized = if (negative) -input else input;
    var exponent: i32 = 129;
    while (normalized >= 2.0) : (exponent += 1) normalized /= 2.0;
    while (normalized < 1.0) : (exponent -= 1) normalized *= 2.0;
    var rounded: u64 = @intFromFloat(@floor((normalized - 1.0) * 2147483648.0 + 0.5));
    if (rounded >= 0x80000000) {
        rounded = 0;
        exponent += 1;
    }
    const fraction: u32 = @intCast(rounded);
    c.rsql64_peddle_write(machine, address, @intCast(exponent));
    c.rsql64_peddle_write(machine, address +% 1, @as(u8, @intCast((fraction >> 24) & 0x7f)) |
        (if (negative) @as(u8, 0x80) else 0));
    c.rsql64_peddle_write(machine, address +% 2, @intCast((fraction >> 16) & 0xff));
    c.rsql64_peddle_write(machine, address +% 3, @intCast((fraction >> 8) & 0xff));
    c.rsql64_peddle_write(machine, address +% 4, @intCast(fraction & 0xff));
}

fn handleBasicFloat(machine: *c.Rsql64Peddle, pc: u16, regs: c.Rsql64PeddleRegs, fac: *f64) !bool {
    // The overlay occupies the same addresses in flat Peddle RAM. Only treat
    // these PCs as BASIC entry points during an explicit float-bridge call.
    if (c.rsql64_peddle_read(machine, BasicFloatActive) == 0) return false;
    if (pc == BasicFin) {
        const address = @as(u16, c.rsql64_peddle_read(machine, 0x007a)) |
            (@as(u16, c.rsql64_peddle_read(machine, 0x007b)) << 8);
        var text_buffer: [64]u8 = undefined;
        var length: usize = 0;
        while (length < text_buffer.len) : (length += 1) {
            const byte = c.rsql64_peddle_read(machine, address +% @as(u16, @intCast(length)));
            if (byte == 0) break;
            text_buffer[length] = byte;
        }
        fac.* = try std.fmt.parseFloat(f64, text_buffer[0..length]);
        return true;
    }
    if (pc == BasicMovfm) {
        const address = @as(u16, regs.a) | (@as(u16, regs.y) << 8);
        fac.* = readBasicFloat(machine, address);
        return true;
    }
    if (pc == BasicFadd) {
        const address = @as(u16, regs.a) | (@as(u16, regs.y) << 8);
        fac.* += readBasicFloat(machine, address);
        return true;
    }
    if (pc == BasicFdiv) {
        const address = @as(u16, regs.a) | (@as(u16, regs.y) << 8);
        fac.* = readBasicFloat(machine, address) / fac.*;
        return true;
    }
    if (pc == BasicMovmf) {
        const address = @as(u16, regs.x) | (@as(u16, regs.y) << 8);
        writeBasicFloat(machine, address, fac.*);
        return true;
    }
    return false;
}

fn isKernalStub(pc: u16) bool {
    return pc == KernalChrout or pc == KernalReadst or pc == KernalSetlfs or
        pc == KernalSetnam or pc == KernalOpen or pc == KernalClose or
        pc == KernalCkout or pc == KernalClrchn or pc == KernalGetin;
}

fn shellInputByte(index: *usize) u8 {
    var value: u8 = 0;
    if (index.* < ShellCommands.len) {
        value = ShellCommands[index.*];
        index.* += 1;
        if (value >= 'A' and value <= 'Z') value |= 0x80;
    }
    return value;
}

fn returnFromSubroutine(machine: *c.Rsql64Peddle, sp: u8) void {
    const next_sp = sp +% 1;
    const lo = c.rsql64_peddle_read(machine, 0x0100 + @as(u16, next_sp));
    const hi_sp = next_sp +% 1;
    const hi = c.rsql64_peddle_read(machine, 0x0100 + @as(u16, hi_sp));
    const return_minus_one = @as(u16, lo) | (@as(u16, hi) << 8);
    c.rsql64_peddle_set_sp(machine, hi_sp);
    c.rsql64_peddle_set_pc(machine, return_minus_one +% 1);
}

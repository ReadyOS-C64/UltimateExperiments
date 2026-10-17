const std = @import("std");
const c = @cImport({
    @cInclude("directory_bridge.h");
    @cInclude("bulk_model_api.h");
    @cInclude("host_input_model.h");
    @cInclude("cia_clock_model.h");
    @cInclude("graphics_color_model.h");
});
const a = std.testing.allocator;
const F = struct {
    m: *c.Dos64Machine,
    labels: []u8,
    s: std.StringHashMapUnmanaged(u16) = .empty,
    tick: u16 = 0,
    fn init() !F {
        const code = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/setup.prg", a, .limited(65538));
        defer a.free(code);
        var f = F{ .m = c.dos64_create() orelse return error.Create, .labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/setup.labels", a, .limited(200000)) };
        c.dos64_load(f.m, std.mem.readInt(u16, code[0..2], .little), code[2..].ptr, code.len - 2);
        var lines = std.mem.splitScalar(u8, f.labels, '\n');
        while (lines.next()) |line| {
            var t = std.mem.tokenizeAny(u8, line, " \r\t");
            if (!std.mem.eql(u8, t.next() orelse continue, "al")) continue;
            const address = t.next() orelse continue;
            const name = t.next() orelse continue;
            try f.s.put(a, name[1..], try std.fmt.parseInt(u16, address, 16));
        }
        c.dos64_uci_model_enable(f.m, 0xdf1c, 3, 0xc9);
        c.dos64_enable_reu(f.m);
        c.bulk_model_enable(f.m);
        c.dir_model_enable(f.m);
        _ = try f.call("runtime_init", 0);
        _ = try f.call("_bc_init", 0);
        var configs = [_]u8{0} ** 268;
        for (0..2) |i| {
            configs[i * 134] = 0xa5;
            configs[i * 134 + 1] = @intCast(i + 1);
            configs[i * 134 + 4] = 0x40;
            @memcpy(configs[i * 134 + 6 ..][0..11], "/usb1/Owned");
        }
        try f.put("_bc_config", &configs);
        return f;
    }
    fn loadFat(f: *F) !void {
        const fat = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/fat-overlay.bin", a, .limited(0x5000));
        defer a.free(fat);
        c.bulk_reu_seed(f.m, 0x3e8000, fat.ptr, @intCast(fat.len));
        try f.put("_nf_io_address", &.{ 0, 0x80, 0x3e, 0 });
        try f.word("_nf_io_buffer", 0x6000);
        try f.word("_nf_io_length", @intCast(fat.len));
        try f.put("_nf_io_direction", &.{1});
        _ = try f.call("_nf_dma", 0);
        try std.testing.expectEqual(@as(u8, 0), try f.byte("_nf_io_status", 0));
        for (fat, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_peek(f.m, 0x6000 + @as(u16, @intCast(i))));
    }
    fn deinit(f: *F) void {
        c.dos64_destroy(f.m);
        f.s.deinit(a);
        a.free(f.labels);
    }
    fn sym(f: *F, n: []const u8) !u16 {
        return f.s.get(n) orelse error.Symbol;
    }
    fn byte(f: *F, n: []const u8, offset: u16) !u8 {
        return c.dos64_peek(f.m, (try f.sym(n)) + offset);
    }
    fn put(f: *F, n: []const u8, bytes: []const u8) !void {
        c.dos64_load(f.m, try f.sym(n), bytes.ptr, bytes.len);
    }
    fn word(f: *F, n: []const u8, v: u16) !void {
        var bytes: [2]u8 = undefined;
        std.mem.writeInt(u16, &bytes, v, .little);
        try f.put(n, &bytes);
    }
    fn call(f: *F, n: []const u8, arg: u8) !u8 {
        const ret = (try f.sym("fixture_return")) -% 1;
        c.dos64_poke(f.m, 0x1ff, @truncate(ret >> 8));
        c.dos64_poke(f.m, 0x1fe, @truncate(ret));
        c.dos64_set_regs(f.m, .{ .pc = try f.sym(n), .sp = 0xfd, .a = arg, .x = 0x82, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
        const r = c.dos64_run(f.m, try f.sym("fixture_return"), if (std.mem.eql(u8, n, "_si_poll")) 250000000 else if (std.mem.eql(u8, n, "_so_prepare")) 5000000 else 12000000);
        try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
        try std.testing.expect(r.stack_high_water < 120);
        try std.testing.expectEqual(@as(u8, 0xff), try f.byte("sp", 0));
        try std.testing.expectEqual(@as(u8, 0xcf), try f.byte("sp", 1));
        return r.regs.a;
    }
    fn request(f: *F, first: u16, folders: u8) !void {
        var q = [_]u8{0} ** 135;
        q[0] = 0xa5;
        q[1] = 1;
        q[2] = folders;
        std.mem.writeInt(u16, q[3..5], first, .little);
        std.mem.writeInt(u16, q[5..7], 1000, .little);
        q[7] = '/';
        try f.put("_db_request", &q);
    }
    fn finish(f: *F) !void {
        for (0..100000) |_| {
            if (try f.byte("_db_result", 0) != 1) return;
            f.tick +%= 1;
            try f.word("_db_now", f.tick / 32);
            _ = try f.call("_db_poll", 0);
        }
        return error.PollBudget;
    }
    fn run(f: *F, first: u16, folders: u8) !void {
        try f.request(first, folders);
        try std.testing.expectEqual(@as(u8, 1), try f.call("_db_begin", 0));
        try f.finish();
    }
    fn page(f: *F) ![2216]u8 {
        const at = @as(u16, try f.byte("_db_page", 0)) | (@as(u16, try f.byte("_db_page", 1)) << 8);
        var data: [2216]u8 = undefined;
        for (&data, 0..) |*v, i| v.* = c.dos64_peek(f.m, at + @as(u16, @intCast(i)));
        return data;
    }
    fn filejob(f: *F, slot: u8, op: u8, mode: u8, path: []const u8) !void {
        try f.put("_bc_slot", &.{slot});
        var q = [_]u8{0} ** 142;
        q[0] = op;
        q[1] = mode;
        @memcpy(q[14..][0..path.len], path);
        try f.put("_br_request", &q);
        try std.testing.expectEqual(@as(u8, 1), try f.call("_bc_start", 0));
        for (0..10000) |_| {
            f.tick +%= 1;
            try f.word("_br_now", f.tick / 32);
            _ = try f.call("_bc_poll", 0);
            if (try f.byte("_bc_status", @as(u16, slot) * 29) != 1) return;
        }
        return error.FileBudget;
    }
};
fn boot(f: *F) !void {
    c.dos64_poke(f.m, 0, 0x2f);
    c.dos64_poke(f.m, 1, 0x35);
    c.native_runtime_control_enable(f.m);
    c.dos64_graphics_color_enable(f.m);
    c.dos64_cia_clock_enable(f.m);
    c.dos64_native_display_enable(f.m);
    c.dos64_host_input_model_enable(f.m);
    try std.testing.expectEqual(@as(u16, 0x080d), try f.sym("setup_boot"));
    c.dos64_set_regs(f.m, .{ .pc = 0x080d, .sp = 0xe0, .a = 0, .x = 0, .y = 0, .p = 0x24, .cycles = 0, .instructions = 0 });
    const r = c.dos64_run(f.m, try f.sym("setup_loop"), 12000000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
    try std.testing.expectEqual(try f.sym("setup_loop"), r.regs.pc);
    try std.testing.expectEqual(@as(u8, 1), try f.call("_rc_state", 0));
}
test "actual SYS bootstrap relocates HIGH and defaults output publication off" {
    var f = try F.init();
    defer f.deinit();
    try boot(&f);
    const run = try f.sym("__HIGH_CODE_RUN__");
    const load = try f.sym("__HIGH_CODE_LOAD__");
    const n = try f.sym("__HIGH_CODE_SIZE__");
    for (0..n) |i| try std.testing.expectEqual(c.dos64_peek(f.m, load + @as(u16, @intCast(i))), c.dos64_peek(f.m, run + @as(u16, @intCast(i))));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_rc_source_ready", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_rc_begin", 0));
}
test "actual coordinator startup closure and UI cancellation use one engine" {
    var f = try F.init();
    defer f.deinit();
    try boot(&f);
    c.dir_model_path(f.m, "/");
    var ui = false;
    for (0..3000) |_| {
        c.dos64_cia_clock_advance(f.m, 1024);
        _ = try f.call("_rc_poll", 0);
        if (try f.call("_rc_state", 0) == 2) {
            ui = true;
            break;
        }
    }
    try std.testing.expect(ui);
    var keys = [_]u8{0} ** 8;
    keys[7] = 128;
    c.dos64_host_input_model_keys(f.m, &keys);
    var terminal = false;
    for (0..3000) |_| {
        c.dos64_cia_clock_advance(f.m, 1024);
        _ = try f.call("_rc_poll", 0);
        if (try f.call("_rc_state", 0) == 5) {
            terminal = true;
            break;
        }
    }
    try std.testing.expect(terminal);
    _ = try f.call("_rc_poll", 0);
    try pane(&f, "SETUP STOPPED - ERROR 13", true);
    try std.testing.expectEqual(@as(u8, 0x13), try f.call("_rc_error", 0));
    try std.testing.expectEqual(@as(u8, 1), try f.call("_bc_files_closed", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_rc_source_ready", 0));
}
test "actual coordinator incoherent clock cannot authorize UI" {
    var f = try F.init();
    defer f.deinit();
    try boot(&f);
    c.dos64_cia_clock_step(f.m, 0x40000);
    var terminal = false;
    for (0..300) |_| {
        _ = try f.call("_rc_poll", 0);
        if (try f.call("_rc_state", 0) == 5) {
            terminal = true;
            break;
        }
    }
    try std.testing.expect(terminal);
    try std.testing.expectEqual(@as(u8, 0xe1), try f.call("_rc_error", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_rc_source_ready", 0));
}
test "compact native AUX code and terminal text are complete across five pages" {
    var f = try F.init();
    defer f.deinit();
    try boot(&f);
    try std.testing.expectEqual(@as(u16, 0xc000), try f.sym("dos64_uci_command"));
    try std.testing.expectEqual(@as(u16, 0xc0a0), try f.sym("dos64_uci_data"));
    try std.testing.expectEqual(@as(u16, 0xc2a0), try f.sym("dos64_uci_status"));
    try std.testing.expectEqual(@as(u16, 0xc3a0), try f.sym("dos64_uci_buffer_end"));
    const run = try f.sym("__AUX_CODE_RUN__");
    const load = try f.sym("__AUX_CODE_LOAD__");
    const n = (try f.sym("__AUX_CODE_SIZE__")) + (try f.sym("__AUX_RO_SIZE__"));
    try std.testing.expectEqual(@as(u16, 1086), n);
    for (0..n) |i| try std.testing.expectEqual(c.dos64_peek(f.m, load + @as(u16, @intCast(i))), c.dos64_peek(f.m, run + @as(u16, @intCast(i))));
}
test "compact native overcapacity request refuses before FPGA upload" {
    var f = try F.init();
    defer f.deinit();
    try f.put("dos64_uci_command", &.{ 1, 3 });
    try f.word("dos64_uci_command_len", 2);
    try f.word("dos64_uci_data_capacity", 513);
    _ = try f.call("dos64_uci_start", 0);
    try std.testing.expectEqual(@as(u8, 1), try f.byte("dos64_uci_error", 0));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_uci_model_count(f.m, 0));
    try std.testing.expectEqual(@as(u64, 0), c.dos64_uci_model_count(f.m, 6));
}

fn prepareUi(f: *F) !void {
    try boot(f);
    c.dir_model_path(f.m, "/");
    for (0..3000) |_| {
        c.dos64_cia_clock_advance(f.m, 1024);
        _ = try f.call("_rc_poll", 0);
        const state = try f.call("_rc_state", 0);
        if (state == 2) return;
        try std.testing.expectEqual(@as(u8, 1), state);
    }
    return error.UIBudget;
}
fn pane(f: *F, title: []const u8, closed: bool) !void {
    const rows = [_][]const u8{ title, "NEW FILES MAY REMAIN IN THE HOME FOLDER.", if (closed) "FILES CLOSED." else "FILE CLEANUP NOT CONFIRMED.", if (closed) "RELOAD SETUP; CHOOSE A NEW FOLDER." else "KEEP THIS SCREEN. DO NOT RETRY." };
    for (rows, 0..) |row, y| for (0..40) |x| {
        const expected: u8 = if (x >= row.len) 32 else if (row[x] >= 65 and row[x] <= 90) row[x] - 64 else row[x];
        try std.testing.expectEqual(expected, c.dos64_peek(f.m, @intCast(0x748 + y * 40 + x)));
        try std.testing.expectEqual(@as(u8, 1), c.dos64_graphics_color_peek(f.m, @intCast(0xdb48 + y * 40 + x)));
    };
}
test "initial relocation bytes retire only after whole-span CRC and UI cache commit" {
    var f = try F.init();
    defer f.deinit();
    const high = try f.sym("__HIGH_CODE_RUN__");
    const hn = try f.sym("__HIGH_CODE_SIZE__");
    const aux = try f.sym("__AUX_CODE_RUN__");
    const an = (try f.sym("__AUX_CODE_SIZE__")) + (try f.sym("__AUX_RO_SIZE__"));
    const code = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/setup.prg", a, .limited(65538));
    defer a.free(code);
    const core = (try f.sym("__UI_CODE_SIZE__")) + (try f.sym("__UI_RO_SIZE__"));
    try std.testing.expectEqual((try f.sym("__HIGH_CODE_LOAD__")), try f.sym("__UIBSS_RUN__"));
    try prepareUi(&f);
    for (0..0x5000) |i| try std.testing.expectEqual(if (i < core) code[2 + 0x6000 - 0x0801 + i] else @as(u8, 0), c.dos64_reu_peek(f.m, 0x3e0000 + @as(u32, @intCast(i))));
    for (0..hn) |i| try std.testing.expectEqual(code[2 + (try f.sym("__HIGH_CODE_LOAD__")) - 0x0801 + i], c.dos64_peek(f.m, high + @as(u16, @intCast(i))));
    for (0..an) |i| try std.testing.expectEqual(code[2 + (try f.sym("__AUX_CODE_LOAD__")) - 0x0801 + i], c.dos64_peek(f.m, aux + @as(u16, @intCast(i))));
    try std.testing.expectEqual(@as(u8, 1), try f.byte("phase_verified", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_sl_install", 0));
    for (0..hn) |i| try std.testing.expectEqual(code[2 + (try f.sym("__HIGH_CODE_LOAD__")) - 0x0801 + i], c.dos64_peek(f.m, high + @as(u16, @intCast(i))));
}
test "full initial CRC still rejects retired source regions before any terminal renderer" {
    for ([_][]const u8{ "rc_failed_common", "retire", "__UI_RO_RUN__" }) |name| {
        var f = try F.init();
        defer f.deinit();
        // The first UI_RO bytes are the bootstrap relocation descriptor.
        // Select a later UI-only string, which startup cannot consult.
        const run = if (std.mem.eql(u8, name, "__UI_RO_RUN__")) (try f.sym(name)) + 64 else try f.sym(name);
        const at: u16 = if (run >= 0xc3a0 and run < 0xc800) (try f.sym("__AUX_CODE_LOAD__")) + run - (try f.sym("__AUX_CODE_RUN__")) else if (run >= 0xf700) (try f.sym("__HIGH_CODE_LOAD__")) + run - (try f.sym("__HIGH_CODE_RUN__")) else run;
        // Each location is immutable source but is not executed before full CRC.
        const changed: u16 = at;
        c.dos64_poke(f.m, changed, c.dos64_peek(f.m, changed) ^ 1);
        try boot(&f);
        c.dir_model_path(f.m, "/");
        var failed = false;
        for (0..3000) |_| {
            c.dos64_cia_clock_advance(f.m, 1024);
            _ = try f.call("_rc_poll", 0);
            if (try f.call("_rc_state", 0) == 5) {
                failed = true;
                break;
            }
        }
        try std.testing.expect(failed);
        try std.testing.expectEqual(@as(u8, 0), try f.byte("phase_verified", 0));
        var before: [160]u8 = undefined;
        for (&before, 0..) |*v, i| v.* = c.dos64_peek(f.m, 0x748 + @as(u16, @intCast(i)));
        _ = try f.call("_rc_poll", 0);
        for (before, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_peek(f.m, 0x748 + @as(u16, @intCast(i))));
    }
}
test "terminal presenter reports open native FILES truth and never closes retries or rearms" {
    var f = try F.init();
    defer f.deinit();
    try prepareUi(&f);
    for (0..3000) |_| {
        if (try f.call("_db_state", 0) != 1) break;
        c.dos64_cia_clock_advance(f.m, 1024);
        _ = try f.call("_rc_poll", 0);
    }
    // SYS reinitializes ownership; authorize this component-test source only
    // after the directory operation has released the shared engine.
    var source = [_]u8{0} ** 134;
    source[0] = 0xa5;
    source[1] = 1;
    source[4] = 0x40;
    @memcpy(source[6..][0..11], "/usb1/Owned");
    try f.put("_bc_config", &source);
    c.bulk_model_seed(f.m, "/usb1/Owned/SRC.BIN", "data".ptr, 4);
    try f.filejob(0, 2, 1, "/usb1/Owned/SRC.BIN");
    try std.testing.expectEqual(@as(u8, 1), c.bulk_model_open(f.m, 1));
    _ = try f.call("fail", 0xe4);
    try std.testing.expectEqual(@as(u8, 5), try f.call("_rc_state", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.byte("failure_closed", 0));
    const commands = c.bulk_model_commands(f.m);
    var counters: [7]u64 = undefined;
    for (&counters, 0..) |*v, i| v.* = c.dos64_uci_model_count(f.m, @intCast(i));
    try f.put("_so_result", &.{ 2, 1, 0 });
    try f.put("_br_result", &.{ 2, 0, 0 });
    _ = try f.call("_rc_poll", 0);
    try pane(&f, "SETUP STOPPED - ERROR E4", false);
    var before: [160]u8 = undefined;
    for (&before, 0..) |*v, i| v.* = c.dos64_peek(f.m, 0x748 + @as(u16, @intCast(i)));
    for (0..8) |_| _ = try f.call("_rc_poll", 0);
    for (before, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_peek(f.m, 0x748 + @as(u16, @intCast(i))));
    try std.testing.expectEqual(@as(u8, 0xe4), try f.call("_rc_error", 0));
    try std.testing.expectEqual(@as(u8, 0), try f.call("_rc_begin", 0));
    try std.testing.expectEqual(commands, c.bulk_model_commands(f.m));
    for (counters, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_uci_model_count(f.m, @intCast(i)));
    try std.testing.expectEqual(@as(u8, 1), c.bulk_model_open(f.m, 1));
}

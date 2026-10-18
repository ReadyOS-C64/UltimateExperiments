const std = @import("std");
const c = @cImport({
    @cInclude("peddle_bridge.h");
    @cInclude("bulk_model_api.h");
    @cInclude("uci_model.h");
    @cInclude("cia_clock_model.h");
    @cInclude("host_input_model.h");
    @cInclude("native_display_model.h");
});
extern fn native_runtime_control_enable(?*anyopaque) void;
const a = std.testing.allocator;
const F = struct {
    m: *c.Dos64Machine,
    labels: []u8,
    s: std.StringHashMapUnmanaged(u16) = .empty,
    fn sym(f: *F, n: []const u8) !u16 {
        return f.s.get(n) orelse error.Symbol;
    }
    fn get(f: *F, n: []const u8) !u8 {
        return c.dos64_peek(f.m, try f.sym(n));
    }
    fn put(f: *F, n: []const u8, v: u8) !void {
        c.dos64_poke(f.m, try f.sym(n), v);
    }
    fn bytes(f: *F, n: []const u8, b: []const u8) !void {
        c.dos64_load(f.m, try f.sym(n), b.ptr, b.len);
    }
    fn call(f: *F, n: []const u8) !void {
        const entry=try f.sym(n);
        inline for (.{"UNITEXTRA","UNITTAIL"}) |prefix| {
            if (f.s.get("__" ++ prefix ++ "_RUN__")) |start| {
                const count=f.s.get("__" ++ prefix ++ "_SIZE__") orelse 0;
                if (entry>=start and @as(u32,entry)<@as(u32,start)+count) return error.DiscardedUnitFixture;
            }
        }
        const before = c.dos64_get_regs(f.m).cycles;
        const ret = (try f.sym("fixture_return")) -% 1;
        c.dos64_poke(f.m, 0x1ff, @truncate(ret >> 8));
        c.dos64_poke(f.m, 0x1fe, @truncate(ret));
        c.dos64_set_regs(f.m, .{ .pc = try f.sym(n), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
        const r = c.dos64_run(f.m, try f.sym("fixture_return"), 2000000);
        try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
        try std.testing.expectEqual(@as(u8, 0xff), r.regs.sp);
        c.dos64_cia_clock_advance(f.m, @intCast((r.regs.cycles - before) / 64));
    }
    fn file(f: *F, op: u8) !void {
        try f.put("dos64_files_op", op);
        try f.call("dos64_elapsed_poll");
        const from = try f.sym("dos64_elapsed_now");
        const to = try f.sym("dos64_files_now");
        c.dos64_poke(f.m, to, c.dos64_peek(f.m, from));
        c.dos64_poke(f.m, to + 1, c.dos64_peek(f.m, from + 1));
        try f.call("dos64_overlay_files_start");
        for (0..5000) |_| {
            if (try f.get("dos64_files_state") != 1) break;
            try f.call("dos64_elapsed_poll");
            c.dos64_poke(f.m, to, c.dos64_peek(f.m, from));
            c.dos64_poke(f.m, to + 1, c.dos64_peek(f.m, from + 1));
            try f.call("dos64_overlay_files_poll");
        }
        try std.testing.expectEqual(@as(u8, 2), try f.get("dos64_files_state"));
    }
    fn init() !F {
        const code = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "work/build/dos64-tests.prg", a, .limited(65538));
        defer a.free(code);
        var f = F{ .m = c.dos64_create() orelse return error.Create, .labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "work/build/dos64-tests.labels", a, .limited(200000)) };
        errdefer f.deinit();
        c.dos64_load(f.m, std.mem.readInt(u16, code[0..2], .little), code[2..].ptr, code.len - 2);
        var lines = std.mem.splitScalar(u8, f.labels, '\n');
        while (lines.next()) |line| {
            var t = std.mem.tokenizeAny(u8, line, " \r\t");
            if (!std.mem.eql(u8, t.next() orelse continue, "al")) continue;
            const addr = t.next() orelse continue;
            const name = t.next() orelse continue;
            try f.s.put(a, name[1..], try std.fmt.parseInt(u16, addr, 16));
        }
        c.dos64_enable_reu(f.m);
        c.dos64_cia_clock_enable(f.m);
        c.dos64_native_display_enable(f.m);
        c.dos64_host_input_model_enable(f.m);
        native_runtime_control_enable(f.m);
        c.dos64_uci_model_enable(f.m, 0xdf1c, 3, 0xc9);
        c.bulk_model_enable(f.m);
        c.dos64_cia_clock_step(f.m, 1);
        c.dos64_poke(f.m, 0, 0x2f);
        c.dos64_poke(f.m, 1, 0x35);
        try f.call("dos64_overlay_init");
        try f.put("dos64_overlay_reu_mib", 4);
        try f.call("dos64_overlay_bootstrap");
        try f.call("dos64_cpu_init");
        try f.put("dos64_cache_limit", 32);
        try f.call("dos64_cache_init");
        try f.call("dos64_disk_init");
        try f.call("dos64_uci_init");
        try f.call("dos64_overlay_files_init");
        try f.put("dos64_host_clock_claim", 0xa5);
        try f.call("dos64_host_clock_init");
        try f.call("dos64_elapsed_poll");
        const hd = try a.alloc(u8, 2097152);
        defer a.free(hd);
        for (hd, 0..) |*v, i| v.* = @truncate(i * 37 ^ (i >> 17));
        c.bulk_model_seed(f.m, "/usb1/Owned/C.IMG", hd.ptr, @intCast(hd.len));
        try f.put("dos64_files_target", 2);
        try f.put("dos64_files_mode", 3);
        const path = "/usb1/Owned/C.IMG\x00";
        try f.put("dos64_files_path_len", path.len);
        c.dos64_load(f.m, (try f.sym("dos64_uci_command")) + 3, path.ptr, path.len);
        try f.file(2);
        try f.put("hdc_target", 2);
        try f.put("hd_profile", 0);
        try f.put("hd_slots", 2);
        try f.put("hd_readonly", 0);
        try f.call("hdb_mount");
        try f.bytes("dos64_files_offset", &.{ 0x39, 0x30, 0, 0 });
        try f.file(6);
        try f.call("dos64_cache_flush");
        try f.put("dos64_disk_loaded", 1);
        try f.bytes("dos64_disk_reu_base", &.{ 0, 0, 0x10 });
        try f.bytes("dos64_disk_sectors", &.{ 0xd0, 2 });
        try f.put("dos64_native_diag", 5);
        c.dos64_poke(f.m, (try f.sym("dos64_native_diag")) + 3, 7);
        try f.put("dos64_export_owned", 0xa5);
        try f.put("dos64_export_paused", 0xa5);
        try f.put("dos64_export_bank", 0x10);
        const output = "/usb1/Owned/OUT.IMG\x00";
        try f.put("dos64_export_path_len", output.len);
        try f.bytes("dos64_export_path", output);
        return f;
    }
    fn snapshot(f: *F) ![25]u8 {
        var b: [25]u8 = undefined;
        const at = try f.sym("dos64_files_state_start");
        for (&b, 0..) |*v, i| v.* = c.dos64_peek(f.m, at + @as(u16, @intCast(i)));
        return b;
    }
    fn deinit(f: *F) void {
        c.dos64_destroy(f.m);
        f.s.deinit(a);
        a.free(f.labels);
    }
};
test "actual native_tick sequential cancel resets only new admitted job and preserves next cancel" {
    var f = try F.init();
    defer f.deinit();
    const before = try f.snapshot();
    try f.call("dos64_native_tick");
    try std.testing.expectEqual(@as(u8, 1), try f.get("sav_context_pending"));
    c.dos64_poke(f.m, (try f.sym("dos64_native_diag")) + 3, 9);
    for (0..1000) |_| {
        if (try f.get("sav_borrowed") == 0) break;
        try f.call("dos64_native_tick");
    }
    try std.testing.expectEqual(@as(u8, 0), try f.get("sav_borrowed"));
    try std.testing.expectEqualSlices(u8, &before, &try f.snapshot());
    try std.testing.expectEqual(@as(u8, 1), try f.get("hdb_online"));
    try std.testing.expectEqual(@as(u8, 1), c.bulk_model_open(f.m, 2));
    try std.testing.expectEqual(@as(u8, 0), c.bulk_model_open(f.m, 1));
    try std.testing.expectEqual(@as(u32, 3), c.bulk_model_commands(f.m));
    // A fresh accepted job clears the prior flag, but a new command9 survives.
    const second = "/usb1/Owned/SECOND.IMG\x00";
    try f.put("dos64_export_path_len", second.len);
    try f.bytes("dos64_export_path", second);
    c.dos64_poke(f.m, (try f.sym("dos64_native_diag")) + 3, 7);
    try f.call("dos64_native_tick");
    try std.testing.expectEqual(@as(u8, 0), try f.get("dos64_export_cancel"));
    c.dos64_poke(f.m, (try f.sym("dos64_native_diag")) + 3, 9);
    for (0..1000) |_| {
        if (try f.get("sav_borrowed") == 0) break;
        try f.call("dos64_native_tick");
    }
    try std.testing.expectEqual(@as(u8, 1), try f.get("dos64_export_cancel"));
    try std.testing.expectEqualSlices(u8, &before, &try f.snapshot());
    try std.testing.expectEqual(@as(u32, 4), c.bulk_model_commands(f.m));
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.bulk_model_size(f.m, "/usb1/Owned/SECOND.IMG"));
}
test "actual native_tick first close status survives later clock loss and retains blocked C snapshot" {
    var f = try F.init();
    defer f.deinit();
    const before = try f.snapshot();
    c.bulk_model_faults(f.m, 3, -1, -1, 0, -1);
    try f.call("dos64_native_tick");
    for (0..200) |_| {
        try f.call("dos64_native_tick");
        if (try f.get("dos64_files_error") != 0) break;
    }
    try std.testing.expectEqual(@as(u8, 3), try f.get("dos64_files_error"));
    try f.put("dos64_host_clock_claim", 0);
    c.dos64_poke(f.m, (try f.sym("dos64_native_diag")) + 3, 9);
    for (0..256) |_| {
        if (try f.get("sav_borrowed") == 0) break;
        try f.call("dos64_native_tick");
    }
    try std.testing.expectEqual(@as(u8, 5), try f.get("sav_error"));
    try std.testing.expectEqual(@as(u8, 1), try f.get("sav_context_pending"));
    try std.testing.expectEqual(@as(u8, 0), try f.get("hdb_online"));
    const at = try f.sym("sav_context_snapshot");
    for (before, 0..) |v, i| try std.testing.expectEqual(v, c.dos64_peek(f.m, at + @as(u16, @intCast(i))));
    try std.testing.expectEqual(@as(u8, 1), c.bulk_model_open(f.m, 2));
}

test "actual native_tick B third arena CRC full output preserves C and dirty readonly policy" {
    var f = try F.init();
    defer f.deinit();
    const before = try f.snapshot();
    const data = try a.alloc(u8, 368640);
    defer a.free(data);
    for (data, 0..) |*v, i| v.* = @truncate((i * 19 + (i >> 9)) ^ 0xa7);
    c.bulk_reu_seed(f.m, 0x380000, data.ptr, @intCast(data.len));
    try f.bytes("dos64_disk_b_descriptor", &.{ 0, 0, 0x38, 0xd0, 2, 40, 0, 2, 9, 1 });
    try f.put("sav_drive", 1);
    try f.put("dos64_export_bank", 0x38);
    const ro = try f.sym("dos64_disk_readonly");
    const dirty = try f.sym("dos64_disk_dirty");
    c.dos64_poke(f.m, ro + 1, 1);
    c.dos64_poke(f.m, dirty + 1, 0);
    try f.call("dos64_native_tick");
    try std.testing.expectEqual(@as(u8, 1), try f.get("sav_selected_drive"));
    for (0..250000) |_| {
        if (try f.get("sav_borrowed") == 0) break;
        try f.call("dos64_native_tick");
    }
    try std.testing.expectEqual(@as(u8, 0), try f.get("sav_borrowed"));
    try std.testing.expectEqual(@as(u8, 0), try f.get("sav_error"));
    try std.testing.expectEqual(@as(u8, 0xa5), c.dos64_peek(f.m, (try f.sym("dos64_native_diag")) + 4));
    try std.testing.expectEqual(@as(u8, 1), try f.get("dos64_export_verified"));
    const crc_at = try f.sym("dos64_export_crc_raw");
    var raw: [4]u8 = undefined;
    for (&raw, 0..) |*v, i| v.* = c.dos64_peek(f.m, crc_at + @as(u16, @intCast(i)));
    try std.testing.expectEqual(std.hash.Crc32.hash(data), std.mem.readInt(u32, &raw, .little) ^ 0xffffffff);
    const out = try a.alloc(u8, data.len);
    defer a.free(out);
    try std.testing.expectEqual(@as(u8, 1), c.bulk_model_read(f.m, "/usb1/Owned/OUT.IMG", out.ptr, @intCast(out.len)));
    try std.testing.expectEqualSlices(u8, data, out);
    try std.testing.expectEqualSlices(u8, &before, &try f.snapshot());
    try std.testing.expectEqual(@as(u8, 1), c.dos64_peek(f.m, ro + 1));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_peek(f.m, dirty + 1));
}

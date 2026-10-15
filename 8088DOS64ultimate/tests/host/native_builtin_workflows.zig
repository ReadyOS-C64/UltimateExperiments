const std = @import("std");
const host = @import("machine.zig");
const c = host.c;
const Fixture = host.Fixture;
const model = @cImport({
    @cInclude("image_import_model.h");
    @cInclude("host_input_model.h");
});
const alloc = std.testing.allocator;
const source_path = "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img";
const Stage = enum { date, time, prompt, workflow, done };
const Screen = struct {
    mode: u8,
    columns: u16,
    page: u8,
    row: u8,
    column: u8,
    text: [2025]u8 = @splat(' '),
    fn line(self: *const Screen, r: usize) []const u8 {
        return self.text[r * 81 ..][0..self.columns];
    }
    fn contains(self: *const Screen, s: []const u8) bool {
        return std.mem.indexOf(u8, &self.text, s) != null;
    }
    fn prompt(self: *const Screen) bool {
        return self.column == 2 and std.mem.eql(u8, std.mem.trim(u8, self.line(self.row), " "), "A>");
    }
};
const Observation = struct { stage: Stage, instructions: u32, screen: Screen, native_bitmap_sha256: [64]u8 };
fn sha(data: []const u8) [64]u8 {
    var digest: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(data, &digest, .{});
    return std.fmt.bytesToHex(digest, .lower);
}
fn word(b: []const u8, at: usize) u16 {
    return std.mem.readInt(u16, b[at..][0..2], .little);
}
const Lane = struct {
    f: Fixture,
    diag: u16,
    counter: u16,
    guest: u16,
    stage: Stage = .date,
    mode_lane: bool = false,
    step: usize = 0,
    pending: []const u8 = "",
    pending_offset: usize = 0,
    submitted_at: u32 = 0,
    seen_output: bool = false,
    config_line_mask: u8 = 0,
    initial_prompt: bool = false,
    observations: std.array_list.Managed(Observation),
    inputs: std.array_list.Managed(u16),
    native_cycles: u64 = 0,
    cpu_ticks: u32 = 0,
    startup_polls: u32 = 0,
    command_calls: u32 = 0,
    max_tick_cycles: u64 = 0,
    max_snapshot_cycles: u64 = 0,
    phi2_remainder: u64 = 0,
    runtime_clock: bool = false,
    fn init() !Lane {
        var f = try Fixture.init();
        errdefer f.deinit();
        return .{ .diag = try f.symbol("dos64_native_diag"), .counter = try f.symbol("dos64_cpu_instructions"), .guest = try f.symbol("dos64_guest"), .f = f, .observations = .init(alloc), .inputs = .init(alloc) };
    }
    fn deinit(self: *Lane) void {
        self.observations.deinit();
        self.inputs.deinit();
        self.f.deinit();
    }
    fn state(self: *const Lane) u8 {
        return self.f.peek(self.diag);
    }
    fn count(self: *const Lane) u32 {
        return @as(u32, self.f.word(self.counter)) | (@as(u32, self.f.word(self.counter + 2)) << 16);
    }
    fn diagnostics(self: *Lane) void {
        var d: [19]u8 = undefined;
        for (&d, 0..) |*v, i| v.* = self.f.peek(self.diag + @as(u16, @intCast(i)));
        std.debug.print("native DOS first divergence: stage={s}, mailbox={x}, guest={x:0>4}:{x:0>4}, instructions={d}, ticks={d}, cycles={d}\n", .{ @tagName(self.stage), d, self.f.word(self.guest + 18), self.f.word(self.guest + 24), self.count(), self.cpu_ticks, self.native_cycles });
    }
    fn call(self: *Lane, name: []const u8, budget: u64) !void {
        const before = c.dos64_get_regs(self.f.machine).cycles;
        const cmd = self.f.peek(self.diag + 3);
        const r = self.f.call(name, budget) catch |err| {
            self.diagnostics();
            return err;
        };
        const elapsed = r.cycles - before;
        self.native_cycles += elapsed;
        if (self.runtime_clock) {
            // Explicit functional64:1 nativeCPU/phi2 ratio, excluding DMA stalls.
            // This is NOT physical64MHz timing/throughput evidence. Keep the
            // sub-tick remainder across every native call, including snapshots.
            self.phi2_remainder += elapsed;
            c.dos64_cia_clock_advance(self.f.machine, @intCast(self.phi2_remainder / 64));
            self.phi2_remainder %= 64;
            if (cmd == 2) self.max_snapshot_cycles = @max(self.max_snapshot_cycles, elapsed) else self.max_tick_cycles = @max(self.max_tick_cycles, elapsed);
        }
        if ((r.p & 1) != 0 or self.state() == 0xe1) {
            self.diagnostics();
            return error.NativeRuntimeFailure;
        }
        if (self.native_cycles > 18_000_000_000 or self.count() > 4_000_000) {
            self.diagnostics();
            return error.NativeDosBudget;
        }
    }
    fn command(self: *Lane, cmd: u8) !void {
        if (self.f.peek(self.diag + 3) != 0) return error.OutstandingNativeCommand;
        self.f.poke(self.diag + 4, 0);
        self.f.poke(self.diag + 3, cmd);
        self.command_calls += 1;
        // Resume may defer at the documented CIA reload exclusion. Keep the
        // original command pending and poll a fixed bound; call advances the
        // independent functional CIA clock using the observed native cost.
        for (0..256) |_| {
            try self.call("dos64_native_tick", if (cmd == 2) 3_000_000 else if (self.mode_lane) 8_000_000 else 5_000_000);
            if (self.f.peek(self.diag + 3) == 0) break;
        }
        if (self.f.peek(self.diag + 3) != 0 or self.f.peek(self.diag + 4) != 0xa5) {
            self.diagnostics();
            return error.NativeCommandRejected;
        }
    }
    fn read(self: *Lane, address: u32, dest: []u8) !void {
        if (self.state() != 5) return error.ReadRequiresCoherentPause;
        var offset: usize = 0;
        while (offset < dest.len) {
            const far = address + @as(u32, @intCast(offset));
            const length = @min(@min(dest.len - offset, 2048), 65536 - (far & 65535));
            for (0..3) |i| self.f.poke(self.diag + 14 + @as(u16, @intCast(i)), @truncate(far >> @as(u5, @intCast(i * 8))));
            self.f.poke(self.diag + 17, @truncate(length));
            self.f.poke(self.diag + 18, @truncate(length >> 8));
            try self.command(4);
            for (0..length) |i| dest[offset + i] = self.f.peek(0xc100 + @as(u16, @intCast(i)));
            offset += length;
        }
    }
    fn screen(self: *Lane) !Screen {
        const before = self.count();
        try self.command(2);
        try std.testing.expectEqual(before, self.count());
        try std.testing.expectEqual(@as(u8, 5), self.state());
        var bda: [256]u8 = undefined;
        try self.read(0x400, &bda);
        const cols = word(&bda, 0x4a);
        const page = bda[0x62];
        const size = word(&bda, 0x4c);
        const offset = word(&bda, 0x4e);
        if (bda[0x49] > 3 or (cols != 40 and cols != 80) or page >= @as(u8, if (cols == 80) 4 else 8) or size != @as(u16, if (cols == 80) 4096 else 2048) or offset != @as(u16, page) * size) return error.InvalidGuestTextGeometry;
        const cursor = word(&bda, 0x50 + @as(usize, page) * 2);
        if (cursor >> 8 >= 25 or cursor & 255 >= cols) return error.InvalidGuestTextCursor;
        var video: [4000]u8 = undefined;
        try self.read(0xb8000 + @as(u32, offset), video[0 .. @as(usize, cols) * 50]);
        var result = Screen{ .mode = bda[0x49], .columns = cols, .page = page, .row = @intCast(cursor >> 8), .column = @truncate(cursor) };
        for (0..25) |row| {
            for (0..cols) |col| {
                const v = video[(row * cols + col) * 2];
                result.text[row * 81 + col] = if (v >= 32 and v < 127) v else '?';
            }
            result.text[row * 81 + 80] = '\n';
        }
        var bitmap: [8000]u8 = undefined;
        for (&bitmap, 0..) |*v, i| v.* = self.f.peek(0x6000 + @as(u16, @intCast(i)));
        try self.observations.append(.{ .stage = self.stage, .instructions = self.count(), .screen = result, .native_bitmap_sha256 = sha(&bitmap) });
        return result;
    }
    fn typeKeys(self: *Lane, text: []const u8) !void {
        for (text) |ascii| {
            const scan: u8 = scanCode(ascii) orelse return error.UnsupportedScriptKey;
            const key = (@as(u16, scan) << 8) | ascii;
            self.f.poke(self.diag + 5, ascii);
            self.f.poke(self.diag + 6, scan);
            try self.command(1);
            try self.inputs.append(key);
        }
    }
    fn captureDisk(self: *Lane, name: []const u8) !void {
        if (self.state() != 5) return error.CaptureRequiresCoherentPause;
        const disk = try alloc.alloc(u8, 368640);
        defer alloc.free(disk);
        for (disk, 0..) |*v, i| v.* = c.dos64_reu_peek(self.f.machine, 0x100000 + @as(u32, @intCast(i)));
        const path = try std.fmt.allocPrint(alloc, "build/{s}-{s}.img", .{ if (self.mode_lane) "mode" else "workflow", name });
        defer alloc.free(path);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = path, .data = disk });
    }
    fn bitmapOracle(self: *Lane, expected_columns: u16) !void {
        var bda: [256]u8 = undefined;
        try self.read(0x400, &bda);
        try std.testing.expectEqual(expected_columns, word(&bda, 0x4a));
        try std.testing.expectEqual(@as(u8, if (expected_columns == 40) 1 else 3), bda[0x49]);
        var vram: [4000]u8 = undefined;
        try self.read(0xb8000 + @as(u32, word(&bda, 0x4e)), vram[0 .. expected_columns * 50]);
        const full = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "assets/native-text/cp437-unscii8.bin", alloc, .limited(2049));
        defer alloc.free(full);
        const narrow = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "assets/native-text/cp437-narrow4x8.bin", alloc, .limited(1025));
        defer alloc.free(narrow);
        var bitmap: [8000]u8 = undefined;
        for (0..25) |row| for (0..40) |cell| {
            const left = (row * expected_columns + cell * (if (expected_columns == 40) @as(usize, 1) else 2)) * 2;
            const attr = vram[left + 1];
            const bg = (attr >> 4) & 7;
            const fg = attr & 15;
            const colors = [16]u8{ 0, 6, 5, 3, 2, 4, 9, 15, 12, 14, 13, 3, 10, 4, 7, 1 };
            try std.testing.expectEqual((colors[fg] << 4) | colors[bg], self.f.peek(@intCast(0x4000 + row * 40 + cell)));
            for (0..8) |y| {
                const expected = if (expected_columns == 40) full[@as(usize, vram[left]) * 8 + y] else nibble(narrow, vram[left], y) * 16 + nibble(narrow, vram[left + 2], y);
                const at = row * 320 + cell * 8 + y;
                bitmap[at] = self.f.peek(@intCast(0x6000 + at));
                try std.testing.expectEqual(expected, bitmap[at]);
            }
        };
        const path = try std.fmt.allocPrint(alloc, "build/mode-{d}-bitmap.bin", .{expected_columns});
        defer alloc.free(path);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = path, .data = &bitmap });
    }
    fn observe(self: *Lane) !void {
        const screen_value = try self.screen();
        const sc = &screen_value;
        if (self.stage == .date and sc.contains("Enter new date (mm-dd-yy):")) {
            try self.command(3);
            try self.typeKeys("\r");
            self.stage = .time;
            return;
        } else if (self.stage == .time and sc.contains("Enter new time:")) {
            try self.command(3);
            try self.typeKeys("\r");
            self.stage = .prompt;
            return;
        } else if (self.stage == .prompt and sc.prompt()) {
            self.initial_prompt = true;
            try self.captureDisk("boot");
            self.stage = .workflow;
            self.pending = self.commands()[0];
        } else if (self.stage == .workflow) {
            if (self.pending_offset == self.pending.len and self.count() > self.submitted_at and sc.prompt()) {
                if (!self.mode_lane) {
                    if (self.step == 3 or self.step == 5) try std.testing.expectEqual(@as(u8, 15), self.config_line_mask);
                    if (self.step == 6 or self.step == 8) try std.testing.expect(self.seen_output);
                    const name = try std.fmt.allocPrint(alloc, "step-{d}", .{self.step});
                    defer alloc.free(name);
                    try self.captureDisk(name);
                } else try self.bitmapOracle(if (self.step == 0) 40 else 80);
                self.step += 1;
                self.pending_offset = 0;
                self.seen_output = false;
                self.config_line_mask = 0;
                if (self.step == self.commands().len) {
                    self.stage = .done;
                    return;
                }
                self.pending = self.commands()[self.step];
            }
            if (!self.mode_lane and (self.step == 3 or self.step == 5)) {
                const expected = [_][]const u8{ "c:", "device=c:\\dos\\ansi.sys", "files=25", "buffers=25" };
                for (0..25) |row| for (expected, 0..) |line, i| if (std.mem.eql(u8, std.mem.trim(u8, sc.line(row), " "), line)) {
                    self.config_line_mask |= @as(u8, 1) << @as(u3, @intCast(i));
                };
            }
            if (!self.mode_lane and (self.step == 6 or self.step == 8)) {
                const expected = if (self.step == 6) "D64EXISTS" else "File not found";
                for (0..25) |row| if (std.mem.eql(u8, std.mem.trim(u8, sc.line(row), " "), expected)) {
                    self.seen_output = true;
                };
            }
        }
        if (self.stage != .done) {
            try self.command(3);
            if (self.stage == .workflow and self.pending_offset < self.pending.len) {
                // Hardware-shaped 15-key ring: fill only available slots, preserving
                // scan/ASCII words and allowing genuine DOS to consume long commands.
                var bda: [256]u8 = undefined;
                // Snapshot is paused; reading head/tail occurred in screen. Access
                // coherent REU copy through SNAPSHOT rather than stale cache bytes.
                try self.command(2);
                try self.read(0x400, &bda);
                try self.command(3);
                const head = word(&bda, 0x1a);
                const tail = word(&bda, 0x1c);
                const used = ((tail + 32 - head) % 32) / 2;
                const n = @min(self.pending.len - self.pending_offset, 15 - used);
                if (n > 0) {
                    try self.typeKeys(self.pending[self.pending_offset..][0..n]);
                    self.pending_offset += n;
                    self.submitted_at = self.count();
                }
            }
        }
    }
    fn commands(self: *const Lane) []const []const u8 {
        return if (self.mode_lane) &mode_commands else &storage_commands;
    }
    fn report(self: *Lane, status: []const u8, source: []const u8) !void {
        const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.prg", alloc, .limited(65538));
        defer alloc.free(prg);
        var guest_regs: [28]u8 = undefined;
        for (&guest_regs, 0..) |*v, i| v.* = self.f.peek(self.guest + @as(u16, @intCast(i)));
        const output = try std.json.Stringify.valueAlloc(alloc, .{ .status = status, .guest_regs = guest_regs, .cpu_opcode = self.f.peek(try self.f.symbol("dos64_cpu_opcode")), .cpu_status = self.f.peek(try self.f.symbol("dos64_cpu_status")), .io_port = self.f.word(try self.f.symbol("dos64_io_port")), .io_value = self.f.word(try self.f.symbol("dos64_io_value")), .video_host_error = self.f.peek(try self.f.symbol("dos64_video_host_error")), .source_sha256 = sha(source), .linked_prg_sha256 = sha(prg), .mode_lane = self.mode_lane, .commands = self.commands(), .completed_commands = self.step, .pending_offset = self.pending_offset, .guest_instructions = self.count(), .native_cpu_cycles = self.native_cycles, .native_ticks = self.cpu_ticks, .startup_polls = self.startup_polls, .maximum_tick_cycles = self.max_tick_cycles, .maximum_snapshot_cycles = self.max_snapshot_cycles, .inputs = self.inputs.items, .observations = self.observations.items, .clock_model = "functional64:1, DMA stalls excluded; no physical timing", .no_direct_cpu_steps_or_DOS_shortcuts = true }, .{ .whitespace = .indent_2 });
        defer alloc.free(output);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = if (self.mode_lane) "build/native-mode-workflow.json" else "build/native-storage-workflow.json", .data = output });
    }
};
const storage_commands = [_][]const u8{ "MD D64TEST\r", "CD D64TEST\r", "COPY \\CONFIG.SYS T.TXT\r", "TYPE T.TXT\r", "REN T.TXT R.TXT\r", "IF EXIST R.TXT TYPE R.TXT\r", "IF EXIST R.TXT ECHO D64EXISTS\r", "DEL R.TXT\r", "TYPE MISSING.TXT\r", "CD \\\r", "RD D64TEST\r" };
const mode_commands = [_][]const u8{ "MODE CO40\r", "MODE CO80\r" };
fn nibble(font: []const u8, ch: usize, y: usize) u8 {
    const v = font[ch * 4 + y / 2];
    return if (y & 1 == 0) v >> 4 else v & 15;
}
fn scanCode(ascii: u8) ?u8 {
    const plain = "1234567890-=QWERTYUIOP[]ASDFGHJKL;'`\\ZXCVBNM,./";
    const scans = [_]u8{ 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53 };
    if (ascii == '\r') return 0x1c;
    if (ascii == ' ') return 0x39;
    if (ascii == '\t') return 0x0f;
    if (ascii == 8) return 0x0e;
    const upper = std.ascii.toUpper(ascii);
    if (std.mem.indexOfScalar(u8, plain, upper)) |i| return scans[i];
    const shifted = "!@#$%^&*()_+{}:\"~|<>?";
    const shifted_scans = [_]u8{ 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26, 27, 39, 40, 41, 43, 51, 52, 53 };
    if (std.mem.indexOfScalar(u8, shifted, ascii)) |i| return shifted_scans[i];
    return null;
}
fn runWorkflow(mode_lane: bool) !void {
    const image = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, source_path, alloc, .limited(368641));
    defer alloc.free(image);
    try std.testing.expectEqualStrings("bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb", &sha(image));
    var lane = try Lane.init();
    defer lane.deinit();
    lane.mode_lane = mode_lane;
    errdefer lane.report("failed", image) catch {};
    c.dos64_enable_reu(lane.f.machine);
    c.dos64_uci_model_enable(lane.f.machine, 0xdf1c, 3, 0xc9);
    model.import_model_source(lane.f.machine, image.ptr, image.len);
    c.dos64_cia_clock_enable(lane.f.machine);
    c.dos64_cia_clock_step(lane.f.machine, 1);
    c.dos64_native_display_enable(lane.f.machine);
    model.dos64_host_input_model_enable(@ptrCast(lane.f.machine));
    c.native_runtime_control_enable(lane.f.machine);
    const config = try lane.f.symbol("dos64_native_config");
    lane.f.poke(config + 4, 0xa5);
    lane.f.poke(config + 7, 9);
    for ("disk.img\x00", 0..) |v, i| lane.f.poke(config + 14 + @as(u16, @intCast(i)), v);
    c.dos64_cia_clock_icr_seed(lane.f.machine, 0x1f, 0x1f);
    c.native_runtime_require_nmi_order(lane.f.machine, try lane.f.symbol("dos64_native_nmi"));
    const entry_before = c.dos64_get_regs(lane.f.machine).cycles;
    c.dos64_set_regs(lane.f.machine, .{ .pc = try lane.f.symbol("dos64_entry"), .sp = 0x57, .a = 0, .x = 0, .y = 0, .p = 0x28, .cycles = 0, .instructions = 0 });
    const entry = c.dos64_run(lane.f.machine, try lane.f.symbol("dos64_native_loop"), 1_000_000);
    try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), entry.status);
    lane.native_cycles += entry.regs.cycles - entry_before;
    try std.testing.expectEqual(@as(u8, 1), c.native_runtime_nmi_checked(lane.f.machine));
    while (lane.state() == 2) : (lane.startup_polls += 1) {
        if (lane.startup_polls >= 150000) return error.ImportPollBudget;
        try lane.call("dos64_native_cold_poll", 40_000_000);
    }
    try std.testing.expectEqual(@as(u8, 4), lane.state());
    try std.testing.expectEqual(@as(u32, 723), model.import_model_commands(lane.f.machine));
    try std.testing.expectEqual(@as(u8, 0), model.import_model_open(lane.f.machine));
    c.dos64_cia_clock_step(lane.f.machine, 0);
    lane.runtime_clock = true;
    var last_observed: u32 = 0xffffffff;
    while (lane.stage != .done) : (lane.cpu_ticks += 1) {
        if (lane.cpu_ticks >= 300000) {
            lane.diagnostics();
            return error.NativeTickBudget;
        }
        // A genuine DOS text scroll alone takes slightly over3M cycles.
        try lane.call("dos64_native_tick", if (mode_lane) 8_000_000 else 5_000_000);
        const count = lane.count();
        // DOS also polls INT16 AH01 without entering the blocking AH00 gate.
        // Observe coherently at bounded progress intervals as well as blocking
        // waits, so date/time and shell input cannot be starved of fixture keys.
        if (count != last_observed and (lane.f.peek(try lane.f.symbol("dos64_bios_waiting")) == 1 or last_observed == 0xffffffff or count -% last_observed >= 4096)) {
            last_observed = count;
            try lane.observe();
        }
    }
    try std.testing.expectEqual(@as(u8, 5), lane.state());
    try std.testing.expect(lane.initial_prompt);
    try lane.captureDisk("final");
    const guest = try alloc.alloc(u8, 640 * 1024);
    defer alloc.free(guest);
    try lane.read(0, guest);
    var video: [16384]u8 = undefined;
    try lane.read(0xb8000, &video);
    if (mode_lane) try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(lane.f.machine, 0x100000, image.ptr, image.len));
    const after = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, source_path, alloc, .limited(368641));
    defer alloc.free(after);
    try std.testing.expectEqualSlices(u8, image, after);
    try std.testing.expect(lane.f.word(try lane.f.symbol("dos64_pit_total")) > 0);
    try std.testing.expect(word(guest, 0x46c) > 0);
    var host_ram: [65536]u8 = undefined;
    for (&host_ram, 0..) |*byte, address| byte.* = lane.f.peek(@intCast(address));
    for ([_]struct { operand: []const u8, buffer: []const u8, opcode: u8 }{
        .{ .operand = "dos64_uci_upload_operand", .buffer = "dos64_uci_command", .opcode = 0xad },
        .{ .operand = "dos64_uci_drain_operand", .buffer = "dos64_uci_data", .opcode = 0x8d },
    }) |item| {
        const operand = try lane.f.symbol(item.operand);
        const base = try lane.f.symbol(item.buffer);
        const value = std.mem.readInt(u16, host_ram[operand..][0..2], .little);
        try std.testing.expectEqual(item.opcode, host_ram[operand - 1]);
        try std.testing.expect(value >= base and value < base + 896);
    }
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/native-workflows-host-64k.bin", .data = &host_ram });
    try lane.report("passed", image);
}

test "opt-in genuine native DOS33 internal disposable floppy workflows" {
    try runWorkflow(false);
}
test "opt-in genuine guest MODE COM selects native forty and eighty columns" {
    try runWorkflow(true);
}
test "complete printable ASCII mapping preserves original XT scan positions" {
    for (32..127) |v| try std.testing.expect(scanCode(@intCast(v)) != null);
}

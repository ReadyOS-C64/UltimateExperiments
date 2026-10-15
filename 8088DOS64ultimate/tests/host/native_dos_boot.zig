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
const Stage = enum { date, time, prompt, ver, dir, done };
const Entry = struct { name: [12]u8, size: u32, seen: bool = false };
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
    version: bool = false,
    initial_prompt: bool = false,
    header: bool = false,
    summary: bool = false,
    free_bytes: u32 = 0,
    pagination: u32 = 0,
    entries: std.array_list.Managed(Entry),
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
        return .{ .diag = try f.symbol("dos64_native_diag"), .counter = try f.symbol("dos64_cpu_instructions"), .guest = try f.symbol("dos64_guest"), .f = f, .entries = .init(alloc), .observations = .init(alloc), .inputs = .init(alloc) };
    }
    fn deinit(self: *Lane) void {
        self.entries.deinit();
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
        if (self.native_cycles > 2_500_000_000 or self.count() > 900_000) {
            self.diagnostics();
            return error.NativeDosBudget;
        }
    }
    fn command(self: *Lane, cmd: u8) !void {
        if (self.f.peek(self.diag + 3) != 0) return error.OutstandingNativeCommand;
        self.f.poke(self.diag + 4, 0);
        self.f.poke(self.diag + 3, cmd);
        self.command_calls += 1;
        try self.call("dos64_native_tick", if (cmd == 2) 3_000_000 else 5_000_000);
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
            const scan: u8 = switch (ascii) {
                'V' => 0x2f,
                'E' => 0x12,
                'R' => 0x13,
                'D' => 0x20,
                'I' => 0x17,
                'P' => 0x19,
                ' ' => 0x39,
                '/' => 0x35,
                '\r' => 0x1c,
                else => return error.UnsupportedScriptKey,
            };
            const key = (@as(u16, scan) << 8) | ascii;
            self.f.poke(self.diag + 5, ascii);
            self.f.poke(self.diag + 6, scan);
            try self.command(1);
            try self.inputs.append(key);
        }
    }
    // Same independent read-only FAT12/name+size/free-space oracle used by the
    // accepted existing DOS lane. No expected names/sizes come from guest RAM.
    fn directoryOracle(self: *Lane, image: []const u8) !void {
        const sector = word(image, 11);
        const reserved = word(image, 14);
        const fat_sectors = word(image, 22);
        const root_entries = word(image, 17);
        const root_lba = @as(usize, reserved) + @as(usize, image[16]) * fat_sectors;
        const root_sectors = (@as(usize, root_entries) * 32 + sector - 1) / sector;
        for (0..root_entries) |i| {
            const e = image[root_lba * sector + i * 32 ..][0..32];
            if (e[0] == 0) break;
            if (e[0] == 0xe5 or e[11] & 0x1e != 0) continue;
            var name: [12]u8 = undefined;
            @memcpy(name[0..8], e[0..8]);
            name[8] = ' ';
            @memcpy(name[9..12], e[8..11]);
            try self.entries.append(.{ .name = name, .size = std.mem.readInt(u32, e[28..32], .little) });
        }
        const clusters = (@as(usize, word(image, 19)) - root_lba - root_sectors) / image[13];
        const fat = image[@as(usize, reserved) * sector ..][0 .. @as(usize, fat_sectors) * sector];
        for (2..clusters + 2) |cluster| {
            const at = cluster + cluster / 2;
            const pair = @as(u16, fat[at]) | (@as(u16, fat[at + 1]) << 8);
            const value = if (cluster & 1 == 0) pair & 0xfff else pair >> 4;
            if (value == 0) self.free_bytes += @as(u32, image[13]) * sector;
        }
    }
    fn directory(self: *Lane, s: *const Screen) void {
        if (s.contains("Directory of  A:")) self.header = true;
        if (!self.header) return;
        for (0..25) |row| {
            const line = s.line(row);
            for (self.entries.items) |*entry| if (std.mem.startsWith(u8, line, &entry.name)) {
                var fields = std.mem.tokenizeScalar(u8, line[12..], ' ');
                if (fields.next()) |txt| {
                    const size = std.fmt.parseInt(u32, txt, 10) catch continue;
                    if (size == entry.size) entry.seen = true;
                }
            };
            var fields = std.mem.tokenizeScalar(u8, line, ' ');
            const count_text = fields.next() orelse continue;
            const label = fields.next() orelse continue;
            const free = fields.next() orelse continue;
            const bytes = fields.next() orelse continue;
            const last = fields.next() orelse continue;
            if (!std.mem.eql(u8, label, "File(s)") or !std.mem.eql(u8, bytes, "bytes") or !std.mem.eql(u8, last, "free")) continue;
            const total = std.fmt.parseInt(usize, count_text, 10) catch continue;
            const available = std.fmt.parseInt(u32, free, 10) catch continue;
            if (total == self.entries.items.len and available == self.free_bytes) self.summary = true;
        }
    }
    fn observe(self: *Lane) !void {
        const s = try self.screen();
        var keys: []const u8 = "";
        switch (self.stage) {
            .date => if (s.contains("Enter new date (mm-dd-yy):")) {
                keys = "\r";
                self.stage = .time;
            },
            .time => if (s.contains("Enter new time:")) {
                keys = "\r";
                self.stage = .prompt;
            },
            .prompt => if (s.prompt()) {
                self.initial_prompt = true;
                keys = "VER\r";
                self.stage = .ver;
            },
            .ver => {
                if (s.contains("MS-DOS Version 3.30")) self.version = true;
                if (self.version and s.prompt()) {
                    keys = "DIR /P\r";
                    self.stage = .dir;
                }
            },
            .dir => {
                self.directory(&s);
                var all = true;
                for (self.entries.items) |e| all = all and e.seen;
                if (all and self.summary and s.prompt()) self.stage = .done else if (std.mem.indexOf(u8, s.line(s.row)[0..s.column], "Strike a key when ready . . .") != null) {
                    if (self.pagination >= 4) return error.PaginationBudget;
                    keys = " ";
                    self.pagination += 1;
                }
            },
            .done => {},
        }
        if (self.stage != .done) {
            try self.command(3);
            try self.typeKeys(keys);
        }
    }
    fn report(self: *Lane, status: []const u8, source: []const u8, guest_hash: ?[64]u8, video_hash: ?[64]u8) !void {
        const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.prg", alloc, .limited(65538));
        defer alloc.free(prg);
        const output = try std.json.Stringify.valueAlloc(alloc, .{ .status = status, .script = "native ENTRY/import/BIOS then native tick; CR,CR,VER CR,DIR /P CR,SPACE per pagination", .source_sha256 = sha(source), .linked_prg_sha256 = sha(prg), .guest_instructions = self.count(), .native_cpu_cycles = self.native_cycles, .native_ticks = self.cpu_ticks, .startup_polls = self.startup_polls, .development_commands = self.command_calls, .maximum_tick_cycles = self.max_tick_cycles, .maximum_snapshot_cycles = self.max_snapshot_cycles, .initial_prompt = self.initial_prompt, .version_3_30 = self.version, .directory_header = self.header, .directory_summary = self.summary, .expected_free_bytes = self.free_bytes, .directory_entries = self.entries.items, .pagination_keys = self.pagination, .input_words = self.inputs.items, .observations = self.observations.items, .guest_640k_sha256 = guest_hash, .cga_16k_sha256 = video_hash, .clock_model = "functional64:1 Peddle CPUcycle/phi2 after startup, DMA stalls excluded; not physical timing", .no_direct_cpu_steps_or_DOS_shortcuts = true }, .{ .whitespace = .indent_2 });
        defer alloc.free(output);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/native-dos-boot.json", .data = output });
    }
};
test "opt-in actual native file startup and bounded runtime boot genuine DOS33 VER and DIR /P" {
    const image = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, source_path, alloc, .limited(368641));
    defer alloc.free(image);
    try std.testing.expectEqualStrings("bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb", &sha(image));
    var lane = try Lane.init();
    defer lane.deinit();
    errdefer lane.report("failed", image, null, null) catch {};
    try lane.directoryOracle(image);
    try std.testing.expectEqual(@as(usize, 35), lane.entries.items.len);
    try std.testing.expectEqual(@as(u32, 9216), lane.free_bytes);
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
        if (lane.cpu_ticks >= 80000) {
            lane.diagnostics();
            return error.NativeTickBudget;
        }
        // A genuine DOS text scroll alone takes slightly over3M cycles.
        try lane.call("dos64_native_tick", 5_000_000);
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
    try std.testing.expect(lane.initial_prompt and lane.version and lane.header and lane.summary);
    try std.testing.expect(lane.pagination > 0);
    for (lane.entries.items) |e| try std.testing.expect(e.seen);
    const guest = try alloc.alloc(u8, 640 * 1024);
    defer alloc.free(guest);
    try lane.read(0, guest);
    var video: [16384]u8 = undefined;
    try lane.read(0xb8000, &video);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(lane.f.machine, 0x100000, image.ptr, image.len));
    const after = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, source_path, alloc, .limited(368641));
    defer alloc.free(after);
    try std.testing.expectEqualSlices(u8, image, after);
    var host_ram: [65536]u8 = undefined;
    for (&host_ram, 0..) |*byte, address| byte.* = lane.f.peek(@intCast(address));
    for ([_]struct { operand: []const u8, buffer: []const u8, opcode: u8 }{
        .{ .operand = "dos64_uci_upload_operand", .buffer = "dos64_uci_command", .opcode = 0xad },
        .{ .operand = "dos64_uci_drain_operand", .buffer = "dos64_uci_data", .opcode = 0x8d },
    }) |item| {
        const operand = try lane.f.symbol(item.operand);
        const base = try lane.f.symbol(item.buffer);
        const value = std.mem.readInt(u16, host_ram[operand..][0..2], .little);
        try std.testing.expectEqual(item.opcode, host_ram[operand-1]);
        try std.testing.expect(value >= base and value < base + 896);
    }
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/native-dos-host-64k.bin", .data = &host_ram });
    try lane.report("passed", image, sha(guest), sha(&video));
}

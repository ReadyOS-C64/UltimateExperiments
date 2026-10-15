const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const allocator = std.testing.allocator;
const long_boot = @import("test_options").long_dos_boot;
const cycle_limit: u64 = if (long_boot) 1_600_000_000 else 200_000_000;
const instruction_limit: u32 = if (long_boot) 700_000 else 20_000;
const call_limit: u32 = if (long_boot) 850_000 else 50_000;
const Oracle = struct {
    source_path: []const u8,
    source_bytes: usize,
    source_sha256: []const u8,
    boot_sector_sha256: []const u8,
    kernel_bytes: usize,
    kernel_sha256: []const u8,
    kernel_rounded_sectors: u16,
    kernel_lba: u16,
    load_physical: u32,
    handoff_cs: u16,
    handoff_ip: u16,
    sectors_per_track: u16,
    heads: u16,
    raw_extent_sectors: u16,
    raw_extent_bytes: usize,
    raw_extent_sha256: []const u8,
    raw_extent_hex: []const u8,
};
const DiskRead = struct { lba: u16, count: u16, destination: u32 };
const Snapshot = struct { registers: [14]u16, guest_instructions: u32 };
const ScriptStage = enum { date, time, initial_prompt, ver, dir, done };
const Screen = struct {
    mode: u8,
    columns: u16,
    page: u8,
    cursor_row: u8,
    cursor_column: u8,
    text: [2025]u8,
    fn line(self: *const Screen, row: usize) []const u8 {
        return self.text[row * 81 ..][0..self.columns];
    }
    fn contains(self: *const Screen, needle: []const u8) bool {
        return std.mem.indexOf(u8, &self.text, needle) != null;
    }
    fn prompt(self: *const Screen) bool {
        const current = std.mem.trim(u8, self.line(self.cursor_row), " ");
        return self.cursor_column == 2 and std.mem.eql(u8, current, "A>");
    }
};
const Observation = struct { guest_instructions: u32, stage: ScriptStage, screen: Screen };
const DirEntry = struct { name: [12]u8, size: u32, seen: bool = false };
const Input = struct { guest_instructions: u32, key: u16, carry: u8, status: u8, head_before: u16, tail_before: u16, head_after: u16, tail_after: u16 };
const Identity = struct { source_sha256: [64]u8, oracle_sha256: [64]u8, linked_prg_sha256: [64]u8, linked_labels_sha256: [64]u8, host_test_sha256: [64]u8 };
const Lane = struct {
    f: Fixture,
    guest: u16,
    counter: u16,
    identity: Identity,
    native_cycles: u64 = 0,
    calls: u32 = 0,
    setup_native_cycles: u64 = 0,
    maximum_call_cycles: u64 = 0,
    support_native_cycles: u64 = 0,
    stage: ScriptStage = .date,
    initial_prompt_seen: bool = false,
    ver_accepted: bool = false,
    dir_accepted: bool = false,
    observations: std.array_list.Managed(Observation),
    inputs: std.array_list.Managed(Input),
    last_screen: ?Screen = null,
    last_observation_count: u32 = 0,
    dir_entries: std.array_list.Managed(DirEntry),
    dir_header_seen: bool = false,
    dir_summary_seen: bool = false,
    expected_free_bytes: u32 = 0,
    handoff: bool = false,
    kernel_bytes_verified: bool = false,
    handoff_instructions: u32 = 0,
    handoff_native_cycles: u64 = 0,
    handoff_read_count: usize = 0,
    ring: [32]Snapshot = undefined,
    ring_count: usize = 0,
    reads: std.array_list.Managed(DiskRead),

    fn count(self: *const Lane) u32 {
        return @as(u32, self.f.word(self.counter)) | (@as(u32, self.f.word(self.counter + 2)) << 16);
    }
    fn snapshot(self: *const Lane) Snapshot {
        var r: [14]u16 = undefined;
        for (&r, 0..) |*v, i| v.* = self.f.word(self.guest + @as(u16, @intCast(i * 2)));
        return .{ .registers = r, .guest_instructions = self.count() };
    }
    fn flush(self: *Lane) !void {
        const start = c.dos64_get_regs(self.f.machine).cycles;
        const r = try self.f.call("dos64_cache_flush", 2_000_000);
        self.support_native_cycles += r.cycles - start;
        if ((r.p & 1) != 0) return error.HostCacheFailure;
    }
    fn reuWord(self: *const Lane, a: u32) u16 {
        return @as(u16, c.dos64_reu_peek(self.f.machine, a)) | (@as(u16, c.dos64_reu_peek(self.f.machine, a + 1)) << 8);
    }
    fn screen(self: *Lane) !Screen {
        try self.flush();
        const mode = c.dos64_reu_peek(self.f.machine, 0x449);
        const cols = self.reuWord(0x44a);
        const page = c.dos64_reu_peek(self.f.machine, 0x462);
        if (mode > 3 or (cols != 40 and cols != 80) or page >= @as(u8, if (cols == 80) 4 else 8)) return error.InvalidTextGeometry;
        const size = self.reuWord(0x44c);
        const offset = self.reuWord(0x44e);
        if (size != @as(u16, if (cols == 80) 0x1000 else 0x800) or offset != @as(u16, page) * size) return error.InvalidTextPage;
        const cursor = self.reuWord(0x450 + @as(u32, page) * 2);
        if (cursor >> 8 >= 25 or cursor & 255 >= cols) return error.InvalidTextCursor;
        var result = Screen{ .mode = mode, .columns = cols, .page = page, .cursor_row = @intCast(cursor >> 8), .cursor_column = @truncate(cursor), .text = @splat(' ') };
        for (0..25) |row| {
            for (0..cols) |col| {
                const v = c.dos64_reu_peek(self.f.machine, 0xb8000 + @as(u32, offset) + @as(u32, @intCast((row * cols + col) * 2)));
                result.text[row * 81 + col] = if (v >= 32 and v < 127) v else '?';
            }
            result.text[row * 81 + 80] = '\n';
        }
        return result;
    }
    fn enqueue(self: *Lane, key: u16) !void {
        // Use the real assembly keyboard backend, preserving the entire guest
        // context. No host edits to the guest ring, results, PC or DOS state.
        try self.flush();
        const before = self.snapshot();
        const head = self.reuWord(0x41a);
        const tail = self.reuWord(0x41c);
        const descriptor = try self.f.symbol("dos64_keyboard_key");
        self.f.poke(descriptor, @truncate(key));
        self.f.poke(descriptor + 1, @truncate(key >> 8));
        const start = c.dos64_get_regs(self.f.machine).cycles;
        const r = try self.f.call("dos64_keyboard_enqueue", 100_000);
        self.support_native_cycles += r.cycles - start;
        try self.flush();
        const status = self.f.peek(try self.f.symbol("dos64_keyboard_status"));
        try self.inputs.append(.{ .guest_instructions = self.count(), .key = key, .carry = r.p & 1, .status = status, .head_before = head, .tail_before = tail, .head_after = self.reuWord(0x41a), .tail_after = self.reuWord(0x41c) });
        try std.testing.expectEqualSlices(u16, &before.registers, &self.snapshot().registers);
        if ((r.p & 1) != 0 or status != 0) return error.ScriptKeyboardRejected;
    }
    fn typeCommand(self: *Lane, command: []const u8) !void {
        // Commands fit the original 15-key FIFO; the BIOS owns consumption.
        for (command) |ascii| {
            const scan: u8 = switch (ascii) {
                'V' => 0x2f,
                'E' => 0x12,
                'R' => 0x13,
                'D' => 0x20,
                'I' => 0x17,
                '\r' => 0x1c,
                else => return error.UnsupportedScriptKey,
            };
            try self.enqueue((@as(u16, scan) << 8) | ascii);
        }
    }
    fn directoryOracle(self: *Lane, image: []const u8) !void {
        const sector = std.mem.readInt(u16, image[11..13], .little);
        const reserved = std.mem.readInt(u16, image[14..16], .little);
        const fat_sectors = std.mem.readInt(u16, image[22..24], .little);
        const root_entries = std.mem.readInt(u16, image[17..19], .little);
        const root_lba = @as(usize, reserved) + @as(usize, image[16]) * fat_sectors;
        const root_sectors = (@as(usize, root_entries) * 32 + sector - 1) / sector;
        for (0..root_entries) |i| {
            const entry = image[root_lba * sector + i * 32 ..][0..32];
            if (entry[0] == 0) break;
            if (entry[0] == 0xe5 or entry[11] & 0x1e != 0) continue;
            var name: [12]u8 = undefined;
            @memcpy(name[0..8], entry[0..8]);
            name[8] = ' ';
            @memcpy(name[9..12], entry[8..11]);
            try self.dir_entries.append(.{ .name = name, .size = std.mem.readInt(u32, entry[28..32], .little) });
        }
        const total = std.mem.readInt(u16, image[19..21], .little);
        const clusters = (@as(usize, total) - root_lba - root_sectors) / image[13];
        const fat = image[@as(usize, reserved) * sector ..][0 .. @as(usize, fat_sectors) * sector];
        for (2..clusters + 2) |cluster| {
            const offset = cluster + cluster / 2;
            const pair = @as(u16, fat[offset]) | (@as(u16, fat[offset + 1]) << 8);
            const value = if (cluster & 1 == 0) pair & 0xfff else pair >> 4;
            if (value == 0) self.expected_free_bytes += @as(u32, image[13]) * sector;
        }
    }
    fn directoryOutput(self: *Lane, current: *const Screen) void {
        if (current.contains("Directory of  A:")) self.dir_header_seen = true;
        if (!self.dir_header_seen) return;
        for (0..25) |row| {
            const line = current.line(row);
            for (self.dir_entries.items) |*entry| {
                if (std.mem.startsWith(u8, line, &entry.name)) {
                    var fields = std.mem.tokenizeScalar(u8, line[12..], ' ');
                    if (fields.next()) |size_text| {
                        const size = std.fmt.parseInt(u32, size_text, 10) catch continue;
                        if (size == entry.size) entry.seen = true;
                    }
                }
            }
            var fields = std.mem.tokenizeScalar(u8, line, ' ');
            const count_text = fields.next() orelse continue;
            const label = fields.next() orelse continue;
            const free_text = fields.next() orelse continue;
            const bytes = fields.next() orelse continue;
            const free = fields.next() orelse continue;
            if (!std.mem.eql(u8, label, "File(s)") or !std.mem.eql(u8, bytes, "bytes") or !std.mem.eql(u8, free, "free")) continue;
            const files = std.fmt.parseInt(usize, count_text, 10) catch continue;
            const available = std.fmt.parseInt(u32, free_text, 10) catch continue;
            if (files == self.dir_entries.items.len and available == self.expected_free_bytes) self.dir_summary_seen = true;
        }
        var all_seen = true;
        for (self.dir_entries.items) |entry| all_seen = all_seen and entry.seen;
        self.dir_accepted = self.dir_header_seen and self.dir_summary_seen and all_seen;
    }
    fn observe(self: *Lane, force: bool) !bool {
        if (!long_boot) return false;
        if (!force and self.count() - self.last_observation_count < 256) return false;
        self.last_observation_count = self.count();
        const current = try self.screen();
        const changed = if (self.last_screen) |previous| !std.meta.eql(previous, current) else true;
        self.last_screen = current;
        if (changed) {
            if (self.observations.items.len >= 4096) return error.ScreenObservationBudget;
            try self.observations.append(.{ .guest_instructions = self.count(), .stage = self.stage, .screen = current });
        }
        switch (self.stage) {
            .date => if (current.contains("Enter new date (mm-dd-yy):")) {
                try self.enqueue(0x1c0d);
                self.stage = .time;
            },
            .time => if (current.contains("Enter new time:")) {
                try self.enqueue(0x1c0d);
                self.stage = .initial_prompt;
            },
            .initial_prompt => if (current.prompt()) {
                self.initial_prompt_seen = true;
                try self.typeCommand("VER\r");
                self.stage = .ver;
            },
            .ver => {
                if (current.contains("MS-DOS Version 3.30")) self.ver_accepted = true;
                if (self.ver_accepted and current.prompt()) {
                    try self.typeCommand("DIR\r");
                    self.stage = .dir;
                }
            },
            .dir => {
                // Compare every visible root filename and size, plus count and
                // free bytes, with an independent read-only FAT12 oracle.
                self.directoryOutput(&current);
                if (self.dir_accepted and current.prompt()) self.stage = .done;
            },
            .done => {},
        }
        return self.stage == .done;
    }
    fn peekCode(self: *Lane, cs: u16, ip: u16) [8]u8 {
        var bytes: [8]u8 = undefined;
        for (&bytes, 0..) |*v, i| v.* = c.dos64_reu_peek(self.f.machine, (@as(u32, cs) * 16 + (ip +% @as(u16, @intCast(i)))) & 0xfffff);
        return bytes;
    }
    fn report(self: *Lane, reason: []const u8, missing_vector: ?u8, previous: Snapshot, allow_flush: bool) !void {
        // Only publish cache contents when the target has returned safely and
        // no terminal host-cache failure has compromised guest authority.
        const coherent = allow_flush and self.f.peek(try self.f.symbol("dos64_bios_host_error")) == 0 and self.f.peek(try self.f.symbol("dos64_cpu_status")) != 3;
        if (coherent) try self.flush();
        const current = self.snapshot();
        var ram_hash: ?[64]u8 = null;
        var video_hash: ?[64]u8 = null;
        if (coherent and long_boot) {
            self.last_screen = try self.screen();
            const ram = try allocator.alloc(u8, 640 * 1024);
            defer allocator.free(ram);
            const video = try allocator.alloc(u8, 0x4000);
            defer allocator.free(video);
            try std.testing.expectEqual(@as(u8, 1), c.dos64_reu_read(self.f.machine, 0, ram.ptr, ram.len));
            try std.testing.expectEqual(@as(u8, 1), c.dos64_reu_read(self.f.machine, 0xb8000, video.ptr, video.len));
            ram_hash = hashHex(ram);
            video_hash = hashHex(video);
            try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/dos-boot-memory.bin", .data = ram });
            try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = "build/dos-boot-video.bin", .data = video });
        }
        var trace: [32]Snapshot = undefined;
        const n = @min(self.ring_count, 32);
        for (0..n) |i| trace[i] = self.ring[(self.ring_count - n + i) % 32];
        const json = try std.json.Stringify.valueAlloc(allocator, .{
            .schema = 2,
            .milestone = if (long_boot) "genuine DOS scripted keyboard and COMMAND built-ins" else "genuine IO.SYS kernel entry; complete DOS boot remains separate",
            .kernel_handoff = self.handoff,
            .kernel_bytes_verified = self.kernel_bytes_verified,
            .command_prompt_accepted = self.initial_prompt_seen and self.ver_accepted,
            .script_stage = self.stage,
            .initial_prompt_seen = self.initial_prompt_seen,
            .ver_accepted = self.ver_accepted,
            .dir_accepted = self.dir_accepted,
            .directory_entries = self.dir_entries.items,
            .expected_free_bytes = self.expected_free_bytes,
            .directory_header_seen = self.dir_header_seen,
            .directory_summary_seen = self.dir_summary_seen,
            .input_history = self.inputs.items,
            .screen_observations = self.observations.items,
            .last_screen = self.last_screen,
            .stop_reason = reason,
            .artifacts = self.identity,
            .guest_ram_sha256 = ram_hash,
            .cga_vram_sha256 = video_hash,
            .missing_bios_vector = missing_vector,
            .cpu_status = self.f.peek(try self.f.symbol("dos64_cpu_status")),
            .cpu_opcode = self.f.peek(try self.f.symbol("dos64_cpu_opcode")),
            .register_order = [_][]const u8{ "ax", "cx", "dx", "bx", "sp", "bp", "si", "di", "es", "cs", "ss", "ds", "ip", "flags" },
            .state = current,
            .instruction_bytes_hex = std.fmt.bytesToHex(self.peekCode(current.registers[9], current.registers[12]), .lower),
            .previous_state = previous,
            .previous_bytes_hex = std.fmt.bytesToHex(self.peekCode(previous.registers[9], previous.registers[12]), .lower),
            .instruction_bytes_coherent = coherent,
            .native_cycles = self.native_cycles,
            .support_native_cycles = self.support_native_cycles,
            .setup_native_cycles = self.setup_native_cycles,
            .native_calls = self.calls,
            .maximum_call_cycles = self.maximum_call_cycles,
            .handoff_guest_instructions = self.handoff_instructions,
            .handoff_native_cycles = self.handoff_native_cycles,
            .handoff_read_count = self.handoff_read_count,
            .bios_reads = self.reads.items,
            .last_trace = trace[0..n],
            .timing_scope = "CPU-step cycles exclude caller JSR and REU DMA stalls; support cycles separately count coherent observations and native keyboard enqueue. Not physical elapsed time or XT speed.",
            .limits = .{ .per_call_native_cycles = 5_000_000, .aggregate_native_cycles = cycle_limit, .completed_guest_instructions = instruction_limit, .native_calls = call_limit },
        }, .{ .whitespace = .indent_2 });
        defer allocator.free(json);
        try std.Io.Dir.cwd().writeFile(std.Options.debug_io, .{ .sub_path = if (long_boot) "build/dos-boot-first.json" else "build/dos-boot-kernel.json", .data = json });
    }
    fn step(self: *Lane, oracle: Oracle) !bool {
        const before = self.snapshot();
        self.ring[self.ring_count % 32] = before;
        self.ring_count += 1;
        if (self.native_cycles + self.support_native_cycles >= cycle_limit or self.count() >= instruction_limit or self.calls >= call_limit) {
            try self.report("bounded execution limit", null, before, true);
            return error.BootBudget;
        }
        // Native BIOS is reached through mutable IVT, guest INT and owned ROM
        // OUT. Observe requests here; never supply sectors or guest results.
        if (before.registers[9] == 0xf000 and before.registers[12] == 0x100 and before.registers[0] >> 8 == 2) {
            const cx = before.registers[1];
            const dx = before.registers[2];
            const cylinder = (cx >> 8) | ((cx & 0xc0) << 2);
            const lba = (cylinder * oracle.heads + (dx >> 8)) * oracle.sectors_per_track + (cx & 0x3f) - 1;
            try self.reads.append(.{ .lba = lba, .count = before.registers[0] & 0xff, .destination = (@as(u32, before.registers[8]) * 16 + before.registers[3]) & 0xfffff });
        }
        const call_start = c.dos64_get_regs(self.f.machine).cycles;
        const r = self.f.call("dos64_cpu_step", 5_000_000) catch |err| {
            if (self.f.last_regs) |native| self.native_cycles += native.cycles - call_start;
            try self.report(@errorName(err), null, before, false);
            return err;
        };
        const elapsed = r.cycles - call_start;
        self.calls += 1;
        self.native_cycles += elapsed;
        self.maximum_call_cycles = @max(self.maximum_call_cycles, elapsed);
        const status = self.f.peek(try self.f.symbol("dos64_cpu_status"));
        if ((r.p & 1) != 0 or status != 0) {
            try self.report(if (status == 2) "unsupported guest instruction" else "target failure or halt", null, before, true);
            if (!self.handoff) return error.KernelHandoffFailed;
            if (status != 2) return error.UnexpectedKernelStop;
            return false;
        }
        const after = self.snapshot();
        if (self.f.peek(try self.f.symbol("dos64_bios_waiting")) != 0 and self.f.peek(try self.f.symbol("dos64_cpu_yield")) != 0) {
            if (!long_boot) {
                try self.report("keyboard BIOS awaiting input", null, before, true);
                return false;
            }
            _ = self.observe(true) catch |err| {
                try self.report(@errorName(err), null, before, true);
                return err;
            };
        }
        // A zero IVT entry is an absent BIOS contract. Stop before executing
        // unrelated low RAM, and retain the actual INT instruction/arguments.
        if (after.registers[9] == 0 and after.registers[12] == 0 and self.f.peek(try self.f.symbol("dos64_cpu_opcode")) == 0xcd) {
            try self.flush();
            const bytes = self.peekCode(before.registers[9], before.registers[12]);
            try self.report("unimplemented BIOS interrupt vector", if (bytes[0] == 0xcd) bytes[1] else null, before, true);
            if (!self.handoff) return error.KernelHandoffFailed;
            return false;
        }
        return true;
    }
};

fn hashHex(bytes: []const u8) [64]u8 {
    var digest: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(bytes, &digest, .{});
    return std.fmt.bytesToHex(digest, .lower);
}
fn fileHash(path: []const u8) ![64]u8 {
    const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, allocator, .limited(1024 * 1024));
    defer allocator.free(bytes);
    return hashHex(bytes);
}
fn hashIs(bytes: []const u8, expected: []const u8) !void {
    const hex = hashHex(bytes);
    try std.testing.expectEqualStrings(expected, &hex);
}

// The default gate asserts genuine boot-sector execution and IO.SYS identity.
// The opt-in long lane additionally supplies keys through the assembled BIOS
// backend, proves COMMAND's VER output and complete DIR listing, then requires
// its returned prompt. Missing behavior or a budget stop is a failing long gate.
test "unchanged DOS boot sector loads FAT12 IO.SYS through real BIOS and reaches kernel entry" {
    const oracle_json = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "tests/fixtures/dos-boot-oracle.json", allocator, .limited(100_000));
    defer allocator.free(oracle_json);
    const parsed = try std.json.parseFromSlice(Oracle, allocator, oracle_json, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();
    const oracle = parsed.value;
    const image = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, oracle.source_path, allocator, .limited(400 * 1024));
    defer allocator.free(image);
    try std.testing.expectEqual(oracle.source_bytes, image.len);
    try hashIs(image, oracle.source_sha256);
    try hashIs(image[0..512], oracle.boot_sector_sha256);
    const expected = try allocator.alloc(u8, oracle.raw_extent_bytes);
    defer allocator.free(expected);
    _ = try std.fmt.hexToBytes(expected, oracle.raw_extent_hex);
    try hashIs(expected, oracle.raw_extent_sha256);
    try hashIs(expected[0..oracle.kernel_bytes], oracle.kernel_sha256);
    try std.testing.expectEqualSlices(u8, expected, image[@as(usize, oracle.kernel_lba) * 512 ..][0..expected.len]);
    const identity = Identity{ .source_sha256 = hashHex(image), .oracle_sha256 = hashHex(oracle_json), .linked_prg_sha256 = try fileHash("build/dos64-tests.prg"), .linked_labels_sha256 = try fileHash("build/dos64-tests.labels"), .host_test_sha256 = try fileHash("tests/host/dos_boot.zig") };
    var lane = Lane{ .f = try Fixture.init(), .guest = 0, .counter = 0, .identity = identity, .reads = std.array_list.Managed(DiskRead).init(allocator), .observations = std.array_list.Managed(Observation).init(allocator), .inputs = std.array_list.Managed(Input).init(allocator), .dir_entries = std.array_list.Managed(DirEntry).init(allocator) };
    defer lane.f.deinit();
    defer lane.reads.deinit();
    defer lane.observations.deinit();
    defer lane.inputs.deinit();
    defer lane.dir_entries.deinit();
    if (long_boot) try lane.directoryOracle(image);
    lane.guest = try lane.f.symbol("dos64_guest");
    lane.counter = try lane.f.symbol("dos64_cpu_instructions");
    c.dos64_enable_reu(lane.f.machine);
    lane.f.poke(try lane.f.symbol("dos64_cache_limit"), 32);
    for ([_]struct { name: []const u8, budget: u64 }{ .{ .name = "dos64_cache_init", .budget = 50_000 }, .{ .name = "dos64_disk_init", .budget = 10_000 } }) |setup| {
        const start = c.dos64_get_regs(lane.f.machine).cycles;
        const r = try lane.f.call(setup.name, setup.budget);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        lane.setup_native_cycles += r.cycles - start;
    }
    // Only the whole immutable floppy is seeded into an owned disk REU slot.
    // Boot code and BIOS must perform every guest-memory load themselves.
    for (image, 0..) |v, i| c.dos64_reu_poke(lane.f.machine, 0x100000 + @as(u32, @intCast(i)), v);
    lane.f.poke(try lane.f.symbol("dos64_disk_loaded"), 1);
    var start = c.dos64_get_regs(lane.f.machine).cycles;
    var r = try lane.f.call("dos64_bios_init", 40_000_000);
    lane.setup_native_cycles += r.cycles - start;
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    start = c.dos64_get_regs(lane.f.machine).cycles;
    r = try lane.f.call("dos64_cpu_init", 10_000);
    lane.setup_native_cycles += r.cycles - start;
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    try std.testing.expectEqual(@as(u8, 0xa5), lane.f.peek(try lane.f.symbol("dos64_bios_ready")));
    try std.testing.expectEqual(@as(u16, 0xffff), lane.f.word(lane.guest + 18));
    try std.testing.expectEqual(@as(u16, 0), lane.f.word(lane.guest + 24));
    _ = try lane.step(oracle);
    _ = try lane.step(oracle);
    try std.testing.expectEqual(@as(u16, 0), lane.f.word(lane.guest + 18));
    try std.testing.expectEqual(@as(u16, 0x7c00), lane.f.word(lane.guest + 24));
    try lane.flush();
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(lane.f.machine, 0x7c00, image.ptr, 512));
    while (lane.f.word(lane.guest + 18) != oracle.handoff_cs or lane.f.word(lane.guest + 24) != oracle.handoff_ip) _ = try lane.step(oracle);
    lane.handoff = true;
    lane.handoff_instructions = lane.count();
    lane.handoff_native_cycles = lane.native_cycles;
    lane.handoff_read_count = lane.reads.items.len;
    try lane.flush();
    const mismatch = c.dos64_reu_compare(lane.f.machine, oracle.load_physical, expected.ptr, expected.len);
    if (mismatch != 0xffffffff) {
        try lane.report("kernel-entry byte mismatch", null, lane.snapshot(), true);
        std.debug.print("DOS kernel first byte divergence physical={x}\n", .{mismatch});
        return error.KernelBytesMismatch;
    }
    lane.kernel_bytes_verified = true;
    var next_lba = oracle.kernel_lba;
    var next_guest = oracle.load_physical;
    var sectors: u16 = 0;
    for (lane.reads.items) |read| {
        if (read.destination < oracle.load_physical) continue; // root directory at 0500
        try std.testing.expectEqual(next_lba, read.lba);
        try std.testing.expectEqual(next_guest, read.destination);
        next_lba += read.count;
        next_guest += @as(u32, read.count) * 512;
        sectors += read.count;
    }
    try std.testing.expectEqual(oracle.raw_extent_sectors, sectors);
    // Entire floppy and original source remain byte-identical after execution.
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(lane.f.machine, 0x100000, image.ptr, image.len));
    const after = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, oracle.source_path, allocator, .limited(400 * 1024));
    defer allocator.free(after);
    try hashIs(after, oracle.source_sha256);
    std.debug.print("Genuine DOS IO.SYS handoff {x}:{x}: {d} instructions, {d} native cycles, {d} raw sectors ({d} IO.SYS rounded sectors)\n", .{ oracle.handoff_cs, oracle.handoff_ip, lane.handoff_instructions, lane.handoff_native_cycles, sectors, oracle.kernel_rounded_sectors });
    try lane.report("kernel-entry byte identity accepted; continuation pending", null, lane.snapshot(), true);
    if (!long_boot) return;
    while (try lane.step(oracle)) {
        if (lane.observe(false) catch |err| {
            try lane.report(@errorName(err), null, lane.snapshot(), true);
            return err;
        }) break;
    }
    if (lane.stage != .done) return error.CommandBuiltinsIncomplete;
    const final_source_hash = try fileHash(oracle.source_path);
    try std.testing.expectEqualStrings(oracle.source_sha256, &final_source_hash);
    try lane.report("genuine COMMAND prompt, VER and DIR accepted", null, lane.snapshot(), true);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(lane.f.machine, 0x100000, image.ptr, image.len));
    try std.testing.expectEqual(@as(u8, 0), lane.f.peek(try lane.f.symbol("dos64_bios_host_error")));
    try std.testing.expectEqual(@as(u8, 0), lane.f.peek(try lane.f.symbol("dos64_disk_host_error")));
}

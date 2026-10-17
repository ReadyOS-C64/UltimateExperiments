const std = @import("std");
pub const c = @cImport({ @cInclude("peddle_bridge.h"); });
const allocator = std.testing.allocator;

pub const Fixture = struct {
    machine: *c.Dos64Machine,
    labels: []u8,
    symbols: std.StringHashMapUnmanaged(u16) = .empty,
    last_regs: ?c.Dos64Regs = null,
    stack_high_water: u8 = 0,
    initial_status: u8 = 0x24,
    unit_extra: ?[]u8 = null,

    pub fn init() !Fixture {
        return initPaths("build/dos64-tests.prg", "build/dos64-tests.labels");
    }
    pub fn initPaths(prg_path: []const u8, labels_path: []const u8) !Fixture {
        const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, prg_path, allocator, .limited(65538));
        defer allocator.free(bytes);
        if (bytes.len < 3) return error.InvalidPrg;
        const address = std.mem.readInt(u16, bytes[0..2], .little);
        if (bytes.len - 2 > 65536 - @as(usize, address)) return error.InvalidPrg;
        const machine = c.dos64_create() orelse return error.CreateMachine;
        errdefer c.dos64_destroy(machine);
        c.dos64_load(machine, address, bytes[2..].ptr, bytes.len-2);
        const labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, labels_path, allocator, .limited(1024*1024));
        errdefer allocator.free(labels);
        var symbols: std.StringHashMapUnmanaged(u16) = .empty;
        errdefer symbols.deinit(allocator);
        var lines = std.mem.splitScalar(u8, labels, '\n');
        while (lines.next()) |line| {
            var fields = std.mem.tokenizeAny(u8, line, " \t\r");
            if (!std.mem.eql(u8, fields.next() orelse continue, "al")) continue;
            const symbol_address = fields.next() orelse continue;
            const raw_name = fields.next() orelse continue;
            if (raw_name.len == 0) continue;
            const name = if (raw_name[0] == '.') raw_name[1..] else raw_name;
            if (!symbols.contains(name)) try symbols.put(allocator, name, try std.fmt.parseInt(u16, symbol_address, 16));
        }
        var extra: ?[]u8 = null;
        errdefer if (extra) |owned| allocator.free(owned);
        if (symbols.get("__UNITEXTRA_SIZE__")) |count| {
            const start = symbols.get("__UNITEXTRA_RUN__") orelse return error.InvalidUnitSidecar;
            const device = symbols.get("__DEVICESTATE_RUN__") orelse return error.InvalidUnitSidecar;
            const device_size = symbols.get("__DEVICESTATE_SIZE__") orelse return error.InvalidUnitSidecar;
            if (start != 0xef00 or count != 251 or @as(u32, start) + count > 0xf000 or
                @as(u32, device) + device_size > start) return error.InvalidUnitSidecar;
            const path = try std.fmt.allocPrint(allocator, "{s}.unit-extra.bin", .{prg_path});
            defer allocator.free(path);
            const code = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, allocator, .limited(256));
            extra = code;
            if (code.len != count) return error.InvalidUnitSidecar;
            c.dos64_load(machine, start, code.ptr, code.len);
        }
        return .{ .machine = machine, .labels = labels, .symbols = symbols, .unit_extra = extra };
    }
    pub fn deinit(self: *Fixture) void {
        if (self.unit_extra) |owned| allocator.free(owned);
        self.symbols.deinit(allocator);
        allocator.free(self.labels);
        c.dos64_destroy(self.machine);
    }
    pub fn symbol(self: *const Fixture, name: []const u8) !u16 {
        if (self.symbols.get(name)) |address| return address;
        std.debug.print("Missing linker symbol: {s}\n", .{name});
        return error.MissingSymbol;
    }
    pub fn peek(self: *const Fixture, address: u16) u8 { return c.dos64_peek(self.machine, address); }
    pub fn poke(self: *Fixture, address: u16, value: u8) void { c.dos64_poke(self.machine, address, value); }
    pub fn word(self: *const Fixture, address: u16) u16 { return @as(u16, self.peek(address)) | (@as(u16, self.peek(address+%1)) << 8); }

    fn checkUnitExtra(self: *const Fixture, writes: bool) !void {
        if (self.unit_extra) |code| for (code, 0..) |expected, index| {
            const address = 0xef00 + @as(u16, @intCast(index));
            if (self.peek(address) != expected or (writes and c.dos64_was_written(self.machine, address) != 0))
                return error.UnitFixtureCodeWrite;
        };
    }
    pub fn call(self: *Fixture, entry: []const u8, budget: u64) !c.Dos64Regs {
        const entry_address = try self.symbol(entry);
        try self.checkUnitExtra(false);
        if (self.unit_extra) |code| {
            if (entry_address >= 0xef00 and @as(u32, entry_address) < 0xef00 + code.len) {
                // EF00 code requires RAM+I/O visible, with driven port bits.
                if ((self.peek(0) & 7) != 7 or (self.peek(1) & 7) != 5) return error.UnitFixtureBank;
                if (self.peek(try self.symbol("dos64_cold_open")) != 0xa5 or
                    self.peek(try self.symbol("dos64_overlay_ready")) != 0 or
                    self.peek(try self.symbol("dos64_native_started")) != 0) return error.DiscardedUnitFixture;
            }
        }
        // Unit-only moved helpers exist only before bitmap ownership. Refuse
        // before seeding the host stack or changing native registers.
        if (self.symbols.get("__UNITCOLD_RUN__")) |cold_start| {
            const cold_size = self.symbols.get("__UNITCOLD_SIZE__") orelse 0;
            if (entry_address >= cold_start and @as(u32, entry_address) < @as(u32, cold_start) + cold_size and
                (self.peek(try self.symbol("dos64_cold_open")) != 0xa5 or self.peek(try self.symbol("dos64_overlay_ready")) != 0 or self.peek(try self.symbol("dos64_native_started")) != 0)) return error.DiscardedUnitFixture;
        }
        const sentinel = try self.symbol("fixture_return");
        const return_address = sentinel -% 1;
        self.poke(0x1ff, @intCast(return_address >> 8));
        self.poke(0x1fe, @truncate(return_address));
        c.dos64_clear_writes(self.machine);
        c.dos64_set_regs(self.machine, .{ .pc = entry_address, .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = self.initial_status, .cycles = 0, .instructions = 0 });
        const result = c.dos64_run(self.machine, sentinel, budget);
        try self.checkUnitExtra(true);
        self.last_regs = result.regs;
        self.stack_high_water = @max(self.stack_high_water, result.stack_high_water);
        return switch (result.status) {
            c.DOS64_RUN_RETURNED => result.regs,
            c.DOS64_RUN_MODEL_FAULT => error.UnsupportedDevice,
            c.DOS64_RUN_STACK_IMBALANCE => error.StackImbalance,
            c.DOS64_RUN_CYCLE_BUDGET => error.CycleBudget,
            c.DOS64_RUN_UNEXPECTED_BRK => error.UnexpectedBrk,
            else => error.InvalidRunnerStatus,
        };
    }
    pub fn expectStatus(self: *const Fixture, expected: u8) !void {
        if (self.peek(try self.symbol("dos64_mailbox")+1) != expected) return error.StatusMismatch;
    }
    pub fn verifyWrites(self: *const Fixture) !void {
        const state_start = try self.symbol("dos64_guest");
        const state_end = try self.symbol("dos64_mailbox_end");
        for (0..65536) |index| {
            const address: u16 = @intCast(index);
            if (c.dos64_was_written(self.machine, address) == 0) continue;
            if (address >= 0x100 and address < 0x200) continue;
            if (address >= state_start and address < state_end) continue;
            return error.ForbiddenWrite;
        }
    }
};

const std = @import("std");
pub const c = @cImport({ @cInclude("peddle_bridge.h"); });
const allocator = std.testing.allocator;

pub const Fixture = struct {
    machine: *c.Dos64Machine,
    labels: []u8,
    last_regs: ?c.Dos64Regs = null,
    stack_high_water: u8 = 0,
    initial_status: u8 = 0x24,

    pub fn init() !Fixture {
        const bytes = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.prg", allocator, .limited(65538));
        defer allocator.free(bytes);
        if (bytes.len < 3) return error.InvalidPrg;
        const address = std.mem.readInt(u16, bytes[0..2], .little);
        if (bytes.len - 2 > 65536 - @as(usize, address)) return error.InvalidPrg;
        const machine = c.dos64_create() orelse return error.CreateMachine;
        errdefer c.dos64_destroy(machine);
        c.dos64_load(machine, address, bytes[2..].ptr, bytes.len-2);
        const labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests.labels", allocator, .limited(1024*1024));
        return .{ .machine = machine, .labels = labels };
    }
    pub fn deinit(self: *Fixture) void {
        allocator.free(self.labels);
        c.dos64_destroy(self.machine);
    }
    pub fn symbol(self: *const Fixture, name: []const u8) !u16 {
        var lines = std.mem.splitScalar(u8, self.labels, '\n');
        while (lines.next()) |line| {
            var fields = std.mem.tokenizeAny(u8, line, " \t\r");
            if (!std.mem.eql(u8, fields.next() orelse continue, "al")) continue;
            const address = fields.next() orelse continue;
            const raw_name = fields.next() orelse continue;
            const candidate = if (raw_name[0] == '.') raw_name[1..] else raw_name;
            if (std.mem.eql(u8, candidate, name)) return std.fmt.parseInt(u16, address, 16);
        }
        std.debug.print("Missing linker symbol: {s}\n", .{name});
        return error.MissingSymbol;
    }
    pub fn peek(self: *const Fixture, address: u16) u8 { return c.dos64_peek(self.machine, address); }
    pub fn poke(self: *Fixture, address: u16, value: u8) void { c.dos64_poke(self.machine, address, value); }
    pub fn word(self: *const Fixture, address: u16) u16 { return @as(u16, self.peek(address)) | (@as(u16, self.peek(address+%1)) << 8); }

    pub fn call(self: *Fixture, entry: []const u8, budget: u64) !c.Dos64Regs {
        const sentinel = try self.symbol("fixture_return");
        const return_address = sentinel -% 1;
        self.poke(0x1ff, @intCast(return_address >> 8));
        self.poke(0x1fe, @truncate(return_address));
        c.dos64_clear_writes(self.machine);
        c.dos64_set_regs(self.machine, .{ .pc = try self.symbol(entry), .sp = 0xfd, .a = 0x71, .x = 0x82, .y = 0x93, .p = self.initial_status, .cycles = 0, .instructions = 0 });
        const start = c.dos64_get_regs(self.machine).cycles;
        while (true) {
            const regs = c.dos64_get_regs(self.machine);
            self.last_regs = regs;
            self.stack_high_water = @max(self.stack_high_water, 255-regs.sp);
            if (c.dos64_model_fault(self.machine) != 0) return error.UnsupportedDevice;
            if (regs.pc == sentinel) {
                if (regs.sp != 0xff) return error.StackImbalance;
                if (c.dos64_model_fault(self.machine) != 0) return error.UnsupportedDevice;
                return regs;
            }
            if (regs.cycles - start >= budget) return error.CycleBudget;
            if (self.peek(regs.pc) == 0) return error.UnexpectedBrk;
            c.dos64_step(self.machine);
        }
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

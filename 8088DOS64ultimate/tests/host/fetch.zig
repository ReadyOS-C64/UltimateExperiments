const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn word(f: *Fixture, location: u16, value: u16) void {
    f.poke(location, @truncate(value));
    f.poke(location + 1, @truncate(value >> 8));
}
fn address(f: *Fixture, physical: u32) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(physical));
    f.poke(a + 1, @truncate(physical >> 8));
    f.poke(a + 2, @truncate(physical >> 16));
}
fn initialize(frames: u8, mode: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    const r = try f.call("dos64_cache_init", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    f.poke(try f.symbol("dos64_memory_mode"), mode);
    _ = try f.call("dos64_fetch_init", 1000);
    return f;
}

// Both paths execute actual linked 6510 assembly. The retained old helper is
// intentionally independent of the span implementation; the host supplies only
// input bytes/actions and compares observable byte/failure/IP behavior.
const Pair = struct {
    fast: Fixture,
    slow: Fixture,
    fn init(frames: u8, mode: u8) !Pair {
        var fast = try initialize(frames, mode);
        errdefer fast.deinit();
        return .{ .fast = fast, .slow = try initialize(frames, mode) };
    }
    fn deinit(p: *Pair) void {
        p.fast.deinit();
        p.slow.deinit();
    }
    fn position(p: *Pair, cs: u16, ip: u16) !void {
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            const g = try f.symbol("dos64_guest");
            word(f, g + 18, cs);
            word(f, g + 24, ip);
        }
    }
    fn backing(p: *Pair, physical: u32, value: u8) void {
        c.dos64_reu_poke(p.fast.machine, physical, value);
        c.dos64_reu_poke(p.slow.machine, physical, value);
    }
    fn next(p: *Pair, expected: ?u8, error_code: u8) !void {
        const before = p.fast.word((try p.fast.symbol("dos64_guest")) + 24);
        const fast = try p.fast.call("dos64_fast_fetch", 10_000);
        const slow = try p.slow.call("cpu_fetch8_slow", 10_000);
        try std.testing.expectEqual(slow.p & 1, fast.p & 1);
        if (expected) |byte| {
            try std.testing.expectEqual(@as(u8, 0), fast.p & 1);
            try std.testing.expectEqual(byte, fast.a);
            try std.testing.expectEqual(slow.a, fast.a);
        } else {
            try std.testing.expectEqual(@as(u8, 1), fast.p & 1);
        }
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            try std.testing.expectEqual(error_code, f.peek(try f.symbol("dos64_memory_error")));
            try std.testing.expectEqual(before +% @as(u16, if (expected != null) 1 else 0), f.word((try f.symbol("dos64_guest")) + 24));
            // No stale code pin can prevent an operand using the sole frame.
            const pins = try f.symbol("dos64_cache_pins");
            for (0..32) |i| try std.testing.expectEqual(@as(u8, 0), f.peek(pins + @as(u16, @intCast(i))));
            try guards(f);
        }
    }
    fn operand(p: *Pair, physical: u32, value: ?u8) !void {
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            try address(f, physical);
            if (value) |v| f.poke(try f.symbol("dos64_mem_value"), v);
            const r = try f.call(if (value != null) "dos64_mem_write" else "dos64_mem_read", 10_000);
            try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        }
    }
    fn flushAndCompare(p: *Pair) !void {
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            const r = try f.call("dos64_cache_flush", 100_000);
            try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        }
        // Full backing comparison catches unexpected dirty writes/evictions;
        // byte expectations above remain independent of either path's output.
        const expected = try std.testing.allocator.alloc(u8, 1024 * 1024);
        defer std.testing.allocator.free(expected);
        try std.testing.expectEqual(@as(u8, 1), c.dos64_reu_read(p.slow.machine, 0, expected.ptr, expected.len));
        try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(p.fast.machine, 0, expected.ptr, expected.len));
    }
};

fn guards(f: *Fixture) !void {
    const zp = try f.symbol("__ZEROPAGE_RUN__");
    const zp_end = zp + try f.symbol("__ZEROPAGE_SIZE__");
    const bss = try f.symbol("__BSS_RUN__");
    const bss_end = bss + try f.symbol("__BSS_SIZE__");
    for (0..65536) |i| {
        const a: u16 = @intCast(i);
        if (c.dos64_was_written(f.machine, a) == 0) continue;
        if ((a >= zp and a < zp_end) or (a >= 0x100 and a < 0x200) or
            (a >= bss and a < bss_end) or (a >= 0x8000 and a < 0xc000) or
            (a >= 0xe100 and a < 0xe900) or (a >= 0xe900 and a < 0xe9c0) or
            a == 0 or a == 1 or (a >= 0xdf00 and a <= 0xdf0a)) continue;
        std.debug.print("Fetch wrote forbidden host address {x}\n", .{a});
        return error.FetchForbiddenWrite;
    }
}

fn pattern(i: usize) u8 {
    return @truncate(i *% 73 +% 19);
}

test "fast fetch matches slow byte path across every span byte and final boundary" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    try p.position(0, 0x1fe);
    for (0..1028) |i| p.backing(0x1fe + @as(u32, @intCast(i)), pattern(i));
    for (0..1028) |i| try p.next(pattern(i), 0);
    try std.testing.expectEqual(c.dos64_dma_transfers(p.slow.machine), c.dos64_dma_transfers(p.fast.machine));
    try p.flushAndCompare();
}

test "fast fetch does not pin code across one-frame operand eviction or dirty alias writes" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    try p.position(0x1234, 0x100);
    for (0..70) |i| p.backing(0x12440 + @as(u32, @intCast(i)), pattern(i));
    for (0..64) |i| {
        try p.next(pattern(i), 0);
        try p.operand(0x90000 + @as(u32, @intCast(i)), @truncate(i));
    }
    try p.next(pattern(64), 0);
    // Translate a different segment:offset alias through the real address ABI.
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
        word(f, try f.symbol("dos64_segment"), 0x1240);
        word(f, try f.symbol("dos64_offset"), 0x81);
        _ = try f.call("dos64_physical", 300);
        f.poke(try f.symbol("dos64_mem_value"), 0xb8);
        const r = try f.call("dos64_mem_write", 10_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    }
    // Backing remains old: this must read authoritative dirty frame bytes.
    try std.testing.expectEqual(pattern(65), c.dos64_reu_peek(p.fast.machine, 0x12481));
    try p.next(0xb8, 0);
    try p.next(pattern(66), 0);
    try p.flushAndCompare();
    try std.testing.expectEqual(@as(u8, 0xb8), c.dos64_reu_peek(p.fast.machine, 0x12481));
}

test "fast fetch validates CS and redirected IP and separately wraps offset and physical address" {
    var p = try Pair.init(2, 1);
    defer p.deinit();
    const starts = [_][2]u16{ .{ 0x1000, 0xfffd }, .{ 0xffff, 0x000d }, .{ 0xfff0, 0x00fd }, .{ 0x1234, 0xfffe } };
    for (starts) |start| {
        try p.position(start[0], start[1]);
        for (0..6) |i| {
            const ip = start[1] +% @as(u16, @intCast(i));
            p.backing((@as(u32, start[0]) * 16 + ip) & 0xfffff, pattern(i));
        }
        // New backing is seeded only after flushing/cold reset between runs.
        for (0..6) |i| try p.next(pattern(i), 0);
        try p.flushAndCompare();
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            _ = try f.call("dos64_cache_init", 50_000);
            f.poke(try f.symbol("dos64_memory_mode"), 1);
        }
    }
    p.backing(0x10100, 0x31);
    p.backing(0x20101, 0x42);
    p.backing(0x20200, 0x53);
    try p.position(0x1000, 0x100);
    try p.next(0x31, 0);
    try p.position(0x2000, 0x101); // Expected IP matches; CS does not.
    try p.next(0x42, 0);
    try p.position(0x2000, 0x200); // CS matches; expected IP does not.
    try p.next(0x53, 0);
    try p.flushAndCompare();
}

test "fast fetch cold reset validates ownership even when generation counters repeat" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    p.backing(0x100, 0x12);
    p.backing(0x101, 0x23);
    try p.position(0, 0x100);
    try p.next(0x12, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
        _ = try f.call("dos64_cache_init", 50_000);
        f.poke(try f.symbol("dos64_memory_mode"), 1);
    }
    // Reuse frame zero at generation one with a different tag. The stale
    // pointer would return this operand page's zero if ownership was skipped.
    try p.operand(0x70000, null);
    try p.next(0x23, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
        _ = try f.call("dos64_cache_init", 50_000);
        f.poke(try f.symbol("dos64_memory_mode"), 1);
    }
    p.backing(0x102, 0x81);
    try p.next(0x81, 0); // Cold invalid flags force refill before any pointer use.
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
        _ = try f.call("dos64_cache_init", 50_000);
        f.poke(try f.symbol("dos64_memory_mode"), 1);
    }
    p.backing(0x103, 0x91);
    // Same frame+tag+generation after reset is also safe: direct bytes come
    // from the newly loaded frame, never from a stale prefetched byte array.
    try p.operand(0x100, null);
    try p.next(0x91, 0);
    try p.flushAndCompare();
}

test "fast fetch retains PC holes ROM CGA and bus-mode failure behavior" {
    var p = try Pair.init(1, 0);
    defer p.deinit();
    for ([_]u32{ 0x9ffff, 0xa0000, 0xb7fff, 0xb8000, 0xbbfff, 0xbc000, 0xeffff, 0xf0000, 0xfffff, 0 }) |physical| {
        // Set a representable segment:offset with the target physical byte.
        const cs: u16 = @intCast(physical >> 4);
        const ip: u16 = @intCast(physical & 15);
        p.backing(physical, 0x6d);
        try p.position(cs, ip);
        const hole = physical >= 0xa0000 and physical < 0xf0000 and !(physical >= 0xb8000 and physical < 0xbc000);
        try p.next(if (hole) 0xff else 0x6d, 0);
    }
    try p.position(0, 0x100);
    try p.operand(0x100, 0x41);
    try p.next(0x41, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| f.poke(try f.symbol("dos64_memory_mode"), 2);
    try p.next(null, 5);
}

test "fast fetch preserves IP on fresh span boundary and cache initialization failures" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    p.backing(0x1ff, 0x77);
    try p.position(0, 0x1ff);
    try p.next(0x77, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| c.dos64_reu_fail_after(f.machine, 0, 17);
    try p.next(null, 3);
    // Failed load did not publish bytes; a fresh retry sees the backing page.
    p.backing(0x200, 0x88);
    try p.next(0x88, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }) |f| f.poke(try f.symbol("dos64_cache_ready"), 0);
    try p.next(null, 4);
    try p.position(0, 0x3333);
    try p.next(null, 4);
}

test "fast fetch bounded long prefix slices preserve the original CPU contract" {
    var f = try initialize(1, 1);
    defer f.deinit();
    _ = try f.call("dos64_cpu_init", 10_000);
    const g = try f.symbol("dos64_guest");
    word(&f, g + 18, 0x1234);
    word(&f, g + 24, 0xffc0);
    for (0..131) |i| {
        const ip = @as(u16, 0xffc0) +% @as(u16, @intCast(i));
        c.dos64_reu_poke(f.machine, (@as(u32, 0x1234) * 16 + ip) & 0xfffff, if (i < 130) 0x2e else 0x90);
    }
    for (0..3) |i| {
        const r = try f.call("dos64_cpu_step", 100_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        try std.testing.expectEqual(@as(u8, if (i < 2) 1 else 0), f.peek(try f.symbol("dos64_cpu_yield")));
        try std.testing.expectEqual(@as(u16, if (i < 2) 0 else 1), f.word(try f.symbol("dos64_cpu_instructions")));
    }
    try std.testing.expectEqual(@as(u16, 0x43), f.word(g + 24));
}

test "fast fetch reports all-frames-pinned failure and never consumes the failing byte" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    p.backing(0x100, 0x11);
    p.backing(0x101, 0x22);
    try p.position(0, 0x100);
    try p.next(0x11, 0);
    for ([_]*Fixture{ &p.fast, &p.slow }, [_][]const u8{ "dos64_fast_fetch", "cpu_fetch8_slow" }) |f, entry| {
        try address(f, 0x80000);
        var r = try f.call("dos64_cache_acquire", 10_000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
        const frame = f.peek(try f.symbol("dos64_cache_selected"));
        r = try f.call(entry, 10_000);
        try std.testing.expectEqual(@as(u8, 1), r.p & 1);
        try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_memory_error")));
        try std.testing.expectEqual(@as(u16, 0x101), f.word((try f.symbol("dos64_guest")) + 24));
        try std.testing.expectEqual(@as(u8, 1), f.peek((try f.symbol("dos64_cache_pins")) + frame));
        f.poke(try f.symbol("dos64_cache_selected"), frame);
        r = try f.call("dos64_cache_release", 1000);
        try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    }
    try p.next(0x22, 0);
    try p.flushAndCompare();
}

test "fast fetch warm sequential helper costs less than the retained assembly byte path" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    try p.position(0, 0x100);
    for (0..128) |i| p.backing(0x100 + @as(u32, @intCast(i)), pattern(i));
    try p.next(pattern(0), 0); // Exclude both refill paths from warm measurement.
    var fast_cycles: u64 = 0;
    var slow_cycles: u64 = 0;
    for (1..128) |i| {
        const fast_before = c.dos64_get_regs(p.fast.machine).cycles;
        const slow_before = c.dos64_get_regs(p.slow.machine).cycles;
        try p.next(pattern(i), 0);
        fast_cycles += c.dos64_get_regs(p.fast.machine).cycles - fast_before;
        slow_cycles += c.dos64_get_regs(p.slow.machine).cycles - slow_before;
    }
    try std.testing.expect(fast_cycles < slow_cycles);
    std.debug.print("Warm actual-assembly fetch 127 bytes: fast={d} slow={d} host CPU cycles (functional DMA; no physical throughput claim)\n", .{ fast_cycles, slow_cycles });
    try p.flushAndCompare();
}

test "fast fetch improves a complete register and taken-branch guest workload with full RAM checks" {
    var p = try Pair.init(1, 1);
    defer p.deinit();
    const code = [_]u8{ 0xb8, 0, 0, 0xbb, 1, 0, 0xb9, 0x80, 0, 0x01, 0xd8, 0xe2, 0xfc, 0x3d, 0x80, 0, 0xf4 };
    for (code, 0..) |byte, i| p.backing(0x100 + @as(u32, @intCast(i)), byte);
    // Route this second machine's aliased fetch entry to the independent retained
    // slow assembly helper. Host patching selects the implementation only;
    // all guest dispatch, arithmetic, branches and memory stay real assembly.
    const wrapper = try p.slow.symbol("cpu_fetch8");
    try std.testing.expectEqual(try p.slow.symbol("dos64_fast_fetch"), wrapper);
    try std.testing.expectEqual(@as(u8, 0xa5), p.slow.peek(wrapper));
    try std.testing.expectEqual(@as(u8, @intCast(try p.slow.symbol("fetch_valid"))), p.slow.peek(wrapper + 1));
    p.slow.poke(wrapper, 0x4c);
    word(&p.slow, wrapper + 1, try p.slow.symbol("cpu_fetch8_slow"));
    try routeSlowWord(&p.slow);
    const golden = try std.testing.allocator.alloc(u8, 1024 * 1024);
    defer std.testing.allocator.free(golden);
    @memset(golden, 0);
    @memcpy(golden[0x100..][0..code.len], &code);
    for ([_][]const u8{ "cold", "warm" }) |phase| {
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| _ = try f.call("dos64_cpu_init", 10_000);
        try p.position(0, 0x100);
        const fast_before = c.dos64_get_regs(p.fast.machine).cycles;
        const slow_before = c.dos64_get_regs(p.slow.machine).cycles;
        for (0..261) |_| {
            for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
                const r = try f.call("dos64_cpu_step", 100_000);
                try std.testing.expectEqual(@as(u8, 0), r.p & 1);
                try guards(f);
            }
            const fast_guest = try p.fast.symbol("dos64_guest");
            const slow_guest = try p.slow.symbol("dos64_guest");
            for (0..28) |i| try std.testing.expectEqual(p.slow.peek(slow_guest + @as(u16, @intCast(i))), p.fast.peek(fast_guest + @as(u16, @intCast(i))));
        }
        const fast_cycles = c.dos64_get_regs(p.fast.machine).cycles - fast_before;
        const slow_cycles = c.dos64_get_regs(p.slow.machine).cycles - slow_before;
        try std.testing.expect(fast_cycles < slow_cycles);
        for ([_]*Fixture{ &p.fast, &p.slow }) |f| {
            const g = try f.symbol("dos64_guest");
            try std.testing.expectEqual(@as(u16, 128), f.word(g));
            try std.testing.expectEqual(@as(u16, 0), f.word(g + 2));
            try std.testing.expectEqual(@as(u16, 1), f.word(g + 6));
            try std.testing.expectEqual(@as(u16, 0x111), f.word(g + 24));
            try std.testing.expectEqual(@as(u16, 0xf046), f.word(g + 26));
            try std.testing.expectEqual(@as(u8, 1), f.peek(try f.symbol("dos64_cpu_status")));
            try std.testing.expectEqual(@as(u16, 261), f.word(try f.symbol("dos64_cpu_instructions")));
            const r = try f.call("dos64_cache_flush", 100_000);
            try std.testing.expectEqual(@as(u8, 0), r.p & 1);
            try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0, golden.ptr, golden.len));
        }
        std.debug.print("Verified {s} 261-instruction register/branch workload: fast={d} slow={d} host CPU cycles (no physical throughput claim)\n", .{ phase, fast_cycles, slow_cycles });
    }
}

fn routeSlowWord(f: *Fixture) !void {
    // Word immediates own their adjacent continuation inside cpu_fetch16.
    // Redirect both internal JSRs as well: the comparison path must remain
    // the independent slow byte helper, never a stale or hybrid fast span.
    const fetch_word = try f.symbol("cpu_fetch16");
    const fetch_fast = try f.symbol("dos64_fast_fetch");
    const fetch_owned = try f.symbol("dos64_fetch_owned_next");
    var redirects: usize = 0;
    for (0..20) |i| {
        const at = fetch_word + @as(u16, @intCast(i));
        if (f.peek(at) != 0x20) continue;
        const target = f.word(at + 1);
        if (target != fetch_fast and target != fetch_owned) continue;
        word(f, at + 1, try f.symbol("cpu_fetch8_slow"));
        redirects += 1;
    }
    try std.testing.expectEqual(@as(usize, 2), redirects);

}

test "owned immediate words retain independent slow-byte behavior at PC frame IP and physical seams" {
    const golden = try std.testing.allocator.alloc(u8, 1024 * 1024);
    defer std.testing.allocator.free(golden);
    for (golden, 0..) |*v, i| v.* = @truncate(i * 17 + (i >> 8));
    for ([_]u8{0, 1}) |mode| {
        var p = try Pair.init(1, mode);
        defer p.deinit();
        try routeSlowWord(&p.slow);
        for (golden, 0..) |v, i| p.backing(@intCast(i), v);
        for ([_]u16{0, 0x9fff, 0xafff, 0xb7ff, 0xbbff, 0xefff, 0xffff}) |cs| {
            for ([_]u16{0, 0xfe00}) |window| {
                for (0..512) |i| {
                    const ip:u16=window|@as(u16,@intCast(i));
                    try p.position(cs,ip);
                    const low=(@as(u32,cs)*16+ip)&0xfffff;
                    const high=(@as(u32,cs)*16+(ip+%1))&0xfffff;
                    var expected:u16=0;
                    for ([_]u32{low,high},0..) |at,byte| {
                        const read=mode==1 or at<0xa0000 or at>=0xf0000 or (at>=0xb8000 and at<0xbc000);
                        expected|=@as(u16,if(read)golden[at] else 0xff)<<@as(u4,@intCast(byte*8));
                    }
                    const fast=try p.fast.call("cpu_fetch16",100000);
                    const slow=try p.slow.call("cpu_fetch16",100000);
                    try std.testing.expectEqual(@as(u8,0),fast.p&1);
                    try std.testing.expectEqual(slow.p&1,fast.p&1);
                    for ([_]*Fixture{&p.fast,&p.slow}) |f| {
                        try std.testing.expectEqual(expected,f.word(try f.symbol("dos64_cpu_value")));
                        try std.testing.expectEqual(ip+%2,f.word((try f.symbol("dos64_guest"))+24));
                        try guards(f);
                    }
                }
            }
        }
        for ([_]*Fixture{&p.fast,&p.slow}) |f| {
            _=try f.call("dos64_cache_flush",100000);
            try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0,golden.ptr,golden.len));
        }
    }
}

const std = @import("std");
const host = @import("machine_future.zig");
const F = host.Fixture;
const c = host.c;
fn put(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn get(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn call(f: *F, n: []const u8, carry: u8) !void {
    const r = try f.call(n, 1_000_000);
    try std.testing.expectEqual(carry, r.p & 1);
}
fn init() !F {
    var f = try F.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    try call(&f, "dos64_overlay_init", 0);
    try put(&f, "dos64_overlay_reu_mib", 4);
    for(0xfe00..0x10000)|at|f.poke(@intCast(at),@truncate(at^0xa5));
    try call(&f, "dos64_overlay_bootstrap", 0);
    return f;
}
fn acquire(f: *F, id: u8) !void {
    try put(f, "dos64_overlay_requested", id);
    try call(f, "dos64_overlay_acquire", 0);
}
fn release(f: *F) !void {
    try call(f, "dos64_overlay_release", 0);
}
test "eight assets commit before cache frames are reclaimed and every payload switches exactly" {
    var f = try init();
    defer f.deinit();
    const assets = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "build/dos64-tests-overlay-startup.bin", std.testing.allocator, .limited(16385));
    defer std.testing.allocator.free(assets);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, assets.ptr, assets.len));
    try std.testing.expectEqual(@as(u64, 8), c.dos64_dma_transfers(f.machine));
    var shadow:[3584]u8=undefined;for(&shadow,0..)|*v,i|{v.*=f.peek(@intCast(0xa000+i));try std.testing.expectEqual(v.*,f.peek(@intCast(0xf000+i)));}
    if(f.symbols.contains("__CPUTRAP_SIZE__")){
        for(0..256)|i|try std.testing.expectEqual(f.peek(0xae00+@as(u16,@intCast(i))),f.peek(0xfe00+@as(u16,@intCast(i))));
    }
    const untouched:usize=if(f.symbols.contains("__CPUTRAP_SIZE__"))0xff00 else 0xfe00;
    for(untouched..0x10000)|at|try std.testing.expectEqual(@as(u8,@truncate(at^0xa5)),f.peek(@intCast(at)));
    try std.testing.expectEqual(@as(u8,0xa5),try get(&f,"hdb_extension_ready"));
    // Four asset slots use16 cacheframes; separate3584-byte source uses7.
    for (0x8000..0xc000) |a| f.poke(@intCast(a), 0xee);
    for ([_]u8{ 7, 4, 5, 6, 1, 2, 3, 6, 5, 4, 7 }) |id| {
        try acquire(&f, id);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_busy"));
        const slot = assets[(if(id==7) @as(usize,7) else @as(usize,id)-1) * 2048 ..][0..2048];
        const len = std.mem.readInt(u16, slot[6..8], .little);
        for (slot[16..][0..len], 0..) |v, i| try std.testing.expectEqual(v, f.peek(0xc900 + @as(u16, @intCast(i))));
        try release(&f);
        try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    }
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, 0x340000, assets.ptr, assets.len));
    for(shadow,0..)|v,i|try std.testing.expectEqual(v,f.peek(@intCast(0xf000+i)));
}
test "PIT wrappers hold one combined image for nested helper calls and release success and failure carry" {
    var f = try init();
    defer f.deinit();
    try call(&f, "dos64_overlay_pit_init", 0);
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    const now = try f.symbol("dos64_pit_now");
    for (0..4) |i| f.poke(now + @as(u16, @intCast(i)), @truncate(@as(u32, 985248) >> @as(u5, @intCast(i * 8))));
    try call(&f, "dos64_overlay_pit_advance", 0);
    try std.testing.expectEqual(@as(u16, 13533), f.word(try f.symbol("dos64_pit_phase")));
    try put(&f, "dos64_irq_line", 8);
    try call(&f, "dos64_overlay_irq_pulse", 1);
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    try put(&f, "dos64_irq_line", 0);
    try call(&f, "dos64_overlay_irq_pulse", 0);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_pic_irr"));
    try put(&f, "dos64_pit_ready", 0);
    try call(&f, "dos64_overlay_pit_rebase", 1);
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
}
test "PIT frame injection reaches resident cache and stack under its lease then returns resident" {
    var f = try init();
    defer f.deinit();
    try put(&f, "dos64_cache_limit", 1);
    try call(&f, "dos64_cache_init", 0);
    try call(&f, "dos64_cpu_init", 0);
    const g = try f.symbol("dos64_guest");
    f.poke(g + 26, 2);
    f.poke(g + 27, 0xf2);
    f.poke(g + 8, 0);
    f.poke(g + 9, 1);
    f.poke(g + 20, 0);
    f.poke(g + 21, 0x20);
    f.poke(g + 18, 0);
    f.poke(g + 19, 0x10);
    f.poke(g + 24, 0x34);
    f.poke(g + 25, 0x12);
    try put(&f, "dos64_pic_phase", 0);
    try put(&f, "dos64_pic_icw1", 0x13);
    try put(&f, "dos64_pic_icw4", 1);
    try put(&f, "dos64_pic_base", 8);
    try put(&f, "dos64_pic_imr", 0);
    try put(&f, "dos64_pic_irr", 1);
    try put(&f, "dos64_pic_isr", 0);
    try put(&f, "dos64_pic_priority", 7);
    c.dos64_reu_poke(f.machine, 32, 0x78);
    c.dos64_reu_poke(f.machine, 33, 0x56);
    c.dos64_reu_poke(f.machine, 34, 0x00);
    c.dos64_reu_poke(f.machine, 35, 0x30);
    try call(&f, "dos64_overlay_irq_try", 0);
    try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_irq_result"));
    try std.testing.expectEqual(@as(u16, 0x5678), f.word(g + 24));
    try std.testing.expectEqual(@as(u16, 0x3000), f.word(g + 18));
    try std.testing.expectEqual(@as(u16, 0xfa), f.word(g + 8));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(try f.symbol("fixture_return"), f.last_regs.?.pc);
}
test "fifth GFX wrapper rejects early bitmap ownership and releases target argument failure" {
    var f = try init();
    defer f.deinit();
    try call(&f, "dos64_overlay_render_graphics_line", 1);
    try std.testing.expectEqual(@as(u8, 8), try get(&f, "dos64_overlay_error"));
    try put(&f, "dos64_bios_ready", 0xa5);
    try put(&f, "dos64_import_state", 0);
    try call(&f, "dos64_cold_release", 0);
    for (0x7000..0x8000) |a| f.poke(@intCast(a), 0);
    try put(&f, "dos64_render_graphics_request", 200);
    try call(&f, "dos64_overlay_render_graphics_line", 1);
    try std.testing.expectEqual(@as(u8, 5), try get(&f, "dos64_overlay_current"));
    try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
    try std.testing.expectEqual(@as(u8, 2), f.peek((try f.symbol("dos64_render_graphics_request")) + 2));
}
test "fourth and fifth partial replacements invalidate current and preserve target state until retry" {
    for ([_]u8{ 4, 5 }) |id| {
        for ([_]u32{ 0, 1 }) |after| {
            var f = try init();
            defer f.deinit();
            try acquire(&f, 1);
            try release(&f);
            try put(&f, "dos64_overlay_requested", id);
            c.dos64_reu_fail_after(f.machine, after, 17);
            try call(&f, "dos64_overlay_acquire", 1);
            try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_current"));
            try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
            try acquire(&f, id);
            try std.testing.expectEqual(id, try get(&f, "dos64_overlay_current"));
            try release(&f);
        }
    }
}

test "new asset headers validate all bytes before publishing their code" {
    for ([_]u8{ 4, 5 }) |id| {
        for (0..16) |index| {
            var f = try init();
            defer f.deinit();
            const far = @as(u32, 0x340000) + (@as(u32, id) - 1) * 2048 + @as(u32, @intCast(index));
            const saved = c.dos64_reu_peek(f.machine, far);
            c.dos64_reu_poke(f.machine, far, saved ^ 0xff);
            try put(&f, "dos64_overlay_requested", id);
            try call(&f, "dos64_overlay_acquire", 1);
            try std.testing.expectEqual(@as(u8, 4), try get(&f, "dos64_overlay_error"));
            try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_current"));
            try std.testing.expectEqual(@as(u8, 0), try get(&f, "dos64_overlay_busy"));
            c.dos64_reu_poke(f.machine, far, saved);
            try acquire(&f, id);
            try release(&f);
        }
    }
}
test "every new wrapper refuses reentry before target state or requested identity changes" {
    for ([_][]const u8{ "pit_init", "pit_rebase", "pit_advance", "pit_poll", "irq_pulse", "irq_select", "irq_try", "irq_repeat", "render_graphics_line" }) |name| {
        var f = try init();
        defer f.deinit();
        try put(&f, "dos64_overlay_busy", 1);
        try put(&f, "dos64_overlay_requested", 3);
        try put(&f, "dos64_overlay_current", 2);
        const n = try std.fmt.allocPrint(std.testing.allocator, "dos64_overlay_{s}", .{name});
        defer std.testing.allocator.free(n);
        try call(&f, n, 1);
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_error"));
        try std.testing.expectEqual(@as(u8, 1), try get(&f, "dos64_overlay_busy"));
        try std.testing.expectEqual(@as(u8, 2), try get(&f, "dos64_overlay_current"));
        try std.testing.expectEqual(@as(u8, 3), try get(&f, "dos64_overlay_requested"));
    }
}

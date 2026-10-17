const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const allocator = std.testing.allocator;
fn word(f: *Fixture, address: u16, value: u16) void {
    f.poke(address, @truncate(value));
    f.poke(address + 1, @truncate(value >> 8));
}
fn far(f: *Fixture, address: u16, value: u32) void {
    for (0..3) |i| f.poke(address + @as(u16, @intCast(i)), @truncate(value >> @as(u5, @intCast(i * 8))));
}
fn getFar(f: *Fixture, address: u16) u32 {
    return @as(u32, f.peek(address)) | (@as(u32, f.peek(address + 1)) << 8) | (@as(u32, f.peek(address + 2)) << 16);
}
fn init(frames: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine); f.poke(0,0x2f); f.poke(1,0x35);
    _ = try f.call("dos64_overlay_init", 100_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"),4);
    _ = try f.call("dos64_overlay_bootstrap",1_000_000);
    f.poke(try f.symbol("dos64_overlay_requested"),7);
    _ = try f.call("dos64_overlay_acquire",100_000);
    _ = try f.call("dos64_overlay_release",100_000);
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    f.poke(try f.symbol("dos64_memory_mode"), 1);
    _ = try f.call("dos64_cpu_init", 10_000);
    _ = try f.call("dos64_disk_init", 10_000);
    f.poke(try f.symbol("dos64_disk_loaded"), 1);
    return f;
}
fn request(f: *Fixture, function: u8, count: u8, cylinder: u16, head: u8, sector: u8, es: u16, bx: u16) !void {
    const g = try f.symbol("dos64_guest");
    word(f, g, (@as(u16, function) << 8) | count);
    word(f, g + 2, (cylinder << 8) | ((cylinder >> 2) & 0xc0) | sector);
    word(f, g + 4, @as(u16, head) << 8);
    word(f, g + 6, bx);
    word(f, g + 16, es);
}
fn transfer(f: *Fixture, status: u8, count: u8) !void {
    const g = try f.symbol("dos64_guest");
    var before: [28]u8 = undefined;
    for (&before, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    const regs = try f.call("dos64_disk_transfer", 80_000_000);
    try std.testing.expectEqual(status, regs.a);
    try std.testing.expectEqual(@as(u8, if (status == 0) 0 else 1), regs.p & 1);
    try std.testing.expectEqual(@as(u16, status) << 8 | count, f.word(g));
    try std.testing.expectEqual(status, f.peek(try f.symbol("dos64_disk_last_status")));
    for (before[2..], 2..) |v, i| try std.testing.expectEqual(v, f.peek(g + @as(u16, @intCast(i))));
}
fn writeGuest(f: *Fixture, address: u32, value: u8) !void {
    far(f, try f.symbol("dos64_address"), address);
    f.poke(try f.symbol("dos64_mem_value"), value);
    const regs = try f.call("dos64_mem_write", 20_000);
    try std.testing.expectEqual(@as(u8, 0), regs.p & 1);
}
fn readGuest(f: *Fixture, address: u32) !u8 {
    far(f, try f.symbol("dos64_address"), address);
    const regs = try f.call("dos64_mem_read", 20_000);
    try std.testing.expectEqual(@as(u8, 0), regs.p & 1);
    return regs.a;
}
fn pattern(address: usize) u8 { return @truncate((address * 13) ^ (address >> 8) ^ 0xa7); }

test "disk init explicitly configures unloaded 360 KiB media and reset requires no image" {
    var f = try init(1);
    defer f.deinit();
    const initial_dma = c.dos64_dma_transfers(f.machine);
    _ = try f.call("dos64_disk_init", 10_000);
    try std.testing.expectEqual(@as(u32, 0x100000), getFar(&f, try f.symbol("dos64_disk_reu_base")));
    try std.testing.expectEqual(@as(u16, 720), f.word(try f.symbol("dos64_disk_sectors")));
    try std.testing.expectEqual(@as(u16, 40), f.word(try f.symbol("dos64_disk_cylinders")));
    try std.testing.expectEqual(@as(u8, 2), f.peek(try f.symbol("dos64_disk_heads")));
    try std.testing.expectEqual(@as(u8, 9), f.peek(try f.symbol("dos64_disk_spt")));
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_disk_loaded")));
    try request(&f, 0, 7, 0, 0, 0, 0, 0);
    try transfer(&f, 0, 0);
    try request(&f, 2, 1, 0, 0, 1, 0, 0);
    try transfer(&f, 0x80, 0);
    try std.testing.expectEqual(initial_dma, c.dos64_dma_transfers(f.machine));
}

test "all 720 CHS sectors match independent linear addressing and verify reads data without guest writes" {
    var f = try init(1);
    defer f.deinit();
    f.initial_status = 0x28;
    const base: u32 = 0x10ff80;
    far(&f, try f.symbol("dos64_disk_reu_base"), base);
    for (0..360 * 1024) |i| c.dos64_reu_poke(f.machine, base + @as(u32, @intCast(i)), pattern(i));
    const r = try f.symbol("dos64_range_request");
    const buffer = try f.symbol("dos64_range_buffer");
    const epoch = try f.symbol("dos64_write_epoch");
    f.poke(0xbfff, 0x29);
    f.poke(0xc100, 0x83);
    f.poke(0xcfff, 0xb7);
    for (0..40) |cylinder| for (0..2) |head| for (1..10) |sector| {
        const lba = (cylinder * 2 + head) * 9 + sector - 1;
        try request(&f, 4, 1, @intCast(cylinder), @intCast(head), @intCast(sector), 0, 0x2000);
        try transfer(&f, 0, 1);
        try std.testing.expectEqual(base + @as(u32, @intCast((lba + 1) * 512)), getFar(&f, r + 3));
        try std.testing.expectEqual(@as(u16, 512), f.word(r + 11));
        // Unaligned source starts require first128, then256, then128 bytes.
        for (0..128) |i| try std.testing.expectEqual(pattern(lba * 512 + 384 + i), f.peek(buffer + @as(u16, @intCast(i))));
        try std.testing.expectEqual(@as(u16, 0), f.word(epoch));
        try std.testing.expectEqual(@as(u8, 8), f.last_regs.?.p & 0x0c);
    };
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x2000));
    try std.testing.expectEqual(@as(u8, 0x29), f.peek(0xbfff));
    try std.testing.expectEqual(@as(u8, 0x83), f.peek(0xc100));
    try std.testing.expectEqual(@as(u8, 0xb7), f.peek(0xcfff));
}

test "disk reads cross track page and REU bank seams and writes export dirty coherent bytes" {
    const path = "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img";
    const original = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, allocator, .limited(400 * 1024));
    defer allocator.free(original);
    try std.testing.expectEqual(@as(usize, 360 * 1024), original.len);
    const expected = try allocator.dupe(u8, original);
    defer allocator.free(expected);
    var f = try init(2);
    defer f.deinit();
    const base: u32 = 0x10ff80;
    far(&f, try f.symbol("dos64_disk_reu_base"), base);
    for (original, 0..) |value, i| c.dos64_reu_poke(f.machine, base + @as(u32, @intCast(i)), value);
    c.dos64_reu_poke(f.machine, base - 1, 0x69);
    c.dos64_reu_poke(f.machine, base + @as(u32, @intCast(original.len)), 0x96);
    try writeGuest(&f, 0x1f7f, 0xc3);
    try writeGuest(&f, 0x2380, 0x5a);
    // Last sector of head0 followed by first sector of head1: explicit linear-cross policy.
    try request(&f, 2, 2, 0, 0, 9, 0, 0x1f80);
    try transfer(&f, 0, 2);
    for (original[8 * 512 .. 10 * 512], 0..) |value, i| try std.testing.expectEqual(value, try readGuest(&f, 0x1f80 + @as(u32, @intCast(i))));
    try std.testing.expectEqual(@as(u8, 0xc3), try readGuest(&f, 0x1f7f));
    try std.testing.expectEqual(@as(u8, 0x5a), try readGuest(&f, 0x2380));
    // Modify a resident dirty byte; disk export must see it before backing flush.
    const modified: u8 = original[8 * 512 + 17] ^ 0xff;
    try writeGuest(&f, 0x1f91, modified);
    expected[8 * 512 + 17] = modified;
    try request(&f, 3, 2, 0, 0, 9, 0, 0x1f80);
    try transfer(&f, 0, 2);
    try std.testing.expectEqual(@as(u32, 0xffffffff), c.dos64_reu_compare(f.machine, base, expected.ptr, expected.len));
    try std.testing.expectEqual(@as(u8, 0x69), c.dos64_reu_peek(f.machine, base - 1));
    try std.testing.expectEqual(@as(u8, 0x96), c.dos64_reu_peek(f.machine, base + @as(u32, @intCast(original.len))));
    const reread = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, path, allocator, .limited(400 * 1024));
    defer allocator.free(reread);
    try std.testing.expectEqualSlices(u8, original, reread);
}

test "physical 64 KiB DMA limits allow exact end and reject crossing even inside BX window" {
    const cases = [_]struct { es: u16, bx: u16, count: u8, status: u8 }{
        .{ .es = 0, .bx = 0xfe00, .count = 1, .status = 0 },
        .{ .es = 0, .bx = 0xfe01, .count = 1, .status = 9 },
        .{ .es = 0x0fff, .bx = 0, .count = 1, .status = 9 },
        .{ .es = 0x1000, .bx = 0, .count = 127, .status = 0 },
        .{ .es = 0x1000, .bx = 0x0200, .count = 127, .status = 0 },
        .{ .es = 0x1000, .bx = 0x0201, .count = 127, .status = 9 },
        .{ .es = 0xffe0, .bx = 0, .count = 1, .status = 0 },
    };
    for (cases) |case| {
        var f = try init(1);
        defer f.deinit();
        const initial_dma = c.dos64_dma_transfers(f.machine);
        try request(&f, 4, case.count, 0, 0, 1, case.es, case.bx);
        try transfer(&f, case.status, if (case.status == 0) case.count else 0);
        if (case.status != 0) try std.testing.expectEqual(initial_dma, c.dos64_dma_transfers(f.machine));
    }
}

test "CHS geometry count drive and slot errors fail before DMA or guest writes" {
    const cases = [_]struct { command: u8 = 2, count: u8 = 1, cylinder: u16 = 0, head: u8 = 0, sector: u8 = 1, drive: u8 = 0, loaded: u8 = 1, status: u8 = 4 }{
        .{ .command = 1, .status = 0 }, .{ .command = 5, .status = 1 },
        .{ .count = 0 }, .{ .count = 128 }, .{ .cylinder = 40 },
        .{ .cylinder = 256 }, .{ .head = 2 }, .{ .sector = 0 }, .{ .sector = 10 },
        .{ .cylinder = 39, .head = 1, .sector = 9, .count = 2 },
        .{ .drive = 1, .status = 0x80 }, .{ .loaded = 0, .status = 0x80 },
    };
    for (cases) |case| {
        var f = try init(1);
        defer f.deinit();
        const initial_dma = c.dos64_dma_transfers(f.machine);
        const g = try f.symbol("dos64_guest");
        try request(&f, case.command, case.count, case.cylinder, case.head, case.sector, 0, 0x2000);
        f.poke(g + 4, case.drive);
        f.poke(try f.symbol("dos64_disk_loaded"), case.loaded);
        try transfer(&f, case.status, 0);
        try std.testing.expectEqual(initial_dma, c.dos64_dma_transfers(f.machine));
        try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(f.machine, 0x2000));
    }
    const configs = [_]struct { cylinders: u16 = 40, heads: u8 = 2, spt: u8 = 9, sectors: u16 = 720, base: u32 = 0x100000, status: u8 = 4 }{
        .{ .cylinders = 0 }, .{ .cylinders = 1025 }, .{ .heads = 0 }, .{ .spt = 0 }, .{ .spt = 64 },
        .{ .sectors = 719 }, .{ .cylinders = 1024, .heads = 255, .spt = 63, .sectors = 0 },
        .{ .base = 0x0fffff, .status = 0x20 }, .{ .base = 0x3ffff0, .status = 0x20 },
        .{ .cylinders = 1024, .heads = 1, .spt = 63, .sectors = 64512, .status = 0x20 },
        .{ .base = 0xffff00, .status = 0x20 },
    };
    for (configs) |config| {
        var f = try init(1);
        defer f.deinit();
        const initial_dma = c.dos64_dma_transfers(f.machine);
        word(&f, try f.symbol("dos64_disk_cylinders"), config.cylinders);
        word(&f, try f.symbol("dos64_disk_sectors"), config.sectors);
        f.poke(try f.symbol("dos64_disk_heads"), config.heads);
        f.poke(try f.symbol("dos64_disk_spt"), config.spt);
        far(&f, try f.symbol("dos64_disk_reu_base"), config.base);
        try request(&f, 2, 1, 0, 0, 1, 0, 0x2000);
        try transfer(&f, config.status, 0);
        try std.testing.expectEqual(initial_dma, c.dos64_dma_transfers(f.machine));
    }
}

test "10-bit cylinder translation and exact 4 MiB image end are checked without overflow" {
    var f = try init(1);
    defer f.deinit();
    word(&f, try f.symbol("dos64_disk_cylinders"), 301);
    word(&f, try f.symbol("dos64_disk_sectors"), 301);
    f.poke(try f.symbol("dos64_disk_heads"), 1);
    f.poke(try f.symbol("dos64_disk_spt"), 1);
    for ([_]u16{ 255, 256, 300 }) |cylinder| {
        try request(&f, 4, 1, cylinder, 0, 1, 0, 0x2000);
        try transfer(&f, 0, 1);
        try std.testing.expectEqual(0x100000 + (@as(u32, cylinder) + 1) * 512, getFar(&f, (try f.symbol("dos64_range_request")) + 3));
    }
    _ = try f.call("dos64_disk_init", 10_000);
    f.poke(try f.symbol("dos64_disk_loaded"), 1);
    far(&f, try f.symbol("dos64_disk_reu_base"), 0x3a6000);
    try request(&f, 4, 1, 39, 1, 9, 0, 0x2000);
    try transfer(&f, 0, 1);
    try std.testing.expectEqual(@as(u32, 0x400000), getFar(&f, (try f.symbol("dos64_range_request")) + 3));
}

test "verify and range failures report only complete sectors and never false success" {
    var verify = try init(1);
    defer verify.deinit();
    try request(&verify, 4, 2, 0, 0, 1, 0, 0x2000);
    c.dos64_reu_fail_after(verify.machine, 2, 16); // Two complete256B chunks then uncertain DMA.
    try transfer(&verify, 0x20, 1);
    try std.testing.expectEqual(@as(u8, 0), verify.peek(try verify.symbol("dos64_disk_host_error")));
    try std.testing.expectEqual(@as(u16, 512), verify.word((try verify.symbol("dos64_range_request")) + 11));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(verify.machine, 0x2000));
    var read = try init(1);
    defer read.deinit();
    try request(&read, 2, 1, 0, 0, 1, 0, 0x2000);
    c.dos64_reu_fail_after(read.machine, 0, 16);
    try transfer(&read, 0x20, 0);
    try std.testing.expectEqual(@as(u8, 0), read.peek(try read.symbol("dos64_disk_host_error")));
    try std.testing.expectEqual(@as(u16, 0), read.word((try read.symbol("dos64_range_request")) + 11));
    try std.testing.expectEqual(@as(u8, 0), c.dos64_reu_peek(read.machine, 0x2000));
    var cache = try init(1);
    defer cache.deinit();
    try request(&cache, 2, 1, 0, 0, 1, 0, 0x2000);
    c.dos64_reu_fail_after(cache.machine, 1, 16); // Source staging succeeds; guest-cache load fails.
    try transfer(&cache, 0x20, 0);
    try std.testing.expectEqual(@as(u8, 1), cache.peek(try cache.symbol("dos64_disk_host_error")));
    try std.testing.expectEqual(@as(u8, 3), cache.peek((try cache.symbol("dos64_range_request")) + 10));
    try request(&cache, 0, 0, 0, 0, 0, 0, 0);
    try transfer(&cache, 0, 0);
    try std.testing.expectEqual(@as(u8, 0), cache.peek(try cache.symbol("dos64_disk_host_error")));
}

test "disk init replaces hostile dual descriptors and all protocol state for every native P" {
    var f=try Fixture.init();defer f.deinit();
    const a=try f.symbol("dos64_disk_reu_base");
    const b=try f.symbol("dos64_disk_b_descriptor");
    const meta_end=(try f.symbol("dos64_disk_cf"))+1;
    const rq=try f.symbol("dos64_floppy_request");
    const request_end=(try f.symbol("dos64_floppy_token"))+4;
    const expected=[_]u8{0,0,0x10,0xd0,2,40,0,2,9,0,0,0};
    const initial_dma=c.dos64_dma_transfers(f.machine);
    const port=f.peek(1);const ddr=f.peek(0);
    for(0..256) |p| {
        for(0..12)|i|f.poke(a+@as(u16,@intCast(i)),@truncate(i*19+p+1));
        for(b..meta_end)|i|f.poke(@intCast(i),@truncate(i*13+p+1));
        for(rq..request_end)|i|f.poke(@intCast(i),@truncate(i*17+p+1));
        f.initial_status=@intCast(p);
        const r=try f.call("dos64_disk_init",10000);
        try std.testing.expectEqual(@as(u8,@intCast(p))&0xce,r.p&0xce);
        try std.testing.expectEqual(@as(u8,0),r.p&1);
        try std.testing.expectEqual(@as(u8,0x93),r.y);
        for(expected,0..)|v,i|try std.testing.expectEqual(v,f.peek(a+@as(u16,@intCast(i))));
        for(expected[0..10],0..)|v,i|try std.testing.expectEqual(if(i==2)@as(u8,0x18)else v,f.peek(b+@as(u16,@intCast(i))));
        for(b+10..meta_end)|i|try std.testing.expectEqual(@as(u8,0),f.peek(@intCast(i)));
        for(rq..request_end)|i|try std.testing.expectEqual(@as(u8,0),f.peek(@intCast(i)));
        try std.testing.expectEqual(port,f.peek(1));try std.testing.expectEqual(ddr,f.peek(0));
    }
    try std.testing.expectEqual(initial_dma,c.dos64_dma_transfers(f.machine));
}

test "disk init writes only complete owned descriptor metadata and request spans plus native stack" {
    var f=try Fixture.init();defer f.deinit();
    const a=try f.symbol("dos64_disk_reu_base");const b=try f.symbol("dos64_disk_b_descriptor");
    const meta_end=(try f.symbol("dos64_disk_cf"))+1;
    const rq=try f.symbol("dos64_floppy_request");const request_end=(try f.symbol("dos64_floppy_token"))+4;
    f.initial_status=0xcf;_ = try f.call("dos64_disk_init",10000);
    for(0..65536)|i| {
        const address:@TypeOf(a)=@intCast(i);
        const owned=(i>=a and i<a+12)or(i>=b and i<meta_end)or(i>=rq and i<request_end)or(i>=0x100 and i<0x200);
        if(!owned)try std.testing.expectEqual(@as(u8,0),c.dos64_was_written(f.machine,address));
    }
}

test "shared cold SAVER descriptor completes STORE0 from hostile request and preserves immutable LOAD1" {
    var f=try Fixture.init();defer f.deinit();c.dos64_enable_reu(f.machine);
    // Real bootstrap installs immutable HDBIOS before its cold SAVER store.
    const installed=try f.call("hdb_load_extension",200000);try std.testing.expectEqual(@as(u8,0),installed.p&1);
    const rq=try f.symbol("dos64_reu_request");const source=try f.symbol("sav_load");
    const load=[_]u8{0,0xb0,0,0x30,0x34,0,8,1};
    const store=[_]u8{0,0xb0,0,0x30,0x34,0,8,0};
    for(load,0..)|v,i|try std.testing.expectEqual(v,f.peek(source+@as(u16,@intCast(i))));
    var bytes:[2048]u8=undefined;for(&bytes,0..)|*v,i|v.*=f.peek(0xb000+@as(u16,@intCast(i)));
    for(bytes,0..)|v,i|c.dos64_reu_poke(f.machine,0x343000+@as(u32,@intCast(i)),v^0xff);
    c.dos64_reu_poke(f.machine,0x342fff,0x91);c.dos64_reu_poke(f.machine,0x343800,0x37);
    for(0..10)|i|f.poke(rq+@as(u16,@intCast(i)),@truncate(0x80+i*7));
    const before=c.dos64_dma_transfers(f.machine);const r=try f.call("sav_boot",50000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u8,0xa5),f.peek(try f.symbol("sav_ready")));
    try std.testing.expectEqual(before+1,c.dos64_dma_transfers(f.machine));
    for(store,0..)|v,i|try std.testing.expectEqual(v,f.peek(rq+@as(u16,@intCast(i))));
    for(load,0..)|v,i|try std.testing.expectEqual(v,f.peek(source+@as(u16,@intCast(i))));
    for(bytes,0..)|v,i|{try std.testing.expectEqual(v,c.dos64_reu_peek(f.machine,0x343000+@as(u32,@intCast(i))));try std.testing.expectEqual(v,f.peek(0xb000+@as(u16,@intCast(i))));}
    try std.testing.expectEqual(@as(u8,0x91),c.dos64_reu_peek(f.machine,0x342fff));try std.testing.expectEqual(@as(u8,0x37),c.dos64_reu_peek(f.machine,0x343800));
}

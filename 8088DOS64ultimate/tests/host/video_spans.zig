const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const allocator = std.testing.allocator;

fn word(f: *Fixture, a: u16, v: u16) void {
    f.poke(a, @truncate(v));
    f.poke(a +% 1, @truncate(v >> 8));
}
fn reg(f: *Fixture, index: u16, value: u16) !void {
    word(f, (try f.symbol("dos64_guest")) + index * 2, value);
}
fn init(frames: u8) !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"), 4);
    f.poke(1,5);
    _ = f.call("dos64_overlay_bootstrap", 300_000) catch |err| { std.debug.print("shadow bootstrap {s}, PC={x}\n", .{@errorName(err), f.last_regs.?.pc}); return err; };
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek(try f.symbol("hdb_extension_ready")));
    for (0..3584) |i| try std.testing.expectEqual(f.peek(@intCast(0xa000+i)), f.peek(@intCast(0xf000+i)));
    f.poke(try f.symbol("dos64_cache_limit"), frames);
    _ = try f.call("dos64_cache_init", 50_000);
    _ = try f.call("dos64_cpu_init", 10_000);
    const g = try f.symbol("dos64_guest");
    for (0..14) |i| word(&f, g + @as(u16, @intCast(i)) * 2, 0xa700 + @as(u16, @intCast(i)));
    word(&f, g + 26, 0xfbd7);
    f.initial_status = 0xec;
    return f;
}
fn guest(f: *Fixture) ![28]u8 {
    var bytes: [28]u8 = undefined;
    const g = try f.symbol("dos64_guest");
    for (&bytes, 0..) |*v, i| v.* = f.peek(g + @as(u16, @intCast(i)));
    return bytes;
}
fn invoke(f: *Fixture, ax: u16, bx: u16, cx: u16, dx: u16, outputs: []const u8, handled: bool) !void {
    try reg(f, 0, ax);
    try reg(f, 3, bx);
    try reg(f, 1, cx);
    try reg(f, 2, dx);
    const before = try guest(f);
    const result = try f.call("dos64_video_service", 30_000_000);
    try std.testing.expectEqual(if (handled) @as(u8, 0) else @as(u8, 1), result.p & 1);
    try std.testing.expectEqual(@as(u8, 0xec), result.p & 0xec);
    try std.testing.expectEqual(@as(u8, 0), f.peek(try f.symbol("dos64_video_host_error")));
    const after = try guest(f);
    for (before, after, 0..) |a, b, i| {
        if (std.mem.indexOfScalar(u8, outputs, @intCast(i)) != null) continue;
        if (a != b) std.debug.print("Video changed unrelated guest byte {d}: {x}->{x}, AX={x}\n", .{ i, a, b, ax });
        try std.testing.expectEqual(a, b);
    }
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush", 1_000_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn busWrite(f: *Fixture, address: u32, value: u8) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address));
    f.poke(a + 1, @truncate(address >> 8));
    f.poke(a + 2, @truncate(address >> 16));
    f.poke(try f.symbol("dos64_mem_value"), value);
    const r = try f.call("dos64_mem_write", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
}
fn busRead(f: *Fixture, address: u32) !u8 {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address));
    f.poke(a + 1, @truncate(address >> 8));
    f.poke(a + 2, @truncate(address >> 16));
    const r = try f.call("dos64_mem_read", 50_000);
    try std.testing.expectEqual(@as(u8, 0), r.p & 1);
    return r.a;
}
fn backingWord(f: *Fixture, a: u32) u16 {
    return @as(u16, c.dos64_reu_peek(f.machine, a)) | (@as(u16, c.dos64_reu_peek(f.machine, a + 1)) << 8);
}
fn mode(f: *Fixture, value: u8) !void {
    try invoke(f, value, 0x1234, 0x5678, 0x9abc, &.{}, true);
}
fn cursor(f: *Fixture, page: u8, row: u8, col: u8) !void {
    try invoke(f, 0x0200, @as(u16, page) << 8, 0x7788, (@as(u16, row) << 8) | col, &.{}, true);
}
fn expectBytes(f: *Fixture, address: u32, expected: []const u8) !void {
    const first = c.dos64_reu_compare(f.machine, address, expected.ptr, expected.len);
    if (first != 0xffffffff) {
        std.debug.print("Video first divergence physical {x}: expected {x}, actual {x}\n", .{ address + first, expected[first], c.dos64_reu_peek(f.machine, address + first) });
        return error.VideoMemoryMismatch;
    }
}

// Independent logical screen oracle: cells are addressed by page/row/column.
// Scroll reads a snapshot, so overlap correctness does not depend on traversal.
const Screen = struct {
    bytes: [16384]u8,
    cols: u8,
    stride: usize,
    pages: u8,
    row: [8]u8 = @splat(0),
    col: [8]u8 = @splat(0),
    fn init(cols: u8) Screen {
        var s = Screen{ .bytes = undefined, .cols = cols, .stride = if (cols == 40) 2048 else 4096, .pages = if (cols == 40) 8 else 4 };
        for (&s.bytes, 0..) |*v, i| v.* = if (i % 2 == 0) 0x20 else 7;
        return s;
    }
    fn index(s: *const Screen, page: u8, row: u8, col: u8) usize {
        return @as(usize, page) * s.stride + (@as(usize, row) * s.cols + col) * 2;
    }
    fn scroll(s: *Screen, page: u8, top: u8, left: u8, bottom: u8, right: u8, lines: u8, attr: u8, down: bool) void {
        const before = s.bytes;
        const height: u16 = @as(u16, bottom) - top + 1;
        var row: u16 = top;
        while (row <= bottom) : (row += 1) {
            var col: u16 = left;
            while (col <= right) : (col += 1) {
                const dst = s.index(page, @intCast(row), @intCast(col));
                const src: i32 = @as(i32, row) + (if (down) -@as(i32, lines) else @as(i32, lines));
                if (lines == 0 or lines >= height or src < top or src > bottom) {
                    s.bytes[dst] = 0x20;
                    s.bytes[dst + 1] = attr;
                } else {
                    const at = s.index(page, @intCast(src), @intCast(col));
                    s.bytes[dst] = before[at];
                    s.bytes[dst + 1] = before[at + 1];
                }
            }
        }
    }
    fn tty(s: *Screen, page: u8, char: u8) void {
        if (char == 7) return;
        const at = s.index(page, s.row[page], s.col[page]);
        switch (char) {
            8 => {
                if (s.col[page] != 0) s.col[page] -= 1;
            },
            13 => s.col[page] = 0,
            10 => s.row[page] += 1,
            else => {
                s.bytes[at] = char;
                s.col[page] += 1;
                if (s.col[page] == s.cols) {
                    s.col[page] = 0;
                    s.row[page] += 1;
                }
            },
        }
        if (s.row[page] == 25) {
            const attr = s.bytes[s.index(page, 24, s.col[page]) + 1];
            s.scroll(page, 0, 0, 24, s.cols - 1, 1, attr, false);
            s.row[page] = 24;
        }
    }
    fn compare(s: *const Screen, f: *Fixture) !void {
        try flush(f);
        try expectBytes(f, 0xb8000, &s.bytes);
    }
};
fn seedScreen(f: *Fixture, s: *Screen) !void {
    // Initialize via the authoritative bus, forcing dirty page evictions.
    for (&s.bytes, 0..) |*v, i| {
        v.* = @truncate((i * 37 + i / 83 + 9) ^ (i >> 4));
        try busWrite(f, 0xb8000 + @as(u32, @intCast(i)), v.*);
    }
}

// Fixed seed and arithmetic keep this fixture independent of Zig RNG changes.
fn random(state: *u32) u32 {
    state.* = state.* *% 1664525 +% 1013904223;
    return state.*;
}

fn fillWhole(f: *Fixture, bytes: []const u8) void {
    for (bytes,0..) |v,i| c.dos64_reu_poke(f.machine,@intCast(i),v);
}
fn wholeSeed(m: u8, page: u8) ![]u8 {
    const bytes=try allocator.alloc(u8,1048576);
    var seed:u32=0x10c6a033;
    for(bytes) |*v| v.*=@truncate(random(&seed));
    bytes[0x449]=m; bytes[0x44a]=if(m<2) 40 else 80; bytes[0x44b]=0; bytes[0x462]=page;
    return bytes;
}
fn scrollWhole(bytes: []u8, m:u8,page:u8, top:u8,left:u8,bottom:u8,right:u8,lines:u8,attr:u8,down:bool) void {
    var s=Screen.init(if(m<2) 40 else 80);
    @memcpy(&s.bytes,bytes[0xb8000..0xbc000]);
    s.scroll(page,top,left,bottom,right,lines,attr,down);
    @memcpy(bytes[0xb8000..0xbc000],&s.bytes);
}
fn dirtySeed(f:*Fixture, bytes:[]u8) !void {
    // Include source, destination and unrelated dirty pages; one lies exactly
    // beyond the video aperture, under the normal hole policy.
    for([_]u32{0x12345,0x9fffe,0xb8000,0xb80ff,0xb8200,0xbbffd}) |a| {
        const v=bytes[a]^0x5a; try busWrite(f,a,v); bytes[a]=v;
    }
}
fn assertPins(f:*Fixture, external: ?u8) !void {
    const p=try f.symbol("dos64_cache_pins");
    for(0..32) |i| try std.testing.expectEqual(if(external!=null and i==external.?) @as(u8,1) else @as(u8,0),f.peek(p+@as(u16,@intCast(i))));
}
fn epoch(f:*Fixture) !u32 { const a=try f.symbol("dos64_write_epoch");return @as(u32,f.word(a))|(@as(u32,f.word(a+2))<<16); }

test "optimized text scroll full1MiB independent oracle metadata and measured cycles" {
    const cases=[_]struct{ frames:u8,m:u8,page:u8,top:u8=0,left:u8=0,bottom:u8=24,right:u8,lines:u8=1,attr:u8=7,down:bool=false }{
        .{.frames=32,.m=3,.page=0,.right=79},
        .{.frames=32,.m=3,.page=3,.right=79,.down=true,.lines=3,.attr=0},
        .{.frames=2,.m=3,.page=2,.right=79},
        .{.frames=1,.m=3,.page=1,.right=79},
        .{.frames=32,.m=1,.page=7,.right=39,.lines=2},
        .{.frames=2,.m=1,.page=5,.right=39,.down=true},
        .{.frames=32,.m=3,.page=1,.top=3,.left=7,.bottom=22,.right=74,.lines=4,.attr=0xff},
        .{.frames=2,.m=3,.page=3,.top=2,.left=1,.bottom=24,.right=78,.lines=7,.down=true,.attr=0x80},
        .{.frames=32,.m=3,.page=2,.right=79,.lines=0},
        .{.frames=32,.m=1,.page=4,.right=39,.lines=255,.attr=0},
    };
    for(cases) |x| {
        var f=try init(x.frames);defer f.deinit();
        const base=try wholeSeed(x.m,x.page);defer allocator.free(base);
        fillWhole(&f,base);
        const expected=try allocator.dupe(u8,base);defer allocator.free(expected);
        try dirtySeed(&f,expected);
        const before_epoch=try epoch(&f);
        const ax=(if(x.down) @as(u16,0x0700) else @as(u16,0x0600))|x.lines;
        const bx=@as(u16,x.attr)<<8;const cx=(@as(u16,x.top)<<8)|x.left;const dx=(@as(u16,x.bottom)<<8)|x.right;
        try invoke(&f,ax,bx,cx,dx,&.{},true);const cycles=f.last_regs.?.cycles;
        scrollWhole(expected,x.m,x.page,x.top,x.left,x.bottom,x.right,x.lines,x.attr,x.down);
        try assertPins(&f,null);
        const count=2*@as(u32,x.right-x.left+1)*(x.bottom-x.top+1);
        try std.testing.expectEqual(before_epoch+%count,try epoch(&f));
        try flush(&f);
        try expectBytes(&f,0,expected);
        if(x.frames==32 and x.lines!=0 and x.lines<25) try std.testing.expect(cycles<1_000_000);

    }
}

test "optimized scroll pin pressure and overflow use scalar fallback preserving external ownership" {
    for([_]bool{false,true}) |overflow| {
        var f=try init(2);defer f.deinit();
        const before=try wholeSeed(3,0);defer allocator.free(before);fillWhole(&f,before);
        const a=try f.symbol("dos64_address");
        const pinned_address:u32=if(overflow) 0xb8000 else 0x30000;
        f.poke(a,@truncate(pinned_address));f.poke(a+1,@truncate(pinned_address>>8));f.poke(a+2,@truncate(pinned_address>>16));
        const r=try f.call("dos64_cache_acquire",50000);try std.testing.expectEqual(@as(u8,0),r.p&1);
        const frame=f.peek(try f.symbol("dos64_cache_selected"));
        const pin=try f.symbol("dos64_cache_pins")+frame;
        if(overflow) f.poke(pin,255);
        // Overflow case stays entirely in one already-pinned VRAM page.
        const bottom:u8=if(overflow) 2 else 24;
        try invoke(&f,0x0601,0x0700,0,(@as(u16,bottom)<<8)|79,&.{},true);
        scrollWhole(before,3,0,0,0,bottom,79,1,7,false);
        try std.testing.expectEqual(if(overflow) @as(u8,255) else @as(u8,1),f.peek(pin));
        for(0..32) |i| if(i!=frame) try std.testing.expectEqual(@as(u8,0),f.peek((try f.symbol("dos64_cache_pins"))+@as(u16,@intCast(i))));
        try flush(&f);try expectBytes(&f,0,before);
    }
}

// Reconstruct a legal scalar prefix from the authoritative post-failure RAM.
// At most the first k writes in traversal order may have committed. Page DMA
// may have partially failed, but those backing artifacts must not win over a
// retained dirty frame, and reads must not leave a source pin behind.
fn verifyScrollPrefix(before:[]const u8,actual:[]const u8,down:bool) !void {
    const final=try allocator.dupe(u8,before);defer allocator.free(final);
    scrollWhole(final,3,0,0,0,24,79,1,7,down);
    var saw_unchanged=false;
    for(0..25) |rr| {
        const row=if(down) 24-rr else rr;
        for(0..160) |col| {
            const at=0xb8000+row*160+col;
            if(before[at]!=final[at]) {
                if(actual[at]==before[at]) saw_unchanged=true else {
                    try std.testing.expect(!saw_unchanged);
                    try std.testing.expectEqual(final[at],actual[at]);
                }
            } else try std.testing.expectEqual(before[at],actual[at]);
        }
    }
    try std.testing.expectEqualSlices(u8,before[0..0xb8000],actual[0..0xb8000]);
    try std.testing.expectEqualSlices(u8,before[0xb8fa0..],actual[0xb8fa0..]);
}

test "optimized scroll injected DMA failures preserve authoritative scalar-prefix full1MiB and release all pins" {
    var failures:usize=0;
    for([_]u8{2,32}) |frames| for([_]bool{false,true}) |down| for([_]u64{0,1,2,3,4,5,6,7,8,9,10,12,15,20,30}) |skip| {
        var f=try init(frames);defer f.deinit();
        const before=try wholeSeed(3,0);defer allocator.free(before);fillWhole(&f,before);try dirtySeed(&f,before);
        try reg(&f,0,(if(down) @as(u16,0x0700) else @as(u16,0x0600))|1);try reg(&f,3,0x0700);try reg(&f,1,0);try reg(&f,2,0x184f);
        const regs=try guest(&f);
        c.dos64_reu_fail_after(f.machine,skip,if(skip%3==0) 0 else if(skip%3==1) 16 else 511);
        const r=try f.call("dos64_video_service",5000000);
        try std.testing.expectEqual(@as(u8,0xec),r.p&0xec);try std.testing.expectEqualSlices(u8,&regs,&(try guest(&f)));
        try assertPins(&f,null);
        if(r.p&1!=0) {failures+=1;try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_video_host_error")));}
        c.dos64_reu_fail_after(f.machine,std.math.maxInt(u64),0); // discard an unreached fixture failure before recovery reads
        try flush(&f);
        const actual=try allocator.alloc(u8,1048576);defer allocator.free(actual);try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,0,actual.ptr,actual.len));
        try verifyScrollPrefix(before,actual,down);
    };
    try std.testing.expect(failures>=40);
    std.debug.print("SCROLLFAULT accepted_failures={d} cases=60\n",.{failures});
}

test "span mode clear matches independent full1MiB bus and exact BDA oracle for every CGA mode" {
    for(0..7) |m| {
        var f=try init(32);defer f.deinit();
        const bytes=try wholeSeed(3,0);defer allocator.free(bytes);fillWhole(&f,bytes);
        const before=try epoch(&f);
        try invoke(&f,@intCast(m),0,0,0,&.{},true);
        try std.testing.expect(f.last_regs.?.cycles<3_000_000);
        try std.testing.expectEqual(before+%16414,try epoch(&f));
        for(bytes[0xb8000..0xbc000],0..) |*v,i| v.*=if(m>=4) 0 else if(i%2==0) 0x20 else 7;
        const cols:u8=if(m==2 or m==3 or m==6) 80 else 40;
        bytes[0x449]=@intCast(m);bytes[0x44a]=cols;bytes[0x44b]=0;bytes[0x44c]=0;bytes[0x44d]=if(m>=4) 0x40 else if(cols==40) 8 else 0x10;
        @memset(bytes[0x44e..0x460],0);
        bytes[0x460]=7;bytes[0x461]=6;bytes[0x462]=0;bytes[0x463]=0xd4;bytes[0x464]=3;
        bytes[0x465]=([_]u8{0x2c,0x28,0x2d,0x29,0x2a,0x2e,0x1e})[m];bytes[0x466]=if(m==6) 0x3f else 0x30;
        try assertPins(&f,null);try flush(&f);try expectBytes(&f,0,bytes);
    }
}

test "resolved writable span byte preserves every host flag state Y and exact per-byte bookkeeping" {
    var f=try init(32);defer f.deinit();
    for(0..256) |status| {
        f.initial_status=@intCast(status);
        try busWrite(&f,0xb8100,0x55);
        const frame=f.peek(try f.symbol("dos64_cache_selected"));
        const genlo=try f.symbol("dos64_cache_generations_lo")+frame;
        const genhi=try f.symbol("dos64_cache_generations_hi")+frame;
        if(status%64==0) {
            f.poke(genlo,255);f.poke(genhi,255);
            const ep=try f.symbol("dos64_write_epoch");for(0..4) |i| f.poke(ep+@as(u16,@intCast(i)),255);
        }
        const beforegen=@as(u16,f.peek(genlo))|(@as(u16,f.peek(genhi))<<8);
        const before=try epoch(&f);
        f.poke(try f.symbol("dos64_video_dirty"),0);
        f.poke(try f.symbol("dos64_mem_value"),@intCast(status));
        const r=try f.call("dos64_mem_write_span_byte",1000); // native Y=93 from actual bridge
        try std.testing.expectEqual(@as(u8,0x93),r.y);
        try std.testing.expectEqual((@as(u8,@intCast(status))|0x20)&0xec,r.p&0xec);
        try std.testing.expectEqual(@as(u8,0),r.p&1);
        try std.testing.expectEqual(before+%1,try epoch(&f));
        const aftergen=@as(u16,f.peek(genlo))|(@as(u16,f.peek(genhi))<<8);
        try std.testing.expectEqual(beforegen+%1,aftergen);
        try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_video_dirty")));
        const pointer=try f.symbol("dos64_mem_pointer");try std.testing.expectEqual(@as(u8,@intCast(status)),f.peek(f.word(pointer)+0x93));
    }
}

test "span aperture clear failure remains a legal byte prefix with full1MiB authority and untouched BDA" {
    var failures:usize=0;
    for([_]u8{1,2,32}) |frames| for([_]u64{0,1,2,5,15,30}) |skip| {
        var f=try init(frames);defer f.deinit();
        const before=try wholeSeed(3,0);defer allocator.free(before);fillWhole(&f,before);try dirtySeed(&f,before);
        try reg(&f,0,6);try reg(&f,3,0x1234);try reg(&f,1,0x5678);try reg(&f,2,0x9abc);
        const regs=try guest(&f);c.dos64_reu_fail_after(f.machine,skip,if(skip%2==0) 511 else 16);
        const r=try f.call("dos64_video_service",10_000_000);
        try std.testing.expectEqual(@as(u8,1),r.p&1);failures+=1;
        try std.testing.expectEqual(@as(u8,0xec),r.p&0xec);try std.testing.expectEqualSlices(u8,&regs,&(try guest(&f)));
        try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_video_host_error")));try assertPins(&f,null);
        c.dos64_reu_fail_after(f.machine,std.math.maxInt(u64),0);try flush(&f);
        const actual=try allocator.alloc(u8,1048576);defer allocator.free(actual);try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,0,actual.ptr,actual.len));
        var unchanged=false;
        for(before[0xb8000..0xbc000],actual[0xb8000..0xbc000]) |old,v| {
            if(old!=0) {if(v==old) unchanged=true else {try std.testing.expect(!unchanged);try std.testing.expectEqual(@as(u8,0),v);}}
            else try std.testing.expectEqual(@as(u8,0),v);
        }
        try std.testing.expectEqualSlices(u8,before[0..0xb8000],actual[0..0xb8000]);
        try std.testing.expectEqualSlices(u8,before[0xbc000..],actual[0xbc000..]);
    };
    try std.testing.expectEqual(@as(usize,18),failures);
}

const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;
const color_model=@cImport({@cInclude("graphics_color_model.h");});
const rgb = [_]u8{ 0, 6, 5, 3, 2, 4, 9, 15, 12, 14, 13, 3, 10, 4, 7, 1 };
fn random(s: *u32) u8 { s.* = s.* *% 1664525 +% 1013904223; return @truncate(s.* >> 19); }
fn init() !Fixture {
    var f = try Fixture.init();
    errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    color_model.dos64_graphics_color_enable(@ptrCast(f.machine));
    _=try f.call("dos64_overlay_init",10000);
    f.poke(try f.symbol("dos64_overlay_reu_mib"),4);
    _=try f.call("dos64_overlay_bootstrap",10000);
    f.poke(try f.symbol("dos64_overlay_requested"),5);
    const loaded=try f.call("dos64_overlay_acquire",10000);
    try std.testing.expectEqual(@as(u8,0),loaded.p&1);
    _=try f.call("dos64_overlay_release",10000);
    f.poke(try f.symbol("dos64_cache_limit"), 1);
    _ = try f.call("dos64_cache_init", 50_000);
    f.initial_status = 0xec;
    return f;
}
fn geometry(f: *Fixture, mode: u8, color: u8) !void {
    c.dos64_reu_poke(f.machine, 0x449, mode);
    c.dos64_reu_poke(f.machine, 0x462, 0);
    c.dos64_reu_poke(f.machine, 0x44e, 0);
    c.dos64_reu_poke(f.machine, 0x44f, 0);
    c.dos64_reu_poke(f.machine, 0x466, color);
    _ = try f.call("dos64_cache_init", 50_000);
}
fn busWrite(f: *Fixture, address: u32, value: u8) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a, @truncate(address)); f.poke(a+1, @truncate(address>>8)); f.poke(a+2, @truncate(address>>16));
    f.poke(try f.symbol("dos64_mem_value"), value);
    try std.testing.expectEqual(@as(u8,0), (try f.call("dos64_mem_write",50_000)).p & 1);
}
fn render(f: *Fixture, line: u8, done: u8, err: u8) !u64 {
    const request = try f.symbol("dos64_render_graphics_request");
    f.poke(request,line);
    for (1..4) |i| f.poke(request+@as(u16,@intCast(i)),0xd7);
    const port=f.peek(1); const ddr=f.peek(0);
    const before=c.dos64_get_regs(f.machine).cycles;
    const r=try f.call("dos64_render_graphics_line",500_000);
    try std.testing.expectEqual(if(err==0) @as(u8,0) else 1,r.p&1);
    try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);
    try std.testing.expectEqual(ddr,f.peek(0));
    try std.testing.expectEqual(port&ddr,f.peek(1)&ddr);
    try std.testing.expectEqual(done,f.peek(request+1));
    try std.testing.expectEqual(if(err==0) @as(u8,1) else 2,f.peek(request+2));
    try std.testing.expectEqual(err,f.peek(request+3));
    // CIA2 belongs to the native clock, which the renderer must never touch.
    for (0xdd00..0xdd10) |at| try std.testing.expectEqual(@as(c_int,0),c.dos64_was_written(f.machine,@intCast(at)));
    return r.cycles-before;
}
const Screen = struct {
    vram: [16384]u8,
    bitmap: [8000]u8 = @splat(0xa7),
    matrix: [1000]u8 = @splat(0x5c),
    colors: [1000]u8 = @splat(0),
    fn seed(f: *Fixture, initial: u32) Screen {
        var s=Screen{.vram=undefined}; var r=initial;
        for (&s.vram,0..) |*v,i| { v.*=random(&r); c.dos64_reu_poke(f.machine,0xb8000+@as(u32,@intCast(i)),v.*); }
        for (0x4000..0x4800) |at| f.poke(@intCast(at),0x5c);
        for (0x6000..0x8000) |at| f.poke(@intCast(at),0xa7);
        f.poke(0x3fff,0x39); f.poke(0x5fff,0x76);
        return s;
    }
    fn palette(mode: u8, color: u8) [4]u8 {
        if (mode==6) return .{0,rgb[color&15],0,0};
        const intensity: u8=if(color&16!=0) 8 else 0;
        const p: [3]u8=if(mode==5) .{3,4,7} else if(color&32!=0) .{3,5,7} else .{2,4,6};
        return .{rgb[color&15],rgb[p[0]+intensity],rgb[p[1]+intensity],rgb[p[2]+intensity]};
    }
    fn row(s: *Screen, mode: u8, color: u8, y: u8, done: u8) void {
        const pal=palette(mode,color);
        const source=@as(usize,y/2)*80+@as(usize,y%2)*8192;
        for (0..done) |cell| {
            var byte: u8=0;
            for (0..(if(mode==6) @as(usize,8) else 4)) |pixel| {
                const left=cell*(if(mode==6) @as(usize,16) else 8)+pixel*2;
                if(mode==6) {
                    const one=(s.vram[source+left/8]>>@as(u3,@intCast(7-left%8)))&1;
                    const two=(s.vram[source+(left+1)/8]>>@as(u3,@intCast(7-(left+1)%8)))&1;
                    byte=(byte<<1)|(one|two);
                } else {
                    const one=(s.vram[source+left/4]>>@as(u3,@intCast(6-(left%4)*2)))&3;
                    const two=(s.vram[source+(left+1)/4]>>@as(u3,@intCast(6-((left+1)%4)*2)))&3;
                    byte=(byte<<2)|(if(one!=0) one else two);
                }
            }
            const at=@as(usize,y/8)*40+cell;
            s.bitmap[@as(usize,y/8)*320+cell*8+y%8]=byte;
            s.matrix[at]=if(mode==6) pal[1]<<4 else (pal[1]<<4)|pal[2];
            if(mode!=6) s.colors[at]=pal[3];
        }
    }
    fn compare(s: *const Screen, f: *Fixture) !void {
        for (s.bitmap,0..) |v,i| {
            const a=f.peek(0x6000+@as(u16,@intCast(i)));
            if(v!=a) std.debug.print("CGA bitmap mismatch at {x}: expected{x} actual{x}\n",.{i,v,a});
            try std.testing.expectEqual(v,a);
        }
        for (s.matrix,0..) |v,i| try std.testing.expectEqual(v,f.peek(0x4000+@as(u16,@intCast(i))));
        for (s.colors,0..) |v,i| try std.testing.expectEqual(v,color_model.dos64_graphics_color_peek(@ptrCast(f.machine),0xd800+@as(u16,@intCast(i))));
        for (0x43e8..0x4800) |at| try std.testing.expectEqual(@as(u8,0x5c),f.peek(@intCast(at)));
        for (0x7f40..0x8000) |at| try std.testing.expectEqual(@as(u8,0xa7),f.peek(@intCast(at)));
        for (0xdbe8..0xdc00) |at| try std.testing.expectEqual(@as(u8,0),f.peek(@intCast(at)));
        try std.testing.expectEqual(@as(u8,0x39),f.peek(0x3fff));
        try std.testing.expectEqual(@as(u8,0x76),f.peek(0x5fff));
    }
    fn guestUnchanged(s: *const Screen, f: *Fixture) !void {
        try std.testing.expectEqual(@as(u8,0),(try f.call("dos64_cache_flush",1_000_000)).p&1);
        try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0xb8000,&s.vram,s.vram.len));
    }
    fn checkPalette(f: *Fixture, mode: u8, color: u8) !void {
        const request=try f.symbol("dos64_render_graphics_request");
        try std.testing.expectEqual(palette(mode,color)[0],f.peek(request+4));
        try std.testing.expectEqual(if(mode==6) @as(u8,0) else 1,f.peek(request+5));
    }
};
test "CGA all 600 scanlines match full independent geometry bitmap palette guards" {
    var f=try init(); defer f.deinit(); var s=Screen.seed(&f,0x80886510);
    var max_cycles:[3]u64=@splat(0);
    for (4..7) |mode| {
        try geometry(&f,@intCast(mode),0x3f);
        for (0..200) |y| {
            const cycles=try render(&f,@intCast(y),40,0);
            max_cycles[mode-4]=@max(max_cycles[mode-4],cycles);
            s.row(@intCast(mode),0x3f,@intCast(y),40);
            try s.compare(&f); try Screen.checkPalette(&f,@intCast(mode),0x3f);
        }
        try s.guestUnchanged(&f);
    }
    std.debug.print("CGA 600 scanlines max native cycles modes4/5/6={any}; excludes REU stalls and physical elapsed\n",.{max_cycles});
}
test "CGA all 256 color control bytes each mode preserve background intensity and palette policy" {
    var f=try init(); defer f.deinit(); var s=Screen.seed(&f,0x12344321);
    for (4..7) |mode| for (0..256) |color| {
        try geometry(&f,@intCast(mode),@intCast(color));
        _=try render(&f,127,40,0); s.row(@intCast(mode),@intCast(color),127,40);
        try s.compare(&f); try Screen.checkPalette(&f,@intCast(mode),@intCast(color));
    };
    try s.guestUnchanged(&f);
}
test "CGA rejects invalid mode scanline active page and start offset without output" {
    var f=try init(); defer f.deinit(); var s=Screen.seed(&f,0x99);
    for ([_]u8{0,1,2,3,7,255}) |mode| {try geometry(&f,mode,0); _=try render(&f,0,0,1);try s.compare(&f);}
    for ([_]u8{200,255}) |line| {try geometry(&f,4,0);_=try render(&f,line,0,1);try s.compare(&f);}
    for ([_]u32{0x462,0x44e,0x44f}) |at| {try geometry(&f,6,0);c.dos64_reu_poke(f.machine,at,1);_=try render(&f,0,0,1);try s.compare(&f);}
}
test "CGA cache load failures commit only complete bytes and retry exact scanline" {
    for (4..7) |mode| for (0..3) |skip| {
        var f=try init();defer f.deinit();var s=Screen.seed(&f,0x4411);
        try geometry(&f,@intCast(mode),0x19);
        c.dos64_reu_fail_after(f.machine,@intCast(skip),17);
        const done:u8=if(skip==2) 16 else 0;
        _=try render(&f,12,done,2);s.row(@intCast(mode),0x19,12,done);try s.compare(&f);
        _=try render(&f,12,40,0);s.row(@intCast(mode),0x19,12,40);try s.compare(&f);try s.guestUnchanged(&f);
    };
}
test "CGA sees dirty BDA and final odd scanline VRAM with one cache frame" {
    var f=try init();defer f.deinit();var s=Screen.seed(&f,0x1234);
    try geometry(&f,4,0);
    try busWrite(&f,0x449,6);try busWrite(&f,0x466,0x0e);
    try std.testing.expectEqual(@as(u8,4),c.dos64_reu_peek(f.machine,0x449));
    _=try render(&f,199,40,0);s.row(6,0x0e,199,40);try s.compare(&f);
    const at:usize=8192+99*80+79;s.vram[at]=0x80;
    try busWrite(&f,0xb8000+@as(u32,@intCast(at)),s.vram[at]);
    try std.testing.expect(s.vram[at]!=c.dos64_reu_peek(f.machine,0xb8000+@as(u32,@intCast(at))));
    _=try render(&f,199,40,0);s.row(6,0x0e,199,40);try s.compare(&f);try s.guestUnchanged(&f);
}
test "CGA dirty writeback failure preserves guest authority and output on retry" {
    var f=try init();defer f.deinit();var s=Screen.seed(&f,0x123456);
    try geometry(&f,5,0x31);s.vram[0]^=0xff;try busWrite(&f,0xb8000,s.vram[0]);
    c.dos64_reu_fail_after(f.machine,0,17);_=try render(&f,0,0,2);try s.compare(&f);
    _=try render(&f,0,40,0);s.row(5,0x31,0,40);try s.compare(&f);try s.guestUnchanged(&f);
}
test "CGA restores native flags DDR port outputs across ROM and input pin mappings" {
    var f=try init();defer f.deinit();var s=Screen.seed(&f,0xbadc0de);try geometry(&f,4,0x37);
    for ([_]u8{0,7,0x2f,0xff}) |ddr| for ([_]u8{0x30,0x35,0x37}) |port| {
        f.initial_status=if(port==0x30) 0x22 else if(port==0x35) 0xec else 0xeb;
        f.poke(0,ddr);f.poke(1,port);_=try render(&f,7,40,0);s.row(4,0x37,7,40);try s.compare(&f);
    };
    f.poke(0,0x2f);f.poke(1,0x35);try s.guestUnchanged(&f);
}
test "CGA exhaustively reduces every possible source byte without inventing foreground indices" {
    var f=try init();defer f.deinit();var s=Screen.seed(&f,0x55);
    for (0..256) |i| {s.vram[i]=@intCast(i);c.dos64_reu_poke(f.machine,0xb8000+@as(u32,@intCast(i)),@intCast(i));}
    for (4..7) |mode| {
        try geometry(&f,@intCast(mode),0x30);
        // Four even scanlines consume the first 320 source bytes.
        for ([_]u8{0,2,4,6}) |y| {_=try render(&f,y,40,0);s.row(@intCast(mode),0x30,y,40);try s.compare(&f);}
    }
    try s.guestUnchanged(&f);
}

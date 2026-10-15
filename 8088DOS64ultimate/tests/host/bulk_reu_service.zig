// Development-only service: actual linked assembly, isolated PRG and oracle.
const std = @import("std");
const c = @cImport({ @cInclude("peddle_bridge.h"); });
const a = std.testing.allocator;
const mb = 0x6000;
const size = 4*1024*1024;
const F = struct {
    m: *c.Dos64Machine,
    labels: []u8,
    seq: u16 = 0,
    fn init() !F {
        const prg = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,
            "agentworking/scratch/bulk-reu/service.prg", a, .limited(65538));
        defer a.free(prg);
        const m = c.dos64_create() orelse return error.Create;
        errdefer c.dos64_destroy(m);
        c.dos64_load(m, 0x801, prg[2..].ptr, prg.len-2);
        _ = c.dos64_enable_reu_sized(m, 16384);
        c.dos64_cia_clock_enable(m);
        const labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,
            "agentworking/scratch/bulk-reu/service.labels", a, .limited(65536));
        var f: F = .{ .m=m, .labels=labels };
        c.dos64_set_regs(m, .{ .pc=try f.sym("dos64_bulk_reu_entry"), .sp=0xff,
            .a=0,.x=0,.y=0,.p=0x24,.cycles=0,.instructions=0 });
        const r = c.dos64_run(m, try f.sym("dos64_bulk_reu_idle"), 10000);
        try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),r.status);
        try std.testing.expectEqual(@as(u8,0x11), f.get(4));
        try std.testing.expectEqual(@as(u8,0),c.dos64_cia_clock_mask(m));
        return f;
    }
    fn deinit(f: *F) void { a.free(f.labels); c.dos64_destroy(f.m); }
    fn sym(f: *F, name: []const u8) !u16 {
        var lines=std.mem.splitScalar(u8,f.labels,'\n');
        while(lines.next()) |line| {
            var words=std.mem.tokenizeAny(u8,line," \r\t");
            if(!std.mem.eql(u8,words.next() orelse continue,"al")) continue;
            const addr=words.next() orelse continue;
            const n=words.next() orelse continue;
            if(std.mem.eql(u8,n[1..],name)) return std.fmt.parseInt(u16,addr,16);
        }
        return error.Symbol;
    }
    fn get(f: *F, off: u16) u8 { return c.dos64_peek(f.m,mb+off); }
    fn put(f: *F, off: u16, val: u8) void { c.dos64_poke(f.m,mb+off,val); }
    fn word(f: *F, off: u16) u16 { return @as(u16,f.get(off))|(@as(u16,f.get(off+1))<<8); }
    fn putword(f: *F, off: u16, val: u16) void { f.put(off,@truncate(val));f.put(off+1,@truncate(val>>8)); }
    fn desc(f: *F, dir: u8, addr: u32, count: u16) void {
        f.seq+%=1;
        f.putword(7,f.seq);f.putword(16,~f.seq);
        f.put(6,dir);f.put(11,@truncate(addr));f.put(12,@truncate(addr>>8));f.put(13,@truncate(addr>>16));
        f.putword(14,count);f.put(4,0x47);
    }
    fn poll(f: *F) !void {
        c.dos64_poke(f.m,0x1ff,0xff);c.dos64_poke(f.m,0x1fe,0xfe);
        c.dos64_clear_writes(f.m);
        c.dos64_set_regs(f.m,.{ .pc=try f.sym("dos64_bulk_reu_poll"),.sp=0xfd,
            .a=0x71,.x=0x82,.y=0x93,.p=0x24,.cycles=0,.instructions=0 });
        const r=c.dos64_run(f.m,0xffff,10000);
        try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),r.status);
        try std.testing.expectEqual(@as(u8,0),c.dos64_model_fault(f.m));
        for(0..65536) |index| {
            const ad:u16=@intCast(index);
            if(c.dos64_was_written(f.m,ad)==0) continue;
            if(ad<=1 or (ad>=0x20 and ad<0x24) or (ad>=0x100 and ad<0x200)) continue;
            if((ad>=mb and ad<mb+32) or (ad>=0xe000 and ad<0xe00f)) continue;
            if(ad>=0xdf00 and ad<=0xdf0a) continue;
            if(ad>=0x8000 and ad<0xc000 and f.get(6)==1) continue;
            std.debug.print("forbidden write {x}\n",.{ad});return error.ForbiddenWrite;
        }
    }
    fn transfer(f:*F, dir:u8, addr:u32, count:u16) !void {
        f.desc(dir,addr,count);try f.poll();
        try std.testing.expectEqual(@as(u8,0xa5),f.get(4));
        try std.testing.expectEqual(f.seq,f.word(9));
    }
};
fn pattern(i:usize) u8 { return @truncate((i*37) ^ (i>>8) ^ (i>>16) ^ 0xa7); }

test "actual service snapshots restores exact four MiB and never changes twelve MiB remainder" {
    var f=try F.init();defer f.deinit();
    const original=try a.alloc(u8,16*1024*1024);defer a.free(original);
    const backup=try a.alloc(u8,size);defer a.free(backup);
    for(original,0..) |*v,i| {v.*=pattern(i);c.dos64_reu_poke(f.m,@intCast(i),v.*);}
    var chunk:usize=0;
    while(chunk<size):(chunk+=0x4000) {
        try f.transfer(1,@intCast(chunk),0x4000);
        for(0..0x4000) |i| backup[chunk+i]=c.dos64_peek(f.m,@intCast(0x8000+i));
    }
    try std.testing.expectEqualSlices(u8,original[0..size],backup);
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,original.ptr,original.len));
    for(0..size) |i| c.dos64_reu_poke(f.m,@intCast(i),0x55);
    chunk=0;
    while(chunk<size):(chunk+=0x4000) {
        c.dos64_load(f.m,0x8000,backup[chunk..].ptr,0x4000);
        try f.transfer(0,@intCast(chunk),0x4000);
    }
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,original.ptr,original.len));
    try std.testing.expectEqual(@as(u64,512),c.dos64_dma_transfers(f.m));
    try std.testing.expectEqual(@as(u64,size*2),c.dos64_dma_bytes(f.m));
}

test "service validates count direction span guards and sequence before DMA" {
    const cases=[_][4]u32{
        .{1,0,0,5},.{1,0,0x4001,5},.{1,0,0xffff,5},.{2,0,1,4},
        .{1,0x400000,1,6},.{0,0x3fffff,2,6},.{0,0xffffff,1,6},.{1,0xffff,2,7},
    };
    for(cases) |v| {
        var f=try F.init();defer f.deinit();
        f.desc(@intCast(v[0]),v[1],@intCast(v[2]));try f.poll();
        try std.testing.expectEqual(@as(u8,0xe1),f.get(4));try std.testing.expectEqual(@as(u8,@intCast(v[3])),f.get(5));
        try std.testing.expectEqual(f.seq,f.word(9));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));
    }
    var f=try F.init();defer f.deinit();
    f.desc(1,0,1);f.put(16,0);try f.poll();try std.testing.expectEqual(@as(u8,3),f.get(5));
    try f.transfer(1,0x3fffff,1);try f.transfer(1,0x3fc000,0x4000);
    const count=c.dos64_dma_transfers(f.m);
    // Duplicate sequence, including a valid old body, never repeats DMA.
    f.put(4,0x47);try f.poll();try std.testing.expectEqual(@as(u8,2),f.get(5));
    try std.testing.expectEqual(count,c.dos64_dma_transfers(f.m));
    f.desc(1,0,1);f.putword(7,f.seq+%1);try f.poll();try std.testing.expectEqual(@as(u8,2),f.get(5));
    f.seq=f.word(9);
    f.desc(1,0,1);f.put(0,'!');try f.poll();try std.testing.expectEqual(@as(u8,1),f.get(5));
    try std.testing.expectEqual(count,c.dos64_dma_transfers(f.m));
}

test "uncommitted body is idle and full sequence wrap is unambiguous" {
    var f=try F.init();defer f.deinit();
    f.desc(1,0,1);f.put(4,0x11);try f.poll();
    try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));
    f.seq=0xffff;f.putword(9,0xffff);try f.transfer(1,0x123456,1);
    try std.testing.expectEqual(@as(u16,0),f.word(9));
}

test "partial DMA failures consume acknowledgement and retry with fresh sequence repairs entire chunk" {
    for([_]u8{0,1}) |dir| {
        var f=try F.init();defer f.deinit();
        for(0..0x4000) |i| {
            c.dos64_reu_poke(f.m,@intCast(0x3fc000+i),pattern(i));
            c.dos64_poke(f.m,@intCast(0x8000+i),pattern(i)^0xff);
        }
        c.dos64_reu_poke(f.m,0x3fbfff,0x7a);c.dos64_reu_poke(f.m,0x400000,0x8b);
        c.dos64_poke(f.m,0x7fff,0x9c);c.dos64_poke(f.m,0xc000,0xad);
        c.dos64_reu_fail_after(f.m,0,17);
        f.desc(dir,0x3fc000,0x4000);try f.poll();
        try std.testing.expectEqual(@as(u8,0xe1),f.get(4));try std.testing.expectEqual(@as(u8,7),f.get(5));
        try std.testing.expectEqual(@as(u8,4),f.get(18));try std.testing.expectEqual(f.seq,f.word(9));
        try f.transfer(dir,0x3fc000,0x4000);
        for(0..0x4000) |i| try std.testing.expectEqual(pattern(i)^@as(u8,if(dir==0) 0xff else 0),
            if(dir==0) c.dos64_reu_peek(f.m,@intCast(0x3fc000+i)) else c.dos64_peek(f.m,@intCast(0x8000+i)));
        try std.testing.expectEqual(@as(u8,0x7a),c.dos64_reu_peek(f.m,0x3fbfff));
        try std.testing.expectEqual(@as(u8,0x8b),c.dos64_reu_peek(f.m,0x400000));
        try std.testing.expectEqual(@as(u8,0x9c),c.dos64_peek(f.m,0x7fff));
        try std.testing.expectEqual(@as(u8,0xad),c.dos64_peek(f.m,0xc000));
    }
}

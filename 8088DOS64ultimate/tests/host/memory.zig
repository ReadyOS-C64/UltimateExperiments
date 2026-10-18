const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn setWord(f: *Fixture, name: []const u8, value: u16) !void {
    const a = try f.symbol(name);
    f.poke(a,@truncate(value)); f.poke(a+1,@truncate(value>>8));
}
fn address(f: *Fixture, physical: u32) !void {
    const a = try f.symbol("dos64_address");
    f.poke(a,@truncate(physical)); f.poke(a+1,@truncate(physical>>8)); f.poke(a+2,@truncate(physical>>16));
}
fn initMemory(limit: u8, mode: u8) !Fixture {
    var f = try Fixture.init(); errdefer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"),limit);
    const r = try f.call("dos64_cache_init",50_000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
    f.poke(try f.symbol("dos64_memory_mode"),mode);
    return f;
}
fn read(f: *Fixture, physical: u32) !u8 {
    try address(f,physical);
    const r = try f.call("dos64_mem_read",5000);
    if ((r.p&1)!=0) {
        std.debug.print("read failed physical={x} code={d}\n",.{physical,f.peek(try f.symbol("dos64_memory_error"))});
        return error.MemoryRead;
    }
    return r.a;
}
fn write(f: *Fixture, physical: u32, value: u8) !void {
    try address(f,physical); f.poke(try f.symbol("dos64_mem_value"),value);
    const r = try f.call("dos64_mem_write",5000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
}
fn flush(f: *Fixture) !void {
    const r = try f.call("dos64_cache_flush",100_000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
}
fn acquire(f: *Fixture, physical: u32) !u8 {
    try address(f,physical);
    const r = try f.call("dos64_cache_acquire",5000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
    return f.peek(try f.symbol("dos64_cache_selected"));
}
fn release(f: *Fixture, frame: u8) !void {
    f.poke(try f.symbol("dos64_cache_selected"),frame);
    const r = try f.call("dos64_cache_release",1000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
}
fn ownership(f: *Fixture) !void {
    const map = try f.symbol("dos64_cache_map");
    const lo = try f.symbol("dos64_cache_tags_lo");
    const hi = try f.symbol("dos64_cache_tags_hi");
    const flags = try f.symbol("dos64_cache_flags");
    const limit = f.peek(try f.symbol("dos64_cache_limit"));
    var seen = [_]bool{false} ** 32;
    for (0..2048) |page| {
        const frame=f.peek(map+@as(u16,@intCast(page)));
        if (frame==0xff) continue;
        try std.testing.expect(frame<limit);
        try std.testing.expect(!seen[frame]); seen[frame]=true;
        try std.testing.expect((f.peek(flags+frame)&1)!=0);
        const tag = @as(u16,f.peek(lo+frame)) | (@as(u16,f.peek(hi+frame))<<8);
        try std.testing.expectEqual(@as(u16,@intCast(page)),tag);
    }
    for (0..32) |frame| try std.testing.expectEqual(seen[frame],(f.peek(flags+@as(u16,@intCast(frame)))&1)!=0);
}

test "20-bit assembly translation handles aliases carry wrap and seeded pairs" {
    var f=try Fixture.init(); defer f.deinit();
    const pairs=[_][2]u16{.{0,0},.{0xffff,0},.{0xffff,0x10},.{0xffff,0xffff},.{0x1234,0xffff},.{0x1000,0},.{0x0fff,0x10}};
    var seed:u32=0x808864;
    for (0..4103) |i| {
        seed=seed*%1664525+%1013904223;
        const segment:u16=if(i<pairs.len) pairs[i][0] else @truncate(seed>>16);
        const offset:u16=if(i<pairs.len) pairs[i][1] else @truncate(seed);
        try setWord(&f,"dos64_segment",segment); try setWord(&f,"dos64_offset",offset);
        f.initial_status=0xa9;
        const r=try f.call("dos64_physical",300);
        const a=try f.symbol("dos64_address");
        const result=@as(u32,f.word(a))|(@as(u32,f.peek(a+2))<<16);
        try std.testing.expectEqual((@as(u32,segment)*16+offset)%0x100000,result);
        try std.testing.expectEqual(@as(u8,0xa9),r.p);
        try std.testing.expectEqual(@as(u8,0x82),r.x);
        try std.testing.expectEqual(@as(u8,0x93),r.y);
        try std.testing.expectEqual(segment,f.word(try f.symbol("dos64_segment")));
    }
}

test "20-bit translation preserves all native flags at nibble and offset carries" {
    var f=try Fixture.init(); defer f.deinit();
    const pairs=[_][2]u16{
        .{0,0}, .{0xffff,0xffff}, .{0xffff,0x10}, .{0x0fff,0x10},
        .{0x7fff,0xffff}, .{0x8000,0x8000}, .{0xfedc,0xba98}, .{0x1234,0x5678},
        .{0x000f,0xff0f}, .{0x0010,0xff00}, .{0x00ff,0xf00f}, .{0x0100,0xf000},
        .{0x0ff0,0x00ff}, .{0xf000,0xffff}, .{0xfff0,0x00ff}, .{0xfff1,0x00ef},
    };
    for (0..256) |native_p| for (pairs) |pair| {
        try setWord(&f,"dos64_segment",pair[0]); try setWord(&f,"dos64_offset",pair[1]);
        f.initial_status=@intCast(native_p);
        const r=try f.call("dos64_physical",300);
        const a=try f.symbol("dos64_address");
        const result=@as(u32,f.word(a))|(@as(u32,f.peek(a+2))<<16);
        try std.testing.expectEqual((@as(u32,pair[0])*16+pair[1])&0xfffff,result);
        // The Peddle status ABI always reports bit5 set; all other bits,
        // including decimal, interrupt, carry and its modeled B bit survive.
        try std.testing.expectEqual(@as(u8,@intCast(native_p))|0x20,r.p);
        try std.testing.expectEqual(@as(u8,0x82),r.x);
        try std.testing.expectEqual(@as(u8,0x93),r.y);
        try std.testing.expectEqual(pair[0],f.word(try f.symbol("dos64_segment")));
        try std.testing.expectEqual(pair[1],f.word(try f.symbol("dos64_offset")));
        try std.testing.expectEqual(@as(u8,0x2f),f.peek(0));
        try std.testing.expectEqual(@as(u8,0x35),f.peek(1));
    };
}

test "cache cold initialization validates capacity and clears full page map" {
    for ([_]u8{0,33,255}) |limit| {
        var f=try Fixture.init(); defer f.deinit();
        f.poke(try f.symbol("dos64_cache_limit"),limit);
        const r=try f.call("dos64_cache_init",50_000);
        try std.testing.expectEqual(@as(u8,1),r.p&1);
        try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cache_ready")));
    }
    var f=try initMemory(32,0); defer f.deinit();
    try ownership(&f);
    try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));
    const map=try f.symbol("dos64_cache_map");
    for (0..2048) |i| try std.testing.expectEqual(@as(u8,0xff),f.peek(map+@as(u16,@intCast(i))));
}

test "every physical page and both page edges use only the one MiB guest arena" {
    var f=try initMemory(32,1); defer f.deinit();
    for (0..2048) |page| {
        const physical:u32=@intCast(page*512);
        c.dos64_reu_poke(f.machine,physical,@truncate(page));
        c.dos64_reu_poke(f.machine,physical+511,@truncate(page>>3));
        try std.testing.expectEqual(@as(u8,@truncate(page)),try read(&f,physical));
        try std.testing.expectEqual(@as(u8,@truncate(page>>3)),try read(&f,physical+511));
        if (page%127==0) try ownership(&f);
    }
    try std.testing.expectEqual(@as(u64,2048),c.dos64_dma_transfers(f.machine));
    try ownership(&f);
    for ([_]u32{0x100000,0x180000,0x200000,0x3fffff}) |a| try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,a));
}

test "segment aliases share one dirty frame and flush preserves neighboring bytes" {
    var f=try initMemory(2,1); defer f.deinit();
    for (0..512) |i| c.dos64_reu_poke(f.machine,0x10000+@as(u32,@intCast(i)),@truncate(i));
    try write(&f,0x10017,0xb9);
    try setWord(&f,"dos64_segment",0x0fff);try setWord(&f,"dos64_offset",0x27);
    _=try f.call("dos64_physical",300);
    const r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,0xb9),r.a);
    try std.testing.expectEqual(@as(u64,1),c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u8,0x17),c.dos64_reu_peek(f.machine,0x10017));
    try flush(&f);
    for (0..512) |i| try std.testing.expectEqual(if(i==0x17) @as(u8,0xb9) else @as(u8,@truncate(i)),c.dos64_reu_peek(f.machine,0x10000+@as(u32,@intCast(i))));
    try ownership(&f);
}

test "dirty eviction and seeded random accesses match an independent RAM oracle" {
    var f=try initMemory(2,1); defer f.deinit();
    var oracle=[_]u8{0} ** (512*9);
    var seed:u32=0x65108088;
    for (0..1200) |i| {
        seed=seed*%1103515245+%12345;
        const index:usize=@intCast((seed>>8)%oracle.len);
        const physical:u32=0x7f600+@as(u32,@intCast(index));
        if ((seed&3)!=0) {
            const value:u8=@truncate(seed>>20);
            try write(&f,physical,value);oracle[index]=value;
        } else try std.testing.expectEqual(oracle[index],try read(&f,physical));
        if (i%41==0) try ownership(&f);
    }
    try flush(&f);
    for (oracle,0..) |value,i| try std.testing.expectEqual(value,c.dos64_reu_peek(f.machine,0x7f600+@as(u32,@intCast(i))));
    try ownership(&f);
}

test "pinned frames survive replacement and pin exhaustion is bounded without DMA" {
    var f=try initMemory(2,1); defer f.deinit();
    c.dos64_reu_poke(f.machine,0x401ff,0xa6);
    c.dos64_reu_poke(f.machine,0x40400,0x3b);
    c.dos64_reu_poke(f.machine,0x40800,0x17);
    const a=try acquire(&f,0x401ff);
    const p=f.word(try f.symbol("dos64_mem_pointer"));
    const b=try acquire(&f,0x40400);
    try address(&f,0x40800);
    const transfers=c.dos64_dma_transfers(f.machine);
    const r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,2),f.peek(try f.symbol("dos64_memory_error")));
    try std.testing.expectEqual(transfers,c.dos64_dma_transfers(f.machine));
    try release(&f,b);try std.testing.expectEqual(@as(u8,0x17),try read(&f,0x40800));
    try std.testing.expectEqual(@as(u8,1),f.peek((try f.symbol("dos64_cache_pins"))+a));
    try std.testing.expectEqual(@as(u8,0xa6),f.peek(p));
    try release(&f,a);try ownership(&f);
    f.poke(try f.symbol("dos64_cache_selected"),a);
    const bad=try f.call("dos64_cache_release",1000);
    try std.testing.expectEqual(@as(u8,1),bad.p&1);
}

test "nested pins reject overflow and flushing keeps a pinned pointer valid" {
    var f=try initMemory(1,1); defer f.deinit();
    const frame=try acquire(&f,0x10);
    const again=try acquire(&f,0x10);
    try std.testing.expectEqual(frame,again);
    const pins=try f.symbol("dos64_cache_pins");
    try std.testing.expectEqual(@as(u8,2),f.peek(pins+frame));
    f.poke(pins+frame,255);
    try address(&f,0x10);
    const r=try f.call("dos64_cache_acquire",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,255),f.peek(pins+frame));
    f.poke(pins+frame,1);
    const p=f.word(try f.symbol("dos64_mem_pointer"));
    try write(&f,0x10,0x44);try flush(&f);
    try std.testing.expectEqual(@as(u8,0x44),f.peek(p));
    try std.testing.expectEqual(@as(u8,1),f.peek(pins+frame));
    try release(&f,frame);
}

test "PC bus protects ROM and holes while CGA and conventional RAM stay coherent" {
    var f=try initMemory(2,0); defer f.deinit();
    for ([_]u32{0xa0000,0xb7fff,0xbc000,0xeffff}) |a| {
        c.dos64_reu_poke(f.machine,a,0x37);
        try std.testing.expectEqual(@as(u8,255),try read(&f,a));try write(&f,a,0x88);
        try std.testing.expectEqual(@as(u8,0x37),c.dos64_reu_peek(f.machine,a));
    }
    try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));
    c.dos64_reu_poke(f.machine,0xfffff,0x42);
    try std.testing.expectEqual(@as(u8,0x42),try read(&f,0xfffff));try write(&f,0xfffff,0x23);
    try std.testing.expectEqual(@as(u8,0x42),try read(&f,0xfffff));
    try write(&f,0x9ffff,0x76);
    try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_video_dirty")));
    try write(&f,0xb8000,0x55);try write(&f,0xbbfff,0xaa);
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_video_dirty")));
    try std.testing.expectEqual(@as(u8,0x55),try read(&f,0xb8000));try flush(&f);
    for ([_]struct{a:u32,v:u8}{.{.a=0xbbfff,.v=0xaa},.{.a=0x9ffff,.v=0x76},.{.a=0xfffff,.v=0x42}}) |item| try std.testing.expectEqual(item.v,c.dos64_reu_peek(f.machine,item.a));
}

test "uninitialized access bad mode and physical overflow never issue DMA" {
    var f=try Fixture.init(); defer f.deinit();c.dos64_enable_reu(f.machine);
    try address(&f,0);var r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    f.poke(try f.symbol("dos64_cache_limit"),1);_=try f.call("dos64_cache_init",50_000);
    try address(&f,0x100000);r=try f.call("dos64_mem_write",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try address(&f,0);f.poke(try f.symbol("dos64_memory_mode"),2);r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));
}

test "partial dirty writeback failure retains the authoritative frame for retry" {
    var f=try initMemory(1,1);defer f.deinit();try write(&f,0x20100,0xc3);
    c.dos64_reu_fail_after(f.machine,0,16);try address(&f,0x30000);
    const r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,3),f.peek(try f.symbol("dos64_memory_error")));
    try ownership(&f);try std.testing.expectEqual(@as(u8,0xc3),try read(&f,0x20100));
    try flush(&f);try std.testing.expectEqual(@as(u8,0xc3),c.dos64_reu_peek(f.machine,0x20100));
}

test "partial load failure never publishes overwritten victim and retry reloads backing" {
    var f=try initMemory(1,1);defer f.deinit();try write(&f,0x10100,0x5b);
    c.dos64_reu_poke(f.machine,0x20000,0x6c);c.dos64_reu_fail_after(f.machine,1,32);
    try address(&f,0x20000);const r=try f.call("dos64_mem_read",5000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);try ownership(&f);
    try std.testing.expectEqual(@as(u8,0x5b),c.dos64_reu_peek(f.machine,0x10100));
    try std.testing.expectEqual(@as(u8,0x5b),try read(&f,0x10100));
    try std.testing.expectEqual(@as(u8,0x6c),try read(&f,0x20000));try ownership(&f);
}

test "warm read has no DMA and preserves host decimal and interrupt state" {
    var f=try initMemory(32,1);defer f.deinit();c.dos64_reu_poke(f.machine,0x73127,0x89);
    try std.testing.expectEqual(@as(u8,0x89),try read(&f,0x73127));
    f.initial_status=0x28;const before=c.dos64_get_regs(f.machine).cycles;
    try std.testing.expectEqual(@as(u8,0x89),try read(&f,0x73127));const r=c.dos64_get_regs(f.machine);
    try std.testing.expectEqual(@as(u8,0x08),r.p&0x0c);
    try std.testing.expectEqual(@as(u64,1),c.dos64_dma_transfers(f.machine));
    var buffer:[256]u8=undefined;
    const profile=try std.fmt.bufPrint(&buffer,"{{\"warm_read_cpu_cycles\":{d},\"dma_stalls\":\"unmodeled\",\"frame_count\":32,\"page_bytes\":512,\"mode\":\"all_ram\"}}\n",.{r.cycles-before});
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io,.{.sub_path="build/memory-profile.json",.data=profile});
}

test "shared cache probe evicts across REC seam and preserves untouched partial pages" {
    var f=try initMemory(32,0);defer f.deinit();
    for (0..256) |i| {
        c.dos64_reu_poke(f.machine,0x7fc00+@as(u32,@intCast(i)),0x77);
        c.dos64_reu_poke(f.machine,0x80300+@as(u32,@intCast(i)),0x66);
    }
    const start=c.dos64_get_regs(f.machine).cycles;
    const r=try f.call("dos64_cache_probe",3_000_000);
    try f.expectStatus(0xa5);
    try std.testing.expectEqual(@as(u8,0),f.peek((try f.symbol("dos64_mailbox"))+4));
    for (0..1536) |i| {
        const expected:u8=@as(u8,@truncate(i)) ^ @as(u8,@intCast(i>>8)) ^ 0xa7;
        try std.testing.expectEqual(expected,f.peek(0x6000+@as(u16,@intCast(i))));
        try std.testing.expectEqual(expected,c.dos64_reu_peek(f.machine,0x7fd00+@as(u32,@intCast(i))));
    }
    for (0..256) |i| {
        try std.testing.expectEqual(@as(u8,0x77),c.dos64_reu_peek(f.machine,0x7fc00+@as(u32,@intCast(i))));
        try std.testing.expectEqual(@as(u8,0x66),c.dos64_reu_peek(f.machine,0x80300+@as(u32,@intCast(i))));
    }
    try ownership(&f);
    try std.testing.expect(f.stack_high_water<=32);
    var buffer:[256]u8=undefined;
    const profile=try std.fmt.bufPrint(&buffer,"{{\"cpu_cycles\":{d},\"stack_high_water\":{d},\"dma_bytes\":{d},\"dma_transfers\":{d},\"physical_timing\":false}}\n",.{r.cycles-start,f.stack_high_water,c.dos64_dma_bytes(f.machine),c.dos64_dma_transfers(f.machine)});
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io,.{.sub_path="build/cache-probe-profile.json",.data=profile});
}

test "memory routines write only owned host frames metadata scratch and REU registers" {
    var f=try initMemory(32,1);defer f.deinit();
    try write(&f,0x51234,0x9e);
    const state_end:u16=try f.symbol("dos64_cache_tags_lo");
    for (0..65536) |i| {
        const a:u16=@intCast(i);
        if(c.dos64_was_written(f.machine,a)==0) continue;
        if(a<2 or (a>=0x20 and a<0xe0) or (a>=0x100 and a<0x200)) continue;
        if(a>=0x8000 and a<0xc000) continue;
        if(a>=0xdf00 and a<=0xdf0a) continue;
        if(a>=0xe000 and a<state_end+192) continue;
        std.debug.print("forbidden pager write at {x}\n",.{a});
        return error.ForbiddenPagerWrite;
    }
}


test "CPU-owned CLD translation independently covers every segment without widening public ABI" {
    var f=try Fixture.init();defer f.deinit();
    const seg=try f.symbol("dos64_segment");const off=try f.symbol("dos64_offset");const a=try f.symbol("dos64_address");
    for(0..65536)|i|{
        const s:u16=@intCast(i);const o:u16=@truncate(i*%40503+%0xfff1);
        try setWord(&f,"dos64_segment",s);try setWord(&f,"dos64_offset",o);
        f.initial_status=@as(u8,@truncate(i))&0xf7;
        const r=try f.call("dos64_physical_owned",300);
        try std.testing.expectEqual((@as(u32,s)*16+o)&0xfffff,@as(u32,f.word(a))|(@as(u32,f.peek(a+2))<<16));
        try std.testing.expectEqual(s,f.word(seg));try std.testing.expectEqual(o,f.word(off));
        try std.testing.expectEqual(@as(u8,0x82),r.x);try std.testing.expectEqual(@as(u8,0x93),r.y);
        try std.testing.expectEqual(@as(u8,0),r.p&8);
        try std.testing.expectEqual(@as(u8,0x2f),f.peek(0));try std.testing.expectEqual(@as(u8,0x35),f.peek(1));
    }
}

test "public byte operands retain decimal-safe read and write for every native status" {
    var f=try Fixture.init();defer f.deinit();c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"),1);
    for(0..256)|p|{
        _=try f.call("dos64_cache_flush",100000);_=try f.call("dos64_cache_init",50000);
        f.poke(try f.symbol("dos64_memory_mode"),1);
        f.poke(try f.symbol("dos64_operand_kind"),1);f.poke(try f.symbol("dos64_operand_width"),0);
        try setWord(&f,"dos64_operand_segment",0x1234);try setWord(&f,"dos64_operand_offset",0x5678);
        c.dos64_reu_poke(f.machine,0x179b8,0xa7);f.initial_status=@intCast(p);
        const r=try f.call("dos64_operand_read",10000);
        try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u8,@intCast(p))&8,r.p&8);
        try std.testing.expectEqual(@as(u16,0xa7),f.word(try f.symbol("dos64_cpu_value")));
        try setWord(&f,"dos64_cpu_value",0x5a);f.initial_status=@intCast(p);
        const w=try f.call("dos64_operand_write",10000);
        try std.testing.expectEqual(@as(u8,0),w.p&1);try std.testing.expectEqual(@as(u8,@intCast(p))&8,w.p&8);
        _=try f.call("dos64_cache_flush",100000);
        try std.testing.expectEqual(@as(u8,0x5a),c.dos64_reu_peek(f.machine,0x179b8));
    }
}

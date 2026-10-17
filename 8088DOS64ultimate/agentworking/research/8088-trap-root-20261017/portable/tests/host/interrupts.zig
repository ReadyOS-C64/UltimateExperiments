const trace=@import("trap_fixture.zig");
const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
const c=host.c;
fn word(f:*Fixture,a:u16,v:u16) void {f.poke(a,@truncate(v));f.poke(a+%1,@truncate(v>>8));}
fn reg(f:*Fixture,index:u16,v:u16) !void {word(f,(try f.symbol("dos64_guest"))+index*2,v);}
fn get(f:*Fixture,index:u16) !u16 {return f.word((try f.symbol("dos64_guest"))+index*2);}
fn bytes(f:*Fixture,seg:u16,off:u16,values:[]const u8) void {
    for(values,0..) |v,i| c.dos64_reu_poke(f.machine,(@as(u32,seg)*16+(off+%@as(u16,@intCast(i))))&0xfffff,v);
}
fn guestWord(f:*Fixture,seg:u16,off:u16,v:u16) void {bytes(f,seg,off,&.{@truncate(v),@truncate(v>>8)});}
fn init(frames:u8) !Fixture {
    var f=try Fixture.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"),frames);_=try f.call("dos64_cache_init",50_000);
    f.poke(try f.symbol("dos64_memory_mode"),1);_=try f.call("dos64_cpu_init",10_000);return f;
}
fn step(f:*Fixture) !void {const r=try f.call("dos64_cpu_step",100_000);try std.testing.expectEqual(@as(u8,0),r.p&1);}
fn flush(f:*Fixture) !void {const r=try f.call("dos64_cache_flush",100_000);try std.testing.expectEqual(@as(u8,0),r.p&1);}
fn reuWord(f:*Fixture,seg:u16,off:u16) u16 {
    return @as(u16,c.dos64_reu_peek(f.machine,(@as(u32,seg)*16+off)&0xfffff))|(@as(u16,c.dos64_reu_peek(f.machine,(@as(u32,seg)*16+(off+%1))&0xfffff))<<8);
}

test "INT uses guest IVT and IRET returns guest handler changes to saved flags" {
    var f=try init(2);defer f.deinit();
    try reg(&f,9,0x1000);try reg(&f,12,0x100);try reg(&f,10,0x2000);try reg(&f,4,0x800);
    try reg(&f,5,0xa55a);try reg(&f,13,0xf703);
    try trace.install(&f);
    bytes(&f,0x1000,0x100,&.{0xcd,0x13,0xf4});
    guestWord(&f,0,0x4c,0x200);guestWord(&f,0,0x4e,0x3000);
    // Normal guest code implements a handler: preserve BP, clear saved CF,
    // produce AX, and IRET. It is neither a host callback nor INT21 replacement.
    bytes(&f,0x3000,0x200,&.{0x55,0x8b,0xec,0x36,0x81,0x66,0x06,0xfe,0xff,0xb8,0x34,0x12,0x5d,0xcf});
    try step(&f);
    try std.testing.expectEqual(@as(u16,0x3000),try get(&f,9));
    try std.testing.expectEqual(@as(u16,0x200),try get(&f,12));
    try std.testing.expectEqual(@as(u16,0x7fa),try get(&f,4));
    try std.testing.expectEqual(@as(u16,0xf403),try get(&f,13));
    try flush(&f);
    try std.testing.expectEqual(@as(u16,0x102),reuWord(&f,0x2000,0x7fa));
    try std.testing.expectEqual(@as(u16,0x1000),reuWord(&f,0x2000,0x7fc));
    try std.testing.expectEqual(@as(u16,0xf703),reuWord(&f,0x2000,0x7fe));
    try trace.enterAndReturn(&f);
    for(0..6) |_| try step(&f);
    try std.testing.expectEqual(@as(u16,0x1000),try get(&f,9));
    try std.testing.expectEqual(@as(u16,0x102),try get(&f,12));
    try std.testing.expectEqual(@as(u16,0x800),try get(&f,4));
    try std.testing.expectEqual(@as(u16,0x1234),try get(&f,0));
    try std.testing.expectEqual(@as(u16,0xa55a),try get(&f,5));
    try std.testing.expectEqual(@as(u16,0xf702),try get(&f,13));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_irq_shadow")));
    try step(&f);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));
}

test "INT captures aliased IVT before writing original FLAGS CS IP stack frame" {
    var f=try init(1);defer f.deinit();
    try reg(&f,9,0x1000);try reg(&f,12,0x100);try reg(&f,10,0);try reg(&f,4,0x50);try reg(&f,13,0xf703);
    try trace.install(&f);
    bytes(&f,0x1000,0x100,&.{0xcd,0x13});guestWord(&f,0,0x4c,0x200);guestWord(&f,0,0x4e,0x4321);
    bytes(&f,0x4321,0x200,&.{0xcf});
    try step(&f);try std.testing.expectEqual(@as(u16,0x4321),try get(&f,9));try std.testing.expectEqual(@as(u16,0x200),try get(&f,12));
    try flush(&f);try std.testing.expectEqual(@as(u16,0xf703),reuWord(&f,0,0x4e));
    try std.testing.expectEqual(@as(u16,0x1000),reuWord(&f,0,0x4c));try std.testing.expectEqual(@as(u16,0x102),reuWord(&f,0,0x4a));
    try trace.enterAndReturn(&f);
    try step(&f);try std.testing.expectEqual(@as(u16,0x1000),try get(&f,9));try std.testing.expectEqual(@as(u16,0x102),try get(&f,12));
    try std.testing.expectEqual(@as(u16,0x50),try get(&f,4));try std.testing.expectEqual(@as(u16,0xf703),try get(&f,13));
}

test "INT3 INTO and final IVT entry preserve software routing and stack wrap" {
    for([_]u8{0xcc,0xcd,0xce}) |opcode| {
        var f=try init(2);defer f.deinit();
        const vector:u16=if(opcode==0xcc) 3 else if(opcode==0xcd) 255 else 4;
        try reg(&f,9,0xffff);try reg(&f,12,0xffff);try reg(&f,10,0x1234);try reg(&f,4,1);try reg(&f,13,0xffd7);
        try trace.install(&f);
        bytes(&f,0xffff,0xffff,&.{0x26,opcode,0xff});
        guestWord(&f,0,vector*4,0xffff);guestWord(&f,0,vector*4+2,0x2000);bytes(&f,0x2000,0xffff,&.{0xcf});
        try step(&f);try std.testing.expectEqual(@as(u16,0x2000),try get(&f,9));try std.testing.expectEqual(@as(u16,0xffff),try get(&f,12));
        try std.testing.expectEqual(@as(u16,0xfffb),try get(&f,4));
        try trace.enterAndReturn(&f);
        try step(&f);try std.testing.expectEqual(@as(u16,0xffff),try get(&f,9));
        try std.testing.expectEqual(@as(u16,if(opcode==0xcd) 2 else 1),try get(&f,12));
        try std.testing.expectEqual(@as(u16,1),try get(&f,4));try std.testing.expectEqual(@as(u16,0xffd7),try get(&f,13));
    }
    var f=try init(1);defer f.deinit();try reg(&f,9,0);try reg(&f,12,0x100);try reg(&f,4,0x800);try reg(&f,13,0xf703);
    bytes(&f,0,0x100,&.{0xce});try step(&f);
    try std.testing.expectEqual(@as(u16,0x101),try get(&f,12));try std.testing.expectEqual(@as(u16,0x800),try get(&f,4));try std.testing.expectEqual(@as(u16,0xf703),try get(&f,13));
}

test "software interrupt IVT memory failure latches without claiming a guest exception" {
    var f=try init(1);defer f.deinit();try reg(&f,9,0x1000);try reg(&f,12,0x100);try reg(&f,4,0x800);
    bytes(&f,0x1000,0x100,&.{0xcd,0x13});
    // Instruction fetch is one page load; fail the next IVT-page load.
    c.dos64_reu_fail_after(f.machine,1,16);
    const r=try f.call("dos64_cpu_step",100_000);try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,3),f.peek(try f.symbol("dos64_cpu_status")));
    try std.testing.expectEqual(@as(u16,0x100),try get(&f,12));try std.testing.expectEqual(@as(u16,0x800),try get(&f,4));
    try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));
}

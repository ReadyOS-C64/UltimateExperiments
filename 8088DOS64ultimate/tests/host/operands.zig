const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
const c=host.c;
fn word(f:*Fixture,a:u16,v:u16) void {f.poke(a,@truncate(v));f.poke(a+1,@truncate(v>>8));}
fn init(frames:u8) !Fixture {
    var f=try Fixture.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"),frames);
    _=try f.call("dos64_cache_init",50_000);f.poke(try f.symbol("dos64_memory_mode"),1);
    _=try f.call("dos64_cpu_init",10_000);return f;
}
fn code(f:*Fixture,ip:u16,bytes:[]const u8) !void {
    const g=try f.symbol("dos64_guest");word(f,g+18,0);word(f,g+24,ip);
    for(bytes,0..) |v,i| c.dos64_reu_poke(f.machine,ip+%@as(u16,@intCast(i)),v);
    _=try f.call("dos64_cache_init",50_000);
}
fn ok(f:*Fixture,name:[]const u8) !void {
    const r=try f.call(name,100_000);try std.testing.expectEqual(@as(u8,0),r.p&1);
}

test "assembled ModRM decoder matches independent complete 16-bit address matrix" {
    var f=try init(2);defer f.deinit();const g=try f.symbol("dos64_guest");
    // BX+SI wraps, BP forms choose SS, direct mod00/rm6 chooses DS.
    word(&f,g+6,0xfff0);word(&f,g+10,0x7ff8);word(&f,g+12,0x0022);word(&f,g+14,0xffe1);
    const segments=[_]u16{0x1234,0,0x4321,0x7654};
    for(segments,0..) |v,i| word(&f,g+16+@as(u16,@intCast(2*i)),v);
    const bases=[_]u16{0x0012,0xffd1,0x801a,0x7fd9,0x0022,0xffe1,0x7ff8,0xfff0};
    const overrides=[_]u8{0xff,16,18,20,22};
    var count:usize=0;
    for(0..2) |width| for(0..3) |mode| for(0..8) |rm| for(overrides) |override| for([_]u16{0x007f,0xff80,0xffff}) |displacement| {
        var bytes=[_]u8{0,0,0};bytes[0]=@as(u8,@intCast(mode*64+5*8+rm));
        var length:usize=1;var expected=bases[rm];
        if(mode==0 and rm==6) {bytes[1]=0x34;bytes[2]=0x12;length=3;expected=0x1234;}
        if(mode==1) {bytes[1]=@truncate(displacement);length=2;expected+%=displacement;}
        if(mode==2) {bytes[1]=@truncate(displacement);bytes[2]=@truncate(displacement>>8);length=3;expected+%=displacement;}
        try code(&f,0x100,bytes[0..length]);
        f.poke(try f.symbol("dos64_operand_width"),@intCast(width));f.poke(try f.symbol("cpu_override"),override);
        try ok(&f,"dos64_decode_rm");
        const use_ss=(rm==2 or rm==3 or (rm==6 and mode!=0));
        const segment_index:usize=if(override==0xff) (if(use_ss) 2 else 3) else (override-16)/2;
        if(f.word(try f.symbol("dos64_operand_offset"))!=expected or f.word(try f.symbol("dos64_operand_segment"))!=segments[segment_index]) {
            std.debug.print("EA mismatch mod={d} rm={d} width={d} override={x} disp={x}\n",.{mode,rm,width,override,displacement});return error.EffectiveAddressMismatch;
        }
        try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_operand_kind")));
        try std.testing.expectEqual(@as(u8,5),f.peek(try f.symbol("dos64_modrm_reg")));
        try std.testing.expectEqual(@as(u8,@intCast(mode)),f.peek(try f.symbol("dos64_modrm_mod")));
        try std.testing.expectEqual(@as(u16,@intCast(0x100+length)),f.word(g+24));count+=1;
    };
    try std.testing.expectEqual(@as(usize,720),count);
}

test "register operands preserve neighbouring bytes including AH CH DH BH" {
    var f=try init(1);defer f.deinit();const g=try f.symbol("dos64_guest");
    const byte_offsets=[_]u16{0,2,4,6,1,3,5,7};
    const value=try f.symbol("dos64_cpu_value");
    for(0..2) |width| for(0..8) |reg| {
        for(0..16) |i| f.poke(g+@as(u16,@intCast(i)),@as(u8,@intCast(0x20+i)));
        try code(&f,0x100,&.{@as(u8,@intCast(0xc0+reg))});
        f.poke(try f.symbol("dos64_operand_width"),@intCast(width));try ok(&f,"dos64_decode_rm");
        const offset:u16=if(width==0) byte_offsets[reg] else @intCast(reg*2);
        try std.testing.expectEqual(@as(u8,@intCast(offset)),f.peek(try f.symbol("dos64_operand_reg")));
        try ok(&f,"dos64_operand_read");
        const expected:u16=0x20+offset | (if(width==0) @as(u16,0) else (0x21+offset)<<8);
        try std.testing.expectEqual(expected,f.word(value));
        word(&f,value,0xa55a);try ok(&f,"dos64_operand_write");
        for(0..16) |i| {
            const expected_byte:u8=if(i==offset) 0x5a else if(width==1 and i==offset+1) 0xa5 else @intCast(0x20+i);
            try std.testing.expectEqual(expected_byte,f.peek(g+@as(u16,@intCast(i))));
        }
    };
}

test "decoded memory descriptor survives immediate fetch eviction and wrapping word store" {
    var f=try init(1);defer f.deinit();const g=try f.symbol("dos64_guest");word(&f,g+22,0x1000);
    // ModRM and displacement end page0; immediate is fetched from page1.
    try code(&f,0x1fd,&.{0x06,0xff,0xff,0x34,0x12});
    f.poke(try f.symbol("cpu_override"),0xff);f.poke(try f.symbol("dos64_operand_width"),1);
    try ok(&f,"dos64_decode_rm");try ok(&f,"cpu_fetch16");
    try std.testing.expectEqual(@as(u16,0x1234),f.word(try f.symbol("dos64_cpu_value")));
    try ok(&f,"dos64_operand_write");try ok(&f,"dos64_cache_flush");
    try std.testing.expectEqual(@as(u8,0x34),c.dos64_reu_peek(f.machine,0x1ffff));
    try std.testing.expectEqual(@as(u8,0x12),c.dos64_reu_peek(f.machine,0x10000));
    try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,0x20000));
    try ok(&f,"dos64_operand_read");try std.testing.expectEqual(@as(u16,0x1234),f.word(try f.symbol("dos64_cpu_value")));
    try std.testing.expectEqual(@as(u16,0xf002),f.word(g+26));
}

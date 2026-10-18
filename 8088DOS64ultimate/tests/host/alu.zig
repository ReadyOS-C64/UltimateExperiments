const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
fn word(f:*Fixture,a:u16,v:u16) void {f.poke(a,@truncate(v));f.poke(a+1,@truncate(v>>8));}

fn oracle(op:u8,width:u8,left:u16,right:u16,initial:u16) struct{value:u16,flags:u16,mask:u16} {
    const bits:u5=if(width==0) 8 else 16;
    const modulus:u32=@as(u32,1)<<bits;const mask=modulus-1;
    const lhs=@as(u32,left)&mask;
    const rhs:u32=if(op>=8) 1 else @as(u32,right)&mask;
    const carry:u32=if(op==2 or op==3) initial&1 else 0;
    const signed_left:i32=if(lhs>=modulus/2) @as(i32,@intCast(lhs))-@as(i32,@intCast(modulus)) else @intCast(lhs);
    const signed_right:i32=if(rhs>=modulus/2) @as(i32,@intCast(rhs))-@as(i32,@intCast(modulus)) else @intCast(rhs);
    const subtract=op==3 or op==5 or op==7 or op==9;
    const logic=op==1 or op==4 or op==6;
    const value:u32=if(logic) switch(op){1=>lhs|rhs,4=>lhs&rhs,6=>lhs^rhs,else=>unreachable} else if(subtract) (lhs+modulus-rhs-carry)&mask else (lhs+rhs+carry)&mask;
    const signed_result=if(subtract) signed_left-signed_right-@as(i32,@intCast(carry)) else signed_left+signed_right+@as(i32,@intCast(carry));
    var flags=initial&~@as(u16,0x08d5);
    const cf=if(op>=8) (initial&1)!=0 else if(logic) false else if(subtract) lhs<rhs+carry else lhs+rhs+carry>=modulus;
    if(cf)flags|=1;
    if(@popCount(@as(u8,@truncate(value)))%2==0)flags|=4;
    if(!logic and (if(subtract) (lhs&15)<(rhs&15)+carry else (lhs&15)+(rhs&15)+carry>15))flags|=0x10;
    if(value==0)flags|=0x40;
    if((value&(modulus/2))!=0)flags|=0x80;
    if(!logic and (signed_result < -@as(i32,@intCast(modulus/2)) or signed_result>=@as(i32,@intCast(modulus/2))))flags|=0x800;
    return .{.value=@intCast(value),.flags=flags,.mask=if(logic) 0xffef else 0xffff};
}

test "assembled ALU matches independent integer flag oracle at edges and seeded inputs" {
    var f=try Fixture.init();defer f.deinit();f.initial_status=0x28;
    const left=try f.symbol("dos64_alu_lhs");const right=try f.symbol("dos64_alu_rhs");
    const result=try f.symbol("dos64_alu_result");const operation=try f.symbol("dos64_alu_op");
    const width_address=try f.symbol("dos64_alu_width");const flags=(try f.symbol("dos64_guest"))+26;
    const edge=[_]u16{0,1,0x0f,0x10,0x7f,0x80,0xff,0x100,0x7fff,0x8000,0xffff};
    var seed:u32=0x8088a1;
    for(0..2) |wide| for(0..10) |op| for(0..160) |i| {
        seed=seed*%1664525+%1013904223;
        const a:u16=if(i<edge.len*edge.len) edge[i%edge.len] else @truncate(seed>>16);
        const b:u16=if(i<edge.len*edge.len) edge[i/edge.len] else @truncate(seed);
        const initial:u16=0xf702|@as(u16,@intCast(i&1));
        word(&f,left,a);word(&f,right,b);word(&f,flags,initial);
        f.poke(operation,@intCast(op));f.poke(width_address,@intCast(wide));
        const expected=oracle(@intCast(op),@intCast(wide),a,b,initial);
        const regs=try f.call("dos64_alu_apply",2000);
        if(f.word(result)!=expected.value or (f.word(flags)&expected.mask)!=(expected.flags&expected.mask)) {
            std.debug.print("ALU divergence op={d} word={d} a={x} b={x} cf={d} result={x}/{x} flags={x}/{x}\n",.{op,wide,a,b,initial&1,f.word(result),expected.value,f.word(flags),expected.flags});return error.AluMismatch;
        }
        try std.testing.expectEqual(@as(u8,0),regs.p&1);
        try std.testing.expectEqual(@as(u8,8),regs.p&0x0c);
    };
}

test "ALU rejects invalid width and operation without changing guest flags" {
    var f=try Fixture.init();defer f.deinit();const flags=(try f.symbol("dos64_guest"))+26;
    for([_][2]u8{.{10,0},.{0,2}}) |item| {
        word(&f,flags,0xfad7);f.poke(try f.symbol("dos64_alu_op"),item[0]);f.poke(try f.symbol("dos64_alu_width"),item[1]);
        const r=try f.call("dos64_alu_apply",1000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u16,0xfad7),f.word(flags));
    }
}

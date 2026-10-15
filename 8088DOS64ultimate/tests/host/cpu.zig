const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
const c=host.c;
const allocator=std.testing.allocator;
const names=[_] []const u8{"ax","cx","dx","bx","sp","bp","si","di","es","cs","ss","ds","ip","flags"};
const Registers=struct {ax:?u16=null,cx:?u16=null,dx:?u16=null,bx:?u16=null,sp:?u16=null,bp:?u16=null,si:?u16=null,di:?u16=null,es:?u16=null,cs:?u16=null,ss:?u16=null,ds:?u16=null,ip:?u16=null,flags:?u16=null};
const State=struct {regs:Registers,ram:[]const [2]u32};
const Case=struct {name:[]const u8,bytes:[]const u8,initial:State,final:State,hash:[]const u8,idx:u32,opcode:[]const u8,flags_mask:u16};

fn setWord(f:*Fixture,address:u16,value:u16) void {f.poke(address,@truncate(value));f.poke(address+1,@truncate(value>>8));}
fn reg(f:*Fixture,index:u16,value:u16) !void {setWord(f,(try f.symbol("dos64_guest"))+index*2,value);}
fn init(frames:u8,mode:u8) !Fixture {
    var f=try Fixture.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);
    f.poke(try f.symbol("dos64_cache_limit"),frames);
    _=try f.call("dos64_cache_init",50_000);
    f.poke(try f.symbol("dos64_memory_mode"),mode);
    _=try f.call("dos64_cpu_init",10_000);
    return f;
}
fn program(f:*Fixture,cs:u16,ip:u16,bytes:[]const u8) !void {
    try reg(f,9,cs);try reg(f,12,ip);
    for(bytes,0..) |value,i| {
        const offset=ip+%@as(u16,@intCast(i));
        const physical=(@as(u32,cs)*16+offset)&0xfffff;
        c.dos64_reu_poke(f.machine,physical,value);
    }
}
fn step(f:*Fixture) !void {
    const r=try f.call("dos64_cpu_step",100_000);
    if((r.p&1)!=0) {
        std.debug.print("CPU fault status={d} opcode={x}\n",.{f.peek(try f.symbol("dos64_cpu_status")),f.peek(try f.symbol("dos64_cpu_opcode"))});
        return error.CpuFault;
    }
}

test "real CPU core executes register immediates exchanges flags and halt" {
    var f=try init(32,1);defer f.deinit();
    const code=[_]u8{0xb8,0x34,0x12,0xbb,0xcd,0xab,0x93,0xb4,0x56,0xf9,0xf5,0xfc,0xf4};
    try program(&f,0,0x100,&code);
    for(0..8) |_| try step(&f);
    const g=try f.symbol("dos64_guest");
    try std.testing.expectEqual(@as(u16,0x56cd),f.word(g));
    try std.testing.expectEqual(@as(u16,0x1234),f.word(g+6));
    try std.testing.expectEqual(@as(u16,0xf002),f.word(g+26));
    try std.testing.expectEqual(@as(u16,0x10d),f.word(g+24));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));
    const count=f.word(try f.symbol("dos64_cpu_instructions"));try step(&f);
    try std.testing.expectEqual(count,f.word(try f.symbol("dos64_cpu_instructions")));
}

test "instruction fetch wraps IP independently of physical address wrap" {
    var f=try init(2,1);defer f.deinit();
    try program(&f,0x1000,0xffff,&.{0xb8,0x67,0x45});try step(&f);
    const g=try f.symbol("dos64_guest");
    try std.testing.expectEqual(@as(u16,0x4567),f.word(g));
    try std.testing.expectEqual(@as(u16,2),f.word(g+24));
    try std.testing.expectEqual(@as(u16,0x1000),f.word(g+18));
}

test "original 8088 segmented word helper wraps offset and preserves input words" {
    var f=try init(1,1);defer f.deinit();
    const segment=try f.symbol("dos64_segment");const offset=try f.symbol("dos64_offset");
    setWord(&f,segment,0x1234);setWord(&f,offset,0xffff);
    c.dos64_reu_poke(f.machine,0x2233f,0x34);c.dos64_reu_poke(f.machine,0x12340,0x12);c.dos64_reu_poke(f.machine,0x22340,0xee);
    var r=try f.call("dos64_cpu_word_read",10_000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);
    const value=try f.symbol("dos64_cpu_value");
    try std.testing.expectEqual(@as(u16,0x1234),f.word(value));
    try std.testing.expectEqual(@as(u16,0xffff),f.word(offset));
    setWord(&f,value,0xa55a);r=try f.call("dos64_cpu_word_write",10_000);
    try std.testing.expectEqual(@as(u8,0),r.p&1);_=try f.call("dos64_cache_flush",100_000);
    try std.testing.expectEqual(@as(u8,0x5a),c.dos64_reu_peek(f.machine,0x2233f));
    try std.testing.expectEqual(@as(u8,0xa5),c.dos64_reu_peek(f.machine,0x12340));
    try std.testing.expectEqual(@as(u8,0xee),c.dos64_reu_peek(f.machine,0x22340));
    try std.testing.expectEqual(@as(u16,0xffff),f.word(offset));
    try std.testing.expectEqual(@as(u16,0x1234),f.word(segment));
}

test "word transfer physical wrap and RAM-hole boundary dispatch each byte" {
    var f=try init(2,0);defer f.deinit();
    const seg=try f.symbol("dos64_segment");const off=try f.symbol("dos64_offset");const value=try f.symbol("dos64_cpu_value");
    setWord(&f,seg,0xffff);setWord(&f,off,0xf);
    c.dos64_reu_poke(f.machine,0xfffff,0x3c);c.dos64_reu_poke(f.machine,0,0x72);
    _=try f.call("dos64_cpu_word_read",10_000);try std.testing.expectEqual(@as(u16,0x723c),f.word(value));
    setWord(&f,seg,0x9fff);setWord(&f,off,0xf);setWord(&f,value,0x3456);
    _=try f.call("dos64_cpu_word_write",10_000);_=try f.call("dos64_cache_flush",100_000);
    try std.testing.expectEqual(@as(u8,0x56),c.dos64_reu_peek(f.machine,0x9ffff));
    try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,0xa0000));
}

test "prefix streams yield without invented length faults and last override wins" {
    var f=try init(2,1);defer f.deinit();
    var code=[_]u8{0x2e} ** 133;code[129]=0x3e;code[130]=0xa1;code[131]=0;code[132]=0;
    try program(&f,0x1000,0x200,&code);try reg(&f,11,0x2000);
    c.dos64_reu_poke(f.machine,0x20000,0xef);c.dos64_reu_poke(f.machine,0x20001,0xbe);
    for(0..2) |_| {try step(&f);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_yield")));}
    try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));
    try step(&f);const g=try f.symbol("dos64_guest");
    try std.testing.expectEqual(@as(u16,0xbeef),f.word(g));
    try std.testing.expectEqual(@as(u16,0x285),f.word(g+24));
    try std.testing.expectEqual(@as(u16,1),f.word(try f.symbol("dos64_cpu_instructions")));
    try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_yield")));
}

test "coherent self modification followed by jump is visible to instruction fetch" {
    var f=try init(1,1);defer f.deinit();
    try program(&f,0,0x100,&.{0xb8,5,0,0xa2,9,1,0xeb,0,0xb0,0,0xf4});
    for(0..5) |_| try step(&f);
    try std.testing.expectEqual(@as(u16,5),f.word(try f.symbol("dos64_guest")));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));
    try std.testing.expectEqual(@as(u16,5),f.word(try f.symbol("dos64_cpu_instructions")));
}

test "reset ROM far jump reaches guest code and repeated short loop stays bounded" {
    var f=try init(2,0);defer f.deinit();
    for([_]u8{0xea,0,1,0,0},0..) |v,i| c.dos64_reu_poke(f.machine,0xffff0+@as(u32,@intCast(i)),v);
    c.dos64_reu_poke(f.machine,0x100,0xf4);try step(&f);try step(&f);
    const g=try f.symbol("dos64_guest");try std.testing.expectEqual(@as(u16,0),f.word(g+18));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));
    var loop=try init(2,1);defer loop.deinit();try program(&loop,0,0x100,&.{0xeb,0xfe});
    for(0..100) |_| try step(&loop);
    try std.testing.expectEqual(@as(u16,0x100),loop.word((try loop.symbol("dos64_guest"))+24));
    try std.testing.expectEqual(@as(u16,100),loop.word(try loop.symbol("dos64_cpu_instructions")));
}

test "STI shadow covers following instruction and unsupported instruction latches" {
    var f=try init(2,1);defer f.deinit();try program(&f,0,0x100,&.{0xfb,0x90,0x31,0xc0});
    try step(&f);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_irq_shadow")));
    try step(&f);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_irq_shadow")));
    var r=try f.call("dos64_cpu_step",10_000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,2),f.peek(try f.symbol("dos64_cpu_status")));
    try std.testing.expectEqual(@as(u16,0x102),f.word((try f.symbol("dos64_guest"))+24));
    r=try f.call("dos64_cpu_step",1000);try std.testing.expectEqual(@as(u8,1),r.p&1);
}

test "word high-byte load failure restores input offset and returns failure" {
    var f=try init(1,1);defer f.deinit();
    setWord(&f,try f.symbol("dos64_segment"),0x1234);setWord(&f,try f.symbol("dos64_offset"),0xffff);
    c.dos64_reu_fail_after(f.machine,1,16);
    const r=try f.call("dos64_cpu_word_read",10_000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u16,0xffff),f.word(try f.symbol("dos64_offset")));
}

test "supplied DOS boot sector executes entry jump and CLI then reports missing XOR" {
    const disk=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img",allocator,.limited(400*1024));defer allocator.free(disk);
    try std.testing.expectEqual(@as(usize,360*1024),disk.len);
    var f=try init(32,0);defer f.deinit();
    try program(&f,0,0x7c00,disk[0..512]);try reg(&f,0,0x87aa);try reg(&f,13,0xf202);
    try step(&f);const g=try f.symbol("dos64_guest");
    try std.testing.expectEqual(@as(u16,0x7c36),f.word(g+24));
    try step(&f);try std.testing.expectEqual(@as(u16,0xf002),f.word(g+26));
    const r=try f.call("dos64_cpu_step",10_000);
    try std.testing.expectEqual(@as(u8,1),r.p&1);
    try std.testing.expectEqual(@as(u8,0x33),f.peek(try f.symbol("dos64_cpu_opcode")));
    try std.testing.expectEqual(@as(u16,0x7c37),f.word(g+24));
    try std.testing.expectEqual(@as(u16,0x87aa),f.word(g));
    try std.testing.expectEqual(@as(u16,2),f.word(try f.symbol("dos64_cpu_instructions")));
}

test "pinned hardware-generated original 8088 cases match registers and complete RAM" {
    const raw=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"tests/fixtures/8088-subset.json",allocator,.limited(4*1024*1024));defer allocator.free(raw);
    const parsed=try std.json.parseFromSlice([]Case,allocator,raw,.{});defer parsed.deinit();
    const expected_ram=try allocator.alloc(u8,1024*1024);defer allocator.free(expected_ram);
    const full=@import("test_options").full_cpu_corpus;
    var executed:usize=0;
    for(parsed.value) |t| {
        if(!full and t.idx>=2 and t.idx<24) continue;
        executed+=1;
        var f=try init(32,1);defer f.deinit();@memset(expected_ram,0);
        const g=try f.symbol("dos64_guest");
        inline for(names,0..) |name,i| if(@field(t.initial.regs,name)) |v| {setWord(&f,g+@as(u16,@intCast(i*2)),v);};
        for(t.initial.ram) |cell| {c.dos64_reu_poke(f.machine,cell[0],@intCast(cell[1]));expected_ram[cell[0]]=@intCast(cell[1]);}
        const cs=t.initial.regs.cs.?;const ip=t.initial.regs.ip.?;
        for(t.bytes,0..) |v,i| {
            const a=(@as(u32,cs)*16+(ip+%@as(u16,@intCast(i))))&0xfffff;
            c.dos64_reu_poke(f.machine,a,v);expected_ram[a]=v;
        }
        const r=try f.call("dos64_cpu_step",100_000);
        if((r.p&1)!=0) {std.debug.print("Hardware case failed {s} idx={d} {s}\n",.{t.opcode,t.idx,t.name});return error.HardwareCaseFault;}
        inline for(names,0..) |name,i| {
            const expected=@field(t.final.regs,name) orelse @field(t.initial.regs,name).?;
            const actual=f.word(g+@as(u16,@intCast(i*2)));
            const mask:u16=if(comptime std.mem.eql(u8,name,"flags")) t.flags_mask else 0xffff;
            if((expected&mask)!=(actual&mask)) {std.debug.print("First register divergence {s} {s} idx={d} expected={x} actual={x}\n",.{t.opcode,name,t.idx,expected,actual});return error.HardwareRegisterMismatch;}
        }
        _=try f.call("dos64_cache_flush",100_000);
        for(t.final.ram) |cell| expected_ram[cell[0]]=@intCast(cell[1]);
        const a=c.dos64_reu_compare(f.machine,0,expected_ram.ptr,expected_ram.len);
        if(a!=0xffffffff) {
            if(a>=expected_ram.len)return error.ComparisonBounds;
            std.debug.print("First RAM divergence {s} idx={d} address={x} expected={x} actual={x}\n",.{t.opcode,t.idx,a,expected_ram[a],c.dos64_reu_peek(f.machine,a)});return error.HardwareMemoryMismatch;
        }
    }
    var buffer:[128]u8=undefined;
    const profile=try std.fmt.bufPrint(&buffer,"{{\"hardware_cases\":{d},\"full_pinned_corpus\":{s},\"cycle_accuracy\":false}}\n",.{executed,if(full) "true" else "false"});
    try std.Io.Dir.cwd().writeFile(std.Options.debug_io,.{.sub_path=if(full) "build/cpu-corpus-full.json" else "build/cpu-corpus-fast.json",.data=profile});
}

test "full RAM oracle comparator detects first middle last mismatches and bounds" {
    var f=try init(32,1);defer f.deinit();
    const oracle=try allocator.alloc(u8,1024*1024);defer allocator.free(oracle);@memset(oracle,0);
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0,oracle.ptr,oracle.len));
    for([_]u32{0,0x54321,0xfffff}) |a| {
        c.dos64_reu_poke(f.machine,a,0x79);
        try std.testing.expectEqual(a,c.dos64_reu_compare(f.machine,0,oracle.ptr,oracle.len));
        c.dos64_reu_poke(f.machine,a,0);
    }
    try std.testing.expectEqual(@as(u32,0xfffffffe),c.dos64_reu_compare(f.machine,0x3fffff,oracle.ptr,2));
}

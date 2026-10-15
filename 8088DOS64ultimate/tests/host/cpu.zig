const std=@import("std");
const host=@import("machine.zig");
const Fixture=host.Fixture;
const c=host.c;
const allocator=std.testing.allocator;
const names=[_] []const u8{"ax","cx","dx","bx","sp","bp","si","di","es","cs","ss","ds","ip","flags"};
const Registers=struct {ax:?u16=null,cx:?u16=null,dx:?u16=null,bx:?u16=null,sp:?u16=null,bp:?u16=null,si:?u16=null,di:?u16=null,es:?u16=null,cs:?u16=null,ss:?u16=null,ds:?u16=null,ip:?u16=null,flags:?u16=null};
const State=struct {regs:Registers,ram:[]const [2]u32};
const Case=struct {name:[]const u8,bytes:[]const u8,initial:State,final:State,hash:[]const u8,idx:u32,opcode:[]const u8,flags_mask:u16,quick:bool,ram_masks:[]const [2]u32=&.{}};

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

fn normalizeUndefinedSavedFlags(t:Case,f:*Fixture,expected_ram:[]u8) !void {
    if(t.ram_masks.len==0)return;
    const divide=std.mem.eql(u8,t.opcode,"F6.6") or std.mem.eql(u8,t.opcode,"F6.7") or std.mem.eql(u8,t.opcode,"F7.6") or std.mem.eql(u8,t.opcode,"F7.7");
    const initial_sp=t.initial.regs.sp orelse return error.InvalidRamMask;
    const ss=t.initial.regs.ss orelse return error.InvalidRamMask;
    if(!divide or t.ram_masks.len!=2 or t.flags_mask!=0xf72a or t.final.regs.sp!=initial_sp-%6)return error.InvalidRamMask;
    const offset=initial_sp-%2;
    for(t.ram_masks,0..) |masked,i| {
        const address=(@as(u32,ss)*16+(offset+%@as(u16,@intCast(i))))&0xfffff;
        const bits:u32=if(i==0) t.flags_mask&255 else t.flags_mask>>8;
        if(masked[0]!=address or masked[1]!=bits or address>=expected_ram.len)return error.InvalidRamMask;
    }
    // Only source-projected DIV error frames may ignore undefined arithmetic
    // bits. Reserved/control bits and all adjacent memory remain exact.
    for(t.ram_masks) |masked| {
        const mask:u8=@intCast(masked[1]);
        expected_ram[masked[0]]=(expected_ram[masked[0]]&mask)|(c.dos64_reu_peek(f.machine,masked[0])&~mask);
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
    var f=try init(2,1);defer f.deinit();try program(&f,0,0x100,&.{0xfb,0x90,0xd6,0xc0});
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

test "supplied boot sector computes real root and data LBAs and requests the first disk read" {
    const disk=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img",allocator,.limited(400*1024));defer allocator.free(disk);
    try std.testing.expectEqual(@as(usize,360*1024),disk.len);
    var f=try init(32,0);defer f.deinit();
    try program(&f,0,0x7c00,disk[0..512]);try reg(&f,0,0x87aa);try reg(&f,13,0xf202);
    // A plain guest IRET is an explicit CPU fixture, not a BIOS implementation
    // or disk service. The rest of the IVT and PC memory start at zero.
    c.dos64_reu_poke(f.machine,0x4c,0);c.dos64_reu_poke(f.machine,0x4d,2);
    c.dos64_reu_poke(f.machine,0x4e,0);c.dos64_reu_poke(f.machine,0x4f,0);
    c.dos64_reu_poke(f.machine,0x200,0xcf);
    const g=try f.symbol("dos64_guest");
    var reached=false;
    for(0..256) |_| {
        if(f.word(g+24)==0x7c6e) {reached=true;break;}
        try step(&f);
    }
    try std.testing.expect(reached);
    try std.testing.expectEqual(@as(u16,0),f.word(g)); // AH=0 disk reset request
    try std.testing.expectEqual(@as(u16,0),f.word(g+4));
    try std.testing.expectEqual(@as(u16,0),f.word(g+2));
    try std.testing.expectEqual(@as(u16,0x7bf8),f.word(g+8));
    const saved_flags=f.word(g+26);
    try step(&f);
    try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));
    try std.testing.expectEqual(@as(u16,0),f.word(g+18));
    try std.testing.expectEqual(@as(u16,0x7bf2),f.word(g+8));
    try std.testing.expectEqual(saved_flags&~@as(u16,0x300),f.word(g+26));
    _=try f.call("dos64_cache_flush",100_000);
    try std.testing.expectEqual(@as(u8,0x70),c.dos64_reu_peek(f.machine,0x7bf2));
    try std.testing.expectEqual(@as(u8,0x7c),c.dos64_reu_peek(f.machine,0x7bf3));
    try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,0x7bf4));
    try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,0x7bf5));
    try std.testing.expectEqual(@as(u8,@truncate(saved_flags)),c.dos64_reu_peek(f.machine,0x7bf6));
    try std.testing.expectEqual(@as(u8,@truncate(saved_flags>>8)),c.dos64_reu_peek(f.machine,0x7bf7));
    try step(&f); // IRET
    try std.testing.expectEqual(@as(u16,0x7c70),f.word(g+24));
    try std.testing.expectEqual(@as(u16,0x7bf8),f.word(g+8));
    try std.testing.expectEqual(saved_flags,f.word(g+26));
    reached=false;
    for(0..256) |_| {
        if(f.word(g+24)==0x7d73) {reached=true;break;}
        try step(&f);
    }
    try std.testing.expect(reached);
    // Stop before the read interrupt. The reset IRET stub supplies no data.
    try std.testing.expectEqual(@as(u16,0x0201),f.word(g)); // AH=read, AL=one sector
    try std.testing.expectEqual(@as(u16,0x0500),f.word(g+6));
    try std.testing.expectEqual(@as(u16,0),f.word(g+16)); // ES:BX=0000:0500
    try std.testing.expectEqual(@as(u16,0x0006),f.word(g+2)); // cylinder0, sector6
    try std.testing.expectEqual(@as(u16,0),f.word(g+4)); // head0, drive0
    _=try f.call("dos64_cache_flush",100_000);
    const root_lba=@as(u16,c.dos64_reu_peek(f.machine,0x7c3f))|(@as(u16,c.dos64_reu_peek(f.machine,0x7c40))<<8);
    const data_lba=@as(u16,c.dos64_reu_peek(f.machine,0x7c37))|(@as(u16,c.dos64_reu_peek(f.machine,0x7c38))<<8);
    try std.testing.expectEqual(@as(u16,5),root_lba);
    try std.testing.expectEqual(@as(u16,12),data_lba);

}

test "pinned hardware-generated original 8088 cases match registers and complete RAM" {
    const raw=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"tests/fixtures/8088-subset.json",allocator,.limited(4*1024*1024));defer allocator.free(raw);
    const parsed=try std.json.parseFromSlice([]Case,allocator,raw,.{});defer parsed.deinit();
    const expected_ram=try allocator.alloc(u8,1024*1024);defer allocator.free(expected_ram);
    const full=@import("test_options").full_cpu_corpus;
    var executed:usize=0;var maximum_slices:usize=0;
    for(parsed.value) |t| {
        if(!full and !t.quick) continue;
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
        // A single hardware string instruction can span bounded target slices.
        // Stop only at one completed guest instruction, never at an arbitrary
        // intermediate REP state, with finite call and aggregate cycle limits.
        const completed=try f.symbol("dos64_cpu_instructions");
        var continuations:usize=0;var total_cycles:u64=0;
        while(f.word(completed)==0) {
            if(continuations>=256 or total_cycles>=10_000_000) {
                std.debug.print("Hardware continuation budget {s} idx={d} slices={d} cycles={d}\n",.{t.opcode,t.idx,continuations,total_cycles});return error.HardwareContinuationBudget;
            }
            const before=c.dos64_get_regs(f.machine).cycles;
            const r=f.call("dos64_cpu_step",100_000) catch |err| {
                std.debug.print("Hardware execution error {s} idx={d} slice={d}: {s}\n",.{t.opcode,t.idx,continuations,@errorName(err)});return err;
            };
            total_cycles+=r.cycles-before;continuations+=1;
            if((r.p&1)!=0) {std.debug.print("Hardware case failed {s} idx={d} {s}\n",.{t.opcode,t.idx,t.name});return error.HardwareCaseFault;}
        }
        try std.testing.expectEqual(@as(u16,1),f.word(completed));
        maximum_slices=@max(maximum_slices,continuations);
        inline for(names,0..) |name,i| {
            const expected=@field(t.final.regs,name) orelse @field(t.initial.regs,name).?;
            const actual=f.word(g+@as(u16,@intCast(i*2)));
            const mask:u16=if(comptime std.mem.eql(u8,name,"flags")) t.flags_mask else 0xffff;
            if((expected&mask)!=(actual&mask)) {std.debug.print("First register divergence {s} {s} idx={d} expected={x} actual={x}\n",.{t.opcode,name,t.idx,expected,actual});return error.HardwareRegisterMismatch;}
        }
        _=try f.call("dos64_cache_flush",100_000);
        for(t.final.ram) |cell| expected_ram[cell[0]]=@intCast(cell[1]);
        try normalizeUndefinedSavedFlags(t,&f,expected_ram);
        const a=c.dos64_reu_compare(f.machine,0,expected_ram.ptr,expected_ram.len);
        if(a!=0xffffffff) {
            if(a>=expected_ram.len)return error.ComparisonBounds;
            std.debug.print("First RAM divergence {s} idx={d} address={x} expected={x} actual={x}\n",.{t.opcode,t.idx,a,expected_ram[a],c.dos64_reu_peek(f.machine,a)});return error.HardwareMemoryMismatch;
        }
    }
    var buffer:[192]u8=undefined;
    const profile=try std.fmt.bufPrint(&buffer,"{{\"hardware_cases\":{d},\"full_pinned_corpus\":{s},\"cycle_accuracy\":false,\"maximum_slices\":{d}}}\n",.{executed,if(full) "true" else "false",maximum_slices});
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

fn branchCondition(condition:usize,flags:u16) bool {
    const carry=(flags&1)!=0;const parity=(flags&4)!=0;const zero=(flags&0x40)!=0;
    const sign=(flags&0x80)!=0;const overflow=(flags&0x800)!=0;
    return switch(condition) {
        0=>overflow,1=>!overflow,2=>carry,3=>!carry,4=>zero,5=>!zero,
        6=>carry or zero,7=>!carry and !zero,8=>sign,9=>!sign,
        10=>parity,11=>!parity,12=>sign!=overflow,13=>sign==overflow,
        14=>zero or sign!=overflow,15=>!zero and sign==overflow,
        else=>unreachable,
    };
}

test "all original Jcc conditions and 60 aliases match every relevant flag combination" {
    var f=try init(2,1);defer f.deinit();const g=try f.symbol("dos64_guest");
    for([_]u8{0x60,0x70}) |base| for(0..16) |condition| {
        // Opcode at FFFF and displacement at 0000 guard instruction-offset wrap.
        _=try f.call("dos64_cache_init",50_000);
        try program(&f,0x1234,0xffff,&.{base+@as(u8,@intCast(condition)),0x80});
        for(0..32) |combination| {
            var flags:u16=0xf602;
            for([_]u16{1,4,0x40,0x80,0x800},0..) |mask,bit| if((combination&(@as(usize,1)<<@as(u6,@intCast(bit))))!=0) {flags|=mask;};
            setWord(&f,g+24,0xffff);setWord(&f,g+26,flags);try step(&f);
            const expected:u16=if(branchCondition(condition,flags)) 0xff81 else 1;
            if(f.word(g+24)!=expected) {
                std.debug.print("Jcc mismatch opcode={x} flags={x} ip={x} expected={x}\n",.{base+condition,flags,f.word(g+24),expected});return error.BranchConditionMismatch;
            }
            try std.testing.expectEqual(flags,f.word(g+26));
            try std.testing.expectEqual(@as(u16,0x1234),f.word(g+18));
        }
    };
    try std.testing.expectEqual(@as(u16,1024),f.word(try f.symbol("dos64_cpu_instructions")));
}

test "LOOP family wraps counters preserves flags and applies signed prefixed displacement" {
    var f=try init(2,1);defer f.deinit();const g=try f.symbol("dos64_guest");
    for(0..4) |operation| for([_]u8{0x80,0x7f}) |displacement| {
        _=try f.call("dos64_cache_init",50_000);
        try program(&f,0x1234,0xffff,&.{0x2e,0xe0+@as(u8,@intCast(operation)),displacement});
        for([_]u16{0,1,2,0xffff}) |cx| for([_]bool{false,true}) |zero| {
            const flags:u16=0xf797|(if(zero) @as(u16,0x40) else 0);
            const after:u16=if(operation==3) cx else cx-%1;
            const taken=if(operation==3) cx==0 else after!=0 and (operation==2 or (operation==0 and !zero) or (operation==1 and zero));
            setWord(&f,g+2,cx);setWord(&f,g+24,0xffff);setWord(&f,g+26,flags);try step(&f);
            const target:u16=if(displacement==0x80) 0xff82 else 0x81;
            try std.testing.expectEqual(if(taken) target else @as(u16,2),f.word(g+24));
            try std.testing.expectEqual(after,f.word(g+2));try std.testing.expectEqual(flags,f.word(g+26));
        };
    };
    try std.testing.expectEqual(@as(u16,64),f.word(try f.symbol("dos64_cpu_instructions")));
}


test "divide-error RAM masks admit only undefined saved flags and detect control or adjacent corruption" {
    var f=try init(32,1);defer f.deinit();
    const expected=try allocator.alloc(u8,1024*1024);defer allocator.free(expected);
    const masks=[_][2]u32{.{0xfe,0x2a},.{0xff,0xf7}};
    const t=Case{.name="DIV error mask fixture",.bytes=&.{0xf6,0xf0},.hash="host-mask-negative-test",.idx=0,.opcode="F6.6",.flags_mask=0xf72a,.quick=true,.ram_masks=&masks,
        .initial=.{.regs=.{.ss=0,.sp=0x100},.ram=&.{}},.final=.{.regs=.{.sp=0xfa},.ram=&.{}}};
    @memset(expected,0);expected[0xfe]=2;expected[0xff]=0xf2;
    c.dos64_reu_poke(f.machine,0xfe,2^0xd5);c.dos64_reu_poke(f.machine,0xff,0xf2^8);
    try normalizeUndefinedSavedFlags(t,&f,expected);
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0,expected.ptr,expected.len));
    // Reserved low bits; TF/IF/DF; reserved high bits; adjacent return-frame byte.
    for([_][2]u32{.{0xfe,2},.{0xfe,8},.{0xfe,0x20},.{0xff,1},.{0xff,2},.{0xff,4},.{0xff,0x10},.{0xfd,1}}) |corruption| {
        @memset(expected,0);expected[0xfe]=2;expected[0xff]=0xf2;
        c.dos64_reu_poke(f.machine,0xfd,0);c.dos64_reu_poke(f.machine,0xfe,2);c.dos64_reu_poke(f.machine,0xff,0xf2);
        const address=corruption[0];c.dos64_reu_poke(f.machine,address,c.dos64_reu_peek(f.machine,address)^@as(u8,@intCast(corruption[1])));
        try normalizeUndefinedSavedFlags(t,&f,expected);
        try std.testing.expectEqual(address,c.dos64_reu_compare(f.machine,0,expected.ptr,expected.len));
    }
    var invalid=t;invalid.opcode="F6.4";
    try std.testing.expectError(error.InvalidRamMask,normalizeUndefinedSavedFlags(invalid,&f,expected));
    invalid=t;invalid.final.regs.sp=0x100;
    try std.testing.expectError(error.InvalidRamMask,normalizeUndefinedSavedFlags(invalid,&f,expected));
    invalid=t;invalid.flags_mask=0xffff;
    try std.testing.expectError(error.InvalidRamMask,normalizeUndefinedSavedFlags(invalid,&f,expected));
    invalid=t;invalid.ram_masks=&.{.{0xfd,0x2a},.{0xff,0xf7}};
    try std.testing.expectError(error.InvalidRamMask,normalizeUndefinedSavedFlags(invalid,&f,expected));
    invalid=t;invalid.ram_masks=&.{.{0xfe,0},.{0xff,0xf7}};
    try std.testing.expectError(error.InvalidRamMask,normalizeUndefinedSavedFlags(invalid,&f,expected));
}

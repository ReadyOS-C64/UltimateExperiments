const std=@import("std");
const host=@import("machine.zig");const F=host.Fixture;const c=host.c;
fn put(f:*F,n:[]const u8,v:u8)!void{f.poke(try f.symbol(n),v);}
fn get(f:*F,n:[]const u8)!u8{return f.peek(try f.symbol(n));}
fn w(f:*F,a:u16,v:u16)void{f.poke(a,@truncate(v));f.poke(a+1,@truncate(v>>8));}
fn d(f:*F,a:u16,v:u32)void{for(0..4)|i|f.poke(a+@as(u16,@intCast(i)),@truncate(v>>@as(u5,@intCast(i*8))));}
fn rd(f:*F,a:u16)u32{var v:u32=0;for(0..4)|i|v|=@as(u32,f.peek(a+@as(u16,@intCast(i))))<<@as(u5,@intCast(i*8));return v;}
fn init()!F{var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine); f.poke(0,0x2f); f.poke(1,0x35);_ = try f.call("dos64_overlay_init",100000);try put(&f,"dos64_overlay_reu_mib",4);_ = try f.call("dos64_overlay_bootstrap",1000000);try put(&f,"dos64_overlay_requested",7);_ = try f.call("dos64_overlay_acquire",100000);_ = try f.call("dos64_overlay_release",100000);try put(&f,"dos64_cache_limit",2);_ = try f.call("dos64_cache_init",100000);try put(&f,"dos64_memory_mode",1);_ = try f.call("dos64_cpu_init",100000);_ = try f.call("dos64_disk_init",100000);try put(&f,"dos64_cold_open",0xa5);return f;}
fn control(f:*F,status:u8)!void{const r=try f.call("dos64_floppy_control",1000000);try std.testing.expectEqual(status,r.a);try std.testing.expectEqual(@as(u8,if(status==0)0 else 1),r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);try std.testing.expectEqual(status,try get(f,"dos64_floppy_status"));}
fn rq(f:*F,op:u8,drive:u8)!u16{const q=try f.symbol("dos64_floppy_request");for(0..27)|i|f.poke(q+@as(u16,@intCast(i)),0);f.poke(q,op);f.poke(q+1,drive);f.poke(q+4,4);return q;}
fn bpb(f:*F,base:u32)void{for(0..32)|i|c.dos64_reu_poke(f.machine,base+@as(u32,@intCast(i)),0);const offsets=[_]u8{11,12,19,20,21,24,25,26,27,14,15,16};const values=[_]u8{0,2,0xd0,2,0xfd,9,0,2,0,1,0,2};for(offsets,values)|o,v|c.dos64_reu_poke(f.machine,base+o,v);}
fn prepare(f:*F,drive:u8,flags:u8)!u32{const q=try rq(f,1,drive);f.poke(q+2,flags);d(f,q+23,0x12345600+@as(u32,drive));try control(f,0);return rd(f,q+5)&0xffffff;}
fn commit(f:*F)!void{const q=try f.symbol("dos64_floppy_request");f.poke(q,2);f.poke(q+3,0xa5);try control(f,0);}
fn mount(f:*F,drive:u8,flags:u8,tag:u8)!u32{const base=try prepare(f,drive,flags);for(0..360*1024)|i|c.dos64_reu_poke(f.machine,base+@as(u32,@intCast(i)),tag^@as(u8,@truncate(i*13)));bpb(f,base);try commit(f);return base;}
fn io(f:*F,fnc:u8,drive:u8,count:u8,lba:u16,status:u8)!void{const g=try f.symbol("dos64_guest");const cy=lba/18;const head=(lba%18)/9;const sec=lba%9+1;w(f,g,(@as(u16,fnc)<<8)|count);w(f,g+2,(cy<<8)|sec);w(f,g+4,(head<<8)|drive);w(f,g+6,0x2000);w(f,g+16,0);const r=try f.call("dos64_disk_transfer",2000000);try std.testing.expectEqual(status,r.a);try std.testing.expectEqual(@as(u8,if(status==0)0 else 1),r.p&1);try std.testing.expectEqual(@as(u8,if(status==0)count else 0),f.peek(g));try std.testing.expectEqual(status,f.peek(g+1));}
fn guest(f:*F,address:u16,value:?u8)!u8{const a=try f.symbol("dos64_address");w(f,a,address);f.poke(a+2,0);if(value)|v|{try put(f,"dos64_mem_value",v);_ = try f.call("dos64_mem_write",100000);}const r=try f.call("dos64_mem_read",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);return r.a;}
fn snapshot(f:*F,drive:u8)!void{const q=try f.symbol("dos64_floppy_request");const off=@as(u16,drive)*4;d(f,q+15,rd(f,try f.symbol("dos64_disk_mount_generation")+off));d(f,q+19,rd(f,try f.symbol("dos64_disk_content_generation")+off));}

test "independent actual A and B reads writes and verify preserve other full image"{var f=try init();defer f.deinit();const a=try mount(&f,0,0,0xa7);const b=try mount(&f,1,0,0x52);try std.testing.expect(a!=b);const bcopy=try std.testing.allocator.alloc(u8,360*1024);defer std.testing.allocator.free(bcopy);for(bcopy,0..)|*v,i|v.*=c.dos64_reu_peek(f.machine,b+@as(u32,@intCast(i)));for([_]u16{0,8,9,127,128,719})|lba|{try io(&f,2,0,1,lba,0);for(0..512)|i|try std.testing.expectEqual(c.dos64_reu_peek(f.machine,a+@as(u32,lba)*512+@as(u32,@intCast(i))),try guest(&f,0x2000+@as(u16,@intCast(i)),null));try io(&f,2,1,1,lba,0);for(0..512)|i|try std.testing.expectEqual(bcopy[@as(usize,lba)*512+i],try guest(&f,0x2000+@as(u16,@intCast(i)),null));} _ = try guest(&f,0x2011,0x99);try io(&f,3,0,1,719,0);try std.testing.expectEqual(@as(u8,0x99),c.dos64_reu_peek(f.machine,a+719*512+17));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,b,bcopy.ptr,bcopy.len));try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_dirty"));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_disk_dirty")+1));try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_content_generation")));try io(&f,4,1,2,127,0);}

test "readonly failures and empty drives distinguish installed geometry from media presence"{var f=try init();defer f.deinit();_ = try mount(&f,1,1,0x72);try io(&f,2,0,1,0,0x80);try io(&f,3,1,1,0,3);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_disk_dirty")+1));try std.testing.expectEqual(@as(u32,0),rd(&f,try f.symbol("dos64_disk_content_generation")+4));const g=try f.symbol("dos64_guest");for([_]u8{0,1})|drive|{w(&f,g,0x0800);w(&f,g+4,drive);const r=try f.call("dos64_disk_transfer",1000000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u16,0x2709),f.word(g+2));try std.testing.expectEqual(@as(u16,0x0102),f.word(g+4));try std.testing.expectEqual(@as(u16,1),f.word(g+6));try std.testing.expectEqual(@as(u16,0xf000),f.word(g+16));}try io(&f,2,2,1,0,0x80);}

test "three arena rotation never stages mounted A or B and stale capability cannot publish"{var f=try init();defer f.deinit();var a=try mount(&f,0,0,1);var b=try mount(&f,1,0,2);for(0..8)|i|{const drive:u8=@intCast(i%2);const base=try prepare(&f,drive,0);try std.testing.expect(base!=a and base!=b);bpb(&f,base);const q=try f.symbol("dos64_floppy_request");f.poke(q,2);f.poke(q+3,0xa5);f.poke(q+11,f.peek(q+11)^0x80);try control(&f,4);f.poke(q+11,f.peek(q+11)^0x80);try commit(&f);if(drive==0)a=base else b=base;try std.testing.expect(a!=b);} }

test "incoming incomplete geometry IO and cancel failures leave old media authoritative"{var f=try init();defer f.deinit();const old=try mount(&f,0,0,0x56);const oldgen=rd(&f,try f.symbol("dos64_disk_mount_generation"));const stage=try prepare(&f,0,0);const q=try f.symbol("dos64_floppy_request");f.poke(q,2);try control(&f,1);f.poke(q+3,0xa5);try control(&f,6);bpb(&f,stage);c.dos64_reu_fail_after(f.machine,0,16);try control(&f,5);try std.testing.expectEqual(oldgen,rd(&f,try f.symbol("dos64_disk_mount_generation")));try std.testing.expectEqual(@as(u8,@truncate(old>>16)),f.peek(try f.symbol("dos64_disk_reu_base")+2));try io(&f,2,0,1,719,0);try std.testing.expectEqual(@as(u8,0x56^@as(u8,@truncate(719*512*13))),try guest(&f,0x2000,null));f.poke(q,3);try control(&f,0);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_floppy_stage_active"));}

test "dirty discard saved clean pairs and old generation acknowledgements fail closed"{var f=try init();defer f.deinit();_ = try mount(&f,0,0,0x53);try io(&f,3,0,1,1,0);var q=try rq(&f,1,0);try control(&f,3);q=try rq(&f,5,0);f.poke(q+3,0xa5);try snapshot(&f,0);const stale=rd(&f,q+19);try io(&f,3,0,1,1,0);try control(&f,4);try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_dirty"));try snapshot(&f,0);d(&f,q+23,0xabcdef01);try control(&f,0);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_disk_dirty"));try std.testing.expectEqual(@as(u32,stale+1),rd(&f,try f.symbol("dos64_disk_clean_content")));try std.testing.expectEqual(@as(u32,0xabcdef01),rd(&f,try f.symbol("dos64_disk_binding")));q=try rq(&f,4,0);try snapshot(&f,0);try control(&f,0);try io(&f,2,0,1,1,0x80);try std.testing.expectEqual(@as(u32,2),rd(&f,try f.symbol("dos64_disk_mount_generation")));}

test "guard busy capacity and generation exhaustion prevent unsafe state reuse"{var f=try init();defer f.deinit();var q=try rq(&f,1,0);try put(&f,"dos64_cold_open",0);try control(&f,7);try put(&f,"dos64_native_diag",5);f.poke(q+4,3);try control(&f,1);f.poke(q+4,4);try control(&f,0);f.poke(q,1);try control(&f,2);f.poke(q,3);try control(&f,0);d(&f,try f.symbol("dos64_floppy_token"),0xffffffff);q=try rq(&f,1,0);try control(&f,8);d(&f,try f.symbol("dos64_floppy_token"),1);_ = try mount(&f,0,0,0x71);d(&f,try f.symbol("dos64_disk_content_generation"),0xffffffff);try io(&f,3,0,1,2,0);try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_exhausted"));q=try rq(&f,5,0);try snapshot(&f,0);f.poke(q+3,0xa5);try control(&f,8);d(&f,try f.symbol("dos64_disk_mount_generation"),0xffffffff);q=try rq(&f,4,0);try snapshot(&f,0);f.poke(q+2,2);try control(&f,8);}

test "failed partial write is conservatively dirty and preserves other drive"{var f=try init();defer f.deinit();_ = try mount(&f,0,0,0x21);const b=try mount(&f,1,0,0x91);for(0..512)|i|_ = try guest(&f,0x2000+@as(u16,@intCast(i)),0x76);c.dos64_reu_fail_after(f.machine,0,16);try io(&f,3,0,1,1,0x20);try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_dirty"));try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_content_generation")));for(512..1024)|i|try std.testing.expectEqual(@as(u8,0x91^@as(u8,@truncate(i*13))),c.dos64_reu_peek(f.machine,b+@as(u32,@intCast(i))));}


test "native flags and descriptors survive alternating A B requests for every host P" {
    var f=try init();defer f.deinit();_ = try mount(&f,0,0,0x13);_ = try mount(&f,1,0,0x37);
    const ap=try f.symbol("dos64_disk_reu_base");const bp=try f.symbol("dos64_disk_b_descriptor");var a:[10]u8=undefined;var b:[10]u8=undefined;for(0..10)|i|{a[i]=f.peek(ap+@as(u16,@intCast(i)));b[i]=f.peek(bp+@as(u16,@intCast(i)));}
    for(0..256)|p|{f.initial_status=@intCast(p);try io(&f,4,@intCast(p%2),1,128,0);try std.testing.expectEqual(@as(u8,@intCast(p))&0xce,f.last_regs.?.p&0xce);for(0..10)|i|{try std.testing.expectEqual(a[i],f.peek(ap+@as(u16,@intCast(i))));try std.testing.expectEqual(b[i],f.peek(bp+@as(u16,@intCast(i))));}}
}

test "stale stage after guest mutation cannot publish even with explicit discard" {
    var f=try init();defer f.deinit();_ = try mount(&f,0,0,0x13);const base=try prepare(&f,0,2);bpb(&f,base);try io(&f,3,0,1,1,0);const q=try f.symbol("dos64_floppy_request");f.poke(q,2);f.poke(q+3,0xa5);try control(&f,4);try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_mount_generation")));f.poke(q,3);try control(&f,0);_ = try prepare(&f,0,2);bpb(&f,rd(&f,q+5)&0xffffff);try commit(&f);try std.testing.expectEqual(@as(u32,2),rd(&f,try f.symbol("dos64_disk_mount_generation")));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_disk_dirty"));
}


test "mount capability echoed length base and latched readonly policy are enforced" {
    var f=try init();defer f.deinit();_ = try mount(&f,0,0,0x19);const base=try prepare(&f,0,1);bpb(&f,base);const q=try f.symbol("dos64_floppy_request");f.poke(q,2);f.poke(q+3,0xa5);
    f.poke(q+8,1);try control(&f,1);f.poke(q+8,0);f.poke(q+7,0x38);try control(&f,4);f.poke(q+7,@truncate(base>>16));f.poke(q+2,0);try commit(&f);try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_readonly"));try io(&f,3,0,1,1,3);
}

test "all DISK startup header bytes fail before DMA and replacement errors preserve both media" {
    for(0..16)|i|{var f=try F.init();defer f.deinit();c.dos64_enable_reu(f.machine);_ = try f.call("dos64_overlay_init",100000);try put(&f,"dos64_overlay_reu_mib",4);const at:u16=0xb800+@as(u16,@intCast(i));f.poke(at,f.peek(at)^0xff);const r=try f.call("dos64_overlay_bootstrap",1000000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_overlay_ready"));}
    var f=try init();defer f.deinit();const a=try mount(&f,0,0,0x61);const b=try mount(&f,1,0,0x36);try put(&f,"dos64_overlay_current",0);c.dos64_reu_poke(f.machine,0x343805,6);try io(&f,3,1,1,1,0x20);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_disk_dirty"));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_disk_dirty")+1));try std.testing.expectEqual(@as(u8,0x61),c.dos64_reu_peek(f.machine,a+512));try std.testing.expectEqual(@as(u8,0x36),c.dos64_reu_peek(f.machine,b+512));
}

test "independent reviewer B multi-sector writes preserve complete readonly A and bind B clean generations" {
    var f=try init(); defer f.deinit();
    const a=try mount(&f,0,1,0x39); const b=try mount(&f,1,0,0xa6);
    const old=try std.testing.allocator.alloc(u8,360*1024); defer std.testing.allocator.free(old);
    try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,a,old.ptr,old.len));
    for(0..9*512)|i|_ = try guest(&f,0x2000+@as(u16,@intCast(i)),@truncate(i*31+(i>>7)));
    try io(&f,3,1,9,8,0);
    for(0..9*512)|i|try std.testing.expectEqual(@as(u8,@truncate(i*31+(i>>7))),c.dos64_reu_peek(f.machine,b+8*512+@as(u32,@intCast(i))));
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,a,old.ptr,old.len));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_disk_dirty"));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_disk_dirty")+1));
    try std.testing.expectEqual(@as(u32,0),rd(&f,try f.symbol("dos64_disk_content_generation")));
    try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_content_generation")+4));
    const q=try rq(&f,5,1);f.poke(q+3,0xa5);try snapshot(&f,0);try control(&f,4);
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_disk_dirty")+1));
    try snapshot(&f,1);d(&f,q+23,0x76543210);try control(&f,0);
    try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_clean_content")+4));
    try std.testing.expectEqual(@as(u32,0x76543210),rd(&f,try f.symbol("dos64_disk_binding")+4));
    try std.testing.expectEqual(@as(u32,0x12345600),rd(&f,try f.symbol("dos64_disk_binding")));
    try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_disk_readonly"));
    try io(&f,2,1,9,8,0);
    for(0..9*512)|i|try std.testing.expectEqual(@as(u8,@truncate(i*31+(i>>7))),try guest(&f,0x2000+@as(u16,@intCast(i)),null));
    try std.testing.expectEqual(@as(u8,@truncate(a>>16)),f.peek(try f.symbol("dos64_disk_reu_base")+2));
    try std.testing.expectEqual(@as(u8,@truncate(b>>16)),f.peek(try f.symbol("dos64_disk_b_descriptor")+2));
}

test "independent reviewer failed B export preserves full A and only dirties B" {
    var f=try init();defer f.deinit();const a=try mount(&f,0,1,0xb4);const b=try mount(&f,1,0,0x47);
    const old=try std.testing.allocator.alloc(u8,360*1024);defer std.testing.allocator.free(old);
    try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,a,old.ptr,old.len));
    for(0..512)|i|_ = try guest(&f,0x2000+@as(u16,@intCast(i)),0x96);
    c.dos64_reu_fail_after(f.machine,0,16);try io(&f,3,1,1,128,0x20);
    try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,a,old.ptr,old.len));
    try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_disk_dirty"));
    try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_disk_dirty")+1));
    try std.testing.expectEqual(@as(u32,0),rd(&f,try f.symbol("dos64_disk_content_generation")));
    try std.testing.expectEqual(@as(u32,1),rd(&f,try f.symbol("dos64_disk_content_generation")+4));
    try std.testing.expectEqual(@as(u8,@truncate(a>>16)),f.peek(try f.symbol("dos64_disk_reu_base")+2));
    try std.testing.expectEqual(@as(u8,@truncate(b>>16)),f.peek(try f.symbol("dos64_disk_b_descriptor")+2));
}

test "independent reviewer native control preserves all host P and crosses token byte carry" {
    var f=try init();defer f.deinit();d(&f,try f.symbol("dos64_floppy_token"),0xfe);
    for(0..256)|p|{
        f.initial_status=@intCast(p);const q=try rq(&f,1,@intCast(p%2));try control(&f,0);
        try std.testing.expectEqual(@as(u32,0xff)+@as(u32,@intCast(p)),rd(&f,q+11));
        const saved=f.peek(q+1);f.poke(q,3);f.poke(q+1,saved^1);try control(&f,4);
        try std.testing.expectEqual(@as(u8,0xa5),try get(&f,"dos64_floppy_stage_active"));
        f.poke(q+1,saved);try control(&f,0);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_floppy_stage_active"));
    }
}

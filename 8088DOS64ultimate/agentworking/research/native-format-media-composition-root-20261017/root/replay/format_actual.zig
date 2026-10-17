const std=@import("std");
const c=@cImport({@cInclude("peddle_bridge.h");});
const code=@embedFile("runtime/work/build/dos64.prg");
const labels=@embedFile("runtime/work/build/dos64.labels");
fn sym(name:[]const u8)u16{
 var lines=std.mem.splitScalar(u8,labels,'\n');while(lines.next())|line|{var t=std.mem.tokenizeAny(u8,line," \r\t");if(!std.mem.eql(u8,t.next() orelse continue,"al"))continue;const address=t.next() orelse continue;const n=t.next() orelse continue;if(std.mem.eql(u8,n[1..],name))return std.fmt.parseInt(u16,address,16) catch unreachable;}@panic("missing linked symbol");
}
const F=struct{
 m:*c.Dos64Machine,
 fn put(f:F,n:[]const u8,b:[]const u8)void{c.dos64_load(f.m,sym(n),b.ptr,b.len);}
 fn call(f:F,n:[]const u8)!c.Dos64RunResult{
 c.dos64_poke(f.m,0x1ff,2);c.dos64_poke(f.m,0x1fe,0xff);c.dos64_set_regs(f.m,.{.pc=sym(n),.sp=0xfd,.a=0x71,.x=0x82,.y=0x93,.p=0x2c,.cycles=0,.instructions=0});const r=c.dos64_run(f.m,0x300,3000000);try std.testing.expectEqual(@as(c_uint,0),r.status);try std.testing.expectEqual(@as(u8,0xff),r.regs.sp);return r;}
 fn init()!F{const f=F{.m=c.dos64_create() orelse return error.Create};c.dos64_load(f.m,0x801,code[2..].ptr,code.len-2);c.dos64_poke(f.m,0,0x2f);c.dos64_poke(f.m,1,0x35);c.dos64_enable_reu(f.m);_=try f.call("dos64_overlay_init");f.put("dos64_overlay_reu_mib",&.{4});try std.testing.expectEqual(@as(u8,0),(try f.call("dos64_overlay_bootstrap")).regs.p&1);_=try f.call("dos64_cpu_reset");f.put("dos64_cache_limit",&.{32});_=try f.call("dos64_cache_init");_=try f.call("dos64_disk_init");f.put("dos64_disk_loaded",&.{1});f.put("dos64_disk_b_descriptor",&.{0,0,0x18,0xd0,2,40,0,2,9,1});return f;}
 fn request(f:F)void{var guest=[_]u8{0}**28;guest[0]=9;guest[1]=5;guest[4]=1;guest[7]=0x20;f.put("dos64_guest",&guest);for(0..9)|i|{const a:u32=0x2000+@as(u32,@intCast(i))*4;for([_]u8{0,0,@intCast(i+1),2},0..)|v,j|c.dos64_reu_poke(f.m,a+@as(u32,@intCast(j)),v);}c.dos64_reu_poke(f.m,0x78,0);c.dos64_reu_poke(f.m,0x79,0x30);c.dos64_reu_poke(f.m,0x7a,0);c.dos64_reu_poke(f.m,0x7b,0);c.dos64_reu_poke(f.m,0x3008,0xa7);}
};
test "actual FORMAT1 runtime has native bounded track writes and returns original native flags"{
 const f=try F.init();defer c.dos64_destroy(f.m);f.request();const r=try f.call("dos64_disk_transfer");try std.testing.expectEqual(@as(u8,0),r.regs.p&1);try std.testing.expectEqual(@as(u8,0x0c),r.regs.p&0x0c);for(0..4608)|i|try std.testing.expectEqual(@as(u8,0xa7),c.dos64_reu_peek(f.m,0x180000+@as(u32,@intCast(i))));try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.m,0x181200));try std.testing.expectEqual(@as(u8,1),c.dos64_peek(f.m,sym("dos64_disk_dirty")+1));}
test "actual FORMAT1 malformed sector ID and immutable nested byte corruption refuse"{
 const f=try F.init();defer c.dos64_destroy(f.m);f.request();c.dos64_reu_poke(f.m,0x2003,1);var r=try f.call("dos64_disk_transfer");try std.testing.expectEqual(@as(u8,1),r.regs.p&1);try std.testing.expectEqual(@as(u8,4),c.dos64_peek(f.m,sym("dos64_guest")+1));f.request();c.dos64_reu_poke(f.m,0x3427ff,1);r=try f.call("dos64_disk_transfer");try std.testing.expectEqual(@as(u8,1),r.regs.p&1);try std.testing.expectEqual(@as(u8,9),c.dos64_peek(f.m,sym("dos64_overlay_error")));try std.testing.expectEqual(@as(u8,0),c.dos64_peek(f.m,sym("dos64_overlay_busy")));}

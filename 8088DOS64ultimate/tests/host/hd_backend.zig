const std=@import("std");
const host=@import("machine.zig");
const F=host.Fixture;
const m=@cImport({@cInclude("uci_model.h");});
const a=std.testing.allocator;
fn get(f:*F,n:[]const u8)!u8{return f.peek(try f.symbol(n));}
fn put(f:*F,n:[]const u8,v:u8)!void{f.poke(try f.symbol(n),v);}
fn word(f:*F,n:[]const u8,v:u16)!void{const x=try f.symbol(n);f.poke(x,@truncate(v));f.poke(x+1,@truncate(v>>8));}
fn load32(f:*F,n:[]const u8)!u32{const x=try f.symbol(n);var v:u32=0;for(0..4)|i|v|=@as(u32,f.peek(x+@as(u16,@intCast(i))))<<@as(u5,@intCast(i*8));return v;}
var max_cycles:u64=0;
fn call(f:*F,n:[]const u8,carry:u8)!void{
 const before=host.c.dos64_get_regs(f.machine).cycles;const r=try f.call(n,100_000);max_cycles=@max(max_cycles,r.cycles-before);
 try std.testing.expectEqual(carry,r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);
 try std.testing.expectEqual(@as(u8,0),try get(f,"dos64_overlay_busy"));
}
fn bytes(f:*F,n:[]const u8,delta:u16,b:[]const u8)!void{const x=(try f.symbol(n))+delta;for(b,0..)|v,i|f.poke(x+@as(u16,@intCast(i)),v);}
fn equalBytes(f:*F,n:[]const u8,b:[]const u8)!void{const x=try f.symbol(n);for(b,0..)|v,i|try std.testing.expectEqual(v,f.peek(x+@as(u16,@intCast(i))));}
fn command(f:*F,cmd:[]const u8,d:[]const u8,s:[]const u8)!void{
 m.dos64_uci_model_enable(f.machine,0xdf1c,1,0xc9);m.dos64_uci_model_block(f.machine,d.ptr,d.len,s.ptr,s.len);
 try call(f,"dos64_overlay_files_start",0);var seen=false;
 for(0..1000)|_|{
  if(try get(f,"dos64_uci_state")==3 and !seen){for(cmd,0..)|v,i|try std.testing.expectEqual(v,m.dos64_uci_model_command(f.machine,@intCast(i)));seen=true;}
  if(try get(f,"dos64_files_state")!=1)break;
  try word(f,"dos64_files_now",f.word(try f.symbol("dos64_files_now"))+%1);try call(f,"dos64_overlay_files_poll",0);
 }
 try std.testing.expect(seen);try std.testing.expect(try get(f,"dos64_files_state")!=1);
}
fn setup(profile:u8,slots:u8)!F{
 var f=try F.init();errdefer f.deinit();host.c.dos64_enable_reu(f.machine);
 _=try f.call("dos64_overlay_init",10_000);try put(&f,"dos64_overlay_reu_mib",4);const boot=try f.call("dos64_overlay_bootstrap",300_000);try std.testing.expectEqual(@as(u8,0),boot.p&1);
 m.dos64_uci_model_enable(f.machine,0xdf1c,1,0xc9);try call(&f,"dos64_uci_init",0);try word(&f,"dos64_uci_timeout",4000);try call(&f,"dos64_overlay_files_init",0);
 try put(&f,"dos64_files_op",2);try put(&f,"dos64_files_mode",3);try put(&f,"dos64_files_path_len",7);try bytes(&f,"dos64_uci_command",3,"HD.IMG\x00");
 try command(&f,&.{1,2,3,'H','D','.','I','M','G',0},"","00,OK");
 try put(&f,"hd_profile",profile);try put(&f,"hd_slots",slots);try call(&f,"dos64_overlay_hd_init",0);return f;
}
const Fault=enum{none,short_read,seek_error,write_error,partial_write,corrupt_write};
const Disk=struct{
 data:[]u8,pos:usize=0,seeks:usize=0,reads:usize=0,writes:usize=0,fault:Fault=.none,fail_after:usize=0,
 fn init(length:usize)!Disk{const b=try a.alloc(u8,length);for(b,0..)|*v,i|v.*=@truncate((i*37)^(i>>8)^(i>>17));return .{.data=b};}
 fn deinit(self:*Disk)void{a.free(self.data);}
 fn request(self:*Disk,f:*F)!void{
  const op=try get(f,"dos64_files_op");
  if(op==6){
   const p=try load32(f,"dos64_files_offset");try std.testing.expect(p<=self.data.len);
   var cmd:[6]u8=.{1,6,0,0,0,0};std.mem.writeInt(u32,cmd[2..6],p,.little);self.seeks+=1;
   if(self.fault==.seek_error){try command(f,&cmd,"","66,SEEK ERROR");return;}
   self.pos=p;try command(f,&cmd,"","00,OK");
  }else if(op==4){
   const count=f.word(try f.symbol("dos64_files_count"));try std.testing.expect(count==512 or count==2);try std.testing.expect(self.pos<=self.data.len);self.reads+=1;
   var n:usize=@min(count,self.data.len-self.pos);
   if(count==512 and self.fault==.short_read and self.reads>self.fail_after)n=@min(n,511);
   try command(f,&.{1,4,@truncate(count),@truncate(count>>8)},self.data[self.pos..][0..n],"");self.pos+=n;
  }else if(op==5){
   try std.testing.expect(self.pos+512<=self.data.len);self.writes+=1;var cmd:[516]u8=undefined;cmd[0..4].*=.{1,5,0,2};const x=try f.symbol("dos64_uci_command");
   for(cmd[4..],4..)|*v,i|v.*=f.peek(x+@as(u16,@intCast(i)));
   if(self.fault==.write_error){try command(f,&cmd,"","75,WRITE ERROR");return;}
   const n:usize=if(self.fault==.partial_write)127 else 512;@memcpy(self.data[self.pos..][0..n],cmd[4..][0..n]);
   if(self.fault==.corrupt_write)self.data[self.pos+217]^=0x80;
   self.pos+=n;try command(f,&cmd,"","00,OK");
  }else return error.UnexpectedFileOperation;
 }
 fn drain(self:*Disk,f:*F)!void{
  var steps:usize=0;while(try get(f,"hd_state")==1):(steps+=1){if(steps>130)return error.HdStepBudget;try std.testing.expectEqual(@as(u8,1),try get(f,"hd_request"));try self.request(f);try call(f,"dos64_overlay_hd_advance",0);}
 }
};
fn start(f:*F,op:u8,lba:u16)!void{try put(f,"hd_op",op);try word(f,"hd_lba",lba);try put(f,"hd_count",1);try call(f,"dos64_overlay_hd_prepare",0);}
fn read(d:*Disk,f:*F,lba:u16)!void{try start(f,0,lba);try d.drain(f);try std.testing.expectEqual(@as(u8,2),try get(f,"hd_state"));try equalBytes(f,"dos64_uci_data",d.data[@as(usize,lba)*512..][0..512]);}
fn pattern()[512]u8{var b:[512]u8=undefined;for(&b,0..)|*v,i|v.*=@truncate(i*13+0x5a);return b;}
fn write(d:*Disk,f:*F,lba:u16,b:[]const u8)!void{try bytes(f,"dos64_uci_command",4,b);try start(f,1,lba);try d.drain(f);}

test "HD two-slot reads force eviction across extent and complete2MiB boundaries"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();
 for([_]u16{0,1,63,64,127,128,0,4095,4032,4094})|lba|try read(&d,&f,lba);
 try std.testing.expectEqual(@as(usize,6),d.seeks);try std.testing.expectEqual(@as(usize,5*64+1),d.reads);
 try std.testing.expectEqual(@as(u8,0),host.c.dos64_reu_peek(f.machine,0x1fffff));try std.testing.expectEqual(@as(u8,0),host.c.dos64_reu_peek(f.machine,0x210000));
}
test "HD20MiB keeps32bit offsets across16MiB and finalsector with all32slots"{
 var f=try setup(1,32);defer f.deinit();var d=try Disk.init(20*1024*1024);defer d.deinit();
 for([_]u16{32767,32768,32769,40959,0})|lba|try read(&d,&f,lba);
 try std.testing.expectEqual(@as(usize,5),d.seeks);try std.testing.expectEqual(@as(u8,0),host.c.dos64_reu_peek(f.machine,0x300000));std.debug.print("HD maximum bounded call CPUcycles={d}\n",.{max_cycles});
}
test "HD failed partial extent never publishes valid tag and clean retry reloads"{
 for([_]usize{0,1,31,63})|after|{
  var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();d.fault=.short_read;d.fail_after=after+1;try start(&f,0,130);try d.drain(&f);
  try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_error"));
  const v=try f.symbol("hd_valid");for(0..32)|i|try std.testing.expectEqual(@as(u8,0),f.peek(v+@as(u16,@intCast(i))));
  d.fault=.none;try read(&d,&f,130);try std.testing.expectEqual(after+2+64,d.reads);
 }
}
test "HD write-through readback retains authority on unknown short or corrupted write"{
 for([_]Fault{.none,.partial_write,.corrupt_write,.write_error,.short_read,.seek_error})|fault|{
  var f=try setup(1,2);defer f.deinit();var d=try Disk.init(20*1024*1024);defer d.deinit();try read(&d,&f,32768);const b=pattern();d.fault=fault;try write(&d,&f,32768,&b);
  try std.testing.expectEqual(@as(u8,0),try get(&f,"hd_valid"));
  if(fault==.none){try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,0),try get(&f,"hd_uncertain"));try std.testing.expectEqual(@as(u8,1),try get(&f,"hd_agreement"));try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_files_uncertain"));}
  else{
   try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,1),try get(&f,"hd_uncertain"));
   for(b,0..)|v,i|try std.testing.expectEqual(v,host.c.dos64_reu_peek(f.machine,0x350000+@as(u32,@intCast(i))));
   try call(&f,"dos64_overlay_hd_init",1);try call(&f,"dos64_overlay_hd_prepare",1);try word(&f,"hd_lba",0);try put(&f,"hd_op",0);d.fault=.none;try call(&f,"dos64_overlay_hd_retry",0);try d.drain(&f);
   try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,0),try get(&f,"hd_uncertain"));
  }
  try std.testing.expectEqualSlices(u8,&b,d.data[0x1000000..][0..512]);d.fault=.none;try read(&d,&f,32768);
 }
}
test "HD rejects invalid spans profiles geometry bounds active and leased reentry"{
 var f=try setup(0,2);defer f.deinit();for([_]u8{0,2,64,255})|n|{try put(&f,"hd_count",n);try call(&f,"dos64_overlay_hd_prepare",1);}try put(&f,"hd_count",1);
 for([_]u16{4096,32768,65535})|lba|{try word(&f,"hd_lba",lba);try call(&f,"dos64_overlay_hd_prepare",1);}
 try put(&f,"hd_profile",1);try word(&f,"hd_lba",40960);try call(&f,"dos64_overlay_hd_prepare",1);try put(&f,"hd_profile",2);try call(&f,"dos64_overlay_hd_prepare",1);try call(&f,"dos64_overlay_hd_init",1);
 try put(&f,"hd_profile",0);try word(&f,"hd_lba",0);for([_]u8{0,33,255})|n|{try put(&f,"hd_slots",n);try call(&f,"dos64_overlay_hd_init",1);try call(&f,"dos64_overlay_hd_prepare",1);}
 try put(&f,"hd_slots",2);try start(&f,0,0);try call(&f,"dos64_overlay_hd_prepare",1);try call(&f,"dos64_overlay_hd_init",1);
 const before=try get(&f,"hd_state");try put(&f,"dos64_overlay_busy",1);const r=try f.call("dos64_overlay_files_init",1000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_overlay_busy"));try std.testing.expectEqual(before,try get(&f,"hd_state"));
}
test "HD partial REU DMA never publishes failed read or write and recovery remains retryable"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();
 try read(&d,&f,0);
 host.c.dos64_reu_fail_after(f.machine,0,127);try start(&f,0,1);
 try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,4),try get(&f,"hd_error"));
 try read(&d,&f,1);
 const b=pattern();const writes=d.writes;
 host.c.dos64_reu_fail_after(f.machine,0,127);try bytes(&f,"dos64_uci_command",4,&b);try start(&f,1,1);
 try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,0),try get(&f,"hd_uncertain"));try std.testing.expectEqual(writes,d.writes);
 try write(&d,&f,1,&b);try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_state"));
 // Fail the first sector cache store after both header and payload replacement DMAs.
 try start(&f,0,128);try d.request(&f);try call(&f,"dos64_overlay_hd_advance",0);try d.request(&f);
 host.c.dos64_reu_fail_after(f.machine,2,127);try call(&f,"dos64_overlay_hd_advance",0);
 try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,4),try get(&f,"hd_error"));
 try read(&d,&f,128);
}
test "HD all32extents cover exactly1MiB preserving every other4MiB REU byte"{
 var f=try setup(1,32);defer f.deinit();var d=try Disk.init(20*1024*1024);defer d.deinit();
 const expected=try a.alloc(u8,4*1024*1024);defer a.free(expected);
 for(expected,0..)|*v,i|{v.*=@truncate((i*29)^(i>>12));host.c.dos64_reu_poke(f.machine,@intCast(i),v.*);}
 const assets=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"build/dos64-tests-overlay-startup.bin",a,.limited(14337));defer a.free(assets);@memcpy(expected[0x340000..][0..assets.len],assets);for(assets,0..)|v,i|host.c.dos64_reu_poke(f.machine,0x340000+@as(u32,@intCast(i)),v);
 // Invalidate loaded window so no stale code survives our independently seeded assets.
 try put(&f,"dos64_overlay_current",0);
 for(0..32)|i|{try read(&d,&f,@intCast((512+i)*64+63));@memcpy(expected[0x200000+i*32768..][0..32768],d.data[(512+i)*32768..][0..32768]);}
 try std.testing.expectEqual(@as(u32,0xffffffff),host.c.dos64_reu_compare(f.machine,0,expected.ptr,expected.len));
 try read(&d,&f,0);@memcpy(expected[0x200000..][0..32768],d.data[0..32768]);
 try std.testing.expectEqual(@as(u32,0xffffffff),host.c.dos64_reu_compare(f.machine,0,expected.ptr,expected.len));
 try std.testing.expectEqual(@as(usize,34),d.seeks);
}
test "HD accepted genuine DOS raw fixtures retain complete16MiB crossing bytes"{
 if(!@import("hd_options").long_hd)return error.SkipZigTest;
 for([_]u8{0,1})|profile|{
  const b=try @import("hd_fixtures.zig").image(profile);const length=b.len;
  var d=Disk{.data=b};defer d.deinit();
  var f=try setup(profile,2);defer f.deinit();
  try read(&d,&f,0);try read(&d,&f,16);if(profile==1){try read(&d,&f,32767);try read(&d,&f,32768);try read(&d,&f,32769);}
  try read(&d,&f,@intCast(length/512-1));
 }
 std.debug.print("HD final maximum bounded call CPUcycles={d}\n",.{max_cycles});
}
test "HD initial write preserves desired bytes across mount probe and exact image lengths reject"{
 const b=pattern();
 for([_]usize{2*1024*1024-1,2*1024*1024,2*1024*1024+1})|length|{
  var f=try setup(0,2);defer f.deinit();var d=try Disk.init(length);defer d.deinit();
  try write(&d,&f,63,&b);
  if(length==2*1024*1024){try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_state"));try std.testing.expectEqualSlices(u8,&b,d.data[63*512..][0..512]);try read(&d,&f,63);}
  else{try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,6),try get(&f,"hd_error"));try std.testing.expectEqual(@as(usize,0),d.writes);try std.testing.expectEqual(@as(u8,1),try get(&f,"hd_uncertain"));for(b,0..)|v,i|try std.testing.expectEqual(v,host.c.dos64_reu_peek(f.machine,0x350000+@as(u32,@intCast(i))));try call(&f,"dos64_overlay_hd_retry",0);try d.drain(&f);try std.testing.expectEqual(@as(u8,6),try get(&f,"hd_error"));}
 }
}
test "HD stale FILE completion cannot publish cached data for a new request"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();try read(&d,&f,0);
 try start(&f,0,128);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_files_state"));try call(&f,"dos64_overlay_hd_advance",0);
 try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_error"));
 try read(&d,&f,128);
 // A new HD operation also refuses a FILE transfer already in progress.
 try put(&f,"dos64_files_state",1);try call(&f,"dos64_overlay_hd_prepare",1);try call(&f,"dos64_overlay_hd_init",1);
}
test "HD native CHS helper checks every legal sector both exact geometries and encoded cylinder highs"{
 for([_]u8{0,1})|profile|{
  var f=try setup(profile,2);defer f.deinit();try put(&f,"hd_count",1);
  const cylinders:usize=if(profile==0)128 else 640;const heads:usize=if(profile==0)2 else 4;
  for(0..cylinders)|cy|{for(0..heads)|he|{for(1..17)|se|{
   try put(&f,"hd_ch",@truncate(cy));try put(&f,"hd_cl",@as(u8,@intCast(se))|@as(u8,@intCast((cy>>8)<<6)));try put(&f,"hd_dh",@intCast(he));
   try call(&f,"dos64_overlay_hd_chs_to_lba",0);try std.testing.expectEqual(@as(u16,@intCast((cy*heads+he)*16+se-1)),f.word(try f.symbol("hd_lba")));
  }}}
  for([_]struct{cy:u16,he:u8,se:u8}{.{.cy=@intCast(cylinders),.he=0,.se=1},.{.cy=0,.he=@intCast(heads),.se=1},.{.cy=0,.he=0,.se=0},.{.cy=0,.he=0,.se=17},.{.cy=1023,.he=3,.se=63}})|v|{
   try put(&f,"hd_ch",@truncate(v.cy));try put(&f,"hd_cl",v.se|@as(u8,@intCast((v.cy>>8)<<6)));try put(&f,"hd_dh",v.he);try call(&f,"dos64_overlay_hd_chs_to_lba",1);
  }
 }
}
test "HD verification timeout retains sector authority until FILE close reopen and replay"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();try read(&d,&f,0);const b=pattern();
 try bytes(&f,"dos64_uci_command",4,&b);try start(&f,1,4095);
 // Write seek, WRITE, verify seek, then stall the verifying READ in UCI.
 for(0..3)|_|{try d.request(&f);try call(&f,"dos64_overlay_hd_advance",0);}
 try std.testing.expectEqual(@as(u8,4),try get(&f,"dos64_files_op"));
 m.dos64_uci_model_enable(f.machine,0xdf1c,10000,0xc9);m.dos64_uci_model_block(f.machine,"".ptr,0,"".ptr,0);
 try word(&f,"dos64_uci_timeout",10);try word(&f,"dos64_files_now",0);try call(&f,"dos64_overlay_files_start",0);
 try word(&f,"dos64_files_now",20);try call(&f,"dos64_overlay_files_poll",0);
 // Allow asynchronous ABORT to settle, preserving the timeout failure.
 m.dos64_uci_model_enable(f.machine,0xdf1c,1,0xc9);try word(&f,"dos64_files_now",21);try call(&f,"dos64_overlay_files_poll",0);
 try std.testing.expectEqual(@as(u8,3),try get(&f,"dos64_files_state"));try std.testing.expectEqual(@as(u8,2),try get(&f,"dos64_files_handle"));
 try call(&f,"dos64_overlay_hd_advance",0);try std.testing.expectEqual(@as(u8,3),try get(&f,"hd_state"));try std.testing.expectEqual(@as(u8,1),try get(&f,"hd_uncertain"));
 for(b,0..)|v,i|try std.testing.expectEqual(v,host.c.dos64_reu_peek(f.machine,0x350000+@as(u32,@intCast(i))));
 try put(&f,"dos64_files_op",3);try command(&f,&.{1,3},"","00,OK");try put(&f,"dos64_files_op",2);try put(&f,"dos64_files_mode",3);try put(&f,"dos64_files_path_len",7);try bytes(&f,"dos64_uci_command",3,"HD.IMG\x00");try command(&f,&.{1,2,3,'H','D','.','I','M','G',0},"","00,OK");
 try word(&f,"dos64_uci_timeout",4000);try call(&f,"dos64_overlay_hd_retry",0);try d.drain(&f);try std.testing.expectEqual(@as(u8,2),try get(&f,"hd_state"));try std.testing.expectEqualSlices(u8,&b,d.data[d.data.len-512..]);
}
test "HD readonly and closed handles reject writes before staging or backing mutation"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();
 try put(&f,"hd_readonly",1);try call(&f,"dos64_overlay_hd_init",0);try read(&d,&f,0);
 try put(&f,"hd_op",1);try word(&f,"hd_lba",0);try call(&f,"dos64_overlay_hd_prepare",1);try std.testing.expectEqual(@as(u8,0),try get(&f,"hd_uncertain"));try std.testing.expectEqual(@as(usize,0),d.writes);
 try put(&f,"dos64_files_op",3);try command(&f,&.{1,3},"","00,OK");try call(&f,"dos64_overlay_hd_init",1);try call(&f,"dos64_overlay_hd_prepare",1);
}
test "HD explicit close reopen init changes media identity and invalidates all old tags"{
 var f=try setup(0,2);defer f.deinit();var d=try Disk.init(2*1024*1024);defer d.deinit();try read(&d,&f,128);
 try put(&f,"dos64_files_op",3);try command(&f,&.{1,3},"","00,OK");try put(&f,"dos64_files_op",2);try put(&f,"dos64_files_mode",3);try put(&f,"dos64_files_path_len",7);try bytes(&f,"dos64_uci_command",3,"HD.IMG\x00");try command(&f,&.{1,2,3,'H','D','.','I','M','G',0},"","00,OK");
 for(d.data)|*v|v.*^=0xff;try call(&f,"dos64_overlay_hd_init",0);try read(&d,&f,128);try std.testing.expectEqual(@as(usize,4),d.seeks);
}
test "HD resident wrapper and native helper preserve all caller status combinations"{
 var f=try setup(1,2);defer f.deinit();try put(&f,"hd_count",1);try put(&f,"hd_ch",0);try put(&f,"hd_cl",0x81);try put(&f,"hd_dh",0);
 for(0..256)|status|{f.initial_status=@intCast(status);try call(&f,"dos64_overlay_hd_chs_to_lba",0);try std.testing.expectEqual(@as(u16,32768),f.word(try f.symbol("hd_lba")));}
 std.debug.print("HD all-tests maximum bounded native call CPUcycles={d}\n",.{max_cycles});
}

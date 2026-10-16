const std=@import("std");
const c=@cImport({@cInclude("peddle_bridge.h");@cInclude("file_model.h");});
const a=std.testing.allocator;
const SIZE=368640;
const BASE=0x100000;
var maximum_poll:u64=0;
var scenarios:usize=0;
const F=struct {
 m:*c.Dos64Machine,
 labels:[]u8,
 prg_path:[]const u8,
 now:u16=0,
 fn init(existing:bool) !F {return initPaths(existing,"build/dos64-floppy-export.prg","build/dos64-floppy-export.labels");}
 fn initPaths(existing:bool,prg_path:[]const u8,labels_path:[]const u8) !F {
  const prg=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,prg_path,a,.limited(65538));defer a.free(prg);
  const m=c.dos64_create() orelse return error.Machine;errdefer c.dos64_destroy(m);
  c.dos64_load(m,0x801,prg[2..].ptr,prg.len-2);_=c.dos64_enable_reu_sized(m,4096);
  c.dos64_uci_model_enable(m,0xdf1c,3,0xc9);c.export_model_enable(m,@intFromBool(existing));
  var f:F=.{.m=m,.prg_path=prg_path,.labels=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,labels_path,a,.limited(200000))};
  _=try f.call("dos64_uci_init");_=try f.call("dos64_files_init");_=try f.call("dos64_export_init");
  try f.word("dos64_uci_timeout",1000);try f.word("dos64_uci_recovery_timeout",100);
  try f.byte("dos64_export_owned",0xa5);try f.byte("dos64_export_paused",0xa5);try f.byte("dos64_export_bank",0x10);
  const path="/usb1/DOS64_TEST/export-owned/WORK.IMG\x00";
  try f.byte("dos64_export_path_len",path.len);const dest=try f.sym("dos64_export_path");
  for(path,0..) |v,i| c.dos64_poke(m,dest+@as(u16,@intCast(i)),v);
  for(0..SIZE) |i| c.dos64_reu_poke(m,BASE+@as(u32,@intCast(i)),pattern(i));
  c.dos64_reu_poke(m,BASE-1,0x67);c.dos64_reu_poke(m,BASE+SIZE,0x79);
  c.dos64_poke(m,0x7fff,0xa7);c.dos64_poke(m,0x8200,0xb8);
  scenarios+=1;return f;
 }
 fn deinit(f:*F) void {a.free(f.labels);c.dos64_destroy(f.m);}
 fn sym(f:*F,name:[]const u8) !u16 {
  var lines=std.mem.splitScalar(u8,f.labels,'\n');while(lines.next()) |line| {
   var fields=std.mem.tokenizeAny(u8,line," \t\r");if(!std.mem.eql(u8,fields.next() orelse continue,"al"))continue;
   const address=fields.next() orelse continue;const symbol=fields.next() orelse continue;
   if(std.mem.eql(u8,symbol[1..],name))return std.fmt.parseInt(u16,address,16);
  }return error.Symbol;
 }
 fn byte(f:*F,name:[]const u8,value:u8) !void {c.dos64_poke(f.m,try f.sym(name),value);}
 fn word(f:*F,name:[]const u8,value:u16) !void {const ad=try f.sym(name);c.dos64_poke(f.m,ad,@truncate(value));c.dos64_poke(f.m,ad+1,@truncate(value>>8));}
 fn long(f:*F,name:[]const u8,value:u32) !void {const ad=try f.sym(name);for(0..4) |i| c.dos64_poke(f.m,ad+@as(u16,@intCast(i)),@truncate(value>>@as(u5,@intCast(i*8))));}
 fn get(f:*F,name:[]const u8) !u8 {return c.dos64_peek(f.m,try f.sym(name));}
 fn call(f:*F,name:[]const u8) !c.Dos64Regs {
  const ret=try f.sym("fixture_return");c.dos64_poke(f.m,0x1ff,@truncate((ret-1)>>8));c.dos64_poke(f.m,0x1fe,@truncate(ret-1));
  c.dos64_set_regs(f.m,.{.pc=try f.sym(name),.sp=0xfd,.a=0x71,.x=0x82,.y=0x93,.p=0xed,.cycles=0,.instructions=0});
  const before=c.dos64_get_regs(f.m).cycles;const port=c.dos64_peek(f.m,1);const ddr=c.dos64_peek(f.m,0);
  const r=c.dos64_run(f.m,ret,100000);
  if(r.status!=c.DOS64_RUN_RETURNED)std.debug.print("call {s} failed status={d} pc={x}\n",.{name,r.status,r.regs.pc});
  try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),r.status);
  try std.testing.expectEqual(@as(u8,0xec),r.regs.p&0xee);
  try std.testing.expectEqual(ddr,c.dos64_peek(f.m,0));try std.testing.expectEqual(port&ddr,c.dos64_peek(f.m,1)&ddr);
  if(std.mem.eql(u8,name,"dos64_export_poll"))maximum_poll=@max(maximum_poll,r.regs.cycles-before);
  return r.regs;
 }
 fn start(f:*F) !void {try std.testing.expectEqual(@as(u8,0),(try f.call("dos64_export_start")).p&1);}
 fn tick(f:*F) !void {try f.word("dos64_export_now",f.now);_=try f.call("dos64_export_poll");}
 fn run(f:*F) !void {for(0..200000) |_| {if(try f.get("dos64_export_state")!=1)return;try f.tick();}return error.PollBudget;}
 fn until(f:*F,phase:u8) !void {for(0..200000) |_| {if(try f.get("dos64_export_phase")==phase)return;try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_state"));try f.tick();}return error.PollBudget;}
 fn authority(f:*F) !void {
  const expected=try a.alloc(u8,4*1024*1024);defer a.free(expected);@memset(expected,0);for(expected[BASE..][0..SIZE],0..) |*v,i|v.*=pattern(i);expected[BASE-1]=0x67;expected[BASE+SIZE]=0x79;
  try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,expected.ptr,expected.len));
  try std.testing.expectEqual(@as(u8,0x67),c.dos64_reu_peek(f.m,BASE-1));try std.testing.expectEqual(@as(u8,0x79),c.dos64_reu_peek(f.m,BASE+SIZE));
  try std.testing.expectEqual(@as(u8,0xa7),c.dos64_peek(f.m,0x7fff));try std.testing.expectEqual(@as(u8,0xb8),c.dos64_peek(f.m,0x8200));
  const prg=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,f.prg_path,a,.limited(65538));defer a.free(prg);
  const upload=try f.sym("dos64_uci_upload_operand");const drain=try f.sym("dos64_uci_drain_operand");
  for(prg[2..],0..) |v,i| {const ad=@as(u16,@intCast(0x801+i));if(ad==upload or ad==upload+1 or ad==drain or ad==drain+1)continue;try std.testing.expectEqual(v,c.dos64_peek(f.m,ad));}
  const state_start=try f.sym("dos64_export_state_start");const state_end=try f.sym("dos64_files_state_end");
  for(0..65536) |index| {const ad:@TypeOf(upload)=@intCast(index);if(c.dos64_was_written(f.m,ad)==0)continue;
   var init_operand=false;for([_][]const u8{"uci_status_read","uci_control_write","uci_id_read","uci_command_write","uci_data_read","uci_stat_read"}) |name| {const opcode=try f.sym(name);if(ad==opcode+1 or ad==opcode+2)init_operand=true;}
   if(init_operand or ad<=1 or (ad>=0x20 and ad<0x24) or (ad>=0x100 and ad<0x200) or (ad>=0x8000 and ad<0x8200) or (ad>=0xc100 and ad<0xc900) or (ad>=0xe000 and ad<0xe00a) or (ad>=state_start and ad<state_end) or (ad>=0xdf00 and ad<=0xdf0a) or (ad>=0xdf1c and ad<=0xdf1f) or ad==upload or ad==upload+1 or ad==drain or ad==drain+1)continue;
   std.debug.print("Forbidden native write {x}\n",.{ad});return error.ForbiddenWrite;
  }
 }
 fn failed(f:*F,code:u8) !void {try std.testing.expectEqual(@as(u8,3),try f.get("dos64_export_state"));try std.testing.expectEqual(code,try f.get("dos64_export_error"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_export_verified"));try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_uncertain"));try f.authority();}
};
fn pattern(i:usize) u8 {return @truncate((i*37)^(i>>8)^(i>>16)^0xa7);}

test "whole360KiB create-new write close reopen exact compare EOF close preserves authority" {
 var f=try F.init(false);defer f.deinit();try f.start();try f.run();
 try std.testing.expectEqual(@as(u8,2),try f.get("dos64_export_state"));try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_verified"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_export_uncertain"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_uncertain"));
 try std.testing.expectEqual(@as(u32,SIZE),c.export_model_size(f.m));for(0..SIZE) |i|try std.testing.expectEqual(pattern(i),c.export_model_byte(f.m,@intCast(i)));
 try std.testing.expectEqual(@as(u32,2),c.export_model_count(f.m,2));try std.testing.expectEqual(@as(u32,1440),c.export_model_count(f.m,5));
 try std.testing.expectEqual(@as(u32,721),c.export_model_count(f.m,4));try std.testing.expectEqual(@as(u32,1),c.export_model_count(f.m,7));try std.testing.expectEqual(@as(u32,2),c.export_model_count(f.m,3));
 try std.testing.expectEqual(@as(u8,0),c.export_model_open(f.m));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 try std.testing.expectEqual(@as(u64,2160),c.dos64_dma_transfers(f.m));try f.authority();
 std.debug.print("floppy_export_full_bytes={d} maximum_poll_cycles={d}\n",.{SIZE,maximum_poll});
}

test "existing destination never overwritten and unknown open cleanup is explicit" {
 var f=try F.init(true);defer f.deinit();try f.start();try f.run();try f.failed(1);
 try std.testing.expectEqual(@as(u32,97),c.export_model_size(f.m));for(0..97) |i|try std.testing.expectEqual(@as(u8,0x6b),c.export_model_byte(f.m,@intCast(i)));
 try std.testing.expectEqual(@as(u32,0),c.export_model_count(f.m,5));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));
 // Exact no-file CLOSE proves closed although operation status is failed.
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
}

test "short WRITE with success status is detected by fresh declared size" {
 var f=try F.init(false);defer f.deinit();c.export_model_faults(f.m,-1,5,-1,-1,0,0);try f.start();try f.run();try f.failed(8);
 try std.testing.expectEqual(@as(u32,SIZE-239),c.export_model_size(f.m));try std.testing.expectEqual(@as(u8,0),c.export_model_open(f.m));
}

test "corrupted read short read and extra EOF byte cannot publish success" {
 for([_]u8{0,1,2}) |which| {
  var f=try F.init(false);defer f.deinit();
  c.export_model_faults(f.m,-1,-1,if(which==0)123456 else -1,if(which==1)1024 else -1,if(which==2)1 else 0,0);
  try f.start();try f.run();try f.failed(if(which==0)4 else if(which==1)3 else 8);
  try std.testing.expectEqual(@as(u8,0),c.export_model_open(f.m));
 }
}

test "DMA partial failure never writes REU or advances verified sectors" {
 for([_]u64{0,1,1440}) |skip| {
  var f=try F.init(false);defer f.deinit();c.dos64_reu_fail_after(f.m,skip,17);try f.start();try f.run();try f.failed(2);
  if(skip<2){try std.testing.expectEqual(@as(u8,@intCast(skip)),try f.get("dos64_export_failure_half"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_export_failure_sector"));}
  try std.testing.expectEqual(@as(u8,0),c.export_model_open(f.m));
 }
}

test "every file phase failure preserves uncertain source and closure failure stays explicit" {
 for([_]c_int{1,2,3,1442,1443,1444,1445,2166}) |command| {
  var f=try F.init(false);defer f.deinit();c.export_model_faults(f.m,command,-1,-1,-1,0,0);try f.start();try f.run();try f.failed(1);
  try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 }
 var f=try F.init(false);defer f.deinit();c.export_model_faults(f.m,-1,-1,-1,-1,0,1);try f.start();try f.run();try f.failed(1);
 try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_cleanup_error"));try std.testing.expectEqual(@as(u8,2),try f.get("dos64_files_handle"));
}

test "start ownership pause banks path and busy rejection have no transport side effects" {
 for([_]u8{0,1,2,3,4,5}) |which| {
  var f=try F.init(false);defer f.deinit();
  switch(which){0=>try f.byte("dos64_export_owned",0),1=>try f.byte("dos64_export_paused",0),2=>try f.byte("dos64_export_bank",0x38),3=>try f.byte("dos64_export_path_len",129),4=>try f.byte("dos64_files_handle",2),5=>c.dos64_poke(f.m,try f.sym("dos64_export_path"),'x'),else=>unreachable}
  try std.testing.expectEqual(@as(u8,1),(try f.call("dos64_export_start")).p&1);try std.testing.expectEqual(@as(u32,0),c.export_model_count(f.m,0));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));try f.authority();
 }
 var f=try F.init(false);defer f.deinit();try f.start();try std.testing.expectEqual(@as(u8,1),(try f.call("dos64_export_start")).p&1);try f.run();try f.authority();
}

test "elapsed wrap total deadline stuck firmware and cancellation are bounded" {
 var f=try F.init(false);defer f.deinit();f.now=65500;try f.word("dos64_export_now",f.now);try f.long("dos64_export_limit",100);try f.start();
 f.now+%=99;try f.tick();try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_state"));f.now+%=1;try f.tick();try f.failed(6);
 var g=try F.init(false);defer g.deinit();try g.start();c.dos64_uci_model_stuck(g.m,1);g.now=1001;try g.tick();g.now=1102;try g.tick();try g.run();try g.failed(1);
 var h=try F.init(false);defer h.deinit();try h.start();try h.until(3);try h.byte("dos64_export_cancel",1);try h.run();try h.failed(7);
 std.debug.print("floppy_export_scenarios={d} maximum_poll_cycles={d}\n",.{scenarios,maximum_poll});
}


test "bank-safe public calls preserve all native mappings with poisoned ROM-visible state" {
 for(0..8) |bank| {var f=try F.init(false);defer f.deinit();c.dos64_poke(f.m,0,0x2f);c.dos64_poke(f.m,1,0xf8|@as(u8,@intCast(bank)));
  // Start state lives below KERNAL ROM; direct calls must expose it internally.
  try f.start();try f.until(3);try f.byte("dos64_export_cancel",1);try f.run();try f.failed(7);
 }
}

test "exact path128 upper bound target2 and slotB whole export remain binary correct" {
 var f=try F.init(false);defer f.deinit();
 try f.byte("dos64_files_target",2);try f.byte("dos64_export_bank",0x18);
 const path=try f.sym("dos64_export_path");try f.byte("dos64_export_path_len",128);
 for(0..128) |i|c.dos64_poke(f.m,path+@as(u16,@intCast(i)),if(i==0)'/' else if(i==127)0 else 'Q');
 for(0..SIZE) |i|c.dos64_reu_poke(f.m,0x180000+@as(u32,@intCast(i)),pattern(i)^0x39);
 try f.start();try f.run();try std.testing.expectEqual(@as(u8,2),try f.get("dos64_export_state"));
 for(0..SIZE) |i|try std.testing.expectEqual(pattern(i)^0x39,c.export_model_byte(f.m,@intCast(i)));
 // No destination REU write; both complete images and all other bytes exact.
 const expected=try a.alloc(u8,4*1024*1024);defer a.free(expected);@memset(expected,0);
 for(0..SIZE) |i|{expected[BASE+i]=pattern(i);expected[0x180000+i]=pattern(i)^0x39;}
 expected[BASE-1]=0x67;expected[BASE+SIZE]=0x79;
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,expected.ptr,expected.len));
}

test "gap8000 and cancellation during stuck transport terminate with explicit unknown handle" {
 var f=try F.init(false);defer f.deinit();try f.start();f.now=0x8000;try f.tick();try f.failed(6);
 var g=try F.init(false);defer g.deinit();try g.start();try g.until(3);c.dos64_uci_model_stuck(g.m,1);try g.byte("dos64_export_cancel",1);try g.tick();
 g.now=101;try g.tick();try g.run();try g.failed(7);try std.testing.expectEqual(@as(u8,1),try g.get("dos64_export_cleanup_error"));
 try std.testing.expectEqual(@as(u8,2),try g.get("dos64_files_handle"));
 std.debug.print("floppy_export_final_scenarios={d} maximum_poll_cycles={d}\n",.{scenarios,maximum_poll});
}

test "32bit total elapsed deadline and overflow retain first failure diagnostics" {
 var f=try F.init(false);defer f.deinit();try f.start();try f.long("dos64_export_elapsed",143000);f.now=1323;try f.tick();try f.failed(6);
 try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_failure_phase"));
 var g=try F.init(false);defer g.deinit();try g.start();try g.long("dos64_export_elapsed",0xffffffff);g.now=1;try g.tick();try g.failed(6);
 var h=try F.init(false);defer h.deinit();c.export_model_faults(h.m,2,-1,-1,-1,0,0);try h.start();try h.run();try h.failed(1);
 try std.testing.expectEqual(@as(u8,3),try h.get("dos64_export_failure_phase"));try std.testing.expectEqual(@as(u8,3),try h.get("dos64_export_failure_files_error"));
 std.debug.print("floppy_export_complete_scenarios={d} maximum_poll_cycles={d}\n",.{scenarios,maximum_poll});
}


test "aligned full-sector DMA alias hypothesis is bypassed by every256-byte WRITE" {
 var f=try F.init(false);defer f.deinit();c.export_model_dma_alias(f.m,1);try f.start();try f.run();
 try std.testing.expectEqual(@as(u8,2),try f.get("dos64_export_state"));
 try std.testing.expectEqual(@as(u32,0),c.export_model_alias_hits(f.m));
 try std.testing.expectEqual(@as(u32,1440),c.export_model_count(f.m,5));
 for(0..1440) |i|try std.testing.expectEqual(@as(u32,256),c.export_model_write_size(f.m,@intCast(i)));
 for(0..SIZE) |i|try std.testing.expectEqual(pattern(i),c.export_model_byte(f.m,@intCast(i)));
 try std.testing.expectEqual(@as(u8,0xd0),try f.get("dos64_export_sectors"));
 try std.testing.expectEqual(@as(u8,2),c.dos64_peek(f.m,(try f.sym("dos64_export_sectors"))+1));
 try f.authority();
}

test "first and second half WRITE failure report logical sector and half without advancement" {
 for([_]c_int{2,3,4,5,1440,1441}) |command| {
  var f=try F.init(false);defer f.deinit();c.export_model_faults(f.m,command,-1,-1,-1,0,0);try f.start();try f.run();try f.failed(1);
  const write_index:usize=@intCast(command-2);
  try std.testing.expectEqual(@as(u8,@intCast(write_index%2)),try f.get("dos64_export_failure_half"));
  const sector=write_index/2;const address=try f.sym("dos64_export_failure_sector");
  try std.testing.expectEqual(@as(u16,@intCast(sector)),@as(u16,c.dos64_peek(f.m,address))|(@as(u16,c.dos64_peek(f.m,address+1))<<8));
  try std.testing.expectEqual(@as(u8,3),try f.get("dos64_export_failure_phase"));
  try std.testing.expectEqual(@as(u32,@intCast(write_index*256)),c.export_model_size(f.m));
  try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 }
}



test "second-half cancellation preserves first-half file bytes logical count and source" {
 var f=try F.init(false);defer f.deinit();try f.start();
 for(0..200000) |_| {
  if(try f.get("dos64_export_write_half")==1 and try f.get("dos64_export_phase")==2)break;
  try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_state"));try f.tick();
 }
 try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_write_half"));
 try f.byte("dos64_export_cancel",1);try f.run();try f.failed(7);
 try std.testing.expectEqual(@as(u8,1),try f.get("dos64_export_failure_half"));
 try std.testing.expectEqual(@as(u8,2),try f.get("dos64_export_failure_phase"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_export_failure_sector"));
 try std.testing.expectEqual(@as(u32,256),c.export_model_size(f.m));
 try std.testing.expectEqual(@as(u32,1),c.export_model_count(f.m,5));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 for(0..256) |i|try std.testing.expectEqual(pattern(i),c.export_model_byte(f.m,@intCast(i)));
}

const std=@import("std");
const c=@cImport({@cInclude("peddle_bridge.h");@cInclude("image_import_model.h");});
const allocator=std.testing.allocator;
const SIZE=4*1024*1024;
var maximum_poll:u64=0;
const F=struct {
 m:*c.Dos64Machine,
 labels:[]u8,
 fn init(source:[]const u8) !F {
  const prg=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"build/dos64-native-file-restore.prg",allocator,.limited(65538));defer allocator.free(prg);
  const m=c.dos64_create() orelse return error.Machine;errdefer c.dos64_destroy(m);
  c.dos64_load(m,0x801,prg[2..].ptr,prg.len-2);
  _=c.dos64_enable_reu_sized(m,16384);
  c.dos64_uci_model_enable(m,0xdf1c,1,0xc9);
  c.import_model_source(m,source.ptr,source.len);
  var f:F=.{.m=m,.labels=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"build/dos64-native-file-restore.labels",allocator,.limited(200000))};
  _=try f.call("dos64_uci_init");_=try f.call("dos64_files_init");_=try f.call("dos64_restore_cold_init");
  try f.word("dos64_uci_timeout",1000);try f.word("dos64_uci_recovery_timeout",100);
  const path=try f.sym("dos64_uci_command")+3;
  for("disk.img\x00",0..) |b,i| c.dos64_poke(m,path+@as(u16,@intCast(i)),b);
  try f.byte("dos64_files_path_len",9);
  try f.long("dos64_restore_expected_crc",crc32(source));
  c.dos64_poke(m,0x7fff,0xa7);c.dos64_poke(m,0x8800,0xb8);
  return f;
 }
 fn deinit(f:*F) void {allocator.free(f.labels);c.dos64_destroy(f.m);}
 fn sym(f:*F,name:[]const u8) !u16 {
  var lines=std.mem.splitScalar(u8,f.labels,'\n');while(lines.next()) |line| {
   var fields=std.mem.tokenizeAny(u8,line," \t\r");if(!std.mem.eql(u8,fields.next() orelse continue,"al")) continue;
   const address=fields.next() orelse continue;const symbol=fields.next() orelse continue;
   if(std.mem.eql(u8,symbol[1..],name)) return std.fmt.parseInt(u16,address,16);
  }return error.Symbol;
 }
 fn byte(f:*F,name:[]const u8,value:u8) !void {c.dos64_poke(f.m,try f.sym(name),value);}
 fn word(f:*F,name:[]const u8,value:u16) !void {const ad=try f.sym(name);c.dos64_poke(f.m,ad,@truncate(value));c.dos64_poke(f.m,ad+1,@truncate(value>>8));}
 fn long(f:*F,name:[]const u8,value:u32) !void {const ad=try f.sym(name);for(0..4) |i| c.dos64_poke(f.m,ad+@as(u16,@intCast(i)),@truncate(value>>@as(u5,@intCast(i*8))));}
 fn get(f:*F,name:[]const u8) !u8 {return c.dos64_peek(f.m,try f.sym(name));}
 fn readlong(f:*F,name:[]const u8) !u32 {const ad=try f.sym(name);var value:u32=0;for(0..4) |i| value|=@as(u32,c.dos64_peek(f.m,ad+@as(u16,@intCast(i))))<<@as(u5,@intCast(i*8));return value;}
 fn call(f:*F,name:[]const u8) !c.Dos64Regs {
  const ret=try f.sym("fixture_return");c.dos64_poke(f.m,0x1ff,@truncate((ret-1)>>8));c.dos64_poke(f.m,0x1fe,@truncate(ret-1));
  c.dos64_set_regs(f.m,.{.pc=try f.sym(name),.sp=0xfd,.a=0x71,.x=0x82,.y=0x93,.p=0x24,.cycles=0,.instructions=0});
  const before=c.dos64_get_regs(f.m).cycles;const result=c.dos64_run(f.m,ret,100000);
  try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),result.status);
  if(std.mem.eql(u8,name,"dos64_restore_cold_poll")) maximum_poll=@max(maximum_poll,result.regs.cycles-before);
  return result.regs;
 }
 fn start(f:*F) !void {const r=try f.call("dos64_restore_cold_start");try std.testing.expectEqual(@as(u8,0),r.p&1);}
 fn run(f:*F,budget:usize) !void {for(0..budget) |_| {if(try f.get("dos64_restore_state")!=1)return;_=try f.call("dos64_restore_cold_poll");}return error.PollBudget;}
 fn guards(f:*F) !void {
  try std.testing.expectEqual(@as(u8,0xa7),c.dos64_peek(f.m,0x7fff));try std.testing.expectEqual(@as(u8,0xb8),c.dos64_peek(f.m,0x8800));
  const prg=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"build/dos64-native-file-restore.prg",allocator,.limited(65538));defer allocator.free(prg);
  const upload=(try f.sym("dos64_uci_upload_operand"))-1;const drain=(try f.sym("dos64_uci_drain_operand"))-1;
  const upload_ptr=@as(u16,c.dos64_peek(f.m,upload+1))|(@as(u16,c.dos64_peek(f.m,upload+2))<<8);
  const drain_ptr=@as(u16,c.dos64_peek(f.m,drain+1))|(@as(u16,c.dos64_peek(f.m,drain+2))<<8);
  try std.testing.expect(upload_ptr>=0xc100 and upload_ptr<=0xc47f);
  try std.testing.expect(drain_ptr>=0xc480 and drain_ptr<=0xc7ff);
  for(prg[2..],0..) |expected,i| {
   const address=0x801+@as(u16,@intCast(i));
   if(address==upload+1 or address==upload+2 or address==drain+1 or address==drain+2) continue;
   try std.testing.expectEqual(expected,c.dos64_peek(f.m,address));
  }
 }
};
fn crc32(data:[]const u8) u32 {var crc:u32=0xffffffff;for(data) |b| {crc^=b;for(0..8) |_| {const low=crc&1;crc>>=1;if(low!=0)crc^=0xedb88320;}}return ~crc;}
fn pattern(i:usize) u8 {return @truncate((i*37)^(i>>8)^(i>>16)^0xa7);}

test "seeded exact4MiB direct file restore groups2048DMA and protects12MiB remainder" {
 const source=try allocator.alloc(u8,SIZE);defer allocator.free(source);for(source,0..) |*b,i| b.*=pattern(i);
 var f=try F.init(source);defer f.deinit();
 const initial=try allocator.alloc(u8,16*1024*1024);defer allocator.free(initial);
 for(initial,0..) |*b,i| {b.*=pattern(i)^0xff;c.dos64_reu_poke(f.m,@intCast(i),b.*);}
 // First DMA intentionally fails after17bytes. Cleanup must close ownership;
 // a fresh verified whole request then repairs the partial prefix.
 c.dos64_reu_fail_after(f.m,0,17);try f.start();try f.run(1000);
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,6),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 _=try f.call("dos64_restore_cold_init");try f.long("dos64_restore_expected_crc",crc32(source));
 const path=try f.sym("dos64_uci_command")+3;
 for("disk.img\x00",0..) |b,i| c.dos64_poke(f.m,path+@as(u16,@intCast(i)),b);
 try f.start();try f.run(1800000);
 try std.testing.expectEqual(@as(u8,2),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,1),try f.get("dos64_restore_complete"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));try std.testing.expectEqual(@as(u8,0),c.import_model_open(f.m));
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,source.ptr,source.len));
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,SIZE,initial[SIZE..].ptr,initial.len-SIZE));
 try std.testing.expectEqual(@as(u64,2049),c.dos64_dma_transfers(f.m));try std.testing.expectEqual(@as(u64,SIZE+17),c.dos64_dma_bytes(f.m));
 try f.guards();std.debug.print("maximum_restore_poll_cycles={d}\n",.{maximum_poll});
}

test "short source and failed preclose cannot publish success or write a partial2048group" {
 const source=[_]u8{0x53}**1536;
 var f=try F.init(&source);defer f.deinit();try f.start();try f.run(1000);
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));try f.guards();
 var g=try F.init(&source);defer g.deinit();c.import_model_faults(g.m,-1,-1,-1,1);try g.start();try g.run(1000);
 try std.testing.expectEqual(@as(u8,3),try g.get("dos64_restore_state"));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(g.m));
 try std.testing.expectEqual(@as(u8,2),try g.get("dos64_files_handle"));try std.testing.expectEqual(@as(u8,1),try g.get("dos64_restore_cleanup_error"));
}

test "32bit elapsed accumulation survives16bit wrap and enforces hard600bound in cleanup" {
 var f=try F.init(&.{});defer f.deinit();try f.start();
 try f.byte("dos64_restore_phase",3);
 // Keep transport active so cleanup cannot terminate before the clock check.
 c.dos64_uci_model_stuck(f.m,1);
 var elapsed:u32=0;
 while(elapsed<144322) {
  elapsed+=@min(@as(u32,20000),144322-elapsed);try f.word("dos64_restore_now",@truncate(elapsed));_=try f.call("dos64_restore_cold_poll");
  if(try f.get("dos64_restore_state")!=1) break;
 }
 try std.testing.expectEqual(@as(u32,144322),try f.readlong("dos64_restore_elapsed"));
 try f.word("dos64_restore_now",@truncate(@as(u32,144323)));_=try f.call("dos64_restore_cold_poll");
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,7),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u8,1),try f.get("dos64_restore_cleanup_error"));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));
}


test "full length source CRC corruption is rejected after exact bounded REU writes" {
 const source=try allocator.alloc(u8,SIZE);defer allocator.free(source);for(source,0..) |*b,i| b.*=pattern(i);
 var f=try F.init(source);defer f.deinit();c.import_model_faults(f.m,-1,123456,-1,0);try f.start();try f.run(1800000);
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,5),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_restore_complete"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 try std.testing.expectEqual(@as(u64,2048),c.dos64_dma_transfers(f.m));try std.testing.expectEqual(@as(u64,SIZE),c.dos64_dma_bytes(f.m));
 try std.testing.expectEqual(@as(u32,123456),c.dos64_reu_compare(f.m,0,source.ptr,source.len));try f.guards();
}

test "extra byte after4MiB is rejected without writing beyond exact destination" {
 const source=try allocator.alloc(u8,SIZE+1);defer allocator.free(source);for(source,0..) |*b,i| b.*=pattern(i);
 var f=try F.init(source);defer f.deinit();c.dos64_reu_poke(f.m,SIZE,0xb7);try f.start();try f.run(1800000);
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,4),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_restore_complete"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,source.ptr,SIZE));try std.testing.expectEqual(@as(u8,0xb7),c.dos64_reu_peek(f.m,SIZE));
 try std.testing.expectEqual(@as(u64,2048),c.dos64_dma_transfers(f.m));try f.guards();
}

test "failed final CLOSE stays failed even when cleanup establishes closed ownership" {
 const source=try allocator.alloc(u8,SIZE);defer allocator.free(source);for(source,0..) |*b,i| b.*=pattern(i);
 var f=try F.init(source);defer f.deinit();c.import_model_faults(f.m,8196,-1,-1,0);try f.start();try f.run(1800000);
 try std.testing.expectEqual(@as(u8,3),try f.get("dos64_restore_state"));try std.testing.expectEqual(@as(u8,8),try f.get("dos64_restore_error"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_restore_complete"));try std.testing.expectEqual(@as(u8,0),try f.get("dos64_restore_cleanup_error"));
 try std.testing.expectEqual(@as(u8,0),try f.get("dos64_files_handle"));try std.testing.expectEqual(@as(u8,0),c.import_model_open(f.m));
 try std.testing.expectEqual(@as(u32,8197),c.import_model_commands(f.m));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.m,0,source.ptr,SIZE));try f.guards();
}

test "actual native entry validates cold config then reaches short source failure with owned clock" {
 const source=[_]u8{0x53}**1536;
 var f=try F.init(&source);defer f.deinit();const cfg=try f.sym("restore_config");
 // Disabled and wrong magic configurations stop before any file transaction.
 var result:c.Dos64RunResult=undefined;
 c.dos64_set_regs(f.m,.{.pc=try f.sym("restore_entry"),.sp=0xff,.a=0,.x=0,.y=0,.p=0x24,.cycles=0,.instructions=0});
 result=c.dos64_run(f.m,try f.sym("restore_idle"),10000);try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),result.status);
 try std.testing.expectEqual(@as(u32,0),c.import_model_commands(f.m));
 c.dos64_poke(f.m,cfg+4,0xa5);c.dos64_poke(f.m,cfg+5,9);c.dos64_poke(f.m,cfg,0);
 c.dos64_set_regs(f.m,.{.pc=try f.sym("restore_entry"),.sp=0xff,.a=0,.x=0,.y=0,.p=0x24,.cycles=0,.instructions=0});
 result=c.dos64_run(f.m,try f.sym("restore_idle"),10000);try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),result.status);
 try std.testing.expectEqual(@as(u32,0),c.import_model_commands(f.m));c.dos64_poke(f.m,cfg,'D');
 const crc=crc32(&source);for(0..4) |i| c.dos64_poke(f.m,cfg+6+@as(u16,@intCast(i)),@truncate(crc>>@as(u5,@intCast(i*8))));
 for("disk.img\x00",0..) |b,i| c.dos64_poke(f.m,cfg+10+@as(u16,@intCast(i)),b);
 c.dos64_cia_clock_enable(f.m);c.dos64_cia_clock_step(f.m,1);
 c.dos64_set_regs(f.m,.{.pc=try f.sym("restore_entry"),.sp=0xff,.a=0,.x=0,.y=0,.p=0x24,.cycles=0,.instructions=0});
 result=c.dos64_run(f.m,try f.sym("restore_idle"),10000000);try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),result.status);
 try std.testing.expectEqual(@as(u8,0xe1),c.dos64_peek(f.m,0x6004));try std.testing.expectEqual(@as(u8,3),c.dos64_peek(f.m,0x6005));
 try std.testing.expectEqual(@as(u8,0),c.dos64_peek(f.m,0x6008));try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.m));
 // Undriven CPU-port input bits read pulled high; only driven mapping bits apply.
 try std.testing.expectEqual(@as(u8,5),c.dos64_peek(f.m,1)&7);
}

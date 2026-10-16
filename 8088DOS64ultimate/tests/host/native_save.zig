const std=@import("std");const h=@import("machine.zig");const F=h.Fixture;const c=h.c;
const model=@cImport({@cInclude("image_import_model.h");@cInclude("host_input_model.h");@cInclude("file_model.h");});
const a=std.testing.allocator;const SIZE=368640;
var max_tick:u64=0;var max_modal_poll:u64=0;var max_prepare:u64=0;var scenarios:usize=0;
fn p(f:*F,n:[]const u8,v:u8) !void {f.poke(try f.symbol(n),v);}
fn g(f:*F,n:[]const u8) !u8 {return f.peek(try f.symbol(n));}
fn word(f:*F,n:[]const u8,v:u16) !void {const s=try f.symbol(n);f.poke(s,@truncate(v));f.poke(s+1,@truncate(v>>8));}
fn diag(f:*F,i:u16) !u8 {return f.peek((try f.symbol("dos64_native_diag"))+i);}
fn put(f:*F,i:u16,v:u8) !void {f.poke((try f.symbol("dos64_native_diag"))+i,v);}
fn call(f:*F,n:[]const u8,budget:u64) !void {const borrowed=try g(f,"sav_borrowed");const command=try diag(f,3);const before=c.dos64_get_regs(f.machine).cycles;const r=f.call(n,budget) catch |err| {const regs=c.dos64_get_regs(f.machine);std.debug.print("native save machine error {s}/{s} pc={x} cycles={d} diag={d}/{d}/{d} import={d}/{d}\n",.{n,@errorName(err),regs.pc,regs.cycles,try diag(f,0),try diag(f,1),try diag(f,2),try g(f,"dos64_import_state"),try g(f,"dos64_import_error")});return err;};const cost=r.cycles-before;if(r.p&1!=0)std.debug.print("native save call failed {s} diag={d}/{d}/{d} overlay={d} save={d}\n",.{n,try diag(f,0),try diag(f,1),try diag(f,2),try g(f,"dos64_overlay_error"),try g(f,"sav_error")});try std.testing.expectEqual(@as(u8,0),r.p&1);if(std.mem.eql(u8,n,"dos64_native_tick")){max_tick=@max(max_tick,cost);if(borrowed==1)max_modal_poll=@max(max_modal_poll,cost) else if(command==7)max_prepare=@max(max_prepare,cost);}c.dos64_cia_clock_advance(f.machine,@intCast(cost/64));}
fn setup() !F {
 var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);c.dos64_uci_model_enable(f.machine,0xdf1c,3,0xc9);c.dos64_cia_clock_enable(f.machine);c.dos64_cia_clock_step(f.machine,1);c.dos64_native_display_enable(f.machine);model.dos64_host_input_model_enable(@ptrCast(f.machine));c.native_runtime_control_enable(f.machine);
 const input=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img",a,.limited(SIZE+1));defer a.free(input);model.import_model_source(f.machine,input.ptr,input.len);
 const config=try f.symbol("dos64_native_config");f.poke(config+4,0xa5);f.poke(config+7,9);for([_]u8{0x37,0x0a,0x77,0x30},0..) |v,i|f.poke(config+10+@as(u16,@intCast(i)),v);for("disk.img\x00",0..) |b,i|f.poke(config+14+@as(u16,@intCast(i)),b);
 try call(&f,"dos64_native_start",500000);
 for(0..200000) |_| {if(try diag(&f,0)==4)break;try std.testing.expectEqual(@as(u8,2),try diag(&f,0));try call(&f,"dos64_native_cold_poll",40000000);}
 try std.testing.expectEqual(@as(u8,4),try diag(&f,0));try put(&f,3,2);try call(&f,"dos64_native_tick",4000000);try std.testing.expectEqual(@as(u8,5),try diag(&f,0));
 model.export_model_enable(f.machine,0);try p(&f,"dos64_export_owned",0xa5);try p(&f,"dos64_export_paused",0xa5);try p(&f,"dos64_export_bank",0x10);
 const path="/usb1/DOS64_TEST/save-owned/WORK.IMG\x00";try p(&f,"dos64_export_path_len",path.len);for(path,0..) |b,i|f.poke((try f.symbol("dos64_export_path"))+@as(u16,@intCast(i)),b);
 scenarios+=1;return f;
}
fn run(f:*F) !void {for(0..250000) |_| {if(try g(f,"sav_borrowed")==0)return;try call(f,"dos64_native_tick",100000);}return error.Budget;}
fn source(f:*F) ![]u8 {const bytes=try a.alloc(u8,SIZE);errdefer a.free(bytes);try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,0x100000,bytes.ptr,bytes.len));return bytes;}
fn start(f:*F) !void {try put(f,3,7);try call(f,"dos64_native_tick",2000000);try std.testing.expectEqual(@as(u8,1),try g(f,"sav_borrowed"));try std.testing.expectEqual(@as(u8,24),try g(f,"dos64_cache_limit"));try std.testing.expectEqual(@as(u8,7),try diag(f,0));}
fn guest(f:*F) ![28]u8 {var b:[28]u8=undefined;const at=try f.symbol("dos64_guest");for(&b,0..) |*v,i|v.*=f.peek(at+@as(u16,@intCast(i)));return b;}
fn snapshot(f:*F,start_addr:u16,len:usize) ![]u8 {const b=try a.alloc(u8,len);for(b,0..) |*v,i|v.*=f.peek(start_addr+@as(u16,@intCast(i)));return b;}

test "real native cold import pause SAVE creates exact image and restores32frames guest registers bitmap" {
 var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);const regs=try guest(&f);const whole=try a.alloc(u8,4*1024*1024);defer a.free(whole);try std.testing.expectEqual(@as(u8,1),c.dos64_reu_read(f.machine,0,whole.ptr,whole.len));const image=try snapshot(&f,0x6000,8000);defer a.free(image);
 const epoch=try snapshot(&f,try f.symbol("dos64_write_epoch"),4);defer a.free(epoch);
 try start(&f);try run(&f);try std.testing.expectEqual(@as(u8,5),try diag(&f,0));try std.testing.expectEqual(@as(u8,0xa5),try diag(&f,4));try std.testing.expectEqual(@as(u8,32),try g(&f,"dos64_cache_limit"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_verified"));
 try std.testing.expectEqualSlices(u8,&regs,&try guest(&f));for(image,0..) |v,i|try std.testing.expectEqual(v,f.peek(0x6000+@as(u16,@intCast(i))));for(epoch,0..) |v,i|try std.testing.expectEqual(v,f.peek((try f.symbol("dos64_write_epoch"))+@as(u16,@intCast(i))));
 try std.testing.expectEqual(@as(u32,SIZE),model.export_model_size(f.machine));for(before,0..) |v,i|try std.testing.expectEqual(v,model.export_model_byte(f.machine,@intCast(i)));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0,whole.ptr,whole.len));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_files_handle"));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_overlay_busy"));
 try put(&f,3,3);for(0..256) |_| {try call(&f,"dos64_native_tick",1000000);if(try diag(&f,3)==0)break;}
 try std.testing.expectEqual(@as(u8,4),try diag(&f,0));std.debug.print("native_save_full={d} max_tick={d}\n",.{SIZE,max_tick});
}

test "all dirty frames flush before borrow no epochs reset borrowed pins reject before any DMA" {
 var f=try setup();defer f.deinit();const adr=try f.symbol("dos64_address");
 for(0..32) |i| {const physical=0x20000+i*512;for(0..3) |j|f.poke(adr+@as(u16,@intCast(j)),@truncate(physical>>@as(u5,@intCast(j*8))));try p(&f,"dos64_mem_value",@intCast(i+1));try call(&f,"dos64_mem_write",100000);}
 const epoch=try snapshot(&f,try f.symbol("dos64_write_epoch"),4);defer a.free(epoch);try start(&f);
 for(0..32) |i|try std.testing.expectEqual(@as(u8,@intCast(i+1)),c.dos64_reu_peek(f.machine,@intCast(0x20000+i*512)));
 for(24..32) |i|try std.testing.expectEqual(@as(u8,0),f.peek((try f.symbol("dos64_cache_flags"))+@as(u16,@intCast(i))));
 try run(&f);for(epoch,0..) |v,i|try std.testing.expectEqual(v,f.peek((try f.symbol("dos64_write_epoch"))+@as(u16,@intCast(i))));
 var pinned=try setup();defer pinned.deinit();pinned.poke((try pinned.symbol("dos64_cache_pins"))+29,1);const count=c.dos64_dma_transfers(pinned.machine);try put(&pinned,3,7);try call(&pinned,"dos64_native_tick",100000);
 try std.testing.expectEqual(count,c.dos64_dma_transfers(pinned.machine));try std.testing.expectEqual(@as(u8,0),try g(&pinned,"sav_borrowed"));try std.testing.expectEqual(@as(u8,0xe1),try diag(&pinned,4));
}

test "SAVE rejects running HD busy FILE unknown and owner reentry without stealing ownership" {
 for([_]u8{0,1,2,3,4,5,6,7}) |which| {var f=try setup();defer f.deinit();switch(which){0=>try put(&f,0,4),1=>try p(&f,"hdb_online",1),2=>try p(&f,"dos64_files_handle",2),3=>try p(&f,"dos64_overlay_busy",1),4=>try p(&f,"hdb_active",1),5=>try p(&f,"dos64_disk_loaded",0),6=>try p(&f,"dos64_export_bank",0x18),7=>try p(&f,"dos64_disk_sectors",0),else=>unreachable}const count=c.dos64_dma_transfers(f.machine);try put(&f,3,7);try call(&f,"dos64_native_tick",100000);try std.testing.expectEqual(@as(u8,0),try g(&f,"sav_borrowed"));try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,4));try std.testing.expectEqual(count+@as(u64,if(which>=5)1 else 0),c.dos64_dma_transfers(f.machine));}
}

test "cancellation preserves source known failure resumes safely unknown cleanup blocks RUN" {
 for([_]bool{false,true}) |bad_close| {var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);if(bad_close)model.export_model_faults(f.machine,-1,-1,-1,-1,0,1);try start(&f);for(0..1000) |_| {if(try g(&f,"dos64_export_phase")==3)break;try call(&f,"dos64_native_tick",100000);}
  try put(&f,3,9);try run(&f);try std.testing.expectEqual(@as(u8,32),try g(&f,"dos64_cache_limit"));try std.testing.expectEqual(@as(u8,if(bad_close)0xe1 else 5),try diag(&f,0));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_uncertain"));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
  if(bad_close){try put(&f,3,3);try call(&f,"dos64_native_tick",100000);try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));}
 }
}

test "failed modal slot DMA cannot execute partial code and restorecache does not allow RUN" {
 var f=try setup();defer f.deinit();c.dos64_reu_fail_after(f.machine,0,17);try put(&f,3,7);try call(&f,"dos64_native_tick",2000000);try std.testing.expectEqual(@as(u8,0),try g(&f,"sav_borrowed"));try std.testing.expectEqual(@as(u8,32),try g(&f,"dos64_cache_limit"));try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));try std.testing.expectEqual(@as(u32,0),model.export_model_count(f.machine,5));
 std.debug.print("native_save_scenarios={d} max_tick={d}\n",.{scenarios,max_tick});
}


test "dirty flush failure retains cache prefix and blocks RUN before code borrow" {
 var f=try setup();defer f.deinit();const adr=try f.symbol("dos64_address");f.poke(adr,0);f.poke(adr+1,0x80);f.poke(adr+2,1);try p(&f,"dos64_mem_value",0xa7);try call(&f,"dos64_mem_write",100000);const selected=try g(&f,"dos64_cache_selected");
 c.dos64_reu_fail_after(f.machine,0,17);try put(&f,3,7);try call(&f,"dos64_native_tick",1000000);try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));try std.testing.expectEqual(@as(u8,0),try g(&f,"sav_borrowed"));try std.testing.expectEqual(@as(u8,32),try g(&f,"dos64_cache_limit"));try std.testing.expect(f.peek((try f.symbol("dos64_cache_flags"))+selected)&2!=0);try std.testing.expectEqual(@as(u8,0xa7),f.peek(0x8000+@as(u16,selected)*512));
 try put(&f,3,3);try call(&f,"dos64_native_tick",100000);try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));
 std.debug.print("native_save_final_scenarios={d} maximum_modal_poll={d} maximum_prepare={d}\n",.{scenarios,max_modal_poll,max_prepare});
}


test "loss of real native clock ownership cancels with source retained and unsafe RUN blocked" {
 var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);try start(&f);try p(&f,"dos64_host_clock_claim",0);try run(&f);
 try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));try std.testing.expectEqual(@as(u8,32),try g(&f,"dos64_cache_limit"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_uncertain"));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
 try put(&f,3,3);try call(&f,"dos64_native_tick",100000);try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,0));
 std.debug.print("native_save_complete_scenarios={d} maximum_modal_poll={d} maximum_prepare={d}\n",.{scenarios,max_modal_poll,max_prepare});
}

test "actual partially completed REP survives paused SAVE and native RUN finishes exact remaining elements" {
 var f=try setup();defer f.deinit();const regs=try f.symbol("dos64_guest");for(0..28) |i|f.poke(regs+@as(u16,@intCast(i)),0);
 f.poke(regs+2,33);f.poke(regs+9,0x90);f.poke(regs+13,0x10);f.poke(regs+15,0x20);f.poke(regs+25,0x30);f.poke(regs+26,2);
 const adr=try f.symbol("dos64_address");
 for([_]u8{0xf3,0xa4,0xf4},0..) |v,i| {f.poke(adr,@intCast(i));f.poke(adr+1,0x30);f.poke(adr+2,0);try p(&f,"dos64_mem_value",v);try call(&f,"dos64_mem_write",100000);}
 for(0..33) |i| {f.poke(adr,@intCast(i));f.poke(adr+1,0x10);f.poke(adr+2,0);try p(&f,"dos64_mem_value",@intCast(0x60+i));try call(&f,"dos64_mem_write",100000);f.poke(adr+1,0x20);try p(&f,"dos64_mem_value",0xff);try call(&f,"dos64_mem_write",100000);}
 try call(&f,"dos64_cpu_step",1000000);try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_string_pending"));try std.testing.expectEqual(@as(u16,17),f.word(regs+2));
 try put(&f,3,2);try call(&f,"dos64_native_tick",4000000);
 const names=[_][]const u8{"dos64_cpu_pending","dos64_string_pending","cpu_rep","cpu_override","string_width","string_kind","string_slice","string_delta","dos64_cpu_irq_shadow","dos64_cpu_opcode","dos64_cpu_yield"};var state:[names.len]u8=undefined;for(names,0..) |name,i|state[i]=try g(&f,name);const before=try guest(&f);
 try start(&f);try run(&f);for(names,0..) |name,i|try std.testing.expectEqual(state[i],try g(&f,name));try std.testing.expectEqualSlices(u8,&before,&try guest(&f));
 try put(&f,3,3);for(0..256) |_| {try call(&f,"dos64_native_tick",1000000);if(try diag(&f,3)==0)break;}
 try std.testing.expectEqual(@as(u8,4),try diag(&f,0));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_string_pending"));try std.testing.expectEqual(@as(u16,0),f.word(regs+2));
 for(0..33) |i| {f.poke(adr,@intCast(i));f.poke(adr+1,0x20);f.poke(adr+2,0);const value=try f.call("dos64_mem_read",100000);try std.testing.expectEqual(@as(u8,@intCast(0x60+i)),value.a);}
 std.debug.print("native_save_with_REP_scenarios={d} maximum_modal_poll={d} maximum_prepare={d}\n",.{scenarios,max_modal_poll,max_prepare});
}


test "fresh FILE_INFO rejects every non360KiB LE32 size before any data READ" {
 for([_]i64{0,368639,368641,0x0105a000,0xffffffff}) |size| {var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);model.export_model_info(f.machine,size,0);try start(&f);try run(&f);
  try std.testing.expectEqual(@as(u8,5),try diag(&f,0));try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,4));try std.testing.expectEqual(@as(u8,8),try g(&f,"dos64_export_error"));try std.testing.expectEqual(@as(u8,12),try g(&f,"dos64_export_failure_phase"));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_export_verified"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_uncertain"));
  try std.testing.expectEqual(@as(u32,1),model.export_model_count(f.machine,7));try std.testing.expectEqual(@as(u32,0),model.export_model_count(f.machine,4));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_files_handle"));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
 }
}

test "empty truncated oversized bad-attribute NUL-name MORE and stale FILE_INFO responses cannot verify" {
 for([_]c_int{1,2,3,4,5,6,7,8,9,12,13}) |fault| {var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);model.export_model_info(f.machine,-1,fault);try start(&f);try run(&f);
  try std.testing.expectEqual(@as(u8,0xe1),try diag(&f,4));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_error"));try std.testing.expectEqual(@as(u8,12),try g(&f,"dos64_export_failure_phase"));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_export_verified"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_uncertain"));try std.testing.expectEqual(@as(u32,0),model.export_model_count(f.machine,4));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_files_handle"));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
 }
}

test "declared metadata size rejects the preserved extra-tail zero-EOF error counterexample before READ" {
 var f=try setup();defer f.deinit();const before=try source(&f);defer a.free(before);model.export_model_faults(f.machine,-1,-1,-1,-1,1,0);try start(&f);try run(&f);
 try std.testing.expectEqual(@as(u32,SIZE+1),model.export_model_size(f.machine));try std.testing.expectEqual(@as(u32,1),model.export_model_count(f.machine,7));try std.testing.expectEqual(@as(u32,0),model.export_model_count(f.machine,4));try std.testing.expectEqual(@as(u8,8),try g(&f,"dos64_export_error"));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_export_verified"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_uncertain"));try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_files_handle"));try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0x100000,before.ptr,before.len));
}

test "FILE_INFO record boundary sizes13and75 and exact360KiB each permit verified native export" {
 for([_]c_int{10,11}) |kind| {var f=try setup();defer f.deinit();model.export_model_info(f.machine,SIZE,kind);try start(&f);try run(&f);try std.testing.expectEqual(@as(u8,0xa5),try diag(&f,4));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_export_verified"));try std.testing.expectEqual(@as(u32,1),model.export_model_count(f.machine,7));try std.testing.expectEqual(@as(u32,721),model.export_model_count(f.machine,4));}
 std.debug.print("native_save_FILE_INFO_scenarios={d} maximum_modal_poll={d} maximum_prepare={d}\n",.{scenarios,max_modal_poll,max_prepare});
}

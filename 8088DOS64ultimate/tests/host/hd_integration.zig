const std=@import("std");const host=@import("machine.zig");const F=host.Fixture;const c=host.c;
const m=@cImport({@cInclude("hd_file_model.h");@cInclude("hd_trace.h");@cInclude("uci_model.h");});const a=std.testing.allocator;
fn p(f:*F,n:[]const u8,v:u8)!void{f.poke(try f.symbol(n),v);}fn g(f:*F,n:[]const u8)!u8{return f.peek(try f.symbol(n));}
fn w(f:*F,n:[]const u8,v:u16)!void{const at=try f.symbol(n);f.poke(at,@truncate(v));f.poke(at+1,@truncate(v>>8));}
var max_call:u64=0;var max_runtime:u64=0;var max_cpu:u64=0;var max_bootstrap:u64=0;
fn call(f:*F,n:[]const u8,budget:u64)!void{const before=c.dos64_get_regs(f.machine).cycles;const result=try f.call(n,budget);max_call=@max(max_call,result.cycles-before);if(std.mem.eql(u8,n,"hdb_runtime") or std.mem.eql(u8,n,"dos64_native_tick"))max_runtime=@max(max_runtime,result.cycles-before);if(std.mem.eql(u8,n,"dos64_cpu_step"))max_cpu=@max(max_cpu,result.cycles-before);if(std.mem.eql(u8,n,"dos64_overlay_bootstrap"))max_bootstrap=@max(max_bootstrap,result.cycles-before);if(result.p&1!=0){std.debug.print("native carry {s}: hdb_active={d} status={x} error={d} guest={x:0>4}:{x:0>4}\n",.{n,try g(f,"hdb_active"),try g(f,"hdb_status"),try g(f,"hdb_error"),f.word((try f.symbol("dos64_guest"))+18),f.word((try f.symbol("dos64_guest"))+24)});return error.NativeCarry;}}
fn reg(f:*F,offset:u16,v:u16)!void{const at=(try f.symbol("dos64_guest"))+offset;f.poke(at,@truncate(v));f.poke(at+1,@truncate(v>>8));}
fn r(f:*F,offset:u16)!u16{return f.word((try f.symbol("dos64_guest"))+offset);}
fn setAddress(f:*F,physical:u32)!void{const at=try f.symbol("dos64_address");for(0..3)|i|f.poke(at+@as(u16,@intCast(i)),@truncate(physical>>@as(u5,@intCast(i*8))));}
fn guestPut(f:*F,physical:u32,data:[]const u8)!void{for(data,0..)|b,i|{try setAddress(f,physical+@as(u32,@intCast(i)));try p(f,"dos64_mem_value",b);try call(f,"dos64_mem_write",100_000);}}
fn guestGet(f:*F,physical:u32,out:[]u8)!void{for(out,0..)|*b,i|{try setAddress(f,physical+@as(u32,@intCast(i)));try call(f,"dos64_mem_read",100_000);b.*=f.last_regs.?.a;}}
fn file(f:*F)!void{try call(f,"dos64_overlay_files_start",100_000);for(0..2000)|_|{if(try g(f,"dos64_files_state")!=1)break;try w(f,"dos64_files_now",f.word(try f.symbol("dos64_files_now"))+%1);try call(f,"dos64_overlay_files_poll",100_000);}try std.testing.expectEqual(@as(u8,2),try g(f,"dos64_files_state"));}
fn setup(image:[]const u8,profile:u8,readonly:u8)!F{
 var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);
 for(0xfe00..0x10000)|i|f.poke(@intCast(i),@truncate(i^0xa5));
 try call(&f,"dos64_overlay_init",10000);try p(&f,"dos64_overlay_reu_mib",4);try call(&f,"dos64_overlay_bootstrap",300_000);
 try std.testing.expectEqual(@as(u8,0xa5),try g(&f,"hdb_extension_ready"));for(0..3584)|i|try std.testing.expectEqual(f.peek(@intCast(0xa000+i)),f.peek(@intCast(0xf000+i)));
 for(0xfe00..0x10000)|i|try std.testing.expectEqual(@as(u8,@truncate(i^0xa5)),f.peek(@intCast(i)));
 try call(&f,"dos64_cpu_init",100_000);try p(&f,"dos64_cache_limit",32);try call(&f,"dos64_cache_init",100_000);try call(&f,"dos64_disk_init",10000);try call(&f,"dos64_bios_init",40_000_000);
 m.dos64_uci_model_enable(f.machine,0xdf1c,1,0xc9);m.hd_model_source(f.machine,image.ptr,image.len);try call(&f,"dos64_uci_init",10000);try w(&f,"dos64_uci_timeout",4000);try call(&f,"dos64_overlay_files_init",10000);
 try p(&f,"dos64_files_op",2);try p(&f,"dos64_files_mode",if(readonly==1)1 else 3);try p(&f,"dos64_files_path_len",7);const cmd=try f.symbol("dos64_uci_command");for("HD.IMG\x00",3..)|b,i|f.poke(cmd+@as(u16,@intCast(i)),b);try file(&f);
 try p(&f,"hd_profile",profile);try p(&f,"hd_slots",2);try p(&f,"hd_readonly",readonly);try call(&f,"hdb_mount",100_000);return f;
}
fn patterned(length:usize)![]u8{const b=try a.alloc(u8,length);for(b,0..)|*v,i|v.*=@truncate(i*37^(i>>17));return b;}
fn tick(f:*F)!void{try w(f,"dos64_elapsed_now",f.word(try f.symbol("dos64_elapsed_now"))+%1);try call(f,"hdb_runtime",1_000_000);try call(f,"dos64_cpu_step",5_000_000);}
fn interrupt(f:*F,ax:u16,cx:u16,dx:u16,bx:u16,es:u16)!void{
 try guestPut(f,0x600,&.{0xcd,0x13,0x90,0x90});try reg(f,0,ax);try reg(f,2,cx);try reg(f,4,dx);try reg(f,6,bx);try reg(f,8,0x1000);try reg(f,16,es);try reg(f,18,0);try reg(f,20,0x3000);try reg(f,24,0x600);try reg(f,26,0xf202);
}
fn finish(f:*F)!void{for(0..20000)|_|{if(try r(f,18)==0 and try r(f,24)==0x602)return;try tick(f);}return error.GuestInterruptBudget;}

test "HD integration owns copied extension and normal INT13 retries preserve registers and frame"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();
 try interrupt(&f,0x0202,0x003f,0x0080,0x2000,0x1000); // invalid sector63 before any file access
 const cmds=m.hd_model_commands(f.machine);try finish(&f);try std.testing.expectEqual(@as(u16,0x0400),try r(&f,0));try std.testing.expectEqual(@as(u16,1),(try r(&f,26))&1);try std.testing.expectEqual(cmds,m.hd_model_commands(f.machine));
 try interrupt(&f,0x0202,0x000f,0x0080,0x2000,0x1000);try tick(&f);try tick(&f);
 try std.testing.expectEqual(@as(u8,1),try g(&f,"hdb_active"));try std.testing.expectEqual(@as(u16,0x100),try r(&f,24));
 var snapshot:[28]u8=undefined;const ga=try f.symbol("dos64_guest");for(&snapshot,0..)|*v,i|v.*=f.peek(ga+@as(u16,@intCast(i)));
 var frame:[6]u8=undefined;try guestGet(&f,0x30ffa,&frame);
 for(0..20)|_|{try tick(&f);for(snapshot,0..)|v,i|try std.testing.expectEqual(v,f.peek(ga+@as(u16,@intCast(i))));var now:[6]u8=undefined;try guestGet(&f,0x30ffa,&now);try std.testing.expectEqualSlices(u8,&frame,&now);}
 try finish(&f);try std.testing.expectEqual(@as(u16,2),try r(&f,0));try std.testing.expectEqual(@as(u16,0),(try r(&f,26))&1);try std.testing.expectEqual(@as(u16,0x1000),try r(&f,8));
 var got:[1024]u8=undefined;try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[14*512..][0..1024],&got);
}
test "HD integration parameters type readonly and physical DMA and image bounds"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,1);defer f.deinit();
 try interrupt(&f,0x0800,0,0x80,0,0);try finish(&f);try std.testing.expectEqual(@as(u16,0x7f10),try r(&f,2));try std.testing.expectEqual(@as(u16,0x0101),try r(&f,4));
 try interrupt(&f,0x1500,0,0x80,0,0);try finish(&f);try std.testing.expectEqual(@as(u16,0x0300),try r(&f,0));try std.testing.expectEqual(@as(u16,0x1000),try r(&f,4));try std.testing.expectEqual(@as(u16,0),(try r(&f,26))&1);
 for([_]struct{ax:u16,cx:u16,dx:u16,bx:u16,status:u16}{.{.ax=0x0301,.cx=1,.dx=0x80,.bx=0,.status=3},.{.ax=0x0201,.cx=1,.dx=0x80,.bx=0xff00,.status=9},.{.ax=0x0202,.cx=0x7f10,.dx=0x0180,.bx=0,.status=4},.{.ax=0x0200,.cx=1,.dx=0x80,.bx=0,.status=4}})|v|{const commands=m.hd_model_commands(f.machine);try interrupt(&f,v.ax,v.cx,v.dx,v.bx,0);try finish(&f);try std.testing.expectEqual(v.status<<8,try r(&f,0));try std.testing.expectEqual(@as(u16,1),(try r(&f,26))&1);try std.testing.expectEqual(commands,m.hd_model_commands(f.machine));}
}
test "HD mutable INT13 vector replacement executes guest handler with no native backend call"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();try guestPut(&f,0x4c,&.{0x00,0x07,0x00,0x00});try guestPut(&f,0x700,&.{0xb4,0x55,0xcf});const commands=m.hd_model_commands(f.machine);try interrupt(&f,0x0201,1,0x80,0,0);try finish(&f);try std.testing.expectEqual(@as(u16,0x5501),try r(&f,0));try std.testing.expectEqual(commands,m.hd_model_commands(f.machine));try std.testing.expectEqual(@as(u8,0),try g(&f,"hdb_active"));
}
test "HD20MiB native BIOS transfers crossing16MiB preserve dirty guest authority and verify writes"{
 const image=try patterned(20*1024*1024);defer a.free(image);var f=try setup(image,1,0);defer f.deinit();
 try call(&f,"dos64_cache_flush",1_000_000);try p(&f,"dos64_cache_limit",1);try call(&f,"dos64_cache_init",100_000);
 // cylinder511/head3/sector16 ->LBA32767, then crosses16MiB into cylinder512.
 try interrupt(&f,0x0203,0xff50,0x0380,0x2000,0x1000);try finish(&f);var got:[1536]u8=undefined;try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[0xfffe00..][0..1536],&got);
 var desired:[1024]u8=undefined;for(&desired,0..)|*v,i|v.*=@truncate(i*11+0xa5);try guestPut(&f,0x12000,&desired);
 // Leave dirty guest bytes resident; export must consume coherent bytes rather than stale REU.
 try interrupt(&f,0x0302,0x0081,0x0080,0x2000,0x1000);try finish(&f);try std.testing.expectEqual(@as(u16,2),try r(&f,0));
 for(desired,0..)|v,i|try std.testing.expectEqual(v,m.hd_model_byte(f.machine,0x1000000+@as(u32,@intCast(i))));
 // VERIFY reads backing/cache, does not compare or overwrite the guest buffer.
 try guestPut(&f,0x12000,&.{0x11,0x22,0x33});try interrupt(&f,0x0402,0x0081,0x0080,0x2000,0x1000);try finish(&f);var unchanged:[3]u8=undefined;try guestGet(&f,0x12000,&unchanged);try std.testing.expectEqualSlices(u8,&.{0x11,0x22,0x33},&unchanged);
 try std.testing.expect(m.hd_model_reads_at(f.machine,0x1000000)>0);
}
test "HD partial write returns guest failure while retaining authoritative recovery sector"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();var desired:[512]u8=undefined;for(&desired,0..)|*v,i|v.*=@truncate(i*19+7);try guestPut(&f,0x12000,&desired);
 m.hd_model_faults(f.machine,-1,-1,127);try interrupt(&f,0x0301,1,0x80,0x2000,0x1000);try finish(&f);try std.testing.expectEqual(@as(u16,0x2000),try r(&f,0));try std.testing.expectEqual(@as(u16,1),(try r(&f,26))&1);try std.testing.expectEqual(@as(u8,1),try g(&f,"hd_uncertain"));
 for(desired,0..)|v,i|try std.testing.expectEqual(v,c.dos64_reu_peek(f.machine,0x350000+@as(u32,@intCast(i))));try interrupt(&f,0,0,0x80,0,0);try finish(&f);try std.testing.expectEqual(@as(u16,0x2000),try r(&f,0));
 var status:[1]u8=undefined;try guestGet(&f,0x474,&status);try std.testing.expectEqual(@as(u8,0x20),status[0]);
}
test "HD coherent partial guest-copy fault remains terminal with dirty cache authority and unchanged frame"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();var old:[512]u8=@splat(0x33);try guestPut(&f,0x12000,&old);
 try interrupt(&f,0x0201,1,0x80,0x2000,0x1000);for(0..10000)|_|{if(try g(&f,"hdb_active")==1 and try g(&f,"hd_state")==2)break;try tick(&f);}
 try std.testing.expectEqual(@as(u8,2),try g(&f,"hd_state"));var before:[6]u8=undefined;try guestGet(&f,0x30ffa,&before);
 // Destination page remains resident; first256 coherent bytes commit, then
 // the next range staging DMA fails before its guest bytes are published.
 c.dos64_reu_fail_after(f.machine,2,127);const result=try f.call("hdb_runtime",1_000_000);try std.testing.expectEqual(@as(u8,1),result.p&1);try std.testing.expectEqual(@as(u8,3),try g(&f,"hdb_active"));try std.testing.expectEqual(@as(u8,0),try g(&f,"hdb_completed"));try std.testing.expectEqual(@as(u16,0x0201),try r(&f,0));
 var got:[512]u8=undefined;try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[0..256],got[0..256]);try std.testing.expectEqualSlices(u8,old[256..],got[256..]);var after:[6]u8=undefined;try guestGet(&f,0x30ffa,&after);try std.testing.expectEqualSlices(u8,&before,&after);
 try call(&f,"dos64_cache_flush",1_000_000);for(got,0..)|v,i|try std.testing.expectEqual(v,c.dos64_reu_peek(f.machine,0x12000+@as(u32,@intCast(i))));
}
test "HD native tick schedules FILE progress outside every CPU and overlay lease"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();
 c.dos64_cia_clock_enable(f.machine);c.dos64_cia_clock_step(f.machine,1);c.dos64_native_display_enable(f.machine);
 const hi=@cImport({@cInclude("host_input_model.h");});hi.dos64_host_input_model_enable(@ptrCast(f.machine));try p(&f,"dos64_host_clock_claim",0xa5);try call(&f,"dos64_host_clock_init",10000);c.dos64_cia_clock_seed(f.machine,0xf000,0xffff);try p(&f,"dos64_host_input_claim",0xa5);try call(&f,"dos64_overlay_input_init",100_000);try call(&f,"dos64_cold_release",10000);try call(&f,"dos64_overlay_text_setup",100_000);
 const diag=try f.symbol("dos64_native_diag");for(0..19)|i|f.poke(diag+@as(u16,@intCast(i)),0);f.poke(diag,4);
 try interrupt(&f,0x0201,1,0x80,0x2000,0x1000);
 for(0..20)|_|{try call(&f,"dos64_native_tick",3_000_000);if(try g(&f,"dos64_files_state")==1)break;}
 try std.testing.expectEqual(@as(u8,1),try g(&f,"hdb_active"));f.poke(diag+3,2);try call(&f,"dos64_native_tick",3_000_000);try std.testing.expectEqual(@as(u8,0xe1),f.peek(diag+4));try std.testing.expectEqual(@as(u8,4),f.peek(diag));
 var completed=false;
 for(0..10000)|_|{try call(&f,"dos64_native_tick",3_000_000);try std.testing.expectEqual(@as(u8,0),try g(&f,"dos64_overlay_busy"));if(try g(&f,"hdb_active")==0 and try r(&f,0)==1){completed=true;break;}}
 try std.testing.expect(completed);try std.testing.expectEqual(@as(u8,4),f.peek(diag));var got:[512]u8=undefined;try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[0..512],&got);
}
test "HD PUSHF far call owned BIOS gate restores caller IF through pending retries"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();try interrupt(&f,0x0201,1,0x80,0x2000,0x1000);try guestPut(&f,0x600,&.{0x9c,0x9a,0x00,0x01,0x00,0xf0,0x90});
 var done=false;for(0..20000)|_|{if(try r(&f,18)==0 and try r(&f,24)==0x606){done=true;break;}try tick(&f);if(try g(&f,"hdb_active")==1)try std.testing.expectEqual(@as(u16,0),(try r(&f,26))&0x200);}
 try std.testing.expect(done);try std.testing.expectEqual(@as(u16,0x200),(try r(&f,26))&0x200);try std.testing.expectEqual(@as(u16,0x1000),try r(&f,8));
}
test "HD multi-sector short read publishes only completed guest sectors and permits clean retry"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();const old:[1024]u8=@splat(0x77);try guestPut(&f,0x12000,&old);
 m.hd_model_faults(f.machine,-1,32768,-1); //LBA64, first read of the second extent
 try interrupt(&f,0x0202,0x0110,0x0180,0x2000,0x1000); //C1/H1/S16=LBA63
 try finish(&f);try std.testing.expectEqual(@as(u16,0x2001),try r(&f,0));try std.testing.expectEqual(@as(u16,1),(try r(&f,26))&1);
 var got:[1024]u8=undefined;try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[63*512..][0..512],got[0..512]);try std.testing.expectEqualSlices(u8,old[512..],got[512..]);
 m.hd_model_faults(f.machine,-1,-1,-1);try interrupt(&f,0,0,0x80,0,0);try finish(&f);try std.testing.expectEqual(@as(u16,0),try r(&f,0));try interrupt(&f,0x0202,0x0110,0x0180,0x2000,0x1000);try finish(&f);try guestGet(&f,0x12000,&got);try std.testing.expectEqualSlices(u8,image[63*512..][0..1024],&got);
}

test "HD host shadow has no alias through ordinary guest RAM or synthetic BIOS ROM"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();var extension:[3584]u8=undefined;for(&extension,0..)|*v,i|v.*=f.peek(@intCast(0xf000+i));
 try guestPut(&f,0xf000,&.{0x55,0xaa});try guestPut(&f,0xf0000,&.{0x12,0x34});try p(&f,"dos64_memory_mode",1);try guestPut(&f,0xfe000,&.{0xde,0xad});try p(&f,"dos64_memory_mode",0);try call(&f,"dos64_cache_flush",1_000_000);
 for(extension,0..)|v,i|try std.testing.expectEqual(v,f.peek(@intCast(0xf000+i)));
}
test "HD extension loader refuses ROM banking before changing destination or initialized guard"{
 var f=try F.init();defer f.deinit();f.poke(0xf000,0x55);f.poke(1,0x37);const result=try f.call("hdb_load_extension",10000);try std.testing.expectEqual(@as(u8,1),result.p&1);try std.testing.expectEqual(@as(u8,0x55),f.peek(0xf000));try std.testing.expectEqual(@as(u8,0),try g(&f,"hdb_extension_ready"));
}
test "HD suspended gate refuses a changed guest context without rewriting its original INT frame"{
 const image=try patterned(2*1024*1024);defer a.free(image);var f=try setup(image,0,0);defer f.deinit();try interrupt(&f,0x0201,1,0x80,0x2000,0x1000);try tick(&f);try tick(&f);var frame:[6]u8=undefined;try guestGet(&f,0x30ffa,&frame);try reg(&f,6,0x3000);const result=try f.call("dos64_cpu_step",100_000);try std.testing.expectEqual(@as(u8,1),result.p&1);try std.testing.expectEqual(@as(u8,3),try g(&f,"hdb_active"));var now:[6]u8=undefined;try guestGet(&f,0x30ffa,&now);try std.testing.expectEqualSlices(u8,&frame,&now);
 std.debug.print("HD bounded calls max={d}, runtime={d}, CPUstep={d}, bootstrap={d}\n",.{max_call,max_runtime,max_cpu,max_bootstrap});
}

test "HD BIOS split256 real dirty guest sector writes survive corruption model at both geometry ends" {
 for([_]u8{0,1})|profile|{
  const length:usize=if(profile==0)2*1024*1024 else 20*1024*1024;const image=try patterned(length);defer a.free(image);var f=try setup(image,profile,0);defer f.deinit();m.hd_model_dma_alias(f.machine,1);
  var desired:[512]u8=undefined;for(&desired,0..)|*v,i|v.*=@truncate((i*23)^(i>>8)^0x6c);try guestPut(&f,0x12000,&desired);
  const last_cx:u16=if(profile==0)0x7f10 else 0x7f90;const last_dx:u16=if(profile==0)0x0180 else 0x0380;
  try interrupt(&f,0x0301,last_cx,last_dx,0x2000,0x1000);try finish(&f);try std.testing.expectEqual(@as(u16,1),try r(&f,0));try std.testing.expectEqual(@as(u16,0),(try r(&f,26))&1);try std.testing.expectEqual(@as(u8,0),try g(&f,"hd_uncertain"));try std.testing.expectEqual(@as(u32,2),m.hd_trace_writes(f.machine));try std.testing.expectEqual(@as(u32,0),m.hd_model_alias_hits(f.machine));
  for(0..2)|half|{try std.testing.expectEqual(@as(u32,256),m.hd_trace_write_field(f.machine,@intCast(half),3));try std.testing.expectEqual(@as(u32,@intCast(length-512+half*256)),m.hd_trace_write_field(f.machine,@intCast(half),0));}
  for(desired,0..)|v,i|try std.testing.expectEqual(v,m.hd_model_byte(f.machine,@intCast(length-512+i)));try std.testing.expectEqual(image[length-513],m.hd_model_byte(f.machine,@intCast(length-513)));
 }
}

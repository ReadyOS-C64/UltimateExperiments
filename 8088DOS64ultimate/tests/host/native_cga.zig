const std=@import("std");
const h=@import("machine.zig");
const F=h.Fixture; const c=h.c;
const im=@cImport({@cInclude("host_input_model.h");@cInclude("graphics_color_model.h");});
const rgb=[_]u8{0,6,5,3,2,4,9,15,12,14,13,3,10,4,7,1};
var snapshot_max:[3]u64=@splat(0); var line_max:u64=0;
fn set(f:*F,n:[]const u8,v:u8)!void{f.poke(try f.symbol(n),v);}
fn call(f:*F,n:[]const u8,budget:u64,carry:u8)!u64{
 const before=c.dos64_get_regs(f.machine).cycles;const r=try f.call(n,budget);
 if(carry!=(r.p&1)) {const d=try f.symbol("dos64_native_diag");const g=try f.symbol("dos64_guest");std.debug.print("{s} unexpected C: stage{x} err{x} detail{x} cpuStatus{x} opcode{x} CS:IP{x}:{x}\n",.{n,f.peek(d),f.peek(d+1),f.peek(d+2),f.peek(try f.symbol("dos64_cpu_status")),f.peek(try f.symbol("dos64_cpu_opcode")),f.word(g+18),f.word(g+24)});}
 try std.testing.expectEqual(carry,r.p&1);return r.cycles-before;
}
fn diag(f:*F,off:u16,v:u8)!void{f.poke((try f.symbol("dos64_native_diag"))+off,v);}
fn fixture(color:bool)!F{
 var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);c.dos64_native_display_enable(f.machine);
 if(color)im.dos64_graphics_color_enable(@ptrCast(f.machine));
 c.dos64_cia_clock_enable(f.machine);im.dos64_host_input_model_enable(@ptrCast(f.machine));
 _=try call(&f,"dos64_overlay_init",10000,0);try set(&f,"dos64_overlay_reu_mib",4);
 _=try call(&f,"dos64_overlay_bootstrap",300_000,0);
 _=try call(&f,"dos64_cpu_init",10000,0);try set(&f,"dos64_cache_limit",32);
 _=try call(&f,"dos64_cache_init",50000,0);_=try call(&f,"dos64_disk_init",10000,0);
 _=try call(&f,"dos64_bios_init",40_000_000,0);
 try set(&f,"dos64_host_clock_claim",0xa5);_=try call(&f,"dos64_host_clock_init",10000,0);
 try set(&f,"dos64_host_input_claim",0xa5);_=try call(&f,"dos64_overlay_input_init",50000,0);
 _=try call(&f,"dos64_cold_release",10000,0);_=try call(&f,"dos64_overlay_text_setup",10000,0);
 for(0..19)|i|try diag(&f,@intCast(i),0);try diag(&f,0,4);try set(&f,"n_present_mode",255);
 return f;
}
fn word(f:*F,a:u16,v:u16)void{f.poke(a,@truncate(v));f.poke(a+1,@truncate(v>>8));}
fn mode(f:*F,v:u8)!void{
 const g=try f.symbol("dos64_guest");word(f,g,v);
 _=try call(f,"dos64_video_service",30_000_000,0);
}
fn write(f:*F,address:u32,value:u8)!void{
 const a=try f.symbol("dos64_address");f.poke(a,@truncate(address));f.poke(a+1,@truncate(address>>8));f.poke(a+2,@truncate(address>>16));
 try set(f,"dos64_mem_value",value);_=try call(f,"dos64_mem_write",50000,0);
}
fn pause(f:*F)!u64{
 try diag(f,3,2);const t=try call(f,"dos64_native_tick",15_000_000,0);
 const d=try f.symbol("dos64_native_diag");try std.testing.expectEqual(@as(u8,5),f.peek(d));try std.testing.expectEqual(@as(u8,0xa5),f.peek(d+4));
 try std.testing.expectEqual(@as(u8,0),f.peek(d+3));return t;
}
fn palette(mode_:u8,color:u8)[4]u8{
 if(mode_==6)return .{0,rgb[color&15],0,0};
 const intense:u8=if(color&16!=0)8 else 0;
 const p:[3]u8=if(mode_==5).{3,4,7} else if(color&32!=0).{3,5,7} else .{2,4,6};
 return .{rgb[color&15],rgb[p[0]+intense],rgb[p[1]+intense],rgb[p[2]+intense]};
}
fn pattern(i:usize)u8{return @truncate((i*73)^(i>>4)^0xa5);}
fn expected(v:[]const u8,mode_:u8,y:usize,cell:usize)u8{
 const source=(y/2)*80+(y%2)*8192;var result:u8=0;
 const pixels:usize=if(mode_==6)8 else 4;
 for(0..pixels)|pixel|{
 const x=cell*pixels*2+pixel*2;
 if(mode_==6){const left=(v[source+x/8]>>@as(u3,@intCast(7-x%8)))&1;const right=(v[source+(x+1)/8]>>@as(u3,@intCast(7-(x+1)%8)))&1;result=(result<<1)|(left|right);}
 else {const left=(v[source+x/4]>>@as(u3,@intCast(6-2*(x%4))))&3;const right=(v[source+(x+1)/4]>>@as(u3,@intCast(6-2*((x+1)%4))))&3;result=(result<<2)|(if(left!=0)left else right);}
 }return result;
}
fn verify(f:*F,mode_:u8,color:u8,v:[]const u8)!void{
 const pal=palette(mode_,color);
 for(0..200)|y|for(0..40)|cell|try std.testing.expectEqual(expected(v,mode_,y,cell),f.peek(@intCast(0x6000+(y/8)*320+cell*8+y%8)));
 for(0..1000)|i|{
 try std.testing.expectEqual(if(mode_==6)pal[1]<<4 else(pal[1]<<4)|pal[2],f.peek(@intCast(0x4000+i)));
 if(mode_!=6)try std.testing.expectEqual(pal[3],im.dos64_graphics_color_peek(@ptrCast(f.machine),@intCast(0xd800+i)));
 }
 try std.testing.expectEqual(pal[0],c.dos64_native_display_reg(f.machine,5));
 try std.testing.expectEqual(@as(u8,if(mode_==6)0xc8 else 0xd8),c.dos64_native_display_reg(f.machine,1));
 try std.testing.expectEqual(@as(u8,0x3b),c.dos64_native_display_reg(f.machine,0));
 try std.testing.expectEqual(@as(u8,8),c.dos64_native_display_reg(f.machine,2));
 try std.testing.expectEqual(@as(u8,2),c.dos64_native_display_reg(f.machine,6)&3);
 try std.testing.expectEqual(@as(u8,3),c.dos64_native_display_reg(f.machine,7)&3);
}
test "real BIOS graphics modes dirty guest bytes snapshot full frame exact and immutable source"{
 var f=try fixture(true);defer f.deinit();var v:[16384]u8=undefined;
 for(4..7)|m|{
 try mode(&f,@intCast(m));_=try call(&f,"dos64_cache_flush",1_000_000,0);
 for(&v,0..)|*b,i|{b.*=pattern(i);c.dos64_reu_poke(f.machine,0xb8000+@as(u32,@intCast(i)),b.*);}
 _=try call(&f,"dos64_cache_init",50000,0);
 const color:u8=if(m==6)0x0e else if(m==5)0x19 else 0x2b;
 try write(&f,0x466,color);v[0]^=0xff;try write(&f,0xb8000,v[0]);
 try std.testing.expect(v[0]!=c.dos64_reu_peek(f.machine,0xb8000));
 var fonts:[3072]u8=undefined;for(&fonts,0..)|*b,i|b.*=f.peek(@intCast(0x4400+i));f.poke(0x43ff,0x51);f.poke(0x7fff,0x72);
 snapshot_max[m-4]=try pause(&f);try verify(&f,@intCast(m),color,&v);
 try std.testing.expectEqual(@as(u32,0xffffffff),c.dos64_reu_compare(f.machine,0xb8000,&v,v.len));
 for(fonts,0..)|b,i|try std.testing.expectEqual(b,f.peek(@intCast(0x4400+i)));
 try std.testing.expectEqual(@as(u8,0x51),f.peek(0x43ff));try std.testing.expectEqual(@as(u8,0x72),f.peek(0x7fff));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_overlay_busy")));
 }
 std.debug.print("native CGA full snapshot CPU cycles modes4/5/6={any}, budget15000000; excludes DMA stalls and real elapsed\n",.{snapshot_max});
}
test "native switches graphics to both text widths and back through coherent BDA"{
 var f=try fixture(true);defer f.deinit();const saved=c.dos64_native_display_reg(f.machine,6);
 for([_]u8{4,3,6,0,5,2,4,1})|m|{
 try mode(&f,m);_=try pause(&f);
 try std.testing.expectEqual(@as(u8,if(m>=4 and m<6)0xd8 else 0xc8),c.dos64_native_display_reg(f.machine,1));
 try std.testing.expectEqual(m,f.peek(try f.symbol("n_present_mode")));
 try std.testing.expectEqual(@as(u8,0),f.peek((try f.symbol("dos64_native_diag"))+9));
 }
 _=try call(&f,"dos64_overlay_text_restore",10000,0);
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_native_text_state")));
 try std.testing.expect(saved!=c.dos64_native_display_reg(f.machine,6));
}
test "guest executed INT10 mode set and guest MOV VRAM reaches scheduled graphics line"{
 var f=try fixture(true);defer f.deinit();const g=try f.symbol("dos64_guest");
 const code=[_]u8{0xb8,4,0,0xcd,0x10,0xb8,0x00,0xb8,0x8e,0xd8,0xc6,0x06,0,0,0xf1,0xf4};
 for(code,0..)|b,i|c.dos64_reu_poke(f.machine,0x1000+@as(u32,@intCast(i)),b);
 word(&f,g+18,0);word(&f,g+24,0x1000);word(&f,g+8,0x100);word(&f,g+20,0x2000);
 for(0..10)|_|_=try call(&f,"dos64_cpu_step",30_000_000,0);
 c.dos64_cia_clock_step(f.machine,0);c.dos64_cia_clock_seed(f.machine,0xbeff,0xffff);
 try diag(&f,0,4);try diag(&f,10,0);try diag(&f,11,0);
 line_max=try call(&f,"dos64_native_tick",3_000_000,0);
 try std.testing.expectEqual(@as(u8,4),f.peek(try f.symbol("n_present_mode")));
 try std.testing.expectEqual(@as(u8,8),f.peek((try f.symbol("dos64_native_diag"))+9));
 try std.testing.expectEqual(@as(u8,0xd0),f.peek(0x6000));
 std.debug.print("native input+8GFX lines+16CPU calls cycles={d}/3000000\n",.{line_max});
}
test "graphics snapshot faults remain unacknowledged and paused only after full successful frame"{
 for([_]u32{0,1,2,3})|skip|{
 var f=try fixture(true);defer f.deinit();try mode(&f,4);_=try call(&f,"dos64_cache_flush",1_000_000,0);
 _=try call(&f,"dos64_cache_init",50000,0);c.dos64_reu_fail_after(f.machine,skip,17);
 try diag(&f,3,2);_=try call(&f,"dos64_native_tick",15_000_000,1);
 const d=try f.symbol("dos64_native_diag");try std.testing.expectEqual(@as(u8,0xe1),f.peek(d));try std.testing.expectEqual(@as(u8,9),f.peek(d+1));
 try std.testing.expectEqual(@as(u8,0xe1),f.peek(d+4));try std.testing.expectEqual(@as(u8,0),f.peek(d+3));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_overlay_busy")));
 }
}
test "unsupported video mode rejected and color RAM mock remains explicit default off"{
 var f=try fixture(true);defer f.deinit();try write(&f,0x449,7);try diag(&f,3,2);_=try call(&f,"dos64_native_tick",1_000_000,1);
 try std.testing.expectEqual(@as(u8,1),f.peek((try f.symbol("dos64_native_diag"))+2));
 var off=try fixture(false);defer off.deinit();try mode(&off,4);try diag(&off,3,2);
 try std.testing.expectError(error.UnsupportedDevice,off.call("dos64_native_tick",15_000_000));
}
test "presentation restores bank and native flags and touches no clock timer register"{
 var f=try fixture(true);defer f.deinit();try mode(&f,5);
 const timers=[_]u8{4,5,6,7,13,14,15};var before:[7]u32=undefined;for(timers,0..)|r,i|before[i]=c.dos64_cia_clock_writes(f.machine,r);
 for(0..256)|p|{
 f.initial_status=@intCast(p);f.poke(try f.symbol("dos64_render_graphics_request"),17);
 const regs=try f.call("dos64_overlay_present_graphics_line",500_000);try std.testing.expectEqual(@as(u8,0),regs.p&1);
 try std.testing.expectEqual(@as(u8,@intCast(p))&0xce,regs.p&0xce);
 try std.testing.expectEqual(@as(u8,0x2f),f.peek(0));try std.testing.expectEqual(@as(u8,0x35)&0x2f,f.peek(1)&0x2f);
 }
 for(timers,0..)|r,i|try std.testing.expectEqual(before[i],c.dos64_cia_clock_writes(f.machine,r));
}

test "direct GFX facade banks before owner state and preserves all driven mapping bits"{
 var f=try fixture(true);defer f.deinit();try mode(&f,4);
 try set(&f,"dos64_overlay_requested",5);_=try call(&f,"dos64_overlay_acquire",10000,0);_=try call(&f,"dos64_overlay_release",10000,0);
 for([_]u8{0,7,0x2f,0xff})|ddr|for([_]u8{0x30,0x35,0x37})|port|{
 f.poke(0,ddr);f.poke(1,port);f.initial_status=0xec;try set(&f,"dos64_render_graphics_request",197);
 const r=try f.call("dos64_present_graphics_line",500_000);
 try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u8,0xcc),r.p&0xce);
 try std.testing.expectEqual(ddr,f.peek(0));try std.testing.expectEqual(port&ddr,f.peek(1)&ddr);
 };
}
test "native rejects nonzero graphics page and start without publishing VIC changes"{
 for([_]u32{0x462,0x44e,0x44f})|at|{
 var f=try fixture(true);defer f.deinit();try mode(&f,4);try write(&f,at,1);
 var old:[8]u8=undefined;for(&old,0..)|*b,i|b.*=c.dos64_native_display_reg(f.machine,@intCast(i));
 try diag(&f,3,2);_=try call(&f,"dos64_native_tick",1_000_000,1);
 for(old,0..)|b,i|try std.testing.expectEqual(b,c.dos64_native_display_reg(f.machine,@intCast(i)));
 }
}

test { _ = @import("render_graphics.zig"); }

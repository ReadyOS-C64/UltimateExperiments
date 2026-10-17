const std=@import("std");
const h=@import("machine.zig");const F=h.Fixture;const c=h.c;
fn w(f:*F,a:u16,v:u16)void{f.poke(a,@truncate(v));f.poke(a+%1,@truncate(v>>8));}
fn reg(f:*F,n:u16,v:u16)!void{w(f,(try f.symbol("dos64_guest"))+n*2,v);}
fn get(f:*F,n:u16)!u16{return f.word((try f.symbol("dos64_guest"))+n*2);}
fn rw(f:*F,a:u32,v:u16)void{c.dos64_reu_poke(f.machine,a,@truncate(v));c.dos64_reu_poke(f.machine,a+1,@truncate(v>>8));}
fn memword(f:*F,a:u32)!u16{_=try f.call("dos64_cache_flush",100000);return @as(u16,c.dos64_reu_peek(f.machine,a))|(@as(u16,c.dos64_reu_peek(f.machine,a+1))<<8);}
fn count(f:*F)!u16{return f.word(try f.symbol("dos64_cpu_instructions"));}
fn init(code:[]const u8,flags:u16)!F{
 var f=try F.init();errdefer f.deinit();if(!f.symbols.contains("dos64_trap_state"))return error.SkipZigTest;
 c.dos64_enable_reu(f.machine);f.poke(try f.symbol("dos64_cache_limit"),2);_=try f.call("dos64_cache_init",50000);f.poke(try f.symbol("dos64_memory_mode"),1);_=try f.call("dos64_cpu_init",10000);
 try reg(&f,9,0x1000);try reg(&f,12,0x100);try reg(&f,10,0x2000);try reg(&f,4,0x800);try reg(&f,13,flags);
 for(code,0..)|v,i|c.dos64_reu_poke(f.machine,0x10100+@as(u32,@intCast(i)),v);
 rw(&f,4,0x200);rw(&f,6,0x3000);rw(&f,12,0x300);rw(&f,14,0x4000);c.dos64_reu_poke(f.machine,0x30200,0xcf);c.dos64_reu_poke(f.machine,0x40300,0xcf);return f;
}
fn step(f:*F)!void{const r=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expect(f.peek(try f.symbol("dos64_cpu_status"))<2);}
fn loc(f:*F,cs:u16,ip:u16)!void{try std.testing.expectEqual(cs,try get(f,9));try std.testing.expectEqual(ip,try get(f,12));}
fn trap(f:*F,ip:u16,n:u16)!void{try step(f);try loc(f,0x3000,0x200);try std.testing.expectEqual(n,try count(f));try std.testing.expectEqual(ip,try memword(f,0x20000+@as(u32,try get(f,4))));try std.testing.expectEqual(@as(u16,0),try get(f,13)&0x300);}

test "type1 follows completed NOP and preserves exact normalized frame without extra retirement"{
 var f=try init(&.{0x90,0x40},0xf3ff);defer f.deinit();try reg(&f,0,7);try step(&f);try loc(&f,0x1000,0x101);try trap(&f,0x101,1);try std.testing.expectEqual(@as(u16,7),try get(&f,0));try std.testing.expectEqual(@as(u16,0x1000),try memword(&f,0x207fc));try std.testing.expectEqual(@as(u16,0xf3d7),try memword(&f,0x207fe));
 try step(&f);try loc(&f,0x1000,0x101);try step(&f);try loc(&f,0x1000,0x102);try std.testing.expectEqual(@as(u16,8),try get(&f,0));try trap(&f,0x102,3);
}
test "TF zero has no type1 and HLT stays halted"{var f=try init(&.{0x90,0xf4},0xf202);defer f.deinit();try step(&f);try step(&f);try step(&f);try loc(&f,0x1000,0x102);try std.testing.expectEqual(@as(u16,2),try count(&f));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));}
test "POPF enable waits through one following instruction and disable still traps once"{
 for([_]u16{0xf002,0xf102})|old|{var f=try init(&.{0x9d,0x40,0x40},old);defer f.deinit();rw(&f,0x20800,old^0x100);try step(&f);try loc(&f,0x1000,0x101);
 if(old&0x100==0){try step(&f);try loc(&f,0x1000,0x102);try std.testing.expectEqual(@as(u16,1),try get(&f,0));try trap(&f,0x102,2);}else{try trap(&f,0x101,1);try step(&f);try step(&f);try step(&f);try loc(&f,0x1000,0x103);try std.testing.expectEqual(@as(u16,2),try get(&f,0));}}
}
test "IRET newly restored TF traces following opcode not IRET itself"{
 var f=try init(&.{0xcf},0xf002);defer f.deinit();rw(&f,0x20800,0x500);rw(&f,0x20802,0x5000);rw(&f,0x20804,0xf302);c.dos64_reu_poke(f.machine,0x50500,0x40);try step(&f);try loc(&f,0x5000,0x500);try step(&f);try loc(&f,0x5000,0x501);try trap(&f,0x501,2);
}
test "single step enters software INT3 vector then nests type1 before handler opcode"{
 var f=try init(&.{0xcc},0xf302);defer f.deinit();try step(&f);try loc(&f,0x4000,0x300);try std.testing.expectEqual(@as(u16,0x7fa),try get(&f,4));try trap(&f,0x300,1);try std.testing.expectEqual(@as(u16,0x4000),try memword(&f,0x207f6));try std.testing.expectEqual(@as(u16,0xf002),try memword(&f,0x207f8));try std.testing.expectEqual(@as(u16,0x101),try memword(&f,0x207fa));try step(&f);try loc(&f,0x4000,0x300);try step(&f);try loc(&f,0x1000,0x101);
}
test "HLT under TF wakes into type1 with post HLT return IP"{var f=try init(&.{0xf4},0xf102);defer f.deinit();try step(&f);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_status")));try trap(&f,0x101,1);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_status")));}
test "original8088 MOV segment suppresses own trap including non SS while STI does not"{
 for([_]u8{0xc0,0xd0,0xd8})|modrm|{var f=try init(&.{0x8e,modrm,0x40},0xf102);defer f.deinit();try reg(&f,0,0x2000);try step(&f);try step(&f);try loc(&f,0x1000,0x103);try std.testing.expectEqual(@as(u16,0x2001),try get(&f,0));try trap(&f,0x103,2);}
 var f=try init(&.{0xfb,0x40},0xf102);defer f.deinit();try step(&f);try trap(&f,0x101,1);try std.testing.expectEqual(@as(u16,0),try get(&f,0));
}
test "original8088 POP segment suppresses own type1 with following opcode single stepped"{
 for([_]u8{0x07,0x17,0x1f})|op|{var f=try init(&.{op,0x40},0xf102);defer f.deinit();rw(&f,0x20800,0x2000);try step(&f);try step(&f);try loc(&f,0x1000,0x102);try std.testing.expectEqual(@as(u16,1),try get(&f,0));try trap(&f,0x102,2);}
}
test "prefix slice yield retains TF without an intermediate trap"{
 var code:[67]u8=undefined;@memset(code[0..65],0x26);code[65]=0x40;code[66]=0xf4;var f=try init(&code,0xf102);defer f.deinit();try step(&f);try std.testing.expectEqual(@as(u16,0),try count(&f));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_pending")));try step(&f);try loc(&f,0x1000,0x142);try trap(&f,0x142,1);
}
test "REP type1 interrupts after one MOVSB including final CX zero and follows original restart loss"{
 for([_]u16{0,1,3})|cx|{var f=try init(&.{0x26,0xf3,0xa4,0x90},0xf102);defer f.deinit();try reg(&f,1,cx);try reg(&f,8,0x6000);try reg(&f,11,0x5000);c.dos64_reu_poke(f.machine,0x60000,0x5a);try step(&f);
 if(cx==0){try loc(&f,0x1000,0x103);try trap(&f,0x103,1);}else{try std.testing.expectEqual(cx-1,try get(&f,1));try std.testing.expectEqual(@as(u16,1),try get(&f,6));try std.testing.expectEqual(@as(u16,1),try get(&f,7));try trap(&f,0x101,0);try std.testing.expectEqual(@as(u8,0x5a),c.dos64_reu_peek(f.machine,0x60000));}}
}
test "WAIT pending traces its test cycle without completing WAIT"{var f=try init(&.{0x9b},0xf102);defer f.deinit();try step(&f);try loc(&f,0x1000,0x100);try trap(&f,0x100,0);}
test "failed type1 IVT fetch is terminal and retains already completed IP"{
 var f=try init(&.{0x90,0x40},0xf102);defer f.deinit();try step(&f);c.dos64_reu_fail_after(f.machine,0,16);const r=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,3),f.peek(try f.symbol("dos64_cpu_status")));try loc(&f,0x1000,0x101);try std.testing.expectEqual(@as(u16,1),try count(&f));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_trap_state")));const again=try f.call("dos64_cpu_step",1000);try std.testing.expectEqual(@as(u8,1),again.p&1);try loc(&f,0x1000,0x101);
}
test "native cold copy installs trap helper exactly before cache and preserves vector page"{
 var f=try F.init();defer f.deinit();const countbytes=f.symbols.get("__CPUTRAP_SIZE__") orelse return error.SkipZigTest;var code:[256]u8=undefined;for(&code,0..)|*v,i|v.*=f.peek(0xae00+@as(u16,@intCast(i)));for(0..256)|i|{f.poke(0xfe00+@as(u16,@intCast(i)),0x5a);f.poke(0xff00+@as(u16,@intCast(i)),0xa6);}f.poke(0,7);f.poke(1,0x35);f.poke(try f.symbol("dos64_cold_open"),0xa5);const r=try f.call("hdb_load_extension",300000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u8,0xa5),f.peek(try f.symbol("hdb_extension_ready")));for(code,0..)|v,i|{try std.testing.expectEqual(v,f.peek(0xfe00+@as(u16,@intCast(i))));try std.testing.expectEqual(@as(u8,0xa6),f.peek(0xff00+@as(u16,@intCast(i))));}try std.testing.expect(countbytes<=256);
}
const ih=@import("machine_irq_pit.zig");
fn iw(f:*ih.Fixture,a:u16,v:u16)void{f.poke(a,@truncate(v));f.poke(a+%1,@truncate(v>>8));}
fn irqword(f:*ih.Fixture,a:u32,v:u16)void{ih.c.dos64_reu_poke(f.machine,a,@truncate(v));ih.c.dos64_reu_poke(f.machine,a+1,@truncate(v>>8));}
test "INTR wins type1 priority and trap precedes ISR opcode including freshly enabled TF"{
 for(0..4)|scenario|{const retired=scenario>0;var f=try ih.Fixture.init();defer f.deinit();if(!f.symbols.contains("dos64_trap_state"))return error.SkipZigTest;f.poke(try f.symbol("dos64_cache_limit"),2);_=try f.call("dos64_cache_init",100000);_=try f.call("dos64_cpu_init",100000);_=try f.call("dos64_io_init",100000);const g=try f.symbol("dos64_guest");iw(&f,g+18,0x1000);iw(&f,g+24,0x100);iw(&f,g+20,0x2000);iw(&f,g+8,0x800);iw(&f,g+26,if(scenario==2)0xf202 else 0xf302);f.poke(try f.symbol("dos64_pic_imr"),0);f.poke(try f.symbol("dos64_irq_callback_enabled"),0);irqword(&f,4,0x200);irqword(&f,6,0x3000);irqword(&f,0x20,0x300);irqword(&f,0x22,0x4000);ih.c.dos64_reu_poke(f.machine,0x10100,if(scenario>=2)0x9d else 0x90);irqword(&f,0x20800,if(scenario==3)0xf202 else 0xf302);ih.c.dos64_reu_poke(f.machine,0x40300,0x40);
 if(retired){const r=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);}f.poke(try f.symbol("dos64_irq_line"),0);_=try f.call("dos64_irq_pulse",100000);_=try f.call("dos64_irq_try",100000);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_irq_result")));try std.testing.expectEqual(@as(u16,0x4000),f.word(g+18));try std.testing.expectEqual(@as(u16,0x300),f.word(g+24));const t=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,0),t.p&1);try std.testing.expectEqual(@as(u16,0x3000),f.word(g+18));try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u16,0),f.word(g));try std.testing.expectEqual(@as(u16,@intFromBool(retired)),f.word(try f.symbol("dos64_cpu_instructions")));try std.testing.expectEqual(@as(u16,if(scenario>=2)0x7f6 else 0x7f4),f.word(g+8));
 }
}
test "type1 entry failure after IVT and partial stack keeps post instruction IP and never retries"{
 for([_]u32{1,2,3})|packets|{var f=try init(&.{0x90},0xf102);defer f.deinit();f.poke(try f.symbol("dos64_cache_limit"),1);try reg(&f,4,0x202);try step(&f);c.dos64_reu_fail_after(f.machine,packets,16);const r=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,3),f.peek(try f.symbol("dos64_cpu_status")));try loc(&f,0x1000,0x101);try std.testing.expectEqual(@as(u16,1),try count(&f));const sp=try get(&f,4);const again=try f.call("dos64_cpu_step",1000);try std.testing.expectEqual(@as(u8,1),again.p&1);try std.testing.expectEqual(sp,try get(&f,4));}
}
test "type1 boundary preserves all256 native caller status combinations"{
 for(0..256)|p|{var f=try init(&.{0x90},0xf302);defer f.deinit();f.initial_status=@intCast(p);for(0..2)|_|{const r=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);}try loc(&f,0x3000,0x200);try std.testing.expectEqual(@as(u16,1),try count(&f));}
}
test "REP accepted INTR precedes type1 after exactly one completed element"{
 var f=try ih.Fixture.init();defer f.deinit();if(!f.symbols.contains("dos64_trap_state"))return error.SkipZigTest;f.poke(try f.symbol("dos64_cache_limit"),2);_=try f.call("dos64_cache_init",100000);_=try f.call("dos64_cpu_init",100000);_=try f.call("dos64_io_init",100000);const g=try f.symbol("dos64_guest");iw(&f,g+18,0x1000);iw(&f,g+24,0x100);iw(&f,g+20,0x2000);iw(&f,g+8,0x800);iw(&f,g+26,0xf302);iw(&f,g+2,3);iw(&f,g+16,0x5000);iw(&f,g+22,0x6000);f.poke(try f.symbol("dos64_pic_imr"),0);f.poke(try f.symbol("dos64_irq_callback_enabled"),1);f.poke(try f.symbol("dos64_pit_poll_enabled"),0);irqword(&f,4,0x200);irqword(&f,6,0x3000);irqword(&f,0x20,0x300);irqword(&f,0x22,0x4000);ih.c.dos64_reu_poke(f.machine,0x10100,0xf3);ih.c.dos64_reu_poke(f.machine,0x10101,0xa4);ih.c.dos64_reu_poke(f.machine,0x60000,0x5a);f.poke(try f.symbol("dos64_irq_line"),0);_=try f.call("dos64_irq_pulse",100000);
 const r=try f.call("dos64_cpu_step",500000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u16,0x4000),f.word(g+18));try std.testing.expectEqual(@as(u16,0x300),f.word(g+24));try std.testing.expectEqual(@as(u16,2),f.word(g+2));try std.testing.expectEqual(@as(u16,1),f.word(g+12));try std.testing.expectEqual(@as(u16,1),f.word(g+14));const t=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,0),t.p&1);try std.testing.expectEqual(@as(u16,0x3000),f.word(g+18));try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));_=try f.call("dos64_cache_flush",100000);try std.testing.expectEqual(@as(u8,0x5a),ih.c.dos64_reu_peek(f.machine,0x50000));try std.testing.expectEqual(@as(u8,0),ih.c.dos64_reu_peek(f.machine,0x50001));try std.testing.expectEqual(@as(u8,0),ih.c.dos64_reu_peek(f.machine,0x207fa));try std.testing.expectEqual(@as(u8,1),ih.c.dos64_reu_peek(f.machine,0x207fb));
}
test "original MOV CS suppresses own trace and fetches from the new code segment"{
 var f=try init(&.{0x8e,0xc8},0xf102);defer f.deinit();try reg(&f,0,0x4000);c.dos64_reu_poke(f.machine,0x40102,0x40);try step(&f);try loc(&f,0x4000,0x102);try step(&f);try loc(&f,0x4000,0x103);try std.testing.expectEqual(@as(u16,0x4001),try get(&f,0));try trap(&f,0x103,2);try std.testing.expectEqual(@as(u16,0x4000),try memword(&f,0x207fc));
}

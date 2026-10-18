const std=@import("std");
const host=@import("machine.zig");const F=host.Fixture;const c=host.c;
fn word(f:*F,at:u16,v:u16)void{f.poke(at,@truncate(v));f.poke(at+%1,@truncate(v>>8));}
fn reg(f:*F,n:u16,v:u16)!void{word(f,(try f.symbol("dos64_guest"))+n*2,v);}
fn reset(f:*F)!void{_=try f.call("dos64_cache_init",50000);_=try f.call("dos64_cpu_init",10000);}
fn init(frames:u8)!F{var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);f.poke(try f.symbol("dos64_cache_limit"),frames);f.poke(try f.symbol("dos64_memory_mode"),1);try reset(&f);return f;}
fn program(f:*F,cs:u16,ip:u16,data:[]const u8)!void{try reg(f,9,cs);try reg(f,12,ip);for(data,0..)|v,i|c.dos64_reu_poke(f.machine,(@as(u32,cs)*16+(ip+%@as(u16,@intCast(i))))&0xfffff,v);}
fn snapshot(f:*F)![28]u8{var b:[28]u8=undefined;const g=try f.symbol("dos64_guest");for(&b,0..)|*v,i|v.*=f.peek(g+@as(u16,@intCast(i)));return b;}
fn unchanged(f:*F,b:[28]u8,ip:u16)!void{var want=b;std.mem.writeInt(u16,want[24..26],ip,.little);try std.testing.expectEqualSlices(u8,&want,&try snapshot(f));}
fn step(f:*F)!void{const r=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);}
fn seed(f:*F,flags:u16)!void{const values=[_]u16{0x1234,0x5678,0x9abc,0x0100,0x8200,0x0200,0x0010,0x0030,0x4000,0x0100,0x3000,0x2000,0x0100,flags};for(values,0..)|v,i|try reg(f,@intCast(i),v);}
fn count(f:*F)!u16{return f.word(try f.symbol("dos64_cpu_instructions"));}

test "8088 absent8087 all8 ESC opcodes decode all256 ModRM forms with exact IP registers flags and dummy word"{
 var f=try init(2);defer f.deinit();var cases:usize=0;
 for(0xd8..0xe0)|op|for(0..256)|modrm|{
  try reset(&f);try seed(&f,@truncate((op*257)^(modrm*131)^0xf202));
  const mode=modrm>>6;const rm=modrm&7;var code=[_]u8{@intCast(op),@intCast(modrm),0,0};var len:usize=2;
  const base=[_]u16{0x110,0x130,0x210,0x230,0x10,0x30,0x200,0x100};var off=base[rm];var seg:u16=if(rm==2 or rm==3 or rm==6)0x3000 else 0x2000;
  if(mode==0 and rm==6){code[2]=0xff;code[3]=0x03;len=4;off=0x3ff;seg=0x2000;}
  if(mode==1){code[2]=0xe1;len=3;off-%=31;}
  if(mode==2){code[2]=0xee;code[3]=0xff;len=4;off-%=18;}
  const at=@as(u32,seg)*16+off;c.dos64_reu_poke(f.machine,at,0xa6);c.dos64_reu_poke(f.machine,@as(u32,seg)*16+(off+%1),0x5c);
  try program(&f,0x100,0x100,code[0..len]);const before=try snapshot(&f);try step(&f);try unchanged(&f,before,0x100+@as(u16,@intCast(len)));try std.testing.expectEqual(@as(u16,1),try count(&f));
  if(mode!=3){try std.testing.expectEqual(off,f.word(try f.symbol("dos64_operand_offset")));try std.testing.expectEqual(seg,f.word(try f.symbol("dos64_operand_segment")));try std.testing.expectEqual(@as(u16,0x5ca6),f.word(try f.symbol("dos64_cpu_value")));}
  _=try f.call("dos64_cache_flush",100000);try std.testing.expectEqual(@as(u8,0xa6),c.dos64_reu_peek(f.machine,at));try std.testing.expectEqual(@as(u8,0x5c),c.dos64_reu_peek(f.machine,@as(u32,seg)*16+(off+%1)));cases+=1;
 };
 try std.testing.expectEqual(@as(usize,2048),cases);
}

test "8088 ESC segment overrides offset wrap physical wrap and no FNSTCW memory store"{
 const cases=[_]struct{code:[]const u8,ds:u16,es:u16,off:u16,seg:u16}{
 .{.code=&.{0x26,0xd9,0x3e,0xff,0xff},.ds=0x2000,.es=0x4000,.off=0xffff,.seg=0x4000},
 .{.code=&.{0x26,0x3e,0xdf,0x86,0xff,0xfd},.ds=0xffff,.es=0x4000,.off=0xffff,.seg=0xffff},
 .{.code=&.{0x36,0xdc,0x06,0xff,0xff},.ds=0x2000,.es=0x4000,.off=0xffff,.seg=0x3000}};
 for(cases)|q|{var f=try init(1);defer f.deinit();try seed(&f,0xfad7);try reg(&f,11,q.ds);try reg(&f,8,q.es);const at=(@as(u32,q.seg)*16+q.off)&0xfffff;const next=(@as(u32,q.seg)*16+(q.off+%1))&0xfffff;c.dos64_reu_poke(f.machine,at,0x34);c.dos64_reu_poke(f.machine,next,0x12);try program(&f,0x100,0xfffd,q.code);const before=try snapshot(&f);try step(&f);try unchanged(&f,before,0xfffd+%@as(u16,@intCast(q.code.len)));try std.testing.expectEqual(q.off,f.word(try f.symbol("dos64_operand_offset")));try std.testing.expectEqual(q.seg,f.word(try f.symbol("dos64_operand_segment")));try std.testing.expectEqual(@as(u16,0x1234),f.word(try f.symbol("dos64_cpu_value")));_=try f.call("dos64_cache_flush",100000);try std.testing.expectEqual(@as(u8,0x34),c.dos64_reu_peek(f.machine,at));try std.testing.expectEqual(@as(u8,0x12),c.dos64_reu_peek(f.machine,next));}
}

fn fault(f:*F,b:[28]u8,ip:u16,retired:u16)!void{const r=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,3),f.peek(try f.symbol("dos64_cpu_status")));try unchanged(f,b,ip);try std.testing.expectEqual(retired,try count(f));const again=try f.call("dos64_cpu_step",1000);try std.testing.expectEqual(@as(u8,1),again.p&1);try unchanged(f,b,ip);}
test "8088 ESC ModRM and both displacement fetch faults restore original IP and retire none"{
 for([_]u16{0x1ff,0x1fe,0x1fd})|ip|{var f=try init(1);defer f.deinit();try seed(&f,0xf247);try program(&f,0,ip,&.{0xdb,0x06,0x00,0x40});const before=try snapshot(&f);c.dos64_reu_fail_after(f.machine,1,17);try fault(&f,before,ip,0);}
}
test "8088 ESC dummy word low and high byte DMA failures remain real host faults"{
 for([_]u64{0,1})|skip|{var f=try init(1);defer f.deinit();try seed(&f,0xfad7);try program(&f,0,0x100,&.{0x90,0xd9,0x06,0xff,0x01});try step(&f);try reg(&f,11,0x4000);const before=try snapshot(&f);c.dos64_reu_poke(f.machine,0x401ff,0x43);c.dos64_reu_poke(f.machine,0x40200,0x21);c.dos64_reu_fail_after(f.machine,skip,19);try fault(&f,before,0x101,1);}
}

test "8088 absent8087 WAIT yields original IP with unchanged FLAGS registers count and consumed first-test IRQ shadow"{
 for([_]u16{0xf002,0xf202})|flags|{var f=try init(2);defer f.deinit();try seed(&f,flags);try program(&f,0x100,0x100,&.{0x9b,0xb8,0xef,0xbe});f.poke(try f.symbol("dos64_cpu_irq_shadow"),1);const before=try snapshot(&f);for(0..20)|_|{try step(&f);try unchanged(&f,before,0x100);try std.testing.expectEqual(@as(u16,0),try count(&f));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_yield")));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_irq_shadow")));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_status")));}}
}

test "actual unmodified TPC FNINIT FNSTCW absence probe observes its unchanged pushedzero and restores BX"{
 var f=try init(2);defer f.deinit();try seed(&f,0xf202);try reg(&f,3,0xa55a);try reg(&f,4,0x8000);try reg(&f,10,0x3000);try reg(&f,11,0x3000);
 // Exact captured TPC7.01 sequence through the final POP BX; RET remains next.
 const code=[_]u8{0xdb,0xe3,0x53,0x33,0xdb,0x53,0x8b,0xdc,0xd9,0x3f,0xbb,0x14,0x00,0x4b,0x75,0xfd,0x5b,0x81,0xe3,0x3f,0x0f,0x81,0xfb,0x3f,0x03,0x5b,0xc3};try program(&f,0x0e00,0x6859,&code);const g=try f.symbol("dos64_guest");var n:usize=0;while(f.word(g+24)!=0x6873 and n<100):(n+=1)try step(&f);
 try std.testing.expectEqual(@as(u16,0x6873),f.word(g+24));try std.testing.expectEqual(@as(u16,0xa55a),f.word(g+6));try std.testing.expectEqual(@as(u16,0x8000),f.word(g+8));try std.testing.expectEqual(@as(u16,0),f.word(g+26)&0x40);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_status")));try std.testing.expect(n>40);
}

test "8088 ESC and WAIT retain bounded prefix continuation and native caller status ABI"{
 for([_]u8{0xdb,0x9b})|opcode|{var f=try init(2);defer f.deinit();try seed(&f,0xfad7);var code=[_]u8{0x26}**66;code[64]=opcode;code[65]=0xe3;try program(&f,0,0x100,&code);const before=try snapshot(&f);try step(&f);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_pending")));try std.testing.expectEqual(@as(u16,0),try count(&f));try step(&f);try unchanged(&f,before,if(opcode==0xdb)0x142 else 0x100);try std.testing.expectEqual(@as(u16,if(opcode==0xdb)1 else 0),try count(&f));}
 for(0..256)|p|{var f=try init(1);defer f.deinit();try seed(&f,0xfad7);try program(&f,0,0x100,&.{0xdb,0xe3,0x9b});f.initial_status=@intCast(p);for(0..2)|_|{const r=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);}}
}

const irqhost=@import("machine_irq_pit.zig");const I=irqhost.Fixture;
fn iw(f:*I,at:u16,v:u16)void{f.poke(at,@truncate(v));f.poke(at+1,@truncate(v>>8));}
test "8088 WAIT accepts enabled real PIC interrupt saves WAIT IP and IRET reenters without retiring WAIT"{
 for([_]bool{false,true})|enabled|{var f=try I.init();defer f.deinit();f.poke(try f.symbol("dos64_cache_limit"),1);_=try f.call("dos64_cache_init",100000);_=try f.call("dos64_cpu_init",100000);_=try f.call("dos64_io_init",100000);const g=try f.symbol("dos64_guest");iw(&f,g+18,0x100);iw(&f,g+24,0x200);iw(&f,g+20,0x2000);iw(&f,g+8,0x1000);iw(&f,g+26,if(enabled)0xf202 else 0xf002);f.poke(try f.symbol("dos64_pic_imr"),0);f.poke(try f.symbol("dos64_irq_callback_enabled"),0);irqhost.c.dos64_reu_poke(f.machine,0x20,0);irqhost.c.dos64_reu_poke(f.machine,0x21,3);irqhost.c.dos64_reu_poke(f.machine,0x22,0);irqhost.c.dos64_reu_poke(f.machine,0x23,4);irqhost.c.dos64_reu_poke(f.machine,0x4300,0xcf);irqhost.c.dos64_reu_poke(f.machine,0x1200,0x9b);
  _=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));f.poke(try f.symbol("dos64_irq_line"),0);_=try f.call("dos64_irq_pulse",100000);const r=try f.call("dos64_irq_try",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(@as(u8,@intFromBool(enabled)),f.peek(try f.symbol("dos64_irq_result")));
  if(enabled){try std.testing.expectEqual(@as(u16,0x400),f.word(g+18));try std.testing.expectEqual(@as(u16,0x300),f.word(g+24));_=try f.call("dos64_cache_flush",100000);try std.testing.expectEqual(@as(u8,0),irqhost.c.dos64_reu_peek(f.machine,0x20ffa));try std.testing.expectEqual(@as(u8,2),irqhost.c.dos64_reu_peek(f.machine,0x20ffb));_=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u16,0x100),f.word(g+18));try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u16,0xf202),f.word(g+26));_=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u16,1),f.word(try f.symbol("dos64_cpu_instructions")));}else{try std.testing.expectEqual(@as(u16,0x200),f.word(g+24));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_pic_irr")));try std.testing.expectEqual(@as(u16,0),f.word(try f.symbol("dos64_cpu_instructions")));}
 }
}

test "STI MOVSS POPSS WAIT admits pending PIC after first wait test and IRET reenters with no WAIT retire"{
 const programs=[_][]const u8{&.{0xfb,0x9b},&.{0x8e,0xd0,0x9b},&.{0x17,0x9b}};
 for(programs,0..)|code,index|{
  var f=try I.init();defer f.deinit();f.poke(try f.symbol("dos64_cache_limit"),1);_=try f.call("dos64_cache_init",100000);_=try f.call("dos64_cpu_init",100000);_=try f.call("dos64_io_init",100000);const g=try f.symbol("dos64_guest");iw(&f,g,0x2000);iw(&f,g+18,0x100);iw(&f,g+24,0x200);iw(&f,g+20,0x2000);iw(&f,g+8,0x1000);iw(&f,g+26,if(index==0)0xf002 else 0xf202);f.poke(try f.symbol("dos64_pic_imr"),0);f.poke(try f.symbol("dos64_irq_callback_enabled"),0);
  for(code,0..)|v,i|irqhost.c.dos64_reu_poke(f.machine,0x1200+@as(u32,@intCast(i)),v);irqhost.c.dos64_reu_poke(f.machine,0x21000,0);irqhost.c.dos64_reu_poke(f.machine,0x21001,0x20);irqhost.c.dos64_reu_poke(f.machine,0x20,0);irqhost.c.dos64_reu_poke(f.machine,0x21,3);irqhost.c.dos64_reu_poke(f.machine,0x22,0);irqhost.c.dos64_reu_poke(f.machine,0x23,4);irqhost.c.dos64_reu_poke(f.machine,0x4300,0xcf);
  _=try f.call("dos64_cpu_step",100000);const wait_ip:u16=0x200+@as(u16,@intCast(code.len))-1;try std.testing.expectEqual(wait_ip,f.word(g+24));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_cpu_irq_shadow")));f.poke(try f.symbol("dos64_irq_line"),0);_=try f.call("dos64_irq_pulse",100000);_=try f.call("dos64_irq_try",100000);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_irq_result")));
  _=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(wait_ip,f.word(g+24));try std.testing.expectEqual(@as(u16,1),f.word(try f.symbol("dos64_cpu_instructions")));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cpu_irq_shadow")));const admitted=try f.call("dos64_irq_try",100000);try std.testing.expectEqual(@as(u8,0),admitted.p&1);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_irq_result")));try std.testing.expectEqual(@as(u16,0x300),f.word(g+24));try std.testing.expectEqual(@as(u16,0x400),f.word(g+18));
  _=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(wait_ip,f.word(g+24));try std.testing.expectEqual(@as(u16,0x100),f.word(g+18));try std.testing.expectEqual(@as(u16,0xf202),f.word(g+26));try std.testing.expectEqual(@as(u16,if(index==2)0x1002 else 0x1000),f.word(g+8));_=try f.call("dos64_cpu_step",100000);try std.testing.expectEqual(wait_ip,f.word(g+24));try std.testing.expectEqual(@as(u16,2),f.word(try f.symbol("dos64_cpu_instructions")));
 }
}

const std=@import("std");
const host=@import("machine.zig");const c=host.c;
const alloc=std.testing.allocator;
fn loadProbe(mode:u8)!host.Fixture{
 var f=try host.Fixture.init();errdefer f.deinit();
 const p=try std.fmt.allocPrint(alloc,"agentworking/scratch/native-text-display/probe-{d}.prg",.{mode});defer alloc.free(p);
 const l=try std.fmt.allocPrint(alloc,"agentworking/scratch/native-text-display/probe-{d}.labels",.{mode});defer alloc.free(l);
 const bytes=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,p,alloc,.limited(65538));defer alloc.free(bytes);
 c.dos64_load(f.machine,std.mem.readInt(u16,bytes[0..2],.little),bytes[2..].ptr,bytes.len-2);
 f.symbols.deinit(alloc);f.symbols=.empty;alloc.free(f.labels);
 f.labels=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,l,alloc,.limited(1048576));
 var lines=std.mem.splitScalar(u8,f.labels,'\n');while(lines.next())|line|{var fields=std.mem.tokenizeAny(u8,line," \t\r");if(!std.mem.eql(u8,fields.next() orelse continue,"al"))continue;const address=fields.next() orelse continue;const raw=fields.next() orelse continue;const name=if(raw[0]=='.')raw[1..] else raw;if(!f.symbols.contains(name))try f.symbols.put(alloc,name,try std.fmt.parseInt(u16,address,16));}
 return f;
}
fn half(v:u8)u8{var x:u8=0;for(0..4)|i|{if((v>>@as(u3,@intCast(6-2*i)))&3!=0)x|=@as(u8,1)<<@as(u3,@intCast(3-i));}return x;}
fn text(cells:[]u8,row:usize,cols:usize,s:[]const u8)void{@memcpy(cells[row*cols..][0..s.len],s);}
test "standalone forty and eighty column PRGs produce exact independently expected glyph buffers"{
 const font=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"assets/native-text/cp437-unscii8.bin",alloc,.limited(2049));defer alloc.free(font);
 for([_]u8{0,3})|mode|{
  var f=try loadProbe(mode);defer f.deinit();c.dos64_enable_reu(f.machine);
  const cols:usize=if(mode==0)40 else 80;
  var cells:[2000]u8=@splat(0x20);
  text(&cells,0,cols,if(mode==0)"DOS64 NATIVE TEXT FIXTURE 40 COLUMNS" else "DOS64 NATIVE TEXT FIXTURE 80 COLUMNS");
  text(&cells,1,cols,"A>VER");text(&cells,2,cols,"MS-DOS Version 3.30 (sample text)");text(&cells,3,cols,"A>DIR");text(&cells,4,cols,"PRESENTATION ONLY - NO DOS EXECUTION");
  @memset(cells[5*cols..6*cols],0xc4);cells[5*cols]=0xda;cells[6*cols-1]=0xbf;
  cells[6*cols]=0xb3;text(&cells,6,cols,"\xb3 CP437 GLYPHS BELOW; CURSOR HIDDEN");cells[7*cols-1]=0xb3;
  @memset(cells[7*cols..8*cols],0xc4);cells[7*cols]=0xc0;cells[8*cols-1]=0xd9;
  for(0..256)|i|cells[10*cols+i]=@intCast(i);
  const r=try f.call("dos64_native_text_probe",50000000);try std.testing.expectEqual(@as(u8,0),r.p&1);
  const m=try f.symbol("dos64_text_probe_mailbox");for("DTP1",0..)|v,i|try std.testing.expectEqual(v,f.peek(m+@as(u16,@intCast(i))));
  try std.testing.expectEqual(@as(u8,1),f.peek(m+4));try std.testing.expectEqual(mode,f.peek(m+5));try std.testing.expectEqual(@as(u8,0xa5),f.peek(m+6));try std.testing.expectEqual(@as(u8,0),f.peek(m+7));
  var sum:u16=0;
  for(0..25)|row|for(0..40)|cell|{
   try std.testing.expectEqual(@as(u8,0xf0),f.peek(@intCast(0x4000+row*40+cell)));
   for(0..8)|line|{
    const ci=row*cols+cell*(if(cols==40)@as(usize,1) else 2);
    const v=if(cols==40)font[@as(usize,cells[ci])*8+line] else half(font[@as(usize,cells[ci])*8+line])*16+half(font[@as(usize,cells[ci+1])*8+line]);
    try std.testing.expectEqual(v,f.peek(@intCast(0x6000+row*320+cell*8+line)));sum+%=v;
   }
  };
  try std.testing.expectEqual(sum,f.word(m+8));try std.testing.expectEqual(@as(u16,@truncate(240*1000)),f.word(m+10));sum=0;for(font,0..)|v,i|{sum+%=v;try std.testing.expectEqual(v,f.peek(@intCast(0x4800+i)));}try std.testing.expectEqual(sum,f.word(m+12));
  for(cells[0..cols*25],0..)|v,i|{try std.testing.expectEqual(v,c.dos64_reu_peek(f.machine,0xb8000+@as(u32,@intCast(i*2))));try std.testing.expectEqual(@as(u8,7),c.dos64_reu_peek(f.machine,0xb8001+@as(u32,@intCast(i*2))));}
  var ram:[65536]u8=undefined;for(&ram,0..)|*v,i|v.*=f.peek(@intCast(i));
  const dump=try std.fmt.allocPrint(alloc,"agentworking/scratch/native-text-display/probe-{d}-ram.bin",.{mode});defer alloc.free(dump);
  try std.Io.Dir.cwd().writeFile(std.Options.debug_io,.{.sub_path=dump,.data=&ram});
  for(0xdd04..0xdd10)|a|try std.testing.expectEqual(@as(u8,0),c.dos64_was_written(f.machine,@intCast(a)));
  std.debug.print("mode {d}: {d} CPU cycles, bitmap checksum {x}, mailbox {x}\n",.{mode,r.cycles,f.word(m+8),m});
 }
}

const std=@import("std");
const c=@cImport({@cInclude("bridge.h");});
const a=std.testing.allocator;
const image_path="reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img";
fn read(path:[]const u8)![]u8{return std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,path,a,.limited(5*1024*1024));}
fn symbol(labels:[]const u8,name:[]const u8)!u16{
 var lines=std.mem.splitScalar(u8,labels,'\n');while(lines.next())|line|{var f=std.mem.tokenizeAny(u8,line," \t\r");if(!std.mem.eql(u8,f.next() orelse continue,"al"))continue;const address=f.next() orelse continue;const raw=f.next() orelse continue;if(std.mem.eql(u8,raw[1..],name))return std.fmt.parseInt(u16,address,16);}return error.MissingSymbol;
}
const Target=struct{
 prg:[]u8,labels:[]u8,
 fn init(small:bool)!Target{return .{.prg=try read(if(small)"build/dos64-iec-standalone-small.prg" else "build/dos64-iec-standalone.prg"),.labels=try read(if(small)"build/dos64-iec-standalone-small.labels" else "build/dos64-iec-standalone.labels")};}
 fn deinit(t:Target)void{a.free(t.prg);a.free(t.labels);}
};
fn seed() [512]u8{var s:[512]u8=undefined;for(&s,0..)|*v,i|v.*=@truncate(i);return s;}
fn runCase(t:Target,source:[]const u8,fault:u8,err:u8,count:u32,chunks:u32,partial:u32)!void{
 const m=c.iec_create(t.prg.ptr,t.prg.len,source.ptr,source.len,fault) orelse return error.Create;defer c.iec_destroy(m);
 const r=c.iec_run(m,try symbol(t.labels,"entry"),try symbol(t.labels,"finished"),600_000_000);
 if(r.status!=0)std.debug.print("IEC model divergence fault={d} pc={X:0>4} cycles={d} status={d}\n",.{fault,r.pc,r.cycles,r.status});
 try std.testing.expectEqual(@as(u8,0),r.status);try std.testing.expectEqual(@as(u8,0xff),r.sp);
 const ram=c.iec_ram(m)[0..65536];const mb=ram[0x6000..0x6020];
 try std.testing.expectEqual(@as(u8,if(err==0)0xa5 else 0xe1),mb[0]);try std.testing.expectEqual(err,mb[1]);try std.testing.expectEqual(@as(u8,if(err==0)1 else 0),mb[13]);
 try std.testing.expectEqual(count,@as(u32,mb[4])|(@as(u32,mb[5])<<8)|(@as(u32,mb[6])<<16));
 try std.testing.expectEqual(chunks,@as(u32,std.mem.readInt(u16,mb[7..9],.little)));
 try std.testing.expectEqual(chunks*512+partial,r.dma_bytes);try std.testing.expectEqual(@as(u8,0),ram[0x98]);
 const known:u8=if(fault==1 or fault==5 or fault==6)0 else 1;try std.testing.expectEqual(known,mb[3]);
 if(fault==1)try std.testing.expectEqual(@as(u8,0x42),mb[2]);
 if(fault==4)try std.testing.expectEqual(@as(u8,2),mb[2]);
 if(err==0){try std.testing.expectEqual(@as(u8,1),mb[14]);try std.testing.expectEqual(@as(u8,5),mb[19]);try std.testing.expectEqual(std.hash.Crc32.hash(source),std.mem.readInt(u32,mb[9..13],.little));try std.testing.expectEqual(@as(u8,1),mb[15]);}
 const nmi=std.mem.readInt(u16,ram[0xfffa..0xfffc],.little);try std.testing.expectEqual(nmi,std.mem.readInt(u16,ram[0xfffe..0x10000],.little));try std.testing.expectEqual(@as(u8,0x40),ram[nmi]);
 try std.testing.expectEqual(@as(u8,0xa7),ram[0xbfff]);try std.testing.expectEqual(@as(u8,if(fault==7)0x17 else 0x5a),ram[0xc200]);
 for(ram[0xf000..0xfe00],0..)|v,i|try std.testing.expectEqual(@as(u8,@truncate(i^0xa5)),v);
 const start=std.mem.readInt(u16,t.prg[0..2],.little);const guard=try symbol(t.labels,"started");
 for(t.prg[2..],0..)|v,i|try std.testing.expectEqual(if(i+start==guard)@as(u8,1) else v,ram[i+start]);
 const expected=try a.alloc(u8,4194304);defer a.free(expected);for(expected,0..)|*v,i|v.*=@truncate(i^(i>>8)^(i>>16)^0xa7);
 @memcpy(expected[0x100000..][0..chunks*512+partial],source[0..chunks*512+partial]);
 try std.testing.expectEqualSlices(u8,expected,c.iec_reu(m)[0..4194304]);
 std.debug.print("IEC actual assembly case fault={d} error={d} bytes={d} DMA={d}+{d} cycles={d} KERNAL calls={d}\n",.{fault,err,count,chunks,partial,r.cycles,r.kernal_calls});
}
test "actual small standalone original EOF boundaries and CRC reject with complete REU oracle"{
 const t=try Target.init(true);defer t.deinit();const s=seed();try runCase(t,&s,0,0,512,1,0);
 try runCase(t,s[0..511],0,4,511,0,0);
 var long:[513]u8=undefined;@memcpy(long[0..512],&s);long[512]=0xff;try runCase(t,&long,0,4,512,0,0);
 var corrupt=s;corrupt[123]^=0x80;try runCase(t,&corrupt,0,6,512,1,0);
}
test "actual standalone cleanup preserves primary API errors and rejects late publication"{
 const t=try Target.init(true);defer t.deinit();const s=seed();
 try runCase(t,&s,1,3,0,0,0);try runCase(t,&s,2,1,0,0,0);try runCase(t,&s,3,2,0,0,0);try runCase(t,&s,4,3,13,0,0);
 try runCase(t,&s,5,7,512,1,0);try runCase(t,&s,6,7,512,1,0);try runCase(t,&s,7,8,512,1,0);try runCase(t,&s,8,5,512,0,11);
}
test "actual fixed full 360 KiB target crosses all REU banks and imports immutable supplied DOS image"{
 const t=try Target.init(false);defer t.deinit();const source=try read(image_path);defer a.free(source);
 var before:[32]u8=undefined;std.crypto.hash.sha2.Sha256.hash(source,&before,.{});var want:[32]u8=undefined;_=try std.fmt.hexToBytes(&want,"bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb");try std.testing.expectEqualSlices(u8,&want,&before);
 try runCase(t,source,0,0,368640,720,0);const after=try read(image_path);defer a.free(after);try std.testing.expectEqualSlices(u8,source,after);
}

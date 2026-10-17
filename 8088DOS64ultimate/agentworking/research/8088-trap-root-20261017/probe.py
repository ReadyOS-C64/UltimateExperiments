from pathlib import Path
import ctypes as C,json,hashlib
P=Path.cwd();L=C.CDLL(str(P/'model.dylib'));ptr=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64
class Regs(C.Structure):_fields_=[('pc',u16),('sp',u8),('a',u8),('x',u8),('y',u8),('p',u8),('cycles',u64),('instructions',u64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',u8)]
for n,r,a in [('dos64_create',ptr,[]),('dos64_destroy',None,[ptr]),('dos64_load',None,[ptr,u16,ptr,C.c_size_t]),('dos64_poke',None,[ptr,u16,u8]),('dos64_peek',u8,[ptr,u16]),('dos64_set_regs',None,[ptr,Regs]),('dos64_run',Result,[ptr,u16,u64]),('dos64_enable_reu',None,[ptr]),('dos64_reu_poke',None,[ptr,u32,u8])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
labels={r.split()[2].lstrip('.'):int(r.split()[1],16)for r in(P/'DOS64.labels').read_text().splitlines()if r.startswith('al ')}
rows=[]
for flags,opcode,vector,wanted in [(0xf002,0x90,1,(0x1000,0x101)),(0xf102,0x90,1,(0x3000,0x200)),(0xf002,0xcc,3,(0x3000,0x200))]:
 m=L.dos64_create()
 try:
  data=(P/'DOS64.PRG').read_bytes();L.dos64_load(m,0x801,data[2:],len(data)-2);L.dos64_enable_reu(m)
  def word(a,v):L.dos64_poke(m,a,v&255);L.dos64_poke(m,a+1,v>>8)
  def call(n):
   stop=0x200;ret=stop-1;word(0x1fe,ret);L.dos64_set_regs(m,Regs(labels[n],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m,stop,200000);assert r.status==0,(n,r.status,hex(r.regs.pc));return r
  def reg(i,v):word(labels['dos64_guest']+i*2,v)
  def get(i):a=labels['dos64_guest']+i*2;return L.dos64_peek(m,a)|(L.dos64_peek(m,a+1)<<8)
  L.dos64_poke(m,labels['dos64_cache_limit'],2);call('dos64_cache_init');L.dos64_poke(m,labels['dos64_memory_mode'],1);call('dos64_cpu_init')
  for i,v in [(9,0x1000),(12,0x100),(10,0x2000),(4,0x800),(13,flags)]:reg(i,v)
  L.dos64_reu_poke(m,0x10100,opcode)
  for a,v in [(vector*4,0),(vector*4+1,2),(vector*4+2,0),(vector*4+3,0x30)]:L.dos64_reu_poke(m,a,v)
  r=call('dos64_cpu_step');after=(get(9),get(12))
  if flags&0x100:
   # Native scheduler normally samples IRQ before this next instruction boundary.
   first=after;r=call('dos64_cpu_step');after=(get(9),get(12))
   assert first==(0x1000,0x101)and after!=wanted,(first,after)
  else:assert after==wanted,(flags,opcode,after,wanted)
  rows.append({'flags':hex(flags),'opcode':hex(opcode),'after_CS_IP':[hex(v)for v in after],'expected_CS_IP':[hex(v)for v in wanted],'missing_type1':bool(flags&0x100),'instruction_count':L.dos64_peek(m,labels['dos64_cpu_instructions']),'host_status':r.status,'native_cycles':r.regs.cycles})
 finally:L.dos64_destroy(m)
(P.parent/'REPRO_RESULT.json').write_text(json.dumps({'status':'REPRODUCED_MISSING_8088_SINGLE_STEP','groups':rows,'native_sha256':hashlib.sha256((P/'DOS64.PRG').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((P/'model.dylib').read_bytes()).hexdigest(),'fresh_build':False,'physical':False,'fixed':False},indent=2)+'\n')
print(json.dumps(rows))

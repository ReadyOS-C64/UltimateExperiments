"""Actual packagedC29/R26, unchanged live provider, trusted fresh bootstrap.

CPU only. Neither a saved stack nor old overlay continuation is resumed.
"""
from pathlib import Path
import binascii,json,re
EXTENTS=((0x1000,0xb600,0),(0xca00,0x600,0xb600),(2,24,0xbc00))

def labels(path):
 return {p[2].lstrip('.'):int(p[1],16)for s in path.read_text().splitlines()if len(p:=s.split())==3 and p[0]=='al'}

def bc_state(f):
 return {n:f.read(f.s[n],w).hex()for n,w in [('se_bc_arena',5),('se_bc_ticket',4),('se_bc_incarnation',4),('se_bc_flags',1),('se_bc_head',1),('se_bc_tail',1),('se_bc_count',1),('se_bc_ring',96)]}

def fs_identity(f,project):
 """Read exact named fields in the frozen real FS_FIELDS contract; no writes."""
 source=(project/'src/fold/source.inc').read_text();pairs=re.findall(r'^    action (se_\w+),(\d+),(\d+)$',source,re.M);raw=bytearray(59);covered=set()
 for name,offset,width in pairs:
  at,n=int(offset),int(width);assert not covered.intersection(range(at,at+n));covered.update(range(at,at+n));raw[at:at+n]=f.read(f.s[name],n)
 assert covered==set(range(59));return bytes(raw)

def suspend_resume(f,dll,fixture,project,out):
 out.mkdir();image=(fixture/'build/overlays/lifectrl.seo').read_bytes();copy=(fixture/'build/overlays/lifecopy.seo').read_bytes()
 assert image==(project/'build/overlays/lifectrl.seo').read_bytes()and copy==(project/'build/overlays/lifecopy.seo').read_bytes()
 prelude=image[36+0x800:36+0x900];assert prelude[:5]==bytes.fromhex('78d8a2ff9a')
 sy=labels(project/'build/overlays/lifecopy.lbl')
 f.m.load(0x800,bytes.fromhex(f.report['resident_binding']['digest'])+bytes(0x40));f.m.load(0xa00,prelude)
 f.put('se_e_redraw',0,1);f.put('se_status',1,1)
 # A foreign phase owner64 is opaque even though the caller can admit C29.
 # This is an explicit fault fixture, not a live-source authority shortcut.
 oldphase=f.read(0x8d00,1152);pattern=bytes((i*29+71)&255 for i in range(1152));f.m.load(0x8d00,pattern);f.put('se_f_owner',64,1);guard=f.reu()
 r,n=f.fast_call(0xae0,a=0);assert r.p&1 and r.a==0xd5 and f.get('se_f_owner',1)==64 and f.read(0x8d00,1152)==pattern and f.reu()==guard
 f.m.load(0x8d00,oldphase);f.put('se_f_owner',0,1)
 canonical=f.canonical();bc=bc_state(f);source=f.merged();catalog=f.catalog();before=f.reu();steps=[]
 fields=[('se_doc_generation',2),('se_doc_length',3),('se_r_revision',4),('se_hot_ready',1),('se_hot_pending',1),('se_hot_generation',2),('se_hot_base',3),('se_hot_old_length',2),('se_hot_length',2),('se_hot_left',2),('se_hot_right',2),('se_hot_caret',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2)]
 source_state={n:f.get(n,w)for n,w in fields}
 def lc(op):
  r,n=f.fast_call(0xae0,a=op);steps.append(n);assert not r.p&1,(op,r.a,r.p);return r
 assert lc(0).a==1
 for at in range(500):
  r=lc(1);assert f.canonical()==canonical and bc_state(f)==bc and f.read(0xc600,1024)==f.shim
  if not r.a:break
  assert r.a==1
 else:raise AssertionError('boundedC29prepare')
 assert at+1==381
 saved=f.reu();handle=f.m.read(0x810);bank=f.m.read(0x811)
 assert f.m.read(f.s['se_reu_logical_owner']+handle)==f.m.read(f.s['se_reu_physical_owner']+bank)==0xfc
 lo=bank*65536;payload=saved[lo:lo+0xbc18];header=saved[lo+0xbc20:lo+0xbc60]
 assert header[:8]==b'LCA1'+bytes((1,0xa5,3,0xfc))
 assert int.from_bytes(header[51:53],'little')==binascii.crc_hqx(payload,65535)and int.from_bytes(header[62:64],'little')==binascii.crc_hqx(header[:62],65535)
 wanted=bytearray(before);wanted[lo:lo+0xbc18]=payload;wanted[lo+0xbc20:lo+0xbc60]=header
 assert saved==wanted,'capture outsideexactFCpayload/header'
 # Real live provider state stays authoritative. In particular this experiment
 # does not restore saved provider ownership over a changed external allocator.
 preserve={n:f.read(f.s[n],w)for n,w in [('se_reu_map',256),('se_reu_logical_owner',256),('se_reu_physical_owner',256),('se_reu_epoch',2),('se_reu_retired',1),('se_reu_banks',2)]}
 for cpu,length,off in EXTENTS:f.m.load(cpu,bytes((i*37+19)&255 for i in range(length)))
 for n,raw in preserve.items():f.m.load(f.s[n],raw)
 f.m.load(0xa000,copy[36:]);f.m.load(0xa00,prelude)
 r,n=f.fast_call(sy['se_lc_restore_begin']);steps.append(n);assert not r.p&1 and r.a==1
 for at in range(200):
  if f.m.read(0x820)==4 and f.m.read(0x827)==2:
   for n,v in [('pc',sy['se_lc_copy_step']),('sp',0xfd),('p',0x24)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
   used=dll.gm_idle(f.m.handle,0xa00,100000);assert used and f.m.regs().sp==255;steps.append(used)
   for cpu,length,off in EXTENTS:assert f.read(cpu,length)==payload[off:off+length],('exactwarmrestore',hex(cpu))
   assert f.reu()==saved and f.read(0xc600,1024)==f.shim
   assert bc_state(f)==bc,'BC17/ring96 exactatfreshprelude'
   used=dll.gm_idle(f.m.handle,f.s['se_idle'],300000);assert used,('freshprelude',hex(f.m.regs().pc));steps.append(used);break
  r,n=f.fast_call(sy['se_lc_copy_step']);steps.append(n);assert not r.p&1 and r.a==1
 else:raise AssertionError('boundedR26restore')
 assert f.canonical()==canonical and f.merged()==source and f.catalog()==catalog and f.reu()==saved
 assert bc_state(f)==bc,'freshhardwaremustnotinvent/dropcanonicalobserverqueue/attempt'
 assert {n:f.get(n,w)for n,w in fields}==source_state
 assert not any(f.get(n,1)for n in('se_f_owner','se_e_job','se_e_draw_busy','se_doc_read_locks','se_fs_owned'))
 assert not f.get('se_bc_flags',1)&8
 result=dict(source_before=source_state,source_after={n:f.get(n,w)for n,w in fields},BC_bit64_before=int(bc['se_bc_flags'],16)&64,BC_bit128_before=int(bc['se_bc_flags'],16)&128,foreign_owner64_opaque_refusal=True,prepare_steps=381,restore_steps=at+1,maximum_call_instructions=max(steps),bc_before=bc,bc_after=bc_state(f),saved_bank=bank,payload_bytes=len(payload),warm_STATE_bytes=f.report['state_bytes'],catalog_assets=len(f.assets),scope='Actual packagedC29/R26; unchanged liveprovider/REU; trustedfreshR26/prelude; noReadyOS/oldstack/native/hardwareclaim')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

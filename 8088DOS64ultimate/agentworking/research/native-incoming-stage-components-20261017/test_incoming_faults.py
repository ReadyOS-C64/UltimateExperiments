from test_incoming import *
from test_online_save import Regs
records=[]
for name,ret,args in [('dos64_host_input_model_keys',None,[C.c_void_p,C.c_void_p]),('bind_silent_pair',None,[C.c_void_p,C.c_uint32,C.c_uint8,C.c_uint32])]:
 if hasattr(L,name):f=getattr(L,name);f.restype=ret;f.argtypes=args

def crc_zero(image):
 prefix=image[:-4];v0=zlib.crc32(prefix+bytes(4));basis={}
 for i in range(32):
  v=zlib.crc32(prefix+(1<<i).to_bytes(4,'little'))^v0;mask=1<<i
  while v:
   k=v.bit_length()-1
   if k in basis:v^=basis[k][0];mask^=basis[k][1]
   else:basis[k]=(v,mask);break
 v=v0;sol=0
 while v:k=v.bit_length()-1;v^=basis[k][0];sol^=basis[k][1]
 result=prefix+sol.to_bytes(4,'little');assert zlib.crc32(result)==0;return result

class Faults(unittest.TestCase):
 def exercise(self,kind):
  image=fat(b'FAULT INPUT REAL BYTES\r\n')
  if kind=='short':image=image[:-1]
  if kind=='extra':image+=b'X'
  m,old,f,path,image,q=setup(self,image=image)
  try:
   before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);hd=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);hdb=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);high=m.get(128,96);zp=m.get(32,36);pos=L.save_model_position(m.m,1);commands=L.bulk_model_commands(m.m);fired=False;original=bytes(image)
   if kind=='unknownclose':L.save_model_fail_close(m.m,2)
   def hook(m,i):
    nonlocal fired
    phase=m.g(IW['phase'])
    if fired:return
    if kind in ['grow','cancel','raw_count','raw_more','suppressLOAD','corruptLOAD']and phase==4:
     fired=True
     if kind=='grow':seed(m,path,original+b'GROWING SOURCE TAIL')
     elif kind=='cancel':m.p(IW['iw_cancel'],1)
     else:
      n=L.bulk_model_commands(m.m)+1;L.bulk_model_faults(m.m,-1,-1,n if kind in ['raw_count','raw_more'] else -1,8 if kind=='raw_count' else 6,-2 if kind=='suppressLOAD' else 0 if kind=='corruptLOAD' else -1)
    elif kind=='changedsource'and phase==8:
     fired=True;b=bytearray(original);b[1234]^=0x80;seed(m,path,b)
    elif kind=='clock'and phase==4:
     fired=True;m.p('dos64_host_clock_claim',0)
    elif kind=='lease'and phase==5:
     fired=True;m.p('dos64_floppy_stage_active',0) # Explicit native lease withdrawal, not a public observation.
   polls=run(self,m,hook);d={'kind':kind,'state':m.g(IW['state']),'error':m.g(IW['error']),'closed':m.g(IW['closed']),'phase':m.g(IW['phase']),'polls':polls,'fired':fired};self.assertEqual(d['state'],3,d);self.assertNotEqual(d['error'],0,d);r=m.call('iw_take');self.assertEqual(r.regs.a|(r.regs.x<<8),0,d);self.assertEqual(m.get(128,96),high);self.assertEqual(m.get(32,36),zp);after=reu(m,0,4194304);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x1da000:],before[0x1da000:]);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(L.save_model_position(m.m,1),pos);self.assertEqual(L.bulk_model_open(m.m,1),1)
   if kind=='unknownclose':
    self.assertEqual(d['closed'],0,d);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_commands(m.m)-commands,1)
   else:
    self.assertEqual(d['closed'],1,d);self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(m.get('hd_state_start',len(hd)),hd);self.assertEqual(m.get('hdb_state_start',len(hdb)),hdb);self.assertEqual(L.bulk_model_open(m.m,2),0)
   if kind in ['short','extra']:self.assertEqual(after,before)
   if kind=='grow':self.assertEqual(after[0x180000:0x1da000],original);self.assertEqual(d['error'],5)
   if kind in ['clock','lease']:self.assertEqual(m.g('dos64_native_diag'),0xe1)
   records.append(d|{'oldmounted_and_arena_tail_exact':True,'C_file_position_and_contents_unchanged':True,'no_receipt':True})
  finally:m.close()
 def test_short(self):self.exercise('short')
 def test_extra(self):self.exercise('extra')
 def test_growth_after_INFO_bounded_LOAD(self):self.exercise('grow')
 def test_changed_same_size_second_open(self):self.exercise('changedsource')
 def test_cancel(self):self.exercise('cancel')
 def test_clock_failure(self):self.exercise('clock')
 def test_native_lease_withdrawal(self):self.exercise('lease')
 def test_unknown_close_no_retry(self):self.exercise('unknownclose')
 def test_LOAD_wrong_reported_count(self):self.exercise('raw_count')
 def test_LOAD_MORE(self):self.exercise('raw_more')
 def test_suppressed_LOAD(self):self.exercise('suppressLOAD')
 def test_corrupted_LOAD(self):self.exercise('corruptLOAD')
 def test_CRC_zero_actual(self):
  b=crc_zero(fat(b'VALID CRC ZERO\r\n'));Incoming.success(self,1,1,b);records.append({'CRC_zero_native_accepted_with_private_receipt':True})
 def test_each_native_BPB_offset_refuses_before_receipt(self):
  offsets=json.loads((P/'GEOMETRY_SOURCE.json').read_text())['tables']['ctl_bpb_offsets']
  for at in offsets:
   with self.subTest(offset=at):
    image=bytearray(fat(b'GEOMETRY INPUT\r\n'));image[at]^=1;m,old,f,path,image,q=setup(self,image=bytes(image))
    try:
     before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);polls=run(self,m);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,9,1));r=m.call('iw_take');self.assertEqual(r.regs.a|(r.regs.x<<8),0);self.assertEqual(m.get('dos64_files_state_start',25),ctx);after=reu(m,0,4194304);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x1da000:],before[0x1da000:]);records.append({'native_generated_BPB_offset':at,'rejected_geometry9':True,'polls':polls})
    finally:m.close()
 def test_silent_both_FETCH_partial_refuses(self):
  for prefix in [0,17,255]:
   with self.subTest(prefix=prefix):
    m,old,f,path,image,q=setup(self)
    try:
     ctx=m.get('dos64_files_state_start',25);fired=False
     def hook(m,i):
      nonlocal fired
      if not fired and m.g(IW['phase'])==5:fired=True;L.bind_silent_pair(m.m,0x180000,1,prefix)
     polls=run(self,m,hook);self.assertTrue(fired);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,6,1));self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(m.g('dos64_native_diag'),0xe1);records.append({'both_silent_FETCH_prefix':prefix,'DMA6_no_receipt':True,'polls':polls})
    finally:m.close()
 def test_bad_path_or_forged_FQ_no_FILE_or_DMA(self):
  for kind in ['token','base','generation','path','capacity','configuredcapacity']:
   with self.subTest(kind=kind):
    m,old,f,path,image,q=setup(self)
    try:
     ctx=m.get('dos64_files_state_start',25);before=reu(m,0,4194304);cmd=L.bulk_model_commands(m.m);fq=symbols['dos64_floppy_request']
     if kind=='token':m.p(fq+11,m.g(fq+11)^1)
     elif kind=='base':m.p(fq+7,0x10)
     elif kind=='generation':m.p(fq+15,m.g(fq+15)^1)
     elif kind=='path':m.put(IW['iw_path'],b'/sd//bad.IMG'.ljust(128,b'\0'))
     elif kind=='capacity':m.p(fq+4,3)
     else:m.p('dos64_overlay_reu_mib',3)
     r=m.call('iw_begin',2000000);self.assertEqual(r.regs.a,0);self.assertEqual(L.bulk_model_commands(m.m),cmd);self.assertEqual(reu(m,0,4194304),before);self.assertEqual(m.get('dos64_files_state_start',25),ctx);r=m.call('iw_take');self.assertEqual(r.regs.a|(r.regs.x<<8),0);records.append({'bad_admission':kind,'no_FILE_or_DMA':True})
    finally:m.close()
 def test_leaf_error_before_physical_STOP_firstcause(self):
  m,old,f,path,image,q=setup(self)
  try:
   ctx=m.get('dos64_files_state_start',25);L.bulk_model_faults(m.m,L.bulk_model_commands(m.m)+2,-1,-1,0,-1);fired=False
   def hook(m,i):
    nonlocal fired
    if not fired and m.g('dos64_files_error') and m.g('dos64_files_state')==1 and m.g('dos64_files_op')==2:
     fired=True;L.dos64_host_input_model_keys(m.m,C.create_string_buffer(bytes(7)+b'\x80'))
   polls=run(self,m,hook);self.assertTrue(fired);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,4,1));self.assertEqual(m.get('dos64_files_state_start',25),ctx);records.append({'FILE_before_physical_STOP':4,'polls':polls})
  finally:m.close()
 def test_full_raw32_gap_not_elapsed16_alias(self):
  m,old,f,path,image,q=setup(self)
  try:
   ctx=m.get('dos64_files_state_start',25);fired=False
   def hook(m,i):
    nonlocal fired
    if not fired and m.g(IW['phase'])==5:fired=True;L.dos64_cia_clock_advance(m.m,0x10000000)
   polls=run(self,m,hook);self.assertTrue(fired);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,2,1));self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get('dos64_files_state_start',25),ctx);records.append({'actual_raw32_gap_10000000':True,'CLOCK2':True,'polls':polls})
  finally:m.close()
 def test_clock_recovers_but_stuck_drain_still_bounded256(self):
  m,old,f,path,image,q=setup(self)
  try:
   fired=False;at=None;recovered=False
   def hook(m,i):
    nonlocal fired,at,recovered
    if not fired and m.g(IW['phase'])==4:
     fired=True;at=i;m.p('dos64_host_clock_claim',0);L.dos64_uci_model_stuck(m.m,1)
    elif fired and not recovered and i==at+2:recovered=True;m.p('dos64_host_clock_claim',0xa5)
   polls=run(self,m,hook);self.assertTrue(recovered);self.assertLessEqual(polls-at,257);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,2,0));self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_open(m.m,1),1);records.append({'clock_recovery_never_resets_drain':True,'after_failure_polls':polls-at,'first_CLOCK2':True})
  finally:m.close()
 def test_late_cancel_withdraws_receipt_but_retains_known_C(self):
  m,old,f,path,image,q=setup(self)
  try:
   ctx=m.get('dos64_files_state_start',25);run(self,m);self.assertEqual(m.g(IW['state']),2);m.p(IW['iw_cancel'],1);r=m.call('iw_take',2000000);self.assertEqual(r.regs.a|(r.regs.x<<8),0);self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(3,3,1));self.assertEqual(m.g('dos64_native_diag'),8);self.assertEqual(m.get('dos64_files_state_start',25),ctx);m.p(IW['iw_cancel'],0);r=m.call('iw_take');self.assertEqual(r.regs.a|(r.regs.x<<8),0);records.append({'late_cancel_irreversible_no_receipt':True,'known_C_retained':True,'caller_must_CANCEL_coretoken_before_Resume':True})
  finally:m.close()
 def test_public_input_edits_cannot_retarget_verified_receipt(self):
  m,old,f,path,image,q=setup(self,target=2,drive=0)
  try:
   run(self,m);self.assertEqual(m.g(IW['state']),2);cmd=L.bulk_model_commands(m.m);before=reu(m,0,4194304);m.put('dos64_floppy_request',bytes([255])*27);m.put(IW['iw_path'],b'/WRONG.IMG'.ljust(128,b'\0'));m.p(IW['iw_enable'],0);m.wide(IW['iw_limit'],0,2);r=m.call('iw_take',2000000);ptr=r.regs.a|(r.regs.x<<8);self.assertEqual(ptr,IW['receipt']);v=m.get(ptr,149);self.assertEqual(v[:2],bytes([0,q[2]]));self.assertEqual(v[2:5],q[5:8]);self.assertEqual(v[5:9],q[11:15]);self.assertEqual(v[21:],path.ljust(128,b'\0'));self.assertEqual(int.from_bytes(v[17:21],'little'),zlib.crc32(image));self.assertEqual(L.bulk_model_commands(m.m),cmd);self.assertEqual(reu(m,0,4194304),before);records.append({'post_admission_publicFQ_path_limit_enable_forgery_no_retarget':True,'private_original_receipt':True})
  finally:m.close()
 def test_active_API_preserves_all_nativeP_and_ZP_patterns(self):
  m,old,f,path,image,q=setup(self)
  try:
   high=m.get(128,96);zp=m.get(32,36);self.assertEqual(m.call('iw_begin',2000000).regs.a,1)
   for p in [0,1,8,9,0x45,0x8d,0xc7,0xcf]:
    ret=symbols['fixture_return']-1;m.p(511,ret>>8);m.p(510,ret&255);L.dos64_set_regs(m.m,Regs(symbols['iw_poll'],0xfd,0x71,0x82,0x93,p,0,0));r=L.dos64_run(m.m,symbols['fixture_return'],2000000);self.assertEqual(r.status,0);self.assertEqual(r.regs.p&0xcf,p&0xcf);self.assertEqual(r.regs.sp,0xff);self.assertEqual(m.get(32,36),zp);self.assertEqual(m.get(128,96),high)
   for i in range(60000):
    if m.g(IW['state'])!=1:break
    m.call('iw_poll',2000000)
   self.assertEqual((m.g(IW['state']),m.g(IW['error']),m.g(IW['closed'])),(2,0,1));records.append({'active_API_P8patterns_high96_ZP20_43_exact':True,'hardware_stack_balanced':True})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Faults));(P/'INCOMING_FAULT_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())

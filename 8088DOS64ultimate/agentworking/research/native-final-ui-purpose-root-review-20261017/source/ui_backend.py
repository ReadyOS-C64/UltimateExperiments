import json
from cold_backend import ColdBackend
from product import Product
from preserved_product import PreservedProduct
from preserved_stage import closed_terminal
class UIBackend(ColdBackend):
 def __init__(self,*a,observer,**kw):super().__init__(*a,**kw);self.observer=observer;self.product=None;self.product_result=None
 def stage_cb(self,end):
  value=super().stage_cb(end)
  # Retain and accept actual stopped stager before its code is replaced.
  raw=self.preserve('before_product',end);closed_terminal(raw,self.stager);self.wire.accept_stage_terminal(raw)
  if end-self.clock()<300:raise TimeoutError('Original core needs300s for bounded product and restoration; no entry')
  self.product=Product(self.wire,self.protocol,self.release,self.assets,self.observer,save=self.save,clock=self.clock,sleep=self.sleep,cancel=self.cancel)
  try:self.product_result=self.product.run(raw,end);self.retain('product-result',self.product_result)
  finally:
   if self.product_result is None:self.retain('product-result-failed',self.product.report)
  return value
 def terminal_validator(self,raw):
  if self.product is None:return closed_terminal(raw,self.stager)
  proof=self.observer.terminal(raw);return dict(proof,known_closed=True,quiet=True)
 def preserve(self,role,parent):
  if self.wire.role!='product':return super().preserve(role,parent)
  self.tx(role+'_pause',lambda:self.wire.control('pause',role+'_pause',self.bound(parent)));raw=self.tx(role+'_RAM',lambda:self.wire.ram(role+'_RAM',self.bound(parent)));self.retain(role+'-RAM',raw);self.observer.terminal(raw);return raw
 def terminal_cb(self,end):
  self.wire.cleanup_mode=True
  if self.product is None:return super().terminal_cb(end)
  raw=self.preserve('product_terminal',end);self.wire.accept_product_terminal(raw);return raw
 def run(self):
  self.machine=PreservedProduct(self.baseline,self.wire.service,self.stager,terminal_validator=self.terminal_validator,clock=self.clock,cleanup_clock=self.wire.clock)
  try:self.callback_result=self.machine.run(originals=self.originals_cb,set_temporary=self.temporary_cb,snapshot=self.snapshot_cb,stage=self.stage_cb,terminal_RAM=self.terminal_cb,restore=self.restore_cb,basic_cleanup=self.basic_cb,profile_restore=self.profile_cb,retain=self.retain)
  except BaseException as e:self.first=e
  finally:
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   self.report={'status':'passed'if self.first is None else'failed','scope':'FINAL_PUBLIC_SETUP_NATIVE_UI_COMPONENT_WITH_RETENTION','first_error':None if self.first is None else repr(self.first),'callback_report':self.callback_result or getattr(self.first,'preserved_stage_report',None),'source_before':self.source_audit_before,'source_after':self.source_audit_after,'stage':self.stage_result,'product':self.product_result or(getattr(self.product,'report',None)),'captures':self.captures,'source_load_ledgers':self.wire.source_loads,'stager_PUT_ledger':[]if self.stage_io is None else self.stage_io.ledger,'native_restore':self.native_result,'native_may_write':self.native_may_write,'native_known_closed':self.native_known_closed,'temporary_turbo':self.turbo_result,'original_CPU_RAM_application_restored':False,'START_DOS_TURBO_executed':False,'final_V1_acceptance':False,'FTP':0,'upper12MiB_access':False}
   try:self.retain('RESULT',self.report)
   except BaseException as e:self.latch(e);self.report.update(status='failed',first_error=repr(self.first),result_record_durable=False)
  if self.first is not None:raise self.first
  return self.report

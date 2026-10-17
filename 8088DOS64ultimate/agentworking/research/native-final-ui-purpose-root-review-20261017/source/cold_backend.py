"""Cold-exclusive successor for the exact retained failed-readonly-stream state.
Fresh original RAM/settings are durable before admission/reset/config change.
"""
from stage_backend import Backend
from cold_entry import ColdEntry
from transport import FIELDS
class ColdBackend(Backend):
 def __init__(self,*a,entry,**kw):
  if type(entry)is not ColdEntry:raise ValueError('Exact byte-bound failed-stream predecessor required')
  self.entry=entry;self.entry_fact=None;super().__init__(*a,**kw)
 def originals_cb(self,end):
  self.audit.verify();self.source_audit_before=True
  self.before=self.tx('inventory_before',lambda:self.wire.inventory(self.bound(end,30)))
  if any(self.before['info'].get(k)!=v for k,v in FIELDS.items()):raise ValueError('Exact known device/firmware before takeover')
  cfg=self.before['configs/C64%20and%20Cartridge%20Settings']['C64 and Cartridge Settings']
  if cfg.get('Command Interface')!='Enabled'or cfg.get('RAM Expansion Unit')!='Enabled'or cfg.get('REU Size')not in ['4 MB','8 MB','16 MB']or cfg.get('REU Preload')!='Disabled':raise ValueError('Enabled configured4MiB-plus/no preload')
  self.tx('original_pause',lambda:self.wire.control('pause','original_pause',self.bound(end)))
  self.ram_before=self.tx('original_RAM',lambda:self.wire.ram('original_RAM',self.bound(end)))
  self.retain('preflight-original-RAM',self.ram_before);self.retain('preflight-inventory',self.before)
  self.entry_fact=self.entry.admit(self.ram_before);self.retain('cold-entry-admission',self.entry_fact)
  self.originals=True;return self.ram_before,self.before

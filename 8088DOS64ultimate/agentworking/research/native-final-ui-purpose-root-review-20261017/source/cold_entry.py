"""Exact failed-stream predecessor permits one *external* documented cold reset.
This is admission only; no API calls, no arbitrary MAIN/application takeover.
"""
import json,zlib,hashlib
from basic_ready import basic_ready
sha=lambda b:hashlib.sha256(b).hexdigest()
ACTIVE_SHA='e9fed827ede0d6d40a3ec249f0c106c81d6fdd2e5d2722d14fcc172fc12c58db'
TERMINAL_SHA='63a92f51afcab9c80de030fd8ff8d9674e1a5d5434a9021938e8ba12672754e0'
class ColdEntry:
 def __init__(self,active,terminal,stream):
  if sha(active)!=ACTIVE_SHA or sha(terminal)!=TERMINAL_SHA or len(terminal)!=65536:raise ValueError('Exact current predecessor and retained terminal source')
  a=json.loads(active)
  for k,v in {'status':'CURRENT9_STAGING_FAILED_RESERVED','hardware_owner':'cia_probe_independent_review','hardware_reserved':True,'current_host_job_live':False,'stager_executed':False,'native_file_jobs':0,'REU_WRITE_commands_confirmed':0,'upper12MiB_accessed':False,'owned_processes_absent_verified':True}.items():
   if type(a.get(k))is not type(v)or a[k]!=v:raise ValueError('Exact source-bound predecessor scope '+k)
  if type(stream)is not bytes or stream[:2]!=b'\x01\x08'or terminal[0x801:0x801+len(stream)-2]!=stream[2:]:raise ValueError('Retained predecessor complete readonly stream source')
  h=terminal[0x3e00:0x3e34]
  if h[:8]!=b'RSF1\1\xa5\3\0'or zlib.crc32(h[:48])!=int.from_bytes(h[48:],'little'):raise ValueError('Exact retained incomplete ready-header/CRC')
  self._source=bytes(stream[2:]);self._header=bytes(h)
 def admit(self,ram):
  if type(ram)is not bytes or len(ram)!=65536:raise ValueError('Fresh complete coherently paused original RAM required')
  if basic_ready(ram)is not None:return {'cold_entry':'FRESH_BASIC_READY','original_CPU_RAM_application_restore':False}
  if ram[0x801:0x801+len(self._source)]!=self._source or ram[0x3e00:0x3e34]!=self._header:raise ValueError('Neither conservative BASIC nor exact owned failed stream; no reset/takeover')
  return {'cold_entry':'EXACT_OWNED_FAILED_READONLY_STREAM','predecessor_header_exact':True,'original_CPU_RAM_application_restore':False,'whole_current_REU_verified':False}

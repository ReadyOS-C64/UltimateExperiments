"""LOCAL standalone C-close gating before any live current-MAIN retirement.
No IO constructor; execute_close is a separately owned deadline-bound backend.
"""
import time,hashlib
from close_contract import Contract,configure,result
class MainTakeover:
 def __init__(self,base,labels_blob,*,clock=time.monotonic):
  if hashlib.sha256(labels_blob.encode()).hexdigest()!='be8d95a436df8067f56380ff11ff8d55c724c929f05cbfd674e971d6a568b9f2':raise ValueError('Exact close-helper source labels')
  self.base=base;self.labels={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in labels_blob.splitlines()if l.startswith('al ')};self.clock=clock;self.attempted=False;self.first=None;self.observation={'known_closed':False};self._terminal=None;self._configured=None;self._nonce=None;self._stager_attempted=False
 def close(self,raw_MAIN,main,raw_labels,raw_map,path,nonce,execute_close,deadline):
  if self.attempted or self.first is not None:raise ValueError('One source-bound standalone close attempt')
  try:
   if self.clock()>=deadline:raise TimeoutError('Original takeover deadline')
   c=Contract(main,raw_labels,raw_map,path);admission=c.admit(raw_MAIN);configured=configure(self.base,self.labels,nonce,c,raw_MAIN)
   self.attempted=True # callback may already retire native main; never rerun
   terminal=execute_close(configured,self.labels,nonce,deadline)
   if self.clock()>=deadline:raise TimeoutError('Takeover endpoint unchanged')
   facts=result(terminal,configured,self.labels,nonce);self._terminal=bytes(terminal);self._configured=configured;self._nonce=bytes(nonce);self.observation={'known_closed':True,'admission':admission,'result':facts};return self.verified()
  except BaseException as e:
   if self.first is None:self.first=e
   raise
 def verified(self):
  if self.first is not None:raise self.first
  if self._terminal is None:raise ValueError('No native terminal C-close proof')
  return result(self._terminal,self._configured,self.labels,self._nonce)
 def start_stager(self,starter):
  # Observations/positive flags never authorize overwriting an open main.
  self.verified()
  if self._stager_attempted:raise ValueError('Stager replacement attempted once')
  self._stager_attempted=True
  try:return starter.start()
  except BaseException as e:
   if self.first is None:self.first=e
   raise

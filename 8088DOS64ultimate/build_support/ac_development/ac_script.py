"""Real DOS commands, native BIOS keyboard queue, bounded current-prompt progression."""
PLAIN="1234567890-=QWERTYUIOP[]ASDFGHJKL;'`\\ZXCVBNM,./"
SCANS=(2,3,4,5,6,7,8,9,10,11,12,13,16,17,18,19,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36,37,38,39,40,41,43,44,45,46,47,48,49,50,51,52,53)
SCAN=dict(zip(PLAIN,SCANS));SCAN.update({' ':0x39,'\r':0x1c,':':0x27,'"':0x28,'#':0x04,'>':0x34,'$':0x05})
TEST_COMMANDS=[('VER\r','Version 3.30'),('DIR\r','File(s)'),('DIR C:\\DOS\\DISK1\r','File(s)'),('DIR C:\\DOS\\DISK2\r','File(s)'),('DIR C:\\DOS\\DISK3\r','File(s)'),('ECHO 10 OPEN "C:\\BASIC.TXT" FOR OUTPUT AS #1 > C:\\CHECK.BAS\r',None),('ECHO 20 PRINT #1,"DOS64 BASIC OK" >> C:\\CHECK.BAS\r',None),('ECHO 30 CLOSE #1:SYSTEM >> C:\\CHECK.BAS\r',None),('C:\\GAMES\\GWBASIC.EXE C:\\CHECK.BAS\r',None),('TYPE C:\\BASIC.TXT\r','DOS64 BASIC OK'),('C:\\TP\\BUILD.BAT\r',None),('TYPE C:\\TP\\HELLO.TXT\r','HELLO FROM TURBO PASCAL 7.01 ON DOS 3.3'),('TYPE C:\\TP\\DONE.TXT\r','TP701_COMPILE_RUN_OK'),('COPY C:\\TP\\HELLO.EXE C:\\HELLO.EXE\r','1 File(s) copied'),('C:\\HELLO.EXE\r','HELLO FROM TURBO PASCAL 7.01 ON DOS 3.3'),('CHKDSK C:\r','bytes total disk space'),('DIR C:\\\r','File(s)')]
# Each fresh actual CLS is observed empty before the next command, preventing stale output acceptance.
COMMANDS=[item for command in TEST_COMMANDS for item in [('CLS\r',None),command]]
def keys(text):
 if any(c.upper() not in SCAN for c in text):raise ValueError('Unsupported exact script character')
 return [(SCAN[c.upper()]<<8)|ord(c) for c in text]
class CollectionScript:
 def __init__(self):self.stage='boot';self.step=-1;self.pending='';self.history=[];self.refills=[];self.receipts=[];self.submitted_at=None;self.seen=False
 def refill(self,s):
  used=s['ring_used']
  if type(used)!=int or not 0<=used<=15:raise ValueError('Coherent BIOS queue occupancy invalid')
  n=min(15-used,len(self.pending));text=self.pending[:n];self.pending=self.pending[n:];words=keys(text);self.history+=words
  if n:self.submitted_at=s['guest_instructions'];self.refills.append({'step':self.step,'ring_used':used,'count':n,'remaining':len(self.pending)})
  return words
 def observe(self,s):
  text=s['text'].replace('\xff',' ').replace('\xa0',' ')
  if self.pending:return self.refill(s)
  if self.stage=='done':return []
  if self.stage=='boot':
   if 'Enter new date' in text or 'Enter new time' in text:self.pending='\r';return self.refill(s)
   if not s['prompt']:return []
   if (s['mode'],s['columns'])!=(3,80):raise ValueError('C boot must begin coherent80columns')
  else:
   command,expected=COMMANDS[self.step]
   if expected and expected in text:self.seen=True
   progressed=self.submitted_at is not None and ((s['guest_instructions']-self.submitted_at)&0xffffffff)>4096
   if not progressed or not s['prompt'] or s['ring_used']!=0:return []
   if command=='CLS\r' and text.strip()!='C>':return []
   if expected and not self.seen:raise ValueError('Current DOS command output missing: '+command)
   if any(x in text for x in ['Bad command or file name','File not found','Syntax error','Out of memory','TP701_COMPILE_FAILED','lost clusters','cross-linked']):raise ValueError('DOS/application reported failure')
   self.receipts.append({'step':self.step,'command':command,'guest_instructions':s['guest_instructions'],'screen':text})
  self.step+=1
  if self.step==len(COMMANDS):self.stage='done';return []
  self.stage='commands';self.pending=COMMANDS[self.step][0];self.seen=False;return self.refill(s)
 def result(self):return {'accepted':self.stage=='done','stage':self.stage,'step':self.step,'commands':COMMANDS,'receipts':self.receipts,'input_key_words':self.history,'ring_refills':self.refills,'no_DOS_API_shortcuts':True}

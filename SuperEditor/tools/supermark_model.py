"""Independent whole-input semantic oracles. Native PETSCII bytes stay unchanged."""
import re
BASIC='END FOR NEXT DATA INPUT DIM READ LET GOTO RUN IF RESTORE GOSUB RETURN REM STOP ON WAIT LOAD SAVE VERIFY DEF POKE PRINT CONT LIST CLR CMD SYS OPEN CLOSE GET NEW TAB( TO FN SPC( THEN NOT STEP AND OR SGN INT ABS USR FRE POS SQR RND LOG EXP COS SIN TAN ATN PEEK LEN STR$ VAL ASC CHR$ LEFT$ RIGHT$ MID$'.split()
ASM=set('ADC AND ASL BCC BCS BEQ BIT BMI BNE BPL BRK BVC BVS CLC CLD CLI CLV CMP CPX CPY DEC DEX DEY EOR INC INX INY JMP JSR LDA LDX LDY LSR NOP ORA PHA PHP PLA PLP ROL ROR RTI RTS SBC SEC SED SEI STA STX STY TAX TAY TSX TXA TXS TYA'.split())
DIRECTIVES=set('.BYTE .WORD .DWORD .ADDR .RES .ASCIIZ .SEGMENT .ORG .PROC .ENDPROC .IF .IFDEF .IFNDEF .ELSE .ELSEIF .ENDIF .MACRO .ENDMACRO .REPEAT .ENDREPEAT .INCLUDE .INCBIN .IMPORT .EXPORT .IMPORTZP .EXPORTZP .DEFINE .ASSERT .SETCPU .SCOPE .ENDSCOPE'.split())
OPS=b'+-*/^=<>#:,()&|!~'
def folded(data):return bytes(x&0x7F if 0xC1<=x<=0xDA else x for x in data)
def lines(data):
 offset=0
 for line in data.split(b'\r')[:-1]:yield offset,line;offset+=len(line)+1
 if data and data[-1]!=13:yield offset,data[offset:]
def blocks(data,start=0):
 out=[];fence=language=regions=overflow=0
 for offset,line in lines(data):
  text=folded(line);a=start+offset;b=a+len(line);kind=level=0;body=a
  if fence:
   kind=5
   if line==b':'*fence:kind=6;body=b;fence=0
  else:
   language=0
   if not line:kind=1
   elif (m:=re.fullmatch(rb'(#{1,6}) (.*)',line,re.S)):
    kind=2;level=len(m[1]);body=a+level+1
   elif (m:=re.fullmatch(rb'( {0,6})(?:[-*]|[0-9]+\.) (.*)',line,re.S)) and len(m[1])%2==0:
    kind=3;level=len(m[1])//2;body=b-len(m[2])
   elif (m:=re.fullmatch(rb'(:{3,15})([^ :][^ ]*)(?: (.*))?',text,re.S)):
    n=len(m[1]);label=m[2];tail=m[3]
    if label==b'END':
     if n==3 and tail is None:
      if overflow:overflow-=1
      elif regions:kind=8;regions-=1;body=b
    elif label==b'REGION' and n==3:
     if regions==16:overflow+=1
     else:kind=7;regions+=1;body=a+n+len(label)+(tail is not None)
    else:
     kind=4;fence=n;body=b
     if tail is None:language={b'BASIC':1,b'ASM':2}.get(label,0)
  out.append(dict(kind=kind,start=a,end=b,body=body,level=level,language=language,fence=fence,regions=regions))
 return out

def inline(data,start=0,body_column=None):
 out=[]
 for offset,line in lines(data):
  stack=[];code=None;i=0;leading=2 if body_column is not None and offset==0 else 0;indent=0;column=body_column if body_column is not None and offset==0 else 0
  while i<len(line):
   c=line[i];p=start+offset+i
   if code is None and c==0x5C:
    if i+1<len(line):
     n=line[i+1]
     escape=n in b'*@\\' or (n==35 and i+column==0 and re.match(rb'#{1,6} ',line[i+1:])) or (n==58 and i+column==0 and re.match(rb':{3,15}[^: ]',line[i+1:])) or (n==45 and leading==0 and indent<=6 and indent%2==0 and line[i+1:i+3]==b'- ') or (n==46 and leading==1 and indent<=6 and indent%2==0 and line[i+1:i+3]==b'. ')
     if escape:out.append((2,0,1,p,p+1));leading=2;i+=2;continue
    leading=2;i+=1;continue
   if c==64 or (code is None and c==42):
    end=i+1
    while end<len(line) and line[end]==c:end+=1
    width=end-i;leading=2
    if c==64 and width==2:
     if code is None:code=p
     else:out.append((1,4,2,code,p));code=None
    elif c==42 and width<=3:
     if stack and stack[-1][1]==width:
      opened,_=stack.pop();out.append((1,width,width,opened,p))
     elif len(stack)<8:stack.append((p,width))
    i=end;continue
   if code is None and leading!=2:
    if c==32 and leading==0:indent=min(255,indent+1)
    elif 48<=c<=57:leading=1
    else:leading=2
   i+=1
 return out

def lex(data,language,start=0):
 if language not in (1,2):return []
 t=folded(data);i=0;out=[];plain=False
 def emit(a,b,style):out.append((start+a,start+b,style))
 while i<len(t):
  c=t[i]
  if c==13:plain=False;i+=1;continue
  if c==34 or (language==2 and c==39):
   end=i+1
   while end<len(t) and t[end] not in (c,13):end+=1
   if end<len(t) and t[end]==c:end+=1
   emit(i,end,9);i=end;plain=False;continue
  if language==2:
   if c==59:
    end=t.find(b'\r',i)
    if end<0:end=len(t)
    emit(i,end,10);i=end;continue
   if m:=re.match(rb'[A-Z_@.][A-Z0-9_@.]*',t[i:]):
    word=m[0];end=i+len(word)
    if end<len(t) and t[end]==58:emit(i,end+1,12);i=end+1;continue
    if word.decode('latin1') in ASM:emit(i,end,7)
    elif word.decode('latin1') in DIRECTIVES:emit(i,end,11)
    i=end;continue
   if c in (36,37):
    pattern=rb'\$[0-9A-F]+' if c==36 else rb'%[01]+'
    if m:=re.match(pattern,t[i:]):emit(i,i+len(m[0]),8);i+=len(m[0]);continue
  else:
   word=next((w.encode() for w in BASIC if t.startswith(w.encode(),i)),None)
   if word:
    end=i+len(word);plain=False
    if word==b'REM':
     end=t.find(b'\r',i)
     if end<0:end=len(t)
     emit(i,end,10);i=end;continue
    emit(i,end,7);i=end
    if word==b'DATA':
     quoted=False
     while i<len(t) and t[i]!=13:
      if t[i]==34:quoted=not quoted
      elif t[i]==58 and not quoted:break
      i+=1
    continue
   if (65<=c<=90) or c in b'_@.':
    if c==46 and not plain:
     pass
    else:plain=True;i+=1;continue
   if not (48<=c<=57):plain=False
  if 48<=c<=57 or (language==1 and c==46 and not plain):
   if language==1 and plain:i+=1;continue
   pattern=rb'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:E[+-]?[0-9]*)?' if language==1 else rb'[0-9]+'
   m=re.match(pattern,t[i:])
   if m:emit(i,i+len(m[0]),8);i+=len(m[0]);continue
  if c in OPS:emit(i,i+1,13);plain=False
  i+=1
 return out

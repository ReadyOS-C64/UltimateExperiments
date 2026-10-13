from pathlib import Path
from PIL import Image
import json,math
root=Path('logs/readyfs_c64u');base=root/'demo-v4-published-20261012';out=root/'demo-v5-edit-20261012'
steps=json.loads((base/'script.json').read_text());report=json.loads((base/'video-report.json').read_text());runs=json.loads((out/'stationary-runs.json').read_text());data=(out/'analysis.gray').read_bytes();size=192*136
live=[]
for i in range(0,len(data),size):
 h=Image.frombytes('L',(192,136),data[i:i+size]).crop((16,110,176,120)).histogram();live.append(sum(h[78:83])>=35)
protected=[];submits=[]
for n,s in enumerate(steps,1):
 a,b=s['start_seconds'],s['seconds']
 if n in (19,20,21):protected.append((a,b));continue
 false=[i/2 for i in range(math.ceil(a*2)+1,min(len(live),math.floor(b*2))) if not live[i]]
 submit=false[0] if false else b
 protected.append((max(0,a-.6),min(b,submit+.75)))
 submits.append({'step':n,'submit_seconds':submit,'end_seconds':b})
# Chapters need time to read their concise opening card.
chapters=json.loads((base/'chapters.json').read_text())
protected += [(c['seconds'],c['seconds']+5.0) for c in chapters]
protected += [(0,5)]
cuts=[]
for a,b,d in runs:
 # Preserve a generous readable lead and a pre-transition tail.
 segments=[(a+3.5,b-1.5)]
 for p,q in protected:
  new=[]
  for x,y in segments:
   if q<=x or p>=y:new.append((x,y))
   else:
    if x<p:new.append((x,p))
    if q<y:new.append((q,y))
  segments=new
 for x,y in segments:
  if y-x>=2.0:cuts.append([x,y])
fps=report['fps'];duration=report['seconds']
cuts=[[math.ceil(a*fps)/fps,math.floor(min(b,duration)*fps)/fps] for a,b in cuts]
cuts.sort();merged=[]
for a,b in cuts:
 if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
 else:merged.append([a,b])
stationary_removed=sum(b-a for a,b in merged)
# A clearly labelled jump omits only repetitive text entry. It ends before
# the complete 255-byte line, Home/End and overwrite demonstrations.
long_entry=[math.ceil(294*fps)/fps,math.floor(332*fps)/fps]
merged.append(long_entry);merged.sort()
keep=[];last=0
for a,b in merged:
 if a>last:keep.append([last,a])
 last=b
if last<duration:keep.append([last,duration])
plan={'original_seconds':duration,'removed_seconds':sum(b-a for a,b in merged),'new_seconds':sum(b-a for a,b in keep),'stationary_wait_seconds_removed':stationary_removed,'long_entry_cut':long_entry,'cuts':merged,'keep':keep,'protected_typing':protected,'submit_estimates':submits,'method':'One labelled repeated-text entry cut, plus stationary work-area intervals; preserve typing through gray-footer disappearance, all editing/history demonstrations, chapter-card reading time, and 5 seconds of each stationary run.'}
(out/'edit-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:plan[k] for k in ('original_seconds','removed_seconds','new_seconds','cuts')}))

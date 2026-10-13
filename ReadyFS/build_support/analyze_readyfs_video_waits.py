from pathlib import Path
from PIL import Image,ImageChops
import json
folder=Path('logs/readyfs_c64u/demo-v5-edit-20261012');data=(folder/'analysis.gray').read_bytes();size=192*136
frames=[Image.frombytes('L',(192,136),data[i:i+size]).crop((16,14,176,114)) for i in range(0,len(data),size)]
# Work-area changes; typing is protected separately by the event timeline.
changes=[0]
for a,b in zip(frames,frames[1:]):
 ha=a.crop((0,96,160,106)).histogram();hb=b.crop((0,96,160,106)).histogram()
 if sum(ha[78:83])>=35 and sum(hb[78:83])>=35:a=a.crop((0,0,160,80));b=b.crop((0,0,160,80))
 h=ImageChops.difference(a,b).histogram();changes.append(sum(h[22:]))
runs=[];start=0
for i,n in enumerate(changes):
 if n>=8:
  if (i-start)/2>=7:runs.append([start/2,i/2,(i-start)/2])
  start=i
if (len(frames)-start)/2>=7:runs.append([start/2,len(frames)/2,(len(frames)-start)/2])
(folder/'stationary-runs.json').write_text(json.dumps(runs,indent=2)+'\n')
print(json.dumps(runs))

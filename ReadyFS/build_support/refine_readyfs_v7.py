from pathlib import Path
from PIL import Image,ImageChops
import subprocess,json
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u';base=root/'demo-v6-published-20261012';work=root/'demo-v7-analysis-20261012'
for name,a,b in [('history',282,326),('previews',331,352),('move-preview',444,468),('delete-preview',544,566)]:
 file=work/f'{name}.gray';subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(a),'-t',str(b-a),'-i',str(base/'readyfs-demo.mp4'),'-vf','crop=768:544:96:144,fps=4,scale=192:136:flags=neighbor,format=gray','-f','rawvideo',str(file)],check=True)
 data=file.read_bytes();size=192*136;frames=[Image.frombytes('L',(192,136),data[i:i+size]) for i in range(0,len(data),size)];last=0;runs=[]
 for i,(x,y) in enumerate(zip(frames,frames[1:]),1):
  h=ImageChops.difference(x,y).histogram();changed=sum(h[22:])
  if changed>25:
   if (i-last)/4>=1.5:runs.append([a+last/4,a+i/4])
   last=i
 if (len(frames)-last)/4>=1.5:runs.append([a+last/4,a+len(frames)/4])
 print(name,json.dumps(runs));(work/f'{name}-holds.json').write_text(json.dumps(runs))

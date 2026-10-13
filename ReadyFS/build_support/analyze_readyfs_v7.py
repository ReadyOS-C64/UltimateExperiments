from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import subprocess,json
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u';base=root/'demo-v6-published-20261012';work=root/'demo-v7-analysis-20261012';steps=json.loads((base/'script.json').read_text());font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',14)
for label,a,b in [('copy',360,423),('move',468,528),('editor',215,282),('history',282,326),('mounts',60,124)]:
 times=[a+i*4 for i in range(int((b-a)/4)+1)];sheet=Image.new('RGB',(4*384,((len(times)+3)//4)*294),(10,14,24))
 for n,t in enumerate(times):
  file=work/f'{label}-{n:02d}.png';subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(t),'-i',str(base/'readyfs-demo.mp4'),'-frames:v','1',str(file)],check=True)
  # Crop the complete C64 picture only; this is an internal editorial view.
  im=Image.open(file).crop((96,144,864,688)).resize((384,272));x=n%4*384;y=n//4*294;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+8,y+273),f'{label} / {t:.1f}s',font=font,fill='white')
 sheet.save(work/f'{label}-contact.png')
print('contact sheets ready')

from pathlib import Path
import json,hashlib,subprocess
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u';base=root/'demo-v6-published-20261012';out=root/'demo-v7-published-20261012'
p=json.loads((out/'edit-plan.json').read_text());r=json.loads((out/'video-report.json').read_text())
assert r['frames']==sum(s['output_frames'] for s in p['segments'])
assert abs(r['seconds']-p['new_seconds'])<.025
assert 480<r['seconds']<500 and r['previous_seconds']-r['seconds']>120
assert r['typing_rate']==1.4
assert r['edit_notice_bounds'][1]+r['edit_notice_bounds'][3]<r['c64_picture_bounds'][1]
for c in p['cuts']:
 for a,b,meaning in p['protected_windows']:assert c['end']<=a or c['start']>=b,meaning
# Reviewed source windows: each file's completion and batch outcome must survive.
windows=[(380,382,'copy readme'),(392,394,'copy one'),(399,401,'copy two'),(412,414,'copy four'),(422,424,'copy three + summary'),(488,491,'move readme + verification skipped'),(496,498,'move one'),(503,505,'move two'),(512,514,'move four'),(526.5,529.2,'move three + summary')]
for a,b,meaning in windows:
 assert all(c['end']<=a+.021 or c['start']>=b-.021 for c in p['cuts']),meaning
old=json.loads((base/'script.json').read_text());new=json.loads((out/'script.json').read_text());assert len(old)==len(new)==37
for a,b in zip(old,new):
 assert {k:v for k,v in a.items() if k not in ('seconds','start_seconds')}=={k:v for k,v in b.items() if k not in ('seconds','start_seconds')}
 assert 0<=b['start_seconds']<=b['seconds']<r['seconds']
for f in ('hardware-checks.json','independent-transfer-checks.json','named-transfer-checks.json'):
 assert (base/f).read_bytes()==(out/f).read_bytes()
assert len(json.loads((out/'hardware-checks.json').read_text()))==62
assert hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest()==r['sha256']
# Extract actual edited frames for visual checks, using source -> output mapping.
def mapped(t):
 last=0
 for s in p['segments']:
  if t<s['source_start']:return last
  if t<=s['source_end']:return s['output_start']+t-s['source_start']
  last=s['output_end']
 return last
from PIL import Image,ImageDraw
samples=[(88.5,'Directory jump'),(259,'Long input'),(305,'First history page'),(351.9,'Named preview'),(381,'COPY readme'),(393,'COPY one'),(400,'COPY two'),(413,'COPY four'),(423,'COPY three'),(489,'MOVE readme'),(497,'MOVE one'),(504,'MOVE two'),(513,'MOVE four'),(527.5,'MOVE three'),(618,'Final evidence')]
canvas=Image.new('RGB',(1440,384*5),(235,237,241));d=ImageDraw.Draw(canvas)
for i,(t,title) in enumerate(samples):
 dest=root/'demo-v7-analysis-20261012'/f'render-{i:02d}.png'
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(mapped(t)),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(dest)],check=True)
 im=Image.open(dest).resize((480,360));x=i%3*480;y=i//3*384;canvas.paste(im,(x,y));d.text((x+6,y+362),f'{title} | output {mapped(t):.2f}s',fill=(0,0,0))
canvas.save(root/'demo-v7-analysis-20261012/render-review.png')
checks={'frame_count':'PASS','protected_actions':'PASS','ten_named_file_completions':'PASS','all_37_steps_unchanged':'PASS','original_62_check_evidence_unchanged':'PASS','overlay_geometry':'PASS','sha256':'PASS','seconds':r['seconds']}
(out/'editorial-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))

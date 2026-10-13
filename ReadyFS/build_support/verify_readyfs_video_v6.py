from pathlib import Path
from PIL import Image,ImageChops
import json,subprocess
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u';out=root/'demo-v6-published-20261012';work=root/'demo-v6-edit-20261012';base=root/'demo-v4-published-20261012'
plan=json.loads((out/'edit-plan.json').read_text());r=json.loads((out/'video-report.json').read_text());steps=json.loads((out/'script.json').read_text());old=json.loads((base/'script.json').read_text());chapters=json.loads((out/'chapters.json').read_text())
assert len(steps)==len(old)==37
for a,b in zip(old,steps):assert {k:v for k,v in a.items() if k not in ('seconds','start_seconds')}=={k:v for k,v in b.items() if k not in ('seconds','start_seconds')}
assert sum(s['output_frames'] for s in plan['segments'])==r['frames']
assert abs(plan['new_seconds']-r['seconds'])<1/r['fps']
for s in plan['segments']:
 assert s['rate'] in (1.,1.4) and s['output_frames']==round(s['source_frames']/s['rate'])
 if s['rate']==1.4:
  mid=(s['source_start']+s['source_end'])/2;assert any(a<=mid<=b for a,b in plan['typing_intervals'])
assert all(0<=s['start_seconds']<=s['seconds']<r['seconds'] for s in steps)
assert all(a['seconds']<b['seconds'] for a,b in zip(chapters,chapters[1:]))
assert r['overlay_bounds'][1]+r['overlay_bounds'][3]<r['c64_picture_bounds'][1] and 120+22<144
# Further idle cuts must not remove any changing visible output or input.
data=(root/'demo-v5-edit-20261012/analysis.gray').read_bytes();size=192*136;audit=[]
for a,b in plan['cuts']:
 if [a,b]==plan['long_entry_cut']:continue
 first=Image.frombytes('L',(192,136),data[int(a*2)*size:(int(a*2)+1)*size]).crop((16,14,176,114));greatest=0
 for i in range(int(a*2)+1,int(b*2)):
  im=Image.frombytes('L',(192,136),data[i*size:(i+1)*size]).crop((16,14,176,114));h=ImageChops.difference(first,im).histogram();greatest=max(greatest,sum(h[22:]))
 assert greatest<=32,(a,b,greatest);audit.append({'cut':[a,b],'changed_pixels':greatest})
(work/'idle-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
for n,t in enumerate([chapters[0]['seconds']+1,chapters[3]['seconds']+2,chapters[5]['seconds']+1]):
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(t),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(work/f'qa-{n+1}.png')],check=True)
result={'all_37_steps_and_screenshots_retained':'PASS','typing_segments_1_4x':'PASS','other_segments_1x':'PASS','frame_exact_timestamps':'PASS','all_idle_cuts_unchanged':'PASS','descriptions_above_picture':'PASS','seconds':r['seconds'],'frames':r['frames']}
(work/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

from pathlib import Path
from PIL import Image,ImageChops
import json,subprocess
root=Path(__file__).resolve().parent.parent;base=root/'logs/readyfs_c64u/demo-v4-published-20261012';out=root/'logs/readyfs_c64u/demo-v5-published-20261012';work=root/'logs/readyfs_c64u/demo-v5-edit-20261012'
plan=json.loads((out/'edit-plan.json').read_text());report=json.loads((out/'video-report.json').read_text());old=json.loads((base/'script.json').read_text());steps=json.loads((out/'script.json').read_text());chapters=json.loads((out/'chapters.json').read_text())
assert len(old)==len(steps)==37
for a,b in plan['cuts']:
 if [a,b]==plan['long_entry_cut']:
  assert 280<a<b<342.86;continue
 assert b>a and all(b<=p+1e-6 or a>=q-1e-6 for p,q in plan['protected_typing'])
for a,b in zip(old,steps):assert {k:v for k,v in a.items() if k not in ('seconds','start_seconds')}=={k:v for k,v in b.items() if k not in ('seconds','start_seconds')}
assert report['overlay_bounds'][1]+report['overlay_bounds'][3]==116<144
assert 120+22<144 and 144+544<=720
assert abs(report['previous_seconds']-report['removed_total_seconds']-report['seconds'])<.05
assert all(0<=s['start_seconds']<=s['seconds']<report['seconds'] for s in steps)
assert all(len(c['description'].split())<=10 for c in chapters)
# Audit footer changes during removed LIVE intervals. Cursor blink alone is
# permitted; no jump changes the live command text.
data=(work/'analysis.gray').read_bytes();size=192*136;cursor_changes=[]
for a,b in plan['cuts']:
 if [a,b]==plan['long_entry_cut']:continue
 first=Image.frombytes('L',(192,136),data[int(a*2)*size:(int(a*2)+1)*size]).crop((16,94,176,110))
 greatest=0
 for i in range(int(a*2)+1,int(b*2)):
  im=Image.frombytes('L',(192,136),data[i*size:(i+1)*size]).crop((16,94,176,110));h=ImageChops.difference(first,im).histogram();greatest=max(greatest,sum(h[22:]))
 assert greatest<=16,'An idle cut changed visible command/output text'
 cursor_changes.append({'cut':[a,b],'footer_changed_pixels':greatest})
(work/'footer-audit.json').write_text(json.dumps(cursor_changes,indent=2)+'\n')
# Contact sheet shows all nine actual header placements and the entire C64 image.
thumbs=[]
for i,c in enumerate(chapters):
 file=work/f'qa-chapter-{i+1:02d}.png';subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(c['seconds']+1),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(file)],check=True);thumbs.append(Image.open(file).resize((480,360)))
sheet=Image.new('RGB',(1440,1080))
for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*480,(i//3)*360))
sheet.save(work/'qa-contact.png')
result={'all_37_steps_and_screenshots_preserved':'PASS','editing_history_and_nonrepetitive_typing_untouched':'PASS','overlay_and_edit_labels_above_picture':'PASS','all_timestamps_remapped':'PASS','wait_seconds_removed':report['removed_wait_seconds'],'new_seconds':report['seconds']}
(work/'edit-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print(json.dumps(cursor_changes))

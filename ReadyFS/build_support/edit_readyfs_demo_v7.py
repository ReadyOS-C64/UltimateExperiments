#!/usr/bin/env python3
"""Make a meaning-first editorial cut from the published v6 take."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,subprocess,shutil,hashlib
root=Path(__file__).resolve().parent.parent
base=root/'logs/readyfs_c64u/demo-v6-published-20261012'
work=root/'logs/readyfs_c64u/demo-v7-analysis-20261012'
out=root/'logs/readyfs_c64u/demo-v7-published-20261012';out.mkdir(exist_ok=True)
p=json.loads((work/'edit-plan.json').read_text());old=json.loads((base/'video-report.json').read_text());fps=old['fps']
def mapped(t):
 last=0
 for s in p['segments']:
  if t<s['source_start']:return last
  if t<=s['source_end']:return s['output_start']+(t-s['source_start'])
  last=s['output_end']
 return last
for f in base.glob('*.png'):shutil.copy2(f,out/f.name)
chapters=json.loads((base/'chapters.json').read_text());steps=json.loads((base/'script.json').read_text())
for c in chapters:c['seconds']=mapped(c['seconds'])
for s in steps:
 for k in ('seconds','start_seconds'):s[k]=mapped(s[k])
filters=[];n=len(p['segments']);filters.append(f'[0:v]split={n}'+''.join(f'[s{i}]' for i in range(n)))
for i,s in enumerate(p['segments']):
 a=round(s['source_start']*fps);b=round(s['source_end']*fps)
 hold=f',tpad=stop_mode=clone:stop_duration={s["hold_frames"]/fps}' if s['hold_frames'] else ''
 filters.append(f'[s{i}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS{hold},trim=end_frame={s["output_frames"]},setpts=PTS-STARTPTS[k{i}]')
filters.append(''.join(f'[k{i}]' for i in range(n))+f'concat=n={n}:v=1:a=0,setsar=1[base]')
# Replace the old label strip, entirely above the C64 picture (which starts y144).
labels=[('Command entry shortened',[(mapped(t),mapped(t)+2) for t in (31.5,198,447,547,599)]),('Additional directory pages omitted',[(mapped(69.5),mapped(69.5)+3)]),('Repeated text entry shortened',[(mapped(248.8),mapped(248.8)+3)]),('History · shorter reading pauses',[(mapped(292.2),mapped(292.2)+2.5)]),('Copy · transfer waits shortened',[(mapped(370.8),mapped(423))]),('Move · transfer waits shortened',[(mapped(480.5),mapped(528))]),('Five files + three folders · preview only',[(mapped(349.25),mapped(352.5))])]
args=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(base/'readyfs-demo.mp4')]
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18);prev='base'
for i,(title,ranges) in enumerate(labels):
 im=Image.new('RGBA',(960,24),(9,14,27,255));ImageDraw.Draw(im).text((52,1),title,font=font,fill=(183,199,223,255));path=work/f'label-{i}.png';im.save(path);args+=['-loop','1','-i',str(path)]
 enabled='+'.join(f'between(t,{a},{b})' for a,b in ranges)
 filters.append(f"[{prev}][{i+1}:v]overlay=x=0:y=118:enable='{enabled}':eof_action=pass[v{i}]");prev=f'v{i}'
filters.append(f'[{prev}]null[final]');(work/'render-filter.txt').write_text(';\n'.join(filters))
args+=['-filter_complex_script',str(work/'render-filter.txt'),'-map','[final]','-frames:v',str(sum(s['output_frames'] for s in p['segments'])),'-r',str(fps),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'readyfs-demo.mp4')]
subprocess.run(args,check=True)
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-show_entries','stream=duration,nb_frames','-of','json',str(out/'readyfs-demo.mp4')]))['streams'][0]
report={**old,'seconds':float(probe['duration']),'frames':int(probe['nb_frames']),'complete_frames':int(probe['nb_frames']),'megabytes':(out/'readyfs-demo.mp4').stat().st_size/1e6,'sha256':hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest(),'previous_seconds':p['previous_seconds'],'editing':'Meaning-first cut: repeated entry, listing pages and transfer waits condensed; complete commands, meaningful editing actions and file outcomes retained. First named selection receives extra reading time. Existing input playback remains 1.4×. Chapter cards at 95% opacity stay above the C64 picture; edit notices also stay outside it.','additional_cuts':len(p['cuts']),'additional_seconds_removed':p['extra_removed_seconds'],'added_reading_seconds':p['first_preview_reading_hold_seconds'],'editorial_savings_by_kind':p['seconds_saved_by_kind'],'editorial_source':'demo-v6-published-20261012','edit_notice_bounds':[0,118,960,24]}
assert report['frames']==sum(s['output_frames'] for s in p['segments'])
for name,data in [('chapters.json',chapters),('script.json',steps),('video-report.json',report),('edit-plan.json',p)]: (out/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ('hardware-checks.json','independent-transfer-checks.json','named-transfer-checks.json'):shutil.copy2(base/name,out/name)
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds'];vtt+=f'{i+1}\n{stamp(c["seconds"])} --> {stamp(end)}\n{c["title"]}\n\n'
(out/'captions.vtt').write_text(vtt)
md=['# ReadyFS: the recorded script','','Edited for comprehension: repeated entry, listing pages and transfer waits are condensed. Complete commands, meaningful editing actions and file outcomes remain. Input playback remains 1.4×; the first named-file preview receives extra reading time. Descriptions stay above the C64 picture. Hardware evidence comes from the same passing 62-check take.','','Mount paths are session hints and may have changed elsewhere.','']
for i,c in enumerate(chapters):
 md+=['## '+c['title'],'',c['description'],'']
 for n,s in enumerate(steps):
  if s['group']!=i:continue
  md += [f'### Step {n+1} · {stamp(s["start_seconds"])}','',s['explanation'],'','```text',s['input'],'```','',f'![Actual C64 display after step {n+1}]({s["screenshot"]})','','```text',s['screen'].rstrip(),'```','']
  for page in s.get('pages',[]):md+=['Earlier preview page:','',f'![Actual preview page]({page["screenshot"]})','','```text',page['screen'].rstrip(),'```','']
(out/'script.md').write_text('\n'.join(md))
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(chapters[2]['seconds']+1),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(out/'poster.png')],check=True)
print(json.dumps({k:report[k] for k in ('seconds','frames','megabytes','sha256','additional_cuts')}),flush=True)

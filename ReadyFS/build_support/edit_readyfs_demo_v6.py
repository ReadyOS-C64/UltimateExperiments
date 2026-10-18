#!/usr/bin/env python3
"""Tighten stationary waits; keep chapter text strictly outside C64 pixels."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,subprocess,shutil,hashlib,math,sys
root=Path(__file__).resolve().parent.parent
base=root/'logs/readyfs_c64u/demo-v4-published-20261012';raw=root/'logs/readyfs_c64u/demo-v4-transfer-tour-20261012a'
work=root/'logs/readyfs_c64u/demo-v6-edit-20261012';out=root/'logs/readyfs_c64u/demo-v6-published-20261012';out.mkdir(exist_ok=True)
plan=json.loads((work/'edit-plan.json').read_text());old=json.loads((base/'video-report.json').read_text());fps=old['fps'];offset=old['setup_trim_seconds']
chapters=json.loads((base/'chapters.json').read_text());steps=json.loads((base/'script.json').read_text())
def mapped(t):
 previous=0.0
 for segment in plan['segments']:
  a,b=segment['source_start'],segment['source_end']
  if t<a:return previous
  if t<=b:return segment['output_start']+(t-a)/(b-a)*(segment['output_end']-segment['output_start'])
  previous=segment['output_end']
 return previous
labels=[('Help & directories','Full commands and shortcuts share the same help.'),('Native mounts','Mount paths are hints and may become stale.'),('Disk to host, and back','Copy both ways; compare when you choose.'),('Edit a command','Insert, overwrite and navigate a long command.'),('History & paging','Recall commands, restore drafts and page output.'),('Preview & copy','List selected files, then copy with verification.'),('Move without readback','Use -nv; check the moved files independently.'),('Delete test copies','Preview deletion; keep the original source.'),('Checks complete','62 checks passed; original settings restored.')]
fontdir=Path('/System/Library/Fonts/Supplemental');titlefont=ImageFont.truetype(str(fontdir/'Arial Bold.ttf'),28);bodyfont=ImageFont.truetype(str(fontdir/'Arial.ttf'),21)
for i,c in enumerate(chapters):
 c['seconds']=mapped(c['seconds']);c['title']=f'{i+1:02d} · '+labels[i][0];c['description']=labels[i][1];c['callout_seconds']=4.8
 im=Image.new('RGBA',(856,104),(0,0,0,0));d=ImageDraw.Draw(im);d.rounded_rectangle((0,0,855,103),radius=16,fill=(23,32,51,242),outline=(83,105,137,242))
 d.rounded_rectangle((20,20,24,83),radius=2,fill=(136,213,221,255));title=c['title'].replace(' · ',' / ')
 assert titlefont.getlength(title)<790 and bodyfont.getlength(c['description'])<790
 d.text((42,15),title,font=titlefont,fill=(243,247,255,255));d.text((42,58),c['description'],font=bodyfont,fill=(211,222,241,255));im.save(work/f'header-{i+1:02d}.png')
for s in steps:
 s['seconds']=mapped(s['seconds']);s['start_seconds']=mapped(s['start_seconds'])
 for key in ('screenshot','editor_screenshot'):
  if s.get(key):shutil.copy2(base/s[key],out/s[key])
 for page in s.get('pages',[]):shutil.copy2(base/page['screenshot'],out/page['screenshot'])
# Frame-exact cuts from the original undecorated capture. Only input segments
# play at 1.4x; physical execution/results and page-reading pauses remain 1x.
filters=[];count=len(plan['segments']);filters.append(f'[0:v]split={count}'+''.join(f'[s{i}]' for i in range(count)))
for i,segment in enumerate(plan['segments']):
 a=round((segment['source_start']+offset)*fps);b=round((segment['source_end']+offset)*fps);rate=segment['rate'];n=segment['output_frames']
 filters.append(f'[s{i}]trim=start_frame={a}:end_frame={b},setpts=(PTS-STARTPTS)/{rate},fps=fps={fps}:start_time=0:round=near,tpad=stop_mode=clone:stop_duration=0.06,trim=end_frame={n},setpts=PTS-STARTPTS[k{i}]')
filters.append(''.join(f'[k{i}]' for i in range(count))+f'concat=n={count}:v=1:a=0,pad=960:720:96:144:color=0x090e1b,setsar=1[base]')
args=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(raw/'readyfs-demo.mp4')]
for i in range(9):args+=['-loop','1','-i',str(work/f'header-{i+1:02d}.png')]
label=Image.new('RGBA',(200,22),(0,0,0,0));ImageDraw.Draw(label).text((0,0),'Wait shortened',font=ImageFont.truetype(str(fontdir/'Arial.ttf'),18),fill=(155,169,194,255));label.save(work/'wait-label.png');args+=['-loop','1','-i',str(work/'wait-label.png')]
prev='base'
for i,c in enumerate(chapters):
 a=c['seconds'];b=a+c['callout_seconds'];filters.append(f'[{i+1}:v]format=rgba,fade=t=in:st={a}:d=0.2:alpha=1,fade=t=out:st={b-.5}:d=0.5:alpha=1[h{i}]');filters.append(f'[{prev}][h{i}]overlay=x=52:y=12:enable=\'between(t,{a},{b})\':eof_action=pass[v{i}]');prev=f'v{i}'
# A brief transparent edit label stays in the empty header band at each jump.
enabled='+'.join(f'between(t,{mapped(a)},{mapped(a)+1.3})' for a,b in plan['cuts'] if [a,b]!=plan['long_entry_cut'])
filters.append(f"[{prev}][10:v]overlay=x=52:y=120:enable='{enabled}':eof_action=pass[edited]");prev='edited'
entry_label=Image.new('RGBA',(360,22),(0,0,0,0));ImageDraw.Draw(entry_label).text((0,0),'Repeated text entry shortened',font=ImageFont.truetype(str(fontdir/'Arial.ttf'),18),fill=(155,169,194,255));entry_label.save(work/'entry-label.png');args+=['-loop','1','-i',str(work/'entry-label.png')]
t=mapped(plan['long_entry_cut'][0]);filters.append(f"[{prev}][11:v]overlay=x=52:y=120:enable='between(t,{t},{t+3})':eof_action=pass[entry]");prev='entry'
filters.append(f'[{prev}]null[final]');(work/'filter.txt').write_text(';\n'.join(filters))
args+=['-filter_complex_script',str(work/'filter.txt'),'-map','[final]','-t',str(plan['new_seconds']),'-r',str(fps),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'readyfs-demo.mp4')]
subprocess.run(args,check=True)
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-show_entries','stream=width,height,duration,nb_frames','-of','json',str(out/'readyfs-demo.mp4')]))['streams'][0]
report={**old,'seconds':float(probe['duration']),'frames':int(probe['nb_frames']),'complete_frames':int(probe['nb_frames']),'megabytes':(out/'readyfs-demo.mp4').stat().st_size/1e6,'sha256':hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest(),'editing':'Stationary waits and one repetitive text-entry section shortened with visible edit labels. Command typing and input editing play at 1.4×; physical execution, results and page-reading pauses stay at recorded speed. Concise chapter cards at 95% opacity appear only in a separate top band; no descriptions cover the C64 picture.','previous_seconds':plan['previous_edited_seconds'],'original_seconds':old['seconds'],'typing_rate':1.4,'typing_speed_seconds_saved':plan['typing_speed_seconds_saved'],'removed_wait_seconds':plan['stationary_wait_seconds_removed'],'removed_total_seconds':plan['removed_seconds'],'removed_text_entry_seconds':plan['long_entry_cut'][1]-plan['long_entry_cut'][0],'wait_cuts':len(plan['cuts'])-1,'total_cuts':len(plan['cuts']),'overlay_bounds':[52,12,856,104],'c64_picture_bounds':[96,144,768,544],'chapter_track':'Navigation-only titles; no captions over the working area.'}
for name,data in [('chapters.json',chapters),('script.json',steps),('video-report.json',report),('edit-plan.json',plan)]: (out/name).write_text(json.dumps(data,indent=2)+'\n')
for name in ('hardware-checks.json','independent-transfer-checks.json','named-transfer-checks.json'):shutil.copy2(base/name,out/name)
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds'];vtt+=f'{i+1}\n{stamp(c["seconds"])} --> {stamp(end)}\n{c["title"]}\n\n'
(out/'captions.vtt').write_text(vtt)
md=['# ReadyFS: the recorded script','','Idle waits and one repetitive text-entry section have been shortened. Command typing and input editing play at 1.4×. Physical execution, results and page-reading pauses remain at their recorded speed. Descriptions stay above the C64 picture. Hardware evidence is from the same passing 62-check take.','','Mount paths are session hints and may have changed elsewhere.','']
for i,c in enumerate(chapters):
 md+=['## '+c['title'],'',c['description'],'']
 for n,s in enumerate(steps):
  if s['group']!=i:continue
  md += [f'### Step {n+1} · {stamp(s["start_seconds"])}','',s['explanation'],'','```text',s['input'],'```','',f'![Actual C64 display after step {n+1}]({s["screenshot"]})','','```text',s['screen'].rstrip(),'```','']
  for page in s.get('pages',[]):md+=['Earlier preview page:','',f'![Actual preview page]({page["screenshot"]})','','```text',page['screen'].rstrip(),'```','']
(out/'script.md').write_text('\n'.join(md))
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(chapters[2]['seconds']+1),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(out/'poster.png')],check=True)
print(json.dumps(report),flush=True)

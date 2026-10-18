#!/usr/bin/env python3
"""Trim only setup, burn readable chapter cards into actual VIC footage, export tour."""
from pathlib import Path
import json,sys,subprocess,hashlib,shutil,math
from PIL import Image,ImageDraw,ImageFont
source,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
assert (source/'status.txt').read_text().strip()=='success'
chapters=json.loads((source/'chapters.json').read_text());steps=json.loads((source/'script.json').read_text());raw=json.loads((source/'video-report.json').read_text())
independent=json.loads((source/'independent-transfer-checks.json').read_text())
assert independent['both_directions_independent_sha256']=='PASS' and independent['original_drives_restored']=='PASS'
shutil.copy2(source/'independent-transfer-checks.json',out/'independent-transfer-checks.json')
named=json.loads((source/'named-transfer-checks.json').read_text());shutil.copy2(source/'named-transfer-checks.json',out/'named-transfer-checks.json')
fps=raw['fps'];cut=math.floor(chapters[0]['seconds']*fps)/fps
for chapter in chapters:chapter['seconds']=max(0,chapter['seconds']-cut)
chapters[0]['seconds']=0
for step in steps:
 if step['input']=='DIR 9:/FOLDER':step['explanation']='Show the boundary of a flat mounted disk: a nested folder path is unsupported, and the error appears in red.'
 step['seconds']=max(0,step['seconds']-cut);step['start_seconds']=max(0,step['start_seconds']-cut)
 shutil.copy2(source/step['screenshot'],out/step['screenshot'])
 for page in step.get('pages',[]):shutil.copy2(source/page['screenshot'],out/page['screenshot'])
 if step.get('editor_screenshot'):shutil.copy2(source/step['editor_screenshot'],out/step['editor_screenshot'])
font_dir=Path('/System/Library/Fonts/Supplemental')
title_font=ImageFont.truetype(str(font_dir/'Arial Bold.ttf'),24)
body_font=ImageFont.truetype(str(font_dir/'Arial.ttf'),19)
label_font=ImageFont.truetype(str(font_dir/'Arial Bold.ttf'),11)
def wrap(text,font,width):
 lines=['']
 for word in text.split():
  trial=(lines[-1]+' '+word).strip()
  if font.getlength(trial)>width and lines[-1]:lines.append(word)
  else:lines[-1]=trial
 return lines
cards=[]
for i,chapter in enumerate(chapters):
 im=Image.new('RGBA',(856,138),(0,0,0,0));draw=ImageDraw.Draw(im)
 draw.rounded_rectangle((0,0,855,137),radius=20,fill=(23,32,51,242),outline=(93,113,151,242),width=1)
 draw.rounded_rectangle((22,18,27,118),radius=2,fill=(136,213,221,255))
 draw.text((44,17),'READYFS / PHYSICAL C64 / 1 MHz',font=label_font,fill=(169,187,222,255))
 title=chapter['title'].replace(' · ',' / ')
 assert title_font.getlength(title)<788,title
 draw.text((44,36),title,font=title_font,fill=(243,247,255,255))
 lines=wrap(chapter['description'],body_font,788)
 assert len(lines)<=3,(title,lines)
 for n,line in enumerate(lines):draw.text((44,70+n*21),line,font=body_font,fill=(211,222,241,255))
 file=source/f'callout-{i+1:02d}.png';im.save(file);cards.append(file)
 duration=max(6,min(11,len(chapter['description'].split())/2.8+1.5))
 if i+1<len(chapters):duration=min(duration,chapters[i+1]['seconds']-chapter['seconds']-.1)
 chapter['callout_seconds']=duration
args=['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(source/'readyfs-demo.mp4')]
for card in cards:args+=['-loop','1','-i',str(card)]
filters=[f'[0:v]trim=start={cut},setpts=PTS-STARTPTS,pad=960:720:96:156:color=0x090e1b,setsar=1[base]']
previous='base'
for i,c in enumerate(chapters):
 start=c['seconds'];end=start+c['callout_seconds'];label=f'card{i}';next_label=f'v{i}'
 filters.append(f'[{i+1}:v]format=rgba,fade=t=in:st={start}:d=0.3:alpha=1,fade=t=out:st={end-.7}:d=0.7:alpha=1[{label}]')
 filters.append(f'[{previous}][{label}]overlay=x=52:y=8:enable=\'between(t,{start},{end})\':eof_action=pass[{next_label}]');previous=next_label
args+=['-filter_complex',';'.join(filters),'-map',f'[{previous}]','-t',str(raw['seconds']-cut),'-r',str(fps),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'readyfs-demo.mp4')]
subprocess.run(args,check=True)
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-show_entries','stream=width,height,duration,nb_frames','-of','json',str(out/'readyfs-demo.mp4')]))['streams'][0]
events=[json.loads(line) for line in (source/'events.jsonl').read_text().splitlines()]
checks=[{'case':e['case'],'result':e['result']} for e in events if 'case' in e and e.get('result')=='PASS']
report={**raw,'seconds':float(probe['duration']),'dimensions':[probe['width'],probe['height']],'frames':int(probe['nb_frames']),'source_frames':raw['frames'],'source_complete_frames':raw['complete_frames'],'complete_frames':int(probe['nb_frames']),'checks':len(checks),'megabytes':(out/'readyfs-demo.mp4').stat().st_size/1e6,'sha256':hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest(),'editing':'Setup trimmed before first chapter; all demonstrations retain original speed. Rounded explanatory chapter cards are burned into this downloadable MP4 at 95% opacity with reading time and fades.','source_take':source.name,'setup_trim_seconds':cut,'native_mount_reporting':'Session-only hints; no network or relay in ReadyFS.','independent_transfer_checks':independent,'named_transfer_checks':named}
for name,data in [('chapters.json',chapters),('script.json',steps),('hardware-checks.json',checks),('video-report.json',report)]:
 (out/name).write_text(json.dumps(data,indent=2)+'\n')
def stamp(seconds):
 ms=round(seconds*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds']
 vtt+=f"{i+1}\n{stamp(c['seconds'])} --> {stamp(end)}\n{c['title']}\n{c['description']}\n\n"
(out/'captions.vtt').write_text(vtt)
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(chapters[1]['seconds']+3),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(out/'poster.png')],check=True)
md=['# ReadyFS: the recorded script','', 'Physical C64 Ultimate, 1 MHz. Screenshots and console snapshots are from the recording.', '', '**Mount-path caveat:** paths are last mounted by ReadyFS during this session, may have changed elsewhere, and are not a live firmware query. No relay or network is used by ReadyFS.','']
for i,c in enumerate(chapters):
 md += ['## '+c['title'],'',c['description'],'']
 for n,s in enumerate(steps):
  if s['group']!=i:continue
  md += [f'### Step {n+1} · {stamp(s["start_seconds"])}','',s['explanation'],'','```text',s['input'],'```','',f'![Actual C64 display after step {n+1}]({s["screenshot"]})','','Actual console snapshot:','','```text',s['screen'].rstrip(),'```','']
  for page in s.get('pages',[]):
   md += ['Earlier preview page:','',f'![Actual preview page]({page["screenshot"]})','','```text',page['screen'].rstrip(),'```','']
(out/'script.md').write_text('\n'.join(md))
print(json.dumps(report),flush=True)

"""Assemble complete chapters from real-time hardware takes, without retiming."""
from pathlib import Path
import json,sys,subprocess,math,hashlib,shutil
first,second,third,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
fps=985248/19656
first_chapters=json.loads((first/'chapters.json').read_text())
events=[json.loads(line) for line in (first/'events.jsonl').read_text().splitlines()]
chapter_events=[e for e in events if 'chapter' in e]
first_epoch=chapter_events[0]['time']-3
for item,event in zip(first_chapters,chapter_events):item['seconds']=event['time']-first_epoch
first_chapters[0]['seconds']=0
parts=[first,second,third];lists=[first_chapters]+[json.loads((p/'chapters.json').read_text()) for p in parts[1:]]
reports=[json.loads((p/'video-report.json').read_text()) for p in parts]
limits=[(0,math.floor(lists[0][3]['seconds']*fps)),(math.floor(lists[1][0]['seconds']*fps),math.floor(next(c['seconds'] for c in lists[1] if c['title'].startswith('07'))*fps)),(math.floor(lists[2][0]['seconds']*fps),reports[2]['frames'])]
assert all(end>start for start,end in limits)
args=['/opt/homebrew/bin/ffmpeg','-v','error','-y']
for p in parts:args+=['-i',str(p/'readyfs-demo.mp4')]
filters=[]
for i,(start,end) in enumerate(limits):filters.append(f'[{i}:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[v{i}]')
filters.append('[v0][v1][v2]concat=n=3:v=1:a=0[v]')
args+=['-filter_complex',';'.join(filters),'-map','[v]','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-r',str(fps),'-movflags','+faststart',str(out/'readyfs-demo.mp4')]
subprocess.run(args,check=True)
chapters=[];offset=0;checks=[]
for i,(p,items,(start,end)) in enumerate(zip(parts,lists,limits)):
 for c in items:
  if start/fps-.03<=c['seconds']<end/fps:
   c=dict(c);c['seconds']=offset+max(0,c['seconds']-start/fps);chapters.append(c)
 if i==0:epoch=first_epoch
 else:epoch=json.loads((p/'capture-timing.json').read_text())['first_packet_epoch']
 for e in [json.loads(line) for line in (p/'events.jsonl').read_text().splitlines()]:
  if e.get('result')=='PASS' and 'case' in e and epoch+start/fps<=e['time']<epoch+end/fps:checks.append({'take':p.name,'case':e['case']})
 offset+=(end-start)/fps
assert len(chapters)==9,(len(chapters),chapters)
video=out/'readyfs-demo.mp4'
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_entries','stream=nb_read_frames,width,height,duration,r_frame_rate','-of','json',str(video)]))['streams'][0]
expected_frames=sum(end-start for start,end in limits)
assert abs(int(probe['nb_read_frames'])-expected_frames)<=1,(probe,expected_frames)
report={'source':'physical C64 Ultimate VIC UDP stream','cpu_mhz':1,'frames':int(probe['nb_read_frames']),'fps':fps,'seconds':float(probe['duration']),'dimensions':[probe['width'],probe['height']],'audio':'silent; ReadyFS produces no music','checks':len(checks),'megabytes':video.stat().st_size/1e6,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'editing':'Three hardware takes joined at chapter boundaries; no cuts within selected demonstrations or speed changes. Initial capture pixel order corrected.','source_takes':[p.name for p in parts],'source_frame_ranges':limits,'source_missing_frames':[r['duplicated_missing_frames'] for r in reports]}
(out/'chapters.json').write_text(json.dumps(chapters,indent=2)+'\n');(out/'video-report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'hardware-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
def stamp(sec):
 ms=round(sec*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds']
 vtt+=f"{i+1}\n{stamp(c['seconds'])} --> {stamp(end)}\n{c['title']}\n{c['description']}\n\n"
(out/'captions.vtt').write_text(vtt);shutil.copy2(first/'poster.png',out/'poster.png')
print(json.dumps(report),flush=True)

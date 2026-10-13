"""Join complete passing chapters from two real-time physical C64 takes."""
from pathlib import Path
import json,sys,subprocess,math,hashlib,shutil
first,second,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
assert (second/'status.txt').read_text().strip()=='success','Nested workflow did not pass'
fps=985248/19656;parts=[first,second]
chapters_by_take=[json.loads((p/'chapters.json').read_text()) for p in parts]
reports=[json.loads((p/'video-report.json').read_text()) for p in parts]
cut=next(c['seconds'] for c in chapters_by_take[0] if c['title'].startswith('04'))
limits=[(0,math.floor(cut*fps)),(math.floor(chapters_by_take[1][0]['seconds']*fps),reports[1]['frames'])]
args=['/opt/homebrew/bin/ffmpeg','-v','error','-y']
for p in parts:args+=['-i',str(p/'readyfs-demo.mp4')]
filters=[f'[{i}:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]' for i,(a,b) in enumerate(limits)]
filters+=['[v0][v1]concat=n=2:v=1:a=0[v]']
args+=['-filter_complex',';'.join(filters),'-map','[v]','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-r',str(fps),'-movflags','+faststart',str(out/'readyfs-demo.mp4')]
subprocess.run(args,check=True)
chapters=[];offset=0;checks=[]
for take_index,(p,items,(a,b)) in enumerate(zip(parts,chapters_by_take,limits)):
 epoch=json.loads((p/'capture-timing.json').read_text())['first_packet_epoch']
 # Events use exact chapter times; frame cuts round down by less than 20 ms.
 # Do not drop a final assertion or admit a prelude assertion at that boundary.
 event_start=epoch+(items[0]['seconds'] if take_index else 0)
 event_end=epoch+(reports[take_index]['seconds'] if take_index else cut)
 for c in items:
  if a/fps-.03<=c['seconds']<b/fps:
   c=dict(c);c['seconds']=offset+max(0,c['seconds']-a/fps);chapters.append(c)
 for line in (p/'events.jsonl').read_text().splitlines():
  e=json.loads(line)
  if e.get('result')=='PASS' and 'case' in e and event_start<=e['time']<event_end:
   checks.append({'take':p.name,'case':e['case']})
 offset+=(b-a)/fps
assert len(chapters)==7,chapters
chapters[0]['seconds']=0
video=out/'readyfs-demo.mp4'
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_entries','stream=nb_read_frames,width,height,duration,r_frame_rate','-of','json',str(video)]))['streams'][0]
expected=sum(b-a for a,b in limits);assert abs(int(probe['nb_read_frames'])-expected)<=1,(probe,expected)
report={'source':'physical C64 Ultimate VIC UDP stream','cpu_mhz':1,'frames':int(probe['nb_read_frames']),'fps':fps,'seconds':float(probe['duration']),'dimensions':[probe['width'],probe['height']],'audio':'silent; ReadyFS produces no music','checks':len(checks),'megabytes':video.stat().st_size/1e6,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'editing':'Two physical takes joined at the chapter 4 boundary. Original speed; no cuts inside selected demonstrations. The second take uses a fresh marker-owned fixture after fixing canonical-path admission.','source_takes':[p.name for p in parts],'source_frame_ranges':limits,'source_missing_frames':[r['duplicated_missing_frames'] for r in reports],'duplicated_missing_frames':sum(r['duplicated_missing_frames'] for r in reports)}
for name,data in [('chapters.json',chapters),('video-report.json',report),('hardware-checks.json',checks)]:
 (out/name).write_text(json.dumps(data,indent=2)+'\n')
def stamp(sec):
 ms=round(sec*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds']
 vtt+=f"{i+1}\n{stamp(c['seconds'])} --> {stamp(end)}\n{c['title']}\n{c['description']}\n\n"
(out/'captions.vtt').write_text(vtt)
poster_time=next(c['seconds'] for c in chapters if c['title'].startswith('05'))-1
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-ss',str(poster_time),'-i',str(video),'-frames:v','1',str(out/'poster.png')],check=True)
print(json.dumps(report),flush=True)

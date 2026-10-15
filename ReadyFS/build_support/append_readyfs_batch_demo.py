#!/usr/bin/env python3
"""Append a successful physical batch take to the retained editor tour.

Keep the original MP4 streams and all 37 original step records. Only the new
chapter's typing is accelerated; operation and paging footage stays at 1x.
"""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys
from readyfs_heading_cards import batch_card
src, site, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
assert (src/'status.txt').read_text().strip() == 'success'
events = [json.loads(x) for x in (src/'events.jsonl').read_text().splitlines()]
assert events[-1].get('complete') and events[-1].get('restored') and events[-1]['result'] == 'PASS'
required = {'batch-demo-preview-unchanged', 'batch-demo-backup-independent-bytes',
            'batch-demo-existing-destination-unchanged', 'batch-demo-source-preserved-and-shared-counter'}
assert required <= {e.get('case') for e in events if e.get('result') == 'PASS'}
raw = json.loads((src/'video-report.json').read_text())
steps = json.loads((src/'script.json').read_text())
chapters = json.loads((src/'chapters.json').read_text())
assert len(steps) == 7 and len(chapters) == 1
# Preserve the exact pre-append published assets in local evidence, not the Site.
base = out/'original';base.mkdir(exist_ok=True)
for name in ('readyfs-demo.mp4', 'chapters.json', 'script.json', 'script.md', 'captions.vtt', 'video-report.json', 'hardware-checks.json'):
    shutil.copy2(site/name, base/name)
old_report = json.loads((base/'video-report.json').read_text())
old_steps = json.loads((base/'script.json').read_text())
old_chapters = json.loads((base/'chapters.json').read_text())
assert len(old_steps) == 37 and len(old_chapters) == 9
work = out/'edit';work.mkdir(exist_ok=True)
chapter = chapters[0];chapter['seconds'] = old_report['seconds'];chapter['callout_seconds'] = 4.8
assert len(chapter['description'].split()) <= 10
segments = [base/'readyfs-demo.mp4'];elapsed = old_report['seconds'];cuts=[];saved=0
fps = raw['fps']
for i, step in enumerate(steps):
    start, typed, result, end = (step[k] for k in ('start_seconds','typed_seconds','seconds','end_seconds'))
    assert start < typed < result < end
    dt = typed - start;duration=dt/1.4+end-typed;saved+=dt-dt/1.4
    card_path=work/f'card-{i:02d}.png';batch_card(i).save(card_path)
    f=f'[0:v]split=2[a][b];[a]trim=duration={dt:.6f},setpts=(PTS-STARTPTS)/1.4[t];[b]trim=start={dt:.6f},setpts=PTS-STARTPTS[o];[t][o]concat=n=2:v=1:a=0,fps={fps},pad=960:720:96:144:color=0x090e1b,setsar=1[base];[base][1:v]overlay=52:12:shortest=1[v]'
    seg=work/f'segment-{i:02d}.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-t',str(end-start),'-i',str(src/'readyfs-demo.mp4'),'-loop','1','-i',str(card_path),'-filter_complex',f,'-map','[v]','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-video_track_timescale','13684',str(seg)],check=True)
    actual=float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(seg)]))['format']['duration'])
    step['group']=9;step['start_seconds']=elapsed;step['typed_seconds']=elapsed+dt/1.4;step['seconds']=elapsed+dt/1.4+result-typed;step['end_seconds']=elapsed+actual;step['typing_rate']=1.4
    step['screenshot']='batch-'+step['screenshot'];shutil.copy2(src/step['screenshot'].removeprefix('batch-'),site/step['screenshot'])
    for page in step.get('pages',[]):
        page['screen']='\n'.join(line[4:] if len(line)>3 and line[:2].isdigit() and line[2:4]==': ' else line for line in page['screen'].splitlines())
        # Color rendering for older pages defaults to white, preserving exact screen text.
        page['screen_rows']=[{'text':line,'color':1} for line in page['screen'].splitlines()]
        shutil.copy2(src/page['screenshot'],site/page['screenshot'])
    cuts.append({'source_start':start,'source_typed':typed,'source_result':result,'source_end':end,'output_start':elapsed,'output_duration':actual})
    elapsed+=actual;segments.append(seg)
    print(json.dumps({'edited_batch_step':i+1,'seconds':elapsed}),flush=True)
(work/'concat.txt').write_text(''.join("file '"+str(p)+"'\n" for p in segments))
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-c','copy','-movflags','+faststart',str(out/'readyfs-demo.mp4')],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,duration,nb_frames','-of','json',str(out/'readyfs-demo.mp4')]))['streams'][0]
assert [probe['width'],probe['height']]==[960,720]
checks=json.loads((base/'hardware-checks.json').read_text())
new_checks=[{'case':e['case'],'result':'PASS'} for e in events if 'case' in e and e.get('result')=='PASS']
checks+=new_checks
report={**old_report,'seconds':float(probe['duration']),'frames':int(probe['nb_frames']),'complete_frames':int(probe['nb_frames']),'sha256':hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest(),'megabytes':(out/'readyfs-demo.mp4').stat().st_size/1e6,'checks':len(checks),'typing_speed_seconds_saved':old_report['typing_speed_seconds_saved']+saved,'editing':old_report['editing']+' Appended physical batch chapter: separate new owned test folder and current DOS-style build; TYPE pages and operations retain recorded speed, input 1.4×. Original nine chapters retained without re-encoding; every decoded frame of the prefix verified unchanged.','batch_append':{'starts_seconds':old_report['seconds'],'source_take':src.name,'source_sha256':raw['sha256'],'source_missing_frames':raw['duplicated_missing_frames'],'original_video_sha256':old_report['sha256'],'original_steps':37,'new_steps':len(steps),'checks':len(new_checks),'settings_restored':True,'independent_checks':json.loads((src/'batch-demo-checks.json').read_text())}}
# Compare every decoded frame of the retained prefix. Remuxing can add SPS/PPS
# bytes to H.264 packets without changing a single displayed pixel.
def frame_hashes(file, count):
    output=subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-frames:v',str(count),'-f','framemd5','-']).decode()
    return [line.rsplit(',',1)[-1].strip() for line in output.splitlines() if not line.startswith('#') and line.strip()]
old_frames=frame_hashes(base/'readyfs-demo.mp4',old_report['frames'])
new_frames=frame_hashes(out/'readyfs-demo.mp4',old_report['frames'])
assert len(old_frames)==old_report['frames'] and old_frames==new_frames
report['batch_append']['original_video_frames_unchanged']=True
all_steps=old_steps+steps;all_chapters=old_chapters+[chapter]
def stamp(s):
    ms=round(s*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(all_chapters):
    end=all_chapters[i+1]['seconds'] if i+1<len(all_chapters) else report['seconds']
    vtt+=f'{i+1}\n{stamp(c["seconds"])} --> {stamp(end)}\n{c["title"]}\n\n'
md=(base/'script.md').read_text()+'\n\n## '+chapter['title']+'\n\n'+chapter['description']+'\n\nThis appended chapter uses a new owned host folder and the current DOS-style scripting build. LAB is assigned during omitted setup:\n\n```text\nALIAS LAB u:'+report['batch_append']['independent_checks']['root']+'\n```\n\n[Download the exact BACKUP.SEQ](examples/BACKUP.SEQ). TYPE displays its real contents before execution.\n'
for i,s in enumerate(steps,len(old_steps)+1):
    md+=f'\n### Step {i} · {stamp(s["start_seconds"])}\n\n{s["explanation"]}\n\n```text\n{s["input"]}\n```\n\n![Actual C64 result]({s["screenshot"]})\n\n```text\n{s["screen"].rstrip()}\n```\n'
    for j,p in enumerate(s.get('pages',[]),1):md+=f'\nScript page {j}:\n\n![Actual C64 script page]({p["screenshot"]})\n\n```text\n{p["screen"]}\n```\n'
for name,data in [('chapters.json',all_chapters),('script.json',all_steps),('video-report.json',report),('hardware-checks.json',checks)]:
    (out/name).write_text(json.dumps(data,indent=2)+'\n');shutil.copy2(out/name,site/name)
(out/'captions.vtt').write_text(vtt);(out/'script.md').write_text(md)
for name in ('captions.vtt','script.md','readyfs-demo.mp4'):shutil.copy2(out/name,site/name)
shutil.copy2(src/'batch-demo-checks.json',site/'batch-demo-checks.json')
(out/'append-plan.json').write_text(json.dumps(cuts,indent=2)+'\n')
print(json.dumps({'seconds':report['seconds'],'append_seconds':report['seconds']-old_report['seconds'],'steps':len(all_steps),'chapters':len(all_chapters),'checks':len(checks),'original_frames':'PASS'}),flush=True)

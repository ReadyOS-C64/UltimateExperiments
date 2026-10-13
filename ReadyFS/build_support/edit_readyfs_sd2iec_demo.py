#!/usr/bin/env python3
"""Edit actual SD footage: omit setup/guards; input 1.4x; operations stay 1x."""
from pathlib import Path
import hashlib,json,subprocess,sys,shutil,math
from PIL import Image,ImageDraw,ImageFont
src,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
assert (src/'status.txt').read_text().strip()=='success'
events=[json.loads(x) for x in (src/'events.jsonl').read_text().splitlines()]
assert events[-1].get('complete') and events[-1]['restored'] and events[-1]['result']=='PASS'
required={'sd-demo-five-native-files-identical','sd-demo-five-returned-independent-hashes','sd-demo-two-softiec-independent-hashes','sd-demo-contained-image-independent-bytes-types','baseline-independent-disk-bytes-and-source-removal','baseline-softiec-cwd-and-config-restored'}
passed={e.get('case') for e in events if e.get('result')=='PASS'};assert required<=passed
steps=json.loads((src/'script.json').read_text());chapters=json.loads((src/'chapters.json').read_text());raw=json.loads((src/'video-report.json').read_text())
work=src/'edit';work.mkdir(exist_ok=True);fps=raw['fps'];elapsed=0;seen=set();segments=[];cuts=[]
fonts=Path('/System/Library/Fonts/Supplemental');font=ImageFont.truetype(str(fonts/'Arial Bold.ttf'),25);small=ImageFont.truetype(str(fonts/'Arial.ttf'),19)
for i,step in enumerate(steps):
    start,typed,finish,result=step['start_seconds'],step['typed_seconds'],step['end_seconds'],step['seconds']
    assert start<typed<result<finish
    chapter=chapters[step['group']];first=step['group'] not in seen
    if first:chapter['seconds']=elapsed;chapter['callout_seconds']=4.8;seen.add(step['group'])
    im=Image.new('RGBA',(856,104),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rounded_rectangle((0,0,855,103),radius=16,fill=(23,32,51,242),outline=(83,105,137,242))
    title=chapter['title'].replace(' · ',' / ');desc=chapter['description']
    assert font.getlength(title)<790 and small.getlength(desc)<790
    d.text((30,14),title,font=font,fill=(245,248,255));d.text((30,57),desc,font=small,fill=(213,225,242))
    card=work/f'card-{i:02d}.png';im.save(card)
    base=Image.new('RGBA',(960,32),(0,0,0,0));ImageDraw.Draw(base).text((52,2),'Typing 1.4×  ·  operations 1×  ·  setup / ownership checks omitted',font=ImageFont.truetype(str(fonts/'Arial.ttf'),16),fill=(158,177,207));base.save(work/'notice.png')
    dt=typed-start;duration=dt/1.4+finish-typed
    filters=f'[0:v]split=2[a][b];[a]trim=duration={dt:.6f},setpts=(PTS-STARTPTS)/1.4[t];[b]trim=start={dt:.6f},setpts=PTS-STARTPTS[o];[t][o]concat=n=2:v=1:a=0,fps={fps},pad=960:720:96:144:color=0x090e1b,setsar=1[base];[base][2:v]overlay=0:111:shortest=1[label]'
    if first:filters+=';[1:v]format=rgba,fade=t=in:st=0:d=.2:alpha=1,fade=t=out:st=4.3:d=.5:alpha=1[card];[label][card]overlay=52:8:enable=\'lt(t,4.8)\':shortest=1[v]'
    else:filters+=';[label]null[v]'
    seg=work/f'segment-{i:02d}.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-t',str(finish-start),'-i',str(src/'readyfs-demo.mp4'),'-loop','1','-i',str(card),'-loop','1','-i',str(work/'notice.png'),'-filter_complex',filters,'-map','[v]','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(seg)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(seg)]))
    actual=float(probe['format']['duration']);step['start_seconds']=elapsed;step['seconds']=elapsed+dt/1.4+result-typed;step['end_seconds']=elapsed+actual
    step['typing_rate']=1.4;cuts.append({'source_start':start,'source_typed':typed,'source_result':result,'source_end':finish,'output_start':elapsed,'output_duration':actual})
    elapsed+=actual;segments.append(seg)
    for key in ('screenshot','editor_screenshot'):
        if step.get(key):shutil.copy2(src/step[key],out/step[key])
    for page in step.get('pages',[]):shutil.copy2(src/page['screenshot'],out/page['screenshot'])
    print(json.dumps({'edited_step':i+1,'steps':len(steps),'seconds':elapsed}),flush=True)
(work/'concat.txt').write_text(''.join("file '"+str(p)+"'\n" for p in segments))
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-c','copy','-movflags','+faststart',str(out/'readyfs-demo.mp4')],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,duration,nb_frames','-of','json',str(out/'readyfs-demo.mp4')]))['streams'][0]
checks=[{'case':e['case'],'result':'PASS'} for e in events if 'case' in e and e.get('result')=='PASS']
report={**raw,'seconds':float(probe['duration']),'frames':int(probe['nb_frames']),'dimensions':[960,720],'megabytes':(out/'readyfs-demo.mp4').stat().st_size/1e6,'sha256':hashlib.sha256((out/'readyfs-demo.mp4').read_bytes()).hexdigest(),'source_take':src.name,'checks':len(checks),'typing_rate':1.4,'editing':'Setup, ownership guards and independent checks omitted. All public commands and operation footage retained; input playback 1.4x, operations 1x. Chapter cards at 95% opacity fade after 4.8 seconds strictly above the complete C64 picture.','overlay_bounds':[52,8,856,104],'c64_picture_bounds':[96,144,768,544],'original_settings_restored':True,'independent_gates':sorted(required)}
for name,data in [('chapters.json',chapters),('script.json',steps),('video-report.json',report),('hardware-checks.json',checks),('edit-plan.json',cuts)]: (out/name).write_text(json.dumps(data,indent=2)+'\n')
def stamp(s):
    ms=round(s*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
vtt='WEBVTT\n\n'
for i,c in enumerate(chapters):
    end=chapters[i+1]['seconds'] if i+1<len(chapters) else report['seconds'];vtt+=f'{i+1}\n{stamp(c["seconds"])} --> {stamp(end)}\n{c["title"]}\n\n'
(out/'captions.vtt').write_text(vtt)
md=['# ReadyFS SD2IEC: recorded commands','','Physical C64 Ultimate and attached SD2IEC, 1 MHz. Typing is presented at 1.4×; all shown operations retain their recorded speed. Setup and ownership checks are omitted from this edit and retained in source evidence.','']
for g,c in enumerate(chapters):
    md+=['## '+c['title'],'',c['description'],'']
    for i,s in enumerate(steps):
        if s['group']!=g:continue
        md += [f'### Step {i+1} · {stamp(s["start_seconds"])}','',s['explanation'],'','```text',s['input'],'```','',f'![Actual C64 result]({s["screenshot"]})','','```text',s['screen'].rstrip(),'```','']
(out/'script.md').write_text('\n'.join(md))
subprocess.run(['ffmpeg','-v','error','-y','-ss',str(chapters[1]['seconds']+2),'-i',str(out/'readyfs-demo.mp4'),'-frames:v','1',str(out/'poster.png')],check=True)
for name in ('sd-demo-scope.json','baseline-independent-disk-checks.json','sd-demo-returned-bytes.json'):shutil.copy2(src/name,out/name)
print(json.dumps(report),flush=True)

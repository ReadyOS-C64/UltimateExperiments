from pathlib import Path
import json,math
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u'
base=root/'demo-v4-published-20261012';previous=json.loads((root/'demo-v5-edit-20261012/edit-plan.json').read_text());out=root/'demo-v6-edit-20261012'
steps=json.loads((base/'script.json').read_text());report=json.loads((base/'video-report.json').read_text());fps=report['fps'];duration=report['seconds'];runs=json.loads((root/'demo-v5-edit-20261012/stationary-runs.json').read_text())
protected=previous['protected_typing'];cuts=[]
for a,b,_ in runs:
 segments=[(a+2.2,b-.9)]
 for p,q in protected:
  split=[]
  for x,y in segments:
   if q<=x or p>=y:split.append((x,y))
   else:
    if x<p:split.append((x,p))
    if q<y:split.append((q,y))
  segments=split
 for x,y in segments:
  if y-x>=1.8:cuts.append([math.ceil(x*fps)/fps,math.floor(y*fps)/fps])
cuts.sort();merged=[]
for a,b in cuts:
 if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
 else:merged.append([a,b])
wait_seconds=sum(b-a for a,b in merged);long_entry=previous['long_entry_cut'];merged.append(long_entry);merged.sort()
# Only user input is accelerated. Physical filesystem execution/results are 1×.
typing=[]
for estimate in previous['submit_estimates']:
 s=steps[estimate['step']-1];a=s['start_seconds'];b=estimate['submit_seconds']
 if abs(b-s['seconds'])<.001:b=min(b,a+len(s['input'])*.3+.8)
 b=max(a,b-.35)
 if b>a:typing.append([a,b])
typing += [[251.7,264.1],[278.0,339.8],[342.9,353.6],[369.0,376.5]]
typing.sort()
boundaries=sorted({round(v*fps)/fps for v in [0,duration,*[v for pair in merged for v in pair],*[v for pair in typing for v in pair]]})
segments=[];clock=0.;typing_seconds=0.
for a,b in zip(boundaries,boundaries[1:]):
 mid=(a+b)/2
 if any(x<=mid<y for x,y in merged):continue
 rate=1.4 if any(x<=mid<y for x,y in typing) else 1.
 if rate==1.4:typing_seconds+=b-a
 segment={'source_start':a,'source_end':b,'rate':rate,'output_start':clock,'output_end':clock+(b-a)/rate}
 if segments and segments[-1]['rate']==rate and abs(segments[-1]['source_end']-a)<1e-8:
  segments[-1]['source_end']=b;segments[-1]['output_end']=segment['output_end']
 else:segments.append(segment)
 clock=segment['output_end']
clock=0.
for segment in segments:
 segment['source_frames']=round((segment['source_end']-segment['source_start'])*fps)
 segment['output_frames']=round(segment['source_frames']/segment['rate'])
 segment['output_start']=clock;clock+=segment['output_frames']/fps;segment['output_end']=clock
plan={'original_seconds':duration,'previous_edited_seconds':json.loads((root/'demo-v5-published-20261012/video-report.json').read_text())['seconds'],'new_seconds':clock,'removed_seconds':sum(b-a for a,b in merged),'stationary_wait_seconds_removed':wait_seconds,'long_entry_cut':long_entry,'cuts':merged,'protected_typing':protected,'typing_intervals':typing,'typing_rate':1.4,'retained_typing_source_seconds':typing_seconds,'typing_speed_seconds_saved':typing_seconds*(1-1/1.4),'segments':segments,'method':'Further shorten unchanged waits, retain the marked repeated-entry jump, show typing/input edits at 1.4×, leave physical execution/results and page-reading pauses at 1×.'}
(out/'edit-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:plan[k] for k in ('new_seconds','stationary_wait_seconds_removed','typing_rate','typing_speed_seconds_saved','retained_typing_source_seconds')}))

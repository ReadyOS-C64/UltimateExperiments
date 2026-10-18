"""Editorial decisions based on visible concepts/actions/results in the v6 cut."""
from pathlib import Path
import json,math
root=Path(__file__).resolve().parent.parent/'logs/readyfs_c64u';base=root/'demo-v6-published-20261012';work=root/'demo-v7-analysis-20261012';r=json.loads((base/'video-report.json').read_text());fps=r['fps'];duration=r['seconds']
# These are positions in the existing 10:22 cut, reviewed using contact sheets
# and finer 4 Hz transition checks. New concepts and actual transitions remain.
raw=[
 (31.5,36.5,'entry','Repeated characters in the unique LAB root; retain start, complete argument and alias result.'),
 (69.5,88.2,'pages','Skip intermediate drive-8 pages after classic listing and paging have already been taught; retain first and last page.'),
 (91.0,94.0,'repeat','Last directory page is already visible for several seconds; shorten its trailing dwell.'),
 (117.8,119.2,'pages','Retain mounted-path context, classic header and final free-block line; omit repeated listing transition.'),
 (121.8,123.2,'repeat','Shorten second identical directory-end dwell.'),
 (186.5,191.0,'transfer','Shorten host-to-disk wait after the no-verify flag is visible; retain named result and later comparison.'),
 (198.0,202.0,'entry','Second COMPARE uses the already-established syntax; retain beginning and complete command.'),
 (214.1,215.6,'repeat','Red unsupported error remains readable before the editing chapter.'),
 (235.0,241.0,'repeat','HEAD result has established successful correction; shorten external preparation before long input.'),
 (248.8,257.8,'entry','Further condense repeated long-line text; retain full 255-byte state and all Home/End/overwrite actions.'),
 (275.5,281.3,'repeat','Long WRITE preview paragraph repeats the entered text; retain zero-change summary and reading beat.'),
 (292.2,293.8,'history','Draft is visible before first recall; shorten hold without removing the key transition.'),
 (295.8,297.3,'history','Shorten first recalled-command hold.'),
 (299.3,300.55,'history','Shorten second recalled-command hold.'),
 (302.8,304.05,'history','Restored draft remains identifiable before output paging.'),
 (307.5,308.55,'history','First output page retains three seconds; shorten trailing hold.'),
 (311.0,313.05,'history','Older page repeats earlier disk-copy output; retain page transition and two seconds.'),
 (315.5,317.55,'history','Newer page repeats already-seen content; retain transition and two seconds.'),
 (324.5,325.5,'repeat','Keep the restored draft execution result, reduce trailing dwell.'),
 (345.3,348.7,'preview','First preview root context retains about three seconds; the important named list gets extra reading time.'),
 (370.8,374.8,'transfer','Copy planning/wait has no new concept; retain command, plan count and first file.'),
 (376.2,378.7,'transfer','Retain first source path then jump to its verified completion.'),
 (382.0,385.5,'transfer','First named completion remains visible for two seconds; avoid waiting for the next identical pattern.'),
 (388.0,390.5,'transfer','Shorten second-file wait; retain its name and completed count.'),
 (396.2,398.0,'transfer','Shorten third-file wait; retain completed TWO.SEQ result.'),
 (402.0,405.0,'transfer','Avoid repeated dwell after third completion.'),
 (408.0,410.5,'transfer','Shorten fourth-file wait; retain FOUR.SEQ result.'),
 (417.0,420.5,'transfer','Shorten final-file wait; retain THREE.SEQ and batch summary.'),
 (447.0,450.5,'entry','MOVE preview syntax repeats recursive what-if; retain complete --whatif argument.'),
 (460.7,463.7,'preview','Same named selection is familiar; shorten root-page pause and keep final list.'),
 (480.5,483.0,'transfer','Shorten move planning before first file.'),
 (485.2,487.0,'transfer','First skipped-readback result follows shortly; retain enough path context.'),
 (492.3,494.5,'transfer','Shorten second move-file wait.'),
 (500.3,502.0,'transfer','Shorten third move-file wait.'),
 (505.0,507.5,'transfer','Reduce repeated result dwell before fourth move-file.'),
 (509.2,511.0,'transfer','Shorten fourth move-file wait.'),
 (514.0,516.0,'transfer','Reduce repeated fourth-file completion dwell.'),
 (519.0,525.0,'transfer','Shorten long final move wait; preserve final file and 11/11 fail-0 summary.'),
 (547.0,550.0,'entry','DELETE what-if follows the established pattern; retain complete command and no-change result.'),
 (558.7,562.2,'preview','The same selected file names have been read twice; shorten repeated preview-root page.'),
 (599.0,601.0,'entry','Final CD uses a known alias; preserve complete command and resulting path.'),
 (607.5,609.5,'repeat','Final one-level DIR repeats familiar results; retain listing before the complete survivor TREE.'),
 (614.9,615.9,'repeat','Shorten pre-conclusion tree dwell; final tree remains visible throughout the concluding card.')]
cuts=[]
for a,b,kind,reason in raw:
 a=round(a*fps)/fps;b=round(b*fps)/fps;cuts.append({'start':a,'end':b,'kind':kind,'reason':reason})
cuts.sort(key=lambda c:c['start']);assert all(a['end']<=b['start'] for a,b in zip(cuts,cuts[1:]))
chapters=json.loads((base/'chapters.json').read_text())
for c in cuts:
 assert all(c['end']<=x['seconds'] or c['start']>=x['seconds']+x['callout_seconds'] for x in chapters),'Do not clip chapter-card reading time'
# Add a dedicated reading beat to the first named-file selection. Later repeats
# need recognition, but this first introduction needs comprehension.
hold_at=round(351.9*fps)/fps;hold_frames=round(1.2*fps)
boundaries=sorted({0,duration,hold_at,*[v for c in cuts for v in (c['start'],c['end'])]});segments=[];clock=0
for a,b in zip(boundaries,boundaries[1:]):
 if any(c['start']<=(a+b)/2<c['end'] for c in cuts):continue
 source_frames=round((b-a)*fps);extra=hold_frames if abs(b-hold_at)<1e-7 else 0
 s={'source_start':a,'source_end':b,'source_frames':source_frames,'hold_frames':extra,'output_frames':source_frames+extra,'output_start':clock,'output_end':clock+(source_frames+extra)/fps};segments.append(s);clock=s['output_end']
def mapped(t):
 last=0
 for s in segments:
  if t<s['source_start']:return last
  if t<=s['source_end']:return s['output_start']+(t-s['source_start'])
  last=s['output_end']
 return last
steps=json.loads((base/'script.json').read_text())
# Protect visually reviewed critical transitions and first-time reading windows.
protected=[(223,229,'HED to HEAD insertion and execution'),(258,270,'complete long line, Home/End and overwrite'),(304.4,307.4,'first history output page'),(317.7,324.3,'restore draft and execute'),(349.25,352.5,'first complete eight-entry preview'),(488,491,'first recursive verify-skipped result'),(526.5,529.2,'move completion summary'),(616,622.70893,'original source and final evidence')]
for c in cuts:
 assert all(c['end']<=a or c['start']>=b for a,b,_ in protected),(c,protected)
by_kind={}
for c in cuts:by_kind[c['kind']]=by_kind.get(c['kind'],0)+c['end']-c['start']
chapter_analysis=[]
for i,c in enumerate(chapters):
 end=chapters[i+1]['seconds'] if i+1<len(chapters) else duration
 chapter_analysis.append({'chapter':c['title'],'before_seconds':end-c['seconds'],'after_seconds':mapped(end)-mapped(c['seconds']),'saved_seconds':end-c['seconds']-(mapped(end)-mapped(c['seconds']))})
plan={'source_cut':'demo-v6-published-20261012','previous_seconds':duration,'new_seconds':clock,'extra_removed_seconds':sum(c['end']-c['start'] for c in cuts),'first_preview_reading_hold_seconds':hold_frames/fps,'cuts':cuts,'segments':segments,'protected_windows':protected,'seconds_saved_by_kind':by_kind,'chapter_analysis':chapter_analysis,'method':'Meaning-first editorial cuts: keep new concepts, complete commands and outcomes; condense repeated syntax, repeated listing pages and per-file waits. Preserve first-time reading time and key actions. Existing 1.4x input playback is unchanged.'}
(work/'edit-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({k:plan[k] for k in ('previous_seconds','new_seconds','extra_removed_seconds','first_preview_reading_hold_seconds','seconds_saved_by_kind')}))

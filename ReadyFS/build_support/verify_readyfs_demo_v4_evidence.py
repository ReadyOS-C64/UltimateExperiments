#!/usr/bin/env python3
"""Check named preview pages and optional readback in the saved hardware tour."""
from pathlib import Path
import json, subprocess, sys
out=Path(sys.argv[1]).resolve()
subprocess.run([sys.executable,str(Path(__file__).with_name('verify_readyfs_demo_v3_evidence.py')),str(out)],check=True)
steps=json.loads((out/'script.json').read_text())
files=('readme.seq','alpha/one.seq','alpha/two.seq','beta/four.seq','beta/deep/three.seq')
dirs=('alpha','beta','beta/deep')
for verb,command in [('copy','CP'),('move','MOVE'),('delete','DELETE')]:
    step=next(s for s in steps if s['input'].split()[0]==command and (' -W' in s['input'].upper() or '--WHATIF' in s['input'].upper()))
    pages=step.get('pages',[])
    text='\n'.join([p['screen'] for p in pages]+[step['screen']]).upper()
    for file in files:assert 'WOULD '+verb.upper()+' '+file.upper() in text,(verb,file,text)
    for directory in dirs:assert 'WOULD '+verb.upper()+' DIR '+directory.upper() in text,(verb,directory,text)
    assert 'WHATIF: NO FILES CHANGED' in text
    assert all((out/p['screenshot']).is_file() for p in pages)
    assert all(any('-- MORE --' in row['text'].upper() and row['color']==7 for row in p['screen_rows']) for p in pages),'Preview pager must be yellow'
single=next(s for s in steps if '--NO-VERIFY' in s['input'].upper())
assert 'VERIFY: SKIPPED' in single['screen'] and 'COPIED README.SEQ: 38 BYTES' in single['screen']
following=steps[steps.index(single)+1]
assert following['input'].startswith('COMPARE ') and 'VERIFY: IDENTICAL' in following['screen']
verified=next(s for s in steps if s['input'].startswith('COPY @LAB:/SOURCE @LAB:/COPY --recursive'))
assert 'VERIFY: IDENTICAL' in verified['screen'],'Default verify did not return after skip'
moved=next(s for s in steps if s['input'].startswith('MV @LAB:/COPY @LAB:/MOVED -R -NV'))
assert 'VERIFY: SKIPPED' in moved['screen'] and 'FAIL 0' in moved['screen']
result={'all_five_named_files_and_three_directories_in_copy_move_delete_previews':'PASS',
        'single_file_skip_then_explicit_compare':'PASS','verify_default_returns_next_command':'PASS',
        'recursive_move_skip_and_independent_byte_oracle':'PASS',
        'preview_pages':sum(len(s.get('pages',[])) for s in steps)}
(out/'named-transfer-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

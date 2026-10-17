"""Close actual final9 run; retain first generated-import ledger rejection."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;W=P/'work'
D=lambda p:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
before=json.loads((P/'FINAL_INPUTS_BEFORE.json').read_text());changes={n:{'before':v,'after':D(Path(n))}for n,v in before.items()if D(Path(n))!=v}
q=P/'gate/core_imports.s';assert set(changes)=={str(q)},changes
# This generated alias table gained only the newly requested debug export;
# removing its two non-emitting assembly lines reproduces the exact old table.
lines=q.read_text().splitlines(keepends=True);old=''.join(l for l in lines if not(l.startswith('.export _overlay_poll')or l.startswith('_overlay_poll = ')))
assert hashlib.sha256(old.encode()).hexdigest()==changes[str(q)]['before']['sha256']
labels={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in(W/'controller.labels').read_text().splitlines()if l.startswith('al ')}
for i,l in enumerate(lines):
 if l.startswith('_')and ' = $'in l:
  name,value=l.strip().split(' = $');assert labels[name]==int(value,16)
assert json.loads((W/'JOURNAL_START_RESULT.json').read_text())=={'passed':True,'groups':9}
log=(P/'FINAL_TEST.stderr').read_text();assert 'Ran 9 tests'in log and log.rstrip().endswith('OK')
assert (P/'gate/journal_gate.c').read_bytes()==(P.parent/'native-start-journal-modal-successor-20261017/gate/journal_gate.c').read_bytes()
assert json.loads((P/'COUPLED_RESULT.json').read_text())['second_RCV_link_exact']
after={n:D(Path(n))for n in before};(P/'FINAL_INPUTS_AFTER.json').write_text(json.dumps(after,indent=2)+'\n')
products={str(W/n):D(W/n)for n in ['controller.prg','START.INO','controller.labels','controller.map','START.RCV','START.REL','DOS64.REL','JOURNAL_START_RESULT.json','journal-peddle.dylib']}
for n in ['gate/START.RCV','gate/gate.labels','gate/gate.map','gate/MATCHED_BINDING.json','COUPLED_RESULT.json']:products[str(P/n)]=D(P/n)
result={'status':'passed_with_explicit_generated_import_qualification','actual_native_groups':9,'input_records':len(before),'unchanged_inputs':len(before)-1,'changed_generated_nonemitting_alias_tables':changes,'generated_alias_delta':'only _overlay_poll debug export; exact old table rederived by deleting those2lines; all alias addresses match final linked labels','algorithm_C_exact_parent':True,'fresh_native_and_model_source_builds':True,'default_public_START_INO_exact_profiles':2,'products':products,'physical':False,'scope':'actual START recovery before normal CFG; no journal restores INO and reaches handoff; pending/error safely blocks; no archive/rollforward or release promotion','first_closure_error_retained':True,'unchanged_full_9_group_suite_not_repeated':True}
(P/'FINAL_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual9 and precise source closure',len(before),'records; one explicit generated-only alias delta')

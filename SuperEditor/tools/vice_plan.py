"""Shared execution/artifact adapter for project-specific .NET VICE plans."""
import json
from pathlib import Path
import shutil
import subprocess
from vice_config import ROOT, PROJECT


def run_plan(plan, evidence):
    plan_path = evidence/'plan.yaml'
    plan_path.write_text(json.dumps(plan, indent=2)+'\n')
    command = ['dotnet', 'run', '--no-build', '--project', str(PROJECT), '--']
    for mode, extra in [('compile-plan', []), ('run-plan', ['--close-vice', '--no-tui'])]:
        result = subprocess.run(command+[mode, '--plan', str(plan_path)]+extra,
                                cwd=ROOT, capture_output=True, text=True, timeout=180)
        (evidence/f'{mode}.stdout.txt').write_text(result.stdout)
        (evidence/f'{mode}.stderr.txt').write_text(result.stderr)
        if mode == 'run-plan' and result.stdout.strip().startswith('{'):
            outcome = json.loads(result.stdout)
            if 'RunDir' in outcome and Path(outcome['RunDir']).exists():
                shutil.copytree(outcome['RunDir'], evidence/'run')
        if result.returncode:
            raise RuntimeError(f'{mode} failed; see {evidence}\n{result.stdout[-1800:]}\n{result.stderr[-1000:]}')
    manifest_path = Path(outcome['Manifest'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    assert manifest['status'] == 'success', manifest
    artifacts = evidence/'run'
    for command_output in (artifacts/'stages').glob('*/monitor_command.txt'):
        assert 'ERROR' not in command_output.read_text(encoding='utf-8-sig'), command_output
    return artifacts, artifacts/'manifest.json'

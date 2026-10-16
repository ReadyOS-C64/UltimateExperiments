"""Local, explicit proof binding for genuine native DOS MODE acceptance.

No runtime allowlist and no device I/O. A caller supplies the reviewed proof's
exact SHA256; the proof binds a passed unit run to its paired runtime build.
"""
import hashlib
import json
from pathlib import Path
import re


def sha(data):return hashlib.sha256(data).hexdigest()


def load_proof(path,expected_sha,current_manifest,expected_runtime,project):
    path=Path(path);raw=path.read_bytes()
    if not isinstance(expected_sha,str) or not re.fullmatch('[0-9a-f]{64}',expected_sha) or sha(raw)!=expected_sha:
        raise ValueError('Reviewed MODE proof SHA256 differs')
    proof=json.loads(raw)
    if proof.get('schema')!=1 or proof.get('purpose')!='genuine-native-dos-mode-proof' or set(proof.get('files',{}))!={'build_manifest','report','bitmap40','bitmap80'}:
        raise ValueError('Unsupported reviewed MODE proof schema')
    bodies={};paths={}
    for role,item in proof['files'].items():
        if set(item)!={'path','sha256','bytes'} or not isinstance(item['path'],str):raise ValueError('Invalid MODE proof input descriptor')
        file=(path.parent/item['path']).resolve();body=file.read_bytes()
        if len(body)!=item['bytes'] or sha(body)!=item['sha256']:raise ValueError('MODE proof input changed: '+role)
        bodies[role]=body;paths[role]=str(file)
    prior=json.loads(bodies['build_manifest']);report=json.loads(bodies['report'])
    files=prior.get('files',{});current=current_manifest.get('files',{})
    runtime=files.get('build/dos64.prg');unit=files.get('build/dos64-tests.prg')
    if not runtime or not unit or runtime!=expected_runtime or current.get('build/dos64.prg')!=runtime or current.get('build/dos64-tests.prg')!=unit:
        raise ValueError('MODE proof runtime/unit build pair differs from reviewed current target')
    if report.get('status')!='passed' or report.get('linked_prg_sha256')!=unit or report.get('mode_lane') is not True or report.get('commands')!=['MODE CO40\r','MODE CO80\r'] or report.get('completed_commands')!=2 or report.get('pending_offset')!=0 or report.get('no_direct_cpu_steps_or_DOS_shortcuts') is not True or report.get('source_sha256')!='bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb':
        raise ValueError('MODE report does not prove completed genuine native MODE for paired unit target')
    from c64u_native_display_application import keys
    if report.get('inputs')!=keys('\r\rMODE CO40\rMODE CO80\r'):raise ValueError('MODE report BIOS key sequence differs')
    # Host observation/recovery code may evolve, but every target source and the
    # actual full framebuffer assertion harness must match the executed cohort.
    names=[n for n in files if n.startswith(('src/','include/','cfg/','assets/native-text/'))]
    names+=['tests/host/native_builtin_workflows.zig']
    required={'src/video.s','src/cpu.s','src/native_runtime.s','src/render_text.s','src/render_graphics.s','include/video.inc','assets/native-text/cp437-narrow4x8.bin','assets/native-text/cp437-unscii8.bin'}
    if not required<=set(names):raise ValueError('MODE proof target source cohort is incomplete')
    for name in names:
        target=(Path(project)/name).resolve()
        if not target.is_relative_to(Path(project).resolve()) or sha(target.read_bytes())!=files.get(name) or current.get(name)!=files.get(name):
            raise ValueError('MODE executed source cohort changed: '+name)
    selected=[];last=-1
    for columns,mode in ((40,1),(80,3)):
        bitmap=bodies['bitmap'+str(columns)]
        if len(bitmap)!=8000:raise ValueError('MODE proof bitmap is incomplete')
        digest=sha(bitmap);found=None
        for index,observation in enumerate(report.get('observations',[])):
            screen=observation.get('screen',{});row=screen.get('row');column=screen.get('column');lines=screen.get('text','').splitlines()
            if (index>last and (screen.get('mode'),screen.get('columns'))==(mode,columns) and
                isinstance(row,int) and isinstance(column,int) and len(lines)==25 and all(len(line)==80 and (columns==80 or line[40:]==' '*40) for line in lines) and 0<=row<25 and 0<=column<columns and
                lines[row][:column].endswith('A>') and observation.get('native_bitmap_sha256')==digest):
                found=index;break
        if found is None:raise ValueError('MODE report lacks ordered coherent geometry/prompt/bitmap checkpoint')
        selected.append({'columns':columns,'mode':mode,'observation':found,'bitmap_sha256':digest});last=found
    return {'proof_path':str(path.resolve()),'proof_sha256':sha(raw),'runtime_sha256':runtime,'executed_unit_sha256':unit,
            'proof_inputs':{role:{'path':paths[role],'sha256':sha(body)} for role,body in bodies.items()},
            'source_count':len(names),'checkpoints':selected,
            'scope':'Genuine MODE unit execution and exact paired runtime build/source identity; no physical MODE acceptance'}

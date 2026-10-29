"""Build a genuine private59 disk: only released C45/R36/R37 differ."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools')]
from d81_image import D81Image
spec=importlib.util.spec_from_file_location('released_lexical_batch',ROOT/'src/cache/lexical-warm-probe/build.py')
released=importlib.util.module_from_spec(spec);spec.loader.exec_module(released)


def build(out,base):
    out.mkdir(parents=True);target=out/'fixture';shutil.copytree(base,target)
    original=json.loads((base/'freeze.json').read_text());assert len(original['names'])==59
    assert original['prg_sha256']=='93832107be6bca207087516304249b5de8b567143528ddcc132befdba64dd76b'
    before=D81Image((base/'build/supereditor.d81').read_bytes())
    images,labels,budgets=released.build(out/'leaf',base,4,True)
    assert {k:v['sha256']for k,v in budgets.items()}=={
        'edit':'b03667c3c42e3635760ac37cc712db9896cc0a2f6f636bb599a0deeb20e87b66',
        'tail':'cd811d24f8944509cef2dfd80e5c0a83302b57b076c95b3e597aed6159cce633',
        'lex':'6c52f74d4d6e0acff3ac4c2159fadd59d09e10977cf0cd3a5dd739739ff1a183'}
    for tag,image in images.items():
        path=target/f'build/overlays/{tag}.seo';path.write_bytes(image)
        p=subprocess.run(['c1541','-attach',str(target/'build/supereditor.d81'),'-delete',tag,
                          '-write',str(path),tag+',s'],capture_output=True,text=True)
        (out/('package-'+tag+'.log')).write_text(p.stdout+p.stderr);assert not p.returncode
    after=D81Image((target/'build/supereditor.d81').read_bytes())
    changed=[]
    for entry in before.entries():
        a=before.read(entry.name,kind=entry.kind).data;b=after.read(entry.name,kind=entry.kind).data
        if a!=b:changed.append(entry.name.decode().lower())
    assert sorted(changed)==['edit','lex','tail']
    assert len(before.entries())==len(after.entries())
    for name in original['names']:
        image=(target/f'build/overlays/{name}.seo').read_bytes()
        assert after.read(name.upper().encode(),kind=1).data==image
        if name not in images:assert image==(base/f'build/overlays/{name}.seo').read_bytes()
    assert after.read(b'SUPEREDITOR',kind=2).data==(base/'build/editor.prg').read_bytes()
    # Source ZIP contains the exact optional source profiles and matching
    # builder flags. Nothing is represented as an unchanged stock build.
    replacements={
        'src/cache/lexical/gateway.s':(ROOT/'src/cache/lexical-warm-probe/gateway.s').read_bytes(),
        'src/cache/arena/open.s':(ROOT/'src/cache/lexical-warm-probe/arena-open.s').read_bytes(),
        'src/cache/arena/page.s':(ROOT/'src/cache/lexical-warm-probe/arena-page.s').read_bytes()}
    with zipfile.ZipFile(base/'product-sources.zip')as z:
        source={info.filename:z.read(info.filename)for info in z.infolist()}
    path='src/cache/lexical/build.py';text=source[path].decode()
    needle="for i,(source,defs)in enumerate(files):\n"
    assert text.count(needle)==1
    text=text.replace(needle,needle+
        "   if tag=='edit':defs=defs+['LX_BATCH_STEPS=4']\n"
        "   if tag in('tail','lex')and source in('cache/arena/open.s','cache/arena/page.s'):defs=defs+['BCA_OUTER_VALIDATED=1']\n")
    replacements[path]=text.encode();source.update(replacements)
    compile(text,'private-frozen-lexical-build.py','exec')
    with zipfile.ZipFile(target/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for name,data in source.items():z.writestr(name,data)
    identity=dict(original);identity['assets']=dict(original['assets']);identity['sources']=dict(original['sources'])
    identity['assets'].update({n:hashlib.sha256(image).hexdigest()for n,image in images.items()})
    identity['sources'].update({n:hashlib.sha256(data).hexdigest()for n,data in replacements.items()})
    identity['disk_sha256']=hashlib.sha256((target/'build/supereditor.d81').read_bytes()).hexdigest()
    (target/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
    proof=dict(status='PASS',control=str(base),candidate=str(target),actual_changes=changed,
               source_flags=dict(C45=['LX_BATCH_STEPS=4'],R36_open_page=['BCA_OUTER_VALIDATED=1'],R37_page=['BCA_OUTER_VALIDATED=1']),
               budgets=budgets,prg_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],assets=identity['assets'])
    (out/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n')
    return target,proof


if __name__=='__main__':
    print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])

"""Compile host defaults and validate immutable64-byte session settings.

TOML reading requires Python3.11+ (stdlib tomllib); binary/runtime-reference
operations have no TOML or disk dependency. No editor integration is implied.
Settings admit builtin BSW9/native8 plus exact inventory GEOS family/size IDs.
Runtime application requires the matching font pack; this generator proves no
renderer integration by itself.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile
try:
    import tomllib
except ImportError:
    tomllib = None

ROOT=Path(__file__).resolve().parents[1]
MAGIC=b'SEST'
VERSION=1
SIZE=64
HEADER_SIZE=8
PROFILE_SIZE=7
PROFILES=('body','heading1','heading2','heading3','heading4','heading5','heading6','code')
BOLD=1
ITALIC=2
UNDERLINE=4
BUILTIN=0
GEOS=1
HEADER=MAGIC+bytes((VERSION,SIZE,len(PROFILES),PROFILE_SIZE))
FIELDS={'font','size','foreground','background','bold','italic','underline'}


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class FontFace:
    name:str
    origin:int
    family:int
    size:int
    advances:tuple
    sources:tuple=()

    @property
    def key(self):return self.origin,self.family,self.size

    @property
    def monospaced(self):
        return len(self.advances) in (96,128) and len(set(self.advances))==1 and self.advances[0]>0


def supported_fonts(catalog_path=None):
    """Settings catalog from exact extracted data; no synthesized family/size."""
    folder=ROOT/'assets/fonts/generated'
    widths=(folder/'bsw9-widths.bin').read_bytes()
    if len(widths)!=128 or not all(1<=v<=16 for v in widths):
        raise SettingsError('invalid supported BSW width metadata')
    if len((folder/'native8.bin').read_bytes())!=1024:
        raise SettingsError('invalid supported native8 asset')
    hashes=lambda names:tuple((str((folder/n).relative_to(ROOT)),
        hashlib.sha256((folder/n).read_bytes()).hexdigest()) for n in names)
    faces=[FontFace('bsw',BUILTIN,0,9,tuple(widths),
                   hashes(('bsw9.bin','bsw9-widths.bin'))),
           FontFace('native',BUILTIN,1,8,(8,)*128,hashes(('native8.bin',)))]
    path=Path(catalog_path) if catalog_path else ROOT/'build/geos-font-catalog/catalog.json'
    inventory=json.loads(path.read_text())
    if inventory.get('schema')!=1:raise SettingsError('unsupported extracted font catalog schema')
    native=[f for f in inventory['faces'] if f['namespace']=='GEOS-font-file']
    for entry in sorted(native,key=lambda f:(f['native_family_id'],f['point_size'])):
        raw=path.parent/entry['files']['font.bin']
        advances=path.parent/entry['files']['advances.bin']
        metrics=tuple(advances.read_bytes())
        if hashlib.sha256(raw.read_bytes()).hexdigest()!=entry['raw_sha256'] or hashlib.sha256(bytes(metrics)).hexdigest()!=entry['advance_sha256']:
            raise SettingsError('extracted font asset hash mismatch')
        if len(metrics)!=96 or entry['metrics']['glyphs']!=96:
            raise SettingsError('genuine font needs exact ASCII32..127 metrics')
        alias=entry['family'].lower().replace('_','-')
        source_name=lambda p:str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name
        faces.append(FontFace(alias,GEOS,entry['native_family_id'],entry['point_size'],metrics,
            ((source_name(raw),entry['raw_sha256']),(source_name(advances),entry['advance_sha256']))))
    return tuple(faces)


@dataclass(frozen=True)
class Profile:
    origin:int
    family:int
    size:int
    foreground:int
    background:int
    styles:int


@dataclass(frozen=True)
class Settings:
    profiles:tuple


def _integer(value,name,low,high):
    if type(value) is not int or not low<=value<=high:
        raise SettingsError('%s must be an integer%d..%d'%(name,low,high))
    return value


def _catalog(catalog):
    faces=tuple(supported_fonts() if catalog is None else catalog)
    keys={};names={}
    for face in faces:
        _integer(face.origin,'font origin',0,255)
        _integer(face.family,'font family',0,65535)
        _integer(face.size,'font size',1,255)
        if len(face.advances) not in (96,128) or not all(type(v) is int and 0<=v<=255 for v in face.advances) or not any(face.advances):
            raise SettingsError('font catalog needs96/128 exact nonnegative measured advances')
        if face.key in keys or (face.name,face.size) in names:raise SettingsError('duplicate font catalog identity')
        keys[face.key]=face;names[(face.name,face.size)]=face
    return faces,keys,names


def validate(settings,catalog=None):
    """Check the WHOLE candidate before any caller publishes active bytes."""
    faces,keys,names=_catalog(catalog)
    if not isinstance(settings,Settings) or len(settings.profiles)!=8:
        raise SettingsError('exactly8 profiles required')
    for name,p in zip(PROFILES,settings.profiles):
        if not isinstance(p,Profile):raise SettingsError('invalid profile')
        _integer(p.origin,name+'.origin',0,255);_integer(p.family,name+'.family',0,65535)
        _integer(p.size,name+'.size',1,255)
        _integer(p.foreground,name+'.foreground',0,15)
        _integer(p.background,name+'.background',0,15)
        _integer(p.styles,name+'.styles',0,7)
        face=keys.get((p.origin,p.family,p.size))
        if face is None:raise SettingsError(name+': unsupported font family/size/origin')
        if name=='code' and not face.monospaced:
            raise SettingsError('code requires equal measured advances, not a font-name guess')
    return settings


def from_mapping(mapping,catalog=None):
    faces,keys,names=_catalog(catalog)
    if type(mapping) is not dict or set(mapping)!={'schema',*PROFILES}:
        raise SettingsError('TOML needs schema and all8 named profiles, with no unknown keys')
    if type(mapping['schema']) is not int or mapping['schema']!=VERSION:
        raise SettingsError('unsupported settings schema')
    result=[]
    for name in PROFILES:
        row=mapping[name]
        if type(row) is not dict or set(row)!=FIELDS:
            raise SettingsError(name+': exact font/size/foreground/background/bold/italic/underline keys required')
        size=_integer(row['size'],name+'.size',1,255)
        if type(row['font']) is not str or (row['font'],size) not in names:
            raise SettingsError(name+': unsupported selectable font/size')
        face=names[(row['font'],size)]
        styles=0
        for field,bit in [('bold',BOLD),('italic',ITALIC),('underline',UNDERLINE)]:
            if type(row[field]) is not bool:raise SettingsError(name+'.'+field+' must be boolean')
            styles|=bit if row[field] else 0
        result.append(Profile(face.origin,face.family,size,row['foreground'],row['background'],styles))
    return validate(Settings(tuple(result)),faces)


def read_toml(data,catalog=None):
    if tomllib is None:raise SettingsError('TOML compilation requires Python3.11+ (tomllib)')
    try:mapping=tomllib.loads(bytes(data).decode('utf-8'))
    except (ValueError,UnicodeError) as exc:raise SettingsError('invalid TOML: '+str(exc)) from exc
    return from_mapping(mapping,catalog)


def encode(settings,catalog=None):
    validate(settings,catalog)
    result=bytearray(HEADER)
    for p in settings.profiles:
        result.extend((p.origin,p.family&255,p.family>>8,p.size,p.foreground,p.background,p.styles))
    assert len(result)==SIZE
    return bytes(result)


def decode(data,catalog=None):
    data=bytes(data)
    if len(data)!=SIZE or data[:HEADER_SIZE]!=HEADER:
        raise SettingsError('invalid settings magic/schema/length/count/stride')
    profiles=[]
    for at in range(HEADER_SIZE,SIZE,PROFILE_SIZE):
        origin,lo,hi,size,fg,bg,styles=data[at:at+PROFILE_SIZE]
        profiles.append(Profile(origin,lo|(hi<<8),size,fg,bg,styles))
    return validate(Settings(tuple(profiles)),catalog)


class SessionSettings:
    """Host reference for atomic session update/reset; NEVER writes a file.

    Parent owns the actual runtime descriptor/typed-object/overlay placement.
    This models validate-before-publish, with no added resident64-byte claim.
    """
    def __init__(self,defaults,catalog=None):
        self.catalog=tuple(supported_fonts() if catalog is None else catalog)
        decode(defaults,self.catalog)
        self.defaults=bytes(defaults)
        self.active=self.defaults

    def apply(self,candidate):
        candidate=bytes(candidate)
        decode(candidate,self.catalog) # all profiles first; old active survives failure
        self.active=candidate
        return self.active

    def update(self,name,**changes):
        if name not in PROFILES:raise SettingsError('unknown session profile')
        if not set(changes)<=set(Profile.__dataclass_fields__):raise SettingsError('unknown session field')
        profiles=list(decode(self.active,self.catalog).profiles)
        at=PROFILES.index(name)
        profiles[at]=replace(profiles[at],**changes)
        return self.apply(encode(Settings(tuple(profiles)),self.catalog))

    def reset_defaults(self):
        return self.apply(self.defaults)


def abi_include():
    lines=['; GENERATED by tools/editor_settings.py; ABI only, allocates no memory.',
        '; Session data lives in a caller-owned typed object/overlay table, never C600-C9FF.',
        '; FG/BG requests need the renderer color-cell/band policy; no per-glyph BG promise.',
        '.ifndef SE_GEOS_SETTINGS_ABI','SE_GEOS_SETTINGS_ABI=1',
        'SES_VERSION=1','SES_SIZE=64','SES_HEADER_SIZE=8','SES_PROFILE_COUNT=8','SES_PROFILE_SIZE=7',
        'SES_MAGIC0=$53','SES_MAGIC1=$45','SES_MAGIC2=$53','SES_MAGIC3=$54',
        'SES_HEADER_VERSION=4','SES_HEADER_LENGTH=5','SES_HEADER_COUNT=6','SES_HEADER_STRIDE=7',
        'SES_ORIGIN=0','SES_FAMILY=1 ;16-bit LE','SES_POINT_SIZE=3','SES_FOREGROUND=4',
        'SES_BACKGROUND=5','SES_STYLES=6','SES_BOLD=1','SES_ITALIC=2','SES_UNDERLINE=4',
        'SES_BUILTIN=0','SES_GEOS=1 ;genuine GEOS family IDs only after catalog admission',
        'SES_BUILTIN_BSW=0','SES_BUILTIN_NATIVE=1']
    lines.extend('SES_'+name.upper()+'='+str(HEADER_SIZE+i*PROFILE_SIZE) for i,name in enumerate(PROFILES))
    lines.extend(['.assert SES_CODE+SES_PROFILE_SIZE=SES_SIZE,error,"settings ABI size"','.endif',''])
    return '\n'.join(lines).encode('ascii')


def compile_defaults(data,catalog=None):
    faces,keys,names=_catalog(catalog)
    settings=read_toml(data,faces);table=encode(settings,faces)
    binary_sha=hashlib.sha256(table).hexdigest()
    emit=['; GENERATED defaults; macro emits64 bytes only when explicitly invoked.',
          '.include "settings.inc"','.macro SE_SETTINGS_EMIT_DEFAULTS']
    for at in range(0,SIZE,8):emit.append(' .byte '+','.join('$%02X'%v for v in table[at:at+8]))
    emit.extend(['.endmacro',''])
    manifest=dict(schema=VERSION,bytes=SIZE,profiles=list(PROFILES),profile_stride=PROFILE_SIZE,
        input_sha256=hashlib.sha256(bytes(data)).hexdigest(),table_sha256=binary_sha,
        table_hex=table.hex(),fonts=[dict(name=f.name,origin=f.origin,family=f.family,size=f.size,
            monospaced=f.monospaced,min_advance=min(f.advances),max_advance=max(f.advances),
            source_sha256=dict(f.sources)) for f in faces],
        profile_values={name:dict(origin=p.origin,family=p.family,size=p.size,
            foreground=p.foreground,background=p.background,styles=p.styles)
            for name,p in zip(PROFILES,settings.profiles)},
        storage='Session-only caller-owned typed REU object or loaded overlay table; no resident64B allocation.',
        reset='RESET defaults restores validated compiled table in session memory; no runtime config/disk writes.',
        limits=['Builtin BSW9/native8 plus exact extracted GEOS faces; actual runtime requires matching font pack.',
            'Code requires equal catalog advances. FG/BG application must follow8x8 tile/band arbitration.',
            'Existing heading inversion and lexical palette overrides are separate renderer semantics.',
            'Generator/host session reference only; actual runtime placement/UI/application are not integrated here.'])
    return {'editor-defaults.bin':table,
        'editor-font-catalog.bin':bytes(v for f in faces for v in (f.origin,f.family&255,f.family>>8,f.size,int(f.monospaced))),
        'editor-defaults.inc':'\n'.join(emit).encode('ascii'),
        'settings.inc':abi_include(),'editor-defaults.json':(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode('utf-8')}


def write_outputs(outputs,directory):
    """Inputs are fully compiled/validated before directory creation/publication."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    pending=[]
    try:
        for name,data in outputs.items():
            fd,path=tempfile.mkstemp(prefix='.'+name+'.',dir=directory)
            with os.fdopen(fd,'wb') as stream:stream.write(data)
            pending.append((Path(path),directory/name))
        # Manifest publishes last, after the deterministic data/include files.
        for temporary,target in pending:os.replace(temporary,target)
    finally:
        for temporary,target in pending:
            if temporary.exists():temporary.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config',nargs='?',type=Path,default=ROOT/'config/editor-defaults.toml')
    parser.add_argument('--out-dir',type=Path,default=ROOT/'build/editor-settings')
    parser.add_argument('--write-abi',type=Path,help='explicitly regenerate owned ABI include')
    args=parser.parse_args()
    try:
        outputs=compile_defaults(args.config.read_bytes())
        write_outputs(outputs,args.out_dir)
        if args.write_abi:
            write_outputs({args.write_abi.name:outputs['settings.inc']},args.write_abi.parent)
    except (SettingsError,OSError) as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps(dict(status='generated',bytes=SIZE,
        table_sha256=hashlib.sha256(outputs['editor-defaults.bin']).hexdigest(),
        files=list(outputs)),sort_keys=True))


if __name__=='__main__':main()

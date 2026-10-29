"""Exact editor capsule and atomic D81 publication guard.

The retired cache-family builder used to live here. Production images now build
directly from Makefile dependencies; this module only authenticates the current
resident/capsule set and publishes a disk from those already-built bytes.
"""
from pathlib import Path
import argparse
import ast
import binascii
import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess
import sys

SCHEMA = 3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_changed(path, data):
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return True


def editor_names(project):
    names = []
    tree = ast.parse((project / "tools/cpu_editor.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "NAMES"
            for target in node.targets
        ):
            names = list(ast.literal_eval(node.value))
        if (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "NAMES"
        ):
            if not isinstance(node.op, ast.Add):
                raise ValueError("unsupported catalog declaration")
            names += ast.literal_eval(node.value)
    if not names or len(names) != len(set(names)):
        raise ValueError("missing/duplicate editor catalog")
    return names


def body_plan_sources(project):
    """Source stability around publication, not an implicit capsule rebuild.

    The current R33 has replaced the old families. Its real include closure
    must remain stable during packaging just as those builder inputs did.
    editor-api.inc is generated from the verified resident identity below.
    """
    entry = project / "src/render/geos/body-plan/entry.s"
    if not entry.exists():
        if "fold" in editor_names(project) and "sema" not in editor_names(project):
            raise ValueError("missing current-BODY plan source")
        return set()  # historical62 packaging fixture; no replacement source
    paths = {entry, project / "Makefile", project / "cfg/overlay-r.cfg"}
    pending = [entry]
    while pending:
        path = pending.pop()
        for kind, name in re.findall(r'^\s*\.(include|incbin)\s+"([^\"]+)"', path.read_text(), re.M | re.I):
            if name == "editor-api.inc":
                continue
            found = next((p.resolve() for p in (path.parent / name, project / "src" / name, project / name) if p.is_file()), None)
            if found is None:
                raise ValueError("unresolved plan input " + name)
            if found not in paths:
                paths.add(found)
                if kind.lower() == "include":
                    pending.append(found)
    return paths


def identity(project, base):
    sys.path.insert(0, str(project / "tools"))
    from bindings import link_symbols, verify

    seal = verify(base / "build/editor.prg", base / "build/editor.lbl")
    report = json.loads((base / "build/editor-report.json").read_text())
    pairs = set(link_symbols(base / "build/editor.lbl"))
    if any((name, value) not in pairs for name, value in report["symbols"].items()):
        raise ValueError("report/label symbol mismatch")
    if (
        seal["digest"] != report["resident_binding"]["digest"]
        or seal["resident_sha256"] != report["sha256"]
    ):
        raise ValueError("report/PRG/labels mismatch")
    sources = (
        "tools/cache_job_build.py",
        "tools/cpu_editor.py",
        "tools/module_bindings.py",
        "tools/bindings.py",
        "tools/overlays.py",
    )
    return {
        "schema": SCHEMA,
        "resident": {
            name: sha(base / "build" / name)
            for name in ("editor.prg", "editor.lbl", "editor-report.json")
        },
        "binding": seal["digest"],
        "api": [
            report["symbols"]["se_overlay_call"],
            report["symbols"]["se_overlay_frame"],
        ],
        "source": {name: sha(project / name) for name in sorted(set(sources) | {str(path.relative_to(project)) for path in body_plan_sources(project)})},
    }


def editor_pair_index(slot, identity):
    """Mirror the resident fixed catalog contract for packaged editor assets."""
    if slot == 1 and 4 <= identity <= 33:
        return identity + 17
    if slot == 0:
        if identity in (1, 2):
            return identity - 1
        if identity == 14:
            return 2
        if 16 <= identity <= 33:
            return identity - 13
    raise ValueError(f"editor pair outside fixed catalog: slot{slot}/id{identity}")


def all_editor_capsules(project, record):
    digest = bytes.fromhex(record["binding"])
    result = {}
    identities = set()
    indexes = set()
    for name in editor_names(project):
        path = project / "build/overlays" / (name + ".seo")
        data = path.read_bytes()
        if (
            len(data) < 53
            or data[:5] != b"SEO2\x02"
            or data[20:36] != digest
            or data[36:52] != digest
        ):
            raise ValueError("foreign/invalid editor capsule " + name)
        if data[16:20] != struct.pack("<HH", *record["api"]):
            raise ValueError("foreign editor API " + name)
        if (
            int.from_bytes(data[8:10], "little") != len(data) - 36
            or binascii.crc_hqx(data[36:], 0xFFFF)
            != int.from_bytes(data[12:14], "little")
            or binascii.crc_hqx(data[:14] + data[16:36], 0xFFFF)
            != int.from_bytes(data[14:16], "little")
        ):
            raise ValueError("editor capsule CRC " + name)
        # Keep the old folded-profile slot/ID/fixed-entry/size contract after
        # deleting its family builder; a valid CRC alone is not admission.
        if data[7] != 0 or not 16 < len(data) - 36 <= 4096 or int.from_bytes(data[10:12], "little") != 16:
            raise ValueError("invalid fixed-entry editor capsule " + name)
        if name == "fold" and (data[5], data[6]) != (0, 33):
            raise ValueError("invalid body-plan identity")
        capsule_identity = (data[5], data[6])
        if data[5] not in (0, 1) or data[6] == 0 or capsule_identity in identities:
            raise ValueError("duplicate/invalid editor capsule identity " + name)
        index = editor_pair_index(*capsule_identity)
        if index in indexes:
            raise ValueError("duplicate fixed editor catalog index " + name)
        identities.add(capsule_identity)
        indexes.add(index)
        result[name] = sha(path)
    if indexes != set(range(51)):
        raise ValueError("incomplete fixed editor pair/index contract")
    return result


def package_inputs(project, runtime=False):
    prefix = "runtime-" if runtime else ""
    manifest = json.loads(
        (project / "build" / (prefix + "disk-manifest.json")).read_text()
    )
    command = manifest["command"]
    members = []
    for index, item in enumerate(command):
        if item != "-write":
            continue
        path = Path(command[index + 1]).resolve()
        if not path.is_relative_to(project / "build"):
            raise ValueError("foreign packaging input path")
        members.append([str(path.relative_to(project)), command[index + 2]])
    if not members or len(members) != len({native for _, native in members}):
        raise ValueError("missing/duplicate packaging member")
    dependencies = [
        "tools/package.py",
        "tools/cache_job_build.py",
        "tools/overlays.py",
        "tools/bindings.py",
        "tools/d81_image.py",
        "tools/cpu_editor.py",
        "build/editor-report.json",
        "build/editor.lbl",
    ]
    if not runtime:
        dependencies.append("build/overlay-probe-report.json")
    files = {
        name: sha(project / name)
        for name in sorted(set(dependencies + [path for path, _ in members]))
    }
    return {"members": members, "files": files}


def ensure_disk(project, c1541="c1541", runtime=False):
    """Publish once from a byte-stable resident and complete capsule cohort."""
    project = project.resolve()
    prefix = "runtime-" if runtime else ""
    disk = project / "build" / (
        "supereditor-runtime.d81" if runtime else "supereditor.d81"
    )
    manifest = project / "build" / (prefix + "disk-manifest.json")
    proof = project / "build" / (prefix + "disk-content.json")
    lock = project / "build" / ("." + prefix + "disk-content.lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RuntimeError("packaging check already running")
    os.close(descriptor)
    try:
        record = identity(project, project)
        capsules = all_editor_capsules(project, record)
        before = None
        try:
            before = package_inputs(project, runtime)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass
        if before is not None and proof.exists() and disk.exists():
            try:
                old = json.loads(proof.read_text())
                if (
                    old["inputs"] == before
                    and old["disk_sha256"] == sha(disk)
                    and old["manifest_sha256"] == sha(manifest)
                    and old["editor_capsules"] == capsules
                ):
                    return {
                        "packaged": False,
                        "members": len(before["members"]),
                        "editor_capsules": len(capsules),
                        "disk_sha256": old["disk_sha256"],
                    }
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                pass
        previous = {
            path: path.read_bytes() if path.exists() else None
            for path in (disk, manifest)
        }
        try:
            command = [
                sys.executable,
                project / "tools/package.py",
                "--c1541",
                c1541,
            ]
            if runtime:
                command.append("--runtime")
            subprocess.run(
                command, cwd=project, check=True, stdout=subprocess.DEVNULL
            )
            if identity(project, project) != record:
                raise RuntimeError("resident/source changed during packaging")
            if all_editor_capsules(project, record) != capsules:
                raise RuntimeError("editor capsule changed during packaging")
            current = package_inputs(project, runtime)
            generated = {
                "build/overlays/" + name + ".seo"
                for name in ("short", "extra", "badcrc", "badhdr", "binderr", "payerr")
            }
            if before is not None:
                for name, value in before["files"].items():
                    if name not in generated and sha(project / name) != value:
                        raise RuntimeError("input changed during packaging: " + name)
            spec = importlib.util.spec_from_file_location(
                "_cache_disk_oracle", project / "tools/d81_image.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            image = module.D81Image(disk.read_bytes())
            for name, native in current["members"]:
                dos_name = native.split(",")[0].upper().encode("ascii")
                kind = 1 if native.lower().endswith(",s") else 2
                if image.read(dos_name, kind=kind).data != (project / name).read_bytes():
                    raise ValueError("packaged bytes differ: " + name)
            if json.loads(manifest.read_text())["sha256"] != sha(disk):
                raise ValueError("disk manifest SHA mismatch")
            state = {
                "inputs": current,
                "disk_sha256": sha(disk),
                "manifest_sha256": sha(manifest),
                "editor_capsules": capsules,
            }
            write_changed(
                proof,
                (json.dumps(state, indent=2, sort_keys=True) + "\n").encode(),
            )
            return {
                "packaged": True,
                "members": len(current["members"]),
                "editor_capsules": len(capsules),
                "disk_sha256": state["disk_sha256"],
            }
        except BaseException:
            for path, data in previous.items():
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    write_changed(path, data)
            raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--runtime", action="store_true")
    parser.add_argument("--c1541", default="c1541")
    arguments = parser.parse_args()
    if not arguments.package:
        parser.error("this guard only publishes already-built editor assets")
    print(
        json.dumps(
            ensure_disk(
                arguments.project, arguments.c1541, arguments.runtime
            ),
            sort_keys=True,
        )
    )

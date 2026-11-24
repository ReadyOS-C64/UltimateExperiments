"""Build an owned-run Ultimate PRG and its matching MODEL.BIN."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zlib

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "probe"
CORE = "reu dot matrix scale embedding wide vector network cache attention_exp attention".split()
PROBE = "boot clock main uci integrity".split()
RUN_PATH = re.compile(r"/USB[1-4]/(?:automation/vice_tasks_dotnet/)?TINY64-[A-Z0-9-]{6,43}")


def genc_rc32_table():
    entries = []
    for value in range(256):
        for _ in range(8):
            value = (value >> 1) ^ (0xedb88320 if value & 1 else 0)
        entries.append(value)
    lines = []
    for byte in range(4):
        lines.append(f"table{byte}:")
        for start in range(0, 256, 16):
            row = entries[start:start + 16]
            lines.append("    .byte " + ",".join(f"${v >> (8 * byte) & 255:02x}" for v in row))
    return "\n".join(lines) + "\n"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_model(source, out, remote, *, name, prefix, offset, base_size):
    data = source.read_bytes()
    if (data[:5] != b"T64M\x04" or
            data[53:64] != name.encode("ascii").ljust(11, b"\0") or
            not 128 <= data[52] <= 255 or
            len(data) != int.from_bytes(data[12:16], "little") or
            len(data) != base_size + 99 * (data[52] - 128)):
        raise ValueError(f"expected a compatible named {name} image")
    filename = name + ".BIN"
    (out / filename).write_bytes(data)
    crc = zlib.crc32(data)
    source_definitions = (
        f'.define {prefix}_MODEL_PATH "{remote}/{filename}"\n'
        f"{prefix}_MODEL_SIZE = {len(data)}\n"
        f"{prefix}_MODEL_CRC = ${crc:08x}\n"
    )
    descriptor = {
        "file": filename,
        "name": name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "crc32": f"{crc:08x}",
        "context": data[52],
        "reu_offset": offset,
    }
    return source_definitions, descriptor


def build(out, remote, core_dir=ROOT / "build", *, interactive=False, qualify_reu=False,
          model_image=ROOT / "build/model.reu", context_test=False, automation=False,
          second_model=None, third_model=None):
    if not RUN_PATH.fullmatch(remote):
        raise ValueError("remote directory must be an owned TINY64 run folder on a USB drive")
    if automation and not interactive:
        raise ValueError("keyboard automation requires the interactive console")
    if third_model is not None and second_model is None:
        raise ValueError("the Japanese console requires the C64PROGINFO image as well")
    if second_model is not None and not interactive:
        raise ValueError("model selection requires the interactive console")
    questions = ["what is 7 times 8", "what is the capital of peru"]
    answers = ["7 times 8 is 56.", "Lima."]
    context_source = ""
    if context_test:
        if interactive:
            raise ValueError("the context probe runs scripted input without the interactive console")
        fixture = json.loads((ROOT / "tests/fixtures/context-probe.json").read_bytes())
        questions[0], answers[0] = fixture["question"], fixture["answer"]
        if (not 0 < len(questions[0]) <= 72 or not 0 < len(answers[0]) <= 78
                or len(questions[0]) + 1 + len(answers[0]) != 128
                or any(not " " <= c <= "~" for c in questions[0] + answers[0])):
            raise ValueError("expected a printable-ASCII context-boundary fixture")
        context_source = ".define CONTEXT_PROMPT " + ",".join(str(ord(c)) for c in questions[0]) + "\n"
    out.mkdir(parents=True, exist_ok=True)
    model = out / "MODEL.BIN"
    payload = model_image.read_bytes()
    core_labels = (core_dir / "core.lbl").read_text()
    group4 = any(line.endswith(" .group4_dot") for line in core_labels.splitlines())
    group8 = any(line.endswith(" .reu_group8_read") for line in core_labels.splitlines())
    version = payload[4:5]
    supported_version = b"\x04" if group8 else b"\x02" if group4 else b"\x01"
    if payload[:4] != b"T64M" or not b"\x01" <= version <= supported_version:
        raise ValueError("model image layout is incompatible with the linked core")
    if context_test and version == b"\x04" and payload[52:53] != b"\x80":
        raise ValueError("the legacy context diagnostic requires a 128-position model")
    model.write_bytes(payload)
    crc = zlib.crc32(payload)
    model_source = ""
    additional_models = {}
    if second_model is not None and (not group8 or version != b"\x03"):
        raise ValueError("model selection requires the original group-eight image")
    for source, key, name, prefix, offset in (
        (second_model, "second_model", "C64PROGINFO", "SECOND", 0x100000),
        (third_model, "third_model", "E2JROMAJI", "THIRD", 0x200000),
    ):
        if source is not None:
            definitions, descriptor = add_model(source, out, remote, name=name,
                                                prefix=prefix, offset=offset, base_size=len(payload))
            model_source += definitions
            additional_models[key] = descriptor
    run_hash = hashlib.sha256(remote.encode("ascii")).digest()
    palette = (1, 3, 6, 7, 13, 14)
    marker = [palette[byte % len(palette)] for byte in run_hash[:12]]
    nonce = int.from_bytes(run_hash[-2:], "little")
    (out / "bundle.inc").write_text(
        f'.define MODEL_PATH "{remote}/MODEL.BIN"\n'
        f"MODEL_SIZE = {model.stat().st_size}\n"
        f"MODEL_CRC32 = ${crc:08x}\n"
        f"RUN_NONCE = ${nonce:04x}\n"
        f"INTERACTIVE = {int(interactive)}\n"
        f"QUALIFY_REU = {int(qualify_reu)}\n"
        f"CONSOLE_AUTOMATION = {int(automation)}\n"
        f"CONTEXT_TEST = {int(context_test)}\n"
        f"DUAL_MODEL = {int(second_model is not None)}\n"
        f"THIRD_MODEL = {int(third_model is not None)}\n"
        f".define RUN_MARKER {','.join(map(str, marker))}\n"
        + context_source + model_source)
    (out / "crc_table.inc").write_text(genc_rc32_table())
    native_objs = []
    sources = PROBE + ["question", "keyboard", "console"] if interactive else PROBE
    if second_model is not None:
        sources = [*sources, "models"]
    if qualify_reu:
        sources = [*sources, "reu_qualify"]
    for stem in sources:
        obj = out / f"{stem}.o"
        subprocess.run(["ca65", "-I", str(out), "-g", "-o", str(obj),
                        str(SOURCE / f"{stem}.s")], check=True)
        native_objs.append(obj)
    kernels = (["dot_group4"] if group4 else []) + (["dot_group8"] if group8 else [])
    core_objs = [core_dir / f"{name}.o" for name in [*CORE, *kernels]]
    prg = out / "PROBE.PRG"
    labels = out / "probe.lbl"
    subprocess.run(["ld65", "-C", str(SOURCE / "ultimate.cfg"), "-m", str(out / "probe.map"),
                    "-Ln", str(labels), "-o", str(prg), *map(str, [*core_objs, *native_objs])], check=True)
    symbols = {name.lstrip("."): int(addr, 16)
               for kind, addr, name in (line.split() for line in labels.read_text().splitlines())
               if kind == "al"}
    prg_data = prg.read_bytes()
    load_addr = int.from_bytes(prg_data[:2], "little")
    end = load_addr + len(prg_data) - 2
    if load_addr != 0x801 or symbols["probe_start"] != 0x80d:
        raise ValueError("invalid BASIC SYS bootstrap")
    if (symbols["__PROBE_LOAD__"] != symbols["__WORK_START__"] or
            symbols["__PROBE_LOAD__"] + symbols["__PROBE_SIZE__"] != end or
            symbols["__PROBE_RUN__"] != 0xa000):
        raise ValueError("unexpected probe relocation map")
    core = (core_dir / "core.bin").read_bytes()
    core_offset = 0x1000 - load_addr + 2
    if prg_data[core_offset:core_offset + len(core)] != core:
        raise ValueError("resident probe core differs from the Peddle build")
    manifest = {
        "remote_path": remote,
        "model_bytes": model.stat().st_size,
        "model_crc32": f"{crc:08x}",
        "prg_sha256": digest(prg),
        "model_sha256": digest(model),
        "model_format_version": version[0],
        "resident_core_sha256": hashlib.sha256(core).hexdigest(),
        "core_object_sha256": {p.name: digest(p) for p in core_objs},
        "load_range": [load_addr, end - 1],
        "probe_bytes": symbols["__PROBE_SIZE__"],
        "mailbox": 0xce00,
        "nonce": nonce,
        "video_colors": marker,
        "answer_records": [0xcc00, 0xcd00],
        "questions": questions,
        "expected_answers": answers,
    }
    if context_test:
        manifest["context_test"] = True
    if interactive:
        manifest["interactive"] = True
        for key in ("answer_records", "questions", "expected_answers"):
            del manifest[key]
    if automation:
        manifest["automation_keyboard"] = True
    if qualify_reu:
        manifest["reu_qualification_mailbox"] = symbols["REU_QUALIFICATION_RESULT"]
    if additional_models:
        manifest.update(additional_models)
        manifest["timing_row"] = 22
    (out / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--remote", required=True)
    parser.add_argument("--core-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--automation", action="store_true")
    parser.add_argument("--qualify-reu", action="store_true")
    parser.add_argument("--context-test", action="store_true")
    parser.add_argument("--model-image", type=Path, default=ROOT / "build/model.reu")
    parser.add_argument("--second-model", type=Path)
    parser.add_argument("--third-model", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.out.resolve(), args.remote, args.core_dir.resolve(),
                           interactive=args.interactive, qualify_reu=args.qualify_reu,
                           model_image=args.model_image, context_test=args.context_test,
                           automation=args.automation, second_model=args.second_model,
                           third_model=args.third_model), indent=2))

"""Check linked segments and stable entry/arena symbols against the host map."""
import json
from pathlib import Path
import re
import sys
import struct
import hashlib
import zlib


def verify(map_text, labels_text, prg=None, overlay_payloads=None, import_payload=None, shadow_payload=None,saver_payload=None,format_payload=None,trap_payload=None):
    errors = []
    symbols = {name.lstrip("."): int(addr, 16) for addr, name in
               re.findall(r"^al ([0-9A-Fa-f]+) (\S+)", labels_text, re.M)}
    options_state = "dos64_options_required" in symbols or "dos64_bios_initial_mode" in symbols
    expected = {"__MAIN_START__": 0x0801, "__MAIN_SIZE__": 0x37FF,
                "__ZP_START__": 0x20, "__ZP_SIZE__": 0xC0,
                "__CONTROL_START__": 0xE000, "__CONTROL_SIZE__": 0x1000,
                "dos64_entry": 0x080D}
    for name, value in expected.items():
        if symbols.get(name) != value:
            errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
    bounds = {"LOADADDR": (0, 1), "BASIC": (0x0801, 0x080C),
              "CODE": (0x080D, 0x3FFF), "RODATA": (0x080D, 0x3FFF),
              "TESTCODE": (0x080D, 0x3FFF), "ZEROPAGE": (0x20, 0xDF),
              "DEVICECODE": (0x5000, 0x5FFF),
              "LOADERCOLD": (0x4000,0x43FF), "LOADERADOPT": (0x6000,0x617F),
              "IMPORTCODE": (0x7000, 0x7FFF),
              "COLDINIT": (0x7000,0x7FFF), "COLDRODATA": (0x7000,0x7FFF), "UNITCOLD": (0x7401,0x7FFF),
              "UNITEXTRA": (0xEF00,0xEFFA), "UNITTAIL": (0xFF00,0xFFCE), "CPUTRAP":(0xFE00,0xFEFF),
              "NATIVESTATE": (0x080D,0x3FFF), "INPUTCODE": (0xC900,0xCFFF),
              "UCIBUFFER": (0xC100, 0xC8FF),
              "IRQMAIN":(0xC900,0xCFFF),"IRQDEVICE":(0xC900,0xCFFF),"PITCODE":(0xC900,0xCFFF),"GFXCODE":(0xC900,0xCFFF),
              "FORMATCODE":(0xC900,0xCFFF),"FORMATCHECKCODE":(0xC900,0xCFFF),"DISKCODE":(0xC900,0xCFFF),"HDCODE": (0xC900,0xCFFF),"HDBIOS":(0xF000,0xFDFF),"SAVERCODE":(0xB010,0xB7FF),
              "FILECODE": (0xC900, 0xCFFF), "RENDERCODE": (0xC900, 0xCFFF), "DISPLAYCODE": (0xC900,0xCFFF),
              "NARROWFONT": (0x4400,0x47FF), "FULLFONT": (0x4800,0x4FFF),
              "RANGEBUFFER": (0xC000, 0xC0FF), "BSS": (0xE000, 0xE0FF), "PAGEMAP": (0xE100, 0xE8FF),
              "CACHEMETA": (0xE900, 0xE9FF), "DEVICESTATE": (0xEA00, 0xEEFF)}
    segments = []
    for name, first, last, size in re.findall(
            r"^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})", map_text, re.M):
        a, b, count = int(first, 16), int(last, 16), int(size, 16)
        segments.append({"name": name, "start": a, "end": b, "bytes": count})
        if name not in bounds or not (bounds[name][0] <= a <= b <= bounds[name][1]):
            errors.append(f"{name} outside owned range: ${a:04X}-${b:04X}")
        if b - a + 1 != count:
            errors.append(f"{name} has inconsistent size")
    extra = [x for x in segments if x["name"] == "UNITEXTRA"]
    if extra and (len(extra) != 1 or extra[0]["start"] != 0xef00 or extra[0]["bytes"] != 251 or
                  not any(x["name"] == "UNITCOLD" for x in segments)):
        errors.append("UNITEXTRA must be the exact251-byte unit-only sidecar")
    tail = [x for x in segments if x["name"] == "UNITTAIL"]
    if tail and (len(tail) != 1 or tail[0]["start"] != 0xff00 or tail[0]["bytes"] != 207 or not extra):
        errors.append("UNITTAIL must be the exact207-byte unit-only sidecar with UNITEXTRA")
    if extra and not tail:
        errors.append("UNITEXTRA requires its exact UNITTAIL companion")
    for name,value in {"__UNITTAIL_RUN__":0xff00,"__UNITTAIL_LOAD__":0xff00,"__UNITTAIL_SIZE__":207}.items():
        if tail and symbols.get(name)!=value:
            errors.append(name+": invalid unit-only sidecar identity")
        if not tail and name in symbols:
            errors.append(name+": sidecar symbol without linked segment")
    if not segments:
        errors.append("No linker segments found")
    for index, seg in enumerate(segments):
        for other in segments[index+1:]:
            # Only these two separately emitted images may share a run window.
            variant={"FILECODE":"FILE","RENDERCODE":"TEXT","DISPLAYCODE":"TEXT","FORMATCHECKCODE":"TEXT","FORMATCODE":"FORMAT","INPUTCODE":"INPUT","IRQMAIN":"PIT","IRQDEVICE":"PIT","PITCODE":"PIT","GFXCODE":"GFX","HDCODE":"HD","DISKCODE":"DISK"}
            exclusive_overlays = seg["name"] in variant and other["name"] in variant and variant[seg["name"]]!=variant[other["name"]]
            if not exclusive_overlays and max(seg['start'], other['start']) <= min(seg['end'], other['end']):
                errors.append(f"Overlapping segments {seg['name']} and {other['name']}")
    if 0x4000 // 0x4000 != 0x6000 // 0x4000 or 0x4800 % 0x800:
        errors.append("VIC bank/font alignment mismatch")
    # The extended runtime layout is one contiguous C64 PRG. Its intentional
    # zero padding is initialization, not additional executable allocation.
    runtime = "__DEVICE_START__" in symbols
    load = {"layout": "runtime" if runtime else "standalone", "start": 0x0801,
            "linked_file_bytes": sum(s["bytes"] for s in segments
                                     if s["name"] in ("BASIC", "CODE", "RODATA", "TESTCODE", "DEVICECODE", "IMPORTCODE", "COLDINIT", "COLDRODATA", "UNITCOLD", "NATIVESTATE", "LOADERCOLD", "NARROWFONT", "FULLFONT")),
            "padding": [], "payload_checked": prg is not None}
    main_end = max((s["end"] + 1 for s in segments
                    if s["name"] in ("BASIC", "CODE", "RODATA", "TESTCODE", "NATIVESTATE")), default=0x0801)
    if runtime:
        area_expected = {"__MAIN_FILEOFFS__": 2, "__MAIN_LAST__": main_end,
                         "__INITVIDEO_START__": 0x4000, "__INITVIDEO_SIZE__": 0x1000,
                         "__INITVIDEO_FILEOFFS__": 0x3801, "__INITVIDEO_LAST__": (0x5000 if any(x["name"]=="FULLFONT" for x in segments) else 0x4000),
                         "__DEVICE_START__": 0x5000, "__DEVICE_SIZE__": 0x1000,
                         "__DEVICE_FILEOFFS__": 0x4801,
                         "__UCI_RAM_START__": 0xC100, "__UCI_RAM_SIZE__": 0x0800}
        device = [s for s in segments if s["name"] == "DEVICECODE"]
        device_end = device[0]["end"] + 1 if device else 0x5000
        area_expected["__DEVICE_LAST__"] = device_end
        if device:
            area_expected.update({"__DEVICECODE_LOAD__": device[0]["start"],
                                  "__DEVICECODE_RUN__": device[0]["start"],
                                  "__DEVICECODE_SIZE__": device[0]["bytes"]})
        for name, value in area_expected.items():
            if symbols.get(name) != value:
                errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
        load["end_exclusive"] = device_end
        for name, first, last in (("unused_main", main_end, 0x4000),
                                  ("display_matrix_and_guard_zero", max((s['end']+1 for s in segments if s['name']=='LOADERCOLD'),default=0x4000), 0x4400 if any(x["name"]=="FULLFONT" for x in segments) else 0x5000)):
            if first < last:
                load["padding"].append({"name": name, "start": first,
                                        "end": last-1, "bytes": last-first,
                                        "file_offset": first-0x0801+2, "value": 0})
    else:
        load["end_exclusive"] = main_end
        if any(s["name"] in ("DEVICECODE", "UCIBUFFER") for s in segments):
            errors.append("Runtime-only segments require the contiguous runtime layout")
    overlays = {seg["name"]: seg for seg in segments
                if seg["name"] in ("FILECODE", "RENDERCODE", "INPUTCODE","IRQMAIN","GFXCODE","HDCODE","DISKCODE")}
    loader=[s for s in segments if s['name']=='LOADERCOLD']
    adopt=[s for s in segments if s['name']=='LOADERADOPT']
    load['cold_loader']=None
    if loader or adopt:
        if len(loader)!=1 or len(adopt)!=1 or 'FILECODE' not in overlays:
            errors.append('Cold loader requires paired phase1 and trailing FILE helper')
        else:
            engine=overlays['FILECODE'];helper=adopt[0];core=loader[0]
            source=0x6010+engine['bytes'];far=0x340010+engine['bytes']
            expected={'__LOADERCOLD_LOAD__':0x4000,'__LOADERCOLD_RUN__':0x4000,'__LOADERCOLD_SIZE__':core['bytes'],
                      'dos64_loader_code_start':0x4000,'dos64_loader_code_end':core['end']+1,
                      '__LOADERADOPT_LOAD__':engine['end']+1,'__LOADERADOPT_RUN__':0x6000,'__LOADERADOPT_SIZE__':helper['bytes'],
                      'dos64_loader_adopt':0x6000,'dos64_loader_adopt_end':helper['end']+1,'dos64_native_nmi':0x5882}
            if core['start']!=0x4000 or helper['start']!=0x6000 or not 0x100<helper['bytes']<=0x180 or helper['end']>=source or source+helper['bytes']>0x6800:
                errors.append('Cold loader run/source/compare lifetime bounds invalid')
            for name,value in expected.items():
                if symbols.get(name)!=value:errors.append('Cold loader linked metadata mismatch: '+name)
            overlays['FILECODE']={**engine,'engine_bytes':engine['bytes'],'helper_bytes':helper['bytes'],
                                  'bytes':engine['bytes']+helper['bytes'],'end':engine['end']+helper['bytes']}
            load['cold_loader']={'phase1':core,'phase2':helper,'source':source,'reu':far,
                                 'trust':'START verified full PRG CRC; after bootstrap full helper byte comparison before execution; no FILE native CRC'}
    display=[x for x in segments if x["name"]=="DISPLAYCODE"]
    if overlays:
        renderer=overlays.get("RENDERCODE")
        if len(display)!=1 or renderer is None:
            errors.append("TEXT requires separate renderer and VIC display segments")
        else:
            part=display[0]
            if renderer["bytes"]!=1003 or part["bytes"]!=245 or part["start"]!=renderer["end"]+1:
                errors.append("TEXT must be contiguous canonical1003+245 bytes")
            for suffix,value in (("RUN",part["start"]),("LOAD",part["start"]),("SIZE",part["bytes"])):
                if symbols.get("__DISPLAYCODE_"+suffix+"__")!=value:errors.append("DISPLAYCODE metadata mismatch")
            overlays["RENDERCODE"]={**renderer,"end":part["end"],"bytes":renderer["bytes"]+part["bytes"],"renderer_bytes":renderer["bytes"],"display_bytes":part["bytes"]}
    elif display:errors.append("DISPLAYCODE requires exclusive TEXT overlay")
    format_parts=[x for x in segments if x["name"]=="FORMATCODE"]
    check_parts=[x for x in segments if x["name"]=="FORMATCHECKCODE"]
    format_layout=bool(format_parts or check_parts)
    if format_layout:
        if len(format_parts)!=1 or len(check_parts)!=1 or "RENDERCODE" not in overlays or "GFXCODE" not in overlays:
            errors.append("FORMAT requires paired nested payload/TEXT checker and GFX")
        else:
            part=format_parts[0];checker=check_parts[0];text=overlays["RENDERCODE"];gfx=overlays["GFXCODE"]
            if part['start']!=0xc900 or not 0<part['bytes']<=0x700 or checker['start']!=0xcde0 or not 0<checker['bytes']<=544 or checker['end']>=0xd000:
                errors.append("FORMAT/checker exact managed-window bounds invalid")
            for name,obj in (("FORMATCODE",part),("FORMATCHECKCODE",checker)):
                for suffix,value in (("RUN",obj['start']),("LOAD",obj['start']),("SIZE",obj['bytes'])):
                    if symbols.get('__'+name+'_'+suffix+'__')!=value:errors.append(name+" metadata mismatch")
            if symbols.get('__FORMAT_START__')!=0xc900 or symbols.get('__FORMAT_SIZE__')!=0x700 or symbols.get('__FORMAT_LAST__')!=part['end']+1 or symbols.get('__FORMAT_FILEOFFS__')!=0:
                errors.append("FORMAT emitted area differs from linked payload")
            overlays['RENDERCODE']={**text,'end':checker['end'],'bytes':text['bytes']+checker['bytes'],'format_checker_bytes':checker['bytes']}
            begin=16+gfx['bytes'];end=begin+16+part['bytes']
            if end>0x800:errors.append("FORMAT nested source exceeds physical GFX slot")
            load['format']={'source':0x9000+begin,'reu':0x342000+begin,'run':0xc900,'bytes':part['bytes'],'padding':0x800-end,'checker':checker,'trust':'cold adoption and every direct selector8 check whole2048 GFXslot CRC outside covered slot; normal GFX unchanged'}
            if prg is not None:
                block=prg[0x9000-0x801+2:0x9800-0x801+2]
                header=b'D64O'+bytes((1,8))+struct.pack('<HHH',part['bytes'],0xc900,0)+b'FMT '
                if len(block)!=0x800 or block[begin:begin+16]!=header or any(block[end:]):errors.append("FORMAT nested header/padding mismatch")
                if format_payload is None or len(format_payload)!=part['bytes'] or block[begin+16:end]!=format_payload:errors.append("FORMAT source differs from linked output")
                address=symbols.get('dos64_format_slot_crc',-1);lo=symbols.get('dos64_overlay_code_start',-1);hi=symbols.get('dos64_overlay_code_end',-1)
                if not 0x080d<=lo<=address or address+4>hi or not hi<=0x4000 or prg[address-0x801+2:address-0x801+6]!=struct.pack('<I',zlib.crc32(block)):
                    errors.append("FORMAT whole-slot expected CRC must bind separate resident field")
    elif format_payload is not None:errors.append("FORMAT payload without linked FORMAT/checker")
    if "IRQMAIN" in overlays:
        members=[next((x for x in segments if x["name"]==name),None) for name in ("IRQMAIN","IRQDEVICE","PITCODE")]
        if any(x is None for x in members):errors.append("PIT requires all three contiguous members")
        else:
            for index,member in enumerate(members):
                for suffix,value in (("RUN",member["start"]),("LOAD",member["start"]),("SIZE",member["bytes"])):
                    if symbols.get("__"+member["name"]+"_"+suffix+"__")!=value:errors.append("PIT member metadata mismatch")
                if index and members[index-1]["end"]+1!=member["start"]:errors.append("PIT members must be contiguous")
            overlays["IRQMAIN"]={**members[0],"end":members[-1]["end"],"bytes":sum(x["bytes"] for x in members),"first_member_bytes":members[0]["bytes"]}
    fonts=[x for x in segments if x["name"] in ("NARROWFONT","FULLFONT")]
    load["startup_fonts"]=[]
    if overlays and len(fonts)!=2:errors.append("Runtime requires both explicitly loaded non-executable fonts")
    for name,start,count,digest in (("NARROWFONT",0x4400,1024,"c15f11a5ae43771657dd24295e37cff5886280b3c32d80c5fe62757eb4e38dfe"),("FULLFONT",0x4800,2048,"94fb2992461e7b79fcb3514d077727f33e5ee4f9d993f40f0aaeabf9c8f1ac30")):
        part=next((x for x in fonts if x["name"]==name),None)
        if part is None:continue
        if part["start"]!=start or part["bytes"]!=count:errors.append(name+" exact startup data range mismatch")
        for suffix,value in (("LOAD",start),("RUN",start),("SIZE",count)):
            if symbols.get("__"+name+"_"+suffix+"__")!=value:errors.append(name+" metadata mismatch")
        if prg is not None and hashlib.sha256(prg[start-0x801+2:start-0x801+2+count]).hexdigest()!=digest:errors.append(name+" loaded asset identity mismatch")
        load["startup_fonts"].append({"name":name,"start":start,"bytes":count,"sha256":digest,"executable":False,"ownership":"matrix/input phase must be released before display; persistent across code overlays"})
    load["overlays"] = []
    if overlays:
        if not runtime:
            errors.append("Overlays require the runtime layout")
        hd_layout="HDCODE"in overlays
        disk_layout="DISKCODE" in overlays
        expected_overlay_count=7 if disk_layout else (6 if hd_layout else 5)
        if len(overlays) != expected_overlay_count:
            errors.append("Complete FILE/TEXT/INPUT/PIT/GFX and optional paired HD/shadow overlay set required")
        device_end = load["end_exclusive"]
        if device_end > 0x6000:
            errors.append("Resident payload overlaps startup overlay sources")
        if device_end < 0x6000:
            load["padding"].append({"name": "unused_device", "start": device_end,
                                    "end": 0x5FFF, "bytes": 0x6000-device_end,
                                    "file_offset": device_end-0x0801+2, "value": 0})
        load["resident_end_exclusive"] = device_end
        load["end_exclusive"] = 0x7000
        variants = (("FILECODE", "FILE", b"FILE"), ("RENDERCODE", "RENDER", b"TEXT"), ("INPUTCODE", "INPUT", b"KEYS"),("IRQMAIN","PIT",b"TIME"),("GFXCODE","GFX",b"CGA "))+((("HDCODE","HD",b"HD  "),)if hd_layout else ())+((("DISKCODE","DISK",b"DSK "),)if disk_layout else ())
        for index, (segment_name, area_name, tag) in enumerate(variants):
            if segment_name not in overlays:
                continue
            seg = overlays[segment_name]
            fields = {f"__{area_name}_START__": 0xC900, f"__{area_name}_SIZE__": 0x700,
                      f"__{area_name}_FILEOFFS__": 0, f"__{area_name}_LAST__": seg["end"]+1,
                      f"__{segment_name}_LOAD__": 0xC900, f"__{segment_name}_RUN__": 0xC900,
                      f"__{segment_name}_SIZE__": seg.get("engine_bytes",seg.get("renderer_bytes",seg.get("first_member_bytes",seg["bytes"])))}
            for name, value in fields.items():
                if symbols.get(name) != value:
                    errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
            if seg["start"] != 0xC900:
                errors.append(f"{segment_name} must start at the exclusive execution window")
            if not 1 <= seg["bytes"] <= 0x700:
                errors.append(f"{segment_name} payload size must fit the exclusive window")
                continue
            source = (0x6000,0x6800,0x8000,0x8800,0x9000,0x9800,0xb800)[index]
            item = {"name": segment_name, "startup_source": source,
                    "reu_slot": 0x343800 if segment_name=="DISKCODE" else 0x340000+index*0x800, "slot_bytes": 0x800,
                    "payload_bytes": seg["bytes"], "run": 0xC900,
                    "members": ([{"name":"RENDERCODE","bytes":seg["renderer_bytes"]},{"name":"DISPLAYCODE","bytes":seg["display_bytes"]}] if "renderer_bytes" in seg else [{"name":segment_name,"bytes":seg["bytes"]}]),
                    "ownership": "startup sources released only after native bootstrap; FILE/TEXT execution exclusive"}
            load["overlays"].append(item)
            if prg is not None:
                offset = source-0x0801+2
                block = prg[offset:offset+0x800]
                expected_header = (b"D64O"+bytes((1, index+1)) +
                                   struct.pack("<HHH", seg["bytes"], 0xC900, 0)+tag)
                if len(block) != 0x800 or block[:16] != expected_header:
                    errors.append(f"{segment_name} startup slot has wrong header or length")
                elif not (format_layout and segment_name=="GFXCODE") and any(block[16+seg["bytes"]:]):
                    errors.append(f"{segment_name} startup slot tail is not zero")
                if overlay_payloads is not None:
                    payload = overlay_payloads.get(segment_name)
                    if payload is None or len(payload) != seg["bytes"] or block[16:16+seg["bytes"]] != payload:
                        errors.append(f"{segment_name} startup payload differs from its linked output")
    elif overlay_payloads:
        errors.append("Overlay payloads provided without linked overlay segments")
    cold = [seg for seg in segments if seg["name"] == "IMPORTCODE"]
    load["cold_import"] = None
    if cold:
        seg = cold[0]
        cold_parts=[item for item in segments if item["name"] in ("IMPORTCODE","COLDINIT","COLDRODATA","UNITCOLD")]
        cold_parts.sort(key=lambda item:item["start"])
        cold_end=max(item["end"]+1 for item in cold_parts)
        if [item["name"] for item in cold_parts] not in (["IMPORTCODE","COLDINIT","COLDRODATA"], ["IMPORTCODE","COLDINIT","COLDRODATA","UNITCOLD"]):
            errors.append("Cold image must retain ordered IMPORT/BIOS-bootstrap/data parts")
        unit = [item for item in cold_parts if item["name"] == "UNITCOLD"]
        if unit:
            if not 0x080D <= symbols.get("fixture_return",0) < 0x4000:
                errors.append("Unit return sentinel must remain resident")
            if not symbols.get("n_started") or not symbols.get("dos64_cold_open"):
                errors.append("Unit cold fixture host guard requires resident startup ownership")
        for before,after in zip(cold_parts,cold_parts[1:]):
            if before["end"]+1!=after["start"]:
                errors.append("Cold linked output contains an undeclared hole")
        for item in cold_parts:
            for suffix,value in (("LOAD",item["start"]),("RUN",item["start"]),("SIZE",item["bytes"])):
                if symbols.get("__"+item["name"]+"_"+suffix+"__")!=value:
                    errors.append("Cold segment metadata mismatch")
        if not runtime or len(overlays) not in (5,6,7):
            errors.append("Cold importer requires runtime and both committed overlay source phases")
        fields = {"__IMPORT_START__": 0x7000, "__IMPORT_SIZE__": 0x1000,
                  "__IMPORT_FILEOFFS__": 0, "__IMPORT_LAST__": cold_end,
                  "__IMPORTCODE_LOAD__": 0x7000, "__IMPORTCODE_RUN__": 0x7000,
                  "__IMPORTCODE_SIZE__": seg["bytes"],
                  "dos64_import_code_start": 0x7000,
                  "dos64_import_code_end": seg["end"]+1,
                  "dos64_import_state_end": seg["end"]+1}
        for name, value in fields.items():
            if symbols.get(name) != value:
                errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
        state_start = symbols.get("dos64_import_state_start", -1)
        if not 0x7000 <= state_start <= seg["end"]:
            errors.append("Cold importer state must be inside its discarded startup image")
        if seg["start"] != 0x7000 or not 1 <= seg["bytes"] <= 0x1000:
            errors.append("Cold importer must start at 7000 and fit its 4096-byte startup phase")
        else:
            load["end_exclusive"] = 0x8000
            if seg["end"] < 0x7FFF:
                first = cold_end
                load["padding"].append({"name": "cold_import_tail_zero", "start": first,
                                        "end": 0x7FFF, "bytes": 0x8000-first,
                                        "file_offset": first-0x0801+2, "value": 0})
            load["cold_import"] = {"start": 0x7000, "end": cold_end-1,
                                   "linked_bytes": cold_end-0x7000, "state_bytes": seg["end"]+1-state_start,
                                   "window_bytes": 0x1000, "payload_checked": import_payload is not None,
                                   "ownership": "startup-only after overlay bootstrap; code/state discarded before bitmap ownership"}
            if import_payload is not None:
                offset = 0x7000-0x0801+2
                if len(import_payload) != cold_end-0x7000 or (prg is not None and prg[offset:offset+len(import_payload)] != import_payload):
                    errors.append("Cold importer bytes differ from exact linked output")
    elif import_payload is not None or symbols.get("__IMPORTCODE_SIZE__", 0):
        errors.append("Linked cold importer segment is missing")
    if "INPUTCODE" in overlays:
        load["end_exclusive"]=0xa000 if "HDCODE"in overlays else 0x9800
        state=[seg for seg in segments if seg["name"]=="NATIVESTATE"]
        native_runtime = "dos64_native_entry" in symbols
        initialized = (b"\xa5\x00\x00\x00\x00"if "HDCODE"in overlays else b"\xa5\x00\x00") if native_runtime else b"\xa5\x00"
        cold_offset = 0
        if options_state:
            # Matched options is an explicit eight-byte schema, not spare state.
            initialized=b"\x03\xa5\x00\x00\x00\x00\x00\x00"
            cold_offset=1
            if not native_runtime or "HDCODE" not in overlays or not loader or len(state)!=1 or symbols.get('dos64_bios_initial_mode')!=state[0]['start'] or symbols.get('dos64_options_required')!=state[0]['end'] or symbols.get('dos64_loader_required')!=state[0]['end']-1:
                errors.append('Matched options state requires exact mode/cold/HD/loader/options eight-byte schema')
        elif loader:
            initialized+=b'\x00'
            if len(state)!=1 or symbols.get('dos64_loader_required')!=state[0]['end']:
                errors.append('Serialized loader-required flag must be final resident initialized byte')
        if len(state)!=1 or state[0]["bytes"]!=len(initialized) or symbols.get("dos64_cold_open")!=state[0]["start"]+cold_offset or symbols.get("dos64_cold_error")!=state[0]["start"]+cold_offset+1:
            errors.append("Cold/native reload guards must be initialized resident state bytes")
        elif native_runtime and (symbols.get("n_started")!=state[0]["start"]+cold_offset+2 or symbols.get("dos64_native_started")!=state[0]["start"]+cold_offset+2):
            errors.append("Native reload guard must follow cold-open/error state")
        elif prg is not None:
            offset=state[0]["start"]-0x0801+2
            if prg[offset:offset+len(initialized)]!=initialized:
                errors.append("Cold/native reload guards must load exact initialized defaults with the PRG")
    shadow=[seg for seg in segments if seg["name"]=="HDBIOS"]
    load["shadow"]=None
    if "HDCODE"in overlays or shadow or shadow_payload is not None:
        if "HDCODE"not in overlays or len(shadow)!=1:
            errors.append("HD and one separate shadow image must be paired")
        else:
            part=shadow[0];count=part["bytes"]
            expected={"__HDEXT_START__":0xf000,"__HDEXT_SIZE__":0xe00,"__HDEXT_FILEOFFS__":0,"__HDEXT_LAST__":part["end"]+1,"__HDBIOS_LOAD__":0xf000,"__HDBIOS_RUN__":0xf000,"__HDBIOS_SIZE__":count}
            if part["start"]!=0xf000 or not 1<=count<=3584 or any(symbols.get(k)!=v for k,v in expected.items()):errors.append("Shadow linked placement/length metadata mismatch")
            state=next((seg for seg in segments if seg["name"]=="NATIVESTATE"),None)
            if state is None or symbols.get("hdb_boot_drive")!=state["start"]+3+(1 if options_state else 0) or symbols.get("hdb_extension_ready")!=state["start"]+4+(1 if options_state else 0):errors.append("HD shadow/reload guards must be explicit initialized resident bytes")
            if prg is not None and shadow_payload is None:errors.append("HD shadow exact linked bytes are required for packaged verification")
            if shadow_payload is not None and(len(shadow_payload)!=count or(prg is not None and prg[0xa000-0x801+2:0xa000-0x801+2+count]!=shadow_payload)):errors.append("Shadow source differs from exact linked bytes")
            load["padding"].append({"name":"shadow_source_tail_zero","start":0xa000+count,"end":0xadff,"bytes":3584-count,"file_offset":0xa000+count-0x801+2,"value":0})
            load["shadow"]={"source":0xa000,"run":0xf000,"window_bytes":3584,"linked_bytes":count,"payload_checked":shadow_payload is not None,"excludes":"FE00-FFFF hardware vectors","ownership":"verified cold copy before guest cache; permanent RAM+IO/no KERNAL"}
            load["end_exclusive"]=0xae00
    trap=next((seg for seg in segments if seg["name"]=="CPUTRAP"),None)
    if trap:
        count=trap["bytes"]
        expected={"__TRAP_RUN_START__":0xfe00,"__TRAP_RUN_SIZE__":0x100,"__TRAP_RUN_FILEOFFS__":0,"__TRAP_RUN_LAST__":0xfe00+count,"__CPUTRAP_LOAD__":0xfe00,"__CPUTRAP_RUN__":0xfe00,"__CPUTRAP_SIZE__":count}
        if not load["shadow"] or trap["start"]!=0xfe00 or not 1<=count<=256 or any(symbols.get(k)!=v for k,v in expected.items()):errors.append("CPU trap layout must fit FE00-FEFF after separate HD shadow")
        if prg is not None and (trap_payload is None or len(trap_payload)!=count or prg[0xae00-0x801+2:0xae00-0x801+2+count]!=trap_payload):errors.append("CPU trap exact linked source required")
        load["cpu_trap"]={"source":0xae00,"run":0xfe00,"linked_bytes":count,"verified_cold_pages":15,"ownership":"copied and verified before cache; FF00-FFFF excluded"}
    elif trap_payload is not None:errors.append("CPU trap payload requires linked CPUTRAP")
    saver=next((seg for seg in segments if seg["name"]=="SAVERCODE"),None)
    load["saver"]=None
    if saver:
        count=saver["bytes"]
        expected={"__SAVER_START__":0xb010,"__SAVER_SIZE__":0x7f0,"__SAVER_FILEOFFS__":0,"__SAVER_LAST__":0xb010+count,"__SAVERCODE_LOAD__":0xb010,"__SAVERCODE_RUN__":0xb010,"__SAVERCODE_SIZE__":count}
        if not load["shadow"] or saver["start"]!=0xb010 or not 1<=count<=0x7f0 or any(symbols.get(k)!=v for k,v in expected.items()):errors.append("SAVER requires exact B010-B7FF linked modal payload after HD/shadow")
        if prg is not None:
            block=prg[0xb000-0x801+2:0xb800-0x801+2]
            header=b"D64O"+bytes((1,7))+struct.pack("<HHH",count,0xb010,0)+b"SAVE"
            if len(block)!=0x800 or block[:16]!=header or any(block[16+count:]):errors.append("SAVER startup header/slot/tail mismatch")
            if saver_payload is None or len(saver_payload)!=count or block[16:16+count]!=saver_payload:errors.append("SAVER exact linked source payload required")
        load["padding"].append({"name":"saver_source_gap_zero","start":0xae00+(trap["bytes"]if trap else 0),"end":0xafff,"bytes":512-(trap["bytes"]if trap else 0),"file_offset":0xae00-0x801+2+(trap["bytes"]if trap else 0),"value":0})
        load["end_exclusive"]=0xb800
        load["saver"]={"source":0xb000,"run":0xb010,"reu":0x343000,"slot_bytes":2048,"linked_bytes":count,"cache_frames":[24,32],"compare_stage":0xb800,"ownership":"modal paused borrow only; normal guest cache32frames"}
    elif saver_payload is not None:errors.append("SAVER payload requires linked SAVERCODE")
    load["disk"]=None
    if "DISKCODE" in overlays:
        load["disk"]={"source":0xb800,"run":0xc900,"reu":0x343800,"slot_bytes":2048,"linked_bytes":overlays["DISKCODE"]["bytes"],"overlay_identity":7,"physical_slot":8}
        if not saver:errors.append("DISK startup requires SAVER paired layout")
        load["end_exclusive"]=0xc000
    load["reserved_reu"]={"floppy_spare":{"start":0x380000,"end_exclusive":0x3da000},"installer_stage":{"start":0x3e0000,"end_exclusive":0x3f0000},"installer_anchor":{"start":0x3ff000,"end_exclusive":0x400000}} if "DISKCODE" in overlays else None
    load["startup_cache_phase"]={"start":0x8000,"end_exclusive":0xc000 if "DISKCODE" in overlays else (0xb800 if saver else (0xae00 if "HDCODE"in overlays else 0x9800)),"cache_frames":31 if "DISKCODE" in overlays else (27 if saver else (23 if "HDCODE"in overlays else 12)),"span_cache_frames":32 if "DISKCODE" in overlays else (28 if saver else (23 if "HDCODE"in overlays else 12)),"disk_frames":4 if "DISKCODE" in overlays else 0,"saver_frames":4 if saver else 0,"gap_cache_frames":[23]if saver else [],"overlay_frames":16 if "HDCODE"in overlays else 12,"shadow_frames":7 if "HDCODE"in overlays else 0}if overlays else None
    load["exclusive_overlay_window_bytes"] = 0x700 if overlays else 0
    load["max_linked_overlay_bytes"] = max((s["bytes"] for s in overlays.values()), default=0)
    load["overlay_source_bytes"] = sum(s["bytes"] for s in overlays.values())
    load["startup_overlay_bytes"] = (len(load["overlays"])+(1 if saver else 0))*0x800
    load["padding_bytes"] = sum(p["bytes"] for p in load["padding"])
    load["shadow_source_bytes"]=load["shadow"]["linked_bytes"]if load["shadow"]else 0
    load["payload_bytes"] = load["end_exclusive"] - load["start"]
    load["accounted_payload_bytes"]=load["linked_file_bytes"]+load["startup_overlay_bytes"]+load["padding_bytes"]+load["shadow_source_bytes"]+(trap["bytes"]if trap else 0)
    if load["accounted_payload_bytes"]!=load["payload_bytes"]:errors.append("Packaged bytes are not completely accounted by linked sources, slots and exact initialization padding")
    load["prg_bytes"] = load["payload_bytes"] + 2
    if prg is not None:
        if prg[:2] != b"\x01\x08":
            errors.append("PRG load address must be $0801")
        if len(prg) != load["prg_bytes"]:
            errors.append(f"PRG length: expected {load['prg_bytes']}, got {len(prg)}")
        for pad in load["padding"]:
            first = pad["file_offset"]
            data = prg[first:first+pad["bytes"]]
            if len(data) != pad["bytes"] or any(data):
                errors.append(f"PRG {pad['name']} is not complete zero initialization")
    return {"segments": segments, "load": load, "errors": errors, "passed": not errors}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("prg", type=Path, nargs="?")
    parser.add_argument("--overlay-files", type=Path)
    parser.add_argument("--overlay-render", type=Path)
    parser.add_argument("--overlay-input",type=Path)
    parser.add_argument("--overlay-pit",type=Path)
    parser.add_argument("--overlay-gfx",type=Path)
    parser.add_argument("--overlay-hd",type=Path)
    parser.add_argument("--overlay-disk",type=Path)
    parser.add_argument("--overlay-format",type=Path)
    parser.add_argument("--shadow",type=Path)
    parser.add_argument("--saver",type=Path)
    parser.add_argument("--cpu-trap",type=Path)
    parser.add_argument("--import-code", type=Path)
    args = parser.parse_args()
    map_path = args.map
    prg_path = args.prg or map_path.with_suffix(".prg")
    payloads = None
    if args.overlay_files or args.overlay_render or args.overlay_input or args.overlay_pit or args.overlay_gfx:
        if not (args.overlay_files and args.overlay_render and args.overlay_input and args.overlay_pit and args.overlay_gfx):
            parser.error("All three linked overlay payload files are required")
        payloads = {"FILECODE": args.overlay_files.read_bytes(),
                    "RENDERCODE": args.overlay_render.read_bytes(),"INPUTCODE":args.overlay_input.read_bytes(),"IRQMAIN":args.overlay_pit.read_bytes(),"GFXCODE":args.overlay_gfx.read_bytes()}
    if bool(args.overlay_hd)!=bool(args.shadow):parser.error("HD/shadow payloads must be paired")
    if args.overlay_hd:
        if payloads is None:parser.error("HD requires all five baseline payload files")
        payloads["HDCODE"]=args.overlay_hd.read_bytes()
    if args.overlay_disk:
        if payloads is None:parser.error("DISK requires baseline payloads")
        payloads["DISKCODE"]=args.overlay_disk.read_bytes()
    report = verify(map_path.read_text(), args.labels.read_text(), prg_path.read_bytes(), payloads, args.import_code.read_bytes() if args.import_code else None,args.shadow.read_bytes()if args.shadow else None,args.saver.read_bytes()if args.saver else None,args.overlay_format.read_bytes()if args.overlay_format else None,args.cpu_trap.read_bytes()if args.cpu_trap else None)
    map_path.with_suffix(".memory.json").write_text(json.dumps(report, indent=2)+"\n")
    if report["errors"]:
        raise SystemExit("\n".join(report["errors"]))
    print(f"Memory verified: {sys.argv[1]} ({sum(s['bytes'] for s in report['segments'])} linked bytes, {report['load']['padding_bytes']} PRG padding bytes)")

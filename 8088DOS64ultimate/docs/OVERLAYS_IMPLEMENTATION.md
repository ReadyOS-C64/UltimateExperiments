# Native FILE/TEXT/INPUT/PIT/GFX code overlays

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


Current five-overlay target is accepted in Peddle. Evidence (local development record, not distributed). Physical DOS acceptance applies separately to the earlier three-overlay runtime.

| Payload | Bytes | Startup source | Immutable REU slot |
|---|---:|---|---|
| FILE |1088|6000|340000|
| TEXT |963|6800|340800|
| INPUT |882|8000|341000|
| PIT/IRQ |1662|8800|341800|
| GFX |1278|9000|342000|

All share C900–CFFF, an exclusive 1792-byte execution window. TEXT is renderer718+VIC245; PIT includes IRQ132+403+converter1127. Maximum payload1662 leaves130 bytes. Each 2048-byte slot has a16-byte identity/version/length/run-address header. Bootstrap validates all headers before DMA and publishes readyA5 only after ALL10240 startup bytes commit. Sources initially occupy bitmap space and twelve cache frames; all assets must commit before cache/BIOS use. Assets are trusted immutable; headers are not payload CRCs. Build checks compare every linked payload/header/font/gap/tail and reject missing variants.

Resident wrappers own the busy lock for their entire bounded callback. No overlaid return address survives replacement; no lease crosses guest execution or another overlay. Busy/reentry/origin errors precede other checks. Acquisition invalidates current identity before DMA and publishes the new owner only on success. Partial DMA never enters the replacement. Same-image hits avoid DMA. IRQ/NMI may not share cache/REU/UCI/scratch ownership.

Cold importer/init/config occupies7000–7A4F,2640 bytes. Initialized cold_openA5 clears irreversibly before bitmap ownership; only loading a fresh PRG reopens it. Resident gateways reject late calls before touching discarded memory. Unit-only helpers occupy7A50–7E1E,975 bytes; the one-byte fixture return sentinel stays resident. The host fixture rejects before stack/register/evidence mutation after any native attempt, committed bootstrap or cold release. No init API reopens the lifetime. All seven standalone physical helper PRGs rebuild byte-identically.

Runtime/unit MAIN free217/216, DEVICE54; ZP18/30, BSS222, DEVICESTATE345. Both PRGs36865 load0801–97FF. These are measured per-window limits, not interchangeable spare RAM. Memory ledger (local development record, not distributed). PIT and GFX contracts are in [timer/IRQ](TIMER_IRQ_IMPLEMENTATION.md) and [graphics](CGA_RENDERER_IMPLEMENTATION.md). RAM+I/O, decimal clear and exclusive ownership remain callable preconditions.

# ReadyFS project inventory

ReadyFS is the standalone filesystem experiment in Ultimate Experiments. It is not integrated into the ReadyOS launcher.

| Location | Contents | Version-control policy |
|---|---|---|
| `src/apps/readyfs/` | C and 6502 assembly sources and headers | Committed |
| `cfg/readyfs_overlay.cfg` | Resident and 28-sidecar linker layout | Committed |
| `Makefile`, `build_support/` | Builders, host tests, VICE plans, hardware automation and documentation tools | Committed |
| `docs/` | User guide, UI, scripts, native configuration, safety and design references, screenshots | Committed |
| `artifacts/readyfs/readyfs-overlay-lab.d81` | Main interactive shell and sidecars | Committed |
| `artifacts/readyfs/readyfs-lab.d81` | Monolithic diagnostic disk | Committed |
| `obj/`, other `artifacts/` | Objects, PRGs, fixtures, maps and generated reports | Ignored |
| `logs/`, `AgentWorking/`, `agent.md` | Local run evidence and internal working history | Ignored |
| `../DOCS/readyfs/` | Publishable Markdown/HTML references and screenshot tours | Committed, rebuilt by the root docs tool |

`make readyfs` builds the complete project and performs its host/protocol/memory checks. VICE plans use `VICE_TASKS_REPO` or the default sibling `../../agenticdevharness` checkout. Hardware automation uses the Terminal-owned wrappers and ownership rules in `AGENTS.md`.

## Current verification

See [READYFS_ACCEPTANCE.md](READYFS_ACCEPTANCE.md) for the current acceptance summary and [README.md](index.md) for the public build and usage guide. Historical requirement ledgers contain dated milestones; they are not a list of raw log files shipped with a clone.

The owner-requested cleanup on 14 October 2026 deleted earlier local runs, retaining the latest successful physical batch capture (`batch-demo-20261013b`) and its final appendix output (`demo-v8-batch-appended-20261013`). No on-device test roots or user media were touched by this host-filesystem cleanup.

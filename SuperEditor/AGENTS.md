# SuperEditor working agreement

Read `agentsworking/README.md`, `agentsworking/STATUS.md`, and the current milestone
in `agentsworking/IMPLEMENTATION_PLAN.md` before starting work.

## Current authorization

The active 2026-10-24 user goal authorizes implementation and verification of
the full standalone editor using this plan. Work through the milestone gates
and retain evidence. Do not change the user's model or schedule work on their
behalf. The earlier planning-only phase boundary has been superseded.

Use up to three concurrent subagents when independent work is available. This
is a concurrency limit, not a lifetime limit: reuse or replace finished agents
with further safe assignments. All agents work in this repository without Git
worktrees; give each agent explicit file/section ownership, and serialize shared
builds. Multiple headless VICE sessions are authorized when each has separate
monitor ports (including the text-monitor port block at binary+100), working
disks, output folders and tracked PIDs. Stop only the
process owned by that run; never kill another run or all VICE processes.
Parallel runs also require unique runtime log and REU backing-image paths.
The private `synchronous_project` runner in tests/test_grid_editor_vice.py
appends a GUID; the installed harness uses second-resolution directories,
which can collide even when ports and working disks differ.

## Product constraints

- Standalone C64 program in idiomatic 6510 assembly, provisionally ca65/ld65.
- PETSCII Markdown-lite; 40/60/80-column views and a GEOS-font hires view.
- D81 and the existing .NET VICE automation harness; warp and drive traps for
  development. UltimateDOS and ReadyOS application integration are later work.
- Preserve `$C600-$C9FF` completely, including initialization, BSS, DMA and loaders.
- REU-backed document storage and overlays; logical allocations, not hard-coded
  physical bank ownership. Read the memory/overlay contracts before editing.
- Markdown syntax must be idiomatic for the C64 keyboard and PETSCII, with its
  differences documented. JSON support was explicitly removed by the user.
- Use operation-sized assembler micromodules for TUI and other reusable
  services, linking only the objects a consumer needs. Follow the ReadyOS TUI
  design roles in `src/tui/theme.inc`: blue background, white text, light-blue
  frames, yellow titles, cyan highlights and light-gray status. Match keyboard
  and popup conventions while preserving mixed-case document text.
- User permits throwaway probe apps and the sibling ZeroPage/Peddle test
  engine when they isolate an uncertainty usefully. Keep probe limitations clear.
- Menus, keyboard navigation, selection, copy/paste, file dialogs and folding
  must work in every display mode. Screenshots are part of feature evidence.

## Long-horizon continuity

- Update STATUS and the active milestone after a meaningful work session.
- Record decisions with stable IDs and status in DECISION_REGISTER. Distinguish
  user constraints, verified facts, design choices, and unproven estimates.
- Record new failures and reusable fixes in LESSONS_LEARNT with evidence links.
- Keep dated session notes under `agentsworking/sessions/` and test artifacts
  under `agentsworking/evidence/<milestone>/<run-id>/`.
- Inspect each relevant screenshot; a harness pass or decoded text is insufficient
  for bitmap rendering. Report exactly what was built and exercised.
- Never describe planning, simulated resume, or keyboard-buffer injection as
  completed software, ReadyOS integration, or proof of physical key chords.
- Keep neighboring projects unchanged unless work there is actually required
  and authorized. Existing unrelated changes are not ours to clean up.

`agentsworking/` is intentionally local and ignored by the repository's existing
rules. Do not force-add working records or external GEOS assets. Promote stable
public documentation deliberately when implementation warrants it.

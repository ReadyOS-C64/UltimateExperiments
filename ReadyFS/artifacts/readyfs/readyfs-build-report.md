# ReadyFS Build Report

Status: **PASS**

- Resident end: `$B539`; 114 safe bytes remain before KERNAL scratch at `$B5AC`.
- Monolithic end: `$C5E9` (limit `$C5FF`).
- Overlay-build cc65 software-stack top: `$D000`.
- IEC configuration policy payload: `$D18` bytes (seventeenth cached sidecar).
- Native filesystem payload: `$E63` bytes (nineteenth cached sidecar).
- Native IEC/media payload: `$FB7` bytes (eighteenth cached sidecar).
- Stream policy payload: `$EB5` bytes (sixteenth cached sidecar).
- Matcher payload: `$FC8` bytes.
- Planner/executor payload: `$FDF` bytes.
- Help/journal payload: `$FFA` bytes.
- Backend/controller payload: `$FFB` bytes.
- CMD/SD2IEC translator payload: `$FF6` bytes (cached runtime sidecar with boot self-test).
- IEC drive profiler payload: `$FEB` bytes (resident-owned command-channel I/O).
- Utility/history payload: `$DCF` bytes (seventh REU-cached runtime sidecar).
- Cooperative tree-controller payload: `$D1A` bytes (eighth REU-cached runtime sidecar).
- Bounded content-view payload: `$FF2` bytes (ninth REU-cached runtime sidecar).
- Batch/alias payload: `$BB5` bytes (tenth sidecar in a dedicated REU bank).
- Recursive controller/name translator payload: `$F67` bytes (eleventh sidecar; cached above the tree queue).
- Tape/core policy and signature payload: `$F7F` bytes (twelfth sidecar; dedicated batch-bank cache).
- Command/editor payload: `$FD4` bytes (thirteenth sidecar).
- Presentation payload: `$A8C` bytes (fourteenth sidecar).
- Command-help payload: `$FB6` bytes (fifteenth sidecar).
- REU regions disjoint: yes.

## Checks

- PASS: `resident_below_b600`
- PASS: `resident_below_kernal_scratch`
- PASS: `software_stack_top_d000`
- PASS: `monolithic_below_c600`
- PASS: `reu_regions_disjoint`
- PASS: `reu_overlay_regions_disjoint`
- PASS: `reu_batch_regions_disjoint`
- PASS: `reu_console_ring_fits_bank`
- PASS: `stream_policy_sidecar`
- PASS: `iec_config_policy_sidecar`
- PASS: `native_files_sidecar`
- PASS: `native_iec_media_sidecar`
- PASS: `presentation_sidecar`
- PASS: `command_help_sidecar`
- PASS: `ui_sidecar`
- PASS: `match_sidecar`
- PASS: `plan_sidecar`
- PASS: `help_sidecar`
- PASS: `backend_sidecar`
- PASS: `cmdpath_sidecar`
- PASS: `drive_sidecar`
- PASS: `utility_sidecar`
- PASS: `tree_sidecar`
- PASS: `content_sidecar`
- PASS: `batch_sidecar`
- PASS: `recursive_sidecar`
- PASS: `tape_sidecar`

## REU Session Map

| Region | Start | End (exclusive) | Bytes |
|---|---:|---:|---:|
| aliases | `$0000` | `$0888` | 2184 |
| drive_profiles | `$0888` | `$08E4` | 92 |
| operation_journal | `$0900` | `$2000` | 5888 |
| retired_scroll_pages_reserved | `$2000` | `$7DC0` | 24000 |
| retired_scroll_live_reserved | `$7DC0` | `$81A8` | 1000 |
| action_checkpoint | `$8200` | `$8300` | 256 |
| action_report | `$8300` | `$8308` | 8 |
| action_reserved | `$8308` | `$8400` | 248 |
| config_backup | `$8400` | `$8D88` | 2440 |
| recursive_checkpoint | `$8E00` | `$8F00` | 256 |
| tree_checkpoint | `$8F00` | `$9000` | 256 |
| config_stage | `$9000` | `$9988` | 2440 |
| recursive_roots | `$9988` | `$9B88` | 512 |
| action_plan | `$A000` | `$DFF0` | 16368 |

## REU Overlay Bank Map

| Region | Start | End (exclusive) | Bytes |
|---|---:|---:|---:|
| overlay_match | `$0000` | `$1000` | 4096 |
| overlay_plan | `$1000` | `$2000` | 4096 |
| overlay_help | `$2000` | `$3000` | 4096 |
| overlay_backend | `$3000` | `$4000` | 4096 |
| overlay_cmdpath_reserved | `$4000` | `$5000` | 4096 |
| overlay_drive_profile | `$5000` | `$6000` | 4096 |
| overlay_utility_tree | `$6000` | `$7000` | 4096 |
| overlay_tree_controller | `$7000` | `$8000` | 4096 |
| overlay_content_view | `$8000` | `$9000` | 4096 |
| tree_queue | `$9000` | `$EFF0` | 24560 |
| overlay_recursive | `$F000` | `$10000` | 4096 |

## REU Batch Bank Map

| Region | Start | End (exclusive) | Bytes |
|---|---:|---:|---:|
| batch_overlay_cache | `$0000` | `$1000` | 4096 |
| batch_script | `$1000` | `$5000` | 16384 |
| batch_checkpoint | `$5000` | `$5100` | 256 |
| tape_overlay_cache | `$5100` | `$6100` | 4096 |

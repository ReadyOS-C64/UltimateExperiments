# Established Ultimate automation references

User direction,2026-10-15: use the existing .NET automation tools for memory inspection and live video rather than assuming a new transport is required. Upstream source was inspected read-only; exact file hashes are in agentworking/research/upstream-ultimate-tools-20261015.json.

The established client is [UltimateClient.cs](/Users/karlprosserpp/dev/c64projects/agenticdevharness/tools/vice_tasks_dotnet/src/ViceTasks.Ultimate/UltimateClient.cs). Its ReadMemoryAsync/WriteMemoryAsync methods use machine:readmem/writemem; WriteKeyboardBufferAsync uses0277 withC6 count last; StartStreamAsync/StopStreamAsync control streams/video; CaptureVideoFrameAsync and UltimateVideoFrameReceiver decode384-wide low-nibble-first VIC pixels. The [existing recorder](/Users/karlprosserpp/dev/c64projects/gdos64-bridge/tools/ultimate/VideoCapture/Program.cs) uses the same actual VIC UDP format and saves live frames.

The DOS project already uses those established REST routes and streamed-pixel format. Keep memory/source/display checks separate from recorded footage: actual VIC streaming supplies video, while memory reads check guest/native state. Readmem does not establish the live6510 processor-port latches at0000/0001; use source-bound native fields for that evidence.

The .NET plan runner explicitly marks physical Ultimate dump.reu unsupported by its REST API (Program.cs line692). Its VICE REU dump facilities are separate. Existing original40fe REU snapshot/recovery remains needed for exhaustive physical4MiB authority; do not substitute a C64 RAM read for a REU dump.

Upstream AGENTS requires a separate macOS Terminal for physical10.0.0.79 access. The project already follows that ownership pattern. Keep all project outputs/staging in8088DOS64ultimate and freshly owned/usb1/DOS64_TEST folders; do not modify upstream tools or their dirty worktrees. Current recording uses this live stream and the reviewed decoder; no separate capture backend is needed.

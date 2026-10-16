# Ultimate hardware jobs must run in detached background processes

Effective 2026-10-16, direct user instruction: all Ultimate FTP/API/test communications must run in truly background shells so they cannot block the conversation.

For every future device job, create an independently owned Terminal dispatch, then start a detached worker with nohup or an equivalent launcher, stdin redirected from /dev/null, stdout/stderr redirected to owned log files, and a durable supervisor/worker PID record. The tool dispatch returns immediately. The Python controller records its actual PID and Terminal ownership in ACTIVE_HARDWARE_SESSION.json; distinguish that PID from an optional shell supervisor. Capture exit status in a durable file. Check independence with local process/FD inspection when needed. Poll saved logs and local process status only; no device communications from foreground tools or concurrent controllers.

Keep one device owner and a reviewed source/configuration manifest. Background execution does not bypass preflight, snapshot, recovery, file verification, deadlines, first-failure retention or source freezing. Preserve predecessor ownership and original REU backup authority. Keep the device reserved while recovery remains incomplete; do not hand it to another job or a human during recovery.

Do not interrupt/restart an already running recovery merely to convert it to a detached launcher. The current approved PID 53528 job in Terminal 1598 was launched before this requirement: it is independent of tool calls and has file-backed stdout/stderr, but stdin is inherited from Terminal and it remains a foreground Terminal process. Let its bounded attempt finish unchanged. All successors must use the detached arrangement above.

Later direct user authorization permits occasional REST full resets when the Ultimate enters a bad state. Check the exact endpoint/source behavior and coordinate with the sole owner before using one; retain evidence and explicitly qualify effects on REU/settings. A reset never proves that original REU bytes were restored. Do not interrupt the currently promising recovery for a reset.

Historical53528 attempt has now completed successfully and exited0; original4MiB ac43 wasindependently verified,settings/media/reset restored,device released. Every successor must usefullydetachedlaunch. ROOTevidence native-bulk-active-wholefile-recovery-root-20261016.json.

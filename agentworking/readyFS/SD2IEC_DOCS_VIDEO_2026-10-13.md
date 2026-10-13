# SD2IEC documentation, website and video update

## Requested outcome

Keep the repo guides, public ReadyFS demo site and video current with SD2IEC examples. Explain multi-file and nested-folder transfers, work inside SD-hosted images, and how those differ from UltimateDOS contained-image paths.

## Plan and evidence boundaries

- Preserve the existing editor/history/paging tour; add the SD2IEC walkthrough as the primary new video and a full chapter/script page.
- Record a native C64 walkthrough against the accepted runtime. No C64 runtime changes are required.
- Use five nested files for Ultimate host → SD → host, selected pairs for IEC9 and SoftwareIEC, an owned SD D64 and a separate unmounted Ultimate D64 for contained-file transfers, and a host intermediate to return a PRG to SD FAT.
- Keep all native mutations inside the previously marked test root, with a fresh child and unused image names. Check the exact marker before mutations. Preserve all test roots.
- Original A8, B settings, CPU/Turbo and SoftwareIEC state are restored. Runtime remains native; external automation installs and records it.
- The video edit omits setup/ownership checks but retains their logs. Input is presented at 1.4×; operations retain recorded speed. Chapter cards stay above the entire C64 picture and fade after 4.8 seconds.

## Recording status

Take `demo-v3-sd2iec-walkthrough-20261013-a` finished FAIL/restored=true; PID7206 exited. The COPY preview correctly displayed `WHATIF: NO FILES CHANGED`, while the new harness incorrectly expected a different summary. No actual recursive copy had begun. Corrected the assertion from observed output and added an absence check before real copying. Snapshot iteration was also made stable against the capture thread.

Fresh take `demo-v3-sd2iec-walkthrough-20261013-b` completed PASS/restored=true at 16:55:16 UTC; Terminal14654/PID8006 exited. Source was `0d24ad1`; runtime artifacts were unchanged from the completed acceptance build. All 32 recorded commands and 67 total recording checks passed. Source capture: 66,182 complete frames, zero missing frames, 1,320.351 seconds at 1 MHz. Independent checks cover five SD destinations, five returned files, two SoftwareIEC files, two persisted IEC-image entries, and the contained-image bytes/types. Original hardware and SoftwareIEC settings were restored.

## Documentation and site

Added a dedicated SD2IEC tutorial, a chapter in the general Markdown/printable guide, six illustrations (five actual C64 captures and one SVG diagram), configuration links, route table, and examples distinguishing ordinary recursive selection from explicit file sets on flat media. The tutorial states that automatic native `disk.d64/FILE` and `!/` transitions remain unimplemented and documents intermediate storage for same-device view changes.

Existing Site: `appgprj_6ac84b23269481919d1ea34651df6e6f`, public, https://readyfs-editor-demo.klumsy.chatgpt.site. Opened its source repository with the Sites helper at source commit `995d677ca9f9b9e552f7170b8bea42cf38896e54`. Published successfully as version 14 at 17:00:51 UTC. Existing RUN-guide edits are preserved; only this task's additions were staged in the parent repo.

## Video editing

The first assembly attempt encoded all 32 segments but failed when the concat manifest interpreted relative paths from its own directory. Resolved editor input/output paths to absolute paths and reran the edit. This was a host video assembly issue; the physical take and its passing evidence remain unchanged.

## Final local verification

- Edited video: 699.258258 seconds (11:39), 960×720, 35,050 frames, 5,096,386 bytes. SHA-256 `f6875931435e94e8fa5b09c2337c0cac5d8c0c2254439e660d235b92515ca1d8`. Seven chapters and 32 synchronized command/screenshot steps.
- Site validator passed both the retained editor tour and the new SD tour, local asset checks, the 12-chapter/26-illustration standalone guide, video hashes, timestamps and independent evidence gates. JavaScript syntax checks passed.
- Browser verified the guide anchor and loaded illustrations, media-view diagram, both primary and full-tour chapter seeking, 32 rendered script steps, and the actual MP4 download. The downloaded file SHA-256 matches the published candidate.
- Expanded the SD walkthrough player to full width below 1000px after inspecting the in-app browser layout; no broken images or media errors.
- Host source capture, edit plan, raw failed take, passing take and all marked filesystem fixtures remain retained. No runtime rebuild or hardware rerun is needed for these documentation/presentation edits.

## Public delivery

- Site: https://readyfs-editor-demo.klumsy.chatgpt.site
- Full SD walkthrough: https://readyfs-editor-demo.klumsy.chatgpt.site/sd2iec.html
- Guide chapter: https://readyfs-editor-demo.klumsy.chatgpt.site/guide.html#12-sd2iec-folders-batches-and-disk-images
- Site source commit: `c8a4049aaed4aad2fd785400f301e5091760a058`; version 14; deployment `appgdep_6ace63b7b8c48191981e4f77ceba151a`, succeeded.
- Repo documentation commit: `134503f`. Publication metadata and screenshot accompany this report. Existing public access was preserved.

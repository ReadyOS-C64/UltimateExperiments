# ReadyFS illustrated user guide — 9 October 2026

## Deliverables

- Markdown source: `ReadyFS/docs/READYFS_USER_GUIDE.md`.
- Portable HTML: `ReadyFS/docs/READYFS_USER_GUIDE.html`.
- Site edition: `agentworking/readyfs-demo-site/dist/guide.html`, byte-identical to the repo HTML.
- Public guide: https://readyfs-editor-demo.klumsy.chatgpt.site/guide.html
- Existing video homepage: https://readyfs-editor-demo.klumsy.chatgpt.site/
- Regenerator: `node ReadyFS/build_support/build_readyfs_user_guide.mjs`.
- Original illustrations, CSS, and video-frame provenance: `ReadyFS/docs/guide-assets/`.

## Coverage and approach

Eleven chapters, approximately 6,850 words, all 41 registered commands and their aliases,
15 option families, two SVG diagrams, and sixteen unaltered screenshots from the
previously verified physical C64 Ultimate recording. Concepts precede syntax,
selection, editor/history, inspection, and the complete nested copy/move/delete
workflow. The command reference follows the dispatcher and states device limitations.
Recipe examples are distinguished from recorded hardware evidence.

The guide documents important current nuances: endpoint-root paths versus aliases;
CD resolves but does not test existence; image-contained paths are parsed but direct
I/O is not implemented; recursive destinations are prepared containers; the selected
root survives recursive DELETE/MOVE cleanup; ordinary recursive mutations do not
require --apply; NEW reads --type; SWAP takes a drive, not an image. It explains
bounded text views, script limits, non-atomic failure handling, and host metadata.

The standalone HTML embeds all 18 illustrations and the linked source-note downloads.
It needs no network for reading or rendering. The one print button calls the native
browser print dialog. The website provides navigation, a guide feature area, and an
offline HTML download while retaining the original video, chapters, and evidence.

## Checks

- Generator verified unique/resolvable anchors, 11 chapters, and 18 embedded images.
- Local response: HTTP 200, text/html.
- Browser review at the default panel width, 1280 px wide layout, and 390 px narrow
  layout; all 18 illustrations loaded, no overflowing tables/preformatted blocks/figures.
- Temporary WeasyPrint Letter and A4 renderings: 34 pages each, no text crossing the
  checked page margins. Letter page contacts reviewed for tables, captions, screenshots,
  and section transitions. Print page numbers and guide labels included.
- Site validation passed: identical repo/Site guide, offline images/print rules/anchors,
  plus preserved seven video chapters, 37 hardware checks, and original MP4 SHA-256.
- The in-app browser did not expose a native print dialog to automation; pagination
  checks used the independent document renderer. Browser/printer pagination can vary.
- Documentation/site changes only; no C64 program changes or new physical mutations.
- Temporary print QA files removed after review.

## Publication

- Audience preserved: public.
- Site project: `appgprj_6ac84b23269481919d1ea34651df6e6f`.
- Pushed source commit: `21a7146377082f65260c0dc740a74e3e283a1733`.
- Saved version: `appgprj_6ac84b23269481919d1ea34651df6e6f~appgver_0b98dbcab92c81918ae2b2898aa09e46` (version 3).
- Deployment: `appgdep_6ac9dd59f9bc81918e3cbbed74ecc1a0`.
- Native result: `succeeded`.
- URL: https://readyfs-editor-demo.klumsy.chatgpt.site

Regenerate HTML after editing Markdown or CSS, copy it to the Site's dist/guide.html,
then publish through the Sites source helper and native tools. Keep the source-video
provenance and existing test roots unchanged.


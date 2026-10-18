# Publication and reproducibility audit

The public surface is the source, tests, build tools, portable documentation, selected screenshots, matched native preview ZIP and our example data disk. The audit is a file/dependency/privacy/build check, not a claim that every emulated instruction or hardware flow is defect-free. [Current limits](STATUS.md).

## Excluded material

Working-record directories, run logs, scratch/research copies, generated builds, user-supplied DOS disk images and original application distributions are ignored and untracked. Local copies are preserved. No DOS, GW-BASIC, Turbo Pascal or unrelated application is bundled in the ZIP or example image. Open-source Peddle code and its license remain included as a build/test dependency.

The preview ZIP allowlist is twelve matched native assets plus README.txt, BUILD.json, SHA256SUMS and DOS64.INI.example. The 360 KiB example disk allowlist is README.TXT, RIPPLE.PAS, RIPPLE.EXE and HANGMAN.BAS. Its FAT12 metadata and boot-error message are created from scratch, not copied from a DOS image. Independent parsing checks every file and allocation.

Public screenshot manifests retain frame hashes and qualification without private absolute paths or device addresses. The overview is composed from four authentic frames with labels outside the unchanged screen pixels. ReadyFS's four recording launchers now use READYFS_PYTHON or Python on PATH instead of a personal interpreter path. Their existing options are preserved; no hardware operation is performed by publication checks.

## Reproducibility checks

The twelve-asset native package was built in a clean source export without working notes or DOS images. Full default tests require the separately supplied original DOS images described in BUILD.md. The audit found one test dependency on a private image inventory; it is replaced by a checked-in hash-only fixture. Another test now anchors to its own project instead of discovering an unrelated ancestor's build directory.

Clean-export `make test` passed **340 Python tooling tests (one optional skip) and 518 Zig/Peddle tests** after supplying only the documented DOS images and the public hash inventory. The final native package passed all 25 packaging controls.

Run `make test` with the documented tools/images, `make v1-package-tests DOS64_V1_CANDIDATE_ARGS='--runtime-media'`, `npm run build:docs`, `npm run check:docs`, and `python3 tools/audit_public.py`. Example-image tests check the exact file allowlist, payload equality, deterministic rebuild and rejection of damaged FAT mirrors.

## History and publication

`tools/audit_public.py` checks the current tracked tree and the contents of both package and disk-image downloads. It does not rewrite or certify earlier Git history. Earlier development commits contained working records, vendor images and personal paths. Removing them from the latest tree does not remove their old blobs. A separate parentless publication snapshot can be reviewed without exposing that accumulated development history; replacing an existing public history is a separate owner-controlled operation. No push or history replacement is performed by the build.

GitHub Pages uploads only DOCS. Its navigation lists DOS64 second, directly after ReadyFS, and offers both Markdown and HTML versions. The Pages workflow also checks the publication allowlists before deployment.

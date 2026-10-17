# V1 human acceptance checklist

Use a fresh test installation and disposable working images. Record the package hash, Ultimate firmware, PAL/Manual64 settings, REU size and display used. Automated model results do not check these boxes. Keep a screenshot or short note for each failure.

## Install and configure

- [ ] Copy the twelve matching release files and your three original DOS images to the Ultimate. Run SETUP without a development computer; browse to the source images and a new destination folder.
- [ ] Create the small C drive, start the generated START and confirm DOS3.30 plus independent A/B/C listings. Repeat installation with20MiB C; confirm its reported size. Originals remain untouched.
- [ ] Use CONFIG to generate another launcher in a folder whose path contains spaces. Launch once in40 columns and once in80. Confirm the displayed settings and disk paths match your choices.
- [ ] Move a whole test installation, use CONFIG's explicit relocation confirmation, and launch again. External/shared image paths must stay unchanged.

## Read, type and run Turbo Pascal

- [ ] Read `DIR | MORE` in40 and80 columns. Page, cancel and scroll; inspect long names, punctuation and the cursor on your actual screen.
- [ ] Test letters, digits, shifted punctuation, backslash/pipe, Backspace/Delete, arrows, Home/End, Esc and Ctrl-C. Holding a key currently does not repeat. See [key mappings](DISPLAY_INPUT.md#c64-physical-keys-for-the-xt-and-turbo-pascal).
- [ ] Open original Turbo Pascal7.01 in80 columns. Type and correct the [V1Check program](V1_ENDPOINT.md#turbo-pascal-acceptance-scenario); navigate the editor, save its PAS and compile an EXE to disk.
- [ ] Run inside the IDE, return to the source, then exit to DOS. Run the saved EXE from DOS and inspect V1TEST.TXT. Confirm the menu and output shortcuts work on the physical keyboard.
- [ ] Inspect the supported CGA4/5/6 test cards on the physical display, alongside their retained reference images. Record legibility and color compromises.

## Change disks and keep your work

Open native disk controls with **CTRL + Commodore + RUN/STOP**. A/B chooses a drive; S saves, N saves as, I inserts, E ejects, W changes session write protection, R resumes and F finishes. Always read the selected drive, image path and dirty/protected state.

- [ ] On disposable A and B working images, create a uniquely named text file from DOS. Save each while C remains mounted. Verify the named saved destinations, resume and read a C file again.
- [ ] Modify a floppy, start a disk change, and exercise Cancel, then Save. Repeat with a disposable change and Discard. Confirm the retained/inserted contents with DOS DIR and TYPE.
- [ ] Attempt to insert an invalid or missing test image. Confirm the error names the file/operation, the old mount remains usable, and C still works. Confirm writes to a protected test image fail visibly.
- [ ] Finish from the native menu and wait for the safe-to-restart message. Reset, relaunch START, read both saved floppy files and reopen the saved Pascal source. Run its EXE again and inspect the C output file.
- [ ] Try an owned output-name collision or invalid test INI. Confirm the message gives a useful next step and does not report a completed installation/save. Retain partial outputs after failures; do not overwrite an uncertain installation.

The machine test campaign separately verifies full image/FAT contents, page and16MiB boundaries, close/reopen/EOF, failed/short I/O and unknown ownership. Those assertions and this checklist together support the [ten V1 release gates](V1_ENDPOINT.md#release-gates). No final gate is closed just by creating this checklist.

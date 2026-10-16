# Optional standalone fixture only; no normal runtime source registration.
.PHONY: floppy-export test-floppy-export
floppy-export:
	$(DOS64_PYTHON) build_support/build_floppy_export.py --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"
test-floppy-export: floppy-export
	$(DOS64_ZIG) build floppy-export --summary all

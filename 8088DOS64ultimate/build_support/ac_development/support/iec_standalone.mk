# Explicit standalone development lane; no dependency from all/test/runtime.
# Explicit validated entry: a retained JSON stamp cannot hide deleted products.
.PHONY: iec-standalone test-iec-standalone vice-iec-standalone vice-iec-standalone-serial
iec-standalone:
	$(DOS64_PYTHON) build_support/build_iec_standalone.py --ensure --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"
test-iec-standalone: iec-standalone
	"$(DOS64_ZIG)" build iec-standalone --cache-dir build/iec-zig-cache --global-cache-dir build/iec-zig-global-cache --summary all
	$(DOS64_PYTHON) -m unittest discover -s tests/iec_standalone -p 'test_*.py'
vice-iec-standalone: iec-standalone
	$(DOS64_PYTHON) build_support/vice_iec_standalone.py --case original
vice-iec-standalone-serial: iec-standalone
	$(DOS64_PYTHON) build_support/vice_iec_standalone.py --serial --case original

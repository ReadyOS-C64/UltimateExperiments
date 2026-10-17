# Synthetic native A/B SaveAs development profile; no hardware or DOS images.
.PHONY: native-media test-native-media
native-media:
	$(DOS64_PYTHON) -B build_support/native_media_tests.py --native-only $(DOS64_NATIVE_MEDIA_ARGS)
test-native-media:
	DOS64_ZIG="$(DOS64_ZIG)" $(DOS64_PYTHON) -B build_support/native_media_tests.py $(DOS64_NATIVE_MEDIA_ARGS)

.PHONY: test-floppy-format
test-floppy-format:
	DOS64_ZIG="$(DOS64_ZIG)" $(DOS64_PYTHON) -B build_support/floppy_format_tests.py $(DOS64_FORMAT_TEST_ARGS)

.PHONY: test-floppy-format-host
test-floppy-format-host:
	$(DOS64_PYTHON) -B -m unittest discover -s tests/floppy_format_host -p 'test_*.py' -v

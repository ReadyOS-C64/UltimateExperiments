# Optional native C installer components; never linked into the 8088 emulator.
DOS64_CC65 ?= cc65
DOS64_CL65 ?= cl65

.PHONY: setup-config setup-config-tests
setup-config: build/setup-config.prg
build/setup-config-code.s: tools/setup/install_config.c tools/setup/install_config.h
	@mkdir -p build
	$(DOS64_CC65) -t none -O --add-source -I tools/setup -o $@ $<
build/setup-config-code.o: build/setup-config-code.s
	$(DOS64_CA65) -g -o $@ $<
build/setup-config-entry.o: tools/setup/codec_test_entry.s
	@mkdir -p build
	$(DOS64_CA65) -g -o $@ $<
build/setup-config.prg: build/setup-config-entry.o build/setup-config-code.o tools/setup/codec_test.cfg
	$(DOS64_CL65) -t none -C tools/setup/codec_test.cfg -o $@ -m build/setup-config.map -Ln build/setup-config.labels build/setup-config-entry.o build/setup-config-code.o
setup-config-tests: setup-config
	$(DOS64_ZIG) build --build-file build_setup_tests.zig test --summary all

.PHONY: setup-release setup-release-tests
setup-release: build/setup-release.prg
build/setup-release-code.s: tools/setup/release.c tools/setup/release.h
	@mkdir -p build
	$(DOS64_CC65) -t none -O --add-source -I tools/setup -o $@ $<
build/setup-release-code.o: build/setup-release-code.s
	$(DOS64_CA65) -g -o $@ $<
build/setup-release.prg: build/setup-config-entry.o build/setup-release-code.o tools/setup/codec_test.cfg
	$(DOS64_CL65) -t none -C tools/setup/codec_test.cfg -o $@ -m build/setup-release.map -Ln build/setup-release.labels build/setup-config-entry.o build/setup-release-code.o
setup-release-tests: setup-release
	$(DOS64_ZIG) build --build-file build_setup_release_tests.zig test --summary all
	$(DOS64_PYTHON) -B tests/tooling/test_setup_release_descriptor.py -v

# Folder-aware native launcher; default template remains disabled until SETUP.
.PHONY: start start-tests
start:
	$(DOS64_PYTHON) -B build_support/start_launcher.py
start-tests: build
	$(DOS64_PYTHON) -B build_support/start_launcher.py --test

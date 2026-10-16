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

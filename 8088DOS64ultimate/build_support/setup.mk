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

# D64S binds the disabled launcher template; DOS64.REL separately binds main.
.PHONY: start-template start-template-tests
start-template: start
	$(DOS64_PYTHON) -B build_support/start_template_descriptor.py --prg build/start/START.PRG --labels build/start/START.labels --map build/start/START.map --out build/start/START.REL
start-template-tests: start-template
	$(DOS64_PYTHON) -B tests/tooling/test_start_template_descriptor.py -v

# Standalone native SETUP build; main and START defaults are unchanged.
.PHONY: setup-installer setup-installer-memory
setup-installer:
	$(DOS64_PYTHON) -B build_support/setup_installer.py
setup-installer-memory: setup-installer
	@echo "Memory checks and source/product closure: build/setup-installer/RESULT.json"

# Opt-in actual native model integrations; uses local DOS media, no hardware.
.PHONY: setup-installer-tests
setup-installer-tests:
	$(DOS64_PYTHON) -B build_support/setup_installer_tests.py $(DOS64_SETUP_TEST_ARGS)

# Explicit matched-release native preflight; standalone setup-installer stays unchanged.
DOS64_SETUP_BUNDLE_RESULT ?= build/start-ini-bundle/RESULT.json
.PHONY: setup-installer-preflight setup-installer-preflight-tests
setup-installer-preflight:
	$(DOS64_PYTHON) -B build_support/setup_installer.py --bundle-result "$(DOS64_SETUP_BUNDLE_RESULT)" --out build/setup-installer-bound
setup-installer-preflight-tests:
	$(DOS64_PYTHON) -B build_support/setup_preflight_tests.py --bundle-result "$(DOS64_SETUP_BUNDLE_RESULT)" $(DOS64_SETUP_PREFLIGHT_ARGS)

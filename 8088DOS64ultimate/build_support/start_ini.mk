# Explicit complete matched release; default start/start-template remain ABI1.
.PHONY: start-ini-bundle start-options-tests ini-options-tests unit-sidecar-tests
start-ini-bundle:
	$(DOS64_PYTHON) -B build_support/start_ini_bundle.py $(DOS64_START_INI_ARGS)
start-options-tests:
	$(DOS64_PYTHON) -B build_support/start_ini_tests.py $(DOS64_START_INI_TEST_ARGS)
ini-options-tests: build
	$(DOS64_ZIG) build --build-file build-ini-options.zig test --summary all
unit-sidecar-tests: build
	$(DOS64_ZIG) build --build-file build-ini-sidecar.zig test --summary all

.PHONY: start-ini-bundle-tests ini-state-memory-tests
start-ini-bundle-tests: start-ini-bundle
	$(DOS64_PYTHON) -B tests/start_options_host/test_bundle.py
ini-state-memory-tests: build
	$(DOS64_PYTHON) -B tests/tooling/test_ini_state_memory.py
	$(DOS64_PYTHON) -B -m unittest discover -s tests/tooling -p test_hd_memory_contract.py -v

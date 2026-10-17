# Standalone CONFIG is opt-in and binds the matching INI release at build time.
.PHONY: config config-tests
config:
	$(DOS64_PYTHON) -B build_support/config_generation.py $(DOS64_CONFIG_ARGS)
config-tests:
	DOS64_ZIG="$(DOS64_ZIG)" $(DOS64_PYTHON) -B build_support/config_generation.py --test $(DOS64_CONFIG_ARGS)

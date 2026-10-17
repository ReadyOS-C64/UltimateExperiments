# Standalone CONFIG is opt-in and binds the matching INI release at build time.
.PHONY: config config-tests
config:
	$(DOS64_PYTHON) -B build_support/config_generation.py $(DOS64_CONFIG_ARGS)
config-tests:
	DOS64_ZIG="$(DOS64_ZIG)" $(DOS64_PYTHON) -B build_support/config_generation.py --test $(DOS64_CONFIG_ARGS)

# Explicit optional V1 CONFIG profile; the default config graph remains unchanged.
.PHONY: config-relocation config-relocation-tests
config-relocation:
	$(DOS64_PYTHON) -B build_support/config_generation.py --startup-diagnostics --all-file-diagnostics --relocation $(DOS64_CONFIG_ARGS)
config-relocation-tests:
	$(DOS64_PYTHON) -B tests/config/test_build_profiles.py
	DOS64_ZIG="$(DOS64_ZIG)" $(DOS64_PYTHON) -B build_support/config_generation.py --startup-diagnostics --all-file-diagnostics --relocation --test $(DOS64_CONFIG_ARGS)

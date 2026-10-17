# Coherent development packaging; never a claim that final V1 gates have passed.
.PHONY: v1-candidate v1-package-tests
v1-candidate:
	$(DOS64_PYTHON) -B build_support/v1_candidate.py $(DOS64_V1_CANDIDATE_ARGS)
v1-package-tests: v1-candidate
	$(DOS64_PYTHON) -B tests/tooling/test_v1_candidate.py

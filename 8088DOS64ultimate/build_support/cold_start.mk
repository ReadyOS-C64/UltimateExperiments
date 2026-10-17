.PHONY: cold-start
cold-start:
	@test -n "$(RUNTIME_MEDIA_RESULT)" || (echo 'Set RUNTIME_MEDIA_RESULT to an immutable runtime-media RESULT.json'; exit 1)
	$(DOS64_PYTHON) -B build_support/cold_start.py --runtime-result "$(RUNTIME_MEDIA_RESULT)" --out build/cold-start

.PHONY: cold-start-tests
cold-start-tests:
	@test -n "$(RUNTIME_MEDIA_RESULT)" || (echo 'Set RUNTIME_MEDIA_RESULT to an immutable runtime-media RESULT.json'; exit 1)
	DOS64_RUNTIME_RESULT="$(RUNTIME_MEDIA_RESULT)" $(DOS64_PYTHON) -B -m unittest discover -s tests/cold_start_host -p 'test_*.py'

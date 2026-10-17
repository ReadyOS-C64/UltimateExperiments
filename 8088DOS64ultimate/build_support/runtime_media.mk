# Optional actual-runtime menu/Save/Insert/Finish native assets. No DOS or model tools.
.PHONY: runtime-media
runtime-media:
	$(DOS64_PYTHON) -B build_support/runtime_media.py $(DOS64_RUNTIME_MEDIA_ARGS)

# Retained staging failures

The FORMAT Make patch dry-run failed only its final EOF hunk because the current public Makefile adds runtime_media.mk. First8hunks applied strictly; final three flag recipes and FORMAT dependency/verify targets were merged explicitly while retaining that include.

The first adaptation script stopped after Make/runtime-inventory changes because runtime-only staging intentionally omitted the older native_media_sources.json. The inventory and missing default-lane sources were copied explicitly from public, preserving already adapted files.

The first default proof command could not start native_media_tests.py because that optional test driver is not a production runtime input. Its exact public source is now copied into the private default-proof stage. No native test or target build ran in that first default attempt.

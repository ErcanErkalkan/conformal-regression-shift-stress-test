.PHONY: verify test synthetic-test real-test diagnostics
verify:
	python verify_release.py
synthetic-test:
	cd synthetic && PYTHONPATH=src python -m pytest -q tests/test_v10.py
real-test:
	cd real_data && PYTHONPATH=code python -m pytest -q tests
test: verify synthetic-test real-test
diagnostics:
	python analysis/reproduce_final_diagnostics.py

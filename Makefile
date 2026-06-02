.PHONY: doctor build-example test smoke clean

doctor:
	PYTHONPATH=src python -m zig_py.doctor

build-example:
	PYTHONPATH=src python -m zig_py.build --example add

test:
	PYTHONPATH=src python -m pytest

smoke:
	bash scripts/smoke.sh

clean:
	rm -rf build .pytest_cache src/zig_PY.egg-info src/zig_py.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

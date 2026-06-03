# zig-PY



"Keep Python.Gain Zig."


zig-PY is a small Python package that proves one honest path: Python can build,
load, and call a Zig function through a shared library.

This repository is intentionally v0-sized. It is not a binding generator, not a
package manager, and not a promise of features that do not run. Every command
below is part of the working path.

## What v0 does

- Checks the local environment for Python, Zig, pytest, and platform details.
- Compiles `examples/add/add.zig` into a platform shared library.
- Loads that shared library from Python with `ctypes`.
- Calls the exported Zig function `add(2, 3)` from Python.
- Runs tests that verify the build, load, and call behavior.
- Prints logs that say what is happening, which command ran, where output went,
  and how to fix known failures.

## What v0 does not do

- No binding generator.
- No package manager.
- No decorators.
- No Python-to-Zig type inference.
- No broad architecture for features that do not exist yet.
- No fake CLI commands beyond the working doctor and example build entry points.

## Requirements

- Python 3.9 or newer.
- Zig installed and available as `zig` on `PATH`.
- `pytest`, installed by the `dev` extra below.

## Install from a fresh checkout

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

### Check tools

```sh
make doctor
```

Expected successful output includes lines like:

```text
zig-PY INFO checking Python, Zig, pytest, and platform
zig-PY OK python: Python 3.x.x at ...
zig-PY OK zig: Zig ... at ...
zig-PY OK pytest: pytest is importable
zig-PY OK platform: ...
zig-PY OK doctor completed successfully
```

### Build the Zig add example

```sh
make build-example
```

By default, v0 builds the example with Zig `ReleaseFast` optimization. This is
the default because local example timings on Linux with Zig 0.16.0 showed that
`ReleaseFast` kept the tiny v0 example build path interactive while other modes
were much slower in that environment: `ReleaseSafe` around 49s, `Debug` around
11s, `ReleaseSmall` around 6.5s, and `ReleaseFast` around 0.2s. These are
example timings from one local machine, not a general speed claim.

To request another Zig optimization mode directly, run:

```sh
PYTHONPATH=src python -m zig_py.build --example add --optimize ReleaseSafe
```

Supported modes are `Debug`, `ReleaseSafe`, `ReleaseFast`, and `ReleaseSmall`.
Use `ReleaseSafe` when you want Zig's safety checks instead of the fastest v0
default. Changing the optimization mode is part of the freshness check, so
zig-PY rebuilds the shared library instead of reusing an older library compiled
with a different mode.

Expected successful output includes:

```text
zig-PY INFO building Zig add example from .../examples/add/add.zig
zig-PY INFO using Zig optimization mode: ReleaseFast
zig-PY INFO running command from ...: zig build-lib ... -O ReleaseFast ...
zig-PY INFO command output will be written to .../build/logs/add-build.log
zig-PY OK built shared library at .../build/zig_py/add/libadd.so
zig-PY OK build log written to .../build/logs/add-build.log
```

A second build with the same source and optimization mode skips when the output
is current. The exact library extension depends on the platform: `.so` on Linux,
`.dylib` on macOS, and `.dll` on Windows.

### Run the example

```sh
python examples/add/run.py
```

Expected successful output includes:

```text
zig-PY INFO running add example: Python will call Zig add(2, 3)
zig-PY INFO loading Zig shared library from ...
zig-PY OK loaded add(a: i32, b: i32) from ...
zig-PY INFO Zig add(2, 3) returned 5
zig-PY OK Python successfully called Zig: add(2, 3) == 5
```

### Run tests

```sh
make test
```

Expected successful output includes:

```text
python -m pytest
...
11 passed
```

### Run the full smoke path

```sh
make smoke
```

This cleans generated output, runs the doctor, builds the Zig shared library,
runs the Python example, and runs the test suite.

Expected successful output ends with:

```text
zig-PY smoke: success - Python called Zig and tests passed
```

## Exit codes

zig-PY uses distinct exit codes for the working v0 path:

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 10 | Missing Zig |
| 11 | Missing Python dependency |
| 20 | Zig build failure |
| 30 | Shared library load failure |
| 40 | Test or example failure |

## Troubleshooting

### `make doctor` reports missing Zig

Install Zig from <https://ziglang.org/download/> and make sure `zig version`
works in the same shell where you run zig-PY commands.

### `make doctor` reports missing pytest

Install the development dependencies from the repository root:

```sh
pip install -e ".[dev]"
```

### `make build-example` fails

Open the build log printed by the command, usually:

```text
build/logs/add-build.log
```

Fix the Zig compiler error shown there, then rerun:

```sh
make build-example
```

### `python examples/add/run.py` cannot load the shared library

Build the example first:

```sh
make build-example
python examples/add/run.py
```

If it still fails, confirm the shared library under `build/zig_py/add/` matches
your operating system and CPU architecture.

## The v0 Python-to-Zig path

The actual Zig function is intentionally tiny:

```zig
export fn add(a: i32, b: i32) i32 {
    return a + b;
}
```

Python loads the compiled shared library with `ctypes`, declares the argument
and return types as 32-bit integers, and calls `add(2, 3)`.

## Next real v1 step

The next real step is a minimal explicit manifest for user-owned Zig functions:
a small config file that names a Zig source file, exported function names, and
ctypes-compatible signatures. That would keep v1 inspectable while allowing more
than one hard-coded example.

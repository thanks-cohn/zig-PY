from __future__ import annotations

from zig_py import load_add_library
from zig_py import logging as log

EXAMPLE_FAILURE = 40


def main() -> int:
    log.info("running add example: Python will call Zig add(2, 3)")
    library = load_add_library()
    result = library.add(2, 3)
    log.info(f"Zig add(2, 3) returned {result}")
    if result != 5:
        log.error(f"expected add(2, 3) == 5, got {result}")
        log.fix("Rebuild the example with make build-example and rerun python examples/add/run.py.")
        return EXAMPLE_FAILURE
    log.ok("Python successfully called Zig: add(2, 3) == 5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

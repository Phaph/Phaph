"""Every name and stat the engine relies on exists in the installed PoB (engine/tools/preflight.py).
Fails after a PoB update (e.g. 1.0) that renames an ailment support, skill tag, weapon type or output stat."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine" / "tools"))

import preflight  # noqa: E402


def test_game_data_preflight(pob):
    errors, _warns = preflight.check(preflight.load_game(pob))
    assert errors == []

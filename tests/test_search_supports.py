"""Support search vs conditions (guide.search_supports): a set that blocks ailments is checked against one that doesn't."""
import guide
from optimize import Result


class _Pob:
    """Damage with chilled enemies on: only a set without an ailment blocker keeps that up."""
    def __init__(self, free_dps):
        self.gems, self.free_dps, self.configs = [], free_dps, 0

    def try_skill(self, group, gems, fields, **kw):
        self.gems = gems[1:]
        return {"supported": {}, "output": {}}

    def auto_config(self, mode):
        self.configs += 1
        return []

    def calc(self, fields=None):
        return {"TotalDPS": 100 if "Elemental Focus" in self.gems else self.free_dps}


def _search(pob, group, skill, exclude=None, **kw):
    sets = ["Other"] if exclude else ["Elemental Focus"]
    pob.gems = sets
    return [Result(sets, 100)]


def test_the_set_without_the_blocker_wins_when_its_own_conditions_pay(monkeypatch):
    monkeypatch.setattr(guide, "optimise_supports", _search)
    pob = _Pob(142)
    assert guide.search_supports(pob, 1, "Bonestorm", "bossing", 5, "total")[0].supports == ["Other"]
    assert pob.gems == ["Other"]


def test_the_blocker_stays_when_it_is_still_better(monkeypatch):
    monkeypatch.setattr(guide, "optimise_supports", _search)
    pob = _Pob(90)
    assert guide.search_supports(pob, 1, "Bonestorm", "bossing", 5, "total")[0].supports == ["Elemental Focus"]
    assert pob.gems == ["Elemental Focus"]   # the build is left on the set that was kept


def test_no_second_search_without_a_blocker(monkeypatch):
    monkeypatch.setattr(guide, "optimise_supports", lambda *a, **k: [Result(["Deliberation"], 100)])
    pob = _Pob(142)
    assert guide.search_supports(pob, 1, "Bonestorm", "mapping", 5, "mapping")[0].supports == ["Deliberation"]
    assert pob.configs == 0

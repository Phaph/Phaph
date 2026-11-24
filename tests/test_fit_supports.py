"""Filler supports (guide.fit_supports) never cost the build its toughness."""
from guide import fit_supports


class _Pob:
    EHP = {"Atziri's Communion": 3000}

    def list_gems(self, kind):
        return []

    def calc(self, fields=None):
        return {"TotalEHP": 12000}

    def send(self, cmd, **kw):
        if cmd == "gem_texts":
            return {"gems": {}}
        assert cmd == "fitting_supports"
        return {"supports": [{"name": n, "family": n, "specific": 0.9} for n in ("Atziri's Communion", "Healing Runes")]}

    def try_skill(self, group, gems, fields, keep_main=False):
        ehp = min(self.EHP.get(g, 12000) for g in gems)
        return {"supported": {g: True for g in gems}, "output": {"TotalEHP": ehp, "SpiritUnreserved": 5}}


def test_filler_that_reserves_life_is_skipped(monkeypatch):
    import guide
    monkeypatch.setattr(guide, "_ALONE", None)
    assert fit_supports(_Pob(), 1, "Herald of Ash", [], 5, keep_main=True) == ["Healing Runes"]


def test_kit_search_keeps_toughness(pob, monk):
    """The damage search for a spirit skill never takes a set that costs most of the toughness (keep_ehp)."""
    from optimize import optimise_supports
    pob.add_skill(["Glacial Cascade"])
    g = pob.add_skill(["Herald of Ash"], main=False)["group"]
    e0 = pob.calc(["TotalEHP"])["TotalEHP"]
    pool = ["Atziri's Communion", "Elemental Focus", "Heft"]
    for kw in ({"metric": "total"},):
        best = optimise_supports(pob, g, "Herald of Ash", slots=2, candidates=pool, keep_main=True, keep_ehp=0.9,
                                 min_gain=-1.0, log=lambda *a: None, **kw)[0]
        assert "Atziri's Communion" not in best.supports
        assert pob.calc(["TotalEHP"])["TotalEHP"] >= 0.9 * e0
    loose = optimise_supports(pob, g, "Herald of Ash", slots=2, candidates=pool, keep_main=True, min_gain=-1.0,
                              log=lambda *a: None)[0]
    assert "Atziri's Communion" in loose.supports   # without the rule it is taken, so the test bites

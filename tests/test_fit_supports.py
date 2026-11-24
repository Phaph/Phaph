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

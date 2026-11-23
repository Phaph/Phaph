"""Python client for the headless Path of Building runner (runner.lua)."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import zlib
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
VENDOR = Path(os.environ.get("POB_VENDOR", ENGINE / "vendor"))
POB_SRC = VENDOR / "PathOfBuilding-PoE2" / "src"
LUAJIT = VENDOR / "LuaJIT" / "src" / "luajit"


class PoBError(RuntimeError):
    pass


def decode_build_code(code: str) -> str:
    """PoB share code -> build XML."""
    raw = base64.b64decode(code.strip().replace("-", "+").replace("_", "/") + "==")
    return zlib.decompress(raw).decode("utf-8")


def encode_build_code(xml: str) -> str:
    """Build XML -> PoB share code."""
    return base64.b64encode(zlib.compress(xml.encode("utf-8"), 9)).decode().replace("+", "-").replace("/", "_")


def apply_patch_file(pob: "PoB") -> list[str]:
    """Patch-notes mode (task 31): with PATCH_FILE set (data/patches/<patch>.json), every PoB process starts with the
    file's number changes applied (runner patch_gem), so every scan and build runs on the patched game before PoB
    itself has it. The file: {"patch": "...", "changes": [{"gem": "Earthquake", "base_multiplier": 1.2,
    "note": "<the patch note line>"}, {"gem": ..., "constant": {stat: value}, "scale": {stat: factor}, "set": 1},
    {"unique": "Leopold's Applause", "replace": [["old line", "new line"]], "add": ["new line"]}]}."""
    path = os.environ.get("PATCH_FILE")
    if not path:
        return []
    import json
    done = []
    for c in json.loads(Path(path).read_text(encoding="utf-8")).get("changes") or []:
        if c.get("gem") or c.get("id"):
            args = {k: c[k] for k in ("constant", "scale", "base_multiplier", "set", "level", "require_types", "id",
                                      "rename", "add", "remove")
                    if c.get(k) is not None}
            r = pob.send("patch_gem", skill=c.get("gem"), **args)
            done += [f"{c.get('gem') or c['id']}: {x}" for x in r.get("changed") or []]
        elif c.get("base"):
            args = {k: c[k] for k in ("armour", "weapon", "req", "flask", "charm") if c.get(k)}
            r = pob.send("patch_base", name=c["base"], **args)
            done += [f"{c['base']}: {x}" for x in r.get("changed") or []]
        elif c.get("passive"):
            r = pob.send("patch_node", name=c["passive"], replace=c.get("replace") or [], add=c.get("add") or [])
            done += [f"{c['passive']}: {x}" for x in r.get("changed") or []]
        elif c.get("unique"):
            r = pob.send("patch_unique", name=c["unique"], replace=c.get("replace") or [], add=c.get("add") or [])
            done += [f"{c['unique']}: {x}" for x in r.get("changed") or []]
    return done


class PoB:
    """One long-running PoB process. Commands are sent one at a time."""

    def __init__(self) -> None:
        if not LUAJIT.exists():
            raise PoBError(f"LuaJIT not found at {LUAJIT}. Run engine/setup.sh first.")
        env = dict(os.environ)
        env["LUA_PATH"] = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;;"
        env["LUA_CPATH"] = f"{VENDOR}/?.so;;"
        self.proc = subprocess.Popen(
            [str(LUAJIT), str(ENGINE / "runner.lua")],
            cwd=POB_SRC,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
            bufsize=1,
        )
        ready = self._read()
        self.version = ready["version"]
        self.patch = ready.get("patch") or "unknown"   # game patch PoB's data is for, e.g. "0_5"
        self.patched = apply_patch_file(self)   # patch-notes mode: PATCH_FILE's number changes, if set

    on_event = None   # called with live events (e.g. tree steps) that arrive before a command's reply
    # Skills placed by a totem gem in this build: {"Fireball": "Spell Totem"}. Every group whose first gem is one of
    # these skills gets the totem gem put in front, so supports, gear and the exported code all keep the totem.
    totem_for: dict | None = None   # set per build: pob.totem_for = {...}

    # What the build is made around (see anchors.py), set per build: {"unique": {name, raw, type, slot...},
    # "keystone": "Chaos Inoculation", "support": "Brutality", "main": main skill name}. craft_gear always equips the
    # unique, optimise_supports always keeps the support on the main skill, optimise_tree always holds the keystone.
    anchors: dict | None = None
    off_meta: bool = False   # off-meta toggle: popular uniques score lower (meta.py)
    no_lineage: bool = False   # campaign stages: no lineage supports (optimize.optimise_supports)
    anchor_notes: list | None = None   # what an anchor couldn't do at this stage, for the guide's notes

    def _with_totem(self, gems: list[str]) -> list[str]:
        meta = (self.totem_for or {}).get(gems[0]) if gems else None
        return [meta, *gems] if meta else list(gems)

    def _read(self) -> dict:
        assert self.proc.stdout
        for line in self.proc.stdout:
            if line.startswith("@@"):
                msg = json.loads(line[2:])
                if isinstance(msg, dict) and "event" in msg:
                    if self.on_event:
                        try:
                            self.on_event(msg)
                        except Exception:  # noqa: BLE001 - a display hook must never break the engine
                            pass
                    continue
                return msg
        raise PoBError("PoB process exited")

    def send(self, cmd: str, **kwargs) -> dict:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps({"cmd": cmd, **kwargs}) + "\n")
        self.proc.stdin.flush()
        res = self._read()
        if not res.pop("ok", False):
            raise PoBError(f"{cmd}: {res.get('error')}")
        return res

    # Convenience wrappers
    def new(self):
        return self.send("new")

    def load_xml(self, xml: str):
        return self.send("load_xml", xml=xml)

    def load_code(self, code: str):
        return self.load_xml(decode_build_code(code))

    def save_xml(self) -> str:
        return self.send("save_xml")["xml"]

    def save_code(self) -> str:
        return encode_build_code(self.save_xml())

    def set_class(self, cls: str, ascendancy: str | None = None):
        return self.send("set_class", **{"class": cls, "ascendancy": ascendancy})

    def set_level(self, level: int):
        return self.send("set_level", level=level)

    def add_item(self, raw: str):
        return self.send("add_item", raw=raw)

    def add_skill(self, gems: list[str], level: int = 20, quality: int = 0, main: bool = True,
                  full_dps: bool = False):
        text = "\n".join(f"{g} {level}/{quality}  1" for g in self._with_totem(gems))
        return self.send("add_skill", text=text, main=main, full_dps=full_dps)

    def use_full_dps(self) -> None:
        """Count the main skill and everything that works alongside it (minions, totems, heralds) in PoB's Full DPS.
        Skills pressed instead of the main one (boss skill, clear skill, basic attack) never add to it."""
        self.send("full_dps_all")
        self.send("sync_minion_counts")

    def try_skill(self, group: int, gems: list[str], fields: list[str], level: int = 20, quality: int = 0,
                  keep_main: bool = False) -> dict:
        """Replace a group's gems and recalculate. keep_main: score the current main skill, not this group."""
        text = "\n".join(f"{g} {level}/{quality}  1" for g in self._with_totem(gems))
        res = self.send("try_skill", group=group, text=text, fields=fields, keep_main=keep_main)
        # dkjson encodes empty tables as [], normalise to dicts
        for key in ("supported", "output"):
            if not isinstance(res.get(key), dict):
                res[key] = {}
        if not isinstance(res.get("warnings"), list):
            res["warnings"] = []
        return res

    def clear_skills(self):
        return self.send("clear_skills")

    def remove_skill(self, group: int):
        return self.send("remove_skill", group=group)

    def set_config(self, **values):
        return self.send("set_config", values=values)

    def alloc_nodes(self, nodes: list):
        return self.send("alloc_nodes", nodes=nodes)

    def auto_config(self, mode: str = "bossing") -> list[dict]:
        """Turn on the conditional bonuses this build sustains. Returns what was applied and why."""
        res = self.send("auto_config", mode=mode).get("applied")
        return res if isinstance(res, list) else []

    def points(self) -> dict:
        return self.send("points")

    def optimise_tree(self, max_dist: int = 6, def_weight: float = 0.25, points: int | None = None,
                      metric: str = "total", goals=None, on_step=None, far_dist: int = 12,
                      refine: bool = True, refine_seconds: float | None = None, jewel: str | None = None,
                      ascendancy_points: int | None = None) -> dict:
        """Spend passive and ascendancy points (see runner.lua optimise_tree).

        far_dist: how far away a notable or keystone may be (small passives: max_dist).
        refine: run the swap phase afterwards, which takes back weak branches and re-spends them.
        jewel: a raw jewel (see jewels.proxy_jewel); sockets taken get a copy of it straight away.
        on_step, if given, is called with each step while the search runs (see runner.lua `live`).
        """
        from goals import weights
        w = weights(goals)
        kwargs = {"max_dist": max_dist, "far_dist": far_dist, "def_weight": def_weight * w["def_mult"],
                  "metric": metric, "movement_weight": w["movement"], "rarity_weight": w["rarity"],
                  "refine_rounds": 12 if refine else 0}
        if refine_seconds is not None:
            kwargs["refine_seconds"] = refine_seconds
        if jewel:
            kwargs["jewel"] = jewel   # a raw jewel: sockets become targets worth their path plus this jewel
        if points is not None:
            kwargs["points"] = points
        if ascendancy_points is not None:
            kwargs["ascendancy_points"] = ascendancy_points   # 0 in Act 1: no trial done yet
        keystone = (self.anchors or {}).get("keystone")
        if keystone and self.hold_keystone(keystone):
            kwargs["locked"] = [keystone]
        if on_step:
            kwargs["live"] = True
            self.on_event = on_step
        try:
            res = self.send("optimise_tree", **kwargs)
        finally:
            self.on_event = None
        if not isinstance(res.get("steps"), list):
            res["steps"] = []
        return res

    def hold_keystone(self, name: str) -> bool:
        """Allocate an anchor keystone and the path to it. False (and nothing allocated) when the path costs more
        points than this level has, e.g. a far keystone in the act stages."""
        before = set(self.send("allocated").get("nodes") or [])
        res = self.alloc_nodes([name])
        if res.get("missing"):
            return False
        after = set(self.send("allocated").get("nodes") or [])
        pts = self.points()
        if pts.get("used", 0) > pts.get("available", 0):
            self.send("dealloc_ids", ids=sorted(after - before))
            if self.anchor_notes is not None and f"keystone:{name}" not in self.anchor_notes:
                self.anchor_notes.append(f"keystone:{name}")
            return False
        return True

    def list_keystones(self) -> list[dict]:
        return self.send("list_keystones")["keystones"]

    def reset_tree(self):
        return self.send("reset_tree")

    def calc(self, fields: list[str] | None = None) -> dict:
        kwargs = {"fields": fields} if fields else {}
        out = self.send("calc", **kwargs)["output"]
        return out if isinstance(out, dict) else {}  # dkjson sends an empty table as []

    def dps_sources(self) -> list[dict]:
        """What Full DPS is made of, biggest first: [{"name", "dps", "share"}]. Empty without Full DPS."""
        r = self.send("dps_sources")
        total = r.get("total") or 0
        return [{"name": x["name"], "dps": round(x["dps"]), "share": round(x["dps"] / total, 3),
                 **({"count": x["count"]} if x.get("count", 1) != 1 else {})}
                for x in (r.get("sources") or []) if total > 0]

    def warnings(self) -> list[str]:
        w = self.send("calc", fields=["TotalDPS"]).get("warnings")
        return w if isinstance(w, list) else []

    def list_gems(self, filter: str | None = None, tags: list[str] | None = None) -> list[dict]:
        return self.send("list_gems", filter=filter, tags=tags or [])["gems"]

    def list_classes(self) -> list[dict]:
        return self.send("list_classes")["classes"]

    def list_uniques(self, type: str | None = None) -> list[dict]:
        return self.send("list_uniques", type=type)["uniques"]

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

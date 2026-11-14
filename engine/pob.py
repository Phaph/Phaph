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
        self.version = self._read()["version"]

    def _read(self) -> dict:
        assert self.proc.stdout
        for line in self.proc.stdout:
            if line.startswith("@@"):
                return json.loads(line[2:])
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
        text = "\n".join(f"{g} {level}/{quality}  1" for g in gems)
        return self.send("add_skill", text=text, main=main, full_dps=full_dps)

    def use_full_dps(self) -> None:
        """Count every skill group in PoB's Full DPS (needed once a build has more than one
        damage source, or minions whose count matters)."""
        self.send("full_dps_all")
        self.send("sync_minion_counts")

    def try_skill(self, group: int, gems: list[str], fields: list[str], level: int = 20, quality: int = 0,
                  keep_main: bool = False) -> dict:
        """Replace a group's gems and recalculate. keep_main: score the current main skill, not this group."""
        text = "\n".join(f"{g} {level}/{quality}  1" for g in gems)
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
                      metric: str = "total", goals=None) -> dict:
        from goals import weights
        w = weights(goals)
        kwargs = {"max_dist": max_dist, "def_weight": def_weight * w["def_mult"], "metric": metric,
                  "movement_weight": w["movement"], "rarity_weight": w["rarity"]}
        if points is not None:
            kwargs["points"] = points
        res = self.send("optimise_tree", **kwargs)
        if not isinstance(res.get("steps"), list):
            res["steps"] = []
        return res

    def reset_tree(self):
        return self.send("reset_tree")

    def calc(self, fields: list[str] | None = None) -> dict:
        kwargs = {"fields": fields} if fields else {}
        out = self.send("calc", **kwargs)["output"]
        return out if isinstance(out, dict) else {}  # dkjson sends an empty table as []

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

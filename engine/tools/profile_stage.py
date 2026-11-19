"""Profile one stage: time spent in PoB per (guide step, command).  python tools/profile_stage.py "Class|Ascendancy|Skill|Weapon" end"""
import sys, time, traceback, json, collections
sys_path = __import__("sys").path; sys_path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
import pob as P
STEPS = {"craft_gear", "optimise_tree", "optimise_supports", "optimise_spirit", "best_triggers", "optimise_defence",
         "fill_spare_spirit", "optimise_utility", "craft_jewels", "proxy_jewel", "kit_out", "specialise_set2",
         "cast_on_crit", "auto_config", "craft_weapon", "balance_attributes", "best_variants", "_consider_uniques"}
acc = collections.defaultdict(lambda: [0.0, 0])
orig = P.PoB.send
def send(self, cmd, **kw):
    t = time.perf_counter()
    try: return orig(self, cmd, **kw)
    finally:
        dt = time.perf_counter() - t
        names = [f.name for f in traceback.extract_stack()[:-1]]
        step = next((n for n in names if n in STEPS), "build_stage(other)")
        a = acc[(step, cmd)]; a[0] += dt; a[1] += 1
P.PoB.send = send
from guide import build_stage
spec = dict(zip(["class","ascendancy","skill","weapon_type"], sys.argv[1].split("|")))
t0 = time.time(); g = build_stage(spec, sys.argv[2]); total = time.time() - t0
print(f"TOTAL {total:.0f}s dps {g.dps:,.0f} boss {g.boss_dps:,.0f}")
by_step = collections.defaultdict(lambda: [0.0, 0])
for (st, cmd), (dt, n) in acc.items(): by_step[st][0] += dt; by_step[st][1] += n
for st, (dt, n) in sorted(by_step.items(), key=lambda x: -x[1][0]): print(f"STEP {st:<22} {dt:7.0f}s {n:7} calls")
for (st, cmd), (dt, n) in sorted(acc.items(), key=lambda x: -x[1][0])[:25]: print(f"CMD  {st:<22} {cmd:<20} {dt:7.0f}s {n:7} calls {dt/n*1000:6.0f} ms/call")

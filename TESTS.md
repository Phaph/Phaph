# In-game test requests (Lodestone leads)

For Kyle's Standard character. Each request: the build (PoB code in `ingame/`, open it in Path of Building with
Import > from text), what to buy, what to do, and what result confirms or kills the lead. PoE 2 has no damage meter,
so the tests use things you can count or time. Write the result under each entry (and Claude updates
`engine/data/breaker/leads.json`, which the Lodestone page shows).

Order = how much the answer is worth.

---

## 1. Rapid Shot + Fresh Clip II: does damage per bolt keep growing with attack speed?

**Why:** strongest lead so far. Fresh Clip II gives 1% more damage per bolt reloaded in the last 8 seconds. PoB counts
those as clip size x 8 / (firing time + reload time): Rapid Shot fires ~100 bolts a clip, so faster attacks mean more
bolts reloaded and more damage per bolt. Damage then grows with roughly attack speed squared, with no cap in the gem.
PoB: 5.68M DPS vs a pinnacle boss at 23 shots/s (Oracle, Uber Endgame).

- **Build:** `ingame/rapid_shot_oracle.txt` (only the main skill matters: Rapid Shot + Fresh Clip II on any crossbow).
- **Buy:** nothing special; any crossbow and Fresh Clip II. Two attack speed set-ups to compare (e.g. with and without
  an attack speed flask/charm or Rapid Attacks II).
- **Do:** fire a full clip at a big target. After a reload, open the character's buff bar: the Fresh Clip buff
  should show a stack count (bolts reloaded). Note the count at both attack speeds.
- **Confirms:** the stack count climbs with attack speed with no visible cap (e.g. 150+ stacks) and damage numbers
  per bolt visibly rise. **Kills:** a hidden cap (stacks stop at a fixed number like 50), or Rapid Shot's clip counts
  as one reload, not one per bolt.

**Result:** _(to fill)_

---

## 2. Rapid Shot + Rampart Raptor: firing without spending bolts

**Why:** new lead from the text scan (2026-11-19). Rampart Raptor (unique Tense Crossbow): "Bolts fired by Crossbow
Attacks have 100% chance to not expend Ammunition if you've Reloaded Recently" (recently = last 4 seconds). PoB
doesn't model ammunition at all. With Rapid Shot that could mean ~4 s of continuous fire after every reload, which
also changes how Fresh Clip (test 1) behaves.

- **Build:** the Rapid Shot build above with Rampart Raptor as the weapon.
- **Buy:** Rampart Raptor.
- **Do:** reload once, then hold Rapid Shot on a boss and watch the ammo counter for 10 seconds.
- **Confirms:** the counter doesn't drop for ~4 s after each reload. **Kills:** it drops normally, or the
  "Reloaded Recently" window ends the moment you start firing.

**Result:** _(to fill)_

---

## 3. Leopold's Applause: does penetration go below 0% resistance on a pinnacle boss?

**Why:** the gloves let hits penetrate resistances down to -50%. Normally a second penetration source does nothing
once a boss is at 0%; with Leopold's it keeps counting. PoB applies the -50% floor to bosses. Measured with the gloves
really worn (replacing Deathblow), Fireball Blood Mage: Leopold's alone +4%, Fire Penetration I alone +10%, **both
+31%**: the pair multiplies. If the floor holds in game, penetration-stacking builds around Leopold's are a real lead.

- **Build:** `ingame/leopolds_fireball_blood_mage.txt` (Fireball, Blood Mage, Leopold's Applause on).
- **Buy:** Leopold's Applause; Fire Penetration I support.
- **Do:** on the same map boss (or a pinnacle boss if you have the fragments), kill it 3 times with Fire Penetration I
  in the Fireball group and 3 times without, same gear otherwise. Time each kill.
- **Confirms:** clearly faster kills with Fire Penetration (PoB: +26% damage on top of Leopold's, vs +10% without it). **Kills:** no difference: the
  game stops penetration at 0% on bosses, or the -50% doesn't apply to them.

**Result:** _(to fill)_

---

## 4. Hexblast: how often can it really go off on one target?

**Why:** PoB casts Hexblast back to back (2.65 casts/s on this build), but it can only detonate a curse that is at
least half expired. The engine now limits it to once per ~5.9 s per target (cast Despair 0.7 s + 1.5 s curse delay +
half of Despair's 7.4 s), 0.17/s: 304K DPS instead of millions. If the real cycle is shorter, Hexblast is better
than we now say.

- **Build:** `ingame/hexblast_lich.txt` (Hexblast + Despair, Lich).
- **Buy:** nothing beyond the gems.
- **Do:** on a single boss, cast Despair then Hexblast as fast as the game allows for 30 seconds. Count the Hexblast
  detonations (the big hit), not the casts.
- **Confirms the limit:** about 5 detonations in 30 s. **Changes it:** clearly more (e.g. 10+): tell Claude the
  count and the limit gets the real number.

**Result:** _(to fill)_

---

## 5. Ember Fusillade: PoB's number vs real

**Why:** it wins several searches. PoB casts it like a plain spell. It ignores both the 10-ember cap with a 1.3 s
launch delay (fewer embers per second, about x0.7) and the 5% more damage per ember fired together (up to x1.5). We
think they roughly cancel; if not, it is over- or under-rated everywhere.

- **Build:** `ingame/ember_fusillade_oracle.txt`.
- **Do:** the same map boss 3 times with this build; compare the kill time with what you'd expect from PoB's 3.16M
  DPS (boss life / DPS). Easier: cast 10 embers then stop, and see whether they launch together after 1.3 s.
- **Confirms "roughly right":** kill times within ~30% of PoB's. **Changes it:** much slower: Claude adds a usage
  limit like Hexblast's.

**Result:** _(to fill)_

---

## Not worth a test

- **"Not consumed" charges reaching 100% (Flicker Strike):** every source together is about 45% (Perpetual Charge 25%,
  The Fabled Stag 10%, Hollow Form up to 10%). Far from 100%: no loop. Marked dead.
- **Detonate Dead against bosses:** limited to one corpse every 4 s (our estimate). Only worth timing if a boss
  build ever wants it.

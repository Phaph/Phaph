#!/usr/bin/env bash
# Builds the headless Path of Building toolchain into engine/vendor.
# Needs git, make and gcc. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor && cd vendor

POB_REPO=https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git
# Pinned so a rebuild never changes the engine by surprise. Move to a new PoB (e.g. 1.0) by changing this line,
# testing on staging first (LAUNCH_1.0.md). POB_REF=dev builds whatever is newest.
POB_REF=${POB_REF:-601768bd105869618c3d6581b883e5d7aeec91b2}   # dev, 2026-11-10, PoB 0.23.1
# PoB uses compound assignment (a += 1), which needs this LuaJIT commit or newer.
LUAJIT_REF=2460b3ff93a1c955de3d62cfc825de7d68dc272e

if [ ! -d PathOfBuilding-PoE2 ]; then
  git init -q PathOfBuilding-PoE2 && git -C PathOfBuilding-PoE2 remote add origin "$POB_REPO"
fi
git -C PathOfBuilding-PoE2 fetch -q --depth 1 origin "$POB_REF" && git -C PathOfBuilding-PoE2 checkout -q FETCH_HEAD
# The image drops .git, so keep the commit for the health check.
git -C PathOfBuilding-PoE2 log -1 --format='%H %cd' --date=short > POB_COMMIT

# Fixed PRNG and string IDs make table iteration order, and so optimiser results, the same
# on every run. Safe here: LuaJIT only runs PoB's and our own code.
LUAJIT_FLAGS="-DLUAJIT_SECURITY_PRNG=0 -DLUAJIT_SECURITY_STRID=0"
if [ ! -x LuaJIT/src/luajit ] || [ "$(cat LuaJIT/.pob-flags 2>/dev/null)" != "$LUAJIT_FLAGS" ]; then
  [ -d LuaJIT ] || git clone https://github.com/LuaJIT/LuaJIT.git LuaJIT
  git -C LuaJIT checkout -q "$LUAJIT_REF"
  make -C LuaJIT clean >/dev/null
  make -C LuaJIT -j"$(nproc)" XCFLAGS="$LUAJIT_FLAGS" >/dev/null
  echo "$LUAJIT_FLAGS" > LuaJIT/.pob-flags
fi

if [ ! -f lua-utf8.so ]; then
  [ -d luautf8 ] || git clone --depth 1 https://github.com/starwing/luautf8.git luautf8
  gcc -O2 -shared -fPIC -I LuaJIT/src -o lua-utf8.so luautf8/lutf8lib.c
fi

echo "PoB $(git -C PathOfBuilding-PoE2 log -1 --format='%h %cd' --date=short), LuaJIT ready"

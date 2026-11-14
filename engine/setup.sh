#!/usr/bin/env bash
# Builds the headless Path of Building toolchain into engine/vendor.
# Needs git, make and gcc. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor && cd vendor

POB_REPO=https://github.com/PathOfBuildingCommunity/PathOfBuilding-PoE2.git
POB_REF=${POB_REF:-dev}
# PoB uses compound assignment (a += 1), which needs this LuaJIT commit or newer.
LUAJIT_REF=2460b3ff93a1c955de3d62cfc825de7d68dc272e

if [ ! -d PathOfBuilding-PoE2 ]; then
  git clone --depth 1 --branch "$POB_REF" "$POB_REPO" PathOfBuilding-PoE2
else
  git -C PathOfBuilding-PoE2 fetch --depth 1 origin "$POB_REF" && git -C PathOfBuilding-PoE2 checkout -q FETCH_HEAD
fi

if [ ! -x LuaJIT/src/luajit ]; then
  [ -d LuaJIT ] || git clone https://github.com/LuaJIT/LuaJIT.git LuaJIT
  git -C LuaJIT checkout -q "$LUAJIT_REF"
  make -C LuaJIT -j"$(nproc)" >/dev/null
fi

if [ ! -f lua-utf8.so ]; then
  [ -d luautf8 ] || git clone --depth 1 https://github.com/starwing/luautf8.git luautf8
  gcc -O2 -shared -fPIC -I LuaJIT/src -o lua-utf8.so luautf8/lutf8lib.c
fi

echo "PoB $(git -C PathOfBuilding-PoE2 log -1 --format='%h %cd' --date=short), LuaJIT ready"

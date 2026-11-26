# Task 53: our own game-data export (PC dry run)

Checked on the server 2026-11-26 from the PoB PoE 2 copy in our image (`src/Export`, `CONTRIBUTING.md`
"Exporting GGPK data from Path of Exile"). Nothing here has been run yet.

## What it can and can't do (read first)
- PoB's own warning: the exporter **does not work on the pre-launch download (torrent)**, because that has no
  `Data` section. So on 1.0 day it only helps once the game itself is live and patched, not before.
  The window it covers: from launch until PoB's first 1.0 release (0-3 days on past patches, task 52).
- Windows only: the export code calls `dir /b`, `del` and `bun_extract_file.exe`, and "Dat View" is a GUI app
  (PoB's runtime exe with `src/Export/Launch.lua`). It can't run headless on the server.
- Lines PoB's parser doesn't know yet stay unsupported after an export (`tools/unsupported_lines.py` counts them).
  New mechanics still need PoB's code, not just its data.

## What's needed on the PC
1. PoE 2 installed (standalone `Content.ggpk`, or the Steam folder).
2. A PoB PoE 2 checkout at the release that matches the installed game (`engine/setup.sh` POB_REF, or a git clone
   of PathOfBuilding-PoE2 at that tag), including `runtime\Path of Building-PoE2.exe`.
3. `bun_extract_file.exe`, `libbun.dll`, `libooz.dll`: prebuilt at https://github.com/zao/ooz/releases (PoB's tip),
   otherwise build them from that repo with Visual Studio + CMake. Copy them to `src\Export\ggpk\`.

## Dry run (about 1 h, estimate)
1. Start Dat View: `"<repo>\runtime\Path of Building-PoE2.exe" "<repo>\src\Export\Launch.lua"`.
2. `Edit Sources...` -> `New` -> paste the path to `Content.ggpk` (standalone: include the file name;
   Steam: the game folder) -> Enter. cmd windows pop up while files unpack, then the table list appears.
3. `Scripts >>`, run in this order (double-click each): `skills.lua`, `bases.lua`, `mods.lua`, `passivetree.lua`,
   `minions.lua`, `miscdata.lua`, `statdesc.lua` (the rest only if these work). Note each one's time and errors.
4. The check: in the checkout, `git status` / `git diff --stat src/Data src/TreeData`. If the export matches the
   game version PoB shipped, the diff should be small (ordering, a few hand fixes). A big diff means the export
   doesn't reproduce PoB's data and isn't usable on launch day as is.
5. Load the exported data in our engine: copy the checkout's `src` over a copy of `engine/vendor/PathOfBuilding-PoE2/src`
   (keep the original), run `python engine/tools/patch_check.py dump` on both and `compare`, plus one small build.
6. Write the times, the errors and the diff size into BREAKER_PLAYBOOK.md (step "PoB 1.0") and tick task 53.

## Not checked
- Whether zao/ooz still has a current Windows release, and whether it reads the 0.5 / 1.0 bundle format.
- Whether the export scripts in our PoB version run cleanly on the current client.
- How long an export takes.

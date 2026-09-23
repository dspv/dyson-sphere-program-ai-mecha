# Game Integration Research

**As of 2026-09-23.** This file owns external findings and version-specific signature evidence. Source reading is not proof of gameplay integration.

## Local environment inventory

The development machine is macOS. Checks of `/Applications` and the usual macOS Steam common directory found no Dyson Sphere Program install, `Assembly-CSharp.dll`, or BepInEx DLL. `dotnet` was not found on `PATH`. The owner's gameplay target is Windows. Its exact game version, installation path, and mod loader build remain open in [risks](../.ai/12-risks.md).

## Verified source findings

- The [BepInEx 5 plugin documentation](https://docs.bepinex.dev/v5.4.16/api/BepInEx.BaseUnityPlugin.html) defines `BaseUnityPlugin` and its logger/config surface. The [setup guide](https://docs.bepinex.dev/v5.4.11/articles/dev_guide/plugin_tutorial/1_setup.html) says to select .NET target from managed runtime DLLs; do not assume a target for the owner's game.
- The [BepInEx install guide](https://docs.bepinex.dev/master/articles/user_guide/installation/) distinguishes Mono and IL2CPP builds. Choose the distribution after inspecting the game installation.
- The [DSP_Mod repository](https://github.com/starfi5h/DSP_Mod) contains BuildToolOpt and documents local game DLL references, a publicized `Assembly-CSharp` for its own development setup, and MIT licensing. Its approach is a lead, not a signature guarantee for this game version.
- [BlueprintTweaks source](https://github.com/kremnev8/DSP-Mods/tree/master/Mods/BlueprintTweaks) is a candidate for studying blueprint and placement paths. Its present compatibility and license for any borrowed code need direct verification before reuse.
- The [blueprint generator](https://github.com/RasmusStagsted/dsp_bp_generator) is only a format lead; the source specification warns that its format may be outdated.

Source review of pinned revisions found:

- [BuildToolOpt revision `be56c083`](https://github.com/starfi5h/DSP_Mod/tree/be56c08309d708dcd3f80fc03b2f36f5cc124459/BuildToolOpt) targets `net472` in its project file and references local game assemblies. It patches `BuildTool_Click`, `BuildTool_Inserter`, path/addon tools, and blueprint paste. Its source shows `CheckBuildConditions` before `CreatePrebuilds` as the build-tool route; it also has a separate hologram mode that permits item-free ghosts, which this project must not enable for acceptance. The repository license is MIT.
- [BlueprintTweaks revision `f91de586`](https://github.com/kremnev8/DSP-Mods/tree/f91de5868fbf2c040ea4c6daf7f4660c2efeeb74/Mods/BlueprintTweaks) has MIT licensing. Its `UndoBuild.Redo` and `UndoBlueprint.Redo` code calls game build-tool condition checks before prebuild creation. The source also demonstrates endpoint and spherical-grid complexity. These are leads only; local DSP signatures and ordinary-mode behavior remain unverified.
- [Spherewright revision `27082109`](https://github.com/AvaloNero/Spherewright/tree/270821096137ddf4fc69c36126c9a7d9b1a66e74) is an MIT-licensed, separate BepInEx/MCP project close to this project's intended bridge. Its [release description](https://old.thunderstore.io/c/dyson-sphere-program/p/Arcueid_77/Spherewright/) says 0.3.3 supports DSP `0.10.34.28529`, BepInEx `5.4.17`, Windows x64 and peaceful single-player, with guarded observation and actions. Its own [architecture](https://github.com/AvaloNero/Spherewright/blob/270821096137ddf4fc69c36126c9a7d9b1a66e74/docs/architecture.md) says it supplies primitives rather than an autonomous goal planner. Its reported gameplay tests are upstream claims, not tests in the owner's game. The 0.4 source has an unshipped read-only factory planner; the released package must not be assumed to have that feature.
- The [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle) requires initialization before normal calls, and its [stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) uses one JSON-RPC message per line. The local probe implements the `2025-06-18` version and refuses a version mismatch. The [Responses function-calling guide](https://developers.openai.com/api/docs/guides/function-calling) documents strict JSON-schema tools and function-call output. The local model adapter requests a single bounded proposal; it has only mocked HTTP test coverage and no live API call yet.

No third-party code has been copied. A `net472` bridge target is a provisional compilation choice, not a verified match for the owner's DSP runtime. [AutoBuild's package](https://thunderstore.io/c/dyson-sphere-program/p/kumor/AutoBuild/) was found; source repository, license, current game compatibility, and method signatures remain unverified. No DSP method signature is claimed as verified for the owner's installation.

## Windows inspection checklist

1. Record game version, executable path, architecture, scripting backend, and the presence of `DSPGAME_Data/Managed/Assembly-CSharp.dll`, `mscorlib.dll`, and `netstandard.dll`.
2. Install a matching BepInEx build, launch the game once, record its version and startup log, and locate `BepInEx/core` and `BepInEx/LogOutput.log`.
3. Build only against local DLLs. Record hashes and versions in the private run log; do not commit DLLs.
4. Inspect actual `GameMain`, player, factory, inventory, and build-tool signatures in this version. For every candidate method, record assembly/type/method, thread context, prerequisites, error behavior, and one visible game check.
5. Study the current BuildToolOpt and BlueprintTweaks code for normal build previews, placement errors, construction drones, belts, sorters, and recipes. Record license before borrowing any code.
6. Complete one observation before attempting a mutation. Preserve the original save and use a copy for every experiment.

## Version-specific API record

No rows are filled because no game DLL has been inspected. Add one short record per feature with game version, precise signature, verification method, and status. Use prose if a record needs more than a short cell.

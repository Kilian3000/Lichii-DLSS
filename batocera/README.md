# Batocera integration

This directory records the integration used with an existing custom Switch 2 system
on Batocera 41. It is **not a universal installer for a stock Batocera installation**:
it depends on the existing library, streaming-controller, hotkey and exit-watch helpers.
It must be adapted when those local helpers differ. The profile initializer refuses
to overwrite an initialized profile, and installation checks that the original
integration has not changed before replacing its files.

For everyday use, see [README-Lichii-DLSS.txt](README-Lichii-DLSS.txt).

## Layout and boundaries

- Normal Lichii: `/userdata/system/lichii`, with its official automatic updates enabled.
- Experimental build: `/userdata/system/lichii-dlss/current.AppImage`, with the official
  self-updater compiled out and disabled in its profile.
- The separate XDG config/data/cache roots live under each application's `profile`.
  Save storage, keys, installed content and mods point to the existing normal profile;
  no game files or user data are distributed here.
- Only controller settings and saved input profiles are synchronized in both directions.
  Graphics and other emulator preferences remain independent. The existing streaming
  selector receives the `lichii` controller family and the experimental config path.
- A common launch lock prevents simultaneous access by the Switch 2 emulators.
- The frontend lists `lichii-dlss` alongside `lichii` and `eglantine` per game. The
  settings shortcut and update/rollback entries target the experimental installation.

`baseline-integration.json` contains the generic integration scripts before this
change. `prepare-integration.py` creates the updated scripts/XML/desktop entry.
`init-profile.py` backs up settings and saves, creates the independent profile, and
enables DLSS. `install-integration.py` verifies the staged release and runtime hashes
before activating the package and prepared integration. It expects release assets in
`/userdata/system/lichii-dlss/staging` and these scripts in `.../setup`.

The separate NVIDIA Linux runtime is not redistributed in the AppImage or source.
The validated runtime was [NVIDIA's Linux DLSS library](https://github.com/NVIDIA/DLSS/blob/9981c6350dc58c0ce21f024fd65e31e851c31689/lib/Linux_x86_64/rel/libnvidia-ngx-dlss.so.310.9.16),
commit `9981c6350dc58c0ce21f024fd65e31e851c31689`.
`libnvidia-ngx-dlss.so.310.9.16` has SHA256
`30982c937afed85c96b8d313323de9a650a2eec6de1bb0f714b21750f4ce98f6`.
Obtain the Linux library and its license from NVIDIA and place them in the separate
profile's `data/lichii/ngx` directory. The installed NVIDIA driver must also provide
its NGX core library. Optional neural rendering remains Off; no model is required.

## Optional neural rendering

The per-game frontend menu offers neural Off/Standard/Natural/Cinematic, DLSS quality
and effect strength. The launcher uses `batocera-renderer.py` to resolve Batocera's
normal global → system → folder → game precedence. Only explicitly selected values
temporarily override the experimental renderer profile, including existing per-game
inheritance flags; shutdown restores the previous values while retaining controller
changes and unrelated settings. A recovery file also handles an interrupted session
on the next launch. Auto leaves the emulator's own preferences in effect when no
inherited frontend choice exists. F1 settings remain available for live comparisons.

The tested model source is NVIDIA's official [RTX Remix 1.6.1 x64 package](https://github.com/NVIDIAGameWorks/rtx-remix/releases/tag/remix-1.6.1):

- Archive SHA256: `7dd1d44492a609050e44b0e3581cec31135d1ed88b4a91123b4faae91955716a`.
- `nvngx_dlssnr.dll` SHA256: `2bc19bc09a7b89dd44f73e2ac0108fcc586e2154bdd0830f242f4f040e28789f`,
  matching NVIDIA's release CRC/SHA manifest.
- Its `WEIGHTS_HT` resource matches the supported 310.8.0 model's resource SHA256
  `836f445d06ecd2e59bb9f17b84b91c143396fd76ccda1c9dc7fe81d5edd548f4`.

`import-neural-model.py` extracts only that verified resource from this newer DLL,
without loading executable code, and reproduces the native importer's packed-weight
and tensor-table hashes. It does not import the additional newer/smaller model.
Obtain the NVIDIA archive yourself, verify its published hashes, extract the DLL,
then run the script with the DLL and a new destination `profile/data/lichii/ngx/nr/310.8.0`.
The weights, DLL, licenses and source archive stay on the user's PC.

Run `python3 batocera/test-batocera-renderer.py` when changing this integration or
updating the underlying settings enums. Tests cover frontend precedence, preference
restoration, interrupted-session recovery, and enum compatibility with the emulator.
The optional GPU smoke command is documented in `docs/user/DLSSLinux.md`.

Revision 4 was validated on RTX 4070 SUPER / NVIDIA 620.70.06: all 15 CTest
groups and four integration checks passed, as did the real-SR GPU suite and NR
control suites at scales 1 and 4, each across three device lifecycles. The NR
suite uses fixed scene pixels after successful NGX evaluation to isolate neural
history/reset/blend assertions; the separate no-model suite retains genuine SR
output/history coverage. Ocarina loaded an existing save through the frontend's
Natural + Native DLAA choices, initialized neural processing at 1920×1080 and
closed cleanly with the model active. Its renderer preferences were restored on
exit; the normal official binary/updater and shared save/controller paths were
verified unchanged. Approximate gameplay samples were 30 FPS with NR at 1440p,
37–42 FPS with NR at 1080p, and 52–60 FPS with ordinary DLSS, depending on scene.

## Building and maintaining the fork

Use **Actions → Build Batocera DLSS → Run workflow**. To incorporate a newer official
release, select **Merge a newer official Lichii release** and enter `latest` or an
official `build-N` tag. The workflow merges upstream, compiles the PGO binaries and
NGX smoke tool, runs CTest, packages an AppImage, then pushes and publishes a prerelease.
Merge/build/test failures prevent publication. They require a source fix before retrying.
The normal official install does not depend on this workflow.

After a published build, the F1 updater's **6** entry installs that fork release with
SHA256 verification and backups; **7** selects a previous installed fork package.
Selecting normal `lichii` for a game returns it to the official build immediately.

Do not promise compatibility merely because compilation succeeds. Test the packaged
`ngx_smoke` on the target GPU/driver, then load a known save in a supported game. The
Graphics panel must report **Native NGX active** with increasing successful evaluations;
an available/ready runtime alone is insufficient. Check the real controller, audio,
exit shortcut, normal official updater and graphics isolation. Keep game captures,
saves, keys, shaders, pipeline caches and other private data out of this repository.

## Validation of revision 2

Base `build-366`, source `5da1ac7e714cfa8db4a83692aca446e54304999b`, native Linux
DLSS integration from myshadowww's upstream PR #840. The local fix reuses stable
Lichii's cooperative-matrix2 feature structure instead of adding a duplicate Vulkan
feature node, which the NVIDIA driver rejected during device creation.

All 15 CTest groups passed. The packaged NGX smoke test passed on RTX 4070 SUPER with
driver 620.70.06, including repeated device lifecycles and failure cleanup. Ocarina
loaded the existing Hyrule Field save and reported over 1,500 successful evaluations
at 1920×1080 → 2560×1440, Automatic selecting Quality. Output remained 1080p. The
normal binary hash and automatic-update setting were unchanged. These checks do not
establish support for every game or eliminate first-use shader compilation pauses.

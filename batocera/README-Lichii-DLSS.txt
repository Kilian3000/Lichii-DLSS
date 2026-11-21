LICHII DLSS — EXPERIMENTAL BATOCERA OPTION

Choosing it for a game

Highlight a game in Nintendo Switch 2, hold the confirm/select-game button,
then open Advanced Game Options > Emulator and choose lichii-dlss.
Choose lichii again to return that game to the normal official version.
The other games keep their existing emulator choices.

Games and saves

All choices use your existing ROM folder. Lichii DLSS points at the same save
storage as normal Lichii and Eglantine; no save export or game copy is needed.
Only one Switch 2 emulator can run at once, protecting the shared saves.
Graphics settings and shader caches are separate between emulator variants.
The DLSS cache was initially seeded from the existing Lichii cache.

Controllers, audio and settings

The same controller preferences are copied between normal Lichii and Lichii DLSS
when the experimental version opens and closes. The existing automatic physical
controller / Moonlight controller selection and audio routing are retained.
Connect Moonlight before starting a game when using the Portal.
PS + Options is still the Batocera exit shortcut.

Exit a running game and use F1 > Applications > Lichii DLSS Settings to configure
the experimental version. Normal Lichii Settings continues to configure the
official version. For an individual game, right-click it > Configure Game.

DLSS support and comparison

NVIDIA DLSS is enabled in the experimental profile. Its quality mode initially
uses Automatic, and optional neural rendering is Off. NVIDIA's separate Linux
DLSS runtime is installed in this profile's ngx folder.

DLSS only replaces supported game upscaling passes. Selecting this emulator does
not force DLSS into every game. A ready runtime alone does not prove DLSS is being
used: while playing a supported game, the Graphics panel reports Native NGX active
and an increasing successful-evaluation count. The status bar also identifies DLSS.

Ocarina's initial comparison uses Docked, 1x resolution and Max Resolution Off,
matching the normal FSR test settings. The current display/stream output remains
1080p. The FSR option remains available as a fallback when DLSS cannot run.

Validated on 21 November 2026: build-366 with the Linux DLSS port and Vulkan
feature-chain fix passed all 15 unit-test groups and the native NGX smoke test
on the RTX 4070 SUPER. Ocarina loaded the existing Hyrule Field save and reported
over 1,500 successful native DLSS evaluations at 1920x1080 -> 2560x1440, Quality.
This confirms working upscaling; image-quality and smoothness preferences still
need a personal comparison. DLSS does not precompile unknown game shaders.

Updates and rollback

Normal Lichii keeps its usual official automatic updates. The experimental build
does not replace itself with official binaries; the two update paths are separate.

In F1 > Applications > Update Switch 2 Emulators:
  6  downloads the newest published Lichii DLSS package.
  7  returns Lichii DLSS to its previous installed package, when one exists.
These preserve the shared saves and the experimental graphics profile.

A newer official release must first be integrated into this fork and built.
Repository: https://github.com/Kilian3000/Lichii-DLSS
Open Actions > Build Batocera DLSS > Run workflow, enable Merge a newer official
Lichii release, and use latest or an official build-N tag. Failed merges, builds
or unit tests stop publication, leaving the previous download available. GPU and
gameplay checks are still needed after a successful build. Codex can handle those
updates and resolve source conflicts when required.

Build information, installed runtime and backups are under
/userdata/system/lichii-dlss. Do not delete or replace the shared NAND save links.

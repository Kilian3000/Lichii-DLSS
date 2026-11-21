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

Per-game frame generation

Advanced Game Options > FRAME GENERATION is available with both lichii and
lichii-dlss: Off, 2x, 3x or 4x. Auto inherits Batocera's global, system and folder
choices, then the emulator's existing preference. To change only Ocarina, choose
it in that game's Advanced Game Options rather than the system options.

These choices use Lichii's built-in Optical Flow frame generation, which supports
Linux in the original official build. The official auto-updating Lichii can use
it; the custom build is needed for the native Linux DLSS/neural additions, not
for this optical-flow option. Generated frames improve presentation smoothness
but do not increase the game's simulation speed. A matching high-refresh display
or stream is needed to show the extra frames.

2x/3x/4x selects a fixed multiplier with automatic target-rate control disabled.
Off only disables frame generation and keeps its other preferences. On normal
Lichii this bridge applies only frame-generation keys; experimental neural and
DLSS choices are ignored. With Auto and no inherited choice, it changes nothing.
Temporary choices are restored on exit. Opening either Lichii settings launcher
also recovers an interrupted override before displaying its settings. Controller
sharing remains specific to the experimental fork. The normal updater is unchanged.

Per-game neural rendering and comparison

With lichii-dlss selected, Advanced Game Options now includes:
  DLSS NEURAL RENDERING: Off (ordinary DLSS), Standard, Natural or Cinematic.
  DLSS QUALITY MODE: Game resolution, Native DLAA, Quality, Balanced,
                     Performance or Ultra Performance.
  NEURAL EFFECT STRENGTH: 25%, 50%, 75% or 100%.
Auto inherits the usual Batocera system/folder choices, then the emulator settings.
Changes in Batocera apply the next time the game starts. The same neural options
can also be changed live in Lichii's Graphics settings with Apply / OK.

Off releases the neural resources and retains ordinary DLSS. Lower effect strength
only blends the picture: it does not reduce the model's processing cost.
Native DLAA processes the game's render resolution rather than upscaling first;
this can reduce neural GPU work. Other quality modes depend on the game's sizes
and can fall back automatically when unsupported.

On the RTX 4070 SUPER, matched Hyrule Field measurements averaged about 60 FPS
with neural rendering Off, 41 FPS with Natural at 1080p Native DLAA, and 33 FPS
with Natural at 1440p. The official Linux build also produced 60 real plus 60
generated frames per second with Optical Flow 2x and 1080p/120 Hz output.
These are scene-dependent samples. Frame generation and neural rendering do not
remove shader compilation pauses.

The global neural default is Off. Per-game Batocera choices temporarily override
only the selected renderer settings. The launcher restores the emulator's own
preferences after exit, and recovers an interrupted override on its next launch.
Normal Lichii, saves and controller preferences are not replaced by these options.

The installed neural model was extracted locally from NVIDIA's official RTX Remix
1.6.1 x64 package. Its existing 310.8.0 WEIGHTS_HT resource, packed weights and
tensor table were verified against the native Lichii importer's hashes. The DLL
is never executed by the importer, and neither DLL nor weights are redistributed
in this fork. Model provenance and test results are under /userdata/system/lichii-dlss.

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

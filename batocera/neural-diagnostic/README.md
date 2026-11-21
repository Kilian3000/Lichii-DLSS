# Isolated neural rendering diagnostic

This is a manual artifact for local comparison, not an emulator release or update.
The workflow applies `runtime.patch` and the checked image-tool adaptation only in
its ephemeral checkout. Production source, settings, installed apps, models, game
images and saves are not modified or uploaded. The AppImage has its updater disabled.
Run it with a private profile and a copied save/cache as appropriate. Do not install
it over the ordinary DLSS build. GPU correctness/performance require target testing.

The independent `offline` job produces `neural-cinematic-offline-linux-x86_64` first;
the `app` job produces `neural-gameplay-diagnostic-linux-x86_64`. Both are Actions
artifacts with seven-day retention. No release, tag, push or remote install occurs.

## Parameters

Unset `LICHII_NR_DIAGNOSTIC` (or set it to `0`) for the original runtime behavior,
including its normal NR Off setting. Other diagnostic variables are then ignored.
Use this for an AppImage parity/baseline check before timing diagnostic cases.

Set `LICHII_NR_DIAGNOSTIC=1` to enable NR independently of the saved NR toggle.
This still requires native DLSS and a supported installed model/GPU. The variables
below are read once per process; restart between cases. They never change config files.

| Variable | Values | Default when enabled |
| --- | --- | --- |
| `LICHII_NR_STYLE` | `standard`, `natural`, `cinematic` | Saved style, Standard if NR was Off |
| `LICHII_NR_INTENSITY` | Finite number 0..2 | Saved strength / 100 |
| `LICHII_NR_TONE` | Finite number 0..2 | Saved local tone / 100 |
| `LICHII_NR_STRUCTURE` | Finite number 0..2 | Saved structure / 100 |
| `LICHII_NR_AUTO_MASK` | `0`, `1` | `1` (production behavior) |
| `LICHII_NR_PASSES` | `1`, `2`, `4` | `1` |
| `LICHII_NR_HEIGHT` | `1080`, `1440`, `2160` | Native SR output size |
| `LICHII_NR_CHECK_EVERY` | `0` or 60..10000 | `0` |

Invalid options explicitly fail the NR diagnostic, leaving plain SR. Never count
that fallback as a valid NR performance result. Forced sizes require a 16:9 SR
output and become 1920x1080, 2560x1440 or 3840x2160. Game rendering, DLSS quality,
SR output and presentation size are unchanged. A differing processing size uses
RGBA16F Vulkan **linear** blits into and out of the NR image. This differs from
Lanczos resizing of offline inputs/results. No blit occurs when sizes already match.

Each live pass owns a separate model, workspace and temporal history. Every pass
consumes the preceding pass's color; history is carried between game frames for
that pass only. Normal scene resets reset all passes. This uses more VRAM than the
offline tool's reused workspace; out-of-memory cases must be reported as failed,
not estimated FPS. The game's motion view is sampled in normalized UV coordinates,
which supports the changed NR extent without rescaling its underlying texture.

`NR DIAGNOSTIC active` logs effective parameters, processing/output sizes, HDR flag,
filter and independent-history count. Query the debug server's `log_tail` with
`contains: "NR DIAGNOSTIC"`. Initialization or rebind failures log `FAILED` and mark
the case invalid. Drained backend teardown (including normal shutdown) logs completed NR frames,
`all N passes timeout-free`, and `kernel_timeout=false`. Periodic checks can be enabled for correctness
runs, but they drain GPU work and can affect timing. Leave CHECK_EVERY unset/zero
for FPS runs; initialization/rebind and shutdown still check timeouts. Close normally
to collect the shutdown check. Forced termination or a missing completion check is
an unvalidated run. Use externally bounded runs for a driver/device hang.

## Cinematic recipe and limits

For a 1440p, one-pass comparison with the requested controls:

```sh
LICHII_NR_DIAGNOSTIC=1 LICHII_NR_STYLE=cinematic \
LICHII_NR_INTENSITY=2 LICHII_NR_TONE=2 LICHII_NR_STRUCTURE=2 \
LICHII_NR_AUTO_MASK=0 LICHII_NR_PASSES=1 LICHII_NR_HEIGHT=1440 \
  ./lichii-nr-diagnostic-linux-x86_64.AppImage ...
```

Natural comparisons use style=natural, intensity/tone/structure=1, auto_mask=1,
and the requested height and pass count. Keep Native DLAA and 1080p output fixed
for the gameplay comparison. Compare actual frame-time samples from the same
scene/camera and capture conditions, including both an original-build baseline
and a diagnostic-build baseline with the master switch unset. Do not add offline
GPU times to game frame times or infer live FPS from the offline benchmark.

The model has local tone, structure, skin and automatic-mask conditioning; it has
**no Global Tone channel**. Setting `LICHII_NR_GLOBAL_TONE` is rejected, rather than
silently mapping it to a different operation. Skin stays -1. Auto-mask=0 selects
the model's non-mask conditioning lanes. Overall intensity=2 uses the existing
shader's extrapolation followed by clipping; this is not verified DLL intensity parity; local tone=2 enters the model, while
the separate style operator already clamps its tone scaling to 1. No new image
algorithm was introduced. UI correction is unavailable; NR applies at the game's
recognized DLSS pass, whose relation to HUD composition can differ from RenoDX.
SDR screenshots remain display-code RGB; paper-white 203 nits is not an SDR model
control. Live HDR inputs use the existing normalized HDR proxy path. Thus this is
the closest exposed model recipe, **not a verified exact RenoDX pipeline match**.

Mapping references: pinned OpenDLSS-NR
[preprocessing](https://github.com/maanHimself/OpenDLSS-NR/blob/9d08f4184bbcb9d858e2fb7a7834ec0837a9d2f1/shaders/preprocess.comp)
and [frame pipeline](https://github.com/maanHimself/OpenDLSS-NR/blob/9d08f4184bbcb9d858e2fb7a7834ec0837a9d2f1/docs/frame.md),
and local `externals/opendlss-nr/shaders/nr_{preprocess,composite,common}.*`.

For the intensity interpretation control, run the same recipe with
`LICHII_NR_INTENSITY=1`. Tone, structure, mask, size and pass count stay identical.
Compare both actual outputs; do not label the intensity-2 extrapolation an exact
RenoDX reproduction. No additional build is needed for this control.

## Offline frozen-image tool

```sh
LICHII_NR_DIAGNOSTIC=1 LICHII_NR_STYLE=cinematic \
LICHII_NR_INTENSITY=2 LICHII_NR_TONE=2 LICHII_NR_STRUCTURE=2 \
LICHII_NR_AUTO_MASK=0 DLSS5VK_DEVICE_INDEX=0 \
  ./neural_image_benchmark MODEL IMAGE.rgba32f 2560 1440 OUTPUT_PREFIX 1 5
```

The CLI is unchanged: `MODEL RGBA32F WIDTH HEIGHT OUTPUT_PREFIX PASSES [REPEATS=5]`.
The input must exactly match WIDTH*HEIGHT*16 bytes: top-down, little-endian RGBA
float32, SDR display-code values, alpha normally 1. Keep the imported 310.8.0 model
and source image on the target PC. Output is `OUTPUT_PREFIX.rgba16f` (full-resolution,
headerless little-endian RGBA16F) and `OUTPUT_PREFIX.json` (effective parameters,
GPU chain/per-pass statistics and all samples). The output parent must exist.
The tool does no resizing; resize to the common final 1080p size separately.
If HEIGHT/PASSES env overrides are supplied, they must agree with the CLI.
With the master switch unset the tool retains Natural, strength/tone/structure=1,
auto-mask=1. It keeps one backend workspace, fresh history every pass, one discarded
warmup chain, then five measured chains by default. The original image is restored
once before each chain; later passes consume the previous result. Nonfinite
outputs, kernel timeouts and Vulkan validation errors fail the run. GPU timestamps
exclude model initialization, source upload, CPU waits, readback, emulator work and
presentation. This is a fresh-history preview, not a live-history gameplay result.

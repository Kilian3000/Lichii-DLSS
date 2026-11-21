#!/usr/bin/env python3
"""Apply the reviewed diagnostic adaptation to an ephemeral CI checkout only."""
from pathlib import Path
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true', help='Validate without changing source files')
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
folder = Path(__file__).resolve().parent
patch = folder / 'runtime.patch'
subprocess.run(['git', 'apply', '--check', str(patch)], cwd=root, check=True)
source = (root / 'batocera/neural_image_benchmark.cpp').read_text()
replacements = [
    ('#include "video_core/neural_rendering/backend.h"',
     '#include "video_core/neural_rendering/backend.h"\n'
     '#include "video_core/neural_rendering/diagnostic_options.h"'),
    ('        const uint32_t width = ParseCount(argv[3], "WIDTH", 7680);',
     '''        const auto& options = NR::NeuralDiagnosticOptions();
        if (!options.error.empty()) throw std::runtime_error(options.error);
        const auto style = static_cast<NR::Style>(options.style.value_or(1));
        const float intensity = options.intensity.value_or(1.0f);
        const float tone = options.tone.value_or(1.0f);
        const float structure = options.structure.value_or(1.0f);
        const bool auto_mask = options.auto_mask.value_or(true);
        const uint32_t width = ParseCount(argv[3], "WIDTH", 7680);'''),
    ('        const std::string prefix = argv[5];',
     '''        if (options.enabled && options.height && options.height != height)
            throw std::runtime_error("LICHII_NR_HEIGHT disagrees with image HEIGHT");
        if (options.enabled && std::getenv("LICHII_NR_PASSES") && options.passes != passes)
            throw std::runtime_error("LICHII_NR_PASSES disagrees with CLI PASSES");
        const std::string prefix = argv[5];'''),
    ('                    frame.style = NR::Style::Natural;\n'
     '                    frame.intensity = frame.tone = frame.structure = 1.0f;',
     '''                    frame.style = style;
                    frame.intensity = intensity;
                    frame.tone = tone;
                    frame.structure = structure;
                    frame.auto_mask = auto_mask;'''),
    ('            {"style", "Natural"}, {"strength_percent", 100}, {"tone_percent", 100},\n'
     '            {"structure_percent", 100}, {"passes", passes}, {"repeats", repeats},',
     '''            {"style", static_cast<unsigned>(style)}, {"intensity", intensity},
            {"local_tone", tone}, {"structure", structure}, {"auto_mask", auto_mask},
            {"skin_structure", -1}, {"global_tone", "unsupported, not applied"},
            {"sdr_display_code_input", true}, {"passes", passes}, {"repeats", repeats},'''),
    ('Natural 100%%; fresh history per pass;',
     'Natural 100%% default; LICHII_NR_DIAGNOSTIC=1 enables env overrides; fresh history per pass;'),
]
for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit(f'Diagnostic benchmark source changed: {old[:100]!r}')
    source = source.replace(old, new)
if args.check:
    print('Diagnostic runtime patch and offline adaptation match current source')
else:
    subprocess.run(['git', 'apply', str(patch)], cwd=root, check=True)
    (root / 'src/video_core/neural_rendering/diagnostic_options.h').write_text(
        (folder / 'options.h').read_text())
    (root / 'src/tests/video_core/neural_rendering_smoke.cpp').write_text(source)
    print('Applied diagnostic-only runtime and standalone image tool; do not publish as a release')

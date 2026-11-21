// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later
#include <cassert>
#include "options.h"
using VideoCore::NeuralRendering::DiagnosticOptions;
int main() {
    for (const char* key : {"LICHII_NR_DIAGNOSTIC", "LICHII_NR_STYLE", "LICHII_NR_INTENSITY",
         "LICHII_NR_TONE", "LICHII_NR_STRUCTURE", "LICHII_NR_AUTO_MASK", "LICHII_NR_PASSES",
         "LICHII_NR_HEIGHT", "LICHII_NR_CHECK_EVERY", "LICHII_NR_GLOBAL_TONE"}) unsetenv(key);
    setenv("LICHII_NR_INTENSITY", "bad", 1);
    assert(!DiagnosticOptions::Load().enabled); // Inactive overrides cannot alter production.
    setenv("LICHII_NR_DIAGNOSTIC", "1", 1);
    assert(!DiagnosticOptions::Load().error.empty());
    setenv("LICHII_NR_INTENSITY", "2", 1);
    setenv("LICHII_NR_STYLE", "cinematic", 1);
    setenv("LICHII_NR_TONE", "2", 1);
    setenv("LICHII_NR_STRUCTURE", "2", 1);
    setenv("LICHII_NR_AUTO_MASK", "0", 1);
    setenv("LICHII_NR_PASSES", "4", 1);
    setenv("LICHII_NR_HEIGHT", "1440", 1);
    auto value = DiagnosticOptions::Load();
    assert(value.error.empty() && value.enabled && value.style == 2 && value.intensity == 2 &&
           value.tone == 2 && value.structure == 2 && value.auto_mask == false &&
           value.passes == 4 && value.height == 1440 && value.check_every == 0);
    for (const char* bad : {"nan", "inf", "-0.1", "2.1", "1junk", ""}) {
        setenv("LICHII_NR_INTENSITY", bad, 1);
        assert(!DiagnosticOptions::Load().error.empty());
    }
    setenv("LICHII_NR_INTENSITY", "0.25", 1);
    assert(DiagnosticOptions::Load().intensity == 0.25f);
    setenv("LICHII_NR_PASSES", "3", 1);
    assert(!DiagnosticOptions::Load().error.empty());
    setenv("LICHII_NR_PASSES", "2", 1);
    setenv("LICHII_NR_HEIGHT", "720", 1);
    assert(!DiagnosticOptions::Load().error.empty());
    setenv("LICHII_NR_HEIGHT", "2160", 1);
    setenv("LICHII_NR_CHECK_EVERY", "1", 1);
    assert(!DiagnosticOptions::Load().error.empty());
    setenv("LICHII_NR_CHECK_EVERY", "600", 1);
    assert(DiagnosticOptions::Load().check_every == 600);
    setenv("LICHII_NR_GLOBAL_TONE", "2", 1);
    assert(!DiagnosticOptions::Load().error.empty());
    setenv("LICHII_NR_DIAGNOSTIC", "0", 1);
    assert(DiagnosticOptions::Load().error.empty() && !DiagnosticOptions::Load().enabled);
}

// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <charconv>
#include <cmath>
#include <cstdlib>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>

namespace VideoCore::NeuralRendering {
// Included only by the explicitly built diagnostic artifact. Never saved to a profile.
struct DiagnosticOptions {
    bool enabled{};
    std::string error;
    std::optional<unsigned> style;
    std::optional<float> intensity, tone, structure;
    std::optional<bool> auto_mask;
    unsigned passes = 1;
    unsigned height{};
    unsigned check_every{}; // Zero avoids periodic GPU drains during FPS measurements.

    static DiagnosticOptions Load() {
        DiagnosticOptions out;
        const char* master = std::getenv("LICHII_NR_DIAGNOSTIC");
        if (!master || std::string_view(master) == "0")
            return out;
        out.enabled = true;
        try {
            if (std::string_view(master) != "1")
                throw std::runtime_error("LICHII_NR_DIAGNOSTIC must be 0 or 1");
            if (const char* value = std::getenv("LICHII_NR_STYLE")) {
                const std::string_view style{value};
                if (style == "standard") out.style = 0;
                else if (style == "natural") out.style = 1;
                else if (style == "cinematic") out.style = 2;
                else throw std::runtime_error("LICHII_NR_STYLE: standard, natural or cinematic");
            }
            auto scalar = [](const char* name) -> std::optional<float> {
                const char* value = std::getenv(name);
                if (!value) return std::nullopt;
                const std::string_view text{value};
                float parsed{};
                const auto result = std::from_chars(text.data(), text.data() + text.size(), parsed);
                if (result.ec != std::errc{} || result.ptr != text.data() + text.size() ||
                    !std::isfinite(parsed) || parsed < 0 || parsed > 2)
                    throw std::runtime_error(std::string(name) + " must be finite in [0, 2]");
                return parsed;
            };
            out.intensity = scalar("LICHII_NR_INTENSITY");
            out.tone = scalar("LICHII_NR_TONE");
            out.structure = scalar("LICHII_NR_STRUCTURE");
            if (const char* value = std::getenv("LICHII_NR_AUTO_MASK")) {
                const std::string_view text{value};
                if (text != "0" && text != "1")
                    throw std::runtime_error("LICHII_NR_AUTO_MASK must be 0 or 1");
                out.auto_mask = text == "1";
            }
            if (const char* value = std::getenv("LICHII_NR_PASSES")) {
                const std::string_view text{value};
                if (text == "1") out.passes = 1;
                else if (text == "2") out.passes = 2;
                else if (text == "4") out.passes = 4;
                else throw std::runtime_error("LICHII_NR_PASSES must be 1, 2 or 4");
            }
            if (const char* value = std::getenv("LICHII_NR_HEIGHT")) {
                const std::string_view text{value};
                if (text == "1080") out.height = 1080;
                else if (text == "1440") out.height = 1440;
                else if (text == "2160") out.height = 2160;
                else throw std::runtime_error("LICHII_NR_HEIGHT must be 1080, 1440 or 2160");
            }
            if (const char* value = std::getenv("LICHII_NR_CHECK_EVERY")) {
                const std::string_view text{value};
                const auto result = std::from_chars(text.data(), text.data() + text.size(), out.check_every);
                if (result.ec != std::errc{} || result.ptr != text.data() + text.size() ||
                    out.check_every > 10000 || (out.check_every && out.check_every < 60))
                    throw std::runtime_error("LICHII_NR_CHECK_EVERY must be 0 or 60..10000");
            }
            if (std::getenv("LICHII_NR_GLOBAL_TONE"))
                throw std::runtime_error("Global Tone has no equivalent in this backend");
        } catch (const std::exception& failure) {
            out.error = failure.what();
        }
        return out;
    }
};
inline const DiagnosticOptions& NeuralDiagnosticOptions() {
    static const auto options = DiagnosticOptions::Load();
    return options;
}
} // namespace VideoCore::NeuralRendering

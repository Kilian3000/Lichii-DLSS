// SPDX-FileCopyrightText: Copyright 2026 Eden Emulator Project
// SPDX-License-Identifier: GPL-3.0-or-later

// Offline fixed-image benchmark; no emulator settings or production runtime changes.
#include <algorithm>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <numeric>
#include <string_view>
#include <nlohmann/json.hpp>
#include <cstdio>
#include <fstream>
#include "numeric.h"
#include "video_core/neural_rendering/backend.h"
#include "video_core/neural_rendering/model.h"
#include "vk_context.h"

namespace NR = VideoCore::NeuralRendering;

struct Image {
    vk::Context& context;
    VkImage image{};
    VkImageView view{};
    VkDeviceMemory memory{};
    /// Allocate an RGBA16F image and view for the standalone inference test.
    Image(vk::Context& context_, uint32_t width, uint32_t height) : context(context_) {
        VkImageCreateInfo create{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        create.imageType = VK_IMAGE_TYPE_2D;
        create.format = VK_FORMAT_R16G16B16A16_SFLOAT;
        create.extent = {width, height, 1};
        create.mipLevels = create.arrayLayers = 1;
        create.samples = VK_SAMPLE_COUNT_1_BIT;
        create.tiling = VK_IMAGE_TILING_OPTIMAL;
        create.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
                       VK_IMAGE_USAGE_TRANSFER_DST_BIT;
        VK_CHECK(vkCreateImage(context.device(), &create, nullptr, &image));
        VkMemoryRequirements requirements;
        vkGetImageMemoryRequirements(context.device(), image, &requirements);
        VkPhysicalDeviceMemoryProperties properties;
        vkGetPhysicalDeviceMemoryProperties(context.physical(), &properties);
        uint32_t type = 0;
        while (type < properties.memoryTypeCount &&
               (!(requirements.memoryTypeBits & (1u << type)) ||
                !(properties.memoryTypes[type].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)))
            ++type;
        if (type == properties.memoryTypeCount)
            throw std::runtime_error("No device-local image memory type");
        VkMemoryAllocateInfo allocate{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        allocate.allocationSize = requirements.size;
        allocate.memoryTypeIndex = type;
        VK_CHECK(vkAllocateMemory(context.device(), &allocate, nullptr, &memory));
        VK_CHECK(vkBindImageMemory(context.device(), image, memory, 0));
        VkImageViewCreateInfo view_info{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        view_info.image = image;
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = create.format;
        view_info.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        VK_CHECK(vkCreateImageView(context.device(), &view_info, nullptr, &view));
        auto cmd = context.beginCommands();
        VkImageMemoryBarrier barrier{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        barrier.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        barrier.newLayout = VK_IMAGE_LAYOUT_GENERAL;
        barrier.dstAccessMask = VK_ACCESS_MEMORY_WRITE_BIT | VK_ACCESS_MEMORY_READ_BIT;
        barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        barrier.image = image;
        barrier.subresourceRange = view_info.subresourceRange;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                             VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, nullptr, 0, nullptr, 1,
                             &barrier);
        VkClearColorValue zero{};
        vkCmdClearColorImage(cmd, image, VK_IMAGE_LAYOUT_GENERAL, &zero, 1,
                             &view_info.subresourceRange);
        context.endAndSubmit(cmd, true);
    }
    ~Image() {
        vkDestroyImageView(context.device(), view, nullptr);
        vkDestroyImage(context.device(), image, nullptr);
        vkFreeMemory(context.device(), memory, nullptr);
    }
};

void Barrier(VkCommandBuffer cmd) {
    VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
    barrier.srcAccessMask = barrier.dstAccessMask =
        VK_ACCESS_MEMORY_WRITE_BIT | VK_ACCESS_MEMORY_READ_BIT;
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                         VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 1, &barrier, 0, nullptr, 0,
                         nullptr);
}

struct OwnedBuffer {
    vk::Context& context;
    vk::Buffer buffer;
    ~OwnedBuffer() { context.destroyBuffer(buffer); }
};

struct OwnedQueries {
    vk::Context& context;
    VkQueryPool pool;
    ~OwnedQueries() { vkDestroyQueryPool(context.device(), pool, nullptr); }
};

uint32_t ParseCount(std::string_view text, const char* name, uint32_t maximum) {
    uint32_t value{};
    const auto [end, error] = std::from_chars(text.data(), text.data() + text.size(), value);
    if (error != std::errc{} || end != text.data() + text.size() || !value || value > maximum)
        throw std::runtime_error(std::string(name) + " must be an integer in 1.." +
                                 std::to_string(maximum));
    return value;
}

std::vector<uint16_t> LoadFixture(const char* path, size_t components) {
    const size_t bytes = components * sizeof(float);
    if (std::filesystem::file_size(path) != bytes)
        throw std::runtime_error("RGBA32F file size does not match WIDTH * HEIGHT * 16");
    std::vector<float> floats(components);
    std::ifstream input(path, std::ios::binary);
    if (!input.read(reinterpret_cast<char*>(floats.data()), static_cast<std::streamsize>(bytes)))
        throw std::runtime_error("Fixture read failed");
    std::vector<uint16_t> pixels(components);
    for (size_t i = 0; i < components; ++i) {
        pixels[i] = num::f16Bits(floats[i]);
        if (!std::isfinite(floats[i]) || !std::isfinite(num::f16ToF32(pixels[i])))
            throw std::runtime_error("Input contains nonfinite or out-of-range half-float values");
    }
    return pixels;
}

nlohmann::json Statistics(std::vector<double> values) {
    if (values.empty())
        throw std::runtime_error("No timing samples");
    std::sort(values.begin(), values.end());
    const size_t middle = values.size() / 2;
    const double median = values.size() % 2 ? values[middle]
                                           : (values[middle - 1] + values[middle]) / 2.0;
    return {{"median", median}, {"min", values.front()}, {"max", values.back()}};
}

int main(int argc, char** argv) {
    if (argc != 7 && argc != 8) {
        std::fprintf(stderr,
            "neural_image_benchmark MODEL RGBA32F WIDTH HEIGHT OUTPUT_PREFIX PASSES [REPEATS=5]\n"
            "Natural 100%%; fresh history per pass; one warmup chain; local GPU processing only.\n");
        return 2;
    }
    try {
        const uint32_t width = ParseCount(argv[3], "WIDTH", 7680);
        const uint32_t height = ParseCount(argv[4], "HEIGHT", 4320);
        const uint32_t passes = ParseCount(argv[6], "PASSES", 8);
        const uint32_t repeats = argc == 8 ? ParseCount(argv[7], "REPEATS", 100) : 5;
        const std::string prefix = argv[5];
        const auto parent = std::filesystem::path(prefix).parent_path();
        if (prefix.empty() || (!parent.empty() && !std::filesystem::is_directory(parent)))
            throw std::runtime_error("OUTPUT_PREFIX must name a file in an existing directory");
        if (!NR::IsInstalled(argv[1]))
            throw std::runtime_error("Model validation failed");
        const size_t components = size_t{width} * height * 4;
        auto pixels = LoadFixture(argv[2], components);
        const VkDeviceSize bytes = components * sizeof(uint16_t);
        vk::Context context;
        Image color(context, width, height);
        Image motion(context, std::max(width / 2, 1u), std::max(height / 2, 1u));
        OwnedBuffer source{context, context.createBuffer(bytes, false, "original fixture")};
        context.upload(source.buffer, pixels.data(), bytes);
        std::vector<uint16_t>().swap(pixels);
        OwnedQueries queries{context, context.createTimestampPool(2)};
        VkBufferImageCopy copy{};
        copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        copy.imageExtent = {width, height, 1};
        std::vector<double> totals;
        std::vector<std::vector<double>> per_pass(passes);
        std::vector<std::vector<double>> chains;
        {
            // Reuse one model/workspace for all passes and chains. This is a fresh-history
            // still-image preview, not a design for sharing histories between live passes.
            NR::Backend backend(context.instance(), context.physical(), context.device(),
                                context.queueFamily(), argv[1], {width, height}, color.image,
                                color.view, motion.view);
            for (uint32_t chain = 0; chain <= repeats; ++chain) {
                auto upload = context.beginCommands();
                Barrier(upload);
                vkCmdCopyBufferToImage(upload, source.buffer.buffer, color.image,
                                       VK_IMAGE_LAYOUT_GENERAL, 1, &copy);
                Barrier(upload);
                context.endAndSubmit(upload, true);
                std::vector<double> durations;
                for (uint32_t pass = 0; pass < passes; ++pass) {
                    auto cmd = context.beginCommands();
                    Barrier(cmd);
                    vkCmdResetQueryPool(cmd, queries.pool, 0, 2);
                    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, queries.pool, 0);
                    NR::Frame frame;
                    frame.style = NR::Style::Natural;
                    frame.intensity = frame.tone = frame.structure = 1.0f;
                    frame.reset = true;
                    frame.motion_scale = {1, 1};
                    // Passes after the first consume the previous pass's color in place.
                    backend.Record(cmd, frame);
                    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, queries.pool, 1);
                    context.endAndSubmit(cmd, true);
                    if (backend.HadTimeout())
                        throw std::runtime_error("Kernel chain timed out");
                    const auto times = context.readTimestampsMs(queries.pool, 2);
                    const double duration = times[1] - times[0];
                    if (!std::isfinite(duration) || duration <= 0)
                        throw std::runtime_error("Invalid GPU timestamp duration");
                    durations.push_back(duration);
                }
                const double total = std::accumulate(durations.begin(), durations.end(), 0.0);
                std::fprintf(stderr, "%s chain %u/%u: %.3f ms GPU NR\n",
                             chain == 0 ? "Warmup" : "Measured", chain, repeats, total);
                if (chain != 0) {
                    totals.push_back(total);
                    chains.push_back(durations);
                    for (uint32_t pass = 0; pass < passes; ++pass)
                        per_pass[pass].push_back(durations[pass]);
                }
            }
            // Allocate readback only after measurement; save the last measured chain only.
            OwnedBuffer readback{context, context.createBuffer(bytes, true, "final image")};
            auto cmd = context.beginCommands();
            Barrier(cmd);
            vkCmdCopyImageToBuffer(cmd, color.image, VK_IMAGE_LAYOUT_GENERAL,
                                   readback.buffer.buffer, 1, &copy);
            VkMemoryBarrier host{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
            host.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
            host.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                                 0, 1, &host, 0, nullptr, 0, nullptr);
            context.endAndSubmit(cmd, true);
            const auto* data = static_cast<const uint16_t*>(readback.buffer.mapped);
            for (size_t i = 0; i < components; ++i)
                if (!std::isfinite(num::f16ToF32(data[i])))
                    throw std::runtime_error("Nonfinite final output");
            if (backend.HadTimeout() || vk::Context::validationErrors())
                throw std::runtime_error("Kernel timeout or Vulkan validation error");
            std::ofstream output(prefix + ".rgba16f", std::ios::binary);
            if (!output.write(reinterpret_cast<const char*>(data),
                              static_cast<std::streamsize>(bytes)) || !output.flush())
                throw std::runtime_error("Final image write failed");
        }
        if (vk::Context::validationErrors())
            throw std::runtime_error("Vulkan validation error during backend cleanup");
        nlohmann::json pass_statistics = nlohmann::json::array();
        for (uint32_t pass = 0; pass < passes; ++pass) {
            auto stats = Statistics(per_pass[pass]);
            stats["pass"] = pass + 1;
            pass_statistics.push_back(std::move(stats));
        }
        const nlohmann::json report{
            {"device", context.deviceName()}, {"width", width}, {"height", height},
            {"style", "Natural"}, {"strength_percent", 100}, {"tone_percent", 100},
            {"structure_percent", 100}, {"passes", passes}, {"repeats", repeats},
            {"warmup_chains", 1}, {"fresh_history_per_pass", true},
            {"gpu_chain_ms", Statistics(totals)}, {"gpu_per_pass_ms", pass_statistics},
            {"gpu_chain_samples_ms", totals}, {"gpu_pass_samples_ms", chains},
            {"output", prefix + ".rgba16f"},
            {"scope", "Offline fresh-history still-image NR preview. GPU timestamps include "
                      "NR preprocessing, inference, compositing and its output copy; exclude "
                      "model initialization, source uploads, CPU submission/waits, readback, "
                      "emulator rendering and presentation. Live multipass processing may need "
                      "separate per-pass temporal histories."},
        };
        std::ofstream metadata(prefix + ".json");
        if (!(metadata << report.dump(2) << '\n') || !metadata.flush())
            throw std::runtime_error("Timing JSON write failed");
        std::puts(report.dump(2).c_str());
        return 0;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}

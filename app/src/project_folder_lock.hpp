// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <algorithm>
#include <chrono>
#include <mutex>

namespace edi_app {

// The assistant's work report is written into the project's folder from a background thread. A save checks that the
// folder did not change meanwhile, so the two take turns (edi ADR-0069).
inline std::recursive_timed_mutex& project_folder_mutex() {
    static std::recursive_timed_mutex mutex;
    return mutex;
}

// A save waits for a report being written, for as long as `left` says, and takes what it waited off it: its retry and
// what follows its question wait for the rest. One stuck on a slow disk does not hold the window: the save goes on
// without the lock and finds the changed folder itself.
inline constexpr std::chrono::milliseconds folder_wait_per_save{1000};
inline std::unique_lock<std::recursive_timed_mutex> lock_project_folder_for_save(std::chrono::milliseconds& left) {
    const auto began = std::chrono::steady_clock::now();
    std::unique_lock held(project_folder_mutex(), left);
    const auto waited = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - began);
    left = std::max(std::chrono::milliseconds::zero(), left - waited);
    return held;
}

}  // namespace edi_app

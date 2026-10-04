#pragma once

#include <chrono>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <vector>

#include "../../fixtures/e04_t9/stress.hpp"

namespace e04_t9 {
inline std::vector<std::string> projects() {
    std::vector<std::string> paths;
    for (const auto& entry : std::filesystem::directory_iterator("docs/user/cli")) {
        const auto path = entry.path() / "project";
        if (std::filesystem::exists(path / "project.edi")) paths.push_back(path.string());
    }
    std::sort(paths.begin(), paths.end());
    return paths;
}
inline std::uint64_t clock_ns() {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}
// Test-owned FIFO. Condition variables force overlap; no sleeps or timing guesses.
class OwnerQueue {
    std::mutex mutex_;
    std::condition_variable ready_;
    std::deque<std::function<void()>> queue_;
   public:
    void post(std::function<void()> delivery) {
        std::lock_guard lock(mutex_);
        queue_.push_back(std::move(delivery));
        ready_.notify_one();
    }
    void one() {
        std::function<void()> delivery;
        {
            std::unique_lock lock(mutex_);
            if (!ready_.wait_for(lock, std::chrono::seconds(10), [&] { return !queue_.empty(); }))
                throw std::runtime_error(" I3 delivery failed to reach the owner queue");
            delivery = std::move(queue_.front());
            queue_.pop_front();
        }
        delivery();
    }
    void drain() {
        for (;;) {
            { std::lock_guard lock(mutex_); if (queue_.empty()) return; }
            one();
        }
    }
};
class Barrier {
    std::mutex mutex_;
    std::condition_variable condition_;
    bool entered_ = false, released_ = false;
   public:
    void block() {
        std::unique_lock lock(mutex_);
        entered_ = true;
        condition_.notify_all();
        if (!condition_.wait_for(lock, std::chrono::seconds(10), [&] { return released_; }))
            throw std::runtime_error(" controlled job was never released");
    }
    void entered() {
        std::unique_lock lock(mutex_);
        if (!condition_.wait_for(lock, std::chrono::seconds(10), [&] { return entered_; }))
            throw std::runtime_error(" controlled worker never entered");
    }
    void release() { std::lock_guard lock(mutex_); released_ = true; condition_.notify_all(); }
};
}  // namespace e04_t9

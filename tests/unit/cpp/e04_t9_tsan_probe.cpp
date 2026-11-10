#include <atomic>
#include <barrier>
#include <iostream>
#include <optional>
#include <thread>
#include "e04_t9_support.hpp"

#if __has_include("edi/calculation.hpp") && __has_include("edi/worker.hpp")
#include "edi/calculation.hpp"
#include "edi/worker.hpp"
#ifndef __has_feature
#define __has_feature(x) 0
#endif
int main() {
#if !defined(__SANITIZE_THREAD__) && !__has_feature(thread_sanitizer)
    std::cerr << " T1 refuses a probe without ThreadSanitizer instrumentation\n";
    return 1;
#else
    auto live = e04_t9_fixture::stress();
    live.calculate();
    auto snapshot = edi::snapshot_for_work(live);
    std::barrier rendezvous(2);
    std::atomic<bool> done{false};
    std::atomic<std::uint64_t> began{0}, ended{0};
    std::uint64_t owner_publication = 0;
    bool published_during_work = false;
    e04_t9::OwnerQueue queue;
    edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
    std::optional<edi::CalculationResult> result;
    worker.submit("tsan", [&](const auto& token, const auto& emit) {
        rendezvous.arrive_and_wait();
        began = e04_t9::clock_ns();
        auto first = edi::calculate(snapshot, token);
        emit([&, first=std::move(first)]() mutable {
            published_during_work = edi::publish(live,std::move(first)) == edi::PublishOutcome::Published;
            owner_publication = e04_t9::clock_ns();
        });
        for (int i = 0; i < 20; ++i) result.emplace(edi::calculate(snapshot, token));
        ended = e04_t9::clock_ns();
        done = true;
        return []{};
    });
    rendezvous.arrive_and_wait();
    const auto owner_begin = e04_t9::clock_ns();
    queue.one();  // real publication while subsequent worker calculations are still running
    int reads = 0;
    do {
        auto held = edi::snapshot_for_work(live);
        (void)held;
        (void)edi::project_edi_files(live);
        for (const auto& bank : live.experiments) (void)bank->computed_current();
        for (const auto& structure : live.structures) {
            (void)structure->geometry_current();
            (void)structure->current_geometry();
        }
        ++reads;
    } while (!done.load());
    const auto owner_end = e04_t9::clock_ns();
    queue.one();
    if (!published_during_work || owner_publication <= began.load() || owner_publication >= ended.load()) {
        std::cerr << " T1 requires owner publication inside the real worker calculation interval\n";
        return 1;
    }
    if (reads == 0 || std::max(owner_begin, began.load()) >= std::min(owner_end, ended.load())) {
        std::cerr << " T1 requires witnessed overlap of real calculations with owner reads\n";
        return 1;
    }
    if (!result || edi::publish(live, std::move(*result)) != edi::PublishOutcome::Published) {
        std::cerr << " T1 unchanged live state must accept the concurrent snapshot result\n";
        return 1;
    }
    std::cout << " T1 witnessed " << reads << " owner read/save/snapshot cycles; publication succeeded\n";
    return 0;
#endif
}
#else
int main() {
    std::cerr << " T1 transaction and worker are missing on red-first main\n";
    return 1;
}
#endif

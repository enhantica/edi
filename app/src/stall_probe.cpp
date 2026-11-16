// SPDX-License-Identifier: BSD-3-Clause
#include "stall_probe.hpp"

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QTimer>
#include <QtGlobal>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <thread>

#if defined(__linux__)
#include <dlfcn.h>
#include <execinfo.h>
#include <pthread.h>
#include <csignal>
#define EDI_STALL_STACKS 1
#endif

namespace edi_app {

namespace {
constexpr int kTickMs = 10;
constexpr qint64 kStallMs = 100;

#if defined(EDI_STALL_STACKS)
// Where the GUI thread was while it did not tick: a watchdog signals it during a stall and the handler keeps its
// stack in a ring the watchdog writes out (EDI_STALL_PROBE_STACKS names the file), one sample per 50 ms of stall.
constexpr int kFrames = 48;
constexpr int kSlots = 256;
struct Sample {
    std::atomic<int> ready{0};
    int count = 0;
    std::array<void*, kFrames> frames{};
};
std::array<Sample, kSlots> g_samples;
std::atomic<unsigned> g_next{0};
std::atomic<long long> g_heartbeat{0};
std::atomic<bool> g_quit{false};

long long now_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

void take_sample(int) {
    Sample& sample = g_samples[g_next.fetch_add(1) % kSlots];
    if (sample.ready.load() != 0) return;  // the writer has not caught up: drop this one
    sample.count = backtrace(sample.frames.data(), kFrames);
    sample.ready.store(1);
}

void write_samples(std::FILE* out, unsigned& read) {
    while (read != g_next.load()) {
        Sample& sample = g_samples[read % kSlots];
        if (sample.ready.load() == 0) break;
        std::fprintf(out, "sample %lld\n", static_cast<long long>(now_ms()));
        for (int i = 0; i < sample.count; ++i) {
            Dl_info info{};
            if (dladdr(sample.frames[static_cast<std::size_t>(i)], &info) != 0 && info.dli_fname != nullptr) {
                const auto offset = reinterpret_cast<std::uintptr_t>(sample.frames[static_cast<std::size_t>(i)]) -
                                    reinterpret_cast<std::uintptr_t>(info.dli_fbase);
                std::fprintf(out, "  %s 0x%zx\n", info.dli_fname, static_cast<std::size_t>(offset));
            }
        }
        sample.ready.store(0);
        ++read;
    }
    std::fflush(out);
}

void install_stacks(QCoreApplication& app) {
    const QByteArray path = qgetenv("EDI_STALL_PROBE_STACKS");
    if (path.isEmpty()) return;
    std::FILE* out = std::fopen(path.constData(), "w");
    if (out == nullptr) {
        qWarning("stall-probe: cannot write %s", path.constData());
        return;
    }
    void* warm[1];
    backtrace(warm, 1);  // loads the unwinder before any signal needs it
    struct sigaction action {};
    action.sa_handler = take_sample;
    action.sa_flags = SA_RESTART;
    sigemptyset(&action.sa_mask);
    sigaction(SIGPROF, &action, nullptr);
    const pthread_t gui = pthread_self();
    g_heartbeat.store(now_ms());
    auto* watchdog = new std::thread([gui, out] {
        unsigned read = 0;
        long long last = 0;
        while (!g_quit.load()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            const long long now = now_ms();
            if (now - g_heartbeat.load() > kStallMs && now - last >= 50) {
                last = now;
                pthread_kill(gui, SIGPROF);
            }
            write_samples(out, read);
        }
        write_samples(out, read);
        std::fclose(out);
    });
    QObject::connect(&app, &QCoreApplication::aboutToQuit, &app, [watchdog] {
        g_quit.store(true);
        watchdog->join();
        delete watchdog;
    });
}
#endif
}  // namespace

void install_stall_probe(QCoreApplication& app) {
    if (!qEnvironmentVariableIsSet("EDI_STALL_PROBE")) {
        return;
    }
    auto* timer = new QTimer(&app);
    auto* clock = new QElapsedTimer;
    auto* longest = new qint64(0);
    auto* stalls = new qint64(0);
    auto* ticks = new qint64(0);
    clock->start();
    QObject::connect(timer, &QTimer::timeout, &app, [clock, longest, stalls, ticks] {
        const qint64 gap = clock->restart();
#if defined(EDI_STALL_STACKS)
        g_heartbeat.store(now_ms());
#endif
        ++*ticks;
        *longest = std::max(*longest, gap);
        if (gap > kStallMs) {
            ++*stalls;
            qWarning("stall-probe: gap %lld ms", static_cast<long long>(gap));
        }
    });
    QObject::connect(&app, &QCoreApplication::aboutToQuit, &app, [clock, longest, stalls, ticks] {
        qWarning("stall-probe: %lld gaps over %lld ms, longest %lld ms, %lld ticks", static_cast<long long>(*stalls),
                 static_cast<long long>(kStallMs), static_cast<long long>(*longest), static_cast<long long>(*ticks));
        delete clock;
        delete longest;
        delete stalls;
        delete ticks;
    });
    timer->start(kTickMs);
#if defined(EDI_STALL_STACKS)
    install_stacks(app);
#endif
    qInfo("stall-probe: on, a gap over %lld ms is noted", static_cast<long long>(kStallMs));
}

}  // namespace edi_app

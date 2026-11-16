// SPDX-License-Identifier: BSD-3-Clause
#include "stall_probe.hpp"

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QTimer>
#include <QtGlobal>
#include <algorithm>

namespace edi_app {

namespace {
constexpr int kTickMs = 10;
constexpr qint64 kStallMs = 100;
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
        ++*ticks;
        *longest = std::max(*longest, gap);
        if (gap > kStallMs) {
            ++*stalls;
            qInfo("stall-probe: gap %lld ms", static_cast<long long>(gap));
        }
    });
    QObject::connect(&app, &QCoreApplication::aboutToQuit, &app, [clock, longest, stalls, ticks] {
        qInfo("stall-probe: %lld gaps over %lld ms, longest %lld ms, %lld ticks", static_cast<long long>(*stalls),
              static_cast<long long>(kStallMs), static_cast<long long>(*longest), static_cast<long long>(*ticks));
        delete clock;
        delete longest;
        delete stalls;
        delete ticks;
    });
    timer->start(kTickMs);
    qInfo("stall-probe: on, a gap over %lld ms is noted", static_cast<long long>(kStallMs));
}

}  // namespace edi_app

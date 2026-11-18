// SPDX-License-Identifier: BSD-3-Clause
#include "ui_probe.hpp"

#include <QCoreApplication>
#include <QJsonDocument>
#include <QString>
#include <QThread>
#include <QTimer>
#include <chrono>
#include <cstdio>

namespace edi_app {

namespace {
constexpr int kTickMs = 10;
bool g_on = false;
}  // namespace

bool ui_trace_on() { return g_on; }

qint64 ui_trace_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

QString ui_trace_thread() {
    return QStringLiteral("0x%1").arg(reinterpret_cast<quintptr>(QThread::currentThreadId()), 0, 16);
}

void ui_trace(const char* event, QJsonObject fields) {
    if (!g_on) {
        return;
    }
    fields.insert(QStringLiteral("event"), QString::fromLatin1(event));
    fields.insert(QStringLiteral("t_ms"), static_cast<double>(ui_trace_ms()));
    const QByteArray line = QJsonDocument(fields).toJson(QJsonDocument::Compact);
    // One write per line, flushed, so lines from other threads never interleave inside one and a crash keeps them.
    std::fprintf(stdout, "ui-probe: %s\n", line.constData());
    std::fflush(stdout);
}

void install_ui_probe(QCoreApplication& app) {
    if (qEnvironmentVariable("EDI_UI_TRACE") != QLatin1String("1")) {
        return;
    }
    g_on = true;
    ui_trace("clock", {{"clock", "monotonic"}, {"unit", "ms"}, {"tick_ms", kTickMs}, {"gui_thread", ui_trace_thread()}});
    auto* timer = new QTimer(&app);
    timer->setTimerType(Qt::PreciseTimer);
    QObject::connect(timer, &QTimer::timeout, &app, [] { ui_trace("tick"); });
    timer->start(kTickMs);
}

}  // namespace edi_app

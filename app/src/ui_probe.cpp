// SPDX-License-Identifier: BSD-3-Clause
#include "ui_probe.hpp"

#if EDI_UI_INSTRUMENTATION
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QJsonDocument>
#include <QThread>
#include <QTimer>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <mutex>

namespace edi_app {

namespace {
constexpr int kTickMs = 10;
std::atomic<bool> g_on{false};
std::atomic<qint64> g_frames{0};
std::mutex g_write;

void write_locked(const char* event, QJsonObject& fields, double now, const QString& thread) {
    fields.insert(QStringLiteral("event"), QString::fromLatin1(event));
    fields.insert(QStringLiteral("t_ms"), now);
    fields.insert(QStringLiteral("thread"), thread);
    const QByteArray line = QJsonDocument(fields).toJson(QJsonDocument::Compact);
    // Flushed per line, so a crash keeps every line written before it.
    std::fprintf(stdout, "ui-probe: %s\n", line.constData());
    std::fflush(stdout);
}
}  // namespace

bool ui_trace_on() { return g_on.load(std::memory_order_relaxed); }

double ui_trace_ms() {
    const auto us =
        std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    return static_cast<double>(us) / 1000.0;
}

QString ui_trace_thread() {
    return QStringLiteral("0x%1").arg(reinterpret_cast<quintptr>(QThread::currentThreadId()), 0, 16);
}

void ui_trace(const char* event, QJsonObject fields) {
    if (!ui_trace_on()) {
        return;
    }
    const QString thread = ui_trace_thread();
    const std::lock_guard lock(g_write);
    write_locked(event, fields, ui_trace_ms(), thread);
}

void ui_trace_group(const std::vector<std::pair<const char*, QJsonObject>>& events) {
    if (!ui_trace_on()) {
        return;
    }
    const QString thread = ui_trace_thread();
    const std::lock_guard lock(g_write);
    const double now = ui_trace_ms();
    for (const auto& [event, given] : events) {
        QJsonObject fields = given;
        write_locked(event, fields, now, thread);
    }
}

QString ui_trace_identity(const std::vector<double>* column) {
    if (column == nullptr) return {};
    QCryptographicHash hash(QCryptographicHash::Sha256);
    hash.addData(QByteArrayView(reinterpret_cast<const char*>(column->data()),
                                static_cast<qsizetype>(column->size()) * static_cast<qsizetype>(sizeof(double))));
    return QString::fromLatin1(hash.result().toHex().left(16));
}

qint64 ui_trace_next_frame() { return g_frames.load() + 1; }

qint64 ui_trace_frame_synced() { return g_frames.fetch_add(1) + 1; }

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
#endif

// SPDX-License-Identifier: BSD-3-Clause
// The measured-layer benchmark (edi ADR-0017 §15): which of two ways draws the measured markers and their
// error bars. Candidate A is Qt Graphs' own series — a ScatterSeries and a NaN-separated LineSeries;
// candidate B is edi's MeasuredLayer, one scene-graph item. For the stress dataset's measured series,
// decimated to 400, 1 200 and 2 400 pixel columns, it times the first population and 200 replacements that
// alternate two point sets, each from the replacement call to the swap of the first frame whose scene
// synchronisation saw the new set; then it grabs the last frame and checks that the highest point is drawn
// where the axes put it. It prints one table. Test tooling, never part of the host.
#include <QColor>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QGuiApplication>
#include <QImage>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickView>
#include <QTimer>
#include <QtGraphs/QValueAxis>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqmlextensionplugin.h>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <vector>

#include "e04_t9/stress.hpp"
#include "edi/presentation.hpp"
#include "engine_setup.hpp"
#include "measured_layer.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {

constexpr int kReplacements = 200;
constexpr int kTimeoutMs = 5000;

// One decimated measured series, as both candidates take it.
struct PointSet {
    QList<QPointF> markers;
    QList<double> low, high;
    QList<QPointF> bars;  // candidate A: (x, low), (x, high), a gap
    double x_min = 0.0, x_max = 1.0, y_min = 0.0, y_max = 1.0;
};

PointSet point_set(const edi::PatternSource& source, double x_min, double x_max, int columns) {
    edi::PatternView view;
    view.x_min = x_min;
    view.x_max = x_max;
    view.columns = columns;
    const edi::PatternPresentation shown = edi::present_pattern(source, view);
    PointSet set;
    set.x_min = x_min;
    set.x_max = x_max;
    set.y_min = shown.y_main.min;
    set.y_max = shown.y_main.max;
    for (const edi::PatternSeries& series : shown.series) {
        if (series.kind != edi::SeriesKind::Measured) {
            continue;
        }
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            if (std::isnan(series.points[i].y)) {
                continue;
            }
            const double x = series.points[i].x;
            set.markers.append(QPointF(x, series.points[i].y));
            set.low.append(series.bar_low[i]);
            set.high.append(series.bar_high[i]);
            set.bars.append(QPointF(x, series.bar_low[i]));
            set.bars.append(QPointF(x, series.bar_high[i]));
            set.bars.append(QPointF(std::nan(""), std::nan("")));
        }
    }
    return set;
}

struct Result {
    double first_ms = 0.0, median_ms = 0.0, p95_ms = 0.0;
    int points = 0;
    bool drawn = false, timed_out = false;
};

Result run(const char* candidate, const PointSet sets[2], int columns) {
    Result result;
    QQuickView view;
    edi_app::configure_engine(*view.engine());
    view.setResizeMode(QQuickView::SizeRootObjectToView);
    view.setInitialProperties({{QStringLiteral("candidate"), QString::fromLatin1(candidate)}});
    view.setSource(QUrl(QStringLiteral("qrc:/edi/bench/ChartBench.qml")));
    view.resize(columns + 200, 600);
    view.show();
    QQuickItem* root = view.rootObject();
    auto* graphs = root->findChild<QQuickItem*>(QStringLiteral("view"));
    auto* markers = root->findChild<QXYSeries*>(QStringLiteral("markers"));
    auto* bars = root->findChild<QXYSeries*>(QStringLiteral("bars"));
    auto* layer = root->findChild<edi_app::MeasuredLayer*>(QStringLiteral("layer"));
    auto* axis_x = root->findChild<QValueAxis*>(QStringLiteral("axisX"));
    auto* axis_y = root->findChild<QValueAxis*>(QStringLiteral("axisY"));
    QCoreApplication::processEvents();
    // The plot area as wide as the columns asked for (the device pixel ratio is the window's).
    for (int attempt = 0; attempt < 4; ++attempt) {
        const double plot = graphs->property("plotArea").toRectF().width() * view.devicePixelRatio();
        view.resize(view.width() + static_cast<int>(std::lround((columns - plot) / view.devicePixelRatio())),
                    view.height());
        QCoreApplication::processEvents();
    }
    const bool is_a = candidate[0] == 'a';

    // What the last scene synchronisation saw: the number of points and the first one's x.
    std::atomic<qsizetype> synced_count{-1};
    std::atomic<double> synced_first{0.0};
    std::atomic<bool> completed{false};
    std::atomic<qsizetype> wanted_count{-2};
    std::atomic<double> wanted_first{0.0};
    QEventLoop loop;
    QObject::connect(
        &view, &QQuickWindow::afterSynchronizing, &view,
        [&] {
            const QList<QPointF>& points = is_a ? markers->points() : layer->points();
            synced_count = points.size();
            synced_first = points.isEmpty() ? 0.0 : points.first().x();
        },
        Qt::DirectConnection);
    QElapsedTimer clock;
    std::atomic<qint64> swapped_ns{0};
    QObject::connect(
        &view, &QQuickWindow::frameSwapped, &view,
        [&] {
            if (!completed && synced_count == wanted_count && synced_first == wanted_first) {
                swapped_ns = clock.nsecsElapsed();
                completed = true;
                QMetaObject::invokeMethod(&loop, &QEventLoop::quit, Qt::QueuedConnection);
            }
        },
        Qt::DirectConnection);

    const auto replace = [&](const PointSet& set) -> double {
        wanted_count = set.markers.size();
        wanted_first = set.markers.isEmpty() ? 0.0 : set.markers.first().x();
        completed = false;
        QTimer guard;
        guard.setSingleShot(true);
        QObject::connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
        guard.start(kTimeoutMs);
        clock.start();
        axis_x->setRange(set.x_min, set.x_max);
        axis_y->setRange(set.y_min, set.y_max);
        if (is_a) {
            markers->replace(set.markers);
            bars->replace(set.bars);
        } else {
            layer->setData(set.markers, set.low, set.high);
        }
        loop.exec();
        if (!completed) {
            result.timed_out = true;
            return static_cast<double>(kTimeoutMs);
        }
        return static_cast<double>(swapped_ns.load()) / 1e6;
    };

    result.first_ms = replace(sets[0]);
    std::vector<double> times;
    for (int i = 0; i < kReplacements && !result.timed_out; ++i) {
        times.push_back(replace(sets[(i + 1) % 2]));
    }
    if (!times.empty()) {
        std::sort(times.begin(), times.end());
        result.median_ms = times[times.size() / 2];
        result.p95_ms = times[static_cast<std::size_t>(0.95 * static_cast<double>(times.size() - 1))];
    }
    // The last frame, grabbed: the highest point of the set shown is drawn where the axes put it.
    const PointSet& last = sets[kReplacements % 2];
    result.points = static_cast<int>(last.markers.size());
    const QImage frame = view.grabWindow();
    const QRectF plot = graphs->property("plotArea").toRectF();
    const QPointF origin = graphs->mapToScene(plot.topLeft());
    const auto highest = std::max_element(last.markers.begin(), last.markers.end(),
                                          [](const QPointF& a, const QPointF& b) { return a.y() < b.y(); });
    if (highest != last.markers.end()) {
        const double dpr = frame.devicePixelRatio();
        const double px = (origin.x() + (highest->x() - last.x_min) / (last.x_max - last.x_min) * plot.width()) * dpr;
        const double py = (origin.y() + (last.y_max - highest->y()) / (last.y_max - last.y_min) * plot.height()) * dpr;
        const QColor mark(QStringLiteral("#03A9F4"));
        for (int dx = -3; dx <= 3 && !result.drawn; ++dx) {
            for (int dy = -3; dy <= 3 && !result.drawn; ++dy) {
                const QPoint at(static_cast<int>(std::lround(px)) + dx, static_cast<int>(std::lround(py)) + dy);
                if (frame.rect().contains(at)) {
                    const QColor seen = frame.pixelColor(at);
                    result.drawn = std::abs(seen.red() - mark.red()) < 40 && std::abs(seen.green() - mark.green()) < 40 &&
                                   std::abs(seen.blue() - mark.blue()) < 40;
                }
            }
        }
    }
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    if (qEnvironmentVariableIsEmpty("QT_QPA_PLATFORM")) {
        qputenv("QT_QPA_PLATFORM", "offscreen");
    }
    QGuiApplication app(argc, argv);
    edi_app::use_design_font();
    const QString root = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QStringLiteral(".");
    edi::Project project = e04_t9_fixture::stress(root.toStdString());
    const edi::PatternSource source = edi::capture_pattern(project, 0);
    const double lo = source.x->front(), hi = source.x->back();
    std::printf("candidate\tcolumns\tpoints\tfirst_population_ms\treplace_median_ms\treplace_p95_ms\tdrawn\tplatform\n");
    int failures = 0;
    for (const int columns : {400, 1200, 2400}) {
        // Two point sets that differ: the full range, and the range without its first and last percent.
        const PointSet sets[2] = {point_set(source, lo, hi, columns),
                                  point_set(source, lo + 0.01 * (hi - lo), hi - 0.01 * (hi - lo), columns)};
        for (const char* candidate : {"a", "b"}) {
            const Result r = run(candidate, sets, columns);
            std::printf("%s\t%d\t%d\t%.2f\t%.2f\t%.2f\t%s\t%s\n", candidate, columns, r.points, r.first_ms, r.median_ms,
                        r.p95_ms, r.timed_out ? "timed-out" : r.drawn ? "yes" : "NO",
                        qPrintable(QGuiApplication::platformName()));
            failures += r.timed_out ? 1 : 0;
        }
    }
    return failures == 0 ? 0 : 1;
}

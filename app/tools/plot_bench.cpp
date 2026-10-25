// SPDX-License-Identifier: BSD-3-Clause
// The plotting benchmark (edi ADR-0041): every way this Qt Graphs version can be fed, and edi's own ScanLines item
// and a QPainter item as references, timed on the two charts that draw the most. "stacked-N" is N line patterns, the
// 324-file scan's patterns repeated (324, 1000, 3000), each reduced at the plot's pixel columns as the Stacked view
// reduces them; "pattern" is the LATP synchrotron pattern calculated with its three structures and two more (the
// first two at half their intensity), as the Pattern chart shows it in band mode: the measured band, a filled profile
// per structure, the total and the background, the residual band and the reflection ticks.
//
// Each cell, a feeding route on a workload in a window of its own, times from the change to the swap of the first
// frame synchronised after it: the first draw; a data update as a fit makes one (every curve replaced); a zoom (the
// middle half of x, every curve fed again for it, as the charts present a zoomed range); and a restyle (every curve's
// colour). A cell stops a measure after kRepeats changes, after kBudgetMs of them, or after kMaxMisses changes in a row
// draw no frame. It logs every change on stderr, prints one table on stdout and writes it as a TSV named after the
// machine and its renderer. Test tooling, never part of the host.
//
//   edi_app_plot_bench [--out <file.tsv>] [--only <method>] [--workloads <name,...>]
#include <QAbstractTableModel>
#include <QColor>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QGuiApplication>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <QPainter>
#include <QPainterPath>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickPaintedItem>
#include <QQuickView>
#include <QRegularExpression>
#include <QSGRendererInterface>
#include <QSysInfo>
#include <QTimer>
#include <QtGraphs/QAbstractSeries>
#include <QtGraphs/QValueAxis>
#include <QtGraphs/QXYModelMapper>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqmlextensionplugin.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/presentation.hpp"
#include "edi/scan.hpp"
#include "edi/scan_views.hpp"
#include "engine_setup.hpp"
#include "scan_lines.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {

constexpr int kRepeats = 10;
constexpr qint64 kBudgetMs = 20000;
constexpr int kFirstTimeoutMs = 60000;
constexpr int kVisibleTimeoutMs = 2000;
constexpr int kMinChangeTimeoutMs = 1000;
constexpr int kMaxMisses = 3;
constexpr const char* kScan = "docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project/experiments/d20_scan";
constexpr const char* kPattern = "docs/user/cli/pd-xray-cwl_latp_scan-4f/project";

void log(const char* format, ...) {
    std::va_list args;
    va_start(args, format);
    std::fputs("plot_bench: ", stderr);
    std::vfprintf(stderr, format, args);
    std::fputc('\n', stderr);
    std::fflush(stderr);
    va_end(args);
}

// One curve: a line's points, or an area's upper and lower lines.
struct Curve {
    QList<QPointF> upper, lower;
    bool area = false;
};

// What one change shows: every curve, and for the line references each trace and where it is drawn.
struct Shown {
    std::vector<Curve> curves;
    double x_min = 0.0, x_max = 1.0, y_min = 0.0, y_max = 1.0;
    std::vector<edi_app::ScanLines::Trace> traces;
    std::vector<edi_app::ScanLines::Style> styles;
};

// A workload's three states: the data, the data as a fit changes it, and the data zoomed to the middle half of x.
struct Workload {
    std::string name;
    Shown data, updated, zoomed;
    bool lines = false;  // only lines: the ScanLines and QPainter references draw it too
    std::size_t points = 0;
};

QColor colour_of(std::size_t i, std::size_t count, float saturation) {
    return QColor::fromHsvF(static_cast<float>(i) / static_cast<float>(std::max<std::size_t>(count, 1)), saturation,
                            0.7F);
}

// ---------------------------------------------------------------------------------------------------- the workloads

struct Scan {
    std::vector<std::vector<double>> x, intensity;
    double lo = INFINITY, hi = -INFINITY, low = INFINITY, high = -INFINITY;
};

Scan read_scan(const QString& directory) {
    Scan scan;
    for (const QString& file : QDir(directory).entryList({QStringLiteral("*.dat")}, QDir::Files, QDir::Name)) {
        const edi::PdDataBase data =
            edi::read_scan_dataset(directory.toStdString(), file.toStdString(), edi::BeamModeEnum::CONSTANT_WAVELENGTH);
        std::vector<double> x = data.axis(), y = data.intensity_meas.get();
        y.resize(x.size(), std::nan(""));
        for (std::size_t i = 0; i < x.size(); ++i) {
            if (std::isfinite(x[i]) && std::isfinite(y[i])) {
                scan.lo = std::min(scan.lo, x[i]);
                scan.hi = std::max(scan.hi, x[i]);
                scan.low = std::min(scan.low, y[i]);
                scan.high = std::max(scan.high, y[i]);
            }
        }
        scan.x.push_back(std::move(x));
        scan.intensity.push_back(std::move(y));
    }
    return scan;
}

// `count` patterns, the scan's repeated, each reduced at `columns` over [x_min, x_max] and raised to its row, as the
// Stacked view draws them; `factor` scales every intensity (a data update).
Shown stacked(const Scan& scan, std::size_t count, int columns, double width_px, double x_min, double x_max,
              double factor) {
    constexpr double kLift = 8.0;
    Shown shown;
    shown.x_min = x_min;
    shown.x_max = x_max;
    shown.y_min = -1.0;
    shown.y_max = static_cast<double>(count) + kLift;
    const double span = scan.high - scan.low;
    for (std::size_t d = 0; d < count; ++d) {
        const std::size_t source = d % scan.x.size();
        std::vector<double> y = scan.intensity[source];
        for (double& value : y) {
            value = scan.low + (value - scan.low) * factor;
        }
        const edi::ScanTrace trace =
            edi::scan_trace(scan.x[source], y, x_min, x_max, static_cast<std::size_t>(columns));
        Curve curve;
        edi_app::ScanLines::Trace lines;
        const double row = static_cast<double>(d);
        // Each column's lowest value, then its highest when it differs.
        const auto add = [&](double x, float value) {
            const double v = (value - scan.low) / span;
            curve.upper.append(QPointF(x, row + v * kLift));
            lines.x.push_back(static_cast<float>((x - x_min) / (x_max - x_min) * width_px));
            lines.v.push_back(static_cast<float>(v));
        };
        for (std::size_t k = 0; k < trace.x.size(); ++k) {
            add(trace.x[k], trace.low[k]);
            if (trace.high[k] != trace.low[k]) {
                add(trace.x[k], trace.high[k]);
            }
        }
        shown.curves.push_back(std::move(curve));
        shown.traces.push_back(std::move(lines));
        shown.styles.push_back({row, kLift, colour_of(d, count, 0.8F)});
    }
    return shown;
}

// The calculated LATP pattern with five structures: its own three and the first two again at half their intensity.
// `factor` scales every calculated column (a fit's update).
edi::PatternSource pattern_source(const edi::PatternSource& captured, double factor) {
    edi::PatternSource source = captured;
    const auto scaled = [factor](const edi::PatternSource::Column& column, double by) -> edi::PatternSource::Column {
        if (!column) {
            return column;
        }
        auto out = std::make_shared<std::vector<double>>(*column);
        for (double& value : *out) {
            value *= by;
        }
        return out;
    };
    source.calc = scaled(captured.calc, factor);
    source.resid = scaled(captured.resid, factor);
    for (std::size_t i = 0; i < captured.components.size(); ++i) {
        source.components[i].net = scaled(captured.components[i].net, factor);
    }
    for (std::size_t i = 0; i < 2 && i < captured.components.size(); ++i) {
        edi::PatternSource::Component extra = captured.components[i];
        extra.structure_id += "-half";
        extra.place = source.components.size();
        extra.net = scaled(captured.components[i].net, 0.5 * factor);
        source.components.push_back(std::move(extra));
    }
    for (std::size_t i = 0; i < 2 && i < captured.phases.size(); ++i) {
        edi::PatternSource::Phase extra = captured.phases[i];
        extra.structure_id += "-half";
        extra.place = source.phases.size();
        auto moved = std::make_shared<std::vector<double>>(*captured.phases[i].position);
        for (double& position : *moved) {
            position *= 1.003;
        }
        extra.position = moved;
        source.phases.push_back(std::move(extra));
    }
    return source;
}

// The presentation as curves on one plot: the main pane above the residual pane above the reflection ticks, each
// pane mapped into its own share of the height.
Shown pattern_shown(const edi::PatternSource& source, int columns, std::optional<double> x_min,
                    std::optional<double> x_max) {
    edi::PatternView view;
    view.columns = columns;
    view.x_min = x_min;
    view.x_max = x_max;
    view.structure_curves = true;
    view.residual_band = true;
    const edi::PatternPresentation shown = edi::present_pattern(source, view);
    // Each pane's range, from what it presents.
    std::array<std::pair<double, double>, 3> range{};
    range.fill({INFINITY, -INFINITY});
    for (const edi::PatternSeries& series : shown.series) {
        auto& [lo, hi] = range[static_cast<std::size_t>(series.pane)];
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            for (const double y : {series.points[i].y, i < series.bar_low.size() ? series.bar_low[i] : NAN,
                                   i < series.bar_high.size() ? series.bar_high[i] : NAN}) {
                if (std::isfinite(y)) {
                    lo = std::min(lo, y);
                    hi = std::max(hi, y);
                }
            }
        }
    }
    // Main [0.4, 1], residual [0.15, 0.35], ticks [0, 0.1].
    const std::array<std::pair<double, double>, 3> band{{{0.4, 1.0}, {0.0, 0.1}, {0.15, 0.35}}};
    const auto place = [&](edi::Pane pane, double y) {
        const auto& [lo, hi] = range[static_cast<std::size_t>(pane)];
        const auto& [bottom, top] = band[static_cast<std::size_t>(pane)];
        return hi > lo ? bottom + (y - lo) / (hi - lo) * (top - bottom) : bottom;
    };
    Shown out;
    out.x_min = shown.x.min;
    out.x_max = shown.x.max;
    out.y_min = 0.0;
    out.y_max = 1.0;
    for (const edi::PatternSeries& series : shown.series) {
        Curve curve;
        // The measured pattern in band mode, each structure's filled profile, the residual band: areas.
        const bool band_low = series.bar_low.size() == series.points.size();
        curve.area = (series.kind == edi::SeriesKind::Measured || series.kind == edi::SeriesKind::StructureCurve ||
                      series.kind == edi::SeriesKind::Residual) &&
                     band_low;
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            const double x = series.points[i].x;
            if (!curve.area) {
                curve.upper.append(QPointF(x, place(series.pane, series.points[i].y)));
                continue;
            }
            const double top = series.kind == edi::SeriesKind::StructureCurve ? series.points[i].y : series.bar_high[i];
            curve.upper.append(QPointF(x, place(series.pane, top)));
            curve.lower.append(QPointF(x, place(series.pane, series.bar_low[i])));
        }
        out.curves.push_back(std::move(curve));
    }
    return out;
}

// --------------------------------------------------------------------------------------------------- the routes

// A table of points for QXYModelMapper: x in column 0, y in column 1.
class PointsModel : public QAbstractTableModel {
   public:
    using QAbstractTableModel::QAbstractTableModel;
    int rowCount(const QModelIndex& parent) const override {
        return parent.isValid() ? 0 : static_cast<int>(points_.size());
    }
    int columnCount(const QModelIndex& parent) const override { return parent.isValid() ? 0 : 2; }
    QVariant data(const QModelIndex& index, int role) const override {
        if (role != Qt::DisplayRole || !index.isValid()) {
            return {};
        }
        const QPointF& point = points_[index.row()];
        return index.column() == 0 ? point.x() : point.y();
    }
    void setPoints(const QList<QPointF>& points) {
        if (points.size() == points_.size() && !points_.isEmpty()) {
            points_ = points;
            emit dataChanged(index(0, 0), index(static_cast<int>(points_.size()) - 1, 1));
            return;
        }
        beginResetModel();
        points_ = points;
        endResetModel();
    }

   private:
    QList<QPointF> points_;
};

// Candidate p's item: every line stroked with QPainter into the item's image on each change, 1 px antialiased, as
// ScanLayer draws the Stacked view.
class Painted : public QQuickPaintedItem {
   public:
    explicit Painted(QQuickItem* parent) : QQuickPaintedItem(parent) { setAntialiasing(true); }
    std::vector<edi_app::ScanLines::Trace> traces;
    std::vector<edi_app::ScanLines::Style> styles;
    double y_min = 0.0, y_max = 1.0, width_px = 1.0;
    void paint(QPainter* painter) override {
        const double h = height(), span = y_max - y_min;
        for (std::size_t d = 0; d < traces.size() && d < styles.size(); ++d) {
            const double base = (y_max - styles[d].row) / span * h, lift = styles[d].lift / span * h;
            QPainterPath path;
            bool drawing = false;
            for (std::size_t k = 0; k < traces[d].x.size(); ++k) {
                const double x = traces[d].x[k], y = base - traces[d].v[k] * lift;
                if (!std::isfinite(x) || !std::isfinite(y)) {
                    drawing = false;
                } else if (drawing) {
                    path.lineTo(x, y);
                } else {
                    path.moveTo(x, y);
                    drawing = true;
                }
            }
            QPen pen(styles[d].colour);
            pen.setWidthF(width_px);
            pen.setCosmetic(true);
            pen.setCapStyle(Qt::FlatCap);
            painter->setPen(pen);
            painter->drawPath(path);
        }
    }
};

struct Method {
    const char* name;
    const char* what;
    bool qt_graphs;
};

const std::vector<Method>& methods() {
    static const std::vector<Method> all = {
        {"cpp-replace", "QXYSeries::replace(QList<QPointF>) from C++, one call per series", true},
        {"cpp-append-list", "clear() and append(QList<QPointF>) from C++", true},
        {"cpp-append-point", "clear() and append(QPointF) per point from C++", true},
        {"cpp-replace-index", "replace(index, QPointF) per point from C++ where the count holds, else replace(list)",
         true},
        {"model-mapper", "QXYModelMapper over a C++ table model; dataChanged, or a reset when the count changes", true},
        {"qml-replace", "the points handed to a QML function that calls series.replace(points)", true},
        {"qml-append", "the points handed to a QML function that appends them one by one", true},
        {"scanlines", "edi's ScanLines item, quads drawn by a shader (lines only)", false},
        {"painter", "a QQuickPaintedItem stroking every line with QPainter, 1 px (lines only)", false},
    };
    return all;
}

// --------------------------------------------------------------------------------------------------- the timing

// The milliseconds from `change` to the swap of the first frame synchronised after it, or -1 after `timeout_ms`.
double frame_after(QQuickWindow& window, const std::function<void()>& change, int timeout_ms) {
    std::atomic<bool> synced{false};
    std::atomic<qint64> swapped{-1};
    QElapsedTimer clock;
    QEventLoop loop;
    const auto sync = QObject::connect(&window, &QQuickWindow::afterSynchronizing, &window, [&] { synced = true; },
                                       Qt::DirectConnection);
    const auto swap = QObject::connect(
        &window, &QQuickWindow::frameSwapped, &window,
        [&] {
            if (synced && swapped < 0) {
                swapped = clock.nsecsElapsed();
                QMetaObject::invokeMethod(&loop, &QEventLoop::quit, Qt::QueuedConnection);
            }
        },
        Qt::DirectConnection);
    QTimer guard;
    guard.setSingleShot(true);
    QObject::connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
    guard.start(timeout_ms);
    clock.start();
    change();
    loop.exec();
    QObject::disconnect(sync);
    QObject::disconnect(swap);
    return swapped < 0 ? -1.0 : static_cast<double>(swapped.load()) / 1e6;
}

void idle(int ms) {
    QElapsedTimer t;
    t.start();
    while (t.elapsed() < ms) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 5);
    }
}

struct Row {
    std::string method, workload, measure, status;
    int n = 0;
    double median = -1.0, p95 = -1.0;
};

Row summarise(const std::string& method, const std::string& workload, const std::string& measure,
              std::vector<double> samples, const std::string& status) {
    Row row{method, workload, measure, status};
    std::erase_if(samples, [](double v) { return v < 0.0; });
    std::sort(samples.begin(), samples.end());
    row.n = static_cast<int>(samples.size());
    if (!samples.empty()) {
        row.median = samples[samples.size() / 2];
        row.p95 = samples[static_cast<std::size_t>(0.95 * static_cast<double>(samples.size() - 1))];
    }
    return row;
}

// One route on one workload, in a window of its own.
std::vector<Row> run_cell(const Method& method, const Workload& work, double width_px) {
    std::vector<Row> rows;
    QQuickView view;
    edi_app::configure_engine(*view.engine());
    view.setResizeMode(QQuickView::SizeRootObjectToView);
    view.setSource(QUrl(QStringLiteral("qrc:/edi/bench/PlotBench.qml")));
    view.resize(1100, 700);
    view.show();
    QQuickItem* root = view.rootObject();
    auto* axis_x = root->findChild<QValueAxis*>(QStringLiteral("axisX"));
    auto* axis_y = root->findChild<QValueAxis*>(QStringLiteral("axisY"));
    auto* lines = root->findChild<edi_app::ScanLines*>(QStringLiteral("lines"));
    idle(200);
    const std::string route = method.name;
    lines->setVisible(route == "scanlines");
    lines->setLineWidth(width_px);
    Painted* painted = nullptr;
    if (route == "painter") {
        painted = new Painted(root);
        painted->setParentItem(root);
        painted->width_px = width_px;
        const auto follow = [painted, lines] {
            painted->setPosition(lines->position());
            painted->setSize(lines->size());
        };
        QObject::connect(lines, &QQuickItem::widthChanged, painted, follow);
        QObject::connect(lines, &QQuickItem::heightChanged, painted, follow);
        follow();
    }
    // The series, an area's upper and lower ones fed alike.
    std::vector<std::vector<QXYSeries*>> feeds;
    std::vector<QAbstractSeries*> owners;
    std::vector<std::unique_ptr<PointsModel>> models;
    std::vector<std::vector<PointsModel*>> model_of;
    if (method.qt_graphs) {
        QList<bool> areas;
        for (const Curve& curve : work.data.curves) {
            areas.append(curve.area);
        }
        QMetaObject::invokeMethod(root, "makeCurves", Q_ARG(QList<bool>, areas), Q_ARG(double, width_px));
        for (const QVariant& feed : root->property("feeds").toList()) {
            std::vector<QXYSeries*> series;
            for (const QVariant& one : feed.toList()) {
                series.push_back(qobject_cast<QXYSeries*>(one.value<QObject*>()));
            }
            feeds.push_back(series);
        }
        for (const QVariant& owner : root->property("owners").toList()) {
            owners.push_back(qobject_cast<QAbstractSeries*>(owner.value<QObject*>()));
        }
        if (route == "model-mapper") {
            for (const auto& series : feeds) {
                model_of.emplace_back();
                for (QXYSeries* one : series) {
                    models.push_back(std::make_unique<PointsModel>());
                    auto* mapper = new QXYModelMapper(root);
                    mapper->setOrientation(Qt::Vertical);
                    mapper->setXSection(0);
                    mapper->setYSection(1);
                    mapper->setModel(models.back().get());
                    mapper->setSeries(one);
                    model_of.back().push_back(models.back().get());
                }
            }
        }
    }
    const auto feed_one = [&](std::size_t curve, std::size_t which, const QList<QPointF>& points) {
        QXYSeries* series = feeds[curve][which];
        if (route == "cpp-replace") {
            series->replace(points);
        } else if (route == "cpp-append-list") {
            series->clear();
            series->append(points);
        } else if (route == "cpp-append-point") {
            series->clear();
            for (const QPointF& point : points) {
                series->append(point);
            }
        } else if (route == "cpp-replace-index") {
            if (series->count() == points.size()) {
                for (qsizetype i = 0; i < points.size(); ++i) {
                    series->replace(i, points[i]);
                }
            } else {
                series->replace(points);
            }
        } else if (route == "model-mapper") {
            model_of[curve][which]->setPoints(points);
        } else if (route == "qml-replace") {
            QMetaObject::invokeMethod(root, "replaceFromQml", Q_ARG(QXYSeries*, series), Q_ARG(QList<QPointF>, points));
        } else if (route == "qml-append") {
            QMetaObject::invokeMethod(root, "appendFromQml", Q_ARG(QXYSeries*, series), Q_ARG(QList<QPointF>, points));
        }
    };
    const auto show = [&](const Shown& shown) {
        axis_x->setRange(shown.x_min, shown.x_max);
        axis_y->setRange(shown.y_min, shown.y_max);
        if (route == "scanlines") {
            lines->setTraces(shown.traces);
            lines->setStyles(shown.styles);
        } else if (painted != nullptr) {
            painted->traces = shown.traces;
            painted->styles = shown.styles;
            painted->y_min = shown.y_min;
            painted->y_max = shown.y_max;
            painted->update();
        } else {
            for (std::size_t c = 0; c < shown.curves.size() && c < feeds.size(); ++c) {
                feed_one(c, 0, shown.curves[c].upper);
                if (shown.curves[c].area && feeds[c].size() > 1) {
                    feed_one(c, 1, shown.curves[c].lower);
                }
            }
        }
    };
    std::vector<edi_app::ScanLines::Style> styles = work.data.styles;
    const auto restyle = [&](int i) {
        const float saturation = i % 2 == 0 ? 0.5F : 0.8F;
        const std::size_t count = std::max(owners.size(), styles.size());
        for (std::size_t c = 0; c < owners.size(); ++c) {
            const QColor colour = colour_of(c, count, saturation);
            if (auto* xy = qobject_cast<QXYSeries*>(owners[c])) {
                xy->setColor(colour);
            } else {
                owners[c]->setProperty("color", colour);
            }
            // A colour change alone does not make Qt Graphs draw (6.11): the series' own update signal asks for it.
            emit owners[c]->update();
        }
        for (std::size_t c = 0; c < styles.size(); ++c) {
            styles[c].colour = colour_of(c, count, saturation);
        }
        if (route == "scanlines") {
            lines->setStyles(styles);
        } else if (painted != nullptr) {
            painted->styles = styles;
            painted->update();
        }
    };

    const std::string cell = route + " on " + work.name;
    log("%s: first draw", cell.c_str());
    const double first = frame_after(view, [&] { show(work.data); }, kFirstTimeoutMs);
    if (first < 0.0) {
        log("%s: no first frame in %d ms; skipping its other measures", cell.c_str(), kFirstTimeoutMs);
        rows.push_back(summarise(route, work.name, "first", {}, "no frame"));
        return rows;
    }
    log("%s: first draw %.2f ms", cell.c_str(), first);
    rows.push_back(summarise(route, work.name, "first", {first}, "ok"));
    const int timeout_ms = std::max(kMinChangeTimeoutMs, static_cast<int>(std::ceil(3.0 * first)));
    idle(300);
    const auto measure = [&](const char* name, const std::function<void(int)>& change) {
        std::vector<double> samples;
        int misses = 0;
        qint64 spent = 0;
        std::string status = "ok";
        for (int i = 0; i < kRepeats; ++i) {
            QElapsedTimer took;
            took.start();
            const double ms = frame_after(view, [&] { change(i); }, timeout_ms);
            spent += took.elapsed();
            samples.push_back(ms);
            misses = ms < 0.0 ? misses + 1 : 0;
            if (ms < 0.0) {
                log("%s: %s %d/%d missed", cell.c_str(), name, i + 1, kRepeats);
            } else {
                log("%s: %s %d/%d %.2f ms", cell.c_str(), name, i + 1, kRepeats, ms);
            }
            if (misses >= kMaxMisses) {
                status = "stopped: no frame";
                break;
            }
            if (spent > kBudgetMs && i + 1 < kRepeats) {
                status = "budget";
                log("%s: %s over its %lld ms budget after %d changes", cell.c_str(), name,
                    static_cast<long long>(kBudgetMs), i + 1);
                break;
            }
            idle(30);
        }
        rows.push_back(summarise(route, work.name, name, samples, status));
    };
    measure("update", [&](int i) { show(i % 2 == 0 ? work.updated : work.data); });
    measure("zoom", [&](int i) { show(i % 2 == 0 ? work.zoomed : work.data); });
    measure("restyle", restyle);
    return rows;
}

// What draws: the graphics API, and on OpenGL its renderer string, read once on the render thread.
QString renderer_of(QQuickWindow& window) {
    QString name;
    QSGRendererInterface* renderer = window.rendererInterface();
    switch (renderer != nullptr ? renderer->graphicsApi() : QSGRendererInterface::Unknown) {
        case QSGRendererInterface::OpenGL: {
            std::atomic<bool> read{false};
            const auto once = QObject::connect(
                &window, &QQuickWindow::beforeRendering, &window,
                [&] {
                    if (!read && QOpenGLContext::currentContext() != nullptr) {
                        const auto* text = reinterpret_cast<const char*>(
                            QOpenGLContext::currentContext()->functions()->glGetString(GL_RENDERER));
                        name = QStringLiteral("OpenGL ") + QString::fromLatin1(text != nullptr ? text : "?");
                        read = true;
                    }
                },
                Qt::DirectConnection);
            frame_after(window, [&] { window.update(); }, kVisibleTimeoutMs);
            QObject::disconnect(once);
            return name.isEmpty() ? QStringLiteral("OpenGL") : name;
        }
        case QSGRendererInterface::Metal:
            return QStringLiteral("Metal");
        case QSGRendererInterface::Direct3D11:
            return QStringLiteral("Direct3D 11");
        case QSGRendererInterface::Direct3D12:
            return QStringLiteral("Direct3D 12");
        case QSGRendererInterface::Vulkan:
            return QStringLiteral("Vulkan");
        case QSGRendererInterface::Software:
            return QStringLiteral("software");
        default:
            return QStringLiteral("unknown");
    }
}

QString slug(QString text) {
    text = text.toLower();
    for (QChar& c : text) {
        if (!c.isLetterOrNumber()) {
            c = QLatin1Char('-');
        }
    }
    while (text.contains(QStringLiteral("--"))) {
        text.replace(QStringLiteral("--"), QStringLiteral("-"));
    }
    return text.mid(0, 60).remove(QRegularExpression(QStringLiteral("^-|-$")));
}

}  // namespace

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    edi_app::use_design_font();
    const QStringList arguments = QCoreApplication::arguments();
    const auto option = [&](const char* name) {
        const qsizetype at = arguments.indexOf(QString::fromLatin1(name));
        return at >= 0 && at + 1 < arguments.size() ? arguments.at(at + 1) : QString();
    };
    const QString only = option("--only");
    const QStringList wanted = option("--workloads").split(QLatin1Char(','), Qt::SkipEmptyParts);

    // The window must be drawn before anything is timed, and its plot gives the pixel columns.
    QQuickView probe;
    edi_app::configure_engine(*probe.engine());
    probe.setResizeMode(QQuickView::SizeRootObjectToView);
    probe.setSource(QUrl(QStringLiteral("qrc:/edi/bench/PlotBench.qml")));
    probe.resize(1100, 700);
    probe.show();
    QElapsedTimer waited;
    waited.start();
    while (!probe.isExposed() && waited.elapsed() < kVisibleTimeoutMs) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 20);
    }
    if (!probe.isExposed() || frame_after(probe, [&] { probe.update(); }, kVisibleTimeoutMs) < 0.0) {
        log("the window is not being drawn (keep it visible and uncovered)");
        return 2;
    }
    const QString renderer = renderer_of(probe);
    auto* plot_item = probe.rootObject()->findChild<QQuickItem*>(QStringLiteral("lines"));
    const double plot_width = plot_item->width();
    const int columns = std::max(1, static_cast<int>(std::ceil(plot_width * probe.devicePixelRatio())));
    const QString machine = qEnvironmentVariableIsSet("EDI_BENCH_MACHINE") ? qEnvironmentVariable("EDI_BENCH_MACHINE")
                                                                            : QSysInfo::machineHostName();
    const QString platform = QGuiApplication::platformName();
    log("machine %s, platform %s, %s, plot %.0f px wide at %.1f device pixels each (%d columns)", qPrintable(machine),
        qPrintable(platform), qPrintable(renderer), plot_width, probe.devicePixelRatio(), columns);
    probe.hide();

    // The workloads.
    std::vector<Workload> workloads;
    QElapsedTimer making;
    making.start();
    const Scan scan = read_scan(QString::fromLatin1(kScan));
    if (scan.x.empty()) {
        log("no .dat files in %s (run from the repository's root)", kScan);
        return 1;
    }
    log("read the scan: %zu files in %lld ms", scan.x.size(), static_cast<long long>(making.elapsed()));
    const double quarter = (scan.hi - scan.lo) / 4.0;
    for (const std::size_t count : {std::size_t{324}, std::size_t{1000}, std::size_t{3000}}) {
        Workload work;
        work.name = "stacked-" + std::to_string(count);
        if (!wanted.isEmpty() && !wanted.contains(QString::fromStdString(work.name))) {
            continue;
        }
        work.lines = true;
        work.data = stacked(scan, count, columns, plot_width, scan.lo, scan.hi, 1.0);
        work.updated = stacked(scan, count, columns, plot_width, scan.lo, scan.hi, 0.97);
        work.zoomed = stacked(scan, count, columns, plot_width, scan.lo + quarter, scan.hi - quarter, 1.0);
        for (const Curve& curve : work.data.curves) {
            work.points += static_cast<std::size_t>(curve.upper.size());
        }
        log("%s: %zu curves, %zu points", work.name.c_str(), work.data.curves.size(), work.points);
        workloads.push_back(std::move(work));
    }
    if (wanted.isEmpty() || wanted.contains(QStringLiteral("pattern"))) {
        making.restart();
        edi::Project project = edi::load_project(kPattern);
        project.calculate();
        const edi::PatternSource captured = edi::capture_pattern(project, 0);
        const edi::PatternSource data = pattern_source(captured, 1.0), updated = pattern_source(captured, 0.98);
        Workload work;
        work.name = "pattern";
        work.data = pattern_shown(data, columns, std::nullopt, std::nullopt);
        work.updated = pattern_shown(updated, columns, std::nullopt, std::nullopt);
        const double lo = work.data.x_min, hi = work.data.x_max;
        work.zoomed = pattern_shown(data, columns, lo + (hi - lo) / 4.0, hi - (hi - lo) / 4.0);
        std::size_t areas = 0;
        for (const Curve& curve : work.data.curves) {
            work.points += static_cast<std::size_t>(curve.upper.size() + curve.lower.size());
            areas += curve.area ? 1 : 0;
        }
        log("pattern: %zu structures, %zu curves (%zu areas), %zu points, made in %lld ms", data.components.size(),
            work.data.curves.size(), areas, work.points, static_cast<long long>(making.elapsed()));
        workloads.push_back(std::move(work));
    }

    std::vector<Row> rows;
    for (const Workload& work : workloads) {
        for (const Method& method : methods()) {
            if ((!only.isEmpty() && only != QLatin1String(method.name)) || (!method.qt_graphs && !work.lines)) {
                continue;
            }
            for (Row& row : run_cell(method, work, 1.0)) {
                rows.push_back(std::move(row));
            }
        }
    }

    // The table, on stdout and as a TSV.
    QString out = option("--out");
    if (out.isEmpty()) {
        QDir().mkpath(QStringLiteral("build/plot-bench"));
        out = QStringLiteral("build/plot-bench/%1-%2-%3.tsv").arg(slug(machine), slug(platform), slug(renderer));
    }
    QFile file(out);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        log("cannot write %s", qPrintable(out));
        return 1;
    }
    const QString header = QStringLiteral("machine\tplatform\trenderer\tmethod\tworkload\tmeasure\tn\tmedian_ms\tp95_ms\tstatus\n");
    file.write(header.toUtf8());
    std::fputs(qPrintable(header), stdout);
    for (const Row& row : rows) {
        const QString line = QStringLiteral("%1\t%2\t%3\t%4\t%5\t%6\t%7\t%8\t%9\t%10\n")
                                 .arg(machine, platform, renderer, QString::fromStdString(row.method),
                                      QString::fromStdString(row.workload), QString::fromStdString(row.measure))
                                 .arg(row.n)
                                 .arg(row.median, 0, 'f', 2)
                                 .arg(row.p95, 0, 'f', 2)
                                 .arg(QString::fromStdString(row.status));
        file.write(line.toUtf8());
        std::fputs(qPrintable(line), stdout);
    }
    log("wrote %s", qPrintable(out));
    return 0;
}

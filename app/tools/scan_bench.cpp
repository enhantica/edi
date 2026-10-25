// SPDX-License-Identifier: BSD-3-Clause
// The scan views' renderer benchmark (edi ADR-0041): how the Stacked view can draw a scan's patterns on the GPU.
// Candidate a is Qt Graphs, one LineSeries per pattern, each fed its trace reduced at the plot's pixel columns
// (edi::scan_trace) in one replace() call; candidate b is edi's ScanLines item, a scene-graph node of quads per
// pattern drawn by a shader, its row, height and colour given to the shader; candidate p is how the view drew before,
// every pattern stroked with QPainter into one image on each change. For the scan given (by default the bundled 324-file scan) it times, from the
// change to the swap of the first frame whose scene synchronisation followed it: the first population; a new x range
// (a zoom or pan step, every trace reduced again); a restyle (every line's colour); and a new stacking offset (every
// line moved, its trace kept). It prints one table, saves the last frame and reports the reduction's own cost. Test
// tooling, never part of the host.
#include <QColor>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QGuiApplication>
#include <QImage>
#include <QPainter>
#include <QPainterPath>
#include <QQuickPaintedItem>
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
#include <cstdlib>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

#include "edi/scan.hpp"
#include "edi/scan_views.hpp"
#include "engine_setup.hpp"
#include "scan_lines.hpp"

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {

constexpr int kRepeats = 30;
constexpr int kTimeoutMs = 10000;

struct Dataset {
    std::vector<double> x, intensity;
};

std::vector<Dataset> read_scan(const QString& directory) {
    QStringList files = QDir(directory).entryList({QStringLiteral("*.dat")}, QDir::Files, QDir::Name);
    std::vector<Dataset> out;
    for (const QString& file : files) {
        const edi::PdDataBase data =
            edi::read_scan_dataset(directory.toStdString(), file.toStdString(), edi::BeamModeEnum::CONSTANT_WAVELENGTH);
        Dataset d;
        d.x = data.axis();
        d.intensity = data.intensity_meas.get();
        d.intensity.resize(d.x.size(), std::nan(""));
        out.push_back(std::move(d));
    }
    return out;
}

struct Stats {
    double median = -1.0, p95 = -1.0;
    int missing = 0;
};

Stats stats(std::vector<double> samples) {
    Stats s;
    s.missing = static_cast<int>(std::count_if(samples.begin(), samples.end(), [](double v) { return v < 0.0; }));
    std::erase_if(samples, [](double v) { return v < 0.0; });
    std::sort(samples.begin(), samples.end());
    if (!samples.empty()) {
        s.median = samples[samples.size() / 2];
        s.p95 = samples[static_cast<std::size_t>(0.95 * static_cast<double>(samples.size() - 1))];
    }
    return s;
}

// The milliseconds from `change` to the swap of the first frame synchronised after it, or -1.
double frame_after(QQuickWindow& window, const std::function<void()>& change) {
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
    guard.start(kTimeoutMs);
    clock.start();
    change();
    loop.exec();
    QObject::disconnect(sync);
    QObject::disconnect(swap);
    return swapped < 0 ? -1.0 : static_cast<double>(swapped.load()) / 1e6;
}

// Candidate p: every pattern's trace stroked with a 2 px antialiased pen into the item's image on each change, as
// ScanLayer draws the Stacked view.
class Painted : public QQuickPaintedItem {
   public:
    explicit Painted(QQuickItem* parent) : QQuickPaintedItem(parent) { setAntialiasing(true); }
    std::vector<edi_app::ScanLines::Trace> traces;
    std::vector<edi_app::ScanLines::Style> styles;
    double y_min = 0.0, y_max = 1.0;
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
            pen.setWidthF(2.0);
            pen.setCosmetic(true);
            pen.setCapStyle(Qt::FlatCap);
            painter->setPen(pen);
            painter->drawPath(path);
        }
    }
};

// Settles between timed changes, so one frame's work does not run into the next.
void idle(int ms) {
    QElapsedTimer t;
    t.start();
    while (t.elapsed() < ms) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 5);
    }
}

}  // namespace

int main(int argc, char** argv) {
    QGuiApplication app(argc, argv);
    edi_app::use_design_font();
    const QString directory = argc > 1 ? QString::fromLocal8Bit(argv[1])
                                       : QStringLiteral("docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project/"
                                                        "experiments/d20_scan");
    const QString frame_path = argc > 2 ? QString::fromLocal8Bit(argv[2]) : QString();
    const QString candidate = argc > 3 ? QString::fromLocal8Bit(argv[3]) : QStringLiteral("a");
    // b and p take the same traces and styles.
    const bool candidate_b = candidate == QLatin1String("b") || candidate == QLatin1String("p");
    QElapsedTimer read_clock;
    read_clock.start();
    const std::vector<Dataset> scan = read_scan(directory);
    const qint64 read_ms = read_clock.elapsed();
    if (scan.empty()) {
        std::fprintf(stderr, "scan_bench: no .dat files in %s\n", qPrintable(directory));
        return 1;
    }
    double lo = INFINITY, hi = -INFINITY, low = INFINITY, high = -INFINITY;
    std::size_t points = 0;
    for (const Dataset& d : scan) {
        points += d.x.size();
        for (std::size_t i = 0; i < d.x.size(); ++i) {
            if (std::isfinite(d.x[i]) && std::isfinite(d.intensity[i])) {
                lo = std::min(lo, d.x[i]);
                hi = std::max(hi, d.x[i]);
                low = std::min(low, d.intensity[i]);
                high = std::max(high, d.intensity[i]);
            }
        }
    }
    const auto patterns = static_cast<int>(scan.size());

    QQuickView view;
    edi_app::configure_engine(*view.engine());
    view.setResizeMode(QQuickView::SizeRootObjectToView);
    view.setSource(QUrl(QStringLiteral("qrc:/edi/bench/ScanBench.qml")));
    view.resize(1100, 700);
    view.show();
    QQuickItem* root = view.rootObject();
    auto* graphs = root->findChild<QQuickItem*>(QStringLiteral("view"));
    auto* axis_x = root->findChild<QValueAxis*>(QStringLiteral("axisX"));
    auto* axis_y = root->findChild<QValueAxis*>(QStringLiteral("axisY"));
    auto* lines = root->findChild<edi_app::ScanLines*>(QStringLiteral("lines"));
    Painted* painted = nullptr;
    if (candidate == QLatin1String("p")) {
        painted = new Painted(root);
        painted->setParentItem(root);
        painted->setPosition(lines->position());
        painted->setSize(lines->size());
        lines->setVisible(false);
    }
    const auto set_traces = [&](std::vector<edi_app::ScanLines::Trace> traces) {
        if (painted != nullptr) {
            painted->traces = std::move(traces);
            painted->update();
        } else {
            lines->setTraces(std::move(traces));
        }
    };
    const auto set_styles = [&](std::vector<edi_app::ScanLines::Style> styles) {
        if (painted != nullptr) {
            painted->styles = std::move(styles);
            painted->y_min = lines->yMin();
            painted->y_max = lines->yMax();
            painted->update();
        } else {
            lines->setStyles(std::move(styles));
        }
    };
    idle(200);
    if (!candidate_b) {
        QMetaObject::invokeMethod(root, "makeSeries", Q_ARG(int, patterns), Q_ARG(double, 2.0));
    }
    std::vector<QXYSeries*> series;
    for (const QVariant& v : root->property("series").toList()) {
        series.push_back(qobject_cast<QXYSeries*>(v.value<QObject*>()));
    }
    idle(200);
    // The plot's pixel columns, or fewer when asked (a fourth argument, the share of them), to see how the cost scales.
    const double share = argc > 4 ? std::atof(argv[4]) : 1.0;
    const int columns = std::max(1, static_cast<int>(std::ceil(share * graphs->property("plotArea").toRectF().width() *
                                                                  view.devicePixelRatio())));

    // The traces of the range shown, and their points: each column's lowest and highest value, up from the
    // pattern's row by `lift` rows over the scan's intensity range, as the Stacked view draws them.
    std::vector<edi::ScanTrace> traces(scan.size());
    double reduce_ms = 0.0;
    const auto reduce = [&](double x_min, double x_max) {
        QElapsedTimer t;
        t.start();
        for (std::size_t d = 0; d < scan.size(); ++d) {
            traces[d] = edi::scan_trace(scan[d].x, scan[d].intensity, x_min, x_max, static_cast<std::size_t>(columns));
        }
        reduce_ms = static_cast<double>(t.nsecsElapsed()) / 1e6;
    };
    double lift = 8.0, shown_min = lo, shown_max = hi;
    std::vector<QColor> colours(scan.size());
    const auto colour_all = [&](float saturation) {
        for (std::size_t d = 0; d < colours.size(); ++d) {
            colours[d] = QColor::fromHsvF(static_cast<float>(d) / static_cast<float>(colours.size()), saturation, 0.7F);
        }
    };
    colour_all(0.8F);
    const auto styles = [&] {
        std::vector<edi_app::ScanLines::Style> out(scan.size());
        for (std::size_t d = 0; d < out.size(); ++d) {
            out[d] = {static_cast<double>(d), lift, colours[d]};
        }
        return out;
    };
    const auto points_of = [&](std::size_t d) {
        QList<QPointF> list;
        const edi::ScanTrace& trace = traces[d];
        list.reserve(static_cast<qsizetype>(2 * trace.x.size()));
        const double row = static_cast<double>(d);
        for (std::size_t k = 0; k < trace.x.size(); ++k) {
            const double y_low = row + (trace.low[k] - low) / (high - low) * lift;
            const double y_high = row + (trace.high[k] - low) / (high - low) * lift;
            list.append(QPointF(trace.x[k], y_low));
            if (y_high != y_low) {
                list.append(QPointF(trace.x[k], y_high));
            }
        }
        return list;
    };
    std::size_t drawn_points = 0;
    const auto fill = [&] {
        drawn_points = 0;
        if (candidate_b) {
            // Each column's lowest and highest value, x in item pixels and v over the scan's intensity range.
            std::vector<edi_app::ScanLines::Trace> out(scan.size());
            const double width = lines->width();
            for (std::size_t d = 0; d < scan.size(); ++d) {
                const edi::ScanTrace& trace = traces[d];
                for (std::size_t k = 0; k < trace.x.size(); ++k) {
                    const auto x = static_cast<float>((trace.x[k] - shown_min) / (shown_max - shown_min) * width);
                    out[d].x.push_back(x);
                    out[d].v.push_back(static_cast<float>((trace.low[k] - low) / (high - low)));
                    if (trace.high[k] != trace.low[k]) {
                        out[d].x.push_back(x);
                        out[d].v.push_back(static_cast<float>((trace.high[k] - low) / (high - low)));
                    }
                }
                drawn_points += out[d].x.size();
            }
            set_traces(std::move(out));
            set_styles(styles());
            return;
        }
        for (std::size_t d = 0; d < series.size(); ++d) {
            const QList<QPointF> list = points_of(d);
            drawn_points += static_cast<std::size_t>(list.size());
            series[d]->replace(list);
        }
    };
    const auto set_range = [&](double x_min, double x_max) {
        shown_min = x_min;
        shown_max = x_max;
        axis_x->setRange(x_min, x_max);
        axis_y->setRange(-1.0, static_cast<double>(patterns) + lift);
    };

    const double first = frame_after(view, [&] {
        reduce(lo, hi);
        set_range(lo, hi);
        fill();
    });
    idle(500);
    std::vector<double> range_ms, reduce_samples, restyle_ms, offset_ms;
    for (int i = 0; i < kRepeats; ++i) {
        const double inset = i % 2 == 0 ? 0.01 * (hi - lo) : 0.0;
        range_ms.push_back(frame_after(view, [&] {
            reduce(lo + inset, hi - inset);
            set_range(lo + inset, hi - inset);
            fill();
        }));
        reduce_samples.push_back(reduce_ms);
        idle(50);
    }
    for (int i = 0; i < kRepeats; ++i) {
        restyle_ms.push_back(frame_after(view, [&] {
            colour_all(i % 2 == 0 ? 0.9F : 0.6F);
            if (candidate_b) {
                set_styles(styles());
            }
            for (std::size_t d = 0; d < series.size(); ++d) {
                series[d]->setColor(colours[d]);
            }
        }));
        idle(50);
    }
    for (int i = 0; i < kRepeats; ++i) {
        offset_ms.push_back(frame_after(view, [&] {
            lift = i % 2 == 0 ? 4.0 : 8.0;
            if (candidate_b) {
                set_styles(styles());
            } else {
                fill();
            }
        }));
        idle(50);
    }
    if (!frame_path.isEmpty()) {
        view.grabWindow().save(frame_path);
    }
    const Stats range = stats(range_ms), reduced = stats(reduce_samples), restyle = stats(restyle_ms),
                offset = stats(offset_ms);
    std::printf("candidate\tpatterns\tpoints_read\tpoints_drawn\tcolumns\tfirst_ms\trange_median_ms\trange_p95_ms\t"
                "reduce_median_ms\trestyle_median_ms\trestyle_p95_ms\toffset_median_ms\toffset_p95_ms\tmissing\tplatform\t"
                "read_ms\n");
    std::printf("%s\t%d\t%zu\t%zu\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%d\t%s\t%lld\n",
                qPrintable(candidate), patterns, points,
                drawn_points, columns, first, range.median, range.p95, reduced.median, restyle.median, restyle.p95,
                offset.median, offset.p95, range.missing + restyle.missing + offset.missing,
                qPrintable(QGuiApplication::platformName()), static_cast<long long>(read_ms));
    return range.missing + restyle.missing + offset.missing == 0 && first >= 0.0 ? 0 : 1;
}

// SPDX-License-Identifier: BSD-3-Clause
// The pattern chart's filled areas through changes of its axes. Every area Qt Graphs lays out must be empty or hold the
// points of the pattern the chart shows at that moment, and every area attached to an axis that changes must be empty or
// hold those of the pattern the axis changes to. The expected points come from the fixture files' rows and Bragg's law,
// the calculated intensities from the project's calculated columns.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <memory>
#include <numbers>
#include <set>
#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlListReference>
#include <QQuickItem>
#include <QQuickWindow>
#include <QtGraphs/QAreaSeries>
#include <QtGraphs/QLineSeries>
#include <QtGraphs/QValueAxis>
#include <QtQml/qqmlextensionplugin.h>
#include <QtQuick/private/qquickpath_p.h>
#include <QtTest/QtTest>
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "edi/version.hpp"
#include "engine_setup.hpp"
#include "experiment_models.hpp"
#include "experiment_view_model.hpp"
#include "parameter_item.hpp"
#include "pattern_chart_controller.hpp"
#include "project_view_model.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {

const QString kFixtures = QStringLiteral(EDI_SOURCE_DIR "/tests/fixtures/excluded_display/");
const QString kMeasured = QStringLiteral("chart.series.meas.band");
const QString kResidual = QStringLiteral("chart.series.resid.band");
QString structureArea(int place) { return QStringLiteral("chart.series.structure.%1").arg(place); }

struct Row {
    double x, y, su;
};

// The measured rows at the end of a fixture's experiment file.
std::vector<Row> measuredRows(const QString& fixture) {
    QFile file(kFixtures + fixture + QStringLiteral("/experiments/pattern.edi"));
    if (!file.open(QIODevice::ReadOnly)) return {};
    std::vector<Row> rows;
    bool inside = false;
    for (const QString& line : QString::fromUtf8(file.readAll()).split(u'\n')) {
        if (inside) {
            const QStringList cells = line.simplified().split(u' ', Qt::SkipEmptyParts);
            if (cells.size() == 3) rows.push_back({cells[0].toDouble(), cells[1].toDouble(), cells[2].toDouble()});
        }
        inside = inside || line.trimmed() == QLatin1String("_data.intensity_meas_su");
    }
    return rows;
}

// A fixture's project without its excluded regions: an area then has exactly one point per row.
edi::Project fixtureProject(const QString& fixture) {
    auto project = edi::load_project((kFixtures + fixture).toStdString(), edi::ProjectLoadMode::Construction);
    project.experiment().excluded_regions.clear();
    return project;
}

// The angle pattern with one structure and the time-of-flight pattern with two, so their panes' heights differ.
edi::Project twoPatterns() {
    edi::Project project = fixtureProject(QStringLiteral("cw"));
    const edi::Project other = fixtureProject(QStringLiteral("tof"));
    auto second = *project.structures.front();
    second.name = "phase2";
    project.structures.push_back(second);
    auto flight = *other.experiments.front();
    flight.name = "flight";
    edi::LinkedStructure link;
    link.structure_id = "phase2";
    flight.linked_structures.push_back(link);
    project.experiments.push_back(flight);
    return project;
}

struct AxisRange {
    double xMin = 0, xMax = 0, yMin = 0, yMax = 0;
    double height = 1;  // the plot's, in pixels
    QString text() const { return QStringLiteral("x %1..%2, y %3..%4").arg(xMin).arg(xMax).arg(yMin).arg(yMax); }
};

struct Edges {
    QList<QPointF> upper, lower;
    bool empty() const { return upper.size() < 2 || lower.size() < 2; }  // Qt Graphs draws nothing then
};

bool close(double a, double b, double share = 1e-6) {
    return std::fabs(a - b) <= share * std::max({1.0, std::fabs(a), std::fabs(b)});
}

// What the chart shows in one state, row by row.
struct Shown {
    std::vector<double> x, measured, su, background, calculated;
    std::vector<std::vector<double>> structures;  // each above the background
    bool residual = false;
    bool measuredBand = true;
    bool squareRoot = false;

    double display(double value) const { return squareRoot ? std::copysign(std::sqrt(std::fabs(value)), value) : value; }
    double least() const { return *std::min_element(x.begin(), x.end()); }
    double greatest() const { return *std::max_element(x.begin(), x.end()); }
    bool shows(const QString& area) const {
        if (area == kMeasured) return measuredBand && !measured.empty();
        if (area == kResidual) return residual;
        for (std::size_t k = 0; k < structures.size(); ++k)
            if (area == structureArea(int(k))) return true;
        return false;
    }
    QStringList areas() const {
        QStringList out;
        if (shows(kMeasured)) out.append(kMeasured);
        if (residual) out.append(kResidual);
        for (std::size_t k = 0; k < structures.size(); ++k) out.append(structureArea(int(k)));
        return out;
    }
    // Whether the calculated line drawn is this pattern's.
    bool hasLine(const QList<QPointF>& line) const {
        std::map<double, std::size_t> rows;
        for (std::size_t k = 0; k < x.size(); ++k) rows.emplace(x[k], k);
        int usable = 0;
        for (const QPointF& point : line) {
            if (!std::isfinite(point.x()) || !std::isfinite(point.y())) continue;
            auto found = rows.lower_bound(point.x() - 1e-6 * std::max(1.0, std::fabs(point.x())));
            if (found == rows.end() || !close(found->first, point.x())) return false;
            if (!close(display(calculated[found->second]), point.y(), 1e-5)) return false;
            ++usable;
        }
        return usable > 2;
    }
    bool sameLine(const Shown& other) const {
        return x == other.x && calculated == other.calculated && squareRoot == other.squareRoot;
    }
    // Whether an x range lies in this pattern's.
    bool spans(const AxisRange& axis) const {
        const double slack = 1e-6 * (greatest() - least());
        return axis.xMax > axis.xMin && axis.xMin >= least() - slack && axis.xMax <= greatest() + slack;
    }

    // What is wrong with an area's points on an axis; nothing when they are this pattern's.
    QString problem(const QString& area, const Edges& edges, const AxisRange& axis) const {
        if (edges.empty()) return {};
        if (!shows(area)) return QStringLiteral("holds %1 points and should be empty").arg(edges.upper.size());
        if (edges.upper.size() != edges.lower.size()) return QStringLiteral("has edges of different lengths");
        std::map<double, std::size_t> rows;
        for (std::size_t k = 0; k < x.size(); ++k) rows.emplace(x[k], k);
        // The fill under a structure's curve or the measured band is never thinner than a twentieth of a pixel.
        const double thin = 0.1 * std::fabs(axis.yMax - axis.yMin) / std::max(1.0, axis.height);
        std::set<std::size_t> held;
        for (qsizetype k = 0; k < edges.upper.size(); ++k) {
            const QPointF up = edges.upper[k], low = edges.lower[k];
            if (!std::isfinite(up.x()) || !std::isfinite(up.y()) || !std::isfinite(low.y()))
                return QStringLiteral("has an unusable point");
            auto found = rows.lower_bound(up.x());
            if (found == rows.end() || (found != rows.begin() && std::fabs(std::prev(found)->first - up.x()) < std::fabs(found->first - up.x())))
                --found;
            const std::size_t row = found->second;
            if (!close(found->first, up.x()) || !close(up.x(), low.x()))
                return QStringLiteral("has a point at x %1, the nearest row is at %2").arg(up.x(), 0, 'g', 9).arg(found->first, 0, 'g', 9);
            held.insert(row);
            const auto wrong = [&](const char* edge, double is, double should) {
                return QStringLiteral("has its %1 edge at %2 at x %3, expected %4").arg(QLatin1String(edge)).arg(is).arg(up.x()).arg(should);
            };
            if (up.y() < low.y()) return QStringLiteral("has its upper edge at %1 below its lower edge at %2 at x %3").arg(up.y()).arg(low.y()).arg(up.x());
            if (area == kMeasured) {
                const double top = display(measured[row] + su[row]), bottom = display(measured[row] - su[row]);
                if (!close(low.y(), bottom)) return wrong("lower", low.y(), bottom);
                if (!close(up.y(), top) && (up.y() < top || up.y() > bottom + thin)) return wrong("upper", up.y(), top);
            } else if (area == kResidual) {
                if (!close(up.y() - low.y(), 2.0 * su[row], 1e-4)) return wrong("upper", up.y(), low.y() + 2.0 * su[row]);
                const double centre = measured[row] - calculated[row];
                if (!close(0.5 * (up.y() + low.y()), centre, 1e-5)) return wrong("lower", low.y(), centre - su[row]);
            } else {
                const double base = display(background[row]);
                if (!close(low.y(), base, 1e-5)) return wrong("lower", low.y(), base);
                const std::size_t place = area.mid(structureArea(0).size() - 1).toULongLong();
                const double top = display(background[row] + structures[place][row]);
                if (!close(up.y(), top, 1e-5) && (up.y() < top || up.y() > base + thin)) return wrong("upper", up.y(), top);
            }
        }
        // Every row in view, and one beyond each end at the most. A pattern with more rows than the plot has columns
        // keeps only some of them: its first and last in view are asked for.
        std::vector<std::size_t> inView;
        int before = 0, after = 0;
        for (std::size_t k = 0; k < x.size(); ++k)
            if (x[k] >= axis.xMin && x[k] <= axis.xMax) inView.push_back(k);
        if (inView.size() > 400) inView = {inView.front(), inView.back()};
        for (const std::size_t row : inView)
            if (!held.contains(row)) return QStringLiteral("has no point for the row in view at x %1").arg(x[row]);
        for (const std::size_t row : held) {
            before += x[row] < axis.xMin ? 1 : 0;
            after += x[row] > axis.xMax ? 1 : 0;
        }
        if (before > 1 || after > 1) return QStringLiteral("has %1 rows before the view and %2 after it").arg(before).arg(after);
        return {};
    }
};

// What the project's experiment shows. The measured columns and the background are the fixture's when there is one.
Shown shownOf(const edi::ExperimentBase& experiment, const std::vector<Row>& rows = {}) {
    Shown out;
    if (!experiment.data) return out;
    const auto& data = *experiment.data;
    if (rows.empty()) {
        out.x = data.axis();
        out.background = data.intensity_bkg.values();
    } else {
        const double first = rows.front().x, last = rows.back().x;
        for (const Row& row : rows) {
            out.x.push_back(row.x);
            out.measured.push_back(row.y);
            out.su.push_back(row.su);
            // Both fixtures' background is the line from 40 at their first row to 80 at their last.
            out.background.push_back(40.0 + 40.0 * (row.x - first) / (last - first));
        }
        out.residual = true;
    }
    if (out.background.empty()) out.background.assign(out.x.size(), 0.0);
    out.calculated = data.intensity_calc.values();
    const std::size_t count = data.component_order.values().size();
    const auto& net = data.component_intensities_net.values();
    for (std::size_t place = 0; place < count; ++place) {
        std::vector<double> curve;
        curve.reserve(out.x.size());
        for (std::size_t row = 0; row < out.x.size(); ++row) curve.push_back(net.at(row * count + place));
        out.structures.push_back(std::move(curve));
    }
    return out;
}

Shown onDSpacing(Shown shown, double wavelength) {
    for (double& x : shown.x) x = wavelength / (2.0 * std::sin(0.5 * x * std::numbers::pi / 180.0));
    return shown;
}

Shown held(Shown shown) {
    shown.residual = false;
    shown.structures.clear();
    return shown;
}

}  // namespace

// A chart in a window, and what Qt Graphs is given and lays out while something changes.
class WatchedChart : public QObject {
    Q_OBJECT
   public:
    struct Area {
        QString name;
        QQuickItem* view;
        QAreaSeries* series;
    };
    struct Record {
        bool layout = false;
        QString area, event;
        Edges edges;
        AxisRange axis;
        double beyond = 0;  // how far outside the plot it was laid out, in pixels
        bool mainMoved = false;  // one of the main pane's ranges had changed by then
        QList<QPointF> line;     // the calculated line then
        int phase = 0;
        const QAreaSeries* series = nullptr;  // which area of that name it was, only to compare
        bool outgoing = false;                // another area of that name had taken its place
    };

    explicit WatchedChart(edi_app::ProjectViewModel& project) {
        edi_app::configure_engine(engine_);
        QQmlComponent component(&engine_);
        component.setData(R"(
            import QtQuick
            import edi.app
            Item {
                required property ProjectViewModel project
                property string yScale: "linear"
                onYScaleChanged: Preferences.patternYScale = yScale
                Component.onCompleted: {
                    Preferences.patternYScale = "linear";
                    Preferences.patternMeasuredStyle = "band";
                    Preferences.structureCurves = true;
                }
                PatternChart {
                    anchors.fill: parent
                    settingsPage: "pattern"
                    axisProject: parent.project
                    experiment: parent.project.currentExperiment
                }
            }
        )", QUrl());
        window_.resize(1000, 720);
        window_.show();
        root_.reset(qobject_cast<QQuickItem*>(component.createWithInitialProperties({{QStringLiteral("project"), QVariant::fromValue(&project)}})));
        if (!root_) {
            error_ = component.errorString();
            return;
        }
        root_->setParentItem(window_.contentItem());
        root_->setSize(window_.size());
        controller_ = root_->findChild<edi_app::PatternChartController*>();
        main_ = root_->findChild<QQuickItem*>(QStringLiteral("chart.view.main"));
        residual_ = root_->findChild<QQuickItem*>(QStringLiteral("chart.view.residual"));
        if (!controller_ || !main_ || !residual_) {
            error_ = QStringLiteral("the chart has no controller or no panes");
            return;
        }
        controller_->setAnimationDuration(0);
        line_ = root_->findChild<QLineSeries*>(QStringLiteral("chart.series.calc"));
        if (!line_) {
            error_ = QStringLiteral("the chart has no calculated line");
            return;
        }
        for (QQuickItem* view : {main_, residual_}) {
            for (const char* name : {"axisX", "axisY"}) {
                auto* axis = qobject_cast<QValueAxis*>(view->property(name).value<QAbstractAxis*>());
                if (!axis) {
                    error_ = QStringLiteral("a pane has no value axis");
                    return;
                }
                connect(axis, &QValueAxis::minChanged, this, [this, view, name] { attached(view, name); });
                connect(axis, &QValueAxis::maxChanged, this, [this, view, name] { attached(view, name); });
            }
        }
        project_ = &project;
        if (!QTest::qWaitForWindowExposed(&window_)) error_ = QStringLiteral("the window was not shown");
        else if (!settle()) error_ = QStringLiteral("the chart did not settle");
    }
    ~WatchedChart() override { root_.reset(); }

    const QString& error() const { return error_; }
    edi_app::PatternChartController* controller() const { return controller_; }
    QQuickItem* mainView() const { return main_; }
    QQuickItem* residualView() const { return residual_; }
    const QLineSeries* calculatedLine() const { return line_; }
    void setYScale(const char* scale) { root_->setProperty("yScale", QString::fromLatin1(scale)); }
    void resize(int width, int height) {
        window_.resize(width, height);
        root_->setSize(QSizeF(width, height));
    }

    // Nothing left to calculate, and three looks in a row at unchanged points and axes.
    bool settle() {
        QString last;
        int same = 0;
        for (int step = 0; step < 300 && same < 4; ++step) {
            QTest::qWait(100);
            QString now;
            for (const Area& area : areas()) {
                const Edges edges = edgesOf(area);
                now += area.name + rangeOf(area.view).text() + QString::number(edges.upper.size());
                for (const QPointF& point : edges.upper) now += QString::number(point.x()) + u' ' + QString::number(point.y()) + u' ';
            }
            same = !project_->calculating() && now == last ? same + 1 : 0;
            last = now;
        }
        watchPaths();
        return same >= 4;
    }

    QList<Area> areas() const {
        QList<Area> out;
        for (QQuickItem* view : {main_, residual_}) {
            const QQmlListReference series(view, "seriesList");
            for (qsizetype k = 0; k < series.count(); ++k)
                if (auto* area = qobject_cast<QAreaSeries*>(series.at(k))) out.append({area->objectName(), view, area});
        }
        return out;
    }
    static Edges edgesOf(const Area& area) { return {area.series->upperSeries()->points(), area.series->lowerSeries()->points()}; }
    static AxisRange rangeOf(const QQuickItem* view) {
        const auto axis = [view](const char* name) { return qobject_cast<QValueAxis*>(view->property(name).value<QAbstractAxis*>()); };
        return {axis("axisX")->min(), axis("axisX")->max(), axis("axisY")->min(), axis("axisY")->max(),
                view->property("plotArea").toRectF().height()};
    }

    bool hasArea(const QString& name) const {
        const QList<Area> all = areas();
        return std::any_of(all.begin(), all.end(), [&name](const Area& area) { return area.name == name; });
    }

    void start() {
        watchPaths();
        records_.clear();
        ends_.clear();
        main_moved_ = false;
        phase_ = 0;
        taken_early_ = taken_late_ = 0;
        known_.clear();
        newest_.clear();
        noteAreas();
        recording_ = true;
    }
    // Another change begins before the last one has settled.
    void next() {
        ends_.append({rangeOf(main_), rangeOf(residual_)});
        main_moved_ = false;
        ++phase_;
    }
    void stop() {
        if (recording_) ends_.append({rangeOf(main_), rangeOf(residual_)});
        recording_ = false;
    }
    int phase() const { return phase_; }
    qsizetype seen(bool layout) const {
        return std::count_if(records_.begin(), records_.end(), [layout](const Record& record) { return record.layout == layout; });
    }

    // The recorded areas that were neither empty nor of the pattern they belonged to. What the chart shows goes over from
    // one state to the other when the main pane's ranges move or the calculated line does, whichever is first: a layout
    // after that has the later state's areas, one before it the earlier's. Two states with the same line (a fill left
    // out or put back) have no such moment. An area on an axis that is changing must already be the later state's.
    // `phase` counts the changes made one after the other without settling (next()).
    QStringList problems(const Shown& before, const Shown& after, int phase = 0) const {
        QStringList out;
        std::map<QString, int> layouts, changes;
        std::map<QString, double> distances;
        for (const Record& record : records_) {
            if (record.phase != phase || record.edges.empty()) continue;
            QString problem;
            if (!record.layout && record.outgoing) {
                problem = QStringLiteral("was replaced by another area and is still drawable");
            } else if (record.layout) {
                QList<const Shown*> states{&after};
                if (before.sameLine(after)) states.append(&before);
                else if (!record.mainMoved && before.hasLine(record.line)) states = {&before};
                for (const Shown* shown : states) {
                    problem = shown->spans(record.axis) ? shown->problem(record.area, record.edges, record.axis)
                                                        : QStringLiteral("is on axes its pattern is not on");
                    if (problem.isEmpty()) break;
                }
            } else {
                problem = after.problem(record.area, record.edges, record.axis);
                // An axis published end by end holds neither range in between: the points are judged on their own.
                if (problem.contains(QLatin1String("in view")) || problem.contains(QLatin1String("the view"))) {
                    AxisRange whole = record.axis;
                    const AxisRange now = record.area == kResidual ? ends_[phase].second : ends_[phase].first;
                    whole.xMin = now.xMin;
                    whole.xMax = now.xMax;
                    problem = after.problem(record.area, record.edges, whole);
                }
            }
            if (problem.isEmpty()) continue;
            if (record.layout && record.outgoing) problem.prepend(QStringLiteral("(the replaced one) "));
            int& count = record.layout ? layouts[record.area] : changes[record.area];
            if (record.layout) distances[record.area] = std::max(distances[record.area], record.beyond);
            if (++count == 1)
                out.append(QStringLiteral("%1 (%2; %3) %4").arg(record.area, record.event, record.axis.text(), problem));
        }
        for (const auto& [area, count] : layouts) out.append(QStringLiteral("%1 layouts of %2, up to %3 px outside the plot").arg(count).arg(area).arg(distances[area]));
        for (const auto& [area, count] : changes) out.append(QStringLiteral("%1 axis changes over %2").arg(count).arg(area));
        return out;
    }

    // Paths new since the start: how many Qt makes for the same areas is its own business.
    int newPaths() const { return taken_early_ + taken_late_; }

    // What should have been observed and was not: a filled layout of every area shown afterwards, an empty one of every
    // area no longer shown, and each area on every axis named ("main axisX, residual axisY") as the axis changed.
    // The areas laid out have to be the very ones the chart then has.
    QStringList unseen(const Shown& before, const Shown& after, const QString& axes, int phase = 0) const {
        QStringList out;
        const QList<Area> now = areas();
        const auto seenLayout = [this, &now, phase](const QString& name, bool empty) {
            const auto area = std::find_if(now.begin(), now.end(), [&name](const Area& each) { return each.name == name; });
            return std::any_of(records_.begin(), records_.end(), [&](const Record& record) {
                return record.layout && record.phase == phase && record.area == name && record.edges.empty() == empty &&
                       (area == now.end() || record.series == area->series);
            });
        };
        if (taken_late_ > 0) out.append(QStringLiteral("%1 paths were laid out before they were watched").arg(taken_late_));
        const QStringList later = after.areas();
        for (const QString& area : later)
            if (!seenLayout(area, false)) out.append(QStringLiteral("no filled layout of %1 was seen").arg(area));
        for (const QString& area : before.areas()) {
            const bool visible = (area == kResidual ? residual_ : main_)->isVisible();
            if (visible && !later.contains(area) && !seenLayout(area, true)) out.append(QStringLiteral("no empty layout of %1 was seen").arg(area));
            for (const QString& axis : axes.split(QStringLiteral(", "), Qt::SkipEmptyParts)) {
                const QStringList words = axis.split(u' ');
                if ((words.first() == QLatin1String("residual")) != (area == kResidual)) continue;
                if (std::none_of(records_.begin(), records_.end(), [&](const Record& record) {
                        return !record.layout && record.phase == phase && record.area == area && record.event == words.last();
                    }))
                    out.append(QStringLiteral("%1 was not seen on the changing %2").arg(area, axis));
            }
        }
        return out;
    }

    // The residual's own range moves with the panes' heights: its band has to be empty each time (ADR-0044).
    QStringList residualLimitProblems() const {
        int ends = 0, filled = 0;
        for (const Record& record : records_) {
            if (record.layout || record.area != kResidual || record.event != QLatin1String("axisY")) continue;
            ++ends;
            filled += record.edges.empty() ? 0 : 1;
        }
        if (ends < 2) return {QStringLiteral("the residual's range was not seen to change")};
        if (filled > 0) return {QStringLiteral("the residual's band was filled at %1 of %2 changes of its limits").arg(filled).arg(ends)};
        return {};
    }

    // Each named area drawn, and no other: its points and the shape Qt laid out from them.
    QStringList settledProblems(const Shown& shown) const {
        QStringList out;
        QStringList wanted = shown.areas();
        for (const Area& area : areas()) {
            const bool want = wanted.removeAll(area.name) > 0;
            const Edges edges = edgesOf(area);
            const AxisRange axis = rangeOf(area.view);
            const auto usable = [](const QList<QPointF>& points) {
                return std::count_if(points.begin(), points.end(), [](const QPointF& p) { return std::isfinite(p.x()) && std::isfinite(p.y()); });
            };
            if (!want) {
                if (!edges.empty()) out.append(QStringLiteral("%1 should hold nothing and holds %2 points").arg(area.name).arg(edges.upper.size()));
                if (area.view->isVisible() && !drawn(area).empty()) out.append(area.name + QStringLiteral(" should not be drawn"));
                continue;
            }
            if (usable(edges.upper) < 2 || usable(edges.lower) < 2) {
                out.append(area.name + QStringLiteral(" has nothing to draw"));
                continue;
            }
            const QString held = shown.problem(area.name, edges, axis);
            if (!held.isEmpty()) out.append(area.name + u' ' + held);
            const Edges shape = drawn(area);
            if (!area.view->isVisible() || shape.empty()) out.append(area.name + QStringLiteral(" is not drawn"));
            else if (const QString bad = shown.problem(area.name, shape, axis); !bad.isEmpty())
                out.append(area.name + QStringLiteral(" is drawn and ") + bad);
            int inside = 0;
            for (const QPointF& point : shape.upper) inside += point.x() >= axis.xMin && point.x() <= axis.xMax ? 1 : 0;
            if (inside < 2) out.append(area.name + QStringLiteral(" is drawn outside the plot"));
        }
        for (const QString& missing : wanted) out.append(missing + QStringLiteral(" does not exist"));
        return out;
    }

   private slots:
    // The shape reports a new path as it takes it, before the path's first layout.
    void watchPaths() {
        for (QQuickItem* view : {main_.data(), residual_.data()}) {
            const QQuickItem* shape = shapeOf(view);
            if (!shape) continue;
            connect(shape, SIGNAL(boundingRectChanged()), this, SLOT(watchPaths()), Qt::UniqueConnection);
            for (QQuickPath* path : pathsOf(view)) {
                if (watched_.contains(path)) continue;
                watched_.insert(path);
                if (recording_) (path->path().isEmpty() ? taken_early_ : taken_late_) += 1;
                connect(path, &QQuickPath::changed, this, [this, view, path] { laidOut(view, path); });
            }
        }
    }

   private:
    static QQuickItem* shapeOf(const QQuickItem* view) {
        for (QQuickItem* child : view->childItems()) {
            if (QByteArrayView(child->metaObject()->className()) != "AreaRenderer") continue;
            for (QQuickItem* shape : child->childItems())
                if (shape->inherits("QQuickShape")) return shape;
        }
        return nullptr;
    }
    static QList<QQuickPath*> pathsOf(const QQuickItem* view) {
        const QQuickItem* shape = shapeOf(view);
        return shape ? shape->findChildren<QQuickPath*>(Qt::FindDirectChildrenOnly) : QList<QQuickPath*>{};
    }
    // The points of a laid out area, back from pixels on the axes it was laid out on.
    static Edges edgesOf(const QQuickPath* path, const AxisRange& axis) {
        const auto* shape = qobject_cast<const QQuickItem*>(path->parent());
        if (!shape || !shape->parentItem()) return {};
        const double width = shape->parentItem()->width(), height = shape->parentItem()->height();
        if (!(width > 0.0) || !(height > 0.0)) return {};
        QList<QPointF> points;
        const QPainterPath drawing = path->path();
        for (int k = 0; k < drawing.elementCount(); ++k) {
            const auto element = drawing.elementAt(k);
            if (k > 0 && element.isMoveTo()) continue;
            points.append(QPointF(axis.xMin + element.x / width * (axis.xMax - axis.xMin),
                                  axis.yMin + (height - element.y) / height * (axis.yMax - axis.yMin)));
        }
        Edges out;
        const qsizetype count = points.size() / 2;  // the upper edge, the lower one backwards, the first point again
        if (count < 2) return out;
        out.upper = points.first(count);
        out.lower = points.sliced(count, count);
        std::reverse(out.lower.begin(), out.lower.end());
        return out;
    }
    // A view lays out its areas in the order it lists them, each into the next shape path.
    Edges drawn(const Area& wanted) const {
        const QList<QQuickPath*> paths = pathsOf(wanted.view);
        qsizetype place = 0;
        for (const Area& area : areas()) {
            if (area.view != wanted.view) continue;
            if (area.series == wanted.series) return place < paths.size() ? edgesOf(paths[place], rangeOf(wanted.view)) : Edges{};
            ++place;
        }
        return {};
    }
    void laidOut(QQuickItem* view, QQuickPath* path) {
        if (!recording_) return;
        noteAreas();
        const qsizetype place = pathsOf(view).indexOf(path);
        qsizetype at = 0;
        for (const Area& area : areas()) {
            if (area.view != view || at++ != place) continue;
            const auto* shape = qobject_cast<const QQuickItem*>(path->parent());
            const QRectF bounds = path->path().boundingRect();
            const double beyond = std::max({0.0, -bounds.left(), -bounds.top(), bounds.right() - shape->parentItem()->width(),
                                            bounds.bottom() - shape->parentItem()->height()});
            records_.append({true, area.name, QStringLiteral("layout"), edgesOf(path, rangeOf(view)), rangeOf(view), beyond, main_moved_, line_->points(), phase_, area.series, outgoing(area)});
        }
    }
    // Of two areas with one name the one seen later has taken the other's place.
    void noteAreas() {
        for (const Area& area : areas()) {
            if (std::any_of(known_.begin(), known_.end(), [&area](const QPointer<QAreaSeries>& each) { return each == area.series; })) continue;
            known_.append(area.series);
            newest_[area.name] = area.series;
        }
    }
    bool outgoing(const Area& area) const {
        const auto newest = newest_.find(area.name);
        return newest != newest_.end() && newest->second && newest->second != area.series;
    }
    void attached(QQuickItem* view, const char* axis) {
        if (!recording_) return;
        main_moved_ = main_moved_ || view == main_;
        noteAreas();
        for (const Area& area : areas())
            if (area.view == view) records_.append({false, area.name, QLatin1String(axis), edgesOf(area), rangeOf(view), 0, main_moved_, line_->points(), phase_, area.series, outgoing(area)});
    }

    QQmlEngine engine_;
    QQuickWindow window_;
    std::unique_ptr<QQuickItem> root_;
    QPointer<edi_app::PatternChartController> controller_;
    QPointer<QQuickItem> main_, residual_;
    edi_app::ProjectViewModel* project_ = nullptr;
    QString error_;
    QPointer<QLineSeries> line_;
    bool recording_ = false, main_moved_ = false;
    int phase_ = 0;
    QList<std::pair<AxisRange, AxisRange>> ends_;  // each phase's last ranges, the main pane's and the residual's
    QList<QPointer<QAreaSeries>> known_;
    std::map<QString, QPointer<QAreaSeries>> newest_;
    int taken_early_ = 0, taken_late_ = 0;  // paths watched before their first layout, and after it
    QList<Record> records_;
    QSet<QQuickPath*> watched_;
};

namespace {

edi_app::ParameterItem* parameterEnding(edi_app::ProjectViewModel& model, const char* ending) {
    edi::Project names = model.project();
    for (const edi::NamedSlot& slot : edi::named_slots(names))
        if (slot.unique_name.ends_with(ending)) return model.parameterNamed(QString::fromStdString(slot.unique_name));
    return nullptr;
}

}  // namespace

// Judges what was recorded since start(), then the settled chart, and keeps what is wrong for the test's end. `axes` are
// those the step has to move.
#define CHECK_CHANGE(step, chart, before, after, axes)                                                                  \
    do {                                                                                                               \
        QVERIFY((chart).settle());                                                                                     \
        (chart).stop();                                                                                                \
        qInfo("%s: %lld layouts and %lld areas on changing axes seen", step, static_cast<long long>((chart).seen(true)), \
              static_cast<long long>((chart).seen(false)));                                                            \
        for (const QString& found : (chart).problems((before), (after), (chart).phase()) +                             \
                                        (chart).unseen((before), (after), QStringLiteral(axes), (chart).phase()) +     \
                                        (chart).settledProblems(after))                                                \
            wrong.append(QLatin1String(step) + QStringLiteral(": ") + found);                                          \
    } while (false)
#define VERIFY_NOTHING_WRONG() QVERIFY2(wrong.isEmpty(), qPrintable(QLatin1Char('\n') + wrong.join(QLatin1Char('\n'))))

class ChartAreaTests : public QObject {
    Q_OBJECT
   private slots:
    void initTestCase() {
        QCOMPARE(measuredRows(QStringLiteral("cw")).size(), std::size_t(161));
        QCOMPARE(measuredRows(QStringLiteral("tof")).size(), std::size_t(161));
    }

    // A created experiment has no measured data, so its beam mode can still be changed.
    void beamMode() {
        edi::Project project = fixtureProject(QStringLiteral("cw"));
        project.experiments.erase_at(0);
        edi::ExperimentTypeTokens type;
        type.sample_form = "powder";
        type.beam_mode = "constant wavelength";
        type.radiation_probe = "neutron";
        type.scattering_type = "bragg";
        project.experiments.push_back(edi::simulation_experiment("pattern", type, "phase"));
        edi_app::ProjectViewModel model(std::move(project), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(model.project().experiment());
        QVERIFY(angle.greatest() < 180.0);
        QCOMPARE(angle.structures.size(), std::size_t(1));
        QCOMPARE(chart.settledProblems(angle), QStringList());
        QStringList wrong;

        chart.start();
        QVERIFY2(model.setExperimentType(0, QStringLiteral("beamMode"), QStringLiteral("time-of-flight")), qPrintable(model.lastError()));
        QVERIFY(chart.settle());
        const Shown flight = shownOf(model.project().experiment());
        QVERIFY(flight.least() > 100.0);
        QCOMPARE(flight.structures.size(), std::size_t(1));
        CHECK_CHANGE("to time of flight", chart, angle, flight, "main axisX, main axisY");

        chart.start();
        QVERIFY2(model.setExperimentType(0, QStringLiteral("beamMode"), QStringLiteral("constant wavelength")), qPrintable(model.lastError()));
        CHECK_CHANGE("to constant wavelength", chart, flight, angle, "main axisX, main axisY");
        VERIFY_NOTHING_WRONG();
    }

    void experimentChoice() {
        edi_app::ProjectViewModel model(twoPatterns(), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(*model.project().experiments[0], measuredRows(QStringLiteral("cw")));
        QCOMPARE(chart.settledProblems(angle), QStringList());
        QStringList wrong;
        Shown flight;
        // The second structure's area is made and laid out for the first time in the first round.
        QVERIFY(!chart.hasArea(structureArea(1)));
        for (int round = 0; round < 2; ++round) {
            chart.start();
            model.setCurrentExperimentIndex(1);
            QVERIFY(chart.settle());
            flight = shownOf(*model.project().experiments[1], measuredRows(QStringLiteral("tof")));
            QCOMPARE(flight.structures.size(), std::size_t(2));
            qInfo("round %d: %d new paths", round, chart.newPaths());
            CHECK_CHANGE("to time of flight", chart, angle, flight, "main axisX, main axisY, residual axisX, residual axisY");
            chart.start();
            model.setCurrentExperimentIndex(0);
            CHECK_CHANGE("to 2 theta", chart, flight, angle, "main axisX, main axisY, residual axisX, residual axisY");
        }
        VERIFY_NOTHING_WRONG();
    }

    // The second structure's area is made, and the axes move on before anything else happens.
    void axesMoveAsAreasAreMade_data() {
        QTest::addColumn<bool>("back");
        QTest::newRow("back to the other experiment") << true;
        QTest::newRow("zoomed") << false;
    }
    void axesMoveAsAreasAreMade() {
        QFETCH(bool, back);
        edi_app::ProjectViewModel model(twoPatterns(), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(*model.project().experiments[0], measuredRows(QStringLiteral("cw")));
        const Shown flight = shownOf(*model.project().experiments[1], measuredRows(QStringLiteral("tof")));
        QCOMPARE(flight.structures.size(), std::size_t(2));
        QVERIFY(flight.calculated.size() == flight.x.size());
        QCOMPARE(chart.settledProblems(angle), QStringList());
        QVERIFY(!chart.hasArea(structureArea(1)));
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        QStringList wrong;
        chart.start();
        model.setCurrentExperimentIndex(1);
        QVERIFY(chart.hasArea(structureArea(1)));
        chart.next();
        if (back) model.setCurrentExperimentIndex(0);
        else chart.controller()->zoomTo(0.4 * plot.width(), 0.45 * plot.width(), 0, plot.height());
        QVERIFY(chart.settle());
        chart.stop();
        for (const QString& found : chart.problems(angle, flight, 0)) wrong.append(QStringLiteral("to time of flight: ") + found);
        CHECK_CHANGE("moved on", chart, flight, back ? angle : flight, "main axisX, residual axisX");
        VERIFY_NOTHING_WRONG();
    }

    void structureLinked() {
        edi::Project project = fixtureProject(QStringLiteral("cw"));
        auto second = *project.structures.front();
        second.name = "phase2";
        project.structures.push_back(second);
        edi_app::ProjectViewModel model(std::move(project), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        const Shown one = shownOf(model.project().experiment(), rows);
        QCOMPARE(chart.settledProblems(one), QStringList());
        QVERIFY(!chart.hasArea(structureArea(1)));
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        // The drawing that makes the new area is the calculation's, so the zoom follows it at once.
        bool zoomed = false;
        connect(chart.controller(), &edi_app::PatternChartController::revisionChanged, &chart, [&] {
            if (zoomed || !chart.hasArea(structureArea(1))) return;
            zoomed = true;
            chart.next();
            chart.controller()->zoomTo(0.4 * plot.width(), 0.45 * plot.width(), 0, plot.height());
        });
        chart.start();
        model.currentExperiment()->linkedStructures()->append();
        QVERIFY(chart.settle());
        QVERIFY(zoomed);
        chart.stop();
        const Shown both = shownOf(model.project().experiment(), rows);
        QCOMPARE(both.structures.size(), std::size_t(2));
        QStringList wrong;
        for (const QString& found : chart.problems(one, both, 0)) wrong.append(QStringLiteral("linked: ") + found);
        CHECK_CHANGE("moved on", chart, both, both, "main axisX, residual axisX");
        VERIFY_NOTHING_WRONG();
    }

    void structureUnlinked() {
        edi::Project project = fixtureProject(QStringLiteral("cw"));
        auto second = *project.structures.front();
        second.name = "phase2";
        project.structures.push_back(second);
        edi::LinkedStructure link;
        link.structure_id = "phase2";
        project.experiment().linked_structures.push_back(link);
        edi_app::ProjectViewModel model(std::move(project), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        const Shown both = shownOf(model.project().experiment(), rows);
        QCOMPARE(both.structures.size(), std::size_t(2));
        QCOMPARE(chart.settledProblems(both), QStringList());
        QStringList wrong;
        chart.start();
        model.currentExperiment()->linkedStructures()->remove(1);
        QVERIFY(chart.settle());
        const Shown one = shownOf(model.project().experiment(), rows);
        QCOMPARE(one.structures.size(), std::size_t(1));
        CHECK_CHANGE("unlinked", chart, both, one, "main axisY, residual axisY");
        VERIFY_NOTHING_WRONG();
    }

    void zoomPanReset() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        const AxisRange full = WatchedChart::rangeOf(chart.mainView());
        QStringList wrong;

        chart.start();
        chart.controller()->zoomTo(0.4 * plot.width(), 0.45 * plot.width(), 0, plot.height());
        CHECK_CHANGE("zoom", chart, shown, shown, "main axisX, residual axisX");
        const AxisRange zoomed = WatchedChart::rangeOf(chart.mainView());
        QVERIFY(close(zoomed.xMax - zoomed.xMin, 0.05 * (full.xMax - full.xMin), 1e-3));

        chart.start();
        chart.controller()->panBy(0.75 * plot.width());
        CHECK_CHANGE("pan", chart, shown, shown, "main axisX, residual axisX");
        QVERIFY(WatchedChart::rangeOf(chart.mainView()).xMin < zoomed.xMin);

        chart.start();
        chart.controller()->reset();
        CHECK_CHANGE("reset", chart, shown, shown, "main axisX, residual axisX");
        QVERIFY(close(WatchedChart::rangeOf(chart.mainView()).xMin, shown.least()) && close(WatchedChart::rangeOf(chart.mainView()).xMax, shown.greatest()));
        VERIFY_NOTHING_WRONG();
    }

    void xAxisQuantity() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        const Shown spacing = onDSpacing(angle, 1.54);
        QStringList wrong;
        chart.start();
        model.setPatternXAxis(QStringLiteral("d_spacing"));
        CHECK_CHANGE("to d", chart, angle, spacing, "main axisX, residual axisX");
        chart.start();
        model.setPatternXAxis(QStringLiteral("native"));
        CHECK_CHANGE("to 2 theta", chart, spacing, angle, "main axisX, residual axisX");
        VERIFY_NOTHING_WRONG();
    }

    void yScale() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown linear = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        Shown root = linear;
        root.squareRoot = true;
        const double reach = WatchedChart::rangeOf(chart.residualView()).yMax;
        QStringList wrong;
        chart.start();
        chart.setYScale("sqrt");
        CHECK_CHANGE("to square root", chart, linear, root, "main axisY, residual axisY");
        QVERIFY(!close(WatchedChart::rangeOf(chart.residualView()).yMax, reach));
        chart.start();
        chart.setYScale("linear");
        CHECK_CHANGE("to linear", chart, root, linear, "main axisY, residual axisY");
        QVERIFY(close(WatchedChart::rangeOf(chart.residualView()).yMax, reach));
        VERIFY_NOTHING_WRONG();
    }

    // The residual has the main pane's scale on a linear axis, so its range follows the panes' heights.
    static bool residualFollowsMain(const WatchedChart& chart) {
        const AxisRange main = WatchedChart::rangeOf(chart.mainView()), residual = WatchedChart::rangeOf(chart.residualView());
        return close((main.yMax - main.yMin) / main.height, (residual.yMax - residual.yMin) / residual.height, 1e-3);
    }

    void residualResized() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        QVERIFY(residualFollowsMain(chart));
        QCOMPARE(chart.settledProblems(shown), QStringList());
        QStringList wrong;
        for (const QSize& size : {QSize(1000, 480), QSize(1100, 660)}) {
            const double reach = WatchedChart::rangeOf(chart.residualView()).yMax;
            chart.start();
            chart.resize(size.width(), size.height());
            CHECK_CHANGE("resize", chart, shown, shown, "residual axisY");
            wrong += chart.residualLimitProblems();
            QVERIFY(WatchedChart::rangeOf(chart.residualView()).yMax != reach);
            QVERIFY(residualFollowsMain(chart));
        }
        VERIFY_NOTHING_WRONG();
    }

    void residualHiddenAndShown() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        Shown hidden = shown;
        hidden.residual = false;
        QStringList wrong;
        QCOMPARE(chart.settledProblems(shown), QStringList());
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("resid"));
        CHECK_CHANGE("hidden", chart, shown, hidden, "residual axisY");
        wrong += chart.residualLimitProblems();
        QVERIFY(!chart.residualView()->isVisible());
        // Resized while hidden, so the axis it comes back on is another one.
        chart.resize(1000, 480);
        QVERIFY(chart.settle());
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("resid"));
        CHECK_CHANGE("shown", chart, hidden, shown, "");
        wrong += chart.residualLimitProblems();
        QVERIFY(residualFollowsMain(chart));
        VERIFY_NOTHING_WRONG();
    }

    void measuredHidden() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        QCOMPARE(chart.settledProblems(shown), QStringList());
        Shown hidden = shown;
        hidden.measuredBand = false;
        QStringList wrong;
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("meas"));
        CHECK_CHANGE("hidden", chart, shown, hidden, "");
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("meas"));
        CHECK_CHANGE("shown", chart, hidden, shown, "");
        VERIFY_NOTHING_WRONG();
    }

    // A wavelength moves the measured rows along a d axis, so a held slider has to move the band with them.
    void heldWavelength() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        model.setPatternXAxis(QStringLiteral("d_spacing"));
        QVERIFY(chart.settle());
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        chart.controller()->zoomTo(0.05 * plot.width(), 0.3 * plot.width(), 0.02 * plot.height(), 0.98 * plot.height());
        QVERIFY(chart.settle());
        Shown before = onDSpacing(shownOf(model.project().experiment(), rows), 1.54);
        QCOMPARE(chart.settledProblems(before), QStringList());
        const AxisRange zoomed = WatchedChart::rangeOf(chart.mainView());
        auto* wavelength = parameterEnding(model, "setup_wavelength");
        QVERIFY(wavelength);

        QStringList wrong;
        model.setAdjusting(true);
        for (const double value : {1.56, 1.61}) {
            chart.start();
            wavelength->setValue(value);
            QVERIFY(chart.settle());
            const AxisRange now = WatchedChart::rangeOf(chart.mainView());
            QVERIFY(now.xMin == zoomed.xMin && now.xMax == zoomed.xMax && now.yMin == zoomed.yMin && now.yMax == zoomed.yMax);
            const Shown full = onDSpacing(shownOf(model.project().experiment(), rows), value);
            // The step was drawn: the calculated line is already at the new wavelength.
            QVERIFY(chart.calculatedLine()->points().size() > 2);
            QVERIFY(full.hasLine(chart.calculatedLine()->points()) && !before.hasLine(chart.calculatedLine()->points()));
            const Shown during = held(full);
            CHECK_CHANGE("held", chart, before, during, "");
            before = during;
        }
        const Shown after = onDSpacing(shownOf(model.project().experiment(), rows), 1.61);
        chart.start();
        model.setAdjusting(false);
        QVERIFY(chart.settle());
        CHECK_CHANGE("released", chart, before, after, "");
        VERIFY_NOTHING_WRONG();
    }

    // The same rows and background with other calculated intensities.
    void scaleEdited() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        auto* scale = parameterEnding(model, ".scale");
        QVERIFY(scale);
        QStringList wrong;
        for (const double value : {4.0 * scale->value(), scale->value()}) {
            const Shown from = shownOf(model.project().experiment(), rows);
            chart.start();
            scale->setValue(value);
            QVERIFY(chart.settle());
            const Shown to = shownOf(model.project().experiment(), rows);
            QVERIFY(!from.sameLine(to));
            CHECK_CHANGE("edited", chart, from, to, "main axisY, residual axisY");
        }
        VERIFY_NOTHING_WRONG();
    }

    // A held slider's first step that raises the fitted y range.
    void heldScale() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        WatchedChart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        const Shown before = shownOf(model.project().experiment(), rows);
        const double top = WatchedChart::rangeOf(chart.mainView()).yMax;
        auto* scale = parameterEnding(model, ".scale");
        QVERIFY(scale);
        QStringList wrong;
        model.setAdjusting(true);
        chart.start();
        scale->setValue(4.0 * scale->value());
        QVERIFY(chart.settle());
        const Shown full = shownOf(model.project().experiment(), rows);
        QVERIFY(WatchedChart::rangeOf(chart.mainView()).yMax > 1.2 * top);
        CHECK_CHANGE("held", chart, before, held(full), "main axisY, residual axisY");
        chart.start();
        model.setAdjusting(false);
        QVERIFY(chart.settle());
        CHECK_CHANGE("released", chart, held(full), shownOf(model.project().experiment(), rows), "");
        VERIFY_NOTHING_WRONG();
    }
};

int main(int argc, char** argv) {
    std::printf("edi_chart_area_tests: built at %s\n", edi::build_commit());
    std::fflush(stdout);
    QGuiApplication app(argc, argv);
    edi_app::use_design_font();
    edi_app::use_fresh_settings();
    ChartAreaTests tests;
    return QTest::qExec(&tests, argc, argv);
}
#include "chart_area_tests.moc"

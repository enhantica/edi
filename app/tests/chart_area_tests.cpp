// SPDX-License-Identifier: BSD-3-Clause
// The pattern chart's filled areas through changes of its axes. Every area Qt Graphs lays out, and every area attached
// to an axis that changes, must be empty or hold the points of the pattern the axis is for. The expected points come
// from the fixture files' rows and Bragg's law.
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
const QString kCalculatedBars = QStringLiteral("chart.series.calc.bars");
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
    bool squareRoot = false;

    double display(double value) const { return squareRoot ? std::copysign(std::sqrt(std::fabs(value)), value) : value; }
    double least() const { return *std::min_element(x.begin(), x.end()); }
    double greatest() const { return *std::max_element(x.begin(), x.end()); }
    double top() const {
        double out = 0.0;
        for (std::size_t k = 0; k < measured.size(); ++k) out = std::max(out, display(measured[k] + su[k]));
        for (const double value : calculated) out = std::max(out, display(value));
        return out;
    }
    bool shows(const QString& area) const {
        if (area == kMeasured) return !measured.empty();
        if (area == kResidual) return residual;
        for (std::size_t k = 0; k < structures.size(); ++k)
            if (area == structureArea(int(k))) return true;
        return false;
    }
    // Whether an x range lies in this pattern's.
    bool spans(const AxisRange& axis) const {
        const double slack = 1e-6 * (greatest() - least());
        return axis.xMax > axis.xMin && axis.xMin >= least() - slack && axis.xMax <= greatest() + slack;
    }

    // What is wrong with an area's points on an axis; nothing when they are this pattern's.
    QString problem(const QString& area, const Edges& edges, const AxisRange& axis, bool withCalculated) const {
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
            if (area == kMeasured) {
                const double top = display(measured[row] + su[row]), bottom = display(measured[row] - su[row]);
                if (!close(low.y(), bottom)) return wrong("lower", low.y(), bottom);
                if (!close(up.y(), top) && (up.y() < top || up.y() > bottom + thin)) return wrong("upper", up.y(), top);
            } else if (area == kResidual) {
                if (!close(up.y() - low.y(), 2.0 * su[row], 1e-4)) return wrong("upper", up.y(), low.y() + 2.0 * su[row]);
                const double centre = measured[row] - calculated[row];
                if (withCalculated && !close(0.5 * (up.y() + low.y()), centre, 1e-5)) return wrong("lower", low.y(), centre - su[row]);
            } else {
                const double base = display(background[row]);
                if (!close(low.y(), base, 1e-5)) return wrong("lower", low.y(), base);
                const std::size_t place = area.mid(structureArea(0).size() - 1).toULongLong();
                const double top = display(background[row] + structures[place][row]);
                if (withCalculated && !close(up.y(), top, 1e-5) && (up.y() < top || up.y() > base + thin))
                    return wrong("upper", up.y(), top);
                if (up.y() < low.y()) return wrong("upper", up.y(), top);
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

// A chart in a window, and what Qt Graphs is given and lays out while something changes.
class Chart : public QObject {
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
    };

    explicit Chart(edi_app::ProjectViewModel& project) {
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
    ~Chart() override { root_.reset(); }

    const QString& error() const { return error_; }
    edi_app::PatternChartController* controller() const { return controller_; }
    QQuickItem* mainView() const { return main_; }
    QQuickItem* residualView() const { return residual_; }
    const QLineSeries* lineSeries(const QString& name) const { return root_->findChild<QLineSeries*>(name); }
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
        watch();
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

    void start() {
        records_.clear();
        recording_ = true;
    }
    void stop() { recording_ = false; }
    qsizetype seen(bool layout) const {
        return std::count_if(records_.begin(), records_.end(), [layout](const Record& record) { return record.layout == layout; });
    }

    // The recorded areas that were neither empty nor of the pattern the axes were for. A layout may show either
    // state, as its axes say; an area on an axis that is changing must already be the later one's.
    QStringList problems(const Shown& before, const Shown& after) const {
        QStringList out;
        // Two y scales show the same rows, and their fitted y ranges tell them apart.
        const bool scales = before.squareRoot != after.squareRoot;
        std::map<QString, int> layouts, changes;
        std::map<QString, double> distances;
        for (const Record& record : records_) {
            if (record.edges.empty()) continue;
            QString problem;
            if (record.layout) {
                problem = QStringLiteral("is on axes that no pattern is on");
                for (const Shown* shown : {&before, &after}) {
                    if (!shown->spans(record.axis)) continue;
                    const bool residual = record.area == kResidual;
                    if (scales && !residual && (record.axis.yMax < 0.5 * shown->top() || record.axis.yMax > 2.0 * shown->top())) continue;
                    problem = shown->problem(record.area, record.edges, record.axis, false);
                    if (problem.isEmpty()) break;
                }
            } else {
                problem = after.problem(record.area, record.edges, record.axis, true);
                // An axis published end by end holds neither range in between: the points are judged on their own.
                if (problem.contains(QLatin1String("in view")) || problem.contains(QLatin1String("the view"))) {
                    AxisRange whole = record.axis;
                    const AxisRange now = rangeOf(record.area == kResidual ? residual_ : main_);
                    whole.xMin = now.xMin;
                    whole.xMax = now.xMax;
                    problem = after.problem(record.area, record.edges, whole, true);
                }
            }
            if (problem.isEmpty()) continue;
            int& count = record.layout ? layouts[record.area] : changes[record.area];
            if (record.layout) distances[record.area] = std::max(distances[record.area], record.beyond);
            if (++count == 1)
                out.append(QStringLiteral("%1 (%2; %3) %4").arg(record.area, record.event, record.axis.text(), problem));
        }
        for (const auto& [area, count] : layouts) out.append(QStringLiteral("%1 layouts of %2, up to %3 px outside the plot").arg(count).arg(area).arg(distances[area]));
        for (const auto& [area, count] : changes) out.append(QStringLiteral("%1 axis changes over %2").arg(count).arg(area));
        return out;
    }

    // Each named area drawn, and no other: its points and the shape Qt laid out from them.
    QStringList settledProblems(const Shown& shown) const {
        QStringList out;
        QStringList wanted;
        if (!shown.measured.empty()) wanted.append(kMeasured);
        if (shown.residual) wanted.append(kResidual);
        for (std::size_t k = 0; k < shown.structures.size(); ++k) wanted.append(structureArea(int(k)));
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
            const QString held = shown.problem(area.name, edges, axis, true);
            if (!held.isEmpty()) out.append(area.name + u' ' + held);
            const Edges shape = drawn(area);
            if (!area.view->isVisible() || shape.empty()) out.append(area.name + QStringLiteral(" is not drawn"));
            else if (const QString bad = shown.problem(area.name, shape, axis, true); !bad.isEmpty())
                out.append(area.name + QStringLiteral(" is drawn and ") + bad);
            int inside = 0;
            for (const QPointF& point : shape.upper) inside += point.x() >= axis.xMin && point.x() <= axis.xMax ? 1 : 0;
            if (inside < 2) out.append(area.name + QStringLiteral(" is drawn outside the plot"));
        }
        for (const QString& missing : wanted) out.append(missing + QStringLiteral(" does not exist"));
        return out;
    }

   private:
    static QList<QQuickPath*> pathsOf(const QQuickItem* view) {
        for (QQuickItem* child : view->childItems()) {
            if (QByteArrayView(child->metaObject()->className()) != "AreaRenderer") continue;
            for (QObject* shape : child->children())
                if (shape->inherits("QQuickShape")) return shape->findChildren<QQuickPath*>(Qt::FindDirectChildrenOnly);
            for (QQuickItem* shape : child->childItems())
                if (shape->inherits("QQuickShape")) return shape->findChildren<QQuickPath*>(Qt::FindDirectChildrenOnly);
        }
        return {};
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
    void watch() {
        for (QQuickItem* view : {main_, residual_}) {
            for (QQuickPath* path : pathsOf(view)) {
                if (watched_.contains(path)) continue;
                watched_.insert(path);
                connect(path, &QQuickPath::changed, this, [this, view, path] { laidOut(view, path); });
            }
        }
    }
    void laidOut(QQuickItem* view, QQuickPath* path) {
        if (!recording_) return;
        const qsizetype place = pathsOf(view).indexOf(path);
        qsizetype at = 0;
        for (const Area& area : areas()) {
            if (area.view != view || at++ != place) continue;
            const auto* shape = qobject_cast<const QQuickItem*>(path->parent());
            const QRectF bounds = path->path().boundingRect();
            const double beyond = std::max({0.0, -bounds.left(), -bounds.top(), bounds.right() - shape->parentItem()->width(),
                                            bounds.bottom() - shape->parentItem()->height()});
            records_.append({true, area.name, QStringLiteral("layout"), edgesOf(path, rangeOf(view)), rangeOf(view), beyond});
        }
    }
    void attached(QQuickItem* view, const char* axis) {
        if (!recording_) return;
        for (const Area& area : areas())
            if (area.view == view) records_.append({false, area.name, QLatin1String(axis) + QStringLiteral(" changed"), edgesOf(area), rangeOf(view)});
    }

    QQmlEngine engine_;
    QQuickWindow window_;
    std::unique_ptr<QQuickItem> root_;
    QPointer<edi_app::PatternChartController> controller_;
    QPointer<QQuickItem> main_, residual_;
    edi_app::ProjectViewModel* project_ = nullptr;
    QString error_;
    bool recording_ = false;
    QList<Record> records_;
    QSet<QQuickPath*> watched_;
};

edi_app::ParameterItem* parameterEnding(edi_app::ProjectViewModel& model, const char* ending) {
    edi::Project names = model.project();
    for (const edi::NamedSlot& slot : edi::named_slots(names))
        if (slot.unique_name.ends_with(ending)) return model.parameterNamed(QString::fromStdString(slot.unique_name));
    return nullptr;
}

}  // namespace

// Judges what was recorded since start(), then the settled chart, and keeps what is wrong for the test's end.
#define CHECK_CHANGE(step, chart, before, after)                                                                       \
    do {                                                                                                               \
        QVERIFY((chart).settle());                                                                                     \
        (chart).stop();                                                                                                \
        qInfo("%s: %lld layouts and %lld areas on changing axes seen", step, static_cast<long long>((chart).seen(true)), \
              static_cast<long long>((chart).seen(false)));                                                            \
        for (const QString& found : (chart).problems((before), (after)) + (chart).settledProblems(after))            \
            wrong.append(QLatin1String(step) + QStringLiteral(": ") + found);                                           \
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
        Chart chart(model);
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
        CHECK_CHANGE("to time of flight", chart, angle, flight);

        chart.start();
        QVERIFY2(model.setExperimentType(0, QStringLiteral("beamMode"), QStringLiteral("constant wavelength")), qPrintable(model.lastError()));
        CHECK_CHANGE("to constant wavelength", chart, flight, angle);
        VERIFY_NOTHING_WRONG();
    }

    void experimentChoice() {
        edi::Project project = fixtureProject(QStringLiteral("cw"));
        const edi::Project other = fixtureProject(QStringLiteral("tof"));
        auto second = *project.structures.front();
        second.name = "phase2";
        project.structures.push_back(second);
        auto flightExperiment = *other.experiments.front();
        flightExperiment.name = "flight";
        // Two rows of Bragg ticks beside one: the panes' heights change with the axes.
        edi::LinkedStructure link;
        link.structure_id = "phase2";
        flightExperiment.linked_structures.push_back(link);
        project.experiments.push_back(flightExperiment);
        edi_app::ProjectViewModel model(std::move(project), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(*model.project().experiments[0], measuredRows(QStringLiteral("cw")));
        QCOMPARE(chart.settledProblems(angle), QStringList());
        // Seen once, so the second structure's area exists.
        model.setCurrentExperimentIndex(1);
        QVERIFY(chart.settle());
        const Shown flight = shownOf(*model.project().experiments[1], measuredRows(QStringLiteral("tof")));
        QCOMPARE(flight.structures.size(), std::size_t(2));
        QCOMPARE(chart.settledProblems(flight), QStringList());
        QStringList wrong;
        chart.start();
        model.setCurrentExperimentIndex(0);
        CHECK_CHANGE("to 2 theta", chart, flight, angle);
        chart.start();
        model.setCurrentExperimentIndex(1);
        CHECK_CHANGE("to time of flight", chart, angle, flight);
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
        Chart chart(model);
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
        CHECK_CHANGE("unlinked", chart, both, one);
        VERIFY_NOTHING_WRONG();
    }

    void zoomPanReset() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        const AxisRange full = Chart::rangeOf(chart.mainView());
        QStringList wrong;

        chart.start();
        chart.controller()->zoomTo(0.4 * plot.width(), 0.45 * plot.width(), 0, plot.height());
        CHECK_CHANGE("zoom", chart, shown, shown);
        const AxisRange zoomed = Chart::rangeOf(chart.mainView());
        QVERIFY(close(zoomed.xMax - zoomed.xMin, 0.05 * (full.xMax - full.xMin), 1e-3));

        chart.start();
        chart.controller()->panBy(0.75 * plot.width());
        CHECK_CHANGE("pan", chart, shown, shown);
        QVERIFY(Chart::rangeOf(chart.mainView()).xMin < zoomed.xMin);

        chart.start();
        chart.controller()->reset();
        CHECK_CHANGE("reset", chart, shown, shown);
        QVERIFY(close(Chart::rangeOf(chart.mainView()).xMin, shown.least()) && close(Chart::rangeOf(chart.mainView()).xMax, shown.greatest()));
        VERIFY_NOTHING_WRONG();
    }

    void xAxisQuantity() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown angle = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        const Shown spacing = onDSpacing(angle, 1.54);
        QStringList wrong;
        chart.start();
        model.setPatternXAxis(QStringLiteral("d_spacing"));
        CHECK_CHANGE("to d", chart, angle, spacing);
        chart.start();
        model.setPatternXAxis(QStringLiteral("native"));
        CHECK_CHANGE("to 2 theta", chart, spacing, angle);
        VERIFY_NOTHING_WRONG();
    }

    void yScale() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown linear = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        Shown root = linear;
        root.squareRoot = true;
        const double reach = Chart::rangeOf(chart.residualView()).yMax;
        QStringList wrong;
        chart.start();
        chart.setYScale("sqrt");
        CHECK_CHANGE("to square root", chart, linear, root);
        QVERIFY(!close(Chart::rangeOf(chart.residualView()).yMax, reach));
        chart.start();
        chart.setYScale("linear");
        CHECK_CHANGE("to linear", chart, root, linear);
        QVERIFY(close(Chart::rangeOf(chart.residualView()).yMax, reach));
        VERIFY_NOTHING_WRONG();
    }

    // The residual has the main pane's scale on a linear axis, so its range follows the panes' heights.
    static bool residualFollowsMain(const Chart& chart) {
        const AxisRange main = Chart::rangeOf(chart.mainView()), residual = Chart::rangeOf(chart.residualView());
        return close((main.yMax - main.yMin) / main.height, (residual.yMax - residual.yMin) / residual.height, 1e-3);
    }

    void residualResized() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        QVERIFY(residualFollowsMain(chart));
        QStringList wrong;
        for (const QSize& size : {QSize(1000, 480), QSize(1100, 660)}) {
            const double reach = Chart::rangeOf(chart.residualView()).yMax;
            chart.start();
            chart.resize(size.width(), size.height());
            CHECK_CHANGE("resize", chart, shown, shown);
            QVERIFY(Chart::rangeOf(chart.residualView()).yMax != reach);
            QVERIFY(residualFollowsMain(chart));
        }
        VERIFY_NOTHING_WRONG();
    }

    void residualHiddenAndShown() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        Shown hidden = shown;
        hidden.residual = false;
        QStringList wrong;
        // Until it is hidden the residual is its own pattern's on any of its ranges.
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("resid"));
        QVERIFY(chart.settle());
        chart.stop();
        wrong += chart.problems(shown, shown);
        wrong += chart.settledProblems(hidden);
        QVERIFY(!chart.residualView()->isVisible());
        // Resized while hidden, so the axis it comes back on is another one.
        chart.resize(1000, 480);
        QVERIFY(chart.settle());
        chart.start();
        chart.controller()->toggleSeries(QStringLiteral("resid"));
        CHECK_CHANGE("shown", chart, hidden, shown);
        QVERIFY(residualFollowsMain(chart));
        VERIFY_NOTHING_WRONG();
    }

    void measuredHidden() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const Shown shown = shownOf(model.project().experiment(), measuredRows(QStringLiteral("cw")));
        chart.controller()->toggleSeries(QStringLiteral("meas"));
        QVERIFY(chart.settle());
        for (const Chart::Area& area : chart.areas())
            if (area.name == kMeasured) QVERIFY(Chart::edgesOf(area).empty());
        chart.controller()->toggleSeries(QStringLiteral("meas"));
        QVERIFY(chart.settle());
        QCOMPARE(chart.settledProblems(shown), QStringList());
    }

    // A wavelength moves the measured rows along a d axis, so a held slider has to move the band with them.
    void heldWavelength() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        model.setPatternXAxis(QStringLiteral("d_spacing"));
        QVERIFY(chart.settle());
        const QSizeF plot = chart.mainView()->property("plotArea").toRectF().size();
        chart.controller()->zoomTo(0.05 * plot.width(), 0.3 * plot.width(), 0.02 * plot.height(), 0.98 * plot.height());
        QVERIFY(chart.settle());
        Shown before = onDSpacing(shownOf(model.project().experiment(), rows), 1.54);
        QCOMPARE(chart.settledProblems(before), QStringList());
        const AxisRange zoomed = Chart::rangeOf(chart.mainView());
        auto* wavelength = parameterEnding(model, "setup_wavelength");
        QVERIFY(wavelength);
        const QLineSeries* calculated = chart.lineSeries(QStringLiteral("chart.series.calc"));
        QVERIFY(calculated);

        QStringList wrong;
        model.setAdjusting(true);
        for (const double value : {1.56, 1.61}) {
            chart.start();
            wavelength->setValue(value);
            QVERIFY(chart.settle());
            const AxisRange now = Chart::rangeOf(chart.mainView());
            QVERIFY(now.xMin == zoomed.xMin && now.xMax == zoomed.xMax && now.yMin == zoomed.yMin && now.yMax == zoomed.yMax);
            const Shown full = onDSpacing(shownOf(model.project().experiment(), rows), value);
            // The step was drawn: the calculated line is already at the new wavelength.
            const QList<QPointF> line = calculated->points();
            QVERIFY(line.size() > 2);
            for (const QPointF& point : line)
                QVERIFY(std::any_of(full.x.begin(), full.x.end(), [&point](double x) { return close(x, point.x()); }));
            const Shown during = held(full);
            CHECK_CHANGE("held", chart, before, during);
            before = during;
        }
        const Shown after = onDSpacing(shownOf(model.project().experiment(), rows), 1.61);
        chart.start();
        model.setAdjusting(false);
        QVERIFY(chart.settle());
        CHECK_CHANGE("released", chart, before, after);
        VERIFY_NOTHING_WRONG();
    }

    // A held slider's first step that raises the fitted y range.
    void heldScale() {
        edi_app::ProjectViewModel model(fixtureProject(QStringLiteral("cw")), nullptr);
        Chart chart(model);
        QVERIFY2(chart.error().isEmpty(), qPrintable(chart.error()));
        const auto rows = measuredRows(QStringLiteral("cw"));
        const Shown before = shownOf(model.project().experiment(), rows);
        const double top = Chart::rangeOf(chart.mainView()).yMax;
        auto* scale = parameterEnding(model, ".scale");
        QVERIFY(scale);
        QStringList wrong;
        model.setAdjusting(true);
        chart.start();
        scale->setValue(4.0 * scale->value());
        QVERIFY(chart.settle());
        const Shown full = shownOf(model.project().experiment(), rows);
        QVERIFY(Chart::rangeOf(chart.mainView()).yMax > 1.2 * top);
        CHECK_CHANGE("held", chart, before, held(full));
        chart.start();
        model.setAdjusting(false);
        QVERIFY(chart.settle());
        CHECK_CHANGE("released", chart, held(full), shownOf(model.project().experiment(), rows));
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

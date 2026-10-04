//  O1-O3: test-owned clocks and frame-state correlation, independent crysta reference.
#include <crysta/analysis.hpp>
#include <crysta/computed.hpp>
#include <crysta/model.hpp>
#include "../cpp/e04_t9_reference.hpp"
#include "../../fixtures/e04_t9/stress.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QImage>
#include <QObject>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTemporaryDir>
#include <QThread>
#include <QVariantList>
#include <QtQml/qqml.h>
#include <algorithm>
#include <atomic>
#include <QMetaMethod>
#include <chrono>
#include <deque>
#include <limits>
#include <mutex>
#if __has_include(<QtGraphs/QXYSeries>)
#include <QtGraphs/QXYSeries>
#define E04_T9_HAS_GRAPHS 1
#else
#define E04_T9_HAS_GRAPHS 0
#endif

class ChartOracle final : public QObject {
    Q_OBJECT
    std::mutex mutex_;
    struct Frame { double maximum; double minimum; double limit; bool requested; qint64 synchronized; };
    std::deque<Frame> pending_;
    QList<QMetaObject::Connection> connections_;
    qint64 start_ = 0, complete_ = 0;
    double expected_ = 0;
    double x_min_ = 0, x_max_ = 0;
    bool view_request_ = false, old_after_input_ = false;
    int sync_count_ = 0;
    QTemporaryDir stress_dir_;
    static qint64 now() { return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
    static QString root() { return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../.."); }
    static double maximum(const auto& values) {
        double out = -std::numeric_limits<double>::infinity();
        for (auto value : values) if (std::isfinite(value)) out = std::max(out, static_cast<double>(value));
        return out;
    }
   public:
    using QObject::QObject;
    Q_INVOKABLE QVariantList datasets() {
        QVariantList out;
        const QStringList paths{QString::fromUtf8(e04_t9_fixture::silicon), QString::fromUtf8(e04_t9_fixture::wish)};
        for (int i = 0; i < paths.size(); ++i) out.append(QVariantMap{{"tag",QString("D%1").arg(i+1)}, {"path",QDir(root()).filePath(paths[i])}});
        auto stress = e04_t9_fixture::stress(root().toStdString());
        edi::save_project(stress, stress_dir_.path().toStdString());
        out.append(QVariantMap{{"tag","D3"},{"path",stress_dir_.path()}});
        return out;
    }
    Q_INVOKABLE QVariantMap reference(const QString& path, double length = 0) const {
        auto project = crysta::load_project(path.toStdString());
        if (length > 0) e04_t9::reference_length_a(project, length);
        crysta::calculate_project(project);
        const auto& experiment = project.experiment();
        const auto& columns = crysta::current(project, experiment);
        QVariantList measured, calc, bkg, residual, su, axis, ticks;
        const auto r = crysta::residual(experiment);
        for (std::size_t i = 0; i < experiment.data->grid.size(); ++i) {
            axis.append(experiment.data->grid[i]); measured.append(experiment.data->intensity[i]);
            su.append(experiment.data->sigma[i]); calc.append(columns.data().intensity_calc[i]);
            bkg.append(columns.data().intensity_bkg[i]); residual.append(r[i]);
        }
        for (double position : columns.refln().position) ticks.append(position);
        return {{"x",axis},{"meas",measured},{"su",su},{"calc",calc},{"bkg",bkg},{"resid",residual},{"ticks",ticks},
                {"maximum",maximum(columns.data().intensity_calc)}, {"length",project.structure.cell.parameters[0].value()}};
    }
    Q_INVOKABLE double calculationBaselineMs(const QString& path, double length) const {
        auto project = edi::load_project(path.toStdString());
        project.structure().cell.length_a.value = length;
        const auto begin = now(); project.calculate();
        return (now()-begin)/1e6;
    }
    Q_INVOKABLE bool chartPixel(QQuickWindow* window, QObject* chart, double x, double y, const QString& color) {
        auto* item = graph(chart);
        auto* x_axis = object(chart,"chart.axis.x"); auto* y_axis = object(chart,"chart.axis.y");
        if (!item || !x_axis || !y_axis || !window) return false;
        const auto plot_rect = item->property("plotArea").toRectF();
        const double left=x_axis->property("min").toDouble(), right=x_axis->property("max").toDouble();
        const double bottom=y_axis->property("min").toDouble(), top=y_axis->property("max").toDouble();
        if (right<=left || top<=bottom) return false;
        const auto point=item->mapToScene({plot_rect.left()+(x-left)/(right-left)*plot_rect.width(),plot_rect.top()+(top-y)/(top-bottom)*plot_rect.height()});
        const auto image=window->grabWindow(); if (image.isNull()) return false;
        const auto ratio=image.devicePixelRatio(); const QColor expected(color);
        for (int dx=-1;dx<=1;++dx) for (int dy=-1;dy<=1;++dy) {
            const int px=qRound(point.x()*ratio)+dx, py=qRound(point.y()*ratio)+dy;
            if (px<0 || py<0 || px>=image.width() || py>=image.height()) continue;
            const auto p=image.pixelColor(px,py);
            if (std::abs(p.red()-expected.red())<20 && std::abs(p.green()-expected.green())<20 && std::abs(p.blue()-expected.blue())<20) return true;
        }
        return false;
    }
    Q_INVOKABLE QObject* object(QObject* chart, const QString& name) const {
        if (!chart) return nullptr;
        if (chart->objectName() == name) return chart;
        return chart->findChild<QObject*>(name, Qt::FindChildrenRecursively);
    }
    Q_INVOKABLE QQuickItem* graph(QObject* chart) const {
        if (!chart) return nullptr;
        for (auto* child : chart->findChildren<QQuickItem*>())
            if (child->property("plotArea").isValid()) return child;
        return nullptr;
    }
    Q_INVOKABLE QVariantMap plot(QObject* chart) const {
        auto* item = graph(chart);
        if (!item) return {};
        const auto rect = item->property("plotArea").toRectF();
        return {{"x",rect.x()},{"y",rect.y()},{"width",rect.width()},{"height",rect.height()}};
    }
    Q_INVOKABLE QVariantList points(QObject* object) const {
        QVariantList result;
#if E04_T9_HAS_GRAPHS
        auto* series = qobject_cast<QXYSeries*>(object);
        if (series) for (const auto& point : series->points()) result.append(QVariantMap{{"x",point.x()},{"y",point.y()}});
#else
        Q_UNUSED(object)
#endif
        return result;
    }
    Q_INVOKABLE bool publicationThreadIsGui(QObject* project) {
        if (!project) return false;
        // Observe the actual signal with a direct connection so a wrong emitter cannot be hidden by queuing.
        const int signal = project->metaObject()->indexOfSignal("recalculated()");
        const int slot = metaObject()->indexOfSlot("published()");
        if (signal < 0 || slot < 0) return false;
        gui_publication_ = true;
        connections_.append(QObject::connect(project, project->metaObject()->method(signal), this,
                                             metaObject()->method(slot), Qt::DirectConnection));
        return true;
    }
    Q_INVOKABLE bool guiPublication() const { return gui_publication_; }
    Q_INVOKABLE bool arm(QQuickWindow* window, QObject* chart, double expected, bool view = false, double left = 0, double right = 0) {
        disarm();
#if E04_T9_HAS_GRAPHS
        auto* series = qobject_cast<QXYSeries*>(object(chart,"chart.series.calc"));
        auto* axis = object(chart,"chart.axis.x");
        if (!window || !series || !axis) return false;
        expected_ = expected; x_min_ = left; x_max_ = right; view_request_ = view;
        start_ = 0; complete_ = 0; old_after_input_ = false; sync_count_ = 0;
        connections_.append(connect(window, &QQuickWindow::afterSynchronizing, this, [=,this] {
            double high = -std::numeric_limits<double>::infinity();
            for (const auto& p : series->points()) if (std::isfinite(p.y())) high = std::max(high, p.y());
            const double lo = axis->property("min").toDouble(), hi = axis->property("max").toDouble();
            std::lock_guard lock(mutex_);
            const bool requested = view_request_ ? std::abs(lo-x_min_) < 1e-8 && std::abs(hi-x_max_) < 1e-8 : high == expected_;
            pending_.push_back({high,lo,hi,requested,now()}); ++sync_count_;
        },Qt::DirectConnection));
        connections_.append(connect(window, &QQuickWindow::frameSwapped, this, [this] {
            const auto swapped = now();
            std::lock_guard lock(mutex_);
            if (pending_.empty()) return;
            const auto frame = pending_.front(); pending_.pop_front();
            if (!start_ || swapped < start_) return;
            if (!frame.requested) old_after_input_ = true;
            if (!complete_ && frame.requested && frame.synchronized >= start_) complete_ = swapped;
        },Qt::DirectConnection));
        window->update();
        return true;
#else
        Q_UNUSED(window) Q_UNUSED(chart) Q_UNUSED(expected) Q_UNUSED(view) Q_UNUSED(left) Q_UNUSED(right)
        return false;
#endif
    }
    Q_INVOKABLE void start() { std::lock_guard lock(mutex_); start_ = now(); }
    Q_INVOKABLE QVariantMap result() { std::lock_guard lock(mutex_); return {{"complete",complete_ > 0},{"latency_ms",(complete_-start_)/1e6},{"oldFrameAfterInput",old_after_input_},{"synchronizedFrames",sync_count_}}; }
    Q_INVOKABLE void disarm() {
        for (const auto& c : connections_) disconnect(c);
        connections_.clear(); std::lock_guard lock(mutex_); pending_.clear();
    }
    Q_INVOKABLE bool finalPixel(QQuickWindow* window, QQuickItem* plot, double x, double y, double left, double right, double bottom, double top, const QString& color) {
        if (!window || !plot || right <= left || top <= bottom) return false;
        const QImage image = window->grabWindow();
        if (image.isNull()) return false;
        const QPointF where = plot->mapToScene(QPointF((x-left)/(right-left)*plot->width(), (top-y)/(top-bottom)*plot->height()));
        const double ratio = image.devicePixelRatio();
        const int cx = qRound(where.x()*ratio), cy = qRound(where.y()*ratio);
        const QColor expected(color);
        for (int dx=-1; dx<=1; ++dx) for (int dy=-1; dy<=1; ++dy) {
            if (cx+dx < 0 || cy+dy < 0 || cx+dx >= image.width() || cy+dy >= image.height()) continue;
            const auto pixel = image.pixelColor(cx+dx, cy+dy);
            if (std::abs(pixel.red()-expected.red()) < 20 && std::abs(pixel.green()-expected.green()) < 20 && std::abs(pixel.blue()-expected.blue()) < 20) return true;
        }
        return false;
    }
   private:
    std::atomic<bool> gui_publication_{true};
   private slots:
    void published() { if (QThread::currentThread() != QCoreApplication::instance()->thread()) gui_publication_ = false; }
};
static void registerChartOracle() {
    qmlRegisterSingletonType<ChartOracle>("EdiChartReference",1,0,"ChartOracle", [](QQmlEngine*,QJSEngine*) -> QObject* { return new ChartOracle; });
}
Q_COREAPP_STARTUP_FUNCTION(registerChartOracle)
#include "test_e04_t9_observer.moc"

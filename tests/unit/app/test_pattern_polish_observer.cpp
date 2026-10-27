#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QImage>
#include <QPointer>
#include <QMutex>
#include <QMutexLocker>
#include <QCryptographicHash>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QVariantList>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqml.h>
#include <algorithm>
#include <map>
#include "measured_layer.hpp"
#include "project_view_model.hpp"

class PatternPolishObserver final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    // Observe the actual source points and receipt in one scene synchronization.
    // No file is inferred from the worker's newest result or GUI grab timing.
    Q_INVOKABLE void watchFollowFrames(QQuickWindow* window, QObject* project, QObject* chart) {
        disconnect(follow_connection_);
        { QMutexLocker guard(&follow_mutex_); follow_frames_.clear(); last_frame_.clear(); }
        QPointer<QObject> guarded_project(project), guarded_chart(chart);
        follow_connection_ = connect(window, &QQuickWindow::afterSynchronizing, this,
            [this, guarded_project, guarded_chart] {
                if (!guarded_project || !guarded_chart || !guarded_chart->property("shown").toBool()) return;
                auto* model = qobject_cast<edi_app::ProjectViewModel*>(guarded_project.data());
                auto* fit = model ? model->fit() : nullptr;
                auto* layer = guarded_chart->findChild<edi_app::MeasuredLayer*>("chart.measured");
                auto* calc = guarded_chart->findChild<QXYSeries*>("chart.series.calc");
                if (!fit || !layer || !calc) return;
                const int count = fit->property("scanPatternUpdates").toInt();
                if (count <= 0) return;
                const QString file = fit->property("scanShownFile").toString();
                QVariantList points;
                QByteArray bytes;
                for (const auto& point : layer->points()) {
                    const double x = point.x(), y = point.y();
                    bytes.append(reinterpret_cast<const char*>(&x), sizeof(x));
                    bytes.append(reinterpret_cast<const char*>(&y), sizeof(y));
                    points.append(QVariantList{x, y});
                }
                const auto signature = QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex();
                const QByteArray key = file.toUtf8() + ':' + QByteArray::number(count) + ':' + signature;
                QMutexLocker guard(&follow_mutex_);
                if (key == last_frame_) return;
                last_frame_ = key;
                follow_frames_.append(QVariantMap{{"file", file}, {"count", count},
                    {"points", points}, {"calculatedCount", calc->points().size()}});
            }, Qt::DirectConnection);
    }
    Q_INVOKABLE QVariantList followFrames() const {
        QMutexLocker guard(&follow_mutex_);
        return follow_frames_;
    }
    Q_INVOKABLE void stopFollowFrames() { disconnect(follow_connection_); }
    Q_INVOKABLE QVariantMap fitRecord(QObject* project) const {
        const auto* vm = qobject_cast<edi_app::ProjectViewModel*>(project);
        if (!vm) return {};
        const auto& saved = vm->project();
        QVariantMap banks;
        for (const auto& bank : saved.experiments)
            banks.insert(QString::fromStdString(bank->name), bank->fit_chi_square ? QVariant(*bank->fit_chi_square) : QVariant());
        return {{"descent", QString::fromStdString(saved.fit_result.descent)},
                {"duration", saved.fit_result.fitting_time}, {"bankChi", banks}};
    }
    Q_INVOKABLE QVariantList series(QObject* chart, const QString& prefix) const {
        QVariantList result;
        if (!chart) return result;
        for (auto* series : chart->findChildren<QXYSeries*>()) {
            if (!series->objectName().startsWith(prefix) || !series->isVisible()) continue;
            QVariantList points;
            for (const auto& point : series->points())
                points.append(QVariantMap{{"x", point.x()}, {"y", point.y()}});
            result.append(QVariantMap{{"name", series->objectName()}, {"points", points}});
        }
        return result;
    }
    Q_INVOKABLE QVariantList measured(QObject* chart) const {
        QVariantList result;
        if (!chart) return result;
        const auto* layer = chart->findChild<edi_app::MeasuredLayer*>("chart.measured");
        if (!layer) return result;
        for (const auto& point : layer->points())
            result.append(QVariantMap{{"x", point.x()}, {"y", point.y()}});
        return result;
    }
    Q_INVOKABLE QVariantMap capture(QQuickWindow* window, const QString& name) const {
        if (!window) return {};
        const bool open_gl = window->rendererInterface()->graphicsApi() == QSGRendererInterface::OpenGL;
        const auto image = window->grabWindow();
        const auto root = QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../../build/pattern-polish-captures");
        QDir().mkpath(root);
        const auto path = QDir(root).filePath(name + ".png");
        return {{"openGL", open_gl}, {"saved", !image.isNull() && image.save(path)},
                {"path", path}, {"width", image.width()}, {"height", image.height()}};
    }
    Q_INVOKABLE QColor pixel(QQuickWindow* window, QQuickItem* item, double x, double y) const {
        if (!window || !item) return {};
        const auto image = window->grabWindow();
        if (image.isNull()) return {};
        const auto point = item->mapToScene({x, y}) * image.devicePixelRatio();
        const int px = qRound(point.x()), py = qRound(point.y());
        return px >= 0 && py >= 0 && px < image.width() && py < image.height()
            ? image.pixelColor(px, py) : QColor{};
    }
    Q_INVOKABLE QColor stripe(QQuickWindow* window, QObject* chart, double x) const {
        if (!window || !chart) return {};
        auto* graph = chart->findChild<QQuickItem*>("chart.view.main");
        auto* axis = chart->findChild<QObject*>("chart.axis.x");
        if (!graph || !axis) return {};
        const double left = axis->property("min").toDouble(), right = axis->property("max").toDouble();
        if (!(right > left)) return {};
        const auto plot = graph->property("plotArea").toRectF();
        const auto image = window->grabWindow();
        if (image.isNull()) return {};
        std::map<QRgb, int> counts;
        for (int i = 1; i < 50; ++i) {
            const auto point = graph->mapToScene({plot.left() + (x-left)/(right-left)*plot.width(),
                                               plot.top() + i*plot.height()/50}) * image.devicePixelRatio();
            const int px = qRound(point.x()), py = qRound(point.y());
            if (px >= 0 && py >= 0 && px < image.width() && py < image.height())
                ++counts[image.pixel(px, py)];
        }
        if (counts.empty()) return {};
        return QColor::fromRgba(std::max_element(counts.begin(), counts.end(),
            [](const auto& a, const auto& b) { return a.second < b.second; })->first);
    }
private:
    QMetaObject::Connection follow_connection_;
    mutable QMutex follow_mutex_;
    QVariantList follow_frames_;
    QByteArray last_frame_;
};

static void register_pattern_polish_observer() {
    qmlRegisterSingletonType<PatternPolishObserver>("PatternPolishAcceptance", 1, 0, "PatternProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new PatternPolishObserver; });
}
Q_COREAPP_STARTUP_FUNCTION(register_pattern_polish_observer)
#include "test_pattern_polish_observer.moc"

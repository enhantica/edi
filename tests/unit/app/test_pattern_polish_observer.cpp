#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QImage>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QVariantList>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqml.h>
#include <algorithm>
#include <map>
#include "measured_layer.hpp"

class PatternPolishObserver final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
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
};

static void register_pattern_polish_observer() {
    qmlRegisterSingletonType<PatternPolishObserver>("PatternPolishAcceptance", 1, 0, "PatternProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new PatternPolishObserver; });
}
Q_COREAPP_STARTUP_FUNCTION(register_pattern_polish_observer)
#include "test_pattern_polish_observer.moc"

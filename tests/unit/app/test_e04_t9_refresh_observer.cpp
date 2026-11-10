//  owner gate (2026-10-02): observe real Qt series replacements, not revision notifications.
#include <QCoreApplication>
#include <QMetaMethod>
#include <QObject>
#include <QVariantMap>
#include <QtGraphs/QXYSeries>
#include <QtQml/qqml.h>
#include <array>
#include <atomic>

class RefreshObserver final : public QObject {
    Q_OBJECT
    QList<QMetaObject::Connection> connections_;
    std::array<std::array<int, 3>, 2> replacements_{};
    std::atomic<int> starts_{0}, finishes_{0}, publications_{0};
    bool trace_available_ = false;

   public:
    using QObject::QObject;
    Q_INVOKABLE void disarm() {
        for (const auto& connection : connections_) disconnect(connection);
        connections_.clear();
    }
    Q_INVOKABLE bool arm(QObject* project, QObject* analysis, QObject* experiment) {
        disarm();
        replacements_ = {};
        starts_ = 0; finishes_ = 0; publications_ = 0; trace_available_ = false;
        if (!project || !analysis || !experiment || analysis == experiment) return false;
        const std::array<QObject*, 2> charts{analysis, experiment};
        const std::array<QString, 3> names{"chart.series.calc", "chart.series.bkg", "chart.series.resid"};
        for (std::size_t page = 0; page < charts.size(); ++page) {
            for (std::size_t curve = 0; curve < names.size(); ++curve) {
                auto* series = charts[page]->findChild<QXYSeries*>(names[curve]);
                if (!series) { disarm(); return false; }
                connections_.append(connect(series, &QXYSeries::pointsReplaced, this,
                    [this, page, curve] { ++replacements_[page][curve]; }, Qt::DirectConnection));
            }
        }
        const auto observe = [this, project](const char* signal, const char* slot) {
            const int source = project->metaObject()->indexOfSignal(signal);
            const int target = metaObject()->indexOfSlot(slot);
            if (source < 0 || target < 0) return false;
            const auto connection = QObject::connect(project, project->metaObject()->method(source), this,
                metaObject()->method(target), Qt::DirectConnection);
            connections_.append(connection);
            return static_cast<bool>(connection);
        };
        if (!observe("recalculated()", "published()")) { disarm(); return false; }
        // Missing actual-calculation instrumentation fails explicitly. Busy-state and publications
        // cannot count superseded calculations, so neither is used as a calculation-count proxy.
        const bool starts = observe("calculationStarted()", "started()");
        const bool finishes = observe("calculationFinished()", "finished()");
        trace_available_ = starts && finishes;
        return true;
    }
    Q_INVOKABLE QVariantMap counts() const {
        return {{"analysisCalc", replacements_[0][0]}, {"analysisBkg", replacements_[0][1]},
                {"analysisResid", replacements_[0][2]}, {"experimentCalc", replacements_[1][0]},
                {"experimentBkg", replacements_[1][1]}, {"experimentResid", replacements_[1][2]},
                {"starts", starts_.load()}, {"finishes", finishes_.load()},
                {"publications", publications_.load()}, {"traceAvailable", trace_available_}};
    }
   private slots:
    void started() { ++starts_; }
    void finished() { ++finishes_; }
    void published() { ++publications_; }
};
static void registerRefreshObserver() {
    qmlRegisterSingletonType<RefreshObserver>("EdiRefreshReference", 1, 0, "RefreshObserver",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new RefreshObserver; });
}
Q_COREAPP_STARTUP_FUNCTION(registerRefreshObserver)
#include "test_e04_t9_refresh_observer.moc"

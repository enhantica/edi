#include <QCryptographicHash>
#include <QElapsedTimer>
#include <QFile>
#include <QFileInfo>
#include <QDirIterator>
#include <QTemporaryDir>
#include <QUrl>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QTimer>
#include <QtGraphs/QXYSeries>
#include <atomic>
#include <mutex>

#include "experiment_view_model.hpp"
#include "fit_view_model.hpp"
#include "measured_layer.hpp"
#include "pattern_model.hpp"
#include "session.hpp"
#if defined(Q_OS_WASM)
#include <emscripten.h>
EM_JS_DEPS(scan_screen, "$stringToNewUTF8,$UTF8ToString");
#endif

namespace {
std::mutex completed_mutex;
QStringList completed_files;
QJsonArray follow_events;
QElapsedTimer* observation_clock = nullptr;
QQuickWindow* observation_window = nullptr;
QJsonObject chart_state() {
    auto* window = observation_window;
    if (!window) return {{"windowPresent", false}};
    QJsonArray charts;
    for (auto* layer : window->findChildren<edi_app::MeasuredLayer*>("chart.measured")) {
        auto* chart = layer->parent();
        auto* calc = chart->findChild<QXYSeries*>("chart.series.calc");
        charts.append(QJsonObject{{"visible", layer->isVisible()},
                                  {"shown", chart->property("shown").toBool()},
                                  {"width", layer->width()}, {"height", layer->height()},
                                  {"measuredPoints", layer->points().size()},
                                  {"calculatedPoints", calc ? calc->points().size() : 0}});
    }
    return {{"windowPresent", true}, {"windowVisible", window->isVisible()},
            {"windowExposed", window->isExposed()},
            {"windowVisibility", static_cast<int>(window->visibility())},
            {"windowWidth", window->width()}, {"windowHeight", window->height()},
            {"charts", charts}};
}
QString wanted(const char* name, const char* fallback) {
#if defined(Q_OS_WASM)
    char* value = reinterpret_cast<char*>(EM_ASM_PTR(
        {
            return stringToNewUTF8(new URL(location.href).searchParams.get(UTF8ToString($0)) ||
                                   UTF8ToString($1));
        },
        name, fallback));
    QString answer = QString::fromUtf8(value);
    free(value);
    return answer;
#else
    return QString::fromUtf8(qgetenv(name).isEmpty() ? QByteArray(fallback) : qgetenv(name));
#endif
}
QString hash_values(const QList<double>& values) {
    return QString::fromLatin1(
        QCryptographicHash::hash(QByteArray(reinterpret_cast<const char*>(values.constData()),
                                            values.size() * sizeof(double)),
                                 QCryptographicHash::Sha256)
            .toHex());
}
QString hash_points(const QList<QPointF>& points) {
    QList<double> values;
    for (const auto& point : points) {
        values.append(point.x());
        values.append(point.y());
    }
    return hash_values(values);
}
bool press(QObject* object) {
    if (!object) return false;
    if (object->metaObject()->indexOfMethod("click()") >= 0)
        return QMetaObject::invokeMethod(object, "click");
    if (object->metaObject()->indexOfMethod("clicked()") >= 0)
        return QMetaObject::invokeMethod(object, "clicked");
    return false;
}
QStringList choices(QObject* object) {
    QStringList result;
    if (object->metaObject()->indexOfMethod("textAt(int)") < 0) return {};
    const int count = object->property("count").toInt();
    for (int i = 0; i < count; ++i) {
        QString text;
        if (!QMetaObject::invokeMethod(object, "textAt", Q_RETURN_ARG(QString, text),
                                       Q_ARG(int, i)))
            return {};
        result.append(text);
    }
    return result;
}
void publish(const QJsonObject& result) {
    QJsonObject output = result;
    {
        std::lock_guard lock(completed_mutex);
        output["followEvents"] = follow_events;
    }
    const QByteArray bytes = QJsonDocument(output).toJson(QJsonDocument::Compact);
#if defined(Q_OS_WASM)
    EM_ASM(
        { globalThis.__scanScreenObservation = JSON.parse(UTF8ToString($0)); }, bytes.constData());
#else
    QFile file(wanted("SCAN_SCREEN_OUTPUT", "scan-screen.json"));
    if (file.open(QIODevice::WriteOnly)) file.write(bytes);
    QCoreApplication::quit();
#endif
}
}  // namespace

void scan_screen_completed(const std::string& file) {
    std::lock_guard lock(completed_mutex);
    completed_files.append(QString::fromStdString(file));
    follow_events.append(QJsonObject{{"event", "file-complete"},
                                     {"file", QString::fromStdString(file)},
                                     {"ms", static_cast<double>(observation_clock->elapsed())}});
}

void scan_screen_follow(const QJsonObject& state) {
    QJsonObject event = state;
    event["ms"] = static_cast<double>(observation_clock->elapsed());
    event["chart"] = chart_state();
    std::lock_guard lock(completed_mutex);
    follow_events.append(event);
}

void scan_screen_worker(const char* event, const std::string& file, bool wanted, bool waiting,
                        bool cancelled, bool has_frame, long remaining) {
    std::lock_guard lock(completed_mutex);
    follow_events.append(QJsonObject{{"event", event}, {"file", QString::fromStdString(file)},
                                     {"ms", static_cast<double>(observation_clock->elapsed())},
                                     {"frameWanted", wanted}, {"waitPatterns", waiting},
                                     {"cancelled", cancelled}, {"hasFrame", has_frame},
                                     {"deadlineRemainingMs", static_cast<qint64>(remaining)}});
}

void scan_screen_settings(QQmlApplicationEngine& engine) {
#if !defined(Q_OS_WASM)
    const QString file = QString::fromUtf8(qgetenv("SCAN_SCREEN_SETTINGS_FILE"));
    if (file.isEmpty()) qFatal("The screen observer requires a private machine settings file");
    engine.rootContext()->setContextProperty("pySettingsPath",
                                             QUrl::fromLocalFile(file).toString());
#else
    static_cast<void>(engine);
#endif
}

void scan_screen_install(QQmlApplicationEngine& engine) {
    auto* window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    auto* session = engine.singletonInstance<edi_app::Session*>("edi.app", "Session");
    engine.singletonInstance<QObject*>("edi.app", "Preferences")->setProperty("patternMeasuredStyle", "points");
    auto* clock = new QElapsedTimer;
    clock->start();
    observation_clock = clock;
    observation_window = window;
    auto* result = new QJsonObject{{"mode", wanted("SCAN_SCREEN_MODE", "adaptive")},
                                   {"frames", QJsonArray{}}};
    auto* preferences = engine.singletonInstance<QObject*>("edi.app", "Preferences");
    if (!preferences || !preferences->setProperty("patternMeasuredStyle", QStringLiteral("linePoints"))) {
        (*result)["error"] = "Scan drawing precondition: the actual measured points must be enabled";
        publish(*result);
        return;
    }
    auto* finish = new QTimer(window);
    finish->setSingleShot(true);
    QObject::connect(finish, &QTimer::timeout, window, [result] {
        (*result)["error"] = "The actual scan did not settle before the observation deadline";
        publish(*result);
    });
    finish->start(120000);
    auto* latest = new QJsonObject;
    auto* previous = new QString;
    auto* previous_chart = new QJsonObject;
    QObject::connect(
        window, &QQuickWindow::afterSynchronizing, window,
        [=] {
            auto* project = session->project();
            if (!project) return;
            QJsonObject chart = chart_state();
            chart["patternShown"] = project->patternShown();
            if (chart != *previous_chart) {
                std::lock_guard lock(completed_mutex);
                follow_events.append(QJsonObject{{"event", "drawability"}, {"chart", chart},
                                                 {"ms", static_cast<double>(clock->elapsed())}});
                *previous_chart = chart;
            }
            edi_app::MeasuredLayer* layer = nullptr;
            for (auto* candidate : window->findChildren<edi_app::MeasuredLayer*>("chart.measured"))
                if (candidate->isVisible() && candidate->parent()->property("shown").toBool())
                    layer = candidate;
            auto* calc =
                layer ? layer->parent()->findChild<QXYSeries*>("chart.series.calc") : nullptr;
            if (!layer || !calc || !layer->isVisible() || calc->points().isEmpty() ||
                layer->points().isEmpty())
                return;
            auto* model = project->currentExperiment()->pattern();
            QList<double> measured;
            for (int role :
                 {edi_app::PatternModel::XRole, edi_app::PatternModel::IntensityMeasRole,
                  edi_app::PatternModel::IntensityMeasSuRole})
                for (int row = 0; row < model->rowCount(); ++row)
                    measured.append(model->data(model->index(row), role).toDouble());
            QStringList files;
            {
                std::lock_guard lock(completed_mutex);
                files = completed_files;
            }
            QJsonArray finished;
            for (const auto& file : files) finished.append(file);
            QJsonArray drawn;
            for (const auto& point : layer->points())
                drawn.append(QJsonArray{point.x(), point.y()});
            *latest = {{"ms", static_cast<double>(clock->elapsed())},
                       {"running", project->fit()->running()},
                       {"patternGeneration", static_cast<qint64>(project->currentExperiment()->patternGeneration())},
                       {"presentedGeneration", static_cast<qint64>(project->currentExperiment()->presentedGeneration())},
                       {"modelMeasured", hash_values(measured)},
                       {"drawnMeasured", hash_points(layer->points())},
                       {"drawnPoints", drawn},
                       {"drawnCalculated", hash_points(calc->points())},
                       {"finished", finished}};
        },
        Qt::DirectConnection);
    QObject::connect(
        window, &QQuickWindow::frameSwapped, window,
        [=] {
            if (latest->isEmpty() || !result->contains("readyGeneration") ||
                latest->value("patternGeneration").toInteger() < result->value("readyGeneration").toInteger())
                return;
            const QString key = latest->value("drawnMeasured").toString() +
                                latest->value("drawnCalculated").toString() +
                                (latest->value("running").toBool() ? "running" : "stopped") +
                                QString::number(latest->value("presentedGeneration").toInteger());
            if (key != *previous) {
                QJsonArray frames = result->value("frames").toArray();
                frames.append(*latest);
                (*result)["frames"] = frames;
                *previous = key;
            }
        },
        Qt::DirectConnection);
    QTimer::singleShot(500, window, [=, &engine] {
        static QTemporaryDir fixture;
        const QString source = QStringLiteral(":/test-fixtures/scan-screen");
        QDirIterator files(source, QDir::Files, QDirIterator::Subdirectories);
        bool copied = fixture.isValid();
        while (copied && files.hasNext()) {
            const QString from = files.next();
            const QString to = fixture.path() + from.mid(source.size());
            copied = QDir().mkpath(QFileInfo(to).absolutePath()) && QFile::copy(from, to)
                     && QFile::setPermissions(to, QFile::ReadOwner | QFile::WriteOwner);
        }
        if (!copied || !QFile::exists(fixture.filePath("project.edi"))) {
            (*result)["error"] = "Scan fixture precondition: the retained 162-file project must be extracted";
            publish(*result);
            return;
        }
        if (!session->openProject(QUrl::fromLocalFile(fixture.path()))) {
            (*result)["error"] = session->lastError();
            publish(*result);
            return;
        }
        press(window->findChild<QObject*>("appBar.tab.analysis"));
        for (auto* button : window->findChildren<QObject*>("sideBar.tab.extras")) {
            QObject* owner = button;
            while (owner && owner->property("pageName").toString() != "analysis")
                owner = owner->parent();
            if (owner) press(button);
        }
        QObject* combo = nullptr;
        QStringList options;
        bool label = false, extras = false;
        for (auto* object : window->findChildren<QObject*>()) {
            const QString text = object->property("text").toString();
            if (text == "Extras" || text == "Extra") {
                extras = true;
                press(object);
            }
            if (text.startsWith("Pattern updates during a scan") ||
                object->property("title").toString() == "Pattern updates during a scan") {
                label = true;
                object->setProperty("collapsed", false);
            }
            const auto values = choices(object);
            if (values.join("|").contains("adaptive", Qt::CaseInsensitive) &&
                values.join("|").contains("every pattern", Qt::CaseInsensitive)) {
                combo = object;
                options = values;
            }
        }
        (*result)["extras"] = extras;
        (*result)["label"] = label;
        (*result)["options"] = QJsonArray::fromStringList(options);
        (*result)["initial"] = combo ? combo->property("currentText").toString() : QString();
        auto* control = qobject_cast<QQuickItem*>(combo);
        (*result)["selectorUsable"] = control && control->isVisible() && control->isEnabled();
        const QString mode = result->value("mode").toString();
        if (combo && mode != "read") {
            int index = -1;
            for (int i = 0; i < options.size(); ++i) {
                const QString label = mode == "every" ? "Every pattern, fit waits for the display"
                    : mode == "second" ? "About once a second"
                    : mode == "adaptive" ? "Adaptive" : mode == "end" ? "Only at the end" : QString();
                if (options[i] == label) {
                    index = i;
                    break;
                }
            }
            if (index >= 0) {
                combo->setProperty("currentIndex", index);
                QMetaObject::invokeMethod(combo, "activated", Q_ARG(int, index));
            }
        }
        (*result)["selected"] = combo ? combo->property("currentText").toString() : QString();
        auto* dialog = window->findChild<QObject*>("preferences");
        if (dialog) QMetaObject::invokeMethod(dialog, "close");
        if (wanted("SCAN_SCREEN_SETTINGS_ONLY", "0") == "1") {
            QTimer::singleShot(1000, window, [=] { publish(*result); });
            return;
        }
        if (mode != "adaptive" && !combo) {
            (*result)["error"] = "The requested scan pattern selector is absent";
            publish(*result);
            return;
        }
        auto* timer = new QTimer(window);
        timer->setInterval(25);
        QObject::connect(timer, &QTimer::timeout, window, [=] {
            auto* project = session->project();
            if (!project->pendingRefusal().isEmpty() || project->calculating() ||
                project->currentExperiment()->pattern()->stale())
                return;
            if (!result->contains("readyGeneration")) {
                (*result)["readyGeneration"] = static_cast<qint64>(project->currentExperiment()->patternGeneration());
                window->update();
                return;
            }
            if (result->value("frames").toArray().isEmpty()) return;
            timer->stop();
            (*result)["started"] = true;
            QObject::connect(project->fit(), &edi_app::FitViewModel::runningChanged, window, [=] {
                if (project->fit()->running()) return;
                (*result)["outcome"] = project->fit()->outcome();
                QTimer::singleShot(1500, window, [=] {
                    finish->stop();
                    publish(*result);
                });
            });
            if (mode == "adaptive") {
                const auto hide = [=] {
                    if (result->contains("heldMs")) return;
                    press(window->findChild<QObject*>("mainArea.analysis.tab.evolution"));
                    (*result)["heldMs"] = static_cast<double>(clock->elapsed());
                    (*result)["heldGeneration"] = static_cast<qint64>(project->currentExperiment()->patternGeneration());
                    {
                        std::lock_guard lock(completed_mutex);
                        (*result)["finishedAtHold"] = completed_files.size();
                    }
                    QTimer::singleShot(1000, window, [=] {
                        QStringList completed;
                        {
                            std::lock_guard lock(completed_mutex);
                            completed = completed_files;
                        }
                        (*result)["finishedAtRelease"] = QJsonArray::fromStringList(completed);
                        (*result)["releasedGeneration"] = static_cast<qint64>(project->currentExperiment()->patternGeneration());
                        (*result)["releasedMs"] = static_cast<double>(clock->elapsed());
                        press(window->findChild<QObject*>("mainArea.analysis.tab.fitting"));
                    });
                };
                if (wanted("SCAN_SCREEN_FORCE_HIDE", "0") == "1") {
                    // Interrupt the first applied pattern before its drawing, exercising the held redraw.
                    (*result)["forced"] = true;
                    QObject::connect(project->currentExperiment(), &edi_app::ExperimentViewModel::patternSourceChanged,
                                     window, [=] {
                        if (!project->fit()->running()) return;
                        {
                            std::lock_guard lock(completed_mutex);
                            if (completed_files.isEmpty()) return;
                        }
                        hide();
                    }, Qt::DirectConnection);
                } else {
                    auto* visibility = new QTimer(window);
                    visibility->setInterval(25);
                    QObject::connect(visibility, &QTimer::timeout, window, [=] {
                        QStringList files;
                        {
                            std::lock_guard lock(completed_mutex);
                            files = completed_files;
                        }
                        if (files.size() < 3 || !project->fit()->running()) return;
                        visibility->stop();
                        hide();
                    });
                    visibility->start();
                }
            }
            project->fit()->start();
        });
        timer->start();
    });
}

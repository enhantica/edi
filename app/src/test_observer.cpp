// SPDX-License-Identifier: BSD-3-Clause
#include "test_observer.hpp"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaMethod>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSocketNotifier>
#include <QTimer>
#include <QUrl>
#include <QtGraphs/QXYSeries>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <functional>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <vector>

#include <unistd.h>

#include "analysis_view_model.hpp"
#include "app_build_info.hpp"
#include "edi/categories.hpp"
#include "edi/fit_job.hpp"
#include "edi/io.hpp"
#include "edi/version.hpp"
#include "experiment_view_model.hpp"
#include "fit_view_model.hpp"
#include "measured_layer.hpp"
#include "pattern_model.hpp"
#include "project_view_model.hpp"
#include "scan_session.hpp"
#include "session.hpp"

namespace edi_app {
namespace {

bool screen_observer = false;

bool enabled() {
    return qgetenv("EDI_TEST_OBSERVERS") == "1" && !qEnvironmentVariableIsEmpty("PYTEST_CURRENT_TEST");
}

bool until(const std::function<bool()>& ready, int milliseconds = 120000) {
    if (ready()) return true;
    QEventLoop loop;
    QTimer check, deadline;
    check.setInterval(0);
    deadline.setSingleShot(true);
    QObject::connect(&check, &QTimer::timeout, &loop, [&] {
        if (ready()) loop.quit();
    });
    QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
    check.start();
    deadline.start(milliseconds);
    loop.exec();
    return ready();
}

std::unique_ptr<ProjectViewModel> load(const QString& path) {
    auto view = std::make_unique<ProjectViewModel>(edi::load_project(path.toStdString()), nullptr);
    QCoreApplication::processEvents();
    until([&] { return !view->calculating() && !view->currentExperiment()->pattern()->stale(); });
    return view;
}

// Switch a loaded project to joint fitting through the Analysis page's own call.
QJsonObject joint(const QString& path) {
    auto view = load(path);
    const QString before = view->analysis()->fittingMode();
    view->analysis()->setFittingMode(QStringLiteral("joint"));
    return {{"before", before}, {"after", view->analysis()->fittingMode()}, {"error", view->lastError()}};
}

// --- scan-screen: what the pattern chart draws while a scan fits -----------------------------------

// The files the fit worker has finished, as it finishes them (before the app is told).
std::mutex completed_mutex;
QStringList completed_files;

void file_completed(const std::string& file) {
    const std::lock_guard lock(completed_mutex);
    completed_files.append(QString::fromStdString(file));
}

QStringList completed() {
    const std::lock_guard lock(completed_mutex);
    return completed_files;
}

QString setting(const char* name, const char* fallback) {
    const QByteArray value = qgetenv(name);
    return QString::fromUtf8(value.isEmpty() ? QByteArray(fallback) : value);
}

QString hash_values(const QList<double>& values) {
    const QByteArray bytes(reinterpret_cast<const char*>(values.constData()),
                           static_cast<qsizetype>(values.size() * sizeof(double)));
    return QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
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
    if (object == nullptr) return false;
    if (object->metaObject()->indexOfMethod("click()") >= 0) return QMetaObject::invokeMethod(object, "click");
    if (object->metaObject()->indexOfMethod("clicked()") >= 0) return QMetaObject::invokeMethod(object, "clicked");
    return false;
}

// A combo box's displayed options, or nothing for any other object.
QStringList choices(QObject* object) {
    if (object->metaObject()->indexOfMethod("textAt(int)") < 0) return {};
    QStringList result;
    const int count = object->property("count").toInt();
    for (int i = 0; i < count; ++i) {
        QString text;
        if (!QMetaObject::invokeMethod(object, "textAt", Q_RETURN_ARG(QString, text), Q_ARG(int, i))) return {};
        result.append(text);
    }
    return result;
}

void publish(const QJsonObject& result) {
    QFile file(setting("SCAN_SCREEN_OUTPUT", "scan-screen.json"));
    if (file.open(QIODevice::WriteOnly)) file.write(QJsonDocument(result).toJson(QJsonDocument::Compact));
    QCoreApplication::quit();
}

// The pattern-update choice for a mode: every, second, adaptive or end.
int option_for(const QStringList& options, const QString& mode) {
    int index = -1;
    for (int i = 0; i < options.size(); ++i) {
        const QString option = options[i].toLower();
        if ((mode == "every" && option.contains("every pattern")) || (mode == "second" && option.contains("second")) ||
            (mode == "adaptive" && option.contains("adaptive")) || (mode == "end" && option.contains("end")))
            index = i;
    }
    return index;
}

struct ScreenObservation {
    QQuickWindow* window = nullptr;
    Session* session = nullptr;
    QElapsedTimer clock;
    QJsonObject result;
    QJsonObject latest;  // the frame being synchronised, recorded when it is swapped
    QString previous;    // the last recorded frame's key
    QTimer* finish = nullptr;
};

// Record, at each scene synchronisation, what the chart's measured layer and calculated series hold.
void record_frame(ScreenObservation& o) {
    auto* project = o.session->project();
    if (project == nullptr) return;
    MeasuredLayer* layer = nullptr;
    for (auto* candidate : o.window->findChildren<MeasuredLayer*>("chart.measured"))
        if (candidate->isVisible() && candidate->parent()->property("shown").toBool()) layer = candidate;
    auto* calc = layer != nullptr ? layer->parent()->findChild<QXYSeries*>("chart.series.calc") : nullptr;
    if (layer == nullptr || calc == nullptr || calc->points().isEmpty() || layer->points().isEmpty()) return;
    auto* model = project->currentExperiment()->pattern();
    QList<double> measured;
    for (int role : {PatternModel::XRole, PatternModel::IntensityMeasRole, PatternModel::IntensityMeasSuRole})
        for (int row = 0; row < model->rowCount(); ++row)
            measured.append(model->data(model->index(row), role).toDouble());
    QJsonArray drawn;
    for (const auto& point : layer->points()) drawn.append(QJsonArray{point.x(), point.y()});
    o.latest = {{"ms", static_cast<double>(o.clock.elapsed())},
                {"running", project->fit()->running()},
                {"patternGeneration", static_cast<qint64>(project->currentExperiment()->patternGeneration())},
                {"presentedGeneration", static_cast<qint64>(project->currentExperiment()->presentedGeneration())},
                {"modelMeasured", hash_values(measured)},
                {"drawnMeasured", hash_points(layer->points())},
                {"drawnPoints", drawn},
                {"drawnCalculated", hash_points(calc->points())},
                {"finished", QJsonArray::fromStringList(completed())}};
}

// Keep a synchronised frame once it is on screen, if it differs from the last one kept.
void keep_frame(ScreenObservation& o) {
    if (o.latest.isEmpty()) return;
    const QString key = o.latest.value("drawnMeasured").toString() + o.latest.value("drawnCalculated").toString() +
                        (o.latest.value("running").toBool() ? "running" : "stopped") +
                        QString::number(o.latest.value("presentedGeneration").toInteger());
    if (key == o.previous) return;
    QJsonArray frames = o.result.value("frames").toArray();
    frames.append(o.latest);
    o.result["frames"] = frames;
    o.previous = key;
}

// Adaptive mode: show Evolution while the fit runs, then the pattern again a second later.
void hold_and_release(ScreenObservation& o, ProjectViewModel* project) {
    if (o.result.contains("heldMs")) return;
    press(o.window->findChild<QObject*>("mainArea.analysis.tab.evolution"));
    o.result["heldMs"] = static_cast<double>(o.clock.elapsed());
    o.result["heldGeneration"] = static_cast<qint64>(project->currentExperiment()->patternGeneration());
    o.result["finishedAtHold"] = static_cast<int>(completed().size());
    QTimer::singleShot(1000, o.window, [&o, project] {
        o.result["finishedAtRelease"] = QJsonArray::fromStringList(completed());
        o.result["releasedGeneration"] = static_cast<qint64>(project->currentExperiment()->patternGeneration());
        o.result["releasedMs"] = static_cast<double>(o.clock.elapsed());
        press(o.window->findChild<QObject*>("mainArea.analysis.tab.fitting"));
    });
}

void start_fit(ScreenObservation& o, const QString& mode) {
    auto* project = o.session->project();
    o.result["started"] = true;
    QObject::connect(project->fit(), &FitViewModel::runningChanged, o.window, [&o, project] {
        if (project->fit()->running()) return;
        o.result["outcome"] = project->fit()->outcome();
        QTimer::singleShot(1500, o.window, [&o] {
            o.finish->stop();
            publish(o.result);
        });
    });
    if (mode == "adaptive") {
        if (setting("SCAN_SCREEN_FORCE_HIDE", "0") == "1") {
            // Hide the pattern as the first finished file is applied, before it is drawn.
            o.result["forced"] = true;
            QObject::connect(
                project->currentExperiment(), &ExperimentViewModel::patternSourceChanged, o.window,
                [&o, project] {
                    if (project->fit()->running() && !completed().isEmpty()) hold_and_release(o, project);
                },
                Qt::DirectConnection);
        } else {
            auto* visibility = new QTimer(o.window);
            visibility->setInterval(25);
            QObject::connect(visibility, &QTimer::timeout, o.window, [&o, project, visibility] {
                if (completed().size() < 3 || !project->fit()->running()) return;
                visibility->stop();
                hold_and_release(o, project);
            });
            visibility->start();
        }
    }
    project->fit()->start();
}

// Open the scan, choose the pattern-update mode in Extras, then fit once the first frame is drawn.
void drive(ScreenObservation& o) {
    if (!o.session->openExample("pd-neut-cwl_cosio-d20_scan-162f")) {
        o.result["error"] = o.session->lastError();
        publish(o.result);
        return;
    }
    press(o.window->findChild<QObject*>("appBar.tab.analysis"));
    for (auto* button : o.window->findChildren<QObject*>("sideBar.tab.extras")) {
        QObject* owner = button;
        while (owner != nullptr && owner->property("pageName").toString() != "analysis") owner = owner->parent();
        if (owner != nullptr) press(button);
    }
    QObject* combo = nullptr;
    QStringList options;
    bool label = false;
    bool extras = false;
    for (auto* object : o.window->findChildren<QObject*>()) {
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
        const QString values = choices(object).join("|");
        if (values.contains("adaptive", Qt::CaseInsensitive) && values.contains("every pattern", Qt::CaseInsensitive)) {
            combo = object;
            options = choices(object);
        }
    }
    o.result["extras"] = extras;
    o.result["label"] = label;
    o.result["options"] = QJsonArray::fromStringList(options);
    o.result["initial"] = combo != nullptr ? combo->property("currentText").toString() : QString();
    auto* control = qobject_cast<QQuickItem*>(combo);
    o.result["selectorUsable"] = control != nullptr && control->isVisible() && control->isEnabled();
    const QString mode = o.result.value("mode").toString();
    if (combo != nullptr && mode != "read") {
        if (const int index = option_for(options, mode); index >= 0) {
            combo->setProperty("currentIndex", index);
            QMetaObject::invokeMethod(combo, "activated", Q_ARG(int, index));
        }
    }
    o.result["selected"] = combo != nullptr ? combo->property("currentText").toString() : QString();
    if (auto* dialog = o.window->findChild<QObject*>("preferences")) QMetaObject::invokeMethod(dialog, "close");
    if (setting("SCAN_SCREEN_SETTINGS_ONLY", "0") == "1") {
        QTimer::singleShot(1000, o.window, [&o] { publish(o.result); });
        return;
    }
    if (mode != "adaptive" && combo == nullptr) {
        o.result["error"] = "The requested scan pattern selector is absent";
        publish(o.result);
        return;
    }
    auto* timer = new QTimer(o.window);
    timer->setInterval(25);
    QObject::connect(timer, &QTimer::timeout, o.window, [&o, timer, mode] {
        auto* project = o.session->project();
        if (project->calculating() || project->currentExperiment()->pattern()->stale() ||
            o.result.value("frames").toArray().isEmpty())
            return;
        timer->stop();
        start_fit(o, mode);
    });
    timer->start();
}

// --test-observer scan-lifecycle <project> (tests/fixtures/scan_lifecycle/README.md): fit the scan once and
// report every fit-model signal with the state read at that moment, then two samples, the last a quiet window
// after the scan's end, so a counter or clock still running after the end shows.
QString lifecycle_project;
constexpr int kQuietMs = 1250;  // beyond the fit view's one-second status timer

// Calls `hit` with the index of the connected signal: QMetaObject::connect to method
// `QObject::staticMetaObject.methodCount() + k` arrives here as `k`.
class SignalTap final : public QObject {
   public:
    std::function<void(int)> hit;
    int qt_metacall(QMetaObject::Call call, int id, void** arguments) override {
        id = QObject::qt_metacall(call, id, arguments);
        if (id >= 0 && call == QMetaObject::InvokeMetaMethod) {
            if (hit) hit(id);
            return -1;
        }
        return id;
    }
};

QJsonObject lifecycle_state(const FitViewModel* fit, const QString& kind, double ms) {
    return {{"kind", kind},
            {"ms", ms},
            {"running", fit->running()},
            {"scanning", fit->scanning()},
            {"scanProcessed", fit->scanProcessed()},
            {"scanFitted", fit->scanFitted()},
            {"scanTotal", fit->scanTotal()},
            {"scanProgress", fit->scanProgress()},
            {"elapsed", fit->elapsed()},
            {"iterations", fit->iterations()},
            {"status", fit->status()},
            {"outcome", fit->outcome()},
            {"scanText", fit->scanText()},
            {"eta", fit->eta()}};
}

// The scan's files as the project lists its datasets.
QJsonArray lifecycle_files(ProjectViewModel* project) {
    QJsonArray files;
    auto* model = project->experiments();
    const int role = model->roleNames().key("file", -1);
    for (int row = 0; row < model->rowCount(); ++row) {
        files.append(model->data(model->index(row), role).toString());
    }
    return files;
}

// Leaves at once: the observation is complete, and tearing the window down takes longer than the scan.
void finish_lifecycle(const QJsonObject& result, int code) {
    std::printf("%s\n", QJsonDocument(result).toJson(QJsonDocument::Compact).constData());
    std::fflush(stdout);
    std::_Exit(code);
}

void install_lifecycle(QQmlApplicationEngine& engine) {
    // Live until the app quits.
    static QElapsedTimer clock;
    static SignalTap tap;
    static QJsonArray events;
    static bool ended = false;
    static double started = 0.0;  // ms at Start
    clock.start();
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    QTimer::singleShot(0, &tap, [session] {
        QJsonObject result{{"project", lifecycle_project}};
        if (!session->openProject(QUrl::fromLocalFile(lifecycle_project))) {
            result["error"] = session->lastError();
            finish_lifecycle(result, 1);
            return;
        }
        ProjectViewModel* project = session->project();
        FitViewModel* fit = project->fit();
        // Every signal FitViewModel declares, connected before Start.
        std::vector<QString> names;
        QJsonArray watched;
        const QMetaObject& meta = FitViewModel::staticMetaObject;
        for (int index = meta.methodOffset(); index < meta.methodCount(); ++index) {
            const QMetaMethod method = meta.method(index);
            if (method.methodType() != QMetaMethod::Signal) continue;
            const int slot = QObject::staticMetaObject.methodCount() + static_cast<int>(names.size());
            names.push_back(QString::fromLatin1(method.name()));
            watched.append(names.back());
            QMetaObject::connect(fit, index, &tap, slot);
        }
        result["mode"] = project->analysis()->fittingMode();
        result["signals_watched"] = watched;
        tap.hit = [fit, project, names, result](int id) mutable {
            const auto now = [] { return static_cast<double>(clock.nsecsElapsed()) / 1e6; };
            QJsonObject event = lifecycle_state(fit, "signal", now());
            event["signal"] = names.at(static_cast<std::size_t>(id));
            events.append(event);
            if (names.at(static_cast<std::size_t>(id)) != QLatin1String("scanFinished") || ended) return;
            ended = true;
            QTimer::singleShot(0, &tap, [fit, now] { events.append(lifecycle_state(fit, "sample", now())); });
            const double terminal = now();
            QTimer::singleShot(kQuietMs, &tap, [fit, project, result, now, terminal]() mutable {
                events.append(lifecycle_state(fit, "sample", now()));
                result["files"] = lifecycle_files(project);
                result["events"] = events;
                // With SCAN_LIFECYCLE_RESET=1, also Reset fits, for a timing of the whole cycle.
                if (qgetenv("SCAN_LIFECYCLE_RESET") == "1") {
                    const double reset_start = now();
                    fit->reset();
                    QCoreApplication::processEvents();
                    result["boundaries"] = QJsonObject{{"start", started},
                                                       {"terminal", terminal},
                                                       {"reset_start", reset_start},
                                                       {"reset_end", now()}};
                }
                finish_lifecycle(result, 0);
            });
        };
        started = static_cast<double>(clock.nsecsElapsed()) / 1e6;
        fit->start();
    });
}

// --test-observer scan-cycle <project> resume (tests/fixtures/scan_pair/README.md): Start on a scan, resumed where
// its rows end, seen as JSON lines on stdout. `ready` once the project is open; then, on {"command":"start"} from
// stdin, every fit-view signal, each file's inner fit with its start values, each fitted file, the terminal state
// and, a quiet window later, `quiet_complete`. Every line names the project and the builds and carries the fit state.
struct CycleObservation {
    QString project, operation, nonce;
    ProjectViewModel* model = nullptr;
    FitViewModel* fit = nullptr;
    QElapsedTimer clock;
    bool started = false, ended = false;
};
CycleObservation cycle;

void cycle_emit(QJsonObject event) {
    event["project"] = cycle.project;
    event["edi_commit"] = QString::fromLatin1(edi::build_commit());
    event["crysta_commit"] = QStringLiteral(EDI_APP_CRYSTA_COMMIT);
    event["ms"] = static_cast<double>(cycle.clock.nsecsElapsed()) / 1e6;
    if (!cycle.nonce.isEmpty()) event["nonce"] = cycle.nonce;
    if (cycle.fit != nullptr) {  // the fit state, as `state` and at the top level
        QJsonObject state;
        for (const char* name : {"running", "scanning", "scanProcessed", "scanFitted", "scanTotal"}) {
            state[QLatin1String(name)] = QJsonValue::fromVariant(cycle.fit->property(name));
            event[QLatin1String(name)] = state[QLatin1String(name)];
        }
        event["state"] = state;
    }
    std::printf("%s\n", QJsonDocument(event).toJson(QJsonDocument::Compact).constData());
    std::fflush(stdout);
}

// On the main thread, in the order the worker reported it.
void cycle_post(QJsonObject event) {
    QMetaObject::invokeMethod(QCoreApplication::instance(), [event] { cycle_emit(event); }, Qt::QueuedConnection);
}

void cycle_inner_fit(const std::string& file, const std::vector<std::pair<std::string, double>>& starts) {
    QJsonObject values;
    for (const auto& [name, value] : starts) values[QString::fromStdString(name)] = value;
    cycle_post({{"event", "inner_fit_started"}, {"file", QString::fromStdString(file)}, {"start_values", values}});
}

void cycle_file_fitted(const std::string& file) {
    cycle_post({{"event", "file_fitted"}, {"file", QString::fromStdString(file)}});
}

// Shows the last dataset with a row, as the dataset selector does: what a finished scan displays.
void cycle_show_last() {
    const ScanSession* session = cycle.model->scanSession();
    if (session == nullptr) return;
    const auto& rows = session->index().rows;
    for (int dataset = static_cast<int>(rows.size()) - 1; dataset >= 0; --dataset) {
        if (rows[static_cast<std::size_t>(dataset)].offset >= 0) {
            cycle.model->setCurrentExperimentIndex(dataset);
            return;
        }
    }
}

void cycle_emit_terminal();

// The displayed terminal result, once the shown dataset's values have reached the model (a selection reads them in
// the background, calculating until they arrive).
void cycle_terminal() {
    cycle_show_last();
    auto* settle = new QTimer(QCoreApplication::instance());
    settle->setInterval(25);
    QObject::connect(settle, &QTimer::timeout, settle, [settle] {
        if (cycle.model->calculating()) return;
        settle->deleteLater();
        cycle_emit_terminal();
    });
    settle->start();
}

// The shown dataset's persisted row and the model values it shows.
void cycle_emit_terminal() {
    QJsonObject event{{"event", "terminal"}};
    const ScanSession* session = cycle.model->scanSession();
    const std::vector<std::string> row =
        session != nullptr ? session->row(cycle.model->project(), cycle.model->currentExperimentIndex())
                           : std::vector<std::string>();
    if (!row.empty()) {  // the shown dataset's recorded result, as `result` and at the top level
        const edi::ScanResultIndex& index = session->index();
        const QJsonObject result{{"success", row[index.success] == "True"},
                                 {"iterations", std::stoi(row[index.iterations])},
                                 {"reduced_chi_square", std::stod(row[index.chi])}};
        for (auto it = result.begin(); it != result.end(); ++it) event[it.key()] = it.value();
        event["result"] = result;
        // The live model's values, as the dataset selection left them, by results column.
        std::set<std::string> columns;
        for (const edi::ScanParameterColumns& column : index.parameters) columns.insert(column.name);
        QJsonObject values;
        for (const edi::NamedSlot& slot : edi::named_slots(const_cast<edi::Project&>(cycle.model->project()))) {
            const std::string column = edi::scan_results_column(slot.unique_name);
            if (columns.contains(column)) values[QString::fromStdString(column)] = slot.parameter->value.get();
        }
        event["parameter_values"] = values;
    }
    cycle_emit(event);
    QTimer::singleShot(kQuietMs, QCoreApplication::instance(), [] {
        cycle_emit({{"event", "quiet_complete"}});
        std::_Exit(0);
    });
}

void cycle_command(const QByteArray& line) {
    const QJsonObject command = QJsonDocument::fromJson(line).object();
    if (command.value("command").toString() != QLatin1String("start") || cycle.started) {
        cycle_emit({{"event", "error"}, {"error", QStringLiteral("unexpected command: ") + QString::fromUtf8(line)}});
        return;
    }
    cycle.started = true;
    cycle.nonce = command.value("nonce").toString();
    cycle_emit({{"event", "started"}});
    const bool complete = cycle.fit->scanTotal() > 0 && cycle.fit->scanProcessed() == cycle.fit->scanTotal();
    if (complete) {  // nothing left to fit: Start launches no worker
        QTimer::singleShot(0, QCoreApplication::instance(), [] { cycle_terminal(); });
        return;
    }
    cycle.fit->start();
}

void install_cycle(QQmlApplicationEngine& engine) {
    static SignalTap tap;
    static QSocketNotifier* input = nullptr;
    static QByteArray pending;
    cycle.clock.start();
    auto* session = engine.singletonInstance<Session*>("edi.app", "Session");
    QTimer::singleShot(0, &tap, [session] {
        if (cycle.operation != QLatin1String("resume") || !session->openProject(QUrl::fromLocalFile(cycle.project))) {
            cycle_emit({{"event", "error"},
                        {"error", cycle.operation != QLatin1String("resume") ? QStringLiteral("unknown operation")
                                                                            : session->lastError()}});
            std::_Exit(1);
        }
        cycle.model = session->project();
        cycle.fit = cycle.model->fit();
        std::vector<QString> names;
        QJsonArray watched;
        const QMetaObject& meta = FitViewModel::staticMetaObject;
        for (int index = meta.methodOffset(); index < meta.methodCount(); ++index) {
            if (meta.method(index).methodType() != QMetaMethod::Signal) continue;
            const int slot = QObject::staticMetaObject.methodCount() + static_cast<int>(names.size());
            names.push_back(QString::fromLatin1(meta.method(index).name()));
            watched.append(names.back());
            QMetaObject::connect(cycle.fit, index, &tap, slot);
        }
        tap.hit = [names](int id) {
            const QString& name = names.at(static_cast<std::size_t>(id));
            cycle_emit({{"event", "fit_signal"}, {"signal", name}});
            if (name == QLatin1String("scanFinished") && cycle.started && !cycle.ended) {
                cycle.ended = true;  // the terminal state once its completion work has settled
                QTimer::singleShot(0, QCoreApplication::instance(), [] { cycle_terminal(); });
            }
        };
        edi::set_scan_file_start_observer(&cycle_inner_fit);
        edi::set_worker_file_observer(&cycle_file_fitted);
        input = new QSocketNotifier(STDIN_FILENO, QSocketNotifier::Read, &tap);
        QObject::connect(input, &QSocketNotifier::activated, &tap, [] {
            char buffer[4096];
            const ssize_t got = ::read(STDIN_FILENO, buffer, sizeof buffer);
            if (got <= 0) {
                input->setEnabled(false);
                return;
            }
            pending.append(buffer, static_cast<qsizetype>(got));
            for (qsizetype end = pending.indexOf('\n'); end >= 0; end = pending.indexOf('\n')) {
                const QByteArray line = pending.left(end).trimmed();
                pending.remove(0, end + 1);
                if (!line.isEmpty()) cycle_command(line);
            }
        });
        // Ready once opening has settled: no calculation running and, for a finished scan, its last row shown.
        auto* settle = new QTimer(&tap);
        settle->setInterval(25);
        QObject::connect(settle, &QTimer::timeout, &tap, [settle, watched] {
            if (cycle.model->calculating()) return;
            settle->stop();
            if (cycle.fit->scanTotal() > 0 && cycle.fit->scanProcessed() == cycle.fit->scanTotal()) cycle_show_last();
            cycle_emit({{"event", "ready"}, {"operation", cycle.operation}, {"signals_watched", watched}});
        });
        settle->start();
    });
}

}  // namespace

std::optional<int> refuse_test_observer(int argc, char* argv[]) {
    for (int index = 1; index < argc; ++index) {
        if (std::strcmp(argv[index], "--test-observer") == 0 && !enabled()) {
            std::fprintf(stderr, "edi_app: --test-observer is for system tests only (EDI_TEST_OBSERVERS=1 in a pytest run)\n");
            return 2;
        }
    }
    return std::nullopt;
}

std::optional<int> start_test_observer(const QStringList& arguments) {
    if (!enabled()) {
        std::fprintf(stderr, "edi_app: --test-observer is for system tests only (EDI_TEST_OBSERVERS=1 in a pytest run)\n");
        return 2;
    }
    const QString action = arguments.value(0);
    if (action == QLatin1String("scan-screen")) {
        screen_observer = true;
        edi::set_worker_file_observer(&file_completed);
        return std::nullopt;
    }
    if (action == QLatin1String("scan-cycle") && arguments.size() >= 3) {
        cycle.project = arguments.at(1);
        cycle.operation = arguments.at(2);
        return std::nullopt;
    }
    if (action == QLatin1String("scan-lifecycle") && arguments.size() >= 2) {
        lifecycle_project = arguments.at(1);
        return std::nullopt;
    }
    if (action != QLatin1String("joint") || arguments.size() < 2) {
        std::fprintf(stderr, "usage: edi_app --test-observer joint <project> | scan-screen | scan-lifecycle <project> | scan-cycle <project> resume\n");
        return 2;
    }
    QJsonObject answer;
    try {
        answer = joint(arguments.at(1));
    } catch (const std::exception& error) {
        answer["error"] = QString::fromUtf8(error.what());
    }
    std::printf("%s\n", QJsonDocument(answer).toJson(QJsonDocument::Compact).constData());
    std::fflush(stdout);
    return answer.contains("before") ? 0 : 1;
}

void configure_test_observer(QQmlApplicationEngine& engine) {
    if (!screen_observer) return;
    // Each run reads and saves the machine settings in a file of its own.
    const QString file = QString::fromUtf8(qgetenv("SCAN_SCREEN_SETTINGS_FILE"));
    if (file.isEmpty()) qFatal("edi_app --test-observer scan-screen needs SCAN_SCREEN_SETTINGS_FILE");
    engine.rootContext()->setContextProperty("pySettingsPath", QUrl::fromLocalFile(file).toString());
}

void install_test_observer(QQmlApplicationEngine& engine) {
    if (!cycle.project.isEmpty()) {
        install_cycle(engine);
        return;
    }
    if (!lifecycle_project.isEmpty()) {
        install_lifecycle(engine);
        return;
    }
    if (!screen_observer) return;
    // Lives until the app quits, as the window does.
    static ScreenObservation o;
    o.window = qobject_cast<QQuickWindow*>(engine.rootObjects().constFirst());
    o.session = engine.singletonInstance<Session*>("edi.app", "Session");
    o.clock.start();
    o.result = {{"mode", setting("SCAN_SCREEN_MODE", "adaptive")}, {"frames", QJsonArray{}}};
    o.finish = new QTimer(o.window);
    o.finish->setSingleShot(true);
    QObject::connect(o.finish, &QTimer::timeout, o.window, [] {
        o.result["error"] = "The actual scan did not settle before the observation deadline";
        publish(o.result);
    });
    o.finish->start(120000);
    QObject::connect(o.window, &QQuickWindow::afterSynchronizing, o.window, [] { record_frame(o); }, Qt::DirectConnection);
    QObject::connect(o.window, &QQuickWindow::frameSwapped, o.window, [] { keep_frame(o); }, Qt::DirectConnection);
    QTimer::singleShot(500, o.window, [] { drive(o); });
}

}  // namespace edi_app

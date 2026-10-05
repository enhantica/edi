#include <QGuiApplication>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QDirIterator>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QQuickItem>
#include <QQuickWindow>
#include <QMouseEvent>
#include <cmath>
#include <QSemaphore>
#include <QTimer>
#include <QtQml>
#include <algorithm>
#include <atomic>
#include <bit>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <optional>
#include <sys/resource.h>
#include <thread>
#undef slots
#include "crysta/analysis.hpp"
#include "crysta/model.hpp"
#include "crysta/constraints.hpp"
#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "engine_setup.hpp"
#include "evolution_view_model.hpp"
#include "measured_layer.hpp"
#include "parameter_item.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
using Clock = std::chrono::steady_clock;
QJsonArray layer_points;
std::ofstream work_stream, trace_stream;
std::string stage;
edi_app::ProjectViewModel* active = nullptr;
std::atomic<int> completed{0};
int stop_after = 0;
bool exercise_follow = false;
QJsonArray events;
std::vector<double> early_times, late_times;
Clock::time_point previous;
long peak_1000 = 0, peak_end = 0;

long peak_memory() {
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
#ifdef __APPLE__
    return usage.ru_maxrss;
#else
    return usage.ru_maxrss * 1024L;
#endif
}

bool until(const std::function<bool()>& ready, int milliseconds = 120000) {
    if (ready()) return true;
    QEventLoop loop;
    QTimer check, deadline;
    check.setInterval(0);
    deadline.setSingleShot(true);
    QObject::connect(&check, &QTimer::timeout, &loop, [&] { if (ready()) loop.quit(); });
    QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
    check.start(); deadline.start(milliseconds); loop.exec();
    return ready();
}

QJsonArray table(edi_app::RowTableModel* model) {
    QJsonArray rows;
    for (int index = 0; index < model->count(); ++index) {
        QJsonObject row;
        for (auto role : model->roleNames()) {
            row[QString::fromUtf8(role)] = QJsonValue::fromVariant(model->get(index, QString::fromUtf8(role)));
        }
        rows.append(row);
    }
    return rows;
}

QJsonObject state(edi_app::ProjectViewModel& view) {
    auto* fit = view.fit();
    return {{"running", fit->running()}, {"scanning", fit->scanning()},
            {"following", fit->following()}, {"continuable", fit->continuable()},
            {"available", fit->available()}, {"canUndo", view.canUndo()},
            {"selected", view.currentExperimentIndex()}, {"outcome", fit->outcome()},
            {"scanFiles", fit->scanFiles()}, {"ok", fit->scanOk()}, {"failed", fit->scanFailed()}};
}

QJsonObject parameters(edi_app::ProjectViewModel& view) {
    QJsonObject values;
    auto* model = view.parameters();
    for (int row = 0; row < model->count(); ++row) {
        auto* parameter = model->get(row, "parameter").value<edi_app::ParameterItem*>();
        if (!parameter) continue;
        for (const edi::NamedParameter& entry : edi::named_parameters(view.project()))
            if (entry.parameter == parameter->parameter())
                values[QString::fromStdString(entry.unique_name)] = QJsonArray{parameter->value(),
                    parameter->hasUncertainty() ? QJsonValue(parameter->uncertainty()) : QJsonValue()};
    }
    return values;
}

QJsonArray pattern(edi_app::ProjectViewModel& view) {
    QJsonArray points;
    auto* model = view.currentExperiment()->pattern();
    for (int row = 0; row < model->rowCount(); ++row) {
        const QModelIndex index = model->index(row);
        points.append(QJsonArray{model->data(index, edi_app::PatternModel::XRole).toDouble(),
            model->data(index, edi_app::PatternModel::IntensityMeasRole).toDouble(),
            model->data(index, edi_app::PatternModel::IntensityMeasSuRole).toDouble(),
            model->data(index, edi_app::PatternModel::IntensityCalcRole).toDouble()});
    }
    return points;
}

QByteArray contents(const std::string& project, const char* relative) {
    QFile file(QString::fromStdString(project + "/" + relative));
    if (!file.open(QIODevice::ReadOnly)) return {};
    return file.readAll();
}

QJsonObject run(edi_app::ProjectViewModel& view, const std::string& label, int limit,
                bool follow = false) {
    stage = label; completed = 0; stop_after = limit; exercise_follow = follow;
    previous = Clock::now(); active = &view;
    QJsonObject before = state(view);
    bool entered = false;
    auto connection = QObject::connect(view.fit(), &edi_app::FitViewModel::runningChanged,
        [&] { entered = entered || view.fit()->running(); });
    view.fit()->start();
    const bool ended = until([&] { return !view.fit()->running(); }, 7200000);
    QObject::disconnect(connection);
    QJsonObject after = state(view);
    active = nullptr;
    return {{"before", before}, {"after", after}, {"entered", entered}, {"ended", ended},
            {"completed", completed.load()}};
}

std::unique_ptr<edi_app::ProjectViewModel> load(const std::string& path) {
    auto view = std::make_unique<edi_app::ProjectViewModel>(edi::load_project(path), nullptr);
    QCoreApplication::processEvents();
    until([&] { return !view->calculating() && !view->currentExperiment()->pattern()->stale(); });
    return view;
}

QJsonObject inventory(const std::string& path) {
    auto view = load(path);
    const int initial = view->currentExperimentIndex();
    QJsonArray selected;
    for (int row = 0; row < view->experiments()->count(); ++row) {
        view->setCurrentExperimentIndex(row);
        until([&] { return !view->calculating(); });
        QCoreApplication::processEvents();
        selected.append(QJsonObject{{"index", view->currentExperimentIndex()},
            {"parameters", parameters(*view)}, {"pattern", pattern(*view)},
            {"fitOutcome", view->currentExperiment()->fitOutcome()}});
    }
    return {{"rows", table(view->experiments())}, {"columns", QJsonArray::fromStringList(view->scanColumns())},
            {"initial", initial}, {"selected", selected}};
}

QJsonObject evolution(const std::string& path) {
    auto view = load(path);
    edi_app::MeasuredLayer layer;
    auto* model = view->evolution(); model->setLayer(&layer);
    QJsonArray columns;
    for (int parameter = 0; parameter < model->parameters()->count(); ++parameter) {
        model->setCurrentParameter(parameter);
        QJsonArray axes;
        for (int mode = 0; mode < 2; ++mode) {
            model->setXMode(mode);
            axes.append(QJsonObject{{"mode", mode}, {"title", model->xTitle()},
                {"points", layer_points}, {"count", model->count()}});
        }
        columns.append(QJsonObject{{"name", model->yTitle()}, {"axes", axes}});
    }
    return {{"columns", columns}};
}

QJsonObject flow(const std::string& path) {
    auto view = load(path);
    const QByteArray original = contents(path, "analysis/results.csv");
    auto first = run(*view, "stop", 40, true);
    const QByteArray partial = contents(path, "analysis/results.csv");
    view->undo();
    const bool restored = contents(path, "analysis/results.csv") == original;
    QJsonObject undone = state(*view);
    auto second = run(*view, "stop-again", 40);
    const QByteArray prefix = contents(path, "analysis/results.csv");
    auto continued = run(*view, "continue", 0);
    const bool retained = contents(path, "analysis/results.csv").startsWith(prefix);
    const QByteArray before_edit = contents(path, "analysis/results.csv");
    if (view->parameters()->count()) {
        auto* item = view->parameters()->get(0, "parameter").value<edi_app::ParameterItem*>();
        if (item) item->setValue(item->value() + 0.001);
    }
    QJsonObject edited = state(*view);
    bool stale_fit = view->fit()->property("outOfDate").toBool();
    // The chart consumes the fit result's stale state, rather than owning another flag.
    QQmlEngine engine; edi_app::use_fresh_settings(); edi_app::configure_engine(engine);
    engine.rootContext()->setContextProperty("probeProject", view.get());
    QQmlComponent chart(&engine);
    chart.setData("import QtQuick\nimport edi.app\nEvolutionChart { width: 1000; height: 400; project: probeProject }", QUrl("qrc:/scan-stale.qml"));
    until([&] { return chart.status() != QQmlComponent::Loading; });
    std::unique_ptr<QObject> chart_object(chart.create());
    auto* marker = chart_object ? chart_object->findChild<QObject*>("evolution.outOfDate") : nullptr;
    bool stale_evolution = marker && marker->property("visible").toBool();
    const bool edit_kept = contents(path, "analysis/results.csv") == before_edit;
    auto restarted = run(*view, "restart", 0);
    return {{"stop", first}, {"partial", QString::fromUtf8(partial)}, {"undoRestored", restored},
        {"undone", undone}, {"stopAgain", second}, {"continue", continued}, {"prefixKept", retained},
        {"edited", edited}, {"editKept", edit_kept}, {"staleFit", stale_fit},
        {"staleEvolution", stale_evolution}, {"restart", restarted}, {"events", events}};
}

QJsonObject single(const std::string& path, int index) {
    auto view = load(path); view->setCurrentExperimentIndex(index);
    until([&] { return !view->calculating(); });
    QJsonObject seed = parameters(*view);
    view->analysis()->setFittingMode("single");
    auto result = run(*view, "single", 0);
    const auto save = view->saveTo(QString::fromStdString(path + "-saved"));
    return {{"seed", seed}, {"run", result}, {"saveError", save},
        {"analysis", QString::fromStdString(view->savedFile("analysis/analysis.edi"))},
        {"rows", table(view->experiments())}, {"result", parameters(*view)}};
}

QJsonObject bundle(const std::string& id, const std::string& destination) {
    edi_app::Session session;
    const bool opened = session.openExample(QString::fromStdString(id));
    if (!opened) return {{"opened", false}, {"error", session.lastError()}};
    auto* view = session.project(); const std::string temporary = view->project().path;
    auto result = run(*view, "bundle", 0);
    const QByteArray bytes = contents(temporary, "analysis/results.csv");
    const bool needs_save = session.needsSaveAs();
    const bool saved = session.saveAs(QUrl::fromLocalFile(QString::fromStdString(destination)));
    return {{"opened", opened}, {"path", QString::fromStdString(temporary)},
        {"needsSaveAs", needs_save}, {"afterNeedsSaveAs", session.needsSaveAs()}, {"run", result}, {"saved", saved},
        {"beforeSave", QString::fromUtf8(bytes)},
        {"afterSave", QString::fromUtf8(contents(destination, "analysis/results.csv"))}};
}
QJsonObject qml_views(const std::string& path, bool clicks) {
    auto view = load(path);
    QQmlEngine engine;
    edi_app::use_fresh_settings(); edi_app::configure_engine(engine);
    engine.rootContext()->setContextProperty("probeProject", view.get());
    QQmlComponent component(&engine);
    component.setData(R"QML(import QtQuick
import QtQuick.Window
import edi.app
Window {
 width: 1000; height: 760; visible: true
 ExperimentsGroup { x: 0; y: 0; width: 600; project: probeProject; collapsed: false }
 BlockSelector { objectName: "probe.selector"; x: 610; y: 0; width: 350
  blocks: probeProject.experiments; blocksTextRole: "label"; blockKind: "experiment"
  blockIndex: probeProject.currentExperimentIndex; outcomeRole: "fitOutcome"
  onBlockActivated: index => probeProject.currentExperimentIndex = index
 }
 EvolutionChart { x: 0; y: 350; width: 1000; height: 400; project: probeProject }
})QML", QUrl("qrc:/scan-contract.qml"));
    until([&] { return component.status() != QQmlComponent::Loading; });
    std::unique_ptr<QObject> root(component.create());
    if (!root) return {{"error", component.errorString()}};
    auto* window = qobject_cast<QQuickWindow*>(root.get());
    auto* list = root->findChild<QObject*>("experiments.list");
    auto* selector = root->findChild<QObject*>("probe.selector");
    auto* pointer = root->findChild<QQuickItem*>("evolution.pointer");
    if (!window || !list || !selector) return {{"error", "actual list/selector must be instantiated"}};
    auto count_rows = [&] {
        int count = 0;
        for (QObject* object : root->findChildren<QObject*>())
            if (object->objectName().startsWith("experiments.row.")) ++count;
        return count;
    };
    until([&] { return count_rows() > 0; });
    const int first = count_rows();
    const double height = list->property("height").toDouble();
    double row_height = 0;
    for (QObject* object : root->findChildren<QObject*>())
        if (object->objectName().startsWith("experiments.row.")) {
            row_height = object->property("height").toDouble(); break;
        }
    if (!(row_height > 0)) return {{"error", "visible table row must have positive height"}};
    const double cache = list->property("cacheBuffer").toDouble();
    const int bound = static_cast<int>(std::ceil((height + 2*cache) / row_height)) + 2;
    QMetaObject::invokeMethod(list, "positionViewAtIndex", Q_ARG(int, view->experiments()->count()-1), Q_ARG(int, 1));
    until([&] { return root->findChild<QObject*>("experiments.row." + QString::number(view->experiments()->count()-1)); });
    const bool last = root->findChild<QObject*>("experiments.row." + QString::number(view->experiments()->count()-1));
    auto* popup = selector->property("popup").value<QObject*>();
    if (popup) QMetaObject::invokeMethod(popup, "open");
    const bool popup_opened = until([&] { return popup && popup->property("opened").toBool(); });
    auto* content = popup ? popup->property("contentItem").value<QQuickItem*>() : nullptr;
    QObject* popup_list = content;
    if (popup_list && !popup_list->property("count").isValid()) {
        for (QObject* child : popup_list->findChildren<QObject*>())
            if (child->property("count").isValid() && child->property("contentY").isValid()) { popup_list=child; break; }
    }
    int delegates = -1;
    int popup_bound = -1;
    if (popup_list) {
        auto* items = popup_list->property("contentItem").value<QQuickItem*>();
        if (items) delegates = items->childItems().size();
        const double item_height = popup_list->property("height").toDouble();
        const double buffer = popup_list->property("cacheBuffer").toDouble();
        const double entry_height = row_height > 0 ? row_height : 20;
        popup_bound = static_cast<int>(std::ceil((item_height + 2*buffer)/entry_height)) + 4;
    }
    if (popup) QMetaObject::invokeMethod(popup, "close");
    QJsonArray clicked;
    if (clicks && pointer && view->evolution()->count()) {
        const int wanted = std::min(17, view->experiments()->count()-1);
        auto* model = view->evolution(); model->setXMode(1);
        until([&] { return pointer->width() > 0 && pointer->height() > 0 && !layer_points.isEmpty(); });
        for (const QJsonValue& value : layer_points) {
            const QJsonArray point = value.toArray();
            if (point[0].toDouble() != wanted + 1) continue;
            const QPointF local((point[0].toDouble()-model->xMin())/(model->xMax()-model->xMin())*pointer->width(),
                (model->yMax()-(point[2].toDouble()+point[3].toDouble())/2)/(model->yMax()-model->yMin())*pointer->height());
            const QPointF position = pointer->mapToScene(local);
            QMouseEvent down(QEvent::MouseButtonPress, position, position, Qt::LeftButton, Qt::LeftButton, Qt::NoModifier);
            QMouseEvent up(QEvent::MouseButtonRelease, position, position, Qt::LeftButton, Qt::NoButton, Qt::NoModifier);
            QCoreApplication::sendEvent(window, &down); QCoreApplication::sendEvent(window, &up);
            QCoreApplication::processEvents();
            clicked.append(QJsonObject{{"wanted", wanted}, {"selected", view->currentExperimentIndex()},
                {"selector", selector->property("currentIndex").toInt()}, {"parameters", parameters(*view)}});
            break;
        }
    }
    return {{"count", view->experiments()->count()}, {"firstDelegates", first}, {"lastReached", last},
        {"lastDelegates", count_rows()}, {"tableBound", bound}, {"popupOpened", popup_opened},
        {"popupDelegates", delegates}, {"popupBound", popup_bound}, {"clicked", clicked},
        {"modelObjects", view->findChildren<QObject*>().size()}};
}

QJsonObject prepare_scale(const std::string& path) {
    auto project = edi::load_project(path);
    edi::Parameter* selected = nullptr;
    for (auto& entry : edi::parameter_entries(project)) {
        entry.parameter->free = false;
        if (!selected && entry.category.find("background") != std::string::npos && entry.name == "intensity") selected = entry.parameter;
    }
    if (!selected) return {{"error", "synthetic scale needs one background parameter"}};
    selected->free = true;
    edi::save_project(project, path);
    return {{"prepared", true}};
}
}

void scan_contract_layer_receipt(const QList<QPointF>& points, const QList<double>& low,
                                 const QList<double>& high) {
    layer_points = {};
    for (qsizetype index = 0; index < points.size(); ++index)
        layer_points.append(QJsonArray{points[index].x(), points[index].y(), low.value(index), high.value(index)});
}

void scan_contract_work(const std::string& file, const crysta::Project& project) {
    if (!work_stream.is_open()) return;
    const auto& data = *project.experiment().data.get();
    QCryptographicHash hash(QCryptographicHash::Sha256);
    for (const auto* values : {&data.grid, &data.intensity, &data.sigma})
        hash.addData(QByteArray(reinterpret_cast<const char*>(values->data()),
                               static_cast<qsizetype>(values->size() * sizeof(double))));
    if (trace_stream.is_open()) trace_stream << "work\t" << stage << "\t" << file << std::endl;
    work_stream << stage << '\t' << file << '\t' << hash.result().toHex().constData() << '\n';
}

void scan_contract_file_completed(const std::string& file) {
    const int count = ++completed;
    const auto now = Clock::now();
    const double seconds = std::chrono::duration<double>(now - previous).count(); previous = now;
    if (count >= 1001 && count <= 2000) early_times.push_back(seconds);
    if (count >= 99001 && count <= 100000) late_times.push_back(seconds);
    if (count == 1000) peak_1000 = peak_memory();
    if (count == 100000) peak_end = peak_memory();
    if (!active) return;
    QMetaObject::invokeMethod(qApp, [file, count] {
        if (!active) return;
        if (completed <= 162) events.append(QJsonObject{{"file", QString::fromStdString(file)},
            {"stage", QString::fromStdString(stage)}, {"state", state(*active)}});
        if (exercise_follow && count == 13) active->setCurrentExperimentIndex(17);
        if (exercise_follow && count == 21) active->fit()->setFollowing(true);
        if (stop_after && count == stop_after) active->fit()->cancel();
    }, Qt::BlockingQueuedConnection);
}

int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    if (argc < 3) return 2;
    const std::string command = argv[1], path = argv[2];
    if (const char* work = std::getenv("SCAN_CONTRACT_WORK")) work_stream.open(work);
    if (const char* trace = std::getenv("EDI_C08_NATIVE_OBSERVER_LOG")) trace_stream.open(trace, std::ios::app);
    stage = command;
    QJsonObject answer;
    try {
        if (command == "reference") {
            auto project = crysta::load_project(path);
            crysta::fit_project(project);
            answer["csv"] = QString::fromUtf8(contents(path, "analysis/results.csv"));
        } else if (command == "reference-projection") {
            QFile cells(argv[3]); cells.open(QIODevice::ReadOnly);
            const QJsonArray rows = QJsonDocument::fromJson(cells.readAll()).array();
            auto seed = crysta::load_project(path);
            QJsonArray projected;
            for (const auto& item : rows) {
                const auto row = item.toObject(); crysta::Project project(seed);
                QJsonObject expected;
                for (auto it = row.begin(); it != row.end(); ++it) {
                    if (!it.key().endsWith(".uncertainty")) continue;
                    const QString name = it.key().chopped(12);
                    auto& parameter = crysta::resolve_unique_name(project, name.toStdString());
                    parameter.set_value(row[name].toString().toDouble());
                    parameter.set_uncertainty(it.value().toString().isEmpty() ? std::optional<double>()
                        : std::optional<double>(it.value().toString().toDouble()));
                    expected[name] = QJsonArray{parameter.value(),
                        parameter.uncertainty() ? QJsonValue(*parameter.uncertainty()) : QJsonValue()};
                }
                const std::string name = QFileInfo(row["file_path"].toString()).fileName().toStdString();
                project.experiment().data = crysta::read_sequential_scan_data(path + "/experiments/d20_scan/" + name);
                crysta::apply_relations(project); crysta::calculate_project(project);
                const auto& data = *project.experiment().data.get();
                const auto& calc = project.experiment().computed().data().intensity_calc.values();
                QJsonArray points;
                for (std::size_t i = 0; i < data.grid.size(); ++i)
                    points.append(QJsonArray{data.grid[i], data.intensity[i], data.sigma[i], calc[i]});
                projected.append(QJsonObject{{"parameters", expected}, {"pattern", points}});
            }
            answer["selected"] = projected;
        } else if (command == "select") {
            auto view = load(path); QJsonArray selected;
            for (int index : {0, std::min(513, view->experiments()->count()-1), view->experiments()->count()-1, 0}) {
                if (trace_stream.is_open()) trace_stream << "select\t" << index << std::endl;
                view->setCurrentExperimentIndex(index); QCoreApplication::processEvents();
                until([&] { return !view->calculating(); });
                selected.append(QJsonObject{{"index", view->currentExperimentIndex()}, {"pattern", pattern(*view)}});
            }
            answer["selected"] = selected;
        } else if (command == "eager") {
            QDirIterator files(QString::fromStdString(path + "/experiments/d20_scan"), {"*.dat"}, QDir::Files);
            int read = 0;
            while (files.hasNext()) { QFile data(files.next()); data.open(QIODevice::ReadOnly); data.readAll(); ++read; }
            auto view = load(path); answer["eagerRead"] = read;
        } else if (command == "inventory") answer = inventory(path);
        else if (command == "evolution") answer = evolution(path);
        else if (command == "flow") answer = flow(path);
        else if (command == "single") answer = single(path, argc > 3 ? std::stoi(argv[3]) : 17);
        else if (command == "virtual") answer = qml_views(path, false);
        else if (command == "click") answer = qml_views(path, true);
        else if (command == "prepare-scale") answer = prepare_scale(path);
        else if (command == "bundle") answer = bundle(path, argv[3]);
        else if (command == "run" || command == "scale") {
            auto view = load(path); answer = run(*view, command, 0);
            answer["csv"] = QString::fromUtf8(contents(path, "analysis/results.csv"));
            answer["peak1000"] = static_cast<double>(peak_1000);
            answer["peak100000"] = static_cast<double>(peak_end);
            auto median = [](std::vector<double> values) {
                if (values.empty()) return 0.0;
                std::sort(values.begin(), values.end()); return values[values.size()/2];
            };
            answer["medianEarly"] = median(early_times); answer["medianLate"] = median(late_times);
            answer["earlySamples"] = static_cast<int>(early_times.size());
            answer["lateSamples"] = static_cast<int>(late_times.size());
        } else answer["error"] = "unknown observation command";
    } catch (const std::exception& error) { answer["error"] = error.what(); }
    if (work_stream.is_open()) work_stream.close();
    std::cout << QJsonDocument(answer).toJson(QJsonDocument::Compact).constData() << '\n';
}

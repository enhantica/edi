#include <sys/resource.h>

#include <QColor>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDirIterator>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMouseEvent>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlExpression>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSemaphore>
#include <QSet>
#include <QThread>
#include <QTimer>
#include <QtQml>
#include <algorithm>
#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <numeric>
#include <optional>
#include <thread>
#undef slots
#include "crysta/analysis.hpp"
#include "crysta/constraints.hpp"
#include "crysta/model.hpp"
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
QJsonObject expected_measurements;
std::vector<double> early_times, late_times;
Clock::time_point previous;
long peak_1000 = 0, peak_end = 0;
std::size_t work_index = 0;
std::atomic<bool> worker_off_owner{true};

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
    QObject::connect(&check, &QTimer::timeout, &loop, [&] {
        if (ready()) loop.quit();
    });
    QObject::connect(&deadline, &QTimer::timeout, &loop, &QEventLoop::quit);
    check.start();
    deadline.start(milliseconds);
    loop.exec();
    return ready();
}

QJsonArray table(edi_app::RowTableModel* model) {
    QJsonArray rows;
    for (int index = 0; index < model->count(); ++index) {
        QJsonObject row;
        for (auto role : model->roleNames()) {
            row[QString::fromUtf8(role)] =
                QJsonValue::fromVariant(model->get(index, QString::fromUtf8(role)));
        }
        rows.append(row);
    }
    return rows;
}

QJsonObject state(edi_app::ProjectViewModel& view) {
    auto* fit = view.fit();
    return {{"running", fit->running()},
            {"scanning", fit->scanning()},
            {"following", fit->following()},
            {"continuable", fit->continuable()},
            {"available", fit->available()},
            {"canUndo", view.canUndo()},
            {"selected", view.currentExperimentIndex()},
            {"outcome", fit->outcome()},
            {"unavailableReason", fit->unavailableReason()},
            {"lastError", view.lastError()},
            {"scanFiles", fit->scanFiles()},
            {"ok", fit->scanOk()},
            {"failed", fit->scanFailed()}};
}

QJsonObject parameters(edi_app::ProjectViewModel& view) {
    QJsonObject values;
    auto* model = view.parameters();
    for (int row = 0; row < model->count(); ++row) {
        auto* parameter = model->get(row, "parameter").value<edi_app::ParameterItem*>();
        if (!parameter) continue;
        for (const edi::NamedParameter& entry : edi::named_parameters(view.project()))
            if (entry.parameter == parameter->parameter())
                values[QString::fromStdString(entry.unique_name)] =
                    QJsonArray{parameter->value(), parameter->hasUncertainty()
                                                       ? QJsonValue(parameter->uncertainty())
                                                       : QJsonValue()};
    }
    return values;
}

QJsonArray pattern(edi_app::ProjectViewModel& view) {
    QJsonArray points;
    auto* model = view.currentExperiment()->pattern();
    for (int row = 0; row < model->rowCount(); ++row) {
        const QModelIndex index = model->index(row);
        points.append(
            QJsonArray{model->data(index, edi_app::PatternModel::XRole).toDouble(),
                       model->data(index, edi_app::PatternModel::IntensityMeasRole).toDouble(),
                       model->data(index, edi_app::PatternModel::IntensityMeasSuRole).toDouble(),
                       model->data(index, edi_app::PatternModel::IntensityCalcRole).toDouble()});
    }
    return points;
}

QString measured_pattern_hash(edi_app::ProjectViewModel& view) {
    const QJsonArray rows = pattern(view);
    QCryptographicHash hash(QCryptographicHash::Sha256);
    for (int column = 0; column < 3; ++column) {
        std::vector<double> values;
        for (const QJsonValue& row : rows) values.push_back(row.toArray()[column].toDouble());
        hash.addData(QByteArray(reinterpret_cast<const char*>(values.data()),
                                static_cast<qsizetype>(values.size() * sizeof(double))));
    }
    return QString::fromLatin1(hash.result().toHex());
}

QByteArray contents(const std::string& project, const char* relative) {
    QFile file(QString::fromStdString(project + "/" + relative));
    if (!file.open(QIODevice::ReadOnly)) return {};
    return file.readAll();
}

QJsonObject run(edi_app::ProjectViewModel& view, const std::string& label, int limit,
                bool follow = false) {
    stage = label;
    completed = 0;
    worker_off_owner = true;
    stop_after = limit;
    exercise_follow = follow;
    previous = Clock::now();
    active = &view;
    QJsonObject before = state(view);
    bool entered = false;
    QString refusal;
    auto refusal_connection = QObject::connect(view.fit(), &edi_app::FitViewModel::refused,
                                               [&](const QString& reason) { refusal = reason; });
    auto connection = QObject::connect(view.fit(), &edi_app::FitViewModel::runningChanged,
                                       [&] { entered = entered || view.fit()->running(); });
    view.fit()->start();
    const bool ended = until([&] { return !view.fit()->running(); }, 7200000);
    QObject::disconnect(connection);
    const bool projected = !entered || until([&] {
        return !view.calculating() && !view.currentExperiment()->pattern()->stale();
    });
    QObject::disconnect(refusal_connection);
    QJsonObject after = state(view);
    active = nullptr;
    return {{"before", before},
            {"after", after},
            {"entered", entered},
            {"ended", ended},
            {"projected", projected},
            {"refusal", refusal},
            {"completed", completed.load()},
            {"workerOffOwner", worker_off_owner.load()}};
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
        QCoreApplication::processEvents();
        until([&] {
            return !view->calculating() && !view->currentExperiment()->pattern()->stale();
        });
        QCoreApplication::processEvents();
        selected.append(QJsonObject{{"index", view->currentExperimentIndex()},
                                    {"parameters", parameters(*view)},
                                    {"pattern", pattern(*view)},
                                    {"fitOutcome", view->currentExperiment()->fitOutcome()}});
    }
    return {{"rows", table(view->experiments())},
            {"columns", QJsonArray::fromStringList(view->scanColumns())},
            {"initial", initial},
            {"selected", selected}};
}

QJsonObject evolution(const std::string& path) {
    auto view = load(path);
    edi_app::MeasuredLayer layer;
    auto* model = view->evolution();
    model->setLayer(&layer);
    QJsonArray columns;
    for (int parameter = 0; parameter < model->parameters()->count(); ++parameter) {
        model->setCurrentParameter(parameter);
        QJsonArray axes;
        for (int mode = 0; mode < 2; ++mode) {
            model->setXMode(mode);
            axes.append(QJsonObject{{"mode", mode},
                                    {"title", model->xTitle()},
                                    {"points", layer_points},
                                    {"count", model->count()}});
        }
        columns.append(QJsonObject{{"name", model->yTitle()}, {"axes", axes}});
    }
    return {{"columns", columns}};
}

QJsonObject result_files(const std::string& path) {
    QJsonObject files;
    for (const char* name : {"results.csv", "results-provenance.csv", "scan-run.json"}) {
        const QString relative = QStringLiteral("analysis/") + name;
        files[name] =
            QFileInfo::exists(QString::fromStdString(path) + "/" + relative)
                ? QJsonValue(QString::fromUtf8(contents(path, relative.toUtf8().constData())))
                : QJsonValue(QJsonValue::Null);
    }
    return files;
}

QJsonObject flow(const std::string& path) {
    auto view = load(path);
    const QJsonObject original = result_files(path);
    const QJsonObject fitted = state(*view);
    // Owner 2026-10-06: a completed scan cannot restart. Reset, not Start,
    // captures all old result files as one Undo transaction.
    view->fit()->reset();
    const QJsonObject reset_files = result_files(path), reset_state = state(*view);
    view->undo();
    const bool reset_restored = result_files(path) == original;
    const QJsonObject restored_state = state(*view);
    view->fit()->reset();
    const QJsonObject before_first = result_files(path);
    auto first = run(*view, "stop", 40, true);
    const QByteArray partial = contents(path, "analysis/results.csv");
    view->undo();
    const bool restored = result_files(path) == before_first;
    QJsonObject undone = state(*view);
    auto second = run(*view, "stop-again", 40);
    const QByteArray prefix = contents(path, "analysis/results.csv");
    if (view->parameters()->count()) {
        auto* parameter = view->parameters()->get(0, "parameter").value<edi_app::ParameterItem*>();
        if (parameter) parameter->setValue(parameter->value() + 0.001);
    }
    until([&] { return !view->calculating() && !view->currentExperiment()->pattern()->stale(); });
    const QJsonObject partial_edited = state(*view);
    auto continued = run(*view, "continue", 0);
    const bool retained = contents(path, "analysis/results.csv").startsWith(prefix);
    const QByteArray before_edit = contents(path, "analysis/results.csv");
    const QJsonArray old_fit_rows = table(view->fit()->results());
    edi_app::MeasuredLayer old_layer;
    view->evolution()->setLayer(&old_layer);
    const QJsonArray old_points = layer_points;
    if (view->parameters()->count()) {
        auto* item = view->parameters()->get(0, "parameter").value<edi_app::ParameterItem*>();
        if (item) item->setValue(item->value() + 0.001);
    }
    until([&] { return !view->calculating() && !view->currentExperiment()->pattern()->stale(); });
    QJsonObject edited = state(*view);
    bool stale_fit = view->fit()->property("outOfDate").toBool();
    QQmlEngine engine;
    edi_app::use_fresh_settings();
    edi_app::configure_engine(engine);
    engine.rootContext()->setContextProperty("probeProject", view.get());
    QQmlComponent chart(&engine);
    chart.setData(
        "import QtQuick\nimport edi.app\nEvolutionChart { width: 1000; height: 400; project: "
        "probeProject }",
        QUrl("qrc:/scan-stale.qml"));
    until([&] { return chart.status() != QQmlComponent::Loading; });
    std::unique_ptr<QObject> chart_object(chart.create());
    auto* marker =
        chart_object ? chart_object->findChild<QObject*>("evolution.outOfDate") : nullptr;
    bool stale_evolution = marker && marker->property("visible").toBool();
    const bool edit_kept = contents(path, "analysis/results.csv") == before_edit;
    const bool results_visible = !old_fit_rows.isEmpty() &&
                                 old_fit_rows == table(view->fit()->results()) &&
                                 !old_points.isEmpty() && old_points == layer_points;
    auto blocked = run(*view, "completed-start", 0);
    const QJsonObject edited_files = result_files(path);
    view->fit()->reset();
    const QJsonObject edit_reset_files = result_files(path), edit_reset_state = state(*view);
    view->undo();
    const bool edit_reset_restored = result_files(path) == edited_files;
    const bool undo_stale = view->fit()->property("outOfDate").toBool();
    view->fit()->reset();
    auto restarted = run(*view, "restart", 0);
    return {{"originalFiles", original},
            {"partialEdited", partial_edited},
            {"fitted", fitted},
            {"resetFiles", reset_files},
            {"resetState", reset_state},
            {"resetRestored", reset_restored},
            {"restoredState", restored_state},
            {"stop", first},
            {"partial", QString::fromUtf8(partial)},
            {"undoRestored", restored},
            {"undone", undone},
            {"stopAgain", second},
            {"continue", continued},
            {"prefixKept", retained},
            {"edited", edited},
            {"editKept", edit_kept},
            {"staleFit", stale_fit},
            {"staleEvolution", stale_evolution},
            {"oldResultsVisible", results_visible},
            {"blocked", blocked},
            {"editResetFiles", edit_reset_files},
            {"editResetState", edit_reset_state},
            {"editResetRestored", edit_reset_restored},
            {"undoStale", undo_stale},
            {"restart", restarted},
            {"events", events}};
}

QJsonObject single(const std::string& path, int index) {
    auto view = load(path);
    view->setCurrentExperimentIndex(index);
    until([&] { return !view->calculating() && !view->currentExperiment()->pattern()->stale(); });
    QJsonObject seed = parameters(*view);
    view->analysis()->setFittingMode("single");
    view->fit()->setFollowing(true);
    const bool following_before = view->fit()->following();
    auto result = run(*view, "single", 0);
    view->fit()->setFollowing(true);
    const bool following_after = view->fit()->following();
    const auto save = view->saveTo(QString::fromStdString(path + "-saved"));
    return {{"seed", seed},
            {"run", result},
            {"followingBefore", following_before},
            {"followingAfter", following_after},
            {"saveError", save},
            {"analysis", QString::fromStdString(view->savedFile("analysis/analysis.edi"))},
            {"rows", table(view->experiments())},
            {"result", parameters(*view)}};
}

QJsonObject tree_hashes(const QString& root) {
    QJsonObject result;
    QDirIterator files(root, QDir::Files, QDirIterator::Subdirectories);
    while (files.hasNext()) {
        QFile file(files.next());
        if (!file.open(QIODevice::ReadOnly))
            throw std::runtime_error("source receipt must read every project file");
        result[file.fileName().mid(root.size() + 1)] = QString::fromLatin1(
            QCryptographicHash::hash(file.readAll(), QCryptographicHash::Sha256).toHex());
    }
    return result;
}

QJsonObject bundle(const std::string& id, const std::string& destination, bool readonly = false) {
    const QString source = readonly ? QString::fromStdString(id)
                                    : QString::fromStdString(":/edi/examples/" + id + "/project");
    const QJsonObject original = tree_hashes(source);
    edi_app::Session session;
    const bool opened = readonly ? session.openProject(QUrl::fromLocalFile(source))
                                 : session.openExample(QString::fromStdString(id));
    if (!opened) return {{"opened", false}, {"error", session.lastError()}};
    auto* view = session.project();
    const std::string temporary = view->project().path;
    auto result = run(*view, "bundle", 0);
    const QByteArray bytes = contents(temporary, "analysis/results.csv");
    const bool needs_save = session.needsSaveAs();
    const bool saved = session.saveAs(QUrl::fromLocalFile(QString::fromStdString(destination)));
    edi_app::Session fresh;
    const bool fresh_opened = readonly ? fresh.openProject(QUrl::fromLocalFile(source))
                                       : fresh.openExample(QString::fromStdString(id));
    const QByteArray fresh_csv =
        fresh_opened ? contents(fresh.project()->project().path, "analysis/results.csv")
                     : QByteArray("missing");
    return {{"opened", opened},
            {"path", QString::fromStdString(temporary)},
            {"needsSaveAs", needs_save},
            {"afterNeedsSaveAs", session.needsSaveAs()},
            {"run", result},
            {"saved", saved},
            {"beforeSave", QString::fromUtf8(bytes)},
            {"sourceBefore", original},
            {"sourceAfter", tree_hashes(source)},
            {"savedTree", tree_hashes(QString::fromStdString(destination))},
            {"freshOpened", fresh_opened},
            {"freshCSV", QString::fromUtf8(fresh_csv)},
            {"afterSave", QString::fromUtf8(contents(destination, "analysis/results.csv"))}};
}

QJsonObject qml_views(const std::string& path, bool clicks) {
    auto view = load(path);
    QQmlEngine engine;
    edi_app::use_fresh_settings();
    edi_app::configure_engine(engine);
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
  Component.onCompleted: {
   if ("templateRole" in this) this.templateRole = "isTemplate"
   if ("currentTemplate" in this) this.currentTemplate = Qt.binding(() => probeProject.templateIndex === probeProject.currentExperimentIndex)
  }
  onBlockActivated: index => probeProject.currentExperimentIndex = index
 }
 EvolutionChart { x: 0; y: 350; width: 1000; height: 400; project: probeProject }
})QML",
                      QUrl("qrc:/scan-contract.qml"));
    until([&] { return component.status() != QQmlComponent::Loading; });
    std::unique_ptr<QObject> root(component.create());
    if (!root) return {{"error", component.errorString()}};
    auto* window = qobject_cast<QQuickWindow*>(root.get());
    auto actual_objects = [&] {
        QSet<QObject*> objects;
        for (auto* object : root->findChildren<QObject*>()) objects.insert(object);
        QList<QQuickItem*> pending;
        if (window) pending.append(window->contentItem());
        while (!pending.isEmpty()) {
            auto* item = pending.takeLast();
            objects.insert(item);
            pending.append(item->childItems());
        }
        return objects;
    };
    auto actual_named = [&](const QString& name) -> QObject* {
        for (auto* object : actual_objects())
            if (object->objectName() == name) return object;
        return nullptr;
    };
    auto* list = actual_named("experiments.list");
    auto* selector = actual_named("probe.selector");
    auto* pointer = qobject_cast<QQuickItem*>(actual_named("evolution.pointer"));
    if (!window || !list || !selector)
        return {{"error", "actual list/selector must be instantiated"}};
    auto count_rows = [&] {
        int count = 0;
        for (QObject* object : actual_objects())
            if (object->objectName().startsWith("experiments.row.")) ++count;
        return count;
    };
    QMetaObject::invokeMethod(list, "forceLayout");
    std::cerr << "QML wait for first visible table row; count=" << list->property("count").toInt()
              << " width=" << list->property("width").toDouble()
              << " height=" << list->property("height").toDouble() << std::endl;
    until([&] { return count_rows() > 0; });
    std::cerr << "QML first row count " << count_rows() << std::endl;
    const int first = count_rows();
    QJsonArray template_tags;
    const int initial = view->currentExperimentIndex();
    auto position = [&](int index) {
        QJSValue object = engine.newQObject(list);
        auto method = object.property("positionViewAtIndex");
        const QJSValue result = method.callWithInstance(object, {QJSValue(index), QJSValue(1)});
        if (result.isError()) throw std::runtime_error(result.toString().toStdString());
        QMetaObject::invokeMethod(list, "forceLayout");
    };
    position(initial);
    std::cerr << "QML positioned table at " << initial << std::endl;
    until([&] { return actual_named("experiments.row." + QString::number(initial)); });
    for (QObject* object : actual_objects()) {
        if (object->objectName().startsWith("experiments.template.") &&
            object->property("visible").toBool()) {
            const QColor color = object->property("color").value<QColor>();
            template_tags.append(
                QJsonObject{{"site", "table"},
                            {"text", object->property("text").toString()},
                            {"color", QJsonArray{color.redF(), color.greenF(), color.blueF()}}});
        }
        const QVariant value = object->property("segments");
        const QVariantList segments = value.canConvert<QJSValue>()
                                          ? value.value<QJSValue>().toVariant().toList()
                                          : value.toList();
        for (const QVariant& entry : segments) {
            const auto segment = entry.toMap();
            if (segment.value("text").toString() != "template") continue;
            const QColor color(segment.value("color").toString());
            template_tags.append(
                QJsonObject{{"site", "selector"},
                            {"text", "template"},
                            {"color", QJsonArray{color.redF(), color.greenF(), color.blueF()}}});
        }
    }
    const double height = list->property("height").toDouble();
    double row_height = 0;
    for (QObject* object : actual_objects())
        if (object->objectName().startsWith("experiments.row.")) {
            row_height = object->property("height").toDouble();
            break;
        }
    if (!(row_height > 0)) return {{"error", "visible table row must have positive height"}};
    const double cache = list->property("cacheBuffer").toDouble();
    const int bound = static_cast<int>(std::ceil((height + 2 * cache) / row_height)) + 2;
    position(view->experiments()->count() - 1);
    std::cerr << "QML positioned table at final dataset" << std::endl;
    until([&] {
        return actual_named("experiments.row." +
                            QString::number(view->experiments()->count() - 1));
    });
    const bool last =
        actual_named("experiments.row." + QString::number(view->experiments()->count() - 1));
    std::cerr << "QML final table row reached " << last << std::endl;
    auto* popup = selector->property("popup").value<QObject*>();
    if (popup) QMetaObject::invokeMethod(popup, "open");
    const bool popup_opened = until([&] { return popup && popup->property("opened").toBool(); });
    auto* content = popup ? popup->property("contentItem").value<QQuickItem*>() : nullptr;
    QObject* popup_list = content;
    if (popup_list && !popup_list->property("count").isValid()) {
        for (QObject* child : popup_list->findChildren<QObject*>())
            if (child->property("count").isValid() && child->property("contentY").isValid()) {
                popup_list = child;
                break;
            }
    }
    int delegates = -1;
    int popup_bound = -1;
    if (popup_list) {
        auto* items = popup_list->property("contentItem").value<QQuickItem*>();
        if (items) delegates = items->childItems().size();
        const double item_height = popup_list->property("height").toDouble();
        const double buffer = popup_list->property("cacheBuffer").toDouble();
        double entry_height = 0;
        if (items)
            for (auto* child : items->childItems())
                if (child->property("index").isValid() && child->height() > 0) {
                    entry_height = child->height();
                    break;
                }
        if (entry_height > 0)
            popup_bound =
                static_cast<int>(std::ceil((item_height + 2 * buffer) / entry_height)) + 4;
    }
    if (popup) QMetaObject::invokeMethod(popup, "close");
    std::cerr << "QML popup delegates " << delegates << std::endl;
    QJsonArray clicked;
    if (clicks && pointer && view->evolution()->count()) {
        const int wanted = std::min(17, view->experiments()->count() - 1);
        auto* model = view->evolution();
        model->setXMode(1);
        std::cerr << "QML pointer geometry " << pointer->width() << " " << pointer->height()
                  << std::endl;
        until([&] {
            return pointer->width() > 0 && pointer->height() > 0 && !layer_points.isEmpty();
        });
        for (const QJsonValue& value : layer_points) {
            const QJsonArray point = value.toArray();
            if (point[0].toDouble() != wanted + 1) continue;
            const QPointF local((point[0].toDouble() - model->xMin()) /
                                    (model->xMax() - model->xMin()) * pointer->width(),
                                (model->yMax() - (point[2].toDouble() + point[3].toDouble()) / 2) /
                                    (model->yMax() - model->yMin()) * pointer->height());
            const QPointF position = pointer->mapToScene(local);
            QMouseEvent down(QEvent::MouseButtonPress, position, position, Qt::LeftButton,
                             Qt::LeftButton, Qt::NoModifier);
            QMouseEvent up(QEvent::MouseButtonRelease, position, position, Qt::LeftButton,
                           Qt::NoButton, Qt::NoModifier);
            QCoreApplication::sendEvent(window, &down);
            QCoreApplication::sendEvent(window, &up);
            QCoreApplication::processEvents();
            clicked.append(QJsonObject{{"wanted", wanted},
                                       {"selected", view->currentExperimentIndex()},
                                       {"selector", selector->property("currentIndex").toInt()},
                                       {"parameters", parameters(*view)}});
            break;
        }
    }
    return {{"count", view->experiments()->count()},
            {"firstDelegates", first},
            {"lastReached", last},
            {"lastDelegates", count_rows()},
            {"tableBound", bound},
            {"popupOpened", popup_opened},
            {"popupDelegates", delegates},
            {"popupBound", popup_bound},
            {"clicked", clicked},
            {"templateTags", template_tags},
            {"modelObjects", view->findChildren<QObject*>().size()}};
}

QJsonObject prepare_scale(const std::string& path) {
    auto project = edi::load_project(path);
    edi::Parameter* selected = nullptr;
    for (auto& entry : edi::parameter_entries(project)) {
        entry.parameter->free = false;
        if (!selected && entry.category.find("background") != std::string::npos &&
            entry.name == "intensity")
            selected = entry.parameter;
    }
    if (!selected) return {{"error", "synthetic scale needs one background parameter"}};
    selected->free = true;
    edi::save_project(project, path);
    return {{"prepared", true}};
}
}  // namespace

void scan_contract_layer_receipt(const QList<QPointF>& points, const QList<double>& low,
                                 const QList<double>& high) {
    layer_points = {};
    for (qsizetype index = 0; index < points.size(); ++index)
        layer_points.append(
            QJsonArray{points[index].x(), points[index].y(), low.value(index), high.value(index)});
}

void scan_contract_work(const std::string& file, const crysta::Project& project) {
    if (active && QThread::currentThread() == qApp->thread()) worker_off_owner = false;
    if (!work_stream.is_open()) return;
    const auto& data = *project.experiment().data.get();
    QCryptographicHash hash(QCryptographicHash::Sha256);
    for (const auto* values : {&data.grid, &data.intensity, &data.sigma})
        hash.addData(QByteArray(reinterpret_cast<const char*>(values->data()),
                                static_cast<qsizetype>(values->size() * sizeof(double))));
    work_stream << "entry\t" << stage << '\t' << ++work_index << '\t'
                << hash.result().toHex().constData() << std::endl;
}

void scan_contract_work_receipt(const std::string& file) {
    if (trace_stream.is_open()) trace_stream << "work\t" << stage << "\t" << file << std::endl;
    if (work_stream.is_open())
        work_stream << "receipt\t" << stage << '\t' << work_index << '\t' << file << std::endl;
}

void scan_contract_file_completed(const std::string& file) {
    const int count = ++completed;
    if (const char* progress = std::getenv("SCAN_CONTRACT_PROGRESS_LOG"))
        if ((count < 1000 && count % 40 == 0) || count % 1000 == 0) {
            std::ofstream log(progress, std::ios::app);
            log << "native " << stage << " committed " << count << " datasets" << std::endl;
        }
    const auto now = Clock::now();
    const double seconds = std::chrono::duration<double>(now - previous).count();
    previous = now;
    if (count >= 1001 && count <= 2000) early_times.push_back(seconds);
    if (count >= 99001 && count <= 100000) late_times.push_back(seconds);
    if (count == 100000) peak_end = peak_memory();
    // The benchmark observes the normal worker/GUI queue. Functional Stop/Follow
    // actors synchronize below; the scale witness never drains or throttles it.
    if (stage == "scale") {
        if (count == 1000) peak_1000 = peak_memory();
        return;
    }
    if (!active) return;
    QMetaObject::invokeMethod(
        qApp,
        [file, count] {
            if (!active) return;
            // F3 publishes measured data asynchronously. A calculated frame may
            // require the worker's next iteration, so this functional actor waits
            // only for the measured columns its Follow assertions actually judge.
            const bool projection_ready = until(
                [&] {
                    if (active->fit()->scanFitted() < count) return false;
                    if (!exercise_follow) return true;
                    const QString selected = active->experiments()
                                                 ->get(active->currentExperimentIndex(), "file")
                                                 .toString();
                    const QString expected = expected_measurements.value(selected).toString();
                    return !expected.isEmpty() && measured_pattern_hash(*active) == expected;
                },
                5000);
            if (completed <= 162)
                events.append(QJsonObject{{"file", QString::fromStdString(file)},
                                          {"stage", QString::fromStdString(stage)},
                                          {"state", state(*active)},
                                          {"projectionReady", projection_ready},
                                          {"pattern", pattern(*active)}});
            if (exercise_follow && count == 13) active->setCurrentExperimentIndex(17);
            if (exercise_follow && count == 21) active->fit()->setFollowing(true);
            if (stop_after && count == stop_after) active->fit()->cancel();
        },
        QThread::currentThread() == qApp->thread() ? Qt::DirectConnection
                                                   : Qt::BlockingQueuedConnection);
}

int main(int argc, char** argv) {
    QQuickWindow::setGraphicsApi(QSGRendererInterface::Null);
    QGuiApplication application(argc, argv);
    if (argc < 3) return 2;
    const std::string command = argv[1], path = argv[2];
    if (const char* work = std::getenv("SCAN_CONTRACT_WORK")) work_stream.open(work);
    if (const char* trace = std::getenv("EDI_C08_NATIVE_OBSERVER_LOG"))
        trace_stream.open(trace, std::ios::app);
    stage = command;
    QJsonObject answer;
    try {
        if (command == "reference") {
            auto project = crysta::load_project(path);
            crysta::fit_project(project);
            answer["csv"] = QString::fromUtf8(contents(path, "analysis/results.csv"));
        } else if (command == "reference-projection") {
            QFile cells(argv[3]);
            if (!cells.open(QIODevice::ReadOnly))
                throw std::runtime_error("independent projection cells must be readable");
            const QJsonArray rows = QJsonDocument::fromJson(cells.readAll()).array();
            auto seed = crysta::load_project(path);
            QJsonArray projected;
            for (const auto& item : rows) {
                const auto row = item.toObject();
                crysta::Project project(seed);
                QJsonObject expected;
                for (auto it = row.begin(); it != row.end(); ++it) {
                    if (!it.key().endsWith(".uncertainty")) continue;
                    const QString name = it.key().chopped(12);
                    // Independent diffraction-lib CSV grammar strips instrument tag prefixes.
                    QString canonical = name;
                    if (canonical.endsWith(".instrument.twotheta_offset"))
                        canonical.replace(".instrument.twotheta_offset",
                                          ".instrument.calib_twotheta_offset");
                    if (canonical.endsWith(".instrument.wavelength"))
                        canonical.replace(".instrument.wavelength",
                                          ".instrument.setup_wavelength");
                    auto& parameter =
                        crysta::resolve_unique_name(project, canonical.toStdString());
                    // A fitted value is admissible outside an edit range; forward calculation
                    // uses its CSV value, while bounds constrain edits and optimization only.
                    parameter.set_bounds(
                        crysta::ParameterRange(-std::numeric_limits<double>::infinity(),
                                               std::numeric_limits<double>::infinity()));
                    parameter.set_value(row[name].toString().toDouble());
                    parameter.set_uncertainty(
                        it.value().toString().isEmpty()
                            ? std::optional<double>()
                            : std::optional<double>(it.value().toString().toDouble()));
                    expected[canonical] =
                        QJsonArray{parameter.value(), parameter.uncertainty()
                                                          ? QJsonValue(*parameter.uncertainty())
                                                          : QJsonValue()};
                }
                const std::string name =
                    QFileInfo(row["file_path"].toString()).fileName().toStdString();
                project.experiment().data =
                    crysta::read_sequential_scan_data(path + "/experiments/d20_scan/" + name);
                crysta::apply_relations(project);
                crysta::calculate_project(project);
                const auto& data = *project.experiment().data.get();
                const auto& calc = project.experiment().computed().data().intensity_calc.values();
                QJsonArray points;
                for (std::size_t i = 0; i < data.grid.size(); ++i)
                    points.append(
                        QJsonArray{data.grid[i], data.intensity[i], data.sigma[i], calc[i]});
                projected.append(QJsonObject{{"parameters", expected}, {"pattern", points}});
            }
            answer["selected"] = projected;
        } else if (command == "select") {
            auto view = load(path);
            QJsonArray selected;
            for (int index : {0, std::min(513, view->experiments()->count() - 1),
                              view->experiments()->count() - 1, 0}) {
                if (trace_stream.is_open()) trace_stream << "select\t" << index << std::endl;
                view->setCurrentExperimentIndex(index);
                QCoreApplication::processEvents();
                until([&] {
                    return !view->calculating() && !view->currentExperiment()->pattern()->stale();
                });
                selected.append(QJsonObject{{"index", view->currentExperimentIndex()},
                                            {"pattern", pattern(*view)}});
            }
            answer["selected"] = selected;
        } else if (command == "eager") {
            QDirIterator files(QString::fromStdString(path + "/experiments/d20_scan"), {"*.dat"},
                               QDir::Files);
            int read = 0;
            while (files.hasNext()) {
                QFile data(files.next());
                if (!data.open(QIODevice::ReadOnly) || data.readAll().isEmpty())
                    throw std::runtime_error("eager escape must read an actual payload");
                ++read;
            }
            auto view = load(path);
            answer["eagerRead"] = read;
        } else if (command == "inventory")
            answer = inventory(path);
        else if (command == "evolution")
            answer = evolution(path);
        else if (command == "flow") {
            QFile expected(argv[3]);
            if (!expected.open(QIODevice::ReadOnly))
                throw std::runtime_error("Follow requires independent measured-file receipts");
            expected_measurements = QJsonDocument::fromJson(expected.readAll()).object();
            answer = flow(path);
        } else if (command == "joint") {
            auto view = load(path);
            const QString original = view->analysis()->fittingMode();
            view->analysis()->setFittingMode("joint");
            answer["before"] = original;
            answer["after"] = view->analysis()->fittingMode();
            answer["error"] = view->lastError();
        } else if (command == "single")
            answer = single(path, argc > 3 ? std::stoi(argv[3]) : 17);
        else if (command == "virtual")
            answer = qml_views(path, false);
        else if (command == "click")
            answer = qml_views(path, true);
        else if (command == "prepare-scale")
            answer = prepare_scale(path);
        else if (command == "bundle")
            answer = bundle(path, argv[3]);
        else if (command == "readonly")
            answer = bundle(path, argv[3], true);
        else if (command == "run" || command == "scale") {
            auto view = load(path);
            answer = run(*view, command, 0);
            if (completed == 100000) peak_end = peak_memory();
            answer["csv"] = QString::fromUtf8(contents(path, "analysis/results.csv"));
            answer["peak1000"] = static_cast<double>(peak_1000);
            answer["peak100000"] = static_cast<double>(peak_end);
            auto median = [](std::vector<double> values) {
                if (values.empty()) return 0.0;
                std::sort(values.begin(), values.end());
                return values[values.size() / 2];
            };
            answer["medianEarly"] = median(early_times);
            answer["medianLate"] = median(late_times);
            answer["earlySamples"] = static_cast<int>(early_times.size());
            answer["lateSamples"] = static_cast<int>(late_times.size());
        } else
            answer["error"] = "unknown observation command";
    } catch (const std::exception& error) {
        answer["error"] = error.what();
    }
    if (work_stream.is_open()) work_stream.close();
    std::cout << QJsonDocument(answer).toJson(QJsonDocument::Compact).constData() << '\n';
}

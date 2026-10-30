// SPDX-License-Identifier: BSD-3-Clause
#include "demo_driver.hpp"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QFileInfo>
#include <QJSEngine>
#include <QJsonDocument>
#include <QKeyEvent>
#include <QKeySequence>
#include <QMap>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSet>
#include <QUrl>
#include <functional>

#include "app_build_info.hpp"
#include "edi/version.hpp"
#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#include "option_list_model.hpp"
#include "session.hpp"

namespace edi_app {
namespace {
bool write_json(const QString& path, const QJsonObject& value) {
    QSaveFile file(path);
    const auto bytes = QJsonDocument(value).toJson(QJsonDocument::Indented);
    return file.open(QIODevice::WriteOnly) && file.write(bytes) == bytes.size() && file.commit();
}

QString digest(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    QCryptographicHash hash(QCryptographicHash::Sha256);
    return hash.addData(&file) ? QString::fromLatin1(hash.result().toHex()) : QString();
}

QJsonArray rect_json(const QRectF& rect) {
    return {rect.x(), rect.y(), rect.width(), rect.height()};
}

Session* session_for(QQuickWindow& window) {
    auto* engine = qmlEngine(window.contentItem());
    return engine ? engine->singletonInstance<Session*>("edi.app", "Session") : nullptr;
}
}  // namespace

bool DemoDriver::loadDocumentationScript(const QString& path, QString* error) {
    const auto refuse = [error](const QString& why) { if (error) *error = why; return false; };
    if (!output_dir_.entryList({"*.png", "manifest.json"}, QDir::Files).isEmpty())
        return refuse("documentation output contains an earlier capture; choose an empty directory");
    if (!loaded_files_.isValid() || !output_dir_.mkpath("inputs"))
        return refuse("cannot create the documentation workspace");
    QJSEngine engine;
    QFile script(path);
    if (!script.open(QIODevice::ReadOnly)) return refuse("cannot open documentation script " + path);
    const auto bytes = script.readAll();
    const auto declaration = engine.evaluate(QString::fromUtf8(bytes), path);
    if (declaration.isError()) return refuse("documentation script: " + declaration.toString());
    const auto example = declaration.property("example").toString();
    const auto workflow_value = declaration.property("workflow");
    const auto workflow = workflow_value.isUndefined() ? QStringLiteral("creation") : workflow_value.toString();
    if (workflow != "creation" && workflow != "reference")
        return refuse("documentation workflow must be creation or reference");
    const QRegularExpression safe_example("^[a-z0-9][a-z0-9_-]*$");
    if (declaration.property("schema").toInt() != 2 || !safe_example.match(example).hasMatch() ||
        !declaration.property("build").isCallable())
        return refuse("documentation script requires schema 2, an example id and a build(capture) function");
    QFile catalogue(":/edi/examples/metadata.json");
    if (!catalogue.open(QIODevice::ReadOnly)) return refuse("cannot read the bundled example catalogue");
    const auto metadata = QJsonDocument::fromJson(catalogue.readAll()).object().value("examples").toObject().value(example).toObject();
    if (metadata.isEmpty()) return refuse("unknown documentation example: " + example);
    const auto values = metadata.value("values").toObject();
    if (values.value("purpose").toArray().first().toString() != "refinement")
        return refuse("the refinement walkthrough requires an example with measured data");
    const auto base = ":/edi/examples/" + example + "/project";
    const auto structures = QDir(base + "/structures").entryList({"*.edi"}, QDir::Files);
    const auto experiments = QDir(base + "/experiments").entryList({"*.edi"}, QDir::Files);
    if (structures.size() != 1 || experiments.size() != 1)
        return refuse("this walkthrough requires one structure and one experiment; adapt its import steps for a multi-block example");
    documentation_example_ = example;
    documentation_workflow_ = workflow;
    documentation_fixture_ = metadata;
    documentation_fixture_["id"] = example;
    auto context = engine.newObject();
    context.setProperty("projectDirectory", loaded_files_.filePath(example));
    QStringList samples;
    for (const auto& sample : metadata.value("samples").toArray()) samples.append(sample.toString());
    context.setProperty("name", example.left(30));
    context.setProperty("title", samples.join(" + ") + " · " + metadata.value("origin").toString());
    context.setProperty("description", metadata.value("detail").toString());
    context.setProperty("fixture", engine.toScriptValue(metadata.toVariantMap()));
    const QMap<QString, QString> selected{{"structure", "structures/" + structures.first()},
                                        {"experiment", "experiments/" + experiments.first()}};
    std::function<bool(const QString&)> copy_inputs = [&](const QString& relative) {
        const QDir directory(base + "/" + relative);
        for (const auto& entry : directory.entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name)) {
            const auto name = relative.isEmpty() ? entry.fileName() : relative + "/" + entry.fileName();
            if (name == "project.edi") continue;
            if (entry.isDir()) { if (!copy_inputs(name)) return false; continue; }
            const auto filename = "inputs/" + name;
            const auto target = output_dir_.absoluteFilePath(filename);
            if (!output_dir_.mkpath(QFileInfo(filename).path())) return false;
            QFile input(base + "/" + name), output(target);
            if (!input.open(QIODevice::ReadOnly) || !output.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
            const auto content = input.readAll();
            if (output.write(content) != content.size() || !output.flush()) return false;
            output.close();
            const QJsonObject artifact{{"file", filename}, {"sha256", digest(target)}};
            const auto part = selected.key(name);
            if (part.isEmpty()) documentation_dependencies_.append(artifact);
            else {
                documentation_inputs_[part] = artifact;
                context.setProperty(part + "File", target);
                context.setProperty(part + "FileName", QFileInfo(name).fileName());
            }
        }
        return true;
    };
    if (!copy_inputs({})) return refuse("cannot copy the separate example inputs and their data dependencies");
    const auto step_values = declaration.property("build").call({context});
    if (step_values.isError()) return refuse("documentation plan: " + step_values.toString());
    if (!step_values.isArray() || step_values.property("length").toInt() == 0)
        return refuse("build(capture) must return a nonempty steps array");
    const auto entries = QJsonArray::fromVariantList(step_values.toVariant().toList());
    std::vector<Step> loaded;
    QSet<QString> names;
    const QRegularExpression safe_name("^[a-z0-9][a-z0-9_-]*$");
    for (const auto& entry : entries) {
        if (!entry.isObject()) return refuse("a documentation step is not an object");
        const auto object = entry.toObject();
        Step step;
        step.image = object.value("id").toString();
        step.description = object.value("description").toString();
        step.page = object.value("page").toString();
        step.sidebar = object.value("sidebar").toString();
        step.capture = object.value("capture").toBool(true);
        if (!safe_name.match(step.image).hasMatch() || names.contains(step.image) || !object.value("actions").isArray())
            return refuse("documentation step ids must be unique safe filenames, with an actions array");
        names.insert(step.image);
        for (const auto& action : object.value("actions").toArray()) {
            if (!action.isString() || action.toString().isEmpty()) return refuse("invalid documentation action");
            step.actions.append(action.toString());
        }
        for (const auto& target : object.value("highlights").toArray()) {
            if (!target.isString() || target.toString().isEmpty()) return refuse("invalid highlight target");
            step.highlights.append(target.toString());
        }
        loaded.push_back(std::move(step));
    }
    QSaveFile retained(output_dir_.filePath("walkthrough.js"));
    if (!retained.open(QIODevice::WriteOnly) || retained.write(bytes) != bytes.size() || !retained.commit())
        return refuse("cannot retain the walkthrough script");
    steps_ = std::move(loaded);
    documentation_ = true;
    documentation_script_ = QString::fromLatin1(QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
    window_.resize(1480, 800);
    return true;
}

std::optional<bool> DemoDriver::documentationAction(const QString& action) {
    if (action.startsWith("examples.open.") || action.startsWith("open-cli-project:") ||
        action.startsWith("open-project:")) {
        if (documentation_workflow_ == "reference" && action == "open-cli-project:" + documentation_example_)
            return std::nullopt;
        fail("the documentation walkthrough must create its project and import separate inputs");
        return false;
    }
    if (action.startsWith("if-enabled:")) {
        auto* item = find(action.mid(11), false);
        if (!item || !on_screen(item)) { fail("sidebar target is missing or off screen: " + action); return false; }
        documentation_skip_ = !item->isEnabled();
        return true;
    }
    if (action.startsWith("fill:")) {
        const auto body = action.mid(5);
        const auto separator = body.indexOf('=');
        auto* item = separator > 0 ? find(body.left(separator), true) : nullptr;
        if (!item || !item->isEnabled() || !on_screen(item) || !click_item(item)) {
            fail("cannot edit documentation form field: " + body.left(separator));
            return false;
        }
        const auto combination = QKeySequence(QKeySequence::SelectAll)[0];
        QKeyEvent select(QEvent::KeyPress, combination.key(), combination.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &select);
        QKeyEvent release(QEvent::KeyRelease, combination.key(), combination.keyboardModifiers());
        QCoreApplication::sendEvent(&window_, &release);
        const auto text = body.mid(separator + 1);
        for (const auto character : text) {
            QKeyEvent press(QEvent::KeyPress, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &press);
            QKeyEvent up(QEvent::KeyRelease, 0, Qt::NoModifier, QString(character));
            QCoreApplication::sendEvent(&window_, &up);
        }
        if (item->property("text").toString() != text) { fail("form field did not retain the requested value"); return false; }
        return true;
    }
    if (action.startsWith("import-structure:") || action.startsWith("import-experiment:")) {
        const bool structure = action.startsWith("import-structure:");
        const auto file = action.mid(structure ? 17 : 18);
        auto* session = session_for(window_);
        if (!session || !session->project() || !QFileInfo(file).isFile()) {
            fail("cannot import the documentation input: " + file);
            return false;
        }
        auto* project = session->project();
        const auto before = structure ? project->structureModels().size() : project->experimentModels().size();
        const bool imported = structure ? project->loadStructure(QUrl::fromLocalFile(file))
                                       : project->loadExperiments({QUrl::fromLocalFile(file)});
        const auto after = structure ? project->structureModels().size() : project->experimentModels().size();
        if (!imported || after != before + 1) { fail("documentation input import did not add one block"); return false; }
        return true;
    }
    if (action == "close-fit-results") {
        auto* session = session_for(window_);
        auto* dialog = window_.findChild<QObject*>("fit.results");
        if (!session || !session->project() || session->project()->fit()->running() ||
            session->project()->fit()->results()->rowCount() == 0 || !dialog ||
            !dialog->property("visible").toBool() || !QMetaObject::invokeMethod(dialog, "accept")) {
            fail("the completed fit results dialog could not be closed");
            return false;
        }
        return true;
    }
    return std::nullopt;
}

bool DemoDriver::saveDocumentationFrame(const QString& path, QString* error) {
    const auto& step = steps_[current_];
    const auto refuse = [error](const QString& why) { if (error) *error = why; return false; };
    auto* tab = find("appBar.tab." + step.page, false);
    if (!tab || !tab->property("checked").toBool()) return refuse("capture is on the wrong workflow page");
    auto* session = session_for(window_);
    auto* project = session ? session->project() : nullptr;
    auto* fit = project ? project->fit() : nullptr;
    auto* fit_dialog = window_.findChild<QObject*>("fit.results");
    const bool results_open = fit_dialog && fit_dialog->property("visible").toBool();
    if ((step.page == "analysis" || step.page == "report") &&
        (!fit || fit->running() || fit->results()->rowCount() == 0 || results_open))
        return refuse("Analysis and Report captures require a completed fit and a closed results popup");
    const auto collect = [this] {
        QJsonObject items;
        std::function<void(QQuickItem*)> visit = [&](QQuickItem* item) {
            if (!item->isVisible() || item->opacity() <= 0) return;
            const QRectF bounds = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
            QRectF visible = bounds.intersected(QRectF(0, 0, window_.width(), window_.height()));
            for (auto* parent = item->parentItem(); parent && !visible.isEmpty(); parent = parent->parentItem()) {
                if (parent->opacity() <= 0) { visible = {}; break; }
                if (parent->clip()) visible = visible.intersected(parent->mapRectToScene(parent->clipRect()));
            }
            const auto name = item->objectName();
            if (!name.isEmpty() && !visible.isEmpty()) {
                if (items.contains(name)) {
                    items[name] = QJsonObject{{"ambiguous", true}};
                } else {
                    auto label = item->property("text").toString();
                    if (label.isEmpty()) label = item->property("title").toString();
                    QJsonObject record{{"bounds", rect_json(bounds)}, {"visible_bounds", rect_json(visible)},
                        {"enabled", item->isEnabled()}, {"label", label.left(256)}};
                    auto icon = item->property("fontIcon").toString();
                    if (icon.isEmpty()) icon = item->property("keyIcon").toString();
                    const auto group_icon = item->property("icon");
                    if (icon.isEmpty() && group_icon.metaType().id() == QMetaType::QString) icon = group_icon.toString();
                    if (!icon.isEmpty()) record["icon"] = icon;
                    if (auto* options = item->property("options").value<OptionListModel*>()) {
                        QJsonArray choices;
                        for (int row = 0; row < options->rowCount(); ++row) {
                            const auto index = options->index(row, 0);
                            choices.append(QJsonObject{{"token", options->data(index, OptionListModel::TokenRole).toString()},
                                {"label", options->data(index, OptionListModel::LabelRole).toString()}});
                        }
                        record["options"] = choices;
                        record["selected"] = item->property("token").toString();
                        record["uid"] = item->property("uid").toString();
                    }
                    items[name] = record;
                }
            }
            for (auto* child : item->childItems()) visit(child);
        };
        visit(window_.contentItem());
        return items;
    };
    const auto items = collect();
    const auto frame = window_.grabWindow();
    if (items != collect() || frame != previous_frame_)
        return refuse("the scene changed between its settled image and layout capture");
    for (const auto& target : step.highlights) {
        if (!items.contains(target) || items.value(target).toObject().value("ambiguous").toBool())
            return refuse("required annotation target is missing or ambiguous: " + target);
    }
    QJsonArray tabs;
    for (const auto& name : {"basic", "extras", "text", "settings"}) {
        auto* item = find(QString("sideBar.tab.") + name, false);
        if (item && on_screen(item))
            tabs.append(QJsonObject{{"id", QString("sideBar.tab.") + name}, {"label", item->property("text").toString()},
                                    {"enabled", item->isEnabled()}, {"checked", item->property("checked").toBool()}});
    }
    if (!step.sidebar.isEmpty()) {
        QStringList selected;
        for (const auto& entry : tabs)
            if (entry.toObject().value("checked").toBool()) selected.append(entry.toObject().value("label").toString());
        if (selected != QStringList{step.sidebar}) return refuse("capture has the wrong sidebar selection");
    }
    QJsonObject state{{"page", step.page}, {"sidebar", step.sidebar}, {"sidebar_tabs", tabs},
        {"has_project", project != nullptr}, {"structures", project ? project->structureModels().size() : 0},
        {"experiments", project ? project->experimentModels().size() : 0},
        {"fit_running", fit && fit->running()}, {"fit_results_open", results_open},
        {"fit_result_rows", fit ? fit->results()->rowCount() : 0},
        {"fit_status", fit ? fit->status() : QString()}, {"fit_outcome", fit ? fit->outcome() : QString()},
        {"scan_total", fit ? fit->scanTotal() : 0}, {"scan_fitted", fit ? fit->scanFitted() : 0},
        {"scan_failed", fit ? fit->scanFailed() : 0}};
    const auto filename = QFileInfo(path).fileName();
    QJsonObject metadata{{"schema", 1}, {"id", step.image}, {"description", step.description},
        {"image", filename}, {"image_sha256", digest(path)},
        {"logical_size", QJsonArray{window_.width(), window_.height()}},
        {"pixel_size", QJsonArray{frame.width(), frame.height()}},
        {"source_revision", QString::fromLatin1(edi::build_commit())}, {"qt_version", qVersion()},
        {"gui_components_revision", EDI_APP_GUI_COMMIT}, {"script_sha256", documentation_script_},
        {"state", state}, {"items", items}, {"highlights", QJsonArray::fromStringList(step.highlights)}};
    const auto sidecar = step.image + ".json";
    if (!write_json(output_dir_.filePath(sidecar), metadata)) return refuse("cannot save capture metadata");
    documentation_scenes_.append(QJsonObject{{"id", step.image}, {"status", "captured"}, {"image", filename},
        {"metadata", sidecar}, {"description", step.description}, {"page", step.page}, {"sidebar", step.sidebar}});
    return saveDocumentationManifest("running") || refuse("cannot save the capture manifest");
}

bool DemoDriver::saveDocumentationManifest(const QString& status, const QString& error) {
    return write_json(output_dir_.filePath("manifest.json"),
        QJsonObject{{"schema", 1}, {"status", status}, {"error", error}, {"example", documentation_example_}, {"workflow", documentation_workflow_}, {"fixture", documentation_fixture_}, {"dependencies", documentation_dependencies_},
            {"source_revision", QString::fromLatin1(edi::build_commit())},
            {"binary_sha256", digest(QCoreApplication::applicationFilePath())},
            {"gui_components_revision", EDI_APP_GUI_COMMIT}, {"script_sha256", documentation_script_},
            {"logical_size", QJsonArray{window_.width(), window_.height()}},
            {"inputs", documentation_inputs_}, {"actions", documentation_actions_}, {"scenes", documentation_scenes_}});
}
}  // namespace edi_app

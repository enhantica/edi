// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_view_model.hpp"

#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaObject>
#include <QSaveFile>
#include <QStandardPaths>
#include <QDir>
#include <QUuid>
#include <optional>
#include <stdexcept>

#include "fit_view_model.hpp"
#include "project_view_model.hpp"
#ifndef __EMSCRIPTEN__
#include "chatgpt_connection.hpp"
#include "connection_services.hpp"
#endif

namespace edi_app {
namespace {
using Object = QJsonObject;
std::string json(const Object& object) { return QJsonDocument(object).toJson(QJsonDocument::Compact).toStdString(); }
Object object(const std::string& text) { return QJsonDocument::fromJson(QByteArray::fromStdString(text)).object(); }
class Rows : public RowTableModel {
   public:
    Rows(const QStringList& names, QObject* parent) : RowTableModel(names, parent), names_(names) {}
    void assign(const QJsonArray& data) {
        QList<Row> rows;
        for (qsizetype i = 0; i < data.size(); ++i) {
            QList<QVariant> values;
            const auto entry = data[i].toObject();
            for (const auto& name : names_) values.append(entry.value(name).toVariant());
            rows.append({reinterpret_cast<const void*>(static_cast<std::uintptr_t>(i + 1)), values});
        }
        setTableRows(rows);
    }
   private:
    QStringList names_;
};
}

struct AssistantViewModel::State {
    AssistantViewModel& owner;
    ProjectViewModel* project = nullptr;
    std::unique_ptr<edi::work::Worker> idle_worker;
    std::unique_ptr<edi::assistant::Controller> controller;
#ifndef __EMSCRIPTEN__
    std::unique_ptr<edi::assistant::native::ChatGptConnection> connection;
#endif
    Rows messages{{"id", "kind", "text", "status", "payload"}, &owner};
    Rows models{{"id", "displayName", "efforts", "available"}, &owner};
    QJsonArray history;
    Object core, native, plan, question;
    QString model, effort, error;
    bool own_edit = false;
    std::uint64_t generation = 0;
    QTimer timer{&owner};
    QString history_path;
    QByteArray consented_context;
    bool archive_refused = false;
    using Limits = edi::assistant::Limits;
    QVariantMap observed;
    void notify() {
        auto property = [this](const QString& name, const auto& value, auto signal) {
            const QVariant next = QVariant::fromValue(value);
            if (!observed.contains(name) || observed.value(name) != next) { observed[name] = next; (owner.*signal)(); }
        };
        property("state", owner.state(), &AssistantViewModel::stateChanged);
        property("connected", owner.connected(), &AssistantViewModel::connectedChanged);
        property("connectionLabel", owner.connectionLabel(), &AssistantViewModel::connectionLabelChanged);
        property("selectedModel", owner.selectedModel(), &AssistantViewModel::selectedModelChanged);
        property("selectedEffort", owner.selectedEffort(), &AssistantViewModel::selectedEffortChanged);
        property("availableEfforts", owner.availableEfforts(), &AssistantViewModel::availableEffortsChanged);
        property("pendingPlan", owner.pendingPlan(), &AssistantViewModel::pendingPlanChanged);
        property("pendingQuestion", owner.pendingQuestion(), &AssistantViewModel::pendingQuestionChanged);
        property("activeJobId", owner.activeJobId(), &AssistantViewModel::activeJobIdChanged);
        property("canCancel", owner.canCancel(), &AssistantViewModel::canCancelChanged);
        property("lastError", owner.lastError(), &AssistantViewModel::lastErrorChanged);
        property("contextPreview", owner.contextPreview(), &AssistantViewModel::contextPreviewChanged);
        property("contextConsentRequired", owner.contextConsentRequired(), &AssistantViewModel::contextPreviewChanged);
    }
    explicit State(AssistantViewModel& vm) : owner(vm) { initialize(); }
#ifndef __EMSCRIPTEN__
    State(AssistantViewModel& vm, edi::assistant::native::NativeDependencies dependencies) : owner(vm) {
        edi::assistant::native::validate_dependencies(dependencies);
        initialize(std::move(dependencies));
    }
    void initialize(std::optional<edi::assistant::native::NativeDependencies> dependencies = {}) {
#else
    void initialize() {
#endif
        idle_worker = std::make_unique<edi::work::Worker>([this](edi::work::Delivery delivery) {
            QMetaObject::invokeMethod(&owner, std::move(delivery), Qt::QueuedConnection);
        });
        history_path = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation) + "/assistant/history.json";
        QFile saved(history_path);
        if (QFileInfo::exists(history_path)) {
            QJsonParseError parsing;
            if (!saved.open(QIODevice::ReadOnly) || saved.size() > static_cast<qint64>(Limits::ui_history_bytes)) archive_refused = true;
            else {
                const auto bytes = saved.read(static_cast<qint64>(Limits::ui_history_bytes) + 1);
                const auto document = QJsonDocument::fromJson(bytes, &parsing);
                archive_refused = bytes.size() > static_cast<qint64>(Limits::ui_history_bytes) || parsing.error != QJsonParseError::NoError || !document.isArray() || document.array().size() > static_cast<qsizetype>(Limits::ui_messages);
                if (!archive_refused) {
                    for (const auto& row : document.array()) if (!row.isObject() || !row.toObject().value("text").isString() || !row.toObject().value("kind").isString()) archive_refused = true;
                    if (!archive_refused) history = document.array();
                }
            }
            if (archive_refused) error = QObject::tr("Saved assistant history could not be loaded within its limits. The file is preserved; clear history explicitly to start again.");
        }
        messages.assign(history);
#ifndef __EMSCRIPTEN__
        const auto sink = [this](const std::string& text) {
            const auto incoming_generation = generation;
            QMetaObject::invokeMethod(&owner, [this, text, incoming_generation] {
                if (!controller || incoming_generation != generation) return;
                native = object(connection->state());
                const auto reply = controller->provider_event(text);
                if (!reply.ok) error = object(reply.value).value("message").toString();
                sync();
            }, Qt::QueuedConnection);
        };
        if (dependencies) connection = std::make_unique<edi::assistant::native::ChatGptConnection>(sink, std::move(*dependencies));
        else connection = std::make_unique<edi::assistant::native::ChatGptConnection>(sink);
#endif
        timer.setInterval(200);
        QObject::connect(&timer, &QTimer::timeout, &owner, [this] {
            if (controller) controller->poll();
            sync();
        });
        timer.start();
    }
    std::uint64_t archive_size(const QJsonArray& rows) const {
        return static_cast<std::uint64_t>(QJsonDocument(rows).toJson(QJsonDocument::Compact).size());
    }
    bool admit(const QJsonArray& next) {
        if (archive_refused || next.size() > static_cast<qsizetype>(Limits::ui_messages) || archive_size(next) > Limits::ui_history_bytes) {
            error = QObject::tr("Assistant history capacity is unavailable. Existing history and project state are preserved.");
            return false;
        }
        return true;
    }
    bool append(const QString& kind, const QString& text, const Object& payload = {}, const QString& row_status = "completed") {
        auto next = history;
        next.append(Object{{"id", QUuid::createUuid().toString(QUuid::WithoutBraces)}, {"kind", kind},
                           {"text", text}, {"status", row_status}, {"payload", payload}});
        if (!admit(next)) return false;
        history = std::move(next); messages.assign(history); persist(); return true;
    }
    void persist() {
        if (archive_refused) return;
        const auto bytes = QJsonDocument(history).toJson(QJsonDocument::Compact);
        QDir().mkpath(QFileInfo(history_path).absolutePath());
        QSaveFile file(history_path);
        if (!file.open(QIODevice::WriteOnly) || !file.setPermissions(QFile::ReadOwner | QFile::WriteOwner) ||
            file.write(bytes) != bytes.size() || !file.commit()) error = QObject::tr("Assistant history could not be saved; the current conversation remains visible.");
    }
    void event(const std::string& input) {
        const Object value = object(input); const auto type = value.value("type").toString();
        if (type == "message_delta") {
            if (!history.isEmpty() && history.last().toObject().value("kind") == "assistant" && history.last().toObject().value("payload").toObject().value("turn_id") == value.value("turn_id") && history.last().toObject().value("payload").toObject().value("request_id") == value.value("request_id")) {
                auto last = history.last().toObject(); last["text"] = last.value("text").toString() + value.value("text").toString();
                auto next = history; next.replace(next.size() - 1, last); if (admit(next)) { history = std::move(next); messages.assign(history); persist(); } else if (controller) controller->cancel();
            } else if (!append("assistant", value.value("text").toString(), value) && controller) controller->cancel();
        } else if (type == "plan_proposed") { plan = value.value("plan").toObject(); append("plan", plan.value("summary").toString(), plan); }
        else if (type == "plan_approved") plan = {};
        else if (type == "question") { question = value.value("question").toObject(); append("question", question.value("text").toString(), question); }
        else if (type == "question_answered" || type == "question_invalidated") question = {};
        else if (type == "tool_result") {
            const bool pending = value.value("pending").toBool();
            append("tool", pending ? QObject::tr("Project tool running") : (value.value("ok").toBool() ? QObject::tr("Project tool completed") : QObject::tr("Project tool refused")), value, pending ? "running" : (value.value("ok").toBool() ? "completed" : "refused"));
        } else if (type == "job_started") append("tool", QObject::tr("Refinement trial running"), value);
        else if (type == "trial_finished") append("trial", value.value("result").toObject().value("reason").toString(), value);
        else if (type == "error") error = value.value("message").toString();
        sync();
    }
    void sync() {
        const Object next_core = controller ? object(controller->state()) : Object{};
#ifndef __EMSCRIPTEN__
        const Object next_native = object(connection->state());
#else
        const Object next_native{{"status", "disconnected"}};
#endif
        core = next_core; native = next_native;
        QJsonArray choices;
        for (const auto& value : native.value("models").toArray()) {
            const auto item = value.toObject(); choices.append(Object{{"id", item.value("id")},
                {"displayName", item.value("display_name")}, {"efforts", item.value("efforts")}, {"available", item.value("available").toBool()}});
        }
        models.assign(choices);
        bool selected_available = false;
        for (const auto& choice : choices) if (choice.toObject().value("id") == model && choice.toObject().value("available").toBool()) selected_available = true;
        if (!selected_available) {
            model.clear(); effort.clear();
            for (const auto& choice : choices) if (choice.toObject().value("available").toBool()) { model = choice.toObject().value("id").toString(); break; }
        }
        const auto efforts = owner.availableEfforts();
        if (!efforts.contains(effort)) effort = efforts.contains("medium") ? QString("medium") : (efforts.isEmpty() ? QString() : efforts.first());
        if (core.value("pending_plan_id").toString().isEmpty()) plan = {};
        if (core.value("pending_question_id").toString().isEmpty()) question = {};
        if (!native.value("last_error").toString().isEmpty()) error = native.value("last_error").toString();
        notify();
    }
    void command(Object command) {
        if (!controller) return;
        command["schema"] = "edi.assistant/1";
        const auto reply = controller->user_command(json(command));
        if (!reply.ok) error = object(reply.value).value("message").toString();
        else error.clear();
        sync(); notify();
    }
    void bind(ProjectViewModel* next) {
#ifndef __EMSCRIPTEN__
        if (controller && connection) connection->cancel(core.value("active_turn_id").toString().toStdString());
#endif
        ++generation;
        consented_context.clear();
        if (project) {
            QObject::disconnect(project, nullptr, &owner, nullptr);
            QObject::disconnect(project->fit(), nullptr, &owner, nullptr);
        }
        controller.reset(); project = next; plan = {}; question = {};
        edi::assistant::Hooks hooks;
        hooks.event = [this](const std::string& text) { event(text); };
        hooks.apply = [this](const edi::Edit& edit, bool structural) {
            if (!project) return std::string("The project was closed");
            own_edit = true; const auto error_text = project->apply(edit, structural); own_edit = false;
            return error_text.toStdString();
        };
        hooks.provider_request = [this](const std::string& text) {
            const auto scope = generation;
            QMetaObject::invokeMethod(&owner, [this, text, scope] {
                if (scope != generation) return;
#ifndef __EMSCRIPTEN__
                const auto requested_context = QJsonDocument(object(text).value("context").toObject()).toJson(QJsonDocument::Compact);
                if (requested_context != consented_context) {
                    error = QObject::tr("Project context changed. Inspect and approve the current outgoing context before continuing.");
                    controller->cancel(); sync(); return;
                }
                const auto reply = connection->send(text);
                if (!reply.ok) {
                    error = object(reply.value).value("message").toString();
                    controller->cancel(); notify();
                }
#else
                (void)text; error = QObject::tr("Browser subscription access needs the local companion."); controller->cancel(); notify();
#endif
            }, Qt::QueuedConnection);
        };
        controller = std::make_unique<edi::assistant::Controller>(project ? project->assistantWorker() : *idle_worker, std::move(hooks));
        if (project) {
            controller->attach(project->assistantProject(), QUuid::createUuid().toString(QUuid::WithoutBraces).toStdString());
            QObject::connect(project, &ProjectViewModel::projectEdited, &owner, [this] {
                if (controller && !own_edit) { controller->notify_changed(); plan = {}; question = {}; sync(); }
            });
            QObject::connect(project->fit(), &FitViewModel::finished, &owner, [this] { if (controller) controller->notify_changed(); });
        }
#ifndef __EMSCRIPTEN__
        const auto state = object(connection->state());
        QJsonArray capabilities;
        for (const auto& row : state.value("models").toArray()) {
            auto item = row.toObject(); if (item.take("available").toBool()) capabilities.append(item);
        }
        if (state.value("status") == "ready") controller->provider_event(json(Object{{"schema", "edi.assistant/1"},
            {"type", "connection"}, {"connection_id", state.value("connection_id")}, {"status", "ready"}, {"capabilities", capabilities}}));
#endif
        sync(); notify();
    }
};

AssistantViewModel::AssistantViewModel(QObject* parent) : QObject(parent), state_(std::make_unique<State>(*this)) { state_->bind(nullptr); }
#ifndef __EMSCRIPTEN__
AssistantViewModel::AssistantViewModel(edi::assistant::native::NativeDependencies dependencies, QObject* parent)
    : QObject(parent), state_(std::make_unique<State>(*this, std::move(dependencies))) { state_->bind(nullptr); }
#endif
AssistantViewModel::~AssistantViewModel() = default;
QString AssistantViewModel::state() const { return state_->core.value("state").toString(); }
bool AssistantViewModel::connected() const { return state_->native.value("status") == "ready"; }
QString AssistantViewModel::connectionLabel() const { return connected() ? state_->native.value("label").toString() : tr("Connect ChatGPT"); }
RowTableModel* AssistantViewModel::models() const { return &state_->models; }
QString AssistantViewModel::selectedModel() const { return state_->model; }
QString AssistantViewModel::selectedEffort() const { return state_->effort; }
QStringList AssistantViewModel::availableEfforts() const {
    for (const auto& item : state_->native.value("models").toArray()) {
        const auto model = item.toObject();
        if (model.value("id").toString() == state_->model) return model.value("efforts").toVariant().toStringList();
    }
    return {};
}
RowTableModel* AssistantViewModel::messages() const { return &state_->messages; }
QVariantMap AssistantViewModel::pendingPlan() const { return state_->plan.toVariantMap(); }
QVariantMap AssistantViewModel::pendingQuestion() const { return state_->question.toVariantMap(); }
QString AssistantViewModel::activeJobId() const { return state_->core.value("active_job_id").toString(); }
bool AssistantViewModel::canCancel() const { return state_->core.value("can_cancel").toBool(); }
QString AssistantViewModel::lastError() const { return state_->error; }
QString AssistantViewModel::contextPreview() const { return state_->controller ? QString::fromStdString(state_->controller->context()) : QString(); }
bool AssistantViewModel::contextConsentRequired() const {
    return !state_->controller || QJsonDocument(object(state_->controller->context())).toJson(QJsonDocument::Compact) != state_->consented_context;
}
void AssistantViewModel::setSelectedModel(const QString& model) {
    for (const auto& row : state_->native.value("models").toArray()) if (row.toObject().value("id") == model && row.toObject().value("available").toBool()) {
        if (state_->model != model) { state_->model = model; state_->effort.clear(); state_->sync(); } return;
    }
    state_->error = tr("This model is unavailable."); state_->notify();
}
void AssistantViewModel::setSelectedEffort(const QString& effort) {
    if (!availableEfforts().contains(effort)) { state_->error = tr("This reasoning effort is unavailable."); state_->notify(); return; }
    if (state_->effort != effort) { state_->effort = effort; state_->notify(); }
}
void AssistantViewModel::setProject(ProjectViewModel* project) { state_->bind(project); }
void AssistantViewModel::send(const QString& text) {
    if (text.trimmed().isEmpty()) return;
    if (contextConsentRequired()) { state_->error = tr("Inspect and approve the outgoing project context before sending."); state_->notify(); return; }
    auto prospective = state_->history;
    prospective.append(Object{{"id", QUuid::createUuid().toString(QUuid::WithoutBraces)}, {"kind", "user"}, {"text", text}, {"status", "completed"}, {"payload", Object{}}});
    if (!state_->admit(prospective)) { state_->notify(); return; }
    Object command{{"type", "message"}, {"text", text}, {"connection_id", state_->native.value("connection_id")}, {"model", state_->model}};
    if (!state_->effort.isEmpty()) command["effort"] = state_->effort;
    state_->command(command);
    if (state_->error.isEmpty()) state_->append("user", text);
}
void AssistantViewModel::approvePlan(const QString& id) {
    const auto revision = state_->controller->revision();
    state_->command({{"type", "approve_plan"}, {"plan_id", id}, {"project_id", QString::fromStdString(revision.project_id)},
                     {"revision", QString::number(revision.revision)}});
}
void AssistantViewModel::answerQuestion(const QString& id, const QString& answer) { state_->command({{"type", "answer"}, {"question_id", id}, {"answer", answer}}); }
void AssistantViewModel::cancel() {
#ifndef __EMSCRIPTEN__
    state_->connection->cancel(state_->core.value("active_turn_id").toString().toStdString());
#endif
    state_->controller->cancel(); state_->sync(); state_->notify();
}
void AssistantViewModel::signIn() {
    if (!state_->controller) return;
    const auto context = object(state_->controller->context());
    if (context.contains("error")) { state_->error = tr("Project context exceeds the assistant limit; nothing was sent."); state_->notify(); return; }
    state_->consented_context = QJsonDocument(context).toJson(QJsonDocument::Compact);
    if (connected()) { state_->error.clear(); state_->notify(); return; }
#ifndef __EMSCRIPTEN__
    const auto reply = state_->connection->sign_in();
    state_->error = reply.ok ? QString() : object(reply.value).value("message").toString();
#else
    state_->error = tr("Browser subscription access needs the local companion, which is not available in this desktop slice.");
#endif
    state_->notify();
}
void AssistantViewModel::signOut() {
#ifndef __EMSCRIPTEN__
    state_->connection->sign_out();
#endif
    state_->controller->cancel(); state_->sync(); state_->notify();
}
void AssistantViewModel::clearHistory() {
    if (canCancel()) return;
    state_->bind(state_->project);
    state_->archive_refused = false; state_->history = {}; state_->error.clear(); state_->messages.assign({}); state_->persist(); state_->notify();
}
}  // namespace edi_app

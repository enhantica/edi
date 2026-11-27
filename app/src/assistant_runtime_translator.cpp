// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_runtime_translator.hpp"
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QSaveFile>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>
#include "assistant_native_tools.hpp"
#include "assistant_providers.hpp"
#include "assistant_thread_settings.hpp"
#include "assistant_tool_server.hpp"
#include "edi/assistant_limits.hpp"

namespace edi_app {
namespace {
using Limits = edi::assistant::Limits;
// JSON-RPC error codes the view model reads: -32601 marks an unsupported method (usage shows "Unsupported"),
// -32600 a request that was not admitted.
constexpr int kUnsupported = -32601;
constexpr int kInvalidRequest = -32600;
constexpr int kRefused = -32000;

QString string_field(const QJsonObject& object, const char* key) {
    const auto value = object.value(QLatin1StringView(key));
    return value.isString() ? value.toString() : QString();
}

// The text parts of a turn's `input`, in order. The view model sends the message and its context as text parts.
QString joined_text(const QJsonArray& input) {
    QStringList parts;
    for (const auto& value : input) {
        const auto part = value.toObject();
        if (part.value(QLatin1StringView("type")) == QLatin1StringView("text") && part.value(QLatin1StringView("text")).isString())
            parts.append(part.value(QLatin1StringView("text")).toString());
    }
    return parts.join(QStringLiteral("\n\n"));
}

// Seconds since the epoch from a number (seconds or milliseconds) or an ISO 8601 string; -1 when unknown.
qint64 epoch_seconds(const QJsonValue& value) {
    if (value.isDouble() && std::isfinite(value.toDouble()) && value.toDouble() >= 0) {
        const auto number = value.toDouble();
        return static_cast<qint64>(number > 1e11 ? number / 1000 : number);
    }
    if (value.isString()) {
        const auto time = QDateTime::fromString(value.toString(), Qt::ISODateWithMs);
        if (time.isValid()) return time.toSecsSinceEpoch();
    }
    return -1;
}

QString guard_executable() {
#ifdef Q_OS_WIN
    const auto name = QStringLiteral("edi_assistant_guard.exe");
#else
    const auto name = QStringLiteral("edi_assistant_guard");
#endif
    return QDir(QCoreApplication::applicationDirPath()).filePath(name);
}

// The names edi's tool server lists, for the session's tool readback.
QStringList mcp_tool_names(const QJsonArray& tools) {
    QStringList names;
    for (const auto& tool : tools) names.append(tool.toObject().value(QLatin1StringView("name")).toString());
    return names;
}
}  // namespace

AssistantRuntimeTranslator::AssistantRuntimeTranslator(AssistantProviderId provider,
                                                       std::unique_ptr<AssistantRuntimeSession> session,
                                                       AssistantRuntimeLaunch launch, QObject* parent,
                                                       std::shared_ptr<const void> releaseOwner)
    : AssistantProvider(parent), provider_(provider), session_(std::move(session)), template_(std::move(launch)),
      launch_(template_), release_owner_(std::move(releaseOwner)) {
    if (!session_) throw std::invalid_argument("A runtime provider needs a session");
    clock_.start();
    timer_.setInterval(100);
    connect(&timer_, &QTimer::timeout, this, [this] { checkDeadline(); });
    timer_.start();
    hold_.setSingleShot(true);
    hold_.setInterval(static_cast<int>(Limits::http_json_ms));
    connect(&hold_, &QTimer::timeout, this, [this] {
        if (held_) finishTurn(QStringLiteral("completed"), {});
    });
    auto* runtime = session_.get();
    connect(runtime, &AssistantRuntimeSession::ready, this, &AssistantRuntimeTranslator::onReady);
    connect(runtime, &AssistantRuntimeSession::accountRefused, this, &AssistantRuntimeTranslator::onAccountRefused);
    connect(runtime, &AssistantRuntimeSession::signInOpened, this, &AssistantRuntimeTranslator::onSignInOpened);
    connect(runtime, &AssistantRuntimeSession::signInFinished, this, &AssistantRuntimeTranslator::onSignInFinished);
    connect(runtime, &AssistantRuntimeSession::signedOut, this, &AssistantRuntimeTranslator::onSignedOut);
    connect(runtime, &AssistantRuntimeSession::removedOnly, this, &AssistantRuntimeTranslator::onSignedOut);
    connect(runtime, &AssistantRuntimeSession::modelsListed, this, &AssistantRuntimeTranslator::onModelsListed);
    connect(runtime, &AssistantRuntimeSession::threadOpened, this, &AssistantRuntimeTranslator::onThreadOpened);
    connect(runtime, &AssistantRuntimeSession::turnStarted, this, &AssistantRuntimeTranslator::onTurnStarted);
    connect(runtime, &AssistantRuntimeSession::textDelta, this, &AssistantRuntimeTranslator::onTextDelta);
    connect(runtime, &AssistantRuntimeSession::itemCompleted, this, &AssistantRuntimeTranslator::onItemCompleted);
    connect(runtime, &AssistantRuntimeSession::foreignTool, this, &AssistantRuntimeTranslator::onForeignTool);
    connect(runtime, &AssistantRuntimeSession::turnFinished, this, &AssistantRuntimeTranslator::onTurnFinished);
    connect(runtime, &AssistantRuntimeSession::usageChanged, this, &AssistantRuntimeTranslator::onUsageChanged);
    connect(runtime, &AssistantRuntimeSession::failed, this, [this](const QString& explanation, FailureKind kind) {
        fail(explanation, kind);
    });
}

AssistantRuntimeTranslator::~AssistantRuntimeTranslator() {
    session_->disconnect(this);
    retire();
}

QJsonObject AssistantRuntimeTranslator::threadPolicy() const {
    // Only what is true of these runtimes: every permission request is declined, and the model comes from the
    // provider's own service. No command or file tool is offered, so there is no sandbox to report; `sandbox` and
    // `approvalsReviewer` are absent from both this policy and the readback.
    return {{"approvalPolicy", "never"},
            {"modelProvider", provider_ == AssistantProviderId::Claude ? QStringLiteral("anthropic") : QStringLiteral("github")}};
}

AssistantProvider::OutputOwnerState AssistantRuntimeTranslator::outputOwnerState() const noexcept {
    if (!release_owner_) return OutputOwnerState::Unobserved;
    if (live_ && !failed_) return OutputOwnerState::Live;
    if (live_ || releasing_) return OutputOwnerState::Releasing;
    return OutputOwnerState::Released;
}

// ---- Lifecycle and delivery ----

bool AssistantRuntimeTranslator::start(const QString& executable, const QString& workspace) {
    if (live_ || releasing_ || executable.isEmpty() || !QFileInfo(workspace).isAbsolute() || !QFileInfo(workspace).isDir() ||
        generation_ == std::numeric_limits<quint64>::max())
        return false;
    ++generation_;
    failed_ = false;
    failure_kind_ = FailureKind::Other;
    settleOperation();
    posts_.clear();
    clearState();
    launch_ = template_;
    launch_.executable = executable;
    launch_.workspace = workspace;
    launch_.skillsDir = QDir(workspace).filePath(QStringLiteral(".agents/skills"));
    if (launch_.guard.isEmpty()) launch_.guard = guard_executable();
    if (launch_.skills.isEmpty()) {
        // The view model stages the approved skills before it starts the runtime; discovery must report each.
        const QDir staged(launch_.skillsDir);
        for (const auto& id : staged.entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name))
            if (QFileInfo(staged.filePath(id + QStringLiteral("/SKILL.md"))).isFile()) launch_.skills.append(id);
    }
    try {
        auto* server = new AssistantToolServer(this);
        tools_ = server;
        connect(server, &AssistantToolServer::toolCall, this, &AssistantRuntimeTranslator::onToolCall);
        connect(server, &AssistantToolServer::cancelled, this, &AssistantRuntimeTranslator::onToolCancelled);
        connect(server, &AssistantToolServer::disconnected, this, &AssistantRuntimeTranslator::onToolsDisconnected);
        connect(server, &AssistantToolServer::toolsListed, this, &AssistantRuntimeTranslator::onToolsListed);
        // The bridge's key lives in an owner-only file in edi's prepared workspace (ADR-0108 §3).
        const auto keyFolder = QDir(workspace).filePath(QStringLiteral(".edi"));
        if (!QDir().mkpath(keyFolder) || !server->listen(keyFolder)) throw std::runtime_error("The tool server could not listen");
        // The same catalogue the view model sends with thread/start, so the start's tool readback can pass.
        const auto catalogue = assistant_native_mcp_tools(assistant_native_tool_specs());
        server->setTools(catalogue);
        launch_.expectedTools = mcp_tool_names(catalogue);
        launch_.toolServer = server->mcpServerEntry(launch_.guard);
    } catch (...) {
        if (tools_) tools_->deleteLater();
        tools_ = nullptr;
        failed_ = true;
        return false;
    }
    lease_ = release_owner_;
    live_ = true;
    bindTools();
    beginOperation(Limits::http_json_ms, 0);
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    bool started = false;
    try {
        started = session_->start(launch_);
    } catch (...) {
        started = false;
    }
    if (!self || generation_ != scope) return false;
    if (!started || failed_) {
        failed_ = true;
        stopRuntime();
        return false;
    }
    post([this] { emit this->started(); });
    return true;
}

void AssistantRuntimeTranslator::retire() {
    if (generation_ != std::numeric_limits<quint64>::max()) ++generation_;
    failed_ = true;
    settleOperation();
    posts_.clear();
    clearState();
    stopRuntime();
}

void AssistantRuntimeTranslator::clearState() {
    waiting_.clear();
    ack_deadlines_.clear();
    requests_.clear();
    login_rpc_.clear();
    login_id_.clear();
    logout_rpc_.clear();
    account_ = Account::Unknown;
    identity_ = {};
    skills_.clear();
    models_ = {};
    models_known_ = false;
    usage_ = {};
    thread_.clear();
    thread_rpc_.clear();
    thread_method_.clear();
    thread_target_.clear();
    opened_thread_.clear();
    tools_listed_ = false;
    model_.clear();
    effort_.clear();
    turn_.clear();
    session_turn_.clear();
    interrupting_ = false;
    held_ = false;
    follow_ups_ = 0;
    hold_.stop();
    messages_.clear();
    message_order_.clear();
    calls_completed_.clear();
    early_calls_.clear();
}

void AssistantRuntimeTranslator::stopRuntime() {
    if (!live_) return;
    live_ = false;
    releasing_ = true;
    hold_.stop();
    try {
        session_->retire();
    } catch (...) {
    }
    if (tools_) {
        tools_->disconnect(this);
        tools_->retire();
        tools_->deleteLater();
        tools_ = nullptr;
    }
    release();
}

void AssistantRuntimeTranslator::release() {
    // After the queued failure, if any: the view model settles a failed operation before it restarts.
    QMetaObject::invokeMethod(
        this,
        [this] {
            if (!releasing_) return;
            releasing_ = false;
            lease_.reset();
            if (outputOwnerState() == OutputOwnerState::Released) emit outputOwnersReleased();
        },
        Qt::QueuedConnection);
}

void AssistantRuntimeTranslator::fail(const QString& explanation, FailureKind kind) {
    if (failed_ || !live_) return;
    failed_ = true;
    failure_kind_ = kind;
    failure_generation_ = generation_;
    settleOperation();
    // As with Codex, nothing that arose before the failure is delivered after it.
    posts_.clear();
    for (const auto& request : std::as_const(requests_))
        if (tools_ && !request.closed) (void)tools_->refuse(request.toolId, tr("The assistant stopped."));
    clearState();
    const auto text = explanation.isEmpty() ? tr("The assistant stopped unexpectedly.") : explanation;
    posts_.push_back({generation_, [this, text] { emit failed(text); }});
    schedule();
    stopRuntime();
}

void AssistantRuntimeTranslator::post(std::function<void()> run) {
    if (failed_) return;
    posts_.push_back({generation_, std::move(run)});
    schedule();
}

void AssistantRuntimeTranslator::schedule() {
    if (drain_scheduled_) return;
    drain_scheduled_ = true;
    QMetaObject::invokeMethod(this, [this] { drain(); }, Qt::QueuedConnection);
}

void AssistantRuntimeTranslator::drain() {
    drain_scheduled_ = false;
    const QPointer<AssistantRuntimeTranslator> self(this);
    while (self && !posts_.empty()) {
        auto next = std::move(posts_.front());
        posts_.pop_front();
        if (next.generation != generation_) continue;
        try {
            next.run();  // The view model may retire or delete this provider here.
        } catch (...) {
        }
    }
}

void AssistantRuntimeTranslator::respond(const QString& id, const QString& method, const QJsonObject& result) {
    ack_deadlines_.remove(id);
    const QJsonObject envelope{{"id", id}, {"result", result}};
    post([this, id, method, envelope] { emit response(id, method, envelope); });
}

void AssistantRuntimeTranslator::refuse(const QString& id, const QString& method, int code, const QString& message) {
    ack_deadlines_.remove(id);
    const QJsonObject envelope{{"id", id}, {"error", QJsonObject{{"code", code}, {"message", message}}}};
    post([this, id, method, envelope] { emit response(id, method, envelope); });
}

void AssistantRuntimeTranslator::notify(const QString& method, const QJsonObject& params) {
    post([this, method, params] { emit event(method, params); });
}

void AssistantRuntimeTranslator::bindTools() {
    tools_listed_ = false;  // the next runtime process must list edi's tools itself
    if (tools_) tools_->bindGeneration(++bind_serial_);
}

void AssistantRuntimeTranslator::onToolsListed() {
    if (!live_ || failed_) return;
    tools_listed_ = true;
    answerThread();
}

void AssistantRuntimeTranslator::onToolsDisconnected() {
    // The runtime process behind the bridge ended; the next one (a new thread, a restart) must be able to connect.
    if (live_ && !failed_) bindTools();
}

// ---- Requests ----

QString AssistantRuntimeTranslator::request(const QString& method, const QJsonObject& params,
                                            const std::function<bool(const QString&)>& prepare) {
    if (failed_ || !live_ || method.isEmpty() || next_id_ == std::numeric_limits<quint64>::max()) return {};
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    auto id = QStringLiteral("edi-%1-%2").arg(generation_).arg(++next_id_);
    if (prepare && !prepare(id)) return {};
    if (!self || generation_ != scope || failed_ || !live_) return {};
    try {
        handle(id, method, params);
    } catch (...) {
        if (self && generation_ == scope) fail(tr("The assistant request could not be handled."));
        return {};
    }
    return id;
}

bool AssistantRuntimeTranslator::notification(const QString& method, const QJsonObject& params) {
    Q_UNUSED(params);
    return live_ && !failed_ && !method.isEmpty();
}

void AssistantRuntimeTranslator::handle(const QString& id, const QString& method, const QJsonObject& params) {
    const auto now = clock_.elapsed();
    if (method == QLatin1StringView("initialize") || method == QLatin1StringView("thread/archive") ||
        method == QLatin1StringView("thread/name/set")) {
        // edi's records carry the archive mark and the name; the runtime has nothing to change.
        respond(id, method, {});
    } else if (method == QLatin1StringView("account/read") || method == QLatin1StringView("model/list") ||
               method == QLatin1StringView("skills/list") || method == QLatin1StringView("thread/start") ||
               method == QLatin1StringView("thread/resume")) {
        // Answered once the session has done its readbacks (identity, tools, skills) and listed its models.
        waiting_.append({id, method, params});
        ack_deadlines_.insert(id, now + static_cast<qint64>(Limits::sign_in_ms));
        service();
    } else if (method == QLatin1StringView("account/login/start")) {
        if (!login_rpc_.isEmpty() || !login_id_.isEmpty()) {
            refuse(id, method, kInvalidRequest, tr("A sign-in is already open."));
            return;
        }
        login_rpc_ = id;
        login_id_ = QStringLiteral("edi-login-%1-%2").arg(generation_).arg(next_id_);
        ack_deadlines_.insert(id, now + static_cast<qint64>(Limits::http_json_ms));
        session_->signIn(launch_);
    } else if (method == QLatin1StringView("account/logout")) {
        logout_rpc_ = id;
        ack_deadlines_.insert(id, now + static_cast<qint64>(Limits::http_json_ms));
        // Copilot's sign-out is not yet qualified to end only the selected account, so edi removes the account
        // from edi instead and says the GitHub sign-in stays (ADR-0108 §5).
        if (provider_ == AssistantProviderId::Copilot) session_->removeAccount(launch_);
        else session_->signOut(launch_);
    } else if (method == QLatin1StringView("account/rateLimits/read")) {
        if (!session_->reportsUsage()) refuse(id, method, kUnsupported, tr("This assistant does not report usage."));
        else respond(id, method, usageResult());
    } else if (method == QLatin1StringView("thread/read")) {
        const auto thread = string_field(params, "threadId");
        if (thread.isEmpty()) refuse(id, method, kInvalidRequest, tr("No conversation was named."));
        else respond(id, method, {{"thread", threadObject(thread)}});
    } else if (method == QLatin1StringView("thread/items/list")) {
        // The runtime keeps no items for edi; the earlier rows come from edi's own history file.
        respond(id, method, {{"data", QJsonArray{}}, {"nextCursor", QJsonValue::Null}});
    } else if (method == QLatin1StringView("thread/settings/update")) {
        const auto model = string_field(params, "model");
        if (thread_.isEmpty() || params.value(QLatin1StringView("threadId")) != thread_ || model.isEmpty()) {
            refuse(id, method, kInvalidRequest, tr("No such conversation is open."));
            return;
        }
        model_ = model;
        effort_ = string_field(params, "effort");
        session_->selectModel(thread_, model_, effort_);
        respond(id, method, {});
        notify(QStringLiteral("thread/settings/updated"), {{"threadId", thread_}, {"threadSettings", readback(QStringLiteral("effort"))}});
    } else if (method == QLatin1StringView("turn/start")) {
        startTurn(id, params);
    } else if (method == QLatin1StringView("turn/steer")) {
        steerTurn(id, params);
    } else if (method == QLatin1StringView("turn/interrupt")) {
        interruptTurn(id, params);
    } else if (method == QLatin1StringView("thread/list")) {
        // These runtimes keep no list for edi; edi's own records of this account's conversations are the list.
        respond(id, method, {{"data", known_threads_}, {"nextCursor", QJsonValue::Null}});
    } else {
        // Anything else the runtime has no equivalent for.
        refuse(id, method, kUnsupported, tr("This assistant does not support %1.").arg(method));
    }
}

bool AssistantRuntimeTranslator::answerable(const Waiting& waiting) const {
    if (waiting.method == QLatin1StringView("account/read")) return account_ != Account::Unknown;
    if (waiting.method == QLatin1StringView("model/list")) return account_ == Account::Ready && models_known_;
    return account_ == Account::Ready;
}

void AssistantRuntimeTranslator::answerWaiting(const Waiting& waiting) {
    if (waiting.method == QLatin1StringView("account/read")) respond(waiting.id, waiting.method, accountResult());
    else if (waiting.method == QLatin1StringView("model/list")) respond(waiting.id, waiting.method, modelResult());
    else if (waiting.method == QLatin1StringView("skills/list")) respond(waiting.id, waiting.method, skillResult(waiting.params));
    else openThread(waiting.id, waiting.method, waiting.params);
}

void AssistantRuntimeTranslator::service() {
    if (failed_ || !live_) return;
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    const auto pending = std::exchange(waiting_, {});
    QList<Waiting> keep;
    for (const auto& waiting : pending) {
        if (!self || generation_ != scope || failed_ || !live_) return;
        if (answerable(waiting)) answerWaiting(waiting);
        else keep.append(waiting);
    }
    if (!self || generation_ != scope) return;
    keep.append(waiting_);  // requests that arrived while these were answered come after them
    waiting_ = std::move(keep);
}

QJsonObject AssistantRuntimeTranslator::accountResult() const {
    // The protocol's account kinds, as the view model checks them:
    //   session state                    account/read result
    //   ready {email, plan, authMethod}  account {type: accountKind(), email, planType: plan, authMethod}
    //   accountRefused, signed out       account: null (the view model starts account/login/start)
    //   accountRefused, other reason     no reply; the provider fails with the reason
    // The kind is the provider's own key (accountKind()); a Claude identity decided by the user's own key keeps it and
    // names the method in authMethod.
    if (account_ != Account::Ready) return {{"account", QJsonValue::Null}, {"requiresOpenaiAuth", true}};
    QJsonObject account{{"type", accountKind()}};
    const auto email = string_field(identity_, "email");
    account["email"] = email.isEmpty() ? QJsonValue(QJsonValue::Null) : QJsonValue(email);
    const auto plan = string_field(identity_, "plan");
    if (!plan.isEmpty()) account["planType"] = plan;
    // What decides the identity (Claude: claude.ai, or the user's own key, token or cloud provider).
    const auto method = string_field(identity_, "authMethod");
    if (!method.isEmpty()) account["authMethod"] = method;
    // Non-secret parts of the principal, so the dialog can name it and an unidentified key can be told apart.
    for (const auto* field : {"organization", "apiKeySource", "tokenSource", "login", "host", "managedSettings"}) {
        const auto value = string_field(identity_, field);
        if (!value.isEmpty()) account[QLatin1StringView(field)] = value;
    }
    if (identity_.value("hooksRan").toBool()) account["hooksRan"] = true;
    return {{"account", account}, {"requiresOpenaiAuth", false}};
}

QJsonObject AssistantRuntimeTranslator::modelResult() const {
    QJsonArray data;
    for (const auto& value : models_) {
        const auto model = value.toObject();
        const auto id = string_field(model, "id");
        if (id.isEmpty()) continue;
        QJsonArray efforts;
        for (const auto& effort : model.value(QLatin1StringView("efforts")).toArray())
            if (effort.isString() && !effort.toString().isEmpty())
                efforts.append(QJsonObject{{"reasoningEffort", effort.toString()}, {"description", QString()}});
        const auto name = string_field(model, "displayName");
        const auto defaultEffort = string_field(model, "defaultEffort");
        data.append(QJsonObject{{"id", id},
                                {"model", id},
                                {"displayName", name.isEmpty() ? id : name},
                                {"description", QString()},
                                {"hidden", false},
                                {"isDefault", data.isEmpty()},
                                {"supportedReasoningEfforts", efforts},
                                // No advertised default means the provider's own default (ADR-0057).
                                {"defaultReasoningEffort",
                                 defaultEffort.isEmpty() ? QJsonValue(QJsonValue::Null) : QJsonValue(defaultEffort)}});
    }
    return {{"data", data}, {"nextCursor", QJsonValue::Null}};
}

QJsonObject AssistantRuntimeTranslator::skillResult(const QJsonObject& params) const {
    const auto cwds = params.value(QLatin1StringView("cwds")).toArray();
    const auto cwd = !cwds.isEmpty() && cwds.first().isString() ? cwds.first().toString() : launch_.workspace;
    // Each skill the runtime discovered, named by the staged copy the view model verifies byte for byte. A skill
    // the runtime did not report is absent, and the view model then refuses the start.
    QJsonArray skills;
    for (const auto& id : skills_)
        skills.append(QJsonObject{{"name", id},
                                  {"path", QDir(cwd).filePath(QStringLiteral(".agents/skills/") + id + QStringLiteral("/SKILL.md"))},
                                  {"description", QString()},
                                  {"enabled", true}});
    return {{"data", QJsonArray{QJsonObject{{"cwd", cwd}, {"skills", skills}, {"errors", QJsonArray{}}}}}};
}

QJsonObject AssistantRuntimeTranslator::usageResult() const {
    // The protocol names the session window by a 300-minute duration and the weekly one by 10080 minutes; the panel
    // labels them by these values.
    QJsonObject limits;
    if (usage_.value(QLatin1StringView("available")).toBool()) {
        for (const auto& value : usage_.value(QLatin1StringView("buckets")).toArray()) {
            const auto bucket = value.toObject();
            const auto window = string_field(bucket, "window");
            if (window != QLatin1StringView("session") && window != QLatin1StringView("weekly")) continue;
            const auto used = bucket.value(QLatin1StringView("usedPercent")).toDouble(std::numeric_limits<double>::quiet_NaN());
            if (!std::isfinite(used)) continue;
            QJsonObject entry{{"usedPercent", std::clamp<qint64>(std::llround(used), 0, 2147483647)},
                              {"windowDurationMins", window == QLatin1StringView("session") ? 300 : 10080}};
            if (const auto resets = epoch_seconds(bucket.value(QLatin1StringView("resetsAt"))); resets >= 0)
                entry["resetsAt"] = static_cast<double>(resets);
            limits[window == QLatin1StringView("session") ? QStringLiteral("primary") : QStringLiteral("secondary")] = entry;
        }
    }
    return {{"rateLimits", limits}};
}

QJsonObject AssistantRuntimeTranslator::threadObject(const QString& thread) const {
    // Every Claude and Copilot conversation edi can name was started by edi (ADR-0108 §8).
    const auto now = static_cast<double>(QDateTime::currentSecsSinceEpoch());
    QJsonObject status{{"type", "notLoaded"}};
    if (thread == thread_ && !thread_.isEmpty())
        status = turn_.isEmpty() ? QJsonObject{{"type", "idle"}}
                                                        : QJsonObject{{"type", "active"}, {"activeFlags", QJsonArray{}}};
    return {{"id", thread}, {"originator", "edi"}, {"ephemeral", false}, {"cwd", launch_.workspace},
            {"createdAt", now}, {"updatedAt", now}, {"status", status}, {"preview", QString()}};
}

QJsonObject AssistantRuntimeTranslator::readback(const QString& effortKey) const {
    // What the thread was opened with, and the policy fields this provider can show.
    auto settings = threadPolicy();
    settings["cwd"] = launch_.workspace;
    settings["model"] = model_;
    settings[effortKey] = effort_;
    return settings;
}

bool AssistantRuntimeTranslator::writeInstructions(const QString& text) const {
    // Claude reads them through --append-system-prompt-file, Copilot from AGENTS.md (ADR-0108 §4, §5).
    const QDir workspace(launch_.workspace);
    const auto path = provider_ == AssistantProviderId::Claude ? workspace.filePath(QStringLiteral(".edi/instructions.md"))
                                                               : workspace.filePath(QStringLiteral("AGENTS.md"));
    if (!QDir().mkpath(QFileInfo(path).absolutePath())) return false;
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) return false;
    const auto bytes = text.toUtf8();
    if (file.write(bytes) != bytes.size() || !file.commit()) return false;
    return QFile::setPermissions(path, QFile::ReadOwner | QFile::WriteOwner);
}

void AssistantRuntimeTranslator::openThread(const QString& id, const QString& method, const QJsonObject& params) {
    if (provider_ == AssistantProviderId::Copilot) {
        // No input without proof of the effective tools and of the selected login and host (ADR-0108 §5).
        if (!assistant_copilot_input_open) {
            refuse(id, method, kInvalidRequest,
                   tr("GitHub Copilot is not available yet: edi cannot confirm which tools it would use."));
            return;
        }
        // The record's host as the Copilot session spells it: lower case, no scheme, github.com when empty.
        auto host = launch_.account.host.trimmed().toLower();
        if (host.startsWith(QStringLiteral("https://"))) host = host.mid(8);
        while (host.endsWith(QLatin1Char('/'))) host.chop(1);
        if (host.isEmpty()) host = QStringLiteral("github.com");
        if (!identity_.value(QLatin1StringView("identityProven")).toBool() ||
            string_field(identity_, "login") != launch_.account.email || string_field(identity_, "host") != host) {
            refuse(id, method, kInvalidRequest,
                   tr("GitHub Copilot did not confirm that it uses this account on this host."));
            return;
        }
    }
    if (!thread_rpc_.isEmpty() || !turn_.isEmpty()) {
        refuse(id, method, kInvalidRequest, tr("A conversation is already being opened or used."));
        return;
    }
    if (!same_path(params.value(QLatin1StringView("cwd")), launch_.workspace)) {
        refuse(id, method, kInvalidRequest, tr("The conversation folder is not edi's prepared workspace."));
        return;
    }
    const bool resume = method == QLatin1StringView("thread/resume");
    const auto target = resume ? string_field(params, "threadId") : QString();
    if (resume && target.isEmpty()) {
        refuse(id, method, kInvalidRequest, tr("No conversation was named."));
        return;
    }
    // thread/resume carries no catalogue; it is the one thread/start would send.
    const auto offered = params.value(QLatin1StringView("dynamicTools"));
    try {
        if (!tools_) throw std::runtime_error("The tool server is gone");
        const auto catalogue =
            assistant_native_mcp_tools(offered.isArray() ? offered.toArray() : assistant_native_tool_specs());
        tools_->setTools(catalogue);
        // The thread's process must show exactly this catalogue before its first input (ADR-0108 §1).
        launch_.expectedTools = mcp_tool_names(catalogue);
        session_->setExpectedTools(launch_.expectedTools);
    } catch (...) {
        refuse(id, method, kRefused, tr("edi's tools could not be offered to the assistant."));
        return;
    }
    launch_.instructions = string_field(params, "developerInstructions");
    if (!writeInstructions(launch_.instructions)) {
        refuse(id, method, kRefused, tr("The assistant instructions could not be written."));
        return;
    }
    model_ = string_field(params, "model");
    effort_ = params.value(QLatin1StringView("config")).toObject().value(QLatin1StringView("model_reasoning_effort")).toString();
    thread_.clear();
    opened_thread_.clear();
    thread_rpc_ = id;
    thread_method_ = method;
    thread_target_ = target;
    ack_deadlines_.insert(id, clock_.elapsed() + static_cast<qint64>(Limits::sign_in_ms));
    // Claude starts one process per thread, which must list edi's tools itself; Copilot's one process listed them at
    // start. A fresh binding keeps an earlier process's listing from counting for the new one.
    if (provider_ == AssistantProviderId::Claude) bindTools();
    session_->openThread(target, model_, effort_);
}

// ---- Session events: account, models, threads ----

void AssistantRuntimeTranslator::onReady(const QJsonObject& identity, const QStringList& tools, const QStringList& skills) {
    Q_UNUSED(tools);  // the session has already checked them
    if (!live_ || failed_) return;
    identity_ = identity;
    skills_.clear();
    for (auto skill : skills) {
        // Claude lists plugin skills as edi:<id>.
        if (skill.startsWith(QLatin1StringView("edi:"))) skill.remove(0, 4);
        if (!skill.isEmpty() && !skills_.contains(skill)) skills_.append(skill);
    }
    account_ = Account::Ready;
    service();
}

void AssistantRuntimeTranslator::onAccountRefused(const QString& reason, bool signedOut) {
    if (!live_ || failed_) return;
    if (!signedOut) {
        fail(reason.isEmpty() ? tr("The account was refused.") : reason);
        return;
    }
    const bool wasReady = account_ == Account::Ready;
    account_ = Account::SignedOut;
    identity_ = {};
    // A signed-in account that signs out asks the view model to read the account again.
    if (wasReady) notify(QStringLiteral("account/updated"), {{"authMode", QJsonValue::Null}});
    service();
}

void AssistantRuntimeTranslator::onSignInOpened(const QString& url, const QString& code, const QString& prompt) {
    if (!live_ || failed_ || login_rpc_.isEmpty()) return;
    const auto rpc = std::exchange(login_rpc_, {});
    QJsonObject result{{"type", accountKind()}, {"loginId", login_id_}, {"authUrl", url}};
    if (!code.isEmpty()) result["userCode"] = code;
    if (!prompt.isEmpty()) result["prompt"] = prompt;
    respond(rpc, QStringLiteral("account/login/start"), result);
}

void AssistantRuntimeTranslator::onSignInFinished(bool success, const QString& message) {
    if (!live_ || failed_) return;
    if (!login_rpc_.isEmpty()) {
        const auto rpc = std::exchange(login_rpc_, {});
        login_id_.clear();
        refuse(rpc, QStringLiteral("account/login/start"), kRefused,
               message.isEmpty() ? tr("The sign-in did not complete.") : message);
        return;
    }
    if (login_id_.isEmpty()) return;
    const auto login = std::exchange(login_id_, {});
    notify(QStringLiteral("account/login/completed"),
           {{"loginId", login}, {"success", success},
            {"error", success ? QJsonValue(QJsonValue::Null) : QJsonValue(message.isEmpty() ? tr("The sign-in did not complete.") : message)}});
    if (!success) return;
    notify(QStringLiteral("account/updated"), {{"authMode", accountKind()}});
    // Read the new identity back before anything is sent: restart the session's readbacks.
    account_ = Account::Unknown;
    identity_ = {};
    skills_.clear();
    models_ = {};
    models_known_ = false;
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    bool restarted = false;
    try {
        session_->retire();
        bindTools();
        restarted = session_->start(launch_);
    } catch (...) {
        restarted = false;
    }
    if (self && generation_ == scope && !restarted) fail(tr("The assistant could not be restarted after sign-in."));
}

void AssistantRuntimeTranslator::onSignedOut() {
    if (!live_ || failed_) return;
    account_ = Account::SignedOut;
    identity_ = {};
    if (!logout_rpc_.isEmpty()) respond(std::exchange(logout_rpc_, {}), QStringLiteral("account/logout"), {});
}

void AssistantRuntimeTranslator::onModelsListed(const QJsonArray& models) {
    if (!live_ || failed_) return;
    models_ = models;
    models_known_ = true;
    service();
}

void AssistantRuntimeTranslator::onThreadOpened(const QString& thread) {
    if (!live_ || failed_ || thread_rpc_.isEmpty() || !opened_thread_.isEmpty()) return;
    if (thread.isEmpty() || (!thread_target_.isEmpty() && thread != thread_target_)) {
        const auto rpc = std::exchange(thread_rpc_, {});
        thread_target_.clear();
        refuse(rpc, std::exchange(thread_method_, {}), kRefused, tr("The assistant opened another conversation than the one asked for."));
        return;
    }
    opened_thread_ = thread;
    answerThread();
}

void AssistantRuntimeTranslator::answerThread() {
    // Only once the runtime runs with edi's settings and has listed edi's tools through edi's server, so the
    // view model's policy check and native dispatch admit calls in their usual order (ADR-0108 §1).
    if (thread_rpc_.isEmpty() || opened_thread_.isEmpty() || !tools_listed_ || account_ != Account::Ready) return;
    const auto rpc = std::exchange(thread_rpc_, {});
    const auto method = std::exchange(thread_method_, {});
    thread_target_.clear();
    thread_ = std::exchange(opened_thread_, {});
    auto result = readback(QStringLiteral("reasoningEffort"));
    result["thread"] = threadObject(thread_);
    respond(rpc, method, result);
}

void AssistantRuntimeTranslator::onUsageChanged(const QJsonObject& snapshot) {
    if (!live_ || failed_) return;
    usage_ = snapshot;
    if (account_ == Account::Ready)
        notify(QStringLiteral("account/rateLimits/updated"), {{"rateLimits", usageResult().value(QLatin1StringView("rateLimits"))}});
}

// ---- Deadlines, with CodexAgent's semantics ----

void AssistantRuntimeTranslator::beginOperation(quint64 totalMs, quint64 idleMs) {
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    if (!finishHumanWait()) return;
    native_work_id_.clear();
    native_work_waiting_ = false;
    wait_accounted_at_ = -1;
    checkDeadline();
    if (!self || generation_ != scope || failed_) return;
    const auto now = clock_.elapsed();
    // Expiry must never turn into the zero (disabled) deadline of a new operation.
    if (operationExpired(now)) {
        fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
        return;
    }
    if (operation_start_ >= 0 && total_ms_) {
        const auto remaining = total_ms_ - static_cast<quint64>(now - operation_start_);
        if (totalMs == 0 || totalMs > remaining) totalMs = remaining;
    }
    operation_start_ = now;
    last_activity_ = now;
    total_ms_ = totalMs;
    idle_ms_ = idleMs;
}

void AssistantRuntimeTranslator::settleOperation() {
    human_wait_start_ = -1;
    human_wait_id_.clear();
    native_work_id_.clear();
    native_work_waiting_ = false;
    wait_accounted_at_ = -1;
    operation_start_ = -1;
    total_ms_ = 0;
    idle_ms_ = 0;
}

bool AssistantRuntimeTranslator::operationExpired(qint64 now) const noexcept {
    return operation_start_ >= 0 &&
           (now < operation_start_ || now < last_activity_ ||
            (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
            (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_));
}

bool AssistantRuntimeTranslator::accountWaits(qint64 now) {
    if (wait_accounted_at_ < 0) return true;
    if (now < wait_accounted_at_ || operation_start_ < 0 || operation_start_ > wait_accounted_at_ ||
        last_activity_ > wait_accounted_at_ || (human_wait_start_ < 0 && native_work_id_.isEmpty()) ||
        (native_work_waiting_ && native_work_id_.isEmpty())) {
        fail(tr("The assistant wait clock is invalid."));
        return false;
    }
    // A human answer suspends both deadlines; edi's own tool work suspends the idle deadline, and the total one only
    // while it waits for the user.
    const auto elapsed = now - wait_accounted_at_;
    if (human_wait_start_ >= 0 || native_work_waiting_) operation_start_ += elapsed;
    if (human_wait_start_ >= 0 || !native_work_id_.isEmpty()) last_activity_ += elapsed;
    wait_accounted_at_ = now;
    return true;
}

void AssistantRuntimeTranslator::activity() {
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return;
    last_activity_ = now;
}

bool AssistantRuntimeTranslator::finishHumanWait() {
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return false;
    human_wait_start_ = -1;
    human_wait_id_.clear();
    if (native_work_id_.isEmpty()) wait_accounted_at_ = -1;
    return true;
}

bool AssistantRuntimeTranslator::beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !live_ || operation_start_ < 0) return false;
    const auto key = idKey(originalRequestId);
    if (key.isEmpty() || !requests_.contains(key)) return false;
    if (human_wait_start_ >= 0) return human_wait_id_ == key;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return false;
    if (operationExpired(now)) {
        fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
        return false;
    }
    human_wait_id_ = key;
    human_wait_start_ = now;
    wait_accounted_at_ = now;
    return true;
}

bool AssistantRuntimeTranslator::endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !live_) return false;
    const auto key = idKey(originalRequestId);
    if (key.isEmpty() || !requests_.contains(key) || (human_wait_start_ >= 0 && human_wait_id_ != key)) return false;
    return finishHumanWait();
}

bool AssistantRuntimeTranslator::beginNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !live_ || operation_start_ < 0) return false;
    const auto key = idKey(originalRequestId);
    if (key.isEmpty() || !requests_.contains(key)) return false;
    if (!native_work_id_.isEmpty()) return native_work_id_ == key;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return false;
    if (operationExpired(now)) {
        fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
        return false;
    }
    native_work_id_ = key;
    native_work_waiting_ = false;
    wait_accounted_at_ = now;
    return true;
}

bool AssistantRuntimeTranslator::setNativeWorkWaiting(const QJsonValue& originalRequestId, quint64 originalGeneration,
                                                      bool waiting) {
    if (generation_ != originalGeneration || failed_ || !live_ || operation_start_ < 0) return false;
    const auto found = requests_.constFind(native_work_id_);
    if (native_work_id_.isEmpty() || found == requests_.cend() || found->id != originalRequestId) return false;
    if (native_work_waiting_ == waiting) return true;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return false;
    if (operationExpired(now)) {
        fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
        return false;
    }
    native_work_waiting_ = waiting;
    wait_accounted_at_ = now;
    return true;
}

bool AssistantRuntimeTranslator::endNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !live_) return false;
    if (native_work_id_.isEmpty())
        return std::any_of(requests_.cbegin(), requests_.cend(), [&](const auto& request) { return request.id == originalRequestId; });
    const auto found = requests_.constFind(native_work_id_);
    if (found == requests_.cend() || found->id != originalRequestId) return false;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return false;
    native_work_id_.clear();
    native_work_waiting_ = false;
    if (human_wait_start_ < 0) wait_accounted_at_ = -1;
    if (operationExpired(now)) {
        fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
        return false;
    }
    return true;
}

void AssistantRuntimeTranslator::checkDeadline() {
    if (failed_ || !live_) return;
    const auto now = clock_.elapsed();
    for (auto it = ack_deadlines_.cbegin(); it != ack_deadlines_.cend(); ++it) {
        if (now >= it.value()) {
            fail(tr("The assistant did not answer a request in time."));
            return;
        }
    }
    if (operation_start_ < 0 || !accountWaits(now)) return;
    if (operationExpired(now)) fail(tr("The assistant operation exceeded its deadline."), FailureKind::OperationDeadline);
}

QString AssistantRuntimeTranslator::idKey(const QJsonValue& value) {
    if (value.isString() && !value.toString().isEmpty() &&
        value.toString().toUtf8().size() <= static_cast<qsizetype>(Limits::id_bytes))
        return QStringLiteral("s:") + value.toString();
    if (value.isDouble()) {
        const auto number = value.toDouble();
        if (std::isfinite(number) && std::floor(number) == number && std::abs(number) <= 9007199254740991.0)
            return QStringLiteral("n:") + QString::number(number, 'f', 0);
    }
    return {};
}

// ---- Turns and items ----

void AssistantRuntimeTranslator::startTurn(const QString& id, const QJsonObject& params) {
    const auto method = QStringLiteral("turn/start");
    if (thread_.isEmpty() || params.value(QLatin1StringView("threadId")) != thread_) {
        refuse(id, method, kInvalidRequest, tr("No such conversation is open."));
        return;
    }
    if (!turn_.isEmpty()) {
        refuse(id, method, kInvalidRequest, tr("A turn is already running."));
        return;
    }
    const auto text = joined_text(params.value(QLatin1StringView("input")).toArray());
    if (text.isEmpty()) {
        refuse(id, method, kInvalidRequest, QStringLiteral("input must not be empty"));
        return;
    }
    const auto model = string_field(params, "model");
    const auto effort = string_field(params, "effort");
    if (!model.isEmpty() && (model != model_ || effort != effort_)) {
        model_ = model;
        effort_ = effort;
        session_->selectModel(thread_, model_, effort_);
    }
    // Acknowledged at admission, as the app-server does, with edi's own turn id; the runtime's turn id is matched
    // to it when the session announces the turn.
    turn_ = QStringLiteral("edi-turn-%1-%2").arg(generation_).arg(++next_id_);
    session_turn_.clear();
    interrupting_ = false;
    held_ = false;
    follow_ups_ = 0;
    messages_.clear();
    message_order_.clear();
    calls_completed_.clear();
    early_calls_.clear();
    respond(id, method, {{"turn", QJsonObject{{"id", turn_}, {"status", "inProgress"}, {"items", QJsonArray{}}, {"error", QJsonValue::Null}}}});
    notify(QStringLiteral("turn/started"),
           {{"threadId", thread_}, {"turn", QJsonObject{{"id", turn_}, {"status", "inProgress"}, {"items", QJsonArray{}}}}});
    session_->sendMessage(thread_, string_field(params, "clientUserMessageId"), text);
}

void AssistantRuntimeTranslator::steerTurn(const QString& id, const QJsonObject& params) {
    // The refusal reasons are the app-server's own words, which the view model recognises as "not admitted".
    const auto method = QStringLiteral("turn/steer");
    const auto expected = string_field(params, "expectedTurnId");
    if (expected.isEmpty()) {
        refuse(id, method, kInvalidRequest, QStringLiteral("expectedTurnId must not be empty"));
        return;
    }
    if (turn_.isEmpty() || interrupting_ || params.value(QLatin1StringView("threadId")) != thread_) {
        refuse(id, method, kInvalidRequest, QStringLiteral("no active turn to steer"));
        return;
    }
    if (expected != turn_) {
        refuse(id, method, kInvalidRequest,
               QStringLiteral("expected active turn id `") + expected + QStringLiteral("` but found `") + turn_ + QLatin1Char('`'));
        return;
    }
    const auto text = joined_text(params.value(QLatin1StringView("input")).toArray());
    if (text.isEmpty()) {
        refuse(id, method, kInvalidRequest, QStringLiteral("input must not be empty"));
        return;
    }
    // The session steers when its runtime can and otherwise queues the message as the next runtime turn; either way
    // it belongs to this protocol turn.
    const auto turn = turn_;
    ++follow_ups_;
    respond(id, method, {{"turnId", turn}});
    session_->sendMessage(thread_, string_field(params, "clientUserMessageId"), text);
}

void AssistantRuntimeTranslator::interruptTurn(const QString& id, const QJsonObject& params) {
    const auto method = QStringLiteral("turn/interrupt");
    // A turn that has already ended needs no interrupt; the view model only needs the acknowledgement.
    const bool running = !turn_.isEmpty() && params.value(QLatin1StringView("threadId")) == thread_ &&
                         params.value(QLatin1StringView("turnId")) == turn_;
    respond(id, method, {});
    if (!running || interrupting_) return;
    interrupting_ = true;
    follow_ups_ = 0;
    for (const auto& call : std::exchange(early_calls_, {}))
        if (tools_) (void)tools_->refuse(call.toolId, tr("The assistant turn was stopped."));
    session_->cancelTurn(thread_);
    // Between runtime turns, or before the first one began, no runtime turn will report the end.
    if (held_ || session_turn_.isEmpty()) finishTurn(QStringLiteral("interrupted"), {});
}

bool AssistantRuntimeTranslator::currentTurn(const QString& thread, const QString& turn) const {
    return live_ && !failed_ && !thread_.isEmpty() && thread == thread_ && !turn_.isEmpty() && !held_ &&
           !session_turn_.isEmpty() && turn == session_turn_;
}

void AssistantRuntimeTranslator::onTurnStarted(const QString& thread, const QString& turn) {
    if (!live_ || failed_ || thread_.isEmpty() || thread != thread_ || turn.isEmpty()) return;
    if (!turn_.isEmpty() && session_turn_.isEmpty() && !interrupting_) {
        session_turn_ = turn;
    } else if (!turn_.isEmpty() && turn == session_turn_) {
        return;
    } else if (!turn_.isEmpty() && !interrupting_ && (held_ || follow_ups_ > 0)) {
        // The runtime turn a follow-up message started continues the same protocol turn.
        held_ = false;
        hold_.stop();
        if (follow_ups_ > 0) --follow_ups_;
        session_turn_ = turn;
    } else {
        // A runtime turn nobody asked for, or one after Stop: it must not run unseen.
        session_->cancelTurn(thread);
        return;
    }
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    for (const auto& call : std::exchange(early_calls_, {})) {
        if (!self || generation_ != scope || failed_) return;
        admitCall(call);
    }
}

void AssistantRuntimeTranslator::startMessage(const QString& item, const QString& type) {
    messages_.insert(item, Message{type, {}, false});
    message_order_.append(item);
    const auto declared = type == QLatin1StringView("reasoning")
                              ? QJsonObject{{"type", type}, {"id", item}, {"summary", QJsonArray{}}, {"content", QJsonArray{}}}
                              : QJsonObject{{"type", type}, {"id", item}, {"text", QString()}};
    notify(QStringLiteral("item/started"), {{"threadId", thread_}, {"turnId", turn_}, {"item", declared}});
}

void AssistantRuntimeTranslator::onTextDelta(const QString& thread, const QString& turn, const QString& item,
                                             const QString& delta) {
    if (!currentTurn(thread, turn) || item.isEmpty() || delta.isEmpty()) return;
    if (!messages_.contains(item)) startMessage(item, QStringLiteral("agentMessage"));
    auto& message = messages_[item];
    // The view model refuses text added to a finished message, or to an item of another type.
    if (message.completed || message.type != QLatin1StringView("agentMessage")) return;
    message.text += delta;
    notify(QStringLiteral("item/agentMessage/delta"), {{"threadId", thread_}, {"turnId", turn_}, {"itemId", item}, {"delta", delta}});
}

void AssistantRuntimeTranslator::onItemCompleted(const QString& thread, const QString& turn, const QJsonObject& item) {
    if (!currentTurn(thread, turn)) return;
    const auto type = string_field(item, "type");
    const auto id = string_field(item, "id");
    if (id.isEmpty() || (type != QLatin1StringView("agentMessage") && type != QLatin1StringView("reasoning"))) return;
    if (!messages_.contains(id)) startMessage(id, type);
    auto& message = messages_[id];
    if (message.completed || message.type != type) return;  // a final item never changes
    const auto text = string_field(item, "text");
    if (!text.isEmpty()) message.text = text;
    message.completed = true;
    const auto finished = type == QLatin1StringView("reasoning")
                           ? QJsonObject{{"type", type}, {"id", id}, {"summary", QJsonArray{message.text}}, {"content", QJsonArray{}}}
                           : QJsonObject{{"type", type}, {"id", id}, {"text", message.text}};
    notify(QStringLiteral("item/completed"), {{"threadId", thread_}, {"turnId", turn_}, {"item", finished}});
}

void AssistantRuntimeTranslator::onForeignTool(const QString& thread, const QString& turn, const QString& tool) {
    if (!live_ || failed_ || thread != thread_) return;
    const auto message = tr("The assistant tried to use %1, a tool edi does not offer, so the turn was stopped.").arg(tool);
    Q_UNUSED(turn);
    if (!turn_.isEmpty()) finishTurn(QStringLiteral("failed"), {{"message", message}});
    // Stop the runtime now; the failure follows the turn's end, so the view model reads that first.
    try {
        session_->retire();
    } catch (...) {
    }
    post([this, message] { fail(message); });
}

void AssistantRuntimeTranslator::onTurnFinished(const QString& thread, const QString& turn, const QString& status,
                                                const QJsonObject& error) {
    if (!live_ || failed_ || thread_.isEmpty() || thread != thread_) return;
    if (!turn_.isEmpty() && session_turn_.isEmpty() && !held_) session_turn_ = turn;  // ended before it was announced
    if (turn_.isEmpty() || held_ || turn != session_turn_) return;
    if (status == QLatin1StringView("completed") && follow_ups_ > 0 && !interrupting_) {
        // A queued follow-up starts the next runtime turn; keep this protocol turn open for it, for a bounded time.
        held_ = true;
        hold_.start();
        return;
    }
    finishTurn(status, error);
}

void AssistantRuntimeTranslator::finishTurn(QString status, QJsonObject error) {
    if (turn_.isEmpty()) return;
    hold_.stop();
    held_ = false;
    // Every item the turn declared is final before its end (the view model checks this for a completed turn).
    for (const auto& id : std::as_const(message_order_)) {
        auto& message = messages_[id];
        if (message.completed) continue;
        message.completed = true;
        const auto finished = message.type == QLatin1StringView("reasoning")
                               ? QJsonObject{{"type", message.type}, {"id", id}, {"summary", QJsonArray{message.text}}, {"content", QJsonArray{}}}
                               : QJsonObject{{"type", message.type}, {"id", id}, {"text", message.text}};
        notify(QStringLiteral("item/completed"), {{"threadId", thread_}, {"turnId", turn_}, {"item", finished}});
    }
    // Calls and questions still open end with the turn, as the app-server resolves them.
    bool unfinished = false;
    for (auto it = requests_.begin(); it != requests_.end(); ++it) {
        auto& request = it.value();
        if (request.closed || request.params.value(QLatin1StringView("turnId")) != turn_) continue;
        request.closed = true;
        unfinished = true;
        if (tools_) (void)tools_->refuse(request.toolId, tr("The assistant turn ended."));
        notify(QStringLiteral("serverRequest/resolved"), {{"threadId", thread_}, {"requestId", request.id}});
    }
    for (const auto& call : std::exchange(early_calls_, {}))
        if (tools_) (void)tools_->refuse(call.toolId, tr("The assistant turn ended."));
    if (status != QLatin1StringView("completed") && status != QLatin1StringView("interrupted")) status = QStringLiteral("failed");
    if (status == QLatin1StringView("completed") && unfinished) {
        status = QStringLiteral("failed");
        error = {{"message", tr("The assistant ended the turn before edi's tool finished.")}};
    }
    QJsonObject turn{{"id", turn_}, {"status", status}, {"items", QJsonArray{}}, {"error", QJsonValue::Null}};
    if (status == QLatin1StringView("failed")) {
        const auto message = string_field(error, "message");
        QJsonObject failure{{"message", message.isEmpty() ? tr("The assistant turn failed.") : message}};
        if (error.value(QLatin1StringView("signedOut")).toBool()) failure["codexErrorInfo"] = QStringLiteral("unauthorized");
        turn["error"] = failure;
    }
    notify(QStringLiteral("turn/completed"), {{"threadId", thread_}, {"turn", turn}});
    turn_.clear();
    session_turn_.clear();
    interrupting_ = false;
    follow_ups_ = 0;
    messages_.clear();
    message_order_.clear();
    calls_completed_.clear();
}

// ---- Tool calls and questions ----

void AssistantRuntimeTranslator::onToolCall(const QJsonValue& toolId, const QString& tool, const QJsonObject& arguments) {
    if (!tools_) return;
    // A call is admitted only for the running turn, once the session's readbacks passed and before Stop.
    if (!live_ || failed_ || account_ != Account::Ready || thread_.isEmpty() || interrupting_) {
        (void)tools_->refuse(toolId, tr("No assistant turn is running."));
        return;
    }
    if (turn_.isEmpty()) {
        (void)tools_->refuse(toolId, tr("No assistant turn is running."));
        return;
    }
    if (held_) {
        // Between the runtime turns of one protocol turn: the call belongs to the next runtime turn, so it waits.
        early_calls_.append({toolId, tool, arguments});
        return;
    }
    admitCall({toolId, tool, arguments});
}

void AssistantRuntimeTranslator::admitCall(const ToolCall& call) {
    if (server_sequence_ == std::numeric_limits<quint64>::max()) {
        if (tools_) (void)tools_->refuse(call.toolId, tr("No more requests can be accepted."));
        return;
    }
    const auto order = ++server_sequence_;
    const auto id = QStringLiteral("edi-tool-%1-%2").arg(generation_).arg(order);
    ServerRequest request;
    request.id = id;
    request.order = order;
    request.toolId = call.toolId;
    if (call.tool == QLatin1StringView("request_user_input")) {
        // edi's question tool has the schema of Codex's tool of the same name, so its arguments are the request.
        request.question = true;
        request.method = QStringLiteral("item/tool/requestUserInput");
        request.params = {{"threadId", thread_},
                          {"turnId", turn_},
                          {"itemId", QStringLiteral("edi-question-%1-%2").arg(generation_).arg(order)},
                          {"questions", call.arguments.value(QLatin1StringView("questions"))}};
    } else {
        const auto callId = QStringLiteral("edi-call-%1-%2").arg(generation_).arg(order);
        request.method = QStringLiteral("item/tool/call");
        request.params = {{"threadId", thread_}, {"turnId", turn_}, {"callId", callId}, {"tool", call.tool}, {"arguments", call.arguments}};
        calls_completed_.insert(callId, false);
        // The item the view model's dispatch checks the call against.
        notify(QStringLiteral("item/started"),
               {{"threadId", thread_},
                {"turnId", turn_},
                {"item", QJsonObject{{"type", "dynamicToolCall"}, {"id", callId}, {"tool", call.tool}, {"arguments", call.arguments},
                                     {"status", "inProgress"}}}});
    }
    const auto key = idKey(request.id);
    const auto method = request.method;
    const auto params = request.params;
    requests_.insert(key, request);
    post([this, key, id, method, params] {
        const auto found = requests_.constFind(key);
        if (found == requests_.cend() || found->closed) return;  // cancelled before the view model saw it
        emit serverRequest(QJsonValue(id), method, params);
    });
}

void AssistantRuntimeTranslator::completeCall(const ServerRequest& request, bool success, const QJsonArray& contentItems) {
    if (request.question) return;
    const auto callId = string_field(request.params, "callId");
    const auto found = calls_completed_.find(callId);
    if (found == calls_completed_.end() || found.value()) return;
    found.value() = true;
    notify(QStringLiteral("item/completed"),
           {{"threadId", request.params.value(QLatin1StringView("threadId"))},
            {"turnId", request.params.value(QLatin1StringView("turnId"))},
            {"item", QJsonObject{{"type", "dynamicToolCall"},
                                 {"id", callId},
                                 {"tool", request.params.value(QLatin1StringView("tool"))},
                                 {"arguments", request.params.value(QLatin1StringView("arguments"))},
                                 {"status", success ? "completed" : "failed"},
                                 {"success", success},
                                 {"contentItems", contentItems}}}});
}

void AssistantRuntimeTranslator::onToolCancelled(const QJsonValue& toolId) {
    if (!live_ || failed_) return;
    early_calls_.erase(std::remove_if(early_calls_.begin(), early_calls_.end(), [&](const ToolCall& call) { return call.toolId == toolId; }),
                       early_calls_.end());
    for (auto it = requests_.begin(); it != requests_.end(); ++it) {
        auto& request = it.value();
        if (request.closed || request.toolId != toolId) continue;
        // The runtime gave up on the call: resolve it as the app-server's serverRequest/resolved does.
        request.closed = true;
        notify(QStringLiteral("serverRequest/resolved"),
               {{"threadId", request.params.value(QLatin1StringView("threadId"))}, {"requestId", request.id}});
        completeCall(request, false, {});
        return;
    }
}

bool AssistantRuntimeTranslator::answer(const QJsonValue& originalId, const QJsonObject& result, void* preparation,
                                        bool (*handoff)(void*) noexcept, const std::function<bool()>& admit) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !requests_.contains(key) || failed_ || !live_) return false;
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto scope = generation_;
    const auto current = [&] { return self && generation_ == scope && !failed_ && live_ && requests_.contains(key); };
    // As CodexAgent::answer: admission, then the waits end and the request retires, then the borrowed handoff runs,
    // and only then is the answer delivered. A failed handoff leaves the request retired, never repeated.
    if (admit && !admit()) return false;
    if (!current()) return false;
    if (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, scope)) return false;
    if (native_work_id_ == key && !endNativeWork(originalId, scope)) return false;
    if (!current()) return false;
    const auto request = requests_.take(key);
    if (handoff && !handoff(preparation)) return false;
    if (!self || generation_ != scope || failed_ || !live_) return false;
    if (request.question) {
        // The answers go back as the tool's result, in the shape the view model built: {answers: {<id>: {answers}}}.
        if (request.closed) return true;  // resolved already, as an answer Codex writes after a cancellation
        return tools_ && tools_->reply(request.toolId, true, QJsonDocument(result).toJson(QJsonDocument::Compact));
    }
    // The projected outgoing JSON the view model put in contentItems is what the model reads.
    const bool success = result.value(QLatin1StringView("success")).toBool();
    const auto contentItems = result.value(QLatin1StringView("contentItems")).toArray();
    QByteArray text;
    for (const auto& value : contentItems) {
        const auto item = value.toObject();
        if (item.value(QLatin1StringView("type")) != QLatin1StringView("inputText") || !item.value(QLatin1StringView("text")).isString())
            continue;
        if (!text.isEmpty()) text.append('\n');
        text.append(item.value(QLatin1StringView("text")).toString().toUtf8());
    }
    if (request.closed) return true;  // resolved already, as an answer Codex writes after a cancellation
    const bool delivered = tools_ && tools_->reply(request.toolId, success, text);
    if (delivered) completeCall(request, success, contentItems);
    return delivered;
}

bool AssistantRuntimeTranslator::reject(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !requests_.contains(key) ||
        (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_)))
        return false;
    if (native_work_id_ == key && !endNativeWork(originalId, generation_)) return false;
    const auto request = requests_.take(key);
    if (failed_ || !live_) return false;
    if (tools_) (void)tools_->refuse(request.toolId, tr("edi does not support this request."));
    if (!request.closed) completeCall(request, false, {});
    return true;
}

void AssistantRuntimeTranslator::resolved(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_)) return;
    if (native_work_id_ == key && !endNativeWork(originalId, generation_)) return;
    requests_.remove(key);
}

bool AssistantRuntimeTranslator::deferServerRequest(const QJsonValue& originalId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !live_) return false;
    const auto key = idKey(originalId);
    auto found = requests_.find(key);
    if (key.isEmpty() || found == requests_.end() || found->id != originalId) return false;
    found->deferred = true;
    return true;
}

void AssistantRuntimeTranslator::resumeDeferredRequests(quint64 originalGeneration) {
    const QPointer<AssistantRuntimeTranslator> self(this);
    const auto current = [&] { return self && generation_ == originalGeneration && live_ && !failed_; };
    if (!current()) return;
    QList<QPair<quint64, QString>> ordered;
    for (auto it = requests_.cbegin(); it != requests_.cend(); ++it)
        if (it->deferred && !it->closed) ordered.append({it->order, it.key()});
    std::sort(ordered.begin(), ordered.end());
    for (const auto& entry : ordered) {
        if (!current()) return;
        auto found = requests_.find(entry.second);
        if (found == requests_.end() || found->order != entry.first || !found->deferred) continue;
        const auto request = *found;
        found->deferred = false;  // consumed before the view model's handler can reenter
        emit serverRequest(request.id, request.method, request.params);
        if (!current()) return;
        found = requests_.find(entry.second);
        if (found != requests_.end() && found->order == entry.first && found->deferred) return;
    }
}
}  // namespace edi_app

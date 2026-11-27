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
        server->setTools(assistant_native_mcp_tools(assistant_native_tool_specs()));
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
    const auto id = QStringLiteral("edi-%1-%2").arg(generation_).arg(++next_id_);
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
    if (method == QLatin1StringView("initialize")) {
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
        session_->signOut(launch_);
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
    } else {
        // thread/list, thread/name/set, thread/archive and anything else the runtime has no equivalent for.
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
    //   ready {email, plan, authMethod}  account {type: "chatgpt", email, planType: plan, authMethod}
    //   accountRefused, signed out       account: null (the view model starts account/login/start)
    //   accountRefused, other reason     no reply; the provider fails with the reason
    // "chatgpt" is the protocol's kind for a subscription account signed in through the runtime's own login, which
    // is how every Claude and Copilot account is read back. The protocol's apiKey kind would send the view model to
    // its sign-in flow, so a Claude identity decided by the user's own key keeps "chatgpt" and names the method in
    // authMethod.
    if (account_ != Account::Ready) return {{"account", QJsonValue::Null}, {"requiresOpenaiAuth", true}};
    QJsonObject account{{"type", "chatgpt"}};
    const auto email = string_field(identity_, "email");
    account["email"] = email.isEmpty() ? QJsonValue(QJsonValue::Null) : QJsonValue(email);
    const auto plan = string_field(identity_, "plan");
    if (!plan.isEmpty()) account["planType"] = plan;
    // What decides the identity (Claude: claude.ai, or the user's own key, token or cloud provider).
    const auto method = string_field(identity_, "authMethod");
    if (!method.isEmpty()) account["authMethod"] = method;
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
        tools_->setTools(assistant_native_mcp_tools(offered.isArray() ? offered.toArray() : assistant_native_tool_specs()));
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
    // Claude starts one process per thread, which lists edi's tools again; Copilot's one process listed them at start.
    if (provider_ == AssistantProviderId::Claude) tools_listed_ = false;
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
    QJsonObject result{{"type", "chatgpt"}, {"loginId", login_id_}, {"authUrl", url}};
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
    notify(QStringLiteral("account/updated"), {{"authMode", "chatgpt"}});
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
}  // namespace edi_app

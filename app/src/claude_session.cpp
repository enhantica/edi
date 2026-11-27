// SPDX-License-Identifier: BSD-3-Clause
#include "claude_session.hpp"
#include <QDateTime>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QSet>
#include <QSettings>
#include <QUrl>
#include <QUuid>
#include "assistant_process.hpp"

namespace edi_app {
namespace {

// The CLI waits up to MCP_TIMEOUT (30 s by default) for edi's server before the first turn.
constexpr int readback_ms = 120000;
constexpr int status_ms = 30000;
constexpr int login_ms = 15 * 60 * 1000;
constexpr int logout_ms = 60000;
constexpr qsizetype login_output_cap = 64 * 1024;

const QString edi_server = QStringLiteral("edi");
const QString edi_tool_prefix = QStringLiteral("mcp__edi__");
const QString skill_tool = QStringLiteral("Skill");

QString new_uuid() { return QUuid::createUuid().toString(QUuid::WithoutBraces); }

QString edi_path(const QString& workspace, const QString& name) {
    return QDir::toNativeSeparators(QDir(workspace).filePath(QStringLiteral(".edi/") + name));
}

bool allowed_tool(const QString& name) { return name == skill_tool || name.startsWith(edi_tool_prefix); }

// Create or replace a file readable only by its owner.
bool write_private(const QString& path, const QByteArray& bytes) {
    QFile file(path);
    constexpr auto owner = QFileDevice::ReadOwner | QFileDevice::WriteOwner;
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate, owner)) return false;
    // An existing file keeps its old mode on open.
    if (!file.setPermissions(owner)) return false;
    return file.write(bytes) == bytes.size() && file.flush();
}

bool valid_skill_id(const QString& id) {
    return !id.isEmpty() && id != QStringLiteral(".") && id != QStringLiteral("..") && !id.contains(u'/') &&
           !id.contains(u'\\') && !id.contains(u':');
}

// Copy one approved skill folder as it is, refusing links so only the verified bytes are staged.
bool copy_skill(const QString& source, const QString& target, QString& problem) {
    if (!QFileInfo(QDir(source).filePath(QStringLiteral("SKILL.md"))).isFile()) {
        problem = QStringLiteral("The skill folder %1 has no SKILL.md.").arg(QDir::toNativeSeparators(source));
        return false;
    }
    if (!QDir().mkpath(target)) {
        problem = QStringLiteral("edi could not create %1.").arg(QDir::toNativeSeparators(target));
        return false;
    }
    const QDir root(source);
    QDirIterator it(source, QDir::AllEntries | QDir::NoDotAndDotDot | QDir::Hidden | QDir::System,
                    QDirIterator::Subdirectories);
    while (it.hasNext()) {
        const QFileInfo entry(it.next());
        const auto destination = QDir(target).filePath(root.relativeFilePath(entry.filePath()));
        if (entry.isSymLink()) {
            problem = QStringLiteral("The skill file %1 is a link.").arg(QDir::toNativeSeparators(entry.filePath()));
            return false;
        }
        if (entry.isDir() ? QDir().mkpath(destination)
                          : QDir().mkpath(QFileInfo(destination).path()) && QFile::copy(entry.filePath(), destination))
            continue;
        problem = QStringLiteral("edi could not stage %1.").arg(QDir::toNativeSeparators(entry.filePath()));
        return false;
    }
    return true;
}

bool same_folder(const QString& reported, const QString& home) {
    if (reported.isEmpty() || home.isEmpty()) return false;
    const auto clean = [](const QString& path) {
        const auto canonical = QFileInfo(path).canonicalFilePath();
        return QDir::cleanPath(QDir::fromNativeSeparators(canonical.isEmpty() ? path : canonical));
    };
#ifdef Q_OS_WIN
    return clean(reported).compare(clean(home), Qt::CaseInsensitive) == 0;
#else
    return clean(reported) == clean(home);
#endif
}

// Plain words for a field of the account principal.
QString field_words(const QString& key) {
    if (key == QStringLiteral("email")) return QStringLiteral("e-mail");
    if (key == QStringLiteral("organization")) return QStringLiteral("organisation");
    if (key == QStringLiteral("authMethod")) return QStringLiteral("sign-in method");
    if (key == QStringLiteral("apiKeySource")) return QStringLiteral("key source");
    if (key == QStringLiteral("tokenSource")) return QStringLiteral("token source");
    return key;
}

// Only Anthropic's sign-in pages are offered to the user.
bool sign_in_url(const QString& text) {
    const QUrl url(text, QUrl::StrictMode);
    if (!url.isValid() || url.scheme() != QStringLiteral("https") || !url.userInfo().isEmpty()) return false;
    const auto host = url.host().toLower();
    for (const auto& domain :
         {QStringLiteral("claude.ai"), QStringLiteral("claude.com"), QStringLiteral("anthropic.com")})
        if (host == domain || host.endsWith(u'.' + domain)) return true;
    return false;
}

}  // namespace

QString claude_managed_settings() {
    // Existence only: edi never reads what an organisation's policy says (ADR-0108 §4, managed settings).
#if defined(Q_OS_WIN)
    for (const auto& root : {QStringLiteral("HKEY_LOCAL_MACHINE"), QStringLiteral("HKEY_CURRENT_USER")}) {
        const QSettings policy(root + QStringLiteral("\\SOFTWARE\\Policies\\ClaudeCode"), QSettings::Registry64Format);
        if (policy.contains(QStringLiteral("Settings"))) return QStringLiteral("policy");
    }
    const auto folder = QDir(qEnvironmentVariable("ProgramFiles", QStringLiteral("C:\\Program Files")))
                            .filePath(QStringLiteral("ClaudeCode"));
#elif defined(Q_OS_MACOS)
    // The documented com.anthropic.claudecode domain, as macOS stores a configuration profile's managed preferences.
    const auto domain = QStringLiteral("com.anthropic.claudecode.plist");
    const QString managed = QStringLiteral("/Library/Managed Preferences/");
    if (QFileInfo::exists(managed + domain) ||
        QFileInfo::exists(managed + qEnvironmentVariable("USER") + u'/' + domain))
        return QStringLiteral("policy");
    const auto folder = QStringLiteral("/Library/Application Support/ClaudeCode");
#else
    const auto folder = QStringLiteral("/etc/claude-code");
#endif
    if (QFileInfo::exists(QDir(folder).filePath(QStringLiteral("managed-settings.json"))) ||
        QFileInfo::exists(QDir(folder).filePath(QStringLiteral("managed-settings.d"))))
        return QStringLiteral("file");
    return {};
}

namespace {

// A sorted, comma-separated list for an error message; "none" when empty.
QString listed(QStringList names) {
    names.sort();
    return names.isEmpty() ? QStringLiteral("none") : names.join(QStringLiteral(", "));
}

QString strip_terminal_codes(QString text) {
    static const QRegularExpression codes(QStringLiteral("\x1b\\[[0-9;?]*[A-Za-z]|\x1b\\][^\x07]*\x07|\r"));
    return text.remove(codes);
}

QString last_line(const QString& text) {
    const auto lines = strip_terminal_codes(text).split(u'\n', Qt::SkipEmptyParts);
    for (auto it = lines.crbegin(); it != lines.crend(); ++it)
        if (!it->trimmed().isEmpty()) return it->trimmed();
    return {};
}

// Plain words for the assistant message `error` values the SDK reference lists.
QString error_words(const QString& error) {
    if (error == QStringLiteral("authentication_failed"))
        return QStringLiteral("Claude is signed out for this account. Sign in again.");
    if (error == QStringLiteral("oauth_org_not_allowed"))
        return QStringLiteral("This Claude account's organisation does not allow this sign-in.");
    if (error == QStringLiteral("account_on_hold")) return QStringLiteral("This Claude account is on hold.");
    if (error == QStringLiteral("billing_error"))
        return QStringLiteral("Claude reported a billing problem for this account.");
    if (error == QStringLiteral("rate_limit")) return QStringLiteral("Claude's usage limit is reached.");
    if (error == QStringLiteral("overloaded")) return QStringLiteral("Claude is overloaded. Try again later.");
    if (error == QStringLiteral("model_not_found")) return QStringLiteral("Claude does not offer the chosen model.");
    return {};
}

}  // namespace

QProcessEnvironment claude_runtime_environment(const QProcessEnvironment& app, const QString& home,
                                               quint64 toolTimeoutMs) {
    auto environment = app;
    for (const auto name : claude_removed_environment)
        environment.remove(QString::fromLatin1(name.data(), static_cast<qsizetype>(name.size())));
    environment.insert(QStringLiteral("CLAUDE_CONFIG_DIR"), QDir::toNativeSeparators(home));
    environment.insert(QStringLiteral("DISABLE_UPDATES"), QStringLiteral("1"));
    environment.insert(QStringLiteral("MCP_PROTOCOL_NEGOTIATION"), QStringLiteral("legacy"));
    if (toolTimeoutMs > 0) environment.insert(QStringLiteral("MCP_TOOL_TIMEOUT"), QString::number(toolTimeoutMs));
    return environment;
}

QStringList claude_runtime_arguments(const QString& workspace, const QString& model, const QString& effort,
                                     const QString& sessionId, bool resume) {
    QStringList arguments{QStringLiteral("-p"),
                          QStringLiteral("--input-format"), QStringLiteral("stream-json"),
                          QStringLiteral("--output-format"), QStringLiteral("stream-json"),
                          QStringLiteral("--verbose"),
                          QStringLiteral("--include-partial-messages"),
                          QStringLiteral("--mcp-config"), edi_path(workspace, QStringLiteral("claude-mcp.json")),
                          QStringLiteral("--strict-mcp-config"),
                          QStringLiteral("--tools"), skill_tool,
                          QStringLiteral("--allowedTools"), QStringLiteral("mcp__edi__*,Skill"),
                          QStringLiteral("--setting-sources"), QStringLiteral("local"),
                          QStringLiteral("--plugin-dir"), edi_path(workspace, QStringLiteral("claude-plugin"))};
    if (!model.isEmpty()) arguments << QStringLiteral("--model") << model;
    if (!effort.isEmpty()) arguments << QStringLiteral("--effort") << effort;
    arguments << (resume ? QStringLiteral("--resume") : QStringLiteral("--session-id")) << sessionId;
    arguments << QStringLiteral("--append-system-prompt-file")
              << edi_path(workspace, QStringLiteral("instructions.md"));
    // A resumed thread reads edi's current instructions and skills.
    arguments << QStringLiteral("--system-prompt-snapshot") << QStringLiteral("off");
    return arguments;
}

ClaudeSession::ClaudeSession(QObject* parent) : AssistantRuntimeSession(parent) {
    readback_timer_.setSingleShot(true);
    connect(&readback_timer_, &QTimer::timeout, this, [this] {
        if (!process_ || readbacks_done_) return;
        // No input is ever written before `system/init`, so a runtime that never sends it cannot be used.
        startFailed(initialize_passed_ && !init_verified_
                        ? QStringLiteral("Claude did not report its tools within %1 seconds.").arg(readback_ms / 1000)
                        : QStringLiteral("Claude did not finish starting within %1 seconds.").arg(readback_ms / 1000),
                    AssistantProvider::FailureKind::OperationDeadline);
    });
}

ClaudeSession::~ClaudeSession() {
    retire();
    for (const auto& process : {status_, login_, logout_})
        if (process) {
            process->disconnect(this);
            process->kill();
        }
}

bool ClaudeSession::start(const AssistantRuntimeLaunch& launch) {
    retire();
    launch_ = launch;
    expected_tools_ = launch.expectedTools;
    session_id_.clear();
    model_.clear();
    effort_.clear();
    auth_method_.clear();
    usage_.clear();
    usage_status_ = {};
    const auto refuse = [this](const QString& explanation) {
        emit failed(explanation, AssistantProvider::FailureKind::Other);
        return false;
    };
    if (launch.executable.isEmpty()) return refuse(QStringLiteral("Claude is not installed."));
    if (launch.guard.isEmpty()) return refuse(QStringLiteral("edi's assistant guard is missing."));
    if (launch.workspace.isEmpty() || !QFileInfo(launch.workspace).isDir())
        return refuse(QStringLiteral("edi's assistant workspace is missing."));
    // Claude's own default home is never used: every account has a home edi created.
    if (launch.account.home.isEmpty()) return refuse(QStringLiteral("This Claude account has no config home."));
    if (launch.toolServer.value(QStringLiteral("command")).toString().isEmpty())
        return refuse(QStringLiteral("edi's tool server is not set up."));
    // `--setting-sources local` would load this file, and with it hooks and other servers.
    if (QFileInfo::exists(QDir(launch.workspace).filePath(QStringLiteral(".claude/settings.local.json"))))
        return refuse(QStringLiteral("edi's assistant workspace holds .claude/settings.local.json, which Claude "
                                     "would load. Remove it and try again."));
    environment_ = claude_runtime_environment(launch.environment, launch.account.home, launch.toolTimeoutMs);
    QString problem;
    if (!prepareWorkspace(problem)) return refuse(problem);
    this->launch(Purpose::Probe, false);
    return true;
}

bool ClaudeSession::prepareWorkspace(QString& problem) {
    const QDir workspace(launch_.workspace);
    const auto base = workspace.filePath(QStringLiteral(".edi"));
    if (!QDir().mkpath(base)) {
        problem = QStringLiteral("edi could not prepare %1.").arg(QDir::toNativeSeparators(base));
        return false;
    }
    // Owner-only where the platform has modes; the files inside are owner-only on their own.
    QFile::setPermissions(base, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    const auto plugin = QDir(base).filePath(QStringLiteral("claude-plugin"));
    // A fresh copy each start, so a skill removed from the bundle does not linger.
    if (QFileInfo::exists(plugin) && !QDir(plugin).removeRecursively()) {
        problem = QStringLiteral("edi could not replace %1.").arg(QDir::toNativeSeparators(plugin));
        return false;
    }
    const auto manifest = QDir(plugin).filePath(QStringLiteral(".claude-plugin"));
    const QJsonObject plugin_json{{QStringLiteral("name"), edi_server},
                                  {QStringLiteral("description"), QStringLiteral("edi's bundled skills")}};
    if (!QDir().mkpath(manifest) ||
        !write_private(QDir(manifest).filePath(QStringLiteral("plugin.json")),
                       QJsonDocument(plugin_json).toJson(QJsonDocument::Indented))) {
        problem = QStringLiteral("edi could not write Claude's skill plugin.");
        return false;
    }
    for (const auto& id : launch_.skills) {
        if (!valid_skill_id(id)) {
            problem = QStringLiteral("The skill name %1 is not valid.").arg(id);
            return false;
        }
        if (!copy_skill(QDir(launch_.skillsDir).filePath(id),
                        QDir(plugin).filePath(QStringLiteral("skills/") + id), problem))
            return false;
    }
    const QJsonObject mcp{{QStringLiteral("mcpServers"), QJsonObject{{edi_server, launch_.toolServer}}}};
    if (!write_private(QDir(base).filePath(QStringLiteral("claude-mcp.json")),
                       QJsonDocument(mcp).toJson(QJsonDocument::Indented))) {
        problem = QStringLiteral("edi could not write Claude's tool server settings.");
        return false;
    }
    if (!write_private(QDir(base).filePath(QStringLiteral("instructions.md")), launch_.instructions.toUtf8())) {
        problem = QStringLiteral("edi could not write the assistant's instructions.");
        return false;
    }
    return true;
}

QProcess* ClaudeSession::runOneShot(const AssistantRuntimeLaunch& launch, const QProcessEnvironment& environment,
                                    const QStringList& arguments, int timeoutMs, QProcess::ProcessChannelMode mode,
                                    OneShotDone done) {
    auto* process = new QProcess(this);
    process->setProgram(launch.executable);
    process->setArguments(arguments);
    if (!launch.workspace.isEmpty()) process->setWorkingDirectory(launch.workspace);
    process->setProcessEnvironment(environment);
    process->setProcessChannelMode(mode);
    auto* timer = new QTimer(process);
    timer->setSingleShot(true);
    auto finish = [process, done](const QString& problem, bool timedOut) {
        if (process->property("ediDone").toBool()) return;
        process->setProperty("ediDone", true);
        done(*process, problem, timedOut);
        process->deleteLater();
    };
    connect(process, &QProcess::finished, this, [finish](int, QProcess::ExitStatus status) {
        finish(status == QProcess::NormalExit ? QString() : QStringLiteral("it stopped unexpectedly"), false);
    });
    connect(process, &QProcess::errorOccurred, this, [finish](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) finish(QStringLiteral("it could not be started"), false);
    });
    connect(timer, &QTimer::timeout, this, [process, finish, timeoutMs] {
        process->kill();
        finish(QStringLiteral("it did not finish within %1 seconds").arg(timeoutMs / 1000), true);
    });
    timer->start(timeoutMs);
    process->start();
    return process;
}

void ClaudeSession::launch(Purpose purpose, bool resume) {
    retireProcess();
    const auto generation = generation_;
    launching_ = true;
    purpose_ = purpose;
    managed_settings_ = claude_managed_settings();
    if (purpose == Purpose::Probe) {
        session_id_ = new_uuid();
        process_model_.clear();
        process_effort_.clear();
        process_used_ = false;
    } else {
        process_model_ = model_;
        process_effort_ = effort_;
        process_used_ = resume;
    }
    // JSON is the default output of `claude auth status`, with `authMethod` and `configDirectory` (CLI reference).
    // It runs with the turn process's environment, so it reports what that process will use.
    status_ = runOneShot(launch_, environment_, {QStringLiteral("auth"), QStringLiteral("status")}, status_ms,
                         QProcess::SeparateChannels, [this, generation, resume](
                                                         QProcess& process, const QString& problem, bool timedOut) {
        if (generation != generation_) return;
        if (!problem.isEmpty()) {
            startFailed(QStringLiteral("Claude could not report its sign-in: %1.").arg(problem),
                        timedOut ? AssistantProvider::FailureKind::OperationDeadline
                                 : AssistantProvider::FailureKind::Other);
            return;
        }
        QJsonParseError error{};
        const auto document = QJsonDocument::fromJson(process.readAllStandardOutput().trimmed(), &error);
        const auto status = document.object();
        const auto method = status.value(QStringLiteral("authMethod")).toString();
        if (error.error != QJsonParseError::NoError || !document.isObject() ||
            !status.value(QStringLiteral("authMethod")).isString()) {
            startFailed(QStringLiteral("Claude reported its sign-in in a form edi does not read."));
            return;
        }
        // Any method the binary offers is accepted; only "none" is signed out.
        if (method.isEmpty() || method == QStringLiteral("none")) {
            retireProcess();
            queued_.clear();
            emit accountRefused(QStringLiteral("Claude is not signed in for this account."), true);
            return;
        }
        const auto folder = status.value(QStringLiteral("configDirectory")).toString();
        if (!same_folder(folder, launch_.account.home)) {
            retireProcess();
            queued_.clear();
            emit accountRefused(folder.isEmpty() ? QStringLiteral("Claude did not report which folder it uses.")
                                                 : QStringLiteral("Claude uses %1, not this account's folder.")
                                                       .arg(QDir::toNativeSeparators(folder)),
                                false);
            return;
        }
        // Only sign-in and the folder are decided here; the identity comes from the turn process itself.
        auth_method_ = method;
        spawn(resume, generation);
    });
}

void ClaudeSession::spawn(bool resume, quint64 generation) {
    launching_ = false;
    auto* process = new AssistantProcess(this);
    process_ = process;
    connect(process, &AssistantProcess::started, this, [this, generation] {
        if (generation == generation_) control(QStringLiteral("initialize"));
    });
    connect(process, &AssistantProcess::record, this, [this, generation](const QJsonObject& record) {
        if (generation == generation_) receive(record);
    });
    connect(process, &AssistantProcess::failed, this,
            [this, generation](const QString& explanation, AssistantProvider::FailureKind kind) {
                if (generation != generation_) return;
                if (!readbacks_done_) {
                    startFailed(explanation, kind);
                    return;
                }
                retireProcess();
                emit failed(explanation, kind);
            });
    readback_timer_.start(readback_ms);
    const auto arguments =
        claude_runtime_arguments(launch_.workspace, process_model_, process_effort_, session_id_, resume);
    if (!process->start(launch_.guard, launch_.executable, arguments, launch_.workspace, environment_) &&
        generation == generation_)
        startFailed(QStringLiteral("Claude could not be started."));
}

void ClaudeSession::retireProcess() {
    ++generation_;
    readback_timer_.stop();
    if (process_) {
        process_->disconnect(this);
        process_->retire();
        process_->deleteLater();
    }
    process_ = nullptr;
    if (status_) {
        status_->disconnect(this);
        status_->kill();
        status_->deleteLater();
    }
    launching_ = false;
    initialize_passed_ = init_verified_ = readbacks_done_ = false;
    requests_.clear();
    tools_.clear();
    account_info_ = {};
    api_key_source_.clear();
    capabilities_.clear();
    dropped_messages_.clear();
    dropping_.clear();
    turn_active_ = interrupted_ = false;
    streamed_items_.clear();
    streaming_item_.clear();
}

void ClaudeSession::retire() {
    retireProcess();
    queued_.clear();
    restart_pending_ = false;
}

void ClaudeSession::startFailed(const QString& explanation, AssistantProvider::FailureKind kind) {
    retireProcess();
    queued_.clear();
    emit failed(explanation, kind);
}

bool ClaudeSession::control(const QString& subtype, const QJsonObject& fields) {
    if (!process_) return false;
    // The SDK's control channel; its wire shape is not in the public docs, so this follows the Agent SDK's.
    const auto id = QStringLiteral("edi-%1").arg(++request_counter_);
    auto request = fields;
    request.insert(QStringLiteral("subtype"), subtype);
    requests_.insert(id, subtype);
    return process_->write({{QStringLiteral("type"), QStringLiteral("control_request")},
                            {QStringLiteral("request_id"), id},
                            {QStringLiteral("request"), request}});
}

void ClaudeSession::receive(const QJsonObject& record) {
    const auto type = record.value(QStringLiteral("type")).toString();
    if (type == QStringLiteral("control_response")) {
        controlResponse(record.value(QStringLiteral("response")).toObject());
        return;
    }
    if (type == QStringLiteral("control_request")) {
        // edi names no permission prompt tool, so nothing should ask; an answer keeps the runtime from waiting.
        process_->write({{QStringLiteral("type"), QStringLiteral("control_response")},
                         {QStringLiteral("response"),
                          QJsonObject{{QStringLiteral("subtype"), QStringLiteral("error")},
                                      {QStringLiteral("request_id"), record.value(QStringLiteral("request_id"))},
                                      {QStringLiteral("error"), QStringLiteral("edi does not answer this request")}}}});
        return;
    }
    if (type == QStringLiteral("system")) {
        if (record.value(QStringLiteral("subtype")).toString() == QStringLiteral("init")) systemInit(record);
        return;
    }
    const bool output = type == QStringLiteral("stream_event") || type == QStringLiteral("assistant") ||
                        type == QStringLiteral("result");
    if (output && !readbacks_done_) {
        startFailed(QStringLiteral("Claude answered before edi sent a message."));
        return;
    }
    if (output && dropRecord(record)) return;
    if (type == QStringLiteral("stream_event")) streamEvent(record);
    else if (type == QStringLiteral("assistant")) assistantMessage(record);
    else if (type == QStringLiteral("result")) result(record);
    else if (type == QStringLiteral("rate_limit_event")) rateLimit(record);
}

void ClaudeSession::controlResponse(const QJsonObject& response) {
    const auto subtype = requests_.take(response.value(QStringLiteral("request_id")).toString());
    if (subtype.isEmpty()) return;
    const bool success = response.value(QStringLiteral("subtype")).toString() == QStringLiteral("success");
    const auto error = response.value(QStringLiteral("error")).toString();
    if (subtype == QStringLiteral("initialize")) {
        if (!success)
            startFailed(QStringLiteral("Claude did not start the session: %1").arg(error));
        else
            initializeReply(response.value(QStringLiteral("response")).toObject());
    } else if (subtype == QStringLiteral("interrupt") && success) {
        const auto receipt = response.value(QStringLiteral("response")).toObject();
        for (const auto& id : receipt.value(QStringLiteral("still_queued")).toArray())
            if (!id.toString().isEmpty()) dropped_messages_.insert(id.toString());
    } else if (subtype == QStringLiteral("set_model") && !success) {
        emit failed(QStringLiteral("Claude did not accept the model: %1").arg(error),
                    AssistantProvider::FailureKind::Other);
    }
}

void ClaudeSession::initializeReply(const QJsonObject& reply) {
    account_info_ = reply.value(QStringLiteral("account")).toObject();
    QSet<QString> commands;
    for (const auto& value : reply.value(QStringLiteral("commands")).toArray()) {
        auto name = value.toObject().value(QStringLiteral("name")).toString();
        if (name.startsWith(u'/')) name.remove(0, 1);
        commands.insert(name);
    }
    // Plugin skills are namespaced under the plugin's name (plugins reference).
    for (const auto& id : launch_.skills)
        if (!commands.contains(QStringLiteral("edi:") + id)) {
            startFailed(QStringLiteral("Claude did not load edi's skill %1.").arg(id));
            return;
        }
    QJsonArray models;
    for (const auto& value : reply.value(QStringLiteral("models")).toArray()) {
        const auto model = value.toObject();
        const auto id = model.value(QStringLiteral("value")).toString();
        if (id.isEmpty()) continue;
        QJsonArray efforts;
        for (const auto& effort : model.value(QStringLiteral("supportedEffortLevels")).toArray())
            if (effort.isString()) efforts.append(effort);
        const auto name = model.value(QStringLiteral("displayName")).toString();
        models.append(QJsonObject{{QStringLiteral("id"), id},
                                  {QStringLiteral("displayName"), name.isEmpty() ? id : name},
                                  {QStringLiteral("efforts"), efforts},
                                  // Claude advertises no default effort; the view model then uses the provider's.
                                  {QStringLiteral("defaultEffort"), QString()}});
    }
    models_ = models;
    initialize_passed_ = true;
    maybeReadbacksDone();
}

void ClaudeSession::systemInit(const QJsonObject& init) {
    // The process's effective tools must be exactly the skill loader and edi's listed tools.
    QStringList tools;
    for (const auto& value : init.value(QStringLiteral("tools")).toArray()) tools.append(value.toString());
    QStringList expected{skill_tool};
    for (const auto& name : expected_tools_) expected.append(edi_tool_prefix + name);
    QString problem;
    if (expected_tools_.isEmpty()) problem = QStringLiteral("edi has no tool list to compare Claude's tools with.");
    else if (QSet<QString>(tools.cbegin(), tools.cend()) != QSet<QString>(expected.cbegin(), expected.cend()) ||
             tools.size() != expected.size())
        problem = QStringLiteral("Claude's tools differ from edi's. Expected: %1. Observed: %2.")
                      .arg(listed(expected), listed(tools));
    if (problem.isEmpty()) {
        QStringList servers;
        for (const auto& value : init.value(QStringLiteral("mcp_servers")).toArray()) {
            const auto server = value.toObject();
            servers.append(QStringLiteral("%1 (%2)").arg(server.value(QStringLiteral("name")).toString(),
                                                         server.value(QStringLiteral("status")).toString()));
        }
        const QStringList wanted{QStringLiteral("edi (connected)")};
        if (servers != wanted)
            problem = QStringLiteral("Claude's tool servers differ from edi's. Expected: %1. Observed: %2.")
                          .arg(listed(wanted), listed(servers));
    }
    if (problem.isEmpty()) {
        const auto plugin_dir = QDir(launch_.workspace).filePath(QStringLiteral(".edi/claude-plugin"));
        QStringList plugins;
        bool plugin_ours = true;
        for (const auto& value : init.value(QStringLiteral("plugins")).toArray()) {
            const auto plugin = value.toObject();
            plugins.append(plugin.value(QStringLiteral("name")).toString());
            const auto path = plugin.value(QStringLiteral("path")).toString();
            if (!path.isEmpty() && !same_folder(path, plugin_dir)) plugin_ours = false;
        }
        const auto errors = init.value(QStringLiteral("plugin_errors")).toArray();
        if (plugins != QStringList{edi_server} || !plugin_ours || !errors.isEmpty())
            problem = QStringLiteral("Claude's plugins differ from edi's. Expected: edi. Observed: %1%2.")
                          .arg(listed(plugins), errors.isEmpty() ? QString() : QStringLiteral(", with load errors"));
    }
    if (problem.isEmpty()) {
        QSet<QString> skills;
        for (const auto& value : init.value(QStringLiteral("skills")).toArray()) skills.insert(value.toString());
        QStringList missing;
        for (const auto& id : launch_.skills)
            if (!skills.contains(QStringLiteral("edi:") + id)) missing.append(QStringLiteral("edi:") + id);
        if (!missing.isEmpty())
            problem = QStringLiteral("Claude did not load edi's skills: %1.").arg(missing.join(QStringLiteral(", ")));
    }
    if (!problem.isEmpty()) {
        if (!readbacks_done_) {
            startFailed(problem);
        } else {
            retireProcess();
            emit failed(problem, AssistantProvider::FailureKind::Other);
        }
        return;
    }
    tools_ = tools;
    api_key_source_ = init.value(QStringLiteral("apiKeySource")).toString();
    capabilities_.clear();
    for (const auto& value : init.value(QStringLiteral("capabilities")).toArray())
        capabilities_.append(value.toString());
    init_verified_ = true;
    maybeReadbacksDone();
}

void ClaudeSession::maybeReadbacksDone() {
    if (readbacks_done_ || !initialize_passed_ || !init_verified_) return;
    const auto text = [this](const char* key) { return account_info_.value(QLatin1String(key)).toString(); };
    identity_ = {{QStringLiteral("email"), text("email")},
                 {QStringLiteral("organization"), text("organization")},
                 {QStringLiteral("plan"), text("subscriptionType")},
                 {QStringLiteral("authMethod"), auth_method_},
                 {QStringLiteral("apiKeySource"), api_key_source_},
                 {QStringLiteral("tokenSource"), text("tokenSource")},
                 {QStringLiteral("host"), launch_.account.host}};
    if (!managed_settings_.isEmpty()) identity_.insert(QStringLiteral("managedSettings"), managed_settings_);
    // Every field the record holds must be reported, and the same, by this process.
    for (auto it = principal_.constBegin(); it != principal_.constEnd(); ++it) {
        const auto recorded = it.value().toString();
        if (recorded.isEmpty()) continue;
        const auto observed = identity_.value(it.key()).toString();
        const bool same = it.key() == QStringLiteral("email")
                              ? observed.compare(recorded, Qt::CaseInsensitive) == 0
                              : observed == recorded;
        if (same) continue;
        retireProcess();
        queued_.clear();
        emit accountRefused(observed.isEmpty()
                                ? QStringLiteral("Claude did not report the %1 this account's record holds (%2).")
                                      .arg(field_words(it.key()), recorded)
                                : QStringLiteral("Claude reports the %1 %2 for this account, not %3.")
                                      .arg(field_words(it.key()), observed, recorded),
                            false);
        return;
    }
    readbacks_done_ = true;
    readback_timer_.stop();
    // A model chosen while this process was starting.
    if (!model_.isEmpty() && model_ != process_model_ && purpose_ != Purpose::Probe) {
        control(QStringLiteral("set_model"), {{QStringLiteral("model"), model_}});
        process_model_ = model_;
    }
    switch (purpose_) {
    case Purpose::Probe:
        emit modelsListed(models_);
        emit ready(identity_, tools_, launch_.skills);
        break;
    case Purpose::Thread:
        emit threadOpened(session_id_);
        flushQueue();
        break;
    case Purpose::Restart:
        flushQueue();
        break;
    }
}

void ClaudeSession::openThread(const QString& resumeId, const QString& model, const QString& effort) {
    if (launch_.executable.isEmpty()) {
        emit failed(QStringLiteral("Claude has not been started."), AssistantProvider::FailureKind::Other);
        return;
    }
    model_ = model;
    effort_ = effort;
    restart_pending_ = false;
    queued_.clear();
    if (!resumeId.isEmpty() && QUuid::fromString(resumeId).isNull()) {
        emit failed(QStringLiteral("This Claude conversation has no valid id."), AssistantProvider::FailureKind::Other);
        return;
    }
    // Every thread gets its own process, so its readbacks are the ones for the process that takes its input.
    session_id_ = resumeId.isEmpty() ? new_uuid() : resumeId;
    launch(Purpose::Thread, !resumeId.isEmpty());
}

void ClaudeSession::sendMessage(const QString& thread, const QString& clientMessageId, const QString& text) {
    if (thread.isEmpty() || thread != session_id_ || (!process_ && !launching_) || purpose_ == Purpose::Probe) {
        emit failed(QStringLiteral("This Claude conversation is not open."), AssistantProvider::FailureKind::Other);
        return;
    }
    const Message message{clientMessageId, text};
    if (!turn_active_ && restart_pending_) {
        // An effort change takes a new process; the session goes on with `--resume` once it has history. Reusing
        // `--session-id` for a session with no message yet is not covered by the CLI reference.
        restart_pending_ = false;
        queued_.push_back(message);
        launch(Purpose::Restart, process_used_);
        if (process_ || launching_) beginTurn(clientMessageId);
        return;
    }
    if (!turn_active_) beginTurn(clientMessageId);
    if (!readbacks_done_) {
        queued_.push_back(message);
        return;
    }
    writeUser(message);
}

bool ClaudeSession::writeUser(const Message& message) {
    // One stream-json user message; its uuid is edi's client message id. The header block keeps a message that
    // starts with "/" from running as one of the binary's commands.
    const QJsonArray content{
        QJsonObject{{QStringLiteral("type"), QStringLiteral("text")},
                    {QStringLiteral("text"), QStringLiteral("Message from the edi user:")}},
        QJsonObject{{QStringLiteral("type"), QStringLiteral("text")}, {QStringLiteral("text"), message.text}}};
    const QJsonObject record{
        {QStringLiteral("type"), QStringLiteral("user")},
        {QStringLiteral("message"),
         QJsonObject{{QStringLiteral("role"), QStringLiteral("user")}, {QStringLiteral("content"), content}}},
        {QStringLiteral("parent_tool_use_id"), QJsonValue::Null},
        {QStringLiteral("session_id"), session_id_},
        {QStringLiteral("uuid"), message.id}};
    if (!process_ || !process_->write(record)) {
        retireProcess();
        emit failed(QStringLiteral("Claude did not take the message."), AssistantProvider::FailureKind::Other);
        return false;
    }
    process_used_ = true;
    return true;
}

void ClaudeSession::flushQueue() {
    while (!queued_.empty() && process_) {
        const auto message = queued_.front();
        queued_.pop_front();
        if (!writeUser(message)) return;
    }
}

void ClaudeSession::cancelTurn(const QString& thread) {
    if (thread != session_id_ || !turn_active_) return;
    if (!readbacks_done_) {
        // The message is still waiting for its process; nothing has reached Claude.
        queued_.clear();
        turn_active_ = false;
        emit turnFinished(session_id_, turn_id_, QStringLiteral("interrupted"), {});
        return;
    }
    interrupted_ = true;
    // Without the capability a steer sent before Stop still runs; the receipt names it and its turn is dropped.
    if (capabilities_.contains(QStringLiteral("interrupt_cancel_queued_v1")))
        control(QStringLiteral("interrupt"), {{QStringLiteral("cancel_queued"), true}});
    else
        control(QStringLiteral("interrupt"));
}

void ClaudeSession::selectModel(const QString& thread, const QString& model, const QString& effort) {
    if (thread != session_id_) return;
    if (!model.isEmpty() && model != model_) {
        model_ = model;
        if (process_ && readbacks_done_) {
            control(QStringLiteral("set_model"), {{QStringLiteral("model"), model}});
            process_model_ = model;
        }
    }
    effort_ = effort;
    restart_pending_ = effort_ != process_effort_;
}

void ClaudeSession::beginTurn(const QString& id) {
    turn_active_ = true;
    interrupted_ = false;
    turn_id_ = id.isEmpty() ? new_uuid() : id;
    last_error_.clear();
    streamed_items_.clear();
    streaming_item_.clear();
    emit turnStarted(session_id_, turn_id_);
}

void ClaudeSession::streamEvent(const QJsonObject& record) {
    // Only the main conversation streams into the panel.
    if (!record.value(QStringLiteral("parent_tool_use_id")).isNull()) return;
    if (!turn_active_) beginTurn(record.value(QStringLiteral("user_message_uuid")).toString());
    const auto event = record.value(QStringLiteral("event")).toObject();
    const auto type = event.value(QStringLiteral("type")).toString();
    if (type == QStringLiteral("message_start")) {
        message_id_ = event.value(QStringLiteral("message")).toObject().value(QStringLiteral("id")).toString();
    } else if (type == QStringLiteral("content_block_start")) {
        streaming_item_.clear();
        if (event.value(QStringLiteral("content_block")).toObject().value(QStringLiteral("type")).toString() ==
            QStringLiteral("text")) {
            streaming_item_ = QStringLiteral("%1-%2").arg(message_id_).arg(++item_counter_);
            streamed_items_.push_back(streaming_item_);
        }
    } else if (type == QStringLiteral("content_block_delta")) {
        const auto delta = event.value(QStringLiteral("delta")).toObject();
        if (delta.value(QStringLiteral("type")).toString() != QStringLiteral("text_delta")) return;
        if (streaming_item_.isEmpty()) {
            streaming_item_ = QStringLiteral("%1-%2").arg(message_id_).arg(++item_counter_);
            streamed_items_.push_back(streaming_item_);
        }
        emit textDelta(session_id_, turn_id_, streaming_item_, delta.value(QStringLiteral("text")).toString());
    } else if (type == QStringLiteral("content_block_stop")) {
        streaming_item_.clear();
    }
}

void ClaudeSession::assistantMessage(const QJsonObject& record) {
    const bool top_level = record.value(QStringLiteral("parent_tool_use_id")).isNull();
    if (!turn_active_) beginTurn(record.value(QStringLiteral("user_message_uuid")).toString());
    // An assistant message with `error` carries the runtime's own text about the failure; `result` reports it.
    if (record.contains(QStringLiteral("error"))) {
        last_error_ = record.value(QStringLiteral("error")).toString();
        if (last_error_.isEmpty()) last_error_ = QStringLiteral("unknown");
        return;
    }
    const auto message = record.value(QStringLiteral("message")).toObject();
    const auto id = message.value(QStringLiteral("id")).toString();
    for (const auto& value : message.value(QStringLiteral("content")).toArray()) {
        const auto block = value.toObject();
        const auto type = block.value(QStringLiteral("type")).toString();
        if (type == QStringLiteral("text") && top_level) {
            QString item;
            if (!streamed_items_.empty()) {
                item = streamed_items_.front();
                streamed_items_.pop_front();
            } else {
                item = QStringLiteral("%1-%2").arg(id).arg(++item_counter_);
            }
            emit itemCompleted(session_id_, turn_id_,
                               {{QStringLiteral("type"), QStringLiteral("agentMessage")},
                                {QStringLiteral("id"), item},
                                {QStringLiteral("text"), block.value(QStringLiteral("text")).toString()}});
        } else if (type == QStringLiteral("thinking") && top_level) {
            // Claude 4 and later models return summarized thinking.
            const auto text = block.value(QStringLiteral("thinking")).toString();
            if (!text.trimmed().isEmpty())
                emit itemCompleted(session_id_, turn_id_,
                                   {{QStringLiteral("type"), QStringLiteral("reasoning")},
                                    {QStringLiteral("id"), QStringLiteral("%1-%2").arg(id).arg(++item_counter_)},
                                    {QStringLiteral("text"), text}});
        } else if (type == QStringLiteral("tool_use")) {
            const auto name = block.value(QStringLiteral("name")).toString();
            if (allowed_tool(name))
                emit toolUse(session_id_, turn_id_, name, block.value(QStringLiteral("input")).toObject(),
                             block.value(QStringLiteral("id")).toString());
            else
                emit foreignTool(session_id_, turn_id_, name);
        } else if (type.endsWith(QStringLiteral("tool_use"))) {
            // A server or connector tool runs outside edi's tool server.
            const auto name = block.value(QStringLiteral("name")).toString();
            emit foreignTool(session_id_, turn_id_, name.isEmpty() ? type : name);
        }
    }
}

void ClaudeSession::result(const QJsonObject& record) {
    const bool is_error = record.value(QStringLiteral("is_error")).toBool();
    if (!turn_active_) {
        if (!is_error) return;
        beginTurn(record.value(QStringLiteral("user_message_uuid")).toString());
    }
    const auto subtype = record.value(QStringLiteral("subtype")).toString();
    QString status = QStringLiteral("completed");
    QJsonObject error;
    if (interrupted_) {
        status = QStringLiteral("interrupted");
    } else if (is_error || subtype != QStringLiteral("success") || !last_error_.isEmpty()) {
        // A signed-out turn reports `success` with `is_error`, so `subtype` alone is not enough.
        status = QStringLiteral("failed");
        auto message = error_words(last_error_);
        if (message.isEmpty()) message = record.value(QStringLiteral("result")).toString().trimmed();
        if (message.isEmpty()) {
            QStringList errors;
            for (const auto& value : record.value(QStringLiteral("errors")).toArray())
                if (!value.toString().trimmed().isEmpty()) errors.append(value.toString().trimmed());
            message = errors.join(u'\n');
        }
        if (message.isEmpty()) message = QStringLiteral("Claude reported an error.");
        error.insert(QStringLiteral("message"), message);
        if (last_error_ == QStringLiteral("authentication_failed")) error.insert(QStringLiteral("signedOut"), true);
    }
    turn_active_ = interrupted_ = false;
    last_error_.clear();
    streamed_items_.clear();
    streaming_item_.clear();
    emit turnFinished(session_id_, turn_id_, status, error);
}

bool ClaudeSession::dropRecord(const QJsonObject& record) {
    const auto type = record.value(QStringLiteral("type")).toString();
    if (dropping_.isEmpty()) {
        if (turn_active_ || dropped_messages_.isEmpty()) return false;
        QStringList ids{record.value(QStringLiteral("user_message_uuid")).toString()};
        for (const auto& id : record.value(QStringLiteral("user_message_uuids")).toArray()) ids.append(id.toString());
        for (const auto& id : ids)
            if (dropped_messages_.contains(id)) dropping_ = id;
        if (dropping_.isEmpty()) return false;
        control(QStringLiteral("interrupt"));
    }
    if (type == QStringLiteral("assistant")) {
        for (const auto& value :
             record.value(QStringLiteral("message")).toObject().value(QStringLiteral("content")).toArray()) {
            const auto block = value.toObject();
            const auto name = block.value(QStringLiteral("name")).toString();
            if (block.value(QStringLiteral("type")).toString().endsWith(QStringLiteral("tool_use")) &&
                !allowed_tool(name)) {
                retireProcess();
                emit failed(QStringLiteral("Claude used a tool edi does not allow: %1.").arg(name),
                            AssistantProvider::FailureKind::Other);
                return true;
            }
        }
    }
    if (type == QStringLiteral("result")) {
        dropped_messages_.remove(dropping_);
        dropping_.clear();
    }
    return true;
}

void ClaudeSession::rateLimit(const QJsonObject& record) {
    // A status signal sent when a limit's status changes. `rate_limit_type` and `utilization` are not in the SDK
    // reference's type; ADR-0108 names them, and the camel-case spelling of the other fields is accepted too.
    const auto info = record.value(QStringLiteral("rate_limit_info")).toObject();
    const auto field = [&info](const char* snake, const char* camel) {
        const auto value = info.value(QLatin1String(snake));
        return value.isUndefined() ? info.value(QLatin1String(camel)) : value;
    };
    const auto kind = field("rate_limit_type", "rateLimitType").toString();
    QString window;
    if (kind == QStringLiteral("five_hour")) window = QStringLiteral("session");
    else if (kind == QStringLiteral("seven_day")) window = QStringLiteral("weekly");
    qint64 resets_at = -1;
    const auto resets = field("resets_at", "resetsAt");
    if (resets.isDouble() && resets.toDouble() > 0) {
        resets_at = static_cast<qint64>(resets.toDouble());
        if (resets_at > 100000000000LL) resets_at /= 1000;  // milliseconds
    }
    bool changed = false;
    const auto status = info.value(QStringLiteral("status")).toString();
    if (status == QStringLiteral("allowed_warning") || status == QStringLiteral("rejected")) {
        QJsonObject notice{{QStringLiteral("status"), status}};
        if (!window.isEmpty()) notice.insert(QStringLiteral("window"), window);
        if (resets_at >= 0) notice.insert(QStringLiteral("resetsAt"), resets_at);
        usage_status_ = notice;
        changed = true;
    } else if (!usage_status_.isEmpty()) {
        usage_status_ = {};
        changed = true;
    }
    const auto utilization = info.value(QStringLiteral("utilization"));
    if (!window.isEmpty() && utilization.isDouble()) {
        // Undocumented scale: a value up to 1 is read as a fraction, a larger one as a percentage.
        const auto used = utilization.toDouble();
        usage_.insert(window, {qBound(0, qRound(used <= 1.0 ? used * 100.0 : used), 100), resets_at});
        changed = true;
    }
    if (changed) emitUsage();
}

void ClaudeSession::emitUsage() {
    QJsonArray buckets;
    for (const auto& window : {QStringLiteral("session"), QStringLiteral("weekly")}) {
        if (!usage_.contains(window)) continue;
        const auto value = usage_.value(window);
        QJsonObject bucket{{QStringLiteral("window"), window}, {QStringLiteral("usedPercent"), value.usedPercent}};
        if (value.resetsAt >= 0) bucket.insert(QStringLiteral("resetsAt"), value.resetsAt);
        buckets.append(bucket);
    }
    QJsonObject snapshot{{QStringLiteral("available"), !buckets.isEmpty() || !usage_status_.isEmpty()},
                         {QStringLiteral("stale"), false},
                         {QStringLiteral("buckets"), buckets},
                         {QStringLiteral("observedAt"), QDateTime::currentSecsSinceEpoch()}};
    if (!usage_status_.isEmpty()) snapshot.insert(QStringLiteral("status"), usage_status_);
    emit usageChanged(snapshot);
}

void ClaudeSession::signIn(const AssistantRuntimeLaunch& launch) {
    if (login_) {
        login_->disconnect(this);
        login_->kill();
        login_->deleteLater();
    }
    if (launch.executable.isEmpty() || launch.account.home.isEmpty()) {
        emit signInFinished(false, QStringLiteral("Claude is not installed or this account has no config home."));
        return;
    }
    login_output_.clear();
    login_url_.clear();
    login_prompt_.clear();
    const auto environment =
        claude_runtime_environment(launch.environment, launch.account.home, launch.toolTimeoutMs);
    // No flag: the binary's login keeps every method it offers.
    login_ = runOneShot(launch, environment, {QStringLiteral("auth"), QStringLiteral("login")}, login_ms,
                        QProcess::MergedChannels, [this](QProcess& process, const QString& problem, bool) {
        login_output_ += QString::fromUtf8(process.readAll());
        if (!problem.isEmpty()) {
            emit signInFinished(false, QStringLiteral("Claude's sign-in stopped: %1.").arg(problem));
        } else if (process.exitCode() == 0) {
            emit signInFinished(true, {});
        } else {
            auto message = last_line(login_output_);
            if (message.isEmpty())
                message = QStringLiteral("Claude's sign-in did not finish (exit code %1).").arg(process.exitCode());
            emit signInFinished(false, message);
        }
        login_output_.clear();
    });
    connect(login_, &QProcess::readyRead, this, &ClaudeSession::loginOutput);
}

void ClaudeSession::loginOutput() {
    if (!login_) return;
    login_output_ += QString::fromUtf8(login_->readAll());
    if (login_output_.size() > login_output_cap) login_output_ = login_output_.right(login_output_cap);
    const auto text = strip_terminal_codes(login_output_);
    static const QRegularExpression url_pattern(QStringLiteral("https://[^\\s\"'<>]+"));
    QRegularExpressionMatch match;
    for (auto it = url_pattern.globalMatch(text); it.hasNext();) {
        const auto candidate = it.next();
        if (sign_in_url(candidate.captured())) {
            match = candidate;
            break;
        }
    }
    if (!match.hasMatch()) return;
    // A line after the URL that mentions a code is the binary asking for one; it may not end in a newline yet.
    QString prompt;
    for (const auto& line : text.mid(match.capturedEnd()).split(u'\n'))
        if (line.contains(QStringLiteral("code"), Qt::CaseInsensitive)) prompt = line.trimmed();
    const auto url = match.captured();
    if (url == login_url_ && prompt == login_prompt_) return;
    login_url_ = url;
    login_prompt_ = prompt;
    emit signInOpened(url, {}, prompt);
}

void ClaudeSession::answerSignIn(const QString& input) {
    // Only the sign-in process reads it; edi keeps no copy.
    if (login_ && login_->state() == QProcess::Running) login_->write(input.toUtf8() + '\n');
}

void ClaudeSession::cancelSignIn() {
    if (!login_) return;
    login_->disconnect(this);
    login_->kill();
    login_->deleteLater();
    login_output_.clear();
    emit signInFinished(false, QStringLiteral("Sign-in was cancelled."));
}

void ClaudeSession::signOut(const AssistantRuntimeLaunch& launch) {
    retire();
    if (logout_) {
        logout_->disconnect(this);
        logout_->kill();
        logout_->deleteLater();
    }
    if (launch.executable.isEmpty() || launch.account.home.isEmpty()) {
        emit failed(QStringLiteral("Claude is not installed or this account has no config home."),
                    AssistantProvider::FailureKind::Other);
        return;
    }
    const auto environment =
        claude_runtime_environment(launch.environment, launch.account.home, launch.toolTimeoutMs);
    logout_ = runOneShot(launch, environment, {QStringLiteral("auth"), QStringLiteral("logout")}, logout_ms,
                         QProcess::MergedChannels, [this](QProcess& process, const QString& problem, bool timedOut) {
        if (problem.isEmpty() && process.exitCode() == 0) {
            emit signedOut();
            return;
        }
        auto detail = problem;
        if (detail.isEmpty()) detail = last_line(QString::fromUtf8(process.readAll()));
        if (detail.isEmpty()) detail = QStringLiteral("exit code %1").arg(process.exitCode());
        emit failed(QStringLiteral("Claude could not sign out: %1.").arg(detail),
                    timedOut ? AssistantProvider::FailureKind::OperationDeadline
                             : AssistantProvider::FailureKind::Other);
    });
}

}  // namespace edi_app

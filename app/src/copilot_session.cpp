// SPDX-License-Identifier: BSD-3-Clause
#include "copilot_session.hpp"
#include "engine_setup.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QUrl>
#include <utility>
#include "assistant_native_tools.hpp"
#include "edi/assistant_limits.hpp"

namespace edi_app {
namespace {

constexpr int readback_ms = 60'000;
constexpr int login_ms = 15 * 60'000;  // a device code lives 15 minutes
constexpr int login_answer_ms = 5 * 60'000;
constexpr int auth_required = -32000;  // ACP: authentication required
constexpr int method_not_found = -32601;
// Each prompt is one text block starting with this header, so a message starting with `/` never runs a CLI command.
const QString prompt_header = QStringLiteral("Message from the edi user:");

const QString edi_prefix = QStringLiteral("edi-");
// The CLI's skill loader (`skill`) stays available: Copilot reads the bundled skills through it (ADR-0108 §6, §7).
const QString skill_tool = QStringLiteral("skill");

QString normalizedHost(QString host) {
    host = host.trimmed().toLower();
    if (host.startsWith(QStringLiteral("https://"))) host = host.mid(8);
    while (host.endsWith(QLatin1Char('/'))) host.chop(1);
    return host.isEmpty() ? QStringLiteral("github.com") : host;
}

QString errorText(const QJsonObject& error) {
    auto message = error.value(QStringLiteral("message")).toString().trimmed();
    const auto data = error.value(QStringLiteral("data"));
    if (data.isString() && !data.toString().trimmed().isEmpty() && data.toString() != message)
        message += (message.isEmpty() ? QString() : QStringLiteral(": ")) + data.toString().trimmed();
    return message;
}

bool writeOwnerOnly(const QString& path, const QByteArray& bytes) {
    constexpr auto owner = QFileDevice::ReadOwner | QFileDevice::WriteOwner;
    QFile file(path);
    if (file.exists() && !file.setPermissions(owner)) return false;
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate, owner)) return false;
    const bool written = file.write(bytes) == bytes.size();
    file.close();
    return written && file.error() == QFileDevice::NoError && file.setPermissions(owner);
}

// The MCP stdio entry's env, as an object of strings; an array of {name, value} is taken too.
std::optional<QJsonObject> serverEnvironment(const QJsonValue& value) {
    QJsonObject env;
    if (value.isUndefined() || value.isNull()) return env;
    if (value.isObject()) env = value.toObject();
    else if (value.isArray()) {
        for (const auto& item : value.toArray())
            env.insert(item.toObject().value(QStringLiteral("name")).toString(),
                       item.toObject().value(QStringLiteral("value")));
    } else return std::nullopt;
    for (auto it = env.begin(); it != env.end(); ++it) {
        // The CLI expands `$VAR` in config values and documents no escape, so a `$` would change the value.
        if (it.key().isEmpty() || !it.value().isString() || it.value().toString().contains(QLatin1Char('$')))
            return std::nullopt;
    }
    return env;
}

// Values of a select option, groups flattened.
QJsonArray selectValues(const QJsonObject& option) {
    QJsonArray values;
    for (const auto& entry : option.value(QStringLiteral("options")).toArray()) {
        const auto object = entry.toObject();
        if (object.contains(QStringLiteral("group"))) {
            for (const auto& inner : object.value(QStringLiteral("options")).toArray()) values.append(inner);
        } else values.append(object);
    }
    return values;
}

QJsonObject optionOf(const QJsonArray& configOptions, const QString& category) {
    for (const auto& value : configOptions) {
        const auto option = value.toObject();
        if (option.value(QStringLiteral("category")).toString() == category &&
            option.value(QStringLiteral("type")).toString() == QStringLiteral("select"))
            return option;
    }
    return {};
}

QString stripTerminal(QString text) {
    static const QRegularExpression csi(QStringLiteral("\x1B\\[[0-9;?]*[ -/]*[@-~]"));
    static const QRegularExpression osc(QStringLiteral("\x1B\\][^\x07\x1B]*(\x07|\x1B\\\\)"));
    text.remove(osc);
    text.remove(csi);
    text.remove(QLatin1Char('\r'));
    return text;
}

}  // namespace

CopilotSession::CopilotSession(QString accountsRoot, QObject* parent)
    : AssistantRuntimeSession(parent), accounts_root_(std::move(accountsRoot)) {
    if (accounts_root_.isEmpty()) {
        const auto base = edi_app::app_local_data_location();
        if (!base.isEmpty()) accounts_root_ = base + QStringLiteral("/assistant/accounts");
    }
    if (!accounts_root_.isEmpty()) accounts_root_ = QDir::cleanPath(accounts_root_);
    readback_timer_.setSingleShot(true);
    login_timer_.setSingleShot(true);
    login_answer_timer_.setSingleShot(true);
    connect(&readback_timer_, &QTimer::timeout, this, &CopilotSession::readbackExpired);
    connect(&login_timer_, &QTimer::timeout, this, [this] {
        if (login_) login_->kill();
        endSignIn(false, QStringLiteral("The GitHub sign-in timed out."));
    });
    connect(&login_answer_timer_, &QTimer::timeout, this, [this] { answerSignIn(QStringLiteral("no")); });
    connect(&process_, &AssistantProcess::started, this, [this] {
        // No fs and no terminal: the agent gets no file or command access through edi.
        const QJsonObject capabilities{{"session", QJsonObject{{"notices", QJsonObject{}}}}};
        request(QStringLiteral("initialize"),
                {{"protocolVersion", 1},
                 {"clientCapabilities", capabilities},
                 {"clientInfo", QJsonObject{{"name", "edi"},
                                            {"version", QCoreApplication::applicationVersion()}}}},
                [this](const QJsonObject& result, const QJsonObject& error) {
                    if (!error.isEmpty()) {
                        fail(QStringLiteral("GitHub Copilot did not start: %1").arg(errorText(error)),
                             AssistantProvider::FailureKind::Other);
                        return;
                    }
                    initialized(result);
                });
    });
    connect(&process_, &AssistantProcess::record, this, &CopilotSession::receive);
    connect(&process_, &AssistantProcess::failed, this, &CopilotSession::fail);
}

CopilotSession::~CopilotSession() {
    process_.disconnect(this);
    process_.retire();
    if (login_) {
        login_->disconnect(this);
        login_->kill();
        login_->waitForFinished(1000);
    }
}

QStringList CopilotSession::availableTools(const QStringList& expectedTools) {
    QStringList names = expectedTools;
    if (names.isEmpty()) {
        for (const auto& name : assistant_native_tool_names()) names.append(name.toString());
        names.append(QStringLiteral("request_user_input"));
    }
    // The CLI names an MCP tool `<server>-<tool>`; edi's tool names need no sanitizing.
    QStringList tools{skill_tool};
    for (const auto& name : names) {
        if (!name.isEmpty() && !tools.contains(edi_prefix + name)) tools.append(edi_prefix + name);
    }
    return tools;
}

const QStringList& CopilotSession::allowedEnvironment() {
    static const QStringList names{
        // Path, home, user, temporary folder, locale and display.
        QStringLiteral("PATH"), QStringLiteral("HOME"), QStringLiteral("USER"), QStringLiteral("LOGNAME"),
        QStringLiteral("TMPDIR"), QStringLiteral("TMP"), QStringLiteral("TEMP"), QStringLiteral("LANG"),
        QStringLiteral("LANGUAGE"), QStringLiteral("TZ"), QStringLiteral("DISPLAY"), QStringLiteral("WAYLAND_DISPLAY"),
        QStringLiteral("XDG_RUNTIME_DIR"), QStringLiteral("XDG_CACHE_HOME"), QStringLiteral("XDG_CONFIG_HOME"),
        QStringLiteral("XDG_DATA_HOME"),
        // The Linux keychain (libsecret) is reached over the session bus.
        QStringLiteral("DBUS_SESSION_BUS_ADDRESS"),
        // Windows system folders and basics.
        QStringLiteral("USERPROFILE"), QStringLiteral("USERNAME"), QStringLiteral("USERDOMAIN"),
        QStringLiteral("HOMEDRIVE"), QStringLiteral("HOMEPATH"), QStringLiteral("SystemRoot"),
        QStringLiteral("SystemDrive"), QStringLiteral("WINDIR"), QStringLiteral("APPDATA"),
        QStringLiteral("LOCALAPPDATA"), QStringLiteral("ProgramData"), QStringLiteral("ProgramFiles"),
        QStringLiteral("ProgramFiles(x86)"), QStringLiteral("ProgramW6432"), QStringLiteral("COMSPEC"),
        QStringLiteral("PATHEXT"), QStringLiteral("COMPUTERNAME"), QStringLiteral("OS"),
        QStringLiteral("NUMBER_OF_PROCESSORS"), QStringLiteral("PROCESSOR_ARCHITECTURE"),
        // Proxies and certificates.
        QStringLiteral("HTTP_PROXY"), QStringLiteral("HTTPS_PROXY"), QStringLiteral("NO_PROXY"),
        QStringLiteral("ALL_PROXY"), QStringLiteral("http_proxy"), QStringLiteral("https_proxy"),
        QStringLiteral("no_proxy"), QStringLiteral("all_proxy"), QStringLiteral("SSL_CERT_FILE"),
        QStringLiteral("SSL_CERT_DIR"), QStringLiteral("NODE_EXTRA_CA_CERTS")};
    return names;
}

QStringList CopilotSession::arguments(const QString& workspace, const QStringList& availableTools) {
    return {QStringLiteral("--acp"),
            QStringLiteral("--stdio"),
            QStringLiteral("--no-auto-update"),
            QStringLiteral("--disable-builtin-mcps"),
            QStringLiteral("--disable-mcp-server"),
            QStringLiteral("computer-use"),
            // A closed list: shell, file, web, agent and question tools are not available at all.
            QStringLiteral("--available-tools"),
            availableTools.join(QLatin1Char(',')),
            QStringLiteral("--allow-tool"),
            skill_tool,
            QStringLiteral("--allow-tool"),
            QStringLiteral("edi"),
            QStringLiteral("--additional-mcp-config"),
            QLatin1Char('@') + QDir(workspace).absoluteFilePath(QStringLiteral(".edi/copilot-mcp.json"))};
}

std::optional<QProcessEnvironment> CopilotSession::environment(const AssistantRuntimeLaunch& launch,
                                                               QString* explanation) {
    const auto deny = [explanation](const QString& text) {
        if (explanation) *explanation = text;
        return std::optional<QProcessEnvironment>{};
    };
    const auto home = launch.account.home;
    if (home.isEmpty() || !QFileInfo(home).isAbsolute() || !QFileInfo(home).isDir())
        return deny(QStringLiteral("The GitHub Copilot account folder is missing."));
    // An empty folder edi owns, so the CLI finds no GitHub CLI login to fall back on.
    const auto emptyGh = QDir::cleanPath(QFileInfo(home).absolutePath() + QStringLiteral("/.empty-gh"));
    if (!QDir().mkpath(emptyGh))
        return deny(QStringLiteral("The folder edi keeps empty for the GitHub CLI could not be created."));
    QFile::setPermissions(emptyGh, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    if (!QDir(emptyGh).isEmpty(QDir::AllEntries | QDir::Hidden | QDir::System | QDir::NoDotAndDotDot))
        return deny(QStringLiteral("The folder edi keeps empty for the GitHub CLI is not empty: %1").arg(emptyGh));

    QProcessEnvironment env;
    for (const auto& name : allowedEnvironment()) {
        if (launch.environment.contains(name)) env.insert(name, launch.environment.value(name));
    }
    for (const auto& name : launch.environment.keys()) {
        if (name.startsWith(QStringLiteral("LC_"))) env.insert(name, launch.environment.value(name));
    }
    env.insert(QStringLiteral("COPILOT_HOME"), home);
    env.insert(QStringLiteral("COPILOT_AUTO_UPDATE"), QStringLiteral("false"));
    if (!launch.skillsDir.isEmpty()) env.insert(QStringLiteral("COPILOT_SKILLS_DIRS"), launch.skillsDir);
    // The CLI moves a tool result above 20 KiB to a file the model cannot open; edi's results stay under this.
    env.insert(QStringLiteral("COPILOT_LARGE_OUTPUT_THRESHOLD_BYTES"),
               QString::number(edi::assistant::Limits::context_bytes));
    env.insert(QStringLiteral("GH_CONFIG_DIR"), emptyGh);
    return env;
}

bool CopilotSession::start(const AssistantRuntimeLaunch& launch) {
    retire();
    has_failed_ = false;
    launch_ = launch;
    const auto deny = [this](const QString& text) {
        fail(text, AssistantProvider::FailureKind::Other);
        return false;
    };
    if (launch.executable.isEmpty()) return deny(QStringLiteral("GitHub Copilot is not installed."));
    if (launch.guard.isEmpty()) return deny(QStringLiteral("The assistant lifetime guard is unavailable."));
    if (launch.workspace.isEmpty() || !QFileInfo(launch.workspace).isDir())
        return deny(QStringLiteral("The assistant workspace is missing."));
    QString explanation;
    const auto env = environment(launch, &explanation);
    if (!env) return deny(explanation);

    const auto ediDir = QDir(launch.workspace).absoluteFilePath(QStringLiteral(".edi"));
    if (!QDir().mkpath(ediDir)) return deny(QStringLiteral("The assistant workspace could not be prepared."));
    QFile::setPermissions(ediDir, QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
    const auto serverEnv = serverEnvironment(launch.toolServer.value(QStringLiteral("env")));
    const auto command = launch.toolServer.value(QStringLiteral("command")).toString();
    if (command.isEmpty() || !serverEnv || !launch.toolServer.value(QStringLiteral("args")).isArray())
        return deny(QStringLiteral("edi's tool server could not be described to GitHub Copilot."));
    QJsonObject server{{"type", "local"},
                       {"command", command},
                       {"args", launch.toolServer.value(QStringLiteral("args"))},
                       {"env", *serverEnv},
                       {"tools", QJsonArray{"*"}},
                       // Always loaded, never behind the CLI's tool search, and from live discovery.
                       {"deferTools", "never"},
                       {"disableToolCache", true}};
    if (launch.toolTimeoutMs > 0) server.insert(QStringLiteral("timeout"), double(launch.toolTimeoutMs));
    const QJsonObject config{{"mcpServers", QJsonObject{{"edi", server}}}};
    if (!writeOwnerOnly(QDir(ediDir).absoluteFilePath(QStringLiteral("copilot-mcp.json")),
                        QJsonDocument(config).toJson(QJsonDocument::Compact)))
        return deny(QStringLiteral("The tool configuration for GitHub Copilot could not be written."));
    // AGENTS.md is the CLI's custom instructions file in the working folder.
    if (!writeOwnerOnly(QDir(launch.workspace).absoluteFilePath(QStringLiteral("AGENTS.md")),
                        launch.instructions.toUtf8()))
        return deny(QStringLiteral("The assistant instructions could not be written."));

    readback_timer_.start(readback_ms);
    available_tools_ = availableTools(launch.expectedTools);
    if (!process_.start(launch.guard, launch.executable, arguments(launch.workspace, available_tools_),
                        launch.workspace, *env)) {
        readback_timer_.stop();
        return deny(QStringLiteral("GitHub Copilot could not be started."));
    }
    return true;
}

void CopilotSession::retire() {
    process_.retire();
    readback_timer_.stop();
    pending_.clear();
    threads_.clear();
    notices_.clear();
    ready_ = can_load_ = can_logout_ = false;
    probe_.clear();
    spare_.clear();
    probe_listed_ = checking_start_ = false;
    commands_.clear();
    identity_text_.clear();
    probe_options_ = {};
}

quint64 CopilotSession::generation() const noexcept { return process_.generation(); }

// JSON-RPC ---------------------------------------------------------------------------------------------------------

bool CopilotSession::request(const QString& method, const QJsonObject& params, Reply reply) {
    const auto id = ++next_id_;
    pending_.insert(id, std::move(reply));
    if (!process_.write({{"jsonrpc", "2.0"}, {"id", double(id)}, {"method", method}, {"params", params}})) {
        pending_.remove(id);
        fail(QStringLiteral("GitHub Copilot could not be reached."), AssistantProvider::FailureKind::Other);
        return false;
    }
    return true;
}

bool CopilotSession::notify(const QString& method, const QJsonObject& params) {
    return process_.write({{"jsonrpc", "2.0"}, {"method", method}, {"params", params}});
}

void CopilotSession::answer(const QJsonValue& id, const QJsonObject& result) {
    process_.write({{"jsonrpc", "2.0"}, {"id", id}, {"result", result}});
}

void CopilotSession::receive(const QJsonObject& record) {
    const auto method = record.value(QStringLiteral("method"));
    const auto id = record.value(QStringLiteral("id"));
    if (method.isString()) {
        const auto params = record.value(QStringLiteral("params")).toObject();
        if (id.isUndefined() || id.isNull()) {
            if (method.toString() == QStringLiteral("session/update")) sessionUpdate(params);
        } else serverRequest(id, method.toString(), params);
        return;
    }
    if (!id.isDouble()) return;
    const auto it = pending_.find(qint64(id.toDouble()));
    if (it == pending_.end()) return;
    const auto reply = std::move(it.value());
    pending_.erase(it);
    const auto error = record.value(QStringLiteral("error"));
    if (error.isObject()) reply({}, error.toObject().isEmpty() ? QJsonObject{{"message", ""}} : error.toObject());
    else reply(record.value(QStringLiteral("result")).toObject(), {});
}

void CopilotSession::serverRequest(const QJsonValue& id, const QString& method, const QJsonObject& params) {
    if (method == QStringLiteral("session/request_permission")) {
        // Never a JSON-RPC error: reject this once, or report the turn cancelled while Stop runs.
        const auto it = threads_.constFind(params.value(QStringLiteral("sessionId")).toString());
        QString reject;
        for (const auto* kind : {"reject_once", "reject_always"}) {
            for (const auto& value : params.value(QStringLiteral("options")).toArray()) {
                const auto option = value.toObject();
                if (option.value(QStringLiteral("kind")).toString() == QLatin1String(kind)) {
                    reject = option.value(QStringLiteral("optionId")).toString();
                    break;
                }
            }
            if (!reject.isEmpty()) break;
        }
        if ((it != threads_.constEnd() && it->cancelling) || reject.isEmpty())
            answer(id, {{"outcome", QJsonObject{{"outcome", "cancelled"}}}});
        else
            answer(id, {{"outcome", QJsonObject{{"outcome", "selected"}, {"optionId", reject}}}});
        return;
    }
    if (method == QStringLiteral("elicitation/create")) {
        answer(id, {{"action", "decline"}});
        return;
    }
    process_.write({{"jsonrpc", "2.0"},
                    {"id", id},
                    {"error", QJsonObject{{"code", method_not_found}, {"message", "Method not found"}}}});
}

void CopilotSession::fail(const QString& explanation, AssistantProvider::FailureKind kind) {
    const auto generation = process_.generation();
    if (has_failed_ && failed_generation_ == generation) return;
    has_failed_ = true;
    failed_generation_ = generation;
    retire();
    emit failed(explanation, kind);
}

QString CopilotSession::withNotices(const QString& message) {
    auto lines = notices_;
    notices_.clear();
    if (!message.isEmpty()) lines.prepend(message);
    return lines.join(QLatin1Char('\n'));
}

void CopilotSession::refuse(const QJsonObject& error, const QString& fallback) {
    const bool signedOut = error.value(QStringLiteral("code")).toInt() == auth_required;
    auto reason = signedOut ? QStringLiteral("This GitHub account is signed out.") : errorText(error);
    if (reason.isEmpty()) reason = fallback;
    emit accountRefused(withNotices(reason), signedOut);
}

// Start and readbacks --------------------------------------------------------------------------------------------

void CopilotSession::initialized(const QJsonObject& result) {
    if (result.value(QStringLiteral("protocolVersion")).toInt() != 1) {
        fail(QStringLiteral("This GitHub Copilot release speaks another protocol version."),
             AssistantProvider::FailureKind::Other);
        return;
    }
    const auto capabilities = result.value(QStringLiteral("agentCapabilities")).toObject();
    can_load_ = capabilities.value(QStringLiteral("loadSession")).toBool();
    can_logout_ = capabilities.value(QStringLiteral("auth")).toObject().value(QStringLiteral("logout")).isObject();
    // ACP reports skills only per session (`available_commands_update`), so the readback opens one session.
    request(QStringLiteral("session/new"), {{"cwd", launch_.workspace}, {"mcpServers", QJsonArray{}}},
            [this](const QJsonObject& reply, const QJsonObject& error) {
                if (!error.isEmpty()) {
                    const auto generation = process_.generation();
                    refuse(error, QStringLiteral("GitHub Copilot refused to open a session."));
                    if (process_.generation() == generation) retire();
                    return;
                }
                probeOpened(reply);
            });
}

void CopilotSession::probeOpened(const QJsonObject& result) {
    probe_ = result.value(QStringLiteral("sessionId")).toString();
    if (probe_.isEmpty()) {
        fail(QStringLiteral("GitHub Copilot opened a session without an id."), AssistantProvider::FailureKind::Other);
        return;
    }
    probe_options_ = result.value(QStringLiteral("configOptions")).toArray();
    checkSkills();
}

void CopilotSession::checkSkills() {
    if (ready_ || probe_.isEmpty() || checking_start_ || !probe_listed_) return;
    for (const auto& skill : launch_.skills) {
        if (!commands_.contains(skill)) return;  // a later update may still bring it
    }
    checking_start_ = true;
    checkIdentity(probe_, [this](const QString& login) { finishStart(login); });
}

CopilotSession::User CopilotSession::parseUser(const QString& text) {
    // `/user show` prints the signed-in account in a format the CLI does not document; these patterns read the
    // login, the hosts it names and a signed-out answer, and anything they cannot read counts as unreadable.
    static const QRegularExpression hostPattern(
        QStringLiteral("\\b((?:[a-z0-9-]+\\.)*ghe\\.com|github\\.com)\\b"), QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression loginPattern(
        QStringLiteral("(?:\\b(?:as|user(?:name)?:|login:|account:)\\s+@?|(?<![\\w.])@)"
                       "([A-Za-z0-9][A-Za-z0-9-]{0,38})\\b"),
        QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression signedOutPattern(
        QStringLiteral("\\bnot (?:currently )?(?:signed|logged) in\\b|"
                       "\\bno (?:signed-in |logged-in )?(?:users?|accounts?)\\b|"
                       "\\b(?:signed|logged) out\\b"),
        QRegularExpression::CaseInsensitiveOption);
    User user;
    for (auto it = hostPattern.globalMatch(text); it.hasNext();) {
        const auto host = it.next().captured(1).toLower();
        if (!user.hosts.contains(host)) user.hosts.append(host);
    }
    user.signedOut = signedOutPattern.match(text).hasMatch();
    if (!user.signedOut) {
        if (const auto match = loginPattern.match(text); match.hasMatch()) user.login = match.captured(1);
    }
    return user;
}

void CopilotSession::runCommand(const QString& session, const QString& command,
                                const std::function<void(const QJsonObject&, const QString&)>& done) {
    identity_text_.insert(session, {});
    request(QStringLiteral("session/prompt"),
            {{"sessionId", session}, {"prompt", QJsonArray{QJsonObject{{"type", "text"}, {"text", command}}}}},
            // NOLINTNEXTLINE(clang-analyzer-cplusplus.NewDeleteLeaks): the std::function owns the lambda; the analyzer does not follow libc++'s release of it
            [this, session, done](const QJsonObject&, const QJsonObject& error) {
                const auto text = identity_text_.take(session).join(QString());
                done(error, text);
            });
}

void CopilotSession::checkIdentity(const QString& session, const std::function<void(const QString&)>& pass,
                                   std::function<void(const QString&, bool)> refused) {
    // The login lives in the system keychain and the home does not choose it, so the CLI's own account command
    // selects the record's login and reads it back in the session that takes the input. Without `/user` over ACP
    // there is no proof, and `ready` says so; the caller sends no input on that route.
    if (!commands_.contains(QStringLiteral("user"))) {
        pass({});
        return;
    }
    if (!refused) {
        refused = [this](const QString& reason, bool signedOut) {
            const auto generation = process_.generation();
            emit accountRefused(withNotices(reason), signedOut);
            if (process_.generation() == generation) retire();
        };
    }
    const auto expected = normalizedHost(launch_.account.host);
    const auto email = launch_.account.email;
    const auto compare = [pass, refused, expected, email](const QJsonObject& error, const QString& text) {
        if (!error.isEmpty()) {
            const bool signedOut = error.value(QStringLiteral("code")).toInt() == auth_required;
            const auto message = errorText(error);
            const auto fallback = QStringLiteral("GitHub Copilot did not report the signed-in account.");
            refused(signedOut || message.isEmpty() ? fallback : message, signedOut);
            return;
        }
        const auto user = parseUser(text);
        if (user.signedOut) {
            refused(QStringLiteral("This GitHub account is signed out."), true);
            return;
        }
        if (user.login.isEmpty()) {
            refused(QStringLiteral("GitHub Copilot did not report which account is signed in."), false);
            return;
        }
        const auto hosts = user.hosts.isEmpty() ? QStringList{QStringLiteral("github.com")} : user.hosts;
        if (!hosts.contains(expected)) {
            refused(QStringLiteral("GitHub Copilot is signed in to %1, not %2.")
                        .arg(hosts.join(QStringLiteral(", ")), expected),
                    false);
            return;
        }
        if (!email.isEmpty() && email.compare(user.login, Qt::CaseInsensitive) != 0) {
            refused(QStringLiteral("GitHub Copilot is signed in as %1, not %2.").arg(user.login, email), false);
            return;
        }
        pass(user.login);
    };
    const auto show = [this, session, compare] { runCommand(session, QStringLiteral("/user show"), compare); };
    // A record without a login is a first sign-in: there is nothing to select yet, and the readback names it.
    if (email.isEmpty()) {
        show();
        return;
    }
    static const QRegularExpression loginShape(QStringLiteral("^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"));
    if (!loginShape.match(email).hasMatch()) {
        refused(QStringLiteral("The saved GitHub login is not valid: %1").arg(email), false);
        return;
    }
    runCommand(session, QStringLiteral("/user switch ") + email,
               [refused, show, email](const QJsonObject& error, const QString&) {
                   if (!error.isEmpty()) {
                       const auto message = errorText(error);
                       refused(message.isEmpty()
                                   ? QStringLiteral("GitHub Copilot could not switch to %1.").arg(email)
                                   : message,
                               error.value(QStringLiteral("code")).toInt() == auth_required);
                       return;
                   }
                   show();
               });
}

void CopilotSession::finishStart(const QString& login) {
    // The probe session passed the identity check after this process started, so it can take the first thread.
    spare_ = probe_;
    ready_ = true;
    readback_timer_.stop();
    const auto generation = process_.generation();
    emitModels(probe_options_);
    if (process_.generation() != generation) return;
    const bool distinguishable = commands_.contains(QStringLiteral("user"));
    // ACP lists no tools; edi's tool server reports what the runtime listed through it.
    emit ready(QJsonObject{{"email", login},
                           {"plan", ""},
                           {"host", normalizedHost(launch_.account.host)},
                           {"login", login},
                           {"accountsDistinguishable", distinguishable},
                           {"identityProven", distinguishable && !login.isEmpty()}},
               QStringList{}, launch_.skills);
}

void CopilotSession::readbackExpired() {
    if (ready_) return;
    QStringList missing;
    for (const auto& skill : launch_.skills) {
        if (!commands_.contains(skill)) missing.append(skill);
    }
    if (!probe_.isEmpty() && !missing.isEmpty())
        fail(QStringLiteral("GitHub Copilot did not load edi's skills: %1.").arg(missing.join(QStringLiteral(", "))),
             AssistantProvider::FailureKind::OperationDeadline);
    else
        fail(QStringLiteral("GitHub Copilot did not answer in time."),
             AssistantProvider::FailureKind::OperationDeadline);
}

// Threads --------------------------------------------------------------------------------------------------------

void CopilotSession::emitModels(const QJsonArray& configOptions) {
    const auto model = optionOf(configOptions, QStringLiteral("model"));
    if (model.isEmpty()) return;
    QJsonArray efforts;
    for (const auto& value : selectValues(optionOf(configOptions, QStringLiteral("thought_level"))))
        efforts.append(value.toObject().value(QStringLiteral("value")));
    QJsonArray rows;
    for (const auto& value : selectValues(model)) {
        const auto option = value.toObject();
        // ACP reports the effort choices of the current model only; no default is advertised.
        rows.append(QJsonObject{{"id", option.value(QStringLiteral("value"))},
                                {"displayName", option.value(QStringLiteral("name"))},
                                {"efforts", efforts},
                                {"defaultEffort", ""}});
    }
    emit modelsListed(rows);
}

void CopilotSession::openThread(const QString& resumeId, const QString& model, const QString& effort) {
    if (!ready_) {
        fail(QStringLiteral("GitHub Copilot is not ready."), AssistantProvider::FailureKind::Other);
        return;
    }
    if (resumeId.isEmpty() && !spare_.isEmpty()) {
        const auto session = std::exchange(spare_, QString());
        threads_[session].id = session;
        threads_[session].configOptions = probe_options_;
        configure(session, model, effort, true, false);
        return;
    }
    if (resumeId.isEmpty()) {
        request(QStringLiteral("session/new"), {{"cwd", launch_.workspace}, {"mcpServers", QJsonArray{}}},
                [this, model, effort](const QJsonObject& result, const QJsonObject& error) {
                    const auto session = result.value(QStringLiteral("sessionId")).toString();
                    if (!error.isEmpty() || session.isEmpty()) {
                        refuse(error, QStringLiteral("GitHub Copilot refused to open a session."));
                        return;
                    }
                    threads_[session].id = session;
                    threads_[session].configOptions = result.value(QStringLiteral("configOptions")).toArray();
                    configure(session, model, effort, true, true);
                });
        return;
    }
    if (!can_load_) {
        emit accountRefused(QStringLiteral("This GitHub Copilot release cannot reopen conversations."), false);
        return;
    }
    // The replayed updates are dropped: edi's history file holds the rows.
    threads_[resumeId].id = resumeId;
    threads_[resumeId].loading = true;
    request(QStringLiteral("session/load"),
            {{"sessionId", resumeId}, {"cwd", launch_.workspace}, {"mcpServers", QJsonArray{}}},
            [this, resumeId, model, effort](const QJsonObject& result, const QJsonObject& error) {
                const auto it = threads_.find(resumeId);
                if (it == threads_.end()) return;
                if (!error.isEmpty()) {
                    threads_.erase(it);
                    refuse(error, QStringLiteral("GitHub Copilot could not reopen the conversation."));
                    return;
                }
                it->loading = false;
                if (result.contains(QStringLiteral("configOptions")))
                    it->configOptions = result.value(QStringLiteral("configOptions")).toArray();
                configure(resumeId, model, effort, true, true);
            });
}

void CopilotSession::configure(const QString& session, const QString& model, const QString& effort, bool open,
                               bool verify) {
    const auto it = threads_.constFind(session);
    if (it == threads_.constEnd()) return;
    const auto modelOption = optionOf(it->configOptions, QStringLiteral("model"));
    const auto effortOption = optionOf(it->configOptions, QStringLiteral("thought_level"));
    const auto modelId = modelOption.value(QStringLiteral("id")).toString(QStringLiteral("model"));
    const auto effortId = effortOption.value(QStringLiteral("id")).toString();
    // A new or reloaded session shows whose it is before its first prompt.
    const auto done = [this, session, open, verify] {
        if (!open || !threads_.contains(session)) return;
        if (!verify) {
            emit threadOpened(session);
            return;
        }
        checkIdentity(session, [this, session](const QString&) {
            if (threads_.contains(session)) emit threadOpened(session);
        });
    };
    // No effort option means the model has no effort choice; the catalogue offers none either.
    const auto setEffort = [this, session, effort, effortId, done] {
        if (effort.isEmpty() || effortId.isEmpty()) {
            done();
            return;
        }
        request(QStringLiteral("session/set_config_option"),
                {{"sessionId", session}, {"configId", effortId}, {"value", effort}},
                [this, session, done](const QJsonObject& result, const QJsonObject& error) {
                    if (!error.isEmpty()) {
                        refuse(error, QStringLiteral("GitHub Copilot refused the reasoning effort."));
                        return;
                    }
                    if (const auto t = threads_.find(session); t != threads_.end())
                        t->configOptions = result.value(QStringLiteral("configOptions")).toArray();
                    done();
                });
    };
    if (model.isEmpty()) {
        setEffort();
        return;
    }
    request(QStringLiteral("session/set_config_option"),
            {{"sessionId", session}, {"configId", modelId}, {"value", model}},
            [this, session, setEffort](const QJsonObject& result, const QJsonObject& error) {
                if (!error.isEmpty()) {
                    refuse(error, QStringLiteral("GitHub Copilot refused the model."));
                    return;
                }
                if (const auto t = threads_.find(session); t != threads_.end())
                    t->configOptions = result.value(QStringLiteral("configOptions")).toArray();
                setEffort();
            });
}

void CopilotSession::selectModel(const QString& thread, const QString& model, const QString& effort) {
    if (!threads_.contains(thread)) return;
    configure(thread, model, effort, false, false);
}

void CopilotSession::sendMessage(const QString& thread, const QString& clientMessageId, const QString& text) {
    Q_UNUSED(clientMessageId);  // ACP prompts carry no client id
    const auto it = threads_.find(thread);
    if (it == threads_.end() || it->loading) {
        emit turnFinished(thread, {}, QStringLiteral("failed"),
                          {{"message", QStringLiteral("This conversation is not open in GitHub Copilot.")}});
        return;
    }
    // ACP has no steer: a message sent during a turn waits for the turn to end.
    if (it->running) {
        it->queue.append(text);
        return;
    }
    startTurn(thread, text);
}

void CopilotSession::startTurn(const QString& session, const QString& text) {
    auto& thread = threads_[session];
    thread.running = true;
    thread.cancelling = false;
    thread.turn = QStringLiteral("turn-%1").arg(++turns_);
    thread.items = 0;
    thread.tools.clear();
    const auto turn = thread.turn;
    const auto generation = process_.generation();
    emit turnStarted(session, turn);
    if (process_.generation() != generation) return;
    request(QStringLiteral("session/prompt"),
            {{"sessionId", session},
             {"prompt", QJsonArray{QJsonObject{{"type", "text"}, {"text", prompt_header + QStringLiteral("\n\n") + text}}}}},
            [this, session, turn](const QJsonObject& result, const QJsonObject& error) {
                const auto t = threads_.constFind(session);
                if (t == threads_.constEnd() || t->turn != turn || !t->running) return;
                if (!error.isEmpty()) {
                    auto message = errorText(error);
                    if (message.isEmpty()) message = QStringLiteral("GitHub Copilot stopped the turn.");
                    QJsonObject failure{{"message", withNotices(message)}};
                    if (error.value(QStringLiteral("code")).toInt() == auth_required)
                        failure.insert(QStringLiteral("signedOut"), true);
                    finishTurn(session, QStringLiteral("failed"), failure);
                    return;
                }
                const auto reason = result.value(QStringLiteral("stopReason")).toString();
                if (reason == QStringLiteral("end_turn")) finishTurn(session, QStringLiteral("completed"), {});
                else if (reason == QStringLiteral("cancelled"))
                    finishTurn(session, QStringLiteral("interrupted"), {});
                else
                    finishTurn(session, QStringLiteral("failed"),
                               {{"message", withNotices(QStringLiteral("GitHub Copilot stopped the turn (%1).")
                                                            .arg(reason.isEmpty() ? QStringLiteral("no reason")
                                                                                  : reason))}});
            });
}

void CopilotSession::finishTurn(const QString& session, const QString& status, const QJsonObject& error) {
    const auto it = threads_.find(session);
    if (it == threads_.end()) return;
    const auto generation = process_.generation();
    flushThought(*it);
    if (process_.generation() != generation) return;
    if (const auto t = threads_.find(session); t != threads_.end()) flushMessage(*t);
    if (process_.generation() != generation) return;
    const auto t = threads_.find(session);
    if (t == threads_.end()) return;
    const auto turn = t->turn;
    const auto next = t->queue.isEmpty() ? std::optional<QString>{} : std::optional(t->queue.takeFirst());
    t->running = false;
    t->cancelling = false;
    t->tools.clear();
    emit turnFinished(session, turn, status, error);
    if (!next || process_.generation() != generation) return;
    if (const auto after = threads_.constFind(session); after != threads_.constEnd() && !after->running)
        startTurn(session, *next);
}

void CopilotSession::cancelTurn(const QString& thread) {
    const auto it = threads_.find(thread);
    if (it == threads_.end() || !it->running) return;
    // Every permission request from here on is answered `cancelled` (requests are never left open).
    it->cancelling = true;
    it->queue.clear();
    notify(QStringLiteral("session/cancel"), {{"sessionId", thread}});
}

// Updates --------------------------------------------------------------------------------------------------------

void CopilotSession::flushMessage(Thread& thread) {
    if (thread.messageId.isEmpty()) return;
    const QJsonObject item{{"type", "agentMessage"}, {"id", thread.messageId}, {"text", thread.messageText}};
    thread.messageId.clear();
    thread.messageText.clear();
    emit itemCompleted(thread.id, thread.turn, item);
}

void CopilotSession::flushThought(Thread& thread) {
    if (thread.thoughtId.isEmpty()) return;
    const QJsonObject item{{"type", "reasoning"}, {"id", thread.thoughtId}, {"text", thread.thoughtText}};
    thread.thoughtId.clear();
    thread.thoughtText.clear();
    emit itemCompleted(thread.id, thread.turn, item);
}

void CopilotSession::sessionUpdate(const QJsonObject& params) {
    const auto session = params.value(QStringLiteral("sessionId")).toString();
    const auto update = params.value(QStringLiteral("update")).toObject();
    const auto kind = update.value(QStringLiteral("sessionUpdate")).toString();

    if (kind == QStringLiteral("notice")) {
        auto text = update.value(QStringLiteral("title")).toString();
        const auto detail = update.value(QStringLiteral("description")).toString();
        if (!detail.isEmpty()) text += QStringLiteral(": ") + detail;
        if (!text.isEmpty()) notices_.append(text);
        while (notices_.size() > 5) notices_.removeFirst();
        return;
    }
    if (kind == QStringLiteral("available_commands_update")) {
        // The update may come before the session/new reply that names the probe session.
        if (ready_ ? session != probe_ : (!probe_.isEmpty() && session != probe_)) return;
        commands_.clear();
        for (const auto& value : update.value(QStringLiteral("availableCommands")).toArray()) {
            auto name = value.toObject().value(QStringLiteral("name")).toString();
            if (name.startsWith(QLatin1Char('/'))) name.remove(0, 1);
            commands_.append(name);
        }
        probe_listed_ = true;
        checkSkills();
        return;
    }
    if (kind == QStringLiteral("config_option_update")) {
        const auto options = update.value(QStringLiteral("configOptions")).toArray();
        if (session == probe_) probe_options_ = options;
        if (const auto it = threads_.find(session); it != threads_.end()) it->configOptions = options;
        return;
    }
    if (const auto text = identity_text_.find(session); text != identity_text_.end()) {
        if (kind == QStringLiteral("agent_message_chunk"))
            text->append(update.value(QStringLiteral("content")).toObject().value(QStringLiteral("text")).toString());
        return;
    }
    const auto it = threads_.find(session);
    if (it == threads_.end() || it->loading || !it->running) return;
    auto& thread = *it;
    const auto generation = process_.generation();
    const auto messageId = update.value(QStringLiteral("messageId")).toString();
    const auto content = update.value(QStringLiteral("content")).toObject();

    if (kind == QStringLiteral("agent_message_chunk")) {
        if (content.value(QStringLiteral("type")).toString() != QStringLiteral("text")) return;
        flushThought(thread);
        if (process_.generation() != generation) return;
        auto& current = threads_[session];
        if (!current.messageId.isEmpty() && !messageId.isEmpty() && messageId != current.messageId) {
            flushMessage(current);
            if (process_.generation() != generation) return;
        }
        auto& open = threads_[session];
        if (open.messageId.isEmpty())
            open.messageId =
                messageId.isEmpty() ? QStringLiteral("%1-m%2").arg(open.turn).arg(++open.items) : messageId;
        const auto delta = content.value(QStringLiteral("text")).toString();
        open.messageText += delta;
        emit textDelta(session, open.turn, open.messageId, delta);
        return;
    }
    if (kind == QStringLiteral("agent_thought_chunk")) {
        if (content.value(QStringLiteral("type")).toString() != QStringLiteral("text")) return;
        flushMessage(thread);
        if (process_.generation() != generation) return;
        auto& open = threads_[session];
        if (!open.thoughtId.isEmpty() && !messageId.isEmpty() && messageId != open.thoughtId) {
            flushThought(open);
            if (process_.generation() != generation) return;
        }
        auto& current = threads_[session];
        if (current.thoughtId.isEmpty())
            current.thoughtId =
                messageId.isEmpty() ? QStringLiteral("%1-r%2").arg(current.turn).arg(++current.items) : messageId;
        current.thoughtText += content.value(QStringLiteral("text")).toString();
        return;
    }
    if (kind == QStringLiteral("tool_call") || kind == QStringLiteral("tool_call_update")) {
        flushThought(thread);
        if (process_.generation() != generation) return;
        flushMessage(threads_[session]);
        if (process_.generation() != generation) return;
        toolUpdate(threads_[session], update);
    }
}

void CopilotSession::toolUpdate(Thread& thread, const QJsonObject& update) {
    const auto id = update.value(QStringLiteral("toolCallId")).toString();
    if (id.isEmpty()) return;
    auto& call = thread.tools[id];
    if (call.reported) return;
    if (const auto name = update.value(QStringLiteral("name")); name.isString() && !name.toString().isEmpty())
        call.name = name.toString();
    // The CLI names an MCP tool `<server>-<tool>`. ACP's `name` field is optional, so a title spelled that way
    // stands in for it; how the pinned release fills either is checked by its sign-in trial.
    if (call.name.isEmpty()) {
        const auto title = update.value(QStringLiteral("title")).toString().trimmed();
        if (title.startsWith(edi_prefix) && !title.contains(QLatin1Char(' '))) call.name = title;
    }
    if (const auto input = update.value(QStringLiteral("rawInput")); input.isObject())
        call.arguments = input.toObject();
    const auto status = update.value(QStringLiteral("status")).toString();
    const bool running = !status.isEmpty() && status != QStringLiteral("pending");
    const auto session = thread.id, turn = thread.turn;

    if (call.name == skill_tool) {
        call.reported = true;
        return;
    }
    if (call.name.startsWith(edi_prefix) && available_tools_.contains(call.name)) {
        if (!running && !update.value(QStringLiteral("rawInput")).isObject()) return;  // input still streaming
        call.reported = true;
        emit toolUse(session, turn, call.name.mid(edi_prefix.size()), call.arguments, id);
        return;
    }
    if (!call.name.isEmpty() || running) {
        // A tool that is not edi's, or one that runs without a name to show it is edi's.
        call.reported = true;
        const auto label = call.name.isEmpty() ? update.value(QStringLiteral("title")).toString() : call.name;
        emit foreignTool(session, turn, label.isEmpty() ? id : label);
    }
}

// Sign-in and sign-out --------------------------------------------------------------------------------------------

void CopilotSession::signIn(const AssistantRuntimeLaunch& launch) {
    cancelSignIn();
    QString explanation;
    const auto env = environment(launch, &explanation);
    if (launch.executable.isEmpty()) explanation = QStringLiteral("GitHub Copilot is not installed.");
    if (!env || launch.executable.isEmpty()) {
        emit signInFinished(false, explanation);
        return;
    }
    QStringList args{QStringLiteral("login")};
    if (const auto host = normalizedHost(launch.account.host); host != QStringLiteral("github.com"))
        args << QStringLiteral("--host") << QStringLiteral("https://") + host;
    login_buffer_.clear();
    login_url_.clear();
    login_code_.clear();
    login_last_line_.clear();
    login_asked_ = false;
    login_host_ = normalizedHost(launch.account.host);
    auto* process = new QProcess(this);
    login_ = process;
    process->setProgram(launch.executable);
    process->setArguments(args);
    process->setProcessEnvironment(*env);
    process->setWorkingDirectory(launch.account.home);
    process->setProcessChannelMode(QProcess::MergedChannels);
    connect(process, &QProcess::readyRead, this, [this, process] {
        if (login_ == process) loginOutput();
    });
    connect(process, &QProcess::finished, this, [this, process](int code, QProcess::ExitStatus status) {
        if (login_ == process) loginFinished(code, status);
        process->deleteLater();
    });
    connect(process, &QProcess::errorOccurred, this, [this, process](QProcess::ProcessError error) {
        if (login_ != process || error != QProcess::FailedToStart) return;
        endSignIn(false, QStringLiteral("GitHub Copilot could not be started for the sign-in."));
        process->deleteLater();
    });
    login_timer_.start(login_ms);
    process->start();
}

void CopilotSession::loginOutput() {
    login_buffer_ += stripTerminal(QString::fromUtf8(login_->readAll()));
    static const QRegularExpression urlPattern(QStringLiteral("https?://[^\\s'\"<>]+"));
    static const QRegularExpression codePattern(QStringLiteral("\\b[A-Z0-9]{4}-[A-Z0-9]{4}\\b"));
    const auto scan = [this](const QString& line) {
        bool changed = false;
        for (auto it = urlPattern.globalMatch(line); it.hasNext();) {
            auto url = it.next().captured();
            while (!url.isEmpty() && QStringLiteral(".,;:)]").contains(url.back())) url.chop(1);
            // Offered only for GitHub's device page or the account's own GHE.com host.
            const QUrl parsed(url);
            const auto host = parsed.host().toLower();
            const bool device = host == QStringLiteral("github.com") &&
                                parsed.path() == QStringLiteral("/login/device") && login_host_ == host;
            const bool ghe = host.endsWith(QStringLiteral(".ghe.com")) && host == login_host_;
            if (parsed.scheme() != QStringLiteral("https") || !(device || ghe)) continue;
            if (login_url_.isEmpty()) {
                login_url_ = url;
                changed = true;
            }
        }
        if (const auto match = codePattern.match(line); match.hasMatch() && login_code_.isEmpty()) {
            login_code_ = match.captured();
            changed = true;
        }
        if (changed) emit signInOpened(login_url_, login_code_, {});
    };
    qsizetype newline;
    while ((newline = login_buffer_.indexOf(QLatin1Char('\n'))) >= 0) {
        const auto line = login_buffer_.left(newline).trimmed();
        login_buffer_.remove(0, newline + 1);
        if (!line.isEmpty()) login_last_line_ = line;
        scan(line);
        if (!login_) return;
    }
    // The plain-file question waits for an answer on its own line, without a newline.
    const auto partial = login_buffer_.trimmed();
    if (!login_asked_ && partial.contains(QStringLiteral("plain"), Qt::CaseInsensitive) &&
        (partial.endsWith(QLatin1Char('?')) || partial.contains(QStringLiteral("y/n"), Qt::CaseInsensitive) ||
         partial.endsWith(QLatin1Char(':')))) {
        login_asked_ = true;
        login_answer_timer_.start(login_answer_ms);
        emit signInOpened({}, {}, partial);
    }
}

void CopilotSession::answerSignIn(const QString& input) {
    if (!login_) return;
    if (!login_asked_) {
        login_->write((input + QLatin1Char('\n')).toUtf8());
        return;
    }
    const auto answer = input.trimmed().toLower();
    const bool yes = answer == QStringLiteral("yes") || answer == QStringLiteral("y");
    login_answer_timer_.stop();
    login_asked_ = false;
    login_buffer_.clear();
    login_->write(yes ? "y\n" : "n\n");
}

void CopilotSession::loginFinished(int exitCode, QProcess::ExitStatus status) {
    loginOutput();
    if (!login_buffer_.trimmed().isEmpty()) login_last_line_ = login_buffer_.trimmed();
    if (status == QProcess::NormalExit && exitCode == 0) endSignIn(true, login_last_line_);
    else endSignIn(false, login_last_line_.isEmpty() ? QStringLiteral("The GitHub sign-in did not finish.")
                                                     : login_last_line_);
}

void CopilotSession::endSignIn(bool success, const QString& message) {
    if (!login_) return;
    login_timer_.stop();
    login_answer_timer_.stop();
    login_->disconnect(this);
    if (login_->state() != QProcess::NotRunning) {
        connect(login_.data(), &QProcess::finished, login_.data(), &QObject::deleteLater);
        login_->kill();
    } else login_->deleteLater();
    login_ = nullptr;
    login_asked_ = false;
    emit signInFinished(success, message);
}

void CopilotSession::cancelSignIn() {
    if (!login_) return;
    endSignIn(false, QStringLiteral("The GitHub sign-in was cancelled."));
}

void CopilotSession::signOut(const AssistantRuntimeLaunch& launch) {
    // ACP's own `logout`, sent only after `/user switch` and `/user show` proved this process uses the account.
    // Without that proof edi offers removal instead (`removeAccount`).
    if (!ready_ || launch_.account.id != launch.account.id || probe_.isEmpty()) {
        emit signOutUnconfirmed(QStringLiteral("GitHub Copilot can sign out only the account that is in use."));
        return;
    }
    if (!can_logout_) {
        emit signOutUnconfirmed(QStringLiteral("This GitHub Copilot release cannot sign out from edi."));
        return;
    }
    if (!commands_.contains(QStringLiteral("user")) || launch_.account.email.isEmpty()) {
        emit signOutUnconfirmed(QStringLiteral("GitHub Copilot cannot show which account it would sign out."));
        return;
    }
    checkIdentity(
        probe_, [this](const QString&) { logout(); },
        [this](const QString& reason, bool) { unconfirmed(reason); });
}

void CopilotSession::logout() {
    request(QStringLiteral("logout"), {}, [this](const QJsonObject&, const QJsonObject& error) {
        if (!error.isEmpty()) {
            const auto reason = errorText(error);
            unconfirmed(reason.isEmpty() ? QStringLiteral("GitHub Copilot could not sign out.") : reason);
            return;
        }
        // Confirmed only by the CLI itself: a new session now needs a sign-in (ACP's auth_required).
        request(QStringLiteral("session/new"), {{"cwd", launch_.workspace}, {"mcpServers", QJsonArray{}}},
                [this](const QJsonObject&, const QJsonObject& refusal) {
                    if (refusal.value(QStringLiteral("code")).toInt() != auth_required) {
                        unconfirmed(QStringLiteral("GitHub Copilot did not confirm the sign-out."));
                        return;
                    }
                    retire();
                    emit signedOut();
                });
    });
}

void CopilotSession::unconfirmed(const QString& reason) {
    // After a sign-out attempt the runtime's state is unknown, so it is not used again.
    retire();
    emit signOutUnconfirmed(withNotices(reason));
}

void CopilotSession::removeAccount(const AssistantRuntimeLaunch& launch) {
    retire();
    removeHome(launch.account);
}

void CopilotSession::removeHome(const AssistantAccountRef& account) {
    const auto copilotRoot = accounts_root_.isEmpty() ? QString() : accounts_root_ + QStringLiteral("/copilot");
    const QFileInfo home(account.home);
    const bool plainId = !account.id.isEmpty() && !account.id.contains(QLatin1Char('/')) &&
                         !account.id.contains(QLatin1Char('\\')) && account.id != QStringLiteral(".") &&
                         account.id != QStringLiteral("..");
    const auto canonicalRoot = QFileInfo(copilotRoot).canonicalFilePath();
    const bool inside = plainId && !copilotRoot.isEmpty() && !canonicalRoot.isEmpty() &&
                        QDir::cleanPath(account.home) == QDir::cleanPath(copilotRoot + QLatin1Char('/') + account.id) &&
                        !home.isSymLink() && QFileInfo(home.absolutePath()).canonicalFilePath() == canonicalRoot;
    if (!inside) {
        emit accountRefused(QStringLiteral("edi removes only accounts whose folder it created."), false);
        return;
    }
    if (home.exists() && !QDir(account.home).removeRecursively()) {
        emit accountRefused(QStringLiteral("The GitHub Copilot account folder could not be removed."), false);
        return;
    }
    emit removedOnly();
}

}  // namespace edi_app

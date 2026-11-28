// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <array>
#include <deque>
#include <functional>
#include <string_view>
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QPointer>
#include <QSet>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QTimer>
#include "assistant_runtime_session.hpp"

namespace edi_app {

class AssistantProcess;

/// Inherited variables the Claude runtime never sees (ADR-0108 §4), because they change how edi's tools and turns
/// run. The user's own credential and provider variables pass through.
inline constexpr std::array<std::string_view, 3> claude_removed_environment{
    "CLAUDECODE",
    "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB",
    "CLAUDE_AUTO_BACKGROUND_TASKS",
};

/// The runtime's environment: the app's, without `claude_removed_environment`, with the account's
/// `CLAUDE_CONFIG_DIR`, `DISABLE_UPDATES=1`, `MCP_PROTOCOL_NEGOTIATION=legacy` and, when `toolTimeoutMs` is not
/// zero, `MCP_TOOL_TIMEOUT`. The same environment serves `claude auth status|login|logout`.
QProcessEnvironment claude_runtime_environment(const QProcessEnvironment& app, const QString& home,
                                               quint64 toolTimeoutMs);

/// The long-lived process's arguments (ADR-0108 §4). An empty `model` or `effort` is left out; `resume` picks
/// `--resume` over `--session-id`.
QStringList claude_runtime_arguments(const QString& workspace, const QString& model, const QString& effort,
                                     const QString& sessionId, bool resume);

/// Where an organisation's managed Claude settings are found at the documented locations: "policy" for a device
/// policy (Windows registry, macOS configuration profile), "file" for a managed settings file or folder, else
/// empty. Only existence is checked; settings Anthropic's servers deliver cannot be seen beforehand.
QString claude_managed_settings();

/// Claude's runtime session: `claude -p` in stream-json mode, one process per open thread (ADR-0108 §4).
///
/// `start` stages the plugin, the MCP config and the instructions and starts a first process with a fresh session
/// id and no model. Every process start first runs `claude auth status` with that process's environment. The first
/// process's `initialize` reply and `system/init` give the identity, the skills, the model list and the tool set;
/// `ready` follows. `openThread` starts a new process for each thread (and an effort change restarts it); each
/// process passes the same readbacks before any input, and no input is written before its `system/init`.
/// `ready`'s identity adds `managedSettings` ("policy" or "file") when an organisation's settings were found, and
/// `hooksRan: true` when the process ran hooks (`hook_started`, `hook_progress`, `hook_response`) before
/// `system/init`.
/// `usageChanged` may carry `status: {status: allowed_warning|rejected, window?, resetsAt?}` beside the buckets.
class ClaudeSession final : public AssistantRuntimeSession {
    Q_OBJECT
public:
    explicit ClaudeSession(QObject* parent = nullptr);
    ~ClaudeSession() override;

    /// The principal the account's record keeps, with keys of `ready`'s identity ({email, organization, plan,
    /// authMethod, apiKeySource, tokenSource, host}). Every non-empty field must be reported the same by each
    /// process before its first input (the e-mail with case ignored), else `accountRefused` (not signed out). Set
    /// before `start`; empty for an account not yet recorded.
    void setAccountRecord(const QJsonObject& principal) { principal_ = principal; }

    void setExpectedTools(const QStringList& names) override { expected_tools_ = names; }
    bool start(const AssistantRuntimeLaunch& launch) override;
    void retire() override;
    quint64 generation() const noexcept override { return generation_; }

    void signIn(const AssistantRuntimeLaunch& launch) override;
    void cancelSignIn() override;
    void answerSignIn(const QString& input) override;
    void signOut(const AssistantRuntimeLaunch& launch) override;

    void openThread(const QString& resumeId, const QString& model, const QString& effort) override;
    void sendMessage(const QString& thread, const QString& clientMessageId, const QString& text) override;
    void cancelTurn(const QString& thread) override;
    void selectModel(const QString& thread, const QString& model, const QString& effort) override;
    bool reportsUsage() const noexcept override { return true; }

private:
    // What a process start leads to once its readbacks pass.
    enum class Purpose : unsigned char { Probe, Thread, Restart };

    AssistantRuntimeLaunch launch_;
    QProcessEnvironment environment_;
    QJsonObject principal_, account_info_;
    QString auth_method_, api_key_source_, api_provider_, managed_settings_;
    quint64 generation_ = 0;

    QPointer<AssistantProcess> process_;
    Purpose purpose_ = Purpose::Probe;
    // `tools_verified_`: the tool readback before input passed; `init_verified_`: the first turn's `system/init` passed.
    bool initialize_passed_ = false, tools_verified_ = false, init_verified_ = false, readbacks_done_ = false,
         hooks_ran_ = false;
    QStringList expected_tools_;
    QJsonObject identity_;
    QJsonArray models_;
    QStringList tools_, capabilities_;
    QTimer readback_timer_;

    QString session_id_, model_, effort_;
    QString process_model_, process_effort_;
    bool process_used_ = false, restart_pending_ = false, launching_ = false;
    struct Message { QString id, text; };
    std::deque<Message> queued_;

    bool turn_active_ = false, interrupted_ = false;
    // Steers the runtime kept after Stop; their turns are stopped and not shown.
    QSet<QString> dropped_messages_;
    // Messages sent while the current turn ran, by client id.
    QSet<QString> steers_;
    QString dropping_;
    QString turn_id_, last_error_;
    std::deque<QString> streamed_items_;
    QString streaming_item_, message_id_;
    quint64 item_counter_ = 0;

    quint64 request_counter_ = 0;
    QHash<QString, QString> requests_;  // request_id -> subtype

    struct Window { int usedPercent = 0; qint64 resetsAt = -1; };
    QHash<QString, Window> usage_;
    QJsonObject usage_status_;

    QPointer<QProcess> status_, login_, logout_;
    QString login_output_, login_url_, login_prompt_;

    // One `claude auth …` run. `problem` is empty when the command exited by itself.
    using OneShotDone = std::function<void(QProcess& process, const QString& problem, bool timedOut)>;
    QProcess* runOneShot(const AssistantRuntimeLaunch& launch, const QProcessEnvironment& environment,
                         const QStringList& arguments, int timeoutMs, QProcess::ProcessChannelMode mode,
                         const OneShotDone& done);

    bool prepareWorkspace(QString& problem);
    void launch(Purpose purpose, bool resume);
    void spawn(bool resume, quint64 generation);
    /// The pinned CLI sends `system/init` only with the first turn, so the tools are read back before any input
    /// through `mcp_status` and `get_context_usage`.
    void mcpStatusReply(const QJsonObject& reply);
    void contextUsageReply(const QJsonObject& reply);
    void toolsProblem(const QString& problem);
    bool dropRecord(const QJsonObject& record);
    void retireProcess();
    void receive(const QJsonObject& record);
    void controlResponse(const QJsonObject& response);
    void initializeReply(const QJsonObject& reply);
    void systemInit(const QJsonObject& init);
    void maybeReadbacksDone();
    void streamEvent(const QJsonObject& record);
    void assistantMessage(const QJsonObject& record);
    void result(const QJsonObject& record);
    void rateLimit(const QJsonObject& record);
    void usageReply(const QJsonObject& reply);
    void beginTurn(const QString& id);
    bool control(const QString& subtype, const QJsonObject& fields = {});
    bool writeUser(const Message& message);
    void flushQueue();
    void startFailed(const QString& explanation,
                     AssistantProvider::FailureKind kind = AssistantProvider::FailureKind::Other);
    void loginOutput();
    void emitUsage();
};

}  // namespace edi_app

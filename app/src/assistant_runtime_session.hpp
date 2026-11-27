// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJsonArray>
#include <QJsonObject>
#include <QObject>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include "assistant_provider.hpp"

namespace edi_app {

/// What a runtime session is started with (ADR-0108 §4, §5). The provider fills it; the session builds its own
/// arguments and environment from it.
struct AssistantRuntimeLaunch {
    QString executable;   ///< the runtime binary (bundled or the developer override)
    QString guard;        ///< edi's lifetime guard, which also serves as the tool bridge (`guard mcp`)
    QString workspace;    ///< edi's prepared workspace, the runtime's working folder
    QString instructions; ///< edi's instruction text for the thread
    QString skillsDir;    ///< the staged, verified skills (`<workspace>/.agents/skills`)
    QStringList skills;   ///< the ids that discovery must report
    QJsonObject toolServer;  ///< the MCP stdio server entry: {command, args, env}
    /// The tool names edi's server lists (`request_user_input` included); a process's tool readback must show
    /// exactly these, in the runtime's own spelling, plus the skill loader.
    QStringList expectedTools;
    quint64 toolTimeoutMs = 0;  ///< edi's longest native deadline, given to the runtime for edi's tools
    AssistantAccountRef account;
    QProcessEnvironment environment;  ///< the app's environment; the session removes and sets per ADR-0108
};

/// One runtime's side of a provider (Claude's stream-json, Copilot's ACP), in normalized terms. The translator
/// (`AssistantRuntimeTranslator`) maps these onto edi's assistant protocol for the view model. Tool calls and
/// questions do not pass through the session: they reach edi through its tool server.
class AssistantRuntimeSession : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    ~AssistantRuntimeSession() override = default;

    /// Start the runtime and do every readback before input (identity, tools, skills). Emits `ready` or `failed`.
    virtual bool start(const AssistantRuntimeLaunch& launch) = 0;
    /// Stop the process; late output is dropped.
    virtual void retire() = 0;
    virtual quint64 generation() const noexcept = 0;

    /// The runtime's own sign-in (browser or device flow) in the account's home. Emits `signInOpened`, then
    /// `signInFinished`.
    virtual void signIn(const AssistantRuntimeLaunch& launch) = 0;
    virtual void cancelSignIn() = 0;
    /// What the user typed or chose for the sign-in process's prompt (a code, or yes/no). Written only to that
    /// process's input; never stored, logged or recorded.
    virtual void answerSignIn(const QString& input) = 0;
    /// The runtime's own sign-out for the account's home. Emits `signedOut`.
    virtual void signOut(const AssistantRuntimeLaunch& launch) = 0;

    /// The tool names edi's server now lists, for every process started after this call (see `expectedTools`).
    virtual void setExpectedTools(const QStringList& names) { Q_UNUSED(names); }
    /// Open a thread: new when `resumeId` is empty, else resume it. Emits `threadOpened` only after the process that
    /// will take the thread's input has passed its readbacks.
    virtual void openThread(const QString& resumeId, const QString& model, const QString& effort) = 0;
    /// Send one user message. While a turn runs the session steers when its runtime can, else queues.
    virtual void sendMessage(const QString& thread, const QString& clientMessageId, const QString& text) = 0;
    virtual void cancelTurn(const QString& thread) = 0;
    virtual void selectModel(const QString& thread, const QString& model, const QString& effort) = 0;
    virtual bool reportsUsage() const noexcept = 0;

signals:
    /// Every readback passed: identity {email, plan, host}, the effective tool names, the discovered skills.
    void ready(const QJsonObject& identity, const QStringList& tools, const QStringList& skills);
    /// A signed-out home, an identity other than the account's, or a refusal (no seat, policy). Plain words.
    void accountRefused(const QString& reason, bool signedOut);
    void signInOpened(const QString& url, const QString& code, const QString& prompt);
    void signInFinished(bool success, const QString& message);
    void signedOut();
    /// Catalogue rows {id, displayName, efforts: [..], defaultEffort} (defaultEffort may be empty).
    void modelsListed(const QJsonArray& models);
    void threadOpened(const QString& thread);
    void turnStarted(const QString& thread, const QString& turn);
    /// Streamed assistant text; `item` names one message within the turn.
    void textDelta(const QString& thread, const QString& turn, const QString& item, const QString& delta);
    /// A completed assistant message or reasoning summary: {type: agentMessage|reasoning, id, text}.
    void itemCompleted(const QString& thread, const QString& turn, const QJsonObject& item);
    /// The runtime's own record of a tool use, for pairing with the tool server's call (name, arguments, its id).
    void toolUse(const QString& thread, const QString& turn, const QString& tool, const QJsonObject& arguments,
                 const QString& runtimeId);
    /// A tool the session must not offer appeared (a built-in): the translator ends the turn and retires.
    void foreignTool(const QString& thread, const QString& turn, const QString& tool);
    /// status: completed | interrupted | failed; error {message, signedOut?} when failed.
    void turnFinished(const QString& thread, const QString& turn, const QString& status, const QJsonObject& error);
    /// {available, stale, buckets: [{window: session|weekly, usedPercent, resetsAt}], observedAt}
    void usageChanged(const QJsonObject& snapshot);
    void failed(const QString& explanation, AssistantProvider::FailureKind kind);
};

}  // namespace edi_app

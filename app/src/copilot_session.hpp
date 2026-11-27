// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <functional>
#include <optional>
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QPointer>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QTimer>
#include "assistant_process.hpp"
#include "assistant_runtime_session.hpp"

namespace edi_app {

/// GitHub Copilot through the Copilot CLI's Agent Client Protocol server (ADR-0108 §5): one process per account,
/// one ACP session per thread, JSON-RPC 2.0 over stdio. Construct and call on the owner thread.
class CopilotSession final : public AssistantRuntimeSession {
    Q_OBJECT
public:
    /// `accountsRoot` is edi's accounts folder (`<AppLocalData>/assistant/accounts`); sign-out deletes only an
    /// account home directly under its `copilot` folder. Empty means that default location.
    explicit CopilotSession(QString accountsRoot = {}, QObject* parent = nullptr);
    ~CopilotSession() override;

    /// The closed tool list: the skill loader and `edi-<name>` for each of edi's tools. Without `expectedTools`
    /// the static catalogue and `request_user_input` stand in, since the process may start before the thread's
    /// catalogue is known.
    static QStringList availableTools(const QStringList& expectedTools);
    /// The app's variables the child may inherit: platform basics, proxies and certificates. `LC_*` is taken too.
    static const QStringList& allowedEnvironment();
    /// The runtime's arguments for a prepared workspace.
    static QStringList arguments(const QString& workspace, const QStringList& availableTools);
    /// The child's environment for an account, built from the allow-list and edi's settings; also used for
    /// `copilot login`. Empty with `explanation` set when the account home or the empty GitHub CLI folder cannot
    /// be used.
    static std::optional<QProcessEnvironment> environment(const AssistantRuntimeLaunch& launch,
                                                          QString* explanation);

    bool start(const AssistantRuntimeLaunch& launch) override;
    void retire() override;
    quint64 generation() const noexcept override;

    void signIn(const AssistantRuntimeLaunch& launch) override;
    void cancelSignIn() override;
    /// Yes or no for the CLI's question whether to keep the token in a plain file (No when nobody answers);
    /// any other input goes to the sign-in process as one line.
    void answerSignIn(const QString& input) override;
    void signOut(const AssistantRuntimeLaunch& launch) override;
    void removeAccount(const AssistantRuntimeLaunch& launch) override;

    void openThread(const QString& resumeId, const QString& model, const QString& effort) override;
    void sendMessage(const QString& thread, const QString& clientMessageId, const QString& text) override;
    void cancelTurn(const QString& thread) override;
    void selectModel(const QString& thread, const QString& model, const QString& effort) override;
    bool reportsUsage() const noexcept override { return false; }

private:
    using Reply = std::function<void(const QJsonObject& result, const QJsonObject& error)>;
    struct ToolCall {
        QString name;
        QJsonObject arguments;
        bool reported = false;
    };
    struct Thread {
        QString id;
        bool loading = false, running = false, cancelling = false;
        QString turn;
        QStringList queue;
        QString messageId, messageText, thoughtId, thoughtText;
        int items = 0;
        QHash<QString, ToolCall> tools;
        QJsonArray configOptions;
    };

    bool request(const QString& method, const QJsonObject& params, Reply reply);
    bool notify(const QString& method, const QJsonObject& params);
    void answer(const QJsonValue& id, const QJsonObject& result);
    void receive(const QJsonObject& record);
    void serverRequest(const QJsonValue& id, const QString& method, const QJsonObject& params);
    void sessionUpdate(const QJsonObject& params);
    void fail(const QString& explanation, AssistantProvider::FailureKind kind);
    void refuse(const QJsonObject& error, const QString& fallback);
    QString withNotices(const QString& message);

    void initialized(const QJsonObject& result);
    void probeOpened(const QJsonObject& result);
    void checkSkills();
    struct User {
        QString login;
        QStringList hosts;
        bool signedOut = false;
    };
    static User parseUser(const QString& text);
    /// Run one CLI command in a session and hand over its text, or the refusal.
    void runCommand(const QString& session, const QString& command,
                    std::function<void(const QJsonObject&, const QString&)> done);
    /// Select the account's login with `/user switch`, then compare `/user show` with the account. `refused`
    /// defaults to `accountRefused` and a retire.
    void checkIdentity(const QString& session, std::function<void(const QString&)> pass,
                       std::function<void(const QString&, bool)> refused = {});
    void finishStart(const QString& login);
    void readbackExpired();

    void logout();
    void unconfirmed(const QString& reason);
    void removeHome(const AssistantAccountRef& account);

    void configure(const QString& session, const QString& model, const QString& effort, bool open, bool verify);
    void emitModels(const QJsonArray& configOptions);
    void startTurn(const QString& session, const QString& text);
    void finishTurn(const QString& session, const QString& status, const QJsonObject& error);
    void flushMessage(Thread& thread);
    void flushThought(Thread& thread);
    void toolUpdate(Thread& thread, const QJsonObject& update);

    void loginOutput();
    void loginFinished(int exitCode, QProcess::ExitStatus status);
    void endSignIn(bool success, const QString& message);

    QString accounts_root_;
    AssistantProcess process_;
    AssistantRuntimeLaunch launch_;
    QStringList available_tools_;
    quint64 failed_generation_ = 0;
    bool has_failed_ = false;
    qint64 next_id_ = 0;
    QHash<qint64, Reply> pending_;
    QHash<QString, Thread> threads_;
    QStringList notices_;

    // The start's readbacks.
    QTimer readback_timer_;
    bool ready_ = false, can_load_ = false, can_logout_ = false;
    QString probe_, spare_;
    bool probe_listed_ = false, checking_start_ = false;
    QStringList commands_;
    QHash<QString, QStringList> identity_text_;
    QJsonArray probe_options_;
    int turns_ = 0;

    // `copilot login`.
    QPointer<QProcess> login_;
    QTimer login_timer_, login_answer_timer_;
    QString login_buffer_, login_url_, login_code_, login_last_line_, login_host_;
    bool login_asked_ = false;
};

}  // namespace edi_app

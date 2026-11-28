// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <deque>
#include <functional>
#include <memory>
#include <QElapsedTimer>
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QPointer>
#include <QStringList>
#include <QTimer>
#include "assistant_provider.hpp"
#include "assistant_runtime_session.hpp"

namespace edi_app {
class AssistantToolServer;

/// The provider for Claude and GitHub Copilot (ADR-0108 §1). It owns one AssistantRuntimeSession and one
/// AssistantToolServer and answers edi's assistant protocol for them as the Codex app-server does: requests are
/// answered from the session's normalized events, tool calls and questions from the tool server become
/// `item/tool/call` and `item/tool/requestUserInput` server requests. Responses, events and server requests are
/// delivered from the event loop, after the call that caused them has returned, in the order they arose.
class AssistantRuntimeTranslator final : public AssistantProvider {
    Q_OBJECT
public:
    /// `launch` is the template the session is started with; start() fills the workspace, the guard, the tool server
    /// entry and, when empty, the staged skill ids.
    AssistantRuntimeTranslator(AssistantProviderId provider, std::unique_ptr<AssistantRuntimeSession> session,
                               AssistantRuntimeLaunch launch, QObject* parent = nullptr,
                               std::shared_ptr<const void> releaseOwner = {});
    ~AssistantRuntimeTranslator() override;

    AssistantProviderId providerId() const noexcept override { return provider_; }
    QString runtimeExecutable() const override { return launch_.executable; }
    QJsonObject threadPolicy() const override;
    QString accountKind() const override { return assistant_provider_key(provider_); }
    void setKnownThreads(const QJsonArray& threads) override { known_threads_ = threads; }
    OutputOwnerState outputOwnerState() const noexcept override;
    bool start(const QString& executable, const QString& workspace) override;
    QString request(const QString& method, const QJsonObject& params,
                    const std::function<bool(const QString&)>& prepare = {}) override;
    bool notification(const QString& method, const QJsonObject& params = {}) override;
    bool answer(const QJsonValue& originalId, const QJsonObject& result, void* preparation = nullptr,
                bool (*handoff)(void*) noexcept = nullptr, const std::function<bool()>& admit = {}) override;
    bool reject(const QJsonValue& originalId) override;
    void resolved(const QJsonValue& originalId) override;
    bool deferServerRequest(const QJsonValue& originalId, quint64 originalGeneration) override;
    void resumeDeferredRequests(quint64 originalGeneration) override;
    void activity() override;
    quint64 outputGeneration() const noexcept override { return generation_; }
    bool optionalUsageBackpressured() const noexcept override { return false; }
    void retire() override;
    /// Claude's own `claude auth logout` for the account, also when no runtime runs (e.g. after a refused identity).
    bool signOutDisconnected() override;
    void beginOperation(quint64 totalMs, quint64 idleMs) override;
    void settleOperation() override;
    bool beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    bool endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    bool beginNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    bool setNativeWorkWaiting(const QJsonValue& originalRequestId, quint64 originalGeneration, bool waiting) override;
    bool endNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    FailureKind failureKind() const noexcept override { return failure_kind_; }
    bool failureActive() const noexcept override { return failed_ && failure_generation_ == generation_; }

private:
    enum class Account : unsigned char { Unknown, Ready, SignedOut };
    struct Waiting {
        QString id, method;
        QJsonObject params;
    };
    struct ServerRequest {
        QJsonValue id;
        QString method;
        QJsonObject params;
        quint64 order = 0;
        bool deferred = false;
        QJsonValue toolId;  // the tool server's request id
        bool question = false;
        bool closed = false;  // the runtime cancelled it or its turn ended; an answer is dropped
    };
    struct ToolCall {
        QJsonValue toolId;
        QString tool;
        QJsonObject arguments;
    };
    struct Message {
        QString type, text;
        bool completed = false;
    };
    struct Post {
        quint64 generation = 0;
        std::function<void()> run;
    };

    // Delivery to the view model.
    void post(std::function<void()> run);
    void schedule();
    void drain();
    void respond(const QString& id, const QString& method, const QJsonObject& result);
    void refuse(const QString& id, const QString& method, int code, const QString& message);
    void notify(const QString& method, const QJsonObject& params);
    void fail(const QString& explanation, FailureKind kind = FailureKind::Other);
    void stopRuntime();
    void release();
    void clearState();

    // Requests.
    void handle(const QString& id, const QString& method, const QJsonObject& params);
    bool answerable(const Waiting& waiting) const;
    void answerWaiting(const Waiting& waiting);
    void service();
    void openThread(const QString& id, const QString& method, const QJsonObject& params);
    void startTurn(const QString& id, const QJsonObject& params);
    void steerTurn(const QString& id, const QJsonObject& params);
    void interruptTurn(const QString& id, const QJsonObject& params);
    QJsonObject accountResult() const;
    QJsonObject modelResult() const;
    QJsonObject skillResult(const QJsonObject& params) const;
    QJsonObject usageResult() const;
    QJsonObject threadObject(const QString& thread) const;
    QJsonObject readback(const QString& effortKey) const;
    bool writeInstructions(const QString& text) const;
    void bindTools();
    void answerThread();

    // Session events.
    void onReady(const QJsonObject& identity, const QStringList& tools, const QStringList& skills);
    void onAccountRefused(const QString& reason, bool signedOut);
    void onSignInOpened(const QString& url, const QString& code, const QString& prompt, bool browserOpened);
    void onSignInFinished(bool success, const QString& message);
    void onSignedOut();
    void onModelsListed(const QJsonArray& models);
    void onThreadOpened(const QString& thread);
    void onTurnStarted(const QString& thread, const QString& turn);
    void onTextDelta(const QString& thread, const QString& turn, const QString& item, const QString& delta);
    void onItemCompleted(const QString& thread, const QString& turn, const QJsonObject& item);
    void onForeignTool(const QString& thread, const QString& turn, const QString& tool);
    void onTurnFinished(const QString& thread, const QString& turn, const QString& status, const QJsonObject& error);
    void onUsageChanged(const QJsonObject& snapshot);
    bool currentTurn(const QString& thread, const QString& turn) const;
    void startMessage(const QString& item, const QString& type);
    void finishTurn(QString status, QJsonObject error);

    // Tool server events.
    void onToolCall(const QJsonValue& toolId, const QString& tool, const QJsonObject& arguments);
    void onToolCancelled(const QJsonValue& toolId);
    void onToolsDisconnected();
    void onToolsListed();
    void admitCall(const ToolCall& call);
    void completeCall(const ServerRequest& request, bool success, const QJsonArray& contentItems);

    // Deadlines, as CodexAgent keeps them.
    bool finishHumanWait();
    bool accountWaits(qint64 now);
    bool operationExpired(qint64 now) const noexcept;
    void checkDeadline();
    static QString idKey(const QJsonValue& value);

    const AssistantProviderId provider_;
    const std::unique_ptr<AssistantRuntimeSession> session_;
    QJsonArray known_threads_;  // edi's records, answered for thread/list
    const AssistantRuntimeLaunch template_;
    AssistantRuntimeLaunch launch_;
    const std::shared_ptr<const void> release_owner_;
    std::shared_ptr<const void> lease_;  // held while a runtime may still produce output
    QPointer<AssistantToolServer> tools_;

    quint64 generation_ = 0, next_id_ = 0, bind_serial_ = 0, server_sequence_ = 0;
    bool live_ = false, releasing_ = false, failed_ = false;
    FailureKind failure_kind_ = FailureKind::Other;
    quint64 failure_generation_ = 0;
    std::deque<Post> posts_;
    bool drain_scheduled_ = false;

    Account account_ = Account::Unknown;
    QJsonObject identity_;
    QStringList skills_;
    QJsonArray models_;
    bool models_known_ = false;
    QJsonObject usage_;
    QList<Waiting> waiting_;
    QHash<QString, qint64> ack_deadlines_;  // requests that wait for the session, by id
    QString login_rpc_, login_id_, logout_rpc_;

    QString thread_, thread_rpc_, thread_method_, thread_target_;
    QString opened_thread_;     // opened by the session, answered once edi's tools are listed
    bool tools_listed_ = false;  // the current runtime process listed edi's tools
    QString model_, effort_;

    QString turn_, session_turn_;  // edi's turn id, and the runtime's turn currently serving it
    bool interrupting_ = false, held_ = false;
    int follow_ups_ = 0;
    QTimer hold_;
    QHash<QString, Message> messages_;
    QStringList message_order_;
    QHash<QString, bool> calls_completed_;  // call item id -> completed
    QList<ToolCall> early_calls_;           // calls that arrived between two runtime turns of one protocol turn

    QHash<QString, ServerRequest> requests_;

    QElapsedTimer clock_;
    QTimer timer_;
    qint64 operation_start_ = -1, last_activity_ = 0;
    qint64 human_wait_start_ = -1;
    QString human_wait_id_;
    QString native_work_id_;
    bool native_work_waiting_ = false;
    qint64 wait_accounted_at_ = -1;
    quint64 total_ms_ = 0, idle_ms_ = 0;
};
}  // namespace edi_app

// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include <optional>
#include <QObject>
#include <functional>
#include <QHash>
#include <QSet>
#include <QJsonObject>
#include <QJsonValue>
#include <QProcess>
#include <QProcessEnvironment>
#include <QPointer>
#include <QTimer>
#include <QElapsedTimer>
#include "edi/assistant_limits.hpp"
#include "assistant_provider.hpp"

namespace edi_app {
bool codex_encoded_size(const QJsonValue&, quint64 cap, quint64& size);
// Measure actual retained data without a cumulative work quota.
bool codex_measured_size(const QJsonValue&, quint64& size);
quint64 codex_json_capacity(quint64 bytes);
// App-internal transport for the pinned runtime, ChatGPT's provider (ADR-0108). It owns no account
// or provider protocol; the VM owns admitted rows, approvals and scientific state.
class CodexAgent final : public AssistantProvider {
    Q_OBJECT
public:
    explicit CodexAgent(QObject* parent = nullptr,std::shared_ptr<const void> releaseOwner = {});
    OutputOwnerState outputOwnerState() const noexcept override;
    static QString executable();
    static QString policyPatch();
    AssistantProviderId providerId() const noexcept override { return AssistantProviderId::ChatGpt; }
    QString runtimeExecutable() const override { return executable(); }
    QString runtimePolicyPatch() const override { return policyPatch(); }
    QJsonObject threadPolicy() const override;
    ~CodexAgent() override;
    /// An added account's own empty folder, given to the runtime as CODEX_HOME; empty for the first ChatGPT
    /// account, which keeps the runtime's ordinary profile (ADR-0108 §8).
    void setAccountHome(const QString& home) { account_home_ = home; }
    /// Start with the app's own environment, plus CODEX_HOME when the account has its own home.
    bool start(const QString& executable, const QString& workspace) override;
    /// Start with exactly `environment`, which names an added account's own CODEX_HOME (ADR-0108 §8).
    bool start(const QString& executable, const QString& workspace, const QProcessEnvironment& environment);
    QString request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare = {}) override;
    bool notification(const QString& method, const QJsonObject& params = {}) override;
    // Borrowed synchronous preparation runs only after the original wire peak fits.
    // No callback/context is retained. The native handoff remains a borrowed
    // function pointer; human answers may add a synchronous admission predicate.
    bool answer(const QJsonValue& originalId, const QJsonObject& result, void* preparation = nullptr,
                bool (*handoff)(void*) noexcept = nullptr,
                const std::function<bool()>& admit = {}) override;
    bool reject(const QJsonValue& originalId) override;
    void resolved(const QJsonValue& originalId) override;
    bool deferServerRequest(const QJsonValue& originalId,quint64 originalGeneration) override;
    void resumeDeferredRequests(quint64 originalGeneration) override;
    void activity() override;
    quint64 outputGeneration() const noexcept override { return generation_; }
    // Optional usage waits only for genuine original transport backpressure.
    bool optionalUsageBackpressured() const noexcept override;
    void retire() override;
    void beginOperation(quint64 totalMs, quint64 idleMs) override;
    void settleOperation() override;
    bool beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    bool endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    // One exact correlated local tool owns idle-only suspension. Only its real
    // inactive-window presentation wait additionally suspends inference total.
    bool beginNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    bool setNativeWorkWaiting(const QJsonValue& originalRequestId, quint64 originalGeneration, bool waiting) override;
    bool endNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) override;
    FailureKind failureKind() const noexcept override { return failure_kind_; }
    bool failureActive() const noexcept override { return failed_ && failure_generation_ == generation_; }

private:
    friend struct CodexAgentTestAccess; // Defined only by the independent finite native probe.
    class Process;
    const std::shared_ptr<const void> release_owner_;
    QString account_home_;
    quint64 process_birth_=0;
    bool process_owner_alive_=false;
    void processOwnerReleased(quint64) noexcept;
    void maybeOwnersReleased() noexcept;
    bool startWith(const QString& executable, const QString& workspace, const QProcessEnvironment* environment);
    using Limits = edi::assistant::Limits;
    QProcess* process_ = nullptr;
    QPointer<QProcess> retired_process_;
    quint64 active_frames_=0;
    bool reading_=false, eof_pending_=false;
    // How the guard said the runtime ended (see app/tools/assistant_guard.cpp), and the number for the message.
    int exit_code_=-1;
    QString exit_detail_;
    QByteArray incoming_;
    // One original-byte required-write holding slot, only for an already-issued
    // optional record occupying the physical QProcess queue. No partial retry.
    QByteArray deferred_required_;
    quint64 optional_queued_bytes_ = 0;
    bool preempting_optional_usage_ = false;
    qint64 deferred_deadline_ = -1;
    QHash<QString, QString> pending_;
    QSet<QString> optional_usage_ids_; // Outstanding or timed-out exact issued IDs, bounded by completed_calls.
    QHash<QString, qint64> pending_deadlines_;
    QHash<QString, quint64> pending_sizes_, server_sizes_;
    struct ServerRequest {QJsonValue id;QString method;QJsonObject params;quint64 order=0;bool deferred=false;};
    QHash<QString, ServerRequest> server_requests_;
    quint64 server_sequence_=0;
    quint64 next_id_ = 0, generation_ = 0;
    bool failed_ = false;
    FailureKind failure_kind_ = FailureKind::Other;
    quint64 failure_generation_ = 0;
    quint64 pending_bytes_ = 0;
    QElapsedTimer clock_;
    QTimer timer_;
    qint64 operation_start_ = -1, last_activity_ = 0;
    qint64 human_wait_start_ = -1;
    QString human_wait_id_; // Shares the original outstanding request key; cleared before its removal.
    bool finishHumanWait();
    QString native_work_id_; // Shares the same already-retained outstanding key.
    bool native_work_waiting_ = false;
    qint64 wait_accounted_at_ = -1;
    bool accountWaits(qint64 now); // Success is callback-free, union of fixed owned roles.
    bool operationExpired(qint64 now) const noexcept;
    quint64 total_ms_ = 0, idle_ms_ = 0, wire_bytes_ = 0, event_count_ = 0;
    bool write(const QJsonObject& envelope, const std::function<bool()>& prepare = {}, bool nonfatalPreflight = false, bool optionalUsage = false,
               void* preparation = nullptr, bool (*handoff)(void*) noexcept = nullptr);
    void read(QProcess* process, quint64 generation, bool finished = false);
    void receive(const QByteArray& record);
    void fail(const char* explanation, FailureKind kind = FailureKind::Other) noexcept;
    void checkDeadline();
    void retireOptionalUsage(const QString& id, UsageDisposition disposition);
    void preemptOptionalUsage();
    void flushRequired() noexcept;
    static QString idKey(const QJsonValue& value);
};
} // namespace edi_app

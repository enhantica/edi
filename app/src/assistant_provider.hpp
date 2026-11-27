// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <functional>
#include <QJsonObject>
#include <QJsonValue>
#include <QObject>
#include <QString>

namespace edi_app {

/// The assistant providers edi offers. The settings keys are chatgpt, claude and copilot (ADR-0108).
enum class AssistantProviderId : unsigned char { ChatGpt, Claude, Copilot };

/// One account of one provider. `home` is the runtime's config home edi created for it, empty for the default
/// ChatGPT login; edi never opens anything inside it.
struct AssistantAccountRef {
    AssistantProviderId provider = AssistantProviderId::ChatGpt;
    QString id, home, host;
    QString email;  ///< the identity the record holds, compared with the runtime's readback; empty before sign-in
};

/// The settings key of a provider: chatgpt, claude or copilot.
QString assistant_provider_key(AssistantProviderId id);

/// The transport between the view model and one assistant runtime or connection (ADR-0055's provider transport,
/// ADR-0108 §1). A runtime provider takes edi's assistant protocol (the app-server JSON-RPC vocabulary) and maps it
/// onto its runtime; the view model reaches a runtime only through this interface. Construct and call on the owner
/// thread; signals use direct connections.
class AssistantProvider : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    ~AssistantProvider() override = default;

    enum class OutputOwnerState { Unobserved, Live, Releasing, Released };
    enum class UsageDisposition { Preempted, TimedOut };
    Q_ENUM(UsageDisposition)
    // First local transport cause, latched before the failed signal.
    enum class FailureKind : unsigned char { Other, LocalCapacity, OperationDeadline };

    virtual AssistantProviderId providerId() const noexcept = 0;
    /// True when the provider speaks edi's assistant protocol; false for ADR-0056's direct connection.
    virtual bool speaksRuntimeProtocol() const noexcept { return true; }
    /// The runtime this provider starts, or empty when it is not installed.
    virtual QString runtimeExecutable() const = 0;
    /// The source patch hash of a runtime built with edi's policy patch, else empty.
    virtual QString runtimePolicyPatch() const { return {}; }
    /// The account kind the runtime's account readback names for a signed-in account: chatgpt, claude or copilot.
    virtual QString accountKind() const { return QStringLiteral("chatgpt"); }
    /// The thread settings a thread's readback must show, field by field. The view model compares only these.
    virtual QJsonObject threadPolicy() const = 0;

    virtual OutputOwnerState outputOwnerState() const noexcept = 0;
    virtual bool start(const QString& executable, const QString& workspace) = 0;
    virtual QString request(const QString& method, const QJsonObject& params,
                            const std::function<bool(const QString&)>& prepare = {}) = 0;
    virtual bool notification(const QString& method, const QJsonObject& params = {}) = 0;
    virtual bool answer(const QJsonValue& originalId, const QJsonObject& result, void* preparation = nullptr,
                        bool (*handoff)(void*) noexcept = nullptr, const std::function<bool()>& admit = {}) = 0;
    virtual bool reject(const QJsonValue& originalId) = 0;
    virtual void resolved(const QJsonValue& originalId) = 0;
    virtual bool deferServerRequest(const QJsonValue& originalId, quint64 originalGeneration) = 0;
    virtual void resumeDeferredRequests(quint64 originalGeneration) = 0;
    virtual void activity() = 0;
    virtual quint64 outputGeneration() const noexcept = 0;
    virtual bool optionalUsageBackpressured() const noexcept = 0;
    virtual void retire() = 0;
    virtual void beginOperation(quint64 totalMs, quint64 idleMs) = 0;
    virtual void settleOperation() = 0;
    virtual bool beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) = 0;
    virtual bool endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) = 0;
    virtual bool beginNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) = 0;
    virtual bool setNativeWorkWaiting(const QJsonValue& originalRequestId, quint64 originalGeneration, bool waiting) = 0;
    virtual bool endNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) = 0;
    virtual FailureKind failureKind() const noexcept = 0;
    virtual bool failureActive() const noexcept = 0;

signals:
    void outputOwnersReleased();  // Hint only; recheck owner state and room.
    void started();
    void response(const QString& id, const QString& method, const QJsonObject& envelope);
    void serverRequest(const QJsonValue& originalId, const QString& method, const QJsonObject& params);
    // A signal, not an override of QObject::event: its name is the protocol's and code connects to it by name.
#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Woverloaded-virtual"
#endif
    void event(const QString& method, const QJsonObject& params);
#if defined(__clang__)
#pragma clang diagnostic pop
#endif
    void failed(const QString& explanation);
    // Only a correlated optional usage read's disposition; not a provider error.
    void optionalUsageUnavailable(const QString& id, UsageDisposition disposition);
    // Hint after the write queue drains; never a retry loop.
    void optionalUsageReady();
};

}  // namespace edi_app

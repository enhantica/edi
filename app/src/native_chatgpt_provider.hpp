// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include "assistant_provider.hpp"
#include "chatgpt_connection.hpp"

namespace edi_app {

/// ChatGPT through ADR-0056's direct connection, the diagnostic door of ADR-0057 (ADR-0108 §1). It offers the
/// connection's own operations and refuses edi's assistant protocol. Credential handling stays the connection's.
class NativeChatGptProvider final : public AssistantProvider {
    Q_OBJECT
public:
    NativeChatGptProvider(std::function<void(const edi::assistant::JsonText&)> eventSink,
                          edi::assistant::native::NativeDependencies dependencies, QObject* parent = nullptr);
    ~NativeChatGptProvider() override;

    // The connection's operations, unchanged (ADR-0056).
    void poll();
    edi::assistant::Reply sign_in();
    edi::assistant::Reply connect_saved(const std::string& registrationId);
    edi::assistant::Reply send(const edi::assistant::JsonText& request);
    void cancel(const std::string& turnId);
    void sign_out();
    edi::assistant::JsonText state() const;

    AssistantProviderId providerId() const noexcept override { return AssistantProviderId::ChatGpt; }
    bool speaksRuntimeProtocol() const noexcept override { return false; }
    QString runtimeExecutable() const override { return {}; }
    QJsonObject threadPolicy() const override { return {}; }
    OutputOwnerState outputOwnerState() const noexcept override { return OutputOwnerState::Unobserved; }
    bool start(const QString&, const QString&) override { return false; }
    QString request(const QString&, const QJsonObject&, const std::function<bool(const QString&)>& = {}) override {
        return {};
    }
    bool notification(const QString&, const QJsonObject& = {}) override { return false; }
    bool answer(const QJsonValue&, const QJsonObject&, void* = nullptr, bool (*)(void*) noexcept = nullptr,
                const std::function<bool()>& = {}) override {
        return false;
    }
    bool reject(const QJsonValue&) override { return false; }
    void resolved(const QJsonValue&) override {}
    bool deferServerRequest(const QJsonValue&, quint64) override { return false; }
    void resumeDeferredRequests(quint64) override {}
    void activity() override {}
    quint64 outputGeneration() const noexcept override { return 0; }
    bool optionalUsageBackpressured() const noexcept override { return false; }
    void retire() override {}
    void beginOperation(quint64, quint64) override {}
    void settleOperation() override {}
    bool beginHumanWait(const QJsonValue&, quint64) override { return false; }
    bool endHumanWait(const QJsonValue&, quint64) override { return false; }
    bool beginNativeWork(const QJsonValue&, quint64) override { return false; }
    bool setNativeWorkWaiting(const QJsonValue&, quint64, bool) override { return false; }
    bool endNativeWork(const QJsonValue&, quint64) override { return false; }
    FailureKind failureKind() const noexcept override { return FailureKind::Other; }
    bool failureActive() const noexcept override { return false; }

private:
    std::unique_ptr<edi::assistant::native::ChatGptConnection> connection_;
};

}  // namespace edi_app

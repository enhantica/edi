// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <utility>
#include <vector>
#include <QByteArray>
#include <QUrl>
#include <memory>
#include "edi/assistant.hpp"

namespace edi::assistant::native {

using HttpHeaders = std::vector<std::pair<QByteArray, QByteArray>>;
enum class HttpMethod { get, post };
enum class HttpFailure { none, cancelled, timeout, tls, network };
struct HttpRequest {
    HttpMethod method;
    QUrl url;
    HttpHeaders headers;
    QByteArray body;
    std::uint64_t body_limit_bytes; // Zero: streaming work has no cumulative body quota.
    std::uint64_t timeout_ms; // Zero: active work has no operation expiry.
};
struct HttpCallbacks {
    std::function<void(int status, HttpHeaders headers)> headers;
    std::function<void(QByteArray bytes)> data;
    std::function<void(HttpFailure failure)> finished;
};
class HttpOperation {
public:
    virtual ~HttpOperation() = default;
    virtual void cancel() noexcept = 0;
};
enum class RecordKind { host, registration, credentials };
struct RecordKey {
    RecordKind kind;
    std::string id;
};
enum class StoreStatus { ok, absent, failed };
struct RecordRead {
    StoreStatus status;
    QByteArray bytes;
};
struct RegistrationList {
    StoreStatus status;
    std::vector<std::string> ids;
};
struct NativeDependencies {
    std::function<std::unique_ptr<HttpOperation>(HttpRequest, HttpCallbacks)> request;
    std::function<bool(const QUrl&)> open_browser;
    std::function<RecordRead(const RecordKey&)> read_record;
    std::function<StoreStatus(const RecordKey&, const QByteArray&)> write_record;
    std::function<StoreStatus(const RecordKey&)> erase_record;
    std::function<RegistrationList()> list_registrations;
    std::function<std::int64_t()> unix_seconds;
    std::function<std::uint64_t()> monotonic_ms;
};

/// Native SIWC connection (ADR-0055). Uses its own protected registrations, never another app's credentials.
/// Construct and call on the Qt event-loop thread. The sink must queue controller input rather than reenter it.
class ChatGptConnection {
   public:
    explicit ChatGptConnection(std::function<void(const JsonText&)> event_sink);
    ChatGptConnection(std::function<void(const JsonText&)> event_sink, NativeDependencies dependencies);
    ~ChatGptConnection();
    /// Settle due transport/auth deadlines using the injected owner-thread clocks.
    void poll();
    ChatGptConnection(const ChatGptConnection&) = delete;
    ChatGptConnection& operator=(const ChatGptConnection&) = delete;
    Reply sign_in();
    Reply connect_saved(std::string registration_id);
    Reply send(const JsonText& request);
    void cancel(std::string turn_id);
    void sign_out();
    JsonText state() const;

   private:
    struct State;
    std::unique_ptr<State> state_;
};
}  // namespace edi::assistant::native

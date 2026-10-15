// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QObject>
#include <functional>
#include <QHash>
#include <QJsonObject>
#include <QJsonValue>
#include <QProcess>
#include <QTimer>
#include <QElapsedTimer>
#include "edi/assistant_limits.hpp"

namespace edi_app {
bool codex_encoded_size(const QJsonValue&, quint64 cap, quint64& size);
// App-internal transport for the unmodified official runtime. It owns no account
// or provider protocol; the VM owns admitted rows, approvals and scientific state.
class CodexAgent final : public QObject {
    Q_OBJECT
public:
    explicit CodexAgent(QObject* parent = nullptr);
    static QString executable();
    ~CodexAgent() override;
    bool start(const QString& executable, const QString& workspace);
    QString request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare = {});
    bool notification(const QString& method, const QJsonObject& params = {});
    bool answer(const QJsonValue& originalId, const QJsonObject& result);
    bool reject(const QJsonValue& originalId);
    void resolved(const QJsonValue& originalId);
    void activity();
    bool retainOutput(quint64 bytes);
    void retire();
    void beginOperation(quint64 totalMs, quint64 idleMs);
    void settleOperation();
signals:
    void started();
    void response(const QString& id, const QString& method, const QJsonObject& envelope);
    void serverRequest(const QJsonValue& originalId, const QString& method, const QJsonObject& params);
    void event(const QString& method, const QJsonObject& params);
    void failed(const QString& explanation);
private:
    using Limits = edi::assistant::Limits;
    static constexpr qsizetype recordLimit = Limits::message_bytes;
    static constexpr qsizetype pendingLimit = Limits::http_operations;
    QProcess* process_ = nullptr;
    QByteArray incoming_;
    QHash<QString, QString> pending_;
    QHash<QString, qint64> pending_deadlines_;
    QHash<QString, quint64> pending_sizes_, server_sizes_;
    QHash<QString, QJsonValue> server_requests_;
    quint64 next_id_ = 0, generation_ = 0;
    bool failed_ = false;
    quint64 pending_bytes_ = 0, output_bytes_ = 0, record_bytes_ = 0;
    QElapsedTimer clock_;
    QTimer timer_;
    qint64 operation_start_ = -1, last_activity_ = 0;
    quint64 total_ms_ = 0, idle_ms_ = 0, wire_bytes_ = 0, event_count_ = 0;
    bool write(const QJsonObject& envelope, const std::function<bool()>& prepare = {}, bool nonfatalPreflight = false);
    void read(QProcess* process, quint64 generation);
    void receive(const QByteArray& record);
    void fail(const char* explanation) noexcept;
    void checkDeadline();
    static QString idKey(const QJsonValue& value);
};
} // namespace edi_app

// SPDX-License-Identifier: BSD-3-Clause
#include "codex_agent.hpp"
#include "assistant_runtime_config.hpp"
#include <QCoreApplication>
#include <QFile>
#include <stdexcept>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonArray>
#include <QPointer>
#include <QJsonParseError>
#include <cmath>
#include <limits>

namespace edi_app {
namespace {
bool addSize(quint64 n, quint64 cap, quint64& size) {
    if (size > cap || n > cap - size) return false;
    size += n; return true;
}
bool stringSize(const QString& text, quint64 cap, quint64& size) {
    if (!addSize(2, cap, size)) return false;
    for (qsizetype i = 0; i < text.size(); ++i) {
        const auto c = text.at(i).unicode(); quint64 n;
        if (c == '"' || c == '\\' || c == 8 || c == 12 || c == 10 || c == 13 || c == 9) n = 2;
        else if (c < 0x20) n = 6;
        else if (c < 0x80) n = 1;
        else if (c < 0x800) n = 2;
        else if (QChar::isHighSurrogate(c)) {
            if (++i >= text.size() || !text.at(i).isLowSurrogate()) return false;
            n = 4;
        } else if (QChar::isLowSurrogate(c)) return false;
        else n = 3;
        if (!addSize(n, cap, size)) return false;
    }
    return true;
}
bool encodedSize(const QJsonValue& value, quint64 cap, quint64& size, quint64 depth = 0) {
    using L = edi::assistant::Limits;
    if (value.isString()) return stringSize(value.toString(), cap, size);
    if (value.isBool()) return addSize(value.toBool() ? 4 : 5, cap, size);
    if (value.isNull() || value.isUndefined()) return addSize(4, cap, size);
    if (value.isDouble()) {
        if (!std::isfinite(value.toDouble())) return false;
        // A scalar double has bounded fixed-size representation. Qt remains the writer.
        const auto scalar = QJsonDocument(QJsonArray{value}).toJson(QJsonDocument::Compact);
        return addSize(static_cast<quint64>(scalar.size() - 2), cap, size);
    }
    if (++depth > L::json_depth || !addSize(2, cap, size)) return false;
    bool first = true;
    if (value.isObject()) {
        const auto object = value.toObject();
        for (auto it = object.constBegin(); it != object.constEnd(); ++it) {
            if ((!first && !addSize(1, cap, size)) || !stringSize(it.key(), cap, size) ||
                !addSize(1, cap, size) || !encodedSize(it.value(), cap, size, depth)) return false;
            first = false;
        }
    } else {
        for (const auto& child : value.toArray()) {
            if ((!first && !addSize(1, cap, size)) || !encodedSize(child, cap, size, depth)) return false;
            first = false;
        }
    }
    return true;
}
} // namespace
bool codex_encoded_size(const QJsonValue& value, quint64 cap, quint64& size) { return encodedSize(value, cap, size); }
CodexAgent::CodexAgent(QObject* parent) : QObject(parent) {
    clock_.start(); timer_.setInterval(100);
    connect(&timer_, &QTimer::timeout, this, [this] { try { checkDeadline(); } catch (...) { fail("The official agent deadline could not be checked."); } });
    timer_.start();
}
void CodexAgent::beginOperation(quint64 totalMs, quint64 idleMs) {
    if (operation_start_ < 0) { wire_bytes_ = 0; event_count_ = 0; }
    operation_start_ = clock_.elapsed(); last_activity_ = operation_start_;
    total_ms_ = totalMs; idle_ms_ = idleMs;
}
bool CodexAgent::retainOutput(quint64 bytes) {
    if (bytes > Limits::stream_retained_bytes || record_bytes_ > Limits::stream_retained_bytes - bytes ||
        static_cast<quint64>(incoming_.size()) > Limits::stream_retained_bytes - bytes - record_bytes_) {
        fail("The official agent output exceeds retained capacity."); return false;
    }
    output_bytes_ = bytes; return true;
}
void CodexAgent::activity() { last_activity_ = clock_.elapsed(); }
void CodexAgent::settleOperation() {
    operation_start_ = -1; total_ms_ = 0; idle_ms_ = 0;
}
void CodexAgent::checkDeadline() {
    if (failed_) return;
    const auto now = clock_.elapsed();
    for (auto it = pending_deadlines_.constBegin(); it != pending_deadlines_.constEnd(); ++it)
        if (now >= it.value()) { fail("The official agent did not acknowledge a control request in time."); return; }
    if (operation_start_ < 0) return;
    if (now < operation_start_ || now < last_activity_ ||
        (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
        (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_))
        fail("The official agent operation exceeded its deadline.");
}
CodexAgent::~CodexAgent() { retire(); }

QString CodexAgent::idKey(const QJsonValue& value) {
    if (value.isString() && !value.toString().isEmpty() && value.toString().size() <= static_cast<qsizetype>(Limits::id_bytes) && value.toString().toUtf8().size() <= static_cast<qsizetype>(Limits::id_bytes))
        return QStringLiteral("s:") + value.toString();
    if (value.isDouble()) {
        const auto number = value.toDouble();
        if (std::isfinite(number) && std::floor(number) == number && std::abs(number) <= 9007199254740991.0)
            return QStringLiteral("n:") + QString::number(number, 'f', 0);
    }
    return {};
}

QString CodexAgent::executable() {
    if (qEnvironmentVariableIsSet("EDI_CODEX_DEVELOPMENT_EXECUTABLE")) {
        const auto path = qEnvironmentVariable("EDI_CODEX_DEVELOPMENT_EXECUTABLE");
        const QFileInfo file(path);
        if (!file.isAbsolute() || !file.isFile() || !file.isExecutable())
            throw std::runtime_error("The explicit development agent executable is unavailable");
        return file.absoluteFilePath(); // Explicit offline/developer composition, never a silent fallback.
    }
    const auto app = QDir::cleanPath(QCoreApplication::applicationDirPath());
    const auto root = app == QDir::cleanPath(QString::fromUtf8(EDI_CODEX_BUILD_APP_DIR))
        ? QString::fromUtf8(EDI_CODEX_RUNTIME_BUILD_DIR) : QDir(app).absoluteFilePath(QString::fromUtf8(EDI_CODEX_INSTALL_RELATIVE));
    QFile manifest(root + "/codex-package.json");
    if (!manifest.open(QIODevice::ReadOnly) || manifest.size() > static_cast<qint64>(Limits::http_json_bytes)) return {};
    QJsonParseError error;
    const auto parsed = QJsonDocument::fromJson(manifest.read(static_cast<qint64>(Limits::http_json_bytes) + 1), &error);
    if (error.error != QJsonParseError::NoError || !parsed.isObject()) return {};
    const auto metadata = parsed.object();
    if (metadata.value("layoutVersion") != 1 || metadata.value("version") != "0.162.1" ||
        metadata.value("target") != QString::fromUtf8(EDI_CODEX_RUNTIME_TARGET) ||
        metadata.value("variant") != "codex-app-server" || metadata.value("entrypoint") != "bin/codex-app-server" ||
        metadata.value("resourcesDir") != "codex-resources" || metadata.value("pathDir") != "codex-path") return {};
    const auto executable = root + "/bin/codex-app-server";
    if (!QFileInfo(executable).isFile() || !QFileInfo(executable).isExecutable()) return {};
    return executable;
}

bool CodexAgent::start(const QString& executable, const QString& workspace) {
    if (process_ || executable.isEmpty() || !QFileInfo(workspace).isAbsolute() || !QFileInfo(workspace).isDir())
        return false;
    try {
        if (generation_ == std::numeric_limits<quint64>::max()) return false;
        const auto scope = ++generation_;
        failed_ = false; incoming_.clear(); pending_.clear(); server_requests_.clear();
        pending_sizes_.clear(); pending_deadlines_.clear(); server_sizes_.clear();
        pending_bytes_ = 0; output_bytes_ = 0; record_bytes_ = 0; wire_bytes_ = 0; event_count_ = 0;
        auto* process = new QProcess(this);
        process_ = process;
        process->setProgram(executable);
        process->setArguments({QStringLiteral("--listen"), QStringLiteral("stdio://"),
            QStringLiteral("-c"), QStringLiteral("sandbox_workspace_write.writable_roots=[]"),
            QStringLiteral("-c"), QStringLiteral("sandbox_workspace_write.network_access=false"),
            QStringLiteral("-c"), QStringLiteral("sandbox_workspace_write.exclude_slash_tmp=true"),
            QStringLiteral("-c"), QStringLiteral("sandbox_workspace_write.exclude_tmpdir_env_var=true"),
            QStringLiteral("-c"), QStringLiteral("features.shell_zsh_fork=false")});
        process->setWorkingDirectory(workspace);
        process->setProcessChannelMode(QProcess::SeparateChannels);
        // The runtime owns its ordinary profile and managed login. Never assign
        // HOME/home/CODEX_HOME, open config/auth files, or copy provider tokens.
        connect(process, &QProcess::started, this, [this, process, scope] {
            try { if (process_ == process && generation_ == scope && !failed_) emit started(); } catch (...) { fail("The official agent handshake could not be prepared."); }
        });
        connect(process, &QProcess::readyReadStandardOutput, this, [this, process, scope] { read(process, scope); });
        connect(process, &QProcess::readyReadStandardError, this, [this, process, scope] {
            if (process_ != process || generation_ != scope) return;
            try {
            process->setReadChannel(QProcess::StandardError);
            while (process->bytesAvailable() > 0 && !failed_) {
                const auto remaining = Limits::stream_wire_bytes - wire_bytes_;
                if (remaining == 0) { fail("The official agent operation exceeded its wire capacity."); break; }
                const auto discarded = process->read(qMin<quint64>(Limits::http_chunk_bytes, remaining));
                if (discarded.isEmpty()) break;
                wire_bytes_ += static_cast<quint64>(discarded.size());
            }
            process->setReadChannel(QProcess::StandardOutput);
            } catch (...) { fail("The official agent diagnostic channel could not be drained."); }
            // Never put raw runtime stderr (which may contain user data) in a
            // provider failure card or credential log.
        });
        connect(process, &QProcess::errorOccurred, this, [this, process, scope](QProcess::ProcessError) {
            if (process_ == process && generation_ == scope) fail("The official agent process could not continue.");
        });
        connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
                [this, process, scope](int, QProcess::ExitStatus) {
            if (process_ != process || generation_ != scope) return;
            read(process, scope);
            if (!failed_) fail("The official agent process ended. Unfinished work was interrupted.");
            process_ = nullptr;
            process->deleteLater();
        });
        beginOperation(Limits::http_json_ms, 0);
        process->start();
        return true;
    } catch (...) {
        fail("The official agent process could not be prepared.");
        return false;
    }
}

bool CodexAgent::write(const QJsonObject& envelope, const std::function<bool()>& prepare, bool nonfatalPreflight) {
    if (!process_ || failed_ || process_->state() != QProcess::Running) return false;
    checkDeadline(); if (failed_) return false;
    quint64 encoded = 0;
    if (!encodedSize(envelope, Limits::request_bytes, encoded)) {
        if (!nonfatalPreflight) fail("The official agent request exceeds the transport capacity."); return false;
    }
    if (encoded >= Limits::request_bytes || static_cast<quint64>(process_->bytesToWrite()) > Limits::request_bytes - encoded - 1) {
        if (!nonfatalPreflight) fail("The official agent write queue exceeds the transport capacity."); return false;
    }
    const auto wire = QJsonDocument(envelope).toJson(QJsonDocument::Compact);
    if (static_cast<quint64>(wire.size()) != encoded) {
        if (!nonfatalPreflight) fail("The official agent request could not be encoded consistently."); return false;
    }
    const auto line = wire + '\n';
    if (prepare && !prepare()) return false;
    if (process_->write(line) != line.size()) {
        fail("The official agent request could not be delivered."); return false;
    }
    return true;
}

QString CodexAgent::request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare) {
    QString id; bool charged = false;
    const auto discard = [&] {
        pending_.remove(id); pending_deadlines_.remove(id);
        if (charged) pending_bytes_ -= pending_sizes_.take(id); else pending_sizes_.remove(id);
    };
    try {
        if (failed_ || method.isEmpty() || pending_.size() >= pendingLimit || next_id_ == std::numeric_limits<quint64>::max()) return {};
        id = QStringLiteral("edi-%1-%2").arg(generation_).arg(++next_id_);
        quint64 bytes = 0;
        const QJsonObject envelope{{"id", id}, {"method", method}, {"params", params}};
        if (!encodedSize(envelope, Limits::record_bytes, bytes) || bytes > Limits::retained_record_bytes - pending_bytes_) return {};
        pending_.insert(id, method); pending_sizes_.insert(id, bytes);
        pending_deadlines_.insert(id, clock_.elapsed() + static_cast<qint64>(Limits::http_json_ms));
        pending_bytes_ += bytes; charged = true;
        if (!write(envelope, [&] { return !prepare || prepare(id); }, static_cast<bool>(prepare))) { discard(); return {}; }
        return id;
    } catch (...) { discard(); return {}; }
}
bool CodexAgent::notification(const QString& method, const QJsonObject& params) {
    return write({{QStringLiteral("method"), method}, {QStringLiteral("params"), params}});
}
bool CodexAgent::answer(const QJsonValue& originalId, const QJsonObject& result) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !server_requests_.contains(key)) return false;
    // Retire before delivery: an uncertain write never permits a repeated answer.
    const auto id = server_requests_.take(key); pending_bytes_ -= server_sizes_.take(key);
    return write({{QStringLiteral("id"), id}, {QStringLiteral("result"), result}});
}
bool CodexAgent::reject(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !server_requests_.contains(key)) return false;
    const auto id = server_requests_.take(key); pending_bytes_ -= server_sizes_.take(key);
    return write({{"id", id}, {"error", QJsonObject{{"code", -32601}, {"message", "This client does not support this request."}}}});
}
void CodexAgent::resolved(const QJsonValue& originalId) { const auto key = idKey(originalId); server_requests_.remove(key); pending_bytes_ -= server_sizes_.take(key); }
void CodexAgent::read(QProcess* process, quint64 scope) {
    if (process_ != process || generation_ != scope || failed_) return;
    try {
        process->setReadChannel(QProcess::StandardOutput);
        while (process_ == process && generation_ == scope && process->bytesAvailable() > 0 && !failed_) {
            // Bound every app-owned append; do not use readAll on a line that has
            // not yet acquired its delimiter. QProcess/OS buffers are distinct.
            const auto capacity = recordLimit + 1 - incoming_.size();
            if (capacity <= 0) { fail("The official agent response exceeds the transport capacity."); return; }
            checkDeadline(); if (failed_) return;
            const auto bytes = process->read(qMin<qsizetype>(Limits::http_chunk_bytes, capacity));
            if (bytes.isEmpty()) return;
            if (static_cast<quint64>(bytes.size()) > Limits::stream_wire_bytes - wire_bytes_) {
                fail("The official agent operation exceeded its wire capacity."); return;
            }
            wire_bytes_ += static_cast<quint64>(bytes.size());
            if (static_cast<quint64>(incoming_.size()) + static_cast<quint64>(bytes.size()) > Limits::stream_retained_bytes - output_bytes_) {
                fail("The official agent assembly exceeds retained capacity."); return;
            }
            incoming_.append(bytes);
            qsizetype newline;
            while (!failed_ && (newline = incoming_.indexOf('\n')) >= 0) {
                if (newline > recordLimit) { fail("The official agent response exceeds the transport capacity."); return; }
                const auto record = incoming_.left(newline);
                incoming_.remove(0, newline + 1);
                if (!record.trimmed().isEmpty()) {
                    if (event_count_ >= Limits::stream_events) { fail("The official agent operation exceeded its event capacity."); return; }
                    ++event_count_;
                    QPointer<CodexAgent> alive(this);
                    record_bytes_ = static_cast<quint64>(record.size());
                    receive(record);
                    if (!alive) return;
                    record_bytes_ = 0;
                }
            }
        }
    } catch (...) { fail("The official agent response could not be retained."); }
}
void CodexAgent::receive(const QByteArray& record) {
    quint64 depth = 0; bool quoted = false, escaped = false;
    for (const char c : record) {
        if (quoted) {
            if (escaped) escaped = false;
            else if (c == '\\') escaped = true;
            else if (c == '"') quoted = false;
        } else if (c == '"') quoted = true;
        else if (c == '{' || c == '[') {
            if (++depth > Limits::json_depth) { fail("The official agent response exceeds the JSON depth capacity."); return; }
        } else if ((c == '}' || c == ']') && depth) --depth;
    }
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(record, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        fail("The official agent response is not a valid protocol object."); return;
    }
    const auto envelope = document.object();
    if (envelope.contains(QStringLiteral("method"))) {
        if (!envelope.value(QStringLiteral("method")).isString() || (envelope.contains(QStringLiteral("params")) && !envelope.value(QStringLiteral("params")).isObject())) {
            fail("The official agent event has an invalid shape."); return;
        }
        const auto method = envelope.value(QStringLiteral("method")).toString();
        const auto params = envelope.value(QStringLiteral("params")).toObject();
        if (envelope.contains(QStringLiteral("id"))) {
            const auto id = envelope.value(QStringLiteral("id")); const auto key = idKey(id);
            if (key.isEmpty() || server_requests_.contains(key) || server_requests_.size() >= static_cast<qsizetype>(Limits::stream_calls)) {
                fail("The official agent request identity is invalid or exceeds capacity."); return;
            }
            quint64 bytes = 0;
            if (!encodedSize(envelope, Limits::record_bytes, bytes) || bytes > Limits::retained_record_bytes - pending_bytes_) {
                fail("The official agent pending approvals exceed capacity."); return;
            }
            server_requests_.insert(key, id); server_sizes_.insert(key, bytes); pending_bytes_ += bytes;
            emit serverRequest(id, method, params);
        } else emit event(method, params);
        return;
    }
    const auto idValue = envelope.value(QStringLiteral("id"));
    if (!idValue.isString() || !pending_.contains(idValue.toString()) ||
        (envelope.contains(QStringLiteral("result")) == envelope.contains(QStringLiteral("error")))) {
        fail("The official agent reply does not match an outstanding request."); return;
    }
    const auto id = idValue.toString(); const auto method = pending_.take(id);
    pending_deadlines_.remove(id); pending_bytes_ -= pending_sizes_.take(id);
    emit response(id, method, envelope);
}
void CodexAgent::fail(const char* explanation) noexcept {
    if (failed_) return;
    failed_ = true; // Nonallocating revocation precedes diagnostics or observers.
    pending_.clear(); server_requests_.clear(); incoming_.clear(); pending_deadlines_.clear(); pending_sizes_.clear(); server_sizes_.clear(); pending_bytes_ = 0; settleOperation();
    try { if (process_ && process_->state() != QProcess::NotRunning) process_->terminate(); } catch (...) {}
    try { emit failed(tr(explanation)); } catch (...) {}
}
void CodexAgent::retire() {
    if (generation_ != std::numeric_limits<quint64>::max()) ++generation_;
    failed_ = true; pending_.clear(); server_requests_.clear(); incoming_.clear(); pending_deadlines_.clear(); pending_sizes_.clear(); server_sizes_.clear(); pending_bytes_ = 0; settleOperation();
    auto* process = process_; process_ = nullptr;
    if (!process) return;
    process->disconnect(this);
    // Shutdown must outlive the facade without a blocking QProcess destructor.
    process->setParent(nullptr);
    process->terminate();
    QTimer::singleShot(static_cast<int>(Limits::callback_ms), process, [process] { if (process->state() != QProcess::NotRunning) process->kill(); });
    connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), process, &QObject::deleteLater);
    if (process->state() == QProcess::NotRunning) process->deleteLater();
}
} // namespace edi_app

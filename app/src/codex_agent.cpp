// SPDX-License-Identifier: BSD-3-Clause
#include "codex_agent.hpp"
#include "../../core/src/assistant_json.hpp"
#include <QAnyStringView>
#include <QtCore/qarraydata.h>
#include <cstddef>
#include <type_traits>
#include "assistant_runtime_config.hpp"
#include <QCoreApplication>
#include <QFile>
#include <stdexcept>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QScopeGuard>
#include <QJsonArray>
#include <QPointer>
#include <QJsonParseError>
#include <cmath>
#include <algorithm>
#include <limits>

namespace edi_app {
namespace {
bool addSize(quint64 n, quint64 cap, quint64& size) {
    if (size > cap || n > cap - size) return false;
    size += n; return true;
}
bool stringSize(QStringView text, quint64 cap, quint64& size) {
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
bool stringSize(QAnyStringView text,quint64 cap,quint64& size) {
    return text.visit([&](auto view) {
        using View=decltype(view);
        if constexpr (std::is_same_v<View,QStringView>)return stringSize(view,cap,size);
        else {
            if constexpr (!std::is_same_v<View,QLatin1StringView>) {
                if(!edi::assistant::detail::utf8(std::string_view(reinterpret_cast<const char*>(view.data()),static_cast<std::size_t>(view.size()))))return false;
            }
            if(!addSize(2,cap,size))return false;
            for(const auto c:view) {
                unsigned char u;
                u=static_cast<unsigned char>(c);
                const quint64 bytes=u=='"' || u=='\\' || u==8 || u==12 || u==10 || u==13 || u==9?2:u<0x20?6:
                    std::is_same_v<View,QLatin1StringView> && u>=0x80?2:1;
                if(!addSize(bytes,cap,size))return false;
            }
            return true;
        }
    });
}
bool encodedSize(const QJsonValue& value, quint64 cap, quint64& size, quint64 depth = 0) {
    using L = edi::assistant::Limits;
    if (value.isString()) return stringSize(value.toStringView(), cap, size);
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
            const auto key=it.key();
            if ((!first && !addSize(1, cap, size)) || !stringSize(QStringView(key), cap, size) ||
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
    connect(&timer_, &QTimer::timeout, this, [this] {
        const QPointer<CodexAgent> receiver(this); const auto scope = generation_;
        try { checkDeadline(); }
        catch (...) { if (receiver && generation_ == scope) fail("The official agent deadline could not be checked."); }
    });
    timer_.start();
}
void CodexAgent::beginOperation(quint64 totalMs, quint64 idleMs) {
    const QPointer<CodexAgent> receiver(this); const auto scope = generation_; auto* process = process_;
    if (!finishHumanWait()) return;
    checkDeadline(); if (!receiver || generation_ != scope || process_ != process || failed_) return;
    const auto now = clock_.elapsed();
    // A second clock sample can cross the old deadline after checkDeadline.
    // Expiry must never become the zero/disabled sentinel for a new role.
    if (operation_start_ >= 0 && (now < operation_start_ || now < last_activity_ ||
        (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
        (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_))) {
        fail("The official agent operation exceeded its deadline."); return;
    }
    if (operation_start_ < 0) { wire_bytes_ = 0; event_count_ = 0; }
    else if (total_ms_) {
        const auto elapsed = static_cast<quint64>(now - operation_start_);
        const auto remaining = total_ms_ - elapsed;
        if (totalMs == 0 || totalMs > remaining) totalMs = remaining;
    }
    operation_start_ = now; last_activity_ = now;
    total_ms_ = totalMs; idle_ms_ = idleMs;
}
bool CodexAgent::remainingOutput(quint64 bytes, quint64& available) const noexcept {
    available = 0;
    // Revocation is not destruction. While old frames or the detached original
    // process own buffers, do not admit replacement growth against a reset view.
    if(retired_process_ || (active_frames_ && (!process_ || failed_)))return false;
    if (bytes > Limits::stream_retained_bytes || record_bytes_ > Limits::stream_retained_bytes - bytes ||
        static_cast<quint64>(incoming_.size()) > Limits::stream_retained_bytes - bytes - record_bytes_)
        return false;
    available = Limits::stream_retained_bytes - bytes - record_bytes_ - static_cast<quint64>(incoming_.size());
    const auto queued=process_?static_cast<quint64>(process_->bytesToWrite()):0;
    const auto held=static_cast<quint64>(deferred_required_.capacity());
    if(request_bytes_>available || read_bytes_>available-request_bytes_ ||
       queued>available-request_bytes_-read_bytes_ || held>available-request_bytes_-read_bytes_-queued)return false;
    available-=request_bytes_+read_bytes_+queued+held;
    return true;
}
bool CodexAgent::retainOutput(quint64 bytes) {
    quint64 available = 0;
    if (!remainingOutput(bytes, available)) {
        fail("The official agent output exceeds retained capacity."); return false;
    }
    output_bytes_ = bytes; return true;
}
bool CodexAgent::releaseOutput(quint64 bytes, quint64 originalGeneration) noexcept {
    if (failed_ || !process_ || generation_ != originalGeneration || bytes > output_bytes_) return false;
    quint64 available = 0;
    if (!remainingOutput(bytes, available)) return false;
    output_bytes_ = bytes;
    return true;
}
void CodexAgent::activity() { last_activity_ = human_wait_start_ >= 0 ? human_wait_start_ : clock_.elapsed(); }
bool CodexAgent::finishHumanWait() {
    if (human_wait_start_ < 0) return true;
    const auto now = clock_.elapsed();
    if (now < human_wait_start_ || operation_start_ < 0 || operation_start_ > human_wait_start_ || last_activity_ > human_wait_start_) {
        fail("The official agent human-wait clock is invalid."); return false;
    }
    const auto elapsed = now - human_wait_start_;
    // Both timestamps are <= human_wait_start_, so each shifted value is <= now.
    operation_start_ += elapsed; last_activity_ += elapsed;
    human_wait_start_ = -1; human_wait_id_.clear();
    return true;
}
bool CodexAgent::beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !process_ || operation_start_ < 0 || !idle_ms_) return false;
    // Success is callback-free: never let an optional-usage observer replace
    // the caller's original request between its owner proof and this entry.
    const auto key = idKey(originalRequestId);
    const auto found = server_requests_.constFind(key);
    if (key.isEmpty() || found == server_requests_.cend()) return false;
    if (human_wait_start_ >= 0) return human_wait_id_ == found.key();
    const auto now = clock_.elapsed();
    if (now < operation_start_ || now < last_activity_ ||
        (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
        (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_)) {
        fail("The official agent operation exceeded its deadline."); return false;
    }
    human_wait_id_ = found.key(); // Implicitly shared with its already retained request owner.
    human_wait_start_ = now;
    return true;
}
bool CodexAgent::endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if (generation_ != originalGeneration || failed_ || !process_) return false;
    const auto key = idKey(originalRequestId);
    if (key.isEmpty() || !server_requests_.contains(key) || (human_wait_start_ >= 0 && human_wait_id_ != key)) return false;
    return finishHumanWait();
}
void CodexAgent::settleOperation() {
    human_wait_start_ = -1; human_wait_id_.clear();
    operation_start_ = -1; total_ms_ = 0; idle_ms_ = 0;
}
void CodexAgent::retireOptionalUsage(const QString& id) {
    if (pending_.value(id) != "account/rateLimits/read" || !optional_usage_ids_.contains(id)) return;
    pending_.remove(id); pending_deadlines_.remove(id); pending_bytes_ -= pending_sizes_.take(id);
    emit optionalUsageUnavailable(id); // No activity/operation/deadline role transition.
}
void CodexAgent::preemptOptionalUsage() {
    const QPointer<CodexAgent> receiver(this);
    const auto scope = generation_;
    for (;;) {
        QString id;
        for (auto i = pending_.constBegin(); i != pending_.constEnd(); ++i)
            if (i.value() == "account/rateLimits/read" && optional_usage_ids_.contains(i.key())) { id = i.key(); break; }
        if (id.isEmpty()) return;
        retireOptionalUsage(id); // Exact issued late-ID ownership remains.
        if (!receiver || generation_ != scope || failed_) return;
    }
}
void CodexAgent::flushRequired() noexcept {
    const QPointer<CodexAgent> receiver(this); const auto scope = generation_; auto* process = process_;
    if(active_frames_==std::numeric_limits<quint64>::max())return;
    ++active_frames_;
    const auto frame=qScopeGuard([receiver]{if(receiver)--receiver->active_frames_;});
    if (deferred_required_.isEmpty() || !process_ || failed_) return;
    try {
        checkDeadline();
        if (!receiver || generation_ != scope || process_ != process || failed_ || !process_ || process_->state() != QProcess::Running) return;
        const auto queued = static_cast<quint64>(process_->bytesToWrite());
        if (queued > Limits::request_bytes || static_cast<quint64>(deferred_required_.size()) > Limits::request_bytes - queued) return;
        const auto lineSize=static_cast<quint64>(deferred_required_.size());
        quint64 available=0;
        if(!remainingOutput(output_bytes_,available) || lineSize>available)return;
        request_bytes_+=lineSize; // Preown the future QProcess queue copy.
        quint64 heldRole=lineSize;
        const auto transfer=qScopeGuard([receiver,&heldRole] {
            if(receiver)receiver->request_bytes_-=heldRole;
        });
        auto line = std::move(deferred_required_); deferred_required_.clear(); deferred_deadline_ = -1;
        const auto lineCapacity=static_cast<quint64>(line.capacity());
        request_bytes_+=lineCapacity;heldRole+=lineCapacity; // Transfer the actual old member backing to the local line.
        // Transfer this exact prepared original once. Any partial write is a
        // fatal uncertain delivery; never replay or rebuild it from current UI.
        const auto written=process->write(line);
        if(receiver && generation_==scope && process_==process){request_bytes_-=lineSize;heldRole-=lineSize;}
        if (written != line.size() && receiver && generation_ == scope && process_ == process)
            fail("The official agent request could not be delivered.");
    } catch (...) { if (receiver && generation_ == scope && process_ == process) fail("The official agent queued control could not be delivered."); }
}
void CodexAgent::checkDeadline() {
    const QPointer<CodexAgent> receiver(this); const auto scope = generation_; auto* process = process_;
    if (failed_) return;
    const auto now = clock_.elapsed();
    if (deferred_deadline_ >= 0 && now >= deferred_deadline_) {
        fail("The official agent did not drain a required control request in time."); return;
    }
    for (;;) {
        QString optional;
        for (auto it = pending_deadlines_.constBegin(); it != pending_deadlines_.constEnd(); ++it) {
            if (now < it.value()) continue;
            if (pending_.value(it.key()) != "account/rateLimits/read" || !optional_usage_ids_.contains(it.key())) {
                fail("The official agent did not acknowledge a control request in time."); return;
            }
            optional = it.key(); break;
        }
        if (optional.isEmpty()) break;
        retireOptionalUsage(optional);
        if (!receiver || generation_ != scope || process_ != process || failed_) return;
    }
    if (operation_start_ < 0) return;
    const auto operationNow = human_wait_start_ >= 0 ? human_wait_start_ : clock_.elapsed();
    if (operationNow < operation_start_ || operationNow < last_activity_ ||
        (total_ms_ && static_cast<quint64>(operationNow - operation_start_) >= total_ms_) ||
        (idle_ms_ && static_cast<quint64>(operationNow - last_activity_) >= idle_ms_))
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

QString CodexAgent::policyPatch() { return QString::fromLatin1(EDI_CODEX_SOURCE_PATCH_SHA256); }

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
    if (!policyPatch().isEmpty() &&
        (metadata.value("ediPolicySchema")!="edi.runtime-policy/1" || metadata.value("ediFlavour")!="edi-app-server/1" ||
         metadata.value("upstreamCommit")!="092d3acd6bec3e3a14bdc7e7a2810ab628ab759d" ||
         metadata.value("sourcePatchSha256")!=policyPatch())) return {};
    const auto executable = root + "/bin/codex-app-server";
    if (!QFileInfo(executable).isFile() || !QFileInfo(executable).isExecutable()) return {};
    return executable;
}

bool CodexAgent::start(const QString& executable, const QString& workspace) {
    if (process_ || retired_process_ || active_frames_ || request_bytes_ || read_bytes_ || record_bytes_ || reading_ || executable.isEmpty() || !QFileInfo(workspace).isAbsolute() || !QFileInfo(workspace).isDir())
        return false;
    const QPointer<CodexAgent> receiver(this);
    QPointer<QProcess> prepared;
    auto scope = generation_;
    const auto current = [&] { return receiver && generation_ == scope && process_ == prepared.data(); };
    try {
        if (generation_ == std::numeric_limits<quint64>::max()) return false;
        scope = ++generation_;
        settleOperation();
        failed_ = false; eof_pending_=false; incoming_.clear(); deferred_required_.clear(); optional_queued_bytes_ = 0; deferred_deadline_ = -1;
        pending_.clear(); optional_usage_ids_.clear(); server_requests_.clear();
        pending_sizes_.clear(); pending_deadlines_.clear(); server_sizes_.clear();
        pending_bytes_ = 0; output_bytes_ = 0; record_bytes_ = 0; request_bytes_ = 0; wire_bytes_ = 0; event_count_ = 0;
        auto* process = new QProcess(this);
        prepared = process; process_ = process;
        process->setProgram(executable);
        process->setArguments({QStringLiteral("--listen"), QStringLiteral("stdio://"),
            QStringLiteral("-c"), QStringLiteral("sandbox_mode=\"read-only\""),
            QStringLiteral("-c"), QStringLiteral("approval_policy=\"never\""),
            QStringLiteral("-c"), QStringLiteral("features.shell_zsh_fork=false")});
        process->setWorkingDirectory(workspace);
        process->setProcessChannelMode(QProcess::SeparateChannels);
        // The runtime owns its ordinary profile and managed login. Never assign
        // HOME/home/CODEX_HOME, open config/auth files, or copy provider tokens.
        connect(process, &QProcess::started, this, [this, original = prepared, scope] {
            const QPointer<CodexAgent> receiver(this);
            const auto current = [&] { return receiver && original && process_ == original.data() && generation_ == scope; };
            try { if (current() && !failed_) emit started(); }
            catch (...) { if (current()) fail("The official agent handshake could not be prepared."); }
        });
        connect(process, &QProcess::bytesWritten, this, [this, original = prepared, scope](qint64 count) {
            if (!original || process_ != original.data() || generation_ != scope || failed_ || count <= 0) return;
            // Optional writes are admitted only at an empty physical queue, so
            // these bytes are its FIFO head even after required writes arrive.
            optional_queued_bytes_ -= qMin(optional_queued_bytes_, static_cast<quint64>(count));
            flushRequired(); // Terminal: the helper can synchronously retire this scope.
        });
        connect(process, &QProcess::readyReadStandardOutput, this, [this, original = prepared, scope] { if (original) read(original.data(), scope); });
        connect(process, &QProcess::readyReadStandardError, this, [this, original = prepared, scope] {
            const QPointer<CodexAgent> receiver(this);
            const auto current = [&] { return receiver && original && process_ == original.data() && generation_ == scope; };
            if (!current()) return;
            if(active_frames_==std::numeric_limits<quint64>::max())return;
            ++active_frames_;
            const auto frame=qScopeGuard([receiver]{if(receiver)--receiver->active_frames_;});
            try {
                original->setReadChannel(QProcess::StandardError);
                while (current() && !failed_ && original->bytesAvailable() > 0) {
                    const auto remaining = Limits::stream_wire_bytes - wire_bytes_;
                    if (remaining == 0) { fail("The official agent operation exceeded its wire capacity."); break; }
                    quint64 available=0;
                    if(!remainingOutput(output_bytes_,available) || !available){fail("The official agent diagnostic exceeds joint retained capacity.");return;}
                    const auto count=std::min({static_cast<quint64>(Limits::http_chunk_bytes),remaining,available});
                    read_bytes_+=count;
                    const auto discardedRole=qScopeGuard([receiver,count]{if(receiver)receiver->read_bytes_-=count;});
                    const auto discarded = original->read(count);
                    if (!current() || failed_) return;
                    if (discarded.isEmpty()) break;
                    wire_bytes_ += static_cast<quint64>(discarded.size());
                }
                if (current()) original->setReadChannel(QProcess::StandardOutput);
            } catch (...) { if (current()) fail("The official agent diagnostic channel could not be drained."); }
            // Never put raw runtime stderr (which may contain user data) in a
            // provider failure card or credential log.
        });
        connect(process, &QProcess::errorOccurred, this, [this, original = prepared, scope](QProcess::ProcessError) {
            if (original && process_ == original.data() && generation_ == scope) fail("The official agent process could not continue.");
        });
        connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
                [this, original = prepared, scope](int, QProcess::ExitStatus) {
            if (original) read(original.data(), scope, true);
        });
        beginOperation(Limits::http_json_ms, 0);
        if (!current() || !prepared || failed_) return false;
        prepared->start();
        return current() && prepared && !failed_;
    } catch (...) {
        if (current()) fail("The official agent process could not be prepared.");
        return false;
    }
}

bool CodexAgent::write(const QJsonObject& envelope, const std::function<bool()>& prepare, bool nonfatalPreflight, bool optionalUsage) {
    const QPointer<CodexAgent> receiver(this);
    if(active_frames_==std::numeric_limits<quint64>::max())return false;
    ++active_frames_;
    const auto frame=qScopeGuard([receiver]{if(receiver)--receiver->active_frames_;});
    auto* process = process_; const auto epoch = generation_;
    if (!process_ || failed_ || process_->state() != QProcess::Running) return false;
    checkDeadline(); if (!receiver || process_ != process || generation_ != epoch || failed_) return false;
    quint64 encoded = 0;
    if (!encodedSize(envelope, Limits::request_bytes, encoded) || encoded >= Limits::request_bytes) {
        if (!nonfatalPreflight) fail("The official agent request exceeds the transport capacity."); return false;
    }
    const auto initialQueued = static_cast<quint64>(process_->bytesToWrite());
    const auto lineSize = encoded + 1;
    if (optionalUsage && (initialQueued != 0 || optional_queued_bytes_ != 0 || !deferred_required_.isEmpty() ||
        lineSize > Limits::request_bytes - Limits::retained_record_bytes)) return false;
    if (!optionalUsage) preemptOptionalUsage();
    if (!receiver || process_ != process || generation_ != epoch || failed_ || !process_) return false;
    const auto queued = static_cast<quint64>(process_->bytesToWrite());
    if (queued > Limits::request_bytes) {
        if (!nonfatalPreflight) fail("The official agent write queue exceeds the transport capacity."); return false;
    }
    const auto held = static_cast<quint64>(deferred_required_.size());
    // Logical required bytes never exceed the existing hard write capacity.
    // Optional queued bytes can neither consume that required ownership nor be
    // retracted from QProcess. Hold the exact required record until they drain.
    const auto optionalHead = qMin(queued, optional_queued_bytes_);
    const auto requiredQueued = queued - optionalHead;
    if (requiredQueued > Limits::request_bytes || held > Limits::request_bytes - requiredQueued ||
        lineSize > Limits::request_bytes - requiredQueued - held) {
        if (!nonfatalPreflight) fail("The official agent write queue exceeds the transport capacity."); return false;
    }
    const bool deferred = held != 0 || lineSize > Limits::request_bytes - queued;
    if (deferred && (optionalUsage || held > Limits::retained_record_bytes || lineSize > Limits::retained_record_bytes - held)) {
        if (!nonfatalPreflight) fail("The official agent queued control exceeds retained capacity."); return false;
    }
    // Actual wire and LF-appended line coexist; a detached holding copy grows
    // only on the deferred path. Charge them beside current VM/record/unread,
    // old holding bytes and QProcess's actual queue before serialization.
    quint64 available=0;
    // Same Qt writer workspace as the VM response seam: aggregate growth,
    // independent escapedString doubling and its owning string conversion.
    const auto minimum=std::max<quint64>(16,sizeof(QArrayData)+alignof(std::max_align_t)+sizeof(QChar));
    const auto wireCapacity=2*(encoded+minimum),lineCapacity=2*(lineSize+minimum);
    const auto oldHeldCapacity=static_cast<quint64>(deferred_required_.capacity());
    const auto nextHeldCapacity=deferred?2*(held+lineSize+minimum):0;
    const auto writerScratch=6*(encoded+minimum);
    const quint64 wireRole=wireCapacity+lineCapacity+lineSize+(deferred?oldHeldCapacity+nextHeldCapacity:0);
    if(wireRole>Limits::stream_retained_bytes || writerScratch>Limits::stream_retained_bytes-wireRole ||
        !remainingOutput(output_bytes_,available) || wireRole+writerScratch>available) {
        if(!nonfatalPreflight)fail("The official agent request exceeds joint retained capacity.");return false;
    }
    request_bytes_+=wireRole+writerScratch;
    quint64 retainedRequest=wireRole+writerScratch;
    const auto requestRole=qScopeGuard([receiver,&retainedRequest] {
        if(receiver)receiver->request_bytes_-=retainedRequest;
    });
    const auto wire = QJsonDocument(envelope).toJson(QJsonDocument::Compact);
    if (static_cast<quint64>(wire.size()) != encoded || static_cast<quint64>(wire.capacity())>wireCapacity) {
        if (!nonfatalPreflight) fail("The official agent request could not be encoded consistently."); return false;
    }
    request_bytes_-=writerScratch;retainedRequest-=writerScratch; // Writer conversion/escaping locals are dead.
    const auto line = wire + '\n';
    if(static_cast<quint64>(line.capacity())>lineCapacity) {
        if(!nonfatalPreflight)fail("The official agent line capacity exceeds its admitted role");return false;
    }
    auto heldWire = deferred_required_;
    if (deferred) {
        heldWire.append(line); // All holding-slot allocation precedes admission/publication.
        if(static_cast<quint64>(heldWire.capacity())>nextHeldCapacity) {
            if(!nonfatalPreflight)fail("The official agent holding capacity exceeds its admitted role");return false;
        }
    }
    const auto priorHeld = deferred_required_.size();
    if (prepare && !prepare()) return false;
    if (!receiver || failed_ || process_ != process || generation_ != epoch || priorHeld != deferred_required_.size()) return false;
    if (deferred) {
        deferred_required_.swap(heldWire); // Nonallocating ownership commit; original deadline stays armed.
        const auto transferred=static_cast<quint64>(deferred_required_.capacity());
        request_bytes_-=transferred;retainedRequest-=transferred; // Actual new member backing transferred; old heldWire stays local.
        if (deferred_deadline_ < 0) deferred_deadline_ = clock_.elapsed() + static_cast<qint64>(Limits::http_json_ms);
        flushRequired(); return receiver && process_ == process && generation_ == epoch && !failed_;
    }
    if (optionalUsage) optional_queued_bytes_ = lineSize;
    if (process->write(line) != line.size()) {
        if (receiver && process_ == process && generation_ == epoch) fail("The official agent request could not be delivered.");
        return false;
    }
    if(receiver && process_==process && generation_==epoch){request_bytes_-=lineSize;retainedRequest-=lineSize;}
    return receiver && process_ == process && generation_ == epoch && !failed_;
}

QString CodexAgent::request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare) {
    const QPointer<CodexAgent> receiver(this);
    if(active_frames_==std::numeric_limits<quint64>::max())return {};
    ++active_frames_;
    const auto frame=qScopeGuard([receiver]{if(receiver)--receiver->active_frames_;});
    auto* originalProcess = process_; const auto scope = generation_;
    QString id; bool charged = false;
    const auto discard = [&] {
        if (!receiver || process_ != originalProcess || generation_ != scope) return;
        pending_.remove(id); pending_deadlines_.remove(id); optional_usage_ids_.remove(id);
        if (charged) pending_bytes_ -= pending_sizes_.take(id); else pending_sizes_.remove(id);
    };
    try {
        const bool optional = method == "account/rateLimits/read";
        if (failed_ || method.isEmpty() || next_id_ == std::numeric_limits<quint64>::max()) return {};
        if (optional && (pending_.size() >= pendingLimit - 1 || optional_usage_ids_.size() >= static_cast<qsizetype>(Limits::completed_calls) ||
            !deferred_required_.isEmpty() || optional_queued_bytes_ != 0 || !process_ || process_->bytesToWrite() != 0)) return {};
        if (optional) for (auto i = pending_.constBegin(); i != pending_.constEnd(); ++i)
            if (i.value() == "account/rateLimits/read") return {};
        id = QStringLiteral("edi-%1-%2").arg(generation_).arg(++next_id_);
        quint64 bytes = 0;
        const QJsonObject envelope{{"id", id}, {"method", method}, {"params", params}};
        if (!encodedSize(envelope, Limits::record_bytes, bytes)) return {};
        if (!optional && (pending_.size() >= pendingLimit - 1 || bytes > Limits::retained_record_bytes - pending_bytes_)) preemptOptionalUsage();
        if (!receiver || process_ != originalProcess || generation_ != scope) return {};
        if (optional && (pending_bytes_ > Limits::retained_record_bytes - Limits::record_bytes ||
            bytes > Limits::retained_record_bytes - Limits::record_bytes - pending_bytes_)) return {};
        if (pending_.size() >= pendingLimit || bytes > Limits::retained_record_bytes - pending_bytes_) return {};
        if (optional) optional_usage_ids_.insert(id);
        pending_.insert(id, method); pending_sizes_.insert(id, bytes);
        pending_deadlines_.insert(id, clock_.elapsed() + static_cast<qint64>(Limits::http_json_ms));
        pending_bytes_ += bytes; charged = true;
        if (!write(envelope, [&] { return !prepare || prepare(id); }, optional || static_cast<bool>(prepare), optional)) { discard(); return {}; }
        return id;
    } catch (...) { discard(); return {}; }
}
bool CodexAgent::notification(const QString& method, const QJsonObject& params) {
    return write({{QStringLiteral("method"), method}, {QStringLiteral("params"), params}});
}
bool CodexAgent::answer(const QJsonValue& originalId, const QJsonObject& result) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !server_requests_.contains(key) || (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_))) return false;
    // Retire before delivery: an uncertain write never permits a repeated answer.
    const auto id = server_requests_.take(key); pending_bytes_ -= server_sizes_.take(key);
    return write({{QStringLiteral("id"), id}, {QStringLiteral("result"), result}});
}
bool CodexAgent::reject(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !server_requests_.contains(key) || (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_))) return false;
    const auto id = server_requests_.take(key); pending_bytes_ -= server_sizes_.take(key);
    return write({{"id", id}, {"error", QJsonObject{{"code", -32601}, {"message", "This client does not support this request."}}}});
}
void CodexAgent::resolved(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_)) return;
    server_requests_.remove(key); pending_bytes_ -= server_sizes_.take(key);
}
void CodexAgent::read(QProcess* process, quint64 scope, bool finished) {
    if (!process || process_ != process || generation_ != scope) return;
    // A nested finished notification records only this original process's EOF.
    // The active reader retains delivery and drains its assembled/buffered tail.
    if (finished) eof_pending_=true;
    if (reading_) return;
    const QPointer<CodexAgent> receiver(this);
    const QPointer<QProcess> original(process);
    if(active_frames_==std::numeric_limits<quint64>::max())return;
    ++active_frames_;reading_=true;
    const auto frame=qScopeGuard([receiver]{if(receiver){receiver->reading_=false;--receiver->active_frames_;}});
    const auto current = [&] { return receiver && original && process_ == original.data() && generation_ == scope; };
    const auto drain=[&] {
        if (!current() || failed_) return;
        try {
            process->setReadChannel(QProcess::StandardOutput);
            while (current() && !failed_ && original->bytesAvailable() > 0) {
                const auto capacity = recordLimit + 1 - incoming_.size();
                if (capacity <= 0) { fail("The official agent response exceeds the transport capacity."); return; }
                checkDeadline(); if (!current() || failed_) return;
                const auto old=static_cast<quint64>(incoming_.size());
                quint64 available=0;
                if(!remainingOutput(output_bytes_,available) || available<=old) {
                    fail("The official agent assembly exceeds retained capacity.");return;
                }
                const auto wireRoom=Limits::stream_wire_bytes-wire_bytes_;
                const auto requested=std::min({static_cast<quint64>(capacity),static_cast<quint64>(Limits::http_chunk_bytes),
                                               (available-old)/2,wireRoom});
                if(!requested){fail("The official agent response has no admitted input capacity.");return;}
                // The local read chunk and complete replacement assembly coexist
                // with the old incoming member. Reserve both before QProcess reads.
                quint64 prepared=requested+old+requested;
                read_bytes_+=prepared;
                const auto assembly=qScopeGuard([receiver,&prepared]{if(receiver)receiver->read_bytes_-=prepared;});
                const auto bytes=process->read(static_cast<qint64>(requested));
                if(!current() || failed_)return;
                if(bytes.isEmpty())return;
                if(static_cast<quint64>(bytes.size())>requested)throw std::logic_error("Agent read exceeded admitted bytes");
                wire_bytes_+=static_cast<quint64>(bytes.size());
                read_bytes_-=requested-static_cast<quint64>(bytes.size());prepared-=requested-static_cast<quint64>(bytes.size());
                QByteArray assembled;assembled.reserve(static_cast<qsizetype>(old)+bytes.size());
                assembled.append(incoming_);assembled.append(bytes);
                incoming_.swap(assembled);
                // The new member owns its growth. The old assembly and chunk stay
                // charged until their local destructors, including across callbacks.
                read_bytes_-=static_cast<quint64>(bytes.size());prepared-=static_cast<quint64>(bytes.size());
                qsizetype newline;
                while (current() && !failed_ && (newline = incoming_.indexOf('\n')) >= 0) {
                    if (newline > recordLimit) { fail("The official agent response exceeds the transport capacity."); return; }
                    quint64 recordOwner=0;
                    const auto raw=qScopeGuard([receiver,&recordOwner]{if(receiver)receiver->record_bytes_-=recordOwner;});
                    QByteArray record;
                    {
                        const auto originalSize=static_cast<quint64>(incoming_.size());
                        const auto prospective=originalSize-1; // Record and remaining tail, excluding the delimiter.
                        quint64 room=0;
                        if(!remainingOutput(output_bytes_,room) || prospective>room){fail("The official agent record exceeds joint retained capacity.");return;}
                        quint64 preparation=prospective;read_bytes_+=preparation;
                        const auto split=qScopeGuard([receiver,&preparation]{if(receiver)receiver->read_bytes_-=preparation;});
                        record=incoming_.left(newline);
                        recordOwner=static_cast<quint64>(record.size());record_bytes_+=recordOwner;
                        read_bytes_-=recordOwner;preparation-=recordOwner;
                        auto tail=incoming_.mid(newline+1);
                        incoming_.swap(tail);
                        // The local tail now owns the OLD member, including LF.
                        // Transfer its prior member charge, never admit a new byte.
                        read_bytes_+=recordOwner+1;preparation+=recordOwner+1;
                    }
                    const bool blank=std::all_of(record.cbegin(),record.cend(),[](char c){return c==' ' || c=='\t' || c=='\r' || c=='\n' || c=='\v' || c=='\f';});
                    if (!blank) {
                        if (event_count_ >= Limits::stream_events) { fail("The official agent operation exceeded its event capacity."); return; }
                        ++event_count_;
                        receive(record);
                        if (!current()) return;
                    }
                }
            }
        } catch (...) { if (current()) fail("The official agent response could not be retained."); }
    };
    drain(); // All local record/parse/assembly owners settle before EOF effects.
    if (!current() || !eof_pending_) return;
    eof_pending_=false;
    if (!failed_) fail("The official agent process ended. Unfinished work was interrupted.");
    if (!current()) return;
    retired_process_=original;
    process_=nullptr;
    original->deleteLater();
}
void CodexAgent::receive(const QByteArray& record) {
    const QPointer<CodexAgent> receiver(this);
    const QPointer<QProcess> original(process_);
    const auto scope = generation_;
    const auto current = [&] { return receiver && original && process_ == original.data() && generation_ == scope; };
    if (!current() || failed_) return;
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
    // Preserve the original encoded-record accounting convention for the
    // parsed representation as a distinct owner beside the raw local frame.
    const auto parsedBytes=static_cast<quint64>(record.size());quint64 available=0;
    if(!remainingOutput(output_bytes_,available) || parsedBytes>available){fail("The official agent parsed response exceeds joint retained capacity.");return;}
    read_bytes_+=parsedBytes;
    const auto parsedRole=qScopeGuard([receiver,parsedBytes]{if(receiver)receiver->read_bytes_-=parsedBytes;});
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
            if (!encodedSize(envelope, Limits::record_bytes, bytes)) {
                fail("The official agent pending approvals exceed capacity."); return;
            }
            if (bytes > Limits::retained_record_bytes - pending_bytes_) preemptOptionalUsage();
            if (!current() || failed_) return;
            if (bytes > Limits::retained_record_bytes - pending_bytes_) {
                fail("The official agent pending approvals exceed capacity."); return;
            }
            server_requests_.insert(key, id); server_sizes_.insert(key, bytes); pending_bytes_ += bytes;
            emit serverRequest(id, method, params);
        } else emit event(method, params);
        return;
    }
    const auto idValue = envelope.value(QStringLiteral("id"));
    if (idValue.isString() && optional_usage_ids_.contains(idValue.toString()) && !pending_.contains(idValue.toString())) {
        if (envelope.contains("result") == envelope.contains("error")) { fail("The official agent late optional reply is malformed."); return; }
        optional_usage_ids_.remove(idValue.toString()); return; // Exact late optional reply, no inference effect.
    }
    if (!idValue.isString() || !pending_.contains(idValue.toString()) ||
        (envelope.contains(QStringLiteral("result")) == envelope.contains(QStringLiteral("error")))) {
        fail("The official agent reply does not match an outstanding request."); return;
    }
    const auto id = idValue.toString(); const auto method = pending_.take(id);
    pending_deadlines_.remove(id); pending_bytes_ -= pending_sizes_.take(id);
    optional_usage_ids_.remove(id);
    emit response(id, method, envelope);
}
void CodexAgent::fail(const char* explanation) noexcept {
    if (failed_) return;
    const QPointer<QProcess> original(process_);
    failed_ = true; // Nonallocating revocation precedes diagnostics or observers.
    settleOperation();
    deferred_required_.clear(); optional_queued_bytes_ = 0; deferred_deadline_ = -1;
    pending_.clear(); optional_usage_ids_.clear(); server_requests_.clear(); incoming_.clear(); pending_deadlines_.clear(); pending_sizes_.clear(); server_sizes_.clear(); pending_bytes_ = 0;
    // Publish the original cause before terminate can synchronously finish and
    // detach this process. After notification, touch only the captured process.
    try { emit failed(tr(explanation)); } catch (...) {}
    try { if (original && original->state() != QProcess::NotRunning) original->terminate(); } catch (...) {}
}
void CodexAgent::retire() {
    if (generation_ != std::numeric_limits<quint64>::max()) ++generation_;
    // Live stack owners settle their own counters even after this revocation.
    failed_ = true; settleOperation(); deferred_required_.clear(); optional_queued_bytes_ = 0; deferred_deadline_ = -1; pending_.clear(); optional_usage_ids_.clear(); server_requests_.clear(); incoming_.clear(); pending_deadlines_.clear(); pending_sizes_.clear(); server_sizes_.clear(); pending_bytes_ = 0;
    const QPointer<QProcess> process(process_); process_ = nullptr;
    if (!process) return;
    retired_process_=process;
    process->disconnect(this);
    if (!process) return;
    // Only the detached original process is touched after these callbacks. A
    // replacement facade/process owns its own channels, maps and first deadline.
    process->setParent(nullptr);
    if (!process) return;
    // Shutdown must outlive the facade without a blocking QProcess destructor.
    process->terminate();
    if (!process) return;
    QTimer::singleShot(static_cast<int>(Limits::callback_ms), process.data(), [process] { if (process && process->state() != QProcess::NotRunning) process->kill(); });
    connect(process.data(), qOverload<int, QProcess::ExitStatus>(&QProcess::finished), process.data(), &QObject::deleteLater);
    if (process->state() == QProcess::NotRunning) process->deleteLater();
}
} // namespace edi_app

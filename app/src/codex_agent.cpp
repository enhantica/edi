// SPDX-License-Identifier: BSD-3-Clause
#include "codex_agent.hpp"
#include "../../core/src/assistant_json.hpp"
#include <QAnyStringView>
#include <QtCore/qarraydata.h>
#include <cstddef>
#include <QtCore/qmath.h>
#include <type_traits>
#include "assistant_runtime_config.hpp"
#include <QCoreApplication>
#include <QEvent>
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
bool addSize(quint64 n, std::optional<quint64> cap, quint64& size) {
    if (n > std::numeric_limits<quint64>::max()-size || (cap && (size>*cap || n>*cap-size))) return false;
    size += n; return true;
}
bool stringSize(QStringView text, std::optional<quint64> cap, quint64& size) {
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
bool stringSize(QAnyStringView text,std::optional<quint64> cap,quint64& size) {
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
bool encodedSize(const QJsonValue& value, std::optional<quint64> cap, quint64& size, quint64 depth = 0) {
    using L = edi::assistant::Limits;

    if (value.isString()) return stringSize(value.toStringView(),cap,size);
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
            const auto key=it.keyView();

            if ((!first && !addSize(1, cap, size)) || !stringSize(key, cap, size) ||
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
bool codex_measured_size(const QJsonValue& value, quint64& size) { return encodedSize(value, std::nullopt, size); }
quint64 codex_json_capacity(quint64 bytes) {
    const auto header=static_cast<quint64>(sizeof(QArrayData)+alignof(std::max_align_t)+sizeof(QChar));
    if(bytes>std::numeric_limits<quint64>::max()/4)throw std::length_error("JSON backing exceeds capacity");
    // Pinned qarraydata.cpp Grow rule; header/alignment/terminator remain owned.
    return qNextPowerOfTwo(bytes+header)+header;
}

// This is the original process with one after-DeferredDelete observation.
// Qt still decides when to deliver/delete; all other behavior is inherited.
class CodexAgent::Process final : public QProcess {
    const QPointer<CodexAgent> owner_;
    const quint64 birth_;
    const std::shared_ptr<const void> lease_;
public:
    Process(CodexAgent* owner,quint64 birth,std::shared_ptr<const void> lease)
        :QProcess(owner),owner_(owner),birth_(birth),lease_(std::move(lease)) {}
protected:
    bool event(QEvent* event) override {
        if(event->type()!=QEvent::DeferredDelete)return QProcess::event(event);
        const auto owner=owner_;const auto birth=birth_;const auto lease=lease_;
        const bool handled=QProcess::event(event); // Original delete completes here.
        // No this/process/event access after that call. Lease outlives both
        // deletion and callback, including facade death/reentrant replacement.
        if(owner)owner->processOwnerReleased(birth);
        return handled;
    }
};

CodexAgent::OutputOwnerState CodexAgent::outputOwnerState() const noexcept {
    if(!release_owner_)return OutputOwnerState::Unobserved;
    if(process_ && !failed_)return OutputOwnerState::Live;
    if(process_ || retired_process_ || process_owner_alive_ || active_frames_ || reading_)return OutputOwnerState::Releasing;
    return OutputOwnerState::Released;
}
void CodexAgent::maybeOwnersReleased() noexcept {
    if(outputOwnerState()!=OutputOwnerState::Released)return;
    try {emit outputOwnersReleased();}catch(...){} // Terminal: receiver may delete this.
}
void CodexAgent::processOwnerReleased(quint64 birth) noexcept {
    if(!release_owner_ || birth!=process_birth_)return;
    process_owner_alive_=false;
    maybeOwnersReleased(); // No facade access after notification.
}
CodexAgent::CodexAgent(QObject* parent,std::shared_ptr<const void> releaseOwner) : QObject(parent),release_owner_(std::move(releaseOwner)) {
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
    native_work_id_.clear(); native_work_waiting_=false; wait_accounted_at_=-1;
    checkDeadline(); if (!receiver || generation_ != scope || process_ != process || failed_) return;
    const auto now = clock_.elapsed();
    // A second clock sample can cross the old deadline after checkDeadline.
    // Expiry must never become the zero/disabled sentinel for a new role.
    if (operation_start_ >= 0 && (now < operation_start_ || now < last_activity_ ||
        (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
        (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_))) {
        fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline); return;
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



bool CodexAgent::operationExpired(qint64 now) const noexcept {
    return operation_start_>=0 && (now<operation_start_ || now<last_activity_ ||
        (total_ms_ && static_cast<quint64>(now-operation_start_)>=total_ms_) ||
        (idle_ms_ && static_cast<quint64>(now-last_activity_)>=idle_ms_));
}
bool CodexAgent::accountWaits(qint64 now) {
    if(wait_accounted_at_<0)return true;
    if(now<wait_accounted_at_ || operation_start_<0 || operation_start_>wait_accounted_at_ || last_activity_>wait_accounted_at_ ||
        (human_wait_start_<0 && native_work_id_.isEmpty()) || (native_work_waiting_ && native_work_id_.isEmpty())) {
        fail("The official agent human-wait clock is invalid."); return false;
    }
    const auto elapsed=now-wait_accounted_at_;
    // Each timestamp is <= the old accounting sample. Shifting by this interval
    // remains <= now without overflow. Overlapping owners contribute a union.
    if(human_wait_start_>=0 || native_work_waiting_)operation_start_+=elapsed;
    if(human_wait_start_>=0 || !native_work_id_.isEmpty())last_activity_+=elapsed;
    wait_accounted_at_=now;
    return true;
}
void CodexAgent::activity() {
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return;
    last_activity_=now; // Only the existing genuine activity callers renew idle.
}
bool CodexAgent::finishHumanWait() {
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return false;
    human_wait_start_=-1;human_wait_id_.clear();
    if(native_work_id_.isEmpty())wait_accounted_at_=-1;
    return true;
}
bool CodexAgent::beginHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if(generation_!=originalGeneration || failed_ || !process_ || operation_start_<0)return false;
    const auto key=idKey(originalRequestId);
    const auto found=server_requests_.constFind(key);
    if(key.isEmpty() || found==server_requests_.cend())return false;
    if(human_wait_start_>=0)return human_wait_id_==found.key();
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return false;
    if(operationExpired(now)){fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline);return false;}
    human_wait_id_=found.key();human_wait_start_=now;wait_accounted_at_=now;
    return true;
}
bool CodexAgent::endHumanWait(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if(generation_!=originalGeneration || failed_ || !process_)return false;
    const auto key=idKey(originalRequestId);
    if(key.isEmpty() || !server_requests_.contains(key) || (human_wait_start_>=0 && human_wait_id_!=key))return false;
    return finishHumanWait();
}
bool CodexAgent::beginNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if(generation_!=originalGeneration || failed_ || !process_ || operation_start_<0)return false;
    const auto key=idKey(originalRequestId);
    const auto found=server_requests_.constFind(key);
    if(key.isEmpty() || found==server_requests_.cend())return false;
    if(!native_work_id_.isEmpty())return native_work_id_==found.key();
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return false;
    if(operationExpired(now)){fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline);return false;}
    native_work_id_=found.key();native_work_waiting_=false;wait_accounted_at_=now;
    return true;
}
bool CodexAgent::setNativeWorkWaiting(const QJsonValue& originalRequestId, quint64 originalGeneration, bool waiting) {
    if(generation_!=originalGeneration || failed_ || !process_ || operation_start_<0)return false;
    const auto found=server_requests_.constFind(native_work_id_);
    if(native_work_id_.isEmpty() || found==server_requests_.cend() || found->id!=originalRequestId)return false;
    if(native_work_waiting_==waiting)return true;
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return false;
    if(operationExpired(now)){fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline);return false;}
    native_work_waiting_=waiting;wait_accounted_at_=now;
    return true;
}
bool CodexAgent::endNativeWork(const QJsonValue& originalRequestId, quint64 originalGeneration) {
    if(generation_!=originalGeneration || failed_ || !process_)return false;
    if(native_work_id_.isEmpty()) {
        // Idempotent matching cleanup, without allocating a new encoded key.
        return std::any_of(server_requests_.cbegin(),server_requests_.cend(),[&](const auto& request){return request.id==originalRequestId;});
    }
    const auto found=server_requests_.constFind(native_work_id_);
    if(found==server_requests_.cend() || found->id!=originalRequestId)return false;
    const auto now=clock_.elapsed();
    if(!accountWaits(now))return false;
    native_work_id_.clear();native_work_waiting_=false;
    if(human_wait_start_<0)wait_accounted_at_=-1;
    if(operationExpired(now)){fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline);return false;}
    return true;
}
void CodexAgent::settleOperation() {
    human_wait_start_=-1;human_wait_id_.clear();native_work_id_.clear();native_work_waiting_=false;wait_accounted_at_=-1;
    operation_start_=-1;total_ms_=0;idle_ms_=0;
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
    const auto frame=qScopeGuard([receiver]{if(receiver){--receiver->active_frames_;receiver->maybeOwnersReleased();}});
    if (deferred_required_.isEmpty() || !process_ || failed_) return;
    try {
        checkDeadline();
        if (!receiver || generation_ != scope || process_ != process || failed_ || !process_ || process_->state() != QProcess::Running) return;
        const auto queued = static_cast<quint64>(process_->bytesToWrite());
        if(queued!=0)return; // Backpressure, never a cumulative admission quota.
        auto line=std::move(deferred_required_);deferred_required_.clear();deferred_deadline_=-1;
        // Transfer this exact prepared original once. Any partial write is a
        // fatal uncertain delivery; never replay or rebuild it from current UI.
        const auto written=process->write(line);
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
    const auto operationNow=clock_.elapsed();
    if(!accountWaits(operationNow))return;
    if(operationExpired(operationNow))fail("The official agent operation exceeded its deadline.", FailureKind::OperationDeadline);
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
    if (metadata.value("layoutVersion") != 1 || metadata.value("version") != QString::fromLatin1(EDI_CODEX_RUNTIME_VERSION) ||
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
    if ((release_owner_ && process_owner_alive_) || process_ || retired_process_ || active_frames_ || reading_ || executable.isEmpty() || !QFileInfo(workspace).isAbsolute() || !QFileInfo(workspace).isDir())
        return false;
    const QPointer<CodexAgent> receiver(this);
    QPointer<QProcess> prepared;
    auto scope = generation_;
    const auto current = [&] { return receiver && generation_ == scope && process_ == prepared.data(); };
    try {
        if (generation_ == std::numeric_limits<quint64>::max()) return false;
        scope = ++generation_;
        settleOperation();
        failure_kind_ = FailureKind::Other;
        failed_ = false; eof_pending_=false; incoming_.clear(); deferred_required_.clear(); optional_queued_bytes_ = 0; deferred_deadline_ = -1;
        pending_.clear(); optional_usage_ids_.clear(); server_requests_.clear();
        pending_sizes_.clear(); pending_deadlines_.clear(); server_sizes_.clear();
        pending_bytes_ = 0; wire_bytes_ = 0; event_count_ = 0;
        auto* process = release_owner_?static_cast<QProcess*>(new Process(this,scope,release_owner_)):new QProcess(this);
        prepared = process; process_ = process;
        // Birth/barrier publish with the original process_, before any original
        // start/error/started callback, including failed-to-start.
        if(release_owner_){process_birth_=scope;process_owner_alive_=true;}
        process->setProgram(executable);
        QStringList arguments{QStringLiteral("--listen"), QStringLiteral("stdio://"),
            QStringLiteral("-c"), QStringLiteral("sandbox_mode=\"read-only\""),
            QStringLiteral("-c"), QStringLiteral("approval_policy=\"never\""),
            QStringLiteral("-c"), QStringLiteral("features.shell_zsh_fork=false"),
            QStringLiteral("-c"), QStringLiteral("features.shell_tool=false"),
            QStringLiteral("-c"), QStringLiteral("features.view_image=false"),
            QStringLiteral("-c"), QStringLiteral("features.stable_environment_tools=false"),
            QStringLiteral("-c"), QStringLiteral("features.apps=false"),
            QStringLiteral("-c"), QStringLiteral("features.plugins=false"),
            QStringLiteral("-c"), QStringLiteral("features.remote_plugin=false"),
            QStringLiteral("-c"), QStringLiteral("features.multi_agent=false"),
            QStringLiteral("-c"), QStringLiteral("orchestrator.mcp.enabled=false")};
        if(policyPatch().isEmpty())arguments <<
            QStringLiteral("-c") << QStringLiteral("features.default_mode_request_user_input=true") <<
            QStringLiteral("-c") << QStringLiteral("tools.experimental_request_user_input.enabled=true");
        process->setArguments(arguments);
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
            const auto frame=qScopeGuard([receiver]{if(receiver){--receiver->active_frames_;receiver->maybeOwnersReleased();}});
            try {
                original->setReadChannel(QProcess::StandardError);
                while (current() && !failed_ && original->bytesAvailable() > 0) {
                    const auto count=static_cast<quint64>(Limits::http_chunk_bytes);

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

bool CodexAgent::write(const QJsonObject& envelope, const std::function<bool()>& prepare, bool nonfatalPreflight, bool optionalUsage,
                       void* preparation, bool (*handoff)(void*) noexcept) {
    const QPointer<CodexAgent> receiver(this);
    if(active_frames_==std::numeric_limits<quint64>::max())return false;
    ++active_frames_;
    const auto frame=qScopeGuard([receiver]{if(receiver){--receiver->active_frames_;receiver->maybeOwnersReleased();}});
    auto* process = process_; const auto epoch = generation_;
    if (!process_ || failed_ || process_->state() != QProcess::Running) return false;
    checkDeadline(); if (!receiver || process_ != process || generation_ != epoch || failed_) return false;
    quint64 encoded = 0;
    if (!encodedSize(envelope, std::nullopt, encoded)) {
        if (!nonfatalPreflight) fail("The official agent request has invalid Unicode, number or nesting."); return false;
    }
    const auto initialQueued = static_cast<quint64>(process_->bytesToWrite());
    const auto lineSize = encoded + 1;
    if(optionalUsage && (initialQueued!=0 || optional_queued_bytes_!=0 || !deferred_required_.isEmpty()))return false;
    if(!optionalUsage)preemptOptionalUsage();
    if(!receiver || process_!=process || generation_!=epoch || failed_ || !process_)return false;
    const auto queued=static_cast<quint64>(process_->bytesToWrite());
    const bool deferred=!deferred_required_.isEmpty() || queued!=0;
    auto line=QJsonDocument(envelope).toJson(QJsonDocument::Compact);
    if(static_cast<quint64>(line.size())!=encoded) {
        if(!nonfatalPreflight)fail("The official agent request could not be encoded consistently.");return false;
    }
    line.append('\n');
    auto heldWire=deferred_required_;
    if(deferred)heldWire.append(line);
    const auto priorHeld=deferred_required_.size();
    if(prepare && !prepare())return false;
    if(!receiver || failed_ || process_!=process || generation_!=epoch || priorHeld!=deferred_required_.size())return false;
    if(handoff && !handoff(preparation))return false;
    if(!receiver || failed_ || process_!=process || generation_!=epoch || priorHeld!=deferred_required_.size())return false;
    if(deferred) {
        deferred_required_.swap(heldWire);
        if(deferred_deadline_<0)deferred_deadline_=clock_.elapsed()+static_cast<qint64>(Limits::http_json_ms);
        flushRequired();return receiver && process_==process && generation_==epoch && !failed_;
    }
    if(optionalUsage)optional_queued_bytes_=lineSize;
    if(process->write(line)!=line.size()) {
        if(receiver && process_==process && generation_==epoch)fail("The official agent request could not be delivered.");return false;
    }
    return receiver && process_==process && generation_==epoch && !failed_;
}

QString CodexAgent::request(const QString& method, const QJsonObject& params, const std::function<bool(const QString&)>& prepare) {
    const QPointer<CodexAgent> receiver(this);
    if(active_frames_==std::numeric_limits<quint64>::max())return {};
    ++active_frames_;
    const auto frame=qScopeGuard([receiver]{if(receiver){--receiver->active_frames_;receiver->maybeOwnersReleased();}});
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
        if (optional && (!deferred_required_.isEmpty() || optional_queued_bytes_ != 0 || !process_ || process_->bytesToWrite() != 0)) return {};
        if (optional) for (auto i = pending_.constBegin(); i != pending_.constEnd(); ++i)
            if (i.value() == "account/rateLimits/read") return {};
        id = QStringLiteral("edi-%1-%2").arg(generation_).arg(++next_id_);
        quint64 bytes = 0;
        const QJsonObject envelope{{"id", id}, {"method", method}, {"params", params}};
        if (!encodedSize(envelope, std::nullopt, bytes)) return {};
        if (!optional) preemptOptionalUsage();
        if (!receiver || process_ != originalProcess || generation_ != scope) return {};

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
bool CodexAgent::answer(const QJsonValue& originalId,const QJsonObject& result,void* preparation,
                        bool (*handoff)(void*) noexcept,const std::function<bool()>& admit) {
    const auto key=idKey(originalId);const QPointer<CodexAgent> receiver(this);const QPointer<QProcess> process(process_);const auto epoch=generation_;
    if(key.isEmpty() || !server_requests_.contains(key))return false;
    // Account/current-question admission happens after optional-usage callbacks,
    // before detaching the question or consuming the original response owner.
    return write({{QStringLiteral("id"),originalId},{QStringLiteral("result"),result}},[&] {
        if(admit && !admit())return false;
        if(!receiver || process_!=process || generation_!=epoch || failed_ || !server_requests_.contains(key))return false;
        if(human_wait_start_>=0 && human_wait_id_==key && !endHumanWait(originalId,epoch))return false;
        if(native_work_id_==key && !endNativeWork(originalId,epoch))return false;
        // Retire before actual delivery: an uncertain write still permits no repeat.
        server_requests_.remove(key);pending_bytes_-=server_sizes_.take(key);return true;
    },false,false,preparation,handoff);
}
bool CodexAgent::reject(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (key.isEmpty() || !server_requests_.contains(key) || (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_))) return false;
    if(native_work_id_==key && !endNativeWork(originalId,generation_))return false;
    const auto id = server_requests_.take(key).id; pending_bytes_ -= server_sizes_.take(key);
    return write({{"id", id}, {"error", QJsonObject{{"code", -32601}, {"message", "This client does not support this request."}}}});
}
void CodexAgent::resolved(const QJsonValue& originalId) {
    const auto key = idKey(originalId);
    if (human_wait_start_ >= 0 && human_wait_id_ == key && !endHumanWait(originalId, generation_)) return;
    if(native_work_id_==key && !endNativeWork(originalId,generation_))return;
    server_requests_.remove(key); pending_bytes_ -= server_sizes_.take(key);
}
bool CodexAgent::deferServerRequest(const QJsonValue& originalId,quint64 originalGeneration) {
    if(generation_!=originalGeneration || failed_ || !process_)return false;
    const auto key=idKey(originalId);auto found=server_requests_.find(key);
    if(key.isEmpty() || found==server_requests_.end() || found->id!=originalId)return false;
    found->deferred=true;return true;
}
void CodexAgent::resumeDeferredRequests(quint64 originalGeneration) {
    const QPointer<CodexAgent> receiver(this);const QPointer<QProcess> process(process_);
    const auto current=[&]{return receiver && process && generation_==originalGeneration && process_==process && !failed_;};
    if(!current())return;
    QList<QPair<quint64,QString>> ordered;
    for(auto it=server_requests_.cbegin();it!=server_requests_.cend();++it)if(it->deferred)ordered.append({it->order,it.key()});
    std::sort(ordered.begin(),ordered.end());
    for(const auto& entry:ordered) {
        if(!current())return;
        auto found=server_requests_.find(entry.second);
        if(found==server_requests_.end() || found->order!=entry.first || !found->deferred)continue;
        const auto request=*found;found->deferred=false; // Consume before the original callback can reenter.
        emit serverRequest(request.id,request.method,request.params);
        if(!current())return;
        found=server_requests_.find(entry.second);
        if(found!=server_requests_.end() && found->order==entry.first && found->deferred)return;
    }
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
    const auto frame=qScopeGuard([receiver]{if(receiver){receiver->reading_=false;--receiver->active_frames_;receiver->maybeOwnersReleased();}});
    const auto current = [&] { return receiver && original && process_ == original.data() && generation_ == scope; };
    const auto drain=[&] {
        if (!current() || failed_) return;
        try {
            process->setReadChannel(QProcess::StandardOutput);
            while (current() && !failed_ && original->bytesAvailable() > 0) {
                checkDeadline(); if (!current() || failed_) return;
                const auto requested=static_cast<quint64>(Limits::http_chunk_bytes);
                const auto bytes=process->read(static_cast<qint64>(requested));
                if(!current() || failed_)return;
                if(bytes.isEmpty())return;
                if(static_cast<quint64>(bytes.size())>requested)throw std::logic_error("Agent read exceeded requested bytes");
                wire_bytes_+=static_cast<quint64>(bytes.size());
                incoming_.append(bytes);
                qsizetype newline;
                while(current() && !failed_ && (newline=incoming_.indexOf('\n'))>=0) {
                    const auto record=incoming_.left(newline);
                    incoming_.remove(0,newline+1);
                    const bool blank=std::all_of(record.cbegin(),record.cend(),[](char c){return c==' ' || c=='\t' || c=='\r' || c=='\n' || c=='\v' || c=='\f';});
                    if (!blank) {
                        ++event_count_; // Observation only; valid work has no event quota.
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
            if (++depth > Limits::json_depth) { fail("The official agent response has unsupported JSON nesting."); return; }
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
            if (key.isEmpty() || server_requests_.contains(key)) {
                fail("The official agent request identity is invalid or duplicated."); return;
            }
            quint64 bytes = 0;
            if (!encodedSize(envelope, std::nullopt, bytes)) {
                fail("The official agent request has invalid Unicode, number or nesting."); return;
            }
            if(server_sequence_==std::numeric_limits<quint64>::max())throw std::length_error("Server request identity is exhausted");
            server_requests_.insert(key,ServerRequest{id,method,params,++server_sequence_,false});server_sizes_.insert(key,bytes);pending_bytes_+=bytes;
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
void CodexAgent::fail(const char* explanation, FailureKind kind) noexcept {
    if (failed_) return;
    const QPointer<QProcess> original(process_);
    failure_kind_ = kind; failure_generation_ = generation_;
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

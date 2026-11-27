// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_process.hpp"
#include "../../core/src/assistant_json.hpp"
#include "assistant_guard_launch.hpp"
#include "codex_agent.hpp"
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QScopeGuard>
#include <algorithm>
#include <limits>
#include <string>

namespace edi_app {

AssistantProcess::AssistantProcess(QObject* parent) : QObject(parent) {
    clock_.start();
    timer_.setInterval(100);
    connect(&timer_, &QTimer::timeout, this, [this] {
        const QPointer<AssistantProcess> receiver(this);
        const auto scope = generation_;
        try {
            checkDeadline();
        } catch (...) {
            if (receiver && generation_ == scope) failWith("The assistant deadline could not be checked.");
        }
    });
}

AssistantProcess::~AssistantProcess() { retire(); }

QString AssistantProcess::guardExecutable() { return assistant_guard_executable(); }

bool AssistantProcess::running() const noexcept {
    return process_ && !failed_ && process_->state() == QProcess::Running;
}

void AssistantProcess::setLimits(quint64 recordBytes, quint64 writeBytes) noexcept {
    record_bytes_ = recordBytes;
    write_bytes_ = writeBytes;
}

bool AssistantProcess::start(const QString& guard, const QString& executable, const QStringList& args,
                             const QString& workspace, const QProcessEnvironment& environment) {
    if (guard.isEmpty() || executable.isEmpty() || !QFileInfo(workspace).isAbsolute() ||
        !QFileInfo(workspace).isDir())
        return false;
    if (process_) retire();
    if (generation_ == std::numeric_limits<quint64>::max()) return false;
    const QPointer<AssistantProcess> receiver(this);
    const auto scope = ++generation_;
    settleOperation();
    failed_ = false;
    failure_kind_ = FailureKind::Other;
    eof_pending_ = false;
    exit_code_ = -1;
    exit_detail_.clear();
    incoming_.clear();
    diagnostics_.clear();
    QPointer<QProcess> prepared;
    const auto current = [&] { return receiver && generation_ == scope && prepared && process_ == prepared.data(); };
    try {
        auto* process = new QProcess(this);
        prepared = process;
        process_ = process;
        assistant_guard_prepare(*process, guard, executable, args, workspace, &environment);
        connect(process, &QProcess::started, this, [this, original = prepared, scope] {
            const QPointer<AssistantProcess> alive(this);
            const auto stillCurrent = [&] {
                return alive && original && process_ == original.data() && generation_ == scope;
            };
            try {
                if (stillCurrent() && !failed_) emit started();
            } catch (...) {
                if (stillCurrent()) failWith("The assistant handshake could not be prepared.");
            }
        });
        connect(process, &QProcess::readyReadStandardOutput, this, [this, original = prepared, scope] {
            if (original) read(original.data(), scope);
        });
        connect(process, &QProcess::readyReadStandardError, this, [this, original = prepared, scope] {
            if (original) readStderr(original.data(), scope);
        });
        connect(process, &QProcess::errorOccurred, this,
                [this, original = prepared, scope](QProcess::ProcessError error) {
            if (!original || process_ != original.data() || generation_ != scope || failed_) return;
            // A write fails when the guard has already exited; its exit code, read at finished, says why.
            if (error == QProcess::WriteError) return;
            try {
                exit_detail_ = QString::fromLatin1(assistant_process_error_kind(error)) + QStringLiteral(": ") +
                               original->errorString();
            } catch (...) {
            }
            failWith("The assistant process could not continue (%1).");
        });
        connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
                [this, original = prepared, scope](int code, QProcess::ExitStatus status) {
            if (original && process_ == original.data() && generation_ == scope)
                exit_code_ = status == QProcess::NormalExit ? code : -1;
            if (original) readStderr(original.data(), scope, true);
            if (original) read(original.data(), scope, true);
        });
        process->start();
        return current() && !failed_;
    } catch (...) {
        if (current()) failWith("The assistant process could not be prepared.");
        return false;
    }
}

bool AssistantProcess::write(const QJsonObject& object) {
    if (!running()) return false;
    const QPointer<AssistantProcess> receiver(this);
    auto* process = process_;
    const auto scope = generation_;
    const auto current = [&] { return receiver && process_ == process && generation_ == scope && !failed_; };
    checkDeadline();
    if (!current()) return false;
    bool delivering = false;
    try {
        quint64 encoded = 0;
        if (!codex_encoded_size(object, write_bytes_, encoded)) return false;
        auto line = QJsonDocument(object).toJson(QJsonDocument::Compact);
        if (static_cast<quint64>(line.size()) != encoded) return false;
        line.append('\n');
        // QProcess queues the whole line or nothing; anything else is an uncertain delivery.
        delivering = true;
        if (process->write(line) != line.size()) {
            if (current()) failWith("The assistant request could not be delivered.");
            return false;
        }
    } catch (...) {
        if (delivering && current()) failWith("The assistant request could not be delivered.");
        return false;
    }
    return current();
}

void AssistantProcess::read(QProcess* process, quint64 scope, bool finished) {
    if (!process || process_ != process || generation_ != scope) return;
    // A nested finished notification records only the EOF; the active reader drains the tail.
    if (finished) eof_pending_ = true;
    if (reading_ == process) return;
    const QPointer<AssistantProcess> receiver(this);
    const QPointer<QProcess> original(process);
    // A process started from inside an older one's record handler reads on its own.
    QProcess* const outer = reading_;
    reading_ = process;
    const auto frame = qScopeGuard([receiver, outer] {
        if (receiver) receiver->reading_ = outer;
    });
    const auto current = [&] {
        return receiver && original && process_ == original.data() && generation_ == scope;
    };
    const auto chunk = static_cast<qint64>(Limits::http_chunk_bytes);
    try {
        while (current() && !failed_ && original->bytesAvailable() > 0) {
            checkDeadline();
            if (!current() || failed_) return;
            original->setReadChannel(QProcess::StandardOutput);
            const auto bytes = original->read(chunk);
            if (!current() || failed_) return;
            if (bytes.isEmpty()) break;
            incoming_.append(bytes);
            qsizetype newline;
            while (current() && !failed_ && (newline = incoming_.indexOf('\n')) >= 0) {
                if (static_cast<quint64>(newline) > record_bytes_) {
                    failWith("The assistant sent a record over the size limit.", FailureKind::LocalCapacity);
                    return;
                }
                const auto line = incoming_.left(newline);
                incoming_.remove(0, newline + 1);
                const bool blank = std::all_of(line.cbegin(), line.cend(), [](char c) {
                    return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
                });
                if (blank) continue;
                receive(line);
                if (!current()) return;
            }
            if (current() && !failed_ && static_cast<quint64>(incoming_.size()) > record_bytes_) {
                failWith("The assistant sent a record over the size limit.", FailureKind::LocalCapacity);
                return;
            }
        }
    } catch (...) {
        if (current()) failWith("The assistant output could not be retained.", FailureKind::LocalCapacity);
    }
    if (!current() || !eof_pending_) return;
    eof_pending_ = false;
    if (!failed_) {
        const auto end = assistant_guard_end(exit_code_);
        if (end.kind == AssistantGuardExit::NotStarted) failWith("The assistant could not be started by the system.");
        else if (end.kind == AssistantGuardExit::Signal) {
            exit_detail_ = QString::number(end.number);
            failWith("The assistant was stopped by the system (signal %1).");
        } else if (end.kind == AssistantGuardExit::Refused)
            failWith("The assistant lifetime guard refused to start the assistant.");
        else if (end.kind == AssistantGuardExit::ExitCode) {
            exit_detail_ = QString::number(end.number);
            failWith("The assistant process ended with exit code %1. Unfinished work was interrupted.");
        } else failWith("The assistant process ended. Unfinished work was interrupted.");
    }
    if (!current()) return;
    process_ = nullptr;
    original->deleteLater();
}

void AssistantProcess::readStderr(QProcess* process, quint64 scope, bool finished) {
    const QPointer<AssistantProcess> receiver(this);
    const QPointer<QProcess> original(process);
    const auto current = [&] {
        return receiver && original && process_ == original.data() && generation_ == scope;
    };
    if (!current()) return;
    const auto limit = static_cast<qsizetype>(Limits::http_chunk_bytes);
    const auto emitLine = [&](QByteArray line) {
        if (line.endsWith('\r')) line.chop(1);
        emit stderrLine(QString::fromUtf8(line));
        return current();
    };
    try {
        // QProcess already holds the bytes; reading them all keeps the stdout read channel untouched.
        diagnostics_.append(original->readAllStandardError());
        qsizetype newline;
        while ((newline = diagnostics_.indexOf('\n')) >= 0) {
            const auto line = diagnostics_.left(newline);
            diagnostics_.remove(0, newline + 1);
            if (!emitLine(line)) return;
        }
        // A line without an end is passed on in pieces rather than held without bound.
        if (diagnostics_.size() > limit || (finished && !diagnostics_.isEmpty())) {
            const auto line = diagnostics_;
            diagnostics_.clear();
            if (!emitLine(line)) return;
        }
    } catch (...) {
        if (current()) failWith("The assistant diagnostic channel could not be drained.");
    }
}

void AssistantProcess::receive(const QByteArray& line) {
    try {
        // Qt keeps the last of duplicate members without saying so; edi's own parser refuses them, and invalid
        // UTF-8 and deep nesting, before Qt reads the record.
        (void)edi::assistant::detail::parse(line.toStdString(), record_bytes_);
    } catch (const edi::assistant::detail::Refusal&) {
        failWith("The assistant sent a record that is not valid JSON.");
        return;
    } catch (const std::exception&) {
        failWith("The assistant output could not be retained.", FailureKind::LocalCapacity);
        return;
    }
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(line, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        failWith("The assistant sent a record that is not a JSON object.");
        return;
    }
    emit record(document.object());
}

void AssistantProcess::failWith(const char* explanation, FailureKind kind) noexcept {
    if (failed_ || !process_) return;
    QString text;
    try {
        text = tr(explanation);
        if (!exit_detail_.isEmpty()) text = text.arg(exit_detail_);
    } catch (...) {
    }
    exit_detail_.clear();
    fail(text, kind);
}

void AssistantProcess::fail(const QString& explanation, FailureKind kind) noexcept {
    if (failed_ || !process_) return;
    const QPointer<QProcess> original(process_);
    failure_kind_ = kind;
    failure_generation_ = generation_;
    failed_ = true;  // Revoke first: observers and writes see the failure.
    settleOperation();
    incoming_.clear();
    try {
        emit failed(explanation, kind);
    } catch (...) {
    }
    try {
        if (original && original->state() != QProcess::NotRunning) original->terminate();
    } catch (...) {
    }
}

void AssistantProcess::retire() {
    if (generation_ != std::numeric_limits<quint64>::max()) ++generation_;
    failed_ = true;
    settleOperation();
    incoming_.clear();
    diagnostics_.clear();
    eof_pending_ = false;
    const QPointer<QProcess> process(process_);
    process_ = nullptr;
    if (!process) return;
    process->disconnect(this);
    // cppcheck-suppress identicalConditionAfterEarlyExit ; the call above can delete it
    if (!process) return;
    // Shutdown must outlive this object without a blocking QProcess destructor. Ending the guard ends the
    // runtime's process group.
    process->setParent(nullptr);
    // cppcheck-suppress identicalConditionAfterEarlyExit ; the call above can delete it
    if (!process) return;
    process->terminate();
    // cppcheck-suppress identicalConditionAfterEarlyExit ; the call above can delete it
    if (!process) return;
    QTimer::singleShot(static_cast<int>(Limits::callback_ms), process.data(), [process] {
        if (process && process->state() != QProcess::NotRunning) process->kill();
    });
    connect(process.data(), qOverload<int, QProcess::ExitStatus>(&QProcess::finished), process.data(),
            &QObject::deleteLater);
    if (process->state() == QProcess::NotRunning) process->deleteLater();
}

bool AssistantProcess::operationExpired(qint64 now) const noexcept {
    return operation_start_ >= 0 &&
           (now < operation_start_ || now < last_activity_ ||
            (total_ms_ && static_cast<quint64>(now - operation_start_) >= total_ms_) ||
            (idle_ms_ && static_cast<quint64>(now - last_activity_) >= idle_ms_));
}

bool AssistantProcess::accountWaits(qint64 now) {
    if (wait_accounted_at_ < 0) return true;
    if (now < wait_accounted_at_ || operation_start_ < 0 || operation_start_ > wait_accounted_at_ ||
        last_activity_ > wait_accounted_at_ || (!idle_suspended_ && !total_suspended_)) {
        failWith("The assistant wait clock is invalid.");
        return false;
    }
    // Each timestamp is at most the last sample, so shifting by this interval stays at most now.
    const auto elapsed = now - wait_accounted_at_;
    if (total_suspended_) operation_start_ += elapsed;
    if (idle_suspended_) last_activity_ += elapsed;
    wait_accounted_at_ = now;
    return true;
}

void AssistantProcess::checkDeadline() {
    if (failed_ || operation_start_ < 0) return;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return;
    if (operationExpired(now))
        failWith("The assistant operation exceeded its deadline.", FailureKind::OperationDeadline);
}

void AssistantProcess::beginOperation(quint64 totalMs, quint64 idleMs) {
    const QPointer<AssistantProcess> receiver(this);
    const auto scope = generation_;
    if (!process_ || failed_) return;
    checkDeadline();
    if (!receiver || generation_ != scope || failed_) return;
    idle_suspended_ = false;
    total_suspended_ = false;
    wait_accounted_at_ = -1;
    const auto now = clock_.elapsed();
    // A second clock sample can cross the old deadline after checkDeadline; expiry never becomes a new operation.
    if (operationExpired(now)) {
        failWith("The assistant operation exceeded its deadline.", FailureKind::OperationDeadline);
        return;
    }
    if (operation_start_ >= 0 && total_ms_) {
        const auto remaining = total_ms_ - static_cast<quint64>(now - operation_start_);
        if (totalMs == 0 || totalMs > remaining) totalMs = remaining;
    }
    operation_start_ = now;
    last_activity_ = now;
    total_ms_ = totalMs;
    idle_ms_ = idleMs;
    timer_.start();
}

void AssistantProcess::settleOperation() {
    idle_suspended_ = false;
    total_suspended_ = false;
    wait_accounted_at_ = -1;
    operation_start_ = -1;
    total_ms_ = 0;
    idle_ms_ = 0;
    timer_.stop();
}

void AssistantProcess::activity() {
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return;
    last_activity_ = now;
}

void AssistantProcess::suspendIdle(bool suspended) {
    if (operation_start_ < 0 || failed_ || idle_suspended_ == suspended) return;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return;
    if (operationExpired(now)) {
        failWith("The assistant operation exceeded its deadline.", FailureKind::OperationDeadline);
        return;
    }
    idle_suspended_ = suspended;
    wait_accounted_at_ = (idle_suspended_ || total_suspended_) ? now : -1;
}

void AssistantProcess::suspendTotal(bool suspended) {
    if (operation_start_ < 0 || failed_ || total_suspended_ == suspended) return;
    const auto now = clock_.elapsed();
    if (!accountWaits(now)) return;
    if (operationExpired(now)) {
        failWith("The assistant operation exceeded its deadline.", FailureKind::OperationDeadline);
        return;
    }
    total_suspended_ = suspended;
    wait_accounted_at_ = (idle_suspended_ || total_suspended_) ? now : -1;
}

}  // namespace edi_app

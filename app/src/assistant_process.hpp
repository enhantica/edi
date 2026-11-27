// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QObject>
#include <QPointer>
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QTimer>
#include "assistant_provider.hpp"
#include "edi/assistant_limits.hpp"

namespace edi_app {

/// One assistant runtime process that speaks one JSON object per line on stdin and stdout (ADR-0108 §2), started
/// through edi's lifetime guard. Every output is fenced by a generation: after retire() or a new start(), output of
/// the old process is dropped. stderr is passed on line by line for diagnostics only and is never shown to users.
/// Construct and call on the owner thread; signals use direct connections.
class AssistantProcess final : public QObject {
    Q_OBJECT
public:
    using Limits = edi::assistant::Limits;
    using FailureKind = AssistantProvider::FailureKind;

    explicit AssistantProcess(QObject* parent = nullptr);
    ~AssistantProcess() override;

    /// edi's lifetime guard, or empty when it is not installed.
    static QString guardExecutable();

    /// Start `executable` with `args` through `guard` in `workspace`, with exactly `environment`. Retires any
    /// earlier process first. Returns false when nothing was started. A start error is reported by `failed`, which
    /// may come before this returns.
    bool start(const QString& guard, const QString& executable, const QStringList& args, const QString& workspace,
               const QProcessEnvironment& environment);
    /// Write one compact JSON line. Refuses, writing nothing, when the record cannot be encoded, is over the write
    /// limit, or the process is not running, has failed or was retired.
    bool write(const QJsonObject& record);
    /// Stop the process (the guard ends the runtime and its children), bump the generation and drop late output.
    void retire();
    /// Fail the current generation with an explanation the user may see, then stop the process.
    void fail(const QString& explanation, FailureKind kind = FailureKind::Other) noexcept;

    quint64 generation() const noexcept { return generation_; }
    /// True while the current process runs and has not failed.
    bool running() const noexcept;
    bool failureActive() const noexcept { return failed_ && failure_generation_ == generation_; }
    FailureKind failureKind() const noexcept { return failure_kind_; }

    /// The largest line read (`recordBytes`) and written (`writeBytes`), without the newline.
    void setLimits(quint64 recordBytes, quint64 writeBytes) noexcept;

    /// Start an operation deadline: `totalMs` from now and `idleMs` since the last activity; 0 disables either. A
    /// nested operation keeps no more total time than the outer one has left. Expiry fails with OperationDeadline.
    /// Needs a started process; start() ends any earlier operation.
    void beginOperation(quint64 totalMs, quint64 idleMs);
    /// End the operation deadline and any suspension.
    void settleOperation();
    /// Renew the idle clock. Only genuine progress should call this.
    void activity();
    /// Stop (true) or restart (false) the idle clock, e.g. while a person answers a question.
    void suspendIdle(bool suspended);
    /// Stop (true) or restart (false) the total clock as well, for a wait that is not the runtime's work.
    void suspendTotal(bool suspended);

signals:
    void started();
    /// One complete line, a JSON object.
    void record(const QJsonObject& record);
    /// Once per generation: the process ended, crashed, sent something invalid or over a limit, or a deadline
    /// passed. The process is stopped.
    void failed(const QString& explanation, AssistantProvider::FailureKind kind);
    /// One line of the runtime's stderr. Diagnostics only: it may hold user data and is never shown.
    void stderrLine(const QString& line);

private:
    void read(QProcess* process, quint64 generation, bool finished = false);
    void readStderr(QProcess* process, quint64 generation, bool finished = false);
    void receive(const QByteArray& line);
    void failWith(const char* explanation, FailureKind kind = FailureKind::Other) noexcept;
    void checkDeadline();
    bool accountWaits(qint64 now);
    bool operationExpired(qint64 now) const noexcept;

    QProcess* process_ = nullptr;
    quint64 generation_ = 0;
    bool failed_ = false;
    FailureKind failure_kind_ = FailureKind::Other;
    quint64 failure_generation_ = 0;
    QProcess* reading_ = nullptr;  // The process whose stdout is being read, compared only.
    bool eof_pending_ = false;
    int exit_code_ = -1;
    QString exit_detail_;
    QByteArray incoming_, diagnostics_;
    quint64 record_bytes_ = Limits::message_bytes, write_bytes_ = Limits::request_bytes;
    QElapsedTimer clock_;
    QTimer timer_;
    qint64 operation_start_ = -1, last_activity_ = 0, wait_accounted_at_ = -1;
    quint64 total_ms_ = 0, idle_ms_ = 0;
    bool idle_suspended_ = false, total_suspended_ = false;
};

}  // namespace edi_app

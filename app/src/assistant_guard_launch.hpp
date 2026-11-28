// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QProcess>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>

namespace edi_app {

/// edi's lifetime guard (app/tools/assistant_guard.cpp) next to the app, or the build's own when a development
/// runtime is named. Empty when neither is executable.
QString assistant_guard_executable();

/// The guard's command line for one runtime: `<appPid> <runtime> <arguments…>`.
QStringList assistant_guard_arguments(const QString& runtime, const QStringList& arguments);

/// Point `process` at the guard running `runtime` in `workspace`, with stdout and stderr kept apart. A null
/// `environment` leaves the process with the app's own environment; otherwise the runtime gets exactly that one.
void assistant_guard_prepare(QProcess& process, const QString& guard, const QString& runtime,
                             const QStringList& arguments, const QString& workspace,
                             const QProcessEnvironment* environment = nullptr);

/// How the guard said the runtime ended.
enum class AssistantGuardExit : unsigned char {
    Ended,       ///< exit code 0, or no code (a crash of the guard itself)
    NotStarted,  ///< 127: the runtime could not be started
    Refused,     ///< 125: the guard refused to start the runtime
    Signal,      ///< 128 + n: signal n stopped the runtime
    ExitCode,    ///< the runtime's own nonzero code
};
struct AssistantGuardEnd {
    AssistantGuardExit kind = AssistantGuardExit::Ended;
    int number = 0;  ///< the signal or the exit code, for the message
};
/// Read a guard exit code, or -1 when the guard did not exit normally.
AssistantGuardEnd assistant_guard_end(int exitCode);

/// A short name for a QProcess error, for a failure message.
const char* assistant_process_error_kind(QProcess::ProcessError error);

}  // namespace edi_app

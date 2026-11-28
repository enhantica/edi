// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_guard_launch.hpp"
#include "assistant_runtime_config.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <algorithm>

namespace edi_app {

QString assistant_guard_executable() {
    const auto guardName =
#ifdef Q_OS_WIN
        QStringLiteral("edi_assistant_guard.exe");
#else
        QStringLiteral("edi_assistant_guard");
#endif
    auto guard = QDir(QCoreApplication::applicationDirPath()).filePath(guardName);
    if (!QFileInfo(guard).isExecutable() && qEnvironmentVariableIsSet("EDI_CODEX_DEVELOPMENT_EXECUTABLE"))
        guard = QDir(QString::fromUtf8(EDI_CODEX_BUILD_APP_DIR)).filePath(guardName);
    if (!QFileInfo(guard).isExecutable()) return {};
    return guard;
}

QStringList assistant_guard_arguments(const QString& runtime, const QStringList& arguments) {
    auto command = arguments;
    command.prepend(runtime);
    command.prepend(QString::number(QCoreApplication::applicationPid()));
    return command;
}

void assistant_guard_prepare(QProcess& process, const QString& guard, const QString& runtime,
                             const QStringList& arguments, const QString& workspace,
                             const QProcessEnvironment* environment) {
    process.setProgram(guard);
    process.setArguments(assistant_guard_arguments(runtime, arguments));
    process.setWorkingDirectory(workspace);
    process.setProcessChannelMode(QProcess::SeparateChannels);
    // The guard does not touch the environment, so this is what the runtime gets.
    if (environment) process.setProcessEnvironment(*environment);
}

AssistantGuardEnd assistant_guard_end(int exitCode) {
    // The guard exits 127 when the runtime could not start, 128 + n when a signal stopped it (macOS stops a
    // program it refuses to run with signal 9), and the runtime's own code otherwise.
    if (exitCode == 127) return {AssistantGuardExit::NotStarted, 0};
    if (exitCode > 128 && exitCode < 160) return {AssistantGuardExit::Signal, exitCode - 128};
    if (exitCode == 125) return {AssistantGuardExit::Refused, 0};
    if (exitCode > 0) return {AssistantGuardExit::ExitCode, exitCode};
    return {AssistantGuardExit::Ended, 0};
}

const char* assistant_process_error_kind(QProcess::ProcessError error) {
    static const char* const kinds[] = {"start error", "crashed",     "timed out",
                                        "read error",  "write error", "unknown error"};
    return kinds[std::clamp(static_cast<int>(error), 0, 5)];
}

}  // namespace edi_app

// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QProcess>
#include <QByteArray>
#include <QMetaObject>
#include <atomic>
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <thread>
#ifdef Q_OS_WIN
#include "../../core/src/windows_sdk.hpp"
#include <tlhelp32.h>
#include <io.h>
#include <fcntl.h>
#else
#include <unistd.h>
#include <signal.h>
#endif

namespace {
#ifdef Q_OS_UNIX
void stopFamily(int) {
    ::kill(-::getpid(), SIGKILL);
    std::_Exit(125);
}
#endif
}

int main(int argc, char** argv) {
#ifndef Q_OS_WIN
    if (::setsid() < 0) return 125;
    ::signal(SIGTERM, stopFamily);
    ::signal(SIGINT, stopFamily);
    ::signal(SIGPIPE, SIG_IGN);
#else
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
    _setmode(_fileno(stderr), _O_BINARY);
#endif
    QCoreApplication app(argc, argv);
    const auto arguments = app.arguments();
    bool valid = false;
    const auto parent = arguments.value(1).toLongLong(&valid);
    if (!valid || parent <= 0 || arguments.size() < 3) return 125;
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    std::setvbuf(stderr, nullptr, _IONBF, 0);
#ifdef Q_OS_WIN
    const HANDLE parentHandle = OpenProcess(SYNCHRONIZE, FALSE, DWORD(parent));
    const HANDLE job = CreateJobObjectW(nullptr, nullptr);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!parentHandle || !job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits))) return 125;
    std::atomic<bool> launchReady{false};
    const auto stop = [&] { TerminateJobObject(job, 125); std::_Exit(125); };
    std::thread([&] {
        if (WaitForSingleObject(parentHandle, INFINITE) != WAIT_OBJECT_0) stop();
        while (!launchReady.load()) std::this_thread::sleep_for(std::chrono::milliseconds(10));
        stop();
    }).detach();
#else
    if (::getppid() != parent) return 125;
    const auto stop = [] { stopFamily(0); };
    std::thread([parent] {
        while (::getppid() == parent) std::this_thread::sleep_for(std::chrono::milliseconds(50));
        stopFamily(0);
    }).detach();
#endif
    QProcess process;
    process.setProgram(arguments.at(2));
    process.setArguments(arguments.mid(3));
#ifdef Q_OS_WIN
    process.setCreateProcessArgumentsModifier([](QProcess::CreateProcessArguments* args) { args->flags |= CREATE_SUSPENDED; });
#endif
    std::mutex mutex;
    std::condition_variable writable;
    std::size_t pending = 0;
    QObject::connect(&process, &QProcess::bytesWritten, &app, [&](qint64 count) {
        std::lock_guard lock(mutex);
        pending -= std::min(pending, static_cast<std::size_t>(count));
        writable.notify_one();
    });
    QObject::connect(&process, &QProcess::started, &app, [&] {
#ifdef Q_OS_WIN
        const auto pid = DWORD(process.processId());
        const HANDLE child = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_QUERY_INFORMATION, FALSE, pid);
        if (!child || !AssignProcessToJobObject(job, child)) {
            if (child) TerminateProcess(child, 125);
            else process.kill();
            launchReady = true;
            stop();
        }
        const HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        THREADENTRY32 entry{}; entry.dwSize = sizeof(entry);
        bool resumed = false;
        if (snapshot != INVALID_HANDLE_VALUE && Thread32First(snapshot, &entry)) do {
            if (entry.th32OwnerProcessID != pid) continue;
            const HANDLE thread = OpenThread(THREAD_SUSPEND_RESUME, FALSE, entry.th32ThreadID);
            if (thread) { resumed = ResumeThread(thread) != DWORD(-1); CloseHandle(thread); }
        } while (!resumed && Thread32Next(snapshot, &entry));
        if (snapshot != INVALID_HANDLE_VALUE) CloseHandle(snapshot);
        CloseHandle(child);
        launchReady = true;
        if (!resumed) stop();
#endif
        std::thread([&] {
            char buffer[16384];
            for (;;) {
#ifdef Q_OS_WIN
                const auto size = _read(_fileno(stdin), buffer, sizeof(buffer));
#else
                const auto size = ::read(STDIN_FILENO, buffer, sizeof(buffer));
#endif
                if (size <= 0) {
                    QMetaObject::invokeMethod(&process, [&] { process.closeWriteChannel(); }, Qt::QueuedConnection);
                    return;
                }
                std::unique_lock lock(mutex);
                writable.wait(lock, [&] { return pending < 1024 * 1024; });
                pending += static_cast<std::size_t>(size);
                lock.unlock();
                const QByteArray bytes(buffer, size);
                QMetaObject::invokeMethod(&process, [&, bytes] { if (process.write(bytes) != bytes.size()) stop(); }, Qt::QueuedConnection);
            }
        }).detach();
    });
    const auto forward = [&](const QByteArray& bytes, FILE* stream) {
        if (!bytes.isEmpty() && std::fwrite(bytes.constData(), 1, bytes.size(), stream) != static_cast<std::size_t>(bytes.size())) stop();
    };
    QObject::connect(&process, &QProcess::readyReadStandardOutput, &app, [&] { forward(process.readAllStandardOutput(), stdout); });
    QObject::connect(&process, &QProcess::readyReadStandardError, &app, [&] { forward(process.readAllStandardError(), stderr); });
    QObject::connect(&process, &QProcess::errorOccurred, &app, [&](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) {
#ifdef Q_OS_WIN
            launchReady = true;
#endif
            stop();
        }
    });
    QObject::connect(&process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), &app, [&](int, QProcess::ExitStatus) {
        forward(process.readAllStandardOutput(), stdout);
        forward(process.readAllStandardError(), stderr);
        stop();
    });
    process.start();
    return app.exec();
}

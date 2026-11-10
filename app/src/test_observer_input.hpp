// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_TEST_OBSERVER_INPUT_HPP
#define EDI_TEST_OBSERVER_INPUT_HPP

#include <QByteArray>
#include <QObject>
#include <functional>
#include <utility>

#ifdef Q_OS_WIN
#include <QTimer>

#include "../../core/src/windows_sdk.hpp"
#else
#include <sys/stat.h>
#include <unistd.h>

#include <QSocketNotifier>
#include <cerrno>
#endif

namespace edi_app::observer_input {
using Receive = std::function<void(const QByteArray&)>;
using Closed = std::function<void()>;

// System-test pipe transport only; the receiver owns notifications and parsing (ADR-0071).
inline bool install(QObject& receiver, Receive receive, Closed closed = {}) {
#ifdef Q_OS_WIN
    const HANDLE pipe = GetStdHandle(STD_INPUT_HANDLE);
    if (pipe == nullptr || pipe == INVALID_HANDLE_VALUE || GetFileType(pipe) != FILE_TYPE_PIPE)
        return false;
    auto* input = new QTimer(&receiver);
    input->setInterval(25);
    const auto stop = [input, closed = std::move(closed)] {
        input->stop();
        if (closed) closed();
    };
    QObject::connect(input, &QTimer::timeout, &receiver,
                     [pipe, receive = std::move(receive), stop] {
                         DWORD available = 0;
                         if (!PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr)) {
                             stop();
                             return;
                         }
                         if (available == 0) return;
                         char buffer[4096];
                         const auto capacity = static_cast<DWORD>(sizeof buffer);
                         DWORD got = 0;
                         if (!ReadFile(pipe, buffer, available < capacity ? available : capacity,
                                       &got, nullptr) ||
                             got == 0) {
                             stop();
                             return;
                         }
                         receive(QByteArray(buffer, static_cast<qsizetype>(got)));
                     });
    input->start();
#else
    struct stat status{};
    if (::fstat(STDIN_FILENO, &status) != 0 || !S_ISFIFO(status.st_mode)) return false;
    auto* input = new QSocketNotifier(STDIN_FILENO, QSocketNotifier::Read, &receiver);
    const auto stop = [input, closed = std::move(closed)] {
        input->setEnabled(false);
        if (closed) closed();
    };
    QObject::connect(
        input, &QSocketNotifier::activated, &receiver, [receive = std::move(receive), stop] {
            char buffer[4096];
            const ssize_t got = ::read(STDIN_FILENO, buffer, sizeof buffer);
            if (got < 0 && (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK)) return;
            if (got <= 0) {
                stop();
                return;
            }
            receive(QByteArray(buffer, static_cast<qsizetype>(got)));
        });
#endif
    return true;
}
}  // namespace edi_app::observer_input

#endif

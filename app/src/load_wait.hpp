// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_LOAD_WAIT_HPP
#define EDI_APP_LOAD_WAIT_HPP

#include <QEventLoop>
#include <QTimer>

#include "project_view_model.hpp"

namespace edi_app {

// For a caller that needs the data before it goes on (the documentation capture, the demo, tests): a Load data route
// reads its files off the GUI thread (edi ADR-0110), so `started` is only its first answer. False when the route
// refused in the call; otherwise whether the load ended with the data in the project, waiting at most `timeout_ms`.
// The refusal, if any, is the project's lastError.
inline bool wait_for_load(ProjectViewModel& project, bool started, int timeout_ms = 120000) {
    if (!started || !project.loadingData()) return started;
    bool settled = false;
    bool loaded = false;
    QEventLoop loop;
    const QMetaObject::Connection end =
        QObject::connect(&project, &ProjectViewModel::dataLoadSettled, &loop, [&](bool applied) {
            settled = true;
            loaded = applied;
            loop.quit();
        });
    QTimer guard;
    guard.setSingleShot(true);
    QObject::connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
    guard.start(timeout_ms);
    loop.exec(QEventLoop::ExcludeUserInputEvents);
    QObject::disconnect(end);
    return settled && loaded;
}

}  // namespace edi_app

#endif

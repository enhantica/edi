// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_LOAD_WAIT_HPP
#define EDI_APP_LOAD_WAIT_HPP

#include <QEventLoop>
#include <QTimer>

#include "project_view_model.hpp"

namespace edi_app {

// For a caller that needs the data before it goes on (the documentation capture, the demo, tests): a Load data route
// reads its files off the GUI thread (edi ADR-0110), so `started` is only its first answer. Call it with the route's
// result straight away, `wait_for_load(project, project.loadData(...))`, so the load it names is the one that call
// started. False when the route refused in the call; otherwise whether that load, and no other, ended with the data
// in the project, waiting at most `timeout_ms`. The refusal, if any, is the project's lastError.
inline bool wait_for_load(ProjectViewModel& project, bool started, int timeout_ms = 120000) {
    const int load = project.startedDataLoad();
    if (!started || load == 0) return started;
    bool settled = false;
    bool loaded = false;
    QEventLoop loop;
    const QMetaObject::Connection end =
        QObject::connect(&project, &ProjectViewModel::dataLoadSettled, &loop, [&](int which, bool applied) {
            if (which != load) return;  // another load's end
            settled = true;
            loaded = applied;
            loop.quit();
        });
    const QMetaObject::Connection gone = QObject::connect(&project, &QObject::destroyed, &loop, &QEventLoop::quit);
    QTimer guard;
    guard.setSingleShot(true);
    QObject::connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
    guard.start(timeout_ms);
    loop.exec(QEventLoop::ExcludeUserInputEvents);
    QObject::disconnect(end);
    QObject::disconnect(gone);
    return settled && loaded;
}

}  // namespace edi_app

#endif

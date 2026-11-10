// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_BACKGROUND_HPP
#define EDI_APP_BACKGROUND_HPP

#include <QCoreApplication>
#include <QMetaObject>
#include <utility>

#if !EDI_WORKER_OWNER_THREAD
#include <QtConcurrent/QtConcurrentRun>
#endif

namespace edi_app {

// Runs `work` off the GUI thread where the build has threads. The single-thread WebAssembly build (EDI_WORKER_OWNER_THREAD,
// ADR-0023: nothing there may wait on a thread pool) runs it on the owner thread at the next turn of the event loop,
// as the calculation worker does.
template <typename Work>
void run_in_background(Work work) {
#if EDI_WORKER_OWNER_THREAD
    QMetaObject::invokeMethod(QCoreApplication::instance(), std::move(work), Qt::QueuedConnection);
#else
    (void)QtConcurrent::run(std::move(work));
#endif
}

}  // namespace edi_app

#endif  // EDI_APP_BACKGROUND_HPP

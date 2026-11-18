// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_UI_PROBE_HPP
#define EDI_APP_UI_PROBE_HPP

#include <QJsonObject>
#include <QString>
#include <QtGlobal>

class QCoreApplication;

namespace edi_app {

/// The UI observation trace (ADR-0096), built only where EDI_UI_INSTRUMENTATION is on (development, test, CI and demo
/// builds; compiled out of release builds) and written only when EDI_UI_TRACE=1: one JSON object per line on standard
/// output, `ui-probe: {...}`, each with its `event` name, `t_ms` (the steady clock in milliseconds) and the `thread`
/// that wrote it. While on, a 10 ms timer on the GUI thread writes a `tick` at every delivery, so the gaps between ticks
/// are how long the GUI thread could not answer; the demo driver and the views add their own events. Read by the GUI
/// watchdog (tools/ci/gui_watchdog.py) and the responsiveness checks; it changes nothing the app does.
#if EDI_UI_INSTRUMENTATION
void install_ui_probe(QCoreApplication& app);
/// Whether the trace is on. Callers use EDI_UI_TRACE, which builds an event's fields only then.
bool ui_trace_on();
/// The trace's clock: the steady clock in milliseconds.
qint64 ui_trace_ms();
/// The current thread, as the trace names threads (`gui_thread` in the `clock` event).
QString ui_trace_thread();
/// Writes one event with its fields, adding `event`, `t_ms` and `thread`.
void ui_trace(const char* event, QJsonObject fields = {});
/// The number the main window's next frame will carry in the trace (`render`), and the count's advance when a frame
/// is synchronised (once per frame, the GUI thread waiting), which returns the frame's number.
qint64 ui_trace_next_frame();
qint64 ui_trace_frame_synced();
#define EDI_UI_TRACE(...)                                 \
    do {                                                  \
        if (::edi_app::ui_trace_on()) {                   \
            ::edi_app::ui_trace(__VA_ARGS__);             \
        }                                                 \
    } while (false)
#else
inline void install_ui_probe(QCoreApplication&) {}
inline bool ui_trace_on() { return false; }
inline qint64 ui_trace_ms() { return 0; }
inline QString ui_trace_thread() { return {}; }
inline void ui_trace(const char*, QJsonObject = {}) {}
inline qint64 ui_trace_next_frame() { return 0; }
inline qint64 ui_trace_frame_synced() { return 0; }
#define EDI_UI_TRACE(...) \
    do {                  \
    } while (false)
#endif

}  // namespace edi_app

#endif  // EDI_APP_UI_PROBE_HPP

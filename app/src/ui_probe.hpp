// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_UI_PROBE_HPP
#define EDI_APP_UI_PROBE_HPP

#include <QJsonObject>
#include <QtGlobal>

class QCoreApplication;
class QString;

namespace edi_app {

/// The UI observation trace (ADR-0096), off unless EDI_UI_TRACE=1: one JSON object per line, written to standard
/// output as `ui-probe: {...}`, each with its `event` name and `t_ms`, the steady clock in milliseconds. While on, a
/// 10 ms timer on the GUI thread writes a `tick` at every delivery, so the gaps between ticks are how long the GUI
/// thread could not answer; the demo driver and the views add their own events. Used by the GUI watchdog
/// (tools/ci/gui_watchdog.py) and the responsiveness checks; it changes nothing the app does.
void install_ui_probe(QCoreApplication& app);
/// Whether the trace is on. Cheap: views test it before building an event's fields.
bool ui_trace_on();
/// The trace's clock: the steady clock in milliseconds.
qint64 ui_trace_ms();
/// The current thread, as the trace names threads (`gui_thread` in the `clock` event).
QString ui_trace_thread();
/// Writes one event with its fields; does nothing while the trace is off.
void ui_trace(const char* event, QJsonObject fields = {});

}  // namespace edi_app

#endif  // EDI_APP_UI_PROBE_HPP

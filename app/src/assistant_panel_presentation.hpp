// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QJSEngine>
#include <QJSValue>

namespace edi_app::assistant_panel_presentation {
/// Original full window label, using the caller's current public engine and Panel translation context.
/// Borrows engine/values for the call; leaves original property/call exceptions pending.
QJSValue usageWindowLabel(QJSEngine* engine, const QJSValue& bucket, const QJSValue& window);
/// Shared account-plan word relation used by the native Array.map callback.
/// Borrows engine/value; no state; leaves original String/property/call exceptions pending.
QJSValue accountPlanWord(QJSEngine* engine, const QJSValue& word);
} // namespace edi_app::assistant_panel_presentation

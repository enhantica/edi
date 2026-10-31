// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QString>

// Explicit selected source phase, never inferred from API availability.
namespace e11_usage_phase {
inline QByteArray phase() { return QByteArrayLiteral("native"); }
inline QByteArray panelHash() { return QByteArrayLiteral("PENDING_ROOT_NATIVE_PANEL_SHA256"); }
inline QString reset(const QString& value, const QString& now) {
    return "usageResetLabel(" + value + "," + now + ")";
}
inline QString color(const QString& remaining) { return "allowanceColor(" + remaining + ")"; }
}  // namespace e11_usage_phase

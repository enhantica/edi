// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QString>

// Explicit selected source phase, never inferred from API availability.
namespace e11_usage_phase {
inline QByteArray phase() { return QByteArrayLiteral("native"); }
inline QByteArray panelHash() { return QByteArrayLiteral("9fd54035a664956aa91352716c64fd89c2d79b0b01c7f568b5569d5e6df76fa3"); }
inline QString reset(const QString& value, const QString& now) {
    return "usageResetLabel(" + value + "," + now + ")";
}
inline QString color(const QString& remaining) { return "allowanceColor(" + remaining + ")"; }
}  // namespace e11_usage_phase

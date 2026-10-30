// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QString>

// Explicit selected source phase, never inferred from API availability.
namespace e11_usage_phase {
inline QByteArray phase() { return QByteArrayLiteral("original"); }
inline QByteArray panelHash() {
    return QByteArrayLiteral("3f32348e85df85cc7cb23b2bef428493fd79adbe587529310684311b38f63ddb");
}
inline QString reset(const QString& value, const QString& now) {
    return "usageResetLabel(" + value + "," + now + ")";
}
inline QString color(const QString& remaining) { return "allowanceColor(" + remaining + ")"; }
}  // namespace e11_usage_phase

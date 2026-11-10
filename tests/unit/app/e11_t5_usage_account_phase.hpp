// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <QByteArray>
#include <QString>

// Explicit selected source phase, never inferred from API availability.
namespace e11_usage_phase {
inline QByteArray phase() { return QByteArrayLiteral("native"); }
inline QByteArray panelHash() { return QByteArrayLiteral("5a33d233fe505fee567e8e2fadef0698fb55cf2d29b48f5c3afa9cfb6b1b9695"); }
inline QString reset(const QString& value, const QString& now) {
    return "usageResetLabel(" + value + "," + now + ")";
}
inline QString color(const QString& remaining) { return "allowanceColor(" + remaining + ")"; }
}  // namespace e11_usage_phase
